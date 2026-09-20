"""Configurações globais do sistema — leitura e escrita.

Módulo de negócio. Fala com o `repositorio.py` (que trata da base de
dados MySQL), nunca com a interface. Devolve valores tipados e
sinaliza erro com `raise ValueError`, como todos os outros módulos
do sistema.

ESTRUTURA (decisão de 19/09/2026):

- A tabela `configuracoes` já existe no esquema MySQL do sistema
  (v1.5.4) com três colunas: `chave`, `valor`, `descricao`.
- A tabela `configuracoes_historico` guarda cada alteração, com
  autor, data e motivo — auditoria completa de quem mudou o quê.
- Não há coluna `grupo`: o agrupamento por tab é feito pelo
  **prefixo da chave** (`operacao.`, `financeiro.`, `stock.`,
  `sistema.`). Isto evita mexer no esquema.
- Os valores são guardados como texto na BD e convertidos pelo
  módulo conforme o tipo esperado pela chave:

    | Tipo       | Formato no MySQL   | Exemplo           |
    |------------|--------------------|-------------------|
    | Inteiro    | `"5"`              | `"5"`             |
    | Decimal    | `"2.5"` (ponto)    | `"2.5"`           |
    | Booleano   | `"true"` / `"false"` | `"true"`        |
    | Tupla      | `"7,1"` (vírgula)  | `"7,1"`           |
    | Texto      | texto simples      | `"15:00"`         |

PERMISSÕES (decisão de 19/09/2026):

Cada chave tem um perfil mínimo para ser alterada:

- Chaves `operacao.*`           → Master + Admin
- Chaves `financeiro.*`         → depende da chave
    - `financeiro.multiplicador_*` → Master apenas
    - restantes                    → Master + Admin
- Chaves `stock.*`              → Master apenas
- Chaves `sistema.*`            → Master apenas

A permissão é validada DENTRO do `definir` — não só na GUI. Se um
Admin tentar alterar uma chave que não lhe pertence, é recusado
com ValueError. Mesma disciplina do `utilizadores.verificar_permissao`.

SEED INICIAL:

No arranque do sistema, `garantir_seed()` insere os valores por
omissão (lidos do `config.py`) para as chaves que ainda não existem
na BD. Idempotente: correr duas vezes seguidas não faz nada na
segunda. É chamado pelo `main_gui.py` depois de
`config.garantir_diretorios()`.

HISTÓRICO:

Cada `definir` cria um registo em `configuracoes_historico` com:

  - `chave` (FK para `configuracoes`)
  - `valor_anterior` — o valor que estava antes (ou "" se era novo)
  - `valor_novo`
  - `data` — data da alteração
  - `responsavel_id` — quem alterou
  - `motivo` — opcional, texto livre

O `motivo` é opcional em todas as chaves (decisão de 19/09/2026).
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import cast

import config
import repositorio



# =====================================================================
# MAPA DAS CHAVES
# =====================================================================
#
# Cada entrada associa uma chave à sua definição:
#
#   - "tipo":   "int", "decimal", "bool", "tupla_mes_dia" ou "texto"
#   - "perfil": "master" ou "master_admin" — quem pode alterar
#   - "default": valor por omissão (usado no seed e como fallback)
#
# Este mapa é a FONTE DE VERDADE do módulo. Se uma chave não estiver
# aqui, o `obter` e o `definir` recusam-na (evita gravar chaves
# inventadas por engano).

_CHAVES = {
    # --- Operação ------------------------------------------------------
    "operacao.dia_vencimento": {
        "tipo": "int",
        "perfil": "master_admin",
        "default": config.DIA_VENCIMENTO,
        "descricao": "Dia do mês sugerido para novas rendas mensais (1–28).",
    },
    "operacao.aviso_previo_dias": {
        "tipo": "int",
        "perfil": "master_admin",
        "default": config.AVISO_PREVIO_DIAS,
        "descricao": "Antecedência mínima para encerramento de um contrato mensal.",
    },
    "operacao.duracao_minima_meses": {
        "tipo": "int",
        "perfil": "master_admin",
        "default": config.DURACAO_MINIMA_MESES,
        "descricao": "Abaixo deste valor, o encerramento é sinalizado com aviso.",
    },

    # --- Financeiro ----------------------------------------------------
    "financeiro.multiplicador_caucao": {
        "tipo": "decimal",
        "perfil": "master",
        "default": config.MULTIPLICADOR_CAUCAO,
        "descricao": "Quantas rendas sugerir como caução ao criar um contrato mensal.",
    },
    "financeiro.multiplicador_maximo_caucao": {
        "tipo": "decimal",
        "perfil": "master",
        "default": config.MULTIPLICADOR_MAXIMO_CAUCAO,
        "descricao": "Teto acima do qual o sistema recusa a caução.",
    },
    "financeiro.epoca_alta_inicio": {
        "tipo": "tupla_mes_dia",
        "perfil": "master_admin",
        "default": config.EPOCA_ALTA_INICIO,
        "descricao": "Mês e dia de início da época alta (independente do ano).",
    },
    "financeiro.epoca_alta_fim": {
        "tipo": "tupla_mes_dia",
        "perfil": "master_admin",
        "default": config.EPOCA_ALTA_FIM,
        "descricao": "Mês e dia de fim da época alta (independente do ano).",
    },
    "empresa.pasta_relatorios": {
        "tipo": "texto",
        "perfil": "master_admin",
        "default": str(config.DIR_RELATORIOS),
        "descricao": "Pasta onde guardar PDFs, CSVs e Excels de relatórios.",
    },

    # --- Stock ---------------------------------------------------------
    "stock.rol_automatico_airbnb": {
        "tipo": "bool",
        "perfil": "master",
        "default": True,
        "descricao": "Gera o Rol de Lavanderia ao criar reserva Airbnb.",
    },
    "stock.permitir_envio_parcial": {
        "tipo": "bool",
        "perfil": "master",
        "default": True,
        "descricao": "Permitir ao Admin enviar menos do que foi pedido.",
    },
}


# =====================================================================
# HELPERS INTERNOS DE CONVERSÃO
# =====================================================================


def _para_texto(valor):
    """Converte um valor Python para a representação na BD.

    - `bool` → "true" / "false"
    - `int` / `Decimal` → texto simples
    - tuplo (mes, dia) → "7,1"
    - `str` → tal e qual (strip aplicado por quem chama)
    """
    if isinstance(valor, bool):
        return "true" if valor else "false"

    if isinstance(valor, tuple) and len(valor) == 2:
        return f"{valor[0]},{valor[1]}"

    return str(valor)


def _do_texto(texto, tipo):
    """Converte o texto guardado na BD para o tipo Python esperado.

    Levanta ValueError se o texto não for compatível com o tipo —
    acontece se alguém alterar a BD à mão com um valor inválido.
    """
    if texto is None:
        raise ValueError("Valor em falta na base de dados.")

    if tipo == "int":
        try:
            return int(texto)
        except (ValueError, TypeError):
            raise ValueError(
                f"Valor inteiro inválido na base de dados: {texto!r}"
            )

    if tipo == "decimal":
        try:
            return Decimal(texto)
        except InvalidOperation:
            raise ValueError(
                f"Valor decimal inválido na base de dados: {texto!r}"
            )

    if tipo == "bool":
        if texto == "true":
            return True
        if texto == "false":
            return False
        raise ValueError(
            f"Valor booleano inválido na base de dados: {texto!r} "
            f"(esperado 'true' ou 'false')"
        )

    if tipo == "tupla_mes_dia":
        try:
            partes = texto.split(",")
            mes = int(partes[0])
            dia = int(partes[1])

            if not 1 <= mes <= 12 or not 1 <= dia <= 31:
                raise ValueError

            return (mes, dia)
        except (ValueError, IndexError):
            raise ValueError(
                f"Tupla (mês, dia) inválida na base de dados: {texto!r} "
                f"(esperado algo como '7,1')"
            )

    # "texto" e fallback
    return texto


# =====================================================================
# PERMISSÕES
# =====================================================================


def _perfil_do_autor(autor):
    """Devolve 'Master', 'Admin' ou None (sem autor)."""
    if autor is None:
        return None

    return autor.get("tipo_utilizador")


def _validar_permissao(chave, autor):
    """Confirma que o autor pode alterar esta chave.

    Levanta ValueError se não puder. A regra é: o perfil exigido
    pela chave (`master` ou `master_admin`) tem de estar contido
    no perfil do autor.
    """
    if autor is None:
        raise ValueError(
            "Não há responsável ativo. Escolha um antes de continuar."
        )

    if not autor.get("id"):
        raise ValueError(
            "O responsável ativo não tem ID. Volte a entrar no sistema."
        )

    definicao = _CHAVES.get(chave)

    if definicao is None:
        raise ValueError(f"Chave de configuração desconhecida: {chave}")

    perfil_exigido = definicao["perfil"]
    perfil_autor = _perfil_do_autor(autor)

    if perfil_exigido == "master":
        if perfil_autor != "Master":
            raise ValueError(
                f"Só um Master pode alterar '{chave}'."
            )
    elif perfil_exigido == "master_admin":
        if perfil_autor not in ("Master", "Admin"):
            raise ValueError(
                f"Só Master ou Admin podem alterar '{chave}'."
            )
    else:
        raise ValueError(
            f"Perfil desconhecido na definição da chave '{chave}': "
            f"{perfil_exigido!r}"
        )


def pode_alterar(chave, autor):
    """Devolve True se o autor pode alterar a chave — sem levantar.

    Útil para a GUI decidir se mostra ou esconde uma opção. Não
    substitui o `_validar_permissao` no `definir` — esse continua
    a ser a barreira real.
    """
    try:
        _validar_permissao(chave, autor)
        return True
    except ValueError:
        return False


# =====================================================================
# LEITURA
# =====================================================================


def obter(chave, default=None):
    """Devolve o valor da chave, já convertido para o tipo certo.

    Se a chave não estiver na BD, devolve `default` (que por omissão
    é `None`, mas quem chama pode passar o valor do `config.py`).

    Se a chave não estiver no mapa `_CHAVES`, levanta ValueError —
    evita `obter("chave.qualquer")` silenciosamente devolver None.
    """
    definicao = _CHAVES.get(chave)

    if definicao is None:
        raise ValueError(f"Chave de configuração desconhecida: {chave}")

    registo = repositorio.procurar_configuracao(chave)

    if registo is None:
        if default is not None:
            return default

        # Cai no default do mapa (que já veio do config.py).
        return definicao["default"]

    return _do_texto(registo["valor"], definicao["tipo"])


def obter_int(chave):
    """Atalho para `obter`, garantindo que devolve int."""
    return int(cast(int, obter(chave)))


def obter_decimal(chave):
    """Atalho para `obter`, garantindo que devolve Decimal."""
    return Decimal(cast(Decimal, obter(chave)))


def obter_bool(chave):
    """Atalho para `obter`, garantindo que devolve bool."""
    return bool(cast(bool, obter(chave)))


def obter_tupla(chave):
    """Atalho para `obter`, garantindo que devolve tuplo (a, b)."""
    return tuple(cast(tuple, obter(chave)))


def listar_por_prefixo(prefixo):
    """Devolve um dicionário {chave: valor} de todas as chaves do
    prefixo indicado (ex.: "operacao." para a tab Operação).

    As chaves que não existirem na BD caem nos defaults do mapa
    `_CHAVES`. Útil para a GUI montar uma tab inteira de uma vez.
    """
    resultado = {}

    for chave, definicao in _CHAVES.items():
        if not chave.startswith(prefixo):
            continue

        registo = repositorio.procurar_configuracao(chave)

        if registo is None:
            resultado[chave] = definicao["default"]
        else:
            resultado[chave] = _do_texto(registo["valor"], definicao["tipo"])

    return resultado


def definir(chave, valor, autor, motivo=""):
    """Grava um novo valor para a chave e registra no histórico.

    Validações:
      - A chave tem de existir no mapa `_CHAVES`.
      - O autor tem de ter perfil suficiente (ver `_validar_permissao`).
      - O valor tem de ser compatível com o tipo da chave.

    Fluxo:
      1. Valida permissão (levanta se não tiver).
      2. Lê o valor atual (para o histórico).
      3. Grava o novo valor na tabela `configuracoes`.
      4. Cria um registo em `configuracoes_historico`.

    Devolve o valor novo, já convertido para o tipo certo.
    """
    _validar_permissao(chave, autor)

    definicao = _CHAVES[chave]
    texto_novo = _para_texto(valor)

    # Ler o valor anterior — para o histórico
    registo_atual = repositorio.procurar_configuracao(chave)
    texto_anterior = registo_atual["valor"] if registo_atual else ""

    # Gravar o valor novo (insert ou update)
    repositorio.gravar_configuracao(
        chave,
        texto_novo,
        descricao=definicao["descricao"],
    )

    # Registar no histórico
    repositorio.inserir_configuracao_historico(
        {
            "id": repositorio.proximo_id("CFH"),
            "chave": chave,
            "valor_anterior": texto_anterior,
            "valor_novo": texto_novo,
            "data": date.today(),
            "responsavel_id": autor["id"],
            "motivo": (motivo or "").strip(),
        }
    )

    return _do_texto(texto_novo, definicao["tipo"])


def listar_historico(chave=None):
    """Devolve o histórico de alterações, opcionalmente filtrado
    por chave. Ordenado do mais recente para o mais antigo.
    """
    registos = repositorio.listar_configuracao_historico(chave=chave)
    registos.sort(key=lambda r: r["data"], reverse=True)
    return registos


# =====================================================================
# SEED INICIAL
# =====================================================================


def garantir_seed():
    """Garante que todas as chaves do mapa existem na BD.

    Insere as que faltarem, com os valores por omissão do `config.py`
    (que já vieram no `_CHAVES`). Idempotente.

    Devolve o número de chaves criadas nesta chamada (0 se já existiam
    todas). Útil para o arranque saber se houve seed novo.
    """
    criadas = 0

    for chave, definicao in _CHAVES.items():
        registo = repositorio.procurar_configuracao(chave)

        if registo is not None:
            continue

        repositorio.gravar_configuracao(
            chave,
            _para_texto(definicao["default"]),
            descricao=definicao["descricao"],
        )
        criadas += 1

    return criadas


# =====================================================================
# METADADOS (para a GUI)
# =====================================================================


def listar_definicoes(prefixo=None):
    """Devolve as definições do mapa `_CHAVES` — sem tocar na BD.

    Cada entrada é um dicionário com:
      - "chave": texto da chave
      - "tipo": tipo do valor
      - "perfil": perfil mínimo para alterar
      - "default": valor por omissão
      - "descricao": texto descritivo

    Filtra por prefixo quando indicado. A GUI usa isto para saber
    que opções mostrar numa tab — sem precisar de hardcoded.
    """
    resultado = []

    for chave, definicao in _CHAVES.items():
        if prefixo is not None and not chave.startswith(prefixo):
            continue

        resultado.append(
            {
                "chave": chave,
                "tipo": definicao["tipo"],
                "perfil": definicao["perfil"],
                "default": definicao["default"],
                "descricao": definicao["descricao"],
            }
        )

    return resultado