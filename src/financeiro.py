"""Relatório financeiro — motor de cálculo puro (v1.5.0).

Módulo de LEITURA. Não escreve nada na base de dados — nem cria
tabelas, nem faz INSERT/UPDATE. Só lê o que já existe, soma, e
devolve números. Não tem GUI, não tem ecrã, não entra no
ITENS_MENU do `app.py`. Quem consome este motor é o
`relatorios.py` (o 4.º e último módulo da v1.5.0), que trata da
apresentação — tabelas, gráficos, exportação.

O relatório é o "Opção 1" definido no handoff original:
um número final só.

    Receita − Descontos − Custos = Resultado Líquido

O utilizador não vê COGS e despesas operacionais separados — as
duas origens continuam distintas na base de dados, mas somam-se
no mesmo número final. Nesta versão, o COGS nem sequer entra no
resultado: aparece à parte, em quantidade (ver abaixo).

DECISÕES DE NEGÓCIO (fechadas na sessão de 19/09/2026):

  - Receita mensal: todos os meses de vigência dentro do
    período × `renda_praticada`. Um contrato que atravessa o
    período conta uma vez por cada mês em que vigorou.
  - Receita airbnb: rateio por noites — `preco_praticado ×
    (noites no período / noites totais)`.
  - Descontos: calculado − praticado, com o mesmo rateio da
    receita (mensal = meses × (renda_calculada −
    renda_praticada); airbnb = rateio × (preco_calculado −
    preco_praticado) + rateio × (multa_calculada −
    multa_praticada)).
  - Mês parcial conta como mês inteiro se o contrato vigorou em
    qualquer dia desse mês. Sem rateio de dias, sem
    arredondamentos.
  - Despesas operacionais: só `estado="paga"`, agregadas por
    `data_pagamento`. As `pendente` e `cancelada` não entram,
    nem as vencidas — o lado da despesa é fluxo de caixa.
  - COGS: saídas (`tipo="saida"`) menos entradas de devolução
    (`tipo="entrada"` com `requisicao_id` preenchido), pela
    `data` do movimento. Reportado em QUANTIDADE, à parte do
    resultado — não soma ao Resultado Líquido (a tabela
    `produtos` não tem preço unitário; ver handoff, Ponto 5.1,
    opção c).
  - Âmbito: todas as ocupações que tenham vigorado dentro do
    período, ativas ou encerradas/canceladas. Um relatório
    histórico não muda conforme as ocupações vão encerrando.
  - API: funções por eixo (`receita_por_unidade`,
    `receita_por_propriedade`, `despesas_por_categoria`,
    `cogs_por_produto`) mais a função agregada `resultado`. O
    `relatorios.py` consome o que quiser.

COMO SE MEDE "MESES DE VIGÊNCIA" (mensal):

    Um mês conta como inteiro se o contrato vigorou em QUALQUER
    dia desse mês. Um contrato que acaba a 15 de junho conta
    junho todo; um que começa a 20 de junho também conta junho
    todo. A renda é mensal, paga-se por mês — não por dia.

    A contagem faz-se pelo par (ano, mês), nunca por aritmética
    de dias. Percorre-se cada mês do período e testa-se, mês a
    mês, se o contrato o tocou.

ESTRUTURA:

    Bloco 1 (este ficheiro, secção atual): cabeçalho, imports,
        constantes, helpers internos.
    Bloco 2: funções de agregação por eixo (receita, descontos,
        despesas, COGS).
    Bloco 3: função agregada `resultado`.

Este módulo não acede a ficheiros nem à interface. Fala com o
`repositorio` (BD) e com os módulos de negócio que já existem
(`contratos`, `despesas`, `estoque`, `unidades`,
`propriedades`). Devolve dicionários/listas e sinaliza erro com
`raise ValueError`.
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal

import despesas
import estoque
import repositorio
import unidades


# =====================================================================
# CONSTANTES
# =====================================================================

# Tipos de ocupação. Reutilizadas do `validacoes.TIPOS_UNIDADE`
# (mensal/airbnb) — não se importa `validacoes` só para isto,
# porque o motor não valida nada do que lê.
_TIPO_MENSAL = "mensal"
_TIPO_AIRBNB = "airbnb"

# Tipos de movimento de stock relevantes para o COGS.
_TIPO_SAIDA = "saida"
_TIPO_ENTRADA = "entrada"

# Estado da despesa que conta para o resultado.
_ESTADO_PAGA = "paga"


# =====================================================================
# HELPERS INTERNOS
# =====================================================================


def _validar_periodo(data_inicio, data_fim):
    """Confirma que o período é coerente antes de qualquer cálculo.

    Um período válido tem data_inicio e data_fim preenchidos, ambos
    `date`, e data_fim posterior a data_inicio. Lança ValueError
    caso contrário — mesma convenção de `validacoes.validar_intervalo`,
    mas sem o import (o motor não valida formulários, valida só o
    seu próprio contrato de entrada).

    A unidade de contagem é a noite/dia: um período com o mesmo dia
    de início e fim não contém nenhum. Não há aqui noção de
    "período de um dia" — quem quer um dia, passa o dia seguinte
    como fim.
    """
    if data_inicio is None:
        raise ValueError("A data de início do período é obrigatória.")

    if data_fim is None:
        raise ValueError("A data de fim do período é obrigatória.")

    if not isinstance(data_inicio, date) or not isinstance(data_fim, date):
        raise ValueError(
            "As datas do período têm de ser objetos `date`."
        )

    if data_fim <= data_inicio:
        raise ValueError(
            "A data de fim do período tem de ser posterior à data "
            "de início."
        )


def _meses_do_periodo(data_inicio, data_fim):
    """Devolve a lista de pares (ano, mês) que o período atravessa,
    do primeiro ao último, inclusive.

    Um período de 2026-06-15 a 2026-08-02 devolve
    [(2026, 6), (2026, 7), (2026, 8)].

    Um período de 2026-06-01 a 2026-06-30 devolve [(2026, 6)].

    A lista é a unidade de contagem do lado mensal: para cada mês
    desta lista, testa-se se o contrato o tocou (ver
    `_meses_de_vigencia_no_periodo`).
    """
    meses = []
    ano, mes = data_inicio.year, data_inicio.month
    ano_fim, mes_fim = data_fim.year, data_fim.month

    while (ano, mes) <= (ano_fim, mes_fim):
        meses.append((ano, mes))

        if mes == 12:
            ano += 1
            mes = 1
        else:
            mes += 1

    return meses


def _primeiro_dia_do_mes(ano, mes):
    """Devolve o `date` do dia 1 do mês indicado."""
    return date(ano, mes, 1)


def _ultimo_dia_do_mes(ano, mes):
    """Devolve o `date` do último dia do mês indicado.

    Usa `calendar.monthrange`, que já sabe quantos dias tem cada
    mês, incluindo fevereiro em ano bissexto — não se reimplementa
    a regra dos anos bissextos.
    """
    return date(ano, mes, monthrange(ano, mes)[1])


def _mes_de(data):
    """Devolve o par (ano, mês) de uma `date` — mesma função que
    `despesas._mes_de` faz do lado das despesas. Duplicada aqui
    porque é um helper de uma linha e importar `despesas` só para
    isto não se justifica.
    """
    return (data.year, data.month)


def _mes_tocado_pela_ocupacao(ocupacao, ano, mes):
    """Diz se uma ocupação tocou o mês indicado.

    Regra de sobreposição, mês a mês: a ocupação tocou o mês se
    começou antes do fim do mês E (não tem data_fim OU a data_fim
    é depois do início do mês).

    Um contrato mensal em vigor (data_fim = None) toca todos os
    meses a partir do seu data_inicio. Um contrato encerrado toca
    os meses entre data_inicio e data_fim, inclusive os parciais.

    Esta é a mesma fórmula de sobreposição usada em
    `contratos._sobrepoe` e no filtro de datas do
    `repositorio.listar_ocupacoes` — coerência interna, não
    coincidência.
    """
    inicio_mes = _primeiro_dia_do_mes(ano, mes)
    fim_mes = _ultimo_dia_do_mes(ano, mes)

    if ocupacao["data_inicio"] > fim_mes:
        return False

    if ocupacao["data_fim"] is not None and ocupacao["data_fim"] <= inicio_mes:
        return False

    return True


def _meses_de_vigencia_no_periodo(ocupacao, meses):
    """Conta quantos meses da lista `meses` a ocupação tocou.

    `meses` é a lista de pares (ano, mês) devolvida por
    `_meses_do_periodo`. Devolve um inteiro — o número de meses
    que contam para a receita desta ocupação no período.

    Zero significa que a ocupação não tocou o período (não devia
    acontecer se veio do filtro de sobreposição do repositório,
    mas protege-se contra chamadas diretas).
    """
    total = 0

    for ano, mes in meses:
        if _mes_tocado_pela_ocupacao(ocupacao, ano, mes):
            total += 1

    return total


def _noites_totais(ocupacao):
    """Número total de noites de uma ocupação airbnb.

    Uma noite é o intervalo [data_inicio, data_fim) — o dia de
    saída não é uma noite ocupada, mesma convenção de
    `contratos._sobrepoe` e de `validacoes.validar_intervalo`.

    Devolve 0 se a ocupação não tiver data_fim (não devia
    acontecer numa airbnb — a data_fim é obrigatória na criação,
    ver `contratos.registar_airbnb`).
    """
    if ocupacao["data_fim"] is None:
        return 0

    return (ocupacao["data_fim"] - ocupacao["data_inicio"]).days


def _noites_no_periodo(ocupacao, data_inicio, data_fim):
    """Número de noites de uma ocupação airbnb que caem dentro do
    período [data_inicio, data_fim).

    Calcula-se pela interseção dos dois intervalos:

        noites = (min(fim_ocupacao, fim_periodo)
                  − max(inicio_ocupacao, inicio_periodo)).days

    Se a interseção for negativa ou nula, devolve 0. O período
    filtra-se também por [inicio, fim) — o dia de fim do período
    não conta como noite.
    """
    if ocupacao["data_fim"] is None:
        return 0

    inicio_intersecao = max(ocupacao["data_inicio"], data_inicio)
    fim_intersecao = min(ocupacao["data_fim"], data_fim)

    if fim_intersecao <= inicio_intersecao:
        return 0

    return (fim_intersecao - inicio_intersecao).days


def _ratear(valor, parte, total):
    """Devolve `valor × (parte / total)`, arredondado a 2 casas
    decimais com a regra bancária do Decimal.

    Usado para ratear preços de airbnb e multas pelas noites do
    período. Se `total` for 0, devolve Decimal("0.00") — evita
    divisão por zero e devolve o neutro para a soma.

    O arredondamento faz-se por linha, não no fim: cada ocupação
    contribui com um valor já arredondado, e a soma final pode
    ter diferenças de cêntimo face a um cálculo em precisão
    infinita. É aceitável — mesma convenção de
    `despesas.dividir_despesa_por_propriedade`.
    """
    if total == 0:
        return Decimal("0.00")

    return (valor * Decimal(parte) / Decimal(total)).quantize(
        Decimal("0.01")
    )


def _listar_ocupacoes_do_periodo(data_inicio, data_fim, tipo=None):
    """Wrapper sobre `repositorio.listar_ocupacoes` que garante as
    duas coisas de que o motor precisa: ocupações inativas
    incluídas (o relatório é histórico) e filtro de sobreposição
    pelo período.

    Centraliza esta chamada para não se repetir em cada função de
    agregação — se um dia a assinatura do repositório mudar, muda
    só aqui.
    """
    return repositorio.listar_ocupacoes(
        incluir_inativas=True,
        tipo=tipo,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

# =====================================================================
# BLOCO 2 — AGREGAÇÕES POR EIXO
# =====================================================================


def _valores_da_ocupacao_no_periodo(
    ocupacao, meses, data_inicio, data_fim, mensal, airbnb
):
    """Devolve o par `(receita, desconto)` de uma ocupação no
    período, já arredondado a 2 casas.

    Função central do motor: é aqui que se decide quanto é que
    uma ocupação contribuiu para o período. Todas as agregações
    de receita e desconto passam por aqui.

    `mensal` e `airbnb` são os detalhes específicos do regime,
    já lidos (o chamador passa-os para não obrigar esta função a
    ir à base de dados). Um dos dois é sempre None — o outro é o
    detalhe da ocupação.

    Lógica por regime:

      - Mensal: `receita = meses_vigorados × renda_praticada`,
        `desconto = meses_vigorados × (renda_calculada −
        renda_praticada)`. `meses_vigorados` é o que
        `_meses_de_vigencia_no_periodo` devolveu.

      - Airbnb: `receita = ratear(preco_praticado,
        noites_no_periodo, noites_totais)`,
        `desconto = ratear(preco_calculado − preco_praticado,
        ...) + ratear(multa_calculada − multa_praticada, ...)`.

    Devolve `(Decimal("0.00"), Decimal("0.00"))` se a ocupação
    não tocou o período em nenhuma das suas noites/meses — não
    devia acontecer se veio do filtro do repositório, mas
    protege-se contra chamadas diretas.
    """
    if ocupacao["tipo"] == _TIPO_MENSAL:
        meses_vigorados = _meses_de_vigencia_no_periodo(ocupacao, meses)

        if meses_vigorados == 0:
            return Decimal("0.00"), Decimal("0.00")

        receita = mensal["renda_praticada"] * meses_vigorados
        desconto = (
            mensal["renda_calculada"] - mensal["renda_praticada"]
        ) * meses_vigorados

        return (
            receita.quantize(Decimal("0.01")),
            desconto.quantize(Decimal("0.01")),
        )

    # Airbnb
    noites_totais = _noites_totais(ocupacao)
    noites_periodo = _noites_no_periodo(ocupacao, data_inicio, data_fim)

    if noites_totais == 0 or noites_periodo == 0:
        return Decimal("0.00"), Decimal("0.00")

    receita = _ratear(
        airbnb["preco_praticado"], noites_periodo, noites_totais
    )

    desconto = _ratear(
        airbnb["preco_calculado"] - airbnb["preco_praticado"],
        noites_periodo,
        noites_totais,
    ) + _ratear(
        airbnb["multa_calculada"] - airbnb["multa_praticada"],
        noites_periodo,
        noites_totais,
    )

    return receita, desconto


def _detalhes_da_ocupacao(ocupacao):
    """Devolve `(mensal, airbnb)` — os dois detalhes específicos do
    regime, um deles sempre None.

    Centraliza a chamada a `contratos.detalhes_mensal` /
    `contratos.detalhes_airbnb` para o motor não ter de saber qual
    chamar. Uma ocupação de tipo "mensal" devolve o detalhe mensal
    e None; uma "airbnb" devolve None e o detalhe airbnb.

    Importa `contratos` aqui dentro, não no topo do ficheiro:
    `contratos.py` importa `unidades.py`, que importa
    `repositorio.py` — tudo cadeias que este motor já carrega no
    topo, mas importar `contratos` no topo criaria uma dependência
    circular potencial (o motor não é importado por ninguém, mas
    é boa prática isolar). Aqui dentro não há esse risco.
    """
    import contratos

    if ocupacao["tipo"] == _TIPO_MENSAL:
        return contratos.detalhes_mensal(ocupacao["id"]), None

    return None, contratos.detalhes_airbnb(ocupacao["id"])


def receita_por_unidade(data_inicio, data_fim):
    """Devolve a receita e o desconto de cada unidade no período.

    Cada elemento da lista devolvida é um dicionário:

        {
            "unidade_id": "UNI-001",
            "receita": Decimal(...),
            "desconto": Decimal(...),
        }

    Só entram unidades com receita ou desconto não nulos — uma
    unidade sem ocupações no período não aparece na lista.
    Ordenada por `unidade_id`.

    O cálculo passa todo por `_valores_da_ocupacao_no_periodo`.
    Esta função só lê as ocupações, lê os detalhes de cada uma, e
    acumula por unidade.
    """
    _validar_periodo(data_inicio, data_fim)
    meses = _meses_do_periodo(data_inicio, data_fim)

    ocupacoes = _listar_ocupacoes_do_periodo(data_inicio, data_fim)

    por_unidade = {}

    for ocupacao in ocupacoes:
        mensal, airbnb = _detalhes_da_ocupacao(ocupacao)

        if mensal is None and airbnb is None:
            # Inconsistência nos dados — ocupação sem detalhe.
            # Salta-se em vez de rebentar: um registo corrompido
            # não devia travar o relatório inteiro.
            continue

        receita, desconto = _valores_da_ocupacao_no_periodo(
            ocupacao, meses, data_inicio, data_fim, mensal, airbnb
        )

        if receita == 0 and desconto == 0:
            continue

        acumulado = por_unidade.setdefault(
            ocupacao["unidade_id"],
            {"unidade_id": ocupacao["unidade_id"], "receita": Decimal("0.00"),
             "desconto": Decimal("0.00")},
        )
        acumulado["receita"] += receita
        acumulado["desconto"] += desconto

    return sorted(por_unidade.values(), key=lambda d: d["unidade_id"])


def receita_por_propriedade(data_inicio, data_fim):
    """Devolve a receita e o desconto de cada propriedade no
    período, agregando as suas unidades.

    Cada elemento:

        {
            "propriedade_id": "PRO-001",
            "propriedade_nome": "...",
            "receita": Decimal(...),
            "desconto": Decimal(...),
        }

    Não duplica o cálculo — chama `receita_por_unidade` e agrupa
    por propriedade. Uma propriedade sem receita nem desconto não
    aparece.

    O nome da propriedade vem de `repositorio.procurar_propriedade`
    para evitar que o consumidor tenha de o ir buscar à parte.
    Ordenada por `propriedade_id`.
    """
    _validar_periodo(data_inicio, data_fim)

    por_unidade = receita_por_unidade(data_inicio, data_fim)

    por_propriedade = {}

    for item in por_unidade:
        unidade = repositorio.procurar_unidade(item["unidade_id"])

        if unidade is None:
            # Unidade desapareceu da base? Não devia acontecer (o
            # sistema não apaga unidades a sério), mas salta-se em
            # vez de rebentar.
            continue

        propriedade_id = unidade["propriedade_id"]

        if propriedade_id not in por_propriedade:
            propriedade = repositorio.procurar_propriedade(propriedade_id)
            nome = propriedade["nome"] if propriedade else propriedade_id

            por_propriedade[propriedade_id] = {
                "propriedade_id": propriedade_id,
                "propriedade_nome": nome,
                "receita": Decimal("0.00"),
                "desconto": Decimal("0.00"),
            }

        por_propriedade[propriedade_id]["receita"] += item["receita"]
        por_propriedade[propriedade_id]["desconto"] += item["desconto"]

    return sorted(
        por_propriedade.values(), key=lambda d: d["propriedade_id"]
    )


def despesas_por_categoria(data_inicio, data_fim):
    """Devolve as despesas operacionais pagas no período, agrupadas
    por categoria.

    Cada elemento:

        {
            "categoria_id": "CAT-001",
            "categoria_nome": "...",
            "total": Decimal(...),
        }

    Só entram despesas com `estado="paga"` — mesma decisão de
    fluxo de caixa do `resultado`. A agregação é por
    `data_pagamento`, dentro do período.

    Uma categoria sem despesas pagas no período não aparece.
    Ordenada por `categoria_id`.

    O nome da categoria vem de `despesas.procurar_categoria` —
    fala-se com o módulo de negócio das despesas, não com o
    repositório diretamente, porque é ali que a leitura está
    definida.
    """
    _validar_periodo(data_inicio, data_fim)

    despesas_pagas = despesas.listar_despesas(estado=_ESTADO_PAGA)

    por_categoria = {}

    for despesa in despesas_pagas:
        if despesa["data_pagamento"] is None:
            # Uma despesa paga sem data de pagamento não devia
            # existir — a `marcar_paga` exige-a. Salta-se em vez
            # de rebentar.
            continue

        if not (data_inicio <= despesa["data_pagamento"] < data_fim):
            continue

        categoria_id = despesa["categoria_id"]

        if categoria_id not in por_categoria:
            categoria = despesas.procurar_categoria(categoria_id)
            nome = categoria["nome"] if categoria else categoria_id

            por_categoria[categoria_id] = {
                "categoria_id": categoria_id,
                "categoria_nome": nome,
                "total": Decimal("0.00"),
            }

        por_categoria[categoria_id]["total"] += despesa["valor"]

    return sorted(
        por_categoria.values(), key=lambda d: d["categoria_id"]
    )


def cogs_por_produto(data_inicio, data_fim):
    """Devolve o COGS em quantidade, por produto, no período.

    Cada elemento:

        {
            "produto_id": "PRD-001",
            "produto_nome": "...",
            "quantidade": 12,
        }

    COGS = saídas (`tipo="saida"`) menos entradas de devolução
    (`tipo="entrada"` com `requisicao_id` preenchido). A conta é
    feita por produto — uma entrada de devolução só abate o COGS
    do produto a que se refere.

    A data considerada é a `data` do movimento. Movimentos sem
    essa data não existem (a coluna é NOT NULL na base).

    Um produto sem movimentos no período não aparece. Produtos
    com quantidade final zero (saídas totalmente devolvidas) não
    aparecem — o COGS líquido é zero.

    Ordenada por `produto_id`.
    """
    _validar_periodo(data_inicio, data_fim)

    movimentos = estoque.listar_movimentos()

    # Soma as saídas e subtrai as entradas de devolução. Um
    # dicionário por produto com a quantidade acumulada.
    por_produto = {}

    for movimento in movimentos:
        if not (data_inicio <= movimento["data"] < data_fim):
            continue

        produto_id = movimento["produto_id"]

        if movimento["tipo"] == _TIPO_SAIDA:
            por_produto[produto_id] = (
                por_produto.get(produto_id, 0) + movimento["quantidade"]
            )
            continue

        if (
            movimento["tipo"] == _TIPO_ENTRADA
            and movimento["requisicao_id"]
        ):
            # Entrada de devolução — abate o COGS do produto.
            por_produto[produto_id] = (
                por_produto.get(produto_id, 0) - movimento["quantidade"]
            )

    # Constrói a lista final, saltando os que ficaram a zero.
    resultado = []

    for produto_id, quantidade in por_produto.items():
        if quantidade == 0:
            continue

        produto = estoque.procurar_produto(produto_id)
        nome = produto["nome"] if produto else produto_id

        resultado.append(
            {
                "produto_id": produto_id,
                "produto_nome": nome,
                "quantidade": quantidade,
            }
        )

    return sorted(resultado, key=lambda d: d["produto_id"])

# =====================================================================
# BLOCO 3 — RESULTADO AGREGADO
# =====================================================================


def resultado(data_inicio, data_fim):
    """Devolve o resultado financeiro do período — a "Opção 1" do
    handoff original, num só dicionário.

    A estrutura devolvida:

        {
            "receita": Decimal(...),           # mensal + airbnb
            "descontos": Decimal(...),          # mensal + airbnb
            "despesas_operacionais": Decimal(...),
            "resultado_liquido": Decimal(...),  # receita − descontos − despesas
            "cogs_quantidade": int,             # NÃO entra no resultado
        }

    COGS fica fora do cálculo do resultado — é reportado em
    quantidade, à parte, porque a tabela `produtos` não tem preço
    unitário e o COGS em euros não é calculável (decisão da sessão
    de 19/09/2026, opção c do handoff, Ponto 5.1). O utilizador
    vê os quatro números monetários e, ao lado, o COGS
    informativo.

    O cálculo não duplica nada — chama as agregações do Bloco 2
    e soma:

      - Receita = soma de `receita` de `receita_por_unidade`.
      - Descontos = soma de `desconto` de `receita_por_unidade`.
      - Despesas operacionais = soma de `total` de
        `despesas_por_categoria`.
      - COGS em quantidade = soma de `quantidade` de
        `cogs_por_produto`.

    Não há aqui rateio nem regra de negócio nova: se uma regra
    mudar, muda nas funções do Bloco 2 e esta herda. É
    deliberado — uma só fonte de verdade para cada número.

    O resultado líquido pode ser negativo (despesas superiores à
    receita) — devolve-se o valor com o sinal, o consumidor é
    que decide como o apresentar.
    """
    _validar_periodo(data_inicio, data_fim)

    por_unidade = receita_por_unidade(data_inicio, data_fim)

    receita = Decimal("0.00")
    descontos = Decimal("0.00")

    for item in por_unidade:
        receita += item["receita"]
        descontos += item["desconto"]

    por_categoria = despesas_por_categoria(data_inicio, data_fim)

    despesas_operacionais = Decimal("0.00")

    for item in por_categoria:
        despesas_operacionais += item["total"]

    por_produto = cogs_por_produto(data_inicio, data_fim)

    cogs_quantidade = sum(item["quantidade"] for item in por_produto)

    resultado_liquido = receita - descontos - despesas_operacionais

    return {
        "receita": receita,
        "descontos": descontos,
        "despesas_operacionais": despesas_operacionais,
        "resultado_liquido": resultado_liquido,
        "cogs_quantidade": cogs_quantidade,
    }