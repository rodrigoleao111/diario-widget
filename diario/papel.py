"""Janela de papel de parede: cobre o monitor principal, fica atrás de todas as outras, não aparece na barra de tarefas nem
no Alt+Tab, não rouba o foco ao ser clicada e sabe dizer quando ninguém a vê: outra janela a cobre por inteiro, a sessão está
bloqueada ou é remota (aí o widget para de animar). Também põe o processo em prioridade baixa e em modo de economia de energia.

O clique chega ao Tk normalmente (o mouse vai para a janela que está sob o cursor, ativa ou não); o que a janela sem
ativação não recebe é o teclado, por isso o campo de lançamento do tema abre uma janela de digitação à parte.
Os ícones da área de trabalho ficam cobertos: o Windows os desenha numa camada abaixo das janelas comuns.
"""
import ctypes
import os
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wintypes.UINT]
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.CloseDesktop.argtypes = [wintypes.HANDLE]
kernel32 = ctypes.windll.kernel32
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]

GWL_EXSTYLE, GA_ROOT = -20, 2
WS_EX_TOOLWINDOW, WS_EX_APPWINDOW, WS_EX_NOACTIVATE = 0x80, 0x40000, 0x08000000
HWND_BOTTOM, HWND_TOP = 1, 0
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x1, 0x2, 0x10, 0x20
SW_SHOWNOACTIVATE = 4
DESKTOP_SWITCHDESKTOP, SM_REMOTESESSION = 0x100, 0x1000
SM_CXSCREEN, SM_CYSCREEN = 0, 1
BELOW_NORMAL_PRIORITY_CLASS, NORMAL_PRIORITY_CLASS = 0x4000, 0x20
PROCESS_POWER_THROTTLING, THROTTLING_EXECUTION_SPEED = 4, 1  # ProcessPowerThrottling e o bit de "velocidade de execução"
# onde olhar para saber se a janela está à mostra: colunas e linhas, em fração do tamanho da janela
_COLUNAS, _LINHAS = (.08, .35, .65, .92), (.1, .4, .7, .95)


def tamanho_da_tela():
    """Tamanho do monitor principal, lido na hora do Windows: muda quando um monitor é ligado ou desligado."""
    return user32.GetSystemMetrics(SM_CXSCREEN), user32.GetSystemMetrics(SM_CYSCREEN)


def janela(root):
    """O handle da janela de nível mais alto do Tk (o `winfo_id` é o de uma filha)."""
    return user32.GetAncestor(root.winfo_id(), GA_ROOT)


def _estilo(h, poe, tira):
    ex = user32.GetWindowLongPtrW(h, GWL_EXSTYLE)
    user32.SetWindowLongPtrW(h, GWL_EXSTYLE, (ex | poe) & ~tira)


def ao_fundo(root):
    """Torna a janela uma janela de fundo: some da barra de tarefas e do Alt+Tab, não é ativada pelo clique e vai para
    trás de todas. Uma vez só, na hora de entrar no modo; depois, `abaixa` a mantém lá."""
    h = janela(root)
    _estilo(h, WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE, WS_EX_APPWINDOW)
    user32.SetWindowPos(h, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED)


def abaixa(root):
    """Garante que a janela continua atrás de todas e à mostra: já no fundo, não faz nada (sem piscar)."""
    h = janela(root)
    if not user32.IsWindowVisible(h) or user32.IsIconic(h):  # Win+D ou "mostrar a área de trabalho" a esconderam
        user32.ShowWindow(h, SW_SHOWNOACTIVATE)
    user32.SetWindowPos(h, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def traz(root):
    """Põe a janela à frente das outras janelas comuns, sem ativá-la e sem torná-la "sempre no topo": a barra de tarefas
    continua por cima e qualquer janela ativada depois passa à frente dela. `abaixa` a devolve ao fundo."""
    h = janela(root)
    if not user32.IsWindowVisible(h) or user32.IsIconic(h):
        user32.ShowWindow(h, SW_SHOWNOACTIVATE)
    user32.SetWindowPos(h, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def toma_foco(top):
    """Torna `top` a janela em primeiro plano. O Windows só deixa uma janela passar à frente da ativa se o processo dela
    estiver em primeiro plano, e o clique no ícone da bandeja deixa o foco na barra de tarefas: liga a fila de entrada à
    da janela ativa por um instante, o truque padrão para o `SetForegroundWindow` valer."""
    h = janela(top)
    ativa = user32.GetForegroundWindow()
    outra = user32.GetWindowThreadProcessId(ativa, None) if ativa else 0
    minha = kernel32.GetCurrentThreadId()
    ligou = bool(outra) and outra != minha and user32.AttachThreadInput(minha, outra, True)
    try:
        user32.BringWindowToTop(h)
        user32.SetForegroundWindow(h)
    finally:
        if ligou:
            user32.AttachThreadInput(minha, outra, False)


def restaura(root):
    """Volta a ser uma janela comum (o tema deixou de ser de papel de parede)."""
    h = janela(root)
    _estilo(h, 0, WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
    user32.SetWindowPos(h, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED)


class _Throttling(ctypes.Structure):  # PROCESS_POWER_THROTTLING_STATE
    _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]


def economiza(ligado):
    """Prioridade abaixo do normal e modo de economia de energia (EcoQoS): no Windows 11 o processo passa a rodar nos
    núcleos eficientes, em frequência baixa, e nunca disputa CPU com o que o usuário está usando. `False` devolve ao padrão.
    Processos que o widget abre (Bloco de Notas, Claude do resumo) herdam a prioridade."""
    h = kernel32.GetCurrentProcess()
    kernel32.SetPriorityClass(h, BELOW_NORMAL_PRIORITY_CLASS if ligado else NORMAL_PRIORITY_CLASS)
    estado = _Throttling(1, THROTTLING_EXECUTION_SPEED if ligado else 0, THROTTLING_EXECUTION_SPEED if ligado else 0)
    kernel32.SetProcessInformation(h, PROCESS_POWER_THROTTLING, ctypes.byref(estado), ctypes.sizeof(estado))


def sessao_inativa():
    """True se ninguém está olhando a tela deste computador: sessão bloqueada (a área de trabalho que recebe a entrada
    deixa de ser a nossa) ou sessão remota (o papel de parede ficaria parado para quem vê pelo acesso remoto, e não
    vale gastar a rede e a CPU animando)."""
    desk = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if not desk:
        return True
    user32.CloseDesktop(desk)
    return bool(user32.GetSystemMetrics(SM_REMOTESESSION))


def _do_processo(h):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value == os.getpid()


def coberto(root):
    """True se nenhum dos pontos amostrados da janela mostra uma janela deste processo: outra janela (maximizada, em tela
    cheia ou várias juntas) a esconde por inteiro. Janelas do próprio widget (calendário, balão) contam como à mostra."""
    h = janela(root)
    r = wintypes.RECT()
    user32.GetWindowRect(h, ctypes.byref(r))
    w, a = r.right - r.left, r.bottom - r.top
    for fy in _LINHAS:
        for fx in _COLUNAS:
            alvo = user32.WindowFromPoint(wintypes.POINT(int(r.left + w * fx), int(r.top + a * fy)))
            if alvo and _do_processo(alvo):
                return False
    return True
