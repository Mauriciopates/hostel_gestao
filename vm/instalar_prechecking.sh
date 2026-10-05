#!/usr/bin/env bash
# =====================================================================
# instalar_prechecking.sh — Caixa de entrada do pré check-in (site)
#
# Complementa o instalar_vm.sh. Corre DEPOIS dele, na mesma VM.
#
# O QUE FAZ:
#   1. Verifica que o instalar_vm.sh já correu (pasta, .env, contentor).
#   2. Acrescenta ao /opt/hostel/.env a password da API (gerada 1 vez).
#   3. Cria a base `hostel_prechecking` com as tabelas `tokens` e
#      `pendentes` (desenho do ficheiro 08 + decisões de 05/10/2026).
#   4. Cria o utilizador `api_prechecking` (só escreve na caixa de
#      entrada) e dá ao `hostel_app` (desktop) o que precisa nela.
#   5. TESTA as permissões: confirma que a API consegue o que deve e
#      que é RECUSADA em tudo o resto.
#
# PORQUÊ UMA BASE SEPARADA: a API é a única peça alcançável a partir
# da internet. Se for comprometida, só chega a esta caixa de entrada —
# nunca à hostel_gestao (clientes, contratos, stock).
#
# NENHUMA PASSWORD É ESCRITA À MÃO: o SQL de root usa a variável do
# próprio contentor, e a password da API vive só no .env (600).
#
# IDEMPOTENTE: pode correr-se várias vezes sem perder dados.
#
# USO (na VM):   sudo bash instalar_prechecking.sh
#
# ATENÇÃO: fins de linha LF (garantido pelo .gitattributes).
# =====================================================================

set -euo pipefail

# --------------------------------------------------------------------
# Configuração (os mesmos valores do instalar_vm.sh)
# --------------------------------------------------------------------
readonly PASTA="/opt/hostel"
readonly FICH_ENV="${PASTA}/.env"
readonly CONTENTOR="hostel_mysql"
readonly BASE="hostel_prechecking"
readonly BASE_SISTEMA="hostel_gestao"
readonly UTIL_API="api_prechecking"
readonly UTIL_APP="hostel_app"

# --------------------------------------------------------------------
# Funções de apoio
# --------------------------------------------------------------------
passo() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
info()  { printf '    %s\n' "$*"; }
ok()    { printf '    \033[1;32mOK\033[0m  %s\n' "$*"; }
erro()  { printf '\033[1;31mERRO: %s\033[0m\n' "$*" >&2; exit 1; }

gerar_password() {
    openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | cut -c1-24
}

# SQL como root DENTRO do contentor (igual ao instalar_vm.sh): o SQL
# entra pelo stdin e a password vem da variável do contentor.
sql_root() {
    docker exec -i "${CONTENTOR}" \
        sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch'
}

# SQL como a API, pela rede (-h 127.0.0.1), tal como a API vai ligar.
# "-e MYSQL_PWD" sem "=" passa o valor do ambiente: a password não
# aparece na linha de comando (nem no `ps`).
sql_api() {
    MYSQL_PWD="${API_PRECHECKING_PASSWORD}" \
        docker exec -i -e MYSQL_PWD "${CONTENTOR}" \
        mysql -h 127.0.0.1 -u"${UTIL_API}" --batch --skip-column-names
}

# Testes: o comando TEM de funcionar / TEM de ser recusado.
deve_aceitar() {
    local descricao="$1" sql="$2"
    if printf '%s\n' "${sql}" | sql_api >/dev/null 2>&1; then
        ok "API pode: ${descricao}"
    else
        erro "a API devia poder '${descricao}' e foi recusada."
    fi
}
deve_recusar() {
    local descricao="$1" sql="$2"
    if printf '%s\n' "${sql}" | sql_api >/dev/null 2>&1; then
        erro "FALHA DE SEGURANÇA: a API conseguiu '${descricao}'."
    else
        ok "API recusada: ${descricao}"
    fi
}

# --------------------------------------------------------------------
# 1. Verificações
# --------------------------------------------------------------------
passo "1/5 Verificações"
[[ ${EUID} -eq 0 ]] || erro "correr com sudo: sudo bash $0"
[[ -f "${FICH_ENV}" ]] || erro "${FICH_ENV} não existe. Correr antes o instalar_vm.sh."
[[ "$(docker inspect -f '{{.State.Health.Status}}' "${CONTENTOR}" \
       2>/dev/null)" == "healthy" ]] \
    || erro "o contentor ${CONTENTOR} não está a correr (healthy)."
command -v openssl >/dev/null 2>&1 || erro "falta o openssl."
info "Pasta, .env e contentor — ok"

# --------------------------------------------------------------------
# 2. Password da API no .env
# --------------------------------------------------------------------
passo "2/5 Password da API"
if grep -q '^API_PRECHECKING_PASSWORD=' "${FICH_ENV}"; then
    info "Já existe no .env — mantida."
else
    printf 'API_PRECHECKING_PASSWORD=%s\n' "$(gerar_password)" \
        >> "${FICH_ENV}"
    info "Gerada e guardada no .env (não é mostrada)."
fi
chown root:root "${FICH_ENV}"
chmod 600 "${FICH_ENV}"

# shellcheck disable=SC1090
. "${FICH_ENV}"
[[ -n "${API_PRECHECKING_PASSWORD:-}" ]] \
    || erro "API_PRECHECKING_PASSWORD vazia no ${FICH_ENV}."

# --------------------------------------------------------------------
# 3. Base e tabelas
# --------------------------------------------------------------------
passo "3/5 Base '${BASE}' e tabelas"
sql_root <<'EOF'
CREATE DATABASE IF NOT EXISTS hostel_prechecking
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE hostel_prechecking;

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
EOF
info "Base e tabelas prontas."

# --------------------------------------------------------------------
# 4. Utilizadores e permissões
# --------------------------------------------------------------------
passo "4/5 Utilizadores e permissões"
# '@%' e não '@localhost': com o Docker a ligação chega ao MySQL
# vinda da rede interna (172.x). A exposição continua limitada pela
# porta em 127.0.0.1 (só dentro da VM) — ver instalar_vm.sh.
sql_root <<EOF
CREATE USER IF NOT EXISTS '${UTIL_API}'@'%'
    IDENTIFIED BY '${API_PRECHECKING_PASSWORD}';
ALTER USER '${UTIL_API}'@'%'
    IDENTIFIED BY '${API_PRECHECKING_PASSWORD}'
    FAILED_LOGIN_ATTEMPTS 3 PASSWORD_LOCK_TIME 1;

-- A API: inserir um pré check-in, ler um token, marcá-lo como usado.
-- NADA MAIS: não lê pendentes, não apaga, não cria tokens, não vê a
-- ${BASE_SISTEMA}.
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '${UTIL_API}'@'%';
GRANT INSERT ON ${BASE}.pendentes TO '${UTIL_API}'@'%';
GRANT SELECT, UPDATE (usado_em) ON ${BASE}.tokens TO '${UTIL_API}'@'%';

-- O desktop (o hostel_app que já existe): emite tokens, lê e
-- importa/rejeita/apaga os pendentes.
GRANT SELECT, INSERT, UPDATE, DELETE ON ${BASE}.tokens
    TO '${UTIL_APP}'@'%';
GRANT SELECT, UPDATE (estado), DELETE ON ${BASE}.pendentes
    TO '${UTIL_APP}'@'%';

FLUSH PRIVILEGES;
EOF
info "api_prechecking criado; hostel_app com acesso à caixa de entrada."

# --------------------------------------------------------------------
# 5. Testes de permissões (com dados de teste, apagados no fim)
# --------------------------------------------------------------------
passo "5/5 Testes de permissões"
# Hash de teste fixo (64 zeros): na prática impossível de coincidir
# com um token real (os reais são SHA-256 de 32 bytes aleatórios).
readonly HASH_TESTE="0000000000000000000000000000000000000000000000000000000000000000"

limpar_teste() {
    sql_root <<EOF >/dev/null 2>&1 || true
DELETE FROM ${BASE}.pendentes WHERE token_hash = '${HASH_TESTE}';
DELETE FROM ${BASE}.tokens    WHERE token_hash = '${HASH_TESTE}';
EOF
}
trap limpar_teste EXIT
limpar_teste

sql_root <<EOF
INSERT INTO ${BASE}.tokens
    (token_hash, referencia, criado_por_id, valido_ate, versao_aviso,
     unidade, morada, data_entrada, data_saida, hora_checkin,
     hora_checkout)
VALUES
    ('${HASH_TESTE}', 'TESTE', 'TESTE', NOW() + INTERVAL 1 DAY, '1.0',
     'Unidade teste', 'Morada teste', CURDATE(), CURDATE(),
     '15:00', '11:00');
EOF

# A base TEM de recusar um pendente sem as confirmações obrigatórias,
# mesmo vindo de quem tem permissão (o root). Corre ANTES do teste da
# API, para a recusa vir do CHECK e não do UNIQUE do token.
if sql_root >/dev/null 2>&1 <<EOF
INSERT INTO ${BASE}.pendentes (token_hash, nome, nacionalidade,
    data_nascimento, tipo_documento, numero_documento,
    pais_emissor_documento, pais_residencia, versao_aviso,
    informado_privacidade, aceitou_regulamento)
VALUES ('${HASH_TESTE}','T','T','1990-01-01','T','T','T','T','1.0',0,1);
EOF
then
    erro "a base aceitou um pendente sem 'informado_privacidade'."
else
    ok "Base recusa pendente sem as confirmações obrigatórias"
fi

# O que a API TEM de conseguir
deve_aceitar "ler um token" \
    "SELECT unidade FROM ${BASE}.tokens WHERE token_hash='${HASH_TESTE}';"
deve_aceitar "marcar o token como usado" \
    "UPDATE ${BASE}.tokens SET usado_em=NOW() WHERE token_hash='${HASH_TESTE}' AND usado_em IS NULL;"
deve_aceitar "inserir um pré check-in" \
    "INSERT INTO ${BASE}.pendentes (token_hash, nome, nacionalidade, data_nascimento, tipo_documento, numero_documento, pais_emissor_documento, pais_residencia, versao_aviso, informado_privacidade, aceitou_regulamento) VALUES ('${HASH_TESTE}','Teste','Portuguesa','1990-01-01','Passaporte','X1','Portugal','Portugal','1.0',1,1);"

# O que a API NÃO PODE fazer
deve_recusar "ler os pendentes" \
    "SELECT nome FROM ${BASE}.pendentes;"
deve_recusar "apagar pendentes" \
    "DELETE FROM ${BASE}.pendentes;"
deve_recusar "criar tokens" \
    "INSERT INTO ${BASE}.tokens (token_hash) VALUES ('x');"
deve_recusar "apagar tokens" \
    "DELETE FROM ${BASE}.tokens;"
deve_recusar "alterar os detalhes de um token" \
    "UPDATE ${BASE}.tokens SET unidade='x' WHERE token_hash='${HASH_TESTE}';"
deve_recusar "ver a ${BASE_SISTEMA}" \
    "SELECT 1 FROM ${BASE_SISTEMA}.clientes LIMIT 1;"
deve_recusar "criar tabelas" \
    "CREATE TABLE ${BASE}.lixo (id INT);"

info "Dados de teste apagados."

# --------------------------------------------------------------------
# Resumo
# --------------------------------------------------------------------
cat <<EOF

  Caixa de entrada pronta: base ${BASE} (tabelas tokens, pendentes)
  Utilizador da API: ${UTIL_API}  (password em ${FICH_ENV})
  O ${UTIL_APP} (desktop) já pode emitir tokens e importar pendentes.

  Próximo passo: instalar a API (FastAPI) nesta VM.

EOF
