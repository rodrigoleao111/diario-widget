"""Acabamento de pixel art para os temas do widget: as técnicas que fazem uma cena parecer desenhada à mão em vez de
montada com retângulos. Pesquisa e regras em .claude/skills/rascunho-tema-widget/referencias/tecnicas.md.

Contrato da paleta (`c`, um dicionário de cores `hx(...)` de um período): s1, s2, s3 (rampa da pedra: base, sombra, luz),
hi (realce quente, quase branco), sh (sombra funda, mais fria e saturada), ol e ol2 (contorno e contorno mais escuro),
wd1, wd2, wd3 (madeira: base, sombra, luz) e paper, paper2 (papel: base, borda). Tudo desenha em pixels de arte.
"""
import random

from PIL import Image

from .pixel import TRANSPARENTE, mix


def tinge(T, x, y, w, h, cor, t):
    """Mistura cada pixel opaco do retângulo com `cor` (sombra e luz sobre o que já foi desenhado)."""
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if 0 <= xx < T.w and 0 <= yy < T.h:
                v = T.im.getpixel((xx, yy))
                if v[3]:
                    T.im.putpixel((xx, yy), mix(v, cor, t))


def pedra(T, x0, y0, w, h, c, seed=1):
    """Aparelho de pedra: fiadas de 7 px com blocos de 10 a 18 px e junta de 1 px um tom abaixo da pedra. Cada bloco tem
    seu tom; alguns ganham brilho no alto, outros sombra no alto ou embaixo, e uma ou outra lasca."""
    r = random.Random(seed)
    T.rect(x0, y0, w, h, mix(c["s1"], c["sh"], .42))
    y, fiada = y0, 0
    while y < y0 + h:
        alt = min(7, y0 + h - y)
        x = x0 - r.randrange(0, 9) - (5 if fiada % 2 else 0)
        while x < x0 + w:
            bw = r.choice((10, 12, 14, 16, 18))
            a, b = max(x + 1, x0), min(x + bw, x0 + w)
            if b > a and alt > 1:
                t = r.random()
                cor = c["s1"] if t < .5 else mix(c["s1"], c["s3"], .38) if t < .8 else mix(c["s1"], c["s2"], .5)
                T.rect(a, y, b - a, alt - 1, cor)
                if r.random() < .5:
                    T.rect(a, y, max(b - a - 2, 1), 1, mix(cor, c["hi"], .4))
                    if r.random() < .5:
                        T.px(a, y + 1, mix(cor, c["hi"], .3))
                elif r.random() < .35:
                    T.rect(a, y, b - a, 1, mix(cor, c["sh"], .35))
                if r.random() < .3:
                    T.rect(a, y + alt - 2, b - a, 1, mix(cor, c["sh"], .3))
                if r.random() < .1 and b - a > 6:
                    T.rect(a + 2 + r.randrange(b - a - 5), y + 2, 2, 2, mix(cor, c["s2"], .6))
            x += bw
        y += alt
        fiada += 1



def luz_e_sombra(T, x0, y0, w, h, c):
    """A luz vem da esquerda: borda clara no lado esquerdo da face e sombra no direito, em três passos (dois lisos e um
    pontilhado de transição)."""
    tinge(T, x0, y0, 1, h, c["hi"], .42)
    tinge(T, x0 + 1, y0, 1, h, c["hi"], .2)
    x1 = x0 + w
    tinge(T, x1 - 2, y0, 2, h, c["sh"], .55)
    tinge(T, x1 - 4, y0, 2, h, c["sh"], .34)
    for yy in range(y0, y0 + h):
        for xx in (x1 - 6, x1 - 5):
            if (xx + yy) % 2 == 0:
                tinge(T, xx, yy, 1, 1, c["sh"], .22)



def sombra_embaixo(T, x, y, w, c, k=.5):
    """Oclusão: duas linhas escuras logo abaixo de cornijas, beirais e ameias."""
    tinge(T, x, y, w, 1, c["sh"], k)
    tinge(T, x, y + 1, w, 1, c["sh"], k * .5)



def borda_colorida(im, linha, c):
    """Troca o contorno externo (a cor `linha`) por um tom escuro da pedra vizinha: mais claro onde a luz bate (cima e
    esquerda) e mais escuro embaixo e à direita (selout)."""
    w, h = im.size
    px = im.load()
    novos = []
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] == 0 or p[:3] != linha[:3]:
                continue
            fora = [(dx, dy) for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
                    if not (0 <= x + dx < w and 0 <= y + dy < h) or px[x + dx, y + dy][3] == 0]
            if not fora:
                continue
            viz = next((px[x + dx, y + dy] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                        if 0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3]
                        and px[x + dx, y + dy][:3] != linha[:3]), None)
            if viz is None:
                continue
            k = .5 if any(dx < 0 or dy < 0 for dx, dy in fora) else .74
            novos.append((x, y, mix(viz, c["ol2"], k)))
    for x, y, cor in novos:
        px[x, y] = cor



def selout(im, c):
    """Contorno de 1 px para sprites: o tom do próprio sprite, mais escuro; mais claro no alto e à esquerda (onde a luz
    bate) e mais escuro embaixo e à direita."""
    w, h = im.size
    out = Image.new("RGBA", (w + 2, h + 2), TRANSPARENTE)
    src, o = im.load(), out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3]:
                o[x + 1, y + 1] = src[x, y]
    for y in range(h):
        for x in range(w):
            p = src[x, y]
            if not p[3]:
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if (0 <= nx < w and 0 <= ny < h and src[nx, ny][3]) or o[nx + 1, ny + 1][3]:
                    continue
                o[nx + 1, ny + 1] = mix(p, c["ol2"], .55 if dx < 0 or dy < 0 else .8)
    return out



def veios(T, x, y, w, h, c, seed=1, vertical=False):
    """Veios da madeira: traços curtos, uns mais escuros e outros mais claros, e um nó de vez em quando."""
    r = random.Random(seed)
    for _ in range(max(w * h // 40, 1)):
        n = r.randrange(3, 10)
        xx, yy = x + r.randrange(w), y + r.randrange(h)
        cor = mix(c["wd1"], c["wd2"], .55) if r.random() < .7 else mix(c["wd1"], c["wd3"], .45)
        if vertical:
            T.rect(xx, yy, 1, min(n, y + h - yy), cor)
        else:
            T.rect(xx, yy, min(n, x + w - xx), 1, cor)
    for _ in range(max(w * h // 600, 0)):
        nx, ny = x + 2 + r.randrange(max(w - 4, 1)), y + 1 + r.randrange(max(h - 2, 1))
        T.rect(nx, ny, 2, 1, c["wd2"])



def envelhece(T, x, y, w, h, c, seed=2):
    """Papel antigo: bordas escurecidas em degradê, pontinhos de fibra e umas manchas claras."""
    r = random.Random(seed)
    for yy in range(y, y + h):
        T.px(x, yy, mix(c["paper"], c["paper2"], .6))
        T.px(x + w - 1, yy, mix(c["paper"], c["paper2"], .6))
        T.px(x + 1, yy, mix(c["paper"], c["paper2"], .3 if yy % 2 else .15))
        T.px(x + w - 2, yy, mix(c["paper"], c["paper2"], .3 if yy % 2 else .15))
    for _ in range(w * h // 90):
        T.px(x + 2 + r.randrange(w - 4), y + r.randrange(h - 3), mix(c["paper"], c["paper2"], .32))
    for _ in range(6):
        mx, my = x + 6 + r.randrange(w - 14), y + 3 + r.randrange(h - 10)
        T.rect(mx, my, r.randrange(3, 6), 2, mix(c["paper"], c["paper2"], .22))
