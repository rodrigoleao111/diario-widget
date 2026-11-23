import glob
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path, PureWindowsPath

from . import config
from .db import tickets_em

_RUIDO = ("This session is being continued", "Base directory for this skill", "[Request interrupted", "[Image", "Caveat:")
_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def rotulo(cwd):
    partes = PureWindowsPath(cwd).parts
    if config.PASTA_BRANCHES and len(partes) > 3 and partes[1] == config.PASTA_BRANCHES:
        return "/".join(partes[2:4])
    if PureWindowsPath(cwd) == PureWindowsPath(Path.home()):
        return "(home)"
    return PureWindowsPath(cwd).name or cwd


def categoria(cwd):
    for padrao, nome in config.CATEGORIAS:
        if re.search(padrao, cwd):
            return nome


def texto_do_usuario(msg):
    c = msg.get("content")
    if isinstance(c, list):
        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    if not isinstance(c, str):
        return None
    c = _REMINDER.sub("", c).strip()
    if not c or c.startswith(_RUIDO) or "tool_use_id" in c:
        return None
    if c.startswith("<") and not c.startswith("<pasted_content"):
        return None
    return re.sub(r"\s+", " ", c)


def texto_do_assistente(msg):
    c = msg.get("content")
    if not isinstance(c, list):
        return None
    t = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text").strip()
    return re.sub(r"\s+", " ", t) or None


def _local(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)


def ler_sessoes(desde):
    """Devolve (eventos, pulsos). pulsos: {(projeto, categoria, data): {datetime}}."""
    eventos, pulsos = [], defaultdict(set)
    corte = datetime.combine(desde, datetime.min.time())
    for f in glob.glob(str(config.PROJETOS_CLAUDE / "*" / "*.jsonl")):
        if datetime.fromtimestamp(os.path.getmtime(f)) < corte:
            continue
        pasta = os.path.basename(os.path.dirname(f))
        raiz, itens = None, []
        for linha in open(f, encoding="utf-8", errors="ignore"):
            try:
                o = json.loads(linha)
            except ValueError:
                continue
            # a pasta do transcrito é o nome do cwd de abertura com tudo que não é alfanumérico trocado por "-";
            # o primeiro cwd do arquivo não serve (sessão retomada de outra pasta) e os cd internos também não
            c = o.get("cwd")
            if c and not raiz and re.sub(r"[^A-Za-z0-9]", "-", c) == pasta:
                raiz = c
            tipo, ts = o.get("type"), o.get("timestamp")
            if tipo not in ("user", "assistant") or not ts:
                continue
            t = _local(ts)
            if t < corte:
                continue
            texto = None
            if tipo == "user" and not o.get("isSidechain"):
                texto = texto_do_usuario(o.get("message", {}))
            elif tipo == "assistant" and not o.get("isSidechain"):
                # o texto que o Claude deixou por último depois do pedido é o que diz o que foi feito
                resp = texto_do_assistente(o.get("message", {}))
                if resp:
                    for it in reversed(itens):
                        if it[1] is not None:
                            it[2] = resp
                            break
            itens.append([t, texto, ""])
        raiz = raiz or pasta
        proj, cat = rotulo(raiz), categoria(raiz)
        for t, texto, resp in itens:
            pulsos[(proj, cat, t.date().isoformat())].add(t)
            if texto:
                eventos.append((t, proj, cat, texto[:400], resp[:700]))
    return eventos, pulsos


def segmentos(pulsos):
    for (proj, cat, dia), ts in pulsos.items():
        ts = sorted(ts)
        ini = fim = ts[0]
        for t in ts[1:]:
            if t - fim > timedelta(minutes=config.GAP_MIN):
                yield proj, cat, dia, ini, fim + timedelta(minutes=config.CAUDA_MIN)
                ini = t
            fim = t
        yield proj, cat, dia, ini, fim + timedelta(minutes=config.CAUDA_MIN)


def coletar(con, desde):
    eventos, pulsos = ler_sessoes(desde)
    novos = 0
    for t, proj, cat, texto, resp in eventos:
        ref = "claude:" + hashlib.sha1(f"{t.isoformat()}{texto}".encode()).hexdigest()[:16]
        cur = con.execute(
            "INSERT OR IGNORE INTO eventos(ref, ts, data, origem, projeto, categoria, tickets, texto, resposta)"
            " VALUES (?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(ref) DO UPDATE SET projeto=excluded.projeto, categoria=excluded.categoria,"
            " tickets=excluded.tickets, resposta=excluded.resposta",
            (ref, t.isoformat(" ", "seconds"), t.date().isoformat(), "claude", proj, cat, tickets_em(texto), texto, resp),
        )
        novos += cur.rowcount
    # só refaz os dias que o scan viu: transcritos já expirados não apagam o que está no banco
    for dia in {d for _, _, d in pulsos}:
        con.execute("DELETE FROM segmentos WHERE origem='claude' AND data=?", (dia,))
    n_seg = 0
    for proj, cat, dia, ini, fim in segmentos(pulsos):
        minutos = round((fim - ini).total_seconds() / 60)
        con.execute(
            "INSERT INTO segmentos(origem, data, projeto, categoria, inicio, fim, minutos) VALUES (?,?,?,?,?,?,?)",
            ("claude", dia, proj, cat, ini.isoformat(" ", "seconds"), fim.isoformat(" ", "seconds"), minutos),
        )
        n_seg += 1
    con.commit()
    return novos, n_seg
