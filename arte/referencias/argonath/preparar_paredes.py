"""Prepara o recurso do tema Argonath a partir da imagem de referência do usuário.

python -X utf8 arte/referencias/argonath/preparar_paredes.py

A referência é pixel art de 160x160 (blocos de 4 px). O script reduz para a grade original, quantiza em 20 cores, apaga
o céu e as nuvens (o que é azul-esverdeado ou creme e está ligado ao topo) e a "poeira" fina que sobra no contorno
das nuvens, e grava diario/recursos/argonath.png: só as estátuas, os penhascos e a névoa, com céu transparente.
"""
from collections import deque
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).parent
SAIDA = AQUI.parents[2] / "diario" / "recursos" / "argonath.png"


def ceu(c):
    r, g, b = c
    return (g - r >= 20 and b - r >= 20) or (r - b >= 36)


def vizinhos(x, y):
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def main():
    im = Image.open(AQUI / "referencia_do_usuario.png").convert("RGB")
    pequena = im.resize((160, 160), Image.BOX)
    quant = pequena.quantize(colors=20, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    px, qp = pequena.load(), quant.load()
    mascara = [[ceu(px[x, y]) for x in range(160)] for y in range(160)]
    visto = [[False] * 160 for _ in range(160)]
    fila = deque((x, 0) for x in range(160) if mascara[0][x])
    for x, y in fila:
        visto[y][x] = True
    while fila:
        x, y = fila.popleft()
        for nx, ny in vizinhos(x, y):
            if 0 <= nx < 160 and 0 <= ny < 160 and not visto[ny][nx] and mascara[ny][nx]:
                visto[ny][nx] = True
                fila.append((nx, ny))
    pedra = [[not visto[y][x] for x in range(160)] for y in range(160)]
    for _ in range(3):  # erosão: tira os fios de 1 px que o contorno das nuvens deixou
        pedra = [[pedra[y][x] and sum(1 for nx, ny in vizinhos(x, y) if 0 <= nx < 160 and 0 <= ny < 160 and pedra[ny][nx]) >= 3
                  for x in range(160)] for y in range(160)]
    for _ in range(3):  # dilatação limitada ao que era pedra: devolve a borda das massas grandes
        pedra = [[pedra[y][x] or (not visto[y][x] and any(0 <= nx < 160 and 0 <= ny < 160 and pedra[ny][nx]
                                                          for nx, ny in vizinhos(x, y))) for x in range(160)]
                 for y in range(160)]
    comp = [[0] * 160 for _ in range(160)]
    tamanhos, n = {}, 0
    for y0 in range(160):
        for x0 in range(160):
            if pedra[y0][x0] and not comp[y0][x0]:
                n += 1
                comp[y0][x0], f, t = n, deque([(x0, y0)]), 0
                while f:
                    x, y = f.popleft()
                    t += 1
                    for nx, ny in vizinhos(x, y):
                        if 0 <= nx < 160 and 0 <= ny < 160 and pedra[ny][nx] and not comp[ny][nx]:
                            comp[ny][nx] = n
                            f.append((nx, ny))
                tamanhos[n] = t
    saida = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    o = saida.load()
    for y in range(160):
        for x in range(160):
            if pedra[y][x] and tamanhos[comp[y][x]] >= 300:
                o[x, y] = qp[x, y] + (255,)
    saida.save(SAIDA)
    print("gravado", SAIDA, saida.size)


if __name__ == "__main__":
    main()
