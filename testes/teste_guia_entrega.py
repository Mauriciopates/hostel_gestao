"""Testes da Guia de entrega e do dono do Rol de Lavanderia
(27/09/2026, v1.6.0) — unittest, não pytest.

Duas partes:

- `TesteMontarGuia`: `estoque.montar_guia_entrega` é uma função
  PURA (recebe tudo já lido), por isso testa-se sem base de dados,
  com dicionários feitos à mão.
- `TesteDonoDoRol` e `TesteGuiaEntregaBD`: correm contra a base de
  teste (`BaseMySQLTest`), porque o dono do Rol sai da tabela
  `responsavel_unidade` e a guia lê as requisições enviadas.
"""

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest  # noqa: E402

import estoque  # noqa: E402
import propriedades  # noqa: E402
import responsaveis  # noqa: E402
import unidades  # noqa: E402


# =====================================================================
# PARTE 1 — FUNÇÃO PURA (sem base de dados)
# =====================================================================


def _req(req_id, dono, origem="pedido", estado="enviada", obs=""):
    return {
        "id": req_id,
        "responsavel_id": dono,
        "origem": origem,
        "estado": estado,
        "observacoes": obs,
    }


def _item(produto_id, pedida, enviada=None):
    return {
        "produto_id": produto_id,
        "quantidade_pedida": pedida,
        "quantidade_enviada": enviada,
    }


_PRODUTOS = {
    "PRD-001": {"id": "PRD-001", "nome": "Mistolin", "unidade_medida": "L"},
    "PRD-002": {"id": "PRD-002", "nome": "Lençol", "unidade_medida": "un"},
    "PRD-003": {"id": "PRD-003", "nome": "Toalha", "unidade_medida": "un"},
}

_RESPONSAVEIS = {
    "RES-001": {"id": "RES-001", "nome": "Mauricio",
                "tipo_utilizador": "Master"},
    "RES-002": {"id": "RES-002", "nome": "Ana", "tipo_utilizador": "Staff"},
    "RES-003": {"id": "RES-003", "nome": "Bruno",
                "tipo_utilizador": "Staff"},
}


def _montar(requisicoes, itens, unidades_por_resp=None):
    return estoque.montar_guia_entrega(
        requisicoes,
        itens,
        _PRODUTOS,
        _RESPONSAVEIS,
        unidades_por_resp or {},
    )


class TesteMontarGuia(unittest.TestCase):

    def test_sem_requisicoes_devolve_lista_vazia(self):
        self.assertEqual(_montar([], {}), [])

    def test_agrupa_por_staff_e_separa_requisicoes_do_rol(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002"),
                _req("REQ-002", "RES-002", origem="rol"),
            ],
            {
                "REQ-001": [_item("PRD-001", 2, 2)],
                "REQ-002": [_item("PRD-002", 1, 1)],
            },
        )
        self.assertEqual(len(blocos), 1)
        self.assertEqual(blocos[0]["responsavel"]["id"], "RES-002")
        self.assertEqual(
            [e["id"] for e in blocos[0]["requisicoes"]], ["REQ-001"]
        )
        self.assertEqual([e["id"] for e in blocos[0]["rol"]], ["REQ-002"])
        self.assertFalse(blocos[0]["por_atribuir"])

    def test_rol_de_quem_nao_e_staff_vai_para_por_atribuir(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002"),
                _req("REQ-002", "RES-001", origem="rol"),
            ],
            {
                "REQ-001": [_item("PRD-001", 2, 2)],
                "REQ-002": [_item("PRD-002", 1, 1)],
            },
        )
        self.assertEqual(len(blocos), 2)
        ultimo = blocos[-1]
        self.assertTrue(ultimo["por_atribuir"])
        self.assertIsNone(ultimo["responsavel"])
        self.assertEqual([e["id"] for e in ultimo["rol"]], ["REQ-002"])

    def test_requisicao_normal_de_um_master_fica_no_bloco_dele(self):
        """Só o Rol vai para "Por atribuir" — uma requisição normal
        é sempre de quem a pediu, seja qual for o perfil."""
        blocos = _montar(
            [_req("REQ-001", "RES-001")],
            {"REQ-001": [_item("PRD-001", 1, 1)]},
        )
        self.assertEqual(len(blocos), 1)
        self.assertFalse(blocos[0]["por_atribuir"])
        self.assertEqual(blocos[0]["responsavel"]["id"], "RES-001")

    def test_totais_somam_o_mesmo_produto_entre_requisicao_e_rol(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002"),
                _req("REQ-002", "RES-002", origem="rol"),
            ],
            {
                "REQ-001": [_item("PRD-003", 2, 2)],
                "REQ-002": [_item("PRD-003", 4, 4), _item("PRD-002", 2, 2)],
            },
        )
        totais = {t["produto_id"]: t["quantidade"]
                  for t in blocos[0]["totais"]}
        self.assertEqual(totais, {"PRD-003": 6, "PRD-002": 2})
        self.assertEqual(blocos[0]["total_itens"], 8)

    def test_usa_quantidade_enviada_e_so_cai_na_pedida_sem_envio(self):
        blocos = _montar(
            [_req("REQ-001", "RES-002")],
            {"REQ-001": [_item("PRD-001", 5, 3), _item("PRD-002", 2)]},
        )
        linhas = {
            linha["produto_id"]: linha["quantidade"]
            for linha in blocos[0]["requisicoes"][0]["itens"]
        }
        self.assertEqual(linhas, {"PRD-001": 3, "PRD-002": 2})

    def test_item_enviado_a_zero_sai_e_requisicao_vazia_nao_entra(self):
        blocos = _montar(
            [_req("REQ-001", "RES-002"), _req("REQ-002", "RES-003")],
            {
                "REQ-001": [_item("PRD-001", 2, 0), _item("PRD-002", 1, 1)],
                "REQ-002": [_item("PRD-001", 2, 0)],
            },
        )
        self.assertEqual(len(blocos), 1)
        itens = blocos[0]["requisicoes"][0]["itens"]
        self.assertEqual([i["produto_id"] for i in itens], ["PRD-002"])

    def test_blocos_ordenados_pelo_nome_do_staff(self):
        blocos = _montar(
            [_req("REQ-001", "RES-003"), _req("REQ-002", "RES-002")],
            {
                "REQ-001": [_item("PRD-001", 1, 1)],
                "REQ-002": [_item("PRD-001", 1, 1)],
            },
        )
        self.assertEqual(
            [b["responsavel"]["nome"] for b in blocos], ["Ana", "Bruno"]
        )

    def test_unidades_do_staff_vem_no_bloco(self):
        blocos = _montar(
            [_req("REQ-001", "RES-002")],
            {"REQ-001": [_item("PRD-001", 1, 1)]},
            {"RES-002": [{"id": "UNI-001", "nome": "Foz Velha"}]},
        )
        self.assertEqual(blocos[0]["unidades"][0]["id"], "UNI-001")


# =====================================================================
# PARTE 2 — COM BASE DE DADOS
# =====================================================================


def _unidade_airbnb(nome="Foz Airbnb"):
    prop = propriedades.criar("Foz Velha", "Rua de Exemplo, 1")
    return unidades.criar(
        prop["id"],
        nome,
        "airbnb",
        Decimal("50.00"),
        Decimal("70.00"),
        Decimal("10.00"),
    )


class _BaseRol(BaseMySQLTest):

    def setUp(self):
        super().setUp()
        self.master = responsaveis.criar(
            "Mauricio", tipo_utilizador="Master"
        )
        self.produto = estoque.criar_produto("Lençol", "unidade")
        estoque.registar_movimento(
            self.produto["id"], "entrada", 30, date.today()
        )
        self.unidade = _unidade_airbnb()

    def _gerar_rol(self):
        resultado_fixo = (
            [
                {
                    "produto_id": self.produto["id"],
                    "quantidade": 2,
                    "nome": self.produto["nome"],
                }
            ],
            [],
        )
        with patch(
            "estoque.configuracoes.obter_bool", return_value=True
        ), patch(
            "estoque.calcular_rol_lavanderia", return_value=resultado_fixo
        ):
            requisicao = estoque.gerar_rol_lavanderia_automatico(
                {"id": "OCU-TESTE", "unidade_id": self.unidade["id"]},
                self.master["id"],
            )
        assert requisicao is not None
        return requisicao


class TesteDonoDoRol(_BaseRol):

    def test_com_um_staff_o_rol_fica_em_nome_dele(self):
        staff = responsaveis.criar("Ana")
        unidades.atribuir_responsavel(self.unidade["id"], staff["id"])

        requisicao = self._gerar_rol()

        self.assertEqual(requisicao["responsavel_id"], staff["id"])
        self.assertIn(self.unidade["id"], requisicao["observacoes"])
        self.assertIn("registada por Mauricio", requisicao["observacoes"])

    def test_sem_staff_fica_em_nome_de_quem_registou(self):
        requisicao = self._gerar_rol()

        self.assertEqual(requisicao["responsavel_id"], self.master["id"])
        self.assertIn("sem staff atribuído", requisicao["observacoes"])

    def test_com_dois_staff_fica_em_nome_de_quem_registou(self):
        for nome in ("Ana", "Bruno"):
            staff = responsaveis.criar(nome)
            unidades.atribuir_responsavel(self.unidade["id"], staff["id"])

        requisicao = self._gerar_rol()

        self.assertEqual(requisicao["responsavel_id"], self.master["id"])
        self.assertIn("mais de um staff", requisicao["observacoes"])

    def test_master_ligado_a_unidade_nao_conta_como_staff(self):
        unidades.atribuir_responsavel(self.unidade["id"], self.master["id"])
        staff = responsaveis.criar("Ana")
        unidades.atribuir_responsavel(self.unidade["id"], staff["id"])

        requisicao = self._gerar_rol()

        self.assertEqual(requisicao["responsavel_id"], staff["id"])


class TesteGuiaEntregaBD(_BaseRol):

    def test_staff_nao_pode_gerar_a_guia(self):
        with self.assertRaises(ValueError):
            estoque.guia_entrega(date.today(), "Staff")

    def test_rol_enviado_hoje_aparece_no_bloco_do_staff(self):
        staff = responsaveis.criar("Ana")
        unidades.atribuir_responsavel(self.unidade["id"], staff["id"])
        requisicao = self._gerar_rol()

        blocos = estoque.guia_entrega(date.today(), "Master")

        self.assertEqual(len(blocos), 1)
        self.assertEqual(blocos[0]["responsavel"]["id"], staff["id"])
        self.assertEqual(blocos[0]["rol"][0]["id"], requisicao["id"])
        self.assertEqual(blocos[0]["unidades"][0]["id"], self.unidade["id"])
        self.assertEqual(blocos[0]["total_itens"], 2)

    def test_outro_dia_nao_tem_nada(self):
        self._gerar_rol()

        blocos = estoque.guia_entrega(date(2000, 1, 1), "Admin")

        self.assertEqual(blocos, [])


if __name__ == "__main__":
    unittest.main()
