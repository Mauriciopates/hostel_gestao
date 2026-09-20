"""Cria um Master inicial na base de dados.

Script de arranque, para correr UMA VEZ, na primeira configuração
de uma base de dados vazia (ou quase). Sem ele, não há como fazer
login no sistema — o `LoginModal` recusa qualquer tentativa porque
nenhum responsável tem credencial.

O que faz:

  1. Verifica se já existe algum responsável com credencial Master
     ativa. Se sim, não faz nada — é idempotente.
  2. Se não existir, cria um novo responsável com perfil Master.
  3. Define-lhe a credencial (username + password).
  4. Imprime as credenciais no terminal.

Como correr:

    cd <pasta do projeto>
    python src/bootstrap.py

Depois de ver as credenciais, entra na GUI com essas credenciais.

IMPORTANTE: este script NÃO é chamado pelo `main_gui.py` — é
manual, e é suposto só correr uma vez. Se correres duas vezes
seguidas, a segunda não faz nada (idempotente).
"""

import sys
from pathlib import Path

# Garante que o `src/` está no `sys.path`, para os imports
# funcionarem mesmo correndo o script de sítios diferentes.
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import configuracoes
import repositorio
import responsaveis
import utilizadores

# =====================================================================
# CREDENCIAIS DO MASTER INICIAL
# =====================================================================
#
# Estas são as credenciais que o script vai criar. Podes mudá-las
# aqui antes de correr, se quiseres.

NOME = "Admin"
USERNAME = "admin"
PASSWORD = "adm12345678"


def main():
    """Cria o Master inicial, se ainda não existir nenhum."""
    print("=== Bootstrap — Master inicial ===\n")

    import config

    config.garantir_diretorios()

    # Verificar se já existe Master COM credencial
    if _ja_existe_master_com_credencial():
        print(
            "Já existe pelo menos um Master com credencial definida. "
            "Nada a fazer."
        )
        return

    # Procurar um Master SEM credencial (caso o bootstrap tenha
    # falhado a meio numa execução anterior)
    master_existente = _procurar_master_sem_credencial()

    if master_existente is not None:
        print(
            f"Encontrado Master sem credencial: "
            f"{master_existente['id']} — {master_existente['nome']}"
        )
        print("A atribuir-lhe credencial...\n")
        master = master_existente
    else:
        print("Nenhum Master encontrado.")
        print("A criar um novo...\n")

        master = responsaveis.criar(
            nome=NOME,
            contacto="",
            tipo_utilizador="Master",
            autor=None,
        )

        print(f"✓ Responsável criado: {master['id']} — {master['nome']}")

    # Definir credencial diretamente na BD
    _definir_credencial_direto(master["id"])

    print(f"✓ Credencial definida: {USERNAME}")

    criadas = configuracoes.garantir_seed()

    if criadas:
        print(f"✓ Seed de configurações: {criadas} chaves criadas")
    else:
        print("✓ Seed de configurações: já estava tudo")

    print("\n=== Pronto ===")
    print("Credenciais:")
    print(f"    Utilizador: {USERNAME}")
    print(f"    Password:   {PASSWORD}")


def _procurar_master_sem_credencial():
    """Devolve o primeiro Master ativo SEM credencial, ou None."""
    for r in responsaveis.listar():
        if r["tipo_utilizador"] != "Master":
            continue

        if r.get("username"):
            continue

        return r

    return None


def _definir_credencial_direto(responsavel_id):
    """Define a credencial por escrita direta na BD.

    Não usa `utilizadores.definir_credencial` porque essa função
    exige um autor ativo — e neste momento ainda não há nenhum.
    """
    import hashlib
    import os
    from datetime import datetime

    from repositorio import atualizar_responsavel

    ITERACOES = 100000
    salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", PASSWORD.encode("utf-8"), salt, ITERACOES
    )
    password_hash = (
        f"pbkdf2_sha256${ITERACOES}$" f"{salt.hex()}${hash_bytes.hex()}"
    )

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    atualizar_responsavel(
        responsavel_id,
        {
            "username": USERNAME,
            "password_hash": password_hash,
            "password_alterada_em": agora,
        },
    )


def _ja_existe_master_com_credencial():
    """Devolve True se já existir algum Master ativo com credencial.

    Percorre os responsáveis ativos e devolve True no primeiro que
    seja Master e tenha `username` preenchido.
    """
    for r in responsaveis.listar():
        if r["tipo_utilizador"] != "Master":
            continue

        if not r.get("username"):
            continue

        return True

    return False


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        sys.exit(1)
