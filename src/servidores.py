"""Servidores de base de dados — lista, credenciais e túnel SSH.

Versão "para cliente" (26/09/2026): tudo se gere no ecrã de
Configurações → Sistema → "Servidor da base de dados". Ninguém precisa
de abrir ficheiros para instalar, mudar ou acrescentar um servidor.

ONDE FICA CADA COISA
- Lista de servidores e qual está ativo: um ficheiro JSON na pasta de
  dados da aplicação do Windows, %APPDATA%\\HostelGestao\\servidores.json.
  Fora da pasta do programa e fora do Git. Não tem passwords.
- Passwords: no Gestor de Credenciais do Windows (o "cofre" do sistema,
  o mesmo que o MySQL Workbench usa no "Store in Vault"), através da
  biblioteca `keyring`. Nunca ficam em texto simples no disco.

PORQUE NÃO NA BASE DE DADOS: para ler uma tabela é preciso já estar
ligado a um servidor. A escolha do servidor tem de existir antes da
ligação, por isso vive num ficheiro local.

PRIMEIRO ARRANQUE: se o JSON ainda não existir, importa os ficheiros
.env (MySQL do Windows) e VM.env (VM pelo túnel) da raiz do projeto,
se existirem — passwords incluídas, que passam para o cofre. Se não
houver nada, a lista fica vazia e o main_gui mostra o formulário de
primeira configuração.

TÚNEL SSH: para servidores que só aceitam ligações "por dentro" (a VM),
a aplicação lança em segundo plano o mesmo comando que se escrevia à mão,
    ssh -N -L <porta_local>:127.0.0.1:<porta_mysql> utilizador@maquina
e fecha-o ao terminar. Usa a chave SSH do PC, sem password
(BatchMode=yes: se a chave falhar, desiste em vez de ficar à espera).

Este módulo NÃO importa o `config` — é o `config` que o importa a ele.
"""

import atexit
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import instancia

logger = logging.getLogger(__name__)

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_DADOS = Path(os.environ.get("APPDATA") or Path.home()) / "HostelGestao"
FICHEIRO_SERVIDORES = PASTA_DADOS / "servidores.json"

# Nome com que as passwords ficam no Gestor de Credenciais do Windows.
SERVICO_COFRE = "HostelGestao"

# Força um servidor só para um arranque, sem mudar o ativo.
# Ex. Git Bash:  HOSTEL_SERVIDOR=vm python src/main_gui.py
VARIAVEL_FORCAR = "HOSTEL_SERVIDOR"

PORTA_LOCAL_INICIAL = 3307   # primeira porta do PC usada para túneis
_ESPERA_TUNEL = 10           # segundos até desistir de um túnel

_tuneis = {}                 # porta_local -> processo ssh aberto por nós


class ErroServidor(Exception):
    """Falha ao preparar a ligação a um servidor (túnel ou MySQL)."""


# =====================================================================
# FICHEIRO DA LISTA
# =====================================================================


def carregar():
    """Lê a lista. Na primeira vez, cria-a (importando os .env)."""
    if not FICHEIRO_SERVIDORES.is_file():
        dados = _importar_ficheiros_env()
        _gravar(dados)
        return dados
    with open(FICHEIRO_SERVIDORES, encoding="utf-8") as f:
        return json.load(f)


def _gravar(dados):
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    with open(FICHEIRO_SERVIDORES, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def listar():
    """[(id, servidor), ...] pela ordem em que foram criados."""
    return list(carregar()["servidores"].items())


def obter(id_servidor):
    return carregar()["servidores"].get(id_servidor)


def servidor_ativo():
    """(id, servidor) a usar neste arranque, ou (None, None) se a lista
    estiver vazia (primeira instalação)."""
    dados = carregar()
    id_servidor = os.environ.get(VARIAVEL_FORCAR) or dados.get("ativo")
    if id_servidor not in dados["servidores"]:
        id_servidor = next(iter(dados["servidores"]), None)
    if id_servidor is None:
        return None, None
    return id_servidor, dados["servidores"][id_servidor]


def definir_ativo(id_servidor):
    """Grava o servidor ativo. Só faz efeito no próximo arranque."""
    dados = carregar()
    if id_servidor not in dados["servidores"]:
        raise ErroServidor(f"Servidor '{id_servidor}' não existe.")
    dados["ativo"] = id_servidor
    _gravar(dados)
    logger.info("Servidor ativo passou a ser '%s'", id_servidor)


def guardar(id_servidor, servidor, password=None):
    """Cria (id_servidor=None) ou atualiza um servidor.

    `servidor` é o dicionário do formulário (sem password). A password
    vai para o cofre; None mantém a que lá estiver. Devolve o id.
    """
    dados = carregar()
    if id_servidor is None:
        id_servidor = _novo_id(servidor["nome"], dados["servidores"])

    servidor = dict(servidor)
    if servidor.get("tunel"):
        tunel = dict(servidor["tunel"])
        tunel["porta_local"] = _porta_local_livre(
            dados["servidores"], id_servidor
        )
        servidor["tunel"] = tunel

    dados["servidores"][id_servidor] = servidor
    if not dados.get("ativo"):
        dados["ativo"] = id_servidor
    _gravar(dados)

    if password is not None:
        _guardar_password(id_servidor, password)
    logger.info("Servidor '%s' gravado", id_servidor)
    return id_servidor


def remover(id_servidor):
    """Remove um servidor da lista (e a password do cofre).

    Só recusa o servidor EM USO NESTE ARRANQUE — que pode não ser o
    gravado como ativo, quando se arranca com HOSTEL_SERVIDOR=... (é
    assim que se sai de um servidor sem utilizadores). Se o removido
    era o gravado como ativo, o ativo passa a ser o que está em uso.
    """
    dados = carregar()
    em_uso, _ = servidor_ativo()
    if id_servidor == em_uso:
        raise ErroServidor("Não se pode remover o servidor que está em uso.")
    dados["servidores"].pop(id_servidor, None)
    if dados.get("ativo") == id_servidor:
        dados["ativo"] = em_uso
    _gravar(dados)
    try:
        _cofre().delete_password(SERVICO_COFRE, _chave_cofre(id_servidor))
    except Exception:  # já não existia — nada a apagar
        pass
    logger.info("Servidor '%s' removido", id_servidor)


def _novo_id(nome, existentes):
    """'VM (VirtualBox)' -> 'vm-virtualbox', sem repetir."""
    base = (
        unicodedata.normalize("NFKD", nome)
        .encode("ascii", "ignore")
        .decode()
    )
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "servidor"
    candidato, n = base, 2
    while candidato in existentes:
        candidato, n = f"{base}-{n}", n + 1
    return candidato


def _porta_local_livre(servidores_existentes, id_servidor):
    """Cada servidor com túnel recebe a sua porta no PC (3307, 3308…),
    para dois túneis nunca se confundirem."""
    usadas = {
        s["tunel"]["porta_local"]
        for i, s in servidores_existentes.items()
        if i != id_servidor and s.get("tunel")
    }
    porta = PORTA_LOCAL_INICIAL
    while porta in usadas:
        porta += 1
    return porta


# =====================================================================
# PASSWORDS NO COFRE DO WINDOWS
# =====================================================================


def _cofre():
    try:
        import keyring
    except ImportError as erro:
        raise ErroServidor(
            "Falta a biblioteca 'keyring'. Instale com: pip install keyring"
        ) from erro
    return keyring


def _chave_cofre(id_servidor):
    return f"servidor:{id_servidor}"


def _guardar_password(id_servidor, password):
    _cofre().set_password(SERVICO_COFRE, _chave_cofre(id_servidor), password)


def obter_password(id_servidor):
    try:
        chave = _chave_cofre(id_servidor)
        return _cofre().get_password(SERVICO_COFRE, chave) or ""
    except ErroServidor:
        raise
    except Exception as erro:
        logger.error("Não consegui ler a password do cofre: %s", erro)
        return ""


# =====================================================================
# CREDENCIAIS PARA O MYSQL
# =====================================================================


def credenciais(servidor, password):
    """Parâmetros de ligação ao MySQL. Com túnel, o MySQL é alcançado
    pela ponta do túnel no próprio PC (127.0.0.1:porta_local)."""
    if servidor.get("tunel"):
        host, porta = "127.0.0.1", servidor["tunel"]["porta_local"]
    else:
        host, porta = servidor["host"], int(servidor["porta"])
    return {
        "host": host,
        "port": porta,
        "user": servidor["utilizador"],
        "password": password,
        "database": servidor["base"],
    }


def descrever(servidor):
    """Texto curto para o ecrã: por onde passa a ligação."""
    tunel = servidor.get("tunel")
    if tunel:
        return (
            f"Túnel SSH {tunel['ssh_utilizador']}@{tunel['ssh_host']} · "
            f"MySQL na porta {tunel['porta_mysql']} dessa máquina · "
            f"base {servidor['base']}"
        )
    return (
        f"Ligação direta a {servidor['host']}:{servidor['porta']} · "
        f"base {servidor['base']}"
    )


# =====================================================================
# TÚNEL SSH
# =====================================================================


def porta_aberta(porta, host="127.0.0.1", espera=1.0):
    try:
        with socket.create_connection((host, porta), timeout=espera):
            return True
    except OSError:
        return False


def _programa_ssh():
    encontrado = shutil.which("ssh")
    if encontrado:
        return encontrado
    windows = Path(r"C:\Windows\System32\OpenSSH\ssh.exe")
    if windows.is_file():
        return str(windows)
    raise ErroServidor(
        "Não encontrei o programa 'ssh' neste computador. Instale o "
        "'Cliente OpenSSH' nas Funcionalidades opcionais do Windows."
    )


def abrir_tunel(servidor):
    """Garante que o túnel do servidor está aberto (se ele usar túnel).

    Reaproveita um túnel já aberto nessa porta. Lança ErroServidor com
    uma explicação em linguagem simples se falhar.
    """
    tunel = servidor.get("tunel")
    if not tunel:
        return

    porta = tunel["porta_local"]
    if porta_aberta(porta):
        return

    comando = [
        _programa_ssh(),
        "-N",
        "-o", "BatchMode=yes",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ConnectTimeout=5",
        "-o", "ServerAliveInterval=30",
        # Aceita sozinho uma máquina nova; recusa se a de sempre mudar.
        "-o", "StrictHostKeyChecking=accept-new",
        "-p", str(tunel.get("ssh_porta", 22)),
        "-L", f"{porta}:127.0.0.1:{tunel['porta_mysql']}",
        f"{tunel['ssh_utilizador']}@{tunel['ssh_host']}",
    ]
    opcoes = {}
    if os.name == "nt":
        # Sem janela preta de consola.
        opcoes["creationflags"] = subprocess.CREATE_NO_WINDOW

    logger.info("A abrir túnel SSH: %s", " ".join(comando[1:]))
    processo = subprocess.Popen(
        comando,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        **opcoes,
    )
    _tuneis[porta] = processo

    limite = time.monotonic() + _ESPERA_TUNEL
    while time.monotonic() < limite:
        if porta_aberta(porta, espera=0.5):
            logger.info("Túnel aberto na porta %s", porta)
            return
        if processo.poll() is not None:
            saida = processo.stderr.read() if processo.stderr else b""
            erro = saida.decode(errors="replace").strip()
            _tuneis.pop(porta, None)
            raise ErroServidor(_explicar_erro_ssh(erro, tunel))
        time.sleep(0.3)

    fechar_tuneis()
    raise ErroServidor(
        f"O túnel para {tunel['ssh_host']} não abriu em {_ESPERA_TUNEL} "
        "segundos. A máquina está ligada?"
    )


def _explicar_erro_ssh(erro, tunel):
    texto = erro.lower()
    if "timed out" in texto or "no route" in texto or "unreachable" in texto:
        causa = f"A máquina {tunel['ssh_host']} não respondeu. Está ligada?"
    elif "permission denied" in texto:
        causa = (
            "A máquina recusou a chave SSH deste PC. A chave pública "
            "(~/.ssh/id_ed25519.pub) tem de estar no authorized_keys de "
            f"{tunel['ssh_utilizador']}."
        )
    elif "host key" in texto and "changed" in texto:
        causa = (
            "A identidade da máquina mudou desde a última ligação. Por "
            "segurança a ligação foi recusada."
        )
    elif "address already in use" in texto:
        causa = (
            f"A porta {tunel['porta_local']} do PC está ocupada por "
            "outro programa."
        )
    else:
        causa = "O túnel SSH não abriu."
    return f"{causa}\n\nMensagem do ssh: {erro or '(nenhuma)'}"


def fechar_tuneis():
    """Fecha os túneis que esta aplicação abriu."""
    for porta, processo in list(_tuneis.items()):
        if processo.poll() is None:
            processo.terminate()
            try:
                processo.wait(timeout=3)
            except subprocess.TimeoutExpired:
                processo.kill()
            logger.info("Túnel na porta %s fechado", porta)
    _tuneis.clear()


atexit.register(fechar_tuneis)


# =====================================================================
# TESTAR E REINICIAR
# =====================================================================


def testar(servidor, password):
    """Tenta ligar ao MySQL. Devolve (True, texto) ou (False, explicação).

    Recebe o dicionário e a password em vez do id, para o formulário
    poder testar um servidor antes de o gravar.
    """
    import mysql.connector

    try:
        abrir_tunel(servidor)
        # use_pure=True (v1.8.0): o conector em Python puro traz os plugins
        # de autenticação (mysql_native_password, caching_sha2_password)
        # no próprio código. A extensão em C procura-os em DLLs que o
        # PyInstaller não copia — no .exe dava o erro 2059 "Authentication
        # plugin 'mysql_native_password' cannot be loaded" (ligação à VM).
        conexao = mysql.connector.connect(
            **credenciais(servidor, password),
            connection_timeout=5,
            use_pure=True,
        )
        try:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE()"
            )
            tabelas = len(cursor.fetchall())
        finally:
            conexao.close()
    except ErroServidor as erro:
        return False, str(erro)
    except mysql.connector.Error as erro:
        return False, f"O MySQL recusou a ligação.\n\n{erro}"

    return True, (
        f"Ligação a '{servidor['base']}' com sucesso — {tabelas} tabelas."
    )


def testar_id(id_servidor):
    return testar(obter(id_servidor), obter_password(id_servidor))


def reiniciar_aplicacao():
    """Lança uma cópia nova da aplicação; quem chama fecha a atual.

    Os túneis desta fecham-se ANTES: se ficassem abertos, a nova
    reaproveitava-os e perdia-os logo a seguir, quando esta terminasse.

    No executável (PyInstaller) o `sys.executable` já É o programa e
    o `sys.argv[0]` também — repetir o argv[0] passava o próprio .exe
    como argumento. A correr do código, `sys.executable` é o python e
    o `sys.argv[0]` o script (src/main_gui.py), que é preciso passar.
    """
    fechar_tuneis()
    ambiente = {k: v for k, v in os.environ.items() if k != VARIAVEL_FORCAR}
    # Cópia única (v1.8.1): esta cópia larga o trinco e a nova, avisada
    # pela variável, espera por ele em vez de se recusar.
    instancia.libertar()
    ambiente[instancia.VARIAVEL_REINICIO] = "1"
    if getattr(sys, "frozen", False):
        comando = [sys.executable] + sys.argv[1:]
    else:
        comando = [sys.executable] + sys.argv
    subprocess.Popen(comando, env=ambiente, cwd=os.getcwd())


# =====================================================================
# IMPORTAÇÃO DOS .env (só no primeiro arranque)
# =====================================================================


def _importar_ficheiros_env():
    """Converte os .env da raiz do projeto em servidores da lista.

    - .env    -> "Local (Windows)", ligação direta.
    - VM.env  -> "VM (VirtualBox)", pelo túnel SSH para a VM db-server
                 (valores da montagem feita a 26/09/2026, ficheiro 12).
    As passwords passam para o cofre. Os .env não são apagados.
    """
    # Sem o cofre, as passwords não tinham onde ficar: melhor parar já
    # (com a instrução de instalação) do que criar a lista sem elas.
    _cofre()

    dados = {"ativo": None, "servidores": {}}
    try:
        from dotenv import dotenv_values
    except ImportError:
        return dados

    ficheiro = RAIZ_PROJETO / ".env"
    if ficheiro.is_file():
        v = dotenv_values(ficheiro)
        dados["servidores"]["local"] = {
            "nome": "Local (Windows)",
            "host": v.get("DB_HOST", "localhost"),
            "porta": int(v.get("DB_PORT") or "3306"),
            "utilizador": v.get("DB_USER", "root"),
            "base": v.get("DB_NAME", "hostel_gestao"),
            "tunel": None,
        }
        _importar_password("local", v.get("DB_PASSWORD", ""))
        dados["ativo"] = "local"

    ficheiro = RAIZ_PROJETO / "VM.env"
    if ficheiro.is_file():
        v = dotenv_values(ficheiro)
        dados["servidores"]["vm"] = {
            "nome": "VM (VirtualBox)",
            "host": "",
            "porta": 3306,
            "utilizador": v.get("DB_USER", "root"),
            "base": v.get("DB_NAME", "hostel_gestao"),
            "tunel": {
                "ssh_utilizador": "db-server",
                "ssh_host": "192.168.56.10",
                "ssh_porta": 22,
                "porta_mysql": 6213,
                "porta_local": int(v.get("DB_PORT") or "3307"),
            },
        }
        _importar_password("vm", v.get("DB_PASSWORD", ""))
        dados["ativo"] = dados["ativo"] or "vm"

    if dados["servidores"]:
        logger.info("Servidores importados dos ficheiros .env: %s",
                    ", ".join(dados["servidores"]))
    return dados


def _importar_password(id_servidor, password):
    try:
        _guardar_password(id_servidor, password)
    except Exception as erro:
        logger.error("Não consegui guardar a password de '%s' no cofre: %s",
                     id_servidor, erro)
