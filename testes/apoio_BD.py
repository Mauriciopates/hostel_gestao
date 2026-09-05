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

1. Antes de cada teste, `repositorio.config.DB_NAME` é substituído por
   uma base de dados SEPARADA, só para testes — por omissão
   "hostel_gestao_teste", ou o nome indicado na variável de ambiente
   DB_NAME_TESTE, se existir. NUNCA aponta para a base de dados real:
   os testes correm sempre contra esta base de dados dedicada, criada
   automaticamente (base de dados + esquema completo) da primeira vez
   que os testes correm — não é preciso nenhum passo manual no
   MySQL Workbench antes de correr os testes.

2. Tal como em teste_repositorio.py, os caminhos de
   `repositorio.PASTA_DADOS` / `FICHEIRO_CONTADORES` são redirecionados
   para uma pasta temporária a cada teste — para `repositorio.
   proximo_id()` (que continua a gravar num ficheiro, decisão 1, por
   ainda não ter sido migrado) nunca tocar no dados/contadores.json
   real. Cada teste começa, por isso, com os contadores a zero (PRO-001,
   CLI-001, etc.), tal como acontecia nos testes antigos em memória.

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
`from apoio_bd import BaseMySQLTest` e cada classe de teste estende
`BaseMySQLTest` em vez de `unittest.TestCase`. Uma subclasse que
define o seu próprio `setUp` tem de chamar `super().setUp()` primeiro
(mesma convenção já usada em teste_contratos.py com `BaseContratosTest`).
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import mysql.connector

import config
import repositorio

# Nome da base de dados de teste — nunca a real. Pode ser trocado com
# a variável de ambiente DB_NAME_TESTE (por exemplo, para isolar
# execuções concorrentes ou usar um servidor de CI diferente).
DB_NAME_TESTE = os.environ.get("DB_NAME_TESTE", "hostel_gestao_teste")

# Esquema físico das tabelas usadas pelos módulos já migrados para
# MySQL — cópia de claude/esquema_mysql.sql (ficheiro do projeto),
# sem o CREATE DATABASE/USE, e com IF NOT EXISTS em cada tabela para
# a criação ser sempre segura repetir. Se o esquema mudar no ficheiro
# principal, replicar a alteração aqui também.
_ESQUEMA_TABELAS = """
CREATE TABLE IF NOT EXISTS propriedades (
    id      VARCHAR(10)  PRIMARY KEY,
    nome    VARCHAR(150) NOT NULL,
    morada  VARCHAR(255),
    ativo   BOOLEAN      NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS unidades (
    id                     VARCHAR(10)   PRIMARY KEY,
    propriedade_id         VARCHAR(10)   NOT NULL,
    nome                   VARCHAR(150)  NOT NULL,
    tipo                   ENUM('mensal', 'airbnb') NOT NULL,
    preco_base             DECIMAL(10,2) NOT NULL,
    preco_epoca_alta       DECIMAL(10,2) NOT NULL,
    multa_check_in_tardio  DECIMAL(10,2) NOT NULL,
    epoca_alta_ativa       BOOLEAN       NOT NULL DEFAULT 0,
    em_manutencao          BOOLEAN       NOT NULL DEFAULT 0,
    ativo                  BOOLEAN       NOT NULL DEFAULT 1,
    FOREIGN KEY (propriedade_id) REFERENCES propriedades(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS quartos (
    id                VARCHAR(10)  PRIMARY KEY,
    unidade_id        VARCHAR(10)  NOT NULL,
    nome              VARCHAR(100) NOT NULL,
    privativo         BOOLEAN      NOT NULL DEFAULT 0,
    limpeza_incluida  BOOLEAN      NOT NULL DEFAULT 0,
    ativo             BOOLEAN      NOT NULL DEFAULT 1,
    FOREIGN KEY (unidade_id) REFERENCES unidades(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lugares (
    id          VARCHAR(10)  PRIMARY KEY,
    quarto_id   VARCHAR(10)  NOT NULL,
    nome        VARCHAR(100) NOT NULL,
    capacidade  INT          NOT NULL CHECK (capacidade >= 1),
    ativo       BOOLEAN      NOT NULL DEFAULT 1,
    FOREIGN KEY (quarto_id) REFERENCES quartos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS responsaveis (
    id        VARCHAR(10)  PRIMARY KEY,
    nome      VARCHAR(150) NOT NULL,
    contacto  VARCHAR(100),
    ativo     BOOLEAN      NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS clientes (
    id                          VARCHAR(10)  PRIMARY KEY,
    nome                        VARCHAR(150) NOT NULL,
    tipo_documento              ENUM('Cartão de Cidadão', 'Passaporte', 'Título de Residência', 'Outro') NOT NULL,
    numero_documento            VARCHAR(50)  NOT NULL,
    nif                         VARCHAR(20),
    email                       VARCHAR(150),
    telefone                    VARCHAR(30),
    morada                      VARCHAR(255),
    nacionalidade               VARCHAR(100),
    estado_civil                VARCHAR(30),
    data_nascimento             DATE,
    validade_documento          DATE,
    contacto_emergencia         VARCHAR(150),
    incompleto                  BOOLEAN      NOT NULL DEFAULT 0,
    anonimizado                 BOOLEAN      NOT NULL DEFAULT 0,
    data_anonimizado            DATE,
    responsavel_anonimizado_id  VARCHAR(10),
    ativo                       BOOLEAN      NOT NULL DEFAULT 1,
    FOREIGN KEY (responsavel_anonimizado_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ocupacoes (
    id               VARCHAR(10) PRIMARY KEY,
    unidade_id       VARCHAR(10) NOT NULL,
    cliente_id       VARCHAR(10) NOT NULL,
    tipo             ENUM('mensal', 'airbnb') NOT NULL,
    data_inicio      DATE        NOT NULL,
    data_fim         DATE,
    lugar_id         VARCHAR(10),
    aviso_documento  BOOLEAN     NOT NULL DEFAULT 0,
    ativo            BOOLEAN     NOT NULL DEFAULT 1,
    FOREIGN KEY (unidade_id) REFERENCES unidades(id),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (lugar_id) REFERENCES lugares(id),
    CHECK (data_fim IS NULL OR data_fim > data_inicio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ocupacoes_mensal (
    ocupacao_id                     VARCHAR(10)   PRIMARY KEY,
    renda_calculada                 DECIMAL(10,2) NOT NULL,
    renda_praticada                 DECIMAL(10,2) NOT NULL,
    responsavel_desconto_renda_id   VARCHAR(10),
    caucao                          DECIMAL(10,2) NOT NULL,
    caucao_exige_confirmacao        BOOLEAN       NOT NULL DEFAULT 0,
    motivo_alteracao_renda          VARCHAR(255),
    motivo_alteracao_caucao         VARCHAR(255),
    dia_vencimento                  INT           NOT NULL CHECK (dia_vencimento BETWEEN 1 AND 28),
    motivo_encerramento             VARCHAR(255),
    duracao_abaixo_minima           BOOLEAN       NOT NULL DEFAULT 0,
    aviso_previo_insuficiente       BOOLEAN       NOT NULL DEFAULT 0,
    FOREIGN KEY (ocupacao_id) REFERENCES ocupacoes(id),
    FOREIGN KEY (responsavel_desconto_renda_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ocupacoes_airbnb (
    ocupacao_id                     VARCHAR(10)   PRIMARY KEY,
    preco_calculado                 DECIMAL(10,2) NOT NULL,
    preco_praticado                 DECIMAL(10,2) NOT NULL,
    responsavel_desconto_preco_id   VARCHAR(10),
    check_in_tardio                 BOOLEAN       NOT NULL DEFAULT 0,
    hora_chegada                    TIME,
    multa_calculada                 DECIMAL(10,2) NOT NULL,
    multa_praticada                 DECIMAL(10,2) NOT NULL,
    responsavel_desconto_multa_id   VARCHAR(10),
    motivo_cancelamento             VARCHAR(255),
    FOREIGN KEY (ocupacao_id) REFERENCES ocupacoes(id),
    FOREIGN KEY (responsavel_desconto_preco_id) REFERENCES responsaveis(id),
    FOREIGN KEY (responsavel_desconto_multa_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS produtos (
    id              VARCHAR(10)  PRIMARY KEY,
    nome            VARCHAR(150) NOT NULL,
    unidade_medida  VARCHAR(30)  NOT NULL,
    stock_minimo    INT          NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    ativo           BOOLEAN      NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS requisicoes (
    id                        VARCHAR(10) PRIMARY KEY,
    responsavel_id            VARCHAR(10) NOT NULL,
    estado                    ENUM('pendente', 'enviada', 'fechada', 'rejeitada') NOT NULL DEFAULT 'pendente',
    data_pedido               DATE        NOT NULL,
    data_envio                DATE,
    data_fecho                DATE,
    responsavel_rejeicao_id   VARCHAR(10),
    motivo_rejeicao           VARCHAR(255),
    observacoes               VARCHAR(255),
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id),
    FOREIGN KEY (responsavel_rejeicao_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS itens_requisicao (
    id                  VARCHAR(10) PRIMARY KEY,
    requisicao_id       VARCHAR(10) NOT NULL,
    produto_id          VARCHAR(10) NOT NULL,
    quantidade_pedida   INT         NOT NULL CHECK (quantidade_pedida > 0),
    quantidade_enviada  INT         NOT NULL DEFAULT 0,
    FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS devolucoes (
    id              VARCHAR(10) PRIMARY KEY,
    requisicao_id   VARCHAR(10) NOT NULL,
    responsavel_id  VARCHAR(10) NOT NULL,
    estado          ENUM('pendente', 'fechada') NOT NULL DEFAULT 'pendente',
    data_reportada  DATE        NOT NULL,
    data_fecho      DATE,
    FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id),
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS itens_devolucao (
    id             VARCHAR(10) PRIMARY KEY,
    devolucao_id   VARCHAR(10) NOT NULL,
    produto_id     VARCHAR(10) NOT NULL,
    quantidade     INT         NOT NULL CHECK (quantidade > 0),
    FOREIGN KEY (devolucao_id) REFERENCES devolucoes(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS movimentos (
    id              VARCHAR(10) PRIMARY KEY,
    produto_id      VARCHAR(10) NOT NULL,
    tipo            ENUM('entrada', 'saida', 'ajuste') NOT NULL,
    quantidade      INT         NOT NULL CHECK (quantidade <> 0),
    data            DATE        NOT NULL,
    responsavel_id  VARCHAR(10),
    requisicao_id   VARCHAR(10),
    motivo          VARCHAR(255),
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id),
    FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS configuracoes (
    chave      VARCHAR(60)  PRIMARY KEY,
    valor      VARCHAR(255) NOT NULL,
    descricao  VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS configuracoes_historico (
    id              VARCHAR(20)  PRIMARY KEY,
    chave           VARCHAR(60)  NOT NULL,
    valor_anterior  VARCHAR(255) NOT NULL,
    valor_novo      VARCHAR(255) NOT NULL,
    data            DATE         NOT NULL,
    responsavel_id  VARCHAR(10)  NOT NULL,
    motivo          VARCHAR(255),
    FOREIGN KEY (chave) REFERENCES configuracoes(chave),
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# Ordem de TRUNCATE segura para chaves estrangeiras: as tabelas
# "filhas" antes das "mães" — o inverso da ordem de criação acima.
# (Na prática, com SET FOREIGN_KEY_CHECKS=0 a ordem deixa de importar
# a estrita correção das FKs durante o TRUNCATE, mas mantém-se
# explícita e documentada, para clareza de quem lê.)
_TABELAS_EM_ORDEM_DE_LIMPEZA = (
    "configuracoes_historico",
    "configuracoes",
    "itens_devolucao",
    "devolucoes",
    "itens_requisicao",
    "movimentos",
    "requisicoes",
    "produtos",
    "ocupacoes_airbnb",
    "ocupacoes_mensal",
    "ocupacoes",
    "clientes",
    "responsaveis",
    "lugares",
    "quartos",
    "unidades",
    "propriedades",
)


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

        for comando in _ESQUEMA_TABELAS.strip().split(";"):
            comando = comando.strip()
            if comando:
                cursor.execute(comando)

        conexao.commit()
    finally:
        conexao.close()


class BaseMySQLTest(unittest.TestCase):
    """Preparação comum aos testes que falam com uma base de dados
    MySQL real (módulos já migrados na Fase 2).

    Uma subclasse que define o seu próprio setUp() tem de chamar
    super().setUp() PRIMEIRO, antes de criar qualquer fixture — senão
    a base de dados de teste e os contadores ainda não estão prontos.
    """

    @classmethod
    def setUpClass(cls):
        _garantir_base_de_teste()

    def setUp(self):
        # 1. Base de dados: aponta para a de teste, nunca para a real.
        # repositorio.py faz "import config" e lê config.DB_NAME em
        # cada obter_conexao() — como é o mesmo objeto módulo (Python
        # só importa cada módulo uma vez), alterar config.DB_NAME aqui
        # é suficiente para redirecionar repositorio.py também.
        self._db_original = config.DB_NAME
        config.DB_NAME = DB_NAME_TESTE

        self._limpar_tabelas()

        # 2. Contadores de identificadores (repositorio.proximo_id):
        # pasta temporária, mesma convenção de
        # teste_repositorio.BaseRepositorio — nunca tocar no
        # dados/contadores.json real.
        self._pasta = Path(tempfile.mkdtemp())
        self._caminhos_originais = (
            repositorio.PASTA_DADOS,
            repositorio.PASTA_BACKUPS,
            repositorio.FICHEIRO_DADOS,
            repositorio.FICHEIRO_CONTADORES,
        )
        repositorio.PASTA_DADOS = self._pasta / "dados"
        repositorio.PASTA_BACKUPS = self._pasta / "backups"
        repositorio.FICHEIRO_DADOS = repositorio.PASTA_DADOS / "dados.json"
        repositorio.FICHEIRO_CONTADORES = (
            repositorio.PASTA_DADOS / "contadores.json"
        )

    def tearDown(self):
        config.DB_NAME = self._db_original

        (
            repositorio.PASTA_DADOS,
            repositorio.PASTA_BACKUPS,
            repositorio.FICHEIRO_DADOS,
            repositorio.FICHEIRO_CONTADORES,
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