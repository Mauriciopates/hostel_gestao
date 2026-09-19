"""Pacote de geração de ficheiros — PDF, CSV e Excel.

Este pacote substitui o antigo `impressao.py` (ficheiro único).
Por fora, a API é IDÊNTICA — quem faz `import impressao` e chama
`impressao.gerar_contrato_pdf(...)` continua a funcionar sem
alterações. Por dentro, está dividido em quatro módulos:

  - `base.py`  — helpers comuns (nome do ficheiro, formatação,
                 pasta de destino, abrir no sistema).
  - `pdf.py`   — geração de PDFs (contratos e relatórios tabulares).
  - `csv.py`   — geração de CSV (dados puros, prontos para Excel,
                 Power BI, Python).
  - `excel.py` — geração de .xlsx (dados com máscara de moeda,
                 negativos a vermelho, cabeçalho estilizado).

DIVISÃO FEITA EM 19/09/2026, a pedido do aluno, ao planear o
tratamento de três formatos de exportação com exigências
diferentes (o CSV tem de ser puro, o Excel formatado, o PDF
Latin-1). Ter os três no mesmo ficheiro tornava cada alteração
arriscada — um bug no Excel tocava no PDF. Com esta divisão,
cada formato vive no seu ficheiro, e a parte comum está
num só sítio.

O que este `__init__.py` faz: reexporta as funções públicas dos
quatro módulos, para que o resto do projeto continue a importar
`impressao` como antes. Não tem lógica nenhuma — só serve de
porta de entrada.
"""

# Reexportações — a API pública do pacote.
#
# Quem faz `import impressao` fica com acesso direto a estas
# funções. O `gui_relatorios.py` e o `gui_contratos.py` não sabem
# (nem precisam de saber) que estão distribuídas por vários
# ficheiros.
#
# Se um dia um destes nomes mudar, muda aqui uma vez e o resto do
# projeto continua a funcionar. O `__all__` abaixo garante que o
# `import *` só traz estes nomes — evita arrastar helpers internos
# por engano.

from .pdf import (
    gerar_contrato_pdf,
    gerar_relatorio_pdf,
)
from .csv import gerar_relatorio_csv
from .excel import gerar_relatorio_excel


__all__ = [
    "gerar_contrato_pdf",
    "gerar_relatorio_pdf",
    "gerar_relatorio_csv",
    "gerar_relatorio_excel",
]