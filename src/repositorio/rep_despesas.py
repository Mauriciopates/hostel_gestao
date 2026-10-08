"""Persistência das despesas: categorias, fornecedores, despesas
e itens de despesa."""

from typing import cast

from ._base import obter_conexao


# --- categorias_despesa ---------------------------------------------


def inserir_categoria_despesa(categoria):
    """Insere uma categoria de despesa nova na base de dados.

    Espera um dicionário com id, nome, ativo. Os campos
    `desativado_por_id`/`data_desativacao` só existem depois de uma
    desativação, por isso não entram no INSERT (ficam NULL por
    omissão da tabela).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO categorias_despesa (id, nome, ativo) "
            "VALUES (%s, %s, %s)",
            (categoria["id"], categoria["nome"], categoria["ativo"]),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_categoria_despesa(linha):
    """Converte `ativo` de 0/1 para bool e repõe "" em
    `desativado_por_id` quando vier NULL — mesma convenção de
    string vazia usada em todo o sistema.
    """
    linha["ativo"] = bool(linha["ativo"])

    if linha.get("desativado_por_id") is None:
        linha["desativado_por_id"] = ""

    return linha


def procurar_categoria_despesa(categoria_id):
    """Procura uma categoria de despesa pelo id. Devolve None se não
    existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM categorias_despesa WHERE id = %s",
            (categoria_id,),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_categoria_despesa(linha)

    return linha


def listar_categorias_despesa(incluir_inativas=False):
    """Devolve as categorias de despesa. Ativas por omissão; todas se
    `incluir_inativas=True`.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativas:
            cursor.execute("SELECT * FROM categorias_despesa")
        else:
            cursor.execute("SELECT * FROM categorias_despesa WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_categoria_despesa(linha) for linha in linhas]


def atualizar_categoria_despesa(categoria_id, campos):
    """Atualiza os campos indicados de uma categoria de despesa.

    Converte "" para NULL em `desativado_por_id` quando presente nos
    campos — é FK para `responsaveis`, e "" não é um id válido
    (mesmo caso já resolvido em `atualizar_produto`).

    Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    campos = dict(campos)

    if "desativado_por_id" in campos:
        campos["desativado_por_id"] = campos["desativado_por_id"] or None

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [categoria_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE categorias_despesa SET {colunas} WHERE id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()


# --- fornecedores ---------------------------------------------------


def inserir_fornecedor(fornecedor):
    """Insere um fornecedor novo na base de dados.

    Espera um dicionário com id, nome, contacto, nif, ativo. Os
    campos `desativado_por_id`/`data_desativacao` não entram no
    INSERT (ficam NULL por omissão).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO fornecedores "
            "(id, nome, contacto, nif, ativo) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                fornecedor["id"],
                fornecedor["nome"],
                fornecedor["contacto"],
                fornecedor["nif"],
                fornecedor["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_fornecedor(linha):
    """Converte `ativo` de 0/1 para bool e repõe "" nos campos de
    texto que vierem NULL — mesma convenção de string vazia usada em
    todo o sistema.
    """
    linha["ativo"] = bool(linha["ativo"])

    for campo in ("contacto", "nif", "desativado_por_id"):
        if linha.get(campo) is None:
            linha[campo] = ""

    return linha


def procurar_fornecedor(fornecedor_id):
    """Procura um fornecedor pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM fornecedores WHERE id = %s",
            (fornecedor_id,),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_fornecedor(linha)

    return linha


def listar_fornecedores(incluir_inativos=False):
    """Devolve os fornecedores. Ativos por omissão; todos se
    `incluir_inativos=True`.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativos:
            cursor.execute("SELECT * FROM fornecedores")
        else:
            cursor.execute("SELECT * FROM fornecedores WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_fornecedor(linha) for linha in linhas]


def atualizar_fornecedor(fornecedor_id, campos):
    """Atualiza os campos indicados de um fornecedor.

    Converte "" para NULL em `desativado_por_id` quando presente nos
    campos — mesma razão de `atualizar_categoria_despesa`. `contacto`
    e `nif` aceitam "" como valor legítimo (é o estado "não
    preenchido" — texto vazio, não FK).

    Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    campos = dict(campos)

    if "desativado_por_id" in campos:
        campos["desativado_por_id"] = campos["desativado_por_id"] or None

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [fornecedor_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE fornecedores SET {colunas} WHERE id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()


# --- despesas -------------------------------------------------------


def inserir_despesa(despesa):
    """Insere uma despesa nova na base de dados.

    Espera um dicionário com TODOS os campos da tabela `despesas`,
    já resolvidos pelo `despesas.py` antes de chamar (autoria,
    categoria, etc.). Este bloco NÃO valida regras de negócio — só
    grava.

    As FKs opcionais (`unidade_id`, `fornecedor_id`,
    `despesa_origem_id`, `responsavel_cancelamento_id`,
    `itens_confirmados_por_id`) são convertidas de "" para NULL —
    mesma convenção de `inserir_movimento`.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO despesas ("
            "id, unidade_id, categoria_id, fornecedor_id, valor, "
            "data_lancamento, data_pagamento, data_vencimento, "
            "estado, recorrente, despesa_origem_id, "
            "itens_confirmados, itens_confirmados_por_id, "
            "itens_confirmados_em, responsavel_lancamento_id, "
            "responsavel_cancelamento_id, motivo_cancelamento, "
            "descricao, comprovativo_caminho) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                despesa["id"],
                despesa["unidade_id"] or None,
                despesa["categoria_id"],
                despesa["fornecedor_id"] or None,
                despesa["valor"],
                despesa["data_lancamento"],
                despesa["data_pagamento"],
                despesa["data_vencimento"],
                despesa["estado"],
                despesa["recorrente"],
                despesa["despesa_origem_id"] or None,
                despesa["itens_confirmados"],
                despesa["itens_confirmados_por_id"] or None,
                despesa["itens_confirmados_em"],
                despesa["responsavel_lancamento_id"],
                despesa["responsavel_cancelamento_id"] or None,
                despesa["motivo_cancelamento"],
                despesa["descricao"],
                despesa["comprovativo_caminho"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_despesa(linha):
    """Converte os BOOLEAN para bool e repõe "" nos campos de texto
    que vierem NULL — mesma convenção de string vazia usada em todo
    o sistema.
    """
    linha["recorrente"] = bool(linha["recorrente"])
    linha["itens_confirmados"] = bool(linha["itens_confirmados"])

    for campo in (
        "unidade_id",
        "fornecedor_id",
        "despesa_origem_id",
        "itens_confirmados_por_id",
        "responsavel_cancelamento_id",
        "unidade_atribuida_por_id",
        "motivo_cancelamento",
        "descricao",
        "comprovativo_caminho",
    ):
        if linha.get(campo) is None:
            linha[campo] = ""

    return linha


def procurar_despesa(despesa_id):
    """Procura uma despesa pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM despesas WHERE id = %s", (despesa_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_despesa(linha)

    return linha


def listar_despesas(
    estado=None,
    unidade_id=None,
    categoria_id=None,
    fornecedor_id=None,
):
    """Devolve as despesas, com filtros opcionais (aplicados na
    consulta SQL, em vez de em Python). Ordenada por data de
    lançamento descendente (mais recentes primeiro).

    O filtro por 'vencida' NÃO está aqui — é calculado em Python no
    `despesas.py`, porque 'vencida' não é um estado guardado.
    """
    condicoes = []
    valores = []

    if estado is not None:
        condicoes.append("estado = %s")
        valores.append(estado)

    if unidade_id is not None:
        condicoes.append("unidade_id = %s")
        valores.append(unidade_id)

    if categoria_id is not None:
        condicoes.append("categoria_id = %s")
        valores.append(categoria_id)

    if fornecedor_id is not None:
        condicoes.append("fornecedor_id = %s")
        valores.append(fornecedor_id)

    sql = "SELECT * FROM despesas"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    sql += " ORDER BY data_lancamento DESC, id DESC"

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_despesa(linha) for linha in linhas]


def atualizar_despesa(despesa_id, campos):
    """Atualiza os campos indicados de uma despesa.

    Converte "" para NULL nas FKs opcionais quando presentes nos
    campos — mesma convenção de `atualizar_movimento`. As colunas de
    texto (`motivo_cancelamento`, `descricao`,
    `comprovativo_caminho`) passam cruas — "" é um valor legítimo
    nelas.

    Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    campos = dict(campos)

    for campo_fk in (
        "unidade_id",
        "fornecedor_id",
        "despesa_origem_id",
        "itens_confirmados_por_id",
        "responsavel_cancelamento_id",
        "unidade_atribuida_por_id",
    ):
        if campo_fk in campos:
            campos[campo_fk] = campos[campo_fk] or None

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [despesa_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE despesas SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


# --- itens_despesa --------------------------------------------------


def inserir_item_despesa(item):
    """Insere um item de despesa novo na base de dados.

    Espera um dicionário com id, despesa_id, produto_id, quantidade,
    movimento_id. O `movimento_id` nasce None (a entrada no stock só
    acontece depois da confirmação) — ver
    `despesas.confirmar_itens_despesa`.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO itens_despesa "
            "(id, despesa_id, produto_id, quantidade, movimento_id) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                item["id"],
                item["despesa_id"],
                item["produto_id"],
                item["quantidade"],
                item["movimento_id"] or None,
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_item_despesa(linha):
    """Repõe "" em `movimento_id` quando vier NULL — é o estado
    normal antes da confirmação, não um erro.
    """
    if linha.get("movimento_id") is None:
        linha["movimento_id"] = ""

    return linha


def listar_itens_despesa(despesa_id=None, produto_id=None):
    """Devolve os itens de despesa, filtráveis por despesa e por
    produto — os filtros aplicam-se na consulta SQL, em vez de em
    Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if despesa_id is not None:
        condicoes.append("despesa_id = %s")
        valores.append(despesa_id)

    if produto_id is not None:
        condicoes.append("produto_id = %s")
        valores.append(produto_id)

    sql = "SELECT * FROM itens_despesa"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_item_despesa(linha) for linha in linhas]


def atualizar_item_despesa(item_id, campos):
    """Atualiza os campos indicados de um item de despesa — usada
    por `despesas.confirmar_itens_despesa` para gravar o
    `movimento_id` depois de criar o movimento de entrada no stock.
    """
    if not campos:
        return

    campos = dict(campos)

    if "movimento_id" in campos:
        campos["movimento_id"] = campos["movimento_id"] or None

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [item_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE itens_despesa SET {colunas} WHERE id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()
