"""Temas do widget. Para acrescentar um: crie a classe em diario/temas/, herdando de `Tema` (ou de `TemaPixel`), e a
inclua em TEMAS. PADRAO é o tema de quem ainda não escolheu. Passo a passo em docs/criar-um-tema.md."""
from .argonath import Argonath
from .argonath_papel import ArgonathPapel
from .castelo import Castelo
from .classico import Classico
from .dino import Dino
from .ilha import Ilha
from .retro import Retro

TEMAS = {t.id: t for t in (Ilha(), Retro(), Dino(), Castelo(), Argonath(), ArgonathPapel(), Classico())}
PADRAO = "ilha"


def obter(tema_id):
    """O tema pedido, ou o padrão se o id não existir (por exemplo, um tema removido)."""
    return TEMAS.get(tema_id) or TEMAS[PADRAO]


def lista():
    """[(id, nome, descricao)] na ordem da tela de configurações."""
    return [(t.id, t.nome, t.descricao) for t in TEMAS.values()]
