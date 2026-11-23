"""Tema Jogo retrô: tela de plataforma 8/16 bits no topo (HUD, céu, colinas, chão de tijolos que rola, herói correndo,
bloco "?") e menu de RPG embaixo. O mundo muda de manhã, tarde e noite: céu, colinas, castelo, estrelas, passarinhos.

O mundo é animado (cache por período e quadro); o HUD e o menu só são redesenhados quando o estado muda.
"""
import math
import random

from PIL import Image

from ..pixel import BRANCO, PRETO, TRANSPARENTE, Tela, contorno, cortar, glifo, hx, icone, largura
from .base import BOTOES, DIAS_SEMANA, DICAS, Estado, Quadro, Regiao
from .pixeltema import TemaPixel, botao_resumir

N = 32  # o chão rola 4 px por quadro e se repete a cada 128 px, então 32 quadros emendam sem pulo
W = 304
HUD_H, CHAO_Y, CENA_H = 13, 58, 74

P = {
    "manha": dict(ceu=[hx("#3c78f0"), hx("#5c94fc"), hx("#84b0fc"), hx("#acd0fc")],
                  nuvem=hx("#fcfcfc"), nuvem2=hx("#a4e4fc"), nuvem_ol=hx("#5c94fc"),
                  colina=hx("#38b838"), colina2=hx("#1f8f1f"), colina_ol=hx("#0a4a0a"),
                  arbusto=hx("#38c038"), arbusto2=hx("#1f8f1f"), tijolo=hx("#c8601c"), tijolo2=hx("#f09050"),
                  argamassa=hx("#5a2000"), relva=hx("#38c038"), janela=hx("#1c3cb8"), janela2=hx("#3c64e8"),
                  borda=hx("#fcfcfc"), texto=BRANCO, ok=hx("#58f858"), dim=hx("#a8b0d8"), seta=hx("#fcd820")),
    "tarde": dict(ceu=[hx("#2a1a5a"), hx("#7a2a7a"), hx("#c8486a"), hx("#f07840"), hx("#ffb458")],
                  nuvem=hx("#ffc8a0"), nuvem2=hx("#e08068"), nuvem_ol=hx("#8a3a5a"),
                  colina=hx("#7a3a7a"), colina2=hx("#5a2a68"), colina_ol=hx("#2a1040"),
                  arbusto=hx("#5a3070"), arbusto2=hx("#3e2058"), tijolo=hx("#a8442c"), tijolo2=hx("#d8784c"),
                  argamassa=hx("#3a1418"), relva=hx("#8aa028"), janela=hx("#481c78"), janela2=hx("#7038a8"),
                  borda=hx("#ffe8c8"), texto=hx("#fff4e0"), ok=hx("#a8f060"), dim=hx("#c8a8d0"), seta=hx("#ffd048")),
    "noite": dict(ceu=[hx("#04061a"), hx("#080c2c"), hx("#0c1440"), hx("#141e58")],
                  nuvem=hx("#34448c"), nuvem2=hx("#222e68"), nuvem_ol=hx("#0c1440"),
                  colina=hx("#124050"), colina2=hx("#0a2c3a"), colina_ol=hx("#020a10"),
                  arbusto=hx("#124a3a"), arbusto2=hx("#0a3228"), tijolo=hx("#4a3a7a"), tijolo2=hx("#6a58a0"),
                  argamassa=hx("#14102a"), relva=hx("#1c6a4a"), janela=hx("#0a1038"), janela2=hx("#182070"),
                  borda=hx("#9cc0ff"), texto=hx("#e4ecff"), ok=hx("#58e8a0"), dim=hx("#6f7ab0"), seta=hx("#ffd060")),
}
HEROI = {"c": hx("#3c78f0"), "s": hx("#f8c898"), "k": hx("#201020"), "o": hx("#f07020"), "g": hx("#38b838"),
         "b": hx("#7a4a20")}
HEROI_A = ["...cccc...", "..cccccc..", ".cccccccc.", ".ssssssss.", ".ssksskss.", ".ssssssss.", "..oooooo..", ".gggggggg.",
           "sgggggggs.", "sgggggggs.", ".gggggggg.", "..gg..gg..", "..bb..bb..", ".bbb..bbb."]
HEROI_B = HEROI_A[:11] + ["...gggg...", "...bbbb...", "..bbbbbb.."]
SETA = ["#....", "##...", "###..", "##...", "#...."]


# ------------------------------------------------------------------ sprites do mundo
def ceu_bandas(T, y0, y1, cores):
    n = len(cores)
    h = (y1 - y0) / n
    for i, c in enumerate(cores):
        T.rect(0, int(y0 + i * h), W, int(h) + 2, c)
    for i in range(1, n):  # transição tracejada entre as faixas
        yb = int(y0 + i * h)
        for x in range(W):
            for dy in (-2, -1, 0, 1):
                if (x + dy) % (2 + abs(dy)) == 0:
                    T.px(x, yb + dy, cores[i] if dy < 0 else cores[i - 1])


def nuvem(c, w, h):
    T = Tela(w, h)
    T.ell(0, h * .35, w * .38, h - 1, c["nuvem"])
    T.ell(w * .22, 0, w * .66, h * .85, c["nuvem"])
    T.ell(w * .55, h * .3, w - 1, h - 1, c["nuvem"])
    T.rect(w // 8, h * .55, w * 3 // 4, h * .45, c["nuvem"])
    T.rect(w // 8, h - 3, w * 3 // 4, 2, c["nuvem2"])
    return contorno(T.im, c["nuvem_ol"])


def colina(c, w, h):
    T = Tela(w, h)
    T.ell(0, 0, w - 1, h * 2 - 1, c["colina"])
    for k in range(1, 5):  # listras de sombra tracejadas
        for x in range(w):
            if (x + k) % 3 == 0:
                T.px(x, int(h * (.25 + k * .17)), c["colina2"])
    T.rect(int(w * .42), int(h * .3), 2, 4, c["colina_ol"])  # olhinhos de colina
    T.rect(int(w * .55), int(h * .3), 2, 4, c["colina_ol"])
    im = contorno(T.im, c["colina_ol"])
    return im.crop((0, 0, im.width, h + 1))


def arbusto(c, w=24, h=10):
    T = Tela(w, h)
    for x0, x1, y0 in ((0, w * .45, h * .35), (w * .25, w * .75, 0), (w * .55, w - 1, h * .35)):
        T.ell(x0, y0, x1, h * 2 - 1, c["arbusto"])
    for x in range(2, w - 2, 4):
        T.px(x, h * .6, c["arbusto2"])
    return contorno(T.im, c["colina_ol"]).crop((0, 0, w + 2, h + 1))


def castelo(t):
    T = Tela(34, 34)
    pedra, escura = hx("#1a2250"), hx("#10163a")
    T.rect(4, 12, 26, 22, pedra)
    for x in range(4, 30, 6):
        T.rect(x, 8, 4, 5, pedra)
    T.rect(0, 4, 10, 30, escura)
    T.rect(24, 4, 10, 30, escura)
    for x in (0, 4, 8, 24, 28, 32):
        T.rect(x, 0, 3, 5, escura)
    T.rect(13, 22, 8, 12, hx("#080a1c"))
    T.ell(13, 18, 20, 26, hx("#080a1c"))
    luz = hx("#ffd060") if (t // 5) % 7 else hx("#a07a30")  # janelas que tremeluzem
    for x, y in ((3, 12), (27, 12), (15, 14)):
        T.rect(x, y, 3, 4, luz)
    return T.im


def bloco(bate):
    T = Tela(14, 14)
    T.rect(0, 0, 14, 14, hx("#5a2000"))
    T.rect(1, 1, 12, 12, hx("#f8b800"))
    T.rect(1, 1, 12, 1, hx("#fcd870"))
    T.rect(1, 1, 1, 12, hx("#fcd870"))
    T.rect(1, 12, 12, 1, hx("#b87800"))
    T.rect(12, 1, 1, 12, hx("#b87800"))
    for x, y in ((2, 2), (11, 2), (2, 11), (11, 11)):
        T.px(x, y, hx("#5a2000"))
    cor = hx("#c88c00") if bate else hx("#5a2000")
    for j, linha in enumerate(glifo("?")[0]):
        for i, v in enumerate(linha):
            if v == "#":
                T.px(4 + i, 3 + j, cor)
    return T.im


def moeda(quadro):
    larg = (6, 4, 2, 4)[quadro % 4]
    T = Tela(8, 12)
    x0 = (8 - larg) // 2
    T.ell(x0, 1, x0 + larg - 1, 10, hx("#fcc800"))
    if larg > 2:
        T.rect(x0 + 1, 3, 1, 5, hx("#fff090"))
    return contorno(T.im, hx("#7a4a00"))


def tijolos(T, c, scroll, y0, linhas=2):
    for j in range(linhas * 8):
        row = j % 8
        for x in range(W):
            if row % 4 == 0:
                cor = c["argamassa"]
            else:
                off = 0 if (row // 4) % 2 == 0 else 4
                cor = c["argamassa"] if (x + scroll + off) % 8 == 7 else (c["tijolo2"] if row % 4 == 1 else c["tijolo"])
            T.px(x, y0 + j, cor)
    T.rect(0, y0, W, 2, c["relva"])
    T.rect(0, y0 + 2, W, 1, c["argamassa"])


def passarinho(T, x, y, f, cor):
    pts = ((0, 1), (1, 0), (2, 1), (3, 0), (4, 1)) if f % 2 else ((0, 0), (1, 1), (2, 1), (3, 1), (4, 0))
    for dx, dy in pts:
        T.px(x + dx, y + dy, cor)


# ------------------------------------------------------------------ o tema
class Retro(TemaPixel):
    id = "retro"
    nome = "Jogo retrô"
    descricao = "Tela de plataforma 8/16 bits com menu de RPG. O mundo muda de manhã, tarde e noite."
    cores_balao = ("#000000", "#fcfcfc", "#fcfcfc")
    CAIXA_ALTA = True
    animacao_ms = 140

    def __init__(self):
        self._cache = {}
        self._ui = (None, None)

    def paleta(self, per):
        c = P[per]
        return dict(texto=c["texto"], dim=c["dim"], ok=c["ok"], acc=c["seta"], sel_fundo=c["seta"], sel_texto=PRETO,
                    linha=c["janela2"], hover=c["seta"])

    def moldura_dialogo(self, T, w, h, titulo, per, hover_fechar):
        c = P[per]
        T.rect(0, 0, w, h, PRETO)
        T.rect(1, 1, w - 2, h - 2, c["borda"])
        T.rect(3, 3, w - 6, h - 6, c["janela"])
        for yy in range(self.TITULO_H, h - 3, 2):
            for xx in range(3, w - 3):
                if (xx + yy) % 4 == 0 and yy < h // 2:
                    T.px(xx, yy, c["janela2"])
        T.rect(3, 3, w - 6, self.TITULO_H - 4, PRETO)
        T.cantos(0, 0, w, h)
        T.texto(8, 5, titulo, c["texto"])
        T.put(icone("fechar", c["seta"] if hover_fechar else c["texto"]), w - 12, 5)
        return (w - 16, 1, w - 2, self.TITULO_H)

    # --- geometria: o menu cresce com o número de linhas ---
    @staticmethod
    def _linhas(e):
        return max(len(e.topicos) + (1 if e.extra else 0), 3)

    def _geo(self, e):
        n = self._linhas(e)
        wh = 11 * n + 9
        wy = CENA_H + 2
        ey = wy + wh + 4
        sty = ey + 16 + 4
        return dict(n=n, wy=wy, wh=wh, ey=ey, sty=sty, H=sty + 7 + 6)

    # --- o mundo (animado) ---
    def _mundo(self, per, t):
        k = (per, t % N)
        if k not in self._cache:
            if len(self._cache) > 200:
                self._cache.clear()
            self._cache[k] = self._desenha_mundo(per, t % N)
        return self._cache[k]

    def _desenha_mundo(self, per, t):
        c = P[per]
        T = Tela(W, CENA_H)
        noite, tarde = per == "noite", per == "tarde"
        ceu_bandas(T, HUD_H, CHAO_Y + 2, c["ceu"])
        rnd = random.Random(4)
        if noite:
            for k in range(42):
                sx, sy = rnd.randrange(2, W - 2), rnd.randrange(HUD_H + 2, 44)
                if (t // 2 + k) % 5:
                    T.px(sx, sy, hx("#fff1c9"))
                    if k % 4 == 0 and (t // 4 + k) % 3:
                        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            T.px(sx + dx, sy + dy, hx("#8aa0d8"))
            lua = Tela(14, 14)
            lua.ell(0, 0, 13, 13, hx("#fcf0c0"))
            px = lua.im.load()
            for yy in range(14):
                for xx in range(14):
                    if (xx - 8) ** 2 + (yy - 5) ** 2 < 49:
                        px[xx, yy] = TRANSPARENTE
            T.put(contorno(lua.im, hx("#c8b070")), 240, 20)
        elif tarde:
            T.ell(192, 36, 218, 62, hx("#ffe070"))
            T.d.ellipse([192, 36, 218, 62], outline=hx("#e05030"))
        else:
            T.ell(240, 17, 254, 31, hx("#fcd820"))
            T.d.ellipse([240, 17, 254, 31], outline=hx("#e08000"))
            for k in range(8):
                a = k * math.pi / 4 + (math.pi / 8 if (t // 4) % 2 else 0)
                T.rect(int(247 + math.cos(a) * 12), int(24 + math.sin(a) * 12), 2, 2, hx("#fcd820"))
        for k, (x0, y0, w_, h_) in enumerate(((16, 22, 30, 13), (112, 18, 24, 11), (234, 32, 28, 12), (176, 12, 26, 11))):
            if (noite and k == 1) or (tarde and k in (2, 3)) or (not noite and not tarde and k == 2):
                continue
            T.put(nuvem(c, w_, h_), x0 + int(3 * math.sin(2 * math.pi * t / N + k)), y0)
        T.put(colina(c, 70, 24), 160, CHAO_Y - 24)
        T.put(colina(c, 52, 17), 2, CHAO_Y - 17)
        T.put(colina(c, 40, 12), 256, CHAO_Y - 12)
        T.put(colina(c, 44, 14), 86, CHAO_Y - 14)
        if noite:
            T.put(castelo(t), 116, CHAO_Y - 34)
        if tarde:
            for k in range(3):
                passarinho(T, 48 + k * 19 + int(2 * math.sin(2 * math.pi * t / N + k)), 24 + k * 4 - (k % 2) * 6,
                           (t // 2 + k) % 2, c["colina_ol"])
        sc = (4 * t) % 128
        tijolos(T, c, sc, CHAO_Y, 2)
        for k in range(2):
            for m in range(3):
                T.put(arbusto(c), (30 + k * 64 - sc) % 128 - 30 + 128 * m, CHAO_Y - 10)
        bate = (t % 16) < 3
        for m in range(3):  # a faixa se repete a cada 128 px
            bx = (96 - sc) % 128 - 20 + 128 * m
            T.put(bloco(bate), bx, 28 - (3 if bate else 0))
            if bate:
                T.put(moeda(t), bx + 3, 20 - (t % 16) * 2)
        T.spr(64, CHAO_Y - 14 - ((t // 2) % 2), HEROI_A if (t // 2) % 2 == 0 else HEROI_B, HEROI)
        return T.im

    # --- HUD e menu ---
    def _interface(self, e, g, piscar):
        c = P[e.periodo]
        T = Tela(W, g["H"])
        regs = []
        T.rect(0, 0, W, HUD_H, PRETO)
        titulo = f"DIÁRIO · {DIAS_SEMANA[e.dia.weekday()].upper()} {e.dia:%d/%m}"
        T.texto(6, 3, titulo, BRANCO)
        if not e.eh_hoje:  # etiqueta "HOJE" ao lado da data
            caixa = (6 + largura(titulo) + 6, 1, 6 + largura(titulo) + 35, 11)
            T.rect(*caixa[:2], 29, 10, PRETO)
            T.rect(caixa[0] + 1, caixa[1] + 1, 27, 8, c["seta"] if e.hover == "hoje" else c["borda"])
            T.rect(caixa[0] + 2, caixa[1] + 2, 25, 6, PRETO)
            T.texto(caixa[0] + 4, caixa[1] + 2, "HOJE", c["seta"] if e.hover == "hoje" else BRANCO)
            regs.append(Regiao("hoje", caixa, DICAS["hoje"]))
        x = W - 4
        for nome in reversed(BOTOES):
            x -= 8
            ic = icone(nome, c["seta"] if e.hover == nome else BRANCO)
            T.put(ic, x + (8 - ic.width) // 2, 6 - ic.height // 2 + 1)
            regs.append(Regiao(nome, (x, 0, x + 8, HUD_H), DICAS[nome]))
        regs.append(Regiao("arrastar", (0, 0, W, HUD_H), "", ""))
        # janela do menu
        wx, wy, ww, wh = 6, g["wy"], W - 12, g["wh"]
        T.rect(wx, wy, ww, wh, PRETO)
        T.rect(wx + 1, wy + 1, ww - 2, wh - 2, c["borda"])
        T.rect(wx + 3, wy + 3, ww - 6, wh - 6, c["janela"])
        for yy in range(wy + 3, wy + 3 + (wh - 6) // 2, 2):  # degradê tracejado
            for xx in range(wx + 3, wx + ww - 3):
                if (xx + yy) % 4 == 0:
                    T.px(xx, yy, c["janela2"])
        T.cantos(wx, wy, ww, wh)
        linhas = list(e.topicos) or [("Nada registrado neste dia.", "aviso")]
        for i, (txt, tipo) in enumerate(linhas):
            y = wy + 7 + i * 11
            cor = {"manual": c["ok"], "aviso": c["dim"], "resumir": c["dim"]}.get(tipo, c["texto"])
            if e.hover == f"linha:{i}" and piscar:
                T.spr(wx + 6, y, SETA, {"#": c["seta"]})
            else:
                T.rect(wx + 7, y + 2, 2, 2, cor)
            curto = cortar(txt, ww - 20)
            T.texto(wx + 14, y, curto, cor)
            if tipo == "resumir":
                r = botao_resumir(T, wx + 14 + largura(curto) + 6, y, e, c["seta"], c["texto"])
                if r:
                    regs.append(r)
            regs.append(Regiao(f"linha:{i}", (wx, y - 2, wx + ww, y + 9), txt if curto != txt else "", ""))
        if e.extra:
            T.texto(wx + 14, wy + 7 + len(linhas) * 11, f"… E MAIS {e.extra}", c["dim"])
        # campo de lançamento: prompt ">" e o Entry do Tk por cima do campo preto
        T.rect(6, g["ey"], ww, 16, PRETO)
        T.rect(7, g["ey"] + 1, ww - 2, 14, c["borda"])
        T.rect(8, g["ey"] + 2, ww - 4, 12, PRETO)
        T.texto(12, g["ey"] + 5, ">", c["ok"])
        campo = (22, g["ey"] + 3, W - 10, g["ey"] + 13)
        # status e contador de moedas (uma por tópico do dia)
        msg = (e.status if e.status and e.status_tipo != "dica" else "ENTER LANÇA").upper()
        cor = {"ok": c["ok"], "info": c["seta"], "erro": hx("#fc5050")}.get(e.status_tipo, c["dim"])
        T.texto(8, g["sty"], cortar(msg, W - 52), cor)
        n = min(len(e.topicos), 99)
        T.put(moeda(0), W - 30, g["sty"] - 3)
        T.texto(W - 20, g["sty"], f"x{n:02d}", c["texto"])
        return T.im, regs, campo

    def quadro(self, e: Estado, t: int) -> Quadro:
        g = self._geo(e)
        piscar = (t // 4) % 2 == 0
        chave = (e.dia, tuple(e.topicos), e.extra, e.status, e.status_tipo, e.hover, e.periodo, e.eh_hoje, piscar)
        if self._ui[0] != chave:
            self._ui = (chave, self._interface(e, g, piscar))
        ui, regs, campo = self._ui[1]
        img = Image.new("RGBA", (W, g["H"]), PRETO)
        img.alpha_composite(self._mundo(e.periodo, t), (0, 0))
        img.alpha_composite(ui)
        c = P[e.periodo]
        Z = self.Z
        imagem = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
        regioes = [Regiao(r.nome, tuple(v * Z for v in r.caixa), r.dica, r.cursor) for r in regs]
        cor = "#%02x%02x%02x" % c["texto"][:3]
        return Quadro(imagem, regioes, tuple(v * Z for v in campo),
                      dict(bg="#000000", fg=cor, cursor=cor, fonte=("Consolas", 10)), False, "#000000")
