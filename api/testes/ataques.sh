#!/usr/bin/env bash
# =====================================================================
# ataques.sh — testes de segurança da API do pré check-in (F6)
#
# Ataca a API PÚBLICA (a mesma morada que o site usa) como um atacante
# faria, e confirma que cada ataque é recusado da forma esperada.
# Não precisa de nenhuma password: só usa o que qualquer pessoa na
# internet tem — o endereço do Funnel.
#
# OS 6 GRUPOS:
#   1. Tokens: inventado, já usado, expirado → 404 e SEMPRE a mesma
#      mensagem (quem tenta adivinhar não sabe qual dos casos acertou).
#   2. CORS: pedido vindo de outro site → sem Access-Control-Allow-
#      Origin (o browser bloqueia a resposta).
#   3. Tamanhos: campo maior do que a coluna → 422; corpo > 8 KB → 413.
#   4. Injeção de SQL no token e nos campos → 422 / tratado como texto.
#   5. Excesso de pedidos: o 11.º pedido no mesmo minuto → 429.
#   6. Extras: /docs e /openapi.json escondidos, método errado → 405,
#      cabeçalhos de segurança, portas 8000 e 6213 fechadas por fora.
#
# NÃO ALTERA NADA: nenhum pedido deste script grava na base. Os
# tokens usados são inventados (formato válido, mas não existem); o
# grupo 1 só testa "usado" e "expirado" se lhe deres esses tokens.
#
# USO — PC (Git Bash, na raiz do repositório hostel_gestao):
#   bash api/testes/ataques.sh
#
# Opcional (variáveis antes do comando):
#   TOKEN_USADO=...      token de um link já submetido (grupo 1)
#   TOKEN_EXPIRADO=...   token de um link fora de validade (grupo 1)
#   IP_VM=...            IP da VM para testar as portas (grupo 6;
#                        por omissão 192.168.56.11)
#   API=...              outra morada (por omissão o Funnel)
#
#   Ex.: TOKEN_USADO=abc... TOKEN_EXPIRADO=xyz... bash api/testes/ataques.sh
#
# DEMORA ~1,5 min: antes do grupo 5 espera 61 s para o limitador de
# pedidos começar do zero (os grupos 1–4 também contam para ele).
#
# Termina com o número de falhas como código de saída (0 = tudo OK).
# =====================================================================

set -u

API="${API:-https://nova-vm.tailce9342.ts.net}"
IP_VM="${IP_VM:-192.168.56.11}"
TOKEN_USADO="${TOKEN_USADO:-}"
TOKEN_EXPIRADO="${TOKEN_EXPIRADO:-}"

ORIGEM_SITE="https://mauriciopates.github.io"
ORIGEM_ATACANTE="https://site-do-atacante.example"

# Formato válido (43 caracteres A-Z a-z 0-9 - _), mas não existe.
TOKEN_FALSO="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

PASTA_TMP="$(mktemp -d)"
trap 'rm -rf "$PASTA_TMP"' EXIT

OK=0
FALHAS=0
SALTADOS=0

# ---------------------------------------------------------------------
# Ajudantes
# ---------------------------------------------------------------------
titulo() {
    printf '\n=== %s ===\n' "$1"
}

ok() {
    OK=$((OK + 1))
    printf '  [OK]      %s\n' "$1"
}

falhou() {
    FALHAS=$((FALHAS + 1))
    printf '  [FALHOU]  %s\n' "$1"
}

saltado() {
    SALTADOS=$((SALTADOS + 1))
    printf '  [SALTADO] %s\n' "$1"
}

# pedir METODO CAMINHO [CORPO_JSON] [ORIGEM]
# Faz o pedido e deixa em $ESTADO o código HTTP, em $CORPO a resposta
# e em $PASTA_TMP/cabecalhos os cabeçalhos.
pedir() {
    local metodo="$1" caminho="$2" corpo="${3:-}" origem="${4:-}"
    local args=(-s -o "$PASTA_TMP/corpo" -D "$PASTA_TMP/cabecalhos"
                -w '%{http_code}' --max-time 15 -X "$metodo")
    [ -n "$origem" ] && args+=(-H "Origin: $origem")
    if [ -n "$corpo" ]; then
        args+=(-H "Content-Type: application/json" --data-binary "$corpo")
    fi
    ESTADO="$(curl "${args[@]}" "$API$caminho")"
    CORPO="$(cat "$PASTA_TMP/corpo" 2>/dev/null)"
}

# esperar CODIGO DESCRICAO
esperar() {
    if [ "$ESTADO" = "$1" ]; then
        ok "$2 → $ESTADO"
    else
        falhou "$2 → esperado $1, veio $ESTADO  $CORPO"
    fi
}

tem_cabecalho() {
    grep -qi "^$1:" "$PASTA_TMP/cabecalhos"
}

valor_cabecalho() {
    grep -i "^$1:" "$PASTA_TMP/cabecalhos" | head -1 \
        | cut -d: -f2- | tr -d '\r' | sed 's/^ *//'
}

# Um pré check-in que passa em TODAS as regras do Pydantic. Recebe o
# token e o nome (para os grupos 3 e 4 trocarem só o que interessa).
pre_checkin_json() {
    local token="$1" nome="$2"
    printf '{"token":"%s","cliente":{"nome":"%s","nacionalidade":"Portuguesa","data_nascimento":"1990-01-01","tipo_documento":"Passaporte","numero_documento":"X1234567","pais_emissor_documento":"Portugal","pais_residencia":"Portugal"},"confirmacoes":{"informado_privacidade":true,"aceitou_regulamento":true,"consente_comunicacoes":false}}' \
        "$token" "$nome"
}

printf 'API atacada: %s\n' "$API"
printf 'Início: %s\n' "$(date '+%d/%m/%Y %H:%M:%S')"

# A API está viva? Se não, não vale a pena continuar.
pedir GET /api/saude
if [ "$ESTADO" != "200" ]; then
    printf '\nA API não responde em %s/api/saude (veio %s).\n' "$API" "$ESTADO"
    printf 'Confirma na VM: systemctl status hostel-api e tailscale funnel status\n'
    exit 99
fi

# ---------------------------------------------------------------------
titulo "1. Tokens inválidos — 404 e sempre a mesma mensagem"
# ---------------------------------------------------------------------
pedir POST /api/reserva "{\"token\":\"$TOKEN_FALSO\"}"
esperar 404 "Token inventado"
MENSAGEM_404="$CORPO"
printf '            mensagem: %s\n' "$MENSAGEM_404"

for caso in USADO EXPIRADO; do
    variavel="TOKEN_$caso"
    token="${!variavel}"
    if [ -z "$token" ]; then
        saltado "Token $caso (passa TOKEN_$caso=... para testar)"
        continue
    fi
    pedir POST /api/reserva "{\"token\":\"$token\"}"
    esperar 404 "Token $caso"
    if [ "$CORPO" = "$MENSAGEM_404" ]; then
        ok "Token $caso tem a MESMA mensagem do inventado"
    else
        falhou "Token $caso com mensagem diferente: $CORPO"
    fi
done

# ---------------------------------------------------------------------
titulo "2. CORS — outro site não consegue ler as respostas"
# ---------------------------------------------------------------------
pedir POST /api/reserva "{\"token\":\"$TOKEN_FALSO\"}" "$ORIGEM_ATACANTE"
if tem_cabecalho "access-control-allow-origin"; then
    falhou "Origem do atacante recebeu Access-Control-Allow-Origin: $(valor_cabecalho access-control-allow-origin)"
else
    ok "Pedido de $ORIGEM_ATACANTE sem Access-Control-Allow-Origin (o browser bloqueia)"
fi

# Pré-voo (OPTIONS) que o browser faz antes do POST: recusado. Não
# conta para o limitador (o CORS responde antes das rotas).
ARGS_PREVOO=(-s -o "$PASTA_TMP/corpo" -D "$PASTA_TMP/cabecalhos"
             -w '%{http_code}' --max-time 15 -X OPTIONS
             -H "Access-Control-Request-Method: POST"
             -H "Access-Control-Request-Headers: content-type")
ESTADO="$(curl "${ARGS_PREVOO[@]}" -H "Origin: $ORIGEM_ATACANTE" \
    "$API/api/pre-checkin")"
if [ "$ESTADO" = "400" ] && ! tem_cabecalho "access-control-allow-origin"; then
    ok "Pré-voo (OPTIONS) do atacante recusado → 400"
else
    falhou "Pré-voo do atacante → $ESTADO (esperado 400 sem Allow-Origin)"
fi

# Controlo: a origem verdadeira do site TEM de ser aceite — prova que
# o teste de cima não passou por o CORS estar simplesmente desligado.
ESTADO="$(curl "${ARGS_PREVOO[@]}" -H "Origin: $ORIGEM_SITE" \
    "$API/api/pre-checkin")"
if [ "$(valor_cabecalho access-control-allow-origin)" = "$ORIGEM_SITE" ]; then
    ok "Controlo: o site verdadeiro ($ORIGEM_SITE) é aceite"
else
    falhou "Controlo: o site verdadeiro não recebeu Allow-Origin (veio $ESTADO)"
fi

# ---------------------------------------------------------------------
titulo "3. Tamanhos — campos e corpo gigantes"
# ---------------------------------------------------------------------
NOME_GIGANTE="$(head -c 151 /dev/zero | tr '\0' 'A')"
pedir POST /api/pre-checkin "$(pre_checkin_json "$TOKEN_FALSO" "$NOME_GIGANTE")"
esperar 422 "Nome com 151 caracteres (coluna tem 150)"
if printf '%s' "$CORPO" | grep -q '"cliente.nome"'; then
    ok "A resposta diz QUAL campo falhou (cliente.nome)"
else
    falhou "A resposta não indica o campo: $CORPO"
fi
if printf '%s' "$CORPO" | grep -q "$NOME_GIGANTE"; then
    falhou "A resposta repete o valor enviado (dados pessoais!)"
else
    ok "A resposta NÃO repete o valor enviado"
fi

CORPO_GIGANTE="{\"token\":\"$(head -c 9000 /dev/zero | tr '\0' 'A')\"}"
pedir POST /api/reserva "$CORPO_GIGANTE"
esperar 413 "Corpo com ~9 KB (limite 8 KB)"

# ---------------------------------------------------------------------
titulo "4. Injeção de SQL"
# ---------------------------------------------------------------------
pedir POST /api/reserva "{\"token\":\"' OR '1'='1\"}"
esperar 422 "SQL no token (' OR '1'='1) — recusado pelo formato"

# Token com formato válido + SQL no nome: passa a validação e CHEGA à
# base. Se o texto fosse executado, a query partia (→ 503). 404 quer
# dizer que correu normalmente, com o texto como simples valor.
pedir POST /api/pre-checkin \
    "$(pre_checkin_json "$TOKEN_FALSO" "Robert'); DROP TABLE pendentes;--")"
esperar 404 "SQL no nome (DROP TABLE) — tratado como texto, não executado"

# ---------------------------------------------------------------------
titulo "5. Excesso de pedidos — o 11.º no mesmo minuto"
# ---------------------------------------------------------------------
printf '  (a esperar 61 s para o limitador começar do zero...)\n'
sleep 61

# Só contam os pedidos que tiveram RESPOSTA. Um "000" (a ligação
# falhou, ex.: o Funnel não respondeu em 15 s) quase sempre nem chegou
# à API — não entrou na conta do limitador — por isso repete-se.
# (Teste de 06/10/2026: o 7.º pedido deu 000 e só 10 chegaram à API;
# o limitador aceitou os 10, como devia, e o teste dava falso FALHOU.)
PRIMEIRO_429=0
RESPONDIDOS=0
SEM_RESPOSTA=0
TENTATIVA=0
while [ "$RESPONDIDOS" -lt 11 ] && [ "$TENTATIVA" -lt 16 ]; do
    TENTATIVA=$((TENTATIVA + 1))
    pedir POST /api/reserva "{\"token\":\"$TOKEN_FALSO\"}"
    if [ "$ESTADO" = "000" ]; then
        SEM_RESPOSTA=$((SEM_RESPOSTA + 1))
        printf '            tentativa %2d → 000 (sem resposta — não conta, repete)\n' \
            "$TENTATIVA"
        continue
    fi
    RESPONDIDOS=$((RESPONDIDOS + 1))
    printf '            pedido %2d → %s\n' "$RESPONDIDOS" "$ESTADO"
    if [ "$ESTADO" = "429" ] && [ "$PRIMEIRO_429" -eq 0 ]; then
        PRIMEIRO_429=$RESPONDIDOS
    fi
done
if [ "$PRIMEIRO_429" -eq 11 ]; then
    ok "Os 10 primeiros passam; o 11.º é bloqueado → 429"
elif [ "$PRIMEIRO_429" -eq 10 ] && [ "$SEM_RESPOSTA" -gt 0 ]; then
    # O pedido sem resposta chegou à API e contou — o limite está certo.
    ok "Bloqueado → 429 (o pedido sem resposta também contou na API)"
elif [ "$RESPONDIDOS" -lt 11 ]; then
    falhou "Só $RESPONDIDOS pedidos tiveram resposta — rede instável, repete"
elif [ "$PRIMEIRO_429" -eq 0 ]; then
    falhou "Nenhum pedido foi bloqueado"
else
    falhou "Bloqueado cedo demais, no pedido $PRIMEIRO_429 (esperado 11)"
fi

# ---------------------------------------------------------------------
titulo "6. Extras — o que não deve estar exposto"
# ---------------------------------------------------------------------
pedir GET /docs
esperar 404 "/docs (documentação automática) escondida"
pedir GET /openapi.json
esperar 404 "/openapi.json (mapa da API) escondido"
pedir GET /api/reserva
esperar 405 "GET em /api/reserva (só aceita POST)"

pedir GET /api/saude
if [ "$(valor_cabecalho cache-control)" = "no-store" ]; then
    ok "Cache-Control: no-store (nada fica guardado em caches)"
else
    falhou "Falta Cache-Control: no-store"
fi
if [ "$(valor_cabecalho x-content-type-options)" = "nosniff" ]; then
    ok "X-Content-Type-Options: nosniff"
else
    falhou "Falta X-Content-Type-Options: nosniff"
fi

# Portas da VM vistas do PC: só o SSH (22) pode responder.
porta_aberta() {
    timeout 5 bash -c "</dev/tcp/$IP_VM/$1" 2>/dev/null
}
for porta in 8000 6213; do
    if porta_aberta "$porta"; then
        falhou "Porta $porta da VM ($IP_VM) responde de fora"
    else
        ok "Porta $porta da VM ($IP_VM) fechada por fora"
    fi
done
if porta_aberta 22; then
    printf '  [INFO]    Porta 22 (SSH) responde — esperado: só entra com chave\n'
else
    printf '  [INFO]    Porta 22 não responde — o IP_VM está certo? (%s)\n' "$IP_VM"
fi

# ---------------------------------------------------------------------
printf '\n=== RESUMO ===\n'
printf '  OK: %d   FALHOU: %d   SALTADO: %d\n' "$OK" "$FALHAS" "$SALTADOS"
printf 'Fim: %s\n' "$(date '+%d/%m/%Y %H:%M:%S')"
exit "$FALHAS"
