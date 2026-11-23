import ctypes
import re
import sys
import subprocess
import traceback
import threading
import time
import tkinter as tk
from datetime import date, datetime, timedelta

from PIL import Image, ImageTk

from . import barra, coleta_claude, config, db, exporta, papel, preferencias, resumir, temas
from .temas import base as tbase
from .temas.base import Estado, periodo_do_horario

LOG = config.RAIZ / "widget.log"
REFRESH_MS = 60_000
MAX_TOPICOS = 14
CHAVE = (1, 2, 3)  # cor-chave de transparência: nos temas de formato livre, o que tem essa cor vira buraco na janela
# "30min texto", "1h30 texto"; "@Projeto" em qualquer ponto do texto escolhe o projeto
_PROJETO = re.compile(r"@(\S+)")


def resumo_velho(con, dia):
    """Hora (ISO) da atividade de trabalho posterior a um resumo com tópicos já gravado; None se não há o que atualizar."""
    return db.resumo_defasado(con, dia) if db.topicos_do_dia(con, dia) else None


def topicos(con, dia):
    """[(texto, tipo)] do que houve no dia; tipo: '' (resumo), 'manual', 'aviso' ou 'resumir' (linha com o botão de resumir)."""
    r = con.execute("SELECT topicos, gerado_em FROM resumos WHERE data=?", (dia,)).fetchone()
    itens = [(t, "") for t in (r["topicos"].splitlines() if r else []) if t.strip()]
    evs = con.execute("SELECT * FROM eventos WHERE data=? ORDER BY ts", (dia,)).fetchall()
    if itens:
        velho = resumo_velho(con, dia)
        if velho:  # resumo gravado, mas o dia ganhou atividade depois dele
            itens.append((f"Resumo de {r['gerado_em'][11:16]}; há atividade até {velho[11:16]}", "resumir"))
    else:
        projetos = [p for p in dict.fromkeys(e["projeto"] for e in evs if e["origem"] == "claude")]
        commits = [e["texto"].replace(" — RED ", " — ") for e in evs if e["origem"] == "svn"]
        if projetos or commits:
            itens = [("Resumo do dia ainda não escrito", "resumir")]
            itens += [(f"Sessões em {p}", "") for p in projetos] + [(c, "") for c in commits]
    itens += [(f"{e['texto']}" + (f" ({exporta.hm(e['minutos'])})" if e["minutos"] else ""), "manual")
              for e in evs if e["origem"] == "manual"]
    return itens


def dias_com_registro(con, ano, mes):
    """Dias do mês (AAAA-MM-DD) que têm algum evento ou segmento."""
    pref = f"{ano:04d}-{mes:02d}-%"
    return {r[0] for r in con.execute("SELECT data FROM eventos WHERE data LIKE ? UNION SELECT data FROM segmentos WHERE data LIKE ?", (pref, pref))}


def interpretar(entrada):
    """'1h30 reunião @CS #12350' -> (texto, projeto, minutos)."""
    d = db.duracao(entrada)
    minutos, entrada = d if d else (None, entrada)
    p = _PROJETO.search(entrada)
    projeto = p.group(1) if p else "(manual)"
    return re.sub(r"\s+", " ", _PROJETO.sub("", entrada)).strip(), projeto, minutos


def _hex(c):
    return "#%02x%02x%02x" % tuple(c[:3])


def _imagem_tk(q):
    """O Quadro do tema como imagem RGB para o Tk. Nos quadros transparentes, alfa < 128 vira a cor-chave."""
    if q.transparente:
        saida = Image.new("RGB", q.imagem.size, CHAVE)
        saida.paste(q.imagem.convert("RGB"), mask=q.imagem.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
        return saida
    if q.imagem.getchannel("A").getextrema()[0] == 255:  # sem nenhum pixel transparente: nada a compor sobre o fundo
        return q.imagem.convert("RGB")
    fundo = Image.new("RGBA", q.imagem.size, q.fundo)
    fundo.alpha_composite(q.imagem)
    return fundo.convert("RGB")


class Superficie:
    """Canvas que mostra o Quadro de um tema e traduz o mouse em regiões. Serve à janela principal e aos diálogos."""

    def __init__(self, janela, ao_mover, ao_clicar, com_entrada=False):
        self.j, self.ao_mover, self.ao_clicar = janela, ao_mover, ao_clicar
        self.c = tk.Canvas(janela, highlightthickness=0, bd=0)
        self.c.pack()
        self.item = self.c.create_image(0, 0, anchor="nw")
        self.regioes, self.foto, self.tam, self._modo, self.estilo = [], None, None, None, {}
        self._pedacos = {}  # {(largura, altura): imagem do Tk} dos pedaços colados por `cola`
        self.entrada = self.item_entrada = None
        if com_entrada:
            self.entrada = tk.Entry(self.c, relief="flat", bd=0, highlightthickness=0)
            self.item_entrada = self.c.create_window(0, 0, window=self.entrada, anchor="nw", state="hidden")
        self.c.bind("<Motion>", lambda e: self._mover(e))
        self.c.bind("<Leave>", lambda e: self.ao_mover(None, e))
        self.c.bind("<ButtonPress-1>", lambda e: self.ao_clicar(self.regiao_em(e.x, e.y), e))

    def regiao_em(self, x, y):
        """A região sob o ponto; 'arrastar' só vale se nenhuma outra (botão, linha, etiqueta) estiver ali."""
        arrastar = None
        for r in self.regioes:
            x0, y0, x1, y1 = r.caixa
            if x0 <= x < x1 and y0 <= y < y1:
                if r.nome != "arrastar":
                    return r
                arrastar = r
        return arrastar

    def _mover(self, e):
        r = self.regiao_em(e.x, e.y)
        self.c.configure(cursor=r.cursor if r and r.cursor else "")
        self.ao_mover(r, e)

    def cola(self, partes):
        """Atualização parcial: cola pedaços (imagem RGB, x, y) na imagem já mostrada. O Tk repinta só a área de cada um."""
        for im, x, y in partes:
            pedaco = self._pedacos.get(im.size)  # a faixa do rio repete o tamanho a cada tique: reaproveita a imagem do Tk
            if pedaco is None:
                if len(self._pedacos) > 24:  # as nuvens têm tamanhos variados: não deixa a lista crescer sem fim
                    self._pedacos.clear()
                pedaco = self._pedacos[im.size] = ImageTk.PhotoImage(im)
            else:
                pedaco.paste(im)
            self.foto.tk.call(str(self.foto), "copy", str(pedaco), "-to", x, y)

    def mostra(self, q, alpha=1.0):
        img = _imagem_tk(q)
        if self.foto is not None and self.tam == img.size:  # mesmo tamanho: reaproveita a imagem do Tk (poupa ~6 ms em tela cheia)
            self.foto.paste(img)
        else:
            self.foto = ImageTk.PhotoImage(img)
        self.c.itemconfigure(self.item, image=self.foto)
        if img.size != self.tam:
            self.tam = img.size
            self.c.configure(width=img.width, height=img.height)
            self.j.geometry(f"{img.width}x{img.height}")
        modo = (q.transparente, q.fundo, alpha)
        if modo != self._modo:
            self._modo = modo
            cor = _hex(CHAVE) if q.transparente else q.fundo
            self.c.configure(bg=cor)
            self.j.configure(bg=cor)
            self.j.attributes("-transparentcolor", _hex(CHAVE) if q.transparente else "")
            self.j.attributes("-alpha", alpha)
        self.regioes, self.estilo = q.regioes, q.estilo_entrada
        if self.entrada is not None:
            if q.entrada:
                x0, y0, x1, y1 = q.entrada
                self.c.coords(self.item_entrada, x0, y0)
                self.c.itemconfigure(self.item_entrada, width=x1 - x0, height=y1 - y0, state="normal")
                s = q.estilo_entrada
                self.entrada.configure(bg=s["bg"], fg=s["fg"], insertbackground=s["cursor"], font=s["fonte"],
                                       disabledbackground=s["bg"])
            else:
                self.c.itemconfigure(self.item_entrada, state="hidden")


class Dialogo:
    """Janela sem borda (calendário, configurações) desenhada pelo tema."""

    def __init__(self, widget, fazer_quadro, ao_clicar, fecha_ao_perder_foco=False):
        self.w, self.fazer_quadro, self.clique, self.hover = widget, fazer_quadro, ao_clicar, ""
        self.vivo, self._arrasto = True, None
        self.top = tk.Toplevel(widget.root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.sup = Superficie(self.top, self._mover, self._clicar)
        self.desenha()
        self.top.update_idletasks()
        r = widget.root
        x, y = r.winfo_x(), r.winfo_y() + r.winfo_height() + 4
        if y + self.top.winfo_reqheight() > r.winfo_screenheight():  # sem espaço embaixo: abre em cima
            y = r.winfo_y() - self.top.winfo_reqheight() - 4
        if widget.papel:  # a janela é a tela inteira: o diálogo abre no meio dela
            x = (r.winfo_screenwidth() - self.top.winfo_reqwidth()) // 2
            y = (r.winfo_screenheight() - self.top.winfo_reqheight()) // 2
        self.top.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.top.focus_force()
        self.top.bind("<Escape>", lambda _e: self.fecha())
        self.top.bind("<B1-Motion>", self._arrasta)
        if fecha_ao_perder_foco:  # clicar fora fecha
            self.top.bind("<FocusOut>", lambda _e: r.after(150, self.fecha))

    def desenha(self):
        if self.vivo:
            self.sup.mostra(self.fazer_quadro(self.hover))

    def _mover(self, r, _e):
        nome = "" if (r is None or r.nome == "arrastar") else r.nome
        if nome != self.hover:
            self.hover = nome
            self.desenha()

    def _clicar(self, r, e):
        if r is None:
            return
        if r.nome == "arrastar":
            self._arrasto = (e.x_root - self.top.winfo_x(), e.y_root - self.top.winfo_y())
        else:
            self.clique(r.nome)

    def _arrasta(self, e):
        if self._arrasto:
            self.top.geometry(f"+{e.x_root - self._arrasto[0]}+{e.y_root - self._arrasto[1]}")

    def fecha(self):
        if self.vivo:
            self.vivo = False
            self.top.destroy()
            self.w.dialogo_fechado(self)


class Widget:
    def __init__(self):
        self.dia = date.today()
        self.segue_hoje = True  # widget deixado aberto de um dia para o outro acompanha a virada
        self.con = db.conectar()
        self.coletando = self.resumindo = self.refazer = False
        self.itens, self.status, self.status_tipo, self.hover, self.t = [], "", "dica", "", 0
        self.efeitos = {}  # {nome: quadro (self.t) em que o clique disparou}; ver Tema.efeitos
        self.dialogos, self._balao, self._balao_id, self._anim_id, self._arrasto = [], None, None, None, None
        self._cal_mes, self._cal_dias, self._minis = None, {}, None
        # barra de tarefas: estado escolhido na tela de configurações, cópia das opções do TranslucentTB e mudanças feitas
        # antes de a tela de boas-vindas dele ser aceita
        self._barra_sel, self._barra_cfg, self._barra_pendente = barra.ESTADOS[0][0], None, []
        self.papel, self.coberto, self._vigia_id, self._digitando, self._no_fundo = False, False, None, None, False
        self._na_frente, self._na_frente_ate = False, 0  # o papel de parede foi trazido à frente pelo ícone da bandeja (ver `trazer_frente`)
        self._tela = None  # tamanho do monitor principal para o qual o papel de parede foi desenhado
        self._t0, self._cobriu_em = time.monotonic(), None  # origem do relógio dos temas que andam em tempo real
        self.bandeja = None
        prefs = preferencias.ler()
        self.tema = temas.obter(prefs.get("tema"))
        r = self.root = tk.Tk()
        r.report_callback_exception = self._erro
        r.overrideredirect(True)
        try:
            r.geometry(f"+{prefs['x']}+{prefs['y']}")
        except (KeyError, tk.TclError):
            r.geometry(f"+{r.winfo_screenwidth() - 520}+40")
        self.sup = Superficie(r, self._ao_mover, self._ao_clicar, com_entrada=True)
        self.entrada = self.sup.entrada
        self.entrada.bind("<Return>", self.lancar)
        self.sup.c.bind("<B1-Motion>", self._arrasta, add="+")
        self.sup.c.bind("<ButtonRelease-1>", lambda _e: self._fim_arraste(), add="+")
        self._ajusta_tema()
        self.recarrega()
        self._cabe_na_tela()
        self._modo_janela()
        self._anima()
        r.after(REFRESH_MS, self._tick)
        if not preferencias.PREVIEW:
            try:
                from . import bandeja
                self.bandeja = bandeja.Bandeja("Diário de atividades (aberto)")
                r.after(250, self._ouve_bandeja)
            except Exception:  # sem pywin32/Pillow o widget funciona igual, só não tem o ícone
                self._erro(*sys.exc_info())
            if barra.instalado():  # barra personalizada precisa do TranslucentTB aberto, e ele pode não ter iniciado com o Windows
                r.after(1500, self._garante_barra)

    # --- estado e desenho ---
    def estado(self, **extra):
        itens = self.itens
        status, tipo = self.status, self.status_tipo
        if self.tema.hover_no_status and self.hover.startswith("linha:"):  # texto inteiro ao passar o mouse
            i = int(self.hover.split(":")[1])
            if i < len(itens):
                status, tipo = itens[i][0], "dica"
        return Estado(dia=self.dia, eh_hoje=self.dia == date.today(), topicos=itens[:MAX_TOPICOS],
                      extra=max(len(itens) - MAX_TOPICOS, 0), status=status, status_tipo=tipo, hover=self.hover,
                      periodo=periodo_do_horario(), tema_atual=self.tema.id, temas=temas.lista(),
                      temas_papel={i for i, t in temas.TEMAS.items() if t.papel}, resumindo=self.resumindo,
                      refazer=self.refazer, efeitos=self._efeitos_ativos(), **extra)

    def _efeitos_ativos(self):
        """{nome: quadros desde o clique} dos efeitos que ainda não acabaram; os que acabaram saem da lista."""
        duracao = self.tema.efeitos
        self.efeitos = {n: t0 for n, t0 in self.efeitos.items() if self.t - t0 < duracao.get(n, 0)}
        return {n: self.t - t0 for n, t0 in self.efeitos.items()}

    def redesenha(self, animando=False):
        """Desenha o quadro. Num tique da animação (`animando`), o tema pode pedir só uma atualização parcial: colar nos
        pedaços da imagem que mudaram, em vez de refazer e repintar a janela toda."""
        if self.coberto:  # ninguém vendo o papel de parede: nada a desenhar até ele voltar a aparecer
            return
        e = self.estado()
        if animando:
            partes = self.tema.partes(e, self.t)
            if partes is not None:
                self.sup.cola(partes)
                return
        alpha = 0.97 if self.tema.id == "classico" else 1.0
        self.sup.mostra(self.tema.quadro(e, self.t), alpha)

    def recarrega(self, msg=None, tipo="ok"):
        """Relê os tópicos do banco e redesenha. Sem msg, a linha de status volta à dica de uso."""
        self.itens = topicos(self.con, self.dia.isoformat())
        self.refazer = resumo_velho(self.con, self.dia.isoformat()) is not None
        self.status, self.status_tipo = (msg, tipo) if msg else ("", "dica")
        self.redesenha()

    def mensagem(self, msg, tipo="ok"):
        self.status, self.status_tipo = msg, tipo
        self.redesenha()

    def _anima(self):
        """Um quadro de animação do tema; temas sem animação só redesenham quando o estado muda."""
        self._anim_id = None
        ms, lento = self.tema.animacao_ms, self.tema.animacao_ociosa_ms
        if not ms or self.coberto:  # coberta, o timer para de vez: o vigia o religa quando a janela voltar a aparecer
            return
        if lento:  # anda em tempo real, então o tique pode ser mais espaçado sem a cena ficar mais lenta
            self.t = self._relogio()
        else:
            self.t += 1
        self.redesenha(animando=True)
        self._anim_id = self.root.after(ms if self.efeitos or not lento else lento, self._anima)  # efeito de clique pede o ritmo cheio

    def _relogio(self):
        """Quadros de `animacao_ms` desde que o tema entrou em cena (sem contar o tempo em que a janela esteve coberta)."""
        return int((time.monotonic() - self._t0) * 1000 / self.tema.animacao_ms)

    def _tick(self):
        if self.segue_hoje:
            self.dia = date.today()
        self.recarrega()
        self.root.after(REFRESH_MS, self._tick)

    # --- mouse ---
    def _ao_mover(self, r, _e):
        if self._arrasto:
            return
        nome = "" if (r is None or r.nome == "arrastar") else r.nome
        if nome != self.hover:
            self.hover = nome
            self._esconde_balao()
            if r and r.dica:
                self._balao_id = self.root.after(450, lambda: self._mostra_balao(r))
            self.redesenha()

    def _ao_clicar(self, r, e):
        if r is None:
            return
        self._esconde_balao()
        if r.nome == "arrastar":
            self._ini_arraste(e)
            return
        if r.nome == "campo":  # papel de parede: a janela não tem teclado, o campo abre uma janela de digitação
            self.digitar()
            return
        if r.nome.startswith("efeito:"):  # enfeite do cenário: o tema desenha a reação, quadro a quadro
            nome = r.nome[len("efeito:"):]
            if nome in self.tema.efeitos and nome not in self._efeitos_ativos():  # no meio do efeito, não reinicia
                if self.tema.animacao_ociosa_ms:  # ritmo lento: sai dele já neste quadro, com o relógio em dia
                    self.t = self._relogio()
                    if self._anim_id:
                        self.root.after_cancel(self._anim_id)
                self.efeitos[nome] = self.t
                if self.tema.animacao_ociosa_ms:
                    self._anima()
                else:
                    self.redesenha()
            return
        acao = {"fechar": self.fechar, "config": self.configuracoes, "relatorio": self.relatorio, "atualizar": self.coletar,
                "resumir": self.resumir, "proximo": lambda: self.mover(1), "anterior": lambda: self.mover(-1), "calendario": self.calendario,
                "hoje": self.ir_hoje}.get(r.nome)
        if acao:
            acao()

    def _mostra_balao(self, r):
        self._esconde_balao()
        fundo, texto, borda = self.tema.cores_balao
        j = self._balao = tk.Toplevel(self.root)
        j.overrideredirect(True)
        j.attributes("-topmost", True)
        tk.Label(j, text=r.dica, bg=fundo, fg=texto, font=("Segoe UI", 9), padx=8, pady=4, justify="left",
                 wraplength=260, highlightthickness=1, highlightbackground=borda).pack()
        j.update_idletasks()
        x0, y0, x1, y1 = r.caixa
        x = min(self.root.winfo_rootx() + x0, self.root.winfo_screenwidth() - j.winfo_reqwidth() - 4)
        y = self.root.winfo_rooty() + y1 + 6
        if y + j.winfo_reqheight() > self.root.winfo_screenheight():  # sem espaço embaixo: aparece em cima
            y = self.root.winfo_rooty() + y0 - j.winfo_reqheight() - 6
        j.geometry(f"+{max(x, 0)}+{y}")

    def _esconde_balao(self):
        if self._balao_id:
            self.root.after_cancel(self._balao_id)
            self._balao_id = None
        if self._balao:
            self._balao.destroy()
            self._balao = None

    # --- ações ---
    def ir_hoje(self):
        self.dia = date.today()
        self.segue_hoje = True
        self.recarrega()

    def mover(self, delta):
        self.dia = min(self.dia + timedelta(days=delta), date.today())
        self.segue_hoje = self.dia == date.today()
        self.recarrega()

    def lancar(self, _e=None):
        bruto = self.entrada.get().strip()
        if not bruto:
            return
        texto, projeto, minutos = interpretar(bruto)
        if not texto:
            return self.recarrega("Escreva o texto da atividade.", "erro")
        db.lancar(self.con, texto, self.dia, projeto, "trabalho", minutos)
        self.entrada.delete(0, "end")
        self.recarrega("Lançado" + (f" ({exporta.hm(minutos)})" if minutos else " (sem duração)"))

    def coletar(self):
        if self.coletando or self.resumindo:
            return
        self.coletando = True
        self.mensagem("Coletando sessões do Claude Code…", "info")

        def trabalho():
            coleta_claude.coletar(db.conectar(), self.dia)

        self._th = threading.Thread(target=trabalho, daemon=True)
        self._th.start()
        self.root.after(400, self._espera)

    def _espera(self):
        if self._th.is_alive():
            return self.root.after(400, self._espera)
        self.coletando = False
        self.recarrega("Atualizado")

    def resumir(self):
        """Botão [resumir] / [atualizar]: pede ao Claude o resumo do dia exibido."""
        dia = self.dia
        self._inicia_resumo("Resumindo o dia com o Claude… pode levar alguns instantes", lambda: resumir.resumir(dia),
                            "Resumo gravado")

    def resumir_semana(self):
        """Botão do calendário: resume os dias da semana que precisam e abre o relatório de horas no Bloco de Notas."""
        de, ate = tbase.semana_do_dia(self.dia)
        self._inicia_resumo(f"Resumindo a semana de {de:%d/%m} a {ate:%d/%m}… pode levar alguns minutos",
                            lambda: resumir.resumir_semana(de, ate), "Relatório da semana aberto no Bloco de Notas")

    def _inicia_resumo(self, msg, trabalho, msg_ok):
        """Roda `trabalho` (que chama o Claude e leva alguns instantes) numa thread. Se ele devolver um arquivo, abre-o."""
        if self.coletando or self.resumindo:
            return
        self.resumindo = True
        self._erro_resumo = self._arquivo_resumo = None
        self._msg_ok = msg_ok
        self.mensagem(msg, "info")

        def rodar():
            try:
                self._arquivo_resumo = trabalho()
            except resumir.ErroResumo as e:
                self._erro_resumo = str(e)
            except Exception as e:  # nada pode escapar da thread: o botão ficaria preso em "resumindo…"
                self._erro_resumo = f"{type(e).__name__}: {e}"

        self._th_resumo = threading.Thread(target=rodar, daemon=True)
        self._th_resumo.start()
        self.root.after(400, self._espera_resumo)

    def _espera_resumo(self):
        if self._th_resumo.is_alive():
            return self.root.after(400, self._espera_resumo)
        self.resumindo = False
        if self._arquivo_resumo:
            subprocess.Popen(["notepad.exe", str(self._arquivo_resumo)])
        if self._erro_resumo:
            self.recarrega(f"Resumo falhou: {self._erro_resumo}", "erro")
        else:
            self.recarrega(self._msg_ok)

    def relatorio(self):
        pasta = config.SAIDA_MD / f"{self.dia:%Y-%m}"
        pasta.mkdir(parents=True, exist_ok=True)
        arq = pasta / f"{self.dia.isoformat()}_relatorio.txt"
        arq.write_text(exporta.dia_txt(self.con, self.dia.isoformat()), encoding="utf-8-sig")
        subprocess.Popen(["notepad.exe", str(arq)])
        self.recarrega("Relatório aberto no Bloco de Notas")

    # --- temas ---
    def aplicar_tema(self, tema_id):
        if tema_id == self.tema.id:
            return
        self.tema = temas.obter(tema_id)
        self._ajusta_tema()
        preferencias.salvar(tema=self.tema.id)
        self.t = 0
        self._t0 = time.monotonic()
        self.efeitos = {}
        if self._anim_id:
            self.root.after_cancel(self._anim_id)
        self._anim_id = None
        self.hover = ""
        self.redesenha()
        self._cabe_na_tela()
        self._modo_janela()
        for d in list(self.dialogos):
            d.desenha()
        self._anima()

    def _miniaturas(self):
        if self._minis is None:
            self._minis = {i: t.miniatura(160) for i, t in temas.TEMAS.items()}
        return self._minis

    def configuracoes(self):
        for d in self.dialogos:
            if d.__dict__.get("tipo") == "config":
                return d.fecha()
        self._fecha_dialogos("calendario")

        def quadro(hover):
            e = self.estado(barra=self._itens_barra())
            e.hover = hover
            return self.tema.configuracoes(e, self._miniaturas())

        def clique(nome):
            if nome == "cfg_fechar":
                d.fecha()
            elif nome.startswith("tema:"):
                self.aplicar_tema(nome.split(":", 1)[1])
            elif nome.startswith("barra:"):
                self._clique_barra(*nome.split(":")[1:])
                d.desenha()

        self._barra_cfg = None  # relê o settings.json do TranslucentTB, que pode ter mudado por fora
        d = Dialogo(self, quadro, clique)
        d.tipo = "config"
        self.dialogos.append(d)

    # --- barra de tarefas (TranslucentTB) ---
    def _itens_barra(self):
        """Itens da coluna "Barra de tarefas" das configurações, no formato de `Estado.barra`."""
        itens = [("titulo", "", "Barra de tarefas", None, True)]
        if not barra.instalado():
            return itens + [("texto", "", "Precisa do TranslucentTB, da Microsoft Store", None, True)]
        if self._barra_cfg is None:
            try:
                self._barra_cfg = barra.ler()
            except barra.Indisponivel as erro:
                return itens + [("texto", "", str(erro), None, True)]
        c, sel, nomes = self._barra_cfg, self._barra_sel, dict(barra.APARENCIAS)
        for k, nome in barra.ESTADOS:
            vale = k == barra.ESTADOS[0][0] or c[k].get("enabled")
            itens.append(("estado", f"barra:estado:{k}", nome, nomes.get(c[k].get("accent"), "?") if vale else "desligada",
                          k == sel))
        ap = c[sel]
        itens.append(("sub", "", dict(barra.ESTADOS)[sel], None, True))
        if sel != barra.ESTADOS[0][0]:
            itens.append(("marca", "barra:ativa", "Usar esta aparência", bool(ap.get("enabled")), True))
        itens += [("opcao", f"barra:aparencia:{v}", rotulo, ap.get("accent") == v, True) for v, rotulo in barra.APARENCIAS]
        rgb, alfa = barra.cor(ap)
        com_cor = ap.get("accent") != "normal"  # a aparência normal ignora a cor
        itens.append(("sub", "", "Cor", None, com_cor))
        itens.append(("cores", "", "", [(f"barra:cor:{h}", h, h == rgb) for h in barra.CORES], com_cor))
        itens.append(("alfas", "", "", [(f"barra:alfa:{a}", f"{round(a * 100 / 255)}%", a == alfa) for a in barra.ALFAS],
                      com_cor))
        itens.append(("passo", "barra:raio", "Raio do desfoque", f"{ap.get('blur_radius', 9):g}", ap.get("accent") == "blur"))
        itens.append(("marca", "barra:peek", "Botão Mostrar área de trabalho", bool(ap.get("show_peek")), True))
        itens.append(("marca", "barra:linha", "Borda da barra", bool(ap.get("show_line")), True))
        itens.append(("espaco", "", "", None, True))
        itens.append(("marca", "barra:bandeja", "Ícone do TranslucentTB", not c.get("hide_tray", False), True))
        return itens

    def _clique_barra(self, acao, valor=None):
        if acao == "estado":
            self._barra_sel = valor
        else:
            self._muda_barra(self._barra_sel, acao, valor)

    def _muda_barra(self, estado, acao, valor):
        try:
            pronto = barra.alterar(estado, acao, valor)
        except (barra.Indisponivel, OSError) as erro:
            return self.mensagem(f"Barra de tarefas: {erro}", "erro")
        if pronto:
            self._barra_cfg = None  # relê na próxima pintura
            return
        # primeira vez: a tela já mostra a mudança, que vai para o arquivo quando o TranslucentTB o criar
        barra.mudar(self._barra_cfg or barra.ler(), estado, acao, valor)
        if not self._barra_pendente:
            self.mensagem("Aceite a tela de boas-vindas do TranslucentTB para a barra de tarefas mudar", "info")
            self.root.after(2000, self._espera_barra)
        self._barra_pendente.append((estado, acao, valor))

    def _espera_barra(self):
        """Primeira vez: o TranslucentTB só cria o arquivo de configuração depois que a tela de boas-vindas é aceita."""
        if barra.CONFIG.exists():
            pendente, self._barra_pendente = self._barra_pendente, []
            for mudanca in pendente:
                self._muda_barra(*mudanca)
            self.mensagem("Barra de tarefas personalizada")
        elif not barra.rodando():
            self._barra_pendente, self._barra_cfg = [], None
            self.mensagem("O TranslucentTB fechou sem a tela de boas-vindas ser aceita", "erro")
        else:
            return self.root.after(2000, self._espera_barra)
        for d in self.dialogos:
            if d.__dict__.get("tipo") == "config":
                d.desenha()

    def _garante_barra(self):
        try:
            barra.garantir()
        except (barra.Indisponivel, OSError) as erro:
            self.mensagem(f"Barra de tarefas: {erro}", "erro")

    def calendario(self):
        for d in self.dialogos:
            if d.__dict__.get("tipo") == "calendario":
                return d.fecha()
        self._fecha_dialogos("config")
        self._cal_mes = date(self.dia.year, self.dia.month, 1)

        def quadro(hover):
            e = self.estado(cal_mes=self._cal_mes, cal_dias=self._dias_do_mes(self._cal_mes))
            e.hover = hover
            return self.tema.calendario(e)

        def clique(nome):
            if nome == "cal_fechar":
                d.fecha()
            elif nome == "cal_semana":
                d.fecha()
                self.resumir_semana()
            elif nome in ("cal_ant", "cal_prox"):
                self._mes_cal(-1 if nome == "cal_ant" else 1)
                d.desenha()
            elif nome.startswith("dia:"):
                d.fecha()
                self.dia = date.fromisoformat(nome[4:])
                self.segue_hoje = self.dia == date.today()
                self.recarrega()

        d = Dialogo(self, quadro, clique, fecha_ao_perder_foco=True)
        d.tipo = "calendario"
        self.dialogos.append(d)

    def _dias_do_mes(self, m):
        if (m.year, m.month) not in self._cal_dias:
            self._cal_dias[(m.year, m.month)] = dias_com_registro(self.con, m.year, m.month)
        return self._cal_dias[(m.year, m.month)]

    def _mes_cal(self, delta):
        ano, mes = self._cal_mes.year, self._cal_mes.month + delta
        ano, mes = ano + (mes - 1) // 12, (mes - 1) % 12 + 1
        novo = date(ano, mes, 1)
        if novo <= date.today().replace(day=1):  # não passa do mês corrente
            self._cal_mes = novo

    def _fecha_dialogos(self, tipo):
        for d in list(self.dialogos):
            if d.__dict__.get("tipo") == tipo:
                d.fecha()

    def dialogo_fechado(self, d):
        if d in self.dialogos:
            self.dialogos.remove(d)

    def _erro(self, *exc):  # sob pythonw o traceback iria para o vazio
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"=== {datetime.now():%Y-%m-%d %H:%M:%S} ===\n" + "".join(traceback.format_exception(*exc)) + "\n")
        except OSError:
            pass
        try:
            self.mensagem(f"Erro: {exc[1]} (veja widget.log)", "erro")
        except Exception:
            pass

    # --- janela ---
    def _ouve_bandeja(self):
        while not self.bandeja.comandos.empty():
            comando = self.bandeja.comandos.get()
            if comando == "mostrar":
                self.trazer_frente()
            elif comando == "fechar":
                return self.fechar()
        self.root.after(250, self._ouve_bandeja)

    def _ajusta_tema(self):
        """Tema de papel de parede cobre a tela toda: diz a ele o tamanho do monitor para escolher a ampliação."""
        self.papel = getattr(self.tema, "papel", False)
        if self.papel:
            self._tela = papel.tamanho_da_tela()
            self.tema.ajusta_tela(*self._tela)

    def _modo_janela(self):
        """Papel de parede: a janela vai para o canto 0,0, atrás de todas e sem ativação, e um vigia passa a conferir se
        algo a cobre. Ao sair dele, volta a ser a janela comum, na posição que o usuário deixou."""
        r = self.root
        if self.papel:
            r.geometry("+0+0")
            r.update()
            papel.ao_fundo(r)
            papel.economiza(True)
            self._no_fundo = True
            if self._vigia_id is None:
                self._vigia()
            return
        if self._vigia_id:
            r.after_cancel(self._vigia_id)
            self._vigia_id = None
        if self._no_fundo:
            self._no_fundo = False
            papel.economiza(False)
            papel.restaura(r)
            p = preferencias.ler()
            r.geometry(f"+{p.get('x', r.winfo_screenwidth() - 520)}+{p.get('y', 40)}")
            self._cabe_na_tela()
        if self.coberto:
            self.coberto = False
            self.redesenha()

    def _vigia(self):
        """Mantém a janela no fundo e vê se alguém a está vendo: coberta por outra janela, com a sessão bloqueada ou remota
        ou com o monitor apagado, a animação para de vez (ver `_anima`) e o relógio da cena para junto. Confere a cada
        0,4 s com a janela à mostra, para religar a animação logo, e a cada 1 s sem ninguém vendo."""
        self._vigia_id = None
        if not self.papel:
            return
        if papel.tamanho_da_tela() != self._tela:  # monitor ligado/desligado ou resolução trocada: refaz a cena no tamanho novo
            self._ajusta_tema()
            self.root.geometry("+0+0")  # o monitor principal pode ser outro, e a janela precisa cobrir o canto dele
            self.redesenha()
        if self._na_frente:
            # o campo fechou ou outra janela ficou por cima (passado 1,5 s do clique, para o ícone da bandeja e a barra de
            # tarefas, que ganham o foco no clique, não contarem): a cena volta ao fundo. Senão, reafirma que está à frente.
            if not self._digitando or (time.monotonic() > self._na_frente_ate and papel.coberto(self.root)):
                self._na_frente = False
            else:
                papel.traz(self.root)
        if not self._na_frente:
            papel.abaixa(self.root)
        c = papel.coberto(self.root) or papel.sessao_inativa() or bool(self.bandeja and self.bandeja.tela_apagada)
        if c != self.coberto:
            self.coberto = c
            if c:
                self._cobriu_em = time.monotonic()
            else:
                self._t0 += time.monotonic() - self._cobriu_em  # a cena continua de onde parou
                if self._anim_id is None:
                    self._anima()
        self._vigia_id = self.root.after(1000 if c else 400, self._vigia)

    def digitar(self):
        """Papel de parede: abre, em cima do campo de lançamento, uma janelinha só com o campo (a do papel de parede não
        ativa, então não receberia o teclado). Enter lança, Esc ou clicar fora fecha."""
        reg = next((x for x in self.sup.regioes if x.nome == "campo"), None)
        if reg is None or self._digitando:
            return
        x0, y0, x1, y1 = reg.caixa
        s = self.sup.estilo
        j = self._digitando = tk.Toplevel(self.root)
        j.overrideredirect(True)
        j.attributes("-topmost", True)
        j.geometry(f"{x1 - x0}x{y1 - y0}+{self.root.winfo_rootx() + x0}+{self.root.winfo_rooty() + y0}")
        campo = tk.Entry(j, relief="flat", bd=0, highlightthickness=0, bg=s["bg"], fg=s["fg"],
                         insertbackground=s["cursor"], font=s["fonte"])
        campo.pack(fill="both", expand=True)

        def fecha(_e=None):
            if self._digitando is j:
                self._digitando = None
                j.destroy()

        def lanca(_e=None):
            self.entrada.delete(0, "end")
            self.entrada.insert(0, campo.get())
            fecha()
            self.lancar()

        campo.bind("<Return>", lanca)
        campo.bind("<Escape>", fecha)
        j.bind("<FocusOut>", lambda _e: j.after(120, lambda: j.focus_displayof() is None and fecha()))  # só se o foco saiu do widget
        j.focus_force()
        campo.focus_set()

    def trazer_frente(self):
        if self.papel:  # a cena inteira vem à frente, com o campo de digitar por cima; o vigia a devolve ao fundo depois
            if self._na_frente and self._digitando:  # segundo clique no ícone: fecha o campo e devolve ao fundo
                self._digitando.destroy()
                self._digitando = None
                return
            self._na_frente, self._na_frente_ate = True, time.monotonic() + 1.5
            self.digitar()
            if self._digitando:  # o campo toma o primeiro plano; só assim o Windows deixa a cena passar à frente da janela ativa
                papel.toma_foco(self._digitando)
            papel.traz(self.root)
            return
        r = self.root
        r.deiconify()
        r.lift()
        r.attributes("-topmost", True)  # o Windows só deixa passar à frente de outras janelas assim
        r.after(300, lambda: r.attributes("-topmost", False))
        try:
            ctypes.windll.user32.SetForegroundWindow(ctypes.windll.user32.GetParent(r.winfo_id()) or r.winfo_id())
        except (AttributeError, OSError):
            pass
        self.entrada.focus_set()

    def _cabe_na_tela(self):
        """Temas de tamanhos diferentes podem empurrar a janela para fora da tela: traz de volta."""
        r = self.root
        r.update_idletasks()
        x = max(0, min(r.winfo_x(), r.winfo_screenwidth() - r.winfo_width()))
        y = max(0, min(r.winfo_y(), r.winfo_screenheight() - r.winfo_height()))
        r.geometry(f"+{x}+{y}")

    def _ini_arraste(self, e):
        self._fecha_dialogos("calendario")
        self._arrasto = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _arrasta(self, e):
        if self._arrasto:
            self.root.geometry(f"+{e.x_root - self._arrasto[0]}+{e.y_root - self._arrasto[1]}")

    def _fim_arraste(self):
        if self._arrasto:
            self._arrasto = None
            self._salva_pos()

    def _salva_pos(self):
        if not self.papel:  # a posição do papel de parede é sempre 0,0: não sobrescreve a da janela comum
            preferencias.salvar(x=self.root.winfo_x(), y=self.root.winfo_y())

    def fechar(self):
        self._salva_pos()
        if self.bandeja:
            self.bandeja.remover()
        self.root.destroy()


def _ja_aberto():
    """Trava de instância única: devolve (True, _) se já há um widget rodando, e nesse caso o pede para vir à frente."""
    try:
        import win32api
        import win32con
        import win32event
        import win32gui
        import winerror
        from . import bandeja
    except ImportError:  # sem pywin32 não há como travar
        return False, None
    mutex = win32event.CreateMutex(None, False, "Local\\DiarioAtividadesWidget")
    if win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS:
        return False, mutex  # quem segura o mutex é o dono da trava; ele precisa ficar vivo até o fim do processo
    hwnd = win32gui.FindWindow(bandeja.CLASSE, None)  # a mesma janela do ícone da bandeja recebe o "clique"
    if hwnd:
        win32gui.PostMessage(hwnd, bandeja.WM_BANDEJA, 0, win32con.WM_LBUTTONUP)
    return True, None


def abrir():
    aberto, _trava = (False, None) if preferencias.PREVIEW else _ja_aberto()  # a prévia (DIARIO_PREVIEW=1) ignora a trava
    if aberto:
        return
    try:  # nitidez em tela com escala acima de 100%
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        tbase.ESCALA = ctypes.windll.user32.GetDpiForSystem() / 96
    except (AttributeError, OSError):
        pass
    Widget().root.mainloop()
