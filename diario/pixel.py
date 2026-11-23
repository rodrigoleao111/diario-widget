"""Ferramentas de pixel art dos temas: fonte 5x7 com acentos, formas com sombreado, contorno e ícones.

Tudo aqui desenha em PIL numa grade pequena ("pixels de arte"); quem chama amplia com NEAREST.
A fonte pixel (recursos/pixel5x7.json) é CC0, de with-pebbly/aseprite-ai-artist, e não traz acentos: eles são
desenhados por cima da letra-base.
"""
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

_FONTE = json.loads((Path(__file__).parent / "recursos" / "pixel5x7.json").read_text(encoding="utf-8"))["glyphs"]
_FONTE["·"] = ["...", "...", "...", ".#.", "...", "...", "..."]
_FONTE["…"] = [".....", ".....", ".....", ".....", ".....", "#.#.#", "....."]
_FONTE["—"] = [".....", ".....", ".....", "#####", ".....", ".....", "....."]
_FONTE["•"] = ["...", "...", ".#.", "###", ".#.", "...", "..."]

# caractere acentuado -> (letra-base, tipo do acento)
ACENTOS = {"á": ("a", "a"), "à": ("a", "g"), "ã": ("a", "t"), "â": ("a", "c"), "é": ("e", "a"), "ê": ("e", "c"),
           "í": ("i", "a"), "ó": ("o", "a"), "õ": ("o", "t"), "ô": ("o", "c"), "ú": ("u", "a"), "ç": ("c", "z"),
           "Á": ("A", "a"), "À": ("A", "g"), "Ã": ("A", "t"), "Â": ("A", "c"), "É": ("E", "a"), "Ê": ("E", "c"),
           "Í": ("I", "a"), "Ó": ("O", "a"), "Õ": ("O", "t"), "Ô": ("O", "c"), "Ú": ("U", "a"), "Ç": ("C", "z")}

BRANCO, PRETO, TRANSPARENTE = (252, 252, 252, 255), (0, 0, 0, 255), (0, 0, 0, 0)


def hx(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def rampa(c, sombra=(42, 20, 72, 255), luz=(255, 242, 176, 255)):
    """(escuro, base, claro): a sombra puxa para o roxo e a luz para o amarelo, como na pixel art de verdade."""
    return mix(c, sombra, .38), c, mix(c, luz, .42)


def glifo(ch):
    """(linhas, pixels extras): os extras são (coluna, linha) relativos ao topo da célula e podem ter linha negativa."""
    if ch in ACENTOS:
        base, k = ACENTOS[ch]
        g = _FONTE[base]
        topo = next(j for j, r in enumerate(g) if "#" in r)
        if base == "i":  # o pingo vira o acento
            return ["..."] + g[1:], [(1, 0), (2, -1)]
        if k == "z":
            return g, [(1, 6), (2, 7)]
        return g, {"a": [(2, topo - 1), (3, topo - 2)], "g": [(3, topo - 1), (2, topo - 2)],
                   "t": [(1, topo - 1), (2, topo - 2), (3, topo - 1), (4, topo - 2)],
                   "c": [(1, topo - 1), (2, topo - 2), (3, topo - 1)]}[k]
    return _FONTE.get(ch) or _FONTE["?"], []


def largura(texto, k=1):
    """Largura em pixels de arte (vezes k) de um texto na fonte pixel."""
    return sum((len(glifo(ch)[0][0]) + 1) * k for ch in texto) - k if texto else 0


def cortar(texto, px):
    """Corta com reticências para caber em px pixels de arte."""
    if largura(texto) <= px:
        return texto
    while texto and largura(texto + "…") > px:
        texto = texto[:-1]
    return texto.rstrip() + "…"


class Tela:
    """Camada RGBA transparente com primitivas de desenho sem suavização."""

    def __init__(s, w, h, fundo=TRANSPARENTE):
        s.w, s.h = w, h
        s.im = Image.new("RGBA", (w, h), fundo)
        s.d = ImageDraw.Draw(s.im)

    def px(s, x, y, c):
        if 0 <= x < s.w and 0 <= y < s.h:
            s.im.putpixel((int(x), int(y)), c)

    def rect(s, x, y, w, h, c):
        if w > 0 and h > 0:
            s.d.rectangle([x, y, x + w - 1, y + h - 1], fill=c)

    def ell(s, x0, y0, x1, y1, c):
        s.d.ellipse([x0, y0, x1, y1], fill=c)

    def poly(s, pts, c):
        s.d.polygon(pts, fill=c)

    def line(s, pts, c, w=1):
        s.d.line(pts, fill=c, width=w)

    def put(s, img, x, y):
        """Cola uma imagem RGBA (com alfa) na posição x,y; a parte que sai da tela é cortada."""
        x, y = int(x), int(y)
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + img.width, s.w), min(y + img.height, s.h)
        if x1 > x0 and y1 > y0:
            s.im.alpha_composite(img.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))

    def spr(s, x, y, linhas, pal):
        for j, linha in enumerate(linhas):
            for i, ch in enumerate(linha):
                if ch in pal:
                    s.px(x + i, y + j, pal[ch])

    def texto(s, x, y, t, c, k=1):
        for ch in t:
            g, extra = glifo(ch)
            for j, linha in enumerate(g):
                for i, v in enumerate(linha):
                    if v == "#":
                        s.rect(x + i * k, y + j * k, k, k, c)
            for i, j in extra:
                s.rect(x + i * k, y + j * k, k, k, c)
            x += (len(g[0]) + 1) * k
        return x

    def cantos(s, x, y, w, h):
        """Come os 4 cantos de um retângulo (contorno pixelado clássico)."""
        for cx, cy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
            s.px(cx, cy, TRANSPARENTE)


def esfera(T, x0, y0, x1, y1, r):
    """Elipse com sombra embaixo e brilho em cima, r = (escuro, base, claro)."""
    w, h = x1 - x0, y1 - y0
    T.ell(x0, y0, x1, y1, r[0])
    T.ell(x0, y0, x1 - w * .1, y1 - h * .13, r[1])
    T.ell(x0 + w * .14, y0 + h * .1, x0 + w * .55, y0 + h * .48, r[2])


def contorno(im, cor):
    w, h = im.size
    out = Image.new("RGBA", (w + 2, h + 2), TRANSPARENTE)
    src, o = im.load(), out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] > 0:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    o[x + 1 + dx, y + 1 + dy] = cor
    for y in range(h):
        for x in range(w):
            if src[x, y][3] > 0:
                o[x + 1, y + 1] = src[x, y]
    return out


# ícones de botão: 5x5 (o da engrenagem é 7x7)
ICONES = {
    "anterior": ["...#.", "..#..", ".#...", "..#..", "...#."],
    "proximo": [".#...", "..#..", "...#.", "..#..", ".#..."],
    "calendario": ["#####", "#...#", "#####", "#.#.#", "#####"],
    "atualizar": [".###.", "#...#", "#..##", "#...#", ".###."],
    "relatorio": ["#####", "#...#", "#.#.#", "#...#", "#####"],
    "fechar": ["#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "config": ["..#.#..", ".#####.", "##...##", ".#...#.", "##...##", ".#####.", "..#.#.."],
}


def icone(nome, cor):
    g = ICONES[nome]
    im = Image.new("RGBA", (len(g[0]), len(g)), TRANSPARENTE)
    for j, linha in enumerate(g):
        for i, v in enumerate(linha):
            if v == "#":
                im.putpixel((i, j), cor)
    return im


def semente(nome):
    return random.Random(sum(map(ord, nome)))
