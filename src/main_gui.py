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

JANELA DE ARRANQUE (v1.10.0, mockup aprovado a 05/10/2026): logo a
seguir ao trinco de cópia única aparece a `JanelaArranque`, com os
passos do arranque a ficarem feitos um a um. Antes, o arranque (túnel
SSH, cópia de segurança do dia) corria sem nada no ecrã e as pessoas
voltavam a clicar no ícone. Os passos lentos correm numa thread
(`JanelaArranque.correr`); os popups e a `Aplicacao` só aparecem
depois de a janela de arranque fechar — o CustomTkinter só aguenta
uma janela-raiz de cada vez.
"""

import logging
import sys
import tkinter

import config
import configuracoes
import desempenho
import instalacao
import instancia
import migracoes
import registo_logs
import repositorio
import servidores
import sistema
from gui import componentes, gui_servidores, janela_arranque
from gui.janela_arranque import JanelaArranque

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

    # MEDIÇÃO DE DESEMPENHO (v2.2.0): `HostelGestao.exe --desempenho`.
    # O cronómetro das consultas tem de entrar ANTES de qualquer
    # ligação à base (o pool guarda as que abrir). A medição em si só
    # começa depois do login, e só para um Master (gui_desempenho).
    modo_desempenho = desempenho.OPCAO_ARRANQUE in sys.argv[1:]
    if modo_desempenho:
        desempenho.instrumentar_mysql()
        logger.info("Arranque em modo de medição de desempenho")

    # CÓPIA ÚNICA (v1.8.1): antes de tudo o resto — de abrir o túnel e
    # de tocar na base. Uma segunda cópia avisa e fecha. Num reinício
    # pedido pela própria aplicação espera que a anterior feche.
    if not instancia.adquirir(instancia.espera_pedida()):
        logger.warning("Já há uma cópia da aplicação aberta — esta fecha")
        _avisar_ja_aberta()
        return

    # JANELA DE ARRANQUE (v1.10.0): aparece já, antes de qualquer
    # ligação. Importar os ecrãs (o passo "A preparar") fica DEPOIS de
    # ela estar no ecrã — é dos passos que mais demora a frio.
    janela = JanelaArranque()
    Aplicacao = janela.correr_aqui(janela_arranque.PREPARAR,
                                   _importar_aplicacao)

    # SERVIDOR (26/09/2026): antes de tudo o resto, abre o túnel SSH da
    # VM (se o servidor ativo o usar) e confirma que o MySQL responde.
    # Se falhar, mostra o plano B (tentar de novo / outro servidor /
    # sair). Tem de ser antes do backup e do seed, que já usam a base.
    janela = _ligar(janela)
    if janela is None:
        return

    janela.correr(janela_arranque.COPIA, _copia_do_dia)

    # MIGRAÇÕES (v1.8.0): depois do backup do dia (a cópia apanha a
    # base antes de qualquer mudança) e antes do seed e do login. Se
    # uma falhar, a aplicação não abre — abrir com a base a meio do
    # caminho seria pior (decisão 2 do passo C).
    try:
        janela.correr(janela_arranque.MIGRAR, migracoes.aplicar_pendentes)
    except ValueError as erro:
        janela.fechar()
        _avisar_migracao_falhou(erro)
        return

    # INSTALAÇÃO (v1.8.0, INST-01): numa base sem nenhum responsável,
    # cria o Master de fábrica — sem isto, uma instalação nova não
    # deixava ninguém entrar. Numa base em uso não faz nada.
    master_criado = janela.correr(janela_arranque.ABRIR, _preparar_login)
    janela.fechar()
    if master_criado:
        _avisar_master_criado()

    while True:
        app = Aplicacao()

        # Se o utilizador clicou "Sair" no LoginModal, a app já
        # foi destruída DENTRO do `__init__` — não há mainloop
        # para arrancar (rebentaria). Sai já.
        if app.terminar_pedido:
            break

        if modo_desempenho:
            # Só na primeira abertura (não depois de um logoff).
            modo_desempenho = False
            from gui import gui_desempenho

            app.after(500, lambda a=app: gui_desempenho.iniciar(a))

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


def _avisar_ja_aberta():
    """Popup da segunda cópia. Ainda não há janela: raiz Tk escondida,
    como em _avisar_migracao_falhou. Depois do OK, traz para a frente
    a janela da cópia que já está aberta (v1.10.0)."""
    raiz = tkinter.Tk()
    raiz.withdraw()
    componentes.mostrar_erro(
        "O Hostel Gestão já está a abrir neste computador.\n\n"
        "Ao carregar em OK, a janela vem para a frente. Aguarde, não é "
        "preciso clicar de novo: o primeiro arranque do dia faz a "
        "cópia de segurança e pode demorar até um minuto.",
        titulo="Hostel Gestão",
    )
    raiz.destroy()
    instancia.trazer_para_frente()


def _importar_aplicacao():
    """Passo "A preparar": carrega os ecrãs todos (gui.app importa-os).
    Fica fora do topo do ficheiro para correr com a janela de arranque
    já no ecrã."""
    from gui.app import Aplicacao
    return Aplicacao


def _ligar(janela):
    """Passo "A ligar ao servidor".

    Testa o servidor ativo numa thread, com a janela de arranque
    viva. Se a base está pronta, devolve a mesma janela. Se não (sem
    servidor, servidor em baixo, base por criar), fecha-a e entrega o
    resultado ao plano B do `gui_servidores` — que não volta a testar
    na primeira volta. Se o plano B resolver, devolve uma janela de
    arranque nova com os dois primeiros passos já feitos; se o
    arranque deve terminar, devolve None.
    """
    id_servidor, servidor = servidores.servidor_ativo()
    diagnostico = None

    if id_servidor is not None:
        password = servidores.obter_password(id_servidor)
        diagnostico = janela.correr(
            janela_arranque.LIGAR,
            lambda: instalacao.diagnosticar(servidor, password),
        )
        estado, texto, _ = diagnostico
        if estado == instalacao.PRONTA:
            logger.info("Servidor '%s': %s", id_servidor, texto)
            return janela

    janela.fechar()
    if not gui_servidores.garantir_ligacao(diagnostico):
        return None
    return JanelaArranque(ja_feitos=janela_arranque.COPIA)


def _copia_do_dia():
    """Passo "Cópia de segurança do dia".

    BACKUP DIÁRIO (23/09/2026): mesma ordem do `main.py`: a cópia de
    hoje ANTES da limpeza, para um erro na limpeza nunca deixar um
    arranque sem cópia do dia; e antes do seed, para a cópia apanhar a
    base tal como estava. O `criar_backup()` decide sozinho se a cópia
    de hoje já existe — só o primeiro arranque do dia espera pelo
    `mysqldump`. Uma falha não impede o arranque: fica no log.
    """
    repositorio.criar_backup()
    repositorio.limpar_backups_antigos()


def _preparar_login():
    """Passo "A abrir o início de sessão": seed das configurações e,
    numa base sem responsáveis, o Master de fábrica. Devolve True se
    o Master foi criado agora (o aviso só se mostra depois de a janela
    de arranque fechar)."""
    configuracoes.garantir_seed()
    return sistema.garantir_master_inicial() is not None


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


def _avisar_migracao_falhou(erro):
    """Uma migração falhou: avisa e a aplicação fecha.

    Ainda não existe nenhuma janela nesta altura (a de arranque já
    fechou): cria-se uma raiz Tk escondida só para o popup de erro não
    aparecer com uma janela vazia atrás.
    """
    raiz = tkinter.Tk()
    raiz.withdraw()
    componentes.mostrar_erro(
        f"{erro}\n\nA aplicação vai fechar. Os detalhes ficaram no "
        f"log e a cópia de segurança de hoje foi feita antes da "
        f"atualização.",
        titulo="Atualização da base de dados",
    )
    raiz.destroy()


if __name__ == "__main__":
    main()
