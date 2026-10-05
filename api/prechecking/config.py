"""Configuração da API, lida das variáveis de ambiente.

Na VM, o serviço systemd carrega /opt/hostel/api.env (600, root),
que só tem o que a API precisa — NUNCA a password de root do MySQL.
Nenhuma password vive no código nem no Git.
"""

import os

# Única origem autorizada a chamar a API a partir de um browser.
ORIGEM_SITE = "https://mauriciopates.github.io"

# Limites de proteção.
TAMANHO_MAXIMO_CORPO = 8 * 1024      # bytes; um pré check-in tem ~1 KB
PEDIDOS_POR_JANELA = 10              # por IP...
JANELA_SEGUNDOS = 60                 # ...em cada minuto
MAXIMO_IPS_EM_MEMORIA = 10_000       # o limitador nunca cresce sem fim


def ligacao_mysql() -> dict:
    """Parâmetros de ligação ao MySQL (127.0.0.1:6213, só na VM).

    Raises:
        RuntimeError: se a password não estiver no ambiente.
    """
    password = os.environ.get("API_PRECHECKING_PASSWORD", "")
    if not password:
        raise RuntimeError("API_PRECHECKING_PASSWORD não definida.")
    return {
        "host": os.environ.get("API_DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("API_DB_PORTA", "6213")),
        "user": os.environ.get("API_DB_UTILIZADOR", "api_prechecking"),
        "password": password,
        "database": os.environ.get("API_DB_BASE", "hostel_prechecking"),
        "connection_timeout": 5,
        "autocommit": False,
    }
