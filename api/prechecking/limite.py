"""Limite de pedidos por IP (janela deslizante, em memória).

Cada IP tem uma fila com as horas dos seus pedidos recentes. Antes de
aceitar um pedido, tiram-se da fila os que já saíram da janela; se
ainda restarem `maximo`, o pedido é recusado (HTTP 429).

Em memória chega: a API corre num só processo e, se reiniciar, os
contadores voltarem a zero não é um problema de segurança.
"""

import threading
import time
from collections import OrderedDict, deque
from typing import Callable


class LimitadorPedidos:
    """Janela deslizante: no máximo `maximo` pedidos em `janela` s."""

    def __init__(self, maximo: int, janela: float, maximo_ips: int,
                 relogio: Callable[[], float] = time.monotonic):
        self._maximo = maximo
        self._janela = janela
        self._maximo_ips = maximo_ips
        self._relogio = relogio          # trocável nos testes
        self._pedidos: "OrderedDict[str, deque]" = OrderedDict()
        self._tranca = threading.Lock()

    def permitir(self, ip: str) -> bool:
        """Regista o pedido e diz se está dentro do limite."""
        agora = self._relogio()
        with self._tranca:
            fila = self._pedidos.pop(ip, None) or deque()
            while fila and agora - fila[0] >= self._janela:
                fila.popleft()
            permitido = len(fila) < self._maximo
            if permitido:
                fila.append(agora)
            # Volta para o fim (o mais recente) e, se houver IPs a
            # mais, esquece o que está parado há mais tempo.
            self._pedidos[ip] = fila
            while len(self._pedidos) > self._maximo_ips:
                self._pedidos.popitem(last=False)
            return permitido
