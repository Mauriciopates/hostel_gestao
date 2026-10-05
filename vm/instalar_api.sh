#!/usr/bin/env bash
# =====================================================================
# instalar_api.sh — API do pré check-in (FastAPI) na VM
#
# Corre DEPOIS do instalar_vm.sh e do instalar_prechecking.sh.
#
# O QUE FAZ:
#   1. Verifica a VM (.env com a password da API, contentor, pasta api/).
#   2. Instala o que falta (python3-venv).
#   3. Cria o utilizador de sistema `hostel_api` (sem shell, sem login):
#      é com ele que a API corre — nunca como root.
#   4. Copia o código para /opt/hostel-api (dono root: a API lê, mas
#      não consegue alterar o próprio código) e cria o ambiente
#      virtual com as dependências. Corre os testes unitários.
#   5. Cria /opt/hostel/api.env SÓ com a password da API (o .env
#      principal tem também a de root, que a API nunca vê) e o serviço
#      systemd `hostel-api`, que arranca sozinho com a VM.
#   6. TESTA a API a correr, com um token de teste (apagado no fim).
#
# A API OUVE SÓ EM 127.0.0.1:8000. Nada de fora da VM lhe chega
# diretamente; na F3 o Tailscale Funnel publica-a em HTTPS.
#
# IDEMPOTENTE: correr outra vez = atualizar o código e reiniciar.
#
# USO:
#   PC (Git Bash, na raiz do repositório):
#     scp -r api vm/instalar_api.sh nova-vm@192.168.56.11:~/
#   VM (depois do ssh):
#     sudo bash instalar_api.sh
#
# ATENÇÃO: fins de linha LF (garantido pelo .gitattributes).
# =====================================================================

set -euo pipefail

# --------------------------------------------------------------------
# Configuração
# --------------------------------------------------------------------
readonly PASTA="/opt/hostel"
readonly FICH_ENV="${PASTA}/.env"
readonly FICH_ENV_API="${PASTA}/api.env"
# FORA de /opt/hostel: essa pasta é 700 (só o root entra, decisão do
# instalar_vm.sh) e o utilizador hostel_api tem de conseguir ler o código.
readonly PASTA_API="/opt/hostel-api"
readonly PASTA_API_ANTIGA="${PASTA}/api"     # 1.ª versão deste script
readonly CONTENTOR="hostel_mysql"
readonly BASE="hostel_prechecking"
readonly UTIL_SISTEMA="hostel_api"
readonly SERVICO="hostel-api"
readonly PORTA_API="8000"
readonly URL="http://127.0.0.1:${PORTA_API}"
readonly ORIGEM_SITE="https://mauriciopates.github.io"

# --------------------------------------------------------------------
# Funções de apoio (as mesmas dos outros scripts)
# --------------------------------------------------------------------
passo() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
info()  { printf '    %s\n' "$*"; }
ok()    { printf '    \033[1;32mOK\033[0m  %s\n' "$*"; }
erro()  { printf '\033[1;31mERRO: %s\033[0m\n' "$*" >&2; exit 1; }

sql_root() {
    docker exec -i "${CONTENTOR}" \
        sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch'
}

# Teste: o código HTTP obtido TEM de ser o esperado.
verificar() {
    local descricao="$1" esperado="$2" obtido="$3"
    if [[ "${obtido}" == "${esperado}" ]]; then
        ok "${descricao} (${obtido})"
    else
        erro "${descricao}: esperado ${esperado}, obtido ${obtido}."
    fi
}

# POST JSON; escreve só o código HTTP. O corpo vai para $RESPOSTA.
RESPOSTA="$(mktemp)"
readonly RESPOSTA
post() {
    curl -s -o "${RESPOSTA}" -w '%{http_code}' -X POST \
        -H 'Content-Type: application/json' "$@"
}

# --------------------------------------------------------------------
# 1. Verificações
# --------------------------------------------------------------------
passo "1/6 Verificações"
[[ ${EUID} -eq 0 ]] || erro "correr com sudo: sudo bash $0"
[[ -f "${FICH_ENV}" ]] || erro "${FICH_ENV} não existe. Correr antes o instalar_vm.sh."
grep -q '^API_PRECHECKING_PASSWORD=.' "${FICH_ENV}" \
    || erro "falta a password da API. Correr antes o instalar_prechecking.sh."
[[ "$(docker inspect -f '{{.State.Health.Status}}' "${CONTENTOR}" \
       2>/dev/null)" == "healthy" ]] \
    || erro "o contentor ${CONTENTOR} não está a correr (healthy)."

# A pasta api/ ao lado do script (scp para ~) ou na raiz do repositório.
DIR_SCRIPT="$(cd "$(dirname "$0")" && pwd)"
ORIGEM=""
for candidato in "${DIR_SCRIPT}/api" "${DIR_SCRIPT}/../api"; do
    if [[ -f "${candidato}/prechecking/app.py" ]]; then
        ORIGEM="$(cd "${candidato}" && pwd)"
        break
    fi
done
[[ -n "${ORIGEM}" ]] || erro "não encontrei a pasta api/ ao lado do script (scp -r api ...)."
info "Código da API: ${ORIGEM}"

# --------------------------------------------------------------------
# 2. Pacotes
# --------------------------------------------------------------------
passo "2/6 Pacotes"
if ! python3 -c 'import venv, ensurepip' >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq python3-venv
fi
command -v curl >/dev/null 2>&1 || apt-get install -y -qq curl
info "$(python3 --version) com venv — ok"

# --------------------------------------------------------------------
# 3. Utilizador de sistema
# --------------------------------------------------------------------
passo "3/6 Utilizador '${UTIL_SISTEMA}'"
if id "${UTIL_SISTEMA}" >/dev/null 2>&1; then
    info "Já existe."
else
    useradd --system --no-create-home --home-dir /nonexistent \
        --shell /usr/sbin/nologin "${UTIL_SISTEMA}"
    info "Criado (sem shell e sem password: ninguém entra com ele)."
fi

# --------------------------------------------------------------------
# 4. Código, ambiente virtual e testes unitários
# --------------------------------------------------------------------
passo "4/6 Código e ambiente virtual"
# A 1.ª versão punha o código dentro de /opt/hostel (700): o serviço
# falhava com "CHDIR: Permission denied". Arruma essa cópia.
if [[ -d "${PASTA_API_ANTIGA}" ]]; then
    systemctl stop "${SERVICO}" 2>/dev/null || true
    rm -rf "${PASTA_API_ANTIGA}"
    info "Removida a cópia antiga em ${PASTA_API_ANTIGA}."
fi
install -m 0755 -o root -g root -d "${PASTA_API}"
rm -rf "${PASTA_API}/prechecking" "${PASTA_API}/testes"
cp -r "${ORIGEM}/prechecking" "${ORIGEM}/testes" \
      "${ORIGEM}/requirements.txt" "${PASTA_API}/"
find "${PASTA_API}" -name '__pycache__' -type d -prune -exec rm -rf {} +
chown -R root:root "${PASTA_API}"
chmod -R u=rwX,go=rX "${PASTA_API}"

if [[ ! -x "${PASTA_API}/.venv/bin/python" ]]; then
    python3 -m venv "${PASTA_API}/.venv"
fi
"${PASTA_API}/.venv/bin/pip" install -q --upgrade pip
"${PASTA_API}/.venv/bin/pip" install -q -r "${PASTA_API}/requirements.txt"
info "Dependências instaladas."

info "Testes unitários:"
if ! (cd "${PASTA_API}" && PYTHONDONTWRITEBYTECODE=1 \
        .venv/bin/python -m unittest discover -s testes \
        -p 'teste_*.py' 2>&1 | tail -n 3 | sed 's/^/      /'; \
        exit "${PIPESTATUS[0]}"); then
    erro "testes unitários falharam (ver: cd ${PASTA_API} && sudo .venv/bin/python -m unittest discover -s testes -p 'teste_*.py' -v). Serviço NÃO alterado."
fi
ok "Testes unitários"

# --------------------------------------------------------------------
# 5. api.env e serviço systemd
# --------------------------------------------------------------------
passo "5/6 Serviço '${SERVICO}'"
# shellcheck disable=SC1090
API_PRECHECKING_PASSWORD="$(. "${FICH_ENV}" && printf '%s' "${API_PRECHECKING_PASSWORD}")"
umask 077
printf 'API_PRECHECKING_PASSWORD=%s\n' "${API_PRECHECKING_PASSWORD}" \
    > "${FICH_ENV_API}"
unset API_PRECHECKING_PASSWORD
umask 022
chown root:root "${FICH_ENV_API}"
chmod 600 "${FICH_ENV_API}"
info "${FICH_ENV_API} (600, root) — só a password da API."

cat > "/etc/systemd/system/${SERVICO}.service" <<EOF
[Unit]
Description=Hostel Gestao - API do pre check-in
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=${UTIL_SISTEMA}
Group=${UTIL_SISTEMA}
WorkingDirectory=${PASTA_API}
# O systemd lê este ficheiro como root ANTES de baixar para o
# utilizador hostel_api: a API recebe a password sem poder ler o ficheiro.
EnvironmentFile=${FICH_ENV_API}
Environment=PYTHONDONTWRITEBYTECODE=1
# --proxy-headers: atrás do Funnel, o IP real vem no X-Forwarded-For,
# aceite SÓ quando o pedido chega de 127.0.0.1 (o próprio Tailscale).
ExecStart=${PASTA_API}/.venv/bin/uvicorn prechecking.app:app \\
    --host 127.0.0.1 --port ${PORTA_API} --workers 1 \\
    --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=on-failure
RestartSec=5

# ---- Endurecimento: se a API for comprometida, fica numa caixa ----
NoNewPrivileges=yes
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictNamespaces=yes
RestrictSUIDSGID=yes
LockPersonality=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICO}" >/dev/null 2>&1
systemctl restart "${SERVICO}"
info "Serviço ativo e a arrancar com a VM."

# --------------------------------------------------------------------
# 6. Testes com a API a correr (token de teste, apagado no fim)
# --------------------------------------------------------------------
passo "6/6 Testes com a API a correr"

# Espera até 20 s que a API responda.
for _ in $(seq 1 20); do
    curl -s -o /dev/null "${URL}/api/saude" && break
    sleep 1
done
verificar "API responde em ${URL}" "200" \
    "$(curl -s -o /dev/null -w '%{http_code}' "${URL}/api/saude")"

# A porta só pode estar em 127.0.0.1 (nunca 0.0.0.0).
if ss -ltnH "sport = :${PORTA_API}" | awk '{print $4}' \
        | grep -qv "^127\.0\.0\.1:"; then
    erro "a porta ${PORTA_API} está aberta para fora da VM."
fi
ok "Porta ${PORTA_API} só em 127.0.0.1"

# Token aleatório (como o desktop fará) e o seu hash SHA-256.
TOKEN_TESTE="$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=\n')"
HASH_TESTE="$(printf '%s' "${TOKEN_TESTE}" | sha256sum | cut -c1-64)"

limpar_teste() {
    sql_root <<EOF >/dev/null 2>&1 || true
DELETE FROM ${BASE}.pendentes WHERE token_hash = '${HASH_TESTE}';
DELETE FROM ${BASE}.tokens    WHERE token_hash = '${HASH_TESTE}';
EOF
    rm -f "${RESPOSTA}"
}
trap limpar_teste EXIT

sql_root <<EOF
INSERT INTO ${BASE}.tokens
    (token_hash, referencia, criado_por_id, valido_ate, versao_aviso,
     unidade, morada, data_entrada, data_saida, hora_checkin,
     hora_checkout)
VALUES
    ('${HASH_TESTE}', 'TESTE', 'TESTE', NOW() + INTERVAL 1 HOUR, '1.0',
     'Unidade teste', 'Morada teste', CURDATE(), CURDATE(),
     '15:00', '11:00');
EOF

PRE_CHECKIN="$(cat <<EOF
{"token": "${TOKEN_TESTE}", "versao_aviso": "1.0",
 "cliente": {"nome": "Teste", "nacionalidade": "Portuguesa",
   "data_nascimento": "1990-01-01", "tipo_documento": "Passaporte",
   "numero_documento": "X0", "pais_emissor_documento": "Portugal",
   "pais_residencia": "Portugal"},
 "confirmacoes": {"informado_privacidade": true,
   "aceitou_regulamento": true, "consente_comunicacoes": false}}
EOF
)"

verificar "Reserva com token válido" "200" \
    "$(post -d "{\"token\": \"${TOKEN_TESTE}\"}" "${URL}/api/reserva")"
grep -q '"Unidade teste"' "${RESPOSTA}" \
    || erro "a reserva não trouxe os detalhes da unidade."

verificar "Pré check-in gravado" "201" \
    "$(post -d "${PRE_CHECKIN}" "${URL}/api/pre-checkin")"

verificar "Segundo envio com o mesmo token recusado" "404" \
    "$(post -d "${PRE_CHECKIN}" "${URL}/api/pre-checkin")"

verificar "Link já usado deixa de abrir" "404" \
    "$(post -d "{\"token\": \"${TOKEN_TESTE}\"}" "${URL}/api/reserva")"

verificar "Token inexistente" "404" \
    "$(post -d "{\"token\": \"$(printf 'x%.0s' {1..43})\"}" \
        "${URL}/api/reserva")"

verificar "Corpo gigante recusado" "413" \
    "$(head -c 100000 /dev/zero | tr '\0' 'a' \
        | post --data-binary @- "${URL}/api/pre-checkin")"

if curl -s -D - -o /dev/null -X OPTIONS "${URL}/api/pre-checkin" \
        -H 'Origin: https://site-malicioso.example' \
        -H 'Access-Control-Request-Method: POST' \
        | grep -qi '^access-control-allow-origin'; then
    erro "FALHA DE SEGURANÇA: CORS aceitou outra origem."
fi
ok "CORS recusa outra origem"

curl -s -D - -o /dev/null -X OPTIONS "${URL}/api/pre-checkin" \
        -H "Origin: ${ORIGEM_SITE}" \
        -H 'Access-Control-Request-Method: POST' \
        -H 'Access-Control-Request-Headers: content-type' \
    | grep -qi "^access-control-allow-origin: ${ORIGEM_SITE}" \
    || erro "CORS não aceitou o site ${ORIGEM_SITE}."
ok "CORS aceita o site"

# O pendente ficou mesmo na base, com a versão do aviso do token.
CONTAGEM="$(printf "SELECT COUNT(*) FROM %s.pendentes WHERE token_hash='%s';\n" \
    "${BASE}" "${HASH_TESTE}" | sql_root | tail -n 1)"
[[ "${CONTAGEM}" == "1" ]] \
    || erro "o pré check-in não ficou na tabela pendentes."
ok "Pendente gravado na base"

info "Dados de teste apagados."

# --------------------------------------------------------------------
# Resumo
# --------------------------------------------------------------------
cat <<EOF

  API do pré check-in a correr: ${URL}  (só dentro da VM)
  Serviço: ${SERVICO}   (utilizador ${UTIL_SISTEMA}, arranca com a VM)

  Comandos úteis (VM):
    sudo systemctl status ${SERVICO}
    sudo journalctl -u ${SERVICO} -n 50
    curl ${URL}/api/saude

  Próximo passo (F3): Tailscale Funnel para a porta ${PORTA_API}.

EOF
