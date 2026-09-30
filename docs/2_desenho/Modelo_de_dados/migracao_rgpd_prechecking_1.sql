-- ====================================================================
-- MIGRAÇÃO — RGPD (textos legais + registo) e PRÉ CHECK-IN (fila do site)
-- Hostel_Gestao · v1.6.0 · 22/09/2026
-- ====================================================================
--
-- Aplicar à mão, como as migrações anteriores. São DUAS bases de dados
-- diferentes, de propósito:
--
--   hostel_gestao      -> o sistema. Só a aplicação desktop lhe toca.
--   hostel_prechecking -> a caixa de entrada do site. A API só sabe
--                         escrever aqui, e nunca chega à de cima.
--
-- É essa separação que faz com que uma falha na API exposta à internet
-- não dê acesso a clientes, contratos nem stock.
--
-- ORDEM: correr a PARTE 1 primeiro (tem as chaves estrangeiras), depois
-- a PARTE 2, e por fim a PARTE 3 (utilizadores e permissões).
-- ====================================================================

/*
CONCLUIDO NA DATA DO DIA 22/09/2026

-- ====================================================================
-- PARTE 1 — hostel_gestao
-- ====================================================================

USE hostel_gestao;


-- --------------------------------------------------------------------
-- textos_legais — o texto de cada documento, versão a versão
-- --------------------------------------------------------------------
-- Porque não fica nas Configurações: o controlo de texto do ecrã de
-- Configurações é um campo de uma linha, pensado para o caminho de uma
-- pasta. Um documento não cabe lá.
--
-- Porquê guardar o texto e não só o número da versão: quando alguém
-- perguntar o que é que o colaborador aceitou em março, tens de poder
-- mostrar a redação exata que estava em vigor nesse dia. É isto que faz
-- prova, e é por isso que uma linha desta tabela NUNCA se edita — cria-se
-- uma versão nova.
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS textos_legais (
    id              INT AUTO_INCREMENT PRIMARY KEY,

    tipo            ENUM(
                        'privacidade_hospede',
                        'privacidade_colaborador',
                        'confidencialidade'
                    ) NOT NULL,

    versao          VARCHAR(20)  NOT NULL,
    texto           MEDIUMTEXT   NOT NULL,
    publicado_em    DATE         NOT NULL,

    -- Só uma versão de cada tipo pode estar em vigor. O MySQL não
    -- consegue garantir isto sozinho (seria um índice parcial), por
    -- isso a regra vive na camada de negócio — ao publicar uma versão
    -- nova, a anterior passa a 0.
    em_vigor        TINYINT(1)   NOT NULL DEFAULT 0,

    CONSTRAINT uq_texto_tipo_versao UNIQUE (tipo, versao),
    INDEX idx_texto_em_vigor (tipo, em_vigor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- --------------------------------------------------------------------
-- avisos_privacidade — quem foi informado / quem aceitou, e quando
-- --------------------------------------------------------------------
-- Uma tabela para as duas naturezas, distinguidas pelo `documento`:
--
--   privacidade_*     -> INFORMAÇÃO prestada (art. 13.º). O titular não
--                        consente nem assina; é informado. Nunca bloqueia
--                        a gravação de um cliente.
--   confidencialidade -> COMPROMISSO do colaborador. É condição de
--                        acesso, e esse bloqueia.
--
-- É um registo histórico: uma linha nunca se atualiza, acrescenta-se
-- outra. Se o texto mudar de versão, a aceitação da versão nova é uma
-- linha nova, e a antiga fica como estava.
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS avisos_privacidade (
    id                INT AUTO_INCREMENT PRIMARY KEY,

    titular_tipo      ENUM('cliente', 'responsavel') NOT NULL,
    titular_id        VARCHAR(10) NOT NULL,

    documento         ENUM(
                          'privacidade_hospede',
                          'privacidade_colaborador',
                          'confidencialidade'
                      ) NOT NULL,

    versao_texto      VARCHAR(20) NOT NULL,

    -- Data/hora do servidor, não do dispositivo de quem submeteu.
    data_entrega      DATETIME    NOT NULL,

    -- Quem entregou/registou. Fica vazio quando veio do site sem
    -- ninguém pelo meio (suporte = 'web').
    registado_por_id  VARCHAR(10) NULL,

    -- Por onde é que a informação foi prestada. Já nasce preparado
    -- para a Fase 3: hoje é 'papel' ou 'contrato'; com o site passa a
    -- 'web', sem mudar a estrutura.
    suporte           ENUM('papel', 'contrato', 'web', 'sistema')
                      NOT NULL DEFAULT 'papel',

    -- Onde está arquivada a folha assinada, quando existe papel.
    arquivo           VARCHAR(255) NULL,

    -- Liga ao texto exato que estava em vigor. É esta chave que
    -- garante que o registo nunca aponta para uma versão inventada.
    --
    -- RESTRICT dos dois lados, e o UPDATE é de propósito: com CASCADE,
    -- renumerar a versão 1.0 para 1.1 reescrevia em silêncio todas as
    -- aceitações antigas, e o registo passava a dizer que as pessoas
    -- aceitaram um texto que nunca viram. Com RESTRICT, a base recusa a
    -- alteração. É a tabela a impor o que o comentário acima promete.
    CONSTRAINT fk_aviso_texto
        FOREIGN KEY (documento, versao_texto)
        REFERENCES textos_legais (tipo, versao)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    INDEX idx_aviso_titular (titular_tipo, titular_id),
    INDEX idx_aviso_documento (documento, versao_texto)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


*/

-- ====================================================================
-- PARTE 2 — hostel_prechecking (a caixa de entrada do site)
-- ====================================================================

CREATE DATABASE IF NOT EXISTS hostel_prechecking
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE hostel_prechecking;


-- --------------------------------------------------------------------
-- tokens — um link por reserva, de uso único e com validade
-- --------------------------------------------------------------------
-- Sem isto, o endereço do formulário é público e qualquer pessoa pode
-- encher a fila de lixo. O token vai no link enviado pela mensagem do
-- Airbnb e só serve para aquela estadia.
--
-- Escrito pela aplicação desktop (que emite o link) e lido pela API
-- (que o valida). A API pode marcá-lo como usado, mas não pode criar
-- tokens novos — ver as permissões na PARTE 3.
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tokens (
    token           VARCHAR(43)  PRIMARY KEY,

    -- A referência da reserva, para saberes a que estadia corresponde
    -- quando o pré check-in chegar.
    referencia      VARCHAR(100) NOT NULL,

    criado_em       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por_id   VARCHAR(10)  NOT NULL,

    -- Depois desta data a API recusa. Sugestão: data de saída + 1 dia.
    valido_ate      DATETIME     NOT NULL,

    -- Uso único: preenchido na primeira submissão aceite.
    usado_em        DATETIME     NULL,

    INDEX idx_token_validade (valido_ate, usado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- --------------------------------------------------------------------
-- pendentes — o que o site submeteu, à espera de validação
-- --------------------------------------------------------------------
-- As colunas seguem exatamente o JSON que a página gera. Nada aqui é
-- definitivo: é matéria-prima que tu confirmas no desktop antes de
-- virar cliente.
--
-- Estas linhas são apagadas assim que o registo é importado. Dados
-- pessoais não devem ficar parados na parte da máquina que está
-- exposta à internet mais tempo do que o necessário.
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pendentes (
    id                      INT AUTO_INCREMENT PRIMARY KEY,

    token                   VARCHAR(43)  NOT NULL,

    -- DUAS datas, e a diferença importa:
    --   submetido_em -> vem do dispositivo do hóspede (relógio dele,
    --                   não é de confiar)
    --   recebido_em  -> carimbo do servidor, e é este que faz prova
    submetido_em            DATETIME     NULL,
    recebido_em             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- ---- os 7 campos do regime Airbnb ----
    nome                    VARCHAR(150) NOT NULL,
    nacionalidade           VARCHAR(100) NOT NULL,
    data_nascimento         DATE         NOT NULL,
    tipo_documento          VARCHAR(50)  NOT NULL,
    numero_documento        VARCHAR(50)  NOT NULL,
    pais_emissor_documento  VARCHAR(100) NOT NULL,
    pais_residencia         VARCHAR(100) NOT NULL,

    -- ---- as três confirmações, separadas ----
    -- Separadas de propósito, e não num só campo "aceitou tudo": cada
    -- uma tem um fundamento jurídico diferente e um destino diferente.
    -- A primeira vira uma linha em `avisos_privacidade`; a terceira é
    -- consentimento revogável e vive noutro sítio.
    versao_aviso            VARCHAR(20)  NOT NULL,
    informado_privacidade   TINYINT(1)   NOT NULL DEFAULT 0,
    aceitou_regulamento     TINYINT(1)   NOT NULL DEFAULT 0,
    consente_comunicacoes   TINYINT(1)   NOT NULL DEFAULT 0,

    -- 'pendente' até alguém olhar. 'rejeitado' fica para o caso de os
    -- dados virem errados e não haver nada a importar.
    estado                  ENUM('pendente', 'importado', 'rejeitado')
                            NOT NULL DEFAULT 'pendente',

    CONSTRAINT fk_pendente_token
        FOREIGN KEY (token) REFERENCES tokens (token)
        ON DELETE RESTRICT,

    INDEX idx_pendente_estado (estado, recebido_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- NOTA sobre o que NÃO está aqui: não se guarda o endereço IP de quem
-- submeteu. Seria mais um dado pessoal recolhido, e para que servisse
-- de alguma coisa teria de ser conservado — o token de uso único já
-- resolve o abuso sem isso. Minimização de dados, art. 5.º/1/c.


-- ====================================================================
-- PARTE 3 — utilizadores e permissões
-- ====================================================================
-- É aqui que a segurança do desenho se concretiza. Trocar as
-- passwords pelas reais antes de correr.
-- ====================================================================

-- --------------------------------------------------------------------
-- A API — vive na VM e é a única coisa que a internet alcança.
-- --------------------------------------------------------------------
-- 'localhost' porque a API corre na própria máquina e fala com o MySQL
-- pelo 127.0.0.1. Nunca precisa de vir de fora.
--
-- O que pode fazer, e mais nada:
--   - inserir um pré check-in
--   - ler um token, para o validar
--   - marcar esse token como usado
--
-- O que NÃO pode: ler os pendentes que já lá estão, apagar seja o que
-- for, criar tokens, ou tocar na hostel_gestao. Se alguém a arrombar,
-- o pior que consegue é deixar lixo numa caixa que tu esvazias.

CREATE USER IF NOT EXISTS 'api_prechecking'@'localhost'
    IDENTIFIED BY '«PASSWORD_DA_API»';

GRANT INSERT ON hostel_prechecking.pendentes TO 'api_prechecking'@'localhost';
GRANT SELECT, UPDATE (usado_em) ON hostel_prechecking.tokens
    TO 'api_prechecking'@'localhost';


-- --------------------------------------------------------------------
-- A aplicação desktop — entra pelo túnel SSH.
-- --------------------------------------------------------------------
-- Também 'localhost': por causa do túnel, a ligação chega ao MySQL
-- como se viesse de dentro da própria máquina. É mais uma razão para o
-- 3306 nunca precisar de estar aberto.

CREATE USER IF NOT EXISTS 'app_desktop'@'localhost'
    IDENTIFIED BY '«PASSWORD_DA_APP»';

GRANT SELECT, INSERT, UPDATE, DELETE ON hostel_gestao.*
    TO 'app_desktop'@'localhost';

-- Na caixa de entrada: lê, importa e apaga. E emite os tokens.
GRANT SELECT, DELETE ON hostel_prechecking.pendentes
    TO 'app_desktop'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON hostel_prechecking.tokens
    TO 'app_desktop'@'localhost';

FLUSH PRIVILEGES;


-- ====================================================================
-- DADOS INICIAIS — a versão 1.0 de cada documento
-- ====================================================================
-- O texto abaixo é um marcador. Substituir pelo conteúdo real dos
-- documentos antes de usar em produção, e subir a versão sempre que o
-- texto mudar (nunca editar uma linha já existente).
-- ====================================================================

USE hostel_gestao;

INSERT INTO textos_legais (tipo, versao, texto, publicado_em, em_vigor)
VALUES
    ('privacidade_hospede', '1.0',
     '«COLAR AQUI O TEXTO DA INFORMAÇÃO DE PRIVACIDADE DO HÓSPEDE»',
     '2026-09-22', 1),
    ('privacidade_colaborador', '1.0',
     '«COLAR AQUI O TEXTO DA INFORMAÇÃO DE PRIVACIDADE DO COLABORADOR»',
     '2026-09-22', 1),
    ('confidencialidade', '1.0',
     '«COLAR AQUI O TEXTO DO TERMO DE CONFIDENCIALIDADE»',
     '2026-09-22', 1)
ON DUPLICATE KEY UPDATE texto = VALUES(texto);

