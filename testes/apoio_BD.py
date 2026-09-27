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
   `config.DIR_BACKUPS`, ...) são redirecionados para uma pasta
   temporária, para `repositorio.proximo_id()` — que continua a
   gravar num ficheiro, decisão 1 — nunca tocar no `dados/contadores.json`
   real. Cada teste começa, por isso, com os contadores a zero
   (PRO-001, CLI-001, etc.), tal como acontecia nos testes antigos
   em memória.

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

import mysql.connector

import config
import repositorio

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

# Esquema físico das tabelas usadas pelos módulos já migrados para
# MySQL — cópia de docs/Modelo_de_dados_esquema_v.1.5.6.sql (o dump
# real do aluno, de 22/09/2026), sem o CREATE DATABASE/USE, e com
# IF NOT EXISTS em cada tabela para a criação ser sempre segura
# repetir. Se o esquema mudar no ficheiro principal, replicar a
# alteração aqui também.
_ESQUEMA_TABELAS = """
CREATE TABLE IF NOT EXISTS responsaveis (
    id                      VARCHAR(10)  PRIMARY KEY,
    nome                    VARCHAR(150) NOT NULL,
    contacto                VARCHAR(100),
    tipo_utilizador         ENUM('Master','Admin','Staff') NOT NULL DEFAULT 'Staff',
    ativo                   BOOLEAN      NOT NULL DEFAULT 1,
    username                VARCHAR(50)  UNIQUE,
    password_hash           VARCHAR(255),
    password_alterada_em    DATETIME,
    ultimo_login            DATETIME,
    desativado_por_id       VARCHAR(10),
    data_desativacao        DATE,
    FOREIGN KEY (desativado_por_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS propriedades (
    id                  VARCHAR(10)  PRIMARY KEY,
    nome                VARCHAR(150) NOT NULL,
    morada              VARCHAR(255),
    ativo               BOOLEAN      NOT NULL DEFAULT 1,
    desativado_por_id   VARCHAR(10),
    data_desativacao    DATE,
    iban                VARCHAR(34),
    FOREIGN KEY (desativado_por_id) REFERENCES responsaveis(id)
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
    permite_cama_extra     BOOLEAN       NOT NULL DEFAULT 0,
    qtd_cama_extra         INT           DEFAULT NULL,
    tipo_cama_extra        VARCHAR(60)   DEFAULT NULL,
    categoria_cama_extra   ENUM('solteiro','casal') DEFAULT NULL,
    ativo                  BOOLEAN       NOT NULL DEFAULT 1,
    desativado_por_id      VARCHAR(10),
    data_desativacao       DATE,
    FOREIGN KEY (propriedade_id) REFERENCES propriedades(id),
    FOREIGN KEY (desativado_por_id) REFERENCES responsaveis(id),
    CHECK (qtd_cama_extra >= 0)
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
    id                 VARCHAR(10)  PRIMARY KEY,
    quarto_id          VARCHAR(10)  NOT NULL,
    nome               VARCHAR(100) NOT NULL,
    tipo_cama          ENUM('solteiro','casal','beliche') NOT NULL DEFAULT 'solteiro',
    posicao_beliche    ENUM('superior','inferior') DEFAULT NULL,
    beliche_grupo_id   VARCHAR(10)  DEFAULT NULL,
    capacidade         INT          NOT NULL CHECK (capacidade >= 1),
    ativo              BOOLEAN      NOT NULL DEFAULT 1,
    FOREIGN KEY (quarto_id) REFERENCES quartos(id)
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
    pais_emissor_documento      VARCHAR(100) NOT NULL DEFAULT '',
    pais_residencia             VARCHAR(100) NOT NULL DEFAULT '',
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
    id                  VARCHAR(10)  PRIMARY KEY,
    nome                VARCHAR(150) NOT NULL,
    unidade_medida      VARCHAR(30)  NOT NULL,
    stock_minimo        INT          NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    ativo               BOOLEAN      NOT NULL DEFAULT 1,
    desativado_por_id   VARCHAR(10),
    data_desativacao    DATE,
    tipo_produto        ENUM('consumivel','roupa_cama','roupa_banho','outro') NOT NULL DEFAULT 'consumivel',
    FOREIGN KEY (desativado_por_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS requisicoes (
    id                        VARCHAR(10) PRIMARY KEY,
    responsavel_id            VARCHAR(10) NOT NULL,
    estado                    ENUM('pendente','enviada','fechada','rejeitada','cancelada') NOT NULL DEFAULT 'pendente',
    data_pedido               DATE        NOT NULL,
    data_envio                DATE,
    data_fecho                DATE,
    responsavel_rejeicao_id   VARCHAR(10),
    motivo_rejeicao           VARCHAR(255),
    observacoes               VARCHAR(255),
    observacao_rececao        TEXT,
    origem                    VARCHAR(20) DEFAULT 'pedido',
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
    estado          ENUM('pendente','fechada') NOT NULL DEFAULT 'pendente',
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
    tipo            ENUM('entrada','saida','ajuste') NOT NULL,
    quantidade      INT         NOT NULL CHECK (quantidade <> 0),
    data            DATE        NOT NULL,
    responsavel_id  VARCHAR(10),
    requisicao_id   VARCHAR(10),
    motivo          VARCHAR(255),
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id),
    FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS responsavel_unidade (
    id              VARCHAR(10) PRIMARY KEY,
    responsavel_id  VARCHAR(10) NOT NULL,
    unidade_id      VARCHAR(10) NOT NULL,
    ativo           BOOLEAN     NOT NULL DEFAULT 1,
    UNIQUE KEY uk_responsavel_unidade (responsavel_id, unidade_id),
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id),
    FOREIGN KEY (unidade_id) REFERENCES unidades(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rol_lavanderia_regras (
    id          VARCHAR(10) PRIMARY KEY,
    tipo_cama   VARCHAR(20) NOT NULL,
    produto_id  VARCHAR(10) NOT NULL,
    quantidade  INT         NOT NULL CHECK (quantidade > 0),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
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

CREATE TABLE IF NOT EXISTS categorias_despesa (
    id                  VARCHAR(10)  PRIMARY KEY,
    nome                VARCHAR(100) NOT NULL,
    ativo               BOOLEAN      NOT NULL DEFAULT 1,
    desativado_por_id   VARCHAR(10),
    data_desativacao    DATE,
    UNIQUE KEY uk_categorias_despesa_nome (nome),
    FOREIGN KEY (desativado_por_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fornecedores (
    id                  VARCHAR(10)  PRIMARY KEY,
    nome                VARCHAR(150) NOT NULL,
    contacto            VARCHAR(100),
    nif                 VARCHAR(20),
    ativo               BOOLEAN      NOT NULL DEFAULT 1,
    desativado_por_id   VARCHAR(10),
    data_desativacao    DATE,
    FOREIGN KEY (desativado_por_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS despesas (
    id                              VARCHAR(10)   PRIMARY KEY,
    unidade_id                      VARCHAR(10),
    categoria_id                    VARCHAR(10)   NOT NULL,
    fornecedor_id                   VARCHAR(10),
    valor                           DECIMAL(10,2) NOT NULL,
    data_lancamento                 DATE          NOT NULL,
    data_pagamento                  DATE,
    data_vencimento                 DATE,
    estado                          ENUM('pendente','paga','cancelada') NOT NULL DEFAULT 'pendente',
    recorrente                      BOOLEAN       NOT NULL DEFAULT 0,
    despesa_origem_id               VARCHAR(10),
    itens_confirmados               BOOLEAN       NOT NULL DEFAULT 1,
    itens_confirmados_por_id        VARCHAR(10),
    itens_confirmados_em            DATETIME,
    responsavel_lancamento_id       VARCHAR(10)   NOT NULL,
    responsavel_cancelamento_id     VARCHAR(10),
    motivo_cancelamento             VARCHAR(255),
    descricao                       VARCHAR(255),
    comprovativo_caminho            VARCHAR(255),
    FOREIGN KEY (unidade_id) REFERENCES unidades(id),
    FOREIGN KEY (categoria_id) REFERENCES categorias_despesa(id),
    FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
    FOREIGN KEY (despesa_origem_id) REFERENCES despesas(id),
    FOREIGN KEY (responsavel_lancamento_id) REFERENCES responsaveis(id),
    FOREIGN KEY (responsavel_cancelamento_id) REFERENCES responsaveis(id),
    FOREIGN KEY (itens_confirmados_por_id) REFERENCES responsaveis(id),
    CHECK (valor >= 0),
    CHECK (estado <> 'cancelada' OR (motivo_cancelamento IS NOT NULL AND responsavel_cancelamento_id IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS itens_despesa (
    id              VARCHAR(10) PRIMARY KEY,
    despesa_id      VARCHAR(10) NOT NULL,
    produto_id      VARCHAR(10) NOT NULL,
    quantidade      INT         NOT NULL CHECK (quantidade > 0),
    movimento_id    VARCHAR(10),
    FOREIGN KEY (despesa_id) REFERENCES despesas(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    FOREIGN KEY (movimento_id) REFERENCES movimentos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS textos_legais (
    id            INT NOT NULL AUTO_INCREMENT,
    tipo          ENUM('privacidade_hospede','privacidade_colaborador','confidencialidade') NOT NULL,
    versao        VARCHAR(20) NOT NULL,
    texto         MEDIUMTEXT  NOT NULL,
    publicado_em  DATE        NOT NULL,
    em_vigor      TINYINT(1)  NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_texto_tipo_versao (tipo, versao),
    KEY idx_texto_em_vigor (tipo, em_vigor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS avisos_privacidade (
    id                INT NOT NULL AUTO_INCREMENT,
    titular_tipo      ENUM('cliente','responsavel') NOT NULL,
    titular_id        VARCHAR(10) NOT NULL,
    documento         ENUM('privacidade_hospede','privacidade_colaborador','confidencialidade') NOT NULL,
    versao_texto      VARCHAR(20) NOT NULL,
    data_entrega      DATETIME    NOT NULL,
    registado_por_id  VARCHAR(10),
    suporte           ENUM('papel','contrato','web','sistema') NOT NULL DEFAULT 'papel',
    arquivo           VARCHAR(255),
    PRIMARY KEY (id),
    KEY idx_aviso_titular (titular_tipo, titular_id),
    KEY idx_aviso_documento (documento, versao_texto),
    CONSTRAINT fk_aviso_texto FOREIGN KEY (documento, versao_texto)
        REFERENCES textos_legais (tipo, versao)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# Ordem de TRUNCATE segura para chaves estrangeiras: as tabelas
# "filhas" antes das "mães" — o inverso da ordem de criação acima.
# (Na prática, com SET FOREIGN_KEY_CHECKS=0 a ordem deixa de importar
# a estrita correção das FKs durante o TRUNCATE, mas mantém-se
# explícita e documentada, para clareza de quem lê.)
_TABELAS_EM_ORDEM_DE_LIMPEZA = (
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

# Nomes de tabela extraídos do `_ESQUEMA_TABELAS`, para a verificação
# leve do `_garantir_esquema_atualizado()` (Alteração B). Calculado
# uma única vez, no import do módulo — evita repetir o parsing em
# cada teste.
_TABELAS_ESPERADAS = tuple(
    linha.split("CREATE TABLE IF NOT EXISTS ", 1)[1].split(" ", 1)[0].strip()
    for linha in _ESQUEMA_TABELAS.split(";")
    if "CREATE TABLE IF NOT EXISTS" in linha
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
    a base de dados de teste e os contadores ainda não estão prontos.
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

        # 2. Contadores de identificadores (repositorio.proximo_id):
        # pasta temporária, mesma convenção de
        # teste_repositorio.BaseRepositorio — nunca tocar no
        # dados/contadores.json real.
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