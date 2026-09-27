"""Persistência das configurações e do histórico de alterações."""

import logging
from typing import cast

from ._base import obter_conexao

logger = logging.getLogger(__name__)


# --- configuracoes ---------------------------------------------------
#
# Tabelas `configuracoes` e `configuracoes_historico`, criadas no
# esquema v1.5.4 (ver Modelo_de_dados_esquema_v.1.5.4.sql).
#
# A tabela `configuracoes` guarda par chave/valor:
#   - chave      (PK, VARCHAR 60)  — ex.: "operacao.dia_vencimento"
#   - valor      (VARCHAR 255)     — sempre texto; conversão fica
#                                     no `configuracoes.py`
#   - descricao  (VARCHAR 255)     — legível, mostrada na GUI
#
# A tabela `configuracoes_historico` guarda cada alteração:
#   - id, chave (FK), valor_anterior, valor_novo,
#     data, responsavel_id (FK), motivo
#
# A leitura/escrita é feita pelo módulo `configuracoes.py` — estas
# funções só tocam na BD. Não validam nada de negócio (permissões,
# tipos, valores por omissão) — isso vive no `configuracoes.py`.


def procurar_configuracao(chave):
    """Devolve o registo da configuração com a chave indicada, ou None.

    A ausência não é erro: quem chama decide se cai no default ou
    levanta. Não normaliza nada — o valor vem cru (texto), a
    conversão é responsabilidade do `configuracoes.py`.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM configuracoes WHERE chave = %s", (chave,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    return linha


def listar_configuracoes(prefixo=None):
    """Devolve todas as configurações, opcionalmente filtradas por
    prefixo da chave (ex.: "operacao." para a tab Operação).

    'prefixo' é comparado com LIKE '<prefixo>%' — se for None, devolve
    tudo. Ordenado por chave, para a leitura ser estável.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)

        if prefixo is None:
            cursor.execute("SELECT * FROM configuracoes ORDER BY chave")
        else:
            cursor.execute(
                "SELECT * FROM configuracoes "
                "WHERE chave LIKE %s ORDER BY chave",
                (f"{prefixo}%",),
            )

        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return linhas


def gravar_configuracao(chave, valor, descricao=""):
    """Insere ou atualiza uma configuração (upsert).

    Se a chave já existir, faz UPDATE ao valor e à descrição.
    Se não existir, faz INSERT.

    Isto evita que o `configuracoes.py` tenha de decidir entre
    inserir e atualizar — a BD trata disso sozinha com
    `INSERT ... ON DUPLICATE KEY UPDATE`.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO configuracoes (chave, valor, descricao) "
            "VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "valor = VALUES(valor), "
            "descricao = VALUES(descricao)",
            (chave, valor, descricao),
        )
        conexao.commit()
        logger.info("Configuração gravada — chave=%s", chave)
    finally:
        conexao.close()


def inserir_configuracao_historico(registo):
    """Insere um registo no histórico de alterações.

    Espera um dicionário com id, chave, valor_anterior, valor_novo,
    data, responsavel_id, motivo.

    O `valor_anterior` é guardado como string vazia "" quando a
    chave estava a ser criada pela primeira vez — o esquema tem
    essa coluna como NOT NULL, por isso não pode ser NULL.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO configuracoes_historico "
            "(id, chave, valor_anterior, valor_novo, data, "
            "responsavel_id, motivo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                registo["id"],
                registo["chave"],
                registo["valor_anterior"],
                registo["valor_novo"],
                registo["data"],
                registo["responsavel_id"],
                registo["motivo"] or None,
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_configuracao_historico(linha):
    """Repõe "" em `motivo` quando vier NULL — mesma convenção de
    string vazia usada em todo o sistema para "sem valor".

    PORQUÊ (22/09/2026): o `inserir_configuracao_historico` já
    converte `""` em `NULL` na gravação (`registo["motivo"] or
    None`), porque a coluna é nullable por desenho — o motivo é
    opcional. Faltava o inverso na leitura: as linhas lidas com o
    motivo em branco chegavam ao consumidor com `None`, o que
    obrigava quem lê a tratar os dois casos (`None` e `""`) como
    coisas diferentes. Todas as outras tabelas do sistema já
    normalizam assim; o `configuracoes_historico` era a única
    exceção.
    """
    if linha.get("motivo") is None:
        linha["motivo"] = ""

    return linha


def listar_configuracao_historico(chave=None):
    """Devolve o histórico de alterações, opcionalmente filtrado por
    chave. Ordenado por data descendente, mais recentes primeiro.

    Quando 'chave' é None, devolve o histórico completo (todas as
    chaves). Útil para a GUI mostrar tudo de uma vez, se precisar.

    As linhas devolvidas passam por `_normalizar_configuracao_historico`
    — o `motivo` vem sempre como string (nunca None), mesmo quando
    foi gravado como NULL por ser opcional.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)

        if chave is None:
            cursor.execute(
                "SELECT * FROM configuracoes_historico "
                "ORDER BY data DESC, id DESC"
            )
        else:
            cursor.execute(
                "SELECT * FROM configuracoes_historico "
                "WHERE chave = %s "
                "ORDER BY data DESC, id DESC",
                (chave,),
            )

        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_configuracao_historico(linha) for linha in linhas]
