"""Configuração central do registo de eventos (logs).

Um só sítio decide para onde vão os logs, em que formato e por
quanto tempo ficam guardados. Os dois pontos de entrada
(`main.py` e `main_gui.py`) chamam `configurar()` logo a seguir ao
`config.garantir_diretorios()` — antes disso a pasta pode ainda não
existir.

Os módulos de negócio NÃO configuram nada: cada um só faz

    logger = logging.getLogger(__name__)

e escreve. É esta separação que permite mudar o formato ou o prazo
de retenção sem tocar em mais nenhum ficheiro.

PORQUE ESTE NOME: um ficheiro chamado `logging.py` dentro de `src/`
taparia o módulo `logging` do Python — e todos os `import logging`
do sistema passavam a importar este ficheiro em vez da biblioteca.

REGRAS DE CONTEÚDO (valem para todo o sistema, não só aqui):
nunca registar passwords, hashes, usernames tentados nem dados
pessoais de clientes ou colaboradores (nomes, NIF, documentos).
Regista-se o ID, nunca o dado. O ficheiro de log não pode passar a
ser, ele próprio, um repositório de dados pessoais.
"""

import logging
import logging.handlers
import sys

import config

NOME_FICHEIRO = "hostel.log"

# Um ficheiro por dia, guardado 90 dias. Mais do que os 30 dos
# backups: um log pesa pouco, e um problema de stock ou de acesso
# pode só ser notado semanas depois.
DIAS_RETENCAO = 90

FORMATO = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"

# Bibliotecas de terceiros que, em INFO, escreveriam linhas que não
# interessam ao diagnóstico do sistema. Só os avisos e erros delas
# chegam ao ficheiro.
_BIBLIOTECAS_SILENCIADAS = ("mysql.connector", "matplotlib", "PIL")

_configurado = False

logger = logging.getLogger(__name__)


def configurar(interface):
    """Liga o registo ao ficheiro diário em `config.DIR_LOGS`.

    `interface` é "gui" ou "cli" — só serve para a linha de arranque
    dizer de onde veio.

    Chamar duas vezes não faz nada da segunda: sem esta proteção, o
    mesmo evento ficava escrito duas vezes no ficheiro (um handler
    por cada chamada).

    Devolve o caminho do ficheiro de log.
    """
    global _configurado

    caminho = config.DIR_LOGS / NOME_FICHEIRO

    if _configurado:
        return caminho

    handler = logging.handlers.TimedRotatingFileHandler(
        caminho,
        when="midnight",
        backupCount=DIAS_RETENCAO,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(FORMATO, FORMATO_DATA))

    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(handler)

    for nome in _BIBLIOTECAS_SILENCIADAS:
        logging.getLogger(nome).setLevel(logging.WARNING)

    sys.excepthook = _registar_excecao_nao_tratada

    _configurado = True

    logger.info(
        "Aplicação iniciada — versão=%s, interface=%s",
        config.VERSAO,
        interface,
    )

    return caminho


def _registar_excecao_nao_tratada(tipo, valor, rasto):
    """Regista um crash antes de a aplicação morrer.

    Sem isto, uma exceção que chegue ao topo sem ninguém a apanhar
    fecha a aplicação sem deixar rasto no ficheiro.

    Depois de registar, entrega ao comportamento normal do Python
    (`sys.__excepthook__`), que continua a mostrar o erro no
    terminal como sempre.

    Um Ctrl+C no terminal (`KeyboardInterrupt`) não é um crash — não
    fica registado como tal.

    NOTA: erros dentro de botões e eventos do Tkinter NÃO passam por
    aqui — o Tkinter apanha-os primeiro, no
    `report_callback_exception`. Esses tratam-se no `app.py`.
    """
    if not issubclass(tipo, KeyboardInterrupt):
        logger.critical(
            "Exceção não tratada — a aplicação vai terminar",
            exc_info=(tipo, valor, rasto),
        )

    sys.__excepthook__(tipo, valor, rasto)