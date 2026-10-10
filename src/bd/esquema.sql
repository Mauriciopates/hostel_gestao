-- =====================================================================
-- Hostel Clean — ESQUEMA OFICIAL DA BASE DE DADOS (v1.8.0, INST-03)
-- =====================================================================
-- Fonte ÚNICA do esquema (decisão D7): lido pela aplicação ao criar
-- uma base nova (INST-02), pelos testes (`testes/apoio_BD.py`) e
-- incluído no executável.
--
-- Gerado a 30/09/2026 a partir da base real (Localhost, mysqldump
-- --no-data) e confirmado contra o código: 25 tabelas de negócio, 45
-- chaves estrangeiras, mais a tabela de controlo `migracoes_aplicadas`.
-- Migração 0003: `avisos_privacidade` trocou titular_tipo +
-- titular_id por cliente_id + responsavel_id, com 3 FKs novas (48 no
-- total) e o CHECK `ck_aviso_um_titular`.
-- Migração 0004: `clientes.consente_comunicacoes_em` (prova do
-- consentimento de comunicações vindo do pré check-in).
-- Migração 0005: `despesas.unidade_atribuida_por_id` e
-- `unidade_atribuida_em` (+ FK; 49 no total) — auditoria da atribuição
-- de unidade a uma despesa paga sem unidade.
-- Migração 0006: `propriedades.senhorio_nome` — nome do senhorio
-- (Primeiro Contraente) que vai para o contrato mensal impresso.
-- Partiu do `Modelo_de_dados_esquema_v.1.5.6.sql`, com:
--   - CREATE TABLE IF NOT EXISTS (pode correr numa base já criada);
--   - ordem das tabelas pela dependência das chaves estrangeiras;
--   - uma só collation (utf8mb4_unicode_ci — funciona em MySQL 8 e
--     MariaDB; a base antiga misturava 0900_ai_ci e unicode_ci);
--   - sem dados, sem AUTO_INCREMENT=N e sem as diretivas do mysqldump.
--
-- Inclui, no fim, a tabela de controlo `migracoes_aplicadas` (grupo
-- Sistema): regista que migrações de `src/migracoes.py` já correram
-- nesta base — o mesmo papel da `django_migrations` do Django. Não tem
-- chaves estrangeiras de propósito: é da infraestrutura, não do
-- negócio. NÃO contém dados iniciais (esses são as próprias
-- migrações). Ordem numa base nova:
--   1. este ficheiro;  2. migracoes.aplicar_pendentes().
--
-- REGRA: uma mudança de esquema numa base existente é SEMPRE uma
-- migração nova em `migracoes.py`; este ficheiro é atualizado no mesmo
-- commit, para uma instalação nova nascer já igual.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `configuracoes` (
  `chave` varchar(60) NOT NULL,
  `valor` varchar(255) NOT NULL,
  `descricao` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`chave`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `responsaveis` (
  `id` varchar(10) NOT NULL,
  `nome` varchar(150) NOT NULL,
  `contacto` varchar(100) DEFAULT NULL,
  `tipo_utilizador` enum('Master','Admin','Staff') NOT NULL DEFAULT 'Staff',
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `username` varchar(50) DEFAULT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `password_alterada_em` datetime DEFAULT NULL,
  `ultimo_login` datetime DEFAULT NULL,
  `desativado_por_id` varchar(10) DEFAULT NULL,
  `data_desativacao` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `fk_responsaveis_desativado_por` (`desativado_por_id`),
  CONSTRAINT `fk_responsaveis_desativado_por` FOREIGN KEY (`desativado_por_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `categorias_despesa` (
  `id` varchar(10) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `desativado_por_id` varchar(10) DEFAULT NULL,
  `data_desativacao` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_categorias_despesa_nome` (`nome`),
  KEY `fk_categorias_despesa_desativado_por` (`desativado_por_id`),
  CONSTRAINT `fk_categorias_despesa_desativado_por` FOREIGN KEY (`desativado_por_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `clientes` (
  `id` varchar(10) NOT NULL,
  `nome` varchar(150) NOT NULL,
  `tipo_documento` enum('Cartão de Cidadão','Passaporte','Título de Residência','Outro') NOT NULL,
  `numero_documento` varchar(50) NOT NULL,
  `nif` varchar(20) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `consente_comunicacoes_em` datetime DEFAULT NULL,
  `telefone` varchar(30) DEFAULT NULL,
  `morada` varchar(255) DEFAULT NULL,
  `nacionalidade` varchar(100) DEFAULT NULL,
  `pais_emissor_documento` varchar(100) NOT NULL DEFAULT '',
  `pais_residencia` varchar(100) NOT NULL DEFAULT '',
  `estado_civil` varchar(30) DEFAULT NULL,
  `data_nascimento` date DEFAULT NULL,
  `validade_documento` date DEFAULT NULL,
  `contacto_emergencia` varchar(150) DEFAULT NULL,
  `incompleto` tinyint(1) NOT NULL DEFAULT '0',
  `anonimizado` tinyint(1) NOT NULL DEFAULT '0',
  `data_anonimizado` date DEFAULT NULL,
  `responsavel_anonimizado_id` varchar(10) DEFAULT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `responsavel_anonimizado_id` (`responsavel_anonimizado_id`),
  CONSTRAINT `clientes_ibfk_1` FOREIGN KEY (`responsavel_anonimizado_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `configuracoes_historico` (
  `id` varchar(20) NOT NULL,
  `chave` varchar(60) NOT NULL,
  `valor_anterior` varchar(255) NOT NULL,
  `valor_novo` varchar(255) NOT NULL,
  `data` date NOT NULL,
  `responsavel_id` varchar(10) NOT NULL,
  `motivo` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `chave` (`chave`),
  KEY `responsavel_id` (`responsavel_id`),
  CONSTRAINT `configuracoes_historico_ibfk_1` FOREIGN KEY (`chave`) REFERENCES `configuracoes` (`chave`),
  CONSTRAINT `configuracoes_historico_ibfk_2` FOREIGN KEY (`responsavel_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `fornecedores` (
  `id` varchar(10) NOT NULL,
  `nome` varchar(150) NOT NULL,
  `contacto` varchar(100) DEFAULT NULL,
  `nif` varchar(20) DEFAULT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `desativado_por_id` varchar(10) DEFAULT NULL,
  `data_desativacao` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_fornecedores_desativado_por` (`desativado_por_id`),
  CONSTRAINT `fk_fornecedores_desativado_por` FOREIGN KEY (`desativado_por_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `produtos` (
  `id` varchar(10) NOT NULL,
  `nome` varchar(150) NOT NULL,
  `unidade_medida` varchar(30) NOT NULL,
  `stock_minimo` int NOT NULL DEFAULT '0',
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `desativado_por_id` varchar(10) DEFAULT NULL,
  `data_desativacao` date DEFAULT NULL,
  `tipo_produto` enum('consumivel','roupa_cama','roupa_banho','outro') NOT NULL DEFAULT 'consumivel',
  PRIMARY KEY (`id`),
  KEY `fk_produtos_desativado_por` (`desativado_por_id`),
  CONSTRAINT `fk_produtos_desativado_por` FOREIGN KEY (`desativado_por_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `produtos_chk_1` CHECK ((`stock_minimo` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `propriedades` (
  `id` varchar(10) NOT NULL,
  `nome` varchar(150) NOT NULL,
  `morada` varchar(255) DEFAULT NULL,
  `senhorio_nome` varchar(150) DEFAULT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `desativado_por_id` varchar(10) DEFAULT NULL,
  `data_desativacao` date DEFAULT NULL,
  `iban` varchar(34) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_propriedades_desativado_por` (`desativado_por_id`),
  CONSTRAINT `fk_propriedades_desativado_por` FOREIGN KEY (`desativado_por_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `requisicoes` (
  `id` varchar(10) NOT NULL,
  `responsavel_id` varchar(10) NOT NULL,
  `estado` enum('pendente','enviada','fechada','rejeitada','cancelada') NOT NULL DEFAULT 'pendente',
  `data_pedido` date NOT NULL,
  `data_envio` date DEFAULT NULL,
  `data_fecho` date DEFAULT NULL,
  `responsavel_rejeicao_id` varchar(10) DEFAULT NULL,
  `motivo_rejeicao` varchar(255) DEFAULT NULL,
  `observacoes` varchar(255) DEFAULT NULL,
  `observacao_rececao` text,
  `origem` varchar(20) DEFAULT 'pedido',
  PRIMARY KEY (`id`),
  KEY `responsavel_id` (`responsavel_id`),
  KEY `responsavel_rejeicao_id` (`responsavel_rejeicao_id`),
  CONSTRAINT `requisicoes_ibfk_1` FOREIGN KEY (`responsavel_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `requisicoes_ibfk_2` FOREIGN KEY (`responsavel_rejeicao_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `devolucoes` (
  `id` varchar(10) NOT NULL,
  `requisicao_id` varchar(10) NOT NULL,
  `responsavel_id` varchar(10) NOT NULL,
  `estado` enum('pendente','fechada') NOT NULL DEFAULT 'pendente',
  `data_reportada` date NOT NULL,
  `data_fecho` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `requisicao_id` (`requisicao_id`),
  KEY `responsavel_id` (`responsavel_id`),
  CONSTRAINT `devolucoes_ibfk_1` FOREIGN KEY (`requisicao_id`) REFERENCES `requisicoes` (`id`),
  CONSTRAINT `devolucoes_ibfk_2` FOREIGN KEY (`responsavel_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `itens_devolucao` (
  `id` varchar(10) NOT NULL,
  `devolucao_id` varchar(10) NOT NULL,
  `produto_id` varchar(10) NOT NULL,
  `quantidade` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `devolucao_id` (`devolucao_id`),
  KEY `idx_itens_devolucao_produto` (`produto_id`),
  CONSTRAINT `itens_devolucao_ibfk_1` FOREIGN KEY (`devolucao_id`) REFERENCES `devolucoes` (`id`),
  CONSTRAINT `itens_devolucao_ibfk_2` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`),
  CONSTRAINT `itens_devolucao_chk_1` CHECK ((`quantidade` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `itens_requisicao` (
  `id` varchar(10) NOT NULL,
  `requisicao_id` varchar(10) NOT NULL,
  `produto_id` varchar(10) NOT NULL,
  `quantidade_pedida` int NOT NULL,
  `quantidade_enviada` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `requisicao_id` (`requisicao_id`),
  KEY `idx_itens_requisicao_produto` (`produto_id`),
  CONSTRAINT `itens_requisicao_ibfk_1` FOREIGN KEY (`requisicao_id`) REFERENCES `requisicoes` (`id`),
  CONSTRAINT `itens_requisicao_ibfk_2` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`),
  CONSTRAINT `itens_requisicao_chk_1` CHECK ((`quantidade_pedida` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `movimentos` (
  `id` varchar(10) NOT NULL,
  `produto_id` varchar(10) NOT NULL,
  `tipo` enum('entrada','saida','ajuste') NOT NULL,
  `quantidade` int NOT NULL,
  `data` date NOT NULL,
  `responsavel_id` varchar(10) DEFAULT NULL,
  `requisicao_id` varchar(10) DEFAULT NULL,
  `motivo` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `responsavel_id` (`responsavel_id`),
  KEY `requisicao_id` (`requisicao_id`),
  KEY `idx_movimentos_produto` (`produto_id`),
  CONSTRAINT `movimentos_ibfk_1` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`),
  CONSTRAINT `movimentos_ibfk_2` FOREIGN KEY (`responsavel_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `movimentos_ibfk_3` FOREIGN KEY (`requisicao_id`) REFERENCES `requisicoes` (`id`),
  CONSTRAINT `movimentos_chk_1` CHECK ((`quantidade` <> 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `rol_lavanderia_regras` (
  `id` varchar(10) NOT NULL,
  `tipo_cama` varchar(20) NOT NULL,
  `produto_id` varchar(10) NOT NULL,
  `quantidade` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_rlr_tipo_cama` (`tipo_cama`),
  KEY `idx_rlr_produto` (`produto_id`),
  CONSTRAINT `fk_rlr_produto` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`),
  CONSTRAINT `chk_rlr_quantidade` CHECK ((`quantidade` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `textos_legais` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tipo` enum('privacidade_hospede','privacidade_colaborador','confidencialidade') NOT NULL,
  `versao` varchar(20) NOT NULL,
  `texto` mediumtext NOT NULL,
  `publicado_em` date NOT NULL,
  `em_vigor` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_texto_tipo_versao` (`tipo`,`versao`),
  KEY `idx_texto_em_vigor` (`tipo`,`em_vigor`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `avisos_privacidade` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cliente_id` varchar(10) DEFAULT NULL,
  `responsavel_id` varchar(10) DEFAULT NULL,
  `documento` enum('privacidade_hospede','privacidade_colaborador','confidencialidade') NOT NULL,
  `versao_texto` varchar(20) NOT NULL,
  `data_entrega` datetime NOT NULL,
  `registado_por_id` varchar(10) DEFAULT NULL,
  `suporte` enum('papel','contrato','web','sistema') NOT NULL DEFAULT 'papel',
  `arquivo` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_aviso_documento` (`documento`,`versao_texto`),
  KEY `fk_aviso_cliente` (`cliente_id`),
  KEY `fk_aviso_responsavel` (`responsavel_id`),
  KEY `fk_aviso_registado_por` (`registado_por_id`),
  CONSTRAINT `fk_aviso_texto` FOREIGN KEY (`documento`, `versao_texto`) REFERENCES `textos_legais` (`tipo`, `versao`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_aviso_cliente` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_aviso_responsavel` FOREIGN KEY (`responsavel_id`) REFERENCES `responsaveis` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `fk_aviso_registado_por` FOREIGN KEY (`registado_por_id`) REFERENCES `responsaveis` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `ck_aviso_um_titular` CHECK (((`cliente_id` is null) <> (`responsavel_id` is null)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `unidades` (
  `id` varchar(10) NOT NULL,
  `propriedade_id` varchar(10) NOT NULL,
  `nome` varchar(150) NOT NULL,
  `tipo` enum('mensal','airbnb') NOT NULL,
  `preco_base` decimal(10,2) NOT NULL,
  `preco_epoca_alta` decimal(10,2) NOT NULL,
  `multa_check_in_tardio` decimal(10,2) NOT NULL,
  `epoca_alta_ativa` tinyint(1) NOT NULL DEFAULT '0',
  `em_manutencao` tinyint(1) NOT NULL DEFAULT '0',
  `permite_cama_extra` tinyint(1) NOT NULL DEFAULT '0',
  `qtd_cama_extra` int DEFAULT NULL,
  `tipo_cama_extra` varchar(60) DEFAULT NULL,
  `categoria_cama_extra` enum('solteiro','casal') DEFAULT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `desativado_por_id` varchar(10) DEFAULT NULL,
  `data_desativacao` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `propriedade_id` (`propriedade_id`),
  KEY `fk_unidades_desativado_por` (`desativado_por_id`),
  CONSTRAINT `fk_unidades_desativado_por` FOREIGN KEY (`desativado_por_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `unidades_ibfk_1` FOREIGN KEY (`propriedade_id`) REFERENCES `propriedades` (`id`),
  CONSTRAINT `unidades_chk_cama_extra` CHECK ((`qtd_cama_extra` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `despesas` (
  `id` varchar(10) NOT NULL,
  `unidade_id` varchar(10) DEFAULT NULL,
  `categoria_id` varchar(10) NOT NULL,
  `fornecedor_id` varchar(10) DEFAULT NULL,
  `valor` decimal(10,2) NOT NULL,
  `data_lancamento` date NOT NULL,
  `data_pagamento` date DEFAULT NULL,
  `data_vencimento` date DEFAULT NULL,
  `estado` enum('pendente','paga','cancelada') NOT NULL DEFAULT 'pendente',
  `recorrente` tinyint(1) NOT NULL DEFAULT '0',
  `despesa_origem_id` varchar(10) DEFAULT NULL,
  `itens_confirmados` tinyint(1) NOT NULL DEFAULT '1',
  `itens_confirmados_por_id` varchar(10) DEFAULT NULL,
  `itens_confirmados_em` datetime DEFAULT NULL,
  `responsavel_lancamento_id` varchar(10) NOT NULL,
  `responsavel_cancelamento_id` varchar(10) DEFAULT NULL,
  `motivo_cancelamento` varchar(255) DEFAULT NULL,
  `descricao` varchar(255) DEFAULT NULL,
  `comprovativo_caminho` varchar(255) DEFAULT NULL,
  `unidade_atribuida_por_id` varchar(10) DEFAULT NULL,
  `unidade_atribuida_em` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_despesas_unidade` (`unidade_id`),
  KEY `idx_despesas_categoria` (`categoria_id`),
  KEY `idx_despesas_fornecedor` (`fornecedor_id`),
  KEY `idx_despesas_estado` (`estado`),
  KEY `idx_despesas_data_lancamento` (`data_lancamento`),
  KEY `idx_despesas_despesa_origem` (`despesa_origem_id`),
  KEY `fk_despesas_responsavel_lancamento` (`responsavel_lancamento_id`),
  KEY `fk_despesas_responsavel_cancelamento` (`responsavel_cancelamento_id`),
  KEY `fk_despesas_itens_confirmados_por` (`itens_confirmados_por_id`),
  KEY `fk_despesas_unidade_atribuida` (`unidade_atribuida_por_id`),
  CONSTRAINT `fk_despesas_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias_despesa` (`id`),
  CONSTRAINT `fk_despesas_despesa_origem` FOREIGN KEY (`despesa_origem_id`) REFERENCES `despesas` (`id`),
  CONSTRAINT `fk_despesas_fornecedor` FOREIGN KEY (`fornecedor_id`) REFERENCES `fornecedores` (`id`),
  CONSTRAINT `fk_despesas_itens_confirmados_por` FOREIGN KEY (`itens_confirmados_por_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `fk_despesas_responsavel_cancelamento` FOREIGN KEY (`responsavel_cancelamento_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `fk_despesas_responsavel_lancamento` FOREIGN KEY (`responsavel_lancamento_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `fk_despesas_unidade_atribuida` FOREIGN KEY (`unidade_atribuida_por_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `fk_despesas_unidade` FOREIGN KEY (`unidade_id`) REFERENCES `unidades` (`id`),
  CONSTRAINT `despesas_chk_cancelamento` CHECK (((`estado` <> 'cancelada') or ((`motivo_cancelamento` is not null) and (`responsavel_cancelamento_id` is not null)))),
  CONSTRAINT `despesas_chk_valor` CHECK ((`valor` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `itens_despesa` (
  `id` varchar(10) NOT NULL,
  `despesa_id` varchar(10) NOT NULL,
  `produto_id` varchar(10) NOT NULL,
  `quantidade` int NOT NULL,
  `movimento_id` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_itens_despesa_despesa` (`despesa_id`),
  KEY `idx_itens_despesa_produto` (`produto_id`),
  KEY `idx_itens_despesa_movimento` (`movimento_id`),
  CONSTRAINT `fk_itens_despesa_despesa` FOREIGN KEY (`despesa_id`) REFERENCES `despesas` (`id`),
  CONSTRAINT `fk_itens_despesa_movimento` FOREIGN KEY (`movimento_id`) REFERENCES `movimentos` (`id`),
  CONSTRAINT `fk_itens_despesa_produto` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`),
  CONSTRAINT `itens_despesa_chk_quantidade` CHECK ((`quantidade` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `quartos` (
  `id` varchar(10) NOT NULL,
  `unidade_id` varchar(10) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `privativo` tinyint(1) NOT NULL DEFAULT '0',
  `limpeza_incluida` tinyint(1) NOT NULL DEFAULT '0',
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `unidade_id` (`unidade_id`),
  CONSTRAINT `quartos_ibfk_1` FOREIGN KEY (`unidade_id`) REFERENCES `unidades` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `lugares` (
  `id` varchar(10) NOT NULL,
  `quarto_id` varchar(10) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `tipo_cama` enum('solteiro','casal','beliche') NOT NULL DEFAULT 'solteiro',
  `posicao_beliche` enum('superior','inferior') DEFAULT NULL,
  `beliche_grupo_id` varchar(10) DEFAULT NULL,
  `capacidade` int NOT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `quarto_id` (`quarto_id`),
  KEY `idx_lugares_beliche_grupo` (`beliche_grupo_id`),
  CONSTRAINT `lugares_ibfk_1` FOREIGN KEY (`quarto_id`) REFERENCES `quartos` (`id`),
  CONSTRAINT `lugares_chk_1` CHECK ((`capacidade` >= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ocupacoes` (
  `id` varchar(10) NOT NULL,
  `unidade_id` varchar(10) NOT NULL,
  `cliente_id` varchar(10) NOT NULL,
  `tipo` enum('mensal','airbnb') NOT NULL,
  `data_inicio` date NOT NULL,
  `data_fim` date DEFAULT NULL,
  `lugar_id` varchar(10) DEFAULT NULL,
  `aviso_documento` tinyint(1) NOT NULL DEFAULT '0',
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `unidade_id` (`unidade_id`),
  KEY `cliente_id` (`cliente_id`),
  KEY `lugar_id` (`lugar_id`),
  CONSTRAINT `ocupacoes_ibfk_1` FOREIGN KEY (`unidade_id`) REFERENCES `unidades` (`id`),
  CONSTRAINT `ocupacoes_ibfk_2` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`),
  CONSTRAINT `ocupacoes_ibfk_3` FOREIGN KEY (`lugar_id`) REFERENCES `lugares` (`id`),
  CONSTRAINT `ocupacoes_chk_1` CHECK (((`data_fim` is null) or (`data_fim` > `data_inicio`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ocupacoes_airbnb` (
  `ocupacao_id` varchar(10) NOT NULL,
  `preco_calculado` decimal(10,2) NOT NULL,
  `preco_praticado` decimal(10,2) NOT NULL,
  `responsavel_desconto_preco_id` varchar(10) DEFAULT NULL,
  `check_in_tardio` tinyint(1) NOT NULL DEFAULT '0',
  `hora_chegada` time DEFAULT NULL,
  `multa_calculada` decimal(10,2) NOT NULL,
  `multa_praticada` decimal(10,2) NOT NULL,
  `responsavel_desconto_multa_id` varchar(10) DEFAULT NULL,
  `motivo_cancelamento` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`ocupacao_id`),
  KEY `responsavel_desconto_preco_id` (`responsavel_desconto_preco_id`),
  KEY `responsavel_desconto_multa_id` (`responsavel_desconto_multa_id`),
  CONSTRAINT `ocupacoes_airbnb_ibfk_1` FOREIGN KEY (`ocupacao_id`) REFERENCES `ocupacoes` (`id`),
  CONSTRAINT `ocupacoes_airbnb_ibfk_2` FOREIGN KEY (`responsavel_desconto_preco_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `ocupacoes_airbnb_ibfk_3` FOREIGN KEY (`responsavel_desconto_multa_id`) REFERENCES `responsaveis` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ocupacoes_mensal` (
  `ocupacao_id` varchar(10) NOT NULL,
  `renda_calculada` decimal(10,2) NOT NULL,
  `renda_praticada` decimal(10,2) NOT NULL,
  `responsavel_desconto_renda_id` varchar(10) DEFAULT NULL,
  `caucao` decimal(10,2) NOT NULL,
  `caucao_exige_confirmacao` tinyint(1) NOT NULL DEFAULT '0',
  `motivo_alteracao_renda` varchar(255) DEFAULT NULL,
  `motivo_alteracao_caucao` varchar(255) DEFAULT NULL,
  `dia_vencimento` int NOT NULL,
  `motivo_encerramento` varchar(255) DEFAULT NULL,
  `duracao_abaixo_minima` tinyint(1) NOT NULL DEFAULT '0',
  `aviso_previo_insuficiente` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`ocupacao_id`),
  KEY `responsavel_desconto_renda_id` (`responsavel_desconto_renda_id`),
  CONSTRAINT `ocupacoes_mensal_ibfk_1` FOREIGN KEY (`ocupacao_id`) REFERENCES `ocupacoes` (`id`),
  CONSTRAINT `ocupacoes_mensal_ibfk_2` FOREIGN KEY (`responsavel_desconto_renda_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `ocupacoes_mensal_chk_1` CHECK ((`dia_vencimento` between 1 and 28))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `responsavel_unidade` (
  `id` varchar(10) NOT NULL,
  `responsavel_id` varchar(10) NOT NULL,
  `unidade_id` varchar(10) NOT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_responsavel_unidade` (`responsavel_id`,`unidade_id`),
  KEY `unidade_id` (`unidade_id`),
  CONSTRAINT `responsavel_unidade_ibfk_1` FOREIGN KEY (`responsavel_id`) REFERENCES `responsaveis` (`id`),
  CONSTRAINT `responsavel_unidade_ibfk_2` FOREIGN KEY (`unidade_id`) REFERENCES `unidades` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Sistema — controlo das migrações (v1.8.0). Mesma definição do
-- `repositorio/rep_migracoes.py`, que a mantém com IF NOT EXISTS só
-- como rede de segurança para bases criadas antes da v1.8.0.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `migracoes_aplicadas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `aplicada_em` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_migracoes_nome` (`nome`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
