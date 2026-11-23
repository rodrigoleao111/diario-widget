"""Resumos pelos botões do widget: `[resumir]` / `[atualizar]` (um dia) e `[resumir semana]` (no calendário).

Faz o mesmo que a skill `/diario resumir`, mas sem abrir uma sessão do Claude Code: coleta, monta o `contexto` de cada dia e
pede ao `claude -p` (sem ferramentas, sem gravar sessão) o parágrafo e os tópicos de todos os dias numa só chamada. Quem
grava no banco é este módulo. Exige o `claude` da linha de comando autenticado (`claude /login`).
"""
import json
import os
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

from . import coleta_claude, config, db, exporta

TIMEOUT_BASE_S, TIMEOUT_DIA_S = 120, 90
MAX_TOPICOS = 9

# Espelha os passos 2, 3 e 3b da skill diario; se o estilo mudar lá, mude aqui.
INSTRUCAO = """Você escreve o resumo de dias de trabalho do usuário para o diário de atividades. \
Abaixo vem o material bruto de cada dia: por projeto, cada PEDIDO feito ao Claude Code com a RESPOSTA dele, mais commits SVN e \
lançamentos manuais.

Para CADA dia, escreva:
1. "texto": UM parágrafo, em primeira pessoa e no passado, no estilo de apontamento: \
"Projeto #ticket: resolvi o conflito da sincronização com a trunk (revisões 19424-19821), ajustei a regra de visualização e \
testei no servidor de homologação...". Várias frentes no mesmo dia entram em sequência no mesmo parágrafo, cada uma com projeto e \
ticket na frente.
2. "topicos": de 2 a 9 linhas curtas (até ~60 caracteres), uma por assunto, no formato "#ticket O que foi feito (rNNN)" ou \
"Projeto: o que foi feito".

Regras:
- Base: o que a RESPOSTA diz que foi feito e os commits (revisão e ticket). Nada de horário, nada de "o usuário pediu", nada que os \
dados não sustentem. Se a resposta diz que algo não foi validado ou commitado, não escreva como pronto.
- Não inclua lançamentos manuais, nem no texto nem nos tópicos.
- Só trabalho. Deixe de fora o que é pessoal, mesmo vindo de \
sessão marcada como trabalho: contratos e assuntos da vida pessoal, e os projetos pessoais do usuário, como o próprio diário de \
atividades (app Python do widget).

Responda SOMENTE com um objeto JSON, sem comentário e sem cercas de código, com uma chave por dia (AAAA-MM-DD):
{"dias": {"AAAA-MM-DD": {"texto": "...", "topicos": ["...", "..."]}}}

MATERIAL
"""


class ErroResumo(Exception):
    """Falha com mensagem pronta para a linha de status do widget."""


def _executavel():
    achado = shutil.which("claude")
    if achado:
        return achado
    npm = Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"
    if npm.exists():
        return str(npm)
    raise ErroResumo("claude não encontrado no PATH")


def _pedir(material, n_dias):
    """Roda `claude -p` com o material na entrada padrão e devolve o texto da resposta."""
    cmd = [_executavel(), "-p", "--tools", "", "--no-session-persistence", "--disable-slash-commands"]
    limite = TIMEOUT_BASE_S + TIMEOUT_DIA_S * n_dias
    for _tentativa in range(2):  # o claude às vezes sai com código 0 e sem escrever nada (visto ao renovar o login)
        try:
            r = subprocess.run(cmd, input=INSTRUCAO + material, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", cwd=config.RAIZ, timeout=limite, creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired:
            raise ErroResumo(f"o Claude não respondeu em {limite // 60} min")
        saida = (r.stdout or "").strip()
        if "Not logged in" in saida:
            raise ErroResumo("claude não está logado: rode  claude /login  num terminal")
        if r.returncode != 0:
            raise ErroResumo((saida or (r.stderr or "").strip() or f"claude saiu com código {r.returncode}").splitlines()[0][:80])
        if saida:
            return saida
    raise ErroResumo("o Claude respondeu vazio duas vezes; tente de novo")


def _extrair(saida, dias):
    """{dia ISO: (texto, tópicos)} dos dias pedidos que vieram completos; tolera texto solto em volta do JSON."""
    try:
        dados = json.loads(saida[saida.index("{"):saida.rindex("}") + 1])["dias"]
    except (ValueError, KeyError, TypeError):
        raise ErroResumo("resposta do Claude fora do formato esperado")
    achados = {}
    for dia in dias:
        try:
            texto = str(dados[dia]["texto"]).strip()
            topicos = [str(t).strip() for t in dados[dia]["topicos"] if str(t).strip()][:MAX_TOPICOS]
        except (KeyError, TypeError):
            continue
        if texto and topicos:
            achados[dia] = (texto, topicos)
    if not achados:
        raise ErroResumo("resposta do Claude veio sem texto ou sem tópicos")
    return achados


def _gerar(con, dias):
    """Pede ao Claude o resumo de `dias` (lista de date), grava o que veio e regera os .md. Levanta ErroResumo."""
    isos = [d.isoformat() for d in dias]
    material = "\n".join(exporta.contexto_do_dia(con, iso, sem_pessoal=True) for iso in isos)
    achados = _extrair(_pedir(material, len(dias)), isos)
    for iso, (texto, topicos) in achados.items():
        db.salvar_resumo(con, iso, texto, topicos)
    for d in dias:
        if d.isoformat() in achados:
            exporta.exportar(con, config.SAIDA_MD, d, d)
    faltam = [d for d in dias if d.isoformat() not in achados]
    if faltam:
        raise ErroResumo("o Claude não devolveu o resumo de " + ", ".join(f"{d:%d/%m}" for d in faltam))


def resumir(dia):
    """Botão [resumir] / [atualizar]: coleta as sessões do dia e (re)escreve o resumo dele."""
    con = db.conectar()
    coleta_claude.coletar(con, dia)
    _gerar(con, [dia])


def _precisa_resumo(con, iso):
    """O dia tem atividade de trabalho e o resumo falta ou ficou velho."""
    ha = con.execute("SELECT 1 FROM eventos WHERE data=? AND origem IN ('claude','svn') "
                     "AND COALESCE(categoria,'')!='pessoal' LIMIT 1", (iso,)).fetchone()
    return bool(ha) and (not db.topicos_do_dia(con, iso) or db.resumo_defasado(con, iso) is not None)


def resumir_semana(de, ate):
    """Botão [resumir semana]: resume só os dias que precisam, grava o relatório da semana e devolve o caminho dele."""
    con = db.conectar()
    coleta_claude.coletar(con, de)
    dias = [de + timedelta(days=i) for i in range((ate - de).days + 1)]
    pendentes = [d for d in dias if _precisa_resumo(con, d.isoformat())]
    if pendentes:
        _gerar(con, pendentes)
    pasta = config.SAIDA_MD / f"{de:%Y-%m}"
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{de.isoformat()}_semana.txt"
    arq.write_text(exporta.semana_txt(con, de, ate), encoding="utf-8-sig")
    return arq
