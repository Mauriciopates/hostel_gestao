"""Persistência do sistema de migrações (v1.8.0, decisão D3).

Único sítio que corre o SQL das migrações. A lista das migrações e a
decisão de quais faltam vivem no `migracoes.py` (camada de negócio);
aqui só se cria a tabela de controlo, se lê o que já foi aplicado e
se executa uma migração.

Cada base de dados (Localhost, VM, testes) tem a sua própria tabela
`migracoes_aplicadas`. Desde o INST-03 ela faz parte do esquema
oficial (`src/bd/esquema.sql`, grupo Sistema) — uma base nova já nasce
com ela. O CREATE TABLE IF NOT EXISTS abaixo fica só como rede de
segurança para bases criadas antes da v1.8.0, e TEM de ser igual à
definição do esquema.
"""

import logging
from datetime import datetime
from typing import cast

from ._base import obter_conexao

logger = logging.getLogger(__name__)


_SQL_TABELA_MIGRACOES = (
    "CREATE TABLE IF NOT EXISTS migracoes_aplicadas ("
    "id INT NOT NULL AUTO_INCREMENT, "
    "nome VARCHAR(100) NOT NULL, "
    "aplicada_em DATETIME NOT NULL, "
    "PRIMARY KEY (id), "
    "UNIQUE KEY uq_migracoes_nome (nome)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 "
    "COLLATE=utf8mb4_unicode_ci"
)


def garantir_tabela_migracoes():
    """Cria a tabela de controlo, se ainda não existir. Idempotente."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(_SQL_TABELA_MIGRACOES)
        conexao.commit()
    finally:
        conexao.close()


def listar_migracoes_aplicadas():
    """Devolve o conjunto (set) dos nomes das migrações já aplicadas
    nesta base de dados."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT nome FROM migracoes_aplicadas")
        linhas = cast(list[tuple], cursor.fetchall())
        return {str(linha[0]) for linha in linhas}
    finally:
        conexao.close()


def aplicar_migracao(nome, instrucoes):
    """Corre as instruções SQL de uma migração e regista-a.

    Tudo na mesma ligação. O registo só é feito depois de TODAS as
    instruções passarem; se alguma falhar, faz-se rollback e a
    exceção sobe — a migração fica por aplicar e volta a ser tentada
    no arranque seguinte.

    ATENÇÃO: no MySQL, CREATE/ALTER/DROP fazem commit sozinhos — o
    rollback só desfaz INSERT/UPDATE/DELETE. É por isso que todas as
    migrações têm de ser idempotentes (IF NOT EXISTS, WHERE NOT
    EXISTS): voltar a corrê-las depois de uma falha a meio tem de ser
    seguro.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        for instrucao in instrucoes:
            cursor.execute(instrucao)
        cursor.execute(
            "INSERT INTO migracoes_aplicadas (nome, aplicada_em) "
            "VALUES (%s, %s)",
            (nome, datetime.now()),
        )
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()
