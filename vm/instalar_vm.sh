#!/usr/bin/env bash
# =====================================================================
# instalar_vm.sh — Provisionamento do servidor de base de dados do
# Hostel Gestão (INST-05, v1.8.0)
#
# O QUE FAZ (num Ubuntu limpo, com um só comando):
#   1. Verifica que corre como root num Ubuntu.
#   2. Instala o Docker Engine + plugin compose (só se faltarem).
#   3. Cria /opt/hostel/ com:
#        .env                -> passwords (geradas 1 vez, permissões 600)
#        docker-compose.yml  -> MySQL 8.4 LTS em 127.0.0.1:6213
#   4. Arranca o contentor e espera que o MySQL esteja pronto.
#   5. Cria a base `hostel_gestao` e o utilizador `hostel_app` com
#      permissões mínimas e bloqueio após 3 falhas de login.
#   6. Mostra o resumo para configurar o seletor de servidores.
#
# AS TABELAS NÃO SÃO CRIADAS AQUI: é a aplicação que as cria no 1.º
# arranque a partir do src/bd/esquema.sql (INST-02, decisão D7 — o
# esquema tem uma só fonte).
#
# IDEMPOTENTE: pode correr-se várias vezes. O que já existe é mantido
# (em particular o .env — gerar passwords novas trancava a app fora).
#
# USO (na VM):   sudo bash instalar_vm.sh
#
# ATENÇÃO: este ficheiro tem de ter fins de linha LF (Unix). Com CRLF
# o bash falha com erros como "$'\r': command not found".
# =====================================================================

# -e: para ao primeiro erro | -u: variável não definida é erro
# -o pipefail: um erro no meio de um "a | b" também conta
set -euo pipefail

# --------------------------------------------------------------------
# Configuração (valores fixos — NUNCA passwords aqui: vai para o Git)
# --------------------------------------------------------------------
readonly PASTA="/opt/hostel"
readonly FICH_ENV="${PASTA}/.env"
readonly FICH_COMPOSE="${PASTA}/docker-compose.yml"
readonly CONTENTOR="hostel_mysql"
readonly IMAGEM="mysql:8.4"          # LTS; o 8.0 terminou em 04/2026
readonly PORTA_VM="6213"             # só em 127.0.0.1 (decisão D13)
readonly BASE="hostel_gestao"
readonly UTIL_APP="hostel_app"
readonly ESPERA_MAX_S=180            # tempo máximo à espera do MySQL

# --------------------------------------------------------------------
# Funções de apoio
# --------------------------------------------------------------------
passo() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
info()  { printf '    %s\n' "$*"; }
erro()  { printf '\033[1;31mERRO: %s\033[0m\n' "$*" >&2; exit 1; }

# Password aleatória só com letras e números: evita problemas de
# aspas no SQL e no .env, mantendo ~140 bits de entropia (24 chars).
gerar_password() {
    openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | cut -c1-24
}

# Corre SQL como root DENTRO do contentor. O SQL entra pelo stdin
# (não aparece no `ps`) e a password do root é lida da variável do
# próprio contentor (as aspas simples impedem que o host a expanda).
sql_root() {
    docker exec -i "${CONTENTOR}" \
        sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch'
}

# --------------------------------------------------------------------
# 1. Verificações iniciais
# --------------------------------------------------------------------
passo "1/6 Verificações"
[[ ${EUID} -eq 0 ]] || erro "correr com sudo: sudo bash $0"
[[ -r /etc/os-release ]] || erro "/etc/os-release não encontrado."
# shellcheck disable=SC1091
. /etc/os-release
[[ "${ID}" == "ubuntu" ]] || erro "este script é só para Ubuntu."
info "Ubuntu ${VERSION_ID} (${VERSION_CODENAME}) — ok"

# --------------------------------------------------------------------
# 2. Docker Engine + compose (repositório oficial da Docker)
# --------------------------------------------------------------------
passo "2/6 Docker"
if command -v docker >/dev/null 2>&1 \
        && docker compose version >/dev/null 2>&1; then
    info "Docker já instalado: $(docker --version) — a saltar."
else
    info "A instalar pacotes base..."
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl openssl

    info "A adicionar a chave e o repositório da Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture)" \
         "signed-by=/etc/apt/keyrings/docker.asc]" \
         "https://download.docker.com/linux/ubuntu" \
         "${VERSION_CODENAME} stable" \
        > /etc/apt/sources.list.d/docker.list

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    info "Instalado: $(docker --version)"
fi
command -v openssl >/dev/null 2>&1 || apt-get install -y -qq openssl

# --------------------------------------------------------------------
# 3. Pasta, segredos (.env) e docker-compose.yml
# --------------------------------------------------------------------
passo "3/6 Configuração em ${PASTA}"
install -m 0700 -d "${PASTA}"      # só o root entra na pasta

PASSWORDS_NOVAS=0
if [[ -f "${FICH_ENV}" ]]; then
    info ".env já existe — passwords mantidas."
else
    umask 077                      # o ficheiro nasce já com 600
    cat > "${FICH_ENV}" <<EOF
# Segredos do Hostel Gestão — NÃO copiar para o Git.
# Gerado por instalar_vm.sh em $(date '+%Y-%m-%d %H:%M').
MYSQL_ROOT_PASSWORD=$(gerar_password)
HOSTEL_APP_PASSWORD=$(gerar_password)
EOF
    PASSWORDS_NOVAS=1
    info ".env criado com passwords novas (root e app diferentes)."
fi
chown root:root "${FICH_ENV}"
chmod 600 "${FICH_ENV}"

# Lê as passwords do .env para variáveis deste script.
# shellcheck disable=SC1090
. "${FICH_ENV}"
[[ -n "${MYSQL_ROOT_PASSWORD:-}" && -n "${HOSTEL_APP_PASSWORD:-}" ]] \
    || erro "o ${FICH_ENV} não tem as duas passwords."

# O compose é sempre reescrito: é "código", não dados. Os ${...} são
# resolvidos pelo docker compose a partir do .env da mesma pasta —
# por isso o heredoc usa 'EOF' com aspas (o bash não os expande).
cat > "${FICH_COMPOSE}" <<'EOF'
# Gerado por instalar_vm.sh — alterações à mão são reescritas.
name: hostel

services:
  mysql:
    image: IMAGEM_AQUI
    container_name: CONTENTOR_AQUI
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      # root só existe como 'root'@'localhost' = só por docker exec
      MYSQL_ROOT_HOST: localhost
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
    ports:
      # 127.0.0.1 = só por dentro da VM. O Docker ignora o ufw, por
      # isso a restrição TEM de estar aqui. Acesso: túnel SSH.
      - "127.0.0.1:PORTA_AQUI:3306"
    volumes:
      # Os dados vivem no volume: sobrevivem a recriar o contentor.
      # NUNCA usar "docker compose down -v" (apaga o volume).
      - dados_mysql:/var/lib/mysql
    healthcheck:
      # -h 127.0.0.1 obriga a TCP: durante a inicialização o MySQL
      # temporário não aceita TCP, por isso só fica "healthy" quando
      # o servidor definitivo está pronto.
      test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 --silent"]
      interval: 5s
      timeout: 3s
      retries: 30

volumes:
  dados_mysql:
EOF
# Troca os marcadores pelos valores fixos do topo do script.
sed -i -e "s|IMAGEM_AQUI|${IMAGEM}|" \
       -e "s|CONTENTOR_AQUI|${CONTENTOR}|" \
       -e "s|PORTA_AQUI|${PORTA_VM}|" "${FICH_COMPOSE}"
chmod 600 "${FICH_COMPOSE}"
info "docker-compose.yml escrito."

# --------------------------------------------------------------------
# 4. Arrancar e esperar pelo MySQL
# --------------------------------------------------------------------
passo "4/6 Arranque do MySQL (${IMAGEM})"
docker compose -f "${FICH_COMPOSE}" --project-directory "${PASTA}" \
    up -d
info "À espera do healthcheck (máx. ${ESPERA_MAX_S} s)..."
decorrido=0
until [[ "$(docker inspect -f '{{.State.Health.Status}}' \
            "${CONTENTOR}")" == "healthy" ]]; do
    (( decorrido >= ESPERA_MAX_S )) && \
        erro "MySQL não arrancou. Ver: docker logs ${CONTENTOR}"
    sleep 5
    decorrido=$(( decorrido + 5 ))
done
info "MySQL pronto (${decorrido} s)."

# --------------------------------------------------------------------
# 5. Base e utilizador da aplicação
# --------------------------------------------------------------------
passo "5/6 Base '${BASE}' e utilizador '${UTIL_APP}'"
# Porquê '@%': a ligação chega ao contentor vinda da rede interna do
# Docker (172.x), não de localhost. A exposição continua limitada
# pela porta em 127.0.0.1 + túnel SSH.
#
# Permissões mínimas, só nesta base:
#   SELECT/INSERT/UPDATE/DELETE  -> uso normal
#   CREATE/ALTER/INDEX/REFERENCES-> 1.º arranque (esquema) e migrações
#   DROP                         -> TRUNCATE ("Começar do zero")
#   LOCK TABLES                  -> mysqldump (cópias de segurança)
# Sem CREATE DATABASE, sem GRANT, sem privilégios globais (D8).
#
# FAILED_LOGIN_ATTEMPTS 3 PASSWORD_LOCK_TIME 1: 3 passwords erradas
# seguidas bloqueiam a conta 1 dia. O ALTER USER repete a password
# do .env, por isso reexecutar o script volta a sincronizá-la.
sql_root <<EOF
CREATE DATABASE IF NOT EXISTS \`${BASE}\`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS '${UTIL_APP}'@'%'
    IDENTIFIED BY '${HOSTEL_APP_PASSWORD}';
ALTER USER '${UTIL_APP}'@'%'
    IDENTIFIED BY '${HOSTEL_APP_PASSWORD}'
    FAILED_LOGIN_ATTEMPTS 3 PASSWORD_LOCK_TIME 1;

GRANT SELECT, INSERT, UPDATE, DELETE,
      CREATE, ALTER, INDEX, REFERENCES, DROP, LOCK TABLES
    ON \`${BASE}\`.* TO '${UTIL_APP}'@'%';
FLUSH PRIVILEGES;
EOF
info "Base e utilizador prontos."

# Verificação: o utilizador da app entra e vê a base?
if docker exec -i "${CONTENTOR}" \
        mysql -h 127.0.0.1 -u"${UTIL_APP}" \
        -p"${HOSTEL_APP_PASSWORD}" -e "USE \`${BASE}\`;" 2>/dev/null
then
    info "Teste de ligação com ${UTIL_APP}: OK"
else
    erro "o ${UTIL_APP} não conseguiu ligar-se à base."
fi

# --------------------------------------------------------------------
# 6. Resumo
# --------------------------------------------------------------------
passo "6/6 Concluído"
# IP da placa Host-Only (rede 192.168.56.x, a que o PC vê).
IP_VM="$(ip -4 -o addr show | awk '{print $4}' | cut -d/ -f1 \
         | grep '^192\.168\.56\.' | head -n1 || true)"
UTIL_SSH="${SUDO_USER:-<utilizador>}"
if (( PASSWORDS_NOVAS )); then
    LINHA_PASS="Password MySQL: ${HOSTEL_APP_PASSWORD}  (mostrada só agora)"
else
    LINHA_PASS="Password MySQL: a que já estava (sudo cat ${FICH_ENV})"
fi
cat <<EOF

  Servidor MySQL: ${IMAGEM} em 127.0.0.1:${PORTA_VM} (só na VM)
  Configuração:   ${PASTA}  (ver segredos: sudo cat ${FICH_ENV})

  1) Seletor de servidores da app (+ Adicionar):
       Utilizador SSH: ${UTIL_SSH}   Endereço: ${IP_VM:-<ip_da_vm>}
       Porta SSH: 22                 Porta MySQL: ${PORTA_VM}
       Utilizador MySQL: ${UTIL_APP}  Base: ${BASE}
       ${LINHA_PASS}
       (a app abre o túnel sozinha, com a chave SSH do PC)

  2) No 1.º arranque a app deteta a base VAZIA e cria as tabelas.

  Conta bloqueada (3 passwords erradas)? Desbloquear na VM:
    sudo docker restart ${CONTENTOR}

EOF
