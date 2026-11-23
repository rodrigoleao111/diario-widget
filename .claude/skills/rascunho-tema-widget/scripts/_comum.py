"""Funções comuns dos scripts de rascunho: achar o tema, montar o Estado de teste e renderizar um quadro."""
import importlib
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
from PIL import Image  # noqa: E402

from diario.temas.base import Estado, estado_exemplo  # noqa: E402

ESTADOS = ("exemplo", "cheio", "vazio", "passado")


def carrega(spec):
    """'modulo:Classe' (ex.: reforma:Reforma) -> instância do tema, sem registrá-lo em TEMAS."""
    modulo, classe = spec.split(":")
    return getattr(importlib.import_module(f"diario.temas.{modulo}"), classe)()


def estado(nome, periodo="manha", efeitos=None):
    """exemplo: o das miniaturas; cheio: 14 tópicos compridos e '… e mais 3'; vazio: dia sem registro;
    passado: outro dia, com o botão Hoje, um tópico sob o mouse e status de sucesso."""
    if nome == "exemplo":
        e = estado_exemplo(periodo)
    else:
        topicos = [(f"Tópico {i}: r1545{i:02d} — #1030{i:02d} texto bem comprido para testar o corte da linha", "" if i % 4 else "manual")
                   for i in range(1, 15)]
        if nome == "cheio":
            e = Estado(dia=date(2026, 10, 26), topicos=topicos, extra=3, periodo=periodo)
        elif nome == "vazio":
            e = Estado(dia=date(2026, 10, 26), periodo=periodo)
        elif nome == "passado":
            e = Estado(dia=date(2026, 10, 22), eh_hoje=False, topicos=topicos[:5], periodo=periodo, hover="linha:1",
                       status="Resumo gravado.", status_tipo="ok")
        else:
            raise SystemExit(f"estado desconhecido: {nome} (use {', '.join(ESTADOS)})")
    e.efeitos = dict(efeitos or {})
    return e


def efeitos_de(args):
    """['martelo=3', 'rosa=5'] -> {'martelo': 3, 'rosa': 5}"""
    return {k: int(v) for k, v in (a.split("=") for a in args or [])}


FUNDOS = {"area": (95, 111, 134), "claro": (233, 237, 243), "escuro": (28, 33, 43), "xadrez": None}


def sobre_fundo(imagem, fundo="area"):
    """Imagem de um tema de janela livre sobre uma "área de trabalho" de teste. Como o widget, trata alfa abaixo de 128
    como buraco e o resto como opaco (sem meio-termo)."""
    im = imagem.convert("RGBA")
    im.putalpha(im.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
    cor = FUNDOS[fundo]
    base = Image.new("RGBA", im.size, (0, 0, 0, 255))
    if cor:
        base.paste(cor + (255,), (0, 0, *im.size))
    else:
        for y in range(0, im.height, 8):
            for x in range(0, im.width, 8):
                base.paste((52, 54, 66, 255) if (x // 8 + y // 8) % 2 else (64, 66, 80, 255), (x, y, x + 8, y + 8))
    base.alpha_composite(im)
    return base.convert("RGB")


def renderiza(tema, e, t=40, fundo="area"):
    """(imagem RGB, milissegundos do primeiro quadro). Tema de janela livre (`Quadro.transparente`) sai sobre `fundo`
    (area, claro, escuro ou xadrez): confira nos dois extremos, claro e escuro."""
    t0 = time.perf_counter()
    q = tema.quadro(e, t)
    ms = 1000 * (time.perf_counter() - t0)
    return (sobre_fundo(q.imagem, fundo) if q.transparente else q.imagem.convert("RGB")), ms


def recorta(im, caixa, zoom, z):
    """Recorta `caixa` (x0, y0, x1, y1 em pixels de arte) e amplia para `zoom` pixels da tela por pixel de arte."""
    x0, y0, x1, y1 = (int(v) for v in caixa.split(","))
    c = im.crop((x0 * z, y0 * z, x1 * z, y1 * z))
    f = zoom / z
    return c.resize((round(c.width * f), round(c.height * f)), Image.NEAREST)
