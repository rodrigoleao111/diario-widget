"""Base dos temas em pixel art: desenham numa grade pequena, ampliam Z vezes e montam o calendário e a tela de
configurações a partir de uma moldura de diálogo que cada tema define."""
import calendar
from datetime import date

from PIL import Image

from ..pixel import Tela, TRANSPARENTE, cortar, icone, largura
from .base import (ATUALIZAR, DICAS, MESES, RESUMINDO, RESUMIR, SEMANA, Quadro, Regiao, Tema, dica_semana, grupos_de_temas)


def botao_resumir(T, x, y, e, cor, cor_hover):
    """Desenha "[resumir]" (ou "[atualizar]", se o dia já tem resumo velho) em (x, y) e devolve a Regiao do clique
    (None enquanto o resumo é gerado).

    A região precisa entrar em `regs` ANTES da região da linha: o widget usa a primeira que casa com o mouse."""
    rotulo = RESUMINDO if e.resumindo else ATUALIZAR if e.refazer else RESUMIR
    sobre = e.hover == "resumir" and not e.resumindo
    cor = cor_hover if sobre else cor
    T.texto(x, y, rotulo, cor)
    if sobre:
        T.rect(x, y + 8, largura(rotulo), 1, cor)
    if e.resumindo:
        return None
    return Regiao("resumir", (x - 2, y - 2, x + largura(rotulo) + 2, y + 9), DICAS["refazer" if e.refazer else "resumir"])


def quebra_px(texto, px, max_linhas):
    """Quebra por palavras em linhas de até px pixels de arte; a última leva reticências se sobrar texto."""
    linhas, atual = [], ""
    for palavra in texto.split():
        tentativa = (atual + " " + palavra).strip()
        if largura(tentativa) <= px or not atual:
            atual = tentativa
        else:
            linhas.append(atual)
            atual = palavra
    linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        linhas[-1] = cortar(linhas[-1] + " …", px)
    return linhas


class TemaPixel(Tema):
    Z = 2  # cada pixel de arte vira Z x Z pixels da tela
    animacao_ms = 220
    CAIXA_ALTA = False
    TITULO_H = 15  # altura da barra de título dos diálogos, em pixels de arte
    PAD = 8
    CHAVE = (1, 2, 3)

    # --- o que cada tema define ---
    def paleta(self, periodo):
        """Cores dos diálogos: texto, dim, ok, acc, sel_fundo, sel_texto, linha, hover."""
        raise NotImplementedError

    def moldura_dialogo(self, T, w, h, titulo, periodo, hover_fechar):
        """Desenha a moldura e a barra de título de um diálogo w x h; devolve a caixa do botão de fechar."""
        raise NotImplementedError

    # --- ferramentas ---
    def _t(self, s):
        return s.upper() if self.CAIXA_ALTA else s

    def _finaliza(self, T, regioes, entrada=None, estilo=None, minis=None):
        """Amplia a camada, converte as caixas para pixels da tela e cola as miniaturas (essas, já em pixels da tela)."""
        Z = self.Z
        img = T.im.resize((T.w * Z, T.h * Z), Image.NEAREST)
        for (mini, caixa) in (minis or []):
            x0, y0, x1, y1 = [v * Z for v in caixa]
            img.paste(mini.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
        regioes = [Regiao(r.nome, tuple(v * Z for v in r.caixa), r.dica, r.cursor) for r in regioes]
        ent = tuple(v * Z for v in entrada) if entrada else None
        return Quadro(img, regioes, ent, estilo or {}, True)

    # --- calendário ---
    def calendario(self, e):
        pal = self.paleta(e.periodo)
        m = e.cal_mes
        semanas = calendar.Calendar(firstweekday=6).monthdayscalendar(m.year, m.month)
        cel_w, cel_h, pad = 19, 11, self.PAD
        W = 7 * cel_w + 2 * pad
        topo = self.TITULO_H + 6
        H = topo + 13 + 10 + len(semanas) * cel_h + 14 + pad  # 14: linha do botão da semana
        T = Tela(W, H)
        fechar = self.moldura_dialogo(T, W, H, self._t("Calendário"), e.periodo, e.hover == "cal_fechar")
        regs = [Regiao("cal_fechar", fechar, "Fechar")]
        for nome, ic, x, dica in (("cal_ant", "anterior", pad, "Mês anterior"),
                                  ("cal_prox", "proximo", W - pad - 16, "Próximo mês")):
            cor = pal["hover"] if e.hover == nome else pal["dim"]
            T.put(icone(ic, cor), x + 5, topo + 3)
            regs.append(Regiao(nome, (x, topo, x + 16, topo + 11), dica))
        titulo = self._t(f"{MESES[m.month - 1]} {m.year}")
        T.texto((W - largura(titulo)) // 2, topo + 2, titulo, pal["texto"])
        for col, letra in enumerate("DSTQQSS"):
            T.texto(pad + col * cel_w + (cel_w - 5) // 2, topo + 14, letra, pal["dim"])
        T.rect(pad, topo + 22, W - 2 * pad, 1, pal["linha"])
        hoje, y0 = date.today(), topo + 25
        for lin, semana in enumerate(semanas):
            for col, dia in enumerate(semana):
                if not dia:
                    continue
                dt = date(m.year, m.month, dia)
                futuro, escolhido = dt > hoje, dt == e.dia
                x, y = pad + col * cel_w, y0 + lin * cel_h
                if escolhido:
                    T.rect(x + 1, y, cel_w - 2, cel_h - 1, pal["sel_fundo"])
                elif not futuro and e.hover == f"dia:{dt.isoformat()}":
                    T.rect(x + 1, y, cel_w - 2, cel_h - 1, pal["linha"])
                cor = pal["sel_texto"] if escolhido else pal["dim"] if futuro else \
                    pal["ok"] if dt.isoformat() in e.cal_dias else pal["texto"]
                tx = x + (cel_w - largura(str(dia))) // 2
                T.texto(tx, y + 2, str(dia), cor)
                if dt == hoje:
                    T.rect(tx, y + 9, largura(str(dia)), 1, cor)
                if not futuro:
                    regs.append(Regiao(f"dia:{dt.isoformat()}", (x, y, x + cel_w, y + cel_h)))
        yb = y0 + len(semanas) * cel_h + 2
        T.rect(pad, yb, W - 2 * pad, 1, pal["linha"])
        rotulo = self._t("[resumindo…]" if e.resumindo else SEMANA)
        sobre = e.hover == "cal_semana" and not e.resumindo
        xb = (W - largura(rotulo)) // 2
        T.texto(xb, yb + 5, rotulo, pal["hover"] if sobre else pal["acc"])
        if sobre:
            T.rect(xb, yb + 13, largura(rotulo), 1, pal["hover"])
        if not e.resumindo:
            regs.append(Regiao("cal_semana", (pad, yb + 2, W - pad, yb + 14), dica_semana(e.dia)))
        return self._finaliza(T, regs)

    # --- configurações ---
    def configuracoes(self, e, miniaturas):
        """Duas colunas: os temas à esquerda e, se o widget mandou itens em `e.barra`, a barra de tarefas à direita."""
        pal = self.paleta(e.periodo)
        W1, W2, pad, linha_h = 190, 206, self.PAD, 46
        W = W1 + (W2 if e.barra else 0)
        topo = self.TITULO_H + 6
        grupos = grupos_de_temas(e)
        x2, w2 = W1 + 4, W2 - 4 - pad  # onde começa e quanto mede o conteúdo da coluna da direita
        h1 = topo + sum(12 + len(ts) * linha_h for _, ts in grupos) + 8 * (len(grupos) - 1)
        h2 = topo + sum(self._altura_item(i, w2) for i in e.barra)
        H = max(h1, h2) + 14 + pad
        T = Tela(W, H)
        fechar = self.moldura_dialogo(T, W, H, self._t("Configurações"), e.periodo, e.hover == "cfg_fechar")
        regs = [Regiao("arrastar", (0, 0, W - 20, self.TITULO_H), "", ""), Regiao("cfg_fechar", fechar, "Fechar")]
        minis, yg = [], topo
        for titulo, temas in grupos:
            T.texto(pad, yg, self._t(titulo), pal["acc"])
            T.rect(pad + largura(self._t(titulo)) + 4, yg + 3, W1 - 2 * pad - largura(self._t(titulo)) - 4, 1, pal["linha"])
            y0 = yg + 12
            for i, (tid, nome, desc) in enumerate(temas):
                y = y0 + i * linha_h
                ativo = tid == e.tema_atual
                caixa = (pad - 3, y - 2, W1 - pad + 3, y + linha_h - 4)
                if ativo or e.hover == f"tema:{tid}":
                    T.rect(caixa[0], caixa[1], caixa[2] - caixa[0], caixa[3] - caixa[1], pal["linha"])
                    if ativo:
                        T.d.rectangle([caixa[0], caixa[1], caixa[2] - 1, caixa[3] - 1], outline=pal["ok"])
                # botão de rádio 7x7
                T.ell(pad, y + 16, pad + 6, y + 22, pal["dim"] if not ativo else pal["ok"])
                T.ell(pad + 1, y + 17, pad + 5, y + 21, pal["linha"] if not ativo else pal["ok"])
                if ativo:
                    T.rect(pad + 2, y + 18, 3, 3, pal["texto"])
                mx0, my0 = pad + 12, y
                T.rect(mx0 - 1, my0 - 1, 58, 42, pal["linha"])
                if tid in miniaturas:
                    minis.append((miniaturas[tid], (mx0, my0, mx0 + 56, my0 + 40)))
                tx = mx0 + 62
                T.texto(tx, y + 1, cortar(self._t(nome), W1 - tx - pad - 12), pal["ok"] if ativo else pal["texto"])
                if ativo:  # marca de "em uso"
                    T.spr(W1 - pad - 8, y + 1, ["....#", "...#.", "#.#..", ".#..."], {"#": pal["ok"]})
                for k, linha in enumerate(quebra_px(desc, W1 - tx - pad - 2, 3)):
                    T.texto(tx, y + 13 + k * 9, linha, pal["dim"])
                regs.append(Regiao(f"tema:{tid}", caixa))
            yg = y0 + len(temas) * linha_h + 8
        if e.barra:
            T.rect(W1 - 3, topo, 1, H - topo - pad - 14, pal["linha"])  # divisória entre as colunas
            y = topo
            for item in e.barra:
                self._item_barra(T, pal, e.hover, item, x2, y, w2, regs)
                y += self._altura_item(item, w2)
        T.texto(pad, H - pad - 7, cortar(self._t("Muda na hora e fica salvo"), W - 2 * pad), pal["dim"])
        return self._finaliza(T, regs, minis=minis)

    # --- coluna da barra de tarefas (formato dos itens no comentário ITENS_BARRA de base.py) ---
    _ALTURAS = {"titulo": 12, "sub": 11, "espaco": 4, "estado": 10, "marca": 10, "opcao": 10, "cores": 12, "alfas": 12,
                "passo": 12}

    def _altura_item(self, item, w):
        tipo, _, rotulo = item[:3]
        return len(quebra_px(rotulo, w, 4)) * 9 + 2 if tipo == "texto" else self._ALTURAS[tipo]

    def _item_barra(self, T, pal, hover, item, x, y, w, regs):
        tipo, nome, rotulo, valor, ativo = item
        rotulo = self._t(rotulo)
        cor = pal["texto"] if ativo else pal["dim"]
        linha = (x - 3, y - 1, x + w + 3, y + 9)  # caixa de uma linha clicável (estado, marca, opção)
        if tipo == "titulo":
            T.texto(x, y, rotulo, pal["acc"])
            T.rect(x + largura(rotulo) + 4, y + 3, w - largura(rotulo) - 4, 1, pal["linha"])
        elif tipo == "sub":
            T.texto(x, y + 2, cortar(rotulo, w), pal["acc"] if ativo else pal["dim"])
        elif tipo == "texto":
            for k, t in enumerate(quebra_px(rotulo, w, 4)):
                T.texto(x, y + k * 9, t, pal["dim"])
        elif tipo == "estado":  # `ativo` aqui é "é o estado escolhido"
            if ativo or hover == nome:
                T.rect(linha[0], linha[1], linha[2] - linha[0], linha[3] - linha[1], pal["linha"])
                if ativo:
                    T.d.rectangle([linha[0], linha[1], linha[2] - 1, linha[3] - 1], outline=pal["ok"])
            v = self._t(valor)
            T.texto(x + w - largura(v), y + 1, v, pal["dim"])
            T.texto(x, y + 1, cortar(rotulo, w - largura(v) - 6), pal["ok"] if ativo else pal["texto"])
            regs.append(Regiao(nome, linha))
        elif tipo in ("marca", "opcao"):
            if ativo and hover == nome:
                T.rect(linha[0], linha[1], linha[2] - linha[0], linha[3] - linha[1], pal["linha"])
            borda = pal["ok"] if valor and ativo else pal["dim"]
            if tipo == "marca":
                T.rect(x, y + 1, 7, 7, borda)
                T.rect(x + 1, y + 2, 5, 5, pal["linha"])
                if valor:
                    T.spr(x + 1, y + 2, [".....", "....#", "#..#.", ".##..", "....."], {"#": borda})
            else:
                T.ell(x, y + 1, x + 6, y + 7, borda)
                T.ell(x + 1, y + 2, x + 5, y + 6, borda if valor else pal["linha"])
                if valor:
                    T.rect(x + 2, y + 3, 3, 3, pal["texto"])
            T.texto(x + 11, y + 1, cortar(rotulo, w - 11), pal["ok"] if valor and ativo else cor)
            if ativo:
                regs.append(Regiao(nome, linha))
        elif tipo == "cores":
            for i, (reg, rgb, escolhida) in enumerate(valor):
                cx = x + i * 13
                if ativo:
                    fora = pal["ok"] if escolhida else pal["sel_fundo"] if hover == reg else pal["dim"]
                    T.rect(cx - 1, y, 12, 11, fora)
                    T.rect(cx, y + 1, 10, 9, tuple(int(rgb[k:k + 2], 16) for k in (0, 2, 4)) + (255,))
                    regs.append(Regiao(reg, (cx - 1, y, cx + 11, y + 11)))
                else:
                    T.d.rectangle([cx, y + 1, cx + 9, y + 9], outline=pal["dim"])
        elif tipo == "alfas":
            cx = x
            for reg, rot, escolhido in valor:
                bw = largura(rot) + 6
                if ativo:
                    fundo = pal["sel_fundo"] if escolhido or hover == reg else pal["linha"]
                    T.rect(cx, y, bw, 10, fundo)
                    T.cantos(cx, y, bw, 10)
                    regs.append(Regiao(reg, (cx, y, cx + bw, y + 10)))
                T.texto(cx + 3, y + 2, rot, pal["sel_texto"] if ativo and (escolhido or hover == reg) else cor)
                cx += bw + 3
        elif tipo == "passo":
            T.texto(x, y + 2, cortar(rotulo, w - 50), cor)
            for sinal, bx in (("-", x + w - 41), ("+", x + w - 9)):
                reg = f"{nome}:{sinal}"
                if ativo:
                    T.rect(bx, y, 9, 10, pal["sel_fundo"] if hover == reg else pal["linha"])
                    T.cantos(bx, y, 9, 10)
                    regs.append(Regiao(reg, (bx, y, bx + 9, y + 10)))
                T.texto(bx + 2, y + 2, sinal, pal["sel_texto"] if ativo and hover == reg else cor)
            T.texto(x + w - 20 - largura(valor) // 2, y + 2, valor, cor)
