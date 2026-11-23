"""Aparência da barra de tarefas do Windows, pelo TranslucentTB (versão da Microsoft Store).

No Windows 11 22H2 em diante a barra é desenhada em XAML dentro do explorer.exe e não obedece mais ao
SetWindowCompositionAttribute, que deixava a barra transparente no Windows 10. O TranslucentTB resolve por dentro do
explorer; o diário só lê e grava o settings.json dele, que ele vigia e recarrega sozinho, e o abre quando não está rodando.
A fonte da verdade é esse arquivo: o diário não guarda cópia das opções.

Na primeira execução o TranslucentTB mostra uma tela de boas-vindas com a licença e só cria o settings.json depois que ela é
aceita. Enquanto o arquivo não existe, `alterar` abre o TranslucentTB e devolve False, e quem chamou repete a mudança depois.
"""
import copy
import json
import os
import subprocess
from pathlib import Path

PACOTE = "28017CharlesMilette.TranslucentTB_v826wp6bftszj"
_LOCAL = Path(os.environ.get("LOCALAPPDATA", ""))
EXE = _LOCAL / "Microsoft" / "WindowsApps" / PACOTE / "ttb.exe"  # atalho de execução do pacote da Store
CONFIG = _LOCAL / "Packages" / PACOTE / "RoamingState" / "settings.json"
PROCESSO = "TranslucentTB.exe"
_SEM_JANELA, _DESLIGADO = 0x08000000, 0x00000008  # CREATE_NO_WINDOW, DETACHED_PROCESS

# os estados da barra, na ordem do menu do TranslucentTB; o primeiro vale sempre, os outros só com "enabled"
ESTADOS = [("desktop_appearance", "Área de trabalho"), ("visible_window_appearance", "Janela visível"),
           ("maximized_window_appearance", "Janela maximizada"), ("start_opened_appearance", "Iniciar aberto"),
           ("search_opened_appearance", "Pesquisa aberta"), ("task_view_opened_appearance", "Visão de tarefas aberta"),
           ("battery_saver_appearance", "Economia de bateria")]
APARENCIAS = [("normal", "Normal"), ("opaque", "Opaca"), ("clear", "Transparente"), ("blur", "Desfoque"),
              ("acrylic", "Acrílico")]
CORES = ["000000", "ffffff", "0063b1", "107c10", "c42b1c", "744da9", "ca5010", "e3008c"]  # atalhos de cor (RRGGBB)
ALFAS = [0x00, 0x40, 0x80, 0xbf, 0xff]  # opacidade da cor: 0%, 25%, 50%, 75%, 100%
RAIOS = [0, 2, 4, 6, 9, 12, 16, 20, 30, 50]  # passos do raio do desfoque (o TranslucentTB aceita de 0 a 750)


def _aparencia(ativa, accent, peek, linha):
    return {"enabled": ativa, "accent": accent, "color": "#00000000", "show_peek": peek, "show_line": linha, "blur_radius": 9.0}


# o que o TranslucentTB grava na primeira vez no Windows 11; vale enquanto o arquivo não existe e para chaves que faltem
PADRAO = {
    "desktop_appearance": {"accent": "clear", "color": "#00000000", "show_peek": False, "show_line": False, "blur_radius": 9.0},
    "visible_window_appearance": _aparencia(False, "clear", True, False),
    "maximized_window_appearance": _aparencia(False, "acrylic", True, True),
    "start_opened_appearance": _aparencia(False, "normal", True, True),
    "search_opened_appearance": _aparencia(False, "normal", True, True),
    "task_view_opened_appearance": _aparencia(True, "normal", False, True),
    "battery_saver_appearance": _aparencia(False, "opaque", True, False),
}


class Indisponivel(Exception):
    """O TranslucentTB não está instalado ou o settings.json dele não pôde ser lido ou gravado."""


def instalado():
    return EXE.exists()


def rodando():
    # em bytes: sem o processo, o tasklist responde com acentos no codepage do console, que não decodifica como UTF-8
    saida = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {PROCESSO}", "/FO", "CSV", "/NH"], capture_output=True,
                           creationflags=_SEM_JANELA).stdout
    return PROCESSO.lower().encode() in saida.lower()


def _abre():
    if not rodando():
        subprocess.Popen([str(EXE)], creationflags=_SEM_JANELA | _DESLIGADO)


def _le_arquivo():
    """(cabeçalho, dict) do settings.json. O TranslucentTB abre o arquivo com uma linha "// See https://..." (o leitor dele
    aceita comentários; o json, não): ela é separada para ser regravada igual."""
    try:
        texto = CONFIG.read_text(encoding="utf-8-sig")
        linhas = texto.splitlines(keepends=True)
        n = next((i for i, l in enumerate(linhas) if not l.lstrip().startswith("//")), len(linhas))
        return texto, "".join(linhas[:n]), json.loads("".join(linhas[n:]))
    except (OSError, ValueError) as erro:
        raise Indisponivel(f"settings.json do TranslucentTB ilegível: {erro}")


def _mescla(d):
    c = copy.deepcopy(PADRAO)
    for k, v in d.items():
        c[k] = {**c[k], **v} if isinstance(v, dict) and isinstance(c.get(k), dict) else v
    return c


def ler():
    """As opções em vigor: o settings.json sobre o PADRAO (só o PADRAO, se o arquivo ainda não existe)."""
    return _mescla(_le_arquivo()[2] if CONFIG.exists() else {})


def cor(ap):
    """(RRGGBB, alfa 0-255) da cor de uma aparência ("#RGB", "#RGBA", "#RRGGBB" ou "#RRGGBBAA")."""
    h = str(ap.get("color", "#00000000")).lstrip("#")
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    try:
        return h[:6].lower(), int(h[6:8], 16) if len(h) == 8 else 0xff
    except ValueError:
        return "000000", 0


def mudar(c, estado, acao, valor=None):
    """Aplica em `c` (o dict das opções) uma ação da tela de configurações sobre a aparência `estado`."""
    ap = c.setdefault(estado, {})
    rgb, alfa = cor(ap)
    if acao == "ativa":
        ap["enabled"] = not ap.get("enabled", False)
    elif acao == "aparencia":
        ap["accent"] = valor
    elif acao == "cor":
        ap["color"] = f"#{valor}{alfa:02x}"
    elif acao == "alfa":
        ap["color"] = f"#{rgb}{int(valor):02x}"
    elif acao == "raio":  # valor "-" ou "+": passo anterior ou seguinte de RAIOS
        r = ap.get("blur_radius", 9.0)
        menores, maiores = [x for x in RAIOS if x < r], [x for x in RAIOS if x > r]
        novo = (menores[-1] if menores else RAIOS[0]) if valor == "-" else (maiores[0] if maiores else RAIOS[-1])
        ap["blur_radius"] = float(novo)
    elif acao in ("peek", "linha"):
        chave = "show_peek" if acao == "peek" else "show_line"
        ap[chave] = not ap.get(chave, False)
    elif acao == "bandeja":
        c["hide_tray"] = not c.get("hide_tray", False)
    else:
        raise ValueError(acao)


def alterar(estado, acao, valor=None):
    """Grava uma mudança no settings.json e garante o TranslucentTB rodando. True: aplicada. False: o arquivo ainda não existe;
    o TranslucentTB foi aberto e espera a tela de boas-vindas ser aceita (repita a mudança depois)."""
    if not instalado():
        raise Indisponivel("TranslucentTB não está instalado (Microsoft Store)")
    if not CONFIG.exists():
        _abre()
        return False
    texto, cabecalho, d = _le_arquivo()
    c = _mescla(d)
    mudar(c, estado, acao, valor)
    d.update(c)  # sobre o dict lido, para manter a ordem das chaves do arquivo
    novo = cabecalho + json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    if novo != texto:  # cada gravação faz o TranslucentTB recarregar
        try:
            tmp = CONFIG.with_suffix(".tmp")
            tmp.write_text(novo, encoding="utf-8")
            os.replace(tmp, CONFIG)  # troca de uma vez: o TranslucentTB nunca lê o arquivo pela metade
        except OSError as erro:
            raise Indisponivel(f"não consegui gravar o settings.json do TranslucentTB: {erro}")
    _abre()
    return True


def precisa_rodar():
    """A barra tem alguma aparência diferente da normal (então o TranslucentTB precisa estar aberto para ela valer)."""
    if not (instalado() and CONFIG.exists()):
        return False
    c = ler()
    return any((k == ESTADOS[0][0] or c[k].get("enabled")) and c[k].get("accent") != "normal" for k, _ in ESTADOS)


def garantir():
    """Ao abrir o widget: se a barra está personalizada, abre o TranslucentTB caso ele não tenha iniciado com o Windows."""
    if precisa_rodar():
        _abre()
