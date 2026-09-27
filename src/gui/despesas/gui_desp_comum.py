"""Helpers partilhados pelos ecrãs e modais de Despesas.

Mesmo papel do `gui_est_comum.py` no Stock: nomes públicos
aqui; cada ficheiro `gui_desp_*` cria o alias privado no topo
(`_autor_atual = gui_desp_comum.autor_atual`)."""

import datetime
from decimal import Decimal, InvalidOperation

import despesas
from .. import componentes
from .. import sessao


# =====================================================================
# HELPERS INTERNOS
# =====================================================================


def parse_decimal(texto, nome_campo):
    """Converte texto monetário (obrigatório) para Decimal.

    Aceita vírgula ou ponto. Vazio levanta erro. Devolve SEMPRE
    Decimal — nunca None —, o que deixa o Pylance sossegado nas
    chamadas onde o valor é obrigatório.
    """
    texto = texto.strip()
    if not texto:
        raise ValueError(f"{nome_campo} é obrigatório.")
    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"{nome_campo} tem um valor inválido.")


def autor_atual():
    """Devolve o dict do responsável ativo, ou None.

    Toda a escrita no módulo `despesas` exige o `autor`. Esta função
    centraliza o acesso à sessão — a GUI nunca chama
    `sessao.obter_responsavel_ativo()` diretamente nos modais.
    """
    return sessao.obter_responsavel_ativo()


def formatar_data(valor):
    """Formata uma `date` para dd/mm/aaaa, ou "—" quando None."""
    if valor is None:
        return "—"
    return valor.strftime("%d/%m/%Y")


def parse_data(texto, nome_campo):
    """Converte texto "dd/mm/aaaa" numa `date`. Devolve None se
    vazio; levanta ValueError se o formato estiver errado.

    Centraliza a conversão — a GUI usa isto em todos os modais
    onde há campos de data.
    """
    texto = texto.strip()
    if not texto:
        return None
    try:
        return datetime.datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"{nome_campo} inválida. Usa o formato dd/mm/aaaa.")


def rotulo_unidade(unidade):
    """Rótulo de dropdown de unidade: "NOME (ID) · Propriedade"."""
    if unidade is None:
        return "— Nenhuma (despesa geral) —"
    return (
        f"{unidade['nome']} ({unidade['id']}) · "
        f"{unidade.get('propriedade_nome', '')}"
    )


def rotulo_categoria(categoria):
    """Rótulo de dropdown de categoria: "NOME"."""
    return categoria["nome"]


def abrir_despesas_ligadas(master, registo, subtitulo, **filtro):
    """Lista (só leitura) das despesas de uma categoria ou de um
    fornecedor — aberta ao clicar no ID dessas tabelas.

    'filtro' vai direto para `despesas.listar_despesas`
    (categoria_id=... ou fornecedor_id=...).
    """
    linhas = [
        (
            d["id"],
            formatar_data(d["data_lancamento"]),
            d["descricao"] or "(sem descrição)",
            componentes.formatar_valor(d["valor"]),
            d["estado"].capitalize(),
        )
        for d in despesas.listar_despesas(**filtro)
    ]

    componentes.ListaVinculadaModal(
        master,
        titulo=f"{registo['nome']} ({registo['id']})",
        subtitulo=subtitulo,
        colunas=(
            componentes.Coluna("ID", minimo=100, espaco=8),
            componentes.Coluna("DATA", minimo=90),
            componentes.Coluna("DESCRIÇÃO", peso=3, minimo=200),
            componentes.Coluna("VALOR", minimo=90, alinhamento="e", espaco=8),
            componentes.Coluna("ESTADO", minimo=80),
        ),
        linhas=linhas,
        mensagem_vazia="Sem despesas ligadas.",
    )
