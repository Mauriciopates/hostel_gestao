"""API do pré check-in (FastAPI).

Endpoints:
  GET  /api/saude        → {"ok": true}  (não toca na base; para a F3)
  POST /api/reserva      → detalhes da reserva do token
  POST /api/pre-checkin  → grava o pré check-in e gasta o token

Porque é POST /api/reserva e não GET /api/reserva?t=TOKEN: o que vai
no endereço (query string) fica escrito nos registos de acesso do
servidor e de qualquer proxy. No corpo do pedido, o token não fica.

Arranque (na VM, pelo serviço systemd — ver vm/instalar_api.sh):
  uvicorn prechecking.app:app --host 127.0.0.1 --port 8000
"""

import logging
from typing import Optional

import mysql.connector
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as ErroHttpStarlette

from . import config
from .esquemas import PedidoReserva, PreCheckin, Reserva
from .limite import LimitadorPedidos
from .repositorio import RepositorioMySQL, hash_token

registo = logging.getLogger("prechecking")

# A MESMA resposta para token inexistente, usado ou expirado: quem
# tenta adivinhar não fica a saber qual dos casos acertou.
ERRO_TOKEN = "Este link não é válido ou já expirou."
ERRO_SERVIDOR = "Serviço temporariamente indisponível."


# --------------------------------------------------------------------
# Limite do tamanho do corpo (middleware ASGI)
# --------------------------------------------------------------------
class LimiteCorpo:
    """Recusa (413) pedidos com corpo maior do que `maximo` bytes.

    Lê o corpo aos bocados e pára assim que passa o limite: um envio
    de 1 GB nunca chega a ficar todo em memória.
    """

    def __init__(self, app, maximo: int):
        self.app = app
        self.maximo = maximo

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cabecalhos = dict(scope.get("headers") or [])
        declarado = cabecalhos.get(b"content-length", b"0")
        if declarado.isdigit() and int(declarado) > self.maximo:
            await self._recusar(scope, receive, send)
            return

        corpo = b""
        while True:
            mensagem = await receive()
            if mensagem["type"] != "http.request":
                break
            corpo += mensagem.get("body", b"")
            if len(corpo) > self.maximo:
                await self._recusar(scope, receive, send)
                return
            if not mensagem.get("more_body", False):
                break

        entregue = False

        async def repetir():
            nonlocal entregue
            if not entregue:
                entregue = True
                return {"type": "http.request", "body": corpo,
                        "more_body": False}
            return await receive()

        await self.app(scope, repetir, send)

    async def _recusar(self, scope, receive, send):
        resposta = JSONResponse({"erro": "Pedido demasiado grande."},
                                status_code=413)
        await resposta(scope, receive, send)


# --------------------------------------------------------------------
# Dependências
# --------------------------------------------------------------------
def obter_repositorio() -> RepositorioMySQL:
    """Repositório real. Os testes trocam-no por um falso."""
    return RepositorioMySQL()


def limitar(request: Request) -> None:
    """429 se este IP passou o limite de pedidos.

    Atrás do Tailscale Funnel, o uvicorn corre com --proxy-headers e
    request.client.host passa a ser o IP real do hóspede (lido do
    X-Forwarded-For, aceite só quando vem de 127.0.0.1).
    """
    ip = request.client.host if request.client else "desconhecido"
    if not request.app.state.limitador.permitir(ip):
        raise HTTPException(status_code=429,
                            detail="Demasiados pedidos. Aguarde um pouco.")


# --------------------------------------------------------------------
# Aplicação
# --------------------------------------------------------------------
def criar_app(limitador: Optional[LimitadorPedidos] = None) -> FastAPI:
    """Monta a aplicação (os testes criam uma nova para cada caso)."""
    # Sem /docs, /redoc nem /openapi.json: em produção não se publica
    # o mapa da API.
    app = FastAPI(title="Pré check-in", docs_url=None, redoc_url=None,
                  openapi_url=None)
    app.state.limitador = limitador or LimitadorPedidos(
        config.PEDIDOS_POR_JANELA, config.JANELA_SEGUNDOS,
        config.MAXIMO_IPS_EM_MEMORIA)

    # O ÚLTIMO middleware acrescentado é o mais exterior. O CORS fica
    # por fora para que até os erros (413, 429) levem os cabeçalhos
    # CORS — senão o browser esconde a resposta do site.
    app.add_middleware(LimiteCorpo, maximo=config.TAMANHO_MAXIMO_CORPO)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.ORIGEM_SITE],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
        max_age=600,
    )

    @app.middleware("http")
    async def cabecalhos_seguranca(request: Request, chamar_seguinte):
        resposta = await chamar_seguinte(request)
        resposta.headers["Cache-Control"] = "no-store"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        return resposta

    @app.exception_handler(RequestValidationError)
    async def dados_invalidos(request: Request,
                              erro: RequestValidationError):
        # Só os NOMES dos campos com problema. A resposta por omissão
        # do FastAPI repetia os valores enviados (dados pessoais).
        campos = sorted({
            ".".join(str(p) for p in e.get("loc", ())
                     if p not in ("body",))
            for e in erro.errors()
        } - {""})
        return JSONResponse({"erro": "Dados inválidos.", "campos": campos},
                            status_code=422)

    # Apanha também os 404/405 das rotas que não existem.
    @app.exception_handler(ErroHttpStarlette)
    async def erro_http(request: Request, erro: ErroHttpStarlette):
        return JSONResponse({"erro": erro.detail},
                            status_code=erro.status_code)

    @app.get("/api/saude")
    def saude() -> dict:
        return {"ok": True}

    @app.post("/api/reserva", response_model=Reserva,
              dependencies=[Depends(limitar)])
    def reserva(pedido: PedidoReserva,
                repo: RepositorioMySQL = Depends(obter_repositorio)):
        try:
            detalhes = repo.obter_reserva(hash_token(pedido.token))
        except (mysql.connector.Error, RuntimeError) as erro:
            registo.error("Base indisponível: %s", type(erro).__name__)
            raise HTTPException(status_code=503, detail=ERRO_SERVIDOR)
        if detalhes is None:
            raise HTTPException(status_code=404, detail=ERRO_TOKEN)
        return detalhes

    @app.post("/api/pre-checkin", status_code=201,
              dependencies=[Depends(limitar)])
    def pre_checkin(dados: PreCheckin,
                    repo: RepositorioMySQL = Depends(obter_repositorio)):
        try:
            gravado = repo.registar_pre_checkin(hash_token(dados.token),
                                                dados)
        except (mysql.connector.Error, RuntimeError) as erro:
            # Nunca se registam os dados do hóspede, só o tipo de erro.
            registo.error("Falha ao gravar: %s", type(erro).__name__)
            raise HTTPException(status_code=503, detail=ERRO_SERVIDOR)
        if not gravado:
            raise HTTPException(status_code=404, detail=ERRO_TOKEN)
        return {"ok": True}

    return app


app = criar_app()
