"""Persistência de responsáveis e das atribuições
responsável <-> unidade."""

from typing import cast

from ._base import obter_conexao


# --- responsaveis -------------------------------------------------


def inserir_responsavel(responsavel):
    """Insere um responsável novo na base de dados.

    Espera um dicionário com id, nome, contacto, ativo,
    tipo_utilizador, e — a partir da v1.5.0 — username,
    password_hash, password_alterada_em, ultimo_login,
    desativado_por_id, data_desativacao.

    Os campos novos são `.get()` com default None: na criação
    de um responsável sem credencial (o caso normal de
    `responsaveis.criar`), todos vêm vazios. O `username` é
    UNIQUE e fica NULL até um Master lhe atribuir credencial.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO responsaveis "
            "(id, nome, contacto, ativo, tipo_utilizador, "
            "username, password_hash, password_alterada_em, "
            "ultimo_login, desativado_por_id, data_desativacao) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                responsavel["id"],
                responsavel["nome"],
                responsavel["contacto"],
                responsavel["ativo"],
                responsavel["tipo_utilizador"],
                responsavel.get("username") or None,
                responsavel.get("password_hash") or None,
                responsavel.get("password_alterada_em"),
                responsavel.get("ultimo_login"),
                responsavel.get("desativado_por_id") or None,
                responsavel.get("data_desativacao"),
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_responsavel(linha):
    """Converte o BOOLEAN (0/1) e os NULL dos campos novos da
    v1.5.0 para a convenção de string vazia usada em todo o
    sistema.

    As datas de credencial (password_alterada_em, ultimo_login,
    data_desativacao) seguem a mesma convenção já aplicada a
    `data_desativacao` em produtos/propriedades/unidades: NULL
    vira "" — quem consome o dicionário não tem de tratar None
    e "" como dois casos diferentes.

    `username` e `password_hash` seguem a convenção de string
    vazia do resto do sistema. Uma string vazia significa "sem
    credencial definida" — o estado inicial dos responsáveis
    existentes até um Master os preencher pela GUI.

    `desativado_por_id` (FK auto-referente) vira "" quando NULL —
    mesma convenção de `desativado_por_id` em produtos.
    """
    linha["ativo"] = bool(linha["ativo"])

    for campo in (
        "username",
        "password_hash",
        "password_alterada_em",
        "ultimo_login",
        "desativado_por_id",
        "data_desativacao",
    ):
        if linha.get(campo) is None:
            linha[campo] = ""

    return linha


def procurar_responsavel(responsavel_id):
    """Procura o responsável pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM responsaveis WHERE id = %s", (responsavel_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_responsavel(linha)

    return linha


def listar_responsaveis(incluir_inativos=False):
    """Devolve os responsáveis ativos, ou todos se pedido."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativos:
            cursor.execute("SELECT * FROM responsaveis")
        else:
            cursor.execute("SELECT * FROM responsaveis WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_responsavel(linha) for linha in linhas]


def procurar_responsavel_por_username(username):
    """Procura o responsável pelo username (coluna UNIQUE desde a
    v1.5.0). Devolve None se não existir.

    Usado por `utilizadores.autenticar` — o login procura pelo
    username, não pelo id. A coluna é NULL para os responsáveis
    que ainda não têm credencial definida; nesse caso devolve
    None como se o username não existisse (a distinção
    "sem credencial" vs "não encontrado" é feita em
    `utilizadores.autenticar`, não aqui).
    """
    if not username:
        return None

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM responsaveis WHERE username = %s",
            (username,),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_responsavel(linha)

    return linha


def listar_responsaveis_com_credencial(incluir_inativos=False):
    """Como `listar_responsaveis`, mas devolve também as colunas
    de credencial (username, password_hash, password_alterada_em,
    ultimo_login, desativado_por_id, data_desativacao) já
    normalizadas.

    Existe para o `gui_responsaveis` poder mostrar, sem segunda
    consulta, o estado da credencial de cada pessoa (tem / não
    tem) e o último acesso. A `listar_responsaveis` continua a
    existir para os consumidores que só querem o perfil — não
    vale a pena obrigá-los a receber campos de credencial que
    não vão usar.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativos:
            cursor.execute("SELECT * FROM responsaveis")
        else:
            cursor.execute("SELECT * FROM responsaveis WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_responsavel(linha) for linha in linhas]


def atualizar_responsavel(responsavel_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    responsável. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [responsavel_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE responsaveis SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- atribuições (responsável <-> unidade) ---------------------------


def inserir_atribuicao(atribuicao):
    """Insere uma ligação nova entre um responsável e uma unidade.

    Espera um dicionário com id, responsavel_id, unidade_id, ativo.
    O par (responsavel_id, unidade_id) é UNIQUE na tabela — inserir
    um par já existente dá erro do MySQL; para reativar uma ligação
    que já existiu, usa `atualizar_atribuicao` sobre a linha
    encontrada por `procurar_atribuicao`, não esta função.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO responsavel_unidade "
            "(id, responsavel_id, unidade_id, ativo) "
            "VALUES (%s, %s, %s, %s)",
            (
                atribuicao["id"],
                atribuicao["responsavel_id"],
                atribuicao["unidade_id"],
                atribuicao["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_atribuicao(linha):
    linha["ativo"] = bool(linha["ativo"])
    return linha


def procurar_atribuicao(responsavel_id, unidade_id):
    """Procura a ligação entre um responsável e uma unidade, ativa
    ou não.

    Devolve a linha inativa também de propósito: é o que permite a
    `unidades.atribuir_responsavel` reativar uma ligação que já
    existiu, em vez de tentar inserir o mesmo par outra vez e
    chocar com a restrição UNIQUE. Devolve None se o par nunca
    tiver sido ligado.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM responsavel_unidade "
            "WHERE responsavel_id = %s AND unidade_id = %s",
            (responsavel_id, unidade_id),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_atribuicao(linha)

    return linha


def listar_atribuicoes(
    responsavel_id=None, unidade_id=None, incluir_inativas=False
):
    """Lista ligações responsável-unidade, filtráveis pelos dois
    lados — mesmo padrão de `listar_itens_requisicao`: os filtros
    aplicam-se na própria consulta SQL, e nenhum dos dois é
    obrigatório.
    """
    condicoes = []
    valores = []

    if responsavel_id is not None:
        condicoes.append("responsavel_id = %s")
        valores.append(responsavel_id)

    if unidade_id is not None:
        condicoes.append("unidade_id = %s")
        valores.append(unidade_id)

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    sql = "SELECT * FROM responsavel_unidade"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_atribuicao(linha) for linha in linhas]


def atualizar_atribuicao(atribuicao_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo)
    de uma atribuição. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [atribuicao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE responsavel_unidade SET {colunas} WHERE id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()
