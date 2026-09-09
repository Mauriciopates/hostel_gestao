"""Camada de persistência. Único módulo que toca em ficheiros e na
base de dados.

Os módulos de negócio nunca leem nem gravam — pedem aqui. Foi isto
que permitiu migrar módulo a módulo de JSON para MySQL (decisão 1)
sem tocar nos módulos de negócio.

MIGRAÇÃO CONCLUÍDA (v1.1.0): todas as entidades falam diretamente
com o MySQL através de `obter_conexao()`, nas funções específicas
por entidade mais abaixo neste ficheiro. As antigas `carregar()` /
`gravar()` / `_estrutura_vazia()` / `_migrar()` e os auxiliares de
serialização (`_reconstituir_tipos`, `_serializar`, `_desserializar`)
que liam e escreviam `dados/dados.json` foram removidos por já não
terem nenhum consumidor — nem `main.py`/`cli.py` nem nenhum módulo
de negócio (grep confirmado em todo o projeto antes da remoção).

Módulos já migrados: propriedades, unidades (unidades, quartos,
lugares), responsaveis, clientes, contratos (ocupacoes, ocupacoes_mensal,
ocupacoes_airbnb), estoque (produtos, movimentos, requisicoes,
itens_requisicao, devolucoes, itens_devolucao).

`dados/contadores.json` continua ativo — `proximo_id()` ainda lê e
grava ali (decisão 1: é uma operação atómica sobre um ficheiro
próprio, não sobre a estrutura de dados que foi retirada).

`criar_backup()`/`limpar_backups_antigos()` passaram a fazer dump
da base MySQL via `mysqldump` (antes copiavam `dados.json`, que já
não existe) — ver docstring de `criar_backup()` para o porquê da
escolha e os requisitos (binário `mysqldump` no PATH).
"""

import json
import os
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import cast

import mysql.connector

import config

## Funções de leitura e escrita de ficheiros

# raiz do projeto = pasta que contém "src" e "testes" como irmãs;
# ancora-se na localização deste ficheiro, não na pasta corrente,
# para funcionar sempre da mesma forma seja qual for o sítio de
# onde o programa é arrancado (terminal na raiz, IDE com cwd em
# src/, etc.) — foi isto que causou a pasta "dados" duplicada
# dentro de src/.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

PASTA_DADOS = RAIZ_PROJETO / "dados"

# o path possibilita a leitura e escrita de ficheiros
# mesmo em sistemas operativos diferentes

PASTA_BACKUPS = RAIZ_PROJETO / "backups"
FICHEIRO_CONTADORES = PASTA_DADOS / "contadores.json"


def _garantir_pastas():
    """Cria as pastas de dados e de cópias de segurança se não existirem.

    Estas pastas estão fora do controlo de versões (decisão 13), pelo que
    não vêm com o repositório: têm de ser criadas na primeira execução.
    """
    PASTA_DADOS.mkdir(exist_ok=True)
    PASTA_BACKUPS.mkdir(exist_ok=True)


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

    destino = PASTA_BACKUPS / f"dump_{date.today().isoformat()}.sql"
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
        destino.unlink(missing_ok=True)
        return None

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

    for ficheiro in PASTA_BACKUPS.glob("dump_*.sql"):
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

    if not FICHEIRO_CONTADORES.exists():
        return {}

    with open(FICHEIRO_CONTADORES, encoding="utf-8") as f:
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
    temporario = FICHEIRO_CONTADORES.with_suffix(".tmp")

    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(contadores, f, ensure_ascii=False, indent=2)

    temporario.replace(FICHEIRO_CONTADORES)


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


## Ligação e funções por entidade (MySQL)
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


# --- propriedades -----------------------------------------------------


def inserir_propriedade(propriedade):
    """Insere uma propriedade nova na base de dados.

    Espera um dicionário com id, nome, morada, ativo — o mesmo formato
    que `propriedades.criar` já construía para a estrutura em memória.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO propriedades (id, nome, morada, ativo) "
            "VALUES (%s, %s, %s, %s)",
            (
                propriedade["id"],
                propriedade["nome"],
                propriedade["morada"],
                propriedade["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def procurar_propriedade(propriedade_id):
    """Procura a propriedade pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM propriedades WHERE id = %s", (propriedade_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha["ativo"] = bool(linha["ativo"])

    return linha


def listar_propriedades(incluir_inativas=False):
    """Devolve as propriedades ativas, ou todas se pedido."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativas:
            cursor.execute("SELECT * FROM propriedades")
        else:
            cursor.execute("SELECT * FROM propriedades WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    for linha in linhas:
        linha["ativo"] = bool(linha["ativo"])

    return linhas


def atualizar_propriedade(propriedade_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) da
    propriedade. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [propriedade_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE propriedades SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


def contar_unidades_ativas(propriedade_id):
    """Conta as unidades ativas associadas à propriedade indicada.

    Substitui o scan direto a dados["unidades"] que `propriedades.
    desativar` fazia antes, agora que essa tabela vive no MySQL.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM unidades "
            "WHERE propriedade_id = %s AND ativo = 1",
            (propriedade_id,),
        )
        total = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    return total


# --- unidades -----------------------------------------------------


def inserir_unidade(unidade):
    """Insere uma unidade nova na base de dados.

    Espera um dicionário com id, propriedade_id, nome, tipo, preco_base,
    preco_epoca_alta, multa_check_in_tardio, epoca_alta_ativa,
    em_manutencao, ativo — o mesmo formato que `unidades.criar` já
    construía para a estrutura em memória.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO unidades (id, propriedade_id, nome, tipo, "
            "preco_base, preco_epoca_alta, multa_check_in_tardio, "
            "epoca_alta_ativa, em_manutencao, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                unidade["id"],
                unidade["propriedade_id"],
                unidade["nome"],
                unidade["tipo"],
                unidade["preco_base"],
                unidade["preco_epoca_alta"],
                unidade["multa_check_in_tardio"],
                unidade["epoca_alta_ativa"],
                unidade["em_manutencao"],
                unidade["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_unidade(linha):
    """Converte os campos BOOLEAN (0/1 no MySQL) de uma linha de
    `unidades` para bool — os DECIMAL já chegam como Decimal.
    """
    linha["epoca_alta_ativa"] = bool(linha["epoca_alta_ativa"])
    linha["em_manutencao"] = bool(linha["em_manutencao"])
    linha["ativo"] = bool(linha["ativo"])
    return linha


def procurar_unidade(unidade_id):
    """Procura a unidade pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM unidades WHERE id = %s", (unidade_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_unidade(linha)

    return linha


def listar_unidades(incluir_inativas=False, propriedade_id=None, tipo=None):
    """Devolve as unidades, filtráveis por propriedade e por tipo —
    os filtros aplicam-se agora na própria consulta SQL, em vez de
    em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    if propriedade_id is not None:
        condicoes.append("propriedade_id = %s")
        valores.append(propriedade_id)

    if tipo is not None:
        condicoes.append("tipo = %s")
        valores.append(tipo)

    sql = "SELECT * FROM unidades"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_unidade(linha) for linha in linhas]


def atualizar_unidade(unidade_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) da
    unidade. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [unidade_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE unidades SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


# --- quartos --------------------------------------------------------


def inserir_quarto(quarto):
    """Insere um quarto novo na base de dados.

    Espera um dicionário com id, unidade_id, nome, privativo,
    limpeza_incluida, ativo.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO quartos (id, unidade_id, nome, privativo, "
            "limpeza_incluida, ativo) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                quarto["id"],
                quarto["unidade_id"],
                quarto["nome"],
                quarto["privativo"],
                quarto["limpeza_incluida"],
                quarto["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_quarto(linha):
    linha["privativo"] = bool(linha["privativo"])
    linha["limpeza_incluida"] = bool(linha["limpeza_incluida"])
    linha["ativo"] = bool(linha["ativo"])
    return linha


def procurar_quarto(quarto_id):
    """Procura o quarto pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM quartos WHERE id = %s", (quarto_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_quarto(linha)

    return linha


def listar_quartos(incluir_inativas=False, unidade_id=None):
    """Devolve os quartos, filtráveis por unidade — o filtro aplica-se
    na própria consulta SQL, em vez de em Python sobre a lista em
    memória.
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    if unidade_id is not None:
        condicoes.append("unidade_id = %s")
        valores.append(unidade_id)

    sql = "SELECT * FROM quartos"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_quarto(linha) for linha in linhas]


def atualizar_quarto(quarto_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    quarto. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [quarto_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE quartos SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


# --- lugares ----------------------------------------------------------


def inserir_lugar(lugar):
    """Insere um lugar novo na base de dados.

    Espera um dicionário com id, quarto_id, nome, tipo_cama,
    capacidade, ativo.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO lugares "
            "(id, quarto_id, nome, tipo_cama, capacidade, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                lugar["id"],
                lugar["quarto_id"],
                lugar["nome"],
                lugar["tipo_cama"],
                lugar["capacidade"],
                lugar["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_lugar(linha):
    linha["ativo"] = bool(linha["ativo"])
    return linha


def procurar_lugar(lugar_id):
    """Procura o lugar pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM lugares WHERE id = %s", (lugar_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_lugar(linha)

    return linha


def listar_lugares(incluir_inativas=False, quarto_id=None):
    """Devolve os lugares, filtráveis por quarto — o filtro aplica-se
    na própria consulta SQL, em vez de em Python sobre a lista em
    memória.
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    if quarto_id is not None:
        condicoes.append("quarto_id = %s")
        valores.append(quarto_id)

    sql = "SELECT * FROM lugares"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_lugar(linha) for linha in linhas]


def atualizar_lugar(lugar_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    lugar. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [lugar_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE lugares SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


# --- responsaveis -------------------------------------------------


def inserir_responsavel(responsavel):
    """Insere um responsável novo na base de dados.

    Espera um dicionário com id, nome, contacto, ativo — o mesmo
    formato que `responsaveis.criar` já construía para a estrutura
    em memória.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO responsaveis (id, nome, contacto, ativo) "
            "VALUES (%s, %s, %s, %s)",
            (
                responsavel["id"],
                responsavel["nome"],
                responsavel["contacto"],
                responsavel["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_responsavel(linha):
    linha["ativo"] = bool(linha["ativo"])
    return linha


def procurar_responsavel(responsavel_id):
    """Procura o responsável pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM responsaveis WHERE id = %s", (responsavel_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_responsavel(linha)

    return linha


def listar_responsaveis(incluir_inativos=False):
    """Devolve os responsáveis ativos, ou todos se pedido."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativos:
            cursor.execute("SELECT * FROM responsaveis")
        else:
            cursor.execute("SELECT * FROM responsaveis WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_responsavel(linha) for linha in linhas]


def atualizar_responsavel(responsavel_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    responsável. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [responsavel_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE responsaveis SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- atribuições (responsável <-> unidade) ---------------------------


def inserir_atribuicao(atribuicao):
    """Insere uma ligação nova entre um responsável e uma unidade.

    Espera um dicionário com id, responsavel_id, unidade_id, ativo.
    O par (responsavel_id, unidade_id) é UNIQUE na tabela — inserir
    um par já existente dá erro do MySQL; para reativar uma ligação
    que já existiu, usa `atualizar_atribuicao` sobre a linha
    encontrada por `procurar_atribuicao`, não esta função.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO responsavel_unidade "
            "(id, responsavel_id, unidade_id, ativo) "
            "VALUES (%s, %s, %s, %s)",
            (
                atribuicao["id"],
                atribuicao["responsavel_id"],
                atribuicao["unidade_id"],
                atribuicao["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_atribuicao(linha):
    linha["ativo"] = bool(linha["ativo"])
    return linha


def procurar_atribuicao(responsavel_id, unidade_id):
    """Procura a ligação entre um responsável e uma unidade, ativa
    ou não.

    Devolve a linha inativa também de propósito: é o que permite a
    `unidades.atribuir_responsavel` reativar uma ligação que já
    existiu, em vez de tentar inserir o mesmo par outra vez e
    chocar com a restrição UNIQUE. Devolve None se o par nunca
    tiver sido ligado.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM responsavel_unidade "
            "WHERE responsavel_id = %s AND unidade_id = %s",
            (responsavel_id, unidade_id),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_atribuicao(linha)

    return linha


def listar_atribuicoes(
    responsavel_id=None, unidade_id=None, incluir_inativas=False
):
    """Lista ligações responsável-unidade, filtráveis pelos dois
    lados — mesmo padrão de `listar_itens_requisicao`: os filtros
    aplicam-se na própria consulta SQL, e nenhum dos dois é
    obrigatório.
    """
    condicoes = []
    valores = []

    if responsavel_id is not None:
        condicoes.append("responsavel_id = %s")
        valores.append(responsavel_id)

    if unidade_id is not None:
        condicoes.append("unidade_id = %s")
        valores.append(unidade_id)

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    sql = "SELECT * FROM responsavel_unidade"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_atribuicao(linha) for linha in linhas]


def atualizar_atribuicao(atribuicao_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo)
    de uma atribuição. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [atribuicao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE responsavel_unidade SET {colunas} WHERE id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()


# --- clientes -------------------------------------------------------


def inserir_cliente(cliente):
    """Insere um cliente novo na base de dados.

    Espera um dicionário com todos os campos que `clientes.criar` já
    construía para a estrutura em memória (id, nome, tipo_documento,
    numero_documento, nif, email, telefone, morada, nacionalidade,
    estado_civil, data_nascimento, validade_documento,
    contacto_emergencia, incompleto, anonimizado, data_anonimizado,
    responsavel_anonimizado_id, ativo).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO clientes ("
            "id, nome, tipo_documento, numero_documento, nif, email, "
            "telefone, morada, nacionalidade, estado_civil, "
            "data_nascimento, validade_documento, contacto_emergencia, "
            "incompleto, anonimizado, data_anonimizado, "
            "responsavel_anonimizado_id, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s)",
            (
                cliente["id"],
                cliente["nome"],
                cliente["tipo_documento"],
                cliente["numero_documento"],
                cliente["nif"],
                cliente["email"],
                cliente["telefone"],
                cliente["morada"],
                cliente["nacionalidade"],
                cliente["estado_civil"],
                cliente["data_nascimento"],
                cliente["validade_documento"],
                cliente["contacto_emergencia"],
                cliente["incompleto"],
                cliente["anonimizado"],
                cliente["data_anonimizado"],
                cliente["responsavel_anonimizado_id"] or None,
                cliente["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_cliente(linha):
    """Converte os campos BOOLEAN (0/1 no MySQL) de uma linha de
    `clientes` para bool — as DATE já chegam como `date` — e repõe ""
    em 'responsavel_anonimizado_id' quando vier NULL (mesma
    convenção de string vazia usada em todo o sistema para "sem
    valor", já aplicada a 'ocupacoes.lugar_id' em
    `_normalizar_ocupacao`; tinha ficado por fazer aqui, apesar de
    `inserir_cliente` já converter "" para NULL na gravação).
    """
    linha["incompleto"] = bool(linha["incompleto"])
    linha["anonimizado"] = bool(linha["anonimizado"])
    linha["ativo"] = bool(linha["ativo"])

    if linha["responsavel_anonimizado_id"] is None:
        linha["responsavel_anonimizado_id"] = ""

    return linha


def procurar_cliente(cliente_id):
    """Procura o cliente pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM clientes WHERE id = %s", (cliente_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_cliente(linha)

    return linha


def listar_clientes(incluir_inativos=False, incompleto=None):
    """Devolve os clientes, filtráveis por estado e por incompletos —
    o filtro 'incompleto' aplica-se agora na própria consulta SQL,
    em vez de em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if not incluir_inativos:
        condicoes.append("ativo = 1")

    if incompleto is not None:
        condicoes.append("incompleto = %s")
        valores.append(incompleto)

    sql = "SELECT * FROM clientes"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_cliente(linha) for linha in linhas]


def atualizar_cliente(cliente_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    cliente. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [cliente_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE clientes SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


def cliente_com_nif_existe(nif, ignorar_id=None):
    """Verifica se o NIF indicado já pertence a outro cliente ativo.

    Substitui o scan direto a dados["clientes"] que
    `clientes._nif_pertence_a_outro_cliente` fazia antes, agora que
    essa tabela vive no MySQL. Só considera clientes ativos (mesma
    regra de negócio de sempre) e ignora, se indicado, o próprio
    cliente — para 'atualizar' não se recusar a si mesmo ao manter
    o NIF que já tinha.
    """
    sql = "SELECT COUNT(*) FROM clientes WHERE nif = %s AND ativo = 1"
    valores = [nif]

    if ignorar_id is not None:
        sql += " AND id != %s"
        valores.append(ignorar_id)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(sql, valores)
        total = cast(tuple, cursor.fetchone())[0]
    finally:
        conexao.close()

    return total > 0


# --- ocupacoes (base comum a contratos mensais e reservas Airbnb) -----


def inserir_ocupacao(ocupacao):
    """Insere uma ocupação (contrato mensal ou reserva Airbnb) na
    tabela base `ocupacoes`. Espera o mesmo dicionário que
    `contratos.criar_mensal`/`contratos.registar_airbnb` já
    construíam para a estrutura em memória.

    'lugar_id' é FK para `lugares` e fica NULL quando vier "" — uma
    ocupação sem lugar atribuído (mesmo caso já resolvido em
    `inserir_cliente` para 'responsavel_anonimizado_id').
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO ocupacoes (id, unidade_id, cliente_id, tipo, "
            "data_inicio, data_fim, lugar_id, aviso_documento, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                ocupacao["id"],
                ocupacao["unidade_id"],
                ocupacao["cliente_id"],
                ocupacao["tipo"],
                ocupacao["data_inicio"],
                ocupacao["data_fim"],
                ocupacao["lugar_id"] or None,
                ocupacao["aviso_documento"],
                ocupacao["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_ocupacao(linha):
    """Converte os BOOLEAN para bool e repõe "" em 'lugar_id' quando
    vier NULL — mesma convenção de string vazia usada em todo o
    sistema para "sem lugar atribuído".
    """
    linha["aviso_documento"] = bool(linha["aviso_documento"])
    linha["ativo"] = bool(linha["ativo"])

    if linha["lugar_id"] is None:
        linha["lugar_id"] = ""

    return linha


def procurar_ocupacao(ocupacao_id):
    """Procura a ocupação (base comum) pelo id. Devolve None se não
    existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ocupacoes WHERE id = %s", (ocupacao_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_ocupacao(linha)

    return linha


def listar_ocupacoes(
    incluir_inativas=False,
    unidade_id=None,
    cliente_id=None,
    tipo=None,
    aviso_documento=None,
):
    """Devolve as ocupações, filtráveis por unidade, cliente, tipo e
    aviso de documento — os filtros aplicam-se na própria consulta
    SQL, em vez de em Python sobre a lista em memória. Serve tanto
    `contratos.listar` (a listagem da interface) como as funções
    internas que antes percorriam dados["ocupacoes"] à mão
    (`contratos._ocupantes_mensal`, `contratos._existe_sobreposicao`,
    `unidades._estado_mensal`, `unidades._estado_airbnb`,
    `unidades.desativar`, `unidades.quarto_privativo_ocupado`).
    """
    condicoes = []
    valores = []

    if not incluir_inativas:
        condicoes.append("ativo = 1")

    if unidade_id is not None:
        condicoes.append("unidade_id = %s")
        valores.append(unidade_id)

    if cliente_id is not None:
        condicoes.append("cliente_id = %s")
        valores.append(cliente_id)

    if tipo is not None:
        condicoes.append("tipo = %s")
        valores.append(tipo)

    if aviso_documento is not None:
        condicoes.append("aviso_documento = %s")
        valores.append(aviso_documento)

    sql = "SELECT * FROM ocupacoes"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_ocupacao(linha) for linha in linhas]


def atualizar_ocupacao(ocupacao_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) da
    ocupação base. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [ocupacao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE ocupacoes SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- ocupacoes_mensal (especialização 1:1 do contrato mensal) ---------


def inserir_ocupacao_mensal(mensal):
    """Insere os dados específicos de um contrato mensal.

    'responsavel_desconto_renda_id' é FK para `responsaveis` e fica
    NULL quando vier "" — sem desconto, não há responsável a
    guardar (mesmo caso de 'lugar_id' em `inserir_ocupacao`).
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO ocupacoes_mensal (ocupacao_id, renda_calculada, "
            "renda_praticada, responsavel_desconto_renda_id, caucao, "
            "caucao_exige_confirmacao, motivo_alteracao_renda, "
            "motivo_alteracao_caucao, dia_vencimento) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                mensal["ocupacao_id"],
                mensal["renda_calculada"],
                mensal["renda_praticada"],
                mensal["responsavel_desconto_renda_id"] or None,
                mensal["caucao"],
                mensal["caucao_exige_confirmacao"],
                mensal["motivo_alteracao_renda"],
                mensal["motivo_alteracao_caucao"],
                mensal["dia_vencimento"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_ocupacao_mensal(linha):
    """Converte os BOOLEAN para bool e repõe "" nos campos de texto
    que vierem NULL (a DECIMAL já chega como Decimal, mesma
    convenção de `_normalizar_unidade`).
    """
    linha["caucao_exige_confirmacao"] = bool(linha["caucao_exige_confirmacao"])
    linha["duracao_abaixo_minima"] = bool(linha["duracao_abaixo_minima"])
    linha["aviso_previo_insuficiente"] = bool(
        linha["aviso_previo_insuficiente"]
    )

    for campo in (
        "responsavel_desconto_renda_id",
        "motivo_alteracao_renda",
        "motivo_alteracao_caucao",
        "motivo_encerramento",
    ):
        if linha[campo] is None:
            linha[campo] = ""

    return linha


def procurar_ocupacao_mensal(ocupacao_id):
    """Procura os dados específicos do contrato mensal pelo id da
    ocupação. Devolve None se não existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM ocupacoes_mensal WHERE ocupacao_id = %s",
            (ocupacao_id,),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_ocupacao_mensal(linha)

    return linha


def atualizar_ocupacao_mensal(ocupacao_id, campos):
    """Atualiza os campos indicados de `ocupacoes_mensal`. Converte
    "" para NULL em 'responsavel_desconto_renda_id' quando presente
    nos campos — é FK para `responsaveis`, e "" não é um id válido
    (mesmo caso já resolvido em `inserir_cliente`).
    """
    if not campos:
        return

    campos = dict(campos)

    if "responsavel_desconto_renda_id" in campos:
        campos["responsavel_desconto_renda_id"] = (
            campos["responsavel_desconto_renda_id"] or None
        )

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [ocupacao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE ocupacoes_mensal SET {colunas} WHERE ocupacao_id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()


# --- ocupacoes_airbnb (especialização 1:1 da reserva Airbnb) ----------


def inserir_ocupacao_airbnb(airbnb):
    """Insere os dados específicos de uma reserva Airbnb.

    'responsavel_desconto_preco_id' e 'responsavel_desconto_multa_id'
    são FK para `responsaveis` e ficam NULL quando vierem "" (mesmo
    caso de `inserir_ocupacao_mensal`). 'hora_chegada' é TIME na
    base — "" também vira NULL, e um valor "HH:MM" é aceite tal
    qual pelo conetor.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO ocupacoes_airbnb (ocupacao_id, preco_calculado, "
            "preco_praticado, responsavel_desconto_preco_id, "
            "check_in_tardio, hora_chegada, multa_calculada, "
            "multa_praticada, responsavel_desconto_multa_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                airbnb["ocupacao_id"],
                airbnb["preco_calculado"],
                airbnb["preco_praticado"],
                airbnb["responsavel_desconto_preco_id"] or None,
                airbnb["check_in_tardio"],
                airbnb["hora_chegada"] or None,
                airbnb["multa_calculada"],
                airbnb["multa_praticada"],
                airbnb["responsavel_desconto_multa_id"] or None,
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_ocupacao_airbnb(linha):
    """Converte BOOLEAN para bool, TIME (o conetor devolve
    `datetime.timedelta`, nunca texto) de volta para "HH:MM", e as
    duas FK de responsável — mais 'motivo_cancelamento' — de NULL
    para "" quando vazias.
    """
    linha["check_in_tardio"] = bool(linha["check_in_tardio"])

    hora_chegada = linha["hora_chegada"]

    if hora_chegada is None:
        linha["hora_chegada"] = ""
    else:
        total_segundos = int(hora_chegada.total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos = resto // 60
        linha["hora_chegada"] = f"{horas:02d}:{minutos:02d}"

    for campo in (
        "responsavel_desconto_preco_id",
        "responsavel_desconto_multa_id",
        "motivo_cancelamento",
    ):
        if linha[campo] is None:
            linha[campo] = ""

    return linha


def procurar_ocupacao_airbnb(ocupacao_id):
    """Procura os dados específicos da reserva Airbnb pelo id da
    ocupação. Devolve None se não existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM ocupacoes_airbnb WHERE ocupacao_id = %s",
            (ocupacao_id,),
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_ocupacao_airbnb(linha)

    return linha


def atualizar_ocupacao_airbnb(ocupacao_id, campos):
    """Atualiza os campos indicados de `ocupacoes_airbnb`. Converte
    "" para NULL nas duas FK de responsável quando presentes nos
    campos — mesma razão de `atualizar_ocupacao_mensal`.
    """
    if not campos:
        return

    campos = dict(campos)

    for campo_fk in (
        "responsavel_desconto_preco_id",
        "responsavel_desconto_multa_id",
    ):
        if campo_fk in campos:
            campos[campo_fk] = campos[campo_fk] or None

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [ocupacao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE ocupacoes_airbnb SET {colunas} WHERE ocupacao_id = %s",
            valores,
        )
        conexao.commit()
    finally:
        conexao.close()


# --- produtos -----------------------------------------------------


def inserir_produto(produto):
    """Insere um produto novo na base de dados.

    Espera um dicionário com id, nome, unidade_medida, stock_minimo,
    ativo — o mesmo formato que `estoque.criar_produto` já construía
    para a estrutura em memória.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO produtos (id, nome, unidade_medida, "
            "stock_minimo, ativo) VALUES (%s, %s, %s, %s, %s)",
            (
                produto["id"],
                produto["nome"],
                produto["unidade_medida"],
                produto["stock_minimo"],
                produto["ativo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_produto(linha):
    linha["ativo"] = bool(linha["ativo"])
    return linha


def procurar_produto(produto_id):
    """Procura o produto pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produtos WHERE id = %s", (produto_id,))
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_produto(linha)

    return linha


def listar_produtos(incluir_inativos=False):
    """Devolve os produtos ativos, ou todos se pedido."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        if incluir_inativos:
            cursor.execute("SELECT * FROM produtos")
        else:
            cursor.execute("SELECT * FROM produtos WHERE ativo = 1")
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_produto(linha) for linha in linhas]


def atualizar_produto(produto_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) do
    produto. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [produto_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE produtos SET {colunas} WHERE id = %s", valores)
        conexao.commit()
    finally:
        conexao.close()


# --- movimentos -----------------------------------------------------


def inserir_movimento(movimento):
    """Insere um movimento de stock (entrada, saída ou ajuste).

    'responsavel_id' e 'requisicao_id' são FK opcionais e ficam NULL
    quando vierem "" — mesmo caso já resolvido em `inserir_ocupacao`
    para 'lugar_id'. Movimentos são imutáveis (decisão 9): não há
    `atualizar_movimento` neste ficheiro, tal como `estoque.py` não
    tem `atualizar` nem `desativar` para esta entidade.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO movimentos (id, produto_id, tipo, quantidade, "
            "data, responsavel_id, requisicao_id, motivo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                movimento["id"],
                movimento["produto_id"],
                movimento["tipo"],
                movimento["quantidade"],
                movimento["data"],
                movimento["responsavel_id"] or None,
                movimento["requisicao_id"] or None,
                movimento["motivo"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_movimento(linha):
    """Repõe "" em 'responsavel_id', 'requisicao_id' e 'motivo' quando
    vierem NULL — mesma convenção de string vazia usada em todo o
    sistema para "sem valor".
    """
    for campo in ("responsavel_id", "requisicao_id", "motivo"):
        if linha[campo] is None:
            linha[campo] = ""

    return linha


def listar_movimentos(produto_id=None):
    """Devolve os movimentos de stock, filtráveis por produto — usada
    por `estoque.saldo_produto` para somar o histórico de um produto,
    em vez de percorrer `dados["movimentos"]` à mão.
    """
    sql = "SELECT * FROM movimentos"
    valores = []

    if produto_id is not None:
        sql += " WHERE produto_id = %s"
        valores.append(produto_id)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_movimento(linha) for linha in linhas]


# --- requisicoes ------------------------------------------------------


def inserir_requisicao(requisicao):
    """Insere uma requisição nova, no estado inicial "pendente".

    'responsavel_rejeicao_id' não entra no INSERT — só existe a
    partir de `rejeitar_requisicao`, muito depois da criação — e
    fica NULL por omissão, tal como a coluna permite. As restantes
    colunas nullable (data_envio, data_fecho) já vêm None do
    dicionário que `estoque.criar_requisicao` constrói.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO requisicoes (id, responsavel_id, estado, "
            "data_pedido, data_envio, data_fecho, motivo_rejeicao, "
            "observacoes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                requisicao["id"],
                requisicao["responsavel_id"],
                requisicao["estado"],
                requisicao["data_pedido"],
                requisicao["data_envio"],
                requisicao["data_fecho"],
                requisicao["motivo_rejeicao"],
                requisicao["observacoes"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def _normalizar_requisicao(linha):
    """Repõe "" em 'responsavel_rejeicao_id', 'motivo_rejeicao' e
    'observacoes' quando vierem NULL — mesma convenção de string
    vazia usada em todo o sistema para "sem valor".
    """
    for campo in ("responsavel_rejeicao_id", "motivo_rejeicao", "observacoes"):
        if linha[campo] is None:
            linha[campo] = ""

    return linha


def procurar_requisicao(requisicao_id):
    """Procura a requisição pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM requisicoes WHERE id = %s", (requisicao_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    if linha is not None:
        linha = _normalizar_requisicao(linha)

    return linha


def listar_requisicoes(estado=None, responsavel_id=None):
    """Devolve as requisições, filtráveis por estado e por
    responsável — o filtro por produto (decisão 20) cruza com
    `itens_requisicao` e continua a ser feito em `estoque.py`, tal
    como `contratos._nif_tem_contrato_mensal_ativo` cruza com
    `clientes` em vez de virar SQL aqui.
    """
    condicoes = []
    valores = []

    if estado is not None:
        condicoes.append("estado = %s")
        valores.append(estado)

    if responsavel_id is not None:
        condicoes.append("responsavel_id = %s")
        valores.append(responsavel_id)

    sql = "SELECT * FROM requisicoes"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return [_normalizar_requisicao(linha) for linha in linhas]


def atualizar_requisicao(requisicao_id, campos):
    """Atualiza os campos indicados de `requisicoes`. Converte "" para
    NULL em 'responsavel_rejeicao_id' quando presente nos campos — é
    FK para `responsaveis` (mesmo caso de
    `atualizar_ocupacao_mensal`).
    """
    if not campos:
        return

    campos = dict(campos)

    if "responsavel_rejeicao_id" in campos:
        campos["responsavel_rejeicao_id"] = (
            campos["responsavel_rejeicao_id"] or None
        )

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [requisicao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE requisicoes SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- itens_requisicao ---------------------------------------------


def inserir_item_requisicao(item):
    """Insere um item de requisição novo na base de dados.

    Espera um dicionário com id, requisicao_id, produto_id,
    quantidade_pedida, quantidade_enviada.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO itens_requisicao (id, requisicao_id, produto_id, "
            "quantidade_pedida, quantidade_enviada) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                item["id"],
                item["requisicao_id"],
                item["produto_id"],
                item["quantidade_pedida"],
                item["quantidade_enviada"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def procurar_item_requisicao(item_id):
    """Procura o item de requisição pelo id. Devolve None se não
    existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM itens_requisicao WHERE id = %s", (item_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    return linha


def listar_itens_requisicao(requisicao_id=None, produto_id=None):
    """Devolve os itens de requisição, filtráveis por requisição e por
    produto — os filtros aplicam-se na própria consulta SQL, em vez
    de em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if requisicao_id is not None:
        condicoes.append("requisicao_id = %s")
        valores.append(requisicao_id)

    if produto_id is not None:
        condicoes.append("produto_id = %s")
        valores.append(produto_id)

    sql = "SELECT * FROM itens_requisicao"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return linhas


def atualizar_item_requisicao(item_id, campos):
    """Atualiza os campos indicados de um item de requisição — usada
    por `estoque.enviar_requisicao` para gravar 'quantidade_enviada'.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [item_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE itens_requisicao SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- devolucoes -------------------------------------------------------


def inserir_devolucao(devolucao):
    """Insere uma devolução nova na base de dados.

    Espera um dicionário com id, requisicao_id, responsavel_id,
    estado, data_reportada, data_fecho.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO devolucoes (id, requisicao_id, responsavel_id, "
            "estado, data_reportada, data_fecho) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                devolucao["id"],
                devolucao["requisicao_id"],
                devolucao["responsavel_id"],
                devolucao["estado"],
                devolucao["data_reportada"],
                devolucao["data_fecho"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def procurar_devolucao(devolucao_id):
    """Procura a devolução pelo id. Devolve None se não existir."""
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM devolucoes WHERE id = %s", (devolucao_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    return linha


def listar_devolucoes(estado=None, requisicao_id=None, responsavel_id=None):
    """Devolve as devoluções, filtráveis por estado, requisição e
    responsável — os filtros aplicam-se na própria consulta SQL, em
    vez de em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if estado is not None:
        condicoes.append("estado = %s")
        valores.append(estado)

    if requisicao_id is not None:
        condicoes.append("requisicao_id = %s")
        valores.append(requisicao_id)

    if responsavel_id is not None:
        condicoes.append("responsavel_id = %s")
        valores.append(responsavel_id)

    sql = "SELECT * FROM devolucoes"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return linhas


def atualizar_devolucao(devolucao_id, campos):
    """Atualiza os campos indicados (dicionário nome -> valor novo) da
    devolução. Não faz nada se `campos` vier vazio.
    """
    if not campos:
        return

    colunas = ", ".join(f"{nome_campo} = %s" for nome_campo in campos)
    valores = list(campos.values()) + [devolucao_id]

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"UPDATE devolucoes SET {colunas} WHERE id = %s", valores
        )
        conexao.commit()
    finally:
        conexao.close()


# --- itens_devolucao ---------------------------------------------------


def inserir_item_devolucao(item):
    """Insere um item de devolução novo na base de dados.

    Espera um dicionário com id, devolucao_id, produto_id,
    quantidade.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO itens_devolucao (id, devolucao_id, produto_id, "
            "quantidade) VALUES (%s, %s, %s, %s)",
            (
                item["id"],
                item["devolucao_id"],
                item["produto_id"],
                item["quantidade"],
            ),
        )
        conexao.commit()
    finally:
        conexao.close()


def procurar_item_devolucao(item_id):
    """Procura o item de devolução pelo id. Devolve None se não
    existir.
    """
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM itens_devolucao WHERE id = %s", (item_id,)
        )
        linha = cast(dict, cursor.fetchone())
    finally:
        conexao.close()

    return linha


def listar_itens_devolucao(devolucao_id=None, produto_id=None):
    """Devolve os itens de devolução, filtráveis por devolução e por
    produto — os filtros aplicam-se na própria consulta SQL, em vez
    de em Python sobre a lista em memória.
    """
    condicoes = []
    valores = []

    if devolucao_id is not None:
        condicoes.append("devolucao_id = %s")
        valores.append(devolucao_id)

    if produto_id is not None:
        condicoes.append("produto_id = %s")
        valores.append(produto_id)

    sql = "SELECT * FROM itens_devolucao"
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)

    conexao = obter_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, valores)
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    return linhas