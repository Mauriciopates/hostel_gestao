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
import tkinter

import config
import configuracoes
import migracoes
import registo_logs
import repositorio
import sistema
from gui import componentes, gui_servidores
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

    # SERVIDOR (26/09/2026): antes de tudo o resto, abre o túnel SSH da
    # VM (se o servidor ativo o usar) e confirma que o MySQL responde.
    # Se falhar, mostra o plano B (tentar de novo / outro servidor /
    # sair). Tem de ser antes do backup e do seed, que já usam a base.
    if not gui_servidores.garantir_ligacao():
        return

    repositorio.criar_backup()
    repositorio.limpar_backups_antigos()

    # MIGRAÇÕES (v1.8.0): depois do backup do dia (a cópia apanha a
    # base antes de qualquer mudança) e antes do seed e do login. Se
    # uma falhar, a aplicação não abre — abrir com a base a meio do
    # caminho seria pior (decisão 2 do passo C).
    if not _aplicar_migracoes():
        return

    configuracoes.garantir_seed()

    # INSTALAÇÃO (v1.8.0, INST-01): numa base sem nenhum responsável,
    # cria o Master de fábrica — sem isto, uma instalação nova não
    # deixava ninguém entrar. Numa base em uso não faz nada.
    if sistema.garantir_master_inicial() is not None:
        _avisar_master_criado()

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


def _avisar_master_criado():
    """Popup da primeira utilização, com as credenciais de fábrica.

    Ainda não há janela: raiz Tk escondida, como em _aplicar_migracoes.
    """
    raiz = tkinter.Tk()
    raiz.withdraw()
    componentes.mostrar_sucesso(
        f"Primeira utilização desta base de dados: foi criado o "
        f"utilizador Master.\n\n"
        f"Utilizador: {config.UTILIZADOR_PADRAO}\n"
        f"Password: {config.PASSWORD_PADRAO}\n\n"
        f"No primeiro acesso vai ser pedido que troque a password.",
        titulo="Instalação",
    )
    raiz.destroy()


def _aplicar_migracoes():
    """Aplica as migrações em falta. Devolve False se alguma falhou
    (depois de avisar o utilizador), True caso contrário.

    Ainda não existe nenhuma janela nesta altura: cria-se uma raiz
    Tk escondida só para o popup de erro não aparecer com uma janela
    vazia atrás.
    """
    try:
        migracoes.aplicar_pendentes()
    except ValueError as erro:
        raiz = tkinter.Tk()
        raiz.withdraw()
        componentes.mostrar_erro(
            f"{erro}\n\nA aplicação vai fechar. Os detalhes ficaram no "
            f"log e a cópia de segurança de hoje foi feita antes da "
            f"atualização.",
            titulo="Atualização da base de dados",
        )
        raiz.destroy()
        return False

    return True


if __name__ == "__main__":
    main()
