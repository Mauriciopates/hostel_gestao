"""Helpers comuns às exportações — PDF, CSV e Excel.

Vive dentro do pacote `impressao/`, ao lado dos três módulos que
geram cada formato. Não tem nenhuma função `gerar_*` — só a base
partilhada: o nome do ficheiro, a pasta de destino, a formatação
de valores e datas em PT-PT, e a abertura automática no sistema.

IMPORTANTE — regra herdada do `impressao.py` original: qualquer
texto que vá para dentro do PDF tem de ser Latin-1. O fpdf com
fontes core (`Times`, `Helvetica`, `Courier`) não aceita
travessões longos, aspas curvas, nem o `€`. Os helpers aqui
evitam isso: valores para o PDF saem como `-` quando vazios, e
as datas usam `-` em vez de `—`. Quem gera PDF tem de continuar
a respeitar esta regra.
"""

from datetime import date, datetime

import config

# =====================================================================
# CONSTANTES
# =====================================================================

# Caracteres que o fpdf com fontes core não aceita. Substituídos
# por equivalentes ASCII antes de qualquer texto entrar num PDF.
# Ver docstring do módulo para a explicação completa.
_LATIN1_SUBSTITUICOES = {
    "€": "EUR",       # não é aceite pela Helvetica do fpdf
    "—": "-",         # travessão longo → hífen
    "–": "-",         # en dash → hífen
    "…": "...",       # reticências → três pontos
    "\u2018": "'",    # aspas curvas simples (esquerda)
    "\u2019": "'",    # aspas curvas simples (direita)
    "\u201C": '"',    # aspas curvas duplas (esquerda)
    "\u201D": '"',    # aspas curvas duplas (direita)
}


# =====================================================================
# NOME E CAMINHO DOS FICHEIROS
# =====================================================================


def nome_base_relatorio(area, relatorio_id, data_inicio, data_fim):
    """Constrói o nome base do ficheiro de relatório, sem extensão.

    Formato:

        relatorio_<area>_<nome>_<data_inicio>_<data_fim>_<hora>

    Ex.: `relatorio_financeiro_resultado_2026-09-01_2026-09-19_14h24`.

    `<area>` e `<nome>` vão em minúsculas, sem acentos nem espaços
    (o `<nome>` já vem assim do mapa `RELATORIOS` no
    `gui_relatorios.py` — é o `id`). As datas vão em ISO, para
    ordenar bem no explorador de ficheiros.

    A HORA no fim (formato HHhMM, ex. `14h24`) evita que duas
    exportações do mesmo relatório no mesmo dia se sobrescrevam —
    cada uma gera um ficheiro próprio. Resolve também o
    `Permission denied` que acontecia quando o ficheiro anterior
    ainda estava aberto no Excel: como o nome é sempre diferente,
    o Windows nunca bloqueia a escrita.

    Serve os três formatos (PDF, CSV, Excel) — cada módulo
    acrescenta a extensão que lhe compete.
    """
    hora_minuto = datetime.now().strftime("%Hh%M")

    return (
        f"relatorio_{area}_{relatorio_id}_"
        f"{data_inicio.isoformat()}_{data_fim.isoformat()}_"
        f"{hora_minuto}"
    )


def pasta_relatorios():
    """Devolve o `Path` da pasta onde os relatórios exportados vivem,
    garantindo que existe.

    Delega em `config.garantir_diretorios()` — a mesma função que
    cria `DIR_DADOS`, `DIR_BACKUPS`, `DIR_CONTRATOS` e
    `DIR_RELATORIOS`. Idempotente: seguro chamar sempre que se vai
    escrever um ficheiro.
    """
    config.garantir_diretorios()
    return config.DIR_RELATORIOS


# =====================================================================
# FORMATAÇÃO DE VALORES E DATAS
# =====================================================================


def formatar_valor_pt(valor):
    """Formata um Decimal ou int como string em PT-PT, para
    apresentação (PDF, Excel).

    Resultado: `4.200,00 €` (ponto de milhar, vírgula decimal,
    símbolo de euro). Um `None` devolve `-` (hífen simples, ASCII).

    NÃO usar no CSV — o CSV leva valores puros (`4200.00`).
    """
    if valor is None:
        return "-"

    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto} €"


def formatar_valor_csv(valor):
    """Formata um Decimal ou int como valor puro para CSV.

    Resultado: `4200.00` (ponto decimal, sem símbolo, sem separador
    de milhar). Um `None` devolve string vazia.

    Este é o formato que o Excel, Power BI e Python reconhecem como
    número. Ver a discussão em 19/09/2026 sobre CSV profissional.
    """
    if valor is None:
        return ""

    if hasattr(valor, "quantize"):
        # Decimal — força 2 casas, sem símbolo
        return f"{valor:.2f}"

    # int ou float — formata com 2 casas, sem símbolo
    return f"{valor:.2f}"


def formatar_data_iso(valor):
    """Formata uma `date` como ISO (AAAA-MM-DD).

    Este é o formato que o Excel reconhece como data, e o que o
    mercado usa em CSV. Um `None` devolve string vazia.
    """
    if valor is None:
        return ""

    return valor.isoformat()


def formatar_data_pt(valor):
    """Formata uma `date` como DD/MM/AAAA, para apresentação (PDF,
    Excel com máscara, ecrã).

    Um `None` devolve `-` (hífen simples, ASCII).
    """
    if valor is None:
        return "-"

    return valor.strftime("%d/%m/%Y")


# =====================================================================
# TEXTO PARA PDF (Latin-1)
# =====================================================================


def sanitizar_texto_pdf(texto):
    """Substitui caracteres não-Latin-1 por equivalentes ASCII.

    O fpdf com fontes core (`Times`, `Helvetica`, `Courier`) não
    aceita `€`, travessões longos, aspas curvas, nem reticências
    tipográficas. Esta função troca-os antes de o texto entrar num
    `pdf.cell` ou `pdf.multi_cell`.

    É a única função que se deve usar sobre QUALQUER texto que vá
    para dentro do PDF — valores, datas, nomes, motivos. Ver a
    docstring do módulo `impressao.pdf` para a explicação completa.
    """
    if texto is None:
        return ""

    texto = str(texto)

    for original, substituto in _LATIN1_SUBSTITUICOES.items():
        texto = texto.replace(original, substituto)

    return texto


# =====================================================================
# ABRIR NO SISTEMA
# =====================================================================


def abrir_no_sistema(caminho):
    """Abre um ficheiro no programa por omissão do sistema.

    Mesma função do `_ImprimirContratoModal` (gui_contratos.py):
    `os.startfile` no Windows, `open` no macOS, `xdg-open` no
    Linux.

    Erros de abertura são silenciosos — o ficheiro já está no
    disco, o utilizador pode abri-lo à mão se algo falhar. Não
    vale a pena interromper o fluxo por causa disso.
    """
    import os
    import subprocess
    import sys

    try:
        if sys.platform.startswith("win"):
            os.startfile(str(caminho))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(caminho)])
        else:
            subprocess.Popen(["xdg-open", str(caminho)])
    except (FileNotFoundError, OSError):
        pass