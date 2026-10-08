"""Testes da v1.12.0 — atribuir unidade a despesas pagas sem unidade.

Cobre os dois modais novos (`DespesasGeraisModal` e
`AtribuirUnidadeModal`), o detalhe enriquecido da despesa e os
contadores do menu lateral. A regra de negócio tem os seus testes em
`teste_financeiro.py`; aqui prova-se que o ecrã a usa bem.
"""

import sys
import tkinter
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest  # noqa: E402
from testes.teste_financeiro import (  # noqa: E402
    _criar_categoria,
    _criar_despesa_paga,
    _criar_master,
    _criar_propriedade,
    _criar_unidade_mensal,
)

import customtkinter as ctk  # noqa: E402

import despesas  # noqa: E402
import estoque  # noqa: E402
import responsaveis  # noqa: E402
from gui import componentes, sessao  # noqa: E402
from gui.despesas.gui_desp_atribuir import (  # noqa: E402
    AtribuirUnidadeModal,
    DespesasGeraisModal,
    periodo_do_mes,
)
from gui.despesas.gui_desp_lista import _DetalheDespesaModal  # noqa: E402

PERIODO = (date(2026, 1, 1), date(2026, 2, 1))


class TestePeriodoDoMes(unittest.TestCase):

    def test_mes_normal_e_dezembro(self):
        self.assertEqual(
            (date(2026, 1, 1), date(2026, 2, 1)),
            periodo_do_mes(date(2026, 1, 20)),
        )
        self.assertEqual(
            (date(2026, 12, 1), date(2027, 1, 1)),
            periodo_do_mes(date(2026, 12, 31)),
        )


class BaseEcra(BaseMySQLTest):

    def setUp(self):
        super().setUp()
        self.autor = _criar_master()
        sessao.definir_responsavel_ativo(self.autor["id"])
        self.categoria = _criar_categoria("Arrendamento", self.autor)
        self.propriedade = _criar_propriedade("Prédio A")
        self.unidade = _criar_unidade_mensal(self.propriedade["id"])

        self.raiz = ctk.CTk()
        self.raiz.withdraw()
        self.janela = tkinter.Toplevel(self.raiz)
        self.janela.geometry("800x600+0+0")
        self.raiz.update()

        self.erro = mock.patch.object(componentes, "mostrar_erro")
        self.erro.start()

    def tearDown(self):
        self.erro.stop()
        try:
            self.raiz.update()
            self.raiz.destroy()
        except Exception:
            pass
        super().tearDown()

    def _geral(self, valor="700.00"):
        return _criar_despesa_paga(
            self.categoria["id"], valor, date(2026, 1, 15), self.autor
        )

    def _rotulo_unidade(self):
        return f"Prédio A · Unidade Mensal ({self.unidade['id']})"


class TesteAtribuirUnidadeModal(BaseEcra):

    def _abrir(self, despesa, chamadas):
        modal = AtribuirUnidadeModal(
            self.janela, despesa, lambda: chamadas.append(1)
        )
        self.raiz.update()
        return modal

    def test_confirmar_so_ativo_com_unidade_escolhida(self):
        modal = self._abrir(self._geral(), [])
        self.assertEqual("disabled", modal.botao_confirmar.cget("state"))

        modal.seletor.set(self._rotulo_unidade())
        modal._atualizar()

        self.assertEqual("normal", modal.botao_confirmar.cget("state"))

    def test_mostra_o_resultado_antes_e_depois(self):
        modal = self._abrir(self._geral("700.00"), [])
        modal.seletor.set(self._rotulo_unidade())
        modal._atualizar()

        texto = modal.rotulo_resumo.cget("text")
        self.assertIn("0,00", texto)
        self.assertIn("-700,00", texto)

    def test_confirmar_grava_e_avisa(self):
        geral = self._geral()
        chamadas = []
        modal = self._abrir(geral, chamadas)
        modal.seletor.set(self._rotulo_unidade())
        modal._atualizar()

        modal._confirmar()

        guardada = despesas.procurar_despesa(geral["id"])
        self.assertEqual(self.unidade["id"], guardada["unidade_id"])
        self.assertEqual([1], chamadas)

    def test_erro_do_negocio_fica_no_modal(self):
        geral = self._geral()
        chamadas = []
        modal = self._abrir(geral, chamadas)
        modal.seletor.set(self._rotulo_unidade())
        modal._atualizar()
        # Outra pessoa atribuiu entretanto.
        despesas.atribuir_unidade(
            geral["id"], self.unidade["id"], self.autor
        )

        modal._confirmar()

        self.assertIn("já tem unidade", modal.rotulo_erro.cget("text"))
        self.assertEqual([], chamadas)

    def test_dividir_pela_propriedade(self):
        geral = self._geral("100.00")
        chamadas = []
        modal = self._abrir(geral, chamadas)
        modal._mudar_vista("Dividir pelas unidades da propriedade")
        modal.seletor.set("Dividir por Prédio A (1 unidade)")
        modal._atualizar()
        self.assertEqual("normal", modal.botao_confirmar.cget("state"))

        modal._confirmar()

        self.assertEqual(
            "cancelada", despesas.procurar_despesa(geral["id"])["estado"]
        )
        self.assertEqual([1], chamadas)


class TesteDespesasGeraisModal(BaseEcra):

    def _abrir(self, chamadas):
        modal = DespesasGeraisModal(
            self.janela, *PERIODO, lambda: chamadas.append(1)
        )
        self.raiz.update()
        return modal

    def test_lista_so_as_gerais_e_aplicar_comeca_desativado(self):
        g1, g2 = self._geral("10.00"), self._geral("20.00")
        _criar_despesa_paga(
            self.categoria["id"], "5.00", date(2026, 1, 15), self.autor,
            self.unidade["id"],
        )

        modal = self._abrir([])

        self.assertEqual(
            {g1["id"], g2["id"]}, {d["id"] for d, _ in modal._linhas}
        )
        self.assertEqual("disabled", modal.botao_aplicar.cget("state"))

    def test_aplicar_atribui_so_as_escolhidas(self):
        g1, g2 = self._geral("10.00"), self._geral("20.00")
        chamadas = []
        modal = self._abrir(chamadas)
        seletor_g1 = [s for d, s in modal._linhas if d["id"] == g1["id"]][0]
        seletor_g1.set(self._rotulo_unidade())
        modal._ao_escolher()
        self.assertIn("Aplicar 1", modal.botao_aplicar.cget("text"))

        modal._aplicar()

        self.assertEqual(
            self.unidade["id"], despesas.procurar_despesa(g1["id"])[
                "unidade_id"]
        )
        self.assertFalse(
            despesas.procurar_despesa(g2["id"])["unidade_id"]
        )
        self.assertEqual([1], chamadas)

    def test_sem_escolhas_nao_chama_ao_mudar(self):
        self._geral()
        chamadas = []
        modal = self._abrir(chamadas)
        modal._aplicar()
        self.assertEqual([], chamadas)


class TesteDetalheDespesa(BaseEcra):

    class _Tela(tkinter.Frame):
        recarregou = 0

        def _recarregar(self):
            type(self).recarregou += 1

    def _abrir(self, despesa):
        tela = self._Tela(self.janela)
        tela.pack()
        modal = _DetalheDespesaModal(tela, despesa)
        self.raiz.update()
        return modal

    def _textos(self, modal):
        textos = []

        def percorrer(widget):
            try:
                textos.append(str(widget.cget("text")))
            except Exception:
                pass
            for filho in widget.winfo_children():
                percorrer(filho)

        percorrer(modal)
        return textos

    def test_paga_sem_unidade_mostra_imputacao_e_botao(self):
        modal = self._abrir(self._geral())
        textos = self._textos(modal)

        self.assertIn("Geral, sem unidade", textos)
        self.assertIn("Atribuir unidade", textos)
        self.assertIn("Lançada por", textos)
        self.assertIn("Master de Teste", textos)
        self.assertIn("Nenhum anexado", textos)
        self.assertIn("Não", textos)

    def test_com_unidade_nao_oferece_atribuir(self):
        d = _criar_despesa_paga(
            self.categoria["id"], "5.00", date(2026, 1, 15), self.autor,
            self.unidade["id"],
        )
        textos = self._textos(self._abrir(d))

        self.assertNotIn("Atribuir unidade", textos)
        self.assertIn(f"Unidade Mensal ({self.unidade['id']})", textos)

    def test_compra_de_stock_mostra_armazem_e_nao_oferece_atribuir(self):
        despesas.criar_categoria("Compra de Stock", self.autor)
        produto = estoque.criar_produto("Lixívia", "L")
        compra, _ = despesas.criar_despesa_stock(
            itens=[{"produto_id": produto["id"], "quantidade": 5}],
            valor_total=Decimal("30.00"),
            data_lancamento=date(2026, 1, 15),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        textos = self._textos(self._abrir(compra))

        self.assertIn("Armazém (geral)", textos)
        self.assertNotIn("Atribuir unidade", textos)

    def test_cancelada_mostra_quem_cancelou_e_porque(self):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("45.00"),
            data_lancamento=date(2026, 1, 5),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        d = despesas.cancelar_despesa(d["id"], "Duplicada", self.autor)
        textos = self._textos(self._abrir(d))

        self.assertIn("Cancelada por", textos)
        self.assertIn("Duplicada", textos)
        self.assertNotIn("Atribuir unidade", textos)


class TesteContadoresDoMenu(BaseEcra):

    def _criar_pendente(self):
        despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("45.00"),
            data_lancamento=date(2026, 1, 5),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

    def test_despesas_conta_as_pendentes_para_o_master(self):
        contador = sessao.contador_so_gestao(despesas.contar_pendentes)
        self.assertEqual(0, contador())
        self._criar_pendente()
        self.assertEqual(1, contador())

    def test_staff_nao_ve_os_numeros(self):
        self._criar_pendente()
        staff = responsaveis.criar("Staff", tipo_utilizador="Staff")
        sessao.definir_responsavel_ativo(staff["id"])

        for funcao in (
            despesas.contar_pendentes,
            estoque.contar_pendentes_aprovacao,
        ):
            self.assertEqual(0, sessao.contador_so_gestao(funcao)())

    def test_sem_sessao_fica_a_zero(self):
        self._criar_pendente()
        sessao.limpar_responsavel_ativo()
        self.assertEqual(
            0, sessao.contador_so_gestao(despesas.contar_pendentes)()
        )

    def test_stock_sem_pendencias_conta_zero(self):
        self.assertEqual(0, estoque.contar_pendentes_aprovacao())


if __name__ == "__main__":
    unittest.main(verbosity=2)
