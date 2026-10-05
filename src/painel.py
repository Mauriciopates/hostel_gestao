"""Painel — os números e as listas do Dashboard (v1.6.0).

Módulo de LEITURA, igual em espírito ao `financeiro.py`: não grava
nada, não tem GUI, não fala com o `repositorio` diretamente. Junta o
que os outros módulos de negócio já sabem responder e devolve tudo
pronto a mostrar, para as três vistas do Dashboard:

- Hoje (Master/Admin): `kpis_hoje`, `movimento_do_dia`, `limpezas`,
  `proximos_dias`, `alertas`.
- Financeiro (Master/Admin): `periodo_do_mes`, `mes_anterior`,
  `resumo_financeiro`, `evolucao_mensal`, `rendas_a_vencer`.
- Staff: `limpezas` (filtrada pelo staff), `requisicoes_do_staff`,
  `stock_disponivel`.

Porque existe (decisão de 27/09/2026, ao aprovar os mockups): o
Dashboard antigo fazia as contas dentro da própria GUI
(`_kpis`, `_alertas`). Aqui ficam testáveis com `unittest`, sem
abrir janela nenhuma, e a GUI só desenha.

Regras de negócio fechadas com o aluno (27/09/2026):

- LIMPEZA = uma SAÍDA (mensal ou Airbnb) nesse dia. Fica "urgente"
  quando a mesma unidade tem uma entrada Airbnb nesse dia ou no
  seguinte — há um hóspede a caminho.
- O staff de uma unidade vem da atribuição responsável-unidade
  (`unidades.unidades_geridas_por`); só contam responsáveis ATIVOS
  do tipo "Staff" — a mesma regra do `estoque._dono_do_rol`.
- "Requisições a confirmar" do Staff = as dele em estado "enviada"
  (o stock já saiu do armazém e falta ele confirmar a receção).
- Os perfis que veem cada alerta decidem-se AQUI, não na GUI.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

import clientes
import contratos
import estoque
import financeiro
import prechecking
import responsaveis
import unidades

# Perfis — as mesmas strings de `responsaveis.tipo_utilizador`.
_GESTAO = ("Master", "Admin")
_TODOS = ("Master", "Admin", "Staff")

# Nomes curtos dos meses, para os rótulos do gráfico. Não se usa
# `strftime("%b")`: sem locale PT dá inglês (mesma razão dos dias da
# semana no `gui_calendario.py`).
NOMES_MESES = (
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
)

NOMES_DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")

# Quantos produtos se nomeiam no detalhe do alerta de stock; os
# restantes resumem-se em "e mais N".
_PRODUTOS_NO_DETALHE = 2


# =====================================================================
# Auxiliares — mapas de nomes, carregados uma vez por chamada
# =====================================================================


def _rotulos_unidades():
    """{unidade_id: "Propriedade · Unidade"} de todas as unidades.

    Inclui as inativas: uma ocupação antiga pode apontar para uma
    unidade entretanto desativada, e o nome tem de continuar a sair.
    Uma consulta só, em vez de uma por linha.
    """
    return {
        u["id"]: f"{u['propriedade_nome']} · {u['nome']}"
        for u in unidades.listar_com_propriedade(incluir_inativas=True)
    }


def _nomes_clientes():
    """{cliente_id: nome} de todos os clientes (incluindo inativos)."""
    return {
        c["id"]: c["nome"]
        for c in clientes.listar(incluir_inativos=True)
    }


def staff_por_unidade():
    """{unidade_id: [nomes do staff]} — quem limpa cada unidade.

    Só responsáveis ativos do tipo "Staff". Uma unidade sem ninguém
    não aparece no dicionário (quem consulta usa `.get(id, [])`).
    """
    mapa = {}

    for responsavel in responsaveis.listar():
        if responsavel.get("tipo_utilizador") != "Staff":
            continue

        for unidade in unidades.unidades_geridas_por(responsavel["id"]):
            mapa.setdefault(unidade["id"], []).append(responsavel["nome"])

    return mapa


def _noites(ocupacao):
    """Noites de uma ocupação, ou None se não tiver data de fim."""
    if ocupacao["data_fim"] is None:
        return None

    return (ocupacao["data_fim"] - ocupacao["data_inicio"]).days


def _linha_ocupacao(ocupacao, rotulos, nomes):
    """Converte uma ocupação numa linha pronta a mostrar."""
    return {
        "ocupacao_id": ocupacao["id"],
        "tipo": ocupacao["tipo"],
        "unidade_id": ocupacao["unidade_id"],
        "unidade": rotulos.get(
            ocupacao["unidade_id"], ocupacao["unidade_id"]
        ),
        "cliente": nomes.get(ocupacao["cliente_id"], ocupacao["cliente_id"]),
        "data_inicio": ocupacao["data_inicio"],
        "data_fim": ocupacao["data_fim"],
        "noites": _noites(ocupacao),
    }


# =====================================================================
# Vista "Hoje"
# =====================================================================


def kpis_hoje(data):
    """Os quatro números do topo da vista Hoje.

    Devolve:

        {
            "airbnb": (unidades ocupadas, unidades em oferta),
            "mensal": (lugares ocupados, lugares em oferta),
            "entradas": {"airbnb": n, "mensal": n},
            "saidas": {"airbnb": n, "mensal": n},
        }

    Ocupação vem de `unidades.taxa_ocupacao` (a mesma regra do
    Dashboard antigo). Entradas e saídas contam as ocupações ativas
    com `data_inicio`/`data_fim` nesse dia, separadas por regime.
    """
    entradas = {"airbnb": 0, "mensal": 0}
    saidas = {"airbnb": 0, "mensal": 0}

    for ocupacao in contratos.listar():
        if ocupacao["data_inicio"] == data:
            entradas[ocupacao["tipo"]] += 1

        if ocupacao["data_fim"] == data:
            saidas[ocupacao["tipo"]] += 1

    return {
        "airbnb": unidades.taxa_ocupacao(data, tipo="airbnb"),
        "mensal": unidades.taxa_ocupacao(data, tipo="mensal"),
        "entradas": entradas,
        "saidas": saidas,
    }


def movimento_do_dia(data):
    """Entradas e saídas de um dia, com nomes já resolvidos.

    Devolve `{"entradas": [...], "saidas": [...]}`; cada linha tem
    ocupacao_id, tipo, unidade_id, unidade ("Propriedade ·
    Unidade"), cliente, data_inicio, data_fim e noites (None num
    mensal sem fim). Ordenadas pelo nome da unidade.
    """
    rotulos = _rotulos_unidades()
    nomes = _nomes_clientes()

    entradas = []
    saidas = []

    for ocupacao in contratos.listar():
        if ocupacao["data_inicio"] == data:
            entradas.append(_linha_ocupacao(ocupacao, rotulos, nomes))

        if ocupacao["data_fim"] == data:
            saidas.append(_linha_ocupacao(ocupacao, rotulos, nomes))

    entradas.sort(key=lambda linha: linha["unidade"])
    saidas.sort(key=lambda linha: linha["unidade"])

    return {"entradas": entradas, "saidas": saidas}


def limpezas(data_inicio, dias=1, responsavel_id=None):
    """Limpezas a fazer entre `data_inicio` e os `dias` seguintes.

    Uma limpeza é uma SAÍDA (mensal ou Airbnb) nesse intervalo.
    `dias=1` é só o dia pedido; `dias=2` é esse dia e o seguinte.

    Com `responsavel_id`, só as unidades que esse responsável gere
    (é a lista "As minhas limpezas" do Staff). Sem ele, todas — e
    cada linha diz quem é o staff da unidade (lista vazia = "por
    atribuir").

    Cada elemento é a linha de `movimento_do_dia` mais:

    - "data": o dia da limpeza.
    - "staff": nomes do staff da unidade.
    - "proxima_entrada": data da próxima entrada Airbnb na unidade
      a partir desse dia, ou None.
    - "urgente": True se essa próxima entrada é no próprio dia ou
      no seguinte.

    Ordenadas por data, depois urgentes primeiro, depois unidade.
    """
    if dias < 1:
        raise ValueError("O número de dias tem de ser pelo menos 1.")

    data_fim = data_inicio + timedelta(days=dias)
    ocupacoes = contratos.listar()

    geridas = None
    if responsavel_id is not None:
        geridas = {
            u["id"] for u in unidades.unidades_geridas_por(responsavel_id)
        }

    rotulos = _rotulos_unidades()
    nomes = _nomes_clientes()
    staff = staff_por_unidade()

    # Entradas Airbnb por unidade — para saber se há hóspede a
    # caminho depois de cada saída.
    entradas_airbnb = {}
    for ocupacao in ocupacoes:
        if ocupacao["tipo"] == "airbnb":
            entradas_airbnb.setdefault(ocupacao["unidade_id"], []).append(
                ocupacao["data_inicio"]
            )

    resultado = []

    for ocupacao in ocupacoes:
        dia = ocupacao["data_fim"]

        if dia is None or not (data_inicio <= dia < data_fim):
            continue

        if geridas is not None and ocupacao["unidade_id"] not in geridas:
            continue

        futuras = [
            d for d in entradas_airbnb.get(ocupacao["unidade_id"], [])
            if d >= dia
        ]
        proxima = min(futuras) if futuras else None

        linha = _linha_ocupacao(ocupacao, rotulos, nomes)
        linha["data"] = dia
        linha["staff"] = staff.get(ocupacao["unidade_id"], [])
        linha["proxima_entrada"] = proxima
        linha["urgente"] = (
            proxima is not None and proxima <= dia + timedelta(days=1)
        )
        resultado.append(linha)

    resultado.sort(
        key=lambda linha: (
            linha["data"], not linha["urgente"], linha["unidade"]
        )
    )

    return resultado


def proximos_dias(data, dias=3):
    """Resumo dos `dias` seguintes a `data` (sem contar `data`).

    Cada elemento: {"data", "entradas", "saidas", "saidas_mensal"}.
    Os dias sem movimento também aparecem, com zeros — um dia
    calmo também é informação.
    """
    ocupacoes = contratos.listar()
    resumo = []

    for deslocamento in range(1, dias + 1):
        dia = data + timedelta(days=deslocamento)
        entradas = sum(1 for o in ocupacoes if o["data_inicio"] == dia)
        saidas = [o for o in ocupacoes if o["data_fim"] == dia]

        resumo.append(
            {
                "data": dia,
                "entradas": entradas,
                "saidas": len(saidas),
                "saidas_mensal": sum(
                    1 for o in saidas if o["tipo"] == "mensal"
                ),
            }
        )

    return resumo


def _alerta(chave, titulo, detalhe, peso, quantidade, perfis):
    return {
        "chave": chave,
        "titulo": titulo,
        "detalhe": detalhe,
        "peso": peso,
        "quantidade": quantidade,
        "perfis": perfis,
    }


def _plural(n, singular, plural):
    return singular if n == 1 else plural


def alertas(tipo_utilizador):
    """Alertas que o perfil indicado deve ver, do mais urgente para
    o menos.

    Os mesmos quatro do Dashboard antigo, agora com o detalhe, e o
    do pré check-in (F5) à cabeça:

    0. "prechecking"  — pré check-ins por validar (Master/Admin).

    1. "requisicoes"  — requisições pendentes (Master/Admin).
    2. "stock"        — produtos abaixo do mínimo (todos).
    3. "documentos"   — contratos com documento a expirar
       (Master/Admin).
    4. "clientes"     — clientes com dados incompletos
       (Master/Admin).

    Cada alerta: chave, titulo, detalhe, peso ("erro" | "aviso" |
    "info"), quantidade e perfis. Os que não têm nada a dizer não
    aparecem. Um perfil desconhecido (ou None) não vê nenhum.
    """
    lista = []

    # F5 (05/10/2026): pré check-ins enviados pelos hóspedes, por
    # validar. 0 quando a caixa de entrada não existe neste servidor.
    if tipo_utilizador in _GESTAO:
        n = prechecking.contar_pendentes()
        if n:
            lista.append(
                _alerta(
                    "prechecking",
                    f"{n} {_plural(n, 'pré check-in', 'pré check-ins')} "
                    "por validar",
                    "enviados pelos hóspedes no site",
                    "aviso",
                    n,
                    _GESTAO,
                )
            )

    if tipo_utilizador in _GESTAO:
        pendentes = estoque.listar_requisicoes(estado="pendente")
        if pendentes:
            n = len(pendentes)
            lista.append(
                _alerta(
                    "requisicoes",
                    f"{n} {_plural(n, 'requisição', 'requisições')} de "
                    f"stock {_plural(n, 'pendente', 'pendentes')}",
                    "à espera de aprovação",
                    "aviso",
                    n,
                    _GESTAO,
                )
            )

    if tipo_utilizador in _TODOS:
        abaixo = estoque.listar_alertas_stock()
        if abaixo:
            n = len(abaixo)
            nomeados = [
                f"{a['produto']['nome']} "
                f"({a['saldo']}/{a['produto']['stock_minimo']})"
                for a in abaixo[:_PRODUTOS_NO_DETALHE]
            ]
            detalhe = ", ".join(nomeados)
            if n > _PRODUTOS_NO_DETALHE:
                detalhe += f" e mais {n - _PRODUTOS_NO_DETALHE}"

            lista.append(
                _alerta(
                    "stock",
                    f"{n} {_plural(n, 'produto', 'produtos')} abaixo "
                    "do mínimo",
                    detalhe,
                    "erro",
                    n,
                    _TODOS,
                )
            )

    if tipo_utilizador in _GESTAO:
        avisos = [
            o for o in contratos.listar(aviso_documento=True)
            if o.get("ativo", True)
        ]
        if avisos:
            n = len(avisos)
            nomes = _nomes_clientes()
            primeiro = avisos[0]
            detalhe = (
                f"{primeiro['id']} · "
                f"{nomes.get(primeiro['cliente_id'], primeiro['cliente_id'])}"
            )
            if n > 1:
                detalhe += f" e mais {n - 1}"

            lista.append(
                _alerta(
                    "documentos",
                    f"{n} {_plural(n, 'contrato', 'contratos')} com "
                    "documento a expirar",
                    detalhe,
                    "aviso",
                    n,
                    _GESTAO,
                )
            )

        incompletos = clientes.listar(incompleto=True)
        if incompletos:
            n = len(incompletos)
            detalhe = incompletos[0]["nome"]
            if n > 1:
                detalhe += f" e mais {n - 1}"

            lista.append(
                _alerta(
                    "clientes",
                    f"{n} {_plural(n, 'cliente', 'clientes')} com dados "
                    "incompletos",
                    detalhe,
                    "info",
                    n,
                    _GESTAO,
                )
            )

    return lista


# =====================================================================
# Vista "Financeiro"
# =====================================================================


def periodo_do_mes(ano, mes):
    """(primeiro dia do mês, primeiro dia do mês seguinte).

    O fim é EXCLUSIVO — é o contrato de período do `financeiro.py`
    (ver `_validar_periodo`: um período com início e fim no mesmo
    dia não contém nenhum).
    """
    inicio = date(ano, mes, 1)

    if mes == 12:
        return inicio, date(ano + 1, 1, 1)

    return inicio, date(ano, mes + 1, 1)


def mes_anterior(ano, mes):
    """(ano, mes) do mês anterior."""
    if mes == 1:
        return ano - 1, 12

    return ano, mes - 1


def mes_seguinte(ano, mes):
    """(ano, mes) do mês seguinte."""
    if mes == 12:
        return ano + 1, 1

    return ano, mes + 1


def variacao_percentual(atual, anterior):
    """Variação de `anterior` para `atual`, em % inteira.

    None quando o anterior é zero — não há base de comparação, e
    "+∞%" não ajuda ninguém. Devolve int (ex.: 6 para +6%).
    """
    if not anterior:
        return None

    variacao = (Decimal(atual) - Decimal(anterior)) / Decimal(anterior)

    return int((variacao * 100).quantize(Decimal("1")))


def resumo_financeiro(ano, mes):
    """O resultado do mês e a comparação com o mês anterior.

    Devolve:

        {
            "atual": <financeiro.resultado do mês>,
            "anterior": <financeiro.resultado do mês anterior>,
            "variacao_receita": int | None,
            "variacao_despesas": int | None,
        }

    Nenhuma conta nova: é o `financeiro.resultado` duas vezes.
    """
    atual = financeiro.resultado(*periodo_do_mes(ano, mes))
    anterior = financeiro.resultado(
        *periodo_do_mes(*mes_anterior(ano, mes))
    )

    return {
        "atual": atual,
        "anterior": anterior,
        "variacao_receita": variacao_percentual(
            atual["receita"], anterior["receita"]
        ),
        "variacao_despesas": variacao_percentual(
            atual["despesas_operacionais"],
            anterior["despesas_operacionais"],
        ),
    }


def evolucao_mensal(ano, mes, meses=6):
    """Receita e despesas dos últimos `meses` meses, acabando em
    (ano, mes), do mais antigo para o mais recente.

    Cada elemento: {"ano", "mes", "rotulo", "receita", "despesas"},
    com "despesas" = despesas operacionais (o que o gráfico
    compara com a receita).
    """
    lista = []
    ano_atual, mes_atual = ano, mes

    for _ in range(meses):
        resultado = financeiro.resultado(
            *periodo_do_mes(ano_atual, mes_atual)
        )
        lista.append(
            {
                "ano": ano_atual,
                "mes": mes_atual,
                "rotulo": NOMES_MESES[mes_atual - 1],
                "receita": resultado["receita"],
                "despesas": resultado["despesas_operacionais"],
            }
        )
        ano_atual, mes_atual = mes_anterior(ano_atual, mes_atual)

    lista.reverse()

    return lista


def _data_vencimento(dia_vencimento, ano, mes):
    """O dia de vencimento nesse mês, encostado ao último dia do mês
    quando o mês é mais curto (dia 31 em fevereiro → 28/29)."""
    ultimo = calendar.monthrange(ano, mes)[1]

    return date(ano, mes, min(dia_vencimento, ultimo))


def rendas_a_vencer(data, dias=7):
    """Rendas mensais que vencem entre `data` e os `dias` seguintes
    (inclusive), ordenadas pela data.

    Para cada contrato mensal ativo, calcula a próxima data de
    vencimento a partir de `data` (este mês ou o seguinte) e fica
    com as que caem no intervalo e dentro da vigência do contrato.

    Cada elemento: {"ocupacao_id", "cliente", "unidade",
    "vencimento", "valor"} — "valor" é a `renda_praticada`.
    """
    limite = data + timedelta(days=dias)
    rotulos = _rotulos_unidades()
    nomes = _nomes_clientes()
    lista = []

    for ocupacao in contratos.listar(tipo="mensal"):
        detalhe = contratos.detalhes_mensal(ocupacao["id"])

        if detalhe is None:
            continue

        dia = int(detalhe["dia_vencimento"])
        vencimento = _data_vencimento(dia, data.year, data.month)

        if vencimento < data:
            vencimento = _data_vencimento(
                dia, *mes_seguinte(data.year, data.month)
            )

        if vencimento > limite or vencimento < ocupacao["data_inicio"]:
            continue

        if ocupacao["data_fim"] is not None and (
            vencimento > ocupacao["data_fim"]
        ):
            continue

        lista.append(
            {
                "ocupacao_id": ocupacao["id"],
                "cliente": nomes.get(
                    ocupacao["cliente_id"], ocupacao["cliente_id"]
                ),
                "unidade": rotulos.get(
                    ocupacao["unidade_id"], ocupacao["unidade_id"]
                ),
                "vencimento": vencimento,
                "valor": detalhe["renda_praticada"],
            }
        )

    lista.sort(key=lambda linha: (linha["vencimento"], linha["unidade"]))

    return lista


# =====================================================================
# Vista "Staff"
# =====================================================================


def requisicoes_do_staff(responsavel_id):
    """As requisições do próprio staff que pedem atenção.

    Devolve `{"a_confirmar": [...], "pendentes": [...]}`:

    - a_confirmar: estado "enviada" — ele tem de confirmar a
      receção.
    - pendentes: estado "pendente" — à espera de aprovação; só
      informação.

    Cada elemento é a requisição com mais "n_itens". Usa o filtro
    de visibilidade do Staff do `estoque.listar_requisicoes`, que
    força `responsavel_id = autor_id` (só as dele).
    """
    resultado = {}

    for chave, estado in (("a_confirmar", "enviada"),
                          ("pendentes", "pendente")):
        lista = []

        for requisicao in estoque.listar_requisicoes(
            estado=estado,
            tipo_utilizador_autor="Staff",
            autor_id=responsavel_id,
        ):
            linha = dict(requisicao)
            linha["n_itens"] = len(
                estoque.listar_itens_requisicao(
                    requisicao_id=requisicao["id"]
                )
            )
            lista.append(linha)

        lista.sort(key=lambda r: r["id"])
        resultado[chave] = lista

    return resultado


def stock_disponivel():
    """Saldo de cada produto ativo, do mais crítico para o menos.

    Cada elemento: {"produto", "saldo", "minimo", "abaixo",
    "proporcao"} — "proporcao" é saldo/mínimo (None quando o mínimo
    é 0) e é o que ordena: quem está mais longe do mínimo vem
    primeiro. Produtos sem mínimo vão para o fim, por nome.
    """
    lista = []

    for produto in estoque.listar_produtos():
        saldo = estoque.saldo_produto(produto["id"])
        minimo = produto["stock_minimo"]

        lista.append(
            {
                "produto": produto,
                "saldo": saldo,
                "minimo": minimo,
                "abaixo": saldo < minimo,
                "proporcao": saldo / minimo if minimo else None,
            }
        )

    lista.sort(
        key=lambda linha: (
            linha["proporcao"] is None,
            linha["proporcao"] if linha["proporcao"] is not None else 0,
            linha["produto"]["nome"],
        )
    )

    return lista
