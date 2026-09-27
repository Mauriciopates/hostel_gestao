"""Testes do `registo_logs.py` — a configuração central dos logs.

Não usam base de dados: são `unittest.TestCase` simples. O
`config.DIR_LOGS` é trocado por uma pasta temporária em cada teste,
por isso NUNCA escrevem no `hostel.log` verdadeiro.

O `registo_logs` mexe em estado GLOBAL do processo — os handlers da
raiz do logging, o nível da raiz, o `sys.excepthook` e a sua própria
flag `_configurado`. Cada teste guarda tudo isso no `setUp` e repõe no
`tearDown`: sem isto, o handler de um teste ficava ligado e os testes
seguintes da suite (os de todos os outros módulos) passavam a
escrever na pasta temporária, que entretanto já foi apagada.

NOTA WINDOWS: o ficheiro de log fica aberto pelo handler. Tem de ser
fechado (`handler.close()`) ANTES de apagar a pasta temporária, senão
o Windows recusa apagar um ficheiro em uso.
"""

import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config
import registo_logs


class TesteConfigurar(unittest.TestCase):

    def setUp(self):
        self._raiz = logging.getLogger()
        self._handlers_antes = list(self._raiz.handlers)
        self._nivel_antes = self._raiz.level
        self._excepthook_antes = sys.excepthook
        self._dir_logs_antes = config.DIR_LOGS

        self._pasta = tempfile.TemporaryDirectory()
        config.DIR_LOGS = Path(self._pasta.name)
        registo_logs._configurado = False

    def tearDown(self):
        for handler in list(self._raiz.handlers):
            if handler not in self._handlers_antes:
                self._raiz.removeHandler(handler)
                handler.close()

        self._raiz.setLevel(self._nivel_antes)
        sys.excepthook = self._excepthook_antes
        config.DIR_LOGS = self._dir_logs_antes
        registo_logs._configurado = False
        self._pasta.cleanup()

    def _handlers_novos(self):
        return [
            h for h in self._raiz.handlers if h not in self._handlers_antes
        ]

    def _ler_log(self):
        for handler in self._handlers_novos():
            handler.flush()
        return (config.DIR_LOGS / registo_logs.NOME_FICHEIRO).read_text(
            encoding="utf-8"
        )

    # -----------------------------------------------------------------

    def test_cria_o_ficheiro_na_pasta_de_logs(self):
        caminho = registo_logs.configurar("gui")
        self.assertEqual(caminho, config.DIR_LOGS / "hostel.log")
        self.assertTrue(caminho.exists())

    def test_regista_o_arranque_com_versao_e_interface(self):
        registo_logs.configurar("cli")
        texto = self._ler_log()
        self.assertIn("Aplicação iniciada", texto)
        self.assertIn(f"versão={config.VERSAO}", texto)
        self.assertIn("interface=cli", texto)

    def test_chamar_duas_vezes_nao_duplica(self):
        """Sem a proteção, cada chamada acrescentava um handler e cada
        linha passava a aparecer duas vezes no ficheiro."""
        registo_logs.configurar("gui")
        registo_logs.configurar("gui")

        self.assertEqual(len(self._handlers_novos()), 1)

        logging.getLogger("estoque").warning("linha única")
        self.assertEqual(self._ler_log().count("linha única"), 1)

    def test_acentos_e_travessoes_gravam_em_utf8(self):
        registo_logs.configurar("gui")
        logging.getLogger("termos").info("Publicação — versão ç ã")
        self.assertIn("Publicação — versão ç ã", self._ler_log())

    def test_bibliotecas_de_terceiros_so_passam_avisos(self):
        registo_logs.configurar("gui")
        logging.getLogger("mysql.connector").info("ruído de biblioteca")
        logging.getLogger("mysql.connector").warning("aviso de biblioteca")
        texto = self._ler_log()
        self.assertNotIn("ruído de biblioteca", texto)
        self.assertIn("aviso de biblioteca", texto)

    def test_crash_fica_registado_com_traceback(self):
        registo_logs.configurar("gui")

        erro = RuntimeError("crash de teste")
        try:
            raise erro
        except RuntimeError:
            pass

        # O comportamento normal do Python (imprimir no terminal) é
        # substituído aqui só para não sujar a saída dos testes.
        with patch.object(sys, "__excepthook__"):
            sys.excepthook(RuntimeError, erro, erro.__traceback__)

        texto = self._ler_log()
        self.assertIn("CRITICAL", texto)
        self.assertIn("Exceção não tratada", texto)
        self.assertIn("RuntimeError: crash de teste", texto)

    def test_ctrl_c_nao_e_registado_como_crash(self):
        registo_logs.configurar("cli")

        with patch.object(sys, "__excepthook__"):
            sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)

        self.assertNotIn("Exceção não tratada", self._ler_log())


if __name__ == "__main__":
    unittest.main()
