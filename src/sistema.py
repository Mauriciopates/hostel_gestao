"""Reset do sistema — "Começar do zero".

Módulo de negócio. Orquestra a operação destrutiva que apaga TODOS
os dados da base de dados e recria o sistema com um único Master
padrão (constantes em `config.py`: NOME_MASTER_PADRAO,
UTILIZADOR_PADRAO, PASSWORD_PADRAO).

OPERATION CRÍTICA — o protocolo é:

  1. Validar o autor (tem de ser Master) e confirmar a password
     dele (regra movida da GUI para aqui em 23/09/2026).
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


def criar_backup_manual(autor):
    """Backup pedido à mão, nas Configurações (28/09/2026).

    Vivia no próprio ecrã, que importava o `repositorio` — a única
    exceção à regra "só o repositório toca na base, e a GUI só fala
    com módulos de negócio". Passou para aqui.

    Gera sempre um ficheiro novo (`manual_<data>_<hora>.sql`) e
    devolve o caminho, ou None se o `mysqldump` falhar. `autor` é só
    para o registo — qualquer perfil que veja o botão pode pedir uma
    cópia.
    """
    logger.info(
        "Backup manual pedido — autor_id=%s",
        autor["id"] if autor else None,
    )

    return repositorio.criar_backup_com_nome("manual")


def comecar_do_zero(autor, password):
    """Apaga todos os dados e recria o Master padrão.

    Parâmetros:
      - `autor`:    o responsável ativo que está a executar o reset.
                    Tem de ser Master. Validado aqui, não só na GUI.
      - `password`: a password do próprio autor, a confirmar a
                    operação. Verificada AQUI (23/09/2026): até esta
                    data a confirmação vivia só no modal da GUI, e
                    qualquer outro caminho (CLI, um ecrã futuro)
                    apagava tudo só com um Master na sessão. Usa o
                    `utilizadores.verificar_password` — é uma
                    confirmação, não um login.

    Devolve o registo do Master criado.

    Levanta ValueError em qualquer falha de validação ou de
    escrita. Não devolve estado intermédio — ou corre tudo, ou
    rebenta antes de apagar.
    """
    _validar_autor_master(autor)

    if not utilizadores.verificar_password(autor["id"], password):
        logger.warning(
            "Reset do sistema recusado — password errada, autor_id=%s",
            autor["id"],
        )
        raise ValueError(
            "A password não corresponde ao utilizador ativo. O reset "
            "não foi executado."
        )

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
        # 2b. (v1.8.0) Já não há contadores para reiniciar: o
        #     `proximo_id` calcula o número a partir do MAX(id) de
        #     cada tabela, e o TRUNCATE do passo 2 deixou-as vazias —
        #     o Master criado a seguir é RES-001 sem mais nada.

        # 3 e 4. Criar o Master padrão e a sua credencial — a mesma
        #    função da instalação (v1.8.0, INST-01).
        master = criar_master_padrao()
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
# MASTER PADRÃO — instalação (INST-01) e "Começar do zero"
# =====================================================================


def criar_master_padrao():
    """Cria o responsável Master de fábrica e a sua credencial.

    Nome, utilizador e password vêm do `config` (NOME_MASTER_PADRAO,
    UTILIZADOR_PADRAO, PASSWORD_PADRAO). A password de fábrica tem de
    ser trocada no primeiro acesso (`utilizadores.usa_password_padrao`
    + TrocarPasswordModal) — por isso pode estar no código e no manual.

    Sem validação de autor: só é chamada quando o sistema está a nascer
    (base nova, ou logo a seguir ao reset). Devolve o responsável.
    """
    master = responsaveis.criar(
        nome=config.NOME_MASTER_PADRAO,
        contacto="",
        tipo_utilizador="Master",
        autor=None,  # não há autor — o sistema está a nascer
    )

    # `utilizadores.definir_credencial` exige um autor ativo, que aqui
    # não existe — por isso a credencial é escrita diretamente.
    _definir_credencial_inicial(master["id"])

    return master


def garantir_master_inicial():
    """Cria o Master padrão se a base não tiver NENHUM responsável.

    Chamada em cada arranque (main_gui.py e main.py), depois das
    migrações e antes do login (v1.8.0, INST-01). Numa base nova é o
    que deixa alguém entrar; numa base em uso não faz nada — conta
    também os responsáveis desativados, para nunca criar um "admin"
    numa base que já teve utilizadores.

    Devolve o Master criado, ou None se não foi preciso.
    """
    if responsaveis.listar(incluir_inativos=True):
        return None

    master = criar_master_padrao()
    logger.warning(
        "Base sem responsáveis — criado o Master padrão id=%s (%s)",
        master["id"],
        config.UTILIZADOR_PADRAO,
    )
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
