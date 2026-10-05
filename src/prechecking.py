"""Pré check-in dos hóspedes — o lado do desktop (F5, 05/10/2026).

O percurso completo (ficheiro 08 do projeto):

  1. Aqui: `gerar_link` cria um token aleatório para uma reserva
     Airbnb. A base `hostel_prechecking` guarda só o HASH SHA-256 e os
     detalhes que o hóspede pode ver (sem código da lockbox).
  2. O anfitrião cola o link na mensagem do Airbnb.
  3. O hóspede preenche o site; a API grava um PENDENTE e gasta o
     token.
  4. Aqui: `listar_pendentes` / `comparar` mostram o que chegou ao lado
     da ficha do cliente; `importar` passa os dados para a ficha e
     regista o aviso de privacidade; `rejeitar` deita-o fora. Nos dois
     casos o pendente é APAGADO — dados pessoais não ficam na base
     exposta à internet.

Só Master e Admin (decisão do aluno, 05/10/2026). A GUI esconde os
ecrãs ao Staff; a barreira real está aqui (`_exigir_gestao`).

Camadas: este módulo recebe dados, devolve resultados e levanta
ValueError. Só o `repositorio` toca nas bases.
"""

import datetime
import hashlib
import logging
import secrets

import mysql.connector

import clientes
import config
import contratos
import propriedades
import repositorio
import responsaveis
import termos
import unidades

logger = logging.getLogger(__name__)

_PERFIS_GESTAO = ("Master", "Admin")

# Estados do pré check-in de uma reserva (calculados, nunca guardados).
SEM_LINK = "sem_link"
LINK_ENVIADO = "link_enviado"
EXPIRADO = "expirado"
RECEBIDO = "recebido"
IMPORTADO = "importado"

ROTULOS_ESTADO = {
    SEM_LINK: "—",
    LINK_ENVIADO: "Link enviado",
    EXPIRADO: "Link expirado",
    RECEBIDO: "Recebido",
    IMPORTADO: "Importado",
}

# Campos que o hóspede envia e que vão para a ficha do cliente:
# (chave no pendente / no cliente, rótulo no ecrã).
CAMPOS_FICHA = (
    ("nome", "Nome"),
    ("nacionalidade", "Nacionalidade"),
    ("data_nascimento", "Data de nascimento"),
    ("tipo_documento", "Tipo de documento"),
    ("numero_documento", "Número do documento"),
    ("pais_emissor_documento", "País emissor"),
    ("pais_residencia", "País de residência"),
)

_TAMANHO_MAXIMO_REGRAS = 2000


class PreCheckinIndisponivel(ValueError):
    """A base `hostel_prechecking` não existe ou não responde neste
    servidor (ex.: o MySQL local do PC). Subclasse de ValueError para
    os ecrãs a mostrarem como qualquer outro erro."""


def _ligacao_segura(funcao, *args, **kwargs):
    """Corre uma função do repositório e traduz os erros de ligação
    numa mensagem clara."""
    try:
        return funcao(*args, **kwargs)
    except mysql.connector.Error as erro:
        logger.warning("Pré check-in indisponível: %s", erro)
        raise PreCheckinIndisponivel(
            "O pré check-in não está disponível neste servidor (a base "
            f"'{config.DB_NAME_PRECHECKING}' não respondeu)."
        ) from erro


def _exigir_gestao(responsavel_id):
    autor = responsaveis.validar_autoria(responsavel_id)
    if autor.get("tipo_utilizador") not in _PERFIS_GESTAO:
        logger.warning(
            "Pré check-in recusado — responsavel_id=%s, tipo=%s",
            autor["id"], autor.get("tipo_utilizador"),
        )
        raise ValueError("Só um Master ou Admin pode gerir o pré check-in.")
    return autor


def hash_token(token):
    """SHA-256 em hexadecimal — a mesma conta que a API faz."""
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def montar_link(token):
    return f"{config.URL_SITE_PRECHECKING}?t={token}"


# --- disponibilidade e contagem ------------------------------------------


def contar_pendentes():
    """Pendentes por validar. 0 se a caixa de entrada não existir neste
    servidor — o menu e o Dashboard nunca rebentam por causa disto."""
    try:
        return repositorio.contar_pendentes()
    except mysql.connector.Error:
        return 0


# --- 1. gerar o link ---------------------------------------------------


def _hora_valida(texto, nome):
    try:
        return datetime.datetime.strptime(texto.strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        raise ValueError(f"{nome}: escreva a hora como HH:MM.") from None


def dados_link(reserva_id):
    """O que o modal "Gerar link" mostra por omissão: alojamento,
    morada, datas, horários de config e validade = dia da saída às
    23:59. Levanta ValueError se a reserva não puder ter link."""
    ocupacao = contratos.procurar(reserva_id)
    if ocupacao is None:
        raise ValueError(f"A reserva {reserva_id} não existe.")
    if ocupacao["tipo"] != "airbnb":
        raise ValueError("O pré check-in é só para reservas Airbnb.")
    if not ocupacao["ativo"]:
        raise ValueError("A reserva está cancelada.")
    if ocupacao["data_fim"] < datetime.date.today():
        raise ValueError("A reserva já terminou.")

    unidade = unidades.procurar(ocupacao["unidade_id"])
    propriedade = (
        propriedades.procurar(unidade["propriedade_id"]) if unidade else None
    )

    return {
        "reserva_id": ocupacao["id"],
        "cliente_id": ocupacao["cliente_id"],
        "unidade": unidade["nome"] if unidade else ocupacao["unidade_id"],
        "morada": (propriedade or {}).get("morada") or "",
        "data_entrada": ocupacao["data_inicio"],
        "data_saida": ocupacao["data_fim"],
        "hora_checkin": config.HORA_CHECK_IN,
        "hora_checkout": config.HORA_CHECK_OUT,
        "valido_ate": datetime.datetime.combine(
            ocupacao["data_fim"], datetime.time(23, 59)
        ),
        "versao_aviso": termos.texto_em_vigor(
            termos.PRIVACIDADE_HOSPEDE)["versao"],
    }


def gerar_link(reserva_id, responsavel_id, hora_checkin, hora_checkout,
               regras="", valido_ate=None):
    """Cria o link de pré check-in de uma reserva e devolve-o.

    O token (32 bytes aleatórios do `secrets`) só existe neste momento:
    a base guarda o hash. Gerar outra vez apaga o link anterior que
    ainda não tenha sido usado (um link ativo por reserva).
    """
    autor = _exigir_gestao(responsavel_id)
    dados = dados_link(reserva_id)

    entrada = _hora_valida(hora_checkin, "Check-in")
    saida = _hora_valida(hora_checkout, "Check-out")

    regras = (regras or "").strip()
    if len(regras) > _TAMANHO_MAXIMO_REGRAS:
        raise ValueError(
            f"As regras têm mais de {_TAMANHO_MAXIMO_REGRAS} caracteres."
        )

    if not dados["morada"]:
        raise ValueError(
            "A propriedade desta unidade não tem morada — preencha-a em "
            "Gestão de Propriedades antes de gerar o link."
        )

    valido_ate = valido_ate or dados["valido_ate"]
    if valido_ate <= datetime.datetime.now():
        raise ValueError("A validade do link já passou.")

    token = secrets.token_urlsafe(32)

    _ligacao_segura(repositorio.substituir_token, {
        "token_hash": hash_token(token),
        "referencia": dados["reserva_id"],
        "criado_por_id": autor["id"],
        "valido_ate": valido_ate,
        "versao_aviso": dados["versao_aviso"],
        "unidade": dados["unidade"],
        "morada": dados["morada"],
        "data_entrada": dados["data_entrada"],
        "data_saida": dados["data_saida"],
        "hora_checkin": entrada.strftime("%H:%M"),
        "hora_checkout": saida.strftime("%H:%M"),
        "regras": regras,
    })
    return montar_link(token)


# --- 2. estado de cada reserva -------------------------------------------


def estados(reserva_ids):
    """{reserva_id: estado} para a coluna da lista de reservas.

    Sem a caixa de entrada neste servidor, todas ficam SEM_LINK.
    """
    reserva_ids = list(reserva_ids)
    try:
        resumo = repositorio.resumo_por_referencia(reserva_ids)
    except mysql.connector.Error:
        resumo = {}

    resultado = {}
    for reserva_id in reserva_ids:
        info = resumo.get(reserva_id)
        if info is None:
            estado = SEM_LINK
        elif info["pendente"]:
            estado = RECEBIDO
        elif not info["ultimo_usado"] and not info["ultimo_expirado"]:
            estado = LINK_ENVIADO
        elif info["algum_usado"]:
            estado = IMPORTADO
        else:
            estado = EXPIRADO
        resultado[reserva_id] = estado
    return resultado


# --- 3. pendentes ------------------------------------------------------


def _cliente_da_reserva(pendente):
    ocupacao = contratos.procurar(pendente["referencia"])
    if ocupacao is None:
        return None, None
    return ocupacao, clientes.procurar(ocupacao["cliente_id"])


def comparar(pendente, cliente):
    """Lista de linhas (chave, rótulo, valor na ficha, valor enviado,
    diferente?) — o quadro "ficha atual / enviado pelo hóspede"."""
    linhas = []
    for chave, rotulo in CAMPOS_FICHA:
        atual = (cliente or {}).get(chave)
        enviado = pendente.get(chave)
        if isinstance(atual, str) and isinstance(enviado, str):
            diferente = atual.strip().casefold() != enviado.strip().casefold()
        else:
            diferente = atual != enviado
        linhas.append((chave, rotulo, atual, enviado, diferente))
    return linhas


def listar_pendentes(responsavel_id):
    """Pendentes por validar, cada um com `cliente_id`, `diferencas`
    (quantos campos mudam) e `reserva_existe`."""
    _exigir_gestao(responsavel_id)
    lista = _ligacao_segura(repositorio.listar_pendentes)
    for pendente in lista:
        ocupacao, cliente = _cliente_da_reserva(pendente)
        pendente["reserva_existe"] = ocupacao is not None
        pendente["cliente_id"] = cliente["id"] if cliente else None
        pendente["diferencas"] = sum(
            1 for linha in comparar(pendente, cliente) if linha[4]
        )
    return lista


def detalhe(pendente_id, responsavel_id):
    """(pendente, cliente, linhas da comparação) para o modal Validar."""
    _exigir_gestao(responsavel_id)
    pendente = _ligacao_segura(repositorio.obter_pendente, pendente_id)
    if pendente is None or pendente["estado"] != "pendente":
        raise ValueError("Este pré check-in já não está por validar.")
    _ocupacao, cliente = _cliente_da_reserva(pendente)
    return pendente, cliente, comparar(pendente, cliente)


def importar(pendente_id, responsavel_id):
    """Passa os dados do hóspede para a ficha do cliente da reserva.

    Por esta ordem — e o pendente só sai no fim:
      1. ficha do cliente (`clientes.atualizar`, com as validações de
         sempre do regime Airbnb);
      2. consentimento de comunicações + email, se houver;
      3. aviso de privacidade (versão que o hóspede viu, suporte web,
         registado por quem importa);
      4. apaga o pendente (o token fica, marcado como usado → a reserva
         passa a "Importado").
    Se 1–3 falharem, o pendente continua lá para nova tentativa
    (repetir é seguro: a ficha fica igual e o aviso não duplica).

    Devolve o cliente atualizado.
    """
    autor = _exigir_gestao(responsavel_id)
    pendente, cliente, _linhas = detalhe(pendente_id, responsavel_id)

    if cliente is None:
        raise ValueError(
            f"A reserva {pendente['referencia']} já não existe — "
            "rejeite este pré check-in."
        )

    atualizado = clientes.atualizar(
        cliente["id"],
        regime="airbnb",
        **{chave: pendente[chave] for chave, _rotulo in CAMPOS_FICHA},
    )

    if pendente["consente_comunicacoes"] and pendente["email"]:
        atualizado = clientes.registar_consentimento_comunicacoes(
            cliente["id"], pendente["email"], pendente["recebido_em"]
        )

    termos.registar_versao_vista(
        cliente["id"], pendente["versao_aviso"], autor["id"]
    )

    _ligacao_segura(repositorio.apagar_pendente, pendente_id)
    logger.info(
        "Pré check-in importado — pendente=%s, reserva=%s, cliente=%s, "
        "por=%s",
        pendente_id, pendente["referencia"], cliente["id"], autor["id"],
    )
    return atualizado


def rejeitar(pendente_id, responsavel_id):
    """Deita fora um pré check-in sem tocar na ficha.

    Apaga o pendente E o token: a reserva volta a "sem link" e pode
    receber um link novo.
    """
    autor = _exigir_gestao(responsavel_id)
    pendente, _cliente, _linhas = detalhe(pendente_id, responsavel_id)
    _ligacao_segura(repositorio.apagar_pendente, pendente_id, True)
    logger.info(
        "Pré check-in rejeitado — pendente=%s, reserva=%s, por=%s",
        pendente_id, pendente["referencia"], autor["id"],
    )
