"""Reset do sistema — "Começar do zero".

Módulo de negócio. Orquestra a operação destrutiva que apaga TODOS
os dados da base de dados e recria o sistema com um único Master
padrão (constantes em `config.py`: NOME_MASTER_PADRAO,
UTILIZADOR_PADRAO, PASSWORD_PADRAO).

OPERATION CRÍTICA — o protocolo é:

  1. Validar o autor (tem de ser Master).
  2. Fazer backup automático com prefixo "pre_reset" — o ficheiro
     .sql fica em `config.DIR_BACKUPS` e serve de rede de segurança.
  3. Apagar todas as tabelas do sistema (`repositorio.apagar_tudo`).
  4. Criar um único responsável Master com o nome padrão.
  5. Definir-lhe a credencial (username + password).
  6. Devolver o Master criado, para quem chamar (o `gui_configuracoes`)
     fazer logoff e voltar ao login.

Se o passo 3 (apagar) falhar, o backup do passo 2 continua em
disco e o utilizador pode recuperar manualmente. Se o passo 4 ou
5 falhar, o sistema fica vazio — é preciso intervir manualmente
(aqui não há rollback automático, porque envolveria restaurar o
dump, que é uma operação com os seus próprios riscos).

A função NÃO se chama sozinha. É chamada pelo
`gui_configuracoes._comecar_do_zero`, e só depois de o utilizador
ter passado pelas duas confirmações (escrever "APAGAR TUDO" +
password).
"""

import logging

import config
import repositorio
import responsaveis
import utilizadores

logger = logging.getLogger(__name__)


def comecar_do_zero(autor):
    """Apaga todos os dados e recria o Master padrão.

    Parâmetros:
      - `autor`: o responsável ativo que está a executar o reset.
                 Tem de ser Master. Validado aqui, não só na GUI.

    Devolve o registo do Master criado.

    Levanta ValueError em qualquer falha de validação ou de
    escrita. Não devolve estado intermédio — ou corre tudo, ou
    rebenta antes de apagar.
    """
    _validar_autor_master(autor)

    logger.warning("Reset do sistema pedido — autor_id=%s", autor["id"])

    # 1. Backup automático antes de apagar
    caminho_backup = repositorio.criar_backup_com_nome("pre_reset")

    if caminho_backup is None:
        logger.error(
            "Reset abortado — backup pré-reset falhou, nada foi apagado"
        )
        raise ValueError(
            "Não foi possível criar o backup automático antes do "
            "reset. Verifique o `mysqldump` e a ligação MySQL."
        )

    # 2. Apagar tudo
    repositorio.apagar_tudo()

    # A partir daqui os dados já foram apagados. Qualquer falha deixa
    # o sistema vazio e sem Master — fica registada com o caminho do
    # backup a restaurar, e a exceção continua a subir.
    try:
        # 2b. Reiniciar os contadores de IDs.
        #     Sem isto, o Master criado a seguir seria RES-007 (ou o
        #     número onde o contador estava), não RES-001. Tem de vir
        #     ANTES de criar o Master: o `responsaveis.criar` chama o
        #     `proximo_id("RES")` e lê o contador — se ainda estivesse
        #     alto, não reiniciava nada.
        _reiniciar_contadores()

        # 3. Criar o Master padrão
        master = responsaveis.criar(
            nome=config.NOME_MASTER_PADRAO,
            contacto="",
            tipo_utilizador="Master",
            autor=None,  # não há autor — o sistema está a nascer de novo
        )

        # 4. Definir a credencial — por escrita direta.
        #
        #    `utilizadores.definir_credencial` exige um `autor` ativo, e
        #    aqui o sistema está literalmente a nascer de novo: não há
        #    sessão antes do reset. Por isso replicamos aqui o que o
        #    `bootstrap.py` já faz no `_definir_credencial_direto` —
        #    hash + escrita direta na BD, sem validação de permissão.
        _definir_credencial_inicial(master["id"])
    except Exception:
        logger.critical(
            "Reset incompleto — dados apagados mas o Master padrão não "
            "foi criado. Intervenção manual necessária. Backup: %s",
            caminho_backup,
            exc_info=True,
        )
        raise

    logger.warning("Reset concluído — novo Master id=%s", master["id"])

    # Devolver o Master para quem chamou (a GUI faz logoff)
    return master


# =====================================================================
# HELPERS INTERNOS
# =====================================================================


def _validar_autor_master(autor):
    """Confirma que o autor existe, está ativo e é Master.

    A barreira real contra abusos. Mesmo que a GUI falhe em esconder
    o botão, isto recusa qualquer tentativa não-Master.
    """
    if autor is None:
        raise ValueError(
            "Não há responsável ativo. Entre novamente no sistema "
            "antes de executar esta operação."
        )

    if not autor.get("id"):
        raise ValueError(
            "O responsável ativo não tem ID. Volte a entrar no sistema."
        )

    if autor.get("tipo_utilizador") != "Master":
        logger.warning(
            "Tentativa de reset recusada — autor_id=%s, tipo=%s",
            autor.get("id"),
            autor.get("tipo_utilizador"),
        )
        raise ValueError("Só um Master pode executar o reset do sistema.")


def _definir_credencial_inicial(responsavel_id):
    """Define a credencial do Master padrão por escrita direta na BD.

    Não usa `utilizadores.definir_credencial` porque essa função
    exige um autor ativo — e no contexto do `comecar_do_zero` não
    existe sessão antes do reset. Mesma técnica do
    `bootstrap.py:_definir_credencial_direto`.
    """
    import hashlib
    import os
    from datetime import datetime

    import repositorio

    ITERACOES = 100000
    salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        config.PASSWORD_PADRAO.encode("utf-8"),
        salt,
        ITERACOES,
    )
    password_hash = (
        f"pbkdf2_sha256${ITERACOES}$" f"{salt.hex()}${hash_bytes.hex()}"
    )

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    repositorio.atualizar_responsavel(
        responsavel_id,
        {
            "username": config.UTILIZADOR_PADRAO,
            "password_hash": password_hash,
            "password_alterada_em": agora,
        },
    )


def _reiniciar_contadores():
    """Zera o ficheiro de contadores de IDs.

    Usada só pelo `comecar_do_zero`. Depois de o reset apagar todos
    os registos, o próximo ID gerado por qualquer `proximo_id(...)`
    deve voltar a ser `XXX-001` (ou `XXX-0001`, conforme o prefixo)
    em vez de continuar a contar de onde estava.

    Não há risco de colisão: o passo 2 (`apagar_tudo`) já limpou as
    tabelas, por isso não existe nenhum registo antigo para colidir
    com os IDs novos.

    O ficheiro é escrito com `{}` — um dicionário vazio. O
    `_carregar_contadores` do `repositorio.py` já trata o caso de
    o ficheiro não existir ou estar vazio, devolvendo `{}` na mesma.
    Por isso, escrever `{}` é equivalente a apagá-lo.
    """
    import json
    from pathlib import Path

    ficheiro = Path(config.DIR_DADOS) / "contadores.json"
    ficheiro.write_text(json.dumps({}), encoding="utf-8")
    logger.info("Contadores de ID reiniciados")
