"""Testes da janela de arranque (v1.10.0).

- `gui/janela_arranque.py`: os passos ficam feitos com o tempo, o
  resultado do trabalho volta à thread principal, uma exceção no
  trabalho é lançada de novo, e o aviso amarelo só aparece na cópia
  de segurança quando ela demora.
- `main_gui._ligar`: com a base pronta segue com a mesma janela; com
  o servidor em baixo entrega o diagnóstico ao plano B (sem testar
  segunda vez).
- `gui_servidores._diagnosticar_e_oferecer`: usa o diagnóstico que
  recebe em vez de voltar a ligar.
- `instancia.trazer_para_frente`: sem janela com aquele título,
  devolve False sem rebentar.

Não precisa de base de dados: o servidor e o MySQL são mocks.
"""

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import instalacao  # noqa: E402
import instancia  # noqa: E402
import main_gui  # noqa: E402
from gui import gui_servidores, janela_arranque  # noqa: E402
from gui.janela_arranque import JanelaArranque  # noqa: E402


def _texto(rotulo):
    return rotulo.cget("text")


class TesteFuncoes(unittest.TestCase):
    def test_texto_tempo_arredonda_para_baixo(self):
        self.assertEqual(janela_arranque.texto_tempo(3.7), "3 s")
        self.assertEqual(janela_arranque.texto_tempo(0), "0 s")
        self.assertEqual(janela_arranque.texto_tempo(-1), "0 s")

    def test_aviso_so_na_copia_e_so_quando_demora(self):
        limite = janela_arranque.AVISO_COPIA_APOS_S
        copia = janela_arranque.COPIA
        ligar = janela_arranque.LIGAR
        self.assertFalse(janela_arranque.mostrar_aviso_copia(copia, 0.5))
        self.assertTrue(janela_arranque.mostrar_aviso_copia(copia, limite))
        self.assertFalse(janela_arranque.mostrar_aviso_copia(ligar, 99))

    def test_cinco_passos(self):
        self.assertEqual(len(janela_arranque.PASSOS), 5)
        self.assertEqual(janela_arranque.ABRIR, 4)


class TesteJanela(unittest.TestCase):
    def setUp(self):
        self.janela = JanelaArranque()

    def tearDown(self):
        self.janela.fechar()

    def test_correr_devolve_o_resultado_e_marca_feito(self):
        valor = self.janela.correr(janela_arranque.LIGAR, lambda: 42)
        self.assertEqual(valor, 42)
        marca, _, tempo = self.janela._linhas[janela_arranque.LIGAR]
        self.assertEqual(_texto(marca), "✓")
        self.assertEqual(_texto(tempo), "0 s")

    def test_correr_conta_os_segundos(self):
        self.janela.correr(janela_arranque.LIGAR, lambda: time.sleep(1.1))
        _, _, tempo = self.janela._linhas[janela_arranque.LIGAR]
        self.assertEqual(_texto(tempo), "1 s")

    def test_trabalho_corre_noutra_thread(self):
        import threading
        principal = threading.get_ident()
        fio = self.janela.correr(janela_arranque.COPIA, threading.get_ident)
        self.assertNotEqual(fio, principal)

    def test_excecao_do_trabalho_e_lancada_aqui(self):
        def falha():
            raise ValueError("migração 7 falhou")

        with self.assertRaisesRegex(ValueError, "migração 7"):
            self.janela.correr(janela_arranque.MIGRAR, falha)

    def test_passos_seguintes_ficam_pendentes(self):
        self.janela.correr(janela_arranque.PREPARAR, lambda: None)
        marca, _, _ = self.janela._linhas[janela_arranque.ABRIR]
        self.assertEqual(_texto(marca), "○")

    def test_aviso_aparece_quando_a_copia_demora(self):
        with mock.patch.object(janela_arranque, "AVISO_COPIA_APOS_S", 0.1):
            self.janela.correr(janela_arranque.COPIA,
                               lambda: time.sleep(0.4))
        self.assertIsNotNone(self.janela._aviso)

    def test_sem_aviso_quando_a_copia_e_rapida(self):
        self.janela.correr(janela_arranque.COPIA, lambda: None)
        self.assertIsNone(self.janela._aviso)

    def test_correr_aqui_corre_na_thread_principal(self):
        import threading
        principal = threading.get_ident()
        fio = self.janela.correr_aqui(janela_arranque.PREPARAR,
                                      threading.get_ident)
        self.assertEqual(fio, principal)

    def test_fechar_duas_vezes_nao_rebenta(self):
        self.janela.fechar()
        self.janela.fechar()


class TesteJaFeitos(unittest.TestCase):
    def test_reabrir_depois_do_plano_b(self):
        janela = JanelaArranque(ja_feitos=janela_arranque.COPIA)
        try:
            marcas = [_texto(m) for m, _, _ in janela._linhas]
            self.assertEqual(marcas, ["✓", "✓", "○", "○", "○"])
        finally:
            janela.fechar()


class TesteLigar(unittest.TestCase):
    """main_gui._ligar com o servidor e o MySQL simulados."""

    SERVIDOR = {"nome": "VM", "base": "hostel_gestao"}

    def setUp(self):
        self.janela = mock.Mock()
        self.janela.correr.side_effect = lambda _indice, trabalho: trabalho()
        patches = [
            mock.patch("servidores.servidor_ativo",
                       return_value=("vm", self.SERVIDOR)),
            mock.patch("servidores.obter_password", return_value="x"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_base_pronta_segue_com_a_mesma_janela(self):
        pronta = (instalacao.PRONTA, "ok", [])
        with mock.patch("instalacao.diagnosticar", return_value=pronta), \
                mock.patch.object(gui_servidores,
                                  "garantir_ligacao") as plano_b:
            resultado = main_gui._ligar(self.janela)
        self.assertIs(resultado, self.janela)
        self.janela.fechar.assert_not_called()
        plano_b.assert_not_called()

    def test_servidor_em_baixo_entrega_o_diagnostico_ao_plano_b(self):
        erro = (instalacao.ERRO, "timed out", [])
        with mock.patch("instalacao.diagnosticar", return_value=erro), \
                mock.patch.object(gui_servidores, "garantir_ligacao",
                                  return_value=False) as plano_b:
            resultado = main_gui._ligar(self.janela)
        self.assertIsNone(resultado)
        self.janela.fechar.assert_called_once()
        plano_b.assert_called_once_with(erro)

    def test_sem_servidor_vai_direto_ao_plano_b(self):
        with mock.patch("servidores.servidor_ativo",
                        return_value=(None, None)), \
                mock.patch("instalacao.diagnosticar") as diagnosticar, \
                mock.patch.object(gui_servidores, "garantir_ligacao",
                                  return_value=False) as plano_b:
            main_gui._ligar(self.janela)
        diagnosticar.assert_not_called()
        plano_b.assert_called_once_with(None)


class TesteDiagnosticoReaproveitado(unittest.TestCase):
    def test_usa_o_diagnostico_recebido(self):
        pronta = (instalacao.PRONTA, "ok", [])
        with mock.patch("instalacao.diagnosticar") as diagnosticar:
            ok, texto = gui_servidores._diagnosticar_e_oferecer(
                {"base": "b"}, "x", pronta)
        diagnosticar.assert_not_called()
        self.assertTrue(ok)
        self.assertEqual(texto, "ok")

    def test_sem_diagnostico_testa(self):
        pronta = (instalacao.PRONTA, "ok", [])
        with mock.patch("instalacao.diagnosticar",
                        return_value=pronta) as diagnosticar:
            gui_servidores._diagnosticar_e_oferecer({"base": "b"}, "x")
        diagnosticar.assert_called_once()


class TesteTrazerParaFrente(unittest.TestCase):
    def test_sem_janela_devolve_false(self):
        self.assertFalse(
            instancia.trazer_para_frente(("Janela que não existe 4f9c",))
        )


if __name__ == "__main__":
    unittest.main()
