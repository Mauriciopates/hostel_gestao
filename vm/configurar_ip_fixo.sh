#!/usr/bin/env bash
# =====================================================================
# configurar_ip_fixo.sh — IP fixo na placa Host-Only da VM (Hostel
# Gestão). Padrão do manual: 192.168.56.11 na enp0s8.
#
# USO (na VM):   sudo bash configurar_ip_fixo.sh [IP]
#                ex.: sudo bash configurar_ip_fixo.sh 192.168.56.11
#
# ATENÇÃO: se estiver ligado por SSH ao IP antigo, a ligação cai no
# fim (é normal). Voltar a entrar com: ssh <utilizador>@<IP novo>
# =====================================================================
set -euo pipefail

readonly IP="${1:-192.168.56.11}"
readonly PLACA_NAT="enp0s3"
readonly PLACA_HOST="enp0s8"
readonly FICHEIRO="/etc/netplan/50-cloud-init.yaml"

[[ ${EUID} -eq 0 ]] || { echo "Correr com: sudo bash $0" >&2; exit 1; }
[[ "${IP}" =~ ^192\.168\.56\.[0-9]{1,3}$ ]] \
    || { echo "IP inválido (esperado 192.168.56.x): ${IP}" >&2; exit 1; }
ip link show "${PLACA_HOST}" >/dev/null 2>&1 \
    || { echo "Placa ${PLACA_HOST} não existe (Adaptador 2?)" >&2; exit 1; }

# 1. O cloud-init deixa de reescrever a rede em cada arranque.
echo "network: {config: disabled}" \
    > /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg

# 2. Cópia de segurança dos ficheiros atuais (uma só vez).
mkdir -p /root/netplan-backup
cp -n /etc/netplan/*.yaml /root/netplan-backup/ 2>/dev/null || true

# 3. Um só ficheiro de rede: os outros saem do caminho (ficam no backup).
for f in /etc/netplan/*.yaml; do
    [[ "${f}" == "${FICHEIRO}" ]] || mv "${f}" "/root/netplan-backup/"
done

cat > "${FICHEIRO}" <<EOT
# Gerado por configurar_ip_fixo.sh
network:
  version: 2
  renderer: networkd
  ethernets:
    ${PLACA_NAT}:
      dhcp4: true
    ${PLACA_HOST}:
      dhcp4: false
      addresses:
        - ${IP}/24
EOT
chmod 600 "${FICHEIRO}"
netplan generate

echo "IP fixo ${IP} configurado em ${PLACA_HOST}. A aplicar..."
echo "(se estiver por SSH, a ligação cai agora: ssh ...@${IP})"
netplan apply
ip -br a
