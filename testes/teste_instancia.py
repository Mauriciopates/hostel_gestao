"""Testes do instancia.py — uma só cópia da aplicação (v1.8.1).

A "outra cópia" é sempre um processo Python à parte (subprocess): no
Windows, o mesmo processo pode pedir o mesmo mutex as vezes que
quiser, por isso só um segundo processo prova a recusa. Cada teste
usa um nome de trinco próprio, para não chocar com uma aplicação
verdadeira aberta no PC enquanto os testes correm.
"""

import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

PASTA_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(PASTA_SRC))

import instancia  # noqa: E402


def _outra_copia(nome, espera_s=0):
    """Arranca um processo que tenta o trinco e escreve True/False."""
    codigo = (
        "import sys; sys.path.insert(0, sys.argv[1]); import instancia; "
        "print(instancia.adquirir(float(sys.argv[3]), sys.argv[2]))"
    )
    return subprocess.Popen(
        [sys.executable, "-c", codigo, str(PASTA_SRC), nome,
         str(espera_s)],
        stdout=subprocess.PIPE, text=True,
    )


def _resposta(processo):
    saida, _ = processo.communicate(timeout=30)
    return saida.strip()


class BaseInstanciaTest(unittest.TestCase):

    def setUp(self):
        instancia.libertar()
        self.nome = f"HostelGestao_teste_{os.getpid()}_{id(self)}"

    def tearDown(self):
        instancia.libertar()


class TesteAdquirir(BaseInstanciaTest):

    def teste_primeira_copia_fica_com_o_trinco(self):
        self.assertTrue(instancia.adquirir(0, self.nome))

    def teste_pedir_de_novo_no_mesmo_processo_devolve_true(self):
        instancia.adquirir(0, self.nome)
        self.assertTrue(instancia.adquirir(0, self.nome))

    def teste_segunda_copia_e_recusada(self):
        instancia.adquirir(0, self.nome)
        self.assertEqual(_resposta(_outra_copia(self.nome)), "False")

    def teste_depois_de_libertar_outra_copia_entra(self):
        instancia.adquirir(0, self.nome)
        instancia.libertar()
        self.assertEqual(_resposta(_outra_copia(self.nome)), "True")

    def teste_sem_ninguem_outra_copia_entra(self):
        self.assertEqual(_resposta(_outra_copia(self.nome)), "True")

    def teste_trinco_largado_quando_o_processo_termina(self):
        # A outra cópia fica com o trinco e termina sem libertar: o
        # sistema operativo larga-o (no Windows, mutex "abandonado").
        self.assertEqual(_resposta(_outra_copia(self.nome)), "True")
        self.assertTrue(instancia.adquirir(0, self.nome))

    def teste_reinicio_espera_que_a_anterior_feche(self):
        instancia.adquirir(0, self.nome)
        nova = _outra_copia(self.nome, espera_s=10)
        time.sleep(1.5)
        instancia.libertar()
        self.assertEqual(_resposta(nova), "True")

    def teste_espera_acaba_e_recusa(self):
        instancia.adquirir(0, self.nome)
        inicio = time.monotonic()
        self.assertEqual(_resposta(_outra_copia(self.nome, 1)), "False")
        self.assertGreaterEqual(time.monotonic() - inicio, 1)


class TesteEsperaPedida(unittest.TestCase):

    def tearDown(self):
        os.environ.pop(instancia.VARIAVEL_REINICIO, None)

    def teste_arranque_normal_nao_espera(self):
        os.environ.pop(instancia.VARIAVEL_REINICIO, None)
        self.assertEqual(instancia.espera_pedida(), 0)

    def teste_reinicio_espera_e_tira_a_variavel(self):
        os.environ[instancia.VARIAVEL_REINICIO] = "1"
        self.assertEqual(instancia.espera_pedida(),
                         instancia.ESPERA_REINICIO_S)
        self.assertNotIn(instancia.VARIAVEL_REINICIO, os.environ)


if __name__ == "__main__":
    unittest.main()
