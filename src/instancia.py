"""Uma só cópia da aplicação aberta de cada vez (v1.8.1).

PORQUÊ: no teste de instalação de 02/10/2026 o 1.º arranque demorou
~25 s sem mostrar nada (cópia de segurança do dia) e foi dado um
segundo duplo clique. As duas cópias aplicaram as migrações ao mesmo
tempo ("Duplicate entry") e, quando uma fechou, levou consigo o túnel
SSH que a outra estava a usar — o login seguinte deu "erro
inesperado". A aplicação passa a recusar a segunda cópia.

COMO: um "trinco" com nome, pedido logo no arranque do main_gui e
largado sozinho quando o processo termina (mesmo se rebentar):
- Windows: um mutex com nome do sistema operativo
  (CreateMutexW + WaitForSingleObject), no espaço "Local\\" — cada
  sessão do Windows tem o seu, por isso dois utilizadores do mesmo PC
  não se bloqueiam.
- Outros sistemas (só para os testes correrem em Linux): flock num
  ficheiro na pasta temporária.

REINÍCIO: ao mudar de servidor, a aplicação lança uma cópia nova e só
depois fecha (`servidores.reiniciar_aplicacao`). Essa cópia nova
recebe a variável de ambiente HOSTEL_REINICIO e espera até
ESPERA_REINICIO_S segundos que a antiga largue o trinco, em vez de se
recusar logo.

Este módulo não importa nada do projeto (é usado pelo main_gui e pelo
servidores, antes de haver config ou base de dados).
"""

import logging
import os
import sys
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

NOME = "HostelGestao_instancia"
VARIAVEL_REINICIO = "HOSTEL_REINICIO"
ESPERA_REINICIO_S = 15

_WAIT_OBJECT_0 = 0x00
_WAIT_ABANDONED = 0x80  # a cópia anterior terminou sem largar: é nosso

_trinco = None  # o trinco desta cópia, enquanto o tiver


def espera_pedida():
    """Segundos a esperar pelo trinco neste arranque.

    0 num arranque normal (outra cópia aberta = recusa já). Num
    reinício pedido pela própria aplicação, ESPERA_REINICIO_S. A
    variável é retirada do ambiente: um reinício seguinte volta a
    pô-la explicitamente.
    """
    if os.environ.pop(VARIAVEL_REINICIO, None):
        return ESPERA_REINICIO_S
    return 0


def adquirir(espera_s=0, nome=NOME):
    """Tenta ficar com o trinco. True se esta é a única cópia.

    Espera até `espera_s` segundos se outra cópia o tiver. Pedir de
    novo quando já se tem devolve True. Se o sistema operativo falhar
    a criar o trinco, deixa abrir (regista no log): mais vale abrir
    sem esta proteção do que não abrir de todo.
    """
    global _trinco
    if _trinco is not None:
        return True
    try:
        trinco = _adquirir_no_sistema(espera_s, nome)
    except OSError as erro:
        logger.error("Não consegui criar o trinco de cópia única: %s",
                     erro)
        return True
    if trinco is None:
        return False
    _trinco = trinco
    return True


def libertar():
    """Larga o trinco (antes de um reinício). Sem trinco, não faz
    nada."""
    global _trinco
    if _trinco is None:
        return
    _, recurso = _trinco
    _trinco = None
    _largar(recurso)


# Início dos títulos das janelas da aplicação: a janela de arranque
# ("Hostel Gestão — a iniciar") e as da `Aplicacao` ("Hostel Clean
# v… — Entrar", "… — Gestão de Alojamento").
PREFIXOS_JANELA = ("Hostel Gestão", "Hostel Clean")


def trazer_para_frente(prefixos=PREFIXOS_JANELA):
    """Traz para a frente a janela da cópia que já está aberta (v1.10.0).

    Chamado pela segunda cópia, depois do aviso "já está a abrir",
    para a pessoa ver onde está a aplicação em vez de clicar outra
    vez. Procura a primeira janela visível cujo título comece por um
    dos `prefixos`. Devolve True se encontrou. Fora do Windows não faz
    nada (só serve para os testes correrem em Linux). Uma falha do
    sistema fica no log e não impede nada.
    """
    try:
        return _trazer_no_sistema(tuple(prefixos))
    except OSError as erro:
        logger.warning("Não consegui trazer a janela para a frente: %s",
                       erro)
        return False


# ---------------------------------------------------------------------
# Implementação por sistema operativo. O `if` fica ao nível do módulo
# para o pyright só analisar o ramo do sistema onde corre (ctypes.WinDLL
# não existe em Linux; fcntl não existe em Windows).
# ---------------------------------------------------------------------

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    def _kernel32():
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [
            wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [
            wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        return kernel32

    def _adquirir_no_sistema(espera_s, nome):
        """Mutex com nome, no espaço "Local\\" da sessão."""
        kernel32 = _kernel32()
        mutex = kernel32.CreateMutexW(None, False, "Local\\" + nome)
        if not mutex:
            raise OSError(ctypes.get_last_error(), "CreateMutexW falhou")
        resultado = kernel32.WaitForSingleObject(
            mutex, int(espera_s * 1000))
        if resultado in (_WAIT_OBJECT_0, _WAIT_ABANDONED):
            return ("windows", mutex)
        kernel32.CloseHandle(mutex)
        return None

    def _largar(mutex):
        kernel32 = _kernel32()
        kernel32.ReleaseMutex(mutex)
        kernel32.CloseHandle(mutex)

    _SW_RESTORE = 9

    def _trazer_no_sistema(prefixos):
        """EnumWindows: a primeira janela visível com o título certo
        é restaurada (se estiver minimizada) e posta à frente."""
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        procurar = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        encontrada = []

        def verificar(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            tamanho = user32.GetWindowTextLengthW(hwnd)
            if tamanho == 0:
                return True
            titulo = ctypes.create_unicode_buffer(tamanho + 1)
            user32.GetWindowTextW(hwnd, titulo, tamanho + 1)
            if titulo.value.startswith(prefixos):
                encontrada.append(hwnd)
                return False  # para a procura
            return True

        user32.EnumWindows(procurar(verificar), 0)
        if not encontrada:
            return False
        if user32.IsIconic(encontrada[0]):
            user32.ShowWindow(encontrada[0], _SW_RESTORE)
        user32.SetForegroundWindow(encontrada[0])
        return True

else:
    import fcntl

    def _adquirir_no_sistema(espera_s, nome):
        """flock num ficheiro da pasta temporária."""
        caminho = Path(tempfile.gettempdir()) / f"{nome}.lock"
        ficheiro = open(caminho, "w")
        limite = time.monotonic() + espera_s
        while True:
            try:
                fcntl.flock(ficheiro, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return ("ficheiro", ficheiro)
            except BlockingIOError:
                if time.monotonic() >= limite:
                    ficheiro.close()
                    return None
                time.sleep(0.2)

    def _largar(ficheiro):
        fcntl.flock(ficheiro, fcntl.LOCK_UN)
        ficheiro.close()

    def _trazer_no_sistema(prefixos):
        """Fora do Windows não há nada a trazer."""
        return False
