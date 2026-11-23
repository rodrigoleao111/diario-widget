"""Argonath em tela cheia, para o papel de parede: a mesma pintura das estátuas, com o rio e uma margem em primeiro plano
onde a tábua do diário se apoia, embaixo à direita.

A arte (um gerador por camada) está em argonath_arte.py; aqui ficam o cache por camada, a montagem do quadro, a atualização
parcial e as regiões clicáveis. A cena tem 640x360 pixels de arte (16:9) e é ampliada por um fator inteiro: 3 em 1920x1080.
Tudo usa o mesmo pixel, do céu à tábua e ao texto.

Os efeitos de clique são os do Argonath da janela (estátuas, canoas, nuvens, céu, água e os dois segredos), reposicionados
nesta cena; o diário (botões, lista, campo, calendário e configurações) é o mesmo, só que a tábua fica na margem e o campo
abre uma janelinha de digitação (a janela de papel de parede não recebe o teclado: ver diario/papel.py).

Camadas, de trás para frente: céu, astros e nuvens (que andam), a cordilheira (com a névoa do vão), as paredes das
estátuas, o rio, a névoa rente à água (que passa na frente da estátua da esquerda) e as canoas, a margem, o pedestal, a tábua com a interface e, na frente de tudo, o capim do pé.
"""
import math
from dataclasses import replace

from PIL import Image

from ..pixel import Tela
from . import argonath as A
from . import argonath_arte as arte
from .argonath import BW, BX, FOLGA, OL, Argonath, Y0
from .argonath_arte import CANOAS_F, ESTRELAS, HP, LX, NUVENS, PE, PX, RIO_P, RX, WP, X_RIO, YR, brilha
from .base import Regiao

R = 2  # pixels de arte por pixel da grade da referência (as coordenadas dos rostos das estátuas estão nessa grade)
MAX_TOPICOS_P = 10  # mais que isso a tábua subiria até o elmo da estátua da direita: o resto vira "… e mais N"
VEL_NUVENS = (.14, .20, .30, .24, .12)  # pixels de arte por quadro, como no Argonath da janela


def x_nuvem(i, largura, t):
    """Coluna (em pixels de arte) da nuvem i no quadro t: anda para a direita e dá a volta fora da tela."""
    return int((NUVENS[i][2] + VEL_NUVENS[i] * t) % (WP + 2 * largura)) - largura


class ArgonathPapel(Argonath):
    id = "argonath-papel"
    nome = "Argonath (papel de parede)"
    descricao = "As estátuas e o rio em tela cheia, com a tábua do diário numa margem embaixo à direita."
    Z = 3
    animacao_ms = 140  # ritmo cheio: usado enquanto um efeito de clique roda
    animacao_ociosa_ms = 140  # parada, a cena anda em tempo real a cada quadro: a água e as canoas andam 1 px por vez, sem saltos
    papel = True  # o widget põe a janela no fundo, cobrindo a tela (ver diario/papel.py)
    efeitos = dict(A.EFEITOS, nuvem4=18, olho=arte.EFEITO_OLHO)  # as do Argonath da janela mais a quinta nuvem e o Olho

    def __init__(self):
        super().__init__()
        self.tela = self.dest = (WP * self.Z, HP * self.Z)  # o monitor e o tamanho da cena nele; `pos` é onde a cena começa
        self.pos = (0, 0)
        self._pp = (None, None)  # primeiro plano (margem, pedestal, tábua, interface), com a chave de cache
        self._ult = None  # o que o último quadro inteiro mostrou: base da atualização parcial (ver `partes`)
        self._rio_ult = (None, None)  # a água do último quadro, com a chave (ver `_rio`)
        self._nevoa_ult = (None, None)  # a névoa da água do último quadro, com a chave (ver `_nevoa`)

    def ajusta_tela(self, w, h):
        """A cena cabe inteira no monitor, na maior ampliação que couber (3 em 1920x1080, 4 em 2560x1440, 6 em 4K, e
        fracionária nas outras, como 2,4 em 1536x960). Telas que não são 16:9 exatas ganham uma faixa: céu em cima
        (a margem e a tábua, embaixo à direita, ficam na borda de baixo) e, nas mais largas, a coluna da borda repetida.

        Fração deixa pixels de 2 e 3 de largura alternados; a ampliação inteira com faixa foi testada (passo 2 da skill pixel-art,
        fundamentos/resolucao-e-escala.md, seção 5.2) e é pior: a coluna repetida vira listra na rocha e na água, visível já com
        6% de faixa (1366x768) e feia com 20% (1600x900). Espelhar a faixa duplica as estátuas. Por isso a fração fica."""
        s = min(w / WP, h / HP)
        self.tela = (w, h)
        dw, dh = max(1, round(WP * s)), max(1, round(HP * s))
        self.dest = (w if w - dw <= 2 else dw, h if h - dh <= 2 else dh)  # 1 ou 2 pixels de sobra (1366x768) não valem uma faixa
        self.pos = ((w - self.dest[0]) // 2, h - self.dest[1])

    def _caixa(self, c):
        """Caixa em pixels de arte -> pixels do monitor (ampliação da cena mais o deslocamento da faixa)."""
        sx, sy, (ox, oy) = self.dest[0] / WP, self.dest[1] / HP, self.pos
        return round(ox + c[0] * sx), round(oy + c[1] * sy), round(ox + c[2] * sx), round(oy + c[3] * sy)

    def _moldura(self, im, per):
        """A cena já ampliada, no tamanho do monitor: o que sobra em cima é céu e, dos lados, a coluna da borda repetida."""
        sw, sh = self.tela
        dw, dh = self.dest
        ox, oy = self.pos
        if im.size == (sw, sh):
            return im
        tela = Image.new(im.mode, (sw, sh))
        if oy:
            ceu = self._ceu_base(per).crop((0, 0, WP, 1)).convert(im.mode).resize((dw, 1), Image.NEAREST)
            tela.paste(ceu.resize((dw, oy), Image.NEAREST), (ox, 0))
        tela.paste(im, (ox, oy))
        if ox:
            tela.paste(tela.crop((ox, 0, ox + 1, sh)).resize((ox, sh), Image.NEAREST), (0, 0))
        if sw - ox - dw:
            tela.paste(tela.crop((ox + dw - 1, 0, ox + dw, sh)).resize((sw - ox - dw, sh), Image.NEAREST), (ox + dw, 0))
        return tela

    def calendario(self, e):
        return self._dialogo(super().calendario, e)

    def configuracoes(self, e, miniaturas):
        return self._dialogo(super().configuracoes, e, miniaturas)

    def _dialogo(self, fazer, *args):
        """Os diálogos saem em escala 2, como nos outros temas: em escala 3 a lista de temas passaria da altura da tela."""
        z, self.Z = self.Z, 2
        try:
            return fazer(*args)
        finally:
            self.Z = z

    # --- camadas ---
    def _primeiro_plano(self, g, ui, per):
        """A margem, o pedestal, a tábua com a interface e o capim do pé, numa camada só: só muda com o estado do diário."""
        chave = (self._ui[0], per)
        if self._pp[0] != chave:
            _agua, terra, frente = self._guarda(("margem", per), lambda: arte.margem_fina(per))
            alt = g["hb"] + FOLGA
            py = PE - alt  # topo da tábua
            caixa = (BX, Y0 - 11, BX + BW, Y0 + alt)  # a tábua e, acima dela, a plaquinha "Hoje"
            T = Tela(WP, HP)
            T.im.alpha_composite(terra)
            T.im.alpha_composite(self._guarda(("pedestal", per), lambda: arte.pedestal(per)), (PX - 4, PE))
            T.im.alpha_composite(self._tabua(per, g).crop(caixa), (PX, py - 11))
            T.im.alpha_composite(ui.crop(caixa), (PX, py - 11))
            T.im.alpha_composite(frente)
            self._pp = (chave, T.im)
        return self._pp[1]

    def _ceu_base(self, per):
        return self._guarda(("ceu", per), lambda: arte.ceu_fino(WP, YR + 8, per, n=40, ondula=True, riscos=False))

    def _nuvem(self, per, i):
        _w, _h, _x, _y, semente = NUVENS[i]
        return self._guarda(("nuvem", per, i), lambda: arte.nuvem_fina(NUVENS[i][0], NUVENS[i][1], semente, per))

    def _ceu(self, per, t, ef):
        """Céu com astros, o efeito de céu e as nuvens (que andam). Devolve a camada e a caixa de cada nuvem."""
        T = Tela(WP, HP, OL)
        T.im.paste(self._ceu_base(per), (0, 0))
        if per != "manha":
            T.put(arte.astros_finos(per, t), 0, 0)
        if "ceu" in ef:
            arte.efeito_ceu_fino(T, per, ef["ceu"])
        caixas = []
        for i, (_w, _h, _x0, y, _s) in enumerate(NUVENS):
            n = self._nuvem(per, i)
            x = x_nuvem(i, n.width, t)
            f = ef.get(f"nuvem{i}")
            T.put(n, x + ((1 if f % 2 else -1) if f is not None else 0), y)
            if f is not None:
                A.chuva(T, per, f, x, y, n.width, n.height)
            caixas.append((x, y, x + n.width, y + n.height))
        return T.im, caixas

    def _montes(self, per):
        """(cristas e névoa sobre transparente, parede esquerda, parede direita, topo do penhasco da esquerda)."""
        def faz():
            base = Tela(WP, HP)
            base.put(arte.cristas_finas(per), 0, 0)
            base.put(arte.olho_fino(per), 0, 0)  # o Olho fechado vem por cima, já na cor tingida da torre
            esq, dire = arte.paredes_finas(per)
            return base.im, esq, dire, A.cume(esq)
        return self._guarda(("montes", per), faz)

    def _estatuas(self, per, ef, esq, dire, topo, y0):
        """As paredes (com a cabeça virada, se a estátua foi clicada) e, na frente delas, poeira, olhos e orcs."""
        pa = A.virar_cabeca(esq, "isildur", ef["isildur"], LX[0]) if "isildur" in ef else esq
        pb = A.virar_cabeca(dire, "anarion", ef["anarion"], RX[0]) if "anarion" in ef else dire
        F = Tela(WP, HP)
        F.put(pa, 0, y0)
        F.put(pb, WP - dire.width, y0)
        for nome in ("isildur", "anarion"):
            if nome in ef:
                arte.poeira_fina(F, nome, ef[nome], y0, per)
                arte.olhos_finos(F, nome, ef[nome], y0)
        if "orcs" in ef:
            A.orcs_em(F, per, ef["orcs"], topo, y0)
        return F.im

    @staticmethod
    def _limita(e):
        if len(e.topicos) > MAX_TOPICOS_P:
            return replace(e, topicos=e.topicos[:MAX_TOPICOS_P], extra=e.extra + len(e.topicos) - MAX_TOPICOS_P)
        return e

    def _paredes(self, per):
        """As duas paredes das estátuas, sem efeito de clique, numa camada só."""
        _base, esq, dire, topo = self._montes(per)
        y0 = YR + 6 - esq.height
        return self._guarda(("paredes", per), lambda: self._estatuas(per, {}, esq, dire, topo, y0))

    def _rio(self, per, t):
        """A água do quadro t. Guarda só o último quadro (o quadro inteiro e a atualização parcial pedem o mesmo): as linhas
        andam em passos diferentes e não se repetem num ciclo curto, então guardar por `t % N` traria de volta um quadro
        antigo e a água daria um salto a cada volta."""
        if self._rio_ult[0] != (per, t):
            self._rio_ult = ((per, t), arte.rio_fino(t, per, self._montes(per)[1]))
        return self._rio_ult[1]

    def _nevoa(self, per, t):
        """A névoa rente à água no quadro t (anda sempre; guarda só o último quadro, como a água)."""
        if self._nevoa_ult[0] != (per, t):
            self._nevoa_ult = ((per, t), arte.nevoa_agua_fina(t, per))
        return self._nevoa_ult[1]

    def quadro(self, e, t):
        e = self._limita(e)
        per, ef = e.periodo, e.efeitos
        g = self._geo(e)
        ui, regs, campo = self._ui_do(e, g)
        ceu, caixas = self._ceu(per, t, ef)
        base, esq, dire, topo = self._montes(per)
        y0 = YR + 6 - esq.height
        img = ceu.copy()
        img.alpha_composite(base)
        if "olho" in ef:  # o Olho olha em volta e o feixe varre a paisagem; fica atrás das estátuas e do rio
            img.alpha_composite(arte.olho_fx(per, ef["olho"]))
        if any(n in ef for n in ("isildur", "anarion", "orcs")):
            img.alpha_composite(self._estatuas(per, ef, esq, dire, topo, y0))
        else:
            img.alpha_composite(self._paredes(per))
        img.alpha_composite(self._rio(per, t), (0, YR))
        if "agua" in ef:
            img.alpha_composite(arte.agua_fx_fina(per, ef["agua"]), (0, YR))
        img.alpha_composite(self._nevoa(per, t), (0, YR - arte.NEVOA_SOBE))  # na frente da parede da esquerda e da água
        img.alpha_composite(arte.canoas_finas(t, per, ef), (0, YR))
        if "gollum" in ef:
            G = Tela(WP, HP)
            arte.gollum_fino(G, per, ef["gollum"])
            img.alpha_composite(G.im)
        img.alpha_composite(self._guarda(("margem", per), lambda: arte.margem_fina(per))[0])
        img.alpha_composite(self._primeiro_plano(g, ui, per))
        z, self.Z = self.Z, 1  # a cena sai em pixels de arte; a ampliação até o monitor é feita aqui, de uma vez
        try:
            q = self._final(img, self._regioes(g, regs, campo, caixas, y0), campo, per)
        finally:
            self.Z = z
        q.imagem = self._moldura(q.imagem.resize(self.dest, Image.NEAREST), per)
        q.regioes = [Regiao(r.nome, self._caixa(r.caixa), r.dica, r.cursor) for r in q.regioes]
        q.entrada = None  # o widget do papel de parede não tem campo de verdade: o clique abre `Widget.digitar`
        q.estilo_entrada["fonte"] = ("Consolas", round(4.5 * self.dest[0] / WP))
        self._ult = dict(chave=(self._ui[0], per, self.tela), livre=not ef, nx=[c[0] for c in caixas], t_est=t,
                         q=q, ireg={r.nome: i for i, r in enumerate(q.regioes)})
        return q

    # --- atualização parcial ---
    def partes(self, e, t):
        """O que mudou desde o último quadro inteiro, parada a animação (nenhum efeito de clique rodando): a faixa do rio
        com as canoas, a névoa sobre o pé da estátua da esquerda, as nuvens que andaram um pixel e as poucas estrelas que cintilam. O resto (céu, estátuas, margem,
        tábua) não é nem refeito nem repintado. `None` pede um quadro inteiro: o diário mudou ou há efeito de clique."""
        u = self._ult
        if u is None or e.efeitos or not u["livre"] or self.dest[0] != self.tela[0]:  # com faixa dos lados, o quadro inteiro a cada vez
            return None
        e = self._limita(e)
        per = e.periodo
        g = self._geo(e)
        ui, _regs, _campo = self._ui_do(e, g)
        if u["chave"] != (self._ui[0], per, self.tela):  # outro estado, período ou tela: o quadro inteiro é outro
            return None
        pp = self._primeiro_plano(g, ui, per)
        nuv = []
        for i, (_w, _h, _x0, y, _s) in enumerate(NUVENS):
            n = self._nuvem(per, i)
            nuv.append((n, x_nuvem(i, n.width, t), y))
        caixas = []
        for i, (n, x, y) in enumerate(nuv):
            xo = u["nx"][i]
            if x != xo:  # a nuvem andou: repinta de onde estava até onde ficou, e a região de clique a acompanha
                caixas.append((max(0, min(x, xo) - 1), y, min(WP, max(x, xo) + n.width + 1), y + n.height))
                u["nx"][i] = x
                self._move_regiao(i, x, y, n)
        if per == "noite":
            for sx, sy, k in ESTRELAS:
                if k % 12 == 0 and brilha(k, t) != brilha(k, u["t_est"]):
                    caixas.append((sx - 2, sy - 2, sx + 3, sy + 3))
            u["t_est"] = t
        ast = None
        if per == "tarde":
            ast = arte.astros_finos(per, 0)
        elif per == "noite" and caixas:
            ast = arte.astros_finos(per, t)
        pedacos = [self._pedaco(per, t, (0, YR, X_RIO, HP), pp, None, nuv),
                   self._pedaco(per, t, (0, YR - arte.NEVOA_SOBE, arte.NEVOA_X, YR), pp, None, nuv)]  # a névoa sobre a estátua
        pedacos += [self._pedaco(per, t, box, pp, ast, nuv) for box in caixas]
        return [p for p in pedacos if p]

    def _move_regiao(self, i, x, y, n):
        j = self._ult["ireg"].get(f"efeito:nuvem{i}")
        if j is not None:
            self._ult["q"].regioes[j] = Regiao(f"efeito:nuvem{i}", self._caixa((x, y, x + n.width, y + n.height)))

    def _compoe(self, per, t, box, pp, ast, nuv):
        """O pedaço `box` (pixels de arte) da cena, com as mesmas camadas e a mesma ordem do quadro inteiro."""
        x0, y0, x1, y1 = box
        T = Tela(x1 - x0, y1 - y0, OL)
        if y1 <= YR:  # céu: o que está atrás das montanhas e das estátuas
            T.im.paste(self._ceu_base(per).crop(box))
            if ast is not None:
                T.im.alpha_composite(ast, (0, 0), box)
            for n, x, y in nuv:
                T.put(n, x - x0, y - y0)
            T.im.alpha_composite(self._montes(per)[0], (0, 0), box)
            T.im.alpha_composite(self._paredes(per), (0, 0), box)
            T.put(self._nevoa(per, t), -x0, YR - arte.NEVOA_SOBE - y0)
        else:  # a faixa do rio, que cobre tudo o que está atrás dela
            T.im.paste(self._rio(per, t).crop((x0, 0, x1, RIO_P)))
            T.put(self._nevoa(per, t), -x0, YR - arte.NEVOA_SOBE - y0)
            T.im.alpha_composite(arte.canoas_finas(t, per), (0, 0), (x0, 0, x1, RIO_P))
        T.im.alpha_composite(self._guarda(("margem", per), lambda: arte.margem_fina(per))[0], (0, 0), box)
        T.im.alpha_composite(pp, (0, 0), box)
        return T.im

    def _pedaco(self, per, t, box, pp, ast, nuv):
        """(imagem RGB ampliada, x, y) do pedaço, em pixels do monitor; None se sobrou nada. Cada pixel do monitor vem do
        mesmo pixel de arte que viria no quadro inteiro (`resize` e `transform` amostram o ponto central), então os
        pedaços emendam sem marca mesmo com ampliação fracionária."""
        x0, y0, x1, y1 = max(0, box[0]), max(0, box[1]), min(WP, box[2]), min(HP, box[3])
        if x1 <= x0 or y1 <= y0:
            return None
        dw, dh = self.dest
        sx, sy = dw / WP, dh / HP
        j0, j1 = max(0, math.ceil(x0 * sx - .5)), min(dw, math.ceil(x1 * sx - .5))  # colunas do monitor cujo centro cai no pedaço
        k0, k1 = max(0, math.ceil(y0 * sy - .5)), min(dh, math.ceil(y1 * sy - .5))
        if j1 <= j0 or k1 <= k0:
            return None
        im = self._compoe(per, t, (x0, y0, x1, y1), pp, ast, nuv)
        im = im.transform((j1 - j0, k1 - k0), Image.AFFINE, (1 / sx, 0, j0 / sx - x0, 0, 1 / sy, k0 / sy - y0), Image.NEAREST)
        return im.convert("RGB"), self.pos[0] + j0, self.pos[1] + k0

    def _regioes(self, g, regs, campo, caixas, y0):
        """Regiões da tábua deslocadas para a margem, a do campo e as áreas clicáveis do cenário (sem dica; só o cursor de
        mão, e nenhum nos segredos). A primeira que casa vence: a tábua primeiro, depois as menores (segredos, canoas,
        rostos, nuvens) e, por último, o céu e a água."""
        alt = g["hb"] + FOLGA
        dx, dy = PX - BX, PE - alt - Y0
        sai = [Regiao("campo", (campo[0] + dx, campo[1] + dy, campo[2] + dx, campo[3] + dy),
                      "Escrever uma atividade (Enter lança)", "xterm")]
        sai += [Regiao(r.nome, (r.caixa[0] + dx, r.caixa[1] + dy, r.caixa[2] + dx, r.caixa[3] + dy), r.dica, r.cursor)
                for r in regs]
        sai.append(Regiao("placa", (PX, PE - alt - 11, PX + BW, PE + 9), "", ""))  # o corpo da tábua não deixa o clique passar
        sai.append(Regiao("efeito:orcs", (0, y0 + 120, A.ORCS_X1 + 4, YR + 1), "", ""))
        for i, (L, cx, linha, _quem) in enumerate(CANOAS_F):
            sai.append(Regiao(f"efeito:canoa{i}", (cx - L // 2 - 4, YR + linha - 26, cx + L // 2 + 4, YR + linha + 3)))
        sai.append(Regiao("efeito:gollum", (0, YR + 8, 90, HP), "", ""))  # o canto esquerdo do rio
        dire_x0 = WP - (RX[1] - RX[0]) * R  # onde começa a parede da direita
        for nome, x_do_ref in (("isildur", lambda rx: (rx - LX[0]) * R), ("anarion", lambda rx: dire_x0 + (rx - RX[0]) * R)):
            c = A.CLIQUE_ROSTO[nome]
            sai.append(Regiao(f"efeito:{nome}", (x_do_ref(c[0]), y0 + c[1] * R, x_do_ref(c[2]), y0 + c[3] * R)))
        ox, oy = arte.posicao_olho()
        sai.append(Regiao("efeito:olho", (ox - 14, oy - 14, ox + 14, oy + 16)))  # o Olho e o alto da torre
        for i, (x0, y1, x1, y2) in enumerate(caixas):
            sai.append(Regiao(f"efeito:nuvem{i}", (x0, y1, x1, y2)))
        sai += [Regiao("efeito:ceu", (LX[1] * R, 0, dire_x0, YR - 80)), Regiao("efeito:agua", (0, YR + 2, 280, HP))]
        return sai
