"""Tema Argonath: as estátuas de Isildur e Anárion guardando o rio Anduin, com o quadro do dia entre elas.

A cena segue a pintura de referência (arte/referencias/argonath): as duas estátuas e os penhascos ficam nas laterais, no
meio vai uma tábua de pedra com a lista do dia, acima o céu com nuvens e abaixo o rio com três canoas em silhueta.
As paredes de pedra vêm do recurso diario/recursos/argonath.png (a referência sem o céu, gerada por
arte/referencias/argonath/preparar_paredes.py); o resto é desenhado aqui. Céu, nuvens, rio e canoas usam blocos de 2x2
pixels de arte, como a grade da referência; texto e tábua usam o pixel normal. O tronco das estátuas estica ou encolhe
com o tamanho da lista, para a cena acompanhar a altura da janela.

Camadas, de trás para frente: céu (astros e nuvens animados) + tábua de pedra e interface + paredes + rio com canoas.
"""
import math
import random
from datetime import date
from pathlib import Path

from PIL import Image, ImageChops

from ..pixel import TRANSPARENTE, Tela, contorno, cortar, hx, icone, largura, mix
from .base import ATUALIZAR, BOTOES, DIAS_SEMANA, DICAS, RESUMINDO, RESUMIR, Estado, Quadro, Regiao
from .pixeltema import TemaPixel, botao_resumir

R = 2  # pixels de arte por pixel da grade da referência
LX = (4, 54)  # colunas da referência que formam a parede da esquerda (até 47 depois da linha 88, onde começa a névoa)
RX = (90, 150)
LINHAS_TOPO, LINHAS_MEIO, LINHAS_BASE = 72, (72, 128), (128, 148)  # faixas da referência; só a do meio estica
LW, RW, CW = (LX[1] - LX[0]) * R, (RX[1] - RX[0]) * R, 196  # paredes e vão entre elas, em pixels de arte
W = LW + CW + RW
Y0, BW, BX = 92, 204, LW - 4  # topo da tábua, largura e x (4 px atrás de cada parede)
RIO, FOLGA = 44, 3  # altura do rio; vão entre a tábua e o rio
DICA_CURTA = "1h30 reunião @CS · Enter lança"

GRADE = {"manha": (255, 255, 255), "tarde": (255, 196, 152), "noite": (92, 112, 178)}
OL = hx("#1f252b")
PEDRA = dict(s1=hx("#5c666e"), s2=hx("#3a4249"), s3=hx("#8a929a"), hl=hx("#d8d4c0"))
SIL = {"manha": hx("#1e2a34"), "tarde": hx("#2a1f2e"), "noite": hx("#0b1018")}
CEU = {"manha": ("#7aa2aa", "#90b6bb", "#aacfd2"), "tarde": ("#4c5c8e", "#d6807a", "#ffc47c"),
       "noite": ("#0a1130", "#16255a", "#32447c")}
NUVEM = {"manha": ("#f6ecd6", "#e4cda7", "#d5b482"), "tarde": ("#ffe6c8", "#f4b48a", "#d9807c"),
         "noite": ("#5c6c9c", "#46557f", "#34426a")}
UI = {
    "manha": dict(paper=hx("#e8dcc0"), paper2=hx("#d3c5a2"), ink=hx("#2a2d36"), dim=hx("#7a7568"), ok=hx("#2f7a46"),
                  acc=hx("#7a2630"), slate=hx("#2b3038"), stxt=hx("#e8e2cc")),
    "tarde": dict(paper=hx("#f0d9b2"), paper2=hx("#dcc08f"), ink=hx("#33262f"), dim=hx("#86705f"), ok=hx("#4a7a26"),
                  acc=hx("#7a2630"), slate=hx("#352a38"), stxt=hx("#ffe9d2")),
    "noite": dict(paper=hx("#d6cdb4"), paper2=hx("#bfb599"), ink=hx("#1f2338"), dim=hx("#666b84"), ok=hx("#2a8a55"),
                  acc=hx("#7a2e3a"), slate=hx("#1a2030"), stxt=hx("#d6e0f4")),
}
STATUS_COR = {"dica": None, "ok": {"manha": hx("#a8f0b8"), "tarde": hx("#b8f0a0"), "noite": hx("#8ee8a8")},
              "info": {"manha": hx("#a8cdfa"), "tarde": hx("#b0c8f8"), "noite": hx("#8ab4f0")},
              "erro": {"manha": hx("#ffa8a0"), "tarde": hx("#ffa8a0"), "noite": hx("#ff8f8f")}}
# (largura, altura, x, y, velocidade em pixels de arte por quadro), em pixels da grade da referência
NUVENS = ((30, 11, 150, 44, .30), (22, 8, 250, 12, .20), (16, 6, 40, 72, .14), (26, 9, 340, 60, .24))
# canoas: (largura do desenho, x do centro, linha da água em que o casco termina, tripulação), em pixels da grade. A
# tripulação tem uma letra de FIGURAS por pessoa, da popa (esquerda) para a proa: as canoas andam para a direita. Duas levam
# um humano e dois hobbits; a terceira, o elfo e o anão.
CANOAS = ((29, 60, 17, "HBB"), (23, 100, 12, "EA"), (29, 138, 14, "BBH"))

# efeitos de clique: duração em quadros (140 ms cada). Os dois últimos são segredos: sem dica e sem cursor de mão.
EFEITOS = {"isildur": 30, "anarion": 30, "canoa0": 22, "canoa1": 22, "canoa2": 22, "ceu": 26, "agua": 26,
           "nuvem0": 18, "nuvem1": 18, "nuvem2": 18, "nuvem3": 18, "gollum": 60, "orcs": 34}
# rosto, olhos, mão erguida e ombro de cada estátua, na grade da referência (a da esquerda é Isildur)
OLHOS = {"isildur": ((31, 31), (37, 31)), "anarion": ((115, 23), (120, 23))}
MAOS = {"isildur": (48, 22), "anarion": (134, 20)}
OMBROS = {"isildur": (30, 50), "anarion": (112, 46)}
CLIQUE_ROSTO = {"isildur": (25, 20, 42, 41), "anarion": (109, 14, 128, 40)}  # elmo e rosto: a única parte clicável
# linhas da cabeça na grade da referência: topo do elmo, fim da parte que se move inteira (a boca) e fim do pescoço, onde o
# movimento já se desfez
CABECA = {"isildur": (18, 38, 44), "anarion": (12, 29, 34)}
GIRO = (5, 2)  # quanto a cabeça anda para o lado dos barcos e desce para olhá-los, em pixels de arte
ORCS_PASSO, ORCS_X1 = 4.4, 30  # velocidade (pixels de arte por quadro) e x em que somem atrás da estátua

_REF = []
_CACHE = {}


def referencia():
    if not _REF:
        _REF.append(Image.open(Path(__file__).parent.parent / "recursos" / "argonath.png").convert("RGBA"))
    return _REF[0]


def grade(im, per):
    """Tinge a camada para a hora do dia (multiplica a cor, o que preserva o contraste entre os tons)."""
    if per == "manha":
        return im
    rgb = ImageChops.multiply(im.convert("RGB"), Image.new("RGB", im.size, GRADE[per])).convert("RGBA")
    rgb.putalpha(im.getchannel("A"))
    return rgb


def ampliar(im):
    return im.resize((im.width * R, im.height * R), Image.NEAREST)


# ------------------------------------------------------------------ céu e nuvens
def ceu(per, h, w=W):
    """Céu em degraus com riscos horizontais, como na referência; devolve uma imagem w x h."""
    a, b, c = map(hx, CEU[per])
    T = Tela(w // R, h // R + 1)
    bayer = ((0, 2), (3, 1))
    n = T.h
    zonas = ((0, .22, a, a), (.22, .42, a, b), (.42, .6, b, b), (.6, .8, b, c), (.8, 1.01, c, c))
    for z0, z1, ca, cb in zonas:
        for y in range(int(z0 * n), min(n, int(z1 * n))):
            f = (y - z0 * n + .5) / max(1, (z1 - z0) * n)
            for x in range(T.w):
                T.px(x, y, cb if f > (bayer[y % 2][x % 2] + .5) / 4 else ca)
    r = random.Random(7)
    for _ in range(70):  # riscos: trechos horizontais um pouco mais claros ou mais escuros
        y, x, comp = r.randrange(n), r.randrange(T.w), r.randint(6, 34)
        base = T.im.getpixel((min(x, T.w - 1), y))
        cor = mix(base, hx("#ffffff"), .13) if r.random() < .5 else mix(base, hx("#10203a"), .1)
        T.rect(x, y, comp, 1, cor)
    return ampliar(T.im).crop((0, 0, w, h))


def nuvem(wr, hr, per, semente):
    """Nuvem de base reta e pontas arredondadas, em blocos da grade da referência: luz no alto, sombra embaixo."""
    luz, meio, sombra = map(hx, NUVEM[per])
    r = random.Random(semente)
    T = Tela(wr, hr)
    n = max(3, wr // 6)
    rx = max(3, round(wr / (n + 1) * 1.25))
    blobs = []
    for i in range(n):
        f = i / (n - 1)
        alt = max(2, round(hr * (.5 + .5 * math.sin(math.pi * f)) * r.uniform(.85, 1.1)))
        blobs.append((round(rx + f * (wr - 1 - 2 * rx)), alt))
    for cx, alt in blobs:  # elipses centradas na base: o meio fica na última linha, com a base reta
        T.ell(cx - rx, hr - 1 - alt, cx + rx, hr - 1 + alt, meio)
    for cx, alt in blobs:
        T.ell(cx - rx + 1, hr - 1 - alt + 1, cx + rx - 2, hr - 1 + alt - 2, luz)
    pix = T.im.load()
    for xx in range(wr):
        ys = [yy for yy in range(hr) if pix[xx, yy][3]]
        if ys:
            pix[xx, ys[-1]] = sombra
            if len(ys) > 3 and pix[xx, ys[-1] - 1][3]:
                pix[xx, ys[-1] - 1] = mix(sombra, meio, .45)
    return ampliar(T.im)


def astros(per, t):
    """Sol baixo (tarde) ou lua com estrelas (noite); a manhã é de céu coberto, como na referência."""
    T = Tela(W // R, Y0 // R + 8)
    if per == "tarde":
        for k, a in ((14, 36), (10, 60)):
            T.d.ellipse([86 - k, 34 - k, 86 + k, 34 + k], fill=(255, 190, 110, a))
        T.ell(79, 27, 93, 41, hx("#ffd37a"))
        T.ell(80, 28, 91, 38, hx("#fff0b8"))
    elif per == "noite":
        r = random.Random(5)
        for k in range(46):
            sx, sy = r.randrange(2, W // R - 2), r.randrange(2, 52)
            if (t + k) % 7:
                T.px(sx, sy, hx("#fff1c9") if k % 3 else hx("#9fb4ec"))
        T.ell(84, 14, 98, 28, hx("#f6efcc"))
        T.ell(84, 14, 96, 26, hx("#fff8de"))
        for cx, cy in ((88, 19), (92, 24), (94, 17)):
            T.px(cx, cy, hx("#d8cfa0"))
    return ampliar(T.im)


def nuvens_em(T, per, t, ef=None):
    """Desenha as nuvens e devolve a caixa de cada uma; a que recebeu um clique treme e solta chuva."""
    ef = ef or {}
    caixas = []
    for i, (wr, hr, x0, y, vel) in enumerate(NUVENS):
        k = ("nuvem", per, i)
        if k not in _CACHE:
            _CACHE[k] = nuvem(wr, hr, per, 20 + i)
        n = _CACHE[k]
        x = int((x0 + vel * t) % (W + 2 * n.width)) - n.width
        f = ef.get(f"nuvem{i}")
        T.put(n, x + ((1 if f % 2 else -1) if f is not None else 0), y)
        if f is not None:
            chuva(T, per, f, x, y, n.width, n.height)
        caixas.append((x, y, x + n.width, y + n.height))
    return caixas


# ------------------------------------------------------------------ paredes de pedra
def parede(per, meio):
    """As duas paredes com `meio` linhas da referência no tronco (o resto fica como está); em pixels de arte."""
    ref = referencia()
    linhas = list(range(LINHAS_TOPO)) + [LINHAS_MEIO[0] + i * (LINHAS_MEIO[1] - LINHAS_MEIO[0]) // meio
                                         for i in range(meio)] + list(range(*LINHAS_BASE))
    esq = Image.new("RGBA", (LX[1] - LX[0], len(linhas)), TRANSPARENTE)
    dire = Image.new("RGBA", (RX[1] - RX[0], len(linhas)), TRANSPARENTE)
    for j, r in enumerate(linhas):
        xmax = LX[1] if r < 88 else 47  # a partir daqui a névoa do vão começa a aparecer na beirada
        esq.paste(ref.crop((LX[0], r, xmax, r + 1)), (0, j))
        borda = esq.getpixel((xmax - LX[0] - 1, j))
        if sum(borda[:3]) > 450:  # névoa clara na beirada: usa a pedra escura
            borda = hx("#5c666e")
        for x in range(xmax - LX[0], LX[1] - LX[0]):  # a beirada se repete até a largura da parede: fica atrás da tábua
            esq.putpixel((x, j), borda)
        dire.paste(ref.crop((RX[0], r, RX[1], r + 1)), (0, j))
    return grade(ampliar(esq), per), grade(ampliar(dire), per)


# ------------------------------------------------------------------ rio e canoas
def faixa_do_rio(per, w=W, alt=RIO):
    """Uma faixa larga e periódica de água: cada linha tem os seus riscos de reflexo e se move na sua velocidade."""
    S, h = 256, alt // R
    base, escuro, claro, brilho = hx("#5f8f9c"), hx("#3f6672"), hx("#a3c9cf"), hx("#e4f0ee")
    T = Tela(S + w // R, h)
    r = random.Random(11)
    for y in range(h):
        fundo = mix(mix(claro, base, min(1, y / 4)), escuro, max(0, (y - 4) / (h - 4)) * .75)
        T.rect(0, y, T.w, 1, fundo)
    for y in range(3, h):
        for _ in range(r.randint(6, 10)):
            x, comp = r.randrange(S), r.randint(2, 6)
            cor = mix(base, brilho, .55) if r.random() < .55 else mix(base, escuro, .55)
            for xx in (x, x + S):
                T.rect(xx, y, comp, 1, cor)
    return T.im


CANOA_ALT = 11  # linhas do desenho: até 7 de tripulante (o elfo) acima do casco (3 linhas), mais uma de folga embaixo
# tripulantes em silhueta (linhas de cima para baixo). Todos têm a cabeça de 2x2 sobre ombros de duas cabeças ou mais, com um
# degrau entre os dois para a cabeça não sumir no corpo; a diferença entre eles está na altura e na largura do tronco: o elfo é
# o mais alto e esguio (com a ponta do capuz), o humano é alto e de ombros largos, o anão é baixo e o mais largo e o hobbit é o
# menor
FIGURAS = {
    "E": [".#..", ".##.", ".##.", "####", "####", "####", "####"],
    "H": [".##..", ".##..", "####.", "#####", "#####", "#####"],
    "A": ["..##..", "..##..", "######", "######", "######"],
    "B": [".##.", ".##.", "####", "####"],
}


def canoa(L, quem, remo):
    """Canoa em silhueta com a tripulação `quem`, na grade da referência (L = largura do desenho); o remo de cada um
    alterna de lado a cada três quadros."""
    k = ("canoa", L, quem, bool(remo))
    if k not in _CACHE:  # só há 3 canoas x 2 poses: desenhar a cada quadro era o que mais pesava nas canoas
        branco = hx("#ffffff")
        T = Tela(L, CANOA_ALT)
        p = CANOA_ALT - 5  # linha das pontas do casco, onde os tripulantes sentam; abaixo dela vêm as três do casco
        T.px(0, p, branco)
        T.px(L - 1, p, branco)
        T.rect(0, p + 1, 2, 1, branco)
        T.rect(L - 2, p + 1, 2, 1, branco)
        T.rect(4, p + 1, L - 8, 1, branco)
        T.rect(1, p + 2, L - 2, 1, branco)
        T.rect(2, p + 3, L - 4, 1, branco)
        passo = (L - 8) / len(quem)
        for n, letra in enumerate(quem):
            fig = FIGURAS[letra]
            x0 = round(4 + passo * (n + .5)) - len(fig[0]) // 2
            T.spr(x0, p + 1 - len(fig), fig, {"#": branco})
            if remo:
                T.px(x0 - 1, p + 1, branco)
                T.px(x0 - 2, p + 2, branco)
            else:
                T.px(x0 + len(fig[0]), p + 1, branco)
                T.px(x0 + len(fig[0]) + 1, p + 2, branco)
        _CACHE[k] = T.im
    return _CACHE[k]


def agua(per, t, linhas, w=W, alt=RIO, ax=84):
    """A água no quadro `t` (na grade da referência), com o reflexo do astro."""
    k = ("faixa", per, w, alt)
    if k not in _CACHE:
        _CACHE[k] = faixa_do_rio(per, w, alt)
    faixa = _CACHE[k]
    T = Tela(w // R, linhas)
    for y in range(alt // R):
        off = int(t * (.10 + .014 * y)) % 256
        T.im.paste(faixa.crop((off, y, off + T.w, y + 1)), (0, y))
    if per != "manha":  # reflexo do sol baixo ou da lua em riscos que tremem
        for y in range(3, alt // R, 2):
            T.rect(ax + int(2 * math.sin(t / 3 + y)), y, 4 - y // 6, 1,
                   hx("#ffd37a") if per == "tarde" else hx("#e8e4c0"))
    return T


def canoas(per, t, ef, w=W, alt=RIO, pos=CANOAS):
    """As três canoas balançando (alt pixels de altura). Com clique, os remadores remam a cada quadro, a canoa
    avança e volta, deixa uma marola maior e levanta respingos."""
    T = Tela(w // R, alt // R)
    sil = SIL[per]
    for i, (L, cx, linha, quem) in enumerate(pos):
        f = ef.get(f"canoa{i}")
        bob = int(1.5 + 1.4 * math.sin(2 * math.pi * (t / 16 + i / 3))) - 1
        c = canoa(L, quem, t % 2 if f is not None else (t // 3 + i) % 2)
        cor = Image.new("RGBA", c.size, sil)
        cor.putalpha(c.getchannel("A"))
        dx = round(9 * math.sin(math.pi * f / EFEITOS[f"canoa{i}"])) if f is not None else 0
        T.put(cor, cx - c.width // 2 + dx, linha - c.height + 1 + bob)
        for j, d in enumerate((-L // 2 - 3, -L // 2 - 7, -L // 2 - 11)):  # marola atrás da canoa
            if j == 2 and f is None:
                continue
            if (t // 2 + j + i) % 3:
                T.rect(cx + d + dx, linha + 1 + j, 4 - j + (2 if f is not None else 0), 1, hx("#e4f0ee"))
        if f is not None:  # respingos dos remos
            r = random.Random(f * 7 + i)
            for _ in range(3):
                T.px(cx + dx + r.randint(-L // 2 - 2, L // 2 + 2), linha - r.randint(0, 3) + bob, hx("#e4f0ee"))
    return tinge_agua(ampliar(T.im), per)


def tinge_agua(im, per):
    """A água escurece com a hora; na tarde puxa para o rosado do poente antes."""
    alpha = im.getchannel("A")
    if per == "noite":
        im = ImageChops.multiply(im.convert("RGB"), Image.new("RGB", im.size, GRADE[per])).convert("RGBA")
    elif per == "tarde":
        im = Image.blend(im.convert("RGB"), Image.new("RGB", im.size, (214, 128, 118)), .42).convert("RGBA")
    im.putalpha(alpha)
    return im


def rio(per, t, w=W, alt=RIO, ax=84):
    """O rio de margem a margem, sem as canoas: névoa junto das paredes e água em movimento."""
    im = tinge_agua(ampliar(agua(per, t, alt // R, w, alt, ax).im), per)
    k = ("nevoa", per, w)  # névoa clara na linha da água, para as paredes entrarem no rio; não depende de t
    if k not in _CACHE:
        nevoa = Tela(w, 8)
        bay = ((0, 2), (3, 1))
        cor = hx("#3a4a78") if per == "noite" else mix(hx("#d8e4e0"), hx("#ffe0b8"), .5 if per == "tarde" else 0)
        for y in range(8):
            for x in range(w):
                if (8 - y) / 8 * .85 > (bay[(y // 2) % 2][(x // 2) % 2] + .5) / 4:
                    nevoa.px(x, y, cor)
        _CACHE[k] = nevoa.im
    im.alpha_composite(_CACHE[k])
    return im


# ------------------------------------------------------------------ efeitos de clique
def envelope(f, dur, sobe=.15, desce=.15):
    """0 -> 1 -> 0 ao longo do efeito: sobe nos primeiros quadros, segura e desce nos últimos."""
    return max(0.0, min(1.0, f / (dur * sobe), (dur - 1 - f) / (dur * desce)))


def cor_da_hora(c, per):
    """A mesma multiplicação de `grade`, para uma cor só."""
    return tuple(c[i] * GRADE[per][i] // 255 for i in range(3)) + (255,)


def estrela4(T, x, y, cor, r=2):
    T.px(x, y, cor)
    for k in range(1, r + 1):
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            T.px(x + dx, y + dy, cor)


def chuva(T, per, f, x, y, w, h):
    """Fios de chuva embaixo da nuvem que recebeu o clique."""
    if f > EFEITOS["nuvem0"] - 4:
        return
    cor = hx("#7f98cc") if per == "noite" else hx("#aacfe0")
    for j in range(8):
        T.rect(x + 3 + j * (w - 8) // 7, y + h + (f * 3 + j * 7) % 38, 2, 4, cor)


def efeito_ceu(T, per, f):
    """Manhã: o sol rompe a nuvem com raios em leque. Tarde: o sol pulsa e faísca. Noite: estrela cadente e a lua cintila."""
    env = envelope(f, EFEITOS["ceu"], .25, .25)
    if per == "manha":
        ox, oy = 214, 22
        r = round(3 + 6 * env)
        T.ell(ox - r, oy - r, ox + r, oy + r, hx("#fff0b0"))
        T.ell(ox - r + 2, oy - r + 2, ox + r - 2, oy + r - 2, hx("#fffbe6"))
        for k in range(-5, 6):
            ang = math.radians(90 + k * 13)
            comp = round(72 * env)
            for s_ in range(r + 1, r + comp):
                if s_ % 2:
                    continue
                px_, py_ = round(ox + math.cos(ang) * s_), round(oy + math.sin(ang) * s_)
                cor = mix(hx("#fff6c8"), hx("#aacfd2"), s_ / (r + comp) * .8)
                T.rect(px_, py_, 2, 2, cor)
    elif per == "tarde":
        for dr, cor in ((16 + 16 * env, hx("#ffb870")), (23 + 20 * env, hx("#f09068"))):
            T.d.ellipse([172 - dr, 68 - dr, 172 + dr, 68 + dr], outline=cor)
        for k, (dx, dy) in enumerate(((-24, -14), (22, -18), (-18, 20), (26, 14))):
            if (f + k * 3) % 8 < 4:
                estrela4(T, 172 + dx, 68 + dy, hx("#fff4c0"), 2 if (f + k) % 2 else 1)
    else:
        if f < 16:
            u = f / 15
            hx_, hy = 330 - 210 * u, 4 + 72 * u
            for k in range(1, 36):
                T.rect(round(hx_ + k * .946), round(hy - k * .33), 2 if k < 20 else 1, 2 if k < 20 else 1,
                       mix(hx("#ffffff"), hx("#32447c"), k / 36))
            T.rect(round(hx_) - 1, round(hy) - 1, 3, 3, hx("#ffffff"))
        for k, (dx, dy) in enumerate(((-12, -10), (13, -6), (11, 12), (-10, 11))):
            if (f + k * 2) % 6 < 3:
                estrela4(T, 182 + dx, 42 + dy, hx("#ffffff"), 3 if (f + k) % 3 == 1 else 2)


def para_cena(nome, rx, ry, y0):
    """Ponto da grade da referência (coluna, linha) nas coordenadas da cena, para a estátua `nome`."""
    if nome == "isildur":
        return (rx - LX[0]) * R, y0 + ry * R
    return LW + CW + (rx - RX[0]) * R, y0 + ry * R


def giro(nome, f, linha):
    """(dx, dy) da cabeça da estátua na linha `linha` da parede (em pixels de arte) no quadro `f`: a cabeça inteira, do elmo à
    boca, anda para o lado do centro do rio e baixa um pouco, com aceleração e freio; no pescoço o movimento se desfaz até
    zero, e do ombro para baixo nada se move."""
    env = envelope(f, EFEITOS[nome], .25, .25)
    env = env * env * (3 - 2 * env)
    _topo, rigido, pescoco = (v * R for v in CABECA[nome])
    k = env * (1.0 if linha < rigido else max(0.0, 1 - (linha - rigido) / (pescoco - rigido)))
    return round(GIRO[0] * k) * (1 if nome == "isildur" else -1), round(GIRO[1] * k)


def _trechos_da_cabeca(s, y, x0, x1):
    """Os trechos opacos (primeira, última coluna) da cabeça na linha `y` da parede, entre x0 e x1: o que passa pelo meio da
    caixa e os soltos dentro dela (as pontas do elmo, com o céu entre elas). O que encosta na beira da caixa sem passar pelo
    meio (o penhasco atrás, o braço erguido) fica de fora."""
    trechos, x, meio = [], x0, (x0 + x1) // 2
    while x < x1:
        if s[x, y][3]:
            a = x
            while x < x1 and s[x, y][3]:
                x += 1
            if a <= meio <= x - 1 or (a > x0 and x < x1):
                trechos.append((a, x - 1))
        x += 1
    return trechos


def virar_cabeca(img, nome, f, ox=None):
    """A parede com a cabeça da estátua virada para os barcos (ver `giro`): elmo e rosto se deslocam juntos, sem deformar. Em
    cada linha só a cabeça sai do lugar; o que ela deixa descoberto vira céu, menos onde ela emenda no ombro ou no braço, que
    ficam como estavam; o lado para onde ela vai passa por cima do que houver ali. `ox` é a coluna da referência em que a imagem
    da parede começa (o padrão é a das paredes da janela). Serve às duas versões do tema: as duas paredes usam a mesma grade
    (2 pixels por linha da referência)."""
    if not envelope(f, EFEITOS[nome], .25, .25):
        return img
    if ox is None:
        ox = LX[0] if nome == "isildur" else RX[0]
    c = CLIQUE_ROSTO[nome]
    x0, x1 = (c[0] - ox) * R - 2, (c[2] - ox) * R + 2
    topo, _r, pescoco = (v * R for v in CABECA[nome])
    out = img.copy()
    s, o = img.load(), out.load()
    for y in range(topo, pescoco):
        dx, dy = giro(nome, f, y)
        if not (dx or dy):
            continue
        for a, b in _trechos_da_cabeca(s, y, x0, x1):  # tira a cabeça do lugar, menos onde ela emenda no ombro
            if (a > x0) if dx >= 0 else (b < x1 - 1):
                for x in range(a, b + 1):
                    o[x, y] = (0, 0, 0, 0)
        for a, b in _trechos_da_cabeca(s, y - dy, x0, x1):  # e a põe na posição nova
            for x in range(max(a, -dx), min(b + 1, img.width - dx)):
                o[x + dx, y] = s[x, y - dy]
    return out


def olhos_em(T, nome, f, y0):
    """Os olhos do elmo acendem num brilho pálido enquanto a estátua olha para os barcos."""
    if envelope(f, EFEITOS[nome], .2, .2) < .5:
        return
    for rx, ry in OLHOS[nome]:
        x, y = para_cena(nome, rx, ry, y0)
        dx, dy = giro(nome, f, ry * R)
        T.rect(x + dx, y + dy, 2, 2, hx("#e8f6ff"))
        T.px(x + dx - 1, y + dy, hx("#7fb8d8"))
        T.px(x + dx + 2, y + dy, hx("#7fb8d8"))


def poeira(T, nome, f, y0, per):
    """Pedrinhas e poeira que se soltam da mão erguida e do ombro da estátua e caem."""
    r = random.Random(nome)
    mx, my = para_cena(nome, *MAOS[nome], y0)
    sx, sy = para_cena(nome, *OMBROS[nome], y0)
    for k in range(18):
        ox, oy = (mx, my) if k < 9 else (sx, sy)
        ox += r.randint(-7, 7)
        cor = cor_da_hora(r.choice((hx("#a29c8e"), hx("#d8d8ca"), hx("#7a828c"))), per)
        age = f - r.randint(0, 10)
        lado = r.choice((-1, 1))
        if 0 <= age <= 18:
            tam = 2 if k % 2 == 0 else 1
            T.rect(round(ox + lado * age * .25), round(oy + .3 * age * age), tam, tam, cor)
    if f < 9:  # a nuvenzinha de pó da hora em que a pedra se solta
        for k in range(10):
            if (k + f) % 2:
                T.px(mx - 6 + r.randint(0, 12), my - 2 + r.randint(0, 6), cor_da_hora(hx("#d8d8ca"), per))


def agua_fx(per, f, w=W, alt=RIO):
    """Anéis que se abrem na água e um peixe que salta (na grade da referência)."""
    T = Tela(w // R, alt // R)
    for cx, cy, s0 in ((99, 14, 0), (66, 11, 5), (134, 12, 9)):
        a = f - s0
        r = 2 + a * 1.6
        if a < 0 or r > 28:
            continue
        T.d.ellipse([cx - r, cy - max(1, r * .32), cx + r, cy + max(1, r * .32)],
                    outline=mix(hx("#e4f0ee"), hx("#a3c9cf"), min(1, r / 28)))
    a = f - 3
    if 0 <= a <= 12:
        x, y = round(118 + a * 1.2), round(14 - 10 * math.sin(math.pi * a / 12))
        T.rect(x - 2, y, 4, 1, hx("#cfe0e6"))
        T.rect(x - 1, y - 1, 2, 1, hx("#6f8a96"))
        T.px(x - 3, y - (1 if a < 6 else 0), hx("#9fb6c0"))
    if a in (0, 1, 12, 13, 14):  # respingo na saída e na volta
        bx = 118 if a < 5 else 133
        for dx, dy in ((-2, -2), (2, -3), (0, -4), (3, -1), (-3, -1)):
            T.px(bx + dx, 15 + dy - (a % 3), hx("#e4f0ee"))
    return tinge_agua(ampliar(T.im), per)


def cume(img):
    """Altura do topo da rocha em cada coluna da parede (abaixo da cabeça da estátua), suavizada: o chão dos orcs."""
    a = img.getchannel("A").load()
    topo = [next((y for y in range(100, img.height) if a[x, y]), img.height) for x in range(img.width)]
    return [min(topo[max(0, x - 3):x + 4]) for x in range(img.width)]


def orc(frame, tipo):
    """Orc correndo para a direita, em silhueta: corpo curvado, focinho, braço com lança, espada ou tocha."""
    T = Tela(16, 15)
    c = hx("#ffffff")
    T.poly([(4, 5), (9, 4), (10, 9), (5, 10)], c)
    T.rect(8, 1, 4, 4, c)
    T.px(12, 3, c)
    T.px(7, 1, c)
    if frame:
        T.line([(5, 10), (2, 14)], c, 2)
        T.line([(9, 10), (12, 13)], c, 2)
    else:
        T.line([(5, 10), (8, 14)], c, 2)
        T.line([(9, 10), (6, 13)], c, 2)
    T.line([(9, 6), (13, 6)], c, 2)
    if tipo == 0:
        T.line([(11, 13), (15, 0)], c)
    elif tipo == 1:
        T.line([(13, 6), (15, 2)], c)
        T.px(14, 2, c)
    else:
        T.line([(13, 6), (13, 3)], c)
    return T.im


def orcs_em(T, per, f, topo, y0):
    """O bando de orcs correndo pelo alto do penhasco da esquerda até sumirem atrás da estátua."""
    sil = SIL[per]
    for i in range(7):
        x = round(-16 - 11 * i + ORCS_PASSO * f)
        pe = x + 7
        if pe >= ORCS_X1 or x < -16:
            continue
        o = orc((f + i) % 2, i % 3)
        cor = Image.new("RGBA", o.size, sil)
        cor.putalpha(o.getchannel("A"))
        y = y0 + topo[min(max(0, pe), ORCS_X1 - 3)] - 14 - (f + i) % 2
        T.put(cor, x, y)
        T.px(x + 11, y + 2, hx("#ff5a2a"))
        if i % 3 == 2:
            T.rect(x + 12, y + 1, 3, 2, hx("#ff9a2a"))
            T.px(x + 13, y, hx("#ffd37a"))


def gollum(f):
    """Gollum agachado num tronco, olhando para a esquerda (para os barcos): olhos enormes e braços finos remando."""
    T = Tela(34, 24)
    pele, sombra = hx("#a8b49a"), hx("#7f8a74")
    T.rect(2, 17, 31, 5, hx("#4a3322"))
    T.rect(2, 17, 31, 1, hx("#7a5a3a"))
    T.rect(2, 21, 31, 1, hx("#2e2016"))
    T.ell(0, 17, 4, 21, hx("#8a6a44"))
    T.px(2, 19, hx("#4a3322"))
    T.ell(29, 17, 33, 21, hx("#8a6a44"))
    T.px(31, 19, hx("#4a3322"))
    T.ell(14, 8, 25, 18, pele)
    T.ell(19, 9, 25, 18, sombra)
    T.rect(14, 14, 10, 4, hx("#6b5a40"))
    remo = (f // 3) % 2
    T.line([(15, 12), (9, 17 + remo)], pele)
    T.line([(15, 13), (9, 18 + remo)], pele)
    T.line([(22, 12), (28, 16 + (1 - remo))], pele)
    T.rect(7, 17 + remo, 3, 2, pele)
    T.rect(27, 16 + (1 - remo), 3, 2, pele)
    T.ell(6, 2, 16, 10, pele)
    T.ell(11, 3, 16, 10, sombra)
    T.poly([(6, 5), (2, 1), (7, 7)], pele)
    T.poly([(16, 5), (19, 2), (15, 7)], pele)
    for ex in (7, 11):
        T.ell(ex, 4, ex + 3, 7, hx("#d8f0ff"))
        T.px(ex + (0 if (f // 8) % 3 else 1), 5, hx("#10161c"))
        T.px(ex + (0 if (f // 8) % 3 else 1), 6, hx("#10161c"))
    T.px(10, 9, hx("#3a2a22"))
    T.px(11, 9, hx("#3a2a22"))
    for hxx, hyy in ((9, 1), (11, 0), (13, 1), (8, 2)):
        T.px(hxx, hyy, hx("#4a3a30"))
    return contorno(T.im, OL)


def gollum_em(T, per, f, yr, x=None):
    """O easter egg: Gollum num tronco entra pelo canto direito (ou chega ao x dado), olha para os barcos, murmura e some."""
    saida = 44
    xo = round(48 * (1 - f / 12)) if f < 12 else 0 if f < saida else round(48 * (f - saida) / (EFEITOS["gollum"] - saida))
    g = gollum(f)
    gx, gy = (W - 42 if x is None else x) + xo, yr + 12 + round(math.sin(f / 2))
    T.put(grade(g, per), gx, gy)
    for k in range(3):  # marola na ponta do tronco
        if (f + k) % 3:
            T.rect(gx - 3 - 3 * k, gy + g.height - 3 + k, 3, 1, hx("#e4f0ee"))
    if 16 <= f < 42:
        texto = "Meu precioso!"
        bw = largura(texto) + 8
        bx, by = gx - bw + 8, gy - 14
        T.rect(bx, by, bw, 11, OL)
        T.rect(bx + 1, by + 1, bw - 2, 9, UI[per]["paper"])
        T.cantos(bx, by, bw, 11)
        T.rect(bx + bw - 10, by + 11, 3, 2, OL)
        T.texto(bx + 4, by + 2, texto, UI[per]["ink"])


# ------------------------------------------------------------------ tábua de pedra
def tabua(per, h):
    """A tábua entre as estátuas: laje de pedra com a beirada chanfrada, rebites e o friso do título."""
    T = Tela(W, Y0 + h + FOLGA)
    s1, s2, s3, hl = PEDRA["s1"], PEDRA["s2"], PEDRA["s3"], PEDRA["hl"]
    T.rect(BX, Y0, BW, h, OL)
    T.rect(BX + 1, Y0 + 1, BW - 2, h - 2, s1)
    T.rect(BX + 1, Y0 + 1, BW - 2, 1, s3)
    T.rect(BX + 1, Y0 + 1, 1, h - 2, s3)
    T.rect(BX + 1, Y0 + h - 2, BW - 2, 1, s2)
    T.rect(BX + BW - 2, Y0 + 1, 1, h - 2, s2)
    r = random.Random(3)
    for _ in range(260):  # granulação da pedra
        x, y = r.randrange(BX + 2, BX + BW - 2), r.randrange(Y0 + 2, Y0 + h - 2)
        T.px(x, y, mix(s1, s3 if r.random() < .5 else s2, .55))
    T.rect(BX + 3, Y0 + 3, BW - 6, 15, s2)  # friso do título
    T.rect(BX + 3, Y0 + 3, BW - 6, 1, mix(s2, OL, .5))
    T.rect(BX + 3, Y0 + 17, BW - 6, 1, s3)
    for rx, ry in ((BX + 5, Y0 + 5), (BX + BW - 6, Y0 + 5), (BX + 5, Y0 + h - 6), (BX + BW - 6, Y0 + h - 6)):
        T.px(rx, ry, hl)
        T.px(rx + 1, ry + 1, OL)
    T.cantos(BX, Y0, BW, h)
    T.rect(BX + 3, Y0 + h, BW - 6, FOLGA, OL)  # base de pedra: a tábua apoia no rio
    T.rect(BX + 4, Y0 + h, BW - 8, FOLGA - 1, s2)
    return grade(T.im, per)


# ------------------------------------------------------------------ os temas
class Argonath(TemaPixel):
    id = "argonath"
    nome = "Argonath"
    descricao = "As estátuas de Isildur e Anárion guardando o rio, com o quadro do dia entre elas e canoas passando."
    cores_balao = ("#e8dcc0", "#2a2d36", "#1f252b")
    animacao_ms = 140
    efeitos = EFEITOS
    PAD = 8

    def __init__(self):
        self._cache = {}
        self._ui = (None, None)

    def paleta(self, per):
        u = UI[per]
        return dict(texto=u["ink"], dim=u["dim"], ok=u["ok"], acc=u["acc"], sel_fundo=u["acc"],
                    sel_texto=hx("#fff8ea"), linha=u["paper2"], hover=u["acc"])

    def moldura_dialogo(self, T, w, h, titulo, per, hover_fechar):
        u = UI[per]
        s1, s2, s3, hl = PEDRA["s1"], PEDRA["s2"], PEDRA["s3"], PEDRA["hl"]
        T.rect(0, 0, w, h, OL)
        T.rect(1, 1, w - 2, h - 2, s1)
        T.rect(1, 1, w - 2, 1, s3)
        T.rect(1, 1, 1, h - 2, s3)
        T.rect(1, h - 2, w - 2, 1, s2)
        T.cantos(0, 0, w, h)
        T.rect(3, 3, w - 6, self.TITULO_H - 4, s2)
        T.texto(9, 6, titulo, OL)
        T.texto(8, 5, titulo, hl)
        T.put(icone("fechar", hx("#ffffff") if hover_fechar else hl), w - 12, 6)
        T.rect(4, self.TITULO_H, w - 8, h - self.TITULO_H - 4, OL)
        T.rect(5, self.TITULO_H + 1, w - 10, h - self.TITULO_H - 6, u["paper"])
        T.cantos(4, self.TITULO_H, w - 8, h - self.TITULO_H - 4)
        return (w - 16, 1, w - 2, self.TITULO_H)

    # --- geometria (pixels de arte), função do número de linhas da lista ---
    @staticmethod
    def _linhas(e):
        return max(len(e.topicos) + (1 if e.extra else 0), 3)

    def _geo(self, e):
        n = self._linhas(e)
        ph = 11 * n + 6
        py = Y0 + 19
        ey = py + ph + 3
        sty = ey + 15 + 3
        hb = sty + 7 + 5 - Y0
        yr = Y0 + hb + FOLGA
        meio = max(1, round((yr + 6 - 2 * (LINHAS_TOPO + LINHAS_BASE[1] - LINHAS_BASE[0])) / R))
        y0 = yr + 6 - (LINHAS_TOPO + meio + LINHAS_BASE[1] - LINHAS_BASE[0]) * R  # topo das paredes
        return dict(n=n, ph=ph, py=py, ey=ey, sty=sty, hb=hb, yr=yr, meio=meio, y0=y0, H=yr + RIO)

    def _guarda(self, k, fn, limite=600):
        if k not in self._cache:
            if len(self._cache) > limite:
                self._cache.clear()
            self._cache[k] = fn()
        return self._cache[k]

    def _parede(self, per, g):
        return self._guarda(("parede", per, g["meio"]), lambda: parede(per, g["meio"]))

    def _tabua(self, per, g):
        return self._guarda(("tabua", per, g["hb"]), lambda: tabua(per, g["hb"]))

    # --- interface (texto, lista, botões) ---
    def _interface(self, e, g):
        u = UI[e.periodo]
        s1, s2, s3, hl = PEDRA["s1"], PEDRA["s2"], PEDRA["s3"], PEDRA["hl"]
        T = Tela(W, g["H"])
        regs = []
        titulo = f"Diário · {DIAS_SEMANA[e.dia.weekday()]} {e.dia:%d/%m}"
        T.texto(BX + 9, Y0 + 7, titulo, OL)
        T.texto(BX + 8, Y0 + 6, titulo, hl)
        if not e.eh_hoje:  # plaquinha de pedra pendurada em cima da tábua, para voltar ao dia atual
            caixa = (BX + 10, Y0 - 10, BX + 38, Y0 + 1)
            T.rect(caixa[0], caixa[1], 28, 11, OL)
            T.rect(caixa[0] + 1, caixa[1] + 1, 26, 10, s3 if e.hover == "hoje" else s1)
            T.rect(caixa[0] + 1, caixa[1] + 1, 26, 1, mix(s3, hl, .4))
            T.texto(caixa[0] + 5, caixa[1] + 2, "Hoje", OL if e.hover == "hoje" else hl)
            regs.append(Regiao("hoje", caixa, DICAS["hoje"]))
        x = BX + BW - 6
        for nome in reversed(BOTOES):
            x -= 9
            ic = icone(nome, hx("#ffd75a") if e.hover == nome else hl)
            T.put(ic, x + (9 - ic.width) // 2, Y0 + 10 - ic.height // 2)
            regs.append(Regiao(nome, (x, Y0 + 2, x + 9, Y0 + 18), DICAS[nome]))
        px_, pw = BX + 6, BW - 12
        T.rect(px_, g["py"], pw, g["ph"], OL)
        T.rect(px_ + 1, g["py"] + 1, pw - 2, g["ph"] - 2, u["paper"])
        T.rect(px_ + 1, g["py"] + g["ph"] - 3, pw - 2, 2, u["paper2"])
        T.cantos(px_, g["py"], pw, g["ph"])
        linhas = list(e.topicos) or [("Nada registrado neste dia.", "aviso")]
        for i, (txt, tipo) in enumerate(linhas):
            y = g["py"] + 5 + i * 11
            cor = {"manual": u["ok"], "aviso": u["dim"], "resumir": u["dim"]}.get(tipo, u["ink"])
            if e.hover == f"linha:{i}":
                T.rect(px_ + 3, y - 2, pw - 6, 11, u["paper2"])
            T.rect(px_ + 7, y + 2, 3, 3, cor if tipo else u["acc"])
            rotulo = RESUMINDO if e.resumindo else ATUALIZAR if e.refazer else RESUMIR
            curto = cortar(txt, pw - 22 - (largura(rotulo) + 10 if tipo == "resumir" else 0))
            T.texto(px_ + 14, y, curto, cor)
            if tipo == "resumir":
                r = botao_resumir(T, px_ + 14 + largura(curto) + 6, y, e, u["acc"], u["ink"])
                if r:
                    regs.append(r)
            regs.append(Regiao(f"linha:{i}", (px_, y - 2, px_ + pw, y + 9), txt if curto != txt else "", ""))
        if e.extra:
            T.texto(px_ + 14, g["py"] + 5 + len(linhas) * 11, f"… e mais {e.extra}", u["dim"])
        T.rect(px_, g["ey"], pw, 15, OL)
        T.rect(px_ + 1, g["ey"] + 1, pw - 2, 13, u["slate"])
        campo = (px_ + 4, g["ey"] + 2, px_ + pw - 4, g["ey"] + 13)
        T.rect(campo[0], campo[1], campo[2] - campo[0], campo[3] - campo[1], mix(u["slate"], hx("#000000"), .35))
        msg = e.status if e.status and e.status_tipo != "dica" else DICA_CURTA
        cor = (STATUS_COR.get(e.status_tipo) or {}).get(e.periodo) or mix(hl, s2, .35)
        T.texto(px_ + 2, g["sty"], cortar(msg, pw - 4), cor)
        return T.im, regs, campo

    def _ui_do(self, e, g):
        chave = (e.dia, tuple(e.topicos), e.extra, e.status, e.status_tipo, e.hover, e.periodo, e.eh_hoje, e.resumindo,
                 e.refazer)
        if self._ui[0] != chave:
            self._ui = (chave, self._interface(e, g))
        return self._ui[1]

    def _final(self, img, regs, campo, per):
        Z = self.Z
        imagem = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
        regioes = [Regiao(r.nome, tuple(v * Z for v in r.caixa), r.dica, r.cursor) for r in regs]
        u = UI[per]
        estilo = dict(bg="#%02x%02x%02x" % mix(u["slate"], hx("#000000"), .35)[:3],
                      fg="#%02x%02x%02x" % u["stxt"][:3], cursor="#%02x%02x%02x" % u["stxt"][:3],
                      fonte=("Consolas", 10))
        return Quadro(imagem, regioes, tuple(v * Z for v in campo), estilo, False, "#1f252b")

    def _cena(self, e, t, g):
        """A imagem da cena e a caixa de cada nuvem (que se move)."""
        per, ef, yr = e.periodo, e.efeitos, g["yr"]
        ceu_k = self._guarda(("ceu", per, yr), lambda: ceu(per, yr))
        img = Image.new("RGBA", (W, g["H"]), OL)
        T = Tela(W, yr)
        T.im.paste(ceu_k)
        T.put(astros(per, t), 0, 0)
        if "ceu" in ef:
            efeito_ceu(T, per, ef["ceu"])
        caixas = nuvens_em(T, per, t, ef)
        img.alpha_composite(T.im)
        img.alpha_composite(self._tabua(per, g))
        img.alpha_composite(self._ui_do(e, g)[0])
        esq, dire = self._parede(per, g)
        y0 = g["y0"]
        topo = self._guarda(("cume", per, g["meio"]), lambda: cume(esq))
        pa, pb = esq, dire
        if "isildur" in ef:
            pa = virar_cabeca(esq, "isildur", ef["isildur"])
        if "anarion" in ef:
            pb = virar_cabeca(dire, "anarion", ef["anarion"])
        img.alpha_composite(pa, (0, y0))
        img.alpha_composite(pb, (W - RW, y0))
        F = Tela(W, g["H"])  # o que se passa na frente das paredes
        for nome in ("isildur", "anarion"):
            if nome in ef:
                poeira(F, nome, ef[nome], y0, per)
                olhos_em(F, nome, ef[nome], y0)
        if "orcs" in ef:
            orcs_em(F, per, ef["orcs"], topo, y0)
        img.alpha_composite(F.im)
        img.alpha_composite(self._guarda(("rio", per, t % 160), lambda: rio(per, t)), (0, yr))
        if "agua" in ef:
            img.alpha_composite(agua_fx(per, ef["agua"]), (0, yr))
        img.alpha_composite(canoas(per, t, ef), (0, yr))
        if "gollum" in ef:
            G = Tela(W, g["H"])
            gollum_em(G, per, ef["gollum"], yr)
            img.alpha_composite(G.im)
        return img, caixas

    def _regioes_efeitos(self, e, g, caixas):
        """Áreas clicáveis do cenário, sem dica (só o cursor de mão, e nenhum nos segredos). A primeira que casa
        vence, então as menores vêm antes das áreas grandes que as contêm: segredos, canoas, rostos das estátuas,
        nuvens, céu e, por último, a água toda."""
        yr = g["yr"]
        regs = [Regiao("efeito:orcs", (0, 120, ORCS_X1 + 4, yr + 1), "", ""),
                Regiao("efeito:gollum", (W - 100, yr + 6, W, g["H"]), "", "")]
        for i, (L, cx, linha, _quem) in enumerate(CANOAS):
            x0 = (cx - L // 2) * R
            regs.append(Regiao(f"efeito:canoa{i}", (x0 - 3, yr + (linha - CANOA_ALT) * R - 4, x0 + L * R + 3,
                                                    yr + (linha + 1) * R + 2)))
        for nome in ("isildur", "anarion"):
            x0, y0 = para_cena(nome, *CLIQUE_ROSTO[nome][:2], g["y0"])
            x1, y1 = para_cena(nome, *CLIQUE_ROSTO[nome][2:], g["y0"])
            regs.append(Regiao(f"efeito:{nome}", (x0, y0, x1, y1)))
        for i, (x0, y0, x1, y1) in enumerate(caixas):  # a plaquinha "Hoje" fica logo acima da tábua: não cobrir
            regs.append(Regiao(f"efeito:nuvem{i}", (x0, y0, x1, min(y1, Y0 - 11))))
        regs += [Regiao("efeito:ceu", (LW, 0, W - RW, Y0 - 11)), Regiao("efeito:agua", (0, yr + 2, W, g["H"]))]
        return regs

    def camadas(self, per, t):
        """Uma camada por painel, para ver como a cena é montada."""
        e = Estado(dia=date.today(), periodo=per)
        g = self._geo(e)
        ce = Tela(W, g["H"])
        ce.im.paste(self._guarda(("ceu", per, g["yr"]), lambda: ceu(per, g["yr"])), (0, 0))
        ce.put(astros(per, t), 0, 0)
        nuvens_em(ce, per, t)
        pa = Tela(W, g["H"])
        esq, dire = self._parede(per, g)
        pa.put(esq, 0, g["yr"] + 6 - esq.height)
        pa.put(dire, W - RW, g["yr"] + 6 - dire.height)
        ta = Tela(W, g["H"])
        ta.im.alpha_composite(self._tabua(per, g))
        ta.im.alpha_composite(self._interface(e, g)[0])
        ri = Tela(W, g["H"])
        ri.put(rio(per, t), 0, g["yr"])
        ri.put(canoas(per, t, {}), 0, g["yr"])
        return [("céu", "degraus, riscos, nuvens e astros", ce.im), ("paredes", "estátuas e penhascos da referência", pa.im),
                ("tábua", "pedra e lista do dia", ta.im), ("rio", "água, névoa e as três canoas", ri.im)]

    def quadro(self, e: Estado, t: int) -> Quadro:
        g = self._geo(e)
        _, regs, campo = self._ui_do(e, g)
        img, caixas = self._cena(e, t, g)
        regs = regs + self._regioes_efeitos(e, g, caixas) + [Regiao("arrastar", (0, 0, W, g["H"]), "", "")]
        return self._final(img, regs, campo, e.periodo)
