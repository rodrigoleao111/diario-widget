"""Tema Ilha flutuante: placa de madeira com papel creme sobre uma ilha de grama; o céu muda de manhã, tarde e noite.

A janela tem formato livre (o que é transparente deixa passar o clique): sol, nuvens, estrelas e flores flutuam na
área de trabalho. O quadro é montado em três camadas em pixels de arte, ampliadas 2x no final:
fundo (céu e ilha, animado) + interface (madeira, papel, texto) + frente (capim, flores, passarinho, heras).
"""
import math
import random

from PIL import Image

from ..pixel import (TRANSPARENTE, Tela, contorno, cortar, esfera, hx, icone, largura, mix, rampa)
from .base import BOTOES, DIAS_SEMANA, DICAS, Estado, Quadro, Regiao
from .pixeltema import TemaPixel, botao_resumir

N = 16  # quadros do ciclo de animação
W = 384  # largura da cena em pixels de arte; a moldura (300) fica no meio
FX, FW, FY = 42, 300, 32
IX = 27  # margem da ilha; a moldura fica 15 px para dentro dela
DICA_CURTA = "1h30 reunião @CS · Enter lança"

_MAD = dict(ol=hx("#4a2c17"), w1=hx("#d9a066"), w2=hx("#ecc58c"), w3=hx("#b07a46"), wtxt=hx("#4a2c17"))
PER = {
    "manha": dict(_MAD, cloud=hx("#ffffff"), cloud2=hx("#cfe3f7"), g1=hx("#5cb82f"), g2=hx("#3f8f2a"), g3=hx("#8be04e"),
                  d1=hx("#8a5a33"), d2=hx("#6b4326"), d3=hx("#a8703f"), sun=hx("#ffd93b"), sun2=hx("#f0a21a"),
                  paper=hx("#fbf1dc"), paper2=hx("#ead9b6"), ink=hx("#28364f"), acc=hx("#2f6db5"), dim=hx("#7a8499"),
                  ok=hx("#2a8a55"), slate=hx("#33415a"), stxt=hx("#e4ecfa"), flower=hx("#ffffff"), fcen=hx("#ffd93b"),
                  leaf=hx("#3f9a2a"), leaf2=hx("#2a7a22")),
    "tarde": dict(_MAD, cloud=hx("#ffd8b0"), cloud2=hx("#f0a67a"), g1=hx("#7fae2a"), g2=hx("#52802a"), g3=hx("#b4cf45"),
                  d1=hx("#8a5230"), d2=hx("#663a22"), d3=hx("#b07040"), sun=hx("#ff9a2e"), sun2=hx("#e0601a"),
                  paper=hx("#fbe3bf"), paper2=hx("#e8c898"), ink=hx("#3b2a3f"), acc=hx("#b4572a"), dim=hx("#8a7480"),
                  ok=hx("#4a7a26"), slate=hx("#4a3550"), stxt=hx("#ffe9d2"), flower=hx("#ffe9b0"), fcen=hx("#e0601a"),
                  leaf=hx("#6a9a28"), leaf2=hx("#4a7820")),
    "noite": dict(_MAD, ol=hx("#2e1c10"), w1=hx("#a86f46"), w2=hx("#c08a5c"), w3=hx("#7c4d2e"), wtxt=hx("#2e1c10"),
                  cloud=hx("#4a5a8c"), cloud2=hx("#2f3a66"), g1=hx("#2f7a52"), g2=hx("#1f5a42"), g3=hx("#4fa06a"),
                  d1=hx("#4a3a4a"), d2=hx("#33283a"), d3=hx("#5e4a5a"), sun=hx("#fdf0c8"), sun2=hx("#cdb98a"),
                  paper=hx("#e8dcc2"), paper2=hx("#cfc2a6"), ink=hx("#2a3148"), acc=hx("#2f5fa8"), dim=hx("#6f7690"),
                  ok=hx("#2a8a55"), slate=hx("#1f2940"), stxt=hx("#c9d6ef"), flower=hx("#b9c8ff"), fcen=hx("#fdf0c8"),
                  leaf=hx("#2f8a58"), leaf2=hx("#1f6a48")),
}
STATUS_COR = {"dica": None, "ok": hx("#1f5a2a"), "info": hx("#1f4a8a"), "erro": hx("#8a1f1f")}


# ------------------------------------------------------------------ sprites
def passaro(modo="acordado", bobe=0):
    t = Tela(22, 16)
    azul, azul2, laranja, bico = hx("#4aa3ff"), hx("#2d6fd6"), hx("#ffb33b"), hx("#ff9a2e")
    t.ell(3, 5 + bobe, 17, 13, azul)
    t.ell(1, 1 + bobe, 9, 9, azul)
    t.poly([(16, 7), (21, 5), (21, 11)], azul2)
    t.ell(3, 8 + bobe, 10, 13, laranja)
    t.ell(9, 6 + bobe, 16, 11, azul2)
    if modo == "acordado":
        t.poly([(0, 4 + bobe), (-1, 5 + bobe), (0, 6 + bobe)], bico)
        t.rect(0, 5 + bobe, 2, 1, bico)
        t.px(3, 3 + bobe, hx("#1a1a2a"))
        t.px(3, 2 + bobe, hx("#ffffff"))
    else:
        t.rect(0, 5 + bobe, 2, 1, bico)
        t.rect(2, 4 + bobe, 3, 1, hx("#1a1a2a"))
    pe = hx("#c06a22")
    t.px(8, 14, pe)
    t.px(11, 14, pe)
    return contorno(t.im, hx("#1d3a6a"))


def sol(pulso, c):
    t = Tela(31, 31)
    cx = cy = 15
    r = 6
    for k in range(8):
        a = k * math.pi / 4
        for d in range(r + 3, r + 6 + (pulso if k % 2 else 0)):
            t.rect(int(cx + math.cos(a) * d), int(cy + math.sin(a) * d), 1 + (d < r + 5), 1 + (d < r + 5), c["sun"])
    t.ell(cx - r, cy - r, cx + r, cy + r, c["sun2"])
    t.ell(cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1, c["sun"])
    t.px(cx - 2, cy - 3, hx("#ffffff"))
    t.px(cx - 3, cy - 2, hx("#ffffff"))
    return t.im


def lua(c):
    t = Tela(20, 20)
    t.ell(2, 2, 17, 17, c["sun"])
    px = t.im.load()
    for y in range(20):
        for x in range(20):
            if (x - 12) ** 2 + (y - 7) ** 2 < 60:
                px[x, y] = TRANSPARENTE
    t.px(5, 12, c["sun2"])
    t.px(6, 13, c["sun2"])
    return t.im


def nuvem(w, h, c):
    sombra, luz = Tela(w, h), Tela(w, h)
    for (x0, y0, x1, y1) in [(0, h // 3, w // 2, h - 1), (w // 4, 0, w * 3 // 4, h * 2 // 3), (w // 3, h // 3, w - 1, h - 1)]:
        sombra.ell(x0, y0, x1, y1, c["cloud2"])
        luz.ell(x0, y0 - 1, x1, y1 - 2, c["cloud"])
    sombra.im.alpha_composite(luz.im)
    return sombra.im


def flor(bal, c, fechada=False):
    t = Tela(9, 15)
    t.rect(4, 6, 1, 9, c["leaf2"])
    t.rect(2, 11, 2, 1, c["leaf"])
    t.rect(5, 9, 2, 1, c["leaf"])
    bx = 4 + bal
    if fechada:
        t.rect(bx - 1, 3, 3, 3, c["flower"])
        t.px(bx, 2, c["flower"])
    else:
        for dx, dy in ((0, -2), (-2, 0), (2, 0), (0, 2)):
            t.rect(bx + dx - (dx == 0), 4 + dy, 2, 2, c["flower"])
        t.rect(bx - 1, 3, 2, 2, c["fcen"])
    return t.im


def ilha(w, c):
    r = random.Random(7)
    t = Tela(w, 36)
    pts = [(0, 10), (w - 1, 10), (w - 8, 22), (w - 22, 31), (w // 2 + 8, 34), (w // 2 - 10, 31), (22, 33), (8, 22)]
    t.poly(pts, c["d1"])
    for _ in range(40):
        x, y = r.randrange(8, w - 8), r.randrange(13, 29)
        if t.im.getpixel((x, y))[3]:
            t.rect(x, y, r.choice((2, 3)), 1, c["d3"] if r.random() < .5 else c["d2"])
    t.rect(0, 0, w, 11, c["g1"])
    t.rect(0, 0, w, 2, c["g3"])
    t.rect(0, 8, w, 3, c["g2"])
    for x in range(1, w - 1, 2):
        if r.random() < .55:
            t.rect(x, 2 + r.randrange(0, 5), 1, 1, c["g3"])
    for x in range(1, w - 1, 3):  # beiral de grama pingando sobre a terra
        t.rect(x, 11, 2, r.choice((1, 2, 3, 4, 5)), c["g2"])
        if r.random() < .3:
            t.rect(x, 11, 1, 2, c["g1"])
    return contorno(t.im, c["ol"])


def tufos(T, c, x0, x1, y):
    """Capim na frente: duas fileiras (a de trás mais escura) e moitas de folhas largas."""
    r = random.Random(3)
    for x in range(x0, x1, 2):
        for k in range(r.choice((1, 2, 2, 3, 3, 4))):
            T.px(x, y - 2 - k, c["g2"])
    for x in range(x0 + 1, x1, 2):
        n = r.choice((2, 3, 3, 4, 4, 5))
        for k in range(n):
            T.px(x, y - k, c["g3"] if k >= n - 2 else c["g1"])
    for x in range(x0 + 3, x1 - 3, 11):
        for dx, dy in ((-2, 1), (-1, 2), (0, 4), (1, 2), (2, 1)):
            T.px(x + dx, y - dy, c["g3"])
            T.px(x + dx, y - dy + 1, c["g1"])


def heras(c):
    r = random.Random(5)
    t = Tela(60, 22)
    for i in range(34):
        x, y = 4 + i * 1.6, 3 + math.sin(i * .7) * 2
        for _ in range(2):
            t.rect(int(x + r.randrange(-2, 3)), int(y + r.randrange(0, 4)), 2, 2, c["leaf"] if r.random() < .6 else c["leaf2"])
    for i in range(7):
        x = 36 + i * 3
        for k in range(r.randrange(2, 6)):
            t.rect(x, 8 + k, 1, 1, c["leaf2"])
            if k % 3 == 2:
                t.rect(x + 1, 8 + k, 2, 2, c["leaf"])
    return t.im


def brilho(T, x, y, forte=True):
    b = hx("#ffffff")
    for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
        T.px(x + dx, y + dy, b)
    if forte:
        T.px(x - 2, y, hx("#bfe0ff"))
        T.px(x + 2, y, hx("#bfe0ff"))


def moldura(T, x, y, w, h, p):
    T.rect(x, y, w, h, p["ol"])
    T.rect(x + 1, y + 1, w - 2, h - 2, p["w1"])
    T.rect(x + 1, y + 1, w - 2, 2, p["w2"])
    T.rect(x + 1, y + h - 3, w - 2, 2, p["w3"])
    T.cantos(x, y, w, h)


# ------------------------------------------------------------------ o tema
class Ilha(TemaPixel):
    id = "ilha"
    nome = "Ilha flutuante"
    descricao = "Placa de madeira sobre uma ilha de grama. O céu muda de manhã, tarde e noite."
    cores_balao = ("#fbf1dc", "#28364f", "#4a2c17")
    PAD = 8

    def __init__(self):
        self._cache = {}
        self._ui = (None, None)

    def paleta(self, per):
        p = PER[per]
        return dict(texto=p["ink"], dim=p["dim"], ok=p["ok"], acc=p["acc"], sel_fundo=p["acc"],
                    sel_texto=hx("#fff8ea"), linha=p["paper2"], hover=p["acc"])

    def moldura_dialogo(self, T, w, h, titulo, per, hover_fechar):
        p = PER[per]
        moldura(T, 0, 0, w, h, p)
        T.texto(8, 4, titulo, p["wtxt"])
        T.put(icone("fechar", hx("#fff0c8") if hover_fechar else p["wtxt"]), w - 12, 5)
        T.rect(4, self.TITULO_H, w - 8, h - self.TITULO_H - 4, p["ol"])
        T.rect(5, self.TITULO_H + 1, w - 10, h - self.TITULO_H - 6, p["paper"])
        T.cantos(4, self.TITULO_H, w - 8, h - self.TITULO_H - 4)
        return (w - 16, 1, w - 2, self.TITULO_H)

    # --- geometria (pixels de arte), função do número de linhas da lista ---
    @staticmethod
    def _linhas(e):
        return max(len(e.topicos) + (1 if e.extra else 0), 3)

    def _geo(self, e):
        n = self._linhas(e)
        ph = 11 * n + 6
        py = FY + 21
        ey = py + ph + 3
        sty = ey + 15 + 3
        fh = sty + 7 + 4 - FY
        return dict(n=n, ph=ph, py=py, ey=ey, sty=sty, fh=fh, H=FY + fh + 32)

    # --- camadas animadas (cache por período, quadro e altura) ---
    def _camada(self, nome, per, t, g, fn):
        k = (nome, per, t % N, g["H"])
        if k not in self._cache:
            if len(self._cache) > 400:
                self._cache.clear()
            self._cache[k] = fn(per, t % N, g)
        return self._cache[k]

    def _fundo(self, per, t, g):
        p = PER[per]
        sk = Tela(W, g["H"])
        noite, tarde = per == "noite", per == "tarde"
        if noite:
            r = random.Random(2)
            for k in range(29):
                sx, sy = r.randrange(2, W - 2), r.randrange(2, 60)
                if (t + k) % 5:
                    sk.px(sx, sy, hx("#fff1c9") if (t + k) % 3 else hx("#8aa0d8"))
            sk.put(lua(p), W - 32, 6)
            for k in range(6):  # vagalumes
                fx = 22 + k * 64 + math.sin((t + k * 3) / 2.5) * 7
                fy = g["py"] + 60 + math.cos((t * 1.2 + k * 2) / 2.2) * 8 - (k % 2) * 16
                if (t + k) % 4:
                    sk.px(fx, fy, hx("#ffe88a"))
                    sk.px(fx + 1, fy, hx("#8a7a3a"))
        else:
            sk.put(sol(t % 8 // 4, p), *((W - 32, 0) if not tarde else (2, 10)))
        dx = (t // 5) % 3
        sk.put(nuvem(34, 18, p), 4 + dx, 12 if not tarde else 50)
        sk.put(nuvem(30, 15, p), 112 + dx, 6)
        sk.put(nuvem(22, 12, p), dx, 76)
        sk.put(nuvem(26, 14, p), W - 22 - dx, 86)
        brilho(sk, 8, 100, t % 6 < 3)
        if not noite:
            brilho(sk, W - 7, 62, t % 6 >= 3)
        sk.put(ilha(W - 2 * IX, p), IX, FY + g["fh"] - 6)
        return sk.im

    def _frente(self, per, t, g):
        p = PER[per]
        T = Tela(W, g["H"])
        noite = per == "noite"
        base = FY + g["fh"]
        tufos(T, p, IX - 3, W - IX + 3, base + 4)
        for k, fxp in enumerate((FX - 9, FX + FW + 1)):  # só nas bordas da ilha, para não cobrir o texto da moldura
            T.put(flor(((t + k * 2) // 4) % 3 - 1, p, fechada=noite), fxp, base - 18)
        T.put(heras(p), FX + FW - 56, 20)
        b = passaro("dormindo" if noite else "acordado", 0 if noite else (1 if t % 8 in (0, 1) else 0))
        bx = FX + FW - 36
        T.put(b, bx, FY - b.size[1] + 2)
        if noite:
            T.texto(bx + 18, 12, "z", mix(p["stxt"], p["slate"], .2))
        elif t % 8 in (2, 3):
            T.px(bx - 4, 20, hx("#ffffff"))
            T.px(bx - 6, 18, hx("#ffffff"))
        return T.im

    # --- interface (madeira, papel, texto): só muda quando o estado muda ---
    def _interface(self, e, g):
        p = PER[e.periodo]
        T = Tela(W, g["H"])
        moldura(T, FX, FY, FW, g["fh"], p)
        regs = []
        # cabeçalho: título e botões (da direita para a esquerda)
        titulo = f"Diário · {DIAS_SEMANA[e.dia.weekday()]} {e.dia:%d/%m}"
        T.texto(FX + 10, 38, titulo, p["wtxt"])
        if not e.eh_hoje:  # etiqueta de madeira "Hoje" ao lado da data, para voltar ao dia atual
            caixa = (FX + 10 + largura(titulo) + 6, 36, FX + 10 + largura(titulo) + 30, 47)
            T.rect(caixa[0], caixa[1], 24, 11, p["ol"])
            T.rect(caixa[0] + 1, caixa[1] + 1, 22, 9, p["w2"] if e.hover == "hoje" else p["w1"])
            T.texto(caixa[0] + 3, caixa[1] + 2, "Hoje", p["wtxt"])
            regs.append(Regiao("hoje", caixa, DICAS["hoje"]))
        x = FX + FW - 6
        for nome in reversed(BOTOES):
            x -= 9
            ic = icone(nome, hx("#fff0c8") if e.hover == nome else p["wtxt"])
            T.put(ic, x + (9 - ic.width) // 2, 41 - ic.height // 2 + 0)
            regs.append(Regiao(nome, (x, FY + 1, x + 9, FY + 19), DICAS[nome]))
        regs.append(Regiao("arrastar", (FX, FY, FX + FW, FY + 20), "", ""))
        # painel de papel com a lista
        px_, pw = FX + 6, FW - 12
        T.rect(px_, g["py"], pw, g["ph"], p["ol"])
        T.rect(px_ + 1, g["py"] + 1, pw - 2, g["ph"] - 2, p["paper"])
        T.rect(px_ + 1, g["py"] + g["ph"] - 3, pw - 2, 2, p["paper2"])
        T.cantos(px_, g["py"], pw, g["ph"])
        linhas = list(e.topicos)
        if not linhas:
            linhas = [("Nada registrado neste dia.", "aviso")]
        for i, (txt, tipo) in enumerate(linhas):
            y = g["py"] + 5 + i * 11
            cor = {"manual": p["ok"], "aviso": p["dim"], "resumir": p["dim"]}.get(tipo, p["ink"])
            if e.hover == f"linha:{i}":
                T.rect(px_ + 3, y - 2, pw - 6, 11, p["paper2"])
            T.rect(px_ + 7, y + 2, 3, 3, cor if tipo else p["acc"])
            curto = cortar(txt, pw - 22)
            T.texto(px_ + 14, y, curto, cor)
            if tipo == "resumir":
                r = botao_resumir(T, px_ + 14 + largura(curto) + 6, y, e, p["acc"], p["ink"])
                if r:
                    regs.append(r)
            regs.append(Regiao(f"linha:{i}", (px_, y - 2, px_ + pw, y + 9), txt if curto != txt else "", ""))
        if e.extra:
            T.texto(px_ + 14, g["py"] + 5 + len(linhas) * 11, f"… e mais {e.extra}", p["dim"])
        # barra do campo de lançamento (o Entry do Tk fica por cima do campo) e status
        T.rect(px_, g["ey"], pw, 15, p["ol"])
        T.rect(px_ + 1, g["ey"] + 1, pw - 2, 13, p["slate"])
        campo = (px_ + 4, g["ey"] + 2, px_ + pw - 4, g["ey"] + 13)
        T.rect(campo[0], campo[1], campo[2] - campo[0], campo[3] - campo[1], mix(p["slate"], hx("#000000"), .35))
        msg = e.status if e.status and e.status_tipo != "dica" else DICA_CURTA
        cor = STATUS_COR.get(e.status_tipo) or mix(p["wtxt"], p["w1"], .3)
        T.texto(px_ + 2, g["sty"], cortar(msg, pw - 4), cor)
        return T.im, regs, campo

    def quadro(self, e: Estado, t: int) -> Quadro:
        g = self._geo(e)
        chave = (e.dia, tuple(e.topicos), e.extra, e.status, e.status_tipo, e.hover, e.periodo, e.eh_hoje)
        if self._ui[0] != chave:
            self._ui = (chave, self._interface(e, g))
        ui, regs, campo = self._ui[1]
        img = Image.new("RGBA", (W, g["H"]), TRANSPARENTE)
        img.alpha_composite(self._camada("fundo", e.periodo, t, g, self._fundo))
        img.alpha_composite(ui)
        img.alpha_composite(self._camada("frente", e.periodo, t, g, self._frente))
        p = PER[e.periodo]
        q = self._finaliza_cena(img, regs, campo, p)
        return q

    def _finaliza_cena(self, img, regs, campo, p):
        Z = self.Z
        imagem = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
        regioes = [Regiao(r.nome, tuple(v * Z for v in r.caixa), r.dica, r.cursor) for r in regs]
        entrada = tuple(v * Z for v in campo)
        estilo = dict(bg="#%02x%02x%02x" % mix(p["slate"], hx("#000000"), .35)[:3], fg="#%02x%02x%02x" % p["stxt"][:3],
                      cursor="#%02x%02x%02x" % p["stxt"][:3], fonte=("Consolas", 10))
        return Quadro(imagem, regioes, entrada, estilo, True)
