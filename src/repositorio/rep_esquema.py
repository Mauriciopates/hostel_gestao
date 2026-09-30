"""Leitura e aplicação do esquema oficial da base de dados (v1.8.0,
INST-03).

O esquema vive num só ficheiro, `src/bd/esquema.sql`
(`config.FICHEIRO_ESQUEMA`) — lido pela aplicação (INST-02, criar as
tabelas numa base nova) e pelos testes (`testes/apoio_BD.py`).
"""

import logging
import re
from typing import cast

import mysql.connector

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


# --- instalação (v1.8.0, INST-02) -------------------------------------
# As duas funções abaixo recebem as credenciais EXPLÍCITAS (o dicionário
# de `servidores.credenciais`) em vez de usar o servidor ativo do
# `config`: o formulário testa e prepara um servidor antes de o gravar.
# Ligam-se ao servidor SEM escolher base, porque a base pode não existir.

# Erros do MySQL que querem dizer "sem permissão".
_ERROS_SEM_PERMISSAO = (1044, 1045, 1142, 1227)

_NOME_BASE_VALIDO = re.compile(r"^[A-Za-z0-9_]+$")


def _ligar_sem_base(credenciais):
    dados = {k: v for k, v in credenciais.items() if k != "database"}
    return mysql.connector.connect(**dados, connection_timeout=5)


def estado_base(credenciais):
    """Devolve (existe, tabelas): se a base de `credenciais["database"]`
    existe no servidor e o conjunto dos nomes das suas tabelas.

    Levanta mysql.connector.Error se não conseguir ligar ao servidor.
    """
    base = credenciais["database"]
    conexao = _ligar_sem_base(credenciais)
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = %s",
            (base,),
        )
        existe = cursor.fetchone() is not None
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s",
            (base,),
        )
        linhas = cast(list[tuple], cursor.fetchall())
        tabelas = {str(linha[0]) for linha in linhas}
    finally:
        conexao.close()

    return existe, tabelas


def preparar_base(credenciais):
    """Cria a base de dados (se não existir) e as tabelas do esquema
    oficial que faltem. Idempotente — não toca em tabelas existentes.

    A base nasce em utf8mb4 / utf8mb4_unicode_ci, a collation do
    esquema. Não corre as migrações: isso acontece no arranque seguinte
    (`main_gui.py`), como em qualquer base.

    Levanta:
    - ValueError se o nome da base tiver caracteres inválidos (vai
      entre acentos graves num CREATE DATABASE — só letras, dígitos e _);
    - PermissionError se o utilizador do MySQL não tiver permissão para
      criar a base ou as tabelas (decisão D8: a app nunca pede o root);
    - mysql.connector.Error nos restantes erros do MySQL.
    """
    base = credenciais["database"]
    if not _NOME_BASE_VALIDO.match(base or ""):
        raise ValueError(
            f"Nome de base de dados inválido: {base!r} "
            f"(só letras, dígitos e _)."
        )

    conexao = _ligar_sem_base(credenciais)
    try:
        cursor = conexao.cursor()
        try:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{base}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.execute(f"USE `{base}`")
            for instrucao in instrucoes_esquema():
                cursor.execute(instrucao)
        except mysql.connector.Error as erro:
            if erro.errno in _ERROS_SEM_PERMISSAO:
                raise PermissionError(str(erro)) from erro
            raise
        conexao.commit()
    finally:
        conexao.close()

    logger.info("Base '%s' preparada com o esquema oficial", base)
