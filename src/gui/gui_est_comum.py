"""Constantes e helpers partilhados pelos quatro ecrãs do módulo
Stock: Produtos, Movimentos, Requisições e Devoluções.

Existe para evitar import cruzado entre os ficheiros `gui_est_*`.
Por exemplo, `_itens_disponiveis_devolucao` é usado pelo ecrã de
Requisições (para decidir se mostra a ação "Reportar sobra" no
Gerir) e pelo ecrã de Devoluções (para validar o que pode ser
devolvido) — se vivesse num dos dois, o outro tinha de o importar,
criando uma dependência cruzada.

Tudo aqui é específico do Stock: cores dos chips de estado, rótulos
de opção (dropdowns), formatadores de produto/responsável, larguras
de colunas dos formulários. O que é genérico da aplicação (popups,
tabelas, helpers de clique) vive em `componentes.py`.
"""

import customtkinter as ctk

import estoque
from . import tema


# =====================================================================
# Textos das opções por omissão (dropdowns de filtro)
# =====================================================================

OPCAO_TODOS_ESTADOS = "Todos os estados"
OPCAO_TODOS_RESPONSAVEIS = "Todos os responsáveis"

# Estados possíveis — listas separadas porque Requisição e Devolução
# têm ciclos de vida diferentes. Minúsculas de propósito: é o formato
# que fica gravado na base de dados e o que aparece na coluna TIPO
# da tabela (coerente com as outras tabelas da aplicação).
ESTADOS_REQUISICAO = ("pendente", "enviada", "fechada", "rejeitada")
ESTADOS_DEVOLUCAO = ("pendente", "fechada")

# Tipos de movimento — minúsculas, mesma razão.
TIPOS_MOVIMENTO = ("entrada", "saida", "ajuste")


# =====================================================================
# Larguras fixas de colunas dos formulários (requisição, devolução,
# movimento). Constantes partilhadas para os três formulários que
# listam produtos terem as colunas alinhadas entre si.
# =====================================================================

LARGURA_PRODUTO = 240
LARGURA_ARMAZEM = 90
LARGURA_PEDIDO = 70


# =====================================================================
# Cores por estado (chips das tabelas de requisição/devolução)
#
# Todos os pares já existiam em tema.py antes desta entrega — a
# tabela de movimentos usa a mesma linguagem visual.
# =====================================================================

CORES_ESTADO = {
    "pendente": (tema.AMARELO_AVISO, tema.TEXTO_AVISO),
    "enviada": (tema.ID_CHIP_FUNDO, tema.AZUL_PRINCIPAL),
    "fechada": (tema.VERDE_LIVRE, tema.TEXTO_LIVRE),
    "rejeitada": (tema.VERMELHO_ERRO, tema.TEXTO_ERRO),
    # Movimentos (chip de tipo)
    "entrada": (tema.VERDE_LIVRE, tema.TEXTO_LIVRE),
    "saida": (tema.VERMELHO_ERRO, tema.TEXTO_ERRO),
    "ajuste": (tema.AMARELO_AVISO, tema.TEXTO_AVISO),
}


# =====================================================================
# Helpers de apresentação
# =====================================================================


def etiqueta_estado(master, estado):
    """Devolve a etiqueta colorida de um estado.

    Serve para requisições, devoluções (pendente/fechada) e movimentos
    (entrada/saida/ajuste) — todas as chaves estão em `CORES_ESTADO`.
    """
    fundo, cor_texto = CORES_ESTADO.get(
        estado, (tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL)
    )

    return ctk.CTkLabel(
        master,
        text=estado,
        text_color=cor_texto,
        fg_color=fundo,
        corner_radius=tema.RAIO_CAMPO,
        font=ctk.CTkFont(size=11, weight="bold"),
        width=100,
    )


def rotulo_responsavel(registo):
    """Texto "STF-002 · Ana Ribeiro" de um responsável.

    Mesmo formato já usado no ecrã de Gestão de Propriedades, para o
    utilizador reconhecer a mesma pessoa escrita da mesma maneira em
    toda a aplicação.
    """
    return f"{registo['id']} · {registo['nome']}"


def rotulo_produto(registo):
    """Texto "PRD-001 · Lixívia" de um produto."""
    return f"{registo['id']} · {registo['nome']}"


def texto_produtos_requisicao(requisicao, produtos):
    """Segunda linha da célula do meio, numa linha de requisição.

    Numa rejeitada mostra o motivo: é o que interessa nesse estado,
    e os produtos já não vão sair do armazém.
    """
    if requisicao["estado"] == "rejeitada":
        return f"motivo: {requisicao['motivo_rejeicao']}"

    itens = estoque.listar_itens_requisicao(requisicao_id=requisicao["id"])

    if not itens:
        return "sem produtos"

    nomes = []

    for item in itens[:3]:
        produto = produtos.get(item["produto_id"])
        nomes.append(produto["nome"] if produto else item["produto_id"])

    texto = ", ".join(nomes)

    if len(itens) > 3:
        texto += ", …"

    plural = "produtos" if len(itens) > 1 else "produto"

    return f"{len(itens)} {plural} · {texto}"


def texto_produtos_devolucao(devolucao, produtos):
    """Segunda linha da célula do meio, numa linha de devolução."""
    itens = estoque.listar_itens_devolucao(devolucao_id=devolucao["id"])

    if not itens:
        return "sem produtos"

    nomes = []

    for item in itens[:3]:
        produto = produtos.get(item["produto_id"])
        nomes.append(produto["nome"] if produto else item["produto_id"])

    texto = ", ".join(nomes)

    if len(itens) > 3:
        texto += ", …"

    plural = "produtos" if len(itens) > 1 else "produto"

    return f"{len(itens)} {plural} · {texto}"


def itens_disponiveis_devolucao(requisicao_id):
    """Itens de uma requisição fechada que ainda podem ser devolvidos.

    Para cada item, desconta da quantidade enviada tudo o que já foi
    reportado noutras devoluções (pendentes ou fechadas) — mesmo
    cálculo que `estoque.reportar_devolucao` usa para validar,
    repetido aqui só para decidir o que mostrar no formulário e no
    "Gerir". Só entram os itens com sobra por reportar (> 0).
    """
    itens = estoque.listar_itens_requisicao(requisicao_id=requisicao_id)
    devolucoes = estoque.listar_devolucoes(requisicao_id=requisicao_id)

    ja_devolvido_por_produto = {}

    for devolucao in devolucoes:
        for item_dev in estoque.listar_itens_devolucao(
            devolucao_id=devolucao["id"]
        ):
            ja_devolvido_por_produto[item_dev["produto_id"]] = (
                ja_devolvido_por_produto.get(item_dev["produto_id"], 0)
                + item_dev["quantidade"]
            )

    disponiveis = []

    for item in itens:
        ja_devolvido = ja_devolvido_por_produto.get(item["produto_id"], 0)
        disponivel = item["quantidade_enviada"] - ja_devolvido

        if disponivel > 0:
            disponiveis.append(
                {
                    "produto_id": item["produto_id"],
                    "quantidade_enviada": item["quantidade_enviada"],
                    "ja_devolvido": ja_devolvido,
                    "disponivel": disponivel,
                }
            )

    return disponiveis