"""Contrato dos temas do widget.

O widget não desenha nada sozinho: monta um `Estado` (dia, tópicos, status, hover...) e pede ao tema um `Quadro`, que é a
imagem da janela inteira mais as regiões clicáveis. Assim um tema pode ter qualquer layout, e o calendário e a tela de
configurações também são desenhados pelo tema.

Para criar um tema novo: subclasse de `Tema` em diario/temas/, com `id`, `nome`, `descricao`, e os métodos `quadro`,
`calendario` e `configuracoes`; depois registrar em diario/temas/__init__.py.
"""
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from PIL import Image


@dataclass
class Regiao:
    """Área clicável. `nome` é a ação ('fechar', 'dia:2026-10-26', 'tema:ilha', 'linha:2'...)."""
    nome: str
    caixa: tuple  # x0, y0, x1, y1 em pixels da janela
    dica: str = ""
    cursor: str = "hand2"  # "" deixa o cursor normal


@dataclass
class Quadro:
    imagem: Image.Image  # RGBA, do tamanho exato da janela
    regioes: list = field(default_factory=list)
    entrada: tuple = None  # caixa onde o widget põe o campo de texto de verdade (Tk), se o quadro tiver um
    estilo_entrada: dict = field(default_factory=dict)  # bg, fg, cursor, fonte
    transparente: bool = False  # True: pixels com alfa < 128 viram buraco na janela (formato livre)
    fundo: str = "#000000"  # cor de fundo da janela quando não é transparente


@dataclass
class Estado:
    dia: date
    eh_hoje: bool = True
    topicos: list = field(default_factory=list)  # [(texto, tipo)], tipo: "" | "manual" | "aviso" | "resumir"
    extra: int = 0  # tópicos que não couberam
    resumindo: bool = False  # o resumo do dia está sendo gerado: o botão do tópico "resumir" vira "resumindo…"
    refazer: bool = False  # o dia já tem resumo, mas ganhou atividade depois: o botão do tópico "resumir" vira "atualizar"
    status: str = ""  # mensagem de status; vazia = dica de uso
    status_tipo: str = "dica"  # dica | ok | info | erro
    hover: str = ""  # nome da região sob o mouse
    periodo: str = "manha"  # manha | tarde | noite
    cal_mes: date = None  # primeiro dia do mês mostrado no calendário
    cal_dias: set = field(default_factory=set)  # dias (AAAA-MM-DD) com registro
    temas: list = field(default_factory=list)  # [(id, nome, descricao)] para a tela de configurações
    temas_papel: set = field(default_factory=set)  # ids dos temas de `temas` que são papel de parede (os outros são do widget)
    tema_atual: str = ""
    barra: list = field(default_factory=list)  # itens da coluna "Barra de tarefas" das configurações; ver ITENS_BARRA
    efeitos: dict = field(default_factory=dict)  # {nome: quadros desde o clique} dos efeitos de clique em andamento


# ITENS_BARRA: cada item de `Estado.barra` é (tipo, regiao, rotulo, valor, ativo), desenhado de cima para baixo na coluna da
# direita das configurações; com `ativo` False o item sai apagado e sem região de clique. Tipos:
#   titulo  título da coluna                      texto   aviso (rotulo), quebrado em linhas
#   sub     subtítulo de um grupo de opções       espaco  só um respiro
#   estado  linha da lista de estados da barra: valor é a aparência em vigor nele, `ativo` diz se é o escolhido
#   marca   caixa de marcar (valor: marcada)      opcao   botão de rádio (valor: escolhido)
#   cores   valor é [(regiao, "rrggbb", escolhida)], amostras lado a lado
#   alfas   valor é [(regiao, "25%", escolhido)], botões lado a lado
#   passo   rotulo e valor (texto) entre os botões regiao + ":-" e regiao + ":+"
ESCALA = 1.0  # escala de DPI do Windows; o widget ajusta ao abrir (só o tema Clássico, que usa fontes de verdade, a usa)
DICA_ENTRADA = "1h30 reunião @Projeto #ticket  ·  Enter lança"
DICAS = {"fechar": "Fechar o widget", "config": "Configurações: escolher o tema",
         "relatorio": "Abrir o relatório do dia no Bloco de Notas",
         "atualizar": "Atualizar: coletar agora as sessões do Claude Code do dia exibido",
         "proximo": "Ir para o dia seguinte", "calendario": "Escolher o dia no calendário",
         "anterior": "Ir para o dia anterior", "hoje": "Voltar para o dia de hoje",
         "resumir": "Resumir o dia: o Claude escreve o parágrafo e os tópicos (leva alguns instantes)",
         "refazer": "Atualizar o resumo: o dia ganhou atividade depois de ele ser escrito (leva alguns instantes)"}
RESUMIR, ATUALIZAR, RESUMINDO = "[resumir]", "[atualizar]", "[resumindo…]"  # rótulos do botão do tópico "resumir"
SEMANA, SEMANA_ROTULO = "[resumir semana]", "Resumir semana"  # botão do calendário (SEMANA: na fonte pixel; ROTULO: no Clássico)


def semana_do_dia(dia):
    """(segunda, último dia útil considerado) da semana de `dia`: do domingo para trás até a segunda, sem passar de hoje."""
    seg = dia - timedelta(days=dia.weekday())
    return seg, min(seg + timedelta(days=6), date.today())


def dica_semana(dia):
    de, ate = semana_do_dia(dia)
    return f"Resumir a semana de {de:%d/%m} a {ate:%d/%m} e abrir as horas no Bloco de Notas (pode levar alguns minutos)"
# ordem dos botões da esquerda para a direita
BOTOES = ["anterior", "calendario", "proximo", "atualizar", "relatorio", "config", "fechar"]
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro",
         "dezembro"]


def periodo_do_horario(agora=None):
    """manha das 6h às 12h, tarde das 12h às 18h, noite o resto. DIARIO_PERIODO força um (para testar)."""
    forcado = os.environ.get("DIARIO_PERIODO")
    if forcado in ("manha", "tarde", "noite"):
        return forcado
    h = (agora or datetime.now()).hour
    return "manha" if 6 <= h < 12 else "tarde" if 12 <= h < 18 else "noite"


def estado_exemplo(periodo="manha"):
    """Estado fixo usado nas miniaturas da tela de configurações."""
    return Estado(dia=date(2026, 10, 26), periodo=periodo, status=DICA_ENTRADA, topicos=[
        ("Resumo do dia ainda não escrito", "resumir"), ("Sessões em Portal", ""),
        ("r20507 — #12345 Guia analisado", ""), ("r20513 — #12346 Commits revisados", ""),
        ("Reunião com CS (1h)", "manual")])


def grupos_de_temas(e):
    """[(título, [(id, nome, descricao)])] da tela de configurações: os temas do widget e os de papel de parede, sem os
    grupos vazios."""
    grupos = [("Widget", [t for t in e.temas if t[0] not in e.temas_papel]),
              ("Papel de parede", [t for t in e.temas if t[0] in e.temas_papel])]
    return [g for g in grupos if g[1]]


class Tema:
    id = ""
    nome = ""
    descricao = ""
    papel = False  # True: tema de papel de parede (janela no fundo, cobrindo a tela); vai no grupo "Papel de parede"
    animacao_ms = None  # None: o tema não anima; senão, intervalo entre quadros
    animacao_ociosa_ms = None  # se definido, o tema anda em tempo real e, sem efeito de clique rodando, o widget só o redesenha a cada tanto
    hover_no_status = False  # True: passar o mouse num tópico mostra o texto inteiro na linha de status; senão, num balão
    cores_balao = ("#2a3243", "#e6e9ef", "#3a4254")  # fundo, texto, borda dos balões de ajuda
    efeitos = {}  # {nome: duração em quadros} dos efeitos que o clique dispara; o tema registra a região "efeito:<nome>"

    def quadro(self, e: Estado, t: int) -> Quadro:
        raise NotImplementedError

    def partes(self, e: Estado, t: int):
        """Atualização parcial da animação: [(imagem RGB, x, y)] dos pedaços da última imagem que mudaram no quadro `t`, em
        pixels da janela; `None` quando é preciso um `quadro` inteiro (estado do diário mudou, efeito de clique rodando...)."""
        return None

    def calendario(self, e: Estado) -> Quadro:
        raise NotImplementedError

    def configuracoes(self, e: Estado, miniaturas: dict) -> Quadro:
        raise NotImplementedError

    def miniatura(self, largura):
        """Prévia reduzida do tema (com dados de exemplo), para a tela de configurações."""
        cache = self.__dict__.setdefault("_minis", {})
        periodo = periodo_do_horario()
        if (largura, periodo) not in cache:
            q = self.quadro(estado_exemplo(periodo), 3)
            fundo = Image.new("RGBA", q.imagem.size, (20, 22, 28, 255))
            fundo.alpha_composite(q.imagem)
            alt = round(fundo.height * largura / fundo.width)
            cache[(largura, periodo)] = fundo.convert("RGB").resize((largura, alt), Image.LANCZOS)
        return cache[(largura, periodo)]
