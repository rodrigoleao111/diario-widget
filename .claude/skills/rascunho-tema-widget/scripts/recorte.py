"""Recorte ampliado de um rascunho, para o autor olhar de perto (rosto do personagem, porta, topo das torres) antes de mostrar.

python -X utf8 recorte.py <modulo:Classe> <saida.png> --caixa x0,y0,x1,y1 [--zoom 8] [--efeito nome=quadro] [--estado cheio]

A caixa é em pixels de arte (a janela tem `Tema.Z` vezes isso na tela); --zoom é quantos pixels da tela vale cada pixel de arte
no recorte (padrão 8). Dica: renderize o quadro inteiro antes e meça a caixa na imagem (divida as coordenadas por Z).
"""
import argparse
from pathlib import Path

from _comum import carrega, efeitos_de, estado, recorta, renderiza


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tema")
    ap.add_argument("saida")
    ap.add_argument("--caixa", required=True)
    ap.add_argument("--zoom", type=int, default=8)
    ap.add_argument("--periodo", default="manha", choices=("manha", "tarde", "noite"))
    ap.add_argument("--estado", default="exemplo")
    ap.add_argument("--efeito", action="append")
    ap.add_argument("--t", type=int, default=40)
    ap.add_argument("--fundo", default="area", choices=("area", "claro", "escuro", "xadrez"))
    a = ap.parse_args()
    tema = carrega(a.tema)
    im, _ = renderiza(tema, estado(a.estado, a.periodo, efeitos_de(a.efeito)), a.t, a.fundo)
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    c = recorta(im, a.caixa, a.zoom, getattr(tema, "Z", 2))
    c.save(a.saida)
    print(c.size, "->", Path(a.saida).resolve())


if __name__ == "__main__":
    main()
