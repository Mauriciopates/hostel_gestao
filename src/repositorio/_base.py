"""Núcleo da camada de persistência: pastas, contadores de IDs,
backups diários e a ligação ao MySQL (`obter_conexao`).

Todos os outros ficheiros do pacote `repositorio` importam daqui."""

import json
import logging
import os
import subprocess
from datetime import date, timedelta

import mysql.connector

import config

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


def _ficheiro_contadores():
    """Caminho do ficheiro de contadores, calculado a cada chamada.

    Não é uma constante de módulo de propósito: se
    `config.garantir_diretorios()` cair no caminho de recurso (ex.
    sem permissão de escrita em C:\\), `config.DIR_DADOS` muda de
    valor — uma constante calculada uma vez à importação deste
    módulo ficaria presa ao caminho antigo.
    """
    return config.DIR_DADOS / "contadores.json"


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
                stdout=f,
                stderr=subprocess.PIPE,
                env=ambiente,
                check=True,
                text=True,
            )
    except (subprocess.CalledProcessError, FileNotFoundError):
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


def _carregar_contadores():
    """Lê o ficheiro dos contadores de identificadores.

    Devolve um dicionário de prefixo para último número atribuído. Se o
    ficheiro não existir, devolve um dicionário vazio.
    """
    _garantir_pastas()
    ficheiro = _ficheiro_contadores()

    if not ficheiro.exists():
        return {}

    with open(ficheiro, encoding="utf-8") as f:
        return json.load(f)


def _gravar_contadores(contadores):
    """Escreve o ficheiro dos contadores, com a mesma proteção do gravar.

      Exemplo de conteúdo do ficheiro:Json

      {
    "UNI": 22,
    "CLI": 14,
    "PRO": 7
      }

    Pelo que entendi esse arquivo é usado para manter o controle dos últimos
    identificadores usados para diferentes entidades, como unidades,
    clientes e produtos. Isso ajuda a garantir que cada nova entidade
    receba um identificador único e sequencial.

    """
    _garantir_pastas()
    ficheiro = _ficheiro_contadores()
    temporario = ficheiro.with_suffix(".tmp")

    try:
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(contadores, f, ensure_ascii=False, indent=2)

        temporario.replace(ficheiro)
    except OSError:
        logger.exception("Falha ao gravar contadores de ID")
        raise


def proximo_id(prefixo):
    """Devolve o próximo identificador para o prefixo indicado.

    Formato prefixo-sequencial com três dígitos: UNI-001, CLI-014
    (decisão 2).
    O contador é gravado antes de o identificador ser devolvido.

    Aqui ele busca o que foi gravado anteriormente exemplo: UNI-22
    CLI-14, PRO-7 e incrementa o número para o próximo id. mesmo que
    excluida se ja existiu UNI-22, o próximo id será UNI-23, garantindo que não
    há duplicidade de identificadores. Isso é importante para manter a
    integridade dos dados e evitar conflitos de identificação.


    """

    contadores = _carregar_contadores()
    numero = contadores.get(prefixo, 0) + 1
    contadores[prefixo] = numero
    _gravar_contadores(contadores)

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
    """
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )
