"""Tema Clássico: o visual escuro original do widget (cores sólidas, Segoe UI), desenhado com PIL."""
import calendar
from datetime import date
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from . import base
from .base import BOTOES, DIAS_SEMANA, DICAS, MESES, Quadro, Regiao, Tema

BG, FG, DIM, ACC, OK, ERRO = "#1e2430", "#e6e9ef", "#8b93a5", "#4da3ff", "#6fcf97", "#eb5757"
BORDA, CAMPO = "#3a4254", "#2a3243"
_FONTES = "C:/Windows/Fonts/"
GLIFOS = {"fechar": "✕", "relatorio": "▤", "atualizar": "↻", "proximo": "▶", "calendario": "📅", "anterior": "◀",
          "config": "⚙"}


@lru_cache(maxsize=None)
def _fonte(arquivo, px):
    try:
        return ImageFont.truetype(_FONTES + arquivo, px)
    except OSError:
        return ImageFont.load_default()


def _quebra(texto, fonte, px, max_linhas):
    """Quebra por palavras em até max_linhas linhas de px pixels; a última leva reticências se sobrar."""
    linhas, atual = [], ""
    for palavra in texto.split():
        tentativa = (atual + " " + palavra).strip()
        if fonte.getlength(tentativa) <= px or not atual:
            atual = tentativa
        else:
            linhas.append(atual)
            atual = palavra
    linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        while linhas[-1] and fonte.getlength(linhas[-1] + "…") > px:
            linhas[-1] = linhas[-1][:-1]
        linhas[-1] = linhas[-1].rstrip() + "…"
    return linhas


def _cabe(texto, fonte, px):
    if fonte.getlength(texto) <= px:
        return texto
    while texto and fonte.getlength(texto + "…") > px:
        texto = texto[:-1]
    return texto.rstrip() + "…"


class Classico(Tema):
    id = "classico"
    nome = "Clássico"
    descricao = "O visual escuro original: cores sólidas e fonte do Windows."
    hover_no_status = True
    LARGURA = 608

    def _fontes(self):
        s = base.ESCALA
        return dict(titulo=_fonte("segoeuib.ttf", round(13.3 * s)), icone=_fonte("seguisym.ttf", round(14.7 * s)),
                    texto=_fonte("segoeui.ttf", round(12 * s)), peq=_fonte("segoeui.ttf", round(10.7 * s)),
                    negrito=_fonte("segoeuib.ttf", round(12 * s)))

    def quadro(self, e, t):
        s, W, f = base.ESCALA, self.LARGURA, self._fontes()
        hh, rh = round(26 * s), round(17 * s)
        n = len(e.topicos) or 1
        y_lista = 8 + hh + 6
        y_extra = y_lista + n * rh
        y_campo = y_extra + (round(14 * s) if e.extra else 0) + 8
        h_campo = round(28 * s)
        cor_status = {"ok": OK, "info": ACC, "erro": ERRO}.get(e.status_tipo, DIM)
        linhas_status = _quebra(e.status or base.DICA_ENTRADA, f["peq"], W - 24, 2)
        y_status = y_campo + h_campo + 3
        H = y_status + len(linhas_status) * round(14 * s) + 8
        im = Image.new("RGBA", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W - 1, H - 1], outline=BORDA)
        regioes = []
        # botões da direita para a esquerda
        iw, x = round(24 * s), W - 6
        for nome in reversed(BOTOES):
            x -= iw
            caixa = (x, 6, x + iw, 6 + hh)
            d.text(((caixa[0] + caixa[2]) // 2, (caixa[1] + caixa[3]) // 2), GLIFOS[nome], font=f["icone"],
                   fill=ACC if e.hover == nome else DIM, anchor="mm")
            regioes.append(Regiao(nome, caixa, DICAS[nome]))
        titulo = f"Diário · {DIAS_SEMANA[e.dia.weekday()]} {e.dia:%d/%m}"
        d.text((10, 6 + hh // 2), titulo, font=f["titulo"], fill=FG, anchor="lm")
        if not e.eh_hoje:  # "Hoje" ao lado da data
            x0 = 10 + int(f["titulo"].getlength(titulo)) + 4
            caixa = (x0, 6, x0 + int(f["negrito"].getlength("Hoje")) + 12, 6 + hh)
            d.text(((caixa[0] + caixa[2]) // 2, (caixa[1] + caixa[3]) // 2), "Hoje", font=f["negrito"],
                   fill=FG if e.hover == "hoje" else ACC, anchor="mm")
            regioes.append(Regiao("hoje", caixa, DICAS["hoje"]))
        regioes.append(Regiao("arrastar", (0, 0, W, 8 + hh), "", ""))
        # lista
        if not e.topicos:
            d.text((12, y_lista + rh // 2), "Nada registrado neste dia.", font=f["texto"], fill=DIM, anchor="lm")
        for i, (texto, tipo) in enumerate(e.topicos):
            cor = {"manual": OK, "aviso": DIM, "resumir": DIM}.get(tipo, FG)
            y = y_lista + i * rh
            linha = _cabe("•  " + texto, f["texto"], W - 36)
            d.text((12, y + rh // 2), linha, font=f["texto"], fill=cor, anchor="lm")
            if tipo == "resumir":
                rotulo = base.RESUMINDO if e.resumindo else base.ATUALIZAR if e.refazer else base.RESUMIR
                sobre = e.hover == "resumir" and not e.resumindo
                x0 = 12 + int(f["texto"].getlength(linha)) + 10
                x1 = x0 + int(f["texto"].getlength(rotulo))
                d.text((x0, y + rh // 2), rotulo, font=f["texto"], fill=FG if sobre else ACC, anchor="lm")
                if sobre:
                    d.line([(x0, y + rh // 2 + 8), (x1, y + rh // 2 + 8)], fill=FG)
                if not e.resumindo:
                    regioes.append(Regiao("resumir", (x0 - 3, y, x1 + 3, y + rh), DICAS["refazer" if e.refazer else "resumir"]))
            regioes.append(Regiao(f"linha:{i}", (0, y, W, y + rh), "", ""))
        if e.extra:
            d.text((12, y_extra + 7), f"… e mais {e.extra}", font=f["peq"], fill=DIM, anchor="lm")
        # campo de lançamento (o Entry do Tk fica por cima) e status
        d.rectangle([12, y_campo, W - 12, y_campo + h_campo], fill=CAMPO)
        for i, linha in enumerate(linhas_status):
            d.text((12, y_status + i * round(14 * s)), linha, font=f["peq"], fill=cor_status)
        return Quadro(im, regioes, (12, y_campo, W - 12, y_campo + h_campo),
                      dict(bg=CAMPO, fg=FG, cursor=FG, fonte=("Segoe UI", 10)), False, BG)

    # --- calendário ---
    def calendario(self, e):
        s, f = base.ESCALA, self._fontes()
        cel_w, cel_h = round(38 * s), round(28 * s)
        W = 7 * cel_w + 20
        m = e.cal_mes
        semanas = calendar.Calendar(firstweekday=6).monthdayscalendar(m.year, m.month)
        y0 = round(40 * s) + round(20 * s)
        yb = y0 + len(semanas) * cel_h + 4  # linha do botão da semana
        H = yb + round(26 * s) + 6
        im = Image.new("RGBA", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W - 1, H - 1], outline=BORDA)
        regioes = []
        for nome, glifo, caixa, dica in (("cal_ant", "◀", (6, 8, 6 + round(32 * s), 8 + round(28 * s)), "Mês anterior"),
                                         ("cal_prox", "▶", (W - 6 - round(32 * s), 8, W - 6, 8 + round(28 * s)),
                                          "Próximo mês")):
            d.text(((caixa[0] + caixa[2]) // 2, (caixa[1] + caixa[3]) // 2), glifo, font=f["icone"],
                   fill=ACC if e.hover == nome else DIM, anchor="mm")
            regioes.append(Regiao(nome, caixa, dica))
        d.text((W // 2, 8 + round(14 * s)), f"{MESES[m.month - 1]} {m.year}", font=f["titulo"], fill=FG, anchor="mm")
        for col, nome in enumerate("DSTQQSS"):
            d.text((10 + col * cel_w + cel_w // 2, round(40 * s) + 8), nome, font=f["peq"], fill=DIM, anchor="mm")
        hoje = date.today()
        for lin, semana in enumerate(semanas):
            for col, dia in enumerate(semana):
                if not dia:
                    continue
                dt = date(m.year, m.month, dia)
                futuro, escolhido = dt > hoje, dt == e.dia
                x, y = 10 + col * cel_w, y0 + lin * cel_h
                caixa = (x, y, x + cel_w, y + cel_h)
                if escolhido:
                    d.rectangle([x + 2, y + 2, x + cel_w - 3, y + cel_h - 3], fill=ACC)
                cor = BG if escolhido else DIM if futuro else OK if dt.isoformat() in e.cal_dias else FG
                d.text(((caixa[0] + caixa[2]) // 2, (caixa[1] + caixa[3]) // 2), str(dia),
                       font=f["negrito"] if dt == hoje else f["texto"], fill=cor, anchor="mm")
                if not futuro:
                    regioes.append(Regiao(f"dia:{dt.isoformat()}", caixa, ""))
        d.line([(10, yb), (W - 10, yb)], fill=BORDA)
        caixa = (10, yb + 2, W - 10, yb + 2 + round(24 * s))
        sobre = e.hover == "cal_semana" and not e.resumindo
        d.text((W // 2, (caixa[1] + caixa[3]) // 2), "Resumindo…" if e.resumindo else base.SEMANA_ROTULO,
               font=f["negrito"] if sobre else f["texto"], fill=FG if sobre else ACC, anchor="mm")
        if not e.resumindo:
            regioes.append(Regiao("cal_semana", caixa, base.dica_semana(e.dia)))
        return Quadro(im, regioes, None, {}, False, BG)

    # --- configurações ---
    def configuracoes(self, e, miniaturas):
        """Duas colunas: os temas à esquerda e, se o widget mandou itens em `e.barra`, a barra de tarefas à direita."""
        s, f = base.ESCALA, self._fontes()
        W1, W2, tw_ = 380, 340, 104
        W = W1 + (W2 if e.barra else 0)
        linha_h = round(76 * s)
        y0 = round(74 * s)
        grupos = base.grupos_de_temas(e)
        cab, folga = round(20 * s), round(8 * s)  # do título de grupo até a primeira linha; da última linha até o próximo título
        x2, w2, y2 = W1 + 12, W2 - 24, round(44 * s)  # coluna da direita: início, largura e topo
        h1 = y0 + sum(len(ts) * linha_h for _, ts in grupos) + (cab + folga) * (len(grupos) - 1)
        h2 = y2 + sum(self._altura_item(i, w2) for i in e.barra)
        H = max(h1, h2) + 12
        im = Image.new("RGBA", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W - 1, H - 1], outline=BORDA)
        regioes = [Regiao("arrastar", (0, 0, W - 40, round(38 * s)), "", "")]
        d.text((12, round(19 * s)), "Configurações", font=f["titulo"], fill=FG, anchor="lm")
        caixa = (W - 40, 4, W - 6, round(38 * s))
        d.text(((caixa[0] + caixa[2]) // 2, (caixa[1] + caixa[3]) // 2), "✕", font=f["icone"],
               fill=ACC if e.hover == "cfg_fechar" else DIM, anchor="mm")
        regioes.append(Regiao("cfg_fechar", caixa, "Fechar"))
        yg = round(54 * s)
        for titulo, temas in grupos:
            d.text((12, yg), titulo, font=f["negrito"], fill=ACC, anchor="lm")
            d.line([(12 + round(f["negrito"].getlength(titulo)) + 8, yg), (W1 - 12, yg)], fill=BORDA)
            y0 = yg + cab
            for i, (tid, nome, desc) in enumerate(temas):
                y = y0 + i * linha_h
                ativo = tid == e.tema_atual
                if e.hover == f"tema:{tid}" or ativo:
                    d.rectangle([8, y, W1 - 8, y + linha_h - 6], fill=CAMPO, outline=ACC if ativo else BORDA)
                cx, cy = 26, y + (linha_h - 6) // 2
                d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], outline=ACC if ativo else DIM, width=2)
                if ativo:
                    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=ACC)
                mini = miniaturas.get(tid)
                if mini:
                    alt = round(mini.height * tw_ / mini.width)
                    im.paste(mini.resize((tw_, alt), Image.LANCZOS), (46, y + (linha_h - 6 - alt) // 2))
                d.text((46 + tw_ + 12, y + 8), nome + ("  ·  em uso" if ativo else ""), font=f["negrito"],
                       fill=OK if ativo else FG)
                for k, linha in enumerate(_quebra(desc, f["peq"], W1 - 46 - tw_ - 12 - 18, 3)):
                    d.text((46 + tw_ + 12, y + 30 + k * round(14 * s)), linha, font=f["peq"], fill=DIM)
                regioes.append(Regiao(f"tema:{tid}", (8, y, W1 - 8, y + linha_h - 6), ""))
            yg = y0 + len(temas) * linha_h + folga
        if e.barra:
            d.line([(W1, y2), (W1, H - 12)], fill=BORDA)  # divisória entre as colunas
            y = y2
            for item in e.barra:
                self._item_barra(d, f, e.hover, item, x2, y, w2, regioes)
                y += self._altura_item(item, w2)
        return Quadro(im, regioes, None, {}, False, BG)

    # --- coluna da barra de tarefas (formato dos itens no comentário ITENS_BARRA de base.py) ---
    _ALTURAS = {"titulo": 22, "sub": 24, "espaco": 8, "estado": 24, "marca": 24, "opcao": 24, "cores": 28, "alfas": 28,
                "passo": 28}

    def _altura_item(self, item, w):
        tipo, _, rotulo = item[:3]
        s = base.ESCALA
        if tipo == "texto":
            return len(_quebra(rotulo, self._fontes()["peq"], w, 4)) * round(15 * s) + 4
        return round(self._ALTURAS[tipo] * s)

    def _item_barra(self, d, f, hover, item, x, y, w, regioes):
        tipo, nome, rotulo, valor, ativo = item
        s = base.ESCALA
        h = self._altura_item(item, w)
        meio = y + h // 2
        cor = FG if ativo else DIM
        linha = (x - 6, y + 1, x + w + 6, y + h - 2)  # caixa de uma linha clicável (estado, marca, opção)
        if tipo == "titulo":
            d.text((x, meio), rotulo, font=f["negrito"], fill=ACC, anchor="lm")
            d.line([(x + round(f["negrito"].getlength(rotulo)) + 8, meio), (x + w, meio)], fill=BORDA)
        elif tipo == "sub":
            d.text((x, y + h - round(4 * s)), _cabe(rotulo, f["negrito"], w), font=f["negrito"], fill=FG if ativo else DIM,
                   anchor="ls")
        elif tipo == "texto":
            for k, t in enumerate(_quebra(rotulo, f["peq"], w, 4)):
                d.text((x, y + k * round(15 * s)), t, font=f["peq"], fill=DIM)
        elif tipo == "estado":  # `ativo` aqui é "é o estado escolhido"
            if ativo or hover == nome:
                d.rectangle(linha, fill=CAMPO, outline=ACC if ativo else BORDA)
            d.text((x + w, meio), valor, font=f["peq"], fill=DIM, anchor="rm")
            d.text((x, meio), _cabe(rotulo, f["texto"], w - round(f["peq"].getlength(valor)) - 10), font=f["texto"],
                   fill=OK if ativo else FG, anchor="lm")
            regioes.append(Regiao(nome, linha, ""))
        elif tipo in ("marca", "opcao"):
            if ativo and hover == nome:
                d.rectangle(linha, fill=CAMPO, outline=BORDA)
            borda = OK if valor and ativo else DIM
            cx = x + 7
            if tipo == "marca":
                d.rectangle([cx - 6, meio - 6, cx + 6, meio + 6], outline=borda, width=2)
                if valor:
                    d.line([(cx - 3, meio), (cx - 1, meio + 3), (cx + 3, meio - 3)], fill=borda, width=2)
            else:
                d.ellipse([cx - 6, meio - 6, cx + 6, meio + 6], outline=borda, width=2)
                if valor:
                    d.ellipse([cx - 2, meio - 2, cx + 2, meio + 2], fill=borda)
            d.text((x + 22, meio), _cabe(rotulo, f["texto"], w - 22), font=f["texto"], fill=OK if valor and ativo else cor,
                   anchor="lm")
            if ativo:
                regioes.append(Regiao(nome, linha, ""))
        elif tipo == "cores":
            lado = round(20 * s)
            for i, (reg, rgb, escolhida) in enumerate(valor):
                cx = x + i * (lado + 8)
                q = (cx, meio - lado // 2, cx + lado, meio + lado // 2)
                if ativo:
                    d.rectangle(q, fill="#" + rgb, outline=OK if escolhida else ACC if hover == reg else BORDA,
                                width=3 if escolhida else 1)
                    regioes.append(Regiao(reg, q, ""))
                else:
                    d.rectangle(q, outline=BORDA)
        elif tipo == "alfas":
            cx = x
            for reg, rot, escolhido in valor:
                bw = round(f["peq"].getlength(rot)) + 16
                q = (cx, meio - round(10 * s), cx + bw, meio + round(10 * s))
                if ativo:
                    d.rectangle(q, fill=CAMPO, outline=OK if escolhido else ACC if hover == reg else BORDA,
                                width=2 if escolhido else 1)
                    regioes.append(Regiao(reg, q, ""))
                d.text(((q[0] + q[2]) // 2, meio), rot, font=f["peq"], fill=OK if escolhido and ativo else cor, anchor="mm")
                cx += bw + 6
        elif tipo == "passo":
            d.text((x, meio), rotulo, font=f["texto"], fill=cor, anchor="lm")
            lado = round(20 * s)
            for sinal, bx in (("−", x + w - 3 * lado - 8), ("+", x + w - lado)):
                q = (bx, meio - lado // 2, bx + lado, meio + lado // 2)
                reg = f"{nome}:{'-' if sinal == '−' else '+'}"
                if ativo:
                    d.rectangle(q, fill=CAMPO, outline=ACC if hover == reg else BORDA)
                    regioes.append(Regiao(reg, q, ""))
                d.text(((q[0] + q[2]) // 2, meio), sinal, font=f["texto"], fill=cor, anchor="mm")
            d.text((x + w - lado * 2 + lado // 2 - 4, meio), valor, font=f["texto"], fill=cor, anchor="mm")
