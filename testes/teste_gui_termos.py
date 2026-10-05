"""Testes da v1.9.0, bloco D — avisos de privacidade nos ecrãs.

- Novo Cliente: o Guardar fica trancado até se confirmar a entrega
  do aviso ao hóspede; ao guardar, regista-se o aviso com o suporte
  escolhido (Papel/Contrato).
- Gerir cliente: a ação "Aviso de privacidade" mostra o estado e o
  modal regista para clientes que já existiam.
- Definir credencial: o aviso de privacidade do colaborador é só
  informação (sem caixa) e fica registado como entregue ("sistema").

Os avisos do sistema (mostrar_sucesso / mostrar_erro) são
substituídos por mocks — uma messagebox real pararia o teste.
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseTermosTest  # noqa: E402

import customtkinter as ctk  # noqa: E402

import clientes  # noqa: E402
import responsaveis  # noqa: E402
import termos  # noqa: E402
from gui import componentes, gui_clientes, gui_responsaveis  # noqa: E402
from gui import sessao  # noqa: E402


def _cliente_antigo():
    """Cliente criado pelo negócio, sem aviso — como os de antes da
    v1.9.0."""
    return clientes.criar(
        "Hóspede Antigo",
        "Passaporte",
        "Z7654321",
        "airbnb",
        nacionalidade="Brasileira",
        pais_emissor_documento="Brasil",
        pais_residencia="Brasil",
        data_nascimento=date(1990, 1, 1),
    )


class _BaseGui(BaseTermosTest):
    def setUp(self):
        super().setUp()
        sessao.definir_responsavel_ativo(self.master["id"])
        self.raiz = ctk.CTk()
        self.raiz.withdraw()
        self.tela = ctk.CTkFrame(self.raiz)
        self.tela._recarregar = mock.Mock()
        self.tela._autor = mock.Mock(return_value=self.master)

        self.sucesso = mock.patch.object(componentes, "mostrar_sucesso")
        self.erro = mock.patch.object(componentes, "mostrar_erro")
        self.mock_sucesso = self.sucesso.start()
        self.mock_erro = self.erro.start()

    def tearDown(self):
        self.sucesso.stop()
        self.erro.stop()
        try:
            self.raiz.update()
            self.raiz.destroy()
        except Exception:
            pass
        super().tearDown()

    def _historico(self, titular_tipo, titular_id, tipo):
        return [
            aviso
            for aviso in termos.historico(titular_tipo, titular_id)
            if aviso["documento"] == tipo
        ]


class TesteNovoClienteAviso(_BaseGui):

    def _preencher_airbnb(self, modal):
        modal.campo_nome.insert(0, "Hóspede Novo")
        modal.campo_nacionalidade.insert(0, "Brasileira")
        modal.campo_data_nascimento.insert(0, "01/01/1990")
        modal.combo_tipo_documento.set("Passaporte")
        modal.campo_numero_documento.insert(0, "N1234567")
        modal.campo_pais_emissor.insert(0, "Brasil")
        modal.campo_pais_residencia.insert(0, "Brasil")

    def test_guardar_trancado_ate_confirmar(self):
        modal = gui_clientes.NovoClienteAirbnbModal(self.tela)
        self.assertEqual(modal.botao_guardar.cget("state"), "disabled")

        modal._bloco_aviso.aceite.set(True)
        modal._ao_mudar_aviso()
        self.assertEqual(modal.botao_guardar.cget("state"), "normal")

    def test_sem_confirmar_nao_grava(self):
        modal = gui_clientes.NovoClienteAirbnbModal(self.tela)
        self._preencher_airbnb(modal)

        modal._guardar()

        self.assertEqual(clientes.listar(), [])
        self.mock_erro.assert_called_once()

    def test_guarda_cliente_e_regista_aviso_com_suporte(self):
        modal = gui_clientes.NovoClienteAirbnbModal(self.tela)
        self._preencher_airbnb(modal)
        modal._bloco_aviso.aceite.set(True)
        modal._ao_mudar_aviso()

        modal._guardar()

        [cliente] = clientes.listar()
        [aviso] = self._historico(
            termos.TITULAR_CLIENTE, cliente["id"], termos.PRIVACIDADE_HOSPEDE
        )
        self.assertEqual(aviso["suporte"], "papel")
        self.assertEqual(aviso["registado_por_id"], self.master["id"])
        self.assertIn("Aviso de privacidade registado",
                      self.mock_sucesso.call_args[0][0])

    def test_modal_mensal_tambem_tem_aviso(self):
        modal = gui_clientes.NovoClienteMensalModal(self.tela)
        self.assertIsNotNone(modal._bloco_aviso)
        self.assertEqual(modal.botao_guardar.cget("state"), "disabled")


class TesteAvisoClienteExistente(_BaseGui):

    def _texto_botao_aviso(self, cliente):
        modal = gui_clientes._AcoesClienteModal(self.tela, cliente)
        textos = [
            filho.cget("text")
            for filho in modal.winfo_children()
            if isinstance(filho, ctk.CTkButton)
        ]
        modal.destroy()
        return [t for t in textos if t.startswith("Aviso de privacidade")]

    def test_gerir_mostra_por_registar_e_depois_em_dia(self):
        cliente = _cliente_antigo()
        self.assertEqual(
            self._texto_botao_aviso(cliente),
            ["Aviso de privacidade · por registar"],
        )

        modal = gui_clientes.AvisoPrivacidadeClienteModal(self.tela, cliente)
        self.assertEqual(modal.botao_registar.cget("state"), "disabled")
        modal.bloco.aceite.set(True)
        modal._ao_mudar()
        modal._registar()

        self.assertEqual(
            self._texto_botao_aviso(cliente),
            ["Aviso de privacidade  ✓ v1.0"],
        )

    def test_regista_suporte_contrato(self):
        cliente = _cliente_antigo()
        modal = gui_clientes.AvisoPrivacidadeClienteModal(self.tela, cliente)
        modal.bloco.aceite.set(True)
        # O seletor do suporte é o SeletorVistas dentro do bloco.
        seletores = [
            neto
            for filho in modal.bloco.winfo_children()
            for neto in filho.winfo_children()
            if isinstance(neto, componentes.SeletorVistas)
        ]
        seletores[0].set("Contrato")
        modal._registar()

        [aviso] = self._historico(
            termos.TITULAR_CLIENTE, cliente["id"], termos.PRIVACIDADE_HOSPEDE
        )
        self.assertEqual(aviso["suporte"], "contrato")

    def test_anonimizado_nao_tem_acao(self):
        cliente = _cliente_antigo()
        clientes.anonimizar(cliente["id"], self.master["id"], date.today())
        cliente = clientes.procurar(cliente["id"])
        self.assertEqual(self._texto_botao_aviso(cliente), [])


class TesteDefinirCredencialAviso(_BaseGui):

    def test_regista_privacidade_colaborador_como_sistema(self):
        staff = responsaveis.criar("Rui Teste", tipo_utilizador="Staff")
        modal = gui_responsaveis.DefinirCredencialModal(self.tela, staff)
        modal.bloco_termo.aceite.set(True)
        modal._ao_mudar_termo()
        modal.campo_username.insert(0, "rui")
        modal.campo_password.insert(0, "RuiTeste2026")
        modal.campo_confirmar.insert(0, "RuiTeste2026")

        modal._gravar()

        self.mock_erro.assert_not_called()
        [aviso] = self._historico(
            termos.TITULAR_RESPONSAVEL,
            staff["id"],
            termos.PRIVACIDADE_COLABORADOR,
        )
        self.assertEqual(aviso["suporte"], "sistema")
        self.assertEqual(
            len(self._historico(
                termos.TITULAR_RESPONSAVEL,
                staff["id"],
                termos.CONFIDENCIALIDADE,
            )),
            1,
        )


if __name__ == "__main__":
    unittest.main()
