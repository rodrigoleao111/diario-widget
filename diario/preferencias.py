"""Preferências do widget (posição e tema), em widget.json ao lado do banco. Não vai para o git."""
import json
import os

from . import config

# DIARIO_PREVIEW=1 abre uma segunda instância de teste: outro arquivo, sem trava de instância única nem ícone na bandeja
PREVIEW = os.environ.get("DIARIO_PREVIEW") == "1"
ARQUIVO = config.RAIZ / ("widget_preview.json" if PREVIEW else "widget.json")


def ler():
    try:
        d = json.loads(ARQUIVO.read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def salvar(**campos):
    """Atualiza só os campos dados, preservando os demais (posição e tema vivem no mesmo arquivo)."""
    d = ler()
    d.update(campos)
    try:
        ARQUIVO.write_text(json.dumps(d))
    except OSError:
        pass
