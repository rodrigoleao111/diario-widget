import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# O banco fica fora do OneDrive de propósito: SQLite sincronizado pelo OneDrive corrompe.
DB = RAIZ / "diario.db"
SAIDA_MD = Path.home() / "Documents" / "Diario"

PROJETOS_CLAUDE = Path.home() / ".claude" / "projects"

# Coleta do SVN: com SVN_URL vazio ela é pulada.
SVN_EXE = r"C:\Program Files\TortoiseSVN\bin\svn.exe"
SVN_URL = ""
SVN_USER = os.environ.get("USERNAME", "")

# Pasta logo abaixo da raiz do disco que guarda checkouts de branch (C:\<pasta>\<branch>\<produto>\...): as sessões
# abertas dentro dela ganham o rótulo <branch>/<produto>. Vazio desliga.
PASTA_BRANCHES = ""

# Silêncio (min) que encerra um segmento de atividade, e tempo creditado depois do último sinal.
GAP_MIN = 25
CAUDA_MIN = 5

# (regex sobre o cwd da sessão, categoria) — a primeira que casar vence.
CATEGORIAS = [
    (r"AndroidStudioProjects|PythonProjects", "pessoal"),
    (r".", "trabalho"),
]

# Valores próprios (servidor SVN, pastas, categorias) ficam em diario/config_local.py, fora do Git: o que estiver lá
# substitui o que está acima.
try:
    from .config_local import *  # noqa: F401,F403
except ImportError:
    pass
