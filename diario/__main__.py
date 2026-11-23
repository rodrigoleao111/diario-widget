import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from . import coleta_claude, coleta_svn, config, db, exporta


def _data(s):
    return date.fromisoformat(s)


def cmd_coletar(a):
    con = db.conectar()
    novos, n_seg = coleta_claude.coletar(con, a.desde)
    print(f"Claude Code: {novos} pedidos lidos, {n_seg} segmentos de atividade desde {a.desde}")
    if not a.sem_svn and config.SVN_URL:
        try:
            print(f"SVN: {coleta_svn.coletar(con, a.desde)} commits novos")
        except (subprocess.SubprocessError, OSError) as e:  # servidor fora do ar ou inacessível (VPN?)
            print(f"SVN: não coletado ({type(e).__name__}); rode de novo com o servidor acessível")


def cmd_exportar(a):
    con = db.conectar()
    de = a.dia or a.desde
    ate = a.dia or a.ate
    for arq in exporta.exportar(con, Path(a.saida), de, ate):
        print(arq)


def cmd_add(a):
    minutos = None
    if a.duracao:
        d = db.duracao(a.duracao)
        if not d or d[1]:
            sys.exit(f"Duração inválida: {a.duracao!r} (use 30min, 1h, 1h30...)")
        minutos = d[0]
    db.lancar(db.conectar(), a.texto, a.dia, a.projeto, a.categoria, minutos)
    print("Lançamento registrado.")


def cmd_contexto(a):
    print(exporta.contexto_do_dia(db.conectar(), a.dia.isoformat()))


def cmd_resumo(a):
    texto = sys.stdin.read() if a.texto == "-" else a.texto
    db.salvar_resumo(db.conectar(), a.dia.isoformat(), texto, a.topico)
    print(f"Resumo de {a.dia.isoformat()} gravado.")


def cmd_widget(a):
    from . import widget
    widget.abrir()


def main():
    if sys.stdout:  # sob pythonw não há stdout
        sys.stdout.reconfigure(encoding="utf-8")
    hoje = date.today()
    p = argparse.ArgumentParser(prog="diario")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("coletar", help="lê transcritos do Claude Code e o svn log para o banco")
    c.add_argument("--desde", type=_data, default=hoje)
    c.add_argument("--sem-svn", action="store_true")
    c.set_defaults(fn=cmd_coletar)

    e = sub.add_parser("exportar", help="gera os .md diários a partir do banco")
    e.add_argument("--dia", type=_data)
    e.add_argument("--desde", type=_data, default=hoje)
    e.add_argument("--ate", type=_data, default=hoje)
    e.add_argument("--saida", default=str(config.SAIDA_MD))
    e.set_defaults(fn=cmd_exportar)

    m = sub.add_parser("add", help="lançamento manual (reunião, ligação...)")
    m.add_argument("texto")
    m.add_argument("--dia", type=_data, default=hoje)
    m.add_argument("--projeto", default="(manual)")
    m.add_argument("--categoria", default="trabalho")
    m.add_argument("--duracao", help="30min, 1h, 1h30...")
    m.set_defaults(fn=cmd_add)

    x = sub.add_parser("contexto", help="imprime o material bruto do dia para escrever o resumo")
    x.add_argument("--dia", type=_data, default=hoje)
    x.set_defaults(fn=cmd_contexto)

    r = sub.add_parser("resumo", help="grava o resumo narrativo do dia ('-' lê da entrada padrão)")
    r.add_argument("texto")
    r.add_argument("--topico", action="append", help="linha curta para o widget; repita a opção para cada tópico")
    r.add_argument("--dia", type=_data, default=hoje)
    r.set_defaults(fn=cmd_resumo)

    sub.add_parser("widget", help="abre o widget de desktop").set_defaults(fn=cmd_widget)

    a = p.parse_args()
    a.fn(a)


main()
