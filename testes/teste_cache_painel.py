"""Testes da cache de leitura do painel (`painel.leitura_em_cache`) e do
cálculo de alertas de stock em lote. Sem MySQL: leituras com Mock."""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import estoque  # noqa: E402
import painel  # noqa: E402

HOJE = date(2026, 10, 9)


class BaseCache(unittest.TestCase):
    def setUp(self):
        self.ocupacoes = [{"id": "OCP-001", "unidade_id": "UNI-001"}]
        self.listar = patch.object(
            painel.contratos, "listar",
            side_effect=lambda **f: [dict(o) for o in self.ocupacoes],
        ).start()
        self.taxa = patch.object(
            painel.unidades, "taxa_ocupacao", return_value=(1, 2)
        ).start()
        self.unid = patch.object(
            painel.unidades, "listar_com_propriedade",
            return_value=[{"id": "UNI-001", "propriedade_nome": "P", "nome": "U"}],
        ).start()
        self.cli = patch.object(
            painel.clientes, "listar",
            return_value=[{"id": "CLI-001", "nome": "Ana"}],
        ).start()
        self.addCleanup(patch.stopall)


class TesteCachePainel(BaseCache):
    def test_sem_janela_cada_chamada_le(self):
        painel._contratos()
        painel._contratos()
        self.assertEqual(self.listar.call_count, 2)

    def test_dentro_da_janela_le_uma_vez(self):
        with painel.leitura_em_cache():
            for _ in range(4):
                painel._contratos()
                painel._taxa_ocupacao(HOJE, "airbnb")
                painel._rotulos_unidades()
                painel._nomes_clientes()
        self.assertEqual(self.listar.call_count, 1)
        self.assertEqual(self.taxa.call_count, 1)
        self.assertEqual(self.unid.call_count, 1)
        self.assertEqual(self.cli.call_count, 1)

    def test_filtros_diferentes_sao_leituras_diferentes(self):
        with painel.leitura_em_cache():
            painel._contratos()
            painel._contratos(aviso_documento=True)
            painel._contratos(aviso_documento=True)
        self.assertEqual(self.listar.call_count, 2)

    def test_copias_independentes(self):
        with painel.leitura_em_cache():
            a = painel._contratos()
            a[0]["id"] = "LIXO"
            a.clear()
            b = painel._contratos()
        self.assertEqual(b, [{"id": "OCP-001", "unidade_id": "UNI-001"}])

    def test_acaba_ao_sair_mesmo_com_excecao(self):
        with self.assertRaises(RuntimeError):
            with painel.leitura_em_cache():
                painel._contratos()
                raise RuntimeError
        painel._contratos()
        self.assertEqual(self.listar.call_count, 2)

    def test_janelas_encadeadas(self):
        with painel.leitura_em_cache():
            painel._contratos()
            with painel.leitura_em_cache():
                painel._contratos()
            painel._contratos()
        self.assertEqual(self.listar.call_count, 1)

    def test_staff_por_unidade_igual_com_e_sem_cache(self):
        with patch.object(
            painel.responsaveis, "listar",
            return_value=[
                {"id": "R1", "nome": "Rui", "tipo_utilizador": "Staff"},
                {"id": "R2", "nome": "Eva", "tipo_utilizador": "Admin"},
            ],
        ), patch.object(
            painel.unidades, "unidades_geridas_por",
            return_value=[{"id": "UNI-001"}],
        ) as geridas:
            sem = painel.staff_por_unidade()
            with painel.leitura_em_cache():
                com = painel.staff_por_unidade()
                painel.staff_por_unidade()
            self.assertEqual(sem, com)
            self.assertEqual(com, {"UNI-001": ["Rui"]})
            self.assertEqual(geridas.call_count, 2)  # 1 sem + 1 com cache


class TesteAlertasStockEmLote(unittest.TestCase):
    def test_saldos_e_ordem_iguais_a_saldo_produto(self):
        produtos = [
            {"id": "P1", "stock_minimo": 10},
            {"id": "P2", "stock_minimo": 5},
            {"id": "P3", "stock_minimo": 2},
        ]
        movs = [
            {"produto_id": "P1", "tipo": "entrada", "quantidade": 8},
            {"produto_id": "P1", "tipo": "saida", "quantidade": 3},
            {"produto_id": "P2", "tipo": "entrada", "quantidade": 9},
            {"produto_id": "P2", "tipo": "ajuste", "quantidade": -1},
        ]
        with patch.object(estoque, "listar_produtos", return_value=produtos), \
             patch.object(estoque.repositorio, "listar_movimentos",
                          return_value=movs) as lm:
            alertas = estoque.listar_alertas_stock()

        self.assertEqual(lm.call_count, 1)
        self.assertEqual([a["produto"]["id"] for a in alertas], ["P1", "P3"])
        self.assertEqual((alertas[0]["saldo"], alertas[0]["em_falta"]), (5, 5))
        self.assertEqual((alertas[1]["saldo"], alertas[1]["em_falta"]), (0, 2))


if __name__ == "__main__":
    unittest.main()
