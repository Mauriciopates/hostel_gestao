"""Ficheiros do modo `--desempenho` (v2.2.0): relatório HTML, CSV e
JSON, na pasta de relatórios da aplicação (a mesma dos PDFs).

O JSON serve para a medição seguinte, NO MESMO SERVIDOR, mostrar a
diferença para esta ("vs anterior") — é assim que se vê o efeito de
uma otimização. Comparar servidores diferentes (Local vs VM) não diz
nada: outros dados, outra latência.

Só grava texto de SQL (com %s), nunca os valores das consultas.
"""

import csv
import json
from datetime import datetime

import config
import desempenho
from . import base

_PREFIXO = "desempenho_"


def _pasta():
    return base.pasta_relatorios()


def medicao_anterior(servidor):
    """{nome do ecrã: total em ms} da última medição deste servidor,
    ou {} se não houver nenhuma."""
    for ficheiro in sorted(_pasta().glob(f"{_PREFIXO}*.json"),
                           reverse=True):
        try:
            dados = json.loads(ficheiro.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if dados.get("servidor") != servidor:
            continue
        return {
            linha["nome"]: linha["total"]
            for linha in dados.get("linhas", [])
            if not linha.get("erro") and not linha.get("saltado")
        }
    return {}


def gravar(linhas, servidor, repeticoes, agora=None):
    """Grava HTML, CSV e JSON e devolve o caminho do HTML.

    `linhas` vem do `desempenho` (medidas, saltadas e com erro). A
    cada linha medida junta-se o tempo da medição anterior deste
    servidor, se houver.
    """
    agora = agora or datetime.now()
    anterior = medicao_anterior(servidor)
    for linha in linhas:
        if not linha.get("erro") and not linha.get("saltado"):
            linha["anterior"] = anterior.get(linha["nome"])

    dados = {
        "quando": agora.strftime("%d/%m/%Y %H:%M"),
        "servidor": servidor,
        "repeticoes": repeticoes,
        "ok": desempenho.LIMITE_OK_MS,
        "lento": desempenho.LIMITE_LENTO_MS,
        "resumo": desempenho.resumo(linhas),
        "linhas": linhas,
    }

    nome = f"{_PREFIXO}{agora.strftime('%Y%m%d_%H%M%S')}"
    pasta = _pasta()
    (pasta / f"{nome}.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    _gravar_csv(linhas, pasta / f"{nome}.csv")
    caminho_html = pasta / f"{nome}.html"
    _gravar_html(dados, caminho_html)
    return caminho_html


def _gravar_csv(linhas, caminho):
    with open(caminho, "w", newline="", encoding="utf-8-sig") as ficheiro:
        escritor = csv.writer(ficheiro, delimiter=";")
        escritor.writerow([
            "ecra", "total_ms", "primeira_ms", "dados_ms", "widgets_ms",
            "desenho_ms", "consultas", "ligacoes", "n_widgets",
            "escritas", "estado",
        ])
        for linha in linhas:
            if linha.get("saltado"):
                escritor.writerow([linha["nome"], "SALTADO",
                                   linha["saltado"]])
                continue
            if linha.get("erro"):
                escritor.writerow([linha["nome"], "ERRO", linha["erro"]])
                continue
            escritor.writerow([
                linha["nome"], round(linha["total"]),
                round(linha["primeira"]), round(linha["dados"]),
                round(linha["construcao"]), round(linha["desenho"]),
                linha["n_consultas"], linha["n_ligacoes"],
                linha["widgets"], linha["escritas"], linha["estado"],
            ])


def _gravar_html(dados, caminho):
    """Página única, sem nada de fora (abre sem internet). O modelo
    vive em `impressao/modelos/desempenho.html` (no executável vai em
    `_internal`, ver HostelGestao.spec); os dados entram no lugar de
    `__JSON__`."""
    modelo = config.FICHEIRO_MODELO_DESEMPENHO.read_text(encoding="utf-8")
    carga = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    caminho.write_text(modelo.replace("__JSON__", carga), encoding="utf-8")
