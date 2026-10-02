#!/usr/bin/env bash
# =====================================================================
# montar_pacote.sh — Pacote de entrega do Hostel Gestão (decisão D14)
#
# Monta C:\HostelGestao_instalacao\ e o .zip em dist/ (o Windows não
# deixa um utilizador normal criar FICHEIROS na raiz do C:, só pastas):
#   HostelGestao\   <- dist/HostelGestao (HostelGestao.exe + _internal)
#   vm\             <- vm/instalar_vm.sh + vm/configurar_ip_fixo.sh
#   docs\           <- manuais (docs/4_manual)
#   LEIA-ME.txt
#
# USO (Git Bash, na RAIZ do repositório, DEPOIS do build):
#   pyinstaller HostelGestao.spec --clean --noconfirm
#   bash montar_pacote.sh
#
# Pode correr-se as vezes que for preciso: apaga e refaz a pasta e o
# .zip. Nunca mexe no repositório.
# =====================================================================
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
DESTINO="/c/HostelGestao_instalacao"
TAR_WINDOWS="/c/Windows/System32/tar.exe"   # o tar do Git Bash não faz .zip

passo() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
erro()  { printf '\033[1;31mERRO: %s\033[0m\n' "$*" >&2; exit 1; }

# --- 1. Verificações -------------------------------------------------
passo "1/4 Verificações"
VERSAO="$(sed -n 's/^VERSAO = "\(.*\)"/\1/p' "$RAIZ/src/config.py")"
[ -n "$VERSAO" ] || erro "não encontrei VERSAO em src/config.py"
ZIP_NOME="HostelGestao_instalacao_v${VERSAO}.zip"
ZIP="$RAIZ/dist/$ZIP_NOME"
EXE="$RAIZ/dist/HostelGestao/HostelGestao.exe"

[ -f "$EXE" ] || erro "falta $EXE — correr primeiro: pyinstaller HostelGestao.spec --clean --noconfirm"
[ -d "$RAIZ/dist/HostelGestao/_internal" ] || erro "falta a pasta _internal ao lado do .exe"
for f in instalar_vm.sh configurar_ip_fixo.sh; do
    [ -f "$RAIZ/vm/$f" ] || erro "falta vm/$f"
    # Com CRLF o bash da VM falha ("$'\r': command not found").
    if grep -q $'\r' "$RAIZ/vm/$f"; then
        erro "vm/$f tem fins de linha Windows (CRLF) — tem de ser LF"
    fi
done
[ -x "$TAR_WINDOWS" ] || erro "não encontrei $TAR_WINDOWS (Windows 10 1803 ou mais recente)"

shopt -s nullglob
MANUAIS=("$RAIZ"/docs/4_manual/Manual_Instalacao_*.docx)
shopt -u nullglob
[ ${#MANUAIS[@]} -gt 0 ] || erro "não há manuais em docs/4_manual/Manual_Instalacao_*.docx"

# Aviso (não trava): código mais recente do que o executável.
if [ -n "$(find "$RAIZ/src" -name '*.py' -newer "$EXE" -print -quit)" ]; then
    printf '\033[1;33mAVISO: há ficheiros em src/ mais recentes do que o .exe — o build pode estar desatualizado.\033[0m\n'
fi
echo "    Versão: $VERSAO"

# --- 2. Pasta ----------------------------------------------------------
passo "2/4 A montar $DESTINO"
rm -rf "$DESTINO" "$ZIP"
mkdir -p "$DESTINO/vm" "$DESTINO/docs"
cp -r "$RAIZ/dist/HostelGestao" "$DESTINO/HostelGestao"
cp "$RAIZ/vm/instalar_vm.sh" "$RAIZ/vm/configurar_ip_fixo.sh" "$DESTINO/vm/"
cp "${MANUAIS[@]}" "$DESTINO/docs/"

# --- 3. LEIA-ME (CRLF: é para abrir no Bloco de Notas) ----------------
passo "3/4 LEIA-ME.txt"
{
    printf 'HOSTEL GESTAO - pacote de instalacao v%s\r\n' "$VERSAO"
    printf '\r\n'
    printf 'HostelGestao\\  aplicacao. Abrir HostelGestao\\HostelGestao.exe.\r\n'
    printf '                Nunca tirar o .exe da pasta (precisa do _internal).\r\n'
    printf 'vm\\            scripts do servidor de base de dados (Ubuntu).\r\n'
    printf '                Nao abrir nem gravar no Bloco de Notas.\r\n'
    printf 'docs\\          manuais:\r\n'
    printf '  1. Manual_Instalacao_VM       - servidor de base de dados\r\n'
    printf '  2. Manual_Instalacao_Sistema  - aplicacao e funcionalidades\r\n'
    printf '\r\n'
    printf 'Esta pasta tem de ficar em C:\\HostelGestao_instalacao\r\n'
} > "$DESTINO/LEIA-ME.txt"

# --- 4. ZIP ------------------------------------------------------------
passo "4/4 A criar dist/$ZIP_NOME"
# O tar.exe do Windows não entende caminhos /c/...: cygpath -w converte.
( cd /c && "$TAR_WINDOWS" -a -c -f "$(cygpath -w "$ZIP")" HostelGestao_instalacao )

printf '\n\033[1;32mPacote pronto.\033[0m\n'
du -sh "$DESTINO" "$ZIP" | sed 's/^/    /'
find "$DESTINO" -maxdepth 2 -not -path "*/_internal*" | sed "s|^|    |"
