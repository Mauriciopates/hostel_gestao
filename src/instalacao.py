"""Instalação assistida da base de dados (v1.8.0, INST-02).

Diz em que estado está a base de dados de um servidor e, quando faz
sentido, prepara-a (cria a base e as tabelas do esquema oficial).
Usado pelo arranque (`gui_servidores.garantir_ligacao`) e pelo botão
"Testar" do formulário de servidor.

Não fala com o MySQL diretamente: pede ao `repositorio` (estado_base,
preparar_base) e ao `servidores` (túnel e credenciais). Recebe o
servidor e a password em vez do id, para o formulário poder usar um
servidor ainda não gravado.

ESTADOS (o que `diagnosticar` devolve):
  ERRO        não liga (servidor em baixo, password errada, túnel...)
  SEM_BASE    liga, mas a base de dados não existe       → oferece criar
  VAZIA       a base existe e não tem tabelas            → oferece criar
  INCOMPLETA  tem parte das nossas tabelas               → oferece completar
  ALHEIA      tem tabelas, mas nenhuma nossa             → RECUSA (nunca
              mistura com a base de outra aplicação)
  PRONTA      tem todas as tabelas do esquema

A `migracoes_aplicadas` não conta para INCOMPLETA: numa base anterior
à v1.8.0 ela é criada pelas próprias migrações, no arranque.
"""

import logging

import repositorio
import servidores

logger = logging.getLogger(__name__)

ERRO = "erro"
SEM_BASE = "sem_base"
VAZIA = "vazia"
INCOMPLETA = "incompleta"
ALHEIA = "alheia"
PRONTA = "pronta"

_ESTADOS_PREPARAVEIS = (SEM_BASE, VAZIA, INCOMPLETA)

_TABELA_DE_CONTROLO = "migracoes_aplicadas"


def diagnosticar(servidor, password):
    """Devolve (estado, texto, em_falta).

    'texto' é a frase para o ecrã; 'em_falta' é a lista das tabelas do
    esquema que faltam (vazia quando não se aplica).
    """
    base = servidor["base"]

    try:
        servidores.abrir_tunel(servidor)
        existe, tabelas = repositorio.estado_base(
            servidores.credenciais(servidor, password)
        )
    except servidores.ErroServidor as erro:
        return ERRO, str(erro), []
    except Exception as erro:  # erro do MySQL (driver) ao ligar
        return ERRO, f"O MySQL recusou a ligação.\n\n{erro}", []

    do_esquema = [
        t for t in repositorio.tabelas_do_esquema()
        if t != _TABELA_DE_CONTROLO
    ]

    if not existe:
        return (
            SEM_BASE,
            f"A base de dados '{base}' não existe neste servidor.",
            do_esquema,
        )

    if not tabelas:
        return (
            VAZIA,
            f"A base de dados '{base}' existe, mas está vazia.",
            do_esquema,
        )

    if not tabelas & set(do_esquema):
        return (
            ALHEIA,
            f"A base de dados '{base}' tem {len(tabelas)} tabelas, mas "
            f"nenhuma é do Hostel Gestão — parece ser de outra "
            f"aplicação. Escolha outra base de dados.",
            [],
        )

    em_falta = [t for t in do_esquema if t not in tabelas]
    if em_falta:
        return (
            INCOMPLETA,
            f"A base de dados '{base}' está incompleta: faltam "
            f"{len(em_falta)} tabelas ({', '.join(em_falta)}).",
            em_falta,
        )

    return (
        PRONTA,
        f"Ligação a '{base}' com sucesso — {len(tabelas)} tabelas.",
        [],
    )


def pode_preparar(estado):
    """True se o estado se resolve criando/completando a base."""
    return estado in _ESTADOS_PREPARAVEIS


def pergunta(estado, servidor):
    """Texto da confirmação a mostrar antes de `preparar`."""
    base = servidor["base"]
    if estado == INCOMPLETA:
        return (
            f"A base de dados '{base}' está incompleta.\n\n"
            f"Criar as tabelas em falta? As que já existem, e os seus "
            f"dados, não são alteradas."
        )
    if estado == VAZIA:
        return (
            f"A base de dados '{base}' está vazia.\n\n"
            f"Criar as tabelas do Hostel Gestão?"
        )
    return (
        f"A base de dados '{base}' não existe neste servidor.\n\n"
        f"Criar a base de dados e as tabelas do Hostel Gestão?"
    )


def preparar(servidor, password):
    """Cria a base (se preciso) e as tabelas em falta.

    Levanta ValueError com uma mensagem pronta para o ecrã se falhar —
    incluindo o caso de o utilizador do MySQL não ter permissão (D8:
    pede-se que a base seja criada à mão; a app nunca pede o root).
    """
    base = servidor["base"]
    try:
        servidores.abrir_tunel(servidor)
        repositorio.preparar_base(servidores.credenciais(servidor, password))
    except PermissionError as erro:
        logger.warning("Sem permissão para preparar '%s': %s", base, erro)
        raise ValueError(
            f"O utilizador '{servidor['utilizador']}' do MySQL não tem "
            f"permissão para criar a base de dados '{base}' ou as suas "
            f"tabelas.\n\n"
            f"Peça ao administrador do MySQL para criar a base "
            f"'{base}' (utf8mb4) e dar a este utilizador todas as "
            f"permissões sobre ela. Depois, volte a testar."
        ) from erro
    except servidores.ErroServidor as erro:
        raise ValueError(str(erro)) from erro
    except ValueError:
        raise
    except Exception as erro:  # restantes erros do MySQL
        logger.exception("Falha ao preparar a base '%s'", base)
        raise ValueError(
            f"Não foi possível preparar a base de dados '{base}'.\n\n"
            f"{erro}"
        ) from erro

    logger.info("Base '%s' preparada (instalação assistida)", base)
