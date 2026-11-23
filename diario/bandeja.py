"""Ícone do widget na área de notificação do Windows (pywin32). O clique chega ao Tk pela fila `comandos`."""
import ctypes
import queue
import threading
import uuid

import win32api
import win32con
import win32gui
from PIL import Image, ImageDraw

from . import config

ICONE = config.RAIZ / "diario.ico"
WM_BANDEJA = win32con.WM_USER + 20
CLASSE = "DiarioBandeja"
ID_FECHAR = 1
WM_POWERBROADCAST, PBT_POWERSETTINGCHANGE, DEVICE_NOTIFY_WINDOW_HANDLE = 0x218, 0x8013, 0  # o win32con não os traz
GUID_ESTADO_DA_TELA = "{6FE69556-704A-47A0-8F24-C28D936FDA47}"  # GUID_CONSOLE_DISPLAY_STATE: 0 apagada, 1 acesa, 2 escurecida


def _gerar_icone():
    """Três tópicos em azul sobre fundo escuro, o mesmo desenho da lista do widget."""
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, 248, 248), radius=48, fill=(30, 36, 48, 255), outline=(77, 163, 255, 255), width=14)
    for y in (72, 120, 168):
        d.ellipse((52, y, 76, y + 24), fill=(77, 163, 255, 255))
        d.rounded_rectangle((92, y + 4, 204, y + 20), radius=8, fill=(230, 233, 239, 255))
    img.save(ICONE, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (256, 256)])


class Bandeja:
    def __init__(self, dica):
        if not ICONE.exists():
            _gerar_icone()
        self.dica = dica
        self.comandos = queue.Queue()
        self.tela_apagada = False  # o papel de parede para de animar enquanto o monitor está apagado
        self.hwnd = None
        self._pronta = threading.Event()
        threading.Thread(target=self._rodar, daemon=True).start()
        self._pronta.wait(5)

    def _rodar(self):
        self._recriar = win32gui.RegisterWindowMessage("TaskbarCreated")  # o Explorer reiniciou: o ícone some e precisa voltar
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = CLASSE
        wc.lpfnWndProc = self._proc
        win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(wc.lpszClassName, "Diário", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
        self._adicionar()
        self._guid = ctypes.create_string_buffer(uuid.UUID(GUID_ESTADO_DA_TELA).bytes_le)  # precisa viver enquanto a janela
        registra = ctypes.windll.user32.RegisterPowerSettingNotification  # avisos do Windows sobre o monitor
        registra.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        registra.restype = ctypes.c_void_p
        registra(self.hwnd, self._guid, DEVICE_NOTIFY_WINDOW_HANDLE)  # sem isso o widget só não sabe que a tela apagou
        self._pronta.set()
        win32gui.PumpMessages()

    def _adicionar(self):
        icone = win32gui.LoadImage(0, str(ICONE), win32con.IMAGE_ICON, 0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE)
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, (self.hwnd, 0, win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                                                      WM_BANDEJA, icone, self.dica))

    def _proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_BANDEJA and lparam in (win32con.WM_LBUTTONUP, win32con.WM_LBUTTONDBLCLK):
            self.comandos.put("mostrar")
        elif msg == WM_BANDEJA and lparam == win32con.WM_RBUTTONUP:
            self._menu(hwnd)
        elif msg == WM_POWERBROADCAST and wparam == PBT_POWERSETTINGCHANGE:
            self.tela_apagada = self.estado_da_tela(lparam) == 0
        elif msg == self._recriar:
            self._adicionar()
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _menu(self, hwnd):
        """Menu do botão direito no ícone: só a opção Fechar, que chega ao Tk como o comando "fechar"."""
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_FECHAR, "Fechar")
        x, y = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(hwnd)  # sem isso o menu não fecha ao clicar fora dele
        escolha = win32gui.TrackPopupMenu(menu, win32con.TPM_RETURNCMD | win32con.TPM_RIGHTBUTTON, x, y, 0, hwnd, None)
        win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)
        if escolha == ID_FECHAR:
            self.comandos.put("fechar")

    @staticmethod
    def estado_da_tela(lparam):
        """O dado de um POWERBROADCAST_SETTING (GUID de 16 bytes, tamanho de 4, depois o dado): 0 apagada, 1 acesa, 2 escurecida."""
        return int.from_bytes(ctypes.string_at(lparam + 20, 4), "little")

    def remover(self):
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 0))
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
        except win32gui.error:
            pass
