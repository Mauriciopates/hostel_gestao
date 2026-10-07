"""Constantes e helpers partilhados pelos ecrãs de Relatórios.

Mesmo papel do `gui_est_comum.py` / `gui_desp_comum.py`: nomes
públicos aqui; cada `gui_relat_*` cria o alias privado no topo."""

from datetime import date, timedelta
from decimal import Decimal

from .. import componentes
from .. import sessao
from .. import tema


# =====================================================================
# CONSTANTES DE APRESENTAÇÃO
# =====================================================================

# Chips de período — a ordem é a que aparece na barra.
# 'personalizado' não é um chip próprio: é o campo único que abre o
# calendário. Está aqui só para o rótulo ser único num sítio.
PERIODO_MES_ATUAL = "mes_atual"
PERIODO_MES_ANTERIOR = "mes_anterior"
PERIODO_ULTIMOS_30 = "ultimos_30"
PERIODO_ESTE_ANO = "este_ano"
PERIODO_PERSONALIZADO = "personalizado"

CHIPS_PERIODO = (
    (PERIODO_MES_ATUAL, "Mês atual"),
    (PERIODO_MES_ANTERIOR, "Mês anterior"),
    (PERIODO_ULTIMOS_30, "Últimos 30 dias"),
    (PERIODO_ESTE_ANO, "Este ano"),
)

PERIODO_DEFAULT = PERIODO_MES_ATUAL


# =====================================================================
# MAPA DOS RELATÓRIOS
# =====================================================================
#
# Cada área tem uma lista de relatórios. Cada relatório é um dicionário:
#
#   - 'id':       identificador interno (usado como chave de despacho
#                 e no nome do ficheiro exportado, sem espaços).
#   - 'titulo':   texto mostrado na lista lateral e no cabeçalho do
#                 relatório.
#   - 'periodo':  True se o relatório usa o período escolhido (barra
#                 de período visível); False se é "agora" (barra
#                 escondida). Só "Stock atual" é False.
#   - 'filtros':  lista de filtros adicionais próprios do relatório.
#                 Cada filtro é ("chave", "rótulo", ("opção1", ...)).
#                 Lista vazia quando não há filtros próprios.
#
# A ORDEM das áreas é a ordem dos cartões no hub (Financeiro primeiro,
# porque é o que se usa mais). A ORDEM dos relatórios dentro de cada
# área é a ordem na lista lateral — o "Resultado" primeiro, porque é
# o relatório de topo.

RELATORIOS = {
    "financeiro": [
        {
            "id": "resultado",
            "titulo": "Resultado",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "receita_unidade",
            "titulo": "Receita por unidade",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "receita_propriedade",
            "titulo": "Receita por propriedade",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "despesas_categoria",
            "titulo": "Despesas por categoria",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "cogs_produto",
            "titulo": "COGS por produto",
            "periodo": True,
            "filtros": [],
        },
    ],
    "contratos": [
        {
            "id": "ocupacoes",
            "titulo": "Ocupações no período",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "contratos_mensais",
            "titulo": "Contratos mensais",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "reservas_airbnb",
            "titulo": "Reservas Airbnb",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "encerramentos",
            "titulo": "Encerramentos",
            "periodo": True,
            "filtros": [],
        },
    ],
    "stock": [
        {
            "id": "movimentos",
            "titulo": "Movimentos",
            "periodo": True,
            "filtros": [
                ("tipo", "Tipo", ("Todos", "entrada", "saida", "ajuste")),
                ("produto", "Produto", ()),  # preenchido em runtime
            ],
        },
        {
            "id": "stock_atual",
            "titulo": "Stock atual",
            "periodo": False,
            "filtros": [],
        },
        {
            "id": "requisicoes",
            "titulo": "Requisições",
            "periodo": True,
            "filtros": [
                (
                    "estado",
                    "Estado",
                    (
                        "Todos",
                        "pendente",
                        "enviada",
                        "fechada",
                        "rejeitada",
                        "cancelada",
                    ),
                ),
                ("origem", "Origem", ("Todas", "pedido", "rol")),
                ("responsavel", "Responsável", ()),  # preenchido em runtime
            ],
        },
        {
            "id": "devolucoes",
            "titulo": "Devoluções",
            "periodo": True,
            "filtros": [
                ("estado", "Estado", ("Todos", "pendente", "fechada")),
                ("responsavel", "Responsável", ()),  # preenchido em runtime
            ],
        },
    ],
}

# Rótulos das áreas no hub — a ordem é a ordem dos cartões.
AREAS = (
    ("financeiro", "Financeiro", "Resultado · Receita · Despesas · COGS"),
    ("contratos", "Contratos", "Ocupações · Mensais · Airbnb · Ocupação"),
    ("stock", "Stock", "Movimentos · Stock atual · Requisições · Devoluções"),
)


# =====================================================================
# HELPERS INTERNOS
# =====================================================================


def autor_atual():
    """Devolve o dict do responsável ativo, ou None.

    Centraliza o acesso à sessão. Vários sítios deste módulo precisam
    de saber quem está logado (para os exports, para os filtros por
    perfil, para o cabeçalho do popup). Não andamos a chamar
    `sessao.obter_responsavel_ativo()` em cada função.
    """
    return sessao.obter_responsavel_ativo()


def formatar_data(valor):
    """Formata uma `date` para dd/mm/aaaa, ou '—' quando None."""
    if valor is None:
        return "—"
    return valor.strftime("%d/%m/%Y")


def formatar_data_iso(valor):
    """Formata uma `date` para AAAA-MM-DD (usado no nome do ficheiro
    exportado — ordena bem no explorador de ficheiros)."""
    return valor.isoformat()


def formatar_valor(valor):
    """Formata um Decimal em PT-PT, com euro no fim — mesma
    convenção do `componentes.formatar_valor`. Reexportado aqui com
    nome próprio para o corpo do ficheiro não ter de ir buscar
    sempre ao `componentes`.
    """
    return componentes.formatar_valor(valor)


def cor_valor(valor, cor_normal=None):
    """Cor do texto de um valor num relatório: vermelho se for
    negativo, senão `cor_normal` (por omissão a cor do texto).

    Regra da revisão de 07/10/2026 (v1.11.1): negativos a vermelho
    em todos os relatórios — ecrã, PDF e Excel.
    """
    if valor is not None and valor < 0:
        return tema.TEXTO_ERRO
    return tema.COR_TEXTO if cor_normal is None else cor_normal


def simetrico(valor):
    """`0 − valor`, sem o "-0,00" que `-Decimal("0.00")` daria.
    Usado nos descontos e despesas, que se mostram como o que se
    tira (negativos)."""
    return Decimal("0.00") - valor


def primeiro_dia_do_mes(d):
    return date(d.year, d.month, 1)


def intervalo_do_atalho(atalho, hoje=None):
    """Converte um atalho de período no par `(data_inicio, data_fim)`
    que o `financeiro.py` espera.

    `data_fim` é EXCLUSIVO no motor — a docstring de
    `financeiro._validar_periodo` é explícita ("um período com o
    mesmo dia de início e fim não contém nenhum"). Este helper é o
    ÚNICO sítio onde essa conversão acontece.

    Regras (fechadas em 19/09/2026):

      - Mês atual    → dia 1 do mês corrente → amanhã (o fim do
                        intervalo é "hoje + 1 dia", para incluir hoje).
      - Mês anterior → dia 1 → dia 1 do mês atual (o mês anterior
                        inteiro, exclusive).
      - Últimos 30   → hoje − 30 dias → amanhã.
      - Este ano     → 1 de janeiro → amanhã.

    Devolve `(data_inicio, data_fim)`, os dois `date`.
    """
    if hoje is None:
        hoje = date.today()

    if atalho == PERIODO_MES_ATUAL:
        return primeiro_dia_do_mes(hoje), hoje + timedelta(days=1)

    if atalho == PERIODO_MES_ANTERIOR:
        primeiro_dia_deste_mes = primeiro_dia_do_mes(hoje)
        ultimo_dia_do_mes_anterior = primeiro_dia_deste_mes - timedelta(days=1)
        return (
            primeiro_dia_do_mes(ultimo_dia_do_mes_anterior),
            primeiro_dia_deste_mes,
        )

    if atalho == PERIODO_ULTIMOS_30:
        return hoje - timedelta(days=30), hoje + timedelta(days=1)

    if atalho == PERIODO_ESTE_ANO:
        return date(hoje.year, 1, 1), hoje + timedelta(days=1)

    raise ValueError(f"Atalho de período desconhecido: {atalho}")


def intervalo_personalizado(data_inicio, data_fim):
    """Converte um intervalo escolhido no calendário (inclusivo nas
    duas pontas, como o utilizador o vê) no par `(data_inicio,
    data_fim)` que o motor espera (fim exclusivo).

    O utilizador escolhe "1 de agosto a 15 de setembro" — quer dizer
    que o dia 15 está incluído. O motor recebe `date(2026, 9, 16)`
    para incluir o dia 15 (fim exclusivo).
    """
    if data_inicio is None or data_fim is None:
        raise ValueError(
            "As duas datas do período personalizado são obrigatórias."
        )

    if data_fim < data_inicio:
        raise ValueError(
            "A data de fim não pode ser anterior à data de início."
        )

    return data_inicio, data_fim + timedelta(days=1)


def intervalo_visivel(atalho, hoje=None):
    """Devolve o intervalo como o UTILIZADOR o vê (as duas pontas
    inclusivas), para mostrar no campo único da barra de período.

    É o contrário de `intervalo_do_atalho`: aquele devolve o que o
    motor come, este devolve o que o utilizador lê. A diferença é
    sempre de 1 dia no fim.
    """
    inicio, fim_exclusivo = intervalo_do_atalho(atalho, hoje)
    return inicio, fim_exclusivo - timedelta(days=1)


def mapa_por_id(registo_lista):
    """Constrói um dicionário {id: registo} a partir de uma lista de
    registos com chave 'id'.

    Serve para evitar N chamadas ao MySQL quando um relatório
    precisa do nome (ou outra coisa) de várias entidades — uma
    leitura só, mapa em memória, consulta em O(1).

    Chamado no início de cada relatório que precise:
      - unidades:   `mapa_por_id(unidades.listar(incluir_inativas=True))`
      - clientes:   `mapa_por_id(clientes.listar(incluir_inativos=True))`
      - produtos:
        `mapa_por_id(estoque.listar_produtos(incluir_inativos=True))`
      - responsáveis: `mapa_por_id(responsaveis.listar(incluir_inativos=True))`
    """
    return {r["id"]: r for r in registo_lista}


def celula_entidade(nome, identificador):
    """Devolve o HTML/markup de uma célula ID + nome, na convenção
    que ficou decidida em 19/09/2026: NOME em cima, ID por baixo em
    letra pequena e cinza.

    Não devolve widget nenhum — devolve o par (texto, config) para
    quem chama construir o CTkLabel. Simplifica: a estrutura é
    sempre a mesma, o sítio é que muda.
    """
    return f"{nome}\n{identificador}"
