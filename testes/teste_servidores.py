"""Testes do servidores.py — vigia do túnel SSH (v1.8.2).

`garantir_tunel` é chamado antes de cada ligação ao MySQL: se o ssh
aberto pela aplicação morreu a meio da sessão, regista no log e
reabre o túnel. Os processos ssh são SIMULADOS (unittest.mock): os
testes não abrem túnel nenhum nem precisam de uma VM.

`e_falha_de_ligacao` decide se um erro é "perdi a ligação ao
servidor" (aviso próprio na interface) ou um bug.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

PASTA_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(PASTA_SRC))

import mysql.connector  # noqa: E402

import servidores  # noqa: E402

PORTA = 3399

SERVIDOR_COM_TUNEL = {
    "nome": "teste",
    "tunel": {
        "porta_local": PORTA,
        "ssh_host": "192.0.2.1",
        "ssh_utilizador": "teste",
        "ssh_porta": 22,
        "porta_mysql": 6213,
    },
}


def _processo(vivo, codigo=255, mensagem=b""):
    """Um `subprocess.Popen` falso: `poll()` devolve None se vivo."""
    processo = mock.Mock()
    processo.poll.return_value = None if vivo else codigo
    processo.returncode = None if vivo else codigo
    processo.stderr.read.return_value = mensagem
    return processo


class TesteGarantirTunel(unittest.TestCase):

    def setUp(self):
        servidores._tuneis.pop(PORTA, None)

    def tearDown(self):
        servidores._tuneis.pop(PORTA, None)

    def test_sem_servidor_nao_faz_nada(self):
        with mock.patch.object(servidores, "abrir_tunel") as abrir:
            servidores.garantir_tunel(None)
        abrir.assert_not_called()

    def test_ligacao_direta_nao_faz_nada(self):
        with mock.patch.object(servidores, "abrir_tunel") as abrir:
            servidores.garantir_tunel({"nome": "local", "tunel": None})
        abrir.assert_not_called()

    def test_ssh_vivo_nao_reabre(self):
        servidores._tuneis[PORTA] = _processo(vivo=True)
        with mock.patch.object(servidores, "abrir_tunel") as abrir:
            servidores.garantir_tunel(SERVIDOR_COM_TUNEL)
        abrir.assert_not_called()

    def test_ssh_morto_regista_e_reabre(self):
        servidores._tuneis[PORTA] = _processo(
            vivo=False, mensagem=b"Timeout, server not responding."
        )
        with mock.patch.object(servidores, "abrir_tunel") as abrir, \
                self.assertLogs("servidores", level="WARNING") as registo:
            servidores.garantir_tunel(SERVIDOR_COM_TUNEL)

        abrir.assert_called_once_with(SERVIDOR_COM_TUNEL)
        self.assertNotIn(PORTA, servidores._tuneis)
        self.assertIn("caiu", registo.output[0])
        self.assertIn("Timeout, server not responding.", registo.output[0])

    def test_sem_processo_nosso_delega_em_abrir_tunel(self):
        """Túnel aberto por outra cópia ou à mão: quem decide se a
        porta já serve é o `abrir_tunel` (reaproveita-a)."""
        with mock.patch.object(servidores, "abrir_tunel") as abrir:
            servidores.garantir_tunel(SERVIDOR_COM_TUNEL)
        abrir.assert_called_once_with(SERVIDOR_COM_TUNEL)

    def test_falha_a_reabrir_chega_a_quem_chamou(self):
        servidores._tuneis[PORTA] = _processo(vivo=False)
        erro = servidores.ErroServidor("A máquina não respondeu.")
        with mock.patch.object(
            servidores, "abrir_tunel", side_effect=erro
        ), self.assertLogs("servidores", level="WARNING"):
            with self.assertRaises(servidores.ErroServidor):
                servidores.garantir_tunel(SERVIDOR_COM_TUNEL)


class TesteEFalhaDeLigacao(unittest.TestCase):

    def test_erro_do_servidor_e_falha_de_ligacao(self):
        self.assertTrue(
            servidores.e_falha_de_ligacao(servidores.ErroServidor("x"))
        )

    def test_codigos_de_ligacao_do_mysql(self):
        for codigo in (2003, 2005, 2006, 2013, 2055):
            with self.subTest(codigo=codigo):
                erro = mysql.connector.errors.InterfaceError(errno=codigo)
                self.assertTrue(servidores.e_falha_de_ligacao(erro))

    def test_erro_de_sql_nao_e_falha_de_ligacao(self):
        erro = mysql.connector.errors.ProgrammingError(errno=1064)
        self.assertFalse(servidores.e_falha_de_ligacao(erro))

    def test_erro_do_python_nao_e_falha_de_ligacao(self):
        self.assertFalse(servidores.e_falha_de_ligacao(ValueError("x")))


if __name__ == "__main__":
    unittest.main()
