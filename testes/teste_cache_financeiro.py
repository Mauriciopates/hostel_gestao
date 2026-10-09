"""Testes da cache de leitura do motor financeiro (`financeiro.leitura_em_cache`).

Não precisam de MySQL: as leituras da base são substituídas por
`Mock`s que contam quantas vezes foram chamadas. Garantem que:

- sem a janela, o comportamento é o de sempre (cada chamada lê);
- dentro da janela cada leitura repetida faz-se UMA vez;
- o resultado é exatamente o mesmo com e sem cache;
- as cópias devolvidas podem ser alteradas sem estragar a cache;
- a cache acaba ao sair da janela (mesmo com exceção) e as janelas
  encadeadas reaproveitam a de fora.
"""

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import financeiro  # noqa: E402

INICIO = date(2026, 9, 1)
FIM = date(2026, 10, 1)


def _despesa(id_, categoria, valor, pago_em):
    return {
        "id": id_, "categoria_id": categoria, "valor": Decimal(valor),
        "data_pagamento": pago_em, "unidade_id": "",
    }


class BaseCache(unittest.TestCase):
    def setUp(self):
        self.pagas = [
            _despesa("DSP-001", "CAT-001", "10.00", date(2026, 9, 3)),
            _despesa("DSP-002", "CAT-002", "5.50", date(2026, 9, 9)),
            _despesa("DSP-003", "CAT-001", "4.50", date(2026, 8, 20)),
        ]
        self.movimentos = [
            {"produto_id": "PRD-001", "tipo": "saida", "quantidade": 3,
             "data": date(2026, 9, 5), "requisicao_id": ""},
        ]

        self.listar_despesas = patch.object(
            financeiro.despesas, "listar_despesas",
            side_effect=lambda estado=None: list(self.pagas),
        ).start()
        self.procurar_categoria = patch.object(
            financeiro.despesas, "procurar_categoria",
            side_effect=lambda cid: {"id": cid, "nome": f"Nome {cid}"},
        ).start()
        self.listar_movimentos = patch.object(
            financeiro.estoque, "listar_movimentos",
            side_effect=lambda: [dict(m) for m in self.movimentos],
        ).start()
        self.procurar_produto = patch.object(
            financeiro.estoque, "procurar_produto",
            side_effect=lambda pid: {"id": pid, "nome": f"Prod {pid}"},
        ).start()
        self.listar_ocupacoes = patch.object(
            financeiro.repositorio, "listar_ocupacoes", return_value=[],
        ).start()
        self.addCleanup(patch.stopall)


class TesteCacheDeLeitura(BaseCache):
    def test_sem_janela_cada_chamada_le_da_base(self):
        financeiro.resultado(INICIO, FIM)
        financeiro.resultado(INICIO, FIM)

        self.assertEqual(self.listar_despesas.call_count, 2)
        self.assertEqual(self.listar_movimentos.call_count, 2)

    def test_dentro_da_janela_le_uma_vez(self):
        with financeiro.leitura_em_cache():
            for _ in range(8):
                financeiro.resultado(INICIO, FIM)

        self.assertEqual(self.listar_despesas.call_count, 1)
        self.assertEqual(self.listar_movimentos.call_count, 1)
        self.assertEqual(self.listar_ocupacoes.call_count, 1)
        # Duas categorias e um produto: uma leitura de cada, não 8x.
        self.assertEqual(self.procurar_categoria.call_count, 2)
        self.assertEqual(self.procurar_produto.call_count, 1)

    def test_meses_diferentes_leem_as_ocupacoes_de_cada_periodo(self):
        with financeiro.leitura_em_cache():
            financeiro.resultado(INICIO, FIM)
            financeiro.resultado(date(2026, 8, 1), INICIO)

        # Períodos diferentes → ocupações diferentes (2 leituras), mas as
        # despesas pagas e os movimentos são os mesmos (1 leitura).
        self.assertEqual(self.listar_ocupacoes.call_count, 2)
        self.assertEqual(self.listar_despesas.call_count, 1)

    def test_resultado_igual_com_e_sem_cache(self):
        sem = financeiro.resultado(INICIO, FIM)

        with financeiro.leitura_em_cache():
            primeiro = financeiro.resultado(INICIO, FIM)
            segundo = financeiro.resultado(INICIO, FIM)

        self.assertEqual(sem, primeiro)
        self.assertEqual(sem, segundo)
        self.assertEqual(sem["despesas_operacionais"], Decimal("15.50"))
        self.assertEqual(sem["cogs_quantidade"], 3)

    def test_despesas_por_categoria_igual_com_e_sem_cache(self):
        sem = financeiro.despesas_por_categoria(INICIO, FIM)

        with financeiro.leitura_em_cache():
            com = financeiro.despesas_por_categoria(INICIO, FIM)

        self.assertEqual(sem, com)

    def test_alterar_o_devolvido_nao_estraga_a_cache(self):
        with financeiro.leitura_em_cache():
            linhas = financeiro.despesas_por_categoria(INICIO, FIM)
            linhas.clear()
            linhas.append({"lixo": True})

            novamente = financeiro.despesas_por_categoria(INICIO, FIM)

        self.assertEqual(len(novamente), 2)
        self.assertNotIn("lixo", novamente[0])

    def test_a_cache_acaba_ao_sair_da_janela(self):
        with financeiro.leitura_em_cache():
            financeiro.resultado(INICIO, FIM)

        # Fora da janela, dados novos na base voltam a ser lidos.
        self.pagas.append(
            _despesa("DSP-004", "CAT-003", "100.00", date(2026, 9, 10))
        )
        resultado = financeiro.resultado(INICIO, FIM)

        self.assertEqual(
            resultado["despesas_operacionais"], Decimal("115.50")
        )

    def test_a_cache_acaba_mesmo_com_excecao(self):
        with self.assertRaises(RuntimeError):
            with financeiro.leitura_em_cache():
                raise RuntimeError("falhou a meio")

        financeiro.resultado(INICIO, FIM)
        financeiro.resultado(INICIO, FIM)

        self.assertEqual(self.listar_despesas.call_count, 2)

    def test_janelas_encadeadas_reaproveitam_a_de_fora(self):
        with financeiro.leitura_em_cache():
            financeiro.resultado(INICIO, FIM)
            with financeiro.leitura_em_cache():
                financeiro.resultado(INICIO, FIM)
            # A de dentro fechou-se, mas a de fora continua ativa.
            financeiro.resultado(INICIO, FIM)

        self.assertEqual(self.listar_despesas.call_count, 1)

    def test_depois_de_tudo_fechado_nao_ha_cache(self):
        with financeiro.leitura_em_cache():
            with financeiro.leitura_em_cache():
                pass

        financeiro.resultado(INICIO, FIM)
        financeiro.resultado(INICIO, FIM)

        self.assertEqual(self.listar_despesas.call_count, 2)


if __name__ == "__main__":
    unittest.main()
