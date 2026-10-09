"""Persistência do pré check-in (F5, 05/10/2026).

Fala com a base `hostel_prechecking` — a caixa de entrada que a API
escreve — e não com a `hostel_gestao`. Mesmo servidor, mesmo
utilizador (`hostel_app`), que lá só pode (F1):
  - tokens:    SELECT, INSERT, UPDATE, DELETE
  - pendentes: SELECT, UPDATE (estado), DELETE

O token NUNCA chega aqui em claro: só o hash SHA-256 (a camada de
negócio calcula-o). Se esta base não existir no servidor ligado (ex.:
o MySQL local do PC), as funções levantam o erro do mysql.connector e
o `prechecking.py` trata-o como "pré check-in indisponível".
"""

import logging
from typing import Any, cast

import config

from ._base import obter_conexao

logger = logging.getLogger(__name__)


def _ligar():
    return obter_conexao(config.DB_NAME_PRECHECKING)


def _hora(valor):
    """TIME do MySQL chega como timedelta → "HH:MM"."""
    if valor is None:
        return ""
    minutos = int(valor.total_seconds()) // 60
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _normalizar_token(linha):
    linha["hora_checkin"] = _hora(linha.get("hora_checkin"))
    linha["hora_checkout"] = _hora(linha.get("hora_checkout"))
    return linha


# --- tokens -----------------------------------------------------------


def substituir_token(dados):
    """Grava um token novo e apaga os links ainda POR USAR da mesma
    reserva, na mesma transação — uma reserva tem no máximo um link
    ativo. Os tokens já usados ficam (o pendente aponta para eles).

    `dados`: token_hash, referencia, criado_por_id, valido_ate,
    versao_aviso, unidade, morada, data_entrada, data_saida,
    hora_checkin, hora_checkout, regras.
    """
    conexao = _ligar()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM tokens WHERE referencia = %s AND usado_em IS NULL",
            (dados["referencia"],),
        )
        cursor.execute(
            "INSERT INTO tokens (token_hash, referencia, criado_por_id, "
            "valido_ate, versao_aviso, unidade, morada, data_entrada, "
            "data_saida, hora_checkin, hora_checkout, regras) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                dados["token_hash"], dados["referencia"],
                dados["criado_por_id"], dados["valido_ate"],
                dados["versao_aviso"], dados["unidade"], dados["morada"],
                dados["data_entrada"], dados["data_saida"],
                dados["hora_checkin"], dados["hora_checkout"],
                dados["regras"] or None,
            ),
        )
        conexao.commit()
        logger.info("Link de pré check-in gerado — reserva=%s",
                    dados["referencia"])
    finally:
        conexao.close()


def resumo_por_referencia(referencias):
    """Estado do pré check-in de cada reserva, numa só consulta.

    Devolve {referencia: {...}} — reservas sem token não aparecem:
      ultimo_usado / ultimo_expirado — o token mais recente;
      algum_usado   — algum token desta reserva já foi usado;
      pendente      — algum pré check-in desta reserva por validar.
    (Gerar um link novo com um pendente por validar deixa os dois: o
    pendente não pode desaparecer do estado.)
    """
    referencias = list(referencias)
    if not referencias:
        return {}

    marcas = ", ".join(["%s"] * len(referencias))
    conexao = _ligar()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT t.referencia, t.usado_em IS NOT NULL AS usado, "
            "t.valido_ate <= NOW() AS expirado, "
            "p.id IS NOT NULL AS pendente "
            "FROM tokens t "
            "LEFT JOIN pendentes p ON p.token_hash = t.token_hash "
            "AND p.estado = 'pendente' "
            f"WHERE t.referencia IN ({marcas}) "
            "ORDER BY t.criado_em, (t.usado_em IS NULL), t.usado_em",
            tuple(referencias),
        )
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()

    # `criado_em` é DATETIME (precisão de 1 s): dois links gerados no mesmo
    # segundo empatam. O desempate no ORDER BY põe o link por usar depois
    # dos já usados (gerar um link novo apaga os por usar, por isso só
    # pode haver um, e é sempre o mais recente) e, entre usados, o usado
    # mais tarde por último.
    resumo = {}
    for linha in linhas:            # o mais recente fica por último
        anterior = resumo.get(linha["referencia"], {})
        resumo[linha["referencia"]] = {
            "ultimo_usado": bool(linha["usado"]),
            "ultimo_expirado": bool(linha["expirado"]),
            "algum_usado": (
                anterior.get("algum_usado", False) or bool(linha["usado"])
            ),
            "pendente": (
                anterior.get("pendente", False) or bool(linha["pendente"])
            ),
        }
    return resumo


def apagar_token(token_hash):
    conexao = _ligar()
    try:
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM tokens WHERE token_hash = %s",
                       (token_hash,))
        conexao.commit()
    finally:
        conexao.close()


# --- pendentes --------------------------------------------------------

_SELECT_PENDENTE = (
    "SELECT p.*, t.referencia, t.unidade, t.morada, t.data_entrada, "
    "t.data_saida, t.hora_checkin, t.hora_checkout "
    "FROM pendentes p JOIN tokens t ON t.token_hash = p.token_hash "
)


def contar_pendentes():
    conexao = _ligar()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM pendentes WHERE estado = 'pendente'"
        )
        return int(cast(tuple, cursor.fetchone())[0])
    finally:
        conexao.close()


def listar_pendentes():
    """Pendentes por validar, os de entrada mais próxima primeiro."""
    conexao = _ligar()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            _SELECT_PENDENTE
            + "WHERE p.estado = 'pendente' "
            "ORDER BY t.data_entrada, p.recebido_em"
        )
        linhas = cast(list, cursor.fetchall())
    finally:
        conexao.close()
    return [_normalizar_token(linha) for linha in linhas]


def obter_pendente(pendente_id):
    conexao = _ligar()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(_SELECT_PENDENTE + "WHERE p.id = %s",
                       (pendente_id,))
        linha = cast("dict[str, Any] | None", cursor.fetchone())
    finally:
        conexao.close()
    return _normalizar_token(linha) if linha else None


def apagar_pendente(pendente_id, apagar_token_tambem=False):
    """Apaga o pendente (dados pessoais fora da caixa de entrada).

    Com `apagar_token_tambem` (Rejeitar) apaga também o token — a
    reserva volta a "sem link" e pode receber um link novo. Pela FK,
    o pendente sai primeiro. Tudo na mesma transação.
    """
    conexao = _ligar()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT token_hash FROM pendentes WHERE id = %s",
            (pendente_id,),
        )
        linha = cast("tuple | None", cursor.fetchone())
        if linha is None:
            conexao.rollback()
            return False
        cursor.execute("DELETE FROM pendentes WHERE id = %s",
                       (pendente_id,))
        if apagar_token_tambem:
            cursor.execute("DELETE FROM tokens WHERE token_hash = %s",
                           (linha[0],))
        conexao.commit()
        return True
    finally:
        conexao.close()
