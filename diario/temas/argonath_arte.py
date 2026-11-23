"""Arte do Argonath de papel de parede: um gerador por camada da cena (céu, nuvens, astros, montanhas, névoa, estátuas, rio,
canoas, margem e pedestal) e os efeitos de clique do céu e da água, todos desenhados direto no pixel de arte.

A cena tem 640x360 pixels de arte e o tema (argonath_papel.py) a amplia por um fator inteiro (3 em 1920x1080). Tudo, do céu à
tábua, usa o mesmo pixel; antes o cenário usava blocos de 2x2, o dobro do pixel da tábua. Com a resolução dobrada há espaço
para detalhe, mas a regra é a clareza: formas grandes e poucos tons, pontilhado em blocos de 2x2 e nenhum pixel solto que
vire ruído.

- céu em 40 tons com divisas que ondulam de leve e pontilhado só no miolo de cada faixa; nuvens como as da pintura (bojo e
  cauda, quatro tons de areia);
- a cordilheira do print aprovado pelo usuário (cinco fileiras de cumes largos, do fundo rosa-lavanda à frente
  cinza-arroxeada, com névoa entre elas), recolorida para a manhã e a noite; névoa em níveis, nunca em xadrez binário;
- as estátuas da própria pintura, ampliadas com Scale2x (que suaviza as diagonais sem inventar cor) e com detalhe de pedra:
  fio de luz nas bordas voltadas para a luz, poucas rachaduras e musgo, e a base molhada;
- rio de poucas formas grandes (faixas de tom e riscos de onda com a sombra da crista), o reflexo das paredes, do sol e da
  lua e canoas com remadores; a névoa rente à água, animada, que passa na frente da estátua da esquerda; a margem é um
  gramado até a borda de baixo, com lâminas, flores e juncos.

Tarde e noite: o céu, as nuvens, a água e a cordilheira (`ATMOS`) têm paleta própria; o resto (névoa, paredes, margem, canoas, tábua) é a
arte da manhã multiplicada pela cor da hora (`argonath.grade`). Luz: do alto e da esquerda.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from ..acabamento import borda_colorida, pedra, selout, tinge
from ..pixel import TRANSPARENTE, Tela, hx, largura, mix
from . import argonath as A
from .argonath import BW, CEU, LINHAS_BASE, LINHAS_MEIO, LINHAS_TOPO, OL, PEDRA

WP, HP = 640, 360  # cena em pixels de arte
RIO_P = 56  # altura do rio
YR = HP - RIO_P  # linha em que o rio começa
MEIO = 50  # linhas do tronco das estátuas (a referência tem 56): o topo das cabeças fica a 26 px do alto
PX, PE = 368, 306  # x da tábua e linha do chão em que ela se apoia (pixels de arte)
LX, RX = (4, 58), (78, 150)  # colunas da referência de cada parede: o miolo do vão (58 a 78) fica de fora e vira névoa
ASTRO = {"tarde": (208, 205), "noite": (224, 76)}  # centro do sol e da lua (pixels de arte): o reflexo cai na água à vista; o sol
# fica meio escondido atrás do primeiro cume, como no print aprovado
# contorno da margem (x, y na grade de 2x2, o desenho original): do pé da estátua da direita, descendo em diagonal até a água
TOPO = [(111, 180), (116, 176), (122, 172), (130, 167), (139, 162), (150, 157), (162, 153), (175, 150), (190, 148),
        (210, 147), (235, 147), (260, 146), (280, 146), (300, 145), (320, 144)]
M = dict(  # a margem: terra (e0 sombra funda ... e4 realce) e grama (g0 ... g4), as sombras puxam para o azul
    e0=hx("#272b35"), e1=hx("#444750"), e2=hx("#666660"), e3=hx("#8d8672"), e4=hx("#bfb18c"),
    g0=hx("#2c4546"), g1=hx("#456550"), g2=hx("#68875a"), g3=hx("#9bb374"), g4=hx("#cfdc9c"),
    ol2=hx("#1b2029"), sh=hx("#232a38"), hi=hx("#e6dcb8"), s1=hx("#666660"), s2=hx("#444750"), s3=hx("#8d8672"))
ESPUMA, AGUA_CLARA, AGUA_ESCURA = hx("#e4f0ee"), hx("#a3c9cf"), (30, 50, 58)
NUVENS = ((112, 50, 84, 36, 20), (72, 34, 262, 8, 21), (100, 44, 330, 70, 22), (68, 32, 440, 30, 23),
          (86, 38, 176, 124, 24))  # (largura, altura, x, y, semente) das cinco nuvens, em pixels de arte
_CACHE = {}


def altura_topo(x):
    """Linha (da grade de 2x2) do topo da margem na coluna x da grade; interpola o contorno TOPO."""
    pts = sorted(TOPO)
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return ya + (yb - ya) * (x - xa) / (xb - xa)
    return pts[-1][1]


# primeira coluna (px) em que a margem já cobre a linha de cima do rio, com folga para o ruído do contorno e os juncos: à
# direita dela nada se mexe, então a atualização parcial da água só precisa da metade esquerda da faixa
X_RIO = next(x for x in range(TOPO[0][0], WP // 2) if altura_topo(x) <= YR // 2) * 2 + 10


def bayer(n):
    """Matriz de Bayer n x n (n potência de 2): limiares de pontilhado ordenado, de 0 a n*n-1."""
    if n == 2:
        return [[0, 2], [3, 1]]
    h = n // 2
    b = bayer(h)
    q = [[0, 2], [3, 1]]
    return [[4 * b[y % h][x % h] + q[y // h][x // h] for x in range(n)] for y in range(n)]


B8 = bayer(8)


def limiar(x, y):
    """Limiar de pontilhado do pixel (x, y), entre 0 e 1."""
    return (B8[y % 8][x % 8] + .5) / 64


def fbm(semente, escalas=(137, 61, 29, 13, 5)):
    """Curva suave e irregular, de -1 a 1, soma de senos de períodos diferentes (a amplitude cai com a frequência)."""
    r = random.Random(semente)
    fases = [r.uniform(0, math.tau) for _ in escalas]
    amps = [1 / (i + 1) ** 1.1 for i in range(len(escalas))]
    tot = sum(amps)
    return lambda x: sum(a * math.sin(math.tau * x / e + f) for a, e, f in zip(amps, escalas, fases)) / tot


def limiar2(x, y):
    """Limiar de pontilhado em blocos de 2x2 px: pontos maiores, que leem como textura e não como ruído."""
    return limiar(x // 2, y // 2)


# ------------------------------------------------------------------ céu
TONS_CEU = [hx(c) for c in ("#6b96a0", "#79a1a9", "#86aeb4", "#90b6bb", "#9bc1c5", "#a9ced1", "#b9dad8", "#cbe5e0")]


def tons_ceu(per, n=20):
    """Os n tons do céu, de cima para o horizonte. Parte dos oito tons de referência (na manhã, os escolhidos à mão; na tarde
    e na noite, a rampa das três cores do Argonath da janela, com o horizonte um pouco mais claro, como o brilho do poente ou
    da lua) e interpola entre eles: com 20 tons a diferença de um para o próximo é pequena demais para se ver como degrau."""
    if per == "manha":
        base = TONS_CEU
    else:
        a, b, c = (hx(v) for v in CEU[per])
        base = [mix(a, b, i / 7 / .6) if i / 7 <= .6 else mix(b, c, (i / 7 - .6) / .4) for i in range(8)]
        base[-1] = mix(base[-1], hx("#fff0c8") if per == "tarde" else hx("#4a5c94"), .3)
    out = []
    for i in range(n):
        u = i / (n - 1) * 7
        k = min(int(u), 6)
        out.append(mix(base[k], base[k + 1], u - k))
    return out


def ceu_fino(w, h, per="manha", n=20, ondula=False, riscos=True):
    """Céu de `n` tons. A divisa entre dois tons vizinhos, que quase não se distinguem, é pontilhada em blocos de 2x2 numa faixa
    estreita, então a transição de cima até o horizonte sai suave, sem degraus nem textura. Só uns riscos longos e quase
    invisíveis (como os da pintura) quebram a uniformidade.

    O papel de parede usa 40 tons, divisas que ondulam de leve (3 a 5 px, período longo: divisa reta de céu é banding, ver a skill
    pixel-art, anti-padrão 117) e o pontilhado só no quarto central de cada faixa, sem riscos. As cenas de Valfenda usam o padrão."""
    T = Tela(w, h)
    tons = tons_ceu(per, n)
    ru, ru2 = fbm(301, (190, 97)), fbm(302, (260, 130))
    for y in range(h):
        for x in range(w):
            yy = y + (3.5 * ru(x + .4 * y) + 1.5 * ru2(x * .6) if ondula else 0)
            f = min(n - 1 - 1e-6, max(0.0, yy / (h - 1) * (n - 1)))
            i = int(f)
            frac = (f - i - .375) / .25 if ondula else min(1, max(0, (f - i - .3) / .4))  # pontilhado só no miolo da faixa
            T.px(x, y, tons[i + 1] if frac > limiar2(x, y) else tons[i])
    if not riscos:
        return T.im
    r = random.Random(7)
    for _ in range(36):  # riscos: poucos, longos, de 1 px de altura, só uma sombra mais clara ou mais escura que o céu
        y, x, comp = r.randrange(h), r.randrange(w), r.randint(40, 150)
        base = T.im.getpixel((min(x, w - 1), y))
        T.rect(x, y, comp, 1, mix(base, hx("#ffffff"), .035) if r.random() < .55 else mix(base, hx("#10203a"), .03))
    return T.im


# ------------------------------------------------------------------ nuvens
NUVEM_PAL = {  # hi, luz, m1, m2, s1: da luz à sombra. Manhã: areia, como na pintura; tarde: rosa e laranja; noite: azul
    "manha": dict(hi=hx("#fdf3dc"), luz=hx("#f6e8c8"), m1=hx("#ecd5a6"), m2=hx("#e0c08a"), s1=hx("#cfa86c")),
    "tarde": dict(hi=hx("#fff1de"), luz=hx("#ffdcb8"), m1=hx("#f8c298"), m2=hx("#ee9c84"), s1=hx("#d6807c")),
    "noite": dict(hi=hx("#8a98c4"), luz=hx("#6c7cab"), m1=hx("#5a6a9a"), m2=hx("#4b5a8a"), s1=hx("#3a4872"))}


def nuvem_fina(w, h, semente, per="manha"):
    """Nuvem como as da pintura de referência: assimétrica, com um bojo alto de dois ou três lobos de um lado e uma cauda que
    afina até uma ponta do outro, base reta no bojo e inclinada na cauda. Quatro tons de areia em zonas grandes e na diagonal
    (a luz vem de cima e da esquerda): claro no alto à esquerda, escuro embaixo à direita, com uns lobos internos mais claros
    no bojo para dar volume sem desenhar um contorno em cada lobo. Sem pontilhado nem contorno. A cauda vai para a esquerda
    ou para a direita conforme a semente."""
    r = random.Random(semente)
    c = NUVEM_PAL[per]
    base = h - 3
    alto = base - 2
    bojo = round(w * r.uniform(.48, .55))
    n = r.choice((2, 3, 3))
    arcos = []  # (centro, meia-largura, altura) dos lobos do bojo
    maior = r.randrange(n)
    for i in range(n):
        meia = round(bojo * r.uniform(.3, .4))
        cx = round(meia + (bojo - 2 * meia) * i / max(1, n - 1))
        arcos.append((cx, meia, min(alto, meia * r.uniform(1.5, 1.85)) * (1.0 if i == maior else r.uniform(.7, .88))))
    cauda0 = alto * r.uniform(.4, .5)
    pos_calombo = r.uniform(.3, .45)

    def topo(x):
        y = base
        for cx, meia, hh in arcos:
            dx = (x - cx) / meia
            if abs(dx) <= 1:
                y = min(y, base - hh * (1 - abs(dx) ** 2.2) ** .4545)  # perfil cheio: ombros redondos e topo largo
        if x >= bojo * .75:  # a cauda: desce afinando, com um calombo pequeno no caminho
            u = min(1.0, (x - bojo * .75) / max(1, w - bojo * .75))
            ht = cauda0 * (1 - u) ** 1.3 + cauda0 * .3 * math.exp(-((u - pos_calombo) / .12) ** 2)
            y = min(y, base - ht)
        return y

    def fundo(x):  # base reta no bojo, subindo em diagonal na cauda
        return base - max(0, round((x - w * .6) * .13))

    m = Image.new("L", (w, h), 0)
    mp = m.load()
    for x in range(w):
        t, f = int(round(topo(x))), fundo(x)
        for y in range(max(0, t), min(h, f + 1)):
            mp[x, y] = 255
    luz = Image.new("L", (w, h), 0)  # lobos internos mais claros, no lado da luz de cada lobo do bojo
    dl = ImageDraw.Draw(luz)
    for cx, meia, hh in arcos:
        dl.ellipse([cx - meia * .55 - meia * .5, base - hh * .75 - hh * .28, cx - meia * .55 + meia * .5, base - hh * .75 + hh * .28],
                   fill=255)
    if r.random() < .5:  # cauda para a esquerda: espelha a forma inteira, e a luz continua vindo da esquerda
        m, luz = ImageOps.mirror(m), ImageOps.mirror(luz)
    mp, lp = m.load(), luz.load()
    for _ in range(2):  # tira os pixels soltos (conta antes de remover, para a remoção não se propagar)
        soltos = [(x, y) for y in range(h) for x in range(w)
                  if mp[x, y] and sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                                      if 0 <= x + dx < w and 0 <= y + dy < h and mp[x + dx, y + dy]) < 2]
        for x, y in soltos:
            mp[x, y] = 0
    out = Image.new("RGBA", (w, h), TRANSPARENTE)
    o = out.load()
    for x in range(w):
        ys = [y for y in range(h) if mp[x, y]]
        if not ys:
            continue
        top, bot = ys[0], ys[-1]
        for y in ys:
            t = (y - top) / (bot - top + 1) + .22 * (x / w - .5)  # fundo de cada coluna: as zonas de tom ficam na diagonal
            cor = c["luz"] if t < .28 else c["m1"] if t < .56 else c["m2"] if t < .82 else c["s1"]
            if lp[x, y] and t < .7:
                cor = c["luz"]
            if y == top and cor == c["luz"]:
                cor = c["hi"]  # só o topo das partes claras recebe o fio de luz
            o[x, y] = cor
    return out.crop(out.getbbox())  # sem a margem vazia: o canto do sprite é o canto da nuvem


# ------------------------------------------------------------------ montanhas e bruma
EFEITO_OLHO = 48  # duração do efeito de clique no Olho, em quadros: abre, olha e varre com o feixe, fecha


OLHO = (157, 186)  # o centro do Olho: a viseira clara da torre do print (a torre vem no recurso da cordilheira)
CABECA_TORRE = (156, 182)  # um pixel da cabeça da torre, de onde sai a cor que cobre a viseira quando o Olho abre
ESCALA_TORRE = .72  # o Olho e o efeito de clique do Olho nesta escala (1 era o tamanho da torre desenhada antiga)


def _k(v):
    """Uma medida da torre ou do Olho na escala da torre."""
    return round(v * ESCALA_TORRE)


def nivel_nevoa(x, y, f, n):
    """Nível (0 a n) da névoa no pixel: f de 0 a 1 vira n níveis, e a divisa entre dois níveis vizinhos é pontilhada em 2x2 só
    no quarto central da faixa (o resto de cada nível é liso: pontilhado que vira campo pede um nível a mais)."""
    v = max(0.0, min(n - 1e-6, f * n))
    i = int(v)
    return i + (1 if (v - i - .375) / .25 > limiar2(x, y) else 0)


def posicao_olho():
    """(coluna, linha) do centro do Olho, na viseira da torre."""
    return OLHO


def cor_torre(per):
    """A cor da cabeça da torre na hora `per` (a que se vê na tela): cobre a viseira quando o Olho abre."""
    return cristas_finas(per).getpixel(CABECA_TORRE)


BRILHO_OLHO = {"manha": .3, "tarde": .75, "noite": 1.0}  # força do halo do Olho em cada hora


def _olho(T, cx, cy, abertura=1.0, pupila=(0, 0), pulso=0.0, brilho=1.0):
    """O Olho aberto em T. `abertura` (0 a 1) é quanto a pálpebra levantou: a amêndoa cresce de uma fenda até a altura toda.
    O halo vermelho cresce com `pulso` e com `brilho` (a hora do dia). A pupila é uma lente vertical, estreita nas pontas, com
    um fio vermelho dos lados, e se desloca com `pupila` (dx, dy): quando o Olho olha de lado ela afina, como numa vista em
    perspectiva."""
    raio, forca = _k(26 + 10 * pulso), 70 + 30 * pulso
    for i in range(10):  # halo: anéis com a opacidade subindo aos poucos para o centro
        rr = raio * (1 - i / 10)
        T.d.ellipse([cx - rr, cy - rr * .8, cx + rr, cy + rr * .8],
                    fill=(255, 96, 32, round(forca * ((i + 1) / 10) ** 1.6 * brilho * abertura)))
    a, k = 4 * abertura * ESCALA_TORRE, _k
    T.poly([(cx - k(8), cy), (cx - k(3), cy - a), (cx + k(3), cy - a), (cx + k(8), cy), (cx + k(3), cy + a), (cx - k(3), cy + a)],
           hx("#ff7a1c"))
    T.poly([(cx - k(6), cy), (cx - k(2), cy - .75 * a), (cx + k(2), cy - .75 * a), (cx + k(6), cy), (cx + k(2), cy + .75 * a),
            (cx - k(2), cy + .75 * a)], hx("#ffc84a"))
    if abertura >= .55:
        px, py = pupila
        meio = round(4 * abertura * ESCALA_TORRE)
        for dy in range(-meio, meio + 1):
            larg = 3 if abs(dy) <= 1 else 2 if abs(dy) <= meio - 1 else 1  # lente: larga no meio, em ponta nas extremidades
            larg = max(1, larg - (1 if abs(px) >= 3 else 0))  # olhando de lado, a pupila afina
            esq = cx + px - larg // 2
            T.rect(esq, cy + py + dy, larg, 1, hx("#140a0a"))
            if abs(dy) <= meio - 2 and meio >= 3:
                T.px(esq - 1, cy + py + dy, hx("#b02a0a"))  # o fio vermelho em volta da pupila
                T.px(esq + larg, cy + py + dy, hx("#b02a0a"))


def olho_fino(per):
    """O Olho em repouso (WP x HP, transparente): fechado, sem brasa nem halo. A camada fica vazia: o Olho fechado é a viseira
    clara da torre do print, que vem no recurso da cordilheira."""
    return Tela(WP, HP).im  # o Olho fechado é a viseira clara da própria torre do print


def olho_fx(per, f):
    """O efeito de clique no Olho, no quadro f (WP x HP, transparente): a pálpebra abre nos 6 primeiros quadros, o Olho olha
    de um lado ao outro, e um feixe de luz sai dele e varre a paisagem de baixo à esquerda para baixo à direita; a pupila
    acompanha a direção do feixe (olha para onde a luz vai, afinando quando olha de lado). Nos 6 últimos quadros o feixe
    some e a pálpebra fecha. Cobre o Olho fechado, que fica atrás."""
    dur = EFEITO_OLHO
    abertura = min(1.0, f / 6) * min(1.0, (dur - 1 - f) / 6)
    feixe = min(1.0, max(0.0, (f - 6) / 6)) * min(1.0, max(0.0, (dur - 12 - f) / 6))
    s = min(1.0, max(0.0, (f - 6) / (dur - 18)))
    ang = math.radians(118 - 62 * s * s * (3 - 2 * s))  # de baixo à esquerda para baixo à direita
    cx, cy = posicao_olho()
    T = Tela(WP, HP)
    k = _k
    T.poly([(cx - k(9), cy), (cx - k(4), cy - k(5)), (cx + k(4), cy - k(5)), (cx + k(9), cy), (cx + k(4), cy + k(5)),
            (cx - k(4), cy + k(5))], cor_torre(per))
    for comprimento, meia, alfa in ((320, 5.0, 26), (240, 3.6, 46), (150, 2.2, 78)):
        pts = [(cx, cy)] + [(cx + comprimento * math.cos(ang + s_ * math.radians(meia)),
                             cy + comprimento * math.sin(ang + s_ * math.radians(meia))) for s_ in (-1, 1)]
        T.d.polygon(pts, fill=(255, 190, 80, round(alfa * feixe)))
    px = max(-_k(4), min(_k(4), round(_k(8) * math.cos(ang))))
    _olho(T, cx, cy, abertura, (px, round(1.4 * math.sin(ang))), pulso=abertura, brilho=BRILHO_OLHO[per])
    return T.im


# A cordilheira vem do print aprovado pelo usuário (10/11/2026), já na grade da cena, em 17 cores e sem pixel solto:
# diario/recursos/argonath_cordilheira.png, feito por arte/referencias/argonath/preparar_cordilheira.py. As cores do print são as
# da tarde; na manhã e na noite cada cor vira a da rampa do período na mesma posição de luminosidade (o fundo claro e enevoado, a
# frente escura). `nevoa` é também a cor da névoa da água; o brilho do horizonte é o da última linha da cordilheira
# (`cor_horizonte`). A água da tarde puxa para o lavanda-rosado do print (`AGUA_TARDE`).
ATMOS = {
    "manha": dict(rampa=("#4a6378", "#7590a2", "#9fb8c4", "#bcd2d6", "#dfeae6"), nevoa="#dfeae6"),
    "tarde": dict(rampa=None, nevoa="#e3bcb3"),
    "noite": dict(rampa=("#141b3a", "#262f5c", "#36437a", "#425083", "#4b5a8c"), nevoa="#4b5a8c"),
}
AGUA_TARDE = ((196, 112, 128), .55)  # cor e força com que a água da tarde puxa para o lavanda-rosado do print
_CORDILHEIRA = []


def _luminosidade(c):
    r, g, b = (v / 255 for v in c[:3])
    return .2126 * r + .7152 * g + .0722 * b


def cristas_finas(per="manha"):
    """A cordilheira como no print: cinco fileiras de cumes triangulares largos, do fundo rosa-lavanda que quase some no céu à
    frente cinza-arroxeada, com a névoa clara atrás de cada crista e no pé. Na tarde, as cores do print; nas outras horas, a
    mesma imagem recolorida pela rampa do período (a cor de cada tom vem da posição da luminosidade dele entre o mais escuro e
    o mais claro). O pé das montanhas desce até a linha d'água como no print, com o brilho do horizonte na última linha. A torre do print vem junto, sobre o pico de rocha escura dela. Fica em cache por hora."""
    k = ("cordilheira", per)
    if k in _CACHE:
        return _CACHE[k]
    if not _CORDILHEIRA:
        _CORDILHEIRA.append(Image.open(Path(__file__).parent.parent / "recursos" / "argonath_cordilheira.png").convert("RGBA"))
    im = _CORDILHEIRA[0].copy()
    rampa = ATMOS[per]["rampa"]
    if rampa:
        cores = {c for c in im.getdata() if c[3]}
        lums = {c: _luminosidade(c) for c in cores}
        lo, hi = min(lums.values()), max(lums.values())
        anc = [hx(h) for h in rampa]
        mapa = {}
        for c, L in lums.items():
            t = (L - lo) / (hi - lo) * (len(anc) - 1)
            i = min(int(t), len(anc) - 2)
            mapa[c] = mix(anc[i], anc[i + 1], t - i)[:3] + (c[3],)
        im.putdata([mapa.get(c, c) for c in im.getdata()])
    _CACHE[k] = im
    return im


def cor_horizonte(per):
    """A cor do brilho do horizonte na hora `per`: a mediana da última linha da cordilheira, rente à água. A água e a névoa
    animada nascem desta cor, então a emenda não aparece."""
    k = ("horizonte", per)
    if k not in _CACHE:
        im = cristas_finas(per)
        cs = sorted((im.getpixel((x, YR - 1)) for x in range(100, 330)), key=lambda c: sum(c[:3]))
        _CACHE[k] = cs[len(cs) // 2][:3] + (255,)
    return _CACHE[k]


def scale2x(im):
    """Scale2x (AdvMAME2x): dobra a resolução e suaviza as diagonais sem criar cores novas."""
    w, h = im.size
    s = im.load()
    out = Image.new("RGBA", (w * 2, h * 2), TRANSPARENTE)
    o = out.load()
    for y in range(h):
        for x in range(w):
            p = s[x, y]
            a = s[x, y - 1] if y > 0 else p
            b = s[x + 1, y] if x < w - 1 else p
            c = s[x - 1, y] if x > 0 else p
            d = s[x, y + 1] if y < h - 1 else p
            o[2 * x, 2 * y] = a if (c == a and c != d and a != b) else p
            o[2 * x + 1, 2 * y] = b if (a == b and a != c and b != d) else p
            o[2 * x, 2 * y + 1] = c if (d == c and d != b and c != a) else p
            o[2 * x + 1, 2 * y + 1] = d if (b == d and b != a and d != c) else p
    return out


def realca(im, k=.65):
    """Realce de contorno e detalhe: cada pixel opaco se afasta da média do 3x3 em volta (só dos vizinhos opacos), o que firma
    as divisas entre as dobras do manto, o elmo e o rosto sem inventar tons fora da paleta da pintura."""
    w, h = im.size
    px = im.load()
    out = im.copy()
    o = out.load()
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if not p[3]:
                continue
            soma, n = [0, 0, 0], 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if 0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3]:
                        q = px[x + dx, y + dy]
                        soma[0] += q[0]
                        soma[1] += q[1]
                        soma[2] += q[2]
                        n += 1
            o[x, y] = tuple(max(0, min(255, round(p[i] + k * (p[i] - soma[i] / n)))) for i in range(3)) + (255,)
    return out


def dobras(im, semente, y_ini):
    """Dobras do manto: faixas verticais de 3 a 6 px, mais claras ou mais escuras, que ondulam devagar com a altura, na parede
    da linha `y_ini` para baixo. Dão a ideia de tecido esculpido sem mexer na silhueta nem nas sombras fundas."""
    col, ond = fbm(semente, (11, 6, 3.4)), fbm(semente + 1, (60, 23))
    w, h = im.size
    px = im.load()
    out = im.copy()
    o = out.load()
    for y in range(y_ini, h):
        d = round(2.2 * ond(y))
        for x in range(w):
            p = px[x, y]
            if not p[3]:
                continue
            v = col(x + d)
            if v > .5:
                o[x, y] = mix(p, hx("#e8e4d0"), .08 + .1 * (v - .5))
            elif v < -.5:
                o[x, y] = mix(p, hx("#1b2430"), .12 + .1 * (-.5 - v))
    return out


CABECAS = {  # (olho esquerdo, olho direito, topo do elmo) na imagem da parede, em pixels de arte
    "isildur": ((55, 61), (69, 61), 37),
    "anarion": ((75, 46), (88, 46), 26)}


def retoca_cabeca(im, nome):
    """Dá à cabeça da estátua um pouco mais de detalhe por cima do que a pintura já tem, sem linhas retas marcadas: um arco
    curto e suave na sobrancelha, luz leve no osso da bochecha, o nariz curto e as narinas, o bigode em arco, mechas de barba
    irregulares que ondulam e esmaecem e o aro do elmo como um arco fraco. Tudo mistura com o tom que já estava."""
    (ax, ay), (bx, by), topo = CABECAS[nome]
    o = im.load()
    esc, claro = hx("#1b2430"), hx("#eef0e0")
    xm = (ax + bx) // 2

    def pinta(x, y, alvo, k):
        if 0 <= x < im.width and 0 <= y < im.height and o[x, y][3]:
            o[x, y] = mix(o[x, y], alvo, k)

    for ex, ey in ((ax, ay), (bx, by)):
        for dx in range(-4, 5):  # sobrancelha: arco suave
            pinta(ex + dx, ey - 3 - (abs(dx) > 2), esc, .30)
        for dx in range(-3, 4):  # osso da bochecha
            pinta(ex + dx, ey + 4, claro, .15)
    for y in range(ay, ay + 6):  # nariz curto, só a luz de um lado
        pinta(xm - 1, y, claro, .2)
    for dx in (-1, 1):
        pinta(xm + dx, ay + 7, esc, .35)  # narinas
    for dx in range(-8, 9):  # bigode: um arco
        pinta(xm + dx, ay + 12 + (dx * dx) // 30, esc, .22)
    for k, comp in ((-6, 9), (-3, 12), (0, 8), (3, 11), (6, 9)):  # mechas da barba: curtas, onduladas, esmaecendo
        for j in range(comp):
            pinta(xm + k + round(1.2 * math.sin(j * .7 + k)), ay + 16 + j, esc, max(.08, .26 - j * .016))
    for dx in range(-10, 11):  # aro do elmo: um arco quase sumido, interrompido para não virar régua
        if (dx + 10) % 5:
            pinta(xm + dx, ay - 7 + (dx * dx) // 40, esc, .09)


def dedos(im, x0, x1):
    """Separa os dedos da mão erguida (a parte mais alta entre as colunas x0 e x1): três entalhes entre as pontas, linhas
    escuras entre os dedos com um fio claro ao lado e a junta, para a mão deixar de ser um bloco."""
    o = im.load()
    esc, claro = hx("#1b2430"), hx("#c8d2d8")
    topo = next((y for y in range(0, 60) for x in range(x0, x1) if o[x, y][3]), None)
    if topo is None:
        return
    cols = [x for x in range(x0, x1) if o[x, topo + 5][3]]
    if len(cols) < 8:
        return
    xl, larg = cols[0], cols[-1] - cols[0] + 1
    for k in (1, 2, 3):
        x = xl + round(larg * k / 4)
        for y in range(topo, topo + 11):
            if y < topo + 3:
                o[x, y] = TRANSPARENTE  # o entalhe entre as pontas dos dedos
            elif o[x, y][3]:
                o[x, y] = mix(o[x, y], esc, .42 - (y - topo) * .02)
                if o[x + 1, y][3]:
                    o[x + 1, y] = mix(o[x + 1, y], claro, .18)
    for x in range(xl + 1, xl + larg - 1):  # a junta dos dedos
        if o[x, topo + 12][3]:
            o[x, topo + 12] = mix(o[x, topo + 12], esc, .4)


def musgo_estatua(im, semente, quantidade, evitar=()):
    """Musgo em tufos: nasce no alto das saliências (um pixel de pedra com céu ou uma sombra logo acima) e se espalha mais para
    os lados e para baixo, em quatro verdes (sombra, base, luz, brilho) da borda de baixo para o alto, com a sombra na ponta de
    baixo e, de alguns tufos, um escorrido que desce pela pedra e some. `evitar`: caixas (x0, y0, x1, y1) sem musgo (o rosto)."""
    r = random.Random(semente)
    w, h = im.size
    px = im.load()
    out = im.copy()
    o = out.load()
    verdes = [hx("#26392b"), hx("#37533a"), hx("#4d6b43"), hx("#6f8d53")]

    def lum(p):
        return .3 * p[0] + .59 * p[1] + .11 * p[2]

    cand = [(x, y) for y in range(h // 5, h - 6) for x in range(2, w - 2)
            if px[x, y][3] and (not px[x, y - 1][3] or lum(px[x, y - 1]) < lum(px[x, y]) - 26)
            and not any(a <= x < c and b <= y < d for a, b, c, d in evitar)]
    r.shuffle(cand)
    usados = []
    for x, y in cand:
        if len(usados) >= quantidade:
            break
        if any(abs(x - ux) < 14 and abs(y - uy) < 11 for ux, uy in usados):
            continue
        usados.append((x, y))
        pts = {(x, y)}
        for _ in range(260):
            if len(pts) >= r.randint(30, 62):
                break
            qx, qy = r.choice(sorted(pts))
            nx, ny = qx + r.choice((-1, -1, 0, 1, 1)), qy + r.choice((0, 0, 1))
            if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] and ny >= y - 1:
                pts.add((nx, ny))
        for mx, my in pts:
            abaixo = (mx, my + 1) not in pts
            i = 0 if abaixo and my > y else 3 if my <= y else 2 if my - y <= 2 else 1
            o[mx, my] = verdes[i]
        for mx, my in sorted(pts):  # escorrido: um fio que desce da ponta de baixo do tufo e esmaece
            if (mx, my + 1) not in pts and r.random() < .5:
                for k in range(1, r.randint(4, 10)):
                    if my + k < h and px[mx, my + k][3]:
                        o[mx, my + k] = mix(o[mx, my + k], verdes[1], max(.1, .4 - k * .04))
    return out


def contorna(im):
    """Contorno de 1 px em selout, desenhado só nos pixels transparentes que já estão dentro da imagem: o tom da pedra vizinha,
    escurecido e azulado, mais leve onde o contorno fica do lado da luz (em cima e à esquerda) e mais forte embaixo e à direita."""
    w, h = im.size
    px = im.load()
    out = im.copy()
    o = out.load()
    escuro = hx("#1b2430")
    for y in range(h):
        for x in range(w):
            if px[x, y][3]:
                continue
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):  # (dx, dy): de onde está o pixel de pedra, visto do contorno
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3]:
                    o[x, y] = mix(px[nx, ny], escuro, .5 if dx > 0 or dy > 0 else .78)  # pedra à direita/embaixo: o contorno é do lado da luz
                    break
    return out


def detalha_pedra(im, semente, base_h=26):
    """Dá à pedra ampliada o detalhe que o pixel menor comporta: grão (um pixel assume a cor de um vizinho), fio de luz nas
    bordas voltadas para o alto e a esquerda e sombra nas outras (selout), rachaduras que descem em zigue-zague, musgo nos
    topos de saliência perto da água e a base molhada, mais escura e azulada, pontilhada para cima."""
    r = random.Random(semente)
    w, h = im.size
    px = im.load()
    out = im.copy()
    o = out.load()
    claro, escuro = hx("#e8e4d0"), hx("#2a3038")
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            p = px[x, y]
            if not p[3]:
                continue
            if r.random() < .04:  # grão
                nx, ny = x + r.choice((-1, 0, 1)), y + r.choice((-1, 0, 1))
                if px[nx, ny][3]:
                    o[x, y] = px[nx, ny]
            if not px[x - 1, y][3] or not px[x, y - 1][3]:  # borda voltada para a luz
                o[x, y] = mix(p, claro, .34)
            elif not px[x + 1, y][3] or not px[x, y + 1][3]:  # borda na sombra
                o[x, y] = mix(p, escuro, .30)
    for _ in range(max(3, w // 18)):  # rachaduras
        x, y = r.randrange(6, w - 6), r.randrange(int(h * .2), int(h * .85))
        for _k in range(r.randint(7, 20)):
            if not (0 <= x < w and 0 <= y < h and px[x, y][3]):
                break
            o[x, y] = mix(o[x, y], escuro, .52)
            if r.random() < .5:
                o[x, y + 1 if y + 1 < h else y] = mix(o[x, y + 1 if y + 1 < h else y], claro, .12)  # o lábio da rachadura
            y += 1
            x += r.choice((-1, 0, 0, 1))
    for y in range(h - base_h, h):  # a base molhada
        for x in range(w):
            p = o[x, y]
            if p[3]:
                k = (y - (h - base_h)) / base_h
                if k > limiar2(x, y) * 1.1:
                    o[x, y] = mix(p, hx("#2c4656"), .35 + .3 * k)
    return out


def limpa_ilhas(im, minimo):
    """Apaga os pedaços isolados com menos de `minimo` pixels (sobras da extração da pintura, como um fiapo de nuvem)."""
    w, h = im.size
    a = im.getchannel("A").load()
    px = im.load()
    visto = [[False] * w for _ in range(h)]
    for y0 in range(h):
        for x0 in range(w):
            if a[x0, y0] and not visto[y0][x0]:
                fila, i = [(x0, y0)], 0
                visto[y0][x0] = True
                while i < len(fila):
                    x, y = fila[i]
                    i += 1
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < w and 0 <= ny < h and a[nx, ny] and not visto[ny][nx]:
                            visto[ny][nx] = True
                            fila.append((nx, ny))
                if len(fila) < minimo:
                    for x, y in fila:
                        px[x, y] = TRANSPARENTE


def corta_borda(im, lado, corte, desde, semente, amplitude=5):
    """Da linha `desde` para baixo, corta a beira `lado` ("dir" ou "esq") da parede numa linha vertical de irregularidade
    suave, `corte` px a partir do lado oposto: é onde a pedra escura acaba e, na pintura, começa o maciço de névoa. A linha
    ondula devagar (nada de dentes), com saliências de até `amplitude` pixels. A névoa do vão fica atrás."""
    ruido = fbm(semente, (61, 27, 11))
    pix = im.load()
    for y in range(desde, im.height):
        xc = corte + round(amplitude * ruido(y))
        for x in range(im.width):
            if (x >= xc if lado == "dir" else x < xc):
                pix[x, y] = TRANSPARENTE


def apara_claro(im, lado, desde, limiar=160, maximo=5):
    """Da linha `desde` para baixo, apaga da beira `lado` ("dir" ou "esq") para dentro os pixels claros (luminância acima de
    `limiar`), até `maximo` por linha: são os restos da montanha clara do vão que o corte reto deixa onde a beira do manto ou
    da rocha entra um pouco. Linha a linha, sem inundação, para não comer os realces de dentro da estátua."""
    pix = im.load()
    for y in range(desde, im.height):
        xs = [x for x in range(im.width) if pix[x, y][3]]
        if not xs:
            continue
        x, passo = (xs[-1], -1) if lado == "dir" else (xs[0], 1)
        for _ in range(maximo):
            p = pix[x, y]
            if not p[3] or .3 * p[0] + .59 * p[1] + .11 * p[2] < limiar:
                break
            pix[x, y] = TRANSPARENTE
            x += passo


def completa_capa(im, y_ini, x_ini, y_fim, x_fim):
    """Refaz a beira esquerda da capa de Anárion entre as linhas `y_ini` e `y_fim`: na pintura, a nuvem de areia passa logo
    atrás dela e, ao apagar a nuvem, a beira perdeu um pedaço (a diagonal recuava e a ponta virava um bico solto). A beira
    passa a ser a reta de (x_ini, y_ini) a (x_fim, y_fim), a continuação da diagonal de cima; o que fica fora dela some e o
    que falta é preenchido copiando a pedra ao longo da própria diagonal (5 linhas acima, 3 px à direita). Os pixels de areia
    que a nuvem deixou na ponta (vermelho bem acima do azul) tomam a cor da capa 2 px à direita."""
    pix = im.load()
    for y in range(y_ini, y_fim + 1):
        xe = round(x_ini + (x_fim - x_ini) * (y - y_ini) / (y_fim - y_ini))
        for x in range(im.width):
            if x < xe:
                pix[x, y] = TRANSPARENTE
            elif pix[x, y][3]:
                break
            else:
                pix[x, y] = pix[x + 3, y - 5]
    for y in range(y_ini - 20, y_fim + 10):
        for x in range(x_fim - 2, x_ini + 16):
            p = pix[x, y]
            if p[3] and p[0] - p[2] > 30:
                pix[x, y] = next((q for q in (pix[x + 2, y], pix[x + 4, y], pix[x + 6, y]) if q[0] - q[2] <= 30), pix[x + 2, y])


def paredes_finas(per="manha"):
    """As duas paredes da pintura em pixel de arte. Para cada uma: Scale2x, a beira de dentro cortada numa silhueta orgânica,
    dobras do manto, realce de contorno, detalhe de pedra, a cabeça e a mão retocadas, musgo em tufos e contorno em selout.
    A da esquerda termina na queda do manto, como na pintura: à direita dela fica o vão, com a névoa e as montanhas.
    Só a cor da hora muda de um período para outro, então a pedra é feita uma vez (fica em cache)."""
    if "paredes" not in _CACHE:
        ref = A.referencia()
        linhas = list(range(LINHAS_TOPO)) + [LINHAS_MEIO[0] + i * (LINHAS_MEIO[1] - LINHAS_MEIO[0]) // MEIO
                                             for i in range(MEIO)] + list(range(*LINHAS_BASE))
        esq = Image.new("RGBA", (LX[1] - LX[0], len(linhas)), TRANSPARENTE)
        dire = Image.new("RGBA", (RX[1] - RX[0], len(linhas)), TRANSPARENTE)
        for j, rr in enumerate(linhas):
            esq.paste(ref.crop((LX[0], rr, LX[1], rr + 1)), (0, j))
            dire.paste(ref.crop((RX[0], rr, RX[1], rr + 1)), (0, j))
        esq, dire = scale2x(esq), scale2x(dire)
        limpa_ilhas(esq, 400)
        limpa_ilhas(dire, 400)
        # fiapos de nuvem da pintura colados à beira de dentro: ao lado do braço erguido de Isildur e na capa de Anárion
        esq.paste(TRANSPARENTE, (93, 160, esq.width, 178))
        esq.paste(TRANSPARENTE, (95, 117, esq.width, 122))
        for y in range(165, 174):  # onde o fiapo atravessa a beira do manto, a beira segue com a cor da linha de cima
            for x in range(88, esq.width):
                esq.putpixel((x, y), esq.getpixel((x, 164)) if x < 92 else TRANSPARENTE)
        dire.paste(TRANSPARENTE, (0, 99, 47, 104))
        completa_capa(dire, 137, 23, 151, 14)
        # na beira de dentro, a pintura tem, atrás das estátuas, a montanha clara do vão; o corte tira essa montanha e segue
        # a beira do manto e da rocha como na pintura, sem morder o manto nem deixar uma prateleira clara para fora
        corta_borda(esq, "dir", 91, 186, 11, amplitude=1)  # o manto de Isildur acaba na coluna 49 da referência
        corta_borda(dire, "esq", 21, 160, 12, amplitude=3)  # e a rocha sob a capa de Anárion começa na 88
        corta_borda(dire, "esq", 26, 188, 13, amplitude=2)  # e, mais abaixo, na 91: à esquerda dela, a encosta da montanha
        apara_claro(esq, "dir", 186)
        apara_claro(dire, "esq", 160)
        pedras = []
        for im, nome, semente, x0_dedos in ((esq, "isildur", 5, 76), (dire, "anarion", 6, 100)):
            im = realca(dobras(im, semente + 20, 90))
            im = detalha_pedra(im, semente)
            retoca_cabeca(im, nome)
            dedos(im, x0_dedos, im.width)
            c = A.CLIQUE_ROSTO[nome]
            ox = LX[0] if nome == "isildur" else RX[0]
            evitar = [((c[0] - ox) * 2 - 4, c[1] * 2 - 4, (c[2] - ox) * 2 + 4, c[3] * 2 + 24)]  # o rosto
            if nome == "anarion":
                evitar.append((0, 128, 34, 164))  # a ponta da capa: um tufo ali pesa e deforma a silhueta
            im = musgo_estatua(im, semente + 40, 28 if nome == "isildur" else 24, evitar)
            pedras.append(im)
        esq, dire = pedras
        _CACHE["paredes"] = (contorna(esq), contorna(dire))
    esq, dire = _CACHE["paredes"]
    return A.grade(esq, per), A.grade(dire, per)


# ------------------------------------------------------------------ efeitos de clique das estátuas
def ponto_estatua(nome, rx, ry, y0):
    """Ponto da grade da referência (coluna, linha) nas coordenadas da cena, para a estátua `nome` (y0: topo da parede)."""
    if nome == "isildur":
        return (rx - LX[0]) * 2, y0 + ry * 2
    return WP - (RX[1] - RX[0]) * 2 + (rx - RX[0]) * 2, y0 + ry * 2


def olhos_finos(T, nome, f, y0):
    """Os olhos do elmo acendem num brilho pálido enquanto a estátua olha para os barcos, acompanhando o giro da cabeça."""
    if A.envelope(f, A.EFEITOS[nome], .2, .2) < .5:
        return
    for rx, ry in A.OLHOS[nome]:
        x, y = ponto_estatua(nome, rx, ry, y0)
        dx, dy = A.giro(nome, f, ry * 2)
        x, y = x + dx, y + dy
        for dx in range(-2, 6):
            for dy in range(-1, 3):
                if not (0 <= dx < 4 and 0 <= dy < 2):
                    T.px(x + dx, y + dy, (127, 184, 216, 70))  # halo
        T.rect(x, y, 4, 2, hx("#e8f6ff"))
        T.px(x - 1, y, hx("#7fb8d8"))
        T.px(x + 4, y, hx("#7fb8d8"))


def poeira_fina(T, nome, f, y0, per):
    """Pedrinhas e poeira que se soltam da mão erguida e do ombro da estátua e caem, de 1 a 2 px."""
    r = random.Random(nome)
    mx, my = ponto_estatua(nome, *A.MAOS[nome], y0)
    sx, sy = ponto_estatua(nome, *A.OMBROS[nome], y0)
    for k in range(22):
        ox, oy = (mx, my) if k < 11 else (sx, sy)
        ox += r.randint(-8, 8)
        cor = A.cor_da_hora(r.choice((hx("#a29c8e"), hx("#d8d8ca"), hx("#7a828c"))), per)
        age = f - r.randint(0, 10)
        lado = r.choice((-1, 1))
        if 0 <= age <= 18:
            tam = 2 if k % 3 == 0 else 1
            T.rect(round(ox + lado * age * .3), round(oy + .35 * age * age), tam, tam, cor)
    if f < 9:  # a nuvenzinha de pó da hora em que a pedra se solta
        for k in range(12):
            if (k + f) % 2:
                T.px(mx - 7 + r.randint(0, 14), my - 3 + r.randint(0, 7), A.cor_da_hora(hx("#d8d8ca"), per))


# ------------------------------------------------------------------ rio e canoas
AGUA = dict(base=hx("#5f8f9c"), escuro=hx("#3f6672"), claro=hx("#a3c9cf"), brilho=hx("#e4f0ee"))


def faixa_do_rio_fina(w=WP, alt=RIO_P):
    """Faixa larga e periódica de água, feita de poucas formas grandes: cinco faixas de tom liso, de longe (clara, em cima) a
    perto (escura), com a divisa entre elas ondulando devagar, e riscos de onda em fileiras escolhidas. Cada risco claro (a
    crista) tem, às vezes, um mais escuro logo abaixo e um pouco à direita (a sombra dela). Os riscos crescem com a proximidade:
    curtos e mais numerosos ao longe, compridos e raros perto."""
    S = 256
    c = AGUA
    T = Tela(S + w, alt)
    r = random.Random(11)
    tons = (hx("#9fc6cb"), hx("#7dabb4"), hx("#5f8f9c"), hx("#4d7c89"), hx("#3f6672"))
    divisas = (8, 20, 33, 45)  # linha em que começa cada faixa depois da primeira
    onda = fbm(5, (97, 41, 19))
    for y in range(alt):
        for x in range(T.w):
            i = sum(1 for k, dv in enumerate(divisas) if y >= dv + round(1.6 * onda(x * (1 + k * .3) + k * 31)))
            T.px(x, y, tons[i])
    fileiras = ((2, 6, 4, 8), (5, 6, 5, 10), (12, 5, 7, 14), (17, 5, 8, 16), (25, 4, 11, 22), (30, 4, 12, 24), (38, 3, 16, 30),
                (43, 3, 18, 34), (50, 3, 22, 40), (53, 2, 24, 44))  # (linha, riscos por período, comprimento mínimo e máximo)
    for y, n, lo, hi in fileiras:
        for _ in range(n):
            x, comp = r.randrange(S), r.randint(lo, hi)
            base = T.im.getpixel((x, y))
            claro, escuro = mix(base, c["brilho"], .5), mix(base, c["escuro"], .42)
            for xx in (x, x + S):
                T.rect(xx, y, comp, 1, claro)
                if r.random() < .6:  # a sombra da crista: um traço mais curto e escuro logo abaixo e à direita
                    T.rect(xx + 2, y + 1, max(2, comp - 5), 1, escuro)
    return T.im


def _reflexo_parede(parede, per):
    """O reflexo da parede da esquerda como camada (WP x RIO_P): a cor do reflexo com o alfa da força. Compor a camada sobre
    a água dá o mesmo `mix` de antes, mas a camada é feita uma vez por hora e cada quadro só cola."""
    k = ("reflexo", per)
    if k not in _CACHE:
        fundo = 28
        base = parede.crop((0, parede.height - fundo, parede.width, parede.height)).transpose(Image.FLIP_TOP_BOTTOM)
        bp = base.load()
        R_ = Tela(WP, RIO_P)
        for ry in range(min(fundo, RIO_P - 6)):
            desloc = (-1, 0, 1)[(ry // 3) % 3]
            forca = round(255 * .62 * (1 - ry / fundo))
            for x in range(base.width):
                v = bp[x, ry]
                if v[3] and 0 <= x + desloc < WP:
                    R_.px(x + desloc, 6 + ry, mix(v, hx("#2d4a58"), .55)[:3] + (forca,))
        _CACHE[k] = R_.im
    return _CACHE[k]


def rio_fino(t, per="manha", parede=None):
    """O rio (WP x RIO_P) no quadro t, na hora `per`: as ondas andam e a água é tingida pela hora (escura à noite, rosada à
    tarde); sob a parede da esquerda aparece o reflexo dela (a base da própria parede, virada de cabeça para baixo,
    escurecida, mais fraca quanto mais fundo, com cada fatia de 3 linhas deslocada 1 px para um lado ou para o outro); sob o
    sol ou a lua, uma coluna de riscos que estreita com a profundidade e balança. A névoa da superfície é uma camada à parte,
    `nevoa_agua_fina`, que passa também na frente da parede da esquerda."""
    if "faixa" not in _CACHE:
        _CACHE["faixa"] = faixa_do_rio_fina()
    faixa = _CACHE["faixa"]
    T = Tela(WP, RIO_P)
    for y in range(RIO_P):  # cada linha anda no seu passo (as de perto mais rápido), no máximo 1 px por quadro: sem saltos
        off = int(t * (.15 + .012 * y)) % 256
        T.im.paste(faixa.crop((off, y, off + WP, y + 1)), (0, y))
    T.im = _tinge_agua_fina(T.im, per)
    if parede is not None:
        T.im.alpha_composite(_reflexo_parede(parede, per))
    T.im.alpha_composite(_nevoa_rio(per))
    pix = T.im.load()
    if per != "manha":
        ax = ASTRO[per][0]
        cor = hx("#ffd37a") if per == "tarde" else hx("#e8e4c0")
        for y in range(4, RIO_P, 4):
            largura = max(3, 18 - y // 3)
            x0 = ax - largura // 2 + round(3 * math.sin(t / 3 + y))
            for x in range(max(0, x0), min(WP, x0 + largura)):
                pix[x, y] = cor
    return T.im


def _nevoa_rio(per):
    """O alto da água (WP x RIO_P): nasce opaco na cor do brilho do horizonte e chega à cor da água em uns 6 px, como no print,
    em níveis de borda ondulada; a linha d'água não aparece como risco."""
    k = ("nevoa-rio", per)
    if k not in _CACHE:
        nevoa, brilho = hx(ATMOS[per]["nevoa"]), cor_horizonte(per)
        ru, ru2 = fbm(211, (83, 37, 17)), fbm(212, (29, 11))
        alfas = (.15, .3, .45, .6, .75, .9, 1.0)
        T = Tela(WP, RIO_P)
        for y in range(12):
            cor = mix(brilho, nevoa, min(1.0, y / 3))
            for x in range(WP):
                f = 1 - y / (6 + 2 * ru(x) + 1 * ru2(x * 1.3 + y * 4))
                nivel = nivel_nevoa(x, y, f, len(alfas))
                if nivel:
                    T.px(x, y, cor[:3] + (round(255 * alfas[min(len(alfas), nivel) - 1]),))
        _CACHE[k] = T.im
    return _CACHE[k]


def _tinge_agua_fina(im, per):
    """A água na cor da hora: na tarde, o lavanda-rosado do print (`AGUA_TARDE`); nas outras horas, como no Argonath da janela."""
    if per != "tarde":
        return A.tinge_agua(im, per)
    alfa = im.getchannel("A")
    im = Image.blend(im.convert("RGB"), Image.new("RGB", im.size, AGUA_TARDE[0]), AGUA_TARDE[1]).convert("RGBA")
    im.putalpha(alfa)
    return im


NEVOA_SOBE, NEVOA_DESCE = 30, 16  # linhas da névoa da água acima e abaixo da linha d'água (YR)
NEVOA_X = X_RIO - 14  # a névoa animada some antes desta coluna: à direita dela a cena não é repintada a cada quadro
NEVOA_PER = 1920  # período (px) do ruído da névoa: os senos têm períodos que dividem este, então a animação nunca salta
VEL_NEVOA = (.11, -.06)  # px por quadro das duas camadas de ruído: andam devagar e em sentidos opostos, e a névoa se desfaz e refaz


def _ruido_periodico(semente, ks=(3, 7, 13, 29)):
    """Lista de NEVOA_PER valores de -1 a 1, soma de senos cujo período divide NEVOA_PER (o ruído se repete sem emenda)."""
    r = random.Random(semente)
    fases = [r.uniform(0, math.tau) for _ in ks]
    amps = [1 / (i + 1) ** 1.1 for i in range(len(ks))]
    tot = sum(amps)
    return [sum(a * math.sin(math.tau * k * x / NEVOA_PER + f) for a, k, f in zip(amps, ks, fases)) / tot for x in range(NEVOA_PER)]


def nevoa_agua_fina(t, per="manha"):
    """A névoa rente à água no quadro t (WP x NEVOA_SOBE + NEVOA_DESCE, para colar em YR - NEVOA_SOBE): mais densa logo acima
    da linha d'água, sobe mais na frente do pé da estátua da esquerda e se apaga antes da margem. Camada da cor da névoa com
    alfa em níveis (pontilhado de 2x2 só na divisa estreita entre níveis). Duas camadas de ruído andam devagar em sentidos
    opostos, então os bancos se deslocam e mudam de forma; nenhuma divisa anda mais de 1 px por quadro."""
    if "ruido-nevoa" not in _CACHE:
        _CACHE["ruido-nevoa"] = (_ruido_periodico(111), _ruido_periodico(112, (5, 11, 23, 47)))
    n1, n2 = _CACHE["ruido-nevoa"]
    o1, o2 = int(t * VEL_NEVOA[0]), int(t * VEL_NEVOA[1])
    cor, brilho = hx(ATMOS[per]["nevoa"]), cor_horizonte(per)  # rente à água, o brilho do horizonte passa na frente da estátua
    alfas = (.10, .22, .34, .46, .58, .70)
    T = Tela(WP, NEVOA_SOBE + NEVOA_DESCE)
    for x in range(NEVOA_X):
        lado = min(1.0, (NEVOA_X - x) / 50)  # apaga antes da margem
        sobe = 9 + 20 * max(0.0, min(1.0, (120 - x) / 50))  # na frente da estátua da esquerda a névoa sobe mais
        for yy in range(-NEVOA_SOBE, NEVOA_DESCE):
            d = yy - 1
            prof = math.exp(-(d / (sobe if d < 0 else 6)) ** 2)
            mancha = .62 + .3 * n1[(x - o1 + 3 * yy) % NEVOA_PER] + .2 * n2[(x - o2 - 2 * yy) % NEVOA_PER]
            linha = max(0.0, 1 - abs(yy + 1.5) / 2.5) * .6  # a linha de brilho rente à água, mais forte, como no print
            nivel = nivel_nevoa(x, yy, (prof * mancha * 1.5 + linha) * lado, len(alfas))
            if nivel:
                c = mix(cor, brilho, max(0.0, 1 - abs(yy + 1) / 3))  # rente à água, a cor do brilho do horizonte
                T.px(x, yy + NEVOA_SOBE, c[:3] + (round(255 * alfas[min(len(alfas), nivel) - 1]),))
    return T.im


# (comprimento, x do centro, linha da água, tripulação), em px. A tripulação tem uma letra por pessoa, da popa (esquerda) para
# a proa, já que as canoas andam para a direita: E elfo, H humano, A anão, B hobbit. Duas canoas levam um humano e dois
# hobbits; a terceira, o elfo e o anão.
CANOAS_F = ((52, 140, 44, "HBB"), (40, 190, 32, "EA"), (52, 236, 24, "BBH"))
CANOA_TOPO = 6  # linhas a mais acima do desenho original, para o tripulante mais alto (o elfo, de capuz pontudo)
SIL = hx("#1e2a34")


# tripulantes sentados em silhueta, de frente para a direita (a proa), da linha de cima até a borda do casco: # é a silhueta, c o
# lado da luz (esquerdo), m um tom acima da silhueta (topo do capuz, cachos, a ponta da barba) e f a sombra do rosto. Proporções
# de figura sentada vista da cintura para cima (o resto fica dentro do casco), conferidas com as medidas de figura humana: o
# adulto mostra cerca de três cabeças e meia de altura e ombros de duas cabeças ou um pouco menos (o capuz engorda a cabeça); o
# hobbit, menor, tem a cabeça um pouco maior em relação ao corpo e ombros de menos de duas cabeças; o anão é baixo e de ombros
# largos. Um pescoço mais estreito que a cabeça separa a cabeça dos ombros, para a silhueta não virar um cone.
TRIPULANTES = {
    "E": ["...#.....",  # elfo: 19 px com a ponta do capuz, cabeça de 4 sobre ombros de 8
          "...##....",
          "..c###...",
          "..####...",
          "..###f...",
          "..####...",
          "...##....",
          "..#####..",
          ".c######.",
          ".#######.",
          ".c######.",
          ".#######.",
          "..######.",
          "..######.",
          "..######.",
          "..######.",
          "..######.",
          "..######.",
          "..######."],
    "H": ["...mmm...",  # humano: 16 px, capuz de 5 sobre ombros de 9
          "..#####..",
          "..c####..",
          "..####f..",
          "...###...",
          ".#######.",
          "c########",
          "c########",
          "#########",
          "#########",
          "#########",
          "#########",
          "#########",
          "#########",
          "#########",
          "#########"],
    "A": ["....###....",  # anão: 14 px, elmo de 5 sobre ombros de 11, barba sobre o peito
          "...c####...",
          "...####f...",
          "...#####...",
          ".#########.",
          "c##########",
          "c######m###",
          "#######m###",
          "###########",
          "###########",
          "###########",
          "###########",
          "###########",
          "###########"],
    "B": ["..mm...",  # hobbit: 11 px, cabeça de 4 sobre ombros de 7
          ".m###..",
          ".c###..",
          ".###f..",
          "..##...",
          ".#####.",
          "c######",
          "#######",
          "#######",
          "#######",
          "#######"],
}


def _tripulante(T, letra, mx, base, cores):
    """Um tripulante de TRIPULANTES sentado na canoa: `base` é a linha da borda do casco sob ele e `mx`, o meio. O elfo leva a
    aljava às costas e o anão, o machado."""
    clara, meio, funda = cores
    fig = TRIPULANTES[letra]
    T.spr(mx - len(fig[0]) // 2, base - len(fig) + 1, fig, {"#": SIL, "c": clara, "m": meio, "f": funda})
    if letra == "E":
        T.line([(mx - 3, base - 8), (mx - 5, base - 16)], SIL)  # aljava nas costas
        T.px(mx - 5, base - 17, meio)  # as penas
    elif letra == "A":
        T.line([(mx - 5, base - 4), (mx - 7, base - 12)], SIL)  # cabo do machado às costas
        T.rect(mx - 10, base - 13, 3, 4, SIL)  # a lâmina
        T.px(mx - 10, base - 13, clara)
        T.px(mx - 10, base - 12, clara)


def remo(mx, base, fase):
    """(mão, ponta da pá) do remo de quem está sentado na coluna `mx`, com a borda do casco na linha `base`, na `fase` (0 a 1)
    da remada: na primeira metade a pá vai, dentro d'água, da frente para trás; na segunda sai da água e volta pelo ar. O
    movimento acelera e freia nas pontas (cosseno), então a pá anda no máximo 1 a 2 px por quadro e não salta."""
    if fase < .5:
        u = .5 - .5 * math.cos(2 * math.pi * fase)  # 0 -> 1 na remada
        ex, ey = mx + round(8 - 14 * u), base + 5 + round(math.sin(2 * math.pi * fase))  # logo abaixo da quilha
    else:
        u = .5 - .5 * math.cos(2 * math.pi * (fase - .5))  # 0 -> 1 na volta
        ex, ey = mx + round(-6 + 14 * u), base + 5 - round(7 * math.sin(2 * math.pi * (fase - .5)))
    return (mx + round((ex - mx) / 4), base - 3), (ex, ey)


def canoa_fina(L, fase, quem):
    """Canoa comprida e baixa, de proa e popa pouco erguidas, com a tripulação `quem` sentada em silhueta (ver
    `_tripulante`): casco, fio de luz na borda de cima (mais forte à esquerda) e o remo de cada um, todos no mesmo ritmo,
    na `fase` (0 a 1) da remada (ver `remo`)."""
    alt = 22 + CANOA_TOPO
    T = Tela(L + 14, alt)
    g0 = 14 + CANOA_TOPO  # linha da borda do casco no meio
    cx = (L - 1) / 2 + 7
    clara = mix(SIL, hx("#6a7e8c"), .55)
    meio = mix(SIL, hx("#46586a"), .5)
    funda = mix(SIL, hx("#0b1018"), .55)
    for x in range(7, 7 + L):
        u = (x - cx) / ((L - 1) / 2)
        gun = g0 - round(3.4 * abs(u) ** 3)  # a borda sobe só nas pontas
        quilha = gun + max(1, round(1.2 + 3.2 * (1 - u * u) ** .8))
        for y in range(gun, quilha + 1):
            T.px(x, y, SIL)
        T.px(x, gun, clara if x < cx else meio)  # fio de luz na borda de cima
        if quilha - gun >= 3:
            T.px(x, gun + 2, mix(SIL, hx("#2e3e4c"), .5))  # a tábua de baixo, um tom acima
    esp = (L - 16) / len(quem)  # distância entre os tripulantes
    for k, letra in enumerate(quem):
        mx = round(cx + (k - (len(quem) - 1) / 2) * esp)
        u = (mx - cx) / ((L - 1) / 2)
        base = g0 - round(3.4 * abs(u) ** 3)
        _tripulante(T, letra, mx, base, (clara, meio, funda))
        mao, (ex, ey) = remo(mx, base, fase)
        T.line([mao, (ex, ey)], meio)  # o cabo um tom acima da silhueta, para a remada se ler na frente do corpo e do casco
        T.rect(ex - 1, ey, 3, 1, meio)  # pá do remo
    return T.im


FUNDO_CASCO = 18 + CANOA_TOPO  # última linha do casco (a quilha, no meio) no desenho de `canoa_fina`


REMADA = 28  # quadros (de 140 ms) de uma remada, com a canoa parada: quase 4 s, um ritmo calmo
REMADA_CLIQUE = 6  # com o clique, a remada é rápida
BALANCO = 40  # quadros de um balanço do casco (1 px para baixo e de volta)
MAROLA = 12  # quadros para um traço de marola andar a distância até o seguinte


def canoas_finas(t, per="manha", ef=None):
    """As três canoas (WP x RIO_P), na hora `per`, desenhadas da mais distante para a mais próxima: remam num ciclo contínuo
    (`remo`), balançam um pixel devagar, deixam uma marola que se afasta para trás e o casco refletido, com o reflexo
    ondulando. A marola de uma canoa não passa por trás da tripulação de outra mais à frente. Com um efeito de clique
    (`ef["canoaN"]` = quadros desde o clique), remam rápido, a canoa avança e volta, a marola cresce e há respingos."""
    ef = ef or {}
    T = Tela(WP, RIO_P)
    dxs = [round(18 * math.sin(math.pi * ef[f"canoa{i}"] / A.EFEITOS[f"canoa{i}"])) if f"canoa{i}" in ef else 0
           for i in range(len(CANOAS_F))]
    for i in sorted(range(len(CANOAS_F)), key=lambda i: CANOAS_F[i][2]):
        L, cx, linha, quem = CANOAS_F[i]
        f, dx = ef.get(f"canoa{i}"), dxs[i]
        fase = (f / REMADA_CLIQUE) % 1 if f is not None else (t / REMADA + i * .37) % 1
        c = canoa_fina(L, fase, quem)
        bob = 1 if math.sin(2 * math.pi * (t / BALANCO + i / 3)) > 0 else 0
        x0, y0 = cx + dx - c.width // 2, linha - 18 - CANOA_TOPO + bob
        C = Tela(WP, RIO_P)  # cada canoa na sua camada: o reflexo e a marola ficam embaixo dela e não furam a de trás
        cp = c.load()
        for ry in range(7):  # reflexo: as últimas linhas do casco viradas, mais fracas a cada linha, ondulando 1 px
            lado = (ry // 2 + t // 5) % 2
            for xx in range(c.width):
                if cp[xx, FUNDO_CASCO - ry][3]:
                    C.px(x0 + xx + lado, y0 + FUNDO_CASCO + 1 + ry, (20, 40, 52, 130 - ry * 17))
        frente = [(CANOAS_F[j][1] + dxs[j] - CANOAS_F[j][0] // 2 - 4, CANOAS_F[j][1] + dxs[j] + CANOAS_F[j][0] // 2 + 4,
                   CANOAS_F[j][2] - 26, CANOAS_F[j][2] + 2) for j in range(len(CANOAS_F)) if CANOAS_F[j][2] > linha]
        popa = cx + dx - L // 2
        for j in range(3):  # marola: três traços que se afastam para trás e encurtam; o último some e um novo nasce na popa
            d = j + (t / MAROLA) % 1
            xa, ya = popa - 4 - round(9 * d), linha + 1 + round(2 * d)
            xb = xa + max(1, round(8 - 2.2 * d)) + (4 if f is not None else 0)
            for x in range(xa, xb):
                if not any(a <= x < b and c0 <= ya < c1 for a, b, c0, c1 in frente):
                    C.px(x, ya, ESPUMA)
        C.put(c, x0, y0)
        if f is not None:  # respingos dos remos
            r = random.Random(f * 7 + i)
            for _ in range(5):
                C.px(cx + dx + r.randint(-L // 2 - 3, L // 2 + 3), linha - r.randint(0, 6) + bob, ESPUMA)
        T.im.alpha_composite(C.im)
    return A.grade(T.im, per)


# ------------------------------------------------------------------ a margem
X_MARGEM = TOPO[0][0] * 2  # primeira coluna (px) em que a margem aparece


def topo_px(x, ruido):
    """Linha (px) do alto da margem na coluna x: o contorno da versão grossa, com a irregularidade de 1 a 2 px."""
    return altura_topo(x / 2) * 2 + 1.7 * ruido(x)


def pedregulho_fino(w, h, semente):
    """Pedra solta e facetada: contorno de 12 pontos, relevo por ruído, luz de cima e da esquerda em seis tons com
    transição pontilhada, rachadura, musgo e líquen no alto e contorno selout (mais claro no lado da luz)."""
    r = random.Random(semente)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    lobos = fbm(semente, (w * .9, w * .4))
    pts = [(w / 2 + math.cos(a) * w / 2 * (.88 + .12 * lobos(i * 7)) * r.uniform(.94, 1.02),
            h / 2 + math.sin(a) * h / 2 * (.88 + .12 * lobos(i * 7 + 3)) * r.uniform(.94, 1.02))
           for i, a in enumerate(k * math.tau / 12 for k in range(12))]
    d.polygon(pts, fill=255)
    relevo = fbm(semente + 1, (w * .7, w * .3, w * .13))
    tons = [M["e0"], M["e1"], mix(M["e1"], M["e2"], .5), M["e2"], M["e3"], M["e4"]]
    mp = m.load()
    out = Image.new("RGBA", (w, h), TRANSPARENTE)
    o = out.load()
    for y in range(h):
        for x in range(w):
            if not mp[x, y]:
                continue
            nx, ny = (x + .5 - w / 2) / (w / 2), (y + .5 - h / 2) / (h / 2)
            nz = math.sqrt(max(0.0, 1 - min(1, nx * nx + ny * ny) * .85))
            nx, ny = nx + .22 * relevo(x * 3 + y), ny + .22 * relevo(y * 3 - x)
            luz = -.5 * nx - .6 * ny + .62 * nz
            i = max(0, min(5, int((luz + .15 + (limiar(x, y) - .5) * .22) * 5.2)))
            o[x, y] = tons[i]
            if ny < -.15 and relevo(x * 2 + 40) > .15 and luz > -.1 and r.random() < .75:  # musgo
                o[x, y] = (M["g2"], M["g1"], M["g3"])[min(2, int(abs(relevo(x * 5 + y * 3)) * 4))]
    for _ in range(max(1, w // 24)):  # rachaduras
        x, y = r.randrange(3, max(4, w - 3)), r.randrange(2, max(3, h // 2))
        for _k in range(r.randint(4, 9)):
            if not (0 <= x < w and 0 <= y < h and mp[x, y]):
                break
            o[x, y] = mix(o[x, y], M["e0"], .6)
            y += 1
            x += r.choice((-1, 0, 1))
    return selout(out, M)


def junco_fino(alt, semente):
    """Moita de juncos de 5 a 7 hastes que se curvam, folhas finas cruzando e, em algumas, a espiga marrom."""
    r = random.Random(semente)
    larg = 22
    T = Tela(larg, alt + 6)
    for i in range(r.randint(5, 7)):
        x0 = 4 + i * (larg - 8) / 6 + r.uniform(-1, 1)
        a = max(6, alt - r.randint(0, int(alt * .45)))
        lean = r.uniform(-.28, .28)
        for k in range(a):
            xx = round(x0 + lean * k * (k / a) * 1.6 + (k / a) ** 2 * 2 * lean * 6)
            cor = M["g0"] if k < 2 else M["g1"] if k < a * .35 else M["g2"] if k < a - 3 else M["g3"]
            T.px(xx, alt + 5 - k, cor)
            if k > 3 and k % 7 == 0:  # folha fina que se afasta da haste
                for j in range(1, 5):
                    T.px(xx + (j if i % 2 else -j), alt + 5 - k - j // 2, M["g2"] if j < 4 else M["g3"])
        if i % 3 == 1:  # espiga
            xx = round(x0 + lean * a * 1.6 + 2 * lean * 6)
            for j in range(5):
                T.px(xx, alt + 5 - a - j, hx("#7a5a3a") if j % 2 else hx("#a07850"))
                T.px(xx + 1, alt + 5 - a - j, hx("#5a3f28"))
            T.px(xx, alt + 5 - a - 5, hx("#c9a070"))
    return T.im


def lamina(T, x, y, alt, tom, dobra=0):
    """Lâmina de grama de 1 px a partir de (x, y) para cima: a base escura, o meio no tom e a ponta clara, com uma dobra."""
    for k in range(alt):
        cor = M["g1"] if k == 0 else tom if k < alt - 1 else M["g3"] if tom == M["g2"] else M["g4"]
        T.px(x + (dobra if k > alt * .6 else 0), y - k, cor)


def terra_fina(x, e):
    """Cor da terra a `e` pixels abaixo da grama: camadas de 4 px que ondulam, cada uma de um tom, com fio de luz na borda de
    cima e sombra na de baixo, veios claros e a oclusão sob a grama."""
    if e < 3:
        return M["e0"]
    if e < 5:
        return mix(M["e0"], M["e1"], .5)
    yy = e + round(2.6 * math.sin(x / 23) + 1.4 * math.sin(x / 7 + 1))
    banda, linha = divmod(yy, 6)
    base = (M["e1"], M["e2"], M["e1"], mix(M["e1"], M["e2"], .5))[banda % 4]
    if banda % 3 == 1 and (x // 17 + banda) % 3 == 0:
        base = mix(base, M["e3"], .35)
    if linha == 0:
        return mix(base, M["e3"], .5)
    if linha == 5:
        return mix(base, M["e0"], .5)
    return base


def margem_fina(per="manha"):
    """A margem do rio em pixel fino. Devolve (agua, terra, frente): espuma e reflexo escuro, que vão sobre a água; o gramado,
    que desce até a borda de baixo da tela, com lâminas, flores e juncos; e o capim que passa na frente do pedestal.

    O gramado é feito de manchas de tom em duas direções (um ruído que corre em x e outro em y, cada um deformado pelo outro:
    manchas e não listras em V), maiores quanto mais perto (embaixo), e as lâminas crescem com a proximidade."""
    r = random.Random(41)
    T, AG, F = Tela(WP, HP), Tela(WP, HP), Tela(WP, HP)
    costa, tom_g, tom_h = fbm(81, (53, 23, 9, 4)), fbm(83, (29, 13, 6)), fbm(84, (23, 11, 5))
    xl, cls = {}, {}  # y -> primeira coluna da margem na linha (a beira da água); (x, y) -> "g" grama
    for x in range(X_MARGEM, WP):
        y0 = int(round(topo_px(x, costa)))
        for y in range(y0, HP):
            xl[y] = min(xl.get(y, WP), x)
            d = y - y0
            perto = 1 - .45 * min(1, max(0, (y - 290) / 70))  # embaixo, mais perto: manchas maiores
            v = .55 * tom_g(x * .5 * perto + 7 * tom_h(y * .6)) + .45 * tom_h(y * 1.2 * perto + 6 * tom_g(x * .33 + 50))
            c = M["g3"] if d == 0 else M["g1"] if v < -.36 else M["g3"] if v > .4 else M["g2"]
            cls[(x, y)] = "g"
            T.px(x, y, c)
    for _ in range(260):  # lâminas dentro da grama: mais altas quanto mais perto, claras e escuras
        x, y = r.randrange(X_MARGEM + 4, WP - 2), r.randrange(280, HP + 4)
        if cls.get((x, min(y, HP - 1))) == "g" and cls.get((x, y - 4)) == "g":
            perto = min(1, max(0, (y - 290) / 70))
            lamina(T, x, y, r.randint(3, 5) + round(4 * perto), M["g2"] if r.random() < .6 else M["g1"], r.choice((-1, 0, 1)))
    for x in range(X_MARGEM + 2, WP):  # capim no alto da margem: lâminas de 2 a 8 px, e uns tufos mais altos
        if r.random() < .6:
            y = int(round(topo_px(x, costa)))
            alt = r.randint(2, 6) if r.random() > .07 else r.randint(8, 12)
            lamina(T, x, y, alt, M["g2"], r.choice((-1, 0, 0, 1)))
    for x in range(X_MARGEM + 40, WP - 10, 7):  # flores: haste de 3 a 5 px e cabeça de 3x3, espalhadas pelo gramado todo
        for _k in range(2):
            if r.random() > .3:
                continue
            y = int(round(topo_px(x, costa))) + r.randint(5, 18) + _k * r.randint(20, 50)
            if cls.get((x, y)) == "g":
                for k in range(r.randint(3, 5)):
                    T.px(x, y - k, M["g1"])
                yy = y - 5
                cor = hx("#f2e8c0") if r.random() < .6 else hx("#d8e0f0") if r.random() < .5 else hx("#e8c860")
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    T.px(x + dx, yy + dy, cor)
                T.px(x, yy, hx("#e8c860") if cor != hx("#e8c860") else hx("#f2e8c0"))
    for y in sorted(xl):  # beira da água: o reflexo escuro da margem com ondulação e a espuma, sobre o rio
        onda = round(1.6 * math.sin(y * .45))
        for dx in range(1, 11):
            AG.px(xl[y] - dx + onda, y, AGUA_ESCURA + (max(0, 160 - dx * 15),))
        if (y // 2) % 3 != 0:  # espuma em traços: duas linhas brancas e, em fatias alternadas, mais dois pixels de água clara
            for dx in range(1, 3):
                AG.px(xl[y] - dx, y, ESPUMA)
            if (y // 2) % 3 == 1:
                for dx in range(3, 5):
                    AG.px(xl[y] - dx, y, AGUA_CLARA)
        T.px(xl[y], y, M["g0"])  # a grama molhada na beira, escura
        T.px(xl[y] + 1, y, mix(T.im.getpixel((xl[y] + 1, y)), M["g0"], .55))
        T.px(xl[y] + 2, y, mix(T.im.getpixel((xl[y] + 2, y)), M["g0"], .25))
    for y in range(312, 356, 6):  # juncos na beira
        x = xl[y] + r.randint(0, 8)
        j = junco_fino(r.randint(11, 20), y)
        T.put(j, x - 10, y - j.height + 6)
    for x in (596, 612, 626):
        j = junco_fino(r.randint(9, 16), x)
        T.put(j, x - 10, int(round(topo_px(x, costa))) + 4 - j.height)
    sx = PX + BW  # sombra da tábua na grama, para a direita (a luz vem da esquerda)
    for y in range(PE - 6, PE + 9):
        for x in range(sx, sx + 34 - (y - PE + 6) * 2):
            if (x + y) % 2 == 0 or x < sx + 20:
                tinge(T, x, y, 1, 1, M["sh"], .40)
    x = PX - 6
    while x < sx + 6:  # capim do pé do pedestal, na frente dele: tufos de 4 a 8 lâminas abertas em leque
        for k in range(r.randint(4, 8)):
            lamina(F, x + k - 3 + r.randint(-1, 1), PE + 12, r.randint(3, 9), M["g2"] if r.random() < .7 else M["g1"],
                   (k - 3) // 2 if r.random() < .8 else 0)
        F.rect(x - 3, PE + 13, 8, 1, M["g0"])
        x += r.randint(11, 19)
    for x in range(PX + 8, sx - 4, 23):
        if r.random() < .6:
            for k in range(4):
                F.px(x, PE + 11 - k, M["g1"])
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                F.px(x + dx, PE + 6 + dy, hx("#f2e8c0"))
            F.px(x, PE + 6, hx("#e8c860"))
    return A.grade(AG.im, per), A.grade(T.im, per), A.grade(F.im, per)


# ------------------------------------------------------------------ o tema (rascunho estático)


# ------------------------------------------------------------------ astros
_r = random.Random(5)
ESTRELAS = [(_r.randrange(6, WP - 6), _r.randrange(6, 230), _k) for _k in range(84)]  # (coluna, linha, número) das estrelas


def brilha(k, t):
    """A estrela de número k está acesa no quadro t? As de número múltiplo de 12 (7 delas, maiores, em cruz) cintilam: somem
    4 quadros a cada 24. As outras ficam acesas, então o que muda de um quadro a outro cabe em remendos minúsculos (cada
    remendo, por menor que seja, custa ~1 ms de colagem no Tk)."""
    return k % 12 != 0 or (t + k * 5) % 24 >= 4


def lua_fina(T, cx, cy, r=15):
    """A lua em T: uma esfera iluminada de cima e da esquerda em cinco tons (o miolo claro e o limbo mais escuro), com mares
    (manchas escuras e irregulares, só no meio do disco), crateras de aro claro e um halo suave de três anéis."""
    for rr in range(34, r + 1, -1):  # halo: anéis de 1 px com a opacidade subindo aos poucos para perto da lua
        T.d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(190, 205, 255, round(4 + 44 * ((34 - rr) / (34 - r)) ** 1.5)))
    tons = [hx("#b9b08a"), hx("#d3cba4"), hx("#e8e1bc"), hx("#f5efd0"), hx("#fffbe6")]
    mar = fbm(91, (23, 11, 6))
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            nx, ny = (x - cx + .5) / r, (y - cy + .5) / r
            d2 = nx * nx + ny * ny
            if d2 > 1:
                continue
            lum = nx * -.5 + ny * -.55 + math.sqrt(1 - d2) * .67
            c = tons[max(0, min(4, int((lum + .1) * 4.2 + (limiar(x, y) - .5) * .5)))]
            m = mar(x * 1.3) * .6 + mar(y * 1.7 + 50) * .4  # mares
            if m > .1 and d2 < .78:
                c = mix(c, hx("#9d9570"), min(.65, (m - .1) * 2.4))
            T.px(x, y, c)
    for dx, dy, rr in ((-5, -5, 3), (5, 4, 3), (7, -6, 2), (-8, 5, 2), (1, 9, 2), (-1, 0, 2)):  # crateras
        T.ell(cx + dx - rr, cy + dy - rr, cx + dx + rr, cy + dy + rr, hx("#aaa27c"))
        T.ell(cx + dx - rr + 1, cy + dy - rr + 1, cx + dx + rr, cy + dy + rr, hx("#c4bc96"))  # o aro claro fica embaixo à direita
        T.px(cx + dx + rr, cy + dy + rr - 1, hx("#fffbe6"))


def astros_finos(per, t):
    """Sol baixo (tarde) ou lua com estrelas que piscam (noite), em (WP, YR); a manhã é de céu coberto. O sol e a lua são
    parados (ficam em cache) e só as estrelas mudam com `t`. As montanhas e as paredes vêm depois e cobrem o que for preciso."""
    k = ("astro-base", per)
    if k not in _CACHE:
        T = Tela(WP, YR)
        cx, cy = ASTRO[per]
        if per == "tarde":
            for rr, a in ((30, 34), (21, 62)):
                T.d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 190, 110, a))
            T.ell(cx - 13, cy - 13, cx + 13, cy + 13, hx("#ffd37a"))
            T.ell(cx - 11, cy - 11, cx + 9, cy + 8, hx("#fff0b8"))
        else:
            lua_fina(T, cx, cy)
        _CACHE[k] = T.im
    if per != "noite":
        return _CACHE[k]
    T = Tela(WP, YR)
    T.im = _CACHE[k].copy()
    for x, y, i in ESTRELAS:
        if brilha(i, t):
            cor = hx("#fff1c9") if i % 3 else hx("#9fb4ec")
            T.px(x, y, cor)
            if i % 12 == 0:  # as que cintilam são maiores: uma cruz de 3 px
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    T.px(x + dx, y + dy, mix(cor, hx("#10203a"), .4))
    return T.im


# ------------------------------------------------------------------ efeitos de clique do céu e da água
def efeito_ceu_fino(T, per, f):
    """O efeito de clique no céu, no quadro f, desenhado em T (WP x HP): manhã, o sol rompe uma nuvem e solta raios
    tracejados em leque; tarde, dois anéis crescem em volta do sol e faíscas piscam; noite, uma estrela cadente cruza o céu e
    cruzes cintilam em volta da lua."""
    env = A.envelope(f, A.EFEITOS["ceu"], .25, .25)
    if per == "manha":
        ox, oy = 300, 92
        r = round(4 + 10 * env)
        T.ell(ox - r, oy - r, ox + r, oy + r, hx("#fff0b0"))
        T.ell(ox - r + 3, oy - r + 3, ox + r - 3, oy + r - 3, hx("#fffbe6"))
        comp = round(120 * env)
        for k in range(-5, 6):
            ang = math.radians(90 + k * 13)
            for s_ in range(r + 3, r + comp):
                if s_ % 4 < 3:
                    T.px(round(ox + math.cos(ang) * s_), round(oy + math.sin(ang) * s_),
                         mix(hx("#fff6c8"), hx("#aacfd2"), s_ / (r + comp) * .8))
    elif per == "tarde":
        cx, cy = ASTRO["tarde"]
        for dr, cor in ((22 + 24 * env, hx("#ffb870")), (32 + 32 * env, hx("#f09068"))):
            T.d.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], outline=cor)
        for k, (dx, dy) in enumerate(((-34, -20), (32, -26), (-26, 30), (38, 20))):
            if (f + k * 3) % 8 < 4:
                A.estrela4(T, cx + dx, cy + dy, hx("#fff4c0"), 4 if (f + k) % 2 else 2)
    else:
        cx, cy = ASTRO["noite"]
        if f < 16:
            u = f / 15
            x_, y_ = 600 - 360 * u, 6 + 130 * u
            for k in range(1, 70):
                T.px(round(x_ + k * .946), round(y_ - k * .33), mix(hx("#ffffff"), hx("#32447c"), k / 70))
            T.rect(round(x_) - 1, round(y_) - 1, 3, 3, hx("#ffffff"))
        for k, (dx, dy) in enumerate(((-26, -20), (28, -12), (24, 26), (-22, 22))):
            if (f + k * 2) % 6 < 3:
                A.estrela4(T, cx + dx, cy + dy, hx("#ffffff"), 4 if (f + k) % 3 == 1 else 3)


def agua_fx_fina(per, f):
    """O efeito de clique na água, no quadro f (WP x RIO_P): anéis de 1 px que se abrem e esmaecem, e um peixe que salta e
    cai com respingo; tingido pela hora como a água."""
    T = Tela(WP, RIO_P)
    for cx, cy, s0 in ((198, 28, 0), (132, 22, 5), (268, 24, 9)):
        a = f - s0
        r = 3 + a * 2.6
        if a < 0 or r > 54:
            continue
        T.d.ellipse([cx - r, cy - max(1, r * .3), cx + r, cy + max(1, r * .3)], outline=mix(ESPUMA, AGUA_CLARA, min(1, r / 54)))
    a = f - 3
    if 0 <= a <= 12:
        x, y = round(236 + a * 2.4), round(26 - 20 * math.sin(math.pi * a / 12))
        T.rect(x - 4, y, 8, 2, hx("#cfe0e6"))
        T.rect(x - 2, y - 1, 5, 1, hx("#6f8a96"))
        T.px(x - 6, y - (1 if a < 6 else 0), hx("#9fb6c0"))
    if a in (0, 1, 12, 13, 14):  # respingo na saída e na volta
        bx = 236 if a < 5 else 265
        for dx, dy in ((-4, -4), (4, -6), (0, -8), (6, -2), (-6, -2)):
            T.px(bx + dx, 30 + dy - (a % 3), ESPUMA)
    return A.tinge_agua(T.im, per)


def gollum_fino(T, per, f):
    """O segredo do Gollum, no quadro f: num tronco no canto esquerdo do rio, ele entra pela esquerda, olha para as canoas,
    murmura e sai. O desenho é o do Argonath da janela, espelhado para olhar para a direita, com a fala num balão à direita."""
    dur, saida = A.EFEITOS["gollum"], 44
    xo = -round(60 * (1 - f / 12)) if f < 12 else 0 if f < saida else -round(60 * (f - saida) / (dur - saida))
    g = ImageOps.mirror(A.gollum(f))
    gx, gy = 8 + xo, YR + 14 + round(math.sin(f / 2))
    T.put(A.grade(g, per), gx, gy)
    for k in range(3):  # marola na ponta do tronco, à esquerda
        if (f + k) % 3:
            T.rect(gx - 3 - 3 * k, gy + g.height - 3 + k, 3, 1, ESPUMA)
    if 16 <= f < 42:
        texto = "Meu precioso!"
        bw = largura(texto) + 8
        bx, by = gx + g.width - 6, gy - 14
        T.rect(bx, by, bw, 11, OL)
        T.rect(bx + 1, by + 1, bw - 2, 9, A.UI[per]["paper"])
        T.cantos(bx, by, bw, 11)
        T.rect(bx + 4, by + 11, 3, 2, OL)
        T.texto(bx + 4, by + 2, texto, A.UI[per]["ink"])


# ------------------------------------------------------------------ pedestal
def pedestal(per):
    """Degrau de pedra sob a tábua, um pouco mais largo que ela: topo com fio claro, junta de blocos e borda em selout."""
    w, h = BW + 8, 9
    T = Tela(w, h)
    T.rect(0, 0, w, h, OL)
    pedra(T, 1, 1, w - 2, h - 2, M | dict(s1=PEDRA["s1"], s2=PEDRA["s2"], s3=PEDRA["s3"], hi=PEDRA["hl"]), seed=7)
    tinge(T, 1, 1, w - 2, 1, PEDRA["hl"], .4)
    tinge(T, 1, h - 3, w - 2, 2, M["sh"], .45)
    T.cantos(0, 0, w, h)
    borda_colorida(T.im, OL, M)
    return A.grade(T.im, per)
