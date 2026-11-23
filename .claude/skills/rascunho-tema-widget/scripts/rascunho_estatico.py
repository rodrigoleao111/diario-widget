"""Rascunho estático de um tema do widget: UMA imagem da manhã, sem registrar o tema em TEMAS.

python -X utf8 rascunho_estatico.py <modulo:Classe> <saida.png> [--estados] [--fundos] [--efeito nome=quadro ...] [--t 40]

Grava a imagem do estado "exemplo" (o das miniaturas) em <saida.png>. Com --estados grava também, ao lado,
<saida>_cheio.png (14 tópicos e "… e mais 3"), <saida>_vazio.png e <saida>_passado.png (botão Hoje, tópico sob o mouse
e status), que servem para você conferir o layout antes de mostrar; só o primeiro vai para o usuário.
Tema de janela livre (sem fundo; o que não é desenhado vira buraco) sai sobre uma área de trabalho de teste (--fundo area,
claro, escuro ou xadrez); --fundos grava também <saida>_claro.png e <saida>_escuro.png: confira nos dois extremos, porque
contorno e nuvem que somem num fundo claro ou escuro são o erro típico.
--efeito congela um efeito de clique num quadro (ex.: martelo=3 mostra a martelada); --periodo existe para depurar, mas o
rascunho é sempre da manhã. Imprime o tamanho da janela e o tempo do primeiro quadro.
Em Git Bash passe caminhos relativos ou o resultado de `cygpath -w`.
"""
import argparse
from pathlib import Path

from _comum import ESTADOS, carrega, efeitos_de, estado, renderiza


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tema", help="modulo:Classe, ex.: reforma:Reforma")
    ap.add_argument("saida", help="arquivo PNG de saída")
    ap.add_argument("--periodo", default="manha", choices=("manha", "tarde", "noite"))
    ap.add_argument("--estados", action="store_true", help="grava também os estados cheio, vazio e passado")
    ap.add_argument("--fundo", default="area", choices=("area", "claro", "escuro", "xadrez"))
    ap.add_argument("--fundos", action="store_true", help="grava também sobre fundo claro e escuro (janela livre)")
    ap.add_argument("--efeito", action="append", help="nome=quadro, repetível")
    ap.add_argument("--t", type=int, default=40, help="quadro de animação a congelar")
    a = ap.parse_args()
    tema = carrega(a.tema)
    saida = Path(a.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    efeitos = efeitos_de(a.efeito)
    for nome in (ESTADOS if a.estados else ("exemplo",)):
        e = estado(nome, a.periodo, efeitos if nome == "exemplo" else None)
        im, ms = renderiza(tema, e, a.t, a.fundo)
        destino = saida if nome == "exemplo" else saida.with_name(f"{saida.stem}_{nome}{saida.suffix}")
        im.save(destino)
        print(f"{nome:8} {im.size}  {ms:5.0f} ms  -> {destino.resolve()}")
        if nome == "exemplo" and a.fundos:
            for fundo in ("claro", "escuro"):
                renderiza(tema, e, a.t, fundo)[0].save(saida.with_name(f"{saida.stem}_{fundo}{saida.suffix}"))


if __name__ == "__main__":
    main()
