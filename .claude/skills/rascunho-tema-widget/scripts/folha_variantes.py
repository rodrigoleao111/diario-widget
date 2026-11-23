"""Folha comparativa de variantes de uma peça (3 igrejas, 3 personagens...), lado a lado, para o usuário escolher.

python -X utf8 folha_variantes.py <modulo:Classe> <saida.png> --atributo v_igreja --valores a,b,c --caixa x0,y0,x1,y1 [--zoom 3]
                                  [--rotulos "A · TORRE,B · CASTELO,C · GEMEAS"] [--fixo v_lutero=a] [--efeito martelo=3]

O tema escolhe a variante lendo um atributo de instância (`self.v_igreja`, `self.v_lutero`...) com um valor padrão na
classe e o inclui na chave de cache de tudo que desenha com ele. O script cria uma instância por valor, ajusta o atributo e
recorta a mesma caixa da cena inteira (em pixels de arte), então as peças aparecem no contexto delas. Rótulos sem acento
(a fonte pixel tem poucos caracteres). Depois da escolha, apague as variantes descartadas do tema.
"""
import argparse
from pathlib import Path

from _comum import RAIZ, carrega, efeitos_de, estado, recorta, renderiza  # noqa: F401
from PIL import Image

from diario.pixel import Tela, hx

FUNDO = (20, 22, 28)


def rotulo(txt, w):
    r = Tela(max(w // 2, 1), 12)
    r.texto(2, 2, txt.upper(), hx("#fcecd1"))
    return r.im.resize((w, 24), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tema")
    ap.add_argument("saida")
    ap.add_argument("--atributo", required=True)
    ap.add_argument("--valores", required=True)
    ap.add_argument("--caixa", required=True)
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--rotulos")
    ap.add_argument("--fixo", action="append", help="outro_atributo=valor, repetível")
    ap.add_argument("--periodo", default="manha", choices=("manha", "tarde", "noite"))
    ap.add_argument("--efeito", action="append")
    ap.add_argument("--t", type=int, default=40)
    ap.add_argument("--fundo", default="area", choices=("area", "claro", "escuro", "xadrez"))
    a = ap.parse_args()
    valores = a.valores.split(",")
    rotulos = a.rotulos.split(",") if a.rotulos else valores
    paineis = []
    for v in valores:
        tema = carrega(a.tema)
        for kv in a.fixo or []:
            k, val = kv.split("=")
            setattr(tema, k, val)
        setattr(tema, a.atributo, v)
        im, _ = renderiza(tema, estado("exemplo", a.periodo, efeitos_de(a.efeito)), a.t, a.fundo)
        paineis.append(recorta(im, a.caixa, a.zoom, getattr(tema, "Z", 2)))
    pw, ph = paineis[0].size
    folha = Image.new("RGB", (len(paineis) * (pw + 16) + 16, ph + 56), FUNDO)
    for i, (p, r) in enumerate(zip(paineis, rotulos)):
        x = 16 + i * (pw + 16)
        folha.paste(rotulo(r, min(pw, len(r) * 12 + 24)), (x, 12))
        folha.paste(p, (x, 44))
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    folha.save(a.saida)
    print(folha.size, "->", Path(a.saida).resolve())


if __name__ == "__main__":
    main()
