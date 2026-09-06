-- ============================================================
-- esquema_mysql.sql
-- Hostel_Cleaning — Sistema de Gestão de Alojamento
-- Estrutura física da base de dados MySQL (Fase 2)
-- Gerado a partir do modelo de dados v1.5 (04/09/2026),
-- adaptado de SQLite para MySQL a pedido do formador.
--
-- Atualizado em 04/09/2026 (sessão de migração de clientes/
-- responsaveis para MySQL): data_nascimento e validade_documento,
-- em `clientes`, deixaram de ser NOT NULL — ver nota junto à tabela.
--
-- Atualizado em 06/09/2026 (arranque da GUI, decisão sobre a
-- planta de lugares): `lugares` ganhou a coluna `tipo_cama`
-- ("solteiro"/"casal"/"beliche") — só decide a aparência do lugar
-- na interface (tamanho/forma da caixa), nunca a capacidade, que
-- continua um campo à parte (decisão 17). Numa base já existente,
-- isto corresponde a uma ALTER TABLE, não a este CREATE TABLE —
-- ver nota junto à tabela.
-- ============================================================

CREATE DATABASE IF NOT EXISTS hostel_gestao
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE hostel_gestao;

-- Desliga temporariamente a verificação de chaves estrangeiras
-- enquanto se criam as tabelas — permite manter a mesma ordem
-- "lógica" (das mais independentes para as mais dependentes)
-- mesmo quando uma tabela anterior referencia uma posterior
-- (ex.: clientes referencia responsaveis, que só vem depois).
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- propriedades
-- ------------------------------------------------------------
CREATE TABLE propriedades (
    id      VARCHAR(10)  PRIMARY KEY,
    nome    VARCHAR(150) NOT NULL,
    morada  VARCHAR(255),
    ativo   BOOLEAN      NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- unidades
-- ------------------------------------------------------------
CREATE TABLE unidades (
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

-- ------------------------------------------------------------
-- quartos
-- ------------------------------------------------------------
CREATE TABLE quartos (
    id                VARCHAR(10)  PRIMARY KEY,
    unidade_id        VARCHAR(10)  NOT NULL,
    nome              VARCHAR(100) NOT NULL,
    privativo         BOOLEAN      NOT NULL DEFAULT 0,
    limpeza_incluida  BOOLEAN      NOT NULL DEFAULT 0,
    ativo             BOOLEAN      NOT NULL DEFAULT 1,
    FOREIGN KEY (unidade_id) REFERENCES unidades(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- lugares
--
-- NOTA (06/09/2026): `tipo_cama` é novo. Numa base já existente
-- (com lugares já gravados), NÃO uses este CREATE TABLE — corre
-- antes, no teu MySQL real:
--
--   ALTER TABLE lugares
--       ADD COLUMN tipo_cama ENUM('solteiro', 'casal', 'beliche')
--           NOT NULL DEFAULT 'solteiro'
--           AFTER nome;
--
-- e só depois de atualizares o tipo_cama real de cada lugar
-- existente (UPDATE a UPDATE, ou à mão no Workbench):
--
--   ALTER TABLE lugares ALTER COLUMN tipo_cama DROP DEFAULT;
--
-- Só decide a aparência do lugar na interface (planta de
-- lugares) — nunca a capacidade, que continua um campo à parte
-- (decisão 17).
-- ------------------------------------------------------------
CREATE TABLE lugares (
    id          VARCHAR(10)  PRIMARY KEY,
    quarto_id   VARCHAR(10)  NOT NULL,
    nome        VARCHAR(100) NOT NULL,
    tipo_cama   ENUM('solteiro', 'casal', 'beliche') NOT NULL,
    capacidade  INT          NOT NULL CHECK (capacidade >= 1),
    ativo       BOOLEAN      NOT NULL DEFAULT 1,
    FOREIGN KEY (quarto_id) REFERENCES quartos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- responsaveis
-- ------------------------------------------------------------
CREATE TABLE responsaveis (
    id        VARCHAR(10)  PRIMARY KEY,
    nome      VARCHAR(150) NOT NULL,
    contacto  VARCHAR(100),
    ativo     BOOLEAN      NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- clientes
--
-- NOTA (04/09/2026): data_nascimento e validade_documento
-- deixaram de ser NOT NULL. clientes.anonimizar() (decisão 8,
-- RGPD) precisa de os limpar para None ao anonimizar um cliente
-- — com NOT NULL essa operação falhava com um erro do MySQL. Os
-- dois continuam a ser tratados como obrigatórios pela camada de
-- negócio (validacoes.validar_cliente) em qualquer cliente ativo
-- e não anonimizado; só deixam de o ser fisicamente na coluna,
-- para permitir o apagamento do RGPD.
-- ------------------------------------------------------------
CREATE TABLE clientes (
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

-- ------------------------------------------------------------
-- ocupacoes (base comum a contratos mensais e reservas Airbnb)
-- ------------------------------------------------------------
CREATE TABLE ocupacoes (
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

-- ------------------------------------------------------------
-- ocupacoes_mensal (especialização 1:1 — PK também é FK)
-- ------------------------------------------------------------
CREATE TABLE ocupacoes_mensal (
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

-- ------------------------------------------------------------
-- ocupacoes_airbnb (especialização 1:1 — PK também é FK)
-- ------------------------------------------------------------
CREATE TABLE ocupacoes_airbnb (
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

-- ------------------------------------------------------------
-- produtos
-- ------------------------------------------------------------
CREATE TABLE produtos (
    id              VARCHAR(10)  PRIMARY KEY,
    nome            VARCHAR(150) NOT NULL,
    unidade_medida  VARCHAR(30)  NOT NULL,
    stock_minimo    INT          NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    ativo           BOOLEAN      NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- requisicoes
-- ------------------------------------------------------------
CREATE TABLE requisicoes (
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

-- ------------------------------------------------------------
-- itens_requisicao
-- ------------------------------------------------------------
CREATE TABLE itens_requisicao (
    id                  VARCHAR(10) PRIMARY KEY,
    requisicao_id       VARCHAR(10) NOT NULL,
    produto_id          VARCHAR(10) NOT NULL,
    quantidade_pedida   INT         NOT NULL CHECK (quantidade_pedida > 0),
    quantidade_enviada  INT         NOT NULL DEFAULT 0,
    FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- devolucoes
-- ------------------------------------------------------------
CREATE TABLE devolucoes (
    id              VARCHAR(10) PRIMARY KEY,
    requisicao_id   VARCHAR(10) NOT NULL,
    responsavel_id  VARCHAR(10) NOT NULL,
    estado          ENUM('pendente', 'fechada') NOT NULL DEFAULT 'pendente',
    data_reportada  DATE        NOT NULL,
    data_fecho      DATE,
    FOREIGN KEY (requisicao_id) REFERENCES requisicoes(id),
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- itens_devolucao
-- ------------------------------------------------------------
CREATE TABLE itens_devolucao (
    id             VARCHAR(10) PRIMARY KEY,
    devolucao_id   VARCHAR(10) NOT NULL,
    produto_id     VARCHAR(10) NOT NULL,
    quantidade     INT         NOT NULL CHECK (quantidade > 0),
    FOREIGN KEY (devolucao_id) REFERENCES devolucoes(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- movimentos
-- ------------------------------------------------------------
CREATE TABLE movimentos (
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

-- ------------------------------------------------------------
-- configuracoes
-- ------------------------------------------------------------
CREATE TABLE configuracoes (
    chave      VARCHAR(60)  PRIMARY KEY,
    valor      VARCHAR(255) NOT NULL,
    descricao  VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- configuracoes_historico
-- ------------------------------------------------------------
CREATE TABLE configuracoes_historico (
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

-- Volta a ligar a verificação de chaves estrangeiras.
SET FOREIGN_KEY_CHECKS = 1;
