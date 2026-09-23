"""Ponto de entrada da interface gráfica.

Separado do `teste_gui.py` por uma questão simples: aquele é um
script de desenvolvimento, que pode ser apagado a qualquer momento
sem afetar o projeto. Este é o ficheiro oficial — quem corre a
aplicação a partir do executável, do atalho, ou com
`python src/main_gui.py`, é este que arranca.

A lógica toda vive no `app.py` (a classe `Aplicacao`); este
ficheiro é o casquilho que a instancia e arranca o loop de eventos
do Tkinter.

LOGOFF (v1.5.0, 17/09/2026): o `Aplicacao.trocar_utilizador` faz
logoff verdadeiro — marca `self.reabrir = True` e destrói a
janela. Este ficheiro deteta isso num `while` e cria uma nova
`Aplicacao`, que volta a pedir credenciais no `LoginModal`. Se
`self.reabrir` ficar False (o normal ao fechar a janela), o
`while` termina e a aplicação fecha de vez.
"""

import logging

import config
import configuracoes
import registo_logs
import repositorio
from gui.app import Aplicacao

logger = logging.getLogger(__name__)


def main():
    """Arranca a aplicação, com suporte a logoff.

    O `while` é o mecanismo do logoff: cada iteração cria uma
    `Aplicacao` nova, corre o `mainloop()`, e — quando este
    devolve — decide se deve continuar (porque o utilizador pediu
    para trocar) ou terminar.

    `config.garantir_diretorios()` corre uma só vez, antes do
    primeiro arranque. Não faz sentido repetir em cada reabertura
    (a árvore já existe), mas também não faz mal se acontecer.

    BACKUP DIÁRIO (23/09/2026): até esta data só o `main.py` (CLI)
    fazia o backup diário e a limpeza dos antigos — e a aplicação
    usada na operação é esta. Na prática, não havia backup diário
    nenhum. Mesma ordem do `main.py`: a cópia de hoje ANTES da
    limpeza, para um erro na limpeza nunca deixar um arranque sem
    cópia do dia; e antes do seed, para a cópia apanhar a base tal
    como estava.

    O `criar_backup()` decide sozinho se a cópia de hoje já existe —
    só o primeiro arranque do dia a faz (e só esse espera pelo
    `mysqldump`). Uma falha do `mysqldump` não impede o arranque:
    devolve None e fica registada no log pelo `repositorio`.
    """
    config.garantir_diretorios()
    registo_logs.configurar("gui")

    repositorio.criar_backup()
    repositorio.limpar_backups_antigos()

    configuracoes.garantir_seed()

    while True:
        app = Aplicacao()

        # Se o utilizador clicou "Sair" no LoginModal, a app já
        # foi destruída DENTRO do `__init__` — não há mainloop
        # para arrancar (rebentaria). Sai já.
        if app.terminar_pedido:
            break

        app.mainloop()

        # Se `reabrir` ficou False, o utilizador fechou a janela
        # normalmente. Termina.
        if not app.reabrir:
            break

        # Se chegou aqui, foi pedido logoff — o `while` recomeça
        # e cria uma nova `Aplicacao`.
        logger.info("Logoff — a reabrir a aplicação")
        del app

    logger.info("Aplicação terminada")


if __name__ == "__main__":
    main()
