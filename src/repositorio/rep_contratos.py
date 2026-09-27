"""Persistência das ocupações: base comum (`ocupacoes`) e as
especializações 1:1 `ocupacoes_mensal` e `ocupacoes_airbnb`."""

from typing import cast

from ._base import obter_conexao


# --- ocupacoes (base comum a contratos mensais e reservas Airbnb) -----


def inserir_ocupacao(ocupacao):
    """Insere uma ocupação (contrato mensal ou reserva Airbnb) na
    tabela base `ocupacoes`. Espera o mesmo dicionário que
    `contratos.criar_mensal`/`contratos.registar_airbnb` já
    construíam para a estrutura em memória.

    'lugar_id' é FK para `lugares` e fica NULL quando vier "" — uma
    ocupação sem lugar atribuído (mesmo caso já resolvido em
    `inserir_cliente` para 'responsavel_anonimizado_id').
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO ocupacoes (id, unidade_id, cliente_id, tipo, "
            "data_inicio, data_fim, lugar_id, aviso_documento, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                ocupacao["id"],
                ocupacao["unidade_id"],
                ocupacao["cliente_id"],
                ocupacao["tipo"],
                ocupacao["data_inicio"],
                ocupacao["data_fim"],
                ocupacao["lugar_id"] or None,
                ocupacao["aviso_documento"],
                ocupacao["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_ocupacao(linha):
    """Converte os BOOLEAN para bool e repõe "" em 'lugar_id' quando
    vier NULL — mesma convenção de string vazia usada em todo o
    sistema para "sem lugar atribuído".
    """
    linha["aviso_documento"] = bool(linha["aviso_documento"])
    linha["ativo"] = bool(linha["ativo"])

    if linha["lugar_id"] is None:
        linha["lugar_id"] = ""

    return linha


def procurar_ocupacao(ocupacao_id):
    """Procura a ocupação (base comum) pelo id. Devolve None se não
    existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ocupacoes WHERE id = %s", (ocupacao_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_ocupacao(linha)

    return linha


def listar_ocupacoes(
    incluir_inativas=False,
    unidade_id=None,
    cliente_id=None,
    tipo=None,
    aviso_documento=None,
    data_inicio=None,
    data_fim=None,
):
    """Devolve as ocupações, filtráveis por unidade, cliente, tipo e
    aviso de documento — os filtros aplicam-se na própria consulta
    SQL, em vez de em Python sobre a lista em memória. Serve tanto
    `contratos.listar` (a listagem da interface) como as funções
    internas que antes percorriam dados["ocupacoes"] à mão
    (`contratos._ocupantes_mensal`, `contratos._existe_sobreposicao`,
    `unidades._estado_mensal`, `unidades._estado_airbnb`,
    `unidades.desativar`, `unidades.quarto_privativo_ocupado`).

    `data_inicio` e `data_fim` filtram por SOBREPOSIÇÃO de intervalo
    (Fase financeiro, v1.5.0): devolve as ocupações que tocam o
    período, mesmo que comecem antes ou acabem depois. A condição
    é `ocupacao.data_inicio < data_fim AND (ocupacao.data_fim IS
    NULL OR ocupacao.data_fim > data_inicio)` — uma ocupação sem
    data_fim (contrato mensal em vigor) conta como se estendendo
    indefinidamente. Um filtro sem os dois parâmetros (ou só um)
    não se aplica — a condição só entra quando AMBOS são
    indicados, porque meio intervalo não define uma janela.
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    if unidade_id is not None:
        condicoes.append("unidade_id = %s")
        valores.append(unidade_id)

    if cliente_id is not None:
        condicoes.append("cliente_id = %s")
        valores.append(cliente_id)

    if tipo is not None:
        condicoes.append("tipo = %s")
        valores.append(tipo)

    if aviso_documento is not None:
        condicoes.append("aviso_documento = %s")
        valores.append(aviso_documento)

    if data_inicio is not None and data_fim is not None:
        condicoes.append("data_inicio < %s")
        valores.append(data_fim)
        condicoes.append("(data_fim IS NULL OR data_fim > %s)")
        valores.append(data_inicio)

    sql = "SELECT * FROM ocupacoes"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_ocupacao(linha) for linha in linhas]


def atualizar_ocupacao(ocupacao_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) da
    ocupação base. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [ocupacao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE ocupacoes SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- ocupacoes_mensal (especialização 1:1 do contrato mensal) ---------


def inserir_ocupacao_mensal(mensal):
    """Insere os dados específicos de um contrato mensal.

    'responsavel_desconto_renda_id' é FK para `responsaveis` e fica
    NULL quando vier "" — sem desconto, não há responsável a
    guardar (mesmo caso de 'lugar_id' em `inserir_ocupacao`).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO ocupacoes_mensal (ocupacao_id, renda_calculada, "
            "renda_praticada, responsavel_desconto_renda_id, caucao, "
            "caucao_exige_confirmacao, motivo_alteracao_renda, "
            "motivo_alteracao_caucao, dia_vencimento) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                mensal["ocupacao_id"],
                mensal["renda_calculada"],
                mensal["renda_praticada"],
                mensal["responsavel_desconto_renda_id"] or None,
                mensal["caucao"],
                mensal["caucao_exige_confirmacao"],
                mensal["motivo_alteracao_renda"],
                mensal["motivo_alteracao_caucao"],
                mensal["dia_vencimento"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_ocupacao_mensal(linha):
    """Converte os BOOLEAN para bool e repõe "" nos campos de texto
    que vierem NULL (a DECIMAL já chega como Decimal, mesma
    convenção de `_normalizar_unidade`).
    """
    linha["caucao_exige_confirmacao"] = bool(linha["caucao_exige_confirmacao"])
    linha["duracao_abaixo_minima"] = bool(linha["duracao_abaixo_minima"])
    linha["aviso_previo_insuficiente"] = bool(
        linha["aviso_previo_insuficiente"]
    )

    for campo in (
        "responsavel_desconto_renda_id",
        "motivo_alteracao_renda",
        "motivo_alteracao_caucao",
        "motivo_encerramento",
    ):
        if linha[campo] is None:
            linha[campo] = ""

    return linha


def procurar_ocupacao_mensal(ocupacao_id):
    """Procura os dados específicos do contrato mensal pelo id da
    ocupação. Devolve None se não existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM ocupacoes_mensal WHERE ocupacao_id = %s",
            (ocupacao_id,),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_ocupacao_mensal(linha)

    return linha


def atualizar_ocupacao_mensal(ocupacao_id, campos):
    """Atualiza os campos indicados de `ocupacoes_mensal`. Converte
    "" para NULL em 'responsavel_desconto_renda_id' quando presente
    nos campos — é FK para `responsaveis`, e "" não é um id válido
    (mesmo caso já resolvido em `inserir_cliente`).
    """
    if not campos:
        return

    campos = dict(campos)

    if "responsavel_desconto_renda_id" in campos:
        campos["responsavel_desconto_renda_id"] = (
            campos["responsavel_desconto_renda_id"] or None
        )

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [ocupacao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE ocupacoes_mensal SET {colunas} WHERE ocupacao_id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()


# --- ocupacoes_airbnb (especialização 1:1 da reserva Airbnb) ----------


def inserir_ocupacao_airbnb(airbnb):
    """Insere os dados específicos de uma reserva Airbnb.

    'responsavel_desconto_preco_id' e 'responsavel_desconto_multa_id'
    são FK para `responsaveis` e ficam NULL quando vierem "" (mesmo
    caso de `inserir_ocupacao_mensal`). 'hora_chegada' é TIME na
    base — "" também vira NULL, e um valor "HH:MM" é aceite tal
    qual pelo conetor.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO ocupacoes_airbnb (ocupacao_id, preco_calculado, "
            "preco_praticado, responsavel_desconto_preco_id, "
            "check_in_tardio, hora_chegada, multa_calculada, "
            "multa_praticada, responsavel_desconto_multa_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                airbnb["ocupacao_id"],
                airbnb["preco_calculado"],
                airbnb["preco_praticado"],
                airbnb["responsavel_desconto_preco_id"] or None,
                airbnb["check_in_tardio"],
                airbnb["hora_chegada"] or None,
                airbnb["multa_calculada"],
                airbnb["multa_praticada"],
                airbnb["responsavel_desconto_multa_id"] or None,
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_ocupacao_airbnb(linha):
    """Converte BOOLEAN para bool, TIME (o conetor devolve
    `datetime.timedelta`, nunca texto) de volta para "HH:MM", e as
    duas FK de responsável — mais 'motivo_cancelamento' — de NULL
    para "" quando vazias.
    """
    linha["check_in_tardio"] = bool(linha["check_in_tardio"])

    hora_chegada = linha["hora_chegada"]

    if hora_chegada is None:
        linha["hora_chegada"] = ""
    else:
        total_segundos = int(hora_chegada.total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos = resto // 60
        linha["hora_chegada"] = f"{horas:02d}:{minutos:02d}"

    for campo in (
        "responsavel_desconto_preco_id",
        "responsavel_desconto_multa_id",
        "motivo_cancelamento",
    ):
        if linha[campo] is None:
            linha[campo] = ""

    return linha


def procurar_ocupacao_airbnb(ocupacao_id):
    """Procura os dados específicos da reserva Airbnb pelo id da
    ocupação. Devolve None se não existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM ocupacoes_airbnb WHERE ocupacao_id = %s",
            (ocupacao_id,),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_ocupacao_airbnb(linha)

    return linha


def atualizar_ocupacao_airbnb(ocupacao_id, campos):
    """Atualiza os campos indicados de `ocupacoes_airbnb`. Converte
    "" para NULL nas duas FK de responsável quando presentes nos
    campos — mesma razão de `atualizar_ocupacao_mensal`.
    """
    if not campos:
        return

    campos = dict(campos)

    for campo_fk in (
        "responsavel_desconto_preco_id",
        "responsavel_desconto_multa_id",
    ):
        if campo_fk in campos:
            campos[campo_fk] = campos[campo_fk] or None

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [ocupacao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE ocupacoes_airbnb SET {colunas} WHERE ocupacao_id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()
