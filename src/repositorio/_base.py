"""Núcleo da camada de persistência: pastas, identificadores,
backups diários e a ligação ao MySQL (`obter_conexao`).

Todos os outros ficheiros do pacote `repositorio` importam daqui."""

import atexit
import logging
import os
import subprocess
import threading
import time
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
    "RLR": "rol_lavanderia_regras",
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


# Reaproveitamento de ligações (otimização de desempenho)
#
# MEDIÇÃO (09/10/2026, ferramentas/perfil): cada ecrã abria UMA ligação
# nova por query (Dashboard: 34 queries = 34 ligações, ~1,5 s dos 2,2 s
# totais; Dashboard › Financeiro: 29 ligações = 2,7 s de 3,6 s). As
# queries em si custavam 1-6 ms. Abrir uma ligação (handshake +
# autenticação, em Python puro) é o que pesa — e numa VM, com túnel SSH,
# pesa muito mais.
#
# Solução: `close()` deixa de fechar. A ligação volta a um conjunto de
# ligações livres e a próxima `obter_conexao()` reaproveita-a. Nenhum dos
# sítios que chamam `obter_conexao()` muda: continuam a fazer
# `conexao = obter_conexao()` ... `conexao.close()`.
#
# O que mantém o comportamento igual ao de antes:
# - Ao "fechar" faz-se ROLLBACK. Antes, fechar a ligação descartava
#   qualquer transação aberta; assim continua. Também evita ler dados
#   velhos: com REPEATABLE READ, uma transação deixada aberta por um
#   SELECT mostraria sempre o estado de quando começou.
# - Uma ligação só é entregue a QUEM a pediu: chamadas encadeadas
#   (uma função que chama outra a meio de uma transação) recebem
#   ligações diferentes, como antes.
# - A chave inclui servidor, porta, utilizador e base — trocar de
#   servidor (ou `config.DB_NAME`, como fazem os testes) nunca
#   reaproveita uma ligação de outro sítio.
# - Uma ligação parada há mais de _VERIFICAR_APOS_S é verificada antes de
#   ser reaproveitada; se morreu (túnel caído, timeout do MySQL), é
#   descartada e abre-se uma nova.
#
# Desligar tudo isto (para comparar ou em caso de problema): variável de
# ambiente HOSTEL_SEM_POOL=1.

_REUTILIZAR = os.environ.get("HOSTEL_SEM_POOL") != "1"
_MAX_LIVRES = 4            # ligações paradas guardadas por servidor/base
_VERIFICAR_APOS_S = 10     # parada há mais do que isto → confirma antes

_trinco = threading.Lock()
_livres = {}               # chave -> [(ligacao, instante_em_que_ficou_livre)]


def _fechar_silencioso(ligacao):
    try:
        ligacao.close()
    except Exception:  # noqa: BLE001 — já a descartar, o erro não interessa
        pass


def _chave_ligacao(base):
    return (config.DB_HOST, config.DB_PORT, config.DB_USER,
            base or config.DB_NAME)


def _abrir_nova(base):
    """Abre uma ligação nova ao MySQL (o que `obter_conexao` fazia)."""
    servidores.garantir_tunel(config.SERVIDOR)
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=base or config.DB_NAME,
        # Python puro: os plugins de autenticação vêm no código; a
        # extensão em C procura DLLs que o PyInstaller não copia
        # (erro 2059 no .exe). Ver rep_esquema._ligar_sem_base.
        use_pure=True,
    )


def _tirar_livre(chave):
    """Devolve uma ligação livre e viva para `chave`, ou None."""
    while True:
        with _trinco:
            livres = _livres.get(chave)
            if not livres:
                return None
            ligacao, desde = livres.pop()

        if time.monotonic() - desde > _VERIFICAR_APOS_S:
            try:
                viva = ligacao.is_connected()
            except Exception:  # noqa: BLE001
                viva = False
            if not viva:
                _fechar_silencioso(ligacao)
                continue

        return ligacao


class _LigacaoReutilizavel:
    """O que `obter_conexao()` devolve: a ligação real, mas com um
    `close()` que a devolve ao conjunto em vez de a fechar.

    Tudo o resto (cursor, commit, rollback, ...) passa direto para a
    ligação real. Depois do `close()` já não se pode usar — como antes.
    """

    def __init__(self, ligacao, chave):
        self._real = ligacao
        self._chave = chave

    def close(self):
        ligacao, self._real = self._real, None
        if ligacao is None:  # fechar duas vezes não faz mal
            return

        try:
            # Equivale a fechar sem ter feito commit.
            ligacao.rollback()
        except Exception:  # noqa: BLE001 — ligação morta ou com leitura
            # por acabar ("Unread result"): não serve para reaproveitar.
            _fechar_silencioso(ligacao)
            return

        with _trinco:
            livres = _livres.setdefault(self._chave, [])
            if len(livres) < _MAX_LIVRES:
                livres.append((ligacao, time.monotonic()))
                return

        _fechar_silencioso(ligacao)

    def __enter__(self):
        return self

    def __exit__(self, *excecao):
        self.close()
        return False

    def __getattr__(self, nome):
        ligacao = self.__dict__.get("_real")
        if ligacao is None:
            raise mysql.connector.Error("A ligação já foi fechada.")
        return getattr(ligacao, nome)


def fechar_ligacoes():
    """Fecha de vez todas as ligações livres (ao sair da aplicação, ou
    antes de apagar/recriar uma base)."""
    with _trinco:
        paradas = [lig for lista in _livres.values() for lig, _ in lista]
        _livres.clear()

    for ligacao in paradas:
        _fechar_silencioso(ligacao)


atexit.register(fechar_ligacoes)


def obter_conexao(base=None):
    """Devolve uma ligação ao servidor MySQL, com as credenciais do
    config (lidas do .env — nunca escritas aqui nem no código-fonte).

    `base` escolhe outra base do MESMO servidor (F5: a
    `config.DB_NAME_PRECHECKING`); por omissão, a do sistema.

    Reaproveita uma ligação livre quando há (ver o bloco acima); só abre
    uma nova — confirmando antes que o túnel SSH, se o servidor usar um,
    continua aberto (`servidores.garantir_tunel`, v1.8.2) — quando não
    há nenhuma. Quem chama continua a fazer `close()` no fim.
    """
    if not _REUTILIZAR:
        return _abrir_nova(base)

    chave = _chave_ligacao(base)
    ligacao = _tirar_livre(chave)

    if ligacao is None:
        ligacao = _abrir_nova(base)

    return _LigacaoReutilizavel(ligacao, chave)
