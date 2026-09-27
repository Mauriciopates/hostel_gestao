"""Persistência de propriedades, unidades, quartos e lugares."""

from typing import cast

from ._base import obter_conexao


# --- propriedades -----------------------------------------------------


def inserir_propriedade(propriedade):
    """Insere uma propriedade nova na base de dados.

    Espera um dicionário com id, nome, morada, iban, ativo. O `iban`
    é opcional (ver docstring do módulo) — quando não vier no
    dicionário, grava-se NULL.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO propriedades (id, nome, morada, iban, ativo) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                propriedade["id"],
                propriedade["nome"],
                propriedade["morada"],
                propriedade.get("iban") or None,
                propriedade["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_propriedade(linha):
    """Converte o BOOLEAN (0/1 no MySQL) para bool e repõe "" em
    `iban` quando vier NULL — mesma convenção de string vazia usada
    em todo o sistema para "sem valor" (aplicada às tabelas de
    unidades, quartos, lugares, responsáveis, clientes, ocupações e
    produtos desde a v1.1.0).
    """
    linha["ativo"] = bool(linha["ativo"])

    if linha.get("iban") is None:
        linha["iban"] = ""

    return linha


def procurar_propriedade(propriedade_id):
    """Procura a propriedade pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM propriedades WHERE id = %s", (propriedade_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_propriedade(linha)

    return linha


def listar_propriedades(incluir_inativas=False):
    """Devolve as propriedades ativas, ou todas se pedido."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativas:
            cursor.execute("SELECT * FROM propriedades")
        else:
            cursor.execute("SELECT * FROM propriedades WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_propriedade(linha) for linha in linhas]


def atualizar_propriedade(propriedade_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) da
    propriedade. Não faz nada se `campos` vier vazio.

    Converte "" para NULL em `iban` quando presente nos campos —
    mesma convenção já aplicada a `responsavel_desconto_renda_id`,
    `desativado_por_id`, etc.: string vazia nunca vai para a base,
    vai NULL.
    """
    if not campos:
        return

    campos = dict(campos)

    if "iban" in campos:
        campos["iban"] = campos["iban"] or None

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [propriedade_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE propriedades SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


def contar_unidades_ativas(propriedade_id):
    """Conta as unidades ativas associadas à propriedade indicada.

    Substitui o scan direto a dados["unidades"] que `propriedades.
    desativar` fazia antes, agora que essa tabela vive no MySQL.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM unidades "
            "WHERE propriedade_id = %s AND ativo = 1",
            (propriedade_id,),
        )
        total = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    return total


# --- unidades -----------------------------------------------------


def inserir_unidade(unidade):
    """Insere uma unidade nova na base de dados.

    Espera um dicionário com id, propriedade_id, nome, tipo, preco_base,
    preco_epoca_alta, multa_check_in_tardio, epoca_alta_ativa,
    em_manutencao, ativo, permite_cama_extra, qtd_cama_extra,
    tipo_cama_extra — o mesmo formato que `unidades.criar` já
    construía para a estrutura em memória. Os três últimos campos
    foram acrescentados na Fase 2, v1.4.0 (item (d) — cama extra do
    Airbnb; a coluna já existia desde um ALTER TABLE anterior, só
    faltava ser escrita).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO unidades (id, propriedade_id, nome, tipo, "
            "preco_base, preco_epoca_alta, multa_check_in_tardio, "
            "epoca_alta_ativa, em_manutencao, ativo, "
            "permite_cama_extra, qtd_cama_extra, tipo_cama_extra) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s)",
            (
                unidade["id"],
                unidade["propriedade_id"],
                unidade["nome"],
                unidade["tipo"],
                unidade["preco_base"],
                unidade["preco_epoca_alta"],
                unidade["multa_check_in_tardio"],
                unidade["epoca_alta_ativa"],
                unidade["em_manutencao"],
                unidade["ativo"],
                unidade["permite_cama_extra"],
                unidade["qtd_cama_extra"],
                unidade["tipo_cama_extra"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_unidade(linha):
    """Converte os campos BOOLEAN (0/1 no MySQL) de uma linha de
    `unidades` para bool — os DECIMAL já chegam como Decimal.

    `permite_cama_extra` segue a mesma conversão (Fase 2, v1.4.0).
    `tipo_cama_extra` segue a convenção de string vazia do resto do
    sistema quando vem NULL (unidade sem cama extra, ou não-Airbnb);
    `qtd_cama_extra` fica None nesse caso — não faz sentido um "0"
    ou uma string vazia para um número que, quando existe, é sempre
    positivo (ver `unidades._validar_cama_extra`).
    """
    linha["epoca_alta_ativa"] = bool(linha["epoca_alta_ativa"])
    linha["em_manutencao"] = bool(linha["em_manutencao"])
    linha["ativo"] = bool(linha["ativo"])
    linha["permite_cama_extra"] = bool(linha["permite_cama_extra"])

    if linha["tipo_cama_extra"] is None:
        linha["tipo_cama_extra"] = ""

    return linha


def procurar_unidade(unidade_id):
    """Procura a unidade pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM unidades WHERE id = %s", (unidade_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_unidade(linha)

    return linha


def listar_unidades(incluir_inativas=False, propriedade_id=None, tipo=None):
    """Devolve as unidades, filtráveis por propriedade e por tipo —
    os filtros aplicam-se agora na própria consulta SQL, em vez de
    em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    if propriedade_id is not None:
        condicoes.append("propriedade_id = %s")
        valores.append(propriedade_id)

    if tipo is not None:
        condicoes.append("tipo = %s")
        valores.append(tipo)

    sql = "SELECT * FROM unidades"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_unidade(linha) for linha in linhas]


def listar_unidades_com_propriedade(incluir_inativas=False, tipo=None):
    """Devolve as unidades já ligadas ao nome da respetiva
    propriedade (INNER JOIN unidades x propriedades), para
    ComboBoxes que têm de desambiguar unidades com o mesmo nome em
    propriedades diferentes (Fase 2, v1.4.0, ação 4 do plano de
    correções). Cada linha tem os mesmos campos de `listar_unidades`
    (via `u.*`), mais `propriedade_nome`.

    `incluir_inativas` refere-se só às unidades — o JOIN não filtra
    por `propriedades.ativo` (uma unidade ativa de uma propriedade
    desativada não devia existir na prática, já que
    `propriedades.desativar` exige forçar quando há unidades
    ativas, mas o filtro fica de fora por segurança, não por
    garantia).

    Ordenado por nome da propriedade e depois da unidade, para o
    ComboBox já sair agrupado por propriedade em vez de disperso.
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("u.ativo = 1")

    if tipo is not None:
        condicoes.append("u.tipo = %s")
        valores.append(tipo)

    sql = (
        "SELECT u.*, p.nome AS propriedade_nome "
        "FROM unidades u "
        "INNER JOIN propriedades p ON p.id = u.propriedade_id"
    )
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY p.nome, u.nome"

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_unidade(linha) for linha in linhas]


def atualizar_unidade(unidade_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) da
    unidade. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [unidade_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE unidades SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


# --- quartos --------------------------------------------------------


def inserir_quarto(quarto):
    """Insere um quarto novo na base de dados.

    Espera um dicionário com id, unidade_id, nome, privativo,
    limpeza_incluida, ativo.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO quartos (id, unidade_id, nome, privativo, "
            "limpeza_incluida, ativo) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                quarto["id"],
                quarto["unidade_id"],
                quarto["nome"],
                quarto["privativo"],
                quarto["limpeza_incluida"],
                quarto["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_quarto(linha):
    linha["privativo"] = bool(linha["privativo"])
    linha["limpeza_incluida"] = bool(linha["limpeza_incluida"])
    linha["ativo"] = bool(linha["ativo"])
    return linha


def procurar_quarto(quarto_id):
    """Procura o quarto pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM quartos WHERE id = %s", (quarto_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_quarto(linha)

    return linha


def listar_quartos(incluir_inativas=False, unidade_id=None):
    """Devolve os quartos, filtráveis por unidade — o filtro aplica-se
    na própria consulta SQL, em vez de em Python sobre a lista em
    memória.
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    if unidade_id is not None:
        condicoes.append("unidade_id = %s")
        valores.append(unidade_id)

    sql = "SELECT * FROM quartos"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_quarto(linha) for linha in linhas]


def atualizar_quarto(quarto_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    quarto. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [quarto_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE quartos SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


# --- lugares ----------------------------------------------------------


def inserir_lugar(lugar):
    """Insere um lugar novo na base de dados.

    Espera um dicionário com id, quarto_id, nome, tipo_cama,
    capacidade, ativo, e opcionalmente posicao_beliche e
    beliche_grupo_id (Fase 2, v1.4.0 — beliches; `.get()` porque só
    faz sentido em lugares com tipo_cama='beliche', ficam None nos
    restantes).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO lugares "
            "(id, quarto_id, nome, tipo_cama, capacidade, ativo, "
            "posicao_beliche, beliche_grupo_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                lugar["id"],
                lugar["quarto_id"],
                lugar["nome"],
                lugar["tipo_cama"],
                lugar["capacidade"],
                lugar["ativo"],
                lugar.get("posicao_beliche"),
                lugar.get("beliche_grupo_id"),
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_lugar(linha):
    linha["ativo"] = bool(linha["ativo"])

    # Fase 2, v1.4.0 — mesma convenção de string vazia usada em todo
    # o sistema para colunas de texto opcionais (ver _normalizar_
    # propriedade/_normalizar_requisicao): NULL vira "", nunca None,
    # para quem consome o dicionário não ter de tratar os dois casos.
    if linha["posicao_beliche"] is None:
        linha["posicao_beliche"] = ""

    if linha["beliche_grupo_id"] is None:
        linha["beliche_grupo_id"] = ""

    return linha


def procurar_lugar(lugar_id):
    """Procura o lugar pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM lugares WHERE id = %s", (lugar_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_lugar(linha)

    return linha


def listar_lugares(incluir_inativas=False, quarto_id=None):
    """Devolve os lugares, filtráveis por quarto — o filtro aplica-se
    na própria consulta SQL, em vez de em Python sobre a lista em
    memória.
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    if quarto_id is not None:
        condicoes.append("quarto_id = %s")
        valores.append(quarto_id)

    sql = "SELECT * FROM lugares"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_lugar(linha) for linha in linhas]


def atualizar_lugar(lugar_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    lugar. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [lugar_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE lugares SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()
