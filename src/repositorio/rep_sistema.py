"""Backup com nome próprio e reset total ("Começar do zero")."""

import logging
import os
import subprocess
from datetime import date

import config

from ._base import _garantir_pastas, obter_conexao

logger = logging.getLogger(__name__)


# --- backup com nome + reset total -----------------------------------
#
# Duas funções usadas pela operação "Começar do zero" (sistema.py).
# O backup com nome próprio permite distinguir os backups automáticos
# diários (dump_YYYY-MM-DD.sql) dos backups de segurança antes de
# uma operação destrutiva (pre_reset_YYYY-MM-DD_HHhMM.sql).


def criar_backup_com_nome(prefixo):
    """Faz um dump da base MySQL com um nome próprio.

    Diferente de `criar_backup()` (que só faz um por dia, com nome
    fixo `dump_<data>.sql`), esta versão aceita um prefixo e gera
    sempre um ficheiro novo, com data e hora no nome:

        <prefixo>_<data>_<hora>.sql

    Exemplos:
      - prefixo="pre_reset" → "pre_reset_2026-09-19_15h42.sql"
      - prefixo="manual"    → "manual_2026-09-19_15h42.sql"

    Devolve o `Path` do ficheiro, ou None se o `mysqldump` falhar.
    Não substitui nenhum ficheiro existente.

    Usa a mesma proteção do `criar_backup()`: a password vai pela
    variável de ambiente `MYSQL_PWD`, nunca como argumento.
    """
    _garantir_pastas()

    agora = date.today()
    from datetime import datetime as _datetime

    hora_minuto = _datetime.now().strftime("%Hh%M")

    nome = f"{prefixo}_{agora.isoformat()}_{hora_minuto}.sql"
    destino = config.DIR_BACKUPS / nome

    comando = [
        "mysqldump",
        f"--host={config.DB_HOST}",
        f"--port={config.DB_PORT}",
        f"--user={config.DB_USER}",
        "--single-transaction",
        "--routines",
        "--triggers",
        config.DB_NAME,
    ]

    ambiente = {**os.environ, "MYSQL_PWD": config.DB_PASSWORD}

    try:
        with open(destino, "w", encoding="utf-8") as f:
            subprocess.run(
                comando,
                stdin=subprocess.DEVNULL,
                stdout=f,
                stderr=subprocess.PIPE,
                env=ambiente,
                check=True,
                text=True,
                # Sem janela preta de consola no executável (v1.8.0);
                # fora do Windows a constante não existe → 0.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except (subprocess.CalledProcessError, OSError):
        logger.error(
            "Falha ao criar backup '%s' — mysqldump indisponível ou "
            "credenciais inválidas",
            prefixo,
        )
        destino.unlink(missing_ok=True)
        return None

    logger.info("Backup '%s' criado: %s", prefixo, destino.name)
    return destino


def apagar_tudo():
    """Apaga o conteúdo de TODAS as tabelas do sistema.

    OPERAÇÃO DESTRUTIVA — usada só pelo `sistema.comecar_do_zero`,
    depois de um backup automático. Nunca chamar sem esse backup.

    Estratégia:
      1. Desliga temporariamente as verificações de FK
         (`FOREIGN_KEY_CHECKS=0`) para permitir apagar em
         qualquer ordem.
      2. Corre TRUNCATE TABLE em cada tabela do sistema.
      3. Religa as verificações de FK.

    TRUNCATE (em vez de DELETE) porque é mais rápido e ignora as
    FKs quando as verificações estão desligadas.

    IDs (v1.8.0): com as tabelas vazias, o `proximo_id` volta a
    começar em 001 em todos os prefixos — calcula o número a partir
    do MAX(id), já não há ficheiro de contadores. Os registos antigos
    só existem no backup feito antes do reset.
    """
    tabelas = [
        "ocupacoes_mensal",
        "ocupacoes_airbnb",
        "itens_devolucao",
        "itens_requisicao",
        "itens_despesa",
        "movimentos",
        "devolucoes",
        "requisicoes",
        "despesas",
        "responsavel_unidade",
        "configuracoes_historico",
        "configuracoes",
        "ocupacoes",
        "lugares",
        "quartos",
        "rol_lavanderia_regras",
        "unidades",
        "propriedades",
        "produtos",
        "fornecedores",
        "categorias_despesa",
        "clientes",
        "responsaveis",
    ]

    logger.warning("RESET DO SISTEMA iniciado — apagar_tudo()")

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()

        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        try:
            for tabela in tabelas:
                cursor.execute(f"TRUNCATE TABLE {tabela}")
        finally:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        conexao.commit()
        logger.warning(
            "RESET DO SISTEMA concluído — %d tabelas truncadas", len(tabelas)
        )
    finally:
        conexao.close()
