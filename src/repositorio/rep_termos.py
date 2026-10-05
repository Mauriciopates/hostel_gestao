"""Persistência dos textos legais e dos avisos de privacidade
(v1.6.0)."""

import logging
from typing import cast

from ._base import obter_conexao

logger = logging.getLogger(__name__)


# --- textos legais e avisos de privacidade (v1.6.0) -------------------


def _normalizar_texto_legal(linha):
    """Converte o TINYINT(1) do `em_vigor` para booleano.

    Mesma convenção do `_normalizar_responsavel`: quem consome o
    dicionário não tem de saber que o MySQL devolve 0/1.
    """
    linha["em_vigor"] = bool(linha["em_vigor"])

    return linha


def obter_texto_em_vigor(tipo):
    """Devolve a versão em vigor de um documento, ou None.

    O `LIMIT 1` é uma rede de segurança: a regra "só uma versão
    de cada tipo em vigor" vive na camada de negócio, porque o
    MySQL não a consegue garantir sozinho (seria um índice
    parcial). Se por engano ficarem duas a 1, devolve a mais
    recente em vez de rebentar.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM textos_legais "
            "WHERE tipo = %s AND em_vigor = 1 "
            "ORDER BY id DESC LIMIT 1",
            (tipo,),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_texto_legal(linha)

    return linha


def obter_texto(tipo, versao):
    """Devolve uma versão concreta de um documento, ou None.

    Serve para mostrar, mais tarde, a redação exata que a pessoa
    aceitou — que pode já não ser a que está em vigor. É esta
    função que dá corpo à prova.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM textos_legais " "WHERE tipo = %s AND versao = %s",
            (tipo, versao),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_texto_legal(linha)

    return linha


# Migração 0003: o titular deixou de ser `titular_tipo` + `titular_id`
# (sem FK possível) e passou a ser UMA de duas colunas, cada uma com a
# sua chave estrangeira. O resto do sistema continua a falar em
# (titular_tipo, titular_id): a tradução para a coluna certa vive só
# aqui, na camada que toca na base.
_COLUNA_TITULAR = {
    "cliente": "cliente_id",
    "responsavel": "responsavel_id",
}


def _coluna_titular(titular_tipo):
    """Nome da coluna do titular. Lista fechada: o nome entra no texto
    do SQL, por isso NUNCA pode vir de fora sem passar por aqui."""
    try:
        return _COLUNA_TITULAR[titular_tipo]
    except KeyError:
        raise ValueError(
            f"Tipo de titular desconhecido: {titular_tipo}"
        ) from None


def _normalizar_aviso(linha):
    """NULL vira "" nos campos opcionais, como no resto do sistema.

    `registado_por_id` é NULL quando o registo veio do site sem
    ninguém pelo meio (suporte = 'web'); `arquivo` é NULL quando
    não há folha assinada guardada.

    Repõe também `titular_tipo` e `titular_id` (calculados a partir da
    coluna preenchida), para quem lê o dicionário não ter de saber da
    mudança da migração 0003.
    """
    if linha.get("cliente_id"):
        linha["titular_tipo"], linha["titular_id"] = (
            "cliente", linha["cliente_id"])
    else:
        linha["titular_tipo"], linha["titular_id"] = (
            "responsavel", linha.get("responsavel_id"))

    for campo in ("registado_por_id", "arquivo"):
        if linha.get(campo) is None:
            linha[campo] = ""

    return linha


def obter_ultimo_aviso(titular_tipo, titular_id, documento):
    """Devolve o registo mais recente desse documento para esse
    titular, ou None se nunca houve nenhum.

    O `id` entra no desempate porque duas entregas podem cair no
    mesmo segundo — sem ele, qual é "a última" ficava ao critério
    do motor.
    """
    coluna = _coluna_titular(titular_tipo)
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM avisos_privacidade "
            f"WHERE {coluna} = %s AND documento = %s "
            "ORDER BY data_entrega DESC, id DESC LIMIT 1",
            (titular_id, documento),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_aviso(linha)

    return linha


def listar_avisos(titular_tipo, titular_id):
    """Histórico completo de um titular, do mais recente para o
    mais antigo. Usado para mostrar o que já foi entregue.
    """
    coluna = _coluna_titular(titular_tipo)
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM avisos_privacidade "
            f"WHERE {coluna} = %s "
            "ORDER BY data_entrega DESC, id DESC",
            (titular_id,),
        )
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_aviso(linha) for linha in linhas]


def registar_aviso(
    titular_tipo,
    titular_id,
    documento,
    versao_texto,
    registado_por_id,
    suporte,
):
    """Grava uma entrega/aceitação e devolve o id criado.

    NÃO recebe a data de propósito: o `NOW()` é avaliado pelo
    servidor MySQL. Se a data viesse do Python, estava a gravar o
    relógio da máquina de quem clicou — e uma data que faz prova
    não pode vir de onde o utilizador mexe.

    Uma linha desta tabela nunca se atualiza. Uma aceitação nova
    é uma linha nova.

    O titular vai para `cliente_id` OU `responsavel_id` (a outra fica
    NULL). As FKs garantem que a pessoa existe e o CHECK
    `ck_aviso_um_titular` que só uma das duas está preenchida.
    """
    _coluna_titular(titular_tipo)          # valida o tipo
    cliente_id = titular_id if titular_tipo == "cliente" else None
    responsavel_id = titular_id if titular_tipo == "responsavel" else None

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO avisos_privacidade "
            "(cliente_id, responsavel_id, documento, versao_texto, "
            "data_entrega, registado_por_id, suporte) "
            "VALUES (%s, %s, %s, %s, NOW(), %s, %s)",
            (
                cliente_id,
                responsavel_id,
                documento,
                versao_texto,
                registado_por_id or None,
                suporte,
            ),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
        logger.info(
            "Aviso de privacidade registado — titular_tipo=%s, "
            "titular_id=%s, documento=%s, suporte=%s",
            titular_tipo,
            titular_id,
            documento,
            suporte,
        )
    finally:
        conexao.close()

    return novo_id


def listar_textos(tipo=None):
    """Todas as versões, da mais recente para a mais antiga.

    Sem `tipo`, devolve as de todos os documentos. Serve o histórico
    do ecrã de Configurações — e o dia em que alguém perguntar que
    redação estava em vigor numa data concreta.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if tipo is None:
            cursor.execute(
                "SELECT * FROM textos_legais "
                "ORDER BY tipo, publicado_em DESC, id DESC"
            )
        else:
            cursor.execute(
                "SELECT * FROM textos_legais WHERE tipo = %s "
                "ORDER BY publicado_em DESC, id DESC",
                (tipo,),
            )
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_texto_legal(linha) for linha in linhas]


def contar_avisos_por_versao(documento, versao_texto):
    """Quantos titulares DISTINTOS registaram esta versão.

    `COUNT(DISTINCT ...)` e não `COUNT(*)`: se um dia a mesma pessoa
    tiver duas linhas da mesma versão (papel e sistema, por exemplo),
    continua a ser uma pessoa. O ecrã diz "2 de 4 aceitaram" — tem de
    contar gente, não registos.

    Porquê o CONCAT: `COUNT(DISTINCT a, b)` ignora as linhas em que
    alguma das colunas é NULL — e aqui uma das duas é SEMPRE NULL.
    O prefixo "C:"/"R:" separa um cliente de um responsável que por
    acaso tivessem o mesmo id.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(DISTINCT IF(cliente_id IS NOT NULL, "
            "CONCAT('C:', cliente_id), CONCAT('R:', responsavel_id))) "
            "FROM avisos_privacidade "
            "WHERE documento = %s AND versao_texto = %s",
            (documento, versao_texto),
        )
        total = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    return total


def publicar_texto(tipo, versao, texto, publicado_em):
    """Põe uma versão nova em vigor e tira a anterior. Devolve o id.

    As duas instruções correm na MESMA transação, e é isso que esta
    função existe para garantir. Se só o UPDATE passasse, ficavas sem
    nenhuma versão em vigor e ninguém conseguia aceitar nada; se só o
    INSERT passasse, ficavas com duas em vigor ao mesmo tempo. Uma
    regra que a base não consegue impor sozinha (seria um índice
    parcial) tem de ser imposta por quem escreve.

    Não é preciso `start_transaction()`: o mysql.connector abre as
    ligações com `autocommit` desligado, portanto os dois `execute`
    já estão dentro da mesma transação e só o `commit` os torna
    definitivos. Se houver exceção pelo meio, o `close()` do
    `finally` fecha sem commit — e o MySQL desfaz tudo.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE textos_legais SET em_vigor = 0 WHERE tipo = %s",
            (tipo,),
        )
        cursor.execute(
            "INSERT INTO textos_legais "
            "(tipo, versao, texto, publicado_em, em_vigor) "
            "VALUES (%s, %s, %s, %s, 1)",
            (tipo, versao, texto, publicado_em),
        )
        novo_id = cursor.lastrowid
        conexao.commit()
        logger.info(
            "Texto legal publicado — tipo=%s, versao=%s", tipo, versao
        )
    finally:
        conexao.close()

    return novo_id
