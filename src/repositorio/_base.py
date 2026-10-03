"""Núcleo da camada de persistência: pastas, identificadores,
backups diários e a ligação ao MySQL (`obter_conexao`).

Todos os outros ficheiros do pacote `repositorio` importam daqui."""

import logging
import os
import subprocess
from datetime import date, timedelta
from typing import cast

import mysql.connector

import config
import servidores

logger = logging.getLogger(__name__)


# Funções de leitura e escrita de ficheiros


def _garantir_pastas():
    """Garante que as pastas de dados e de cópias de segurança
    existem.

    Delega em `config.garantir_diretorios()` (Fase 1, v1.4.0): essa
    função é agora a única a decidir onde `dados/` e `backups/`
    vivem no disco (fora do repositório, para funcionar também como
    executável PyInstaller) e a criá-las. Chamada idempotente,
    seguro repetir sempre que se vai tocar em disco.
    """
    config.garantir_diretorios()


def criar_backup():
    """Faz um dump da base de dados MySQL para a pasta de cópias de
    segurança, usando `mysqldump`.

    Uma cópia por dia, criada ao arrancar antes de qualquer operação. Se
    já existir a cópia de hoje, não faz nada — a proteção é do estado com
    que o dia começou.

    A palavra-passe é passada ao `mysqldump` pela variável de ambiente
    `MYSQL_PWD`, não como argumento da linha de comandos — um argumento
    fica visível a qualquer utilizador que liste os processos em
    execução (`ps`), a variável de ambiente do subprocesso não.

    Devolve o caminho da cópia, ou None se o `mysqldump` falhar (binário
    ausente do PATH, credenciais erradas, ligação recusada) — uma falha
    no backup não deve impedir o arranque do sistema.
    """
    _garantir_pastas()

    destino = config.DIR_BACKUPS / f"dump_{date.today().isoformat()}.sql"
    # Formato de data ISO 8601, que é o formato de data mais
    # utilizado e recomendado para intercâmbio de dados entre sistemas.

    if destino.exists():
        return destino

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
        logger.warning(
            "Falha ao criar backup diário — mysqldump indisponível ou "
            "credenciais inválidas"
        )
        destino.unlink(missing_ok=True)
        return None

    logger.info("Backup diário criado: %s", destino.name)
    return destino


def limpar_backups_antigos(dias=None):
    """Elimina as cópias de segurança com mais dias do que o configurado.

    O prazo vem da configuração (30 dias por omissão), justificado pelo
    ciclo mensal do negócio: um erro de lançamento pode só ser detetado no
    fecho do mês seguinte.

    Devolve o número de cópias eliminadas.
    """
    if dias is None:
        dias = config.DIAS_BACKUP

    _garantir_pastas()
    limite = date.today() - timedelta(days=dias)
    eliminadas = 0

    for ficheiro in config.DIR_BACKUPS.glob("dump_*.sql"):
        texto = ficheiro.stem.replace("dump_", "")
        try:
            data_copia = date.fromisoformat(texto)
        except ValueError:
            continue

        if data_copia < limite:
            ficheiro.unlink()
            eliminadas += 1

    return eliminadas


# não pode ser menor que o limite, o sistema ignora e não trava a execução


# Identificadores (v1.8.0 — decisão D4, sem `contadores.json`)
#
# Cada prefixo pertence a uma tabela. O próximo número é calculado a
# partir do maior já gravado nessa tabela (regra "calcular, não
# guardar"): um registo semeado por SQL ou por uma migração fica
# contado sem mais nada — era por não o estar que a categoria
# CAT-001 e os itens ITD-001..003 davam chave duplicada.
# CNT e RSV partilham a tabela `ocupacoes`, por isso o MAX é sempre
# filtrado pelo prefixo.
_TABELA_POR_PREFIXO = {
    "PRO": "propriedades",
    "UNI": "unidades",
    "QRT": "quartos",
    "LUG": "lugares",
    "ATR": "responsavel_unidade",
    "RES": "responsaveis",
    "CLI": "clientes",
    "CNT": "ocupacoes",
    "RSV": "ocupacoes",
    "PRD": "produtos",
    "MOV": "movimentos",
    "REQ": "requisicoes",
    "ITR": "itens_requisicao",
    "DEV": "devolucoes",
    "ITD": "itens_devolucao",
    "DSP": "despesas",
    "IDP": "itens_despesa",
    "CAT": "categorias_despesa",
    "FOR": "fornecedores",
    "CFH": "configuracoes_historico",
}


def proximo_id(prefixo):
    """Devolve o próximo identificador livre para o prefixo indicado.

    Formato prefixo-sequencial com pelo menos três dígitos: UNI-001,
    CLI-014, PRO-1000 (decisão 2).

    O número é o maior já gravado na tabela do prefixo, mais um. NÃO
    reserva nada: duas chamadas seguidas sem gravar entre elas
    devolvem o mesmo ID — por isso cada ID é gravado logo a seguir a
    ser gerado (é o que todos os módulos já fazem). O MAX é numérico
    (CAST), para o PRO-1000 não ficar antes do PRO-999, como ficaria
    numa comparação de texto.

    Como não há DELETE no sistema, um número só volta a ficar livre
    depois do "Começar do zero" (TRUNCATE), que é o pretendido.

    Levanta ValueError se o prefixo não pertencer a nenhuma tabela.
    """
    tabela = _TABELA_POR_PREFIXO.get(prefixo)

    if tabela is None:
        raise ValueError(
            f"Prefixo de identificador desconhecido: {prefixo!r}."
        )

    # SUBSTRING do MySQL conta a partir de 1: "UNI-001" → o número
    # começa na posição len("UNI") + 2 = 5.
    inicio_numero = len(prefixo) + 2

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"SELECT MAX(CAST(SUBSTRING(id, %s) AS UNSIGNED)) "
            f"FROM {tabela} WHERE id LIKE %s",
            (inicio_numero, f"{prefixo}-%"),
        )
        ultimo = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    numero = int(cast(int, ultimo) or 0) + 1

    return f"{prefixo}-{numero:03d}"


# Ligação e funções por entidade (MySQL)
#
# Funções que falam diretamente com o MySQL, uma ligação nova por
# operação (mais simples e mais seguro em concorrência do que
# partilhar uma ligação global; o custo de abrir/fechar mais vezes é
# aceitável para o volume de dados de um hostel). Um bloco por
# entidade, todas já migradas (ver docstring do ficheiro).


def obter_conexao():
    """Abre uma ligação nova ao servidor MySQL, com as credenciais do
    config (lidas do .env — nunca escritas aqui nem no código-fonte).

    Antes de ligar confirma que o túnel SSH (se o servidor usar um)
    continua aberto e reabre-o se tiver caído — ver
    `servidores.garantir_tunel` (v1.8.2).
    """
    servidores.garantir_tunel(config.SERVIDOR)
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        # Python puro: os plugins de autenticação vêm no código; a
        # extensão em C procura DLLs que o PyInstaller não copia
        # (erro 2059 no .exe). Ver rep_esquema._ligar_sem_base.
        use_pure=True,
    )
