from datetime import date, datetime, timedelta

from . import config, db

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MAX_PEDIDOS = 12


def hm(minutos):
    h, m = divmod(round(minutos), 60)
    return f"{h}h{m:02d}"


def uniao_minutos(intervalos):
    total, ini_atual, fim_atual = timedelta(), None, None
    for ini, fim in sorted(intervalos):
        if fim_atual is None or ini > fim_atual:
            if fim_atual:
                total += fim_atual - ini_atual
            ini_atual, fim_atual = ini, fim
        else:
            fim_atual = max(fim_atual, fim)
    if fim_atual:
        total += fim_atual - ini_atual
    return total.total_seconds() / 60


def total_minutos(segs, cat=None):
    """Minutos do dia (na categoria, ou em todas se cat for None): união dos trechos medidos (sem contar sobreposição)
    mais as durações informadas à mão."""
    medidos = [(datetime.fromisoformat(s["inicio"]), datetime.fromisoformat(s["fim"]))
               for s in segs if cat in (None, s["categoria"]) and s["origem"] != "manual"]
    return uniao_minutos(medidos) + sum(s["minutos"] for s in segs if cat in (None, s["categoria"]) and s["origem"] == "manual")


def _dt(s):
    return datetime.fromisoformat(s)


def _juntar_tickets(linhas):
    return ", ".join(sorted({t for l in linhas for t in l["tickets"].split(",") if t}))


def _manual(e):
    projeto = "" if e["projeto"] == "(manual)" else f"[{e['projeto']}] "  # "(manual)" é só o projeto padrão
    return f"{_dt(e['ts']):%H:%M} {projeto}{e['texto']}" + (f" ({hm(e['minutos'])})" if e["minutos"] else "")


def dia_md(con, dia):
    segs = con.execute("SELECT * FROM segmentos WHERE data=? ORDER BY inicio", (dia,)).fetchall()
    evs = con.execute("SELECT * FROM eventos WHERE data=? ORDER BY ts", (dia,)).fetchall()
    if not segs and not evs:
        return None

    d = date.fromisoformat(dia)
    out = [f"# Diário — {DIAS[d.weekday()]}, {d:%d/%m/%Y}", ""]

    totais = []
    for cat in ("trabalho", "pessoal"):
        if any(s["categoria"] == cat for s in segs):
            totais.append(f"{cat} {hm(total_minutos(segs, cat))}")
    if totais:
        out += [f"**Tempo ativo estimado (sem sobreposição):** {' · '.join(totais)}", ""]

    resumo = db.resumo_do_dia(con, dia)
    if resumo:
        out += ["## Resumo", "", resumo, ""]

    projetos = []
    for s in segs:
        if s["projeto"] not in projetos:
            projetos.append(s["projeto"])
    if projetos:
        out += ["| Projeto | Categoria | Tickets | Janela | Horas est. |", "|---|---|---|---|---|"]
        for p in projetos:
            ss = [s for s in segs if s["projeto"] == p]
            tk = _juntar_tickets([e for e in evs if e["projeto"] == p])
            ini, fim = min(_dt(s["inicio"]) for s in ss), max(_dt(s["fim"]) for s in ss)
            out.append(f"| {p} | {ss[0]['categoria']} | {tk or '—'} | {'—' if all(s['origem'] == 'manual' for s in ss) else f'{ini:%H:%M}–{fim:%H:%M}'} | {hm(sum(s['minutos'] for s in ss))} |")
        out.append("")

    for p in projetos:
        pedidos = [e for e in evs if e["projeto"] == p and e["origem"] == "claude"]
        if not pedidos:
            continue
        out += [f"## {p}", "", f"Pedidos ao Claude ({len(pedidos)}):", ""]
        out += [f"- {_dt(e['ts']):%H:%M} {e['texto'][:140]}" for e in pedidos[:MAX_PEDIDOS]]
        if len(pedidos) > MAX_PEDIDOS:
            out.append(f"- … e mais {len(pedidos) - MAX_PEDIDOS}")
        out.append("")

    commits = [e for e in evs if e["origem"] == "svn"]
    if commits:
        out += ["## Commits SVN", ""] + [f"- {_dt(e['ts']):%H:%M} {e['texto']}" for e in commits] + [""]

    manuais = [e for e in evs if e["origem"] == "manual"]
    if manuais:
        out += ["## Lançamentos manuais", ""] + [f"- {_manual(e)}" for e in manuais] + [""]

    return "\n".join(out)


def dia_txt(con, dia):
    """Relatório do dia em texto puro: resumo narrativo, horas por projeto, commits e lançamentos manuais."""
    segs = con.execute("SELECT * FROM segmentos WHERE data=? ORDER BY inicio", (dia,)).fetchall()
    evs = con.execute("SELECT * FROM eventos WHERE data=? ORDER BY ts", (dia,)).fetchall()
    d = date.fromisoformat(dia)
    out = [f"RELATÓRIO DE ATIVIDADES — {DIAS[d.weekday()]}, {d:%d/%m/%Y}", ""]
    if not segs and not evs:
        return "\n".join(out + ["Nada registrado neste dia.", ""])

    out += [f"Total: {hm(total_minutos(segs))} (estimado, sem sobreposição)", ""]

    topicos, resumo = db.topicos_do_dia(con, dia), db.resumo_do_dia(con, dia)
    out += ["RESUMO", "------"]
    if topicos:
        out += [f"- {t}" for t in topicos]
    else:  # resumo escrito antes dos tópicos existirem, ou ainda não escrito
        out.append(resumo or "(resumo ainda não escrito — peça \"/diario resumir\" ao Claude Code)")
    ultimo = db.resumo_defasado(con, dia)
    if ultimo:
        gravado = con.execute("SELECT gerado_em FROM resumos WHERE data=?", (dia,)).fetchone()[0]
        out.append(f"(resumo gravado às {_dt(gravado):%H:%M}; há atividade até {_dt(ultimo):%H:%M} — rode \"/diario resumir\")")
    out.append("")

    projetos = list(dict.fromkeys(s["projeto"] for s in segs))
    if projetos:
        out += ["HORAS", "-----"]
        for p in projetos:
            ss = [s for s in segs if s["projeto"] == p]
            tk = _juntar_tickets([e for e in evs if e["projeto"] == p])
            ini, fim = min(_dt(s["inicio"]) for s in ss), max(_dt(s["fim"]) for s in ss)
            janela = "" if all(s["origem"] == "manual" for s in ss) else f" ({ini:%H:%M}–{fim:%H:%M})"  # manual só tem duração
            out.append(f"{p} — {hm(sum(s['minutos'] for s in ss))}{janela}" + (f" — tickets {tk}" if tk else ""))
        out.append("")

    commits = [e for e in evs if e["origem"] == "svn"]
    if commits:
        out += ["COMMITS SVN", "-" * 11] + [f"{_dt(e['ts']):%H:%M} {e['texto']}" for e in commits] + [""]

    manuais = [e for e in evs if e["origem"] == "manual"]
    if manuais:
        out += ["LANÇAMENTOS MANUAIS", "-------------------"] + [_manual(e) for e in manuais] + [""]

    return "\n".join(out)


def semana_txt(con, de, ate):
    """Relatório da semana para apontar horas: por dia com atividade, as horas de trabalho, o resumo e os lançamentos manuais."""
    blocos, total, pessoal = [], 0, 0
    for i in range((ate - de).days + 1):
        d = de + timedelta(days=i)
        iso = d.isoformat()
        segs = con.execute("SELECT * FROM segmentos WHERE data=?", (iso,)).fetchall()
        manuais = con.execute("SELECT * FROM eventos WHERE data=? AND origem='manual' AND categoria!='pessoal' ORDER BY ts",
                              (iso,)).fetchall()
        minutos, resumo = total_minutos(segs, "trabalho"), db.resumo_do_dia(con, iso)
        total += minutos
        pessoal += total_minutos(segs, "pessoal")
        if not (minutos or resumo or manuais):
            continue
        bloco = [f"{DIAS[d.weekday()][:3]} {d:%d/%m} — {hm(minutos)}", resumo or "(resumo ainda não escrito)"]
        bloco += [f"Manual: {_manual(e)}" for e in manuais]
        blocos.append("\n".join(bloco))
    out = [f"RELATÓRIO DA SEMANA — {de:%d/%m} a {ate:%d/%m/%Y}", "",
           f"Total de trabalho: {hm(total)} (estimado, sem sobreposição; o silêncio acima de {config.GAP_MIN} min corta o trecho). "
           "Ajuste antes de apontar."]
    if pessoal:
        out.append(f"Fora do total: {hm(pessoal)} de atividade pessoal.")
    return "\n".join(out + [""] + ["\n\n".join(blocos) if blocos else "Nada registrado nesta semana.", ""])


def contexto_do_dia(con, dia, sem_pessoal=False):
    """Material bruto do dia para escrever o resumo: o que foi pedido, o que o Claude respondeu, commits e lançamentos.
    `sem_pessoal` tira os projetos de categoria pessoal (o botão do widget não confia no modelo para ignorá-los)."""
    evs = con.execute("SELECT * FROM eventos WHERE data=? ORDER BY ts", (dia,)).fetchall()
    segs = con.execute("SELECT * FROM segmentos WHERE data=?", (dia,)).fetchall()
    d = date.fromisoformat(dia)
    out = [f"DIA {dia} ({DIAS[d.weekday()]})", ""]
    for p in dict.fromkeys(s["projeto"] for s in segs):
        ss = [s for s in segs if s["projeto"] == p]
        if sem_pessoal and ss[0]["categoria"] == "pessoal":
            continue
        out.append(f"[{p}] categoria={ss[0]['categoria']} horas={hm(sum(s['minutos'] for s in ss))}")
        for e in (e for e in evs if e["projeto"] == p and e["origem"] == "claude"):
            out.append(f"  {_dt(e['ts']):%H:%M} PEDIDO: {e['texto'][:300]}")
            if e["resposta"]:
                out.append(f"        RESPOSTA: {e['resposta'][:500]}")
        out.append("")
    for titulo, origem in (("COMMITS SVN", "svn"), ("LANÇAMENTOS MANUAIS", "manual")):
        linhas = [e for e in evs if e["origem"] == origem]
        if linhas:
            out += [titulo] + [f"  {_manual(e)}" for e in linhas] + [""]
    resumo = db.resumo_do_dia(con, dia)
    if resumo:
        out += ["RESUMO ATUAL", resumo, ""]
    return "\n".join(out)


def exportar(con, saida, de, ate):
    escritos = []
    d = de
    while d <= ate:
        md = dia_md(con, d.isoformat())
        if md:
            pasta = saida / f"{d:%Y-%m}"
            pasta.mkdir(parents=True, exist_ok=True)
            arq = pasta / f"{d.isoformat()}.md"
            arq.write_text(md, encoding="utf-8")
            escritos.append(arq)
        d += timedelta(days=1)
    return escritos
