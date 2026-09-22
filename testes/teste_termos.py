"""Testes do módulo `termos` (v1.6.0).

Correm contra a base de dados de DESENVOLVIMENTO — o `.env` tem de
apontar para lá, nunca para produção.

Usam identificadores que não existem no sistema real
(`RES-TESTE`, `CLI-TESTE`) e apagam as próprias linhas no fim, para
não deixarem lixo na `avisos_privacidade`.

Pré-requisito: a PARTE 1 da migração aplicada e pelo menos uma
versão em vigor de cada documento.
"""

import unittest

import repositorio
import termos


RESPONSAVEL_TESTE = "RES-TESTE"
CLIENTE_TESTE = "CLI-TESTE"


def _limpar(titular_tipo, titular_id):
    """Apaga os registos de teste. Vai ao repositório em cru
    porque o `termos` não tem — nem deve ter — função de apagar:
    a tabela é um histórico.
    """
    conexao = repositorio.obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM avisos_privacidade "
            "WHERE titular_tipo = %s AND titular_id = %s",
            (titular_tipo, titular_id),
        )
        conexao.commit()
    finally:
        conexao.close()


class TesteVerificar(unittest.TestCase):
    """Estado de um titular perante o documento em vigor."""

    def setUp(self):
        _limpar(termos.TITULAR_RESPONSAVEL, RESPONSAVEL_TESTE)

    def tearDown(self):
        _limpar(termos.TITULAR_RESPONSAVEL, RESPONSAVEL_TESTE)

    def test_quem_nunca_aceitou_precisa_aceitar(self):
        estado = termos.verificar(
            termos.TITULAR_RESPONSAVEL,
            RESPONSAVEL_TESTE,
            termos.CONFIDENCIALIDADE,
        )

        self.assertIsNone(estado["versao_aceite"])
        self.assertTrue(estado["precisa_aceitar"])

    def test_depois_de_aceitar_deixa_de_precisar(self):
        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            RESPONSAVEL_TESTE,
            termos.CONFIDENCIALIDADE,
            registado_por_id=RESPONSAVEL_TESTE,
        )

        estado = termos.verificar(
            termos.TITULAR_RESPONSAVEL,
            RESPONSAVEL_TESTE,
            termos.CONFIDENCIALIDADE,
        )

        self.assertFalse(estado["precisa_aceitar"])
        self.assertEqual(
            estado["versao_aceite"], estado["texto"]["versao"]
        )
        self.assertIsNotNone(estado["data_aceite"])

    def test_informacao_ao_hospede_nunca_bloqueia(self):
        estado = termos.verificar(
            termos.TITULAR_CLIENTE,
            CLIENTE_TESTE,
            termos.PRIVACIDADE_HOSPEDE,
        )

        self.assertFalse(estado["precisa_aceitar"])


class TesteRegistar(unittest.TestCase):
    """Gravação do aviso e proteção do histórico."""

    def setUp(self):
        _limpar(termos.TITULAR_RESPONSAVEL, RESPONSAVEL_TESTE)

    def tearDown(self):
        _limpar(termos.TITULAR_RESPONSAVEL, RESPONSAVEL_TESTE)

    def test_devolve_a_versao_em_vigor(self):
        em_vigor = termos.texto_em_vigor(termos.CONFIDENCIALIDADE)

        versao = termos.registar(
            termos.TITULAR_RESPONSAVEL,
            RESPONSAVEL_TESTE,
            termos.CONFIDENCIALIDADE,
            registado_por_id=RESPONSAVEL_TESTE,
        )

        self.assertEqual(versao, em_vigor["versao"])

    def test_nao_duplica_a_mesma_versao(self):
        for _ in range(3):
            termos.registar(
                termos.TITULAR_RESPONSAVEL,
                RESPONSAVEL_TESTE,
                termos.CONFIDENCIALIDADE,
                registado_por_id=RESPONSAVEL_TESTE,
            )

        historico = termos.historico(
            termos.TITULAR_RESPONSAVEL, RESPONSAVEL_TESTE
        )

        self.assertEqual(len(historico), 1)

    def test_a_data_vem_do_servidor(self):
        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            RESPONSAVEL_TESTE,
            termos.CONFIDENCIALIDADE,
            registado_por_id=RESPONSAVEL_TESTE,
        )

        aviso = repositorio.obter_ultimo_aviso(
            termos.TITULAR_RESPONSAVEL,
            RESPONSAVEL_TESTE,
            termos.CONFIDENCIALIDADE,
        )

        if aviso is None:
            self.fail("O aviso não ficou gravado.")

        self.assertIsNotNone(aviso["data_entrega"])


class TesteErros(unittest.TestCase):
    """Argumentos fora dos ENUM saem como ValueError em português."""

    def test_titular_desconhecido(self):
        with self.assertRaises(ValueError):
            termos.verificar(
                "hospede", RESPONSAVEL_TESTE, termos.CONFIDENCIALIDADE
            )

    def test_titular_vazio(self):
        with self.assertRaises(ValueError):
            termos.verificar(
                termos.TITULAR_RESPONSAVEL, "", termos.CONFIDENCIALIDADE
            )

    def test_documento_desconhecido(self):
        with self.assertRaises(ValueError):
            termos.verificar(
                termos.TITULAR_RESPONSAVEL, RESPONSAVEL_TESTE, "inventado"
            )

    def test_suporte_desconhecido(self):
        with self.assertRaises(ValueError):
            termos.registar(
                termos.TITULAR_RESPONSAVEL,
                RESPONSAVEL_TESTE,
                termos.CONFIDENCIALIDADE,
                suporte="fax",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)