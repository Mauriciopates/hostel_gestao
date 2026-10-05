"""Persistência do stock: produtos, movimentos, requisições,
devoluções e respetivos itens."""

from typing import cast

from ._base import obter_conexao


# --- produtos -----------------------------------------------------


def inserir_produto(produto):
    """Insere um produto novo na base de dados.

    Passou a gravar também `desativado_por_id`/`data_desativacao`
    (a NULL na criação — só fazem sentido quando um produto é
    desativado com dependências ativas). Ver
    `estoque.desativar_produto`.

    Passou a gravar também `tipo_produto` (Fase 4, v1.4.0) — um
    ENUM com os valores 'consumivel', 'roupa_cama', 'roupa_banho'
    ou 'outro'. Vem sempre preenchido do `estoque.criar_produto`
    (default 'consumivel'). A coluna tem esse DEFAULT na base
    também, por isso valores antigos nunca ficam NULL.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO produtos (id, nome, unidade_medida, "
            "stock_minimo, tipo_produto, ativo, desativado_por_id, "
            "data_desativacao) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                produto["id"],
                produto["nome"],
                produto["unidade_medida"],
                produto["stock_minimo"],
                produto.get("tipo_produto") or "consumivel",
                produto["ativo"],
                produto.get("desativado_por_id") or None,
                produto.get("data_desativacao"),
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_produto(linha):
    """Converte os BOOLEAN para bool e repõe "" em
    `desativado_por_id` quando vier NULL — mesma convenção de string
    vazia usada em todo o sistema para "sem valor" (aplicada às
    tabelas de ocupações e clientes desde a v1.1.0).

    Repõe o default 'consumivel' em `tipo_produto` quando vier NULL
    (Fase 4, v1.4.0). Não devia acontecer — a coluna tem NOT NULL
    DEFAULT 'consumivel' na base — mas protege-se para o caso de
    alguma linha ser mexida à mão sem esse campo.
    """
    linha["ativo"] = bool(linha["ativo"])

    if linha.get("desativado_por_id") is None:
        linha["desativado_por_id"] = ""

    if linha.get("tipo_produto") is None:
        linha["tipo_produto"] = "consumivel"

    return linha


def procurar_produto(produto_id):
    """Procura o produto pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produtos WHERE id = %s", (produto_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_produto(linha)

    return linha


def listar_produtos(incluir_inativos=False):
    """Devolve os produtos ativos, ou todos se pedido."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativos:
            cursor.execute("SELECT * FROM produtos")
        else:
            cursor.execute("SELECT * FROM produtos WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_produto(linha) for linha in linhas]


def atualizar_produto(produto_id, campos):
    """Atualiza os campos indicados de um produto. Converte "" para
    NULL em `desativado_por_id` — é FK para `responsaveis`, e "" não
    é um id válido (mesmo caso já resolvido em
    `atualizar_ocupacao_mensal`).
    """
    if not campos:
        return

    campos = dict(campos)

    if "desativado_por_id" in campos:
        campos["desativado_por_id"] = campos["desativado_por_id"] or None

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [produto_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE produtos SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


def contar_movimentos_produto(produto_id):
    """Conta os movimentos associados a um produto.

    Usada por `estoque.desativar_produto` para decidir se a
    desativação tem de ser forçada — mesma função da
    `contar_unidades_ativas` (propriedades), agora para produtos.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM movimentos WHERE produto_id = %s",
            (produto_id,),
        )
        total = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    return total


def contar_itens_requisicao_produto(produto_id):
    """Conta os itens de requisição que referem este produto.

    Usada por `estoque.desativar_produto` para a mesma decisão de
    dependências ativas.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM itens_requisicao WHERE produto_id = %s",
            (produto_id,),
        )
        total = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    return total


def contar_itens_devolucao_produto(produto_id):
    """Conta os itens de devolução que referem este produto."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM itens_devolucao WHERE produto_id = %s",
            (produto_id,),
        )
        total = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    return total


# --- movimentos -----------------------------------------------------


def inserir_movimento(movimento):
    """Insere um movimento de stock (entrada, saída ou ajuste).

    'responsavel_id' e 'requisicao_id' são FK opcionais e ficam NULL
    quando vierem "" — mesmo caso já resolvido em `inserir_ocupacao`
    para 'lugar_id'. Movimentos são imutáveis (decisão 9): não há
    `atualizar_movimento` neste ficheiro, tal como `estoque.py` não
    tem `atualizar` nem `desativar` para esta entidade.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO movimentos (id, produto_id, tipo, quantidade, "
            "data, responsavel_id, requisicao_id, motivo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                movimento["id"],
                movimento["produto_id"],
                movimento["tipo"],
                movimento["quantidade"],
                movimento["data"],
                movimento["responsavel_id"] or None,
                movimento["requisicao_id"] or None,
                movimento["motivo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_movimento(linha):
    """Repõe "" em 'responsavel_id', 'requisicao_id' e 'motivo' quando
    vierem NULL — mesma convenção de string vazia usada em todo o
    sistema para "sem valor".
    """
    for campo in ("responsavel_id", "requisicao_id", "motivo"):
        if linha[campo] is None:
            linha[campo] = ""

    return linha


def listar_movimentos(produto_id=None, tipo=None):
    """Devolve os movimentos de stock, filtráveis por produto e por
    tipo — usado por `estoque.listar_movimentos` (para o ecrã de
    Movimentos) e por `estoque.saldo_produto` (que só filtra por
    produto).

    Os filtros aplicam-se na própria consulta SQL, em vez de em
    Python sobre a lista em memória — mesma convenção dos outros
    `listar` do ficheiro.

    Ordenada por data decrescente (mais recentes primeiro) — a
    ordenação também vem da consulta, para o resultado já chegar
    pronto a desenhar.
    """
    condicoes = []
    valores = []

    if produto_id is not None:
        condicoes.append("produto_id = %s")
        valores.append(produto_id)

    if tipo is not None:
        condicoes.append("tipo = %s")
        valores.append(tipo)

    sql = "SELECT * FROM movimentos"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    sql += " ORDER BY data DESC, id DESC"

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_movimento(linha) for linha in linhas]


# --- requisicoes ------------------------------------------------------


def inserir_requisicao(requisicao):
    """Insere uma requisição nova, no estado inicial "pendente".

    Passa a gravar também `observacao_rececao` e `origem` — as duas
    colunas novas de 13/09/2026 (ver docstring do módulo). Ambas
    vêm sempre preenchidas do `estoque.criar_requisicao` (a primeira
    com "" por omissão, a segunda com "pedido" ou "rol").

    'responsavel_rejeicao_id' não entra no INSERT — só existe a
    partir de `rejeitar_requisicao`, muito depois da criação — e
    fica NULL por omissão, tal como a coluna permite. As restantes
    colunas nullable (data_envio, data_fecho) já vêm None do
    dicionário que `estoque.criar_requisicao` constrói.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO requisicoes (id, responsavel_id, estado, "
            "data_pedido, data_envio, data_fecho, motivo_rejeicao, "
            "observacoes, observacao_rececao, origem) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                requisicao["id"],
                requisicao["responsavel_id"],
                requisicao["estado"],
                requisicao["data_pedido"],
                requisicao["data_envio"],
                requisicao["data_fecho"],
                requisicao["motivo_rejeicao"],
                requisicao["observacoes"],
                requisicao.get("observacao_rececao", ""),
                requisicao.get("origem") or "pedido",
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_requisicao(linha):
    """Repõe "" em 'responsavel_rejeicao_id', 'motivo_rejeicao',
    'observacoes', 'observacao_rececao' e 'origem' quando vierem
    NULL — mesma convenção de string vazia usada em todo o sistema
    para "sem valor".

    'origem' tem DEFAULT 'pedido' na tabela e o negócio preenche-a
    sempre, por isso na prática nunca vem NULL — mas fica na lista
    por simetria, e para proteger o dia em que a coluna perca esse
    DEFAULT.
    """
    for campo in (
        "responsavel_rejeicao_id",
        "motivo_rejeicao",
        "observacoes",
        "observacao_rececao",
        "origem",
    ):
        if linha[campo] is None:
            linha[campo] = ""

    return linha


def procurar_requisicao(requisicao_id):
    """Procura a requisição pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM requisicoes WHERE id = %s", (requisicao_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_requisicao(linha)

    return linha


def listar_requisicoes(estado=None, responsavel_id=None):
    """Devolve as requisições, filtráveis por estado e por
    responsável — o filtro por produto (decisão 20) cruza com
    `itens_requisicao` e continua a ser feito em `estoque.py`, tal
    como `contratos._nif_tem_contrato_mensal_ativo` cruza com
    `clientes` em vez de virar SQL aqui.
    """
    condicoes = []
    valores = []

    if estado is not None:
        condicoes.append("estado = %s")
        valores.append(estado)

    if responsavel_id is not None:
        condicoes.append("responsavel_id = %s")
        valores.append(responsavel_id)

    sql = "SELECT * FROM requisicoes"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_requisicao(linha) for linha in linhas]


def atualizar_requisicao(requisicao_id, campos):
    """Atualiza os campos indicados de `requisicoes`. Converte "" para
    NULL em 'responsavel_rejeicao_id' quando presente nos campos — é
    FK para `responsaveis` (mesmo caso de
    `atualizar_ocupacao_mensal`).

    Não trata `observacao_rececao` nem `origem` de forma especial —
    são colunas de texto, e uma string vazia é um valor legítimo
    nelas (tal como `motivo_rejeicao` ou `observacoes`, que já
    passam cruas).
    """
    if not campos:
        return

    campos = dict(campos)

    if "responsavel_rejeicao_id" in campos:
        campos["responsavel_rejeicao_id"] = (
            campos["responsavel_rejeicao_id"] or None
        )

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [requisicao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE requisicoes SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- itens_requisicao ---------------------------------------------


def inserir_item_requisicao(item):
    """Insere um item de requisição novo na base de dados.

    Espera um dicionário com id, requisicao_id, produto_id,
    quantidade_pedida, quantidade_enviada.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO itens_requisicao (id, requisicao_id, produto_id, "
            "quantidade_pedida, quantidade_enviada) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                item["id"],
                item["requisicao_id"],
                item["produto_id"],
                item["quantidade_pedida"],
                item["quantidade_enviada"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def procurar_item_requisicao(item_id):
    """Procura o item de requisição pelo id. Devolve None se não
    existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM itens_requisicao WHERE id = %s", (item_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    return linha


def listar_itens_requisicao(requisicao_id=None, produto_id=None):
    """Devolve os itens de requisição, filtráveis por requisição e por
    produto — os filtros aplicam-se na própria consulta SQL, em vez
    de em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if requisicao_id is not None:
        condicoes.append("requisicao_id = %s")
        valores.append(requisicao_id)

    if produto_id is not None:
        condicoes.append("produto_id = %s")
        valores.append(produto_id)

    sql = "SELECT * FROM itens_requisicao"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return linhas


def atualizar_item_requisicao(item_id, campos):
    """Atualiza os campos indicados de um item de requisição — usada
    por `estoque.enviar_requisicao` para gravar 'quantidade_enviada'.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [item_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE itens_requisicao SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- devolucoes -------------------------------------------------------


def inserir_devolucao(devolucao):
    """Insere uma devolução nova na base de dados.

    Espera um dicionário com id, requisicao_id, responsavel_id,
    estado, data_reportada, data_fecho.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO devolucoes (id, requisicao_id, responsavel_id, "
            "estado, data_reportada, data_fecho) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                devolucao["id"],
                devolucao["requisicao_id"],
                devolucao["responsavel_id"],
                devolucao["estado"],
                devolucao["data_reportada"],
                devolucao["data_fecho"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def procurar_devolucao(devolucao_id):
    """Procura a devolução pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM devolucoes WHERE id = %s", (devolucao_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    return linha


def listar_devolucoes(estado=None, requisicao_id=None, responsavel_id=None):
    """Devolve as devoluções, filtráveis por estado, requisição e
    responsável — os filtros aplicam-se na própria consulta SQL, em
    vez de em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if estado is not None:
        condicoes.append("estado = %s")
        valores.append(estado)

    if requisicao_id is not None:
        condicoes.append("requisicao_id = %s")
        valores.append(requisicao_id)

    if responsavel_id is not None:
        condicoes.append("responsavel_id = %s")
        valores.append(responsavel_id)

    sql = "SELECT * FROM devolucoes"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return linhas


def atualizar_devolucao(devolucao_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) da
    devolução. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [devolucao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE devolucoes SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- itens_devolucao ---------------------------------------------------


def inserir_item_devolucao(item):
    """Insere um item de devolução novo na base de dados.

    Espera um dicionário com id, devolucao_id, produto_id,
    quantidade.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO itens_devolucao (id, devolucao_id, produto_id, "
            "quantidade) VALUES (%s, %s, %s, %s)",
            (
                item["id"],
                item["devolucao_id"],
                item["produto_id"],
                item["quantidade"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def procurar_item_devolucao(item_id):
    """Procura o item de devolução pelo id. Devolve None se não
    existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM itens_devolucao WHERE id = %s", (item_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    return linha


def listar_itens_devolucao(devolucao_id=None, produto_id=None):
    """Devolve os itens de devolução, filtráveis por devolução e por
    produto — os filtros aplicam-se na própria consulta SQL, em vez
    de em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if devolucao_id is not None:
        condicoes.append("devolucao_id = %s")
        valores.append(devolucao_id)

    if produto_id is not None:
        condicoes.append("produto_id = %s")
        valores.append(produto_id)

    sql = "SELECT * FROM itens_devolucao"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return linhas

    # --- rol_lavanderia_regras -------------------------------------------


def listar_regras_rol_lavanderia(tipo_cama=None):
    """Devolve as regras do Rol de Lavanderia, filtráveis por
    tipo_cama.

    Fase 4, v1.4.0. A tabela `rol_lavanderia_regras` liga cada tipo
    de cama ('casal', 'solteiro', 'beliche', 'extra_casal',
    'extra_solteiro') a um produto e uma quantidade. Usada por
    `estoque.calcular_rol_lavanderia` para o cálculo automático do
    Rol.

    Devolve lista de dicionários, uma linha por (tipo_cama,
    produto_id).
    """
    condicoes = []
    valores = []

    if tipo_cama is not None:
        condicoes.append("tipo_cama = %s")
        valores.append(tipo_cama)

    sql = "SELECT * FROM rol_lavanderia_regras"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return linhas


def procurar_regra_rol_lavanderia(regra_id):
    """Devolve a regra do Rol com este id, ou None (v1.9.0)."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM rol_lavanderia_regras WHERE id = %s", (regra_id,)
        )
        linha = cursor.fetchone()
    finally:
        conexao.close()

    return cast(dict, linha) if linha else None


def inserir_regra_rol_lavanderia(regra):
    """Insere uma regra do Rol (id, tipo_cama, produto_id,
    quantidade) — v1.9.0, ecrã "Regras do Rol"."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO rol_lavanderia_regras "
            "(id, tipo_cama, produto_id, quantidade) "
            "VALUES (%s, %s, %s, %s)",
            (
                regra["id"],
                regra["tipo_cama"],
                regra["produto_id"],
                regra["quantidade"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def atualizar_quantidade_regra_rol_lavanderia(regra_id, quantidade):
    """Muda a quantidade de uma regra do Rol (v1.9.0)."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE rol_lavanderia_regras SET quantidade = %s WHERE id = %s",
            (quantidade, regra_id),
        )
        conexao.commit()
    finally:
        conexao.close()


def apagar_regra_rol_lavanderia(regra_id):
    """Apaga uma regra do Rol (v1.9.0).

    Exceção consciente à regra "não há DELETE no sistema": uma regra
    do Rol é configuração (que roupa vai para cada cama), não um
    registo do negócio — nada a referencia, e "retirar um produto da
    regra" é exatamente deixar de ter a linha. O histórico fica no
    log (`estoque.retirar_regra_rol`).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM rol_lavanderia_regras WHERE id = %s", (regra_id,)
        )
        conexao.commit()
    finally:
        conexao.close()
