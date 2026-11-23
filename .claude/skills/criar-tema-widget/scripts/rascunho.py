"""Rascunho de um tema do widget SEM registrá-lo em TEMAS, para o usuário aprovar o visual antes de aplicar.

python -X utf8 rascunho.py <modulo:Classe> <pasta de saída> [--t manha=157,tarde=28,noite=77] [--gif]

`modulo:Classe` é o tema em diario/temas/ (ex.: dino:Dino). Grava, na pasta:
  periodos.png   a janela inteira em manhã, tarde e noite, um quadro de cada (--t escolhe o quadro; padrão 5)
  calendario.png e config.png   os diálogos da manhã (conferem paleta() e moldura_dialogo())
  camadas.png    só se o tema tiver `camadas(periodo, t) -> [(nome, descricao, imagem RGBA)]`: uma camada por painel
  <periodo>.gif  só com --gif: o chão repete a cada 160 quadros; guarda 1 a cada 2
Caminhos: em Git Bash, Python do Windows não entende /c/...; passe caminho relativo ou o resultado de `cygpath -w`.
"""
import argparse
import importlib
import sys
import time
from datetime import date
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diario import temas  # noqa: E402
from diario.pixel import Tela, hx  # noqa: E402
from diario.temas.base import estado_exemplo  # noqa: E402

PERIODOS = ("manha", "tarde", "noite")
FUNDO = (20, 22, 28, 255)


def sobre_fundo(im, fundo=FUNDO):
    base = Image.new("RGBA", im.size, fundo)
    base.alpha_composite(im.convert("RGBA"))
    return base


def estado(tema, per):
    e = estado_exemplo(per)
    e.temas = temas.lista() + ([] if tema.id in temas.TEMAS else [(tema.id, tema.nome, tema.descricao)])
    e.tema_atual = tema.id
    e.cal_mes, e.cal_dias = date(2026, 10, 1), {"2026-10-26", "2026-10-22", "2026-10-05"}
    return e


def empilha(imagens, vazio=12):
    folha = Image.new("RGBA", (max(i.width for i in imagens), sum(i.height + vazio for i in imagens) + vazio), FUNDO)
    y = vazio
    for im in imagens:
        folha.paste(im, (0, y))
        y += im.height + vazio
    return folha.convert("RGB")


def xadrez(im):
    fundo = Image.new("RGBA", im.size, (52, 54, 66, 255))
    for y in range(0, im.height, 8):
        for x in range(0, im.width, 8):
            if (x // 8 + y // 8) % 2:
                fundo.paste((64, 66, 80, 255), (x, y, x + 8, y + 8))
    fundo.alpha_composite(im)
    return fundo


def folha_de_camadas(tema, per, t):
    """Duas colunas, uma camada por painel, ampliadas como o widget mostra (Z)."""
    cam = tema.camadas(per, t)
    z = getattr(tema, "Z", 2)
    pw, ph = cam[0][2].width * z, (cam[0][2].height + 12) * z
    linhas = (len(cam) + 1) // 2
    folha = Image.new("RGBA", (pw * 2 + 36, ph * linhas + 12 * (linhas + 1)), FUNDO)
    for i, (nome, desc, im) in enumerate(cam):
        rotulo = Tela(im.width, 12)
        rotulo.texto(2, 2, f"{nome} · {desc}".upper(), hx("#fcecd1"))
        painel = Image.new("RGBA", (pw, ph), FUNDO)
        painel.alpha_composite(rotulo.im.resize((pw, 12 * z), Image.NEAREST))
        painel.paste(xadrez(im.resize((pw, im.height * z), Image.NEAREST)), (0, 12 * z))
        folha.paste(painel, (12 + (i % 2) * (pw + 12), 12 + (i // 2) * (ph + 12)))
    return folha.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tema", help="modulo:Classe, ex.: dino:Dino")
    ap.add_argument("saida")
    ap.add_argument("--t", default="", help="quadro por período, ex.: manha=157,tarde=28,noite=77")
    ap.add_argument("--gif", action="store_true")
    a = ap.parse_args()
    modulo, classe = a.tema.split(":")
    tema = getattr(importlib.import_module(f"diario.temas.{modulo}"), classe)()
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    ts = {p: 5 for p in PERIODOS}
    ts.update({k: int(v) for k, v in (kv.split("=") for kv in a.t.split(",") if kv)})

    quadros = []
    for per in PERIODOS:
        t0 = time.perf_counter()
        q = tema.quadro(estado(tema, per), ts[per])
        t1 = time.perf_counter()
        tema.quadro(estado(tema, per), ts[per] + 1)
        t2 = time.perf_counter()
        print(f"{per:6} {q.imagem.size}  1º quadro {1000 * (t1 - t0):5.0f} ms  seguinte {1000 * (t2 - t1):5.0f} ms")
        quadros.append(sobre_fundo(q.imagem))
    empilha(quadros).save(saida / "periodos.png")

    e = estado(tema, "manha")
    e.hover = "dia:2026-10-22"
    sobre_fundo(tema.calendario(e).imagem).save(saida / "calendario.png")
    minis = {i: t.miniatura(160) for i, t in temas.TEMAS.items()}
    minis[tema.id] = tema.miniatura(160)
    e.hover = f"tema:{tema.id}"
    sobre_fundo(tema.configuracoes(e, minis).imagem).save(saida / "config.png")

    if hasattr(tema, "camadas"):
        folha_de_camadas(tema, "manha", ts["manha"]).save(saida / "camadas.png")
    if a.gif:
        passo = 2
        for per in PERIODOS:
            qs = [sobre_fundo(tema.quadro(estado(tema, per), t).imagem).convert("RGB") for t in range(0, 160, passo)]
            pal = qs[0].quantize(colors=96, method=Image.MEDIANCUT)
            qs = [q.quantize(palette=pal, dither=Image.NONE) for q in qs]
            qs[0].save(saida / f"{per}.gif", save_all=True, append_images=qs[1:], loop=0,
                       duration=(tema.animacao_ms or 100) * passo)
    print("gravado em", saida.resolve(), "->", ", ".join(sorted(p.name for p in saida.iterdir())))


if __name__ == "__main__":
    main()
