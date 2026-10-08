"""Testes do relatório "Rentabilidade" (v1.12.0) — a parte que não
precisa de ecrã: a lista de linhas que desenha a tabela E alimenta o
PDF, o CSV e o Excel.

O motor (`financeiro.rentabilidade`) tem os seus testes em
`teste_financeiro.py`; aqui entram dados já calculados, para provar
só a montagem: sinais, ordem, linha de gerais e total.
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gui.relatorios.gui_relat_financeiro import RelatFinanceiro  # noqa: E402

D = Decimal


def _linha(tabela, descontos, despesas):
    receita = tabela - descontos
    resultado = receita - despesas
    return {
        "receita_tabela": D(tabela),
        "descontos": D(descontos),
        "receita": D(receita),
        "despesas": D(despesas),
        "resultado": D(resultado),
        "rentavel": resultado >= 0,
    }


def _dados(gerais="0.00"):
    unidade_1 = {
        "unidade_id": "UNI-001",
        "unidade_nome": "Quarto 1",
        **_linha(D("250.00"), D("50.00"), D("80.00")),
    }
    unidade_2 = {
        "unidade_id": "UNI-002",
        "unidade_nome": "Quarto 2",
        **_linha(D("200.00"), D("0.00"), D("300.00")),
    }
    propriedade = {
        "propriedade_id": "PRO-001",
        "propriedade_nome": "Prédio A",
        **_linha(D("450.00"), D("50.00"), D("380.00")),
        "unidades": [unidade_1, unidade_2],
    }
    gerais = D(gerais)
    total = _linha(D("450.00"), D("50.00"), D("380.00") + gerais)
    return {"propriedades": [propriedade], "gerais": gerais, "total": total}


class TesteMontarLinhasRentabilidade(unittest.TestCase):

    def _montar(self, dados, por_unidade):
        return RelatFinanceiro._montar_linhas_rentabilidade(
            dados, por_unidade
        )

    def test_por_propriedade_nao_tem_linhas_de_unidade(self):
        linhas = self._montar(_dados(), por_unidade=False)

        self.assertEqual(
            ["propriedade", "total"], [linha["tipo"] for linha in linhas]
        )

    def test_por_unidade_poe_as_unidades_a_seguir_a_propriedade(self):
        linhas = self._montar(_dados(), por_unidade=True)

        self.assertEqual(
            ["propriedade", "unidade", "unidade", "total"],
            [linha["tipo"] for linha in linhas],
        )

    def test_descontos_e_despesas_saem_com_sinal_negativo(self):
        linha = self._montar(_dados(), por_unidade=False)[0]

        tabela, descontos, despesas, resultado = linha["valores"]
        self.assertEqual(D("450.00"), tabela)
        self.assertEqual(D("-50.00"), descontos)
        self.assertEqual(D("-380.00"), despesas)
        self.assertEqual(D("20.00"), resultado)
        # A conta lê-se de cima para baixo: tabela + (−) + (−) = resultado.
        self.assertEqual(resultado, tabela + descontos + despesas)

    def test_sem_desconto_nao_aparece_menos_zero(self):
        linhas = self._montar(_dados(), por_unidade=True)
        quarto_2 = linhas[2]

        self.assertEqual("0.00", str(quarto_2["valores"][1]))

    def test_estado_de_cada_linha(self):
        linhas = self._montar(_dados(), por_unidade=True)

        self.assertEqual(
            [True, True, False, True],
            [linha["rentavel"] for linha in linhas],
        )

    def test_texto_do_ficheiro_traz_propriedade_e_unidade(self):
        linhas = self._montar(_dados(), por_unidade=True)

        self.assertEqual("Prédio A (PRO-001)", linhas[0]["exportar"])
        self.assertEqual(
            "Prédio A (PRO-001) / Quarto 1 (UNI-001)",
            linhas[1]["exportar"],
        )

    def test_texto_do_ecra_tem_nome_e_id_em_duas_linhas(self):
        linhas = self._montar(_dados(), por_unidade=True)

        self.assertEqual("Prédio A\nPRO-001", linhas[0]["ecra"])
        self.assertEqual("    Quarto 1\n    UNI-001", linhas[1]["ecra"])

    def test_sem_gerais_nao_ha_linha_de_gerais(self):
        linhas = self._montar(_dados("0.00"), por_unidade=True)

        self.assertNotIn("gerais", [linha["tipo"] for linha in linhas])

    def test_stock_central_vem_depois_das_gerais_e_antes_do_total(self):
        dados = _dados("25.00")
        dados["stock_central"] = D("30.00")

        linhas = self._montar(dados, por_unidade=False)

        self.assertEqual(
            ["propriedade", "gerais", "stock", "total"],
            [linha["tipo"] for linha in linhas],
        )
        stock = linhas[2]
        self.assertEqual("Stock central (compras de stock)", stock["ecra"])
        self.assertEqual(D("-30.00"), stock["valores"][2])
        self.assertIsNone(stock["rentavel"])

    def test_sem_stock_central_nao_ha_linha(self):
        linhas = self._montar(_dados(), por_unidade=False)

        self.assertNotIn("stock", [linha["tipo"] for linha in linhas])

    def test_gerais_ficam_antes_do_total_so_com_despesas(self):
        linhas = self._montar(_dados("25.00"), por_unidade=False)

        self.assertEqual(
            ["propriedade", "gerais", "total"],
            [linha["tipo"] for linha in linhas],
        )
        gerais = linhas[1]
        self.assertEqual("Despesas gerais não atribuídas", gerais["exportar"])
        self.assertEqual(
            (D("0.00"), D("0.00"), D("-25.00"), D("-25.00")),
            gerais["valores"],
        )
        self.assertIsNone(gerais["rentavel"])

    def test_total_pesa_as_gerais(self):
        total = self._montar(_dados("25.00"), por_unidade=False)[-1]

        self.assertEqual("TOTAL (1 propriedades)", total["exportar"])
        self.assertEqual(D("-405.00"), total["valores"][2])
        self.assertEqual(D("-5.00"), total["valores"][3])
        self.assertFalse(total["rentavel"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
