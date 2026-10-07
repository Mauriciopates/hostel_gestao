"""Valores de configuração do sistema.

Contém os valores por omissão definidos na análise. Na Fase 1 são constantes
do módulo; a leitura passa a fazer-se pelo repositório quando este existir,
mantendo estes valores como estado inicial.

Montantes em Decimal (decisão 4). Datas de época alta guardadas como
(mes, dia) para serem independentes do ano.
"""

import sys
from pathlib import Path

from decimal import Decimal

# --- Servidor da base de dados (26/09/2026) ----------------------------------
# O servidor (Local, VM, ...) escolhe-se em Configurações → Sistema →
# "Servidor da base de dados". A lista fica em %APPDATA%\HostelGestao e as
# passwords no Gestor de Credenciais do Windows — nunca aqui nem num .env.
# Ver src/servidores.py.
import servidores  # noqa: E402

SERVIDOR_ID, SERVIDOR = servidores.servidor_ativo()
RAIZ_PROJETO = servidores.RAIZ_PROJETO

# --- Ligação à base de dados MySQL -----------------------------------------
if SERVIDOR is not None:
    SERVIDOR_NOME = SERVIDOR["nome"]
    _credenciais = servidores.credenciais(
        SERVIDOR, servidores.obter_password(SERVIDOR_ID)
    )
else:
    # Primeira instalação, ainda sem servidor: o main_gui mostra o
    # formulário antes de qualquer acesso à base.
    SERVIDOR_NOME = "Sem servidor"
    _credenciais = {"host": "localhost", "port": 3306, "user": "root",
                    "password": "", "database": "hostel_gestao"}

DB_HOST = _credenciais["host"]
DB_PORT = int(_credenciais["port"])
DB_USER = _credenciais["user"]
DB_PASSWORD = _credenciais["password"]
DB_NAME = _credenciais["database"]

# --- Pré check-in dos hóspedes (F5, 05/10/2026) ----------------------------
# Caixa de entrada que a API escreve (base separada, no MESMO servidor e
# com o MESMO utilizador `hostel_app`). Ver o ficheiro 08 do projeto.
DB_NAME_PRECHECKING = "hostel_prechecking"
# Página pública do site (GitHub Pages). O link do hóspede é este
# endereço com "?t=<token>" no fim.
URL_SITE_PRECHECKING = (
    "https://mauriciopates.github.io/site_checking_hostel_gestao/"
)

# --- Preços ---------------------------------------------------------------
PRECO_BASE_MENSAL = Decimal("250.00")  # por pessoa, por mês
PRECO_BASE_AIRBNB = Decimal("45.00")  # por noite
PRECO_EPOCA_ALTA = Decimal("90.00")  # por noite

# Época alta nunca é automática: exige indicador manual ativo na unidade
# E data dentro deste período (decisão da análise).
EPOCA_ALTA_INICIO = (7, 1)  # 1 de julho
EPOCA_ALTA_FIM = (9, 30)  # 30 de setembro

# --- Caução ---------------------------------------------------------------
# Multiplicadores, não montantes: a caução calcula-se a partir da renda
# praticada, dispensando manutenção quando as rendas mudam (decisão 14).
MULTIPLICADOR_CAUCAO = Decimal("1")  # sugerido
MULTIPLICADOR_MAXIMO_CAUCAO = Decimal("2")  # teto aceite; regra da casa

# --- Penalizações e juros -------------------------------------------------
MULTA_CHECK_IN_TARDIO = Decimal("20.00")  # sobreponível por unidade
JUROS_ATRASO = Decimal("0.10")

# --- Regime mensal ----------------------------------------------------------
DIA_VENCIMENTO = 5
AVISO_PREVIO_DIAS = 15
DURACAO_MINIMA_MESES = 3

# --- Regime Airbnb ----------------------------------------------------------
ESTADIA_MINIMA_NOITES = 1
ESTADIA_MAXIMA_NOITES = 28

# --- Horários ---------------------------------------------------------------
HORA_CHECK_IN = "15:00"
HORA_CHECK_OUT = "11:00"
HORA_LIMITE_CHECK_IN_TARDIO = "17:00"

# --- Cópias de segurança -----------------------------------------------------
DIAS_BACKUP = 30

# --- Conservação de dados (RGPD) --------------------------------------------
PRAZO_CONSERVACAO_HOSPEDES_DIAS = 365  # boletins SIBA/AIMA
PRAZO_CONSERVACAO_FISCAL_DIAS = 3650  # art.º 40.º Código Comercial
PRAZO_CONSERVACAO_LOGS_DIAS = 180  # minimização

# Mostrada na interface (decisão 21); atualizar a cada fecho de versão.
VERSAO = "1.11.1"

# --- Utilizador Master padrão (reset do sistema) ----------------------------
# Usados pela função "Começar do zero" (gui_configuracoes.py → Fase 4).
# Depois de um reset, o sistema fica só com este utilizador.
# A password fica em texto na primeira gravação, mas é logo convertida
# para hash pelo `utilizadores.definir_credencial` — nunca é guardada
# em claro na base de dados.
NOME_MASTER_PADRAO = "Admin"
UTILIZADOR_PADRAO = "admin"
PASSWORD_PADRAO = "adm12345678"

# --- Bloqueio do login por tentativas falhadas (v1.8.0) -------------
# 3 falhas seguidas bloqueiam 30 s; cada falha a seguir dobra a espera
# (60, 120, 240 s...) até ao máximo de 5 min. Um login certo limpa a
# contagem. Regra em `utilizadores.duracao_bloqueio`.
LOGIN_FALHAS_ANTES_BLOQUEIO = 3
LOGIN_BLOQUEIO_INICIAL_S = 30
LOGIN_BLOQUEIO_MAXIMO_S = 300

# --- Diretoria base de dados persistentes (Fase 1, v1.4.0) ------------------
# Fica FORA da pasta de instalação/repositório: evita erros de permissão
# de escrita quando o sistema corre como executável PyInstaller (nunca se
# escreve em sys._MEIPASS — a pasta temporária onde o PyInstaller
# descompacta o executável, apagada ao fechar o programa).
if sys.platform == "win32":
    DIR_BASE = Path("C:\\Hostel_gestao")
else:
    DIR_BASE = Path.home() / "Hostel_gestao"

DIR_DADOS = DIR_BASE / "dados"
DIR_BACKUPS = DIR_BASE / "backups"
DIR_CONTRATOS = DIR_BASE / "contratos"
DIR_RELATORIOS = DIR_BASE / "relatorios"
DIR_LOGS = DIR_BASE / "logs"

# --- Esquema oficial da base de dados (v1.8.0, INST-03) --------------
# Fonte única do esquema (decisão D7), dentro do `src/` para ir no
# executável. No PyInstaller, os ficheiros de dados ficam em
# `sys._MEIPASS` (a pasta `_internal` do modo --onedir) — o `bd/` tem
# de ser declarado nos "datas" do .spec (INST-04). A correr do código,
# fica ao lado deste config.py.
_PASTA_CODIGO = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
)
FICHEIRO_ESQUEMA = _PASTA_CODIGO / "bd" / "esquema.sql"
FICHEIRO_ESQUEMA_PRECHECKING = (
    _PASTA_CODIGO / "bd" / "esquema_prechecking.sql"
)

# --- Imagens (v1.8.0, INST-04) --------------------------------------
# Fonte única do caminho do `img/` (logótipo, ícone). A correr do
# código, o `img/` está na raiz do repositório, ao lado do `src/`. No
# executável (PyInstaller --onedir), o .spec copia-o para dentro do
# `_internal` (sys._MEIPASS). Antes, cada módulo calculava
# `Path(__file__).parent.parent.parent / "img"` — no executável isso
# aponta para FORA do `_internal` e as imagens desapareciam.
if getattr(sys, "frozen", False):
    PASTA_IMG = _PASTA_CODIGO / "img"
else:
    PASTA_IMG = _PASTA_CODIGO.parent / "img"


def garantir_diretorios():
    """Cria a árvore de diretorias persistentes, se ainda não existir.

    Chamada uma vez, explicitamente, em cada ponto de entrada
    (`main.py` e `main_gui.py`) — nunca ao importar este módulo, para
    não criar pastas em disco só por correr os testes automáticos.
    Idempotente (`exist_ok=True`): seguro chamar sempre que o sistema
    arranca.

    Se `DIR_BASE` não puder ser criada (ex. sem permissão de escrita
    na raiz do disco, no Windows), cai para `Path.home() /
    "Hostel_gestao"` e todas as subpastas passam a viver aí.
    """
    global DIR_BASE, DIR_DADOS, DIR_BACKUPS, DIR_CONTRATOS
    global DIR_RELATORIOS, DIR_LOGS
    try:
        DIR_BASE.mkdir(parents=True, exist_ok=True)
    except OSError:
        DIR_BASE = Path.home() / "Hostel_gestao"
        DIR_DADOS = DIR_BASE / "dados"
        DIR_BACKUPS = DIR_BASE / "backups"
        DIR_CONTRATOS = DIR_BASE / "contratos"
        DIR_RELATORIOS = DIR_BASE / "relatorios"
        DIR_LOGS = DIR_BASE / "logs"
        DIR_BASE.mkdir(parents=True, exist_ok=True)

    for diretoria in (
        DIR_DADOS,
        DIR_BACKUPS,
        DIR_CONTRATOS,
        DIR_RELATORIOS,
        DIR_LOGS,
    ):
        diretoria.mkdir(parents=True, exist_ok=True)
