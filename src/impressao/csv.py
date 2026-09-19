"""Geração de CSV — dados puros, prontos para ferramentas.

Este módulo gera os CSV dos relatórios, em formato PROFISSIONAL:
valores numéricos puros (`4200.00`, `-50.00`), datas em ISO
(`2026-09-01`), sem símbolo de euro nem separador de milhar.

A decisão foi do aluno em 19/09/2026, ao ver o ficheiro aberto no
Excel: um CSV "formatado" (`4.200,00 €`) o Excel trata como TEXTO,
não como número — não dá para somar, filtrar, nem fazer fórmulas.
Um CSV puro, o Excel reconhece como número imediatamente.

REGRA: se um dia este CSV for aberto num sistema com locale
diferente (por exemplo, em inglês), os valores continuam a fazer
sentido — `4200.00` é reconhecido universalmente. Um valor
formatado em PT-PT não é.

O Excel (.xlsx) tem tratamento diferente — esse vai com máscara de
moeda e cabeçalho estilizado. Ver `impressao/excel.py`.
"""

import csv

from . import base


def gerar_relatorio_csv(
    titulo,
    colunas,
    linhas,
    area,
    relatorio_id,
    data_inicio,
    data_fim,
    separador=";",
):
    """Gera um CSV com o conteúdo de um relatório.

    Parâmetros:
      - `titulo`:     o título do relatório (usado só para o
                      contexto, não vai para dentro do ficheiro).
      - `colunas`:    tuplo de strings, os nomes das colunas.
      - `linhas`:     lista de listas. Cada célula pode ser `str`,
                      `Decimal`, `int`, `date` ou `None` — este
                      módulo trata da conversão.
      - `area`:       chave da área ('financeiro', 'contratos',
                      'stock').
      - `relatorio_id`: id do relatório ('resultado', etc.).
      - `data_inicio`: `date` — primeira data do período.
      - `data_fim`:   `date` — última data do período (inclusiva).
      - `separador`:  `";"` (por omissão) ou `","`. Quem chama
                      decide — o Excel em PT-PT costuma abrir `;`
                      corretamente, mas há instalações que
                      preferem `,`. A interface pergunta antes de
                      gerar.

    Devolve o `Path` do ficheiro gerado.

    Estrutura do CSV:
      - Primeira linha: cabeçalho das colunas.
      - Segunda em diante: dados.
      - SEM comentários (`#`) nem linhas em branco — o título e o
        período vivem no nome do ficheiro. Isto é o que o mercado
        faz: CSV é dados, não apresentação.

    Formato dos valores:
      - `Decimal`: `4200.00` (ponto decimal, sem símbolo, sem
        separador de milhar). Ver `base.formatar_valor_csv`.
      - `date`: `2026-09-01` (ISO). Ver `base.formatar_data_iso`.
      - `str`: tal e qual.
      - `None`: string vazia.
    """
    if separador not in (";", ","):
        raise ValueError(
            f"Separador inválido: {separador!r}. Usa ';' ou ','."
        )

    prefixo = base.nome_base_relatorio(
        area, relatorio_id, data_inicio, data_fim
    )
    caminho = base.pasta_relatorios() / f"{prefixo}.csv"

    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=separador)

        # Cabeçalho — tal e qual como chegou.
        escritor.writerow(colunas)

        # Linhas — cada célula passa por `_celula_para_csv`.
        for linha in linhas:
            escritor.writerow(
                [_celula_para_csv(c) for c in linha]
            )

    return caminho


def _celula_para_csv(celula):
    """Converte uma célula para o formato CSV (numérico/ISO).

    Aceita `str`, `Decimal`, `int`, `float`, `date` ou `None`.
    Devolve sempre uma string — o `csv.writer` escreve-a tal e
    qual.

    Esta é a fronteira da decisão A (valores puros). O que entra
    aqui como `Decimal` sai como `4200.00`; como `date` sai como
    `2026-09-01`; como `str` sai tal e qual.
    """
    from datetime import date
    from decimal import Decimal

    if celula is None:
        return ""

    if isinstance(celula, Decimal):
        return base.formatar_valor_csv(celula)

    if isinstance(celula, (int, float)):
        return base.formatar_valor_csv(celula)

    if isinstance(celula, date):
        return base.formatar_data_iso(celula)

    return str(celula)