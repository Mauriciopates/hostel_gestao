"""Valores de configuração do sistema.

Contém os valores por omissão definidos na análise. Na Fase 1 são constantes
do módulo; a leitura passa a fazer-se pelo repositório quando este existir,
mantendo estes valores como estado inicial.

Montantes em Decimal (decisão 4). Datas de época alta guardadas como
(mes, dia) para serem independentes do ano.
"""

from decimal import Decimal

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

# --- Regime mensal --------------------------------------------------------
DIA_VENCIMENTO = 5
AVISO_PREVIO_DIAS = 15
DURACAO_MINIMA_MESES = 3

# --- Regime Airbnb --------------------------------------------------------
ESTADIA_MINIMA_NOITES = 1
ESTADIA_MAXIMA_NOITES = 28

# --- Horários -------------------------------------------------------------
HORA_CHECK_IN = "15:00"
HORA_CHECK_OUT = "11:00"
HORA_LIMITE_CHECK_IN_TARDIO = "17:00"

# --- Cópias de segurança --------------------------------------------------
DIAS_BACKUP = 30

# --- Conservação de dados (RGPD) ------------------------------------------
PRAZO_CONSERVACAO_HOSPEDES_DIAS = 365  # boletins SIBA/AIMA
PRAZO_CONSERVACAO_FISCAL_DIAS = 3650  # art.º 40.º Código Comercial
PRAZO_CONSERVACAO_LOGS_DIAS = 180  # minimização

# --- Versão do formato de dados -------------------------------------------
VERSAO_DADOS = 1
