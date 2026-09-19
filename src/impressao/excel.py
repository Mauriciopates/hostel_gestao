"""Geração de Excel (.xlsx) — dados com aspeto, prontos para
apresentação.

Este módulo gera os relatórios em formato Excel PROFISSIONAL:
- Os valores continuam numéricos (o Excel soma, filtra, faz
  fórmulas — tal como no CSV).
- Mas as células recebem máscara de moeda (`€`), negativos a
  vermelho, e o cabeçalho fica estilizado (bold, fundo cinza,
  texto branco/escuro).

É o meio-termo entre o CSV (puro, sem aspeto) e o PDF (só
apresentação, sem cálculo): o Excel é as duas coisas ao mesmo
tempo.

Decisão do aluno em 19/09/2026, ao testar o CSV no Excel e ver
que um ficheiro "pronto para reunião" exigia formatação manual
célula a célula.

Diferenças face ao CSV:
- Extensão `.xlsx` (binário, precisa de biblioteca — o `openpyxl`).
- Cabeçalho formatado: fundo azul escuro, texto branco, bold.
- Colunas com largura ajustada ao conteúdo (até um limite).
- Valores com formato de moeda nativo do Excel (`#,##0.00 €`).
- Negativos a vermelho (regra de formatação condicional).

Diferenças face ao PDF:
- Os valores continuam a ser NÚMEROS no Excel (o utilizador
  pode fazer somas depois de abrir).
- Não há paginação nem impressão — é um ficheiro de trabalho.
"""

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import base

# =====================================================================
# CONSTANTES DE ESTILO
# =====================================================================

# Fundo do cabeçalho — o mesmo azul escuro que a aplicação usa em
# NAVY_ESCURO, para casar com o resto do sistema.
_COR_FUNDO_CABECALHO = "0C2F48"

# Texto do cabeçalho — branco sobre o fundo escuro.
_COR_TEXTO_CABECALHO = "FFFFFF"

# Formato de moeda nativo do Excel. O Excel reconhece este formato
# como número E mostra o símbolo de euro com separador de milhar.
# É diferente do que o CSV tem — aqui o utilizador vê formatado,
# mas o valor por baixo continua a ser número.
_FORMATO_MOEDA = "#,##0.00\\ €"

# Cor do texto para valores negativos — o mesmo vermelho do tema.
_COR_NEGATIVO = "C0392B"

# Largura máxima de uma coluna (em caracteres). O Excel mede em
# unidades que dependem do tipo de letra; 40 é um bom limite para
# evitar colunas a ocupar o ecrã todo quando há um nome comprido.
_LARGURA_MAX_COLUNA = 40

_LARGURA_MIN_COLUNA = 10


def gerar_relatorio_excel(
    titulo,
    colunas,
    linhas,
    area,
    relatorio_id,
    data_inicio,
    data_fim,
):
    """Gera um Excel (.xlsx) com o conteúdo de um relatório.

    Parâmetros idênticos aos do `gerar_relatorio_csv` e
    `gerar_relatorio_pdf` — o `gui_relatorios.py` passa os mesmos
    dados aos três.

    Devolve o `Path` do ficheiro gerado.

    Estrutura:
      - Linha 1: cabeçalho das colunas (fundo escuro, texto
        branco, bold).
      - Linha 2 em diante: dados.
      - A primeira coluna fica alinhada à esquerda, as restantes
        à direita (valores numéricos).

    Só dados: o título e o período vivem no nome do ficheiro —
    não são escritos dentro da folha. Decisão do aluno em
    19/09/2026: o Excel é um ficheiro de trabalho, não um
    documento de apresentação.

    Formato dos valores:
      - `Decimal` e `int` → número no Excel, com máscara de moeda.
      - `date` → data no Excel, formato ISO (o Excel reconhece).
      - `str` → tal e qual.

    Os negativos ficam a vermelho. (Aplicado manualmente por
    linha, porque o openpyxl não tem formatação condicional
    simples para intervalos.)
    """
    prefixo = base.nome_base_relatorio(
        area, relatorio_id, data_inicio, data_fim
    )
    caminho = base.pasta_relatorios() / f"{prefixo}.xlsx"

    wb = Workbook()
    ws = wb.active
    assert ws is not None  # `wb.active` de um Workbook novo nunca é None
    ws.title = "Relatório"

    # ---- Linha 1: cabeçalho ------------------------------------
    for indice, titulo_coluna in enumerate(colunas, start=1):
        celula = ws.cell(row=1, column=indice, value=str(titulo_coluna))
        celula.font = Font(bold=True, color=_COR_TEXTO_CABECALHO, size=10)
        celula.fill = PatternFill(
            start_color=_COR_FUNDO_CABECALHO,
            end_color=_COR_FUNDO_CABECALHO,
            fill_type="solid",
        )
        celula.alignment = Alignment(horizontal="center", vertical="center")

    # ---- Linha 2 em diante: dados ------------------------------
    for numero_linha, linha in enumerate(linhas, start=2):
        for indice, celula in enumerate(linha, start=1):
            valor = _valor_para_celula_excel(celula)
            c = ws.cell(row=numero_linha, column=indice, value=valor)

            # Alinhamento — primeira coluna à esquerda, resto à
            # direita.
            if indice == 1:
                c.alignment = Alignment(horizontal="left")
            else:
                c.alignment = Alignment(horizontal="right")

            # Formato de moeda + negativos a vermelho, quando
            # aplicável. O `_formatar_celula` decide se aplica
            # consoante o tipo do valor.
            _formatar_celula(c, celula)

    # ---- Larguras das colunas ----------------------------------
    _ajustar_larguras(ws, colunas, linhas)

    wb.save(str(caminho))
    return caminho


def _valor_para_celula_excel(celula):
    """Converte uma célula para o valor que vai dentro do Excel.

    Para o Excel, um `Decimal` deve chegar como `float` (o Excel
    não tem tipo Decimal nativo). Um `date` chega como `datetime`
    para o Excel o reconhecer como data. Uma string chega tal
    qual.

    Isto é a diferença crucial face ao CSV: no CSV o `Decimal` vira
    TEXTO (`"4200.00"`), no Excel vira NÚMERO (`4200.0`).
    """
    from datetime import date, datetime
    from decimal import Decimal

    if celula is None:
        return ""

    if isinstance(celula, Decimal):
        return float(celula)

    if isinstance(celula, (int, float)):
        return celula

    if isinstance(celula, date):
        # O `openpyxl` exige `datetime` (não aceita `date` puro).
        return datetime(celula.year, celula.month, celula.day)

    return str(celula)


def _formatar_celula(celula_excel, valor_original):
    """Aplica formato de moeda e cor conforme o valor original.

    - Se `valor_original` for `Decimal` ou número: máscara de
      moeda. Se for negativo, também pinta o texto a vermelho.
    - Se for `date`: formato de data ISO (o Excel reconhece).
    - Se for `str`: fica como está.
    """
    from datetime import date
    from decimal import Decimal

    if isinstance(valor_original, Decimal):
        celula_excel.number_format = _FORMATO_MOEDA

        if valor_original < 0:
            celula_excel.font = Font(color=_COR_NEGATIVO)

    elif isinstance(valor_original, (int, float)):
        celula_excel.number_format = _FORMATO_MOEDA

        if valor_original < 0:
            celula_excel.font = Font(color=_COR_NEGATIVO)

    elif isinstance(valor_original, date):
        celula_excel.number_format = "yyyy-mm-dd"


def _ajustar_larguras(ws, colunas, linhas):
    """Ajusta a largura de cada coluna ao conteúdo mais comprido
    (cabeçalho incluído).

    Respeita os limites `_LARGURA_MIN_COLUNA` e
    `_LARGURA_MAX_COLUNA` — um valor muito comprido não faz a
    coluna ocupar o ecrã todo, e um valor muito curto não fica
    apertado.
    """
    for indice, titulo in enumerate(colunas, start=1):
        largura = len(str(titulo)) + 2

        for linha in linhas:
            if indice - 1 < len(linha):
                valor = linha[indice - 1]
                largura = max(largura, len(str(valor)) + 2)

        largura = max(_LARGURA_MIN_COLUNA, min(largura, _LARGURA_MAX_COLUNA))
        ws.column_dimensions[get_column_letter(indice)].width = largura
