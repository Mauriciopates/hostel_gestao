"""Testes da Guia de entrega e do dono do Rol de Lavanderia
(27/09/2026, v1.6.0) — unittest, não pytest.

Duas partes:

- `TesteMontarGuia`: `estoque.montar_guia_entrega` é uma função
  PURA (recebe tudo já lido), por isso testa-se sem base de dados,
  com dicionários feitos à mão. Desde 10/10/2026 a guia é por
  unidade (o Rol vai para a unidade da reserva).
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

_UNIDADES = {
    "UNI-001": {"id": "UNI-001", "nome": "Bonfim 1",
                "propriedade_nome": "Casa Bonfim"},
    "UNI-003": {"id": "UNI-003", "nome": "AP 1",
                "propriedade_nome": "Santa Catarina"},
    "UNI-008": {"id": "UNI-008", "nome": "AP 2",
                "propriedade_nome": "Santa Catarina"},
}


def _nota(unidade_id, nome="AP 1"):
    """A nota que `_dono_do_rol` escreve em todo o Rol."""
    return (
        f"Rol da unidade {nome} ({unidade_id}), reserva RSV-001, "
        f"registada por Mauricio."
    )


_NOMES = {"RES-002": "Ana", "RES-003": "Bruno"}


def _montar(requisicoes, itens):
    return estoque.montar_guia_entrega(
        requisicoes, itens, _PRODUTOS, _UNIDADES, _NOMES
    )


class TesteUnidadeDoRol(unittest.TestCase):

    def test_le_a_unidade_da_nota(self):
        self.assertEqual(estoque.unidade_do_rol(_nota("UNI-008")), "UNI-008")

    def test_nota_sem_unidade_devolve_none(self):
        self.assertIsNone(estoque.unidade_do_rol("Rol antigo"))
        self.assertIsNone(estoque.unidade_do_rol(""))
        self.assertIsNone(estoque.unidade_do_rol(None))


class TesteMontarGuia(unittest.TestCase):

    def test_sem_requisicoes_devolve_lista_vazia(self):
        self.assertEqual(_montar([], {}), [])

    def test_rol_vai_para_o_bloco_da_unidade_da_reserva(self):
        blocos = _montar(
            [_req("REQ-001", "RES-002", origem="rol",
                  obs=_nota("UNI-003"))],
            {"REQ-001": [_item("PRD-002", 2, 2)]},
        )
        self.assertEqual(len(blocos), 1)
        self.assertEqual(blocos[0]["unidade"]["id"], "UNI-003")
        self.assertEqual([e["id"] for e in blocos[0]["rol"]], ["REQ-001"])
        self.assertFalse(blocos[0]["sem_unidade"])

    def test_um_bloco_por_unidade_mesmo_com_o_mesmo_staff(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002", origem="rol",
                     obs=_nota("UNI-003")),
                _req("REQ-002", "RES-002", origem="rol",
                     obs=_nota("UNI-008", "AP 2")),
            ],
            {
                "REQ-001": [_item("PRD-002", 1, 1)],
                "REQ-002": [_item("PRD-002", 1, 1)],
            },
        )
        self.assertEqual(
            [b["unidade"]["id"] for b in blocos], ["UNI-003", "UNI-008"]
        )

    def test_dois_rol_da_mesma_unidade_ficam_no_mesmo_bloco(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002", origem="rol",
                     obs=_nota("UNI-003")),
                _req("REQ-002", "RES-003", origem="rol",
                     obs=_nota("UNI-003")),
            ],
            {
                "REQ-001": [_item("PRD-003", 2, 2)],
                "REQ-002": [_item("PRD-003", 4, 4), _item("PRD-002", 2, 2)],
            },
        )
        self.assertEqual(len(blocos), 1)
        totais = {t["produto_id"]: t["quantidade"]
                  for t in blocos[0]["totais"]}
        self.assertEqual(totais, {"PRD-003": 6, "PRD-002": 2})
        self.assertEqual(blocos[0]["total_itens"], 8)

    def test_pedido_de_staff_vai_para_o_bloco_do_staff_no_fim(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002"),
                _req("REQ-002", "RES-002", origem="rol",
                     obs=_nota("UNI-003")),
            ],
            {
                "REQ-001": [_item("PRD-001", 2, 2)],
                "REQ-002": [_item("PRD-002", 1, 1)],
            },
        )
        self.assertEqual(len(blocos), 2)
        ultimo = blocos[-1]
        self.assertTrue(ultimo["sem_unidade"])
        self.assertIsNone(ultimo["unidade"])
        self.assertEqual(ultimo["staff"], {"id": "RES-002", "nome": "Ana"})
        self.assertEqual(
            [e["id"] for e in ultimo["requisicoes"]], ["REQ-001"]
        )

    def test_um_bloco_por_staff_ordenado_pelo_nome(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-003"),
                _req("REQ-002", "RES-002"),
                _req("REQ-003", "RES-002"),
            ],
            {
                "REQ-001": [_item("PRD-001", 1, 1)],
                "REQ-002": [_item("PRD-001", 1, 1)],
                "REQ-003": [_item("PRD-003", 2, 2)],
            },
        )
        self.assertEqual(
            [b["staff"]["nome"] for b in blocos], ["Ana", "Bruno"]
        )
        self.assertEqual(
            [e["id"] for e in blocos[0]["requisicoes"]],
            ["REQ-002", "REQ-003"],
        )

    def test_rol_sem_unidade_vem_depois_dos_pedidos_de_staff(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002", origem="rol", obs="Rol antigo"),
                _req("REQ-002", "RES-003"),
            ],
            {
                "REQ-001": [_item("PRD-002", 1, 1)],
                "REQ-002": [_item("PRD-001", 1, 1)],
            },
        )
        self.assertEqual(blocos[0]["staff"]["nome"], "Bruno")
        self.assertIsNone(blocos[1]["staff"])
        self.assertEqual([e["id"] for e in blocos[1]["rol"]], ["REQ-001"])

    def test_rol_sem_unidade_reconhecivel_vai_para_sem_unidade(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002", origem="rol", obs="Rol antigo"),
                _req("REQ-002", "RES-002", origem="rol",
                     obs=_nota("UNI-999")),
            ],
            {
                "REQ-001": [_item("PRD-002", 1, 1)],
                "REQ-002": [_item("PRD-002", 1, 1)],
            },
        )
        self.assertEqual(len(blocos), 1)
        self.assertTrue(blocos[0]["sem_unidade"])
        self.assertEqual(
            [e["id"] for e in blocos[0]["rol"]], ["REQ-001", "REQ-002"]
        )

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

    def test_blocos_ordenados_por_propriedade_e_unidade(self):
        blocos = _montar(
            [
                _req("REQ-001", "RES-002", origem="rol",
                     obs=_nota("UNI-008", "AP 2")),
                _req("REQ-002", "RES-002", origem="rol",
                     obs=_nota("UNI-001", "Bonfim 1")),
                _req("REQ-003", "RES-002", origem="rol",
                     obs=_nota("UNI-003")),
            ],
            {
                "REQ-001": [_item("PRD-002", 1, 1)],
                "REQ-002": [_item("PRD-002", 1, 1)],
                "REQ-003": [_item("PRD-002", 1, 1)],
            },
        )
        self.assertEqual(
            [b["unidade"]["id"] for b in blocos],
            ["UNI-001", "UNI-003", "UNI-008"],
        )


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

    def test_rol_enviado_hoje_aparece_no_bloco_da_unidade(self):
        staff = responsaveis.criar("Ana")
        unidades.atribuir_responsavel(self.unidade["id"], staff["id"])
        requisicao = self._gerar_rol()

        blocos = estoque.guia_entrega(date.today(), "Master")

        self.assertEqual(len(blocos), 1)
        self.assertEqual(blocos[0]["unidade"]["id"], self.unidade["id"])
        self.assertEqual(blocos[0]["unidade"]["propriedade_nome"],
                         "Foz Velha")
        self.assertEqual(blocos[0]["rol"][0]["id"], requisicao["id"])
        self.assertEqual(blocos[0]["total_itens"], 2)

    def test_outro_dia_nao_tem_nada(self):
        self._gerar_rol()

        blocos = estoque.guia_entrega(date(2000, 1, 1), "Admin")

        self.assertEqual(blocos, [])


if __name__ == "__main__":
    unittest.main()
