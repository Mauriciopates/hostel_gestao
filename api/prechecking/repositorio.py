"""Acesso ao MySQL — a ÚNICA parte da API que fala com a base.

Liga como `api_prechecking`, que só pode:
  - SELECT em tokens
  - UPDATE (usado_em) em tokens
  - INSERT em pendentes
Tudo o resto é recusado pelo próprio MySQL (testado na F1).

Todas as queries são PARAMETRIZADAS (%s): o valor nunca é colado no
texto do SQL, por isso não há injeção de SQL.
"""

import datetime as dt
import hashlib
from typing import Any, Optional, cast

import mysql.connector

from . import config
from .esquemas import PreCheckin, Reserva

# Condição de "token válido", usada no SELECT e no UPDATE.
_TOKEN_VALIDO = "token_hash = %s AND usado_em IS NULL AND valido_ate > NOW()"


def hash_token(token: str) -> str:
    """SHA-256 do token em hexadecimal (64 caracteres).

    A base nunca guardou o token em claro: guarda este hash. Para
    procurar, calcula-se o hash do token recebido e compara-se.
    """
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _hora(valor) -> str:
    """TIME do MySQL (chega como timedelta) → "HH:MM"."""
    if isinstance(valor, dt.timedelta):
        minutos = int(valor.total_seconds()) // 60
        return f"{minutos // 60:02d}:{minutos % 60:02d}"
    return str(valor)[:5]


class RepositorioMySQL:
    """Operações da API sobre a base hostel_prechecking."""

    def _ligar(self):
        return mysql.connector.connect(**config.ligacao_mysql())

    def obter_reserva(self, token_hash: str) -> Optional[Reserva]:
        """Detalhes da reserva se o token for válido; senão None.

        None cobre os 3 casos (não existe, já usado, expirado) — quem
        chama não sabe qual foi, e de propósito.
        """
        ligacao = self._ligar()
        try:
            cursor = ligacao.cursor(dictionary=True)
            cursor.execute(
                "SELECT unidade, morada, data_entrada, data_saida,"
                " hora_checkin, hora_checkout, regras"
                " FROM tokens WHERE " + _TOKEN_VALIDO,
                (token_hash,))
            # cast: o mysql-connector não sabe que dictionary=True dá um
            # dicionário; só serve para o pyright, não muda nada.
            linha = cast("dict[str, Any] | None", cursor.fetchone())
            cursor.close()
            ligacao.rollback()   # só leitura; fecha a transação
        finally:
            ligacao.close()
        if linha is None:
            return None
        return Reserva(
            unidade=linha["unidade"],
            morada=linha["morada"],
            data_entrada=linha["data_entrada"],
            data_saida=linha["data_saida"],
            hora_checkin=_hora(linha["hora_checkin"]),
            hora_checkout=_hora(linha["hora_checkout"]),
            regras=linha["regras"],
        )

    def registar_pre_checkin(self, token_hash: str,
                             dados: PreCheckin) -> bool:
        """Gasta o token e guarda o pré check-in, numa só transação.

        Returns:
            True se ficou registado; False se o token não era válido.

        Porque é seguro com dois envios ao mesmo tempo: o UPDATE só
        muda a linha se `usado_em IS NULL`. O MySQL tranca a linha;
        o segundo pedido espera e, quando a vê, já tem usado_em
        preenchido → 0 linhas afetadas → False. Só um "ganha".
        """
        ligacao = self._ligar()
        try:
            ligacao.start_transaction()
            cursor = ligacao.cursor()

            # 1) Gastar o token (só se ainda for válido).
            cursor.execute(
                "UPDATE tokens SET usado_em = NOW() WHERE " + _TOKEN_VALIDO,
                (token_hash,))
            if cursor.rowcount != 1:
                ligacao.rollback()
                return False

            # 2) A versão do aviso que faz prova é a do token.
            cursor.execute(
                "SELECT versao_aviso FROM tokens WHERE token_hash = %s",
                (token_hash,))
            linha = cast("tuple[Any, ...] | None", cursor.fetchone())
            versao_aviso = linha[0] if linha else None

            # 3) Guardar o pré check-in na caixa de entrada.
            cliente = dados.cliente
            conf = dados.confirmacoes
            cursor.execute(
                "INSERT INTO pendentes (token_hash, submetido_em, nome,"
                " nacionalidade, data_nascimento, tipo_documento,"
                " numero_documento, pais_emissor_documento,"
                " pais_residencia, email, versao_aviso,"
                " informado_privacidade, aceitou_regulamento,"
                " consente_comunicacoes)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
                " %s, %s, %s)",
                (token_hash, dados.submetido_em_utc(), cliente.nome,
                 cliente.nacionalidade, cliente.data_nascimento,
                 cliente.tipo_documento, cliente.numero_documento,
                 cliente.pais_emissor_documento, cliente.pais_residencia,
                 dados.email, versao_aviso,
                 int(conf.informado_privacidade),
                 int(conf.aceitou_regulamento),
                 int(conf.consente_comunicacoes)))
            cursor.close()
            ligacao.commit()
            return True
        except Exception:
            # Qualquer falha desfaz TUDO: o token volta a ficar livre e
            # o hóspede pode tentar outra vez.
            ligacao.rollback()
            raise
        finally:
            ligacao.close()
