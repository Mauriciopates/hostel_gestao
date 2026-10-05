"""Testes da API do pré check-in (unittest, sem base de dados).

O repositório MySQL é trocado por um FALSO em memória que imita as
mesmas regras (token válido = existe, não usado, não expirado). Assim
testa-se a API toda — validação, CORS, limites, respostas — sem
precisar da VM. A ligação real ao MySQL é testada pelo
vm/instalar_api.sh, já na VM.

Correr (na pasta api/, com o ambiente virtual da API ativo):
    python -m unittest discover -s testes -p "teste_*.py"
"""

import datetime as dt
import logging
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mysql.connector  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from prechecking import config  # noqa: E402
from prechecking.app import criar_app, obter_repositorio  # noqa: E402
from prechecking.esquemas import Reserva  # noqa: E402
from prechecking.limite import LimitadorPedidos  # noqa: E402
from prechecking.repositorio import hash_token  # noqa: E402

TOKEN_OK = "a" * 43
TOKEN_USADO = "b" * 43
TOKEN_EXPIRADO = "c" * 43
TOKEN_INEXISTENTE = "d" * 43
ORIGEM = config.ORIGEM_SITE

# Os testes de "base em baixo" geram erros no registo de propósito.
logging.getLogger("prechecking").setLevel(logging.CRITICAL)


def reserva_exemplo() -> Reserva:
    return Reserva(unidade="Unidade teste", morada="Rua de Teste, 1",
                   data_entrada=dt.date(2026, 10, 10),
                   data_saida=dt.date(2026, 10, 12),
                   hora_checkin="15:00", hora_checkout="11:00",
                   regras="Sem festas.")


class RepositorioFalso:
    """Imita o RepositorioMySQL em memória (dados fictícios)."""

    def __init__(self):
        self.tokens = {
            hash_token(TOKEN_OK): {"usado": False, "expirado": False},
            hash_token(TOKEN_USADO): {"usado": True, "expirado": False},
            hash_token(TOKEN_EXPIRADO): {"usado": False, "expirado": True},
        }
        self.pendentes = []
        self.falhar = False

    def _valido(self, token_hash):
        t = self.tokens.get(token_hash)
        return t is not None and not t["usado"] and not t["expirado"]

    def obter_reserva(self, token_hash):
        if self.falhar:
            raise mysql.connector.errors.InterfaceError("sem ligação")
        return reserva_exemplo() if self._valido(token_hash) else None

    def registar_pre_checkin(self, token_hash, dados):
        if self.falhar:
            raise mysql.connector.errors.InterfaceError("sem ligação")
        if not self._valido(token_hash):
            return False
        self.tokens[token_hash]["usado"] = True
        self.pendentes.append((token_hash, dados))
        return True


def corpo_valido(token=TOKEN_OK) -> dict:
    """O JSON que o index.html monta (dados fictícios)."""
    return {
        "token": token,
        "versao_aviso": "1.0",
        "submetido_em": "2026-10-05T14:30:00.000Z",
        "cliente": {
            "nome": "Ana Teste",
            "nacionalidade": "Portuguesa",
            "data_nascimento": "1990-05-20",
            "tipo_documento": "Passaporte",
            "numero_documento": "X0000000",
            "pais_emissor_documento": "Portugal",
            "pais_residencia": "Portugal",
        },
        "confirmacoes": {
            "informado_privacidade": True,
            "aceitou_regulamento": True,
            "consente_comunicacoes": False,
        },
    }


class BaseApiTest(unittest.TestCase):
    """Cria uma API nova, com repositório falso, para cada teste."""

    def setUp(self):
        self.repo = RepositorioFalso()
        self.app = criar_app(LimitadorPedidos(1000, 60, 100))
        self.app.dependency_overrides[obter_repositorio] = \
            lambda: self.repo
        self.cliente = TestClient(self.app)

    def enviar(self, corpo, **extra):
        return self.cliente.post("/api/pre-checkin", json=corpo, **extra)


class TesteSaude(BaseApiTest):

    def test_saude_responde_sem_base(self):
        self.repo.falhar = True
        resposta = self.cliente.get("/api/saude")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"ok": True})

    def test_sem_documentacao_publicada(self):
        for caminho in ("/docs", "/redoc", "/openapi.json"):
            self.assertEqual(self.cliente.get(caminho).status_code, 404)


class TesteReserva(BaseApiTest):

    def test_token_valido_devolve_detalhes(self):
        resposta = self.cliente.post("/api/reserva",
                                     json={"token": TOKEN_OK})
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(dados["unidade"], "Unidade teste")
        self.assertEqual(dados["hora_checkin"], "15:00")
        self.assertEqual(dados["data_entrada"], "2026-10-10")

    def test_nunca_devolve_codigo_lockbox(self):
        resposta = self.cliente.post("/api/reserva",
                                     json={"token": TOKEN_OK})
        texto = resposta.text.lower()
        self.assertNotIn("lockbox", texto)
        self.assertNotIn("codigo", texto)

    def test_erro_igual_para_inexistente_usado_expirado(self):
        respostas = [
            self.cliente.post("/api/reserva", json={"token": t})
            for t in (TOKEN_INEXISTENTE, TOKEN_USADO, TOKEN_EXPIRADO)
        ]
        for r in respostas:
            self.assertEqual(r.status_code, 404)
        self.assertEqual(len({r.text for r in respostas}), 1)

    def test_token_com_caracteres_invalidos(self):
        resposta = self.cliente.post(
            "/api/reserva", json={"token": "' OR '1'='1' -- " + "x" * 20})
        self.assertEqual(resposta.status_code, 422)

    def test_token_curto_ou_gigante(self):
        for token in ("abc", "a" * 101):
            resposta = self.cliente.post("/api/reserva",
                                         json={"token": token})
            self.assertEqual(resposta.status_code, 422)

    def test_get_com_token_no_endereco_nao_existe(self):
        resposta = self.cliente.get("/api/reserva?t=" + TOKEN_OK)
        self.assertEqual(resposta.status_code, 405)

    def test_base_em_baixo_da_503(self):
        self.repo.falhar = True
        resposta = self.cliente.post("/api/reserva",
                                     json={"token": TOKEN_OK})
        self.assertEqual(resposta.status_code, 503)


class TestePreCheckin(BaseApiTest):

    def test_envio_valido_grava_e_gasta_token(self):
        resposta = self.enviar(corpo_valido())
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(len(self.repo.pendentes), 1)
        token_hash, dados = self.repo.pendentes[0]
        self.assertEqual(token_hash, hash_token(TOKEN_OK))
        self.assertEqual(dados.cliente.nome, "Ana Teste")

    def test_segundo_envio_com_mesmo_token_recusado(self):
        self.assertEqual(self.enviar(corpo_valido()).status_code, 201)
        segunda = self.enviar(corpo_valido())
        self.assertEqual(segunda.status_code, 404)
        self.assertEqual(len(self.repo.pendentes), 1)

    def test_depois_de_usado_a_reserva_deixa_de_abrir(self):
        self.enviar(corpo_valido())
        resposta = self.cliente.post("/api/reserva",
                                     json={"token": TOKEN_OK})
        self.assertEqual(resposta.status_code, 404)

    def test_token_usado_ou_expirado(self):
        for token in (TOKEN_USADO, TOKEN_EXPIRADO, TOKEN_INEXISTENTE):
            resposta = self.enviar(corpo_valido(token))
            self.assertEqual(resposta.status_code, 404)
        self.assertEqual(self.repo.pendentes, [])

    def test_sem_confirmacoes_obrigatorias(self):
        for campo in ("informado_privacidade", "aceitou_regulamento"):
            corpo = corpo_valido()
            corpo["confirmacoes"][campo] = False
            self.assertEqual(self.enviar(corpo).status_code, 422)
        self.assertEqual(self.repo.pendentes, [])

    def test_confirmacao_tem_de_ser_booleano(self):
        corpo = corpo_valido()
        corpo["confirmacoes"]["informado_privacidade"] = "sim"
        self.assertEqual(self.enviar(corpo).status_code, 422)

    def test_consentimento_e_email_andam_juntos(self):
        corpo = corpo_valido()
        corpo["confirmacoes"]["consente_comunicacoes"] = True
        self.assertEqual(self.enviar(corpo).status_code, 422)

        corpo = corpo_valido()
        corpo["email"] = "ana@exemplo.pt"
        self.assertEqual(self.enviar(corpo).status_code, 422)

        corpo = corpo_valido()
        corpo["confirmacoes"]["consente_comunicacoes"] = True
        corpo["email"] = "ana@exemplo.pt"
        self.assertEqual(self.enviar(corpo).status_code, 201)

    def test_email_mal_formado(self):
        corpo = corpo_valido()
        corpo["confirmacoes"]["consente_comunicacoes"] = True
        corpo["email"] = "isto-nao-e-email"
        self.assertEqual(self.enviar(corpo).status_code, 422)

    def test_campos_vazios_ou_so_espacos(self):
        corpo = corpo_valido()
        corpo["cliente"]["nome"] = "   "
        resposta = self.enviar(corpo)
        self.assertEqual(resposta.status_code, 422)
        self.assertIn("cliente.nome", resposta.json()["campos"])

    def test_tamanhos_maximos_iguais_as_colunas(self):
        limites = {"nome": 150, "nacionalidade": 100,
                   "tipo_documento": 50, "numero_documento": 50,
                   "pais_emissor_documento": 100, "pais_residencia": 100}
        for campo, maximo in limites.items():
            corpo = corpo_valido()
            corpo["cliente"][campo] = "x" * maximo
            self.assertEqual(self.enviar(corpo).status_code, 201, campo)
            self.repo.tokens[hash_token(TOKEN_OK)]["usado"] = False

            corpo["cliente"][campo] = "x" * (maximo + 1)
            self.assertEqual(self.enviar(corpo).status_code, 422, campo)

    def test_espacos_nas_pontas_sao_tirados(self):
        corpo = corpo_valido()
        corpo["cliente"]["nome"] = "  Ana Teste  "
        self.enviar(corpo)
        self.assertEqual(self.repo.pendentes[0][1].cliente.nome,
                         "Ana Teste")

    def test_data_nascimento_impossivel(self):
        for data in ("1850-01-01", "2999-01-01", "2026-02-30", "ontem"):
            corpo = corpo_valido()
            corpo["cliente"]["data_nascimento"] = data
            self.assertEqual(self.enviar(corpo).status_code, 422, data)

    def test_campo_a_mais_recusado(self):
        corpo = corpo_valido()
        corpo["cliente"]["admin"] = True
        self.assertEqual(self.enviar(corpo).status_code, 422)

    def test_campo_em_falta(self):
        corpo = corpo_valido()
        del corpo["cliente"]["numero_documento"]
        resposta = self.enviar(corpo)
        self.assertEqual(resposta.status_code, 422)
        self.assertIn("cliente.numero_documento", resposta.json()["campos"])

    def test_erro_de_validacao_nao_repete_os_dados(self):
        corpo = corpo_valido()
        corpo["cliente"]["numero_documento"] = "SEGREDO" * 20
        resposta = self.enviar(corpo)
        self.assertEqual(resposta.status_code, 422)
        self.assertNotIn("SEGREDO", resposta.text)

    def test_json_partido(self):
        resposta = self.cliente.post(
            "/api/pre-checkin", content=b"{nao e json",
            headers={"Content-Type": "application/json"})
        self.assertEqual(resposta.status_code, 422)

    def test_submetido_em_convertido_para_utc(self):
        corpo = corpo_valido()
        corpo["submetido_em"] = "2026-10-05T15:30:00+01:00"
        self.enviar(corpo)
        dados = self.repo.pendentes[0][1]
        self.assertEqual(dados.submetido_em_utc(),
                         dt.datetime(2026, 10, 5, 14, 30))

    def test_base_em_baixo_da_503_sem_dados_na_resposta(self):
        self.repo.falhar = True
        resposta = self.enviar(corpo_valido())
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("Ana", resposta.text)


class TesteProtecoes(BaseApiTest):

    def test_corpo_gigante_recusado(self):
        corpo = corpo_valido()
        corpo["cliente"]["nome"] = "x" * (config.TAMANHO_MAXIMO_CORPO + 1)
        resposta = self.enviar(corpo)
        self.assertEqual(resposta.status_code, 413)
        self.assertEqual(self.repo.pendentes, [])

    def test_cors_aceita_o_site(self):
        resposta = self.cliente.options("/api/pre-checkin", headers={
            "Origin": ORIGEM,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.headers.get("access-control-allow-origin"), ORIGEM)

    def test_cors_recusa_outra_origem(self):
        resposta = self.cliente.options("/api/pre-checkin", headers={
            "Origin": "https://site-malicioso.example",
            "Access-Control-Request-Method": "POST",
        })
        self.assertNotIn("access-control-allow-origin", resposta.headers)

        resposta = self.enviar(corpo_valido(), headers={
            "Origin": "https://site-malicioso.example"})
        self.assertNotIn("access-control-allow-origin", resposta.headers)

    def test_erros_levam_cabecalho_cors(self):
        resposta = self.enviar(corpo_valido(TOKEN_INEXISTENTE),
                               headers={"Origin": ORIGEM})
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(
            resposta.headers.get("access-control-allow-origin"), ORIGEM)

    def test_cabecalhos_de_seguranca(self):
        resposta = self.cliente.post("/api/reserva",
                                     json={"token": TOKEN_OK})
        self.assertEqual(resposta.headers["cache-control"], "no-store")
        self.assertEqual(resposta.headers["x-content-type-options"],
                         "nosniff")

    def test_excesso_de_pedidos_da_429(self):
        app = criar_app(LimitadorPedidos(3, 60, 100))
        app.dependency_overrides[obter_repositorio] = lambda: self.repo
        cliente = TestClient(app)
        estados = [cliente.post("/api/reserva",
                                json={"token": TOKEN_OK}).status_code
                   for _ in range(5)]
        self.assertEqual(estados, [200, 200, 200, 429, 429])

    def test_rota_inexistente_resposta_curta(self):
        resposta = self.cliente.get("/admin")
        self.assertEqual(resposta.status_code, 404)
        self.assertIn("erro", resposta.json())


class TesteLimitador(unittest.TestCase):

    def setUp(self):
        self.agora = 1000.0
        self.limitador = LimitadorPedidos(
            2, 60, 3, relogio=lambda: self.agora)

    def test_janela_deslizante(self):
        self.assertTrue(self.limitador.permitir("1.1.1.1"))
        self.assertTrue(self.limitador.permitir("1.1.1.1"))
        self.assertFalse(self.limitador.permitir("1.1.1.1"))
        self.agora += 60
        self.assertTrue(self.limitador.permitir("1.1.1.1"))

    def test_ips_contam_em_separado(self):
        self.limitador.permitir("1.1.1.1")
        self.limitador.permitir("1.1.1.1")
        self.assertTrue(self.limitador.permitir("2.2.2.2"))

    def test_memoria_limitada(self):
        for i in range(10):
            self.limitador.permitir(f"10.0.0.{i}")
        self.assertEqual(len(self.limitador._pedidos), 3)


class TesteHash(unittest.TestCase):

    def test_hash_sha256_conhecido(self):
        # echo -n "abc" | sha256sum
        self.assertEqual(
            hash_token("abc"),
            "ba7816bf8f01cfea414140de5dae2223"
            "b00361a396177a9cb410ff61f20015ad")

    def test_hash_tem_64_caracteres(self):
        self.assertEqual(len(hash_token(TOKEN_OK)), 64)


if __name__ == "__main__":
    unittest.main()
