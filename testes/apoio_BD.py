"""Apoio comum aos testes que falam com uma base de dados MySQL real.

Desde a migração da Fase 2, os módulos de negócio (propriedades,
unidades, clientes, responsaveis, contratos, estoque) já não recebem
nem devolvem a estrutura `dados` em memória — cada operação grava e lê
diretamente da base de dados MySQL, através do `repositorio.py`. Os
testes automáticos deixaram, por isso, de poder simular um dicionário
`dados` à mão: têm de correr contra uma base de dados a sério.

Este ficheiro isola essa base de dados de teste da base de dados REAL
do aluno (a apontada por DB_NAME no .env, normalmente "hostel_gestao",
com os dados verdadeiros do hostel) de duas formas:

1. Antes de cada teste, os caminhos persistentes (`config.DIR_DADOS`,
   `config.DIR_BACKUPS`, `DIR_CONTRATOS`, ...) são redirecionados para
   uma pasta temporária, para os testes nunca escreverem PDFs,
   backups ou logs nas pastas reais. Os IDs (v1.8.0) já não dependem
   de ficheiro nenhum: o `repositorio.proximo_id()` calcula-os a
   partir do MAX(id) de cada tabela, por isso, com as tabelas vazias
   pelo TRUNCATE, cada teste começa em PRO-001, CLI-001, etc.

2. O `config.DB_NAME` é substituído por uma base de dados SEPARADA,
   só para testes — por omissão "hostel_gestao_teste", ou o nome
   indicado na variável de ambiente DB_NAME_TESTE, se existir. NUNCA
   aponta para a base de dados real: os testes correm sempre contra
   esta base de dados dedicada, criada automaticamente (base de dados
   + esquema completo) da primeira vez que os testes correm — não é
   preciso nenhum passo manual no MySQL Workbench antes de correr os
   testes.

Com esta base de dados dedicada, cada teste começa com todas as
tabelas vazias (TRUNCATE, antes de cada teste — ver `_limpar_tabelas`
abaixo): não há necessidade de simular dicionários "dados" à mão como
nos testes antigos (pré-migração MySQL). Cria-se o registo mesmo, com
as funções normais do módulo (propriedades.criar(...), por exemplo),
e ele fica na base de dados de teste até ao fim desse teste.

NOTA IMPORTANTE sobre identidade de objetos: `procurar_X()` faz sempre
um SELECT novo à base de dados — já não devolve o MESMO objeto Python
que `criar()` devolveu (ao contrário da versão em memória, onde
`procurar` percorria a mesma lista e devolvia o próprio dicionário lá
guardado). Por isso os testes migrados comparam com `assertEqual`
(valores iguais), nunca com `assertIs` (mesmo objeto) — e não podem
verificar "está na lista de dados" com `assertIn(x, dados["algo"])`,
porque essa lista em memória deixou de existir.

Uso: cada ficheiro de teste que precisa da base de dados faz
`from testes.apoio_BD import BaseMySQLTest` e cada classe de teste estende
`BaseMySQLTest` em vez de `unittest.TestCase`. Uma subclasse que
define o seu próprio `setUp` tem de chamar `super().setUp()` primeiro
(mesma convenção já usada em teste_contratos.py com `BaseContratosTest`).
"""

import logging
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import mysql.connector  # noqa: E402

import config  # noqa: E402
import migracoes  # noqa: E402
import repositorio  # noqa: E402
import utilizadores  # noqa: E402

# Logs durante os testes (v1.6.0, 23/09/2026).
#
# Os testes não passam pelo `main`/`main_gui`, por isso o
# `registo_logs.configurar()` nunca corre — e os logs dos módulos
# NUNCA vão para o `hostel.log` verdadeiro. Vão para um ficheiro
# próprio, só dos testes:
#
#     testes/teste_logs/testes.log
#
# - A pasta é criada se não existir.
# - O ficheiro é REESCRITO a cada execução da suite (mode="w"): mostra
#   só a última corrida. Se acumulasse, crescia depressa — os testes
#   provocam de propósito centenas de recusas e erros.
# - Serve para investigar um teste que falhou: o que os módulos
#   registaram até ao erro. NÃO é para ler como o log da operação —
#   está cheio de WARNING/CRITICAL provocados de propósito.
# - Nada vai para o ecrã: sem isto, o Python imprimia todos os
#   WARNING/ERROR na saída dos testes.
# - O `self.assertLogs(...)` continua a funcionar (por isso não se usa
#   `logging.disable`). As linhas apanhadas por um `assertLogs` ficam
#   presas nesse teste e não chegam a este ficheiro — é o normal.
# - `testes/teste_logs/` está no `.gitignore`: é resultado local.
#
# Só se configura se a raiz não tiver já um destino — para não
# interferir com uma configuração feita de propósito.
PASTA_LOGS_TESTE = Path(__file__).resolve().parent / "teste_logs"

if not logging.getLogger().handlers:
    PASTA_LOGS_TESTE.mkdir(exist_ok=True)

    _handler_testes = logging.FileHandler(
        PASTA_LOGS_TESTE / "testes.log", mode="w", encoding="utf-8"
    )
    _handler_testes.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    logging.getLogger().addHandler(_handler_testes)
    logging.getLogger().setLevel(logging.INFO)

    # Mesmas bibliotecas silenciadas no `registo_logs.py`.
    for _nome in ("mysql.connector", "matplotlib", "PIL"):
        logging.getLogger(_nome).setLevel(logging.WARNING)

_logger_testes = logging.getLogger("testes")

# Nome da base de dados de teste — nunca a real. Pode ser trocado com
# a variável de ambiente DB_NAME_TESTE (por exemplo, para isolar
# execuções concorrentes ou usar um servidor de CI diferente).
DB_NAME_TESTE = os.environ.get("DB_NAME_TESTE", "hostel_gestao_teste")

# Esquema das tabelas (v1.8.0, INST-03): lido do ficheiro OFICIAL
# `src/bd/esquema.sql` — a mesma fonte que a aplicação usa para criar
# uma base nova (decisão D7). Até à v1.7.0 havia aqui uma cópia à mão
# do esquema, que tinha de ser replicada a cada mudança (e já não tinha
# 4 índices da base real). Uma lista de instruções CREATE TABLE IF NOT
# EXISTS, pela ordem das chaves estrangeiras.
_ESQUEMA_TABELAS = repositorio.instrucoes_esquema()

# Migrações que MUDAM A ESTRUTURA de uma tabela que já existe. O
# CREATE TABLE IF NOT EXISTS do esquema não toca numa tabela já criada,
# por isso uma base de teste antiga ficava com a forma velha. Estas
# correm (idempotentes: numa base já em dia não fazem nada) sempre que
# a base de teste é preparada. As migrações de DADOS (0001, 0002) não
# entram: a base de teste quer as tabelas vazias (decisão 4, passo C).
_MIGRACOES_DE_ESTRUTURA = (
    "0003_avisos_privacidade_fks",
    "0004_consentimento_comunicacoes",
    "0005_despesa_unidade_atribuida",
    "0006_propriedade_senhorio",
)
_INSTRUCOES_ESTRUTURA = [
    instrucao
    for nome, instrucoes in migracoes.MIGRACOES
    if nome in _MIGRACOES_DE_ESTRUTURA
    for instrucao in instrucoes
]

# Ordem de TRUNCATE segura para chaves estrangeiras: as tabelas
# "filhas" antes das "mães" — o inverso da ordem de criação acima.
# (Na prática, com SET FOREIGN_KEY_CHECKS=0 a ordem deixa de importar
# a estrita correção das FKs durante o TRUNCATE, mas mantém-se
# explícita e documentada, para clareza de quem lê.)
_TABELAS_EM_ORDEM_DE_LIMPEZA = (
    # v1.8.0 — controlo das migrações (sem FKs)
    "migracoes_aplicadas",
    # v1.6.0 — avisos antes de textos_legais (FK composta)
    "avisos_privacidade",
    "textos_legais",
    # Despesas (tabelas novas — filhas primeiro)
    "itens_despesa",
    "despesas",
    "fornecedores",
    "categorias_despesa",
    # Configurações
    "configuracoes_historico",
    "configuracoes",
    # Stock (filhas primeiro)
    "rol_lavanderia_regras",
    "itens_devolucao",
    "devolucoes",
    "itens_requisicao",
    "movimentos",
    "requisicoes",
    "produtos",
    # Ocupações
    "ocupacoes_airbnb",
    "ocupacoes_mensal",
    "ocupacoes",
    # Clientes e responsáveis
    "clientes",
    "responsavel_unidade",
    # Estrutura física
    "lugares",
    "quartos",
    "unidades",
    "propriedades",
    # Responsáveis (por último — é FK de muitas tabelas)
    "responsaveis",
)

# Nomes das tabelas do esquema oficial, para a verificação leve do
# `_garantir_esquema_atualizado()` (Alteração B). Calculado uma única
# vez, no import do módulo.
_TABELAS_ESPERADAS = tuple(repositorio.tabelas_do_esquema())


def _obter_conexao_servidor():
    """Liga ao servidor MySQL sem escolher nenhuma base de dados —
    só para poder criar a base de dados de teste, se ainda não
    existir. Usa as mesmas credenciais do .env (config.DB_*).
    """
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def _garantir_base_de_teste():
    """Cria a base de dados de teste e o esquema completo, se ainda
    não existirem — idempotente (CREATE DATABASE/TABLE IF NOT EXISTS),
    por isso é seguro chamar em cada execução dos testes. NUNCA cria
    nem altera nada na base de dados real (config.DB_NAME) — só nesta,
    dedicada aos testes.
    """
    conexao = _obter_conexao_servidor()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_NAME_TESTE} "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE {DB_NAME_TESTE}")

        for comando in _ESQUEMA_TABELAS:
            cursor.execute(comando)

        # Restos do último teste podiam apontar para pessoas que já não
        # existem e impedir as FKs novas. É a base de TESTE: cada
        # `setUp` esvazia tudo de qualquer forma.
        cursor.execute("TRUNCATE TABLE avisos_privacidade")
        for comando in _INSTRUCOES_ESTRUTURA:
            cursor.execute(comando)

        conexao.commit()
    finally:
        conexao.close()


def _garantir_esquema_atualizado():
    """Versão leve do `_garantir_base_de_teste`, para correr em cada
    `setUp` (Alteração B, combinada com o aluno em 22/09/2026).

    PORQUÊ: quando o `_ESQUEMA_TABELAS` ganha tabelas novas (caso da
    v1.6.0, com `textos_legais` e `avisos_privacidade`), a base de
    dados de teste pode já existir criada com o esquema antigo. O
    `_garantir_base_de_teste()` só corre uma vez por sessão (no
    `setUpClass`), por isso não chega para reparar esse caso. Esta
    função é chamada no início de cada `setUp`, verifica se TODAS as
    tabelas esperadas existem na base de teste, e só corre o
    esquema completo se faltar alguma.

    CUSTO: um `SHOW TABLES` por teste. Se o esquema estiver completo
    (caso normal), é a única coisa que acontece — não há custo a
    pagar. Só quando falta alguma tabela é que o esquema completo
    corre, e mesmo aí só uma vez: a partir daí as tabelas já
    existem e os testes seguintes só fazem o `SHOW TABLES`.

    NUNCA cria nem altera nada na base de dados real — só olha para
    a base de teste (`config.DB_NAME`, que o `setUp` já substituiu
    por `DB_NAME_TESTE` antes de chamar isto).
    """
    try:
        conexao = repositorio.obter_conexao()
    except mysql.connector.Error:
        # Base de dados de teste ainda não existe (primeira execução
        # de sempre, sem `setUpClass` a ter passado por cá). Deixa o
        # `_garantir_base_de_teste()` tratar disso.
        _garantir_base_de_teste()
        return

    try:
        cursor = conexao.cursor()
        cursor.execute("SHOW TABLES")

        existentes = set()

        for (nome_tabela,) in cursor.fetchall():
            existentes.add(str(nome_tabela))
    finally:
        conexao.close()

    if not set(_TABELAS_ESPERADAS).issubset(existentes):
        _garantir_base_de_teste()


class BaseMySQLTest(unittest.TestCase):
    """Preparação comum aos testes que falam com uma base de dados
    MySQL real (módulos já migrados na Fase 2).

    Uma subclasse que define o seu próprio setUp() tem de chamar
    super().setUp() PRIMEIRO, antes de criar qualquer fixture — senão
    a base de dados de teste e as pastas temporárias ainda não estão
    prontas.
    """

    @classmethod
    def setUpClass(cls):
        _garantir_base_de_teste()

    def setUp(self):
        # 0. Marcador no `testes/teste_logs/testes.log`: sem ele não se
        # sabia que teste gerou cada linha.
        _logger_testes.info("=== %s ===", self.id())

        # 1. Base de dados: aponta para a de teste, nunca para a real.
        # repositorio.py faz "import config" e lê config.DB_NAME em
        # cada obter_conexao() — como é o mesmo objeto módulo (Python
        # só importa cada módulo uma vez), alterar config.DB_NAME aqui
        # é suficiente para redirecionar repositorio.py também.
        self._db_original = config.DB_NAME
        config.DB_NAME = DB_NAME_TESTE

        # 1b. Versão leve do esquema (Alteração B): garante que as
        # tabelas todas existem antes do TRUNCATE. Só corre o esquema
        # completo se faltar alguma — ver a docstring de
        # `_garantir_esquema_atualizado` para o porquê.
        _garantir_esquema_atualizado()

        self._limpar_tabelas()

        # 1c. Bloqueio do login (v1.8.0): as falhas contam-se num
        # dicionário do módulo `utilizadores`, que passaria de um
        # teste para o seguinte (e "ana" é usada em muitos).
        utilizadores.limpar_tentativas()

        # 2. Pastas persistentes numa pasta temporária (PDFs,
        # backups, logs), mesma convenção de
        # teste_repositorio.BaseRepositorio. Os IDs já não usam
        # ficheiro (v1.8.0): vêm do MAX(id) das tabelas limpas acima.
        #
        # A partir da v1.6.0, os caminhos vivem em `config.DIR_DADOS`
        # e `config.DIR_BACKUPS` (a `repositorio.py` deixou de os
        # expor como constantes próprias — ver decisão de 15/09/2026
        # em `repositorio.py`, no docstring do ficheiro).
        self._pasta = Path(tempfile.mkdtemp())
        self._caminhos_originais = (
            config.DIR_DADOS,
            config.DIR_BACKUPS,
            config.DIR_CONTRATOS,
            config.DIR_RELATORIOS,
            config.DIR_LOGS,
        )
        config.DIR_DADOS = self._pasta / "dados"
        config.DIR_BACKUPS = self._pasta / "backups"
        config.DIR_CONTRATOS = self._pasta / "contratos"
        config.DIR_RELATORIOS = self._pasta / "relatorios"
        config.DIR_LOGS = self._pasta / "logs"

    def tearDown(self):
        config.DB_NAME = self._db_original

        (
            config.DIR_DADOS,
            config.DIR_BACKUPS,
            config.DIR_CONTRATOS,
            config.DIR_RELATORIOS,
            config.DIR_LOGS,
        ) = self._caminhos_originais

        shutil.rmtree(self._pasta, ignore_errors=True)

    def _limpar_tabelas(self):
        """Esvazia todas as tabelas da base de dados de teste, antes
        de cada teste — cada teste começa sempre do zero, tal como os
        testes antigos começavam sempre com um dicionário "dados"
        novo.
        """
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for tabela in _TABELAS_EM_ORDEM_DE_LIMPEZA:
                cursor.execute(f"TRUNCATE TABLE {tabela}")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            conexao.commit()
        finally:
            conexao.close()


class BaseTermosTest(BaseMySQLTest):
    """Fornece uma versão em vigor de cada um dos três documentos
    legais, pronta a usar pelos testes de `termos`.

    PORQUÊ (v1.6.0): com as tabelas `textos_legais` e
    `avisos_privacidade` vazias — o estado que `BaseMySQLTest.setUp`
    deixa depois do TRUNCATE — qualquer chamada a
    `termos.texto_em_vigor(tipo)` rebenta com ValueError. E o seed
    da migração não sobrevive a um TRUNCATE. Qualquer teste que
    dependa de `texto_em_vigor` ou de `verificar`/`registar` tem de
    herdar desta classe, não de `BaseMySQLTest` diretamente.

    Publica uma versão de cada tipo do ENUM, via `termos.publicar` —
    não por INSERT direto — para respeitar a regra de negócio (a
    transação UPDATE + INSERT dentro de `publicar_texto`, e a
    validação de que só um Master pode publicar). Isso implica criar
    um Master primeiro: como `BaseMySQLTest.setUp` deixa as tabelas
    todas vazias, sem um responsável ativo não há autor para o
    `publicar`.

    As versões publicadas são "1.0" para cada documento — o mesmo
    número para os três de propósito, porque um teste que queira
    distinguir as versões entre documentos não deve depender do que
    esta classe publica. Se um teste precisar de uma versão
    diferente (para testar uma republicação, por exemplo), publica-a
    ele mesmo.

    O Master criado fica acessível em `self.master`, para os testes
    o reutilizarem como autor em `termos.publicar` ou em chamadas a
    outros módulos que exijam autoria.
    """

    # Versão publicada por omissão — mesma para os três documentos.
    # Ver a nota da docstring sobre não depender disto.
    VERSAO_INICIAL = "1.0"

    # Textos mínimos para cada documento. Não precisam de ser
    # realistas — os testes de `termos` não validam o conteúdo, só
    # o versionamento e o registo da aceitação.
    TEXTOS = {
        "confidencialidade": (
            "Termo de confidencialidade e uso do sistema — versão 1.0."
        ),
        "privacidade_hospede": (
            "Informação de privacidade a hóspedes — versão 1.0."
        ),
        "privacidade_colaborador": (
            "Informação de privacidade a colaboradores — versão 1.0."
        ),
    }

    def setUp(self):
        super().setUp()

        import responsaveis
        import termos

        # Master primeiro — sem ele, `termos.publicar` recusa
        # (valida o autor contra `Master`). `responsaveis.criar` é
        # o caminho normal, mesma função que o bootstrap usa.
        self.master = responsaveis.criar(
            nome="Master de Teste",
            contacto="",
            tipo_utilizador="Master",
        )

        # Uma versão em vigor de cada tipo de documento, via
        # `termos.publicar` — o caminho de negócio, não INSERT
        # direto. `termos.publicar` recebe o dict do autor.
        for tipo, texto in self.TEXTOS.items():
            termos.publicar(
                tipo=tipo,
                versao=self.VERSAO_INICIAL,
                texto=texto,
                autor=self.master,
            )


# ---------------------------------------------------------------------
# Pré check-in (F5): a base `hostel_prechecking` de TESTE
# ---------------------------------------------------------------------

DB_NAME_PRECHECKING_TESTE = os.environ.get(
    "DB_NAME_PRECHECKING_TESTE", "hostel_prechecking_teste"
)


def instrucoes_esquema_prechecking():
    """As instruções do `src/bd/esquema_prechecking.sql`, sem
    comentários (há ";" dentro deles), uma por elemento."""
    linhas = []
    for linha in config.FICHEIRO_ESQUEMA_PRECHECKING.read_text(
        encoding="utf-8"
    ).splitlines():
        sem_comentario = linha.split("--", 1)[0].rstrip()
        if sem_comentario:
            linhas.append(sem_comentario)
    texto = "\n".join(linhas)
    return [i.strip() for i in texto.split(";") if i.strip()]


def _garantir_base_prechecking_teste():
    conexao = _obter_conexao_servidor()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_NAME_PRECHECKING_TESTE} "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE {DB_NAME_PRECHECKING_TESTE}")
        for comando in instrucoes_esquema_prechecking():
            cursor.execute(comando)
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE pendentes")
        cursor.execute("TRUNCATE TABLE tokens")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conexao.commit()
    finally:
        conexao.close()


class BasePreCheckinTest(BaseTermosTest):
    """`BaseTermosTest` + a caixa de entrada do pré check-in, vazia, na
    base `hostel_prechecking_teste` (nunca na real)."""

    def setUp(self):
        super().setUp()
        self._db_prechecking_original = config.DB_NAME_PRECHECKING
        config.DB_NAME_PRECHECKING = DB_NAME_PRECHECKING_TESTE
        _garantir_base_prechecking_teste()

    def tearDown(self):
        config.DB_NAME_PRECHECKING = self._db_prechecking_original
        super().tearDown()
