"""Esquemas Pydantic: o que a API aceita e o que devolve.

Os tamanhos máximos são IGUAIS aos das colunas da base (ver
vm/instalar_prechecking.sh). Assim um texto gigante é recusado aqui,
antes de chegar ao MySQL. `extra="forbid"` recusa campos que não
existem no formulário.
"""

import datetime as dt
from typing import Annotated, Optional

from pydantic import (
    BaseModel, ConfigDict, Field, StrictBool, StringConstraints,
    field_validator, model_validator,
)

# Token: secrets.token_urlsafe(32) dá 43 caracteres de A-Z a-z 0-9 - _
Token = Annotated[str, StringConstraints(
    min_length=20, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]


# Texto obrigatório, sem espaços nas pontas, até N caracteres.
Texto50 = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=1, max_length=50)]
Texto100 = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=1, max_length=100)]
Texto150 = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=1, max_length=150)]


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PedidoReserva(_Estrito):
    """Corpo de POST /api/reserva."""
    token: Token


class Reserva(BaseModel):
    """Detalhes que o hóspede pode ver (SEM código da lockbox)."""
    unidade: str
    morada: str
    data_entrada: dt.date
    data_saida: dt.date
    hora_checkin: str
    hora_checkout: str
    regras: Optional[str] = None


class Cliente(_Estrito):
    """Os 7 campos do regime Airbnb."""
    nome: Texto150
    nacionalidade: Texto100
    data_nascimento: dt.date
    tipo_documento: Texto50
    numero_documento: Texto50
    pais_emissor_documento: Texto100
    pais_residencia: Texto100

    @field_validator("data_nascimento")
    @classmethod
    def _nascimento_plausivel(cls, valor: dt.date) -> dt.date:
        if not dt.date(1900, 1, 1) <= valor <= dt.date.today():
            raise ValueError("data de nascimento fora do intervalo")
        return valor


class Confirmacoes(_Estrito):
    """As 3 confirmações, separadas (StrictBool: só true/false)."""
    informado_privacidade: StrictBool
    aceitou_regulamento: StrictBool
    consente_comunicacoes: StrictBool = False


class PreCheckin(_Estrito):
    """Corpo de POST /api/pre-checkin (o JSON montado pelo index.html)."""
    token: Token
    # Recebida mas NÃO usada: a versão que faz prova é a da linha do
    # token (a que estava em vigor quando o link foi emitido).
    versao_aviso: Optional[Annotated[str, Field(max_length=20)]] = None
    # Relógio do telemóvel — guardado só como informação.
    submetido_em: Optional[dt.datetime] = None
    cliente: Cliente
    confirmacoes: Confirmacoes
    # Campo novo da F4: só existe com consentimento de comunicações.
    email: Optional[Annotated[str, StringConstraints(
        strip_whitespace=True, min_length=3, max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]] = None

    @model_validator(mode="after")
    def _regras_das_confirmacoes(self) -> "PreCheckin":
        c = self.confirmacoes
        if not c.informado_privacidade or not c.aceitou_regulamento:
            raise ValueError("faltam confirmações obrigatórias")
        # As mesmas regras do CHECK ck_pendente_email da base.
        if c.consente_comunicacoes and self.email is None:
            raise ValueError("consentimento sem email")
        if not c.consente_comunicacoes and self.email is not None:
            raise ValueError("email sem consentimento")
        return self

    def submetido_em_utc(self) -> Optional[dt.datetime]:
        """submetido_em em UTC e sem fuso (a coluna é DATETIME)."""
        if self.submetido_em is None:
            return None
        if self.submetido_em.tzinfo is None:
            return self.submetido_em
        return self.submetido_em.astimezone(
            dt.timezone.utc).replace(tzinfo=None)
