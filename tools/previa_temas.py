"""Renderiza os temas sem abrir janela, para conferir o visual: python tools/previa_temas.py <pasta de saída>.

Gera, para cada tema e período, o quadro principal, o calendário e a tela de configurações (PNG ampliado do jeito que o
widget mostra) e mede o tempo de cada quadro.
"""
import sys
import time
from datetime import date
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from diario import temas  # noqa: E402
from diario.temas.base import Estado, estado_exemplo  # noqa: E402


def sobre_fundo(q, fundo=(20, 22, 28, 255)):
    im = Image.new("RGBA", q.imagem.size, fundo)
    im.alpha_composite(q.imagem)
    return im.convert("RGB")


def main(saida):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    for tid, tema in temas.TEMAS.items():
        for per in ("manha", "tarde", "noite"):
            e = estado_exemplo(per)
            e.temas, e.tema_atual = temas.lista(), tid
            e.cal_mes, e.cal_dias = date(2026, 10, 1), {"2026-10-26", "2026-10-22", "2026-10-05"}
            t0 = time.perf_counter()
            q = tema.quadro(e, 5)
            t1 = time.perf_counter()
            for t in range(1, 4):
                tema.quadro(e, 5 + t)
            t2 = time.perf_counter()
            print(f"{tid:9} {per:6} {q.imagem.size}  1º quadro {1000 * (t1 - t0):6.0f} ms   seguintes "
                  f"{1000 * (t2 - t1) / 3:5.0f} ms")
            sobre_fundo(q).save(saida / f"{tid}_{per}.png")
            if per == "manha":
                e.eh_hoje = False
                sobre_fundo(tema.quadro(e, 5)).save(saida / f"{tid}_passado.png")
                e.hover = "dia:2026-10-22"
                sobre_fundo(tema.calendario(e)).save(saida / f"{tid}_calendario.png")
                e.hover = "tema:retro"
                minis = {i: t.miniatura(160) for i, t in temas.TEMAS.items()}
                sobre_fundo(tema.configuracoes(e, minis)).save(saida / f"{tid}_config.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "previa")
