"""Persistência de clientes."""

from typing import cast

from ._base import obter_conexao


# --- clientes -------------------------------------------------------


def inserir_cliente(cliente):
    """Insere um cliente novo na base de dados.

    Espera um dicionário com todos os campos que `clientes.criar` já
    construía para a estrutura em memória (id, nome, tipo_documento,
    numero_documento, nif, email, telefone, morada, nacionalidade,
    estado_civil, data_nascimento, validade_documento,
    contacto_emergencia, pais_emissor_documento, pais_residencia,
    incompleto, anonimizado, data_anonimizado,
    responsavel_anonimizado_id, ativo).

    'pais_emissor_documento' e 'pais_residencia' são novas
    (16/09/2026, exigidas só no regime Airbnb) — exige o
    ALTER TABLE clientes correspondente (ver aviso separado).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO clientes ("
            "id, nome, tipo_documento, numero_documento, nif, email, "
            "telefone, morada, nacionalidade, estado_civil, "
            "data_nascimento, validade_documento, contacto_emergencia, "
            "pais_emissor_documento, pais_residencia, "
            "incompleto, anonimizado, data_anonimizado, "
            "responsavel_anonimizado_id, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                cliente["id"],
                cliente["nome"],
                cliente["tipo_documento"],
                cliente["numero_documento"],
                cliente["nif"],
                cliente["email"],
                cliente["telefone"],
                cliente["morada"],
                cliente["nacionalidade"],
                cliente["estado_civil"],
                cliente["data_nascimento"],
                cliente["validade_documento"],
                cliente["contacto_emergencia"],
                cliente["pais_emissor_documento"],
                cliente["pais_residencia"],
                cliente["incompleto"],
                cliente["anonimizado"],
                cliente["data_anonimizado"],
                cliente["responsavel_anonimizado_id"] or None,
                cliente["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_cliente(linha):
    """Converte os campos BOOLEAN (0/1 no MySQL) de uma linha de
    `clientes` para bool — as DATE já chegam como `date` — e repõe ""
    em 'responsavel_anonimizado_id' quando vier NULL (mesma
    convenção de string vazia usada em todo o sistema para "sem
    valor", já aplicada a 'ocupacoes.lugar_id' em
    `_normalizar_ocupacao`; tinha ficado por fazer aqui, apesar de
    `inserir_cliente` já converter "" para NULL na gravação).
    """
    linha["incompleto"] = bool(linha["incompleto"])
    linha["anonimizado"] = bool(linha["anonimizado"])
    linha["ativo"] = bool(linha["ativo"])

    if linha["responsavel_anonimizado_id"] is None:
        linha["responsavel_anonimizado_id"] = ""

    return linha


def procurar_cliente(cliente_id):
    """Procura o cliente pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM clientes WHERE id = %s", (cliente_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_cliente(linha)

    return linha


def listar_clientes(incluir_inativos=False, incompleto=None):
    """Devolve os clientes, filtráveis por estado e por incompletos —
    o filtro 'incompleto' aplica-se agora na própria consulta SQL,
    em vez de em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if not incluir_inativos:
        condicoes.append("ativo = 1")

    if incompleto is not None:
        condicoes.append("incompleto = %s")
        valores.append(incompleto)

    sql = "SELECT * FROM clientes"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_cliente(linha) for linha in linhas]


def atualizar_cliente(cliente_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    cliente. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [cliente_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE clientes SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


def cliente_com_nif_existe(nif, ignorar_id=None):
    """Verifica se o NIF indicado já pertence a outro cliente ativo.

    Substitui o scan direto a dados["clientes"] que
    `clientes._nif_pertence_a_outro_cliente` fazia antes, agora que
    essa tabela vive no MySQL. Só considera clientes ativos (mesma
    regra de negócio de sempre) e ignora, se indicado, o próprio
    cliente — para 'atualizar' não se recusar a si mesmo ao manter
    o NIF que já tinha.
    """
    sql = "SELECT COUNT(*) FROM clientes WHERE nif = %s AND ativo = 1"
    valores = [nif]

    if ignorar_id is not None:
        sql += " AND id != %s"
        valores.append(ignorar_id)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(sql, valores)
        total = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    return total > 0
