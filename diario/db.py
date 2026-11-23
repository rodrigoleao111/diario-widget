import re
import sqlite3
import uuid
from datetime import datetime, timedelta

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS eventos (
    id        INTEGER PRIMARY KEY,
    ref       TEXT NOT NULL UNIQUE,
    ts        TEXT NOT NULL,
    data      TEXT NOT NULL,
    origem    TEXT NOT NULL,          -- claude | svn | manual
    projeto   TEXT,
    categoria TEXT,
    tickets   TEXT NOT NULL DEFAULT '',
    texto     TEXT NOT NULL,
    resposta  TEXT NOT NULL DEFAULT '',  -- último texto do Claude depois deste pedido (só origem claude)
    minutos   INTEGER                    -- duração informada (só origem manual)
);
CREATE INDEX IF NOT EXISTS ix_eventos_data ON eventos(data);

CREATE TABLE IF NOT EXISTS segmentos (
    id        INTEGER PRIMARY KEY,
    origem    TEXT NOT NULL,          -- claude | manual
    data      TEXT NOT NULL,
    projeto   TEXT,
    categoria TEXT,
    inicio    TEXT NOT NULL,
    fim       TEXT NOT NULL,
    minutos   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_segmentos_data ON segmentos(data);

CREATE TABLE IF NOT EXISTS resumos (
    data      TEXT PRIMARY KEY,
    texto     TEXT NOT NULL,
    gerado_em TEXT NOT NULL,
    topicos   TEXT NOT NULL DEFAULT ''   -- uma linha curta por tópico, para o widget
);
"""

_TICKET = re.compile(r"(?:#|\b(?:tkts?|tickets?|chamados?|redmine|bugs?)\s*#?\s*)(\d{5,6}(?:\s*(?:,|e|/)\s*#?\d{5,6})*)\b", re.I)


def conectar():
    con = sqlite3.connect(config.DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    colunas = {r[1] for r in con.execute("PRAGMA table_info(eventos)")}
    for nome, tipo in (("resposta", "TEXT NOT NULL DEFAULT ''"), ("minutos", "INTEGER")):  # banco criado antes da coluna
        if nome not in colunas:
            con.execute(f"ALTER TABLE eventos ADD COLUMN {nome} {tipo}")
    if "topicos" not in {r[1] for r in con.execute("PRAGMA table_info(resumos)")}:
        con.execute("ALTER TABLE resumos ADD COLUMN topicos TEXT NOT NULL DEFAULT ''")
    return con


def tickets_em(texto):
    numeros = (n for grupo in _TICKET.findall(texto) for n in re.findall(r"\d{5,6}", grupo))  # "tickets 103687 e 103700"
    return ",".join(f"#{n}" for n in sorted(set(numeros)))


# duração no começo do texto: 30min, 30m, 1h, 1h30, 1h30min, 1h 30min
_DURACAO = re.compile(r"^\s*(?:(\d+)\s*h(?:(\d{1,2})(?:min|m)?|\s+(\d{1,2})\s*(?:min|m)\b)?|(\d+)\s*(?:min|m))(?=\s|$)", re.I)


def duracao(texto):
    """'1h30 reunião' -> (90, 'reunião'); None se o texto não começa com uma duração."""
    m = _DURACAO.match(texto)
    if not m:
        return None
    h, m_junto, m_solto, so_min = m.groups()
    return int(h or 0) * 60 + int(m_junto or m_solto or so_min or 0), texto[m.end():].strip()


def lancar(con, texto, dia, projeto="(manual)", categoria="trabalho", minutos=None):
    """Lançamento manual. Sem minutos entra só o texto, sem duração; com minutos soma ao total do dia."""
    ts = datetime.fromisoformat(f"{dia.isoformat()} {datetime.now():%H:%M}")
    con.execute(
        "INSERT INTO eventos(ref, ts, data, origem, projeto, categoria, tickets, texto, minutos) VALUES (?,?,?,?,?,?,?,?,?)",
        (f"manual:{uuid.uuid4().hex}", ts.isoformat(" ", "seconds"), dia.isoformat(), "manual",
         projeto, categoria, tickets_em(texto), texto, minutos),
    )
    if minutos:
        con.execute(
            "INSERT INTO segmentos(origem, data, projeto, categoria, inicio, fim, minutos) VALUES (?,?,?,?,?,?,?)",
            ("manual", dia.isoformat(), projeto, categoria, ts.isoformat(" ", "seconds"),
             (ts + timedelta(minutes=minutos)).isoformat(" ", "seconds"), minutos),
        )
    con.commit()


def salvar_resumo(con, dia, texto, topicos=None):
    """Grava o resumo do dia. Sem topicos, mantém os que já existiam."""
    con.execute(
        "INSERT INTO resumos(data, texto, gerado_em, topicos) VALUES (?,?,?,?)"
        " ON CONFLICT(data) DO UPDATE SET texto=excluded.texto, gerado_em=excluded.gerado_em,"
        " topicos=CASE WHEN excluded.topicos='' THEN resumos.topicos ELSE excluded.topicos END",
        (dia, texto.strip(), datetime.now().isoformat(" ", "seconds"), "\n".join(t.strip() for t in topicos or [])),
    )
    con.commit()


def resumo_do_dia(con, dia):
    r = con.execute("SELECT texto FROM resumos WHERE data=?", (dia,)).fetchone()
    return r["texto"] if r else None


def resumo_defasado(con, dia):
    """Hora (ISO) da última atividade de trabalho do dia posterior à gravação do resumo, ou None se o resumo está em dia
    (atividade pessoal não conta: o resumo não a cobre)."""
    r = con.execute("SELECT gerado_em FROM resumos WHERE data=?", (dia,)).fetchone()
    if not r:
        return None
    ultimo = con.execute("SELECT MAX(ts) FROM eventos WHERE data=? AND origem IN ('claude','svn') "
                         "AND COALESCE(categoria,'')!='pessoal'", (dia,)).fetchone()[0]
    return ultimo if ultimo and ultimo > r["gerado_em"] else None


def topicos_do_dia(con, dia):
    """Linhas curtas do resumo do dia (as mesmas do widget), sem os lançamentos manuais."""
    r = con.execute("SELECT topicos FROM resumos WHERE data=?", (dia,)).fetchone()
    return [t.strip() for t in (r["topicos"].splitlines() if r else []) if t.strip()]
