"""Testes do login da CLI (v1.8.0, decisões D9 e D10).

`cli.iniciar_sessao` segue a mesma ordem do GUI: login → troca da
password de fábrica → termo de confidencialidade. O teclado é
simulado (`ler_texto`, `getpass.getpass`, `confirmar`); a base é a de
teste (apoio_BD), com o Master de fábrica criado pelo
`sistema.garantir_master_inicial` e os textos da migração 0002.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest  # noqa: E402

import cli  # noqa: E402
import config  # noqa: E402
import migracoes  # noqa: E402
import sistema  # noqa: E402
import termos  # noqa: E402
import utilizadores  # noqa: E402

_NOVA = "NovaPassword123"


def _publicar_textos_demo():
    """Os três documentos v0.1, pela própria migração 0002."""
    lista = [
        m for m in migracoes.MIGRACOES if m[0] == "0002_textos_legais_demo"
    ]
    migracoes.aplicar_pendentes(lista)


class BaseLoginCliTest(BaseMySQLTest):

    def setUp(self):
        super().setUp()
        master = sistema.garantir_master_inicial()
        # Base de teste vazia → o Master é sempre criado. O assert
        # também diz ao pyright que daqui para a frente não é None.
        assert master is not None
        self.master = master
        # A sessão da CLI é um global do módulo — começa sempre vazia.
        cli._autor = None

    def tearDown(self):
        cli._autor = None
        super().tearDown()

    def _entrar(self, passwords, aceita=True):
        with patch("cli.ler_texto", return_value=config.UTILIZADOR_PADRAO), \
                patch("cli.getpass.getpass", side_effect=passwords), \
                patch("cli.confirmar", return_value=aceita), \
                patch("builtins.print"):
            return cli.iniciar_sessao()


class TestePasswordDeFabrica(BaseLoginCliTest):

    def test_troca_obrigatoria_e_depois_entra(self):
        entrou = self._entrar([config.PASSWORD_PADRAO, _NOVA, _NOVA])

        self.assertTrue(entrou)
        _, motivo = utilizadores.autenticar(config.UTILIZADOR_PADRAO, _NOVA)
        self.assertEqual(utilizadores.MOTIVO_OK, motivo)

    def test_confirmacao_diferente_volta_a_pedir(self):
        entrou = self._entrar(
            [config.PASSWORD_PADRAO, _NOVA, "outra-coisa", _NOVA, _NOVA]
        )

        self.assertTrue(entrou)

    def test_desistir_nao_entra_e_nao_muda_nada(self):
        entrou = self._entrar([config.PASSWORD_PADRAO, ""])

        self.assertFalse(entrou)
        _, motivo = utilizadores.autenticar(
            config.UTILIZADOR_PADRAO, config.PASSWORD_PADRAO
        )
        self.assertEqual(utilizadores.MOTIVO_OK, motivo)


class TesteTermoNaCli(BaseLoginCliTest):

    def test_sem_texto_publicado_entra(self):
        """Igual ao GUI: falta de texto é falha de configuração."""
        self.assertTrue(
            self._entrar([config.PASSWORD_PADRAO, _NOVA, _NOVA])
        )

    def test_aceitar_regista_e_entra(self):
        _publicar_textos_demo()

        entrou = self._entrar([config.PASSWORD_PADRAO, _NOVA, _NOVA])

        self.assertTrue(entrou)
        estado = termos.verificar(
            termos.TITULAR_RESPONSAVEL, self.master["id"],
            termos.CONFIDENCIALIDADE,
        )
        self.assertFalse(estado["precisa_aceitar"])
        self.assertEqual("0.1", estado["versao_aceite"])

    def test_recusar_nao_entra(self):
        _publicar_textos_demo()

        entrou = self._entrar(
            [config.PASSWORD_PADRAO, _NOVA, _NOVA], aceita=False
        )

        self.assertFalse(entrou)
        estado = termos.verificar(
            termos.TITULAR_RESPONSAVEL, self.master["id"],
            termos.CONFIDENCIALIDADE,
        )
        self.assertTrue(estado["precisa_aceitar"])

    def test_ordem_password_antes_do_termo(self):
        """Desistir da troca da password termina ANTES do termo — o
        termo nem chega a ser mostrado."""
        _publicar_textos_demo()

        with patch("cli.confirmar") as confirmar:
            with patch("cli.ler_texto",
                       return_value=config.UTILIZADOR_PADRAO), \
                    patch("cli.getpass.getpass",
                          side_effect=[config.PASSWORD_PADRAO, ""]), \
                    patch("builtins.print"):
                self.assertFalse(cli.iniciar_sessao())

        confirmar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
