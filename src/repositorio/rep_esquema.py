"""Leitura e aplicação do esquema oficial da base de dados (v1.8.0,
INST-03).

O esquema vive num só ficheiro, `src/bd/esquema.sql`
(`config.FICHEIRO_ESQUEMA`) — lido pela aplicação (INST-02, criar as
tabelas numa base nova) e pelos testes (`testes/apoio_BD.py`).
"""

import logging

import config

from ._base import obter_conexao

logger = logging.getLogger(__name__)


def instrucoes_esquema():
    """Devolve a lista das instruções CREATE TABLE do esquema oficial,
    pela ordem do ficheiro (já ordenada pelas chaves estrangeiras).

    O ficheiro só tem DDL e comentários de linha ("--"), sem ";"
    dentro de textos — por isso basta tirar os comentários e partir
    no ";". Levanta FileNotFoundError se o ficheiro não existir (num
    executável, é sinal de que o `bd/` não foi incluído no .spec).
    """
    texto = config.FICHEIRO_ESQUEMA.read_text(encoding="utf-8")

    sem_comentarios = "\n".join(
        linha
        for linha in texto.splitlines()
        if not linha.strip().startswith("--")
    )

    return [
        instrucao.strip()
        for instrucao in sem_comentarios.split(";")
        if instrucao.strip()
    ]


def tabelas_do_esquema():
    """Devolve a lista dos nomes das tabelas do esquema oficial."""
    nomes = []
    for instrucao in instrucoes_esquema():
        cabecalho = instrucao.split("(", 1)[0]
        nomes.append(cabecalho.split()[-1].strip("`"))
    return nomes


def criar_tabelas():
    """Cria na base de dados ativa as tabelas que ainda não existam.

    Idempotente (CREATE TABLE IF NOT EXISTS): numa base já criada não
    faz nada. Não cria a base de dados em si nem corre as migrações —
    isso é o INST-02, que chama esta função e depois
    `migracoes.aplicar_pendentes()`.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        for instrucao in instrucoes_esquema():
            cursor.execute(instrucao)
        conexao.commit()
    finally:
        conexao.close()

    logger.info("Esquema oficial aplicado (%s)", config.FICHEIRO_ESQUEMA)
