"""Tema Dino do deserto: um dinossauro corre num deserto que rola e pula os cactos sozinho. O cenário é feito em camadas
com parallax (céu, astros, nuvens, pássaros, montanhas, colinas, chão, cactos, dino) e muda de manhã, tarde e noite. A
lista de tópicos é um cartão de papel que afunda na terra do chão.

Cada camada que rola é uma faixa larga desenhada uma vez por período; a cada quadro só se recorta uma janela dela (com a
volta emendada), então o quadro custa poucos milissegundos e `t` pode crescer sem parar. O HUD e o cartão só são
redesenhados quando o estado muda.
"""
import math
import random

from PIL import Image

from ..pixel import Tela, TRANSPARENTE, contorno, cortar, hx, icone, largura, mix
from .base import BOTOES, DIAS_SEMANA, DICAS, Estado, Quadro, Regiao
from .pixeltema import TemaPixel, botao_resumir

W, CENA_H, HUD_H, GY = 304, 100, 13, 84  # largura, altura do cenário, barra superior e linha do chão (pixels de arte)
VEL = dict(nuvens=.25, montanhas=.6, colinas=1.5, chao=3)  # pixels de arte por quadro
L_CHAO = 480  # o chão e os cactos se repetem a cada 480 px
DINO_X = 58
SALTO_Q, SALTO_H = 20, 38  # quadros no ar e altura do pulo; no ar o chão passa 3 x 20 = 60 px
POS_CACTOS = [(60, "alto"), (185, "pequeno"), (300, "gemeos"), (415, "alto")]  # centros na faixa de 480 px (≥ 60 px de intervalo livre)
PRETO_PASSARO = hx("#0b0710")

_ESC = hx("#2c1d2e")
P = {
    "manha": dict(ceu=[hx("#577f9d"), hx("#6fb0b7"), hx("#a0ddd3")], nuvem=hx("#fcecd1"),
                  mont=hx("#b87e6c"), mont2=hx("#d3a084"), ol=_ESC, cacto=hx("#cdd4a1"), cacto2=hx("#83a181"),
                  grama=hx("#aad795"), terra=hx("#8f5252"), terra2=hx("#6a3948"), pedra=hx("#a86a5c"),
                  dino=hx("#4ab071"), sol=hx("#fff0b0"), sol2=hx("#f2c46a"), papel=hx("#fcecd1"), papel2=hx("#ecd5b8"),
                  tinta=_ESC, dim=hx("#8a7a86"), ok=hx("#2f8a58"), seta=hx("#ffd86b"), poeira=hx("#e6c8a4")),
    "tarde": dict(ceu=[hx("#4d3a73"), hx("#a24d72"), hx("#e8825a"), hx("#f7c27c")], nuvem=hx("#ffd2a8"),
                  mont=hx("#8e4f62"), mont2=hx("#c2745f"), ol=hx("#2a1730"), cacto=hx("#c8c78c"),
                  cacto2=hx("#7a9468"), grama=hx("#a9bd57"), terra=hx("#85464a"), terra2=hx("#5c2c3c"),
                  pedra=hx("#a05f58"), dino=hx("#4ab071"), sol=hx("#ffb04a"), sol2=hx("#ff7a3c"), papel=hx("#fbe3bf"),
                  papel2=hx("#e8c898"), tinta=hx("#2a1730"), dim=hx("#8a7480"), ok=hx("#3f7a2a"), seta=hx("#ffd86b"),
                  poeira=hx("#e8b890")),
    "noite": dict(ceu=[hx("#0d1230"), hx("#161d48"), hx("#222d62"), hx("#34447c")], nuvem=hx("#3b4a86"),
                  mont=hx("#3a3057"), mont2=hx("#4d4272"), ol=hx("#120c1c"), cacto=hx("#7f9a84"),
                  cacto2=hx("#556f61"), grama=hx("#3f805f"), terra=hx("#4b2a40"), terra2=hx("#2f1b2c"),
                  pedra=hx("#664a66"), dino=hx("#3d9e69"), sol=hx("#fff1c8"), sol2=hx("#d9c58f"), papel=hx("#e8dcc2"),
                  papel2=hx("#d0c3a6"), tinta=hx("#1d1830"), dim=hx("#6f7690"), ok=hx("#2a8a55"), seta=hx("#ffd86b"),
                  poeira=hx("#6a5a86")),
}

# g = corpo, s = sombra (perna de trás), e = olho, w = brilho do olho, n = narina
DINO_CORPO = [
    "..........gggggggg",
    ".........gggggggggg",
    ".........gggeegggggggg"[:21],
    ".........gggewgggggng"[:21],
    ".........gggggggggggg",
    ".........gggggggggggg",
    ".........gggggggggggg",
    ".........ggggggggggg",
    "........ggggggg",
    ".....gggggggggggg",
    "..ggggggggggggggggg",
    ".gggggggggggggggggg",
    "gggggggggggggggg",
    ".gggggggggggggg",
    "..gggggggggggg",
    "....gggggggggg",
]
DINO_PERNAS = {
    "a": [".....sss...ggg", ".....sss...ggg", "...........ggg", "...........gggg"],
    "b": [".....sss...ggg", ".....sss...ggg", ".....sss", ".....ssss"],
    "pulo": [".....sss...ggg", ".....sss...ggg", "....ssss..gggg"],
}
# pássaro de 7x4 com as asas em quatro posições (em cima, no meio, embaixo, no meio)
PASSARO = [["#.....#", ".#...#.", "..#.#..", "...#..."],
           [".......", "##...##", "..###..", "......."],
           ["...#...", "..#.#..", ".#...#.", "#.....#"],
           [".......", "##...##", "..###..", "......."]]
# (x inicial, y, velocidade em px/quadro, fase): um bando para a direita, um para a esquerda e um solitário
BANDO = [(20, 26, .8, 0), (8, 32, .8, 1), (32, 32, .8, 2),
         (210, 44, -.55, 3), (222, 40, -.55, 0),
         (120, 19, 1.1, 2)]


# ------------------------------------------------------------------ sprites
def dino(c, pose="a", pisca=False):
    linhas = DINO_CORPO + DINO_PERNAS[pose]
    T = Tela(21, len(linhas))
    pal = {"g": c["dino"], "s": mix(c["dino"], c["ol"], .35), "e": c["ol"], "w": c["papel"], "n": c["ol"]}
    if pisca:
        pal["w"] = pal["e"]
    T.spr(0, 0, [ln.ljust(21, ".") for ln in linhas], pal)
    return contorno(T.im, c["ol"])


def _vertical(T, x, y0, y1, w, cor, sombra):
    T.rect(x, y0, w, y1 - y0 + 1, cor)
    T.rect(x, y0, 1, y1 - y0 + 1, sombra)
    T.px(x, y0, TRANSPARENTE)
    T.px(x + w - 1, y0, TRANSPARENTE)


def cacto(c, tipo):
    cor, sh = c["cacto"], c["cacto2"]
    if tipo == "alto":
        T = Tela(13, 22)
        _vertical(T, 4, 0, 21, 5, cor, sh)
        _vertical(T, 0, 7, 14, 3, cor, sh)
        T.rect(3, 12, 2, 3, cor)
        _vertical(T, 10, 3, 10, 3, cor, sh)
        T.rect(8, 8, 2, 3, cor)
        T.rect(4, 19, 5, 3, sh)
    elif tipo == "pequeno":
        T = Tela(11, 15)
        _vertical(T, 3, 0, 14, 4, cor, sh)
        _vertical(T, 7, 4, 9, 3, cor, sh)
        T.rect(6, 7, 1, 3, cor)
        T.rect(3, 12, 4, 3, sh)
    else:  # gêmeos
        T = Tela(24, 16)
        for x0, h in ((0, 16), (10, 13), (18, 10)):
            _vertical(T, x0 + 1, 16 - h, 15, 4, cor, sh)
            T.rect(x0 + 1, 13, 4, 3, sh)
    return contorno(T.im, c["ol"])


def cacto_longe(c, colina):
    """Silhueta de cacto distante: sem contorno, cor entre o cacto e a colina."""
    T = Tela(7, 11)
    cor = mix(c["cacto2"], colina, .4)
    T.rect(2, 0, 3, 11, cor)
    T.rect(0, 3, 2, 4, cor)
    T.rect(1, 6, 2, 2, cor)
    T.rect(5, 2, 2, 4, cor)
    T.rect(4, 5, 2, 2, cor)
    return T.im


def mini_cacto(cor, sombra):
    T = Tela(5, 7)
    T.rect(2, 0, 2, 7, cor)
    T.rect(0, 2, 1, 3, cor)
    T.rect(0, 4, 3, 1, cor)
    T.rect(4, 1, 1, 3, cor)
    T.rect(3, 3, 1, 1, cor)
    T.rect(2, 5, 2, 2, sombra)
    return T.im


# ------------------------------------------------------------------ faixas (desenhadas uma vez por período)
def _topo(T, ys, cor):
    """Linha de contorno de 1 px acompanhando a curva ys[x], sem buracos nos degraus."""
    for x in range(len(ys)):
        lo, hi = min(ys[x - 1], ys[x]), max(ys[x - 1], ys[x])
        T.rect(x, lo - 1, 1, hi - lo + 1, cor)


def faixa_ceu(c):
    T = Tela(W, CENA_H)
    cores = c["ceu"]
    n = len(cores)
    h = GY / n
    for i, cor in enumerate(cores):
        T.rect(0, int(i * h), W, int(h) + 2, cor)
    escada = "AABAABABBB"  # transição em degraus: as listras do escuro para o claro, como na referência
    for i in range(1, n):
        yb = int(i * h)
        for k, ch in enumerate(escada):
            T.rect(0, yb - 5 + k, W, 1, cores[i - 1] if ch == "A" else cores[i])
    return T.im


def faixa_nuvens(c):
    L = 640
    T = Tela(L, CENA_H)
    r = random.Random(11)
    circ, x = [], 0
    while x < L:
        circ.append((x, r.randrange(52, 60), r.randrange(10, 21)))
        x += r.randrange(15, 29)

    def topo(x):
        t = 56
        for cx, cy, rad in circ:
            dx = (x - cx + L // 2) % L - L // 2
            if abs(dx) < rad:
                t = min(t, cy - int(math.sqrt(rad * rad - dx * dx)))
        return t

    for x in range(L):
        y = topo(x)
        T.rect(x, y, 1, GY - y + 2, c["nuvem"])
    for cx in range(30, L, 97):  # nuvenzinhas soltas mais acima
        yy = 17 + (cx * 7) % 9
        T.ell(cx, yy + 2, cx + 17, yy + 8, c["nuvem"])
        T.ell(cx + 4, yy, cx + 12, yy + 7, c["nuvem"])
    return T.im


def faixa_montanhas(c):
    L = 608
    T = Tela(L, CENA_H)

    def y1(x):
        a = 2 * math.pi * x / L
        return int(58 + 8 * math.sin(3 * a + .5) + 3.5 * math.sin(7 * a + 2.1) + 1.5 * math.sin(13 * a + 4))

    def y2(x):
        a = 2 * math.pi * x / L
        return y1(x) + int(9 + 5 * math.sin(5 * a + 1) + 2 * math.sin(11 * a))

    ys = [y1(x) for x in range(L)]
    for x in range(L):
        T.rect(x, ys[x], 1, GY - ys[x] + 1, c["mont"])
        T.rect(x, y2(x), 1, GY - y2(x) + 1, c["mont2"])
    _topo(T, ys, c["ol"])
    return T.im


def faixa_colinas(c):
    L = 640
    T = Tela(L, CENA_H)
    corpo = mix(c["mont"], c["ol"], .28)

    def y(x):
        a = 2 * math.pi * x / L
        return int(76 + 4 * math.sin(9 * a + .3) + 2 * math.sin(17 * a + 1.1))

    ys = [y(x) for x in range(L)]
    for cx in range(20, L, 107):  # cactos de fundo, sem contorno
        T.put(cacto_longe(c, corpo), cx, ys[(cx + 3) % L] - 9)
    for x in range(L):
        T.rect(x, ys[x], 1, GY - ys[x] + 1, corpo)
    _topo(T, ys, mix(c["ol"], corpo, .2))
    return T.im


def faixa_chao(c):
    L = L_CHAO
    T = Tela(L, CENA_H)
    r = random.Random(5)

    def degraus(n, vmax):
        saida = []
        while len(saida) < n:
            saida += [r.randrange(0, vmax + 1)] * r.randrange(2, 5)
        return saida[:n]

    z1, z2 = degraus(L, 2), degraus(L, 2)
    T.rect(0, GY - 1, L, 1, c["ol"])
    for x in range(L):
        gb = GY + 6 + z1[x]
        T.rect(x, GY, 1, gb - GY, c["grama"])
        T.rect(x, gb, 1, 2, c["ol"])
        sp = GY + 11 + z2[x]
        T.rect(x, gb + 2, 1, sp - gb - 2, c["terra"])
        T.rect(x, sp, 1, CENA_H - sp, c["terra2"])
    for _ in range(26):
        x, y = r.randrange(L), r.randrange(GY + 12, CENA_H - 1)
        T.rect(x, y, r.choice((1, 2, 2, 3)), 1, c["pedra"])
    for x in range(5, L, 41):  # tufos secos no capim
        T.rect(x, GY - 3, 1, 2, c["cacto2"])
        T.rect(x + 2, GY - 4, 1, 3, c["cacto2"])
        T.rect(x + 4, GY - 3, 1, 2, c["cacto2"])
    return T.im


def faixa_cactos(c):
    T = Tela(L_CHAO, CENA_H)
    for cx, tipo in POS_CACTOS:
        im = cacto(c, tipo)
        T.put(im, cx - im.width // 2, GY - im.height)
    return T.im


FAIXAS = {"ceu": faixa_ceu, "nuvens": faixa_nuvens, "montanhas": faixa_montanhas, "colinas": faixa_colinas,
          "chao": faixa_chao, "cactos": faixa_cactos}


def recorte(faixa, x):
    """Janela de W px da faixa, dando a volta no fim (a faixa é emendada)."""
    L = faixa.width
    x %= L
    if x + W <= L:
        return faixa.crop((x, 0, x + W, CENA_H))
    out = Image.new("RGBA", (W, CENA_H), TRANSPARENTE)
    out.paste(faixa.crop((x, 0, L, CENA_H)), (0, 0))
    out.paste(faixa.crop((0, 0, x + W - L, CENA_H)), (L - x, 0))
    return out


# ------------------------------------------------------------------ camadas que mudam a cada quadro
def astros(per, c, t):
    T = Tela(W, CENA_H)
    if per == "manha":
        cx, cy, r = W - 46, 27, 8
        for k in range(8):
            a = k * math.pi / 4 + (math.pi / 8 if (t // 5) % 2 else 0)
            T.rect(int(cx + math.cos(a) * 13), int(cy + math.sin(a) * 13), 2, 2, c["sol"])
        T.ell(cx - r, cy - r, cx + r, cy + r, c["sol2"])
        T.ell(cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1, c["sol"])
    elif per == "tarde":
        cx, cy, r = 205, 34, 12
        T.ell(cx - r, cy - r, cx + r, cy + r, c["sol2"])
        T.ell(cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2, c["sol"])
    else:
        rnd = random.Random(2)
        for k in range(46):
            sx, sy = rnd.randrange(2, W - 2), rnd.randrange(HUD_H + 2, 52)
            if (t // 3 + k) % 6:
                T.px(sx, sy, hx("#fff1c9") if k % 3 else hx("#8aa0d8"))
                if k % 7 == 0:
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        T.px(sx + dx, sy + dy, hx("#8aa0d8"))
        cx, cy = W - 46, 28
        T.ell(cx - 9, cy - 9, cx + 9, cy + 9, c["sol"])
        T.ell(cx - 3, cy - 12, cx + 14, cy + 5, TRANSPARENTE)  # recorte do crescente
        T.px(cx - 4, cy + 2, c["sol2"])
        T.px(cx - 5, cy + 3, c["sol2"])
    return T.im


def passaros(t):
    """Silhuetas pretas batendo asa: um bando indo para a direita, outro para a esquerda e um solitário."""
    T = Tela(W, CENA_H)
    volta = W + 60
    for x0, y0, v, fase in BANDO:
        x = int((x0 + v * t) % volta) - 30
        y = y0 + int(round(math.sin(t / 7 + fase) * 1.5))
        T.spr(x, y, PASSARO[(t // 3 + fase) % 4], {"#": PRETO_PASSARO})
    return T.im


def pose_do_dino(t):
    """(altura do pulo, no ar?): o dino pula quando o centro de um cacto está a 30 px à frente e pousa 30 px depois."""
    centro = DINO_X + 11
    meia = 3 * SALTO_Q // 2
    for cx, _ in POS_CACTOS:
        delta = (cx - 3 * t - centro + L_CHAO // 2) % L_CHAO - L_CHAO // 2
        if -meia <= delta <= meia:
            u = (meia - delta) / (2 * meia)
            return int(round(4 * SALTO_H * u * (1 - u))), True
    return 0, False


def css(cor):
    return "#%02x%02x%02x" % cor[:3]


# ------------------------------------------------------------------ o tema
class Dino(TemaPixel):
    id = "dino"
    nome = "Dino do deserto"
    descricao = "Um dinossauro corre num deserto que rola e pula os cactos. Muda de manhã, tarde e noite."
    cores_balao = ("#fcecd1", "#2c1d2e", "#2c1d2e")
    animacao_ms = 100

    def __init__(self):
        self._faixas = {}
        self._sprites = {}
        self._fundos = {}
        self._ui = (None, None)

    def paleta(self, per):
        c = P[per]
        verde = mix(c["dino"], c["ol"], .35)
        return dict(texto=c["tinta"], dim=c["dim"], ok=c["ok"], acc=verde, sel_fundo=verde, sel_texto=c["papel"],
                    linha=c["papel2"], hover=verde)

    def moldura_dialogo(self, T, w, h, titulo, per, hover_fechar):
        c = P[per]
        T.rect(0, 0, w, h, c["ol"])
        T.rect(1, self.TITULO_H, w - 2, h - self.TITULO_H - 1, c["papel"])
        T.rect(1, h - 3, w - 2, 2, c["papel2"])
        T.cantos(0, 0, w, h)
        T.texto(8, 5, titulo, c["papel"])
        T.put(icone("fechar", c["seta"] if hover_fechar else c["papel"]), w - 12, 5)
        return (w - 16, 1, w - 2, self.TITULO_H)

    # --- geometria: o cartão cresce com o número de linhas ---
    @staticmethod
    def _geo(e):
        n = max(len(e.topicos) + (1 if e.extra else 0), 3)
        cy = CENA_H + 2
        ch = 11 * n + 8
        ey = cy + ch + 4
        sty = ey + 16 + 4
        return dict(n=n, cy=cy, ch=ch, ey=ey, sty=sty, H=sty + 7 + 7)

    # --- cache ---
    def _faixa(self, per, nome):
        if (per, nome) not in self._faixas:
            self._faixas[(per, nome)] = FAIXAS[nome](P[per])
        return self._faixas[(per, nome)]

    def _sprite(self, per, pose, pisca):
        k = (per, pose, pisca)
        if k not in self._sprites:
            self._sprites[k] = dino(P[per], pose, pisca)
        return self._sprites[k]

    def _fundo(self, per, H):
        """Terra abaixo do cenário, com pedrinhas fixas (o cartão e o campo ficam por cima)."""
        if (per, H) not in self._fundos:
            c = P[per]
            T = Tela(W, H)
            T.rect(0, 0, W, H, c["terra2"])
            rnd = random.Random(9)
            for _ in range(40):
                T.rect(rnd.randrange(W), rnd.randrange(CENA_H + 1, H - 1), rnd.choice((1, 2, 3)), 1,
                       mix(c["terra2"], c["pedra"], .55))
            self._fundos[(per, H)] = T.im
        return self._fundos[(per, H)]

    # --- o cenário, de trás para a frente ---
    def _cenario(self, per, t):
        c = P[per]
        img = self._faixa(per, "ceu").copy()
        img.alpha_composite(astros(per, c, t))
        img.alpha_composite(recorte(self._faixa(per, "nuvens"), int(VEL["nuvens"] * t)))
        img.alpha_composite(passaros(t))
        img.alpha_composite(recorte(self._faixa(per, "montanhas"), int(VEL["montanhas"] * t)))
        img.alpha_composite(recorte(self._faixa(per, "colinas"), int(VEL["colinas"] * t)))
        img.alpha_composite(recorte(self._faixa(per, "chao"), 3 * t))
        img.alpha_composite(recorte(self._faixa(per, "cactos"), 3 * t))
        alt, no_ar = pose_do_dino(t)
        pose = "pulo" if no_ar else "a" if (t // 2) % 2 == 0 else "b"
        sp = self._sprite(per, pose, (t % 60) in (0, 1))
        D = Tela(W, CENA_H)
        D.put(sp, DINO_X - 1, GY - sp.height - alt)
        if not no_ar:  # poeirinha atrás dos pés
            for k in range(3):
                D.px(DINO_X - 3 - k * 2 - (t % 2), GY - 1 - ((t // 2 + k) % 3), c["poeira"])
        img.alpha_composite(D.im)
        return img

    # --- HUD e cartão (só mudam com o estado) ---
    def _interface(self, e, g):
        c = P[e.periodo]
        T = Tela(W, g["H"])
        regs = []
        T.rect(0, 0, W, HUD_H, c["ol"])
        titulo = f"DIÁRIO · {DIAS_SEMANA[e.dia.weekday()].upper()} {e.dia:%d/%m}"
        T.texto(6, 3, titulo, c["papel"])
        if not e.eh_hoje:  # etiqueta "Hoje" ao lado da data
            caixa = (6 + largura(titulo) + 6, 1, 6 + largura(titulo) + 33, 11)
            T.rect(caixa[0], caixa[1], 27, 10, c["ol"])
            T.rect(caixa[0] + 1, caixa[1] + 1, 25, 8, c["seta"] if e.hover == "hoje" else c["papel"])
            T.texto(caixa[0] + 3, caixa[1] + 2, "Hoje", c["tinta"])
            regs.append(Regiao("hoje", caixa, DICAS["hoje"]))
        x = W - 4
        for nome in reversed(BOTOES):
            x -= 8
            ic = icone(nome, c["seta"] if e.hover == nome else c["papel"])
            T.put(ic, x + (8 - ic.width) // 2, 6 - ic.height // 2 + 1)
            regs.append(Regiao(nome, (x, 0, x + 8, HUD_H), DICAS[nome]))
        regs.append(Regiao("arrastar", (0, 0, W, HUD_H), "", ""))
        # cartão de papel com a lista
        cy, ch = g["cy"], g["ch"]
        T.rect(6, cy, W - 12, ch, c["ol"])
        T.rect(7, cy + 1, W - 14, ch - 2, c["papel"])
        T.rect(7, cy + ch - 3, W - 14, 2, c["papel2"])
        T.cantos(6, cy, W - 12, ch)
        linhas = list(e.topicos) or [("Nada registrado neste dia.", "aviso")]
        verde, sombra = mix(c["ok"], c["ol"], .1), mix(c["ok"], c["ol"], .45)
        for i, (txt, tipo) in enumerate(linhas):
            y = cy + 6 + i * 11
            cor = {"manual": c["ok"], "aviso": c["dim"], "resumir": c["dim"]}.get(tipo, c["tinta"])
            if e.hover == f"linha:{i}":
                T.rect(9, y - 2, W - 18, 11, c["papel2"])
            T.put(mini_cacto(*((c["dim"], c["dim"]) if tipo in ("aviso", "resumir") else (verde, sombra))), 12, y - 1)
            curto = cortar(txt, W - 40)
            T.texto(22, y, curto, cor)
            if tipo == "resumir":
                r = botao_resumir(T, 22 + largura(curto) + 6, y, e, verde, c["tinta"])
                if r:
                    regs.append(r)
            regs.append(Regiao(f"linha:{i}", (6, y - 2, W - 6, y + 9), txt if curto != txt else "", ""))
        if e.extra:
            T.texto(22, cy + 6 + len(linhas) * 11, f"… e mais {e.extra}", c["dim"])
        # campo de lançamento: o Entry do Tk fica por cima da caixa escura
        T.rect(6, g["ey"], W - 12, 16, c["ol"])
        T.rect(7, g["ey"] + 1, W - 14, 14, c["papel2"])
        T.rect(8, g["ey"] + 2, W - 16, 12, c["ol"])
        T.texto(12, g["ey"] + 5, ">", c["dino"])
        campo = (22, g["ey"] + 3, W - 10, g["ey"] + 13)
        # status (na terra) e contador de tópicos
        msg = e.status if e.status and e.status_tipo != "dica" else "Enter lança · 1h30 reunião @CS"
        cor = {"ok": c["grama"], "info": c["seta"], "erro": hx("#ff8a7a")}.get(e.status_tipo, mix(c["papel2"], c["terra2"], .2))
        T.texto(8, g["sty"], cortar(msg, W - 52), cor)
        T.put(mini_cacto(c["cacto"], c["cacto2"]), W - 33, g["sty"] - 1)
        T.texto(W - 24, g["sty"], f"x{min(len(e.topicos), 99):02d}", c["papel"])
        return T.im, regs, campo

    def quadro(self, e: Estado, t: int) -> Quadro:
        g = self._geo(e)
        chave = (e.dia, tuple(e.topicos), e.extra, e.status, e.status_tipo, e.hover, e.periodo, e.eh_hoje)
        if self._ui[0] != chave:
            self._ui = (chave, self._interface(e, g))
        ui, regs, campo = self._ui[1]
        c = P[e.periodo]
        img = self._fundo(e.periodo, g["H"]).copy()
        img.alpha_composite(self._cenario(e.periodo, t))
        img.alpha_composite(ui)
        Z = self.Z
        imagem = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
        regioes = [Regiao(r.nome, tuple(v * Z for v in r.caixa), r.dica, r.cursor) for r in regs]
        return Quadro(imagem, regioes, tuple(v * Z for v in campo),
                      dict(bg=css(c["ol"]), fg=css(c["papel"]), cursor=css(c["papel"]), fonte=("Consolas", 10)),
                      False, css(c["terra2"]))
