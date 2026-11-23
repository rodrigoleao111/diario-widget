"""Tema Castelo medieval: muralha de pedra com duas torres, pergaminho na lista e um céu que muda de manhã, tarde e noite.

Como a Ilha, a janela tem formato livre (o que é transparente deixa passar o clique) e os elementos flutuam soltos na
área de trabalho: sol, nuvens, ilhotas com torrezinha, um dragão que cruza o céu, bandeiras ao vento, tochas, um
cavaleiro de guarda e uma árvore. O quadro é montado em camadas de pixels de arte, ampliadas 2x no final:
fundo (céu, ilhotas e a ilha de grama, animado) + dragão (por quadro) + castelo (pedra, estático) + interface
(faixas, pergaminho, texto) + frente (bandeiras, chamas, capim, cavaleiro, árvore).
"""
import math
import random

from PIL import Image

from ..pixel import (TRANSPARENTE, Tela, contorno, cortar, hx, icone, largura, mix)
from .base import BOTOES, DIAS_SEMANA, DICAS, Estado, Quadro, Regiao
from .ilha import brilho, flor, ilha, lua, nuvem, sol, tufos
from .pixeltema import TemaPixel, botao_resumir

N = 16  # quadros do ciclo de animação (tudo que se repete divide 16)
W = 416  # largura da cena em pixels de arte; a muralha (300) fica no meio
FX, FW, FY = 58, 300, 56
TW = 28  # largura das torres; cada uma invade 4 px da muralha
TX = (FX - TW + 4, FX + FW - 4)
IX = 12  # margem da ilha
ALTURA_TELHADO = 27
DICA_CURTA = "1h30 reunião @CS · Enter lança"
EFEITOS = {"porta": 16, "dragao": 12, "cavaleiro": 12, "tocha0": 12, "tocha1": 12, "sol": 12}  # duração em quadros

_BASE = dict(ol=hx("#232733"), wd1=hx("#8a5a33"), wd2=hx("#6b4326"), wd3=hx("#a8703f"), ouro=hx("#f2c14e"),
             ouro2=hx("#b8862a"), brasa=hx("#ff6a1a"), chama=hx("#ffb02e"), fogo=hx("#fff2a0"), manto=hx("#c8412f"))
PER = {
    "manha": dict(_BASE, s1=hx("#7a8493"), s2=hx("#5b6573"), s3=hx("#98a3b2"), r1=hx("#c8412f"), r2=hx("#8f2c24"),
                  r3=hx("#e5705a"), ban1=hx("#b8322a"), ban2=hx("#2f56a8"), fresta=hx("#1b1e28"), luz=hx("#3b4254"),
                  cloud=hx("#ffffff"), cloud2=hx("#cfe3f7"), g1=hx("#5cb82f"), g2=hx("#3f8f2a"), g3=hx("#8be04e"),
                  d1=hx("#6b7380"), d2=hx("#4c5360"), d3=hx("#8a93a0"), sun=hx("#ffd93b"), sun2=hx("#f0a21a"),
                  paper=hx("#f6e9c8"), paper2=hx("#e2cf9f"), ink=hx("#2a2f45"), acc=hx("#8f2c24"), dim=hx("#857b6a"),
                  ok=hx("#2a7a45"), slate=hx("#2a2f3d"), stxt=hx("#f7f1e1"), flower=hx("#ffffff"), fcen=hx("#ffd93b"),
                  leaf=hx("#3f9a2a"), leaf2=hx("#2a7a22"), dr1=hx("#4fa83a"), dr2=hx("#e8d36a"), dr3=hx("#c8412f"),
                  olho=hx("#fff2a0"), pele=hx("#f2c9a0"), branco=hx("#f4f4f8"), inter=hx("#20232f")),
    "tarde": dict(_BASE, s1=hx("#8a7a84"), s2=hx("#695a68"), s3=hx("#ac9ca2"), r1=hx("#c24a3a"), r2=hx("#86302c"),
                  r3=hx("#e68062"), ban1=hx("#a8302e"), ban2=hx("#4a4a98"), fresta=hx("#2a1f2c"), luz=hx("#4a3a48"),
                  cloud=hx("#ffd8b0"), cloud2=hx("#f0a67a"), g1=hx("#7fae2a"), g2=hx("#52802a"), g3=hx("#b4cf45"),
                  d1=hx("#76687a"), d2=hx("#574a5e"), d3=hx("#94869a"), sun=hx("#ff9a2e"), sun2=hx("#e0601a"),
                  paper=hx("#f8e2bb"), paper2=hx("#e8c898"), ink=hx("#3b2a3f"), acc=hx("#86302c"), dim=hx("#8a7480"),
                  ok=hx("#4a7a26"), slate=hx("#3a2f45"), stxt=hx("#ffe9d2"), flower=hx("#ffe9b0"), fcen=hx("#e0601a"),
                  leaf=hx("#6a9a28"), leaf2=hx("#4a7820"), dr1=hx("#7a9a30"), dr2=hx("#e8b86a"), dr3=hx("#c24a3a"),
                  olho=hx("#fff2a0"), pele=hx("#f0b88c"), branco=hx("#f8e6d8"), inter=hx("#2a1f2c")),
    "noite": dict(_BASE, ol=hx("#151824"), s1=hx("#586382"), s2=hx("#414a66"), s3=hx("#717c9e"), r1=hx("#7a2e3a"),
                  r2=hx("#52202c"), r3=hx("#9a4654"), ban1=hx("#7a2430"), ban2=hx("#26408a"), fresta=hx("#ffd36a"),
                  luz=hx("#ffd36a"), cloud=hx("#4a5a8c"), cloud2=hx("#2f3a66"), g1=hx("#2f7a52"), g2=hx("#1f5a42"),
                  g3=hx("#4fa06a"), d1=hx("#4a4a62"), d2=hx("#33334a"), d3=hx("#5e5e7a"), sun=hx("#fdf0c8"),
                  sun2=hx("#cdb98a"), paper=hx("#e6dcc4"), paper2=hx("#cfc2a6"), ink=hx("#2a3148"), acc=hx("#7a2e3a"),
                  dim=hx("#6f7690"), ok=hx("#2a8a55"), slate=hx("#1c2236"), stxt=hx("#dbe4f7"), flower=hx("#b9c8ff"),
                  fcen=hx("#fdf0c8"), leaf=hx("#2f8a58"), leaf2=hx("#1f6a48"), dr1=hx("#2f6a4a"), dr2=hx("#8a8a5a"),
                  dr3=hx("#7a2e3a"), olho=hx("#ffe14a"), wd1=hx("#6a4428"), wd2=hx("#4a2e1a"), wd3=hx("#865a34"),
                  manto=hx("#b8323f"), pele=hx("#e0b088"), branco=hx("#d4d8ee"), inter=hx("#b87a30")),
}
STATUS_COR = {"dica": None, "ok": {"manha": hx("#a8f0b8"), "tarde": hx("#b8f0a0"), "noite": hx("#8ee8a8")},
              "info": {"manha": hx("#a8cdfa"), "tarde": hx("#b0c8f8"), "noite": hx("#8ab4f0")},
              "erro": {"manha": hx("#ffa8a0"), "tarde": hx("#ffa8a0"), "noite": hx("#ff8f8f")}}
DOURADO = hx("#ffd75a")


# ------------------------------------------------------------------ pedra, telhado, estandarte
def faixa(p):
    return mix(p["s1"], p["ol"], .4)


def tijolos(T, x, y, w, h, c):
    """Parede de pedra: juntas de 6 em 6 px, fiadas alternadas e um brilho no canto de cada tijolo."""
    T.rect(x, y, w, h, c["s1"])
    for j, yy in enumerate(range(y, y + h, 6)):
        T.rect(x, yy, w, 1, c["s2"])
        off = 5 if j % 2 else 0
        for xx in range(x + off - 10, x + w, 10):
            if xx >= x:
                T.rect(xx, yy, 1, min(6, y + h - yy), c["s2"])
            if x <= xx + 1 and xx + 2 < x + w:
                T.px(xx + 1, yy + 1, c["s3"])
                T.px(xx + 2, yy + 1, c["s3"])


def tinge(T, x, y, w, h, cor, t):
    """Mistura cada pixel do retângulo com `cor` (sombra e luz do cilindro da torre)."""
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if 0 <= xx < T.w and 0 <= yy < T.h:
                v = T.im.getpixel((xx, yy))
                if v[3]:
                    T.im.putpixel((xx, yy), mix(v, cor, t))


def telhado(w, c):
    """Cone de telhas, claro à esquerda e escuro à direita, com um contorno de 1 px."""
    ww, h = w + 8, ALTURA_TELHADO
    t = Tela(ww, h)
    for j in range(h):
        rw = max(2, round((j + 1) / h * ww))
        x0 = (ww - rw) // 2
        for i in range(rw):
            esq = x0 + i < ww / 2
            cor = c["r1"] if esq else c["r2"]
            if esq and i < 2 and rw > 4:
                cor = c["r3"]
            if j % 5 == 4:
                cor = mix(cor, c["ol"], .4)
            t.px(x0 + i, j, cor)
    return contorno(t.im, c["ol"])


def estandarte(cor, c):
    t = Tela(12, 24)
    t.rect(0, 0, 12, 20, cor)
    t.poly([(0, 19), (5, 19), (0, 23)], cor)
    t.poly([(6, 19), (11, 19), (11, 23)], cor)
    t.rect(0, 0, 12, 2, c["ouro"])
    t.rect(5, 5, 2, 10, c["ouro"])
    t.rect(2, 8, 8, 2, c["ouro"])
    return contorno(t.im, c["ol"])


def fresta(T, x, y, c, acesa):
    """Seteira: 3 px de largura, moldura de pedra clara; de noite a luz acende."""
    T.rect(x - 1, y - 1, 5, 10, c["s3"])
    T.rect(x, y, 3, 8, c["luz"] if acesa else c["fresta"])
    if acesa:
        T.rect(x + 1, y + 1, 1, 6, hx("#fff0b0"))


def torre(T, x, y0, base, c, lado):
    """Corpo, anel de pedra no alto, seteiras, estandarte e (na direita) a janela de madeira."""
    h = base - y0
    T.rect(x, y0, TW, h, c["ol"])
    tijolos(T, x + 1, y0 + 1, TW - 2, h - 1, c)
    tinge(T, x + TW - 7, y0 + 1, 6, h - 1, c["ol"], .28)
    tinge(T, x + 1, y0 + 1, 3, h - 1, hx("#ffffff"), .14)
    T.rect(x - 2, y0 - 5, TW + 4, 6, c["ol"])
    T.rect(x - 1, y0 - 4, TW + 2, 3, c["s3"])
    T.rect(x - 1, y0 - 1, TW + 2, 1, c["s2"])
    T.put(telhado(TW, c), x - 4, y0 - 5 - ALTURA_TELHADO - 1)
    T.rect(x + TW // 2, y0 - 5 - ALTURA_TELHADO - 11, 1, 11, c["wd2"])  # mastro
    acesa = c["luz"] == hx("#ffd36a")
    cx = x + (TW - 3) // 2
    fresta(T, cx, y0 + 8, c, acesa)
    ban = c["ban1"] if lado == 0 else c["ban2"]
    T.rect(x + 7, y0 + 21, 14, 2, c["wd2"])
    T.put(estandarte(ban, c), x + 7, y0 + 22)
    if base - (y0 + 56) >= 62:
        fresta(T, cx, (y0 + 56 + base - 40) // 2 - 4, c, acesa)
    if lado:  # janela de madeira (a porta da torre da esquerda é desenhada à parte: ela abre)
        wx, wy = x + 9, base - 22
        T.rect(wx - 1, wy - 1, 12, 14, c["s3"])
        T.rect(wx, wy, 10, 12, c["luz"] if acesa else c["fresta"])
        T.rect(wx + 4, wy, 2, 12, c["wd2"])
        T.rect(wx, wy + 5, 10, 2, c["wd2"])
        T.rect(wx - 2, wy + 12, 14, 2, c["wd1"])


def ameias(T, x0, x1, y, c):
    """Dentes da muralha: 9 px de largura, 6 de altura, de 15 em 15."""
    for xx in range(x0, x1 - 8, 15):
        T.rect(xx, y - 6, 9, 7, c["ol"])
        T.rect(xx + 1, y - 5, 7, 6, c["s1"])
        T.rect(xx + 1, y - 5, 7, 1, c["s3"])
        T.rect(xx + 1, y - 5, 1, 5, c["s3"])
        T.px(xx + 6, y - 3, c["s2"])
        T.px(xx + 6, y - 2, c["s2"])


def muralha(T, h, c):
    """A parede entre as torres: ameias em cima, pedra, e a faixa escura do título."""
    T.rect(FX, FY, FW, h, c["ol"])
    tijolos(T, FX + 1, FY + 1, FW - 2, h - 2, c)
    ameias(T, FX + 6, FX + FW - 4, FY, c)
    T.rect(FX + 5, FY + 1, FW - 10, 18, faixa(c))
    T.rect(FX + 5, FY + 19, FW - 10, 1, c["s3"])
    for rx in (FX + 3, FX + FW - 4):  # rebites
        for ry in (FY + 4, FY + 14):
            T.px(rx, ry, c["s3"])


# ------------------------------------------------------------------ bichos e bichinhos
def dragao(c, asa):
    """Dragão verde de perfil, voando para a direita; `asa` 0 = asa para cima, 1 = para baixo."""
    t = Tela(34, 22)
    t.poly([(10, 11), (4, 14), (0, 13), (2, 17), (9, 17), (13, 15)], c["dr1"])  # cauda
    t.rect(0, 12, 2, 2, c["dr3"])
    t.ell(8, 9, 22, 16, c["dr1"])  # corpo
    t.ell(10, 13, 21, 17, c["dr2"])  # barriga
    t.poly([(19, 11), (25, 5), (28, 6), (23, 13)], c["dr1"])  # pescoço
    t.ell(23, 3, 31, 9, c["dr1"])  # cabeça
    t.rect(29, 6, 4, 3, c["dr1"])  # focinho
    t.px(27, 4, c["olho"])
    t.px(28, 4, c["ol"])
    t.px(24, 2, c["dr3"])
    t.px(25, 1, c["dr3"])
    t.px(12, 17, c["dr1"])
    t.px(18, 17, c["dr1"])
    if asa == 0:
        t.poly([(10, 10), (7, 3), (12, 5), (15, 0), (18, 4), (21, 3), (19, 10)], c["dr3"])
        t.line([(12, 9), (10, 5)], c["ol"])
        t.line([(15, 9), (15, 3)], c["ol"])
    else:
        t.poly([(10, 11), (5, 18), (10, 17), (14, 21), (18, 17), (20, 12)], c["dr3"])
        t.line([(12, 12), (9, 17)], c["ol"])
        t.line([(15, 12), (14, 18)], c["ol"])
    return contorno(t.im, c["ol"])


def cavaleiro(c, respira):
    t = Tela(10, 15)
    pal = {"r": c["r1"], "h": c["s3"], "k": c["fresta"], "b": c["s1"], "l": c["s2"], "d": c["wd2"], "s": c["ban2"],
           "y": c["ouro"]}
    linhas = ["....rr....",
              "...rrr....",
              "..hhhhh...",
              "..hkkkh...",
              "..hhhhh...",
              "..bbbbb...",
              ".sbbbbbb..",
              "ssbbbbbb..",
              "sysbbbb...",
              ".ssbbbb...",
              "..bbbbb...",
              "..lb.bl...",
              "..ll.ll...",
              "..ll.ll...",
              ".ddd.ddd.."]
    t.spr(0, 0, linhas, pal)
    t.px(8, 3, c["s3"]) if respira else None
    return contorno(t.im, c["ol"])


def lanca(c):
    t = Tela(3, 32)
    t.rect(1, 3, 1, 29, c["wd1"])
    t.px(1, 0, c["s3"])
    t.rect(0, 1, 3, 1, c["s3"])
    t.rect(0, 2, 3, 1, c["s1"])
    t.px(1, 3, c["ban1"])
    return contorno(t.im, c["ol"])


def arvore(c, bal):
    t = Tela(24, 30)
    t.rect(10, 16, 4, 14, c["wd1"])
    t.rect(10, 16, 1, 14, c["wd3"])
    t.rect(13, 16, 1, 14, c["wd2"])
    t.rect(8, 28, 8, 2, c["wd2"])
    for (x0, y0, x1, y1) in ((1, 8, 12, 20), (10, 8, 22, 20), (5, 0, 18, 13)):
        t.ell(x0 + bal, y0, x1 + bal, y1, c["leaf2"])
        t.ell(x0 + bal, y0 - 1, x1 + bal - 1, y1 - 3, c["leaf"])
    for (x, y) in ((6, 6), (13, 4), (16, 11), (7, 12)):
        t.px(x + bal, y, c["g3"])
        t.px(x + bal + 1, y, c["g3"])
    return contorno(t.im, c["ol"])


def ilhota(c, torrinha, bobe):
    """Pedaço de rocha flutuando: com torrezinha de bandeira, ou com uma árvore."""
    t = Tela(36, 40)
    t.poly([(0, 24), (35, 24), (30, 31), (22, 38), (18, 39), (12, 33), (5, 29)], c["d1"])
    t.rect(0, 22, 36, 4, c["g1"])
    t.rect(0, 22, 36, 1, c["g3"])
    t.px(9, 29, c["d3"])
    t.px(10, 29, c["d3"])
    t.px(22, 30, c["d2"])
    t.px(23, 30, c["d2"])
    t.px(16, 34, c["d2"])
    if torrinha:
        t.rect(14, 8, 9, 15, c["s1"])
        t.rect(14, 8, 2, 15, c["s3"])
        t.rect(20, 8, 3, 15, c["s2"])
        t.rect(12, 5, 13, 3, c["s3"])
        t.poly([(11, 5), (25, 5), (18, -1 + 0)], c["r1"])
        t.rect(17, 14, 2, 5, c["fresta"])
        t.rect(18, -6 + 6, 1, 1, c["wd2"])
        t.rect(2, 20, 9, 2, c["g2"])
    else:
        t.rect(17, 12, 3, 11, c["wd1"])
        t.ell(10, 3, 27, 16, c["leaf2"])
        t.ell(10, 2, 25, 13, c["leaf"])
        t.px(15, 6, c["g3"])
        t.px(16, 6, c["g3"])
    return contorno(t.im, c["ol"])


def moldura_pedra(T, x, y, w, h, p):
    T.rect(x, y, w, h, p["ol"])
    tijolos(T, x + 1, y + 1, w - 2, h - 2, p)
    T.cantos(x, y, w, h)


# ------------------------------------------------------------------ efeitos de clique
# O widget conta os quadros desde o clique (Estado.efeitos[nome]); cada função abaixo desenha um quadro do efeito.
# Porta: (largura da folha, pose do rei) a cada quadro. A folha gira na dobradiça da esquerda (10 = fechada) e o rei
# olha para fora: "f" de frente, "e" para a esquerda, "d" para a direita.
ROTEIRO_PORTA = [(7, None), (4, None), (2, None), (2, "f"), (2, "e"), (2, "e"), (2, "e"), (2, "f"), (2, "d"), (2, "d"),
                 (2, "d"), (2, "f"), (2, "f"), (4, "f"), (7, None), (10, None)]
PORTA_W, PORTA_H = 10, 15
FOGO_DRAGAO = [4, 9, 15, 20, 24, 24, 24, 22, 18, 13, 8, 3]  # comprimento da labareda em cada quadro
LANCA_SOBE = [3, 6, 9, 12, 12, 12, 12, 12, 9, 6, 3, 0]  # quanto a lança sobe, em px
CHAMA_CRESCE = [2, 5, 8, 10, 10, 9, 8, 6, 4, 2, 1, 0]  # quanto a chama da tocha cresce, em px
SOL_OLHOS = ["a", "a", "f", "a", "a", "a", "p", "p", "p", "a", "a", ""]  # aberto, fechado, piscadela, sem rosto


def rei(c, pose):
    """Rei de 7x14 px: coroa, barba branca, manto vermelho com gola e barra de arminho. A cabeça vira, o corpo fica."""
    dx = {"f": 0, "e": -1, "d": 1}[pose]
    olhos = {"f": "fkfkf", "e": "kfkff", "d": "ffkfk"}[pose]
    cabeca = [".y.y.y.", ".yyryy.", ".fffff.", "." + olhos + ".", ".fffff.", ".wwfww.", "..www.."]
    cabeca = [l[1:] + "." if dx < 0 else "." + l[:-1] if dx > 0 else l for l in cabeca]
    corpo = ["wwwwwww", "rrrwrrr", "rrrrrrr", "rgggggr", "rrrrrrr", "rrrrrrr", "wwwwwww"]
    t = Tela(7, 14)
    t.spr(0, 0, cabeca + corpo, {"y": c["ouro"], "r": c["manto"], "f": c["pele"], "k": c["ol"], "w": c["branco"],
                                  "g": c["ouro2"]})
    return t.im


def porta(c, w, pose):
    """A porta da torre da esquerda com a moldura de pedra (12x16): folha de madeira de `w` px e, atrás dela, o vão
    escuro com o rei. Com w = 10 é idêntica à porta fechada de antes."""
    t = Tela(PORTA_W + 2, PORTA_H + 1)
    t.rect(0, 0, 12, 16, c["s3"])
    t.rect(1, 1, 10, 15, c["inter"])
    if pose:
        t.put(rei(c, pose), 3, 2)
    t.rect(1, 1, w, 15, c["wd1"])
    for k in range(1, w, 3):
        t.rect(1 + k, 2, 1, 14, c["wd2"])
    if w < PORTA_W:  # a espessura da folha entreaberta
        t.rect(w, 1, 1, 15, c["wd2"])
    t.rect(1, 5, w, 1, c["ol"])
    t.rect(1, 11, w, 1, c["ol"])
    if w > 4:
        t.px(w - 2, 9, c["ouro"])
    t.px(1, 1, c["s3"])  # o arco: os dois cantos de cima são de pedra
    t.px(10, 1, c["s3"])
    return t.im


def chama(T, tx, ty, f, grande, c):
    """Chama da tocha: `f` é o tremor (0 a 2) e `grande` quantos px ela cresceu (0 = a chama de sempre)."""
    w = 3 + 2 * (grande >= 3) + 2 * (grande >= 8)
    T.rect(tx - w // 2, ty - 7 - f - grande, w, 4 + f + grande, c["brasa"])
    T.rect(tx - w // 2 + (f == 2), ty - 6 - f - grande, w - 1, 3 + f + grande, c["chama"])
    cw = 1 + 2 * (grande >= 3)
    T.rect(tx - cw // 2, ty - 4 - grande // 2, cw, 1 + grande // 2, c["fogo"])
    r = random.Random(grande * 7 + f)
    for _ in range(grande // 2):  # faíscas
        T.px(tx + r.randrange(-w, w + 1), ty - 8 - grande - r.randrange(0, 6), c["fogo"] if r.random() < .5 else c["chama"])


def labareda(T, x, y, f, c):
    """Fogo que o dragão cospe pela boca em (x, y): cone que cresce, ondula e se apaga no quadro `f` do efeito."""
    comp = FOGO_DRAGAO[f]
    r = random.Random(f)
    for i in range(comp):
        meio = y + round(math.sin(i / 3 + f) * (1 + i / 12))
        alt = 1 + i // 4
        for dy in range(-alt, alt + 1):
            ponta = i > comp - 4
            if ponta and r.random() < .5:
                continue
            cor = c["fogo"] if abs(dy) <= alt // 3 and i < comp * .6 else c["chama"] if abs(dy) <= alt * 2 // 3 else c["brasa"]
            T.px(x + i, meio + dy, cor)
    for _ in range(comp // 4):  # brasas soltas
        T.px(x + comp + r.randrange(-2, 6), y + r.randrange(-5, 6), c["chama"])


def rosto_sol(T, cx, cy, olhos):
    """Rosto do sol em (cx, cy): olhos abertos, fechados ou uma piscadela (o direito fecha), com sorriso e bochechas."""
    tinta, rosa = hx("#7a4a10"), hx("#ff8a5a")
    if olhos == "a" or olhos == "p":
        T.px(cx - 3, cy - 1, tinta)
        T.px(cx - 3, cy - 2, tinta)
    else:
        T.rect(cx - 4, cy - 1, 3, 1, tinta)
    if olhos == "a":
        T.px(cx + 2, cy - 1, tinta)
        T.px(cx + 2, cy - 2, tinta)
    else:
        T.rect(cx + 1, cy - 1, 3, 1, tinta)
    for dx, dy in ((-2, 2), (-1, 3), (0, 3), (1, 3), (2, 2)):
        T.px(cx + dx, cy + dy, tinta)
    T.px(cx - 4, cy + 1, rosa)
    T.px(cx + 3, cy + 1, rosa)


def cintila(T, x, y, f):
    """A lua cintila: estrelinhas de quatro pontas acendem e apagam ao redor dela."""
    brilho_ = hx("#ffffff")
    for k, (dx, dy) in enumerate(((-3, 3), (22, 6), (20, 21), (-1, 17), (10, -4))):
        fase = (f + k * 2) % 6
        if fase < 3:
            T.px(x + dx, y + dy, brilho_)
            if fase == 1:
                for ex, ey in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    T.px(x + dx + ex, y + dy + ey, brilho_)


# ------------------------------------------------------------------ o tema
class Castelo(TemaPixel):
    id = "castelo"
    nome = "Castelo medieval"
    descricao = "Muralha de pedra com duas torres, dragão no céu e cavaleiro de guarda. O céu muda com a hora."
    cores_balao = ("#f6e9c8", "#2a2f45", "#232733")
    animacao_ms = 160
    efeitos = EFEITOS
    PAD = 8

    def __init__(self):
        self._cache = {}
        self._pedra = {}
        self._portas = {}
        self._ui = (None, None)

    def paleta(self, per):
        p = PER[per]
        return dict(texto=p["ink"], dim=p["dim"], ok=p["ok"], acc=p["acc"], sel_fundo=p["acc"],
                    sel_texto=hx("#fff8ea"), linha=p["paper2"], hover=p["acc"])

    def moldura_dialogo(self, T, w, h, titulo, per, hover_fechar):
        p = PER[per]
        moldura_pedra(T, 0, 0, w, h, p)
        T.rect(2, 2, w - 4, self.TITULO_H - 4, faixa(p))
        T.texto(9, 5, titulo, p["ol"])
        T.texto(8, 4, titulo, p["stxt"])
        T.put(icone("fechar", DOURADO if hover_fechar else p["stxt"]), w - 12, 5)
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
            for k in range(36):
                sx, sy = r.randrange(2, W - 2), r.randrange(2, 70)
                if (t + k) % 5:
                    sk.px(sx, sy, hx("#fff1c9") if (t + k) % 3 else hx("#8aa0d8"))
            sk.put(lua(p), 232, 8, )
            for k in range(6):  # vagalumes nas laterais
                fx = (8 + k * 12 if k < 3 else W - 44 + (k - 3) * 12) + math.sin((t + k * 3) / 2.5) * 5
                fy = g["py"] + 50 + math.cos((t * 1.2 + k * 2) / 2.2) * 8 - (k % 2) * 16
                if (t + k) % 4:
                    sk.px(fx, fy, hx("#ffe88a"))
                    sk.px(fx + 1, fy, hx("#8a7a3a"))
        else:
            sk.put(sol(t % 8 // 4, p), *((232, 0) if not tarde else (160, 14)))
        dx = (t // 5) % 3
        sk.put(nuvem(34, 18, p), 2 + dx, 56 if not tarde else 78)
        sk.put(nuvem(30, 15, p), 150 + dx, 4)
        sk.put(nuvem(22, 12, p), 2 + dx, 112)
        sk.put(nuvem(26, 14, p), W - 28 - dx, 98)
        sk.put(nuvem(24, 12, p), 296 + dx, 10)
        brilho(sk, 14, 92, t % 6 < 3)
        brilho(sk, W - 10, 70, t % 6 >= 3)
        bob = [0, 0, 1, 1, 1, 1, 0, 0][t % 8]
        sk.put(ilhota(p, True, bob), 74, 2 + bob)
        sk.put(ilhota(p, False, bob), 292, 20 + (1 - bob))
        sk.put(ilha(W - 2 * IX, p), IX, FY + g["fh"] - 6)
        return sk.im

    def _castelo(self, per, g):
        k = (per, g["H"])
        if k not in self._pedra:
            p = PER[per]
            T = Tela(W, g["H"])
            base = FY + g["fh"]
            muralha(T, g["fh"], p)
            for lado, x in enumerate(TX):
                torre(T, x, FY - 10, base, p, lado)
            self._pedra[k] = T.im
        return self._pedra[k]

    def _frente(self, per, t, g):
        p = PER[per]
        T = Tela(W, g["H"])
        base = FY + g["fh"]
        y_ground = base - 6
        tufos(T, p, IX - 3, W - IX + 3, base + 1)
        # bandeiras ao vento, no alto dos mastros
        for lado, x in enumerate(TX):
            mx, my = x + TW // 2 + 1, FY - 10 - 5 - ALTURA_TELHADO - 11
            cor = p["ban1"] if lado == 0 else p["ban2"]
            for i in range(11):
                onda = round(math.sin((i * .7) - t * math.pi / 8 * 2) * (1 + i / 7))
                T.rect(mx + i, my + onda, 1, 6 - i // 4, cor)
                T.px(mx + i, my + onda, p["ouro"])
        # (as tochas e o cavaleiro são desenhados por quadro em _atores: reagem ao clique)
        a = arvore(p, [0, 0, 1, 1][t // 4 % 4])
        T.put(a, 4, y_ground + 4 - a.height)
        for k2, fxp in enumerate((29, W - 14)):  # flores nas bordas da ilha
            T.put(flor(((t + k2 * 2) // 4) % 3 - 1, p, fechada=per == "noite"), fxp, y_ground - 10)
        return T.im

    @staticmethod
    def _pos_dragao(t):
        return (t * 3) % (W + 80) - 40, 24 + round(math.sin(t / 6) * 6)

    def _dragao(self, per, t, f=None):
        """O dragão no quadro `t`; com `f` (quadro do efeito "dragao"), cuspindo fogo."""
        p = PER[per]
        d = dragao(p, t // 2 % 2)
        x, y = self._pos_dragao(t)
        sprite = Tela(W, 60)
        sprite.put(d, x, y)
        if f is not None:
            labareda(sprite, x + 34, y + 8, f, p)
        return sprite.im

    def _porta(self, per, f):
        """Sprite da porta no quadro `f` do efeito "porta" (None = fechada, parada); em cache."""
        k = (per, f)
        if k not in self._portas:
            w, pose = ROTEIRO_PORTA[f] if f is not None else (PORTA_W, None)
            self._portas[k] = porta(PER[per], w, pose)
        return self._portas[k]

    def _atores(self, per, t, g, ef):
        """Tochas e cavaleiro, desenhados por quadro porque reagem ao clique (chama que cresce, lança que sobe)."""
        p = PER[per]
        T = Tela(W, g["H"])
        pos = self._pos(g)
        for i, (tx, ty) in enumerate(pos["tochas"]):
            T.rect(tx - 1, ty, 3, 2, p["ol"])
            T.rect(tx, ty - 3, 1, 4, p["wd2"])
            f = ef.get(f"tocha{i}")
            chama(T, tx, ty, (0, 1, 0, 2)[t % 4], CHAMA_CRESCE[f] if f is not None else 0, p)
        kx, ky = pos["cavaleiro"]
        noite = per == "noite"
        k = cavaleiro(p, noite)
        sobe = LANCA_SOBE[ef["cavaleiro"]] if "cavaleiro" in ef else 0
        bob = t % 8 // 4
        T.put(lanca(p), kx + 9, ky - 17 + bob - sobe)
        ky += 0 if noite else bob
        T.put(k, kx, ky)
        if sobe:  # o braço acompanha a lança para cima; a mão fica no cabo
            T.rect(kx + 9, ky + 8 - min(sobe, 6), 2, min(sobe, 6) + 1, p["s1"])
            T.px(kx + 10, ky + 8 - min(sobe, 6), p["s3"])
            if "cavaleiro" in ef and 3 <= ef["cavaleiro"] <= 8 and ef["cavaleiro"] % 2:  # reflexo na ponta
                gx, gy = kx + 11, ky - 17 - sobe + 2
                for ex, ey in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                    T.px(gx + ex, gy + ey, hx("#ffffff"))
        if noite:
            T.texto(kx + 4, ky - 10, "z", mix(p["stxt"], p["slate"], .2))
        return T.im

    def _pos(self, g):
        """Onde ficam, em pixels de arte, as coisas que reagem ao clique."""
        base = FY + g["fh"]
        ky = base - 6 + 4 - 17  # topo do cavaleiro (sprite de 17 px com contorno)
        return dict(base=base, porta=(TX[0] + 8, base - 16), tochas=[(x + TW // 2, base - 34) for x in TX],
                    cavaleiro=(TX[1] + TW + 4, ky))

    def _regioes_efeitos(self, e, t, g):
        """Áreas clicáveis dos enfeites. Mudam com o quadro (o dragão voa): ficam fora do cache da interface."""
        pos = self._pos(g)
        px_, py_ = pos["porta"]
        kx, ky = pos["cavaleiro"]
        x, y = self._pos_dragao(t)
        astro = {"manha": (236, 4, 259, 27), "tarde": (164, 18, 187, 41), "noite": (232, 8, 252, 28)}[e.periodo]
        regs = [Regiao("efeito:dragao", (x, y, x + 36, y + 24)),
                Regiao("efeito:porta", (px_ - 1, py_ - 1, px_ + 13, pos["base"]), "Bater na porta"),
                Regiao("efeito:cavaleiro", (kx - 1, ky - 20, kx + 12, ky + 17), "Cumprimentar o cavaleiro"),
                Regiao("efeito:sol", astro, "Cutucar o sol" if e.periodo != "noite" else "Cutucar a lua")]
        for i, (tx, ty) in enumerate(pos["tochas"]):
            regs.append(Regiao(f"efeito:tocha{i}", (tx - 4, ty - 12, tx + 5, ty + 4), "Atiçar o fogo"))
        return regs

    # --- interface (faixas, pergaminho, texto): só muda quando o estado muda ---
    def _interface(self, e, g):
        p = PER[e.periodo]
        T = Tela(W, g["H"])
        regs = []
        # cabeçalho: título e botões (da direita para a esquerda)
        titulo = f"Diário · {DIAS_SEMANA[e.dia.weekday()]} {e.dia:%d/%m}"
        T.texto(FX + 13, FY + 7, titulo, p["ol"])
        T.texto(FX + 12, FY + 6, titulo, p["stxt"])
        if not e.eh_hoje:  # tabuleta de madeira "Hoje" ao lado da data, para voltar ao dia atual
            caixa = (FX + 12 + largura(titulo) + 6, FY + 4, FX + 12 + largura(titulo) + 30, FY + 15)
            T.rect(caixa[0], caixa[1], 24, 11, p["ol"])
            T.rect(caixa[0] + 1, caixa[1] + 1, 22, 9, p["wd3"] if e.hover == "hoje" else p["wd1"])
            T.texto(caixa[0] + 3, caixa[1] + 2, "Hoje", p["stxt"])
            regs.append(Regiao("hoje", caixa, DICAS["hoje"]))
        x = FX + FW - 6
        for nome in reversed(BOTOES):
            x -= 9
            ic = icone(nome, DOURADO if e.hover == nome else p["stxt"])
            T.put(ic, x + (9 - ic.width) // 2, FY + 10 - ic.height // 2)
            regs.append(Regiao(nome, (x, FY + 1, x + 9, FY + 19), DICAS[nome]))
        regs.append(Regiao("arrastar", (FX, FY, FX + FW, FY + 20), "", ""))
        # pergaminho com a lista
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
        # faixa escura de baixo, barra do campo de lançamento (o Entry do Tk fica por cima) e status
        T.rect(px_, g["py"] + g["ph"] + 1, pw, FY + g["fh"] - 1 - (g["py"] + g["ph"] + 1), faixa(p))
        T.rect(px_, g["ey"], pw, 15, p["ol"])
        T.rect(px_ + 1, g["ey"] + 1, pw - 2, 13, p["slate"])
        campo = (px_ + 4, g["ey"] + 2, px_ + pw - 4, g["ey"] + 13)
        T.rect(campo[0], campo[1], campo[2] - campo[0], campo[3] - campo[1], mix(p["slate"], hx("#000000"), .35))
        msg = e.status if e.status and e.status_tipo != "dica" else DICA_CURTA
        cor = (STATUS_COR.get(e.status_tipo) or {}).get(e.periodo) or mix(p["stxt"], faixa(p), .35)
        T.texto(px_ + 2, g["sty"], cortar(msg, pw - 4), cor)
        return T.im, regs, campo

    def quadro(self, e: Estado, t: int) -> Quadro:
        g = self._geo(e)
        ef = e.efeitos
        chave = (e.dia, tuple(e.topicos), e.extra, e.status, e.status_tipo, e.hover, e.periodo, e.eh_hoje)
        if self._ui[0] != chave:
            self._ui = (chave, self._interface(e, g))
        ui, regs, campo = self._ui[1]
        img = Image.new("RGBA", (W, g["H"]), TRANSPARENTE)
        img.alpha_composite(self._camada("fundo", e.periodo, t, g, self._fundo))
        if "sol" in ef:
            img.alpha_composite(self._astro(e.periodo, ef["sol"]))
        img.alpha_composite(self._dragao(e.periodo, t, ef.get("dragao")))
        img.alpha_composite(self._castelo(e.periodo, g))
        px_, py_ = self._pos(g)["porta"]
        img.alpha_composite(self._porta(e.periodo, ef.get("porta")), (px_, py_))
        img.alpha_composite(ui)
        img.alpha_composite(self._camada("frente", e.periodo, t, g, self._frente))
        img.alpha_composite(self._atores(e.periodo, t, g, ef))
        return self._finaliza_cena(img, regs + self._regioes_efeitos(e, t, g), campo, PER[e.periodo])

    def _astro(self, per, f):
        """Rosto do sol piscando, ou a lua cintilando, por cima do céu."""
        T = Tela(W, 60)
        if per == "noite":
            cintila(T, 232, 8, f)
        else:
            olhos = SOL_OLHOS[f]
            if olhos:
                x, y = (232, 0) if per == "manha" else (160, 14)
                rosto_sol(T, x + 15, y + 15, olhos)
        return T.im

    def _finaliza_cena(self, img, regs, campo, p):
        Z = self.Z
        imagem = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
        regioes = [Regiao(r.nome, tuple(v * Z for v in r.caixa), r.dica, r.cursor) for r in regs]
        entrada = tuple(v * Z for v in campo)
        estilo = dict(bg="#%02x%02x%02x" % mix(p["slate"], hx("#000000"), .35)[:3], fg="#%02x%02x%02x" % p["stxt"][:3],
                      cursor="#%02x%02x%02x" % p["stxt"][:3], fonte=("Consolas", 10))
        return Quadro(imagem, regioes, entrada, estilo, True)
