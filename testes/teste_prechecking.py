"""Testes do pré check-in no desktop (F5, 05/10/2026).

Correm contra `hostel_gestao_teste` + `hostel_prechecking_teste`
(`apoio_BD.BasePreCheckinTest`), nunca contra as bases reais. O papel
da API (gravar um pendente e gastar o token) é imitado com um INSERT
igual ao que ela faz. Dados todos fictícios.
"""

import datetime
import re
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import (  # noqa: E402
    BasePreCheckinTest,
    instrucoes_esquema_prechecking,
)

import clientes  # noqa: E402
import config  # noqa: E402
import contratos  # noqa: E402
import prechecking  # noqa: E402
import propriedades  # noqa: E402
import repositorio  # noqa: E402
import responsaveis  # noqa: E402
import termos  # noqa: E402
import unidades  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def _sql_prechecking(sql, parametros=()) -> list[Any]:
    """Corre SQL na caixa de entrada de TESTE; devolve as linhas (lista
    vazia quando a instrução não devolve nada)."""
    conexao = repositorio.obter_conexao(config.DB_NAME_PRECHECKING)
    try:
        cursor = conexao.cursor()
        cursor.execute(sql, parametros)
        linhas = list(cursor.fetchall()) if cursor.description else []
        conexao.commit()
        return cast(list[Any], linhas)
    finally:
        conexao.close()


def _token_do_link(link):
    return parse_qs(urlparse(link).query)["t"][0]


class BaseReservaTest(BasePreCheckinTest):
    """Uma propriedade com morada, uma unidade Airbnb, um cliente e uma
    reserva daqui a 5 dias."""

    def setUp(self):
        super().setUp()
        self.propriedade = propriedades.criar(
            "Santa Catarina Teste", morada="Rua de Teste, 1, Porto"
        )
        self.unidade = unidades.criar(
            self.propriedade["id"], "Unidade Airbnb Teste", "airbnb",
            Decimal("45.00"), Decimal("90.00"), Decimal("20.00"),
        )
        self.cliente = clientes.criar(
            "Ana Teste", "Cartão de Cidadão", "X0000001", "airbnb",
            nacionalidade="Brasileira", pais_emissor_documento="Brasil",
            pais_residencia="Brasil", data_nascimento=date(1990, 1, 1),
        )
        self.entrada = date.today() + timedelta(days=5)
        self.saida = self.entrada + timedelta(days=2)
        self.reserva, _ = contratos.registar_airbnb(
            self.unidade["id"], self.cliente["id"], self.entrada,
            self.saida, Decimal("90.00"),
        )

    def _gerar(self, **extra):
        argumentos = {"hora_checkin": "15:00", "hora_checkout": "11:00"}
        argumentos.update(extra)
        return prechecking.gerar_link(
            self.reserva["id"], self.master["id"], **argumentos
        )

    def _simular_api(self, link, **campos):
        """O que a API faz no POST /api/pre-checkin: gasta o token e
        grava o pendente (com a versão do aviso do token)."""
        token_hash = prechecking.hash_token(_token_do_link(link))
        dados = {
            "nome": "Ana Teste", "nacionalidade": "Brasileira",
            "data_nascimento": date(1990, 1, 1),
            "tipo_documento": "Passaporte",
            "numero_documento": "FX123456",
            "pais_emissor_documento": "Brasil",
            "pais_residencia": "Portugal",
            "email": None, "consente_comunicacoes": 0,
        }
        dados.update(campos)
        _sql_prechecking(
            "UPDATE tokens SET usado_em = NOW() WHERE token_hash = %s",
            (token_hash,),
        )
        _sql_prechecking(
            "INSERT INTO pendentes (token_hash, nome, nacionalidade, "
            "data_nascimento, tipo_documento, numero_documento, "
            "pais_emissor_documento, pais_residencia, email, "
            "versao_aviso, informado_privacidade, aceitou_regulamento, "
            "consente_comunicacoes) SELECT %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, versao_aviso, 1, 1, %s FROM tokens "
            "WHERE token_hash = %s",
            (token_hash, dados["nome"], dados["nacionalidade"],
             dados["data_nascimento"], dados["tipo_documento"],
             dados["numero_documento"], dados["pais_emissor_documento"],
             dados["pais_residencia"], dados["email"],
             dados["consente_comunicacoes"], token_hash),
        )
        return _sql_prechecking(
            "SELECT id FROM pendentes WHERE token_hash = %s", (token_hash,)
        )[0][0]

    def _estado(self):
        return prechecking.estados([self.reserva["id"]])[self.reserva["id"]]


# ---------------------------------------------------------------------
# 1. Gerar o link
# ---------------------------------------------------------------------


class TesteGerarLink(BaseReservaTest):

    def test_link_aponta_para_o_site_com_token(self):
        link = self._gerar()
        self.assertTrue(link.startswith(config.URL_SITE_PRECHECKING))
        self.assertRegex(_token_do_link(link), r"^[A-Za-z0-9_-]{43}$")

    def test_base_guarda_so_o_hash(self):
        token = _token_do_link(self._gerar())
        linhas = _sql_prechecking("SELECT token_hash FROM tokens")
        self.assertEqual([(prechecking.hash_token(token),)], linhas)
        self.assertNotIn(token, str(linhas))

    def test_detalhes_copiados_para_o_token(self):
        self._gerar(regras="Sem festas.")
        linha = _sql_prechecking(
            "SELECT referencia, unidade, morada, data_entrada, data_saida,"
            " regras, versao_aviso, criado_por_id FROM tokens"
        )[0]
        self.assertEqual(
            (self.reserva["id"], "Unidade Airbnb Teste",
             "Rua de Teste, 1, Porto", self.entrada, self.saida,
             "Sem festas.", "1.0", self.master["id"]),
            linha,
        )

    def test_validade_por_omissao_e_o_dia_da_saida(self):
        self._gerar()
        valido_ate = _sql_prechecking("SELECT valido_ate FROM tokens")[0][0]
        self.assertEqual(
            datetime.datetime.combine(self.saida, datetime.time(23, 59)),
            valido_ate,
        )

    def test_gerar_outra_vez_substitui_o_link_por_usar(self):
        primeiro = _token_do_link(self._gerar())
        segundo = _token_do_link(self._gerar())
        hashes = [h for (h,) in _sql_prechecking(
            "SELECT token_hash FROM tokens")]
        self.assertNotEqual(primeiro, segundo)
        self.assertEqual([prechecking.hash_token(segundo)], hashes)

    def test_staff_recusado(self):
        staff = responsaveis.criar("Staff Teste", tipo_utilizador="Staff",
                                   autor=self.master)
        with self.assertRaises(ValueError):
            prechecking.gerar_link(self.reserva["id"], staff["id"],
                                   "15:00", "11:00")

    def test_reserva_cancelada_recusada(self):
        contratos.cancelar_airbnb(self.reserva["id"])
        with self.assertRaises(ValueError):
            self._gerar()

    def test_hora_mal_escrita_recusada(self):
        for hora in ("15h", "25:00", ""):
            with self.subTest(hora=hora):
                with self.assertRaises(ValueError):
                    self._gerar(hora_checkin=hora)

    def test_propriedade_sem_morada_recusada(self):
        repositorio.atualizar_propriedade(
            self.propriedade["id"], {"morada": ""})
        with self.assertRaises(ValueError) as contexto:
            self._gerar()
        self.assertIn("morada", str(contexto.exception))


# ---------------------------------------------------------------------
# 2. Estado de cada reserva
# ---------------------------------------------------------------------


class TesteEstados(BaseReservaTest):

    def test_percurso_completo_dos_estados(self):
        self.assertEqual(prechecking.SEM_LINK, self._estado())

        link = self._gerar()
        self.assertEqual(prechecking.LINK_ENVIADO, self._estado())

        pendente_id = self._simular_api(link)
        self.assertEqual(prechecking.RECEBIDO, self._estado())

        prechecking.importar(pendente_id, self.master["id"])
        self.assertEqual(prechecking.IMPORTADO, self._estado())

    def test_link_expirado(self):
        self._gerar()
        _sql_prechecking(
            "UPDATE tokens SET valido_ate = NOW() - INTERVAL 1 MINUTE")
        self.assertEqual(prechecking.EXPIRADO, self._estado())

    def test_link_novo_com_pendente_continua_recebido(self):
        self._simular_api(self._gerar())
        self._gerar()
        self.assertEqual(prechecking.RECEBIDO, self._estado())

    def test_link_novo_depois_de_importado_fica_enviado(self):
        pendente_id = self._simular_api(self._gerar())
        prechecking.importar(pendente_id, self.master["id"])
        self._gerar()
        self.assertEqual(prechecking.LINK_ENVIADO, self._estado())

    def test_rejeitar_volta_a_sem_link(self):
        pendente_id = self._simular_api(self._gerar())
        prechecking.rejeitar(pendente_id, self.master["id"])
        self.assertEqual(prechecking.SEM_LINK, self._estado())


# ---------------------------------------------------------------------
# 3. Pendentes: listar, comparar, importar, rejeitar
# ---------------------------------------------------------------------


class TestePendentes(BaseReservaTest):

    def test_contar_e_listar(self):
        self._simular_api(self._gerar())
        self.assertEqual(1, prechecking.contar_pendentes())

        lista = prechecking.listar_pendentes(self.master["id"])
        self.assertEqual(1, len(lista))
        self.assertEqual(self.reserva["id"], lista[0]["referencia"])
        self.assertEqual(self.cliente["id"], lista[0]["cliente_id"])
        # Tipo, número do documento e país de residência mudaram.
        self.assertEqual(3, lista[0]["diferencas"])

    def test_comparar_marca_as_diferencas(self):
        pendente_id = self._simular_api(self._gerar())
        _p, _c, linhas = prechecking.detalhe(pendente_id, self.master["id"])
        diferentes = {chave for chave, _r, _a, _e, dif in linhas if dif}
        self.assertEqual(
            {"tipo_documento", "numero_documento", "pais_residencia"},
            diferentes,
        )

    def test_maiusculas_e_espacos_nao_contam_como_diferenca(self):
        pendente_id = self._simular_api(
            self._gerar(), nome="  ANA TESTE ")
        _p, _c, linhas = prechecking.detalhe(pendente_id, self.master["id"])
        self.assertFalse(dict((c, d) for c, _r, _a, _e, d in linhas)["nome"])

    def test_importar_atualiza_ficha_e_apaga_pendente(self):
        pendente_id = self._simular_api(self._gerar())
        prechecking.importar(pendente_id, self.master["id"])

        cliente = clientes.procurar(self.cliente["id"])
        self.assertEqual("Passaporte", cliente["tipo_documento"])
        self.assertEqual("FX123456", cliente["numero_documento"])
        self.assertEqual("Portugal", cliente["pais_residencia"])
        self.assertEqual(0, prechecking.contar_pendentes())

    def test_importar_regista_aviso_web_por_quem_importa(self):
        pendente_id = self._simular_api(self._gerar())
        prechecking.importar(pendente_id, self.master["id"])

        aviso = termos.historico(termos.TITULAR_CLIENTE,
                                 self.cliente["id"])[0]
        self.assertEqual(termos.PRIVACIDADE_HOSPEDE, aviso["documento"])
        self.assertEqual("web", aviso["suporte"])
        self.assertEqual("1.0", aviso["versao_texto"])
        self.assertEqual(self.master["id"], aviso["registado_por_id"])

    def test_aviso_fica_com_a_versao_que_o_hospede_viu(self):
        """Link emitido com a 1.0; a 2.0 é publicada antes de importar
        → regista-se a 1.0 (a que ele leu)."""
        link = self._gerar()
        pendente_id = self._simular_api(link)
        termos.publicar(termos.PRIVACIDADE_HOSPEDE, "2.0", "Texto 2.0.",
                        autor=self.master)

        prechecking.importar(pendente_id, self.master["id"])

        aviso = termos.historico(termos.TITULAR_CLIENTE,
                                 self.cliente["id"])[0]
        self.assertEqual("1.0", aviso["versao_texto"])

    def test_consentimento_guarda_email_e_data(self):
        pendente_id = self._simular_api(
            self._gerar(), email="ana@exemplo.pt", consente_comunicacoes=1)
        prechecking.importar(pendente_id, self.master["id"])

        cliente = clientes.procurar(self.cliente["id"])
        self.assertEqual("ana@exemplo.pt", cliente["email"])
        self.assertIsNotNone(cliente["consente_comunicacoes_em"])

    def test_sem_consentimento_nao_mexe_no_email(self):
        pendente_id = self._simular_api(self._gerar())
        prechecking.importar(pendente_id, self.master["id"])
        cliente = clientes.procurar(self.cliente["id"])
        self.assertIsNone(cliente["consente_comunicacoes_em"])

    def test_importar_com_dados_invalidos_nao_apaga_pendente(self):
        pendente_id = self._simular_api(self._gerar(),
                                        tipo_documento="Carta de condução")
        with self.assertRaises(ValueError):
            prechecking.importar(pendente_id, self.master["id"])
        self.assertEqual(1, prechecking.contar_pendentes())

    def test_rejeitar_nao_toca_na_ficha(self):
        pendente_id = self._simular_api(self._gerar())
        prechecking.rejeitar(pendente_id, self.master["id"])

        cliente = clientes.procurar(self.cliente["id"])
        self.assertEqual("X0000001", cliente["numero_documento"])
        self.assertEqual([], _sql_prechecking("SELECT id FROM pendentes"))
        self.assertEqual([], _sql_prechecking("SELECT 1 FROM tokens"))

    def test_staff_nao_ve_nem_importa(self):
        pendente_id = self._simular_api(self._gerar())
        staff = responsaveis.criar("Staff Teste", tipo_utilizador="Staff",
                                   autor=self.master)
        for funcao in (
            lambda: prechecking.listar_pendentes(staff["id"]),
            lambda: prechecking.importar(pendente_id, staff["id"]),
            lambda: prechecking.rejeitar(pendente_id, staff["id"]),
        ):
            with self.assertRaises(ValueError):
                funcao()
        self.assertEqual(1, prechecking.contar_pendentes())

    def test_importar_duas_vezes_recusa_a_segunda(self):
        pendente_id = self._simular_api(self._gerar())
        prechecking.importar(pendente_id, self.master["id"])
        with self.assertRaises(ValueError):
            prechecking.importar(pendente_id, self.master["id"])


# ---------------------------------------------------------------------
# 4. Servidor sem a caixa de entrada (ex.: MySQL local do PC)
# ---------------------------------------------------------------------


class TesteSemCaixaDeEntrada(BaseReservaTest):

    def setUp(self):
        super().setUp()
        config.DB_NAME_PRECHECKING = "base_que_nao_existe_xyz"

    def test_contagem_e_estados_nao_rebentam(self):
        self.assertEqual(0, prechecking.contar_pendentes())
        self.assertEqual(
            {self.reserva["id"]: prechecking.SEM_LINK},
            prechecking.estados([self.reserva["id"]]),
        )

    def test_gerar_link_da_mensagem_clara(self):
        with self.assertRaises(prechecking.PreCheckinIndisponivel):
            self._gerar()


# ---------------------------------------------------------------------
# 5. Decisão de 05/10/2026: aviso informativo validado fica validado
# ---------------------------------------------------------------------


class TesteAvisoValidadoFicaValidado(BaseReservaTest):

    def test_versao_nova_nao_volta_a_por_registar(self):
        termos.registar(termos.TITULAR_CLIENTE, self.cliente["id"],
                        termos.PRIVACIDADE_HOSPEDE,
                        registado_por_id=self.master["id"],
                        suporte="papel")
        termos.publicar(termos.PRIVACIDADE_HOSPEDE, "2.0", "Texto 2.0.",
                        autor=self.master)

        estado = termos.verificar(termos.TITULAR_CLIENTE,
                                  self.cliente["id"],
                                  termos.PRIVACIDADE_HOSPEDE)
        self.assertTrue(estado["em_dia"])
        self.assertEqual("1.0", estado["versao_aceite"])

    def test_confidencialidade_continua_a_pedir_a_versao_nova(self):
        termos.registar(termos.TITULAR_RESPONSAVEL, self.master["id"],
                        termos.CONFIDENCIALIDADE,
                        registado_por_id=self.master["id"])
        termos.publicar(termos.CONFIDENCIALIDADE, "2.0", "Texto 2.0.",
                        autor=self.master)

        estado = termos.verificar(termos.TITULAR_RESPONSAVEL,
                                  self.master["id"],
                                  termos.CONFIDENCIALIDADE)
        self.assertFalse(estado["em_dia"])
        self.assertTrue(estado["precisa_aceitar"])


# ---------------------------------------------------------------------
# 6. O esquema oficial e o script da VM não divergem
# ---------------------------------------------------------------------


def _normalizar(sql):
    return re.sub(r"\s+", " ", sql).strip().rstrip(";").strip()


class TesteEsquemaPreCheckin(unittest.TestCase):

    def test_esquema_igual_ao_do_instalar_prechecking(self):
        script = (RAIZ / "vm" / "instalar_prechecking.sh").read_text(
            encoding="utf-8")
        bloco = script.split("sql_root <<'EOF'", 1)[1].split("\nEOF", 1)[0]
        linhas = [linha.split("--", 1)[0].rstrip()
                  for linha in bloco.splitlines()]
        do_script = [
            _normalizar(i) for i in "\n".join(linhas).split(";")
            if "CREATE TABLE" in i
        ]
        do_esquema = [_normalizar(i)
                      for i in instrucoes_esquema_prechecking()]
        self.assertEqual(2, len(do_esquema))
        self.assertEqual(do_script, do_esquema)


if __name__ == "__main__":
    unittest.main()
