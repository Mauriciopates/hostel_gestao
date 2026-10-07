"""Testes da v1.11.2, ponto 8 — Configurações com "Gerir".

- Cada linha mostra o valor atual (só leitura) e um botão Gerir.
- O modal `GerirConfiguracaoModal` só deixa confirmar quando o valor
  mudou e é válido, mostra o resumo antes → depois e grava pelo
  `configuracoes.definir`.

As teclas são simuladas como no `TesteCampoData`: o texto entra com
`insert` e o `<KeyRelease>` é gerado no `_entry` interno, com o foco
no campo e numa janela visível.
"""

import sys
import tkinter
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest  # noqa: E402

import customtkinter as ctk  # noqa: E402

import configuracoes  # noqa: E402
import responsaveis  # noqa: E402
from gui import componentes, sessao  # noqa: E402
from gui.gui_configuracoes_modal import (  # noqa: E402
    GerirConfiguracaoModal,
    formatar_valor,
)


def _definicao(chave):
    return configuracoes.listar_definicoes(chave)[0]


class TesteFormatarValor(unittest.TestCase):

    def test_formatos(self):
        self.assertEqual(
            "30 dias",
            formatar_valor("operacao.aviso_previo_dias", 30, "int"),
        )
        self.assertEqual("Sim", formatar_valor("x", True, "bool"))
        self.assertEqual(
            "15 de jun", formatar_valor("x", (6, 15), "tupla_mes_dia")
        )


class TesteGerirModal(BaseMySQLTest):

    def setUp(self):
        super().setUp()
        configuracoes.garantir_seed()
        self.master = responsaveis.criar(
            "Master Teste", tipo_utilizador="Master"
        )
        sessao.definir_responsavel_ativo(self.master["id"])

        self.raiz = ctk.CTk()
        self.raiz.withdraw()
        self.janela = tkinter.Toplevel(self.raiz)
        self.janela.geometry("600x400+0+0")
        self.raiz.update()

        self.erro = mock.patch.object(componentes, "mostrar_erro")
        self.erro.start()
        self.gravados = []

    def tearDown(self):
        self.erro.stop()
        try:
            self.raiz.update()
            self.raiz.destroy()
        except Exception:
            pass
        super().tearDown()

    def _abrir(self, chave):
        modal = GerirConfiguracaoModal(
            self.janela,
            titulo="Teste",
            definicao=_definicao(chave),
            valor_atual=configuracoes.obter(chave),
            ao_gravar=self.gravados.append,
        )
        self.raiz.update()
        return modal

    def _escrever(self, modal, texto):
        modal.campo.delete(0, "end")
        modal.campo.insert(0, texto)
        modal.campo._entry.focus_force()
        self.raiz.update()
        modal.campo._entry.event_generate("<KeyRelease>", keysym="5")
        self.raiz.update()

    def test_sem_mudanca_nao_deixa_confirmar(self):
        modal = self._abrir("operacao.aviso_previo_dias")

        self.assertEqual("disabled", modal.botao_confirmar.cget("state"))

    def test_valor_novo_mostra_resumo_e_grava(self):
        chave = "operacao.aviso_previo_dias"
        antes = configuracoes.obter_int(chave)
        modal = self._abrir(chave)

        self._escrever(modal, str(antes + 10))

        self.assertEqual("normal", modal.botao_confirmar.cget("state"))
        self.assertIn("→", modal.rotulo_resumo.cget("text"))

        modal.botao_confirmar.invoke()
        self.raiz.update()

        self.assertEqual(antes + 10, configuracoes.obter(chave))
        self.assertEqual([antes + 10], self.gravados)

    def test_valor_fora_dos_limites_fica_bloqueado(self):
        modal = self._abrir("operacao.dia_vencimento")

        self._escrever(modal, "45")

        self.assertEqual("disabled", modal.botao_confirmar.cget("state"))
        self.assertIn("1 e 28", modal.rotulo_erro.cget("text"))
        self.assertEqual([], self.gravados)

    def test_sim_nao_grava(self):
        chave = "stock.rol_automatico_airbnb"
        antes = configuracoes.obter_bool(chave)
        modal = self._abrir(chave)

        novo = "Não" if antes else "Sim"
        modal.seletor_bool.set(novo)
        modal._ao_mudar_bool(novo)  # o CTkSegmentedButton.set não chama
        modal.botao_confirmar.invoke()
        self.raiz.update()

        self.assertEqual(not antes, configuracoes.obter(chave))


if __name__ == "__main__":
    unittest.main(verbosity=2)
