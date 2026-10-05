"""Testes de interface do pré check-in (F5, 05/10/2026).

Usam a mesma preparação dos testes de negócio (`teste_prechecking`:
reserva Airbnb, bases de teste) e abrem os ecrãs com a raiz escondida.
A leitura em segundo plano é trocada por uma chamada direta, para o
teste não depender de threads nem de temporizadores.
"""

import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes import teste_prechecking as base  # noqa: E402

import customtkinter as ctk  # noqa: E402

import clientes  # noqa: E402
import contratos  # noqa: E402
import prechecking  # noqa: E402
from gui import componentes, gui_prechecking, sessao  # noqa: E402
from gui.contratos import gui_cnt_airbnb_lista  # noqa: E402


def _sincrono(master, trabalho, ao_terminar, texto="", ao_falhar=None):
    ao_terminar(trabalho())


def _textos(widget):
    """Todos os textos visíveis (labels, botões) dentro de um widget."""
    textos = []
    for filho in widget.winfo_children():
        try:
            texto = filho.cget("text")
        except (ValueError, Exception):
            texto = None
        if isinstance(texto, str) and texto.strip():
            textos.append(texto.strip())
        textos.extend(_textos(filho))
    return textos


class _TelaFalsa(ctk.CTkFrame):
    """Ecrã de onde os modais são abertos (precisa de `_recarregar`)."""

    _recarregar: Any = None


class _BaseGui(base.BaseReservaTest):

    def setUp(self):
        super().setUp()
        sessao.definir_responsavel_ativo(self.master["id"])
        self.raiz = ctk.CTk()
        self.raiz.withdraw()
        self.tela = _TelaFalsa(self.raiz)
        self.tela._recarregar = mock.Mock()

        self.patches = [
            mock.patch.object(componentes, "mostrar_sucesso"),
            mock.patch.object(componentes, "mostrar_erro"),
            mock.patch.object(componentes, "confirmar", return_value=True),
            mock.patch.object(componentes, "carregar_em_segundo_plano",
                              _sincrono),
        ]
        (self.mock_sucesso, self.mock_erro, self.mock_confirmar,
         _) = [p.start() for p in self.patches]

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        try:
            self.raiz.update()
            self.raiz.destroy()
        except Exception:
            pass
        super().tearDown()


class TesteGerarLinkModal(_BaseGui):

    def test_mostra_dados_da_reserva(self):
        modal = gui_prechecking.GerarLinkModal(self.tela, self.reserva)
        textos = _textos(modal)
        self.assertIn("Unidade Airbnb Teste", textos)
        self.assertIn("Rua de Teste, 1, Porto", textos)
        self.assertEqual("15:00", modal.campo_checkin.get())
        self.assertEqual("11:00", modal.campo_checkout.get())

    def test_gerar_mostra_o_link_e_grava_token(self):
        modal = gui_prechecking.GerarLinkModal(self.tela, self.reserva)
        modal.area_regras.definir("Sem festas.")
        modal._gerar()

        self.mock_erro.assert_not_called()
        self.assertTrue(modal.caixa_link.winfo_ismapped()
                        or modal.caixa_link.winfo_manager() == "pack")
        self.assertTrue(any(t.startswith("✓ Link gerado")
                            for t in _textos(modal)))
        self.assertEqual("Gerar outro link", modal.botao_gerar.cget("text"))
        self.assertEqual(prechecking.LINK_ENVIADO, self._estado())
        self.tela._recarregar.assert_called()

    def test_hora_invalida_mostra_erro(self):
        modal = gui_prechecking.GerarLinkModal(self.tela, self.reserva)
        modal.campo_checkin.delete(0, "end")
        modal.campo_checkin.insert(0, "15h")
        modal._gerar()
        self.mock_erro.assert_called_once()
        self.assertEqual(prechecking.SEM_LINK, self._estado())

    def test_reserva_cancelada_nao_abre(self):
        contratos.cancelar_airbnb(self.reserva["id"])
        resultado = gui_prechecking.abrir(
            gui_prechecking.GerarLinkModal, self.tela, self.reserva)
        self.assertIsNone(resultado)
        self.mock_erro.assert_called_once()


class TesteListaEValidar(_BaseGui):

    def test_lista_mostra_o_pendente(self):
        self._simular_api(self._gerar())
        ecra = gui_prechecking.ListaPreCheckins(self.raiz, mock.Mock())
        textos = _textos(ecra.tabela)
        self.assertIn("Ana Teste", textos)
        self.assertIn(self.reserva["id"], textos)
        self.assertIn("3 campos", textos)

    def test_lista_vazia(self):
        ecra = gui_prechecking.ListaPreCheckins(self.raiz, mock.Mock())
        self.assertIn("Não há pré check-ins por validar.",
                      _textos(ecra.tabela))

    def test_validar_mostra_diferencas_e_importa(self):
        pendente_id = self._simular_api(self._gerar())
        modal = gui_prechecking.ValidarPreCheckinModal(self.tela,
                                                       pendente_id)
        textos = _textos(modal)
        self.assertIn("FX123456", textos)
        self.assertIn("X0000001", textos)

        modal._importar()

        self.mock_sucesso.assert_called_once()
        self.assertEqual(
            "FX123456",
            clientes.procurar(self.cliente["id"])["numero_documento"])
        self.assertEqual(0, prechecking.contar_pendentes())

    def test_rejeitar_pede_confirmacao(self):
        pendente_id = self._simular_api(self._gerar())
        modal = gui_prechecking.ValidarPreCheckinModal(self.tela,
                                                       pendente_id)
        self.mock_confirmar.return_value = False
        modal._rejeitar()
        self.assertEqual(1, prechecking.contar_pendentes())

        self.mock_confirmar.return_value = True
        modal._rejeitar()
        self.assertEqual(0, prechecking.contar_pendentes())
        self.assertEqual(
            "X0000001",
            clientes.procurar(self.cliente["id"])["numero_documento"])

    def test_pendente_ja_tratado_nao_abre_janela(self):
        pendente_id = self._simular_api(self._gerar())
        prechecking.rejeitar(pendente_id, self.master["id"])
        resultado = gui_prechecking.abrir(
            gui_prechecking.ValidarPreCheckinModal, self.tela, pendente_id)
        self.assertIsNone(resultado)
        self.mock_erro.assert_called_once()


class TesteListaReservas(_BaseGui):

    def test_coluna_pre_checkin_mostra_o_estado(self):
        self._gerar()
        ecra = gui_cnt_airbnb_lista.ListaReservasAirbnb(
            self.raiz, mock.Mock())
        self.assertIn("Link enviado", _textos(ecra.tabela))


class TesteContadorDoMenu(_BaseGui):

    def test_pilula_aparece_e_some(self):
        barra = componentes.BarraLateral(
            self.raiz, mock.Mock(), [{
                "tipo": "item", "texto": "Pré check-ins",
                "ecra": gui_prechecking.ListaPreCheckins,
                "contador": prechecking.contar_pendentes,
            }],
        )
        etiqueta, _funcao = barra._contadores[0]
        self.assertEqual("", etiqueta.winfo_manager())

        pendente_id = self._simular_api(self._gerar())
        barra.atualizar_contadores()
        self.assertEqual("place", etiqueta.winfo_manager())
        self.assertEqual("1", etiqueta.cget("text").strip())

        prechecking.rejeitar(pendente_id, self.master["id"])
        barra.atualizar_contadores()
        self.assertEqual("", etiqueta.winfo_manager())

    def test_erro_na_contagem_nao_rebenta(self):
        def rebenta():
            raise RuntimeError("sem base")

        barra = componentes.BarraLateral(
            self.raiz, mock.Mock(), [{
                "tipo": "item", "texto": "X",
                "ecra": gui_prechecking.ListaPreCheckins,
                "contador": rebenta,
            }],
        )
        self.assertEqual("", barra._contadores[0][0].winfo_manager())


if __name__ == "__main__":
    unittest.main()
