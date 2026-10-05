-- =====================================================================
-- Hostel Clean — ESQUEMA OFICIAL DA BASE `hostel_prechecking`
-- (caixa de entrada do pré check-in — F1 de 05/10/2026)
-- =====================================================================
-- Base SEPARADA da `hostel_gestao`: é a única parte alcançável a partir
-- da internet (pela API). Ver o ficheiro 08 do projeto.
--
-- Na VM é criada pelo `vm/instalar_prechecking.sh` (que leva estas
-- mesmas instruções — o `testes/teste_prechecking.py` confirma que os
-- dois ficheiros não divergem). Aqui serve de documentação oficial (nada
-- de tabelas soltas) e para os testes criarem `hostel_prechecking_teste`.
--
-- REGRA: mudar estas tabelas = mudar AQUI e no instalar_prechecking.sh
-- no mesmo commit.
-- =====================================================================

-- ---------------------------------------------------------------
-- tokens — um link por reserva, de uso único e com validade
-- ---------------------------------------------------------------
-- O link leva o token em claro (?t=...), mas a base só guarda o
-- HASH SHA-256 dele. Se esta tabela for roubada, os hashes não
-- servem para abrir nenhum link (o mesmo princípio das passwords).
--
-- Emitido pelo desktop, que copia para aqui os DETALHES que o
-- hóspede pode ver. A API nunca lê a hostel_gestao: tudo o que
-- mostra ao hóspede está nesta linha. SEM código da lockbox
-- (decisão de 05/10/2026: vai por mensagem do Airbnb).
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tokens (
    token_hash      CHAR(64)      NOT NULL PRIMARY KEY,

    -- A que estadia corresponde (id da reserva na hostel_gestao).
    referencia      VARCHAR(100)  NOT NULL,

    criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por_id   VARCHAR(10)   NOT NULL,

    -- Depois desta data a API recusa. Sugestão: data de saída + 1 dia.
    valido_ate      DATETIME      NOT NULL,

    -- Uso único: preenchido na primeira submissão aceite.
    usado_em        DATETIME      NULL,

    -- Versão do aviso de privacidade em vigor quando o link foi
    -- emitido. A API copia-a para o pendente: é a prova do texto
    -- que foi mostrado (art. 5.º/2).
    versao_aviso    VARCHAR(20)   NOT NULL,

    -- ---- detalhes da reserva mostrados ao hóspede ----
    unidade         VARCHAR(100)  NOT NULL,
    morada          VARCHAR(255)  NOT NULL,
    data_entrada    DATE          NOT NULL,
    data_saida      DATE          NOT NULL,
    hora_checkin    TIME          NOT NULL,
    hora_checkout   TIME          NOT NULL,
    regras          TEXT          NULL,

    CONSTRAINT ck_token_datas CHECK (data_saida >= data_entrada),
    INDEX idx_token_validade (valido_ate, usado_em),
    INDEX idx_token_referencia (referencia)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------
-- pendentes — o que o site submeteu, à espera de validação
-- ---------------------------------------------------------------
-- Apagados assim que importados: dados pessoais não ficam parados
-- na parte da máquina exposta à internet.
-- NÃO se guarda o IP (minimização, art. 5.º/1/c).
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pendentes (
    id                      INT AUTO_INCREMENT PRIMARY KEY,

    -- UNIQUE: um token só pode gerar UM pendente, mesmo que dois
    -- pedidos cheguem ao mesmo tempo. A base garante-o sozinha.
    token_hash              CHAR(64)     NOT NULL,

    -- submetido_em: relógio do telemóvel (não é de confiar)
    -- recebido_em:  carimbo do servidor (é este que faz prova)
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

    -- Só preenchido se o hóspede consentir comunicações: sem
    -- consentimento, o email não é recolhido (minimização).
    email                   VARCHAR(254) NULL,

    -- ---- as três confirmações, separadas ----
    versao_aviso            VARCHAR(20)  NOT NULL,
    informado_privacidade   TINYINT(1)   NOT NULL,
    aceitou_regulamento     TINYINT(1)   NOT NULL,
    consente_comunicacoes   TINYINT(1)   NOT NULL DEFAULT 0,

    estado                  ENUM('pendente', 'importado', 'rejeitado')
                            NOT NULL DEFAULT 'pendente',

    -- As duas primeiras são obrigatórias para a estadia: a base
    -- recusa um pendente sem elas, mesmo que a API falhe a validar.
    CONSTRAINT ck_pendente_informado CHECK (informado_privacidade = 1),
    CONSTRAINT ck_pendente_regulamento CHECK (aceitou_regulamento = 1),
    -- Consentimento sem email não serve; email sem consentimento
    -- não se guarda.
    CONSTRAINT ck_pendente_email CHECK (
        (consente_comunicacoes = 1 AND email IS NOT NULL)
        OR (consente_comunicacoes = 0 AND email IS NULL)
    ),

    CONSTRAINT uq_pendente_token UNIQUE (token_hash),
    CONSTRAINT fk_pendente_token
        FOREIGN KEY (token_hash) REFERENCES tokens (token_hash)
        ON DELETE RESTRICT ON UPDATE RESTRICT,

    INDEX idx_pendente_estado (estado, recebido_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
