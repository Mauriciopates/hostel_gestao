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

BLOQUEIO (v1.8.1): `bloqueio_migracoes` usa o GET_LOCK do próprio MySQL
para que só UM arranque de cada vez aplique migrações nesta base. Sem
ele, duas cópias da aplicação a arrancar ao mesmo tempo (dois cliques,
ou dois PCs depois de uma atualização) liam as duas "falta a 0002",
corriam-na as duas e a segunda rebentava no registo com "Duplicate
entry" (teste de instalação de 02/10/2026).
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import cast

from ._base import obter_conexao

logger = logging.getLogger(__name__)

# Segundos que um arranque espera pelo outro antes de desistir. Uma
# base nova aplica todas as migrações em poucos segundos; 60 s chega
# com folga mesmo numa VM lenta.
ESPERA_BLOQUEIO_S = 60

# O nome do bloqueio inclui a base: duas bases no mesmo servidor
# (hostel_gestao e hostel_gestao_teste) não se bloqueiam uma à outra.
# O MySQL aceita no máximo 64 caracteres no nome — daí o LEFT.
_SQL_NOME_BLOQUEIO = "LEFT(CONCAT('hostel_migracoes.', DATABASE()), 64)"


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


@contextmanager
def bloqueio_migracoes(espera_s=ESPERA_BLOQUEIO_S):
    """Garante que só este arranque aplica migrações enquanto o bloco
    `with` durar.

    GET_LOCK é um bloqueio com nome, guardado pelo servidor MySQL e
    preso à LIGAÇÃO: por isso a ligação fica aberta durante todo o
    bloco, e fechá-la (mesmo se a aplicação rebentar) liberta-o. Não
    precisa de privilégios especiais.

    Se outro arranque tiver o bloqueio, espera até `espera_s`
    segundos — quando entra, as migrações que o outro aplicou já
    estão registadas e não se repetem. Se o tempo acabar, lança
    ValueError (a aplicação mostra o erro e não abre).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"SELECT GET_LOCK({_SQL_NOME_BLOQUEIO}, %s)", (espera_s,)
        )
        obtido = cast(tuple, cursor.fetchone())[0]
        if obtido != 1:
            raise ValueError(
                f"Outro arranque da aplicação está a atualizar a base "
                f"de dados há mais de {espera_s} segundos. Feche as "
                f"outras janelas do Hostel Gestão e tente de novo."
            )
        try:
            yield
        finally:
            cursor.execute(f"SELECT RELEASE_LOCK({_SQL_NOME_BLOQUEIO})")
            cursor.fetchall()
    finally:
        conexao.close()


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
