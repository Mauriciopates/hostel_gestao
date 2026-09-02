"""Testes do módulo estoque.py — unittest, não pytest.

sys.path.insert(0, "src") porque o unittest corre a partir da raiz
do projeto e não encontraria os módulos sem isto (mesma convenção
usada nos outros ficheiros de teste).

Cada teste constrói o seu próprio "dados" em memória — sem pasta
temporária nem redirecionar caminhos. Exceção conhecida:
repositorio.proximo_id() grava mesmo no dados/contadores.json real,
mesmo durante os testes (precedente já aceite desde
teste_propriedades.py e teste_unidades.py) — por isso os testes
verificam o prefixo do id (ex.: "PRD-"), nunca o número exato.
"""

import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, "src")

import estoque
import responsaveis


def _dados():
    return {
        "produtos": [],
        "movimentos": [],
        "requisicoes": [],
        "itens_requisicao": [],
        "devolucoes": [],
        "itens_devolucao": [],
        "responsaveis": [],
    }


def _responsavel_ativo(dados, nome="Ana Ferreira"):
    return responsaveis.criar(dados, nome)


def _responsavel_inativo(dados, nome="Rui Nogueira"):
    r = responsaveis.criar(dados, nome)
    responsaveis.desativar(dados, r["id"])
    return r


def _produto_ativo(dados, nome="Toalhas", unidade_medida="unidade"):
    return estoque.criar_produto(dados, nome, unidade_medida)


def _produto_inativo(dados, nome="Sabonetes"):
    p = estoque.criar_produto(dados, nome, "unidade")
    estoque.desativar_produto(dados, p["id"])
    return p


def _requisicao_pendente(
    dados,
    responsavel_id,
    produto_id,
    quantidade_pedida,
    data_pedido,
    observacoes="",
):
    """Cria uma requisição de um único item — atalho para os testes
    que não precisam de vários produtos ao mesmo tempo (decisão 20
    passou a exigir uma lista de itens em `criar_requisicao`).
    """
    return estoque.criar_requisicao(
        dados,
        responsavel_id,
        [
            {
                "produto_id": produto_id,
                "quantidade_pedida": quantidade_pedida,
            }
        ],
        data_pedido,
        observacoes,
    )


def _item_da_requisicao(dados, requisicao_id, produto_id):
    for item in estoque.listar_itens_requisicao(
        dados, requisicao_id=requisicao_id
    ):
        if item["produto_id"] == produto_id:
            return item

    return None


def _reportar_devolucao_1_item(
    dados,
    requisicao_id,
    responsavel_id,
    produto_id,
    quantidade,
    data_reportada,
):
    """Reporta uma devolução de um único item — atalho para os
    testes que não precisam de vários produtos ao mesmo tempo
    (decisão 20 passou a exigir uma lista de itens em
    `reportar_devolucao`).
    """
    return estoque.reportar_devolucao(
        dados,
        requisicao_id,
        responsavel_id,
        [{"produto_id": produto_id, "quantidade": quantidade}],
        data_reportada,
    )


def _item_da_devolucao(dados, devolucao_id, produto_id):
    for item in estoque.listar_itens_devolucao(
        dados, devolucao_id=devolucao_id
    ):
        if item["produto_id"] == produto_id:
            return item

    return None


# ---------------------------------------------------------------
# Produto
# ---------------------------------------------------------------


class TestCriarProduto(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()

    def test_cria_produto_valido(self):
        p = estoque.criar_produto(self.dados, "Toalhas", "unidade", 5)
        self.assertTrue(p["id"].startswith("PRD-"))
        self.assertEqual(p["nome"], "Toalhas")
        self.assertEqual(p["unidade_medida"], "unidade")
        self.assertEqual(p["stock_minimo"], 5)
        self.assertTrue(p["ativo"])
        self.assertIn(p, self.dados["produtos"])

    def test_stock_minimo_omisso_fica_zero(self):
        p = estoque.criar_produto(self.dados, "Toalhas", "unidade")
        self.assertEqual(p["stock_minimo"], 0)

    def test_remove_espacos_do_nome_e_unidade(self):
        p = estoque.criar_produto(self.dados, "  Toalhas  ", "  un  ")
        self.assertEqual(p["nome"], "Toalhas")
        self.assertEqual(p["unidade_medida"], "un")

    def test_nome_vazio_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_produto(self.dados, "   ", "unidade")

    def test_unidade_medida_vazia_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_produto(self.dados, "Toalhas", "  ")

    def test_stock_minimo_nao_inteiro_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_produto(self.dados, "Toalhas", "un", "5")  # type: ignore

    def test_stock_minimo_booleano_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_produto(self.dados, "Toalhas", "un", True)

    def test_stock_minimo_negativo_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_produto(self.dados, "Toalhas", "un", -1)


class TestProcurarProduto(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.produto = _produto_ativo(self.dados)

    def test_encontra_produto_existente(self):
        encontrado = estoque.procurar_produto(self.dados, self.produto["id"])
        self.assertEqual(encontrado, self.produto)

    def test_devolve_none_para_id_inexistente(self):
        self.assertIsNone(estoque.procurar_produto(self.dados, "PRD-999"))


class TestListarProdutos(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.ativo = _produto_ativo(self.dados, "Toalhas")
        self.inativo = _produto_inativo(self.dados, "Sabonetes")

    def test_lista_so_ativos_por_omissao(self):
        resultado = estoque.listar_produtos(self.dados)
        self.assertIn(self.ativo, resultado)
        self.assertNotIn(self.inativo, resultado)

    def test_lista_todos_com_incluir_inativos(self):
        resultado = estoque.listar_produtos(self.dados, incluir_inativos=True)
        self.assertIn(self.ativo, resultado)
        self.assertIn(self.inativo, resultado)

    def test_devolve_lista_nova(self):
        resultado = estoque.listar_produtos(self.dados)
        resultado.append("intruso")
        self.assertNotIn("intruso", self.dados["produtos"])


class TestAtualizarProduto(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.produto = _produto_ativo(self.dados, "Toalhas", "un")

    def test_altera_nome(self):
        atualizado = estoque.atualizar_produto(
            self.dados, self.produto["id"], nome="Lençóis"
        )
        self.assertEqual(atualizado["nome"], "Lençóis")

    def test_altera_unidade_medida(self):
        atualizado = estoque.atualizar_produto(
            self.dados, self.produto["id"], unidade_medida="kg"
        )
        self.assertEqual(atualizado["unidade_medida"], "kg")

    def test_altera_stock_minimo(self):
        atualizado = estoque.atualizar_produto(
            self.dados, self.produto["id"], stock_minimo=10
        )
        self.assertEqual(atualizado["stock_minimo"], 10)

    def test_none_nao_altera(self):
        atualizado = estoque.atualizar_produto(self.dados, self.produto["id"])
        self.assertEqual(atualizado["nome"], "Toalhas")
        self.assertEqual(atualizado["unidade_medida"], "un")

    def test_produto_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.atualizar_produto(self.dados, "PRD-999", nome="X")

    def test_nome_vazio_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.atualizar_produto(
                self.dados, self.produto["id"], nome="   "
            )

    def test_unidade_medida_vazia_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.atualizar_produto(
                self.dados, self.produto["id"], unidade_medida="  "
            )

    def test_stock_minimo_nao_inteiro_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.atualizar_produto(
                self.dados, self.produto["id"], stock_minimo="5"
            )

    def test_stock_minimo_negativo_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.atualizar_produto(
                self.dados, self.produto["id"], stock_minimo=-1
            )


class TestDesativarReativarProduto(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.produto = _produto_ativo(self.dados)

    def test_desativa_produto_ativo(self):
        p = estoque.desativar_produto(self.dados, self.produto["id"])
        self.assertFalse(p["ativo"])

    def test_desativar_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.desativar_produto(self.dados, "PRD-999")

    def test_desativar_ja_inativo_e_erro(self):
        estoque.desativar_produto(self.dados, self.produto["id"])
        with self.assertRaises(ValueError):
            estoque.desativar_produto(self.dados, self.produto["id"])

    def test_reativa_produto_inativo(self):
        estoque.desativar_produto(self.dados, self.produto["id"])
        p = estoque.reativar_produto(self.dados, self.produto["id"])
        self.assertTrue(p["ativo"])

    def test_reativar_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.reativar_produto(self.dados, "PRD-999")

    def test_reativar_ja_ativo_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.reativar_produto(self.dados, self.produto["id"])


# ---------------------------------------------------------------
# Movimento
# ---------------------------------------------------------------


class TestRegistarMovimento(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()

    def test_regista_entrada(self):
        m = estoque.registar_movimento(
            self.dados, self.produto["id"], "entrada", 20, self.hoje
        )
        self.assertTrue(m["id"].startswith("MOV-"))
        self.assertEqual(m["tipo"], "entrada")
        self.assertEqual(m["quantidade"], 20)
        self.assertIn(m, self.dados["movimentos"])

    def test_regista_saida(self):
        m = estoque.registar_movimento(
            self.dados, self.produto["id"], "saida", 5, self.hoje
        )
        self.assertEqual(m["tipo"], "saida")

    def test_regista_ajuste_com_motivo(self):
        m = estoque.registar_movimento(
            self.dados,
            self.produto["id"],
            "ajuste",
            -2,
            self.hoje,
            motivo="Contagem física",
        )
        self.assertEqual(m["quantidade"], -2)
        self.assertEqual(m["motivo"], "Contagem física")

    def test_ajuste_sem_motivo_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados, self.produto["id"], "ajuste", -2, self.hoje
            )

    def test_produto_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados, "PRD-999", "entrada", 10, self.hoje
            )

    def test_tipo_desconhecido_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados,
                self.produto["id"],
                "transferencia",
                10,
                self.hoje,
            )

    def test_quantidade_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados,
                self.produto["id"],
                "entrada",
                None,
                self.hoje,
            )

    def test_quantidade_nao_inteira_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados,
                self.produto["id"],
                "entrada",
                "10",
                self.hoje,
            )

    def test_quantidade_zero_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados, self.produto["id"], "entrada", 0, self.hoje
            )

    def test_quantidade_negativa_em_entrada_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados,
                self.produto["id"],
                "entrada",
                -5,
                self.hoje,
            )

    def test_quantidade_negativa_em_saida_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados, self.produto["id"], "saida", -5, self.hoje
            )

    def test_data_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados, self.produto["id"], "entrada", 10, None
            )

    def test_responsavel_id_vazio_e_aceite(self):
        m = estoque.registar_movimento(
            self.dados, self.produto["id"], "entrada", 10, self.hoje
        )
        self.assertEqual(m["responsavel_id"], "")

    def test_responsavel_id_valido_fica_gravado(self):
        responsavel = _responsavel_ativo(self.dados)
        m = estoque.registar_movimento(
            self.dados,
            self.produto["id"],
            "entrada",
            10,
            self.hoje,
            responsavel_id=responsavel["id"],
        )
        self.assertEqual(m["responsavel_id"], responsavel["id"])

    def test_responsavel_id_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados,
                self.produto["id"],
                "entrada",
                10,
                self.hoje,
                responsavel_id="RES-999",
            )

    def test_responsavel_id_inativo_e_erro(self):
        responsavel = _responsavel_inativo(self.dados)
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados,
                self.produto["id"],
                "entrada",
                10,
                self.hoje,
                responsavel_id=responsavel["id"],
            )


class TestSaldoProduto(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()

    def test_saldo_zero_sem_movimentos(self):
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto["id"]), 0
        )

    def test_saldo_soma_entradas_e_subtrai_saidas(self):
        estoque.registar_movimento(
            self.dados, self.produto["id"], "entrada", 20, self.hoje
        )
        estoque.registar_movimento(
            self.dados, self.produto["id"], "saida", 5, self.hoje
        )
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto["id"]), 15
        )

    def test_saldo_com_ajuste_positivo_e_negativo(self):
        estoque.registar_movimento(
            self.dados, self.produto["id"], "entrada", 10, self.hoje
        )
        estoque.registar_movimento(
            self.dados,
            self.produto["id"],
            "ajuste",
            -3,
            self.hoje,
            motivo="Contagem",
        )
        estoque.registar_movimento(
            self.dados,
            self.produto["id"],
            "ajuste",
            2,
            self.hoje,
            motivo="Contagem",
        )
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto["id"]), 9
        )

    def test_saldo_ignora_movimentos_de_outro_produto(self):
        outro = _produto_ativo(self.dados, "Outro", "un")
        estoque.registar_movimento(
            self.dados, outro["id"], "entrada", 50, self.hoje
        )
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto["id"]), 0
        )

    def test_produto_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.saldo_produto(self.dados, "PRD-999")


class TesteAlertasStock(unittest.TestCase):
    """Limiar de reposição: comparação e listagem (decisão 9)."""

    def setUp(self):
        self.dados = {
            "produtos": [
                {
                    "id": "PRD-001",
                    "nome": "Lençol branco",
                    "unidade_medida": "unidade",
                    "stock_minimo": 10,
                    "ativo": True,
                },
                {
                    "id": "PRD-002",
                    "nome": "Toalha de banho",
                    "unidade_medida": "unidade",
                    "stock_minimo": 5,
                    "ativo": True,
                },
                {
                    "id": "PRD-003",
                    "nome": "Fronha",
                    "unidade_medida": "unidade",
                    "stock_minimo": 0,
                    "ativo": True,
                },
                {
                    "id": "PRD-004",
                    "nome": "Cortina antiga",
                    "unidade_medida": "unidade",
                    "stock_minimo": 20,
                    "ativo": False,
                },
            ],
            "movimentos": [
                # PRD-001: 3 em stock, mínimo 10 → falta 7
                {
                    "id": "MOV-001",
                    "produto_id": "PRD-001",
                    "tipo": "entrada",
                    "quantidade": 3,
                    "data": date(2026, 9, 1),
                },
                # PRD-002: 5 em stock, mínimo 5 → na fronteira
                {
                    "id": "MOV-002",
                    "produto_id": "PRD-002",
                    "tipo": "entrada",
                    "quantidade": 5,
                    "data": date(2026, 9, 1),
                },
                # PRD-003: 8 em stock, mínimo 0
                {
                    "id": "MOV-003",
                    "produto_id": "PRD-003",
                    "tipo": "entrada",
                    "quantidade": 8,
                    "data": date(2026, 9, 1),
                },
                # PRD-004: 1 em stock, mínimo 20, mas inativo
                {
                    "id": "MOV-004",
                    "produto_id": "PRD-004",
                    "tipo": "entrada",
                    "quantidade": 1,
                    "data": date(2026, 9, 1),
                },
            ],
        }

    def test_abaixo_do_minimo_deteta(self):
        self.assertTrue(estoque.abaixo_do_minimo(self.dados, "PRD-001"))

    def test_saldo_igual_ao_minimo_nao_alerta(self):
        """A comparação é estrita: igual ao mínimo ainda chega."""
        self.assertFalse(estoque.abaixo_do_minimo(self.dados, "PRD-002"))

    def test_acima_do_minimo_nao_alerta(self):
        self.assertFalse(estoque.abaixo_do_minimo(self.dados, "PRD-003"))

    def test_minimo_zero_com_saldo_positivo_nao_alerta(self):
        self.assertFalse(estoque.abaixo_do_minimo(self.dados, "PRD-003"))

    def test_produto_inexistente_recusa(self):
        with self.assertRaises(ValueError):
            estoque.abaixo_do_minimo(self.dados, "PRD-999")

    def test_saldo_negativo_alerta_mesmo_sem_minimo(self):
        self.dados["movimentos"].append(
            {
                "id": "MOV-005",
                "produto_id": "PRD-003",
                "tipo": "saida",
                "quantidade": 12,
                "data": date(2026, 9, 2),
            }
        )
        self.assertTrue(estoque.abaixo_do_minimo(self.dados, "PRD-003"))

    def test_listagem_so_traz_os_que_faltam(self):
        alertas = estoque.listar_alertas_stock(self.dados)
        ids = [a["produto"]["id"] for a in alertas]
        self.assertEqual(ids, ["PRD-001"])

    def test_listagem_ignora_inativos(self):
        """PRD-004 tem 1 para um mínimo de 20, mas está inativo."""
        alertas = estoque.listar_alertas_stock(self.dados)
        ids = [a["produto"]["id"] for a in alertas]
        self.assertNotIn("PRD-004", ids)

    def test_listagem_calcula_em_falta(self):
        alertas = estoque.listar_alertas_stock(self.dados)
        self.assertEqual(alertas[0]["saldo"], 3)
        self.assertEqual(alertas[0]["em_falta"], 7)

    def test_listagem_ordena_pelo_que_falta_mais(self):
        self.dados["movimentos"].append(
            {
                "id": "MOV-006",
                "produto_id": "PRD-002",
                "tipo": "saida",
                "quantidade": 4,
                "data": date(2026, 9, 2),
            }
        )
        alertas = estoque.listar_alertas_stock(self.dados)
        ids = [a["produto"]["id"] for a in alertas]
        self.assertEqual(ids, ["PRD-001", "PRD-002"])

    def test_sem_alertas_devolve_lista_vazia(self):
        self.dados["movimentos"].append(
            {
                "id": "MOV-007",
                "produto_id": "PRD-001",
                "tipo": "entrada",
                "quantidade": 50,
                "data": date(2026, 9, 2),
            }
        )
        self.assertEqual(estoque.listar_alertas_stock(self.dados), [])


# ---------------------------------------------------------------
# Requisicao / ItemRequisicao
# ---------------------------------------------------------------


class TestCriarRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados)
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()

    def test_cria_requisicao_pendente(self):
        r = _requisicao_pendente(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            10,
            self.hoje,
        )
        self.assertTrue(r["id"].startswith("REQ-"))
        self.assertEqual(r["estado"], "pendente")
        self.assertIsNone(r["data_envio"])
        self.assertIn(r, self.dados["requisicoes"])

        item = _item_da_requisicao(self.dados, r["id"], self.produto["id"])
        if item is None:
            self.fail("Item de requisição não encontrado.")
        self.assertTrue(item["id"].startswith("ITR-"))
        self.assertEqual(item["requisicao_id"], r["id"])
        self.assertEqual(item["quantidade_pedida"], 10)
        self.assertEqual(item["quantidade_enviada"], 0)

    def test_cria_requisicao_com_varios_itens(self):
        outro_produto = _produto_ativo(self.dados, "Sabonetes")
        r = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            [
                {
                    "produto_id": self.produto["id"],
                    "quantidade_pedida": 10,
                },
                {
                    "produto_id": outro_produto["id"],
                    "quantidade_pedida": 5,
                },
            ],
            self.hoje,
        )
        itens = estoque.listar_itens_requisicao(
            self.dados, requisicao_id=r["id"]
        )
        self.assertEqual(len(itens), 2)
        self.assertEqual(
            {i["produto_id"] for i in itens},
            {self.produto["id"], outro_produto["id"]},
        )

    def test_itens_vazios_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados, self.responsavel["id"], [], self.hoje
            )

    def test_produto_repetido_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados,
                self.responsavel["id"],
                [
                    {
                        "produto_id": self.produto["id"],
                        "quantidade_pedida": 5,
                    },
                    {
                        "produto_id": self.produto["id"],
                        "quantidade_pedida": 3,
                    },
                ],
                self.hoje,
            )

    def test_responsavel_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            _requisicao_pendente(
                self.dados,
                "RES-999",
                self.produto["id"],
                10,
                self.hoje,
            )

    def test_responsavel_inativo_e_erro(self):
        inativo = _responsavel_inativo(self.dados)
        with self.assertRaises(ValueError):
            _requisicao_pendente(
                self.dados,
                inativo["id"],
                self.produto["id"],
                10,
                self.hoje,
            )

    def test_produto_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            _requisicao_pendente(
                self.dados,
                self.responsavel["id"],
                "PRD-999",
                10,
                self.hoje,
            )

    def test_produto_inativo_e_erro(self):
        inativo = _produto_inativo(self.dados)
        with self.assertRaises(ValueError):
            _requisicao_pendente(
                self.dados,
                self.responsavel["id"],
                inativo["id"],
                10,
                self.hoje,
            )

    def test_quantidade_pedida_none_e_erro(self):
        with self.assertRaises(ValueError):
            _requisicao_pendente(
                self.dados,
                self.responsavel["id"],
                self.produto["id"],
                None,
                self.hoje,
            )

    def test_quantidade_pedida_nao_inteira_e_erro(self):
        with self.assertRaises(ValueError):
            _requisicao_pendente(
                self.dados,
                self.responsavel["id"],
                self.produto["id"],
                "10",
                self.hoje,
            )

    def test_quantidade_pedida_zero_e_erro(self):
        with self.assertRaises(ValueError):
            _requisicao_pendente(
                self.dados,
                self.responsavel["id"],
                self.produto["id"],
                0,
                self.hoje,
            )

    def test_data_pedido_none_e_erro(self):
        with self.assertRaises(ValueError):
            _requisicao_pendente(
                self.dados,
                self.responsavel["id"],
                self.produto["id"],
                10,
                None,
            )

    def test_pode_pedir_mais_do_que_o_saldo(self):
        r = _requisicao_pendente(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            1000,
            self.hoje,
        )
        item = _item_da_requisicao(self.dados, r["id"], self.produto["id"])
        if item is None:
            self.fail("Item de requisição não encontrado.")
        self.assertEqual(item["quantidade_pedida"], 1000)


class TestListarItensRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados)
        self.produto_a = _produto_ativo(self.dados, "Toalhas")
        self.produto_b = _produto_ativo(self.dados, "Sabonetes")
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            [
                {
                    "produto_id": self.produto_a["id"],
                    "quantidade_pedida": 10,
                },
                {
                    "produto_id": self.produto_b["id"],
                    "quantidade_pedida": 5,
                },
            ],
            self.hoje,
        )

    def test_lista_todos_os_itens_da_requisicao(self):
        itens = estoque.listar_itens_requisicao(
            self.dados, requisicao_id=self.requisicao["id"]
        )
        self.assertEqual(len(itens), 2)

    def test_filtra_por_produto(self):
        itens = estoque.listar_itens_requisicao(
            self.dados, produto_id=self.produto_a["id"]
        )
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["produto_id"], self.produto_a["id"])

    def test_procurar_encontra_item_existente(self):
        item = _item_da_requisicao(
            self.dados, self.requisicao["id"], self.produto_a["id"]
        )
        if item is None:
            self.fail("Item de requisição não encontrado.")
        encontrado = estoque.procurar_item_requisicao(self.dados, item["id"])
        self.assertEqual(encontrado, item)

    def test_procurar_devolve_none_para_inexistente(self):
        self.assertIsNone(
            estoque.procurar_item_requisicao(self.dados, "ITR-999")
        )

    def test_listar_devolve_lista_nova(self):
        resultado = estoque.listar_itens_requisicao(self.dados)
        resultado.append("intruso")
        self.assertNotIn("intruso", self.dados["itens_requisicao"])


class TestProcurarListarRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.resp_a = _responsavel_ativo(self.dados, "Ana Ferreira")
        self.resp_b = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto_a = _produto_ativo(self.dados, "Toalhas")
        self.produto_b = _produto_ativo(self.dados, "Sabonetes")
        self.hoje = date.today()
        self.req_a = _requisicao_pendente(
            self.dados,
            self.resp_a["id"],
            self.produto_a["id"],
            10,
            self.hoje,
        )
        self.req_b = _requisicao_pendente(
            self.dados,
            self.resp_b["id"],
            self.produto_b["id"],
            5,
            self.hoje,
        )

    def test_procurar_encontra_requisicao_existente(self):
        encontrada = estoque.procurar_requisicao(self.dados, self.req_a["id"])
        self.assertEqual(encontrada, self.req_a)

    def test_procurar_devolve_none_para_inexistente(self):
        self.assertIsNone(estoque.procurar_requisicao(self.dados, "REQ-999"))

    def test_listar_sem_filtro_devolve_todas(self):
        resultado = estoque.listar_requisicoes(self.dados)
        self.assertEqual(len(resultado), 2)

    def test_listar_filtra_por_estado(self):
        estoque.rejeitar_requisicao(
            self.dados,
            self.req_b["id"],
            self.resp_a["id"],
            "Sem stock",
        )
        pendentes = estoque.listar_requisicoes(self.dados, estado="pendente")
        self.assertEqual(pendentes, [self.req_a])

    def test_listar_filtra_por_responsavel(self):
        resultado = estoque.listar_requisicoes(
            self.dados, responsavel_id=self.resp_a["id"]
        )
        self.assertEqual(resultado, [self.req_a])

    def test_listar_filtra_por_produto(self):
        resultado = estoque.listar_requisicoes(
            self.dados, produto_id=self.produto_b["id"]
        )
        self.assertEqual(resultado, [self.req_b])

    def test_listar_devolve_lista_nova(self):
        resultado = estoque.listar_requisicoes(self.dados)
        resultado.append("intruso")
        self.assertNotIn("intruso", self.dados["requisicoes"])


class TestEnviarRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados)
        self.admin = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto_a = _produto_ativo(self.dados, "Toalhas")
        self.produto_b = _produto_ativo(self.dados, "Sabonetes")
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            [
                {
                    "produto_id": self.produto_a["id"],
                    "quantidade_pedida": 10,
                },
                {
                    "produto_id": self.produto_b["id"],
                    "quantidade_pedida": 6,
                },
            ],
            self.hoje,
        )
        estoque.registar_movimento(
            self.dados, self.produto_a["id"], "entrada", 20, self.hoje
        )
        estoque.registar_movimento(
            self.dados, self.produto_b["id"], "entrada", 20, self.hoje
        )

    def test_envia_quantidade_pedida_por_omissao(self):
        r = estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            self.hoje,
        )
        self.assertEqual(r["estado"], "enviada")
        self.assertEqual(r["data_envio"], self.hoje)

        item_a = _item_da_requisicao(self.dados, r["id"], self.produto_a["id"])
        item_b = _item_da_requisicao(self.dados, r["id"], self.produto_b["id"])
        if item_a is None or item_b is None:
            self.fail("Item de requisição não encontrado.")
        self.assertEqual(item_a["quantidade_enviada"], 10)
        self.assertEqual(item_b["quantidade_enviada"], 6)
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto_a["id"]), 10
        )
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto_b["id"]), 14
        )

    def test_envio_parcial_de_um_item(self):
        r = estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            self.hoje,
            quantidades_enviadas={self.produto_a["id"]: 4},
        )
        item_a = _item_da_requisicao(self.dados, r["id"], self.produto_a["id"])
        item_b = _item_da_requisicao(self.dados, r["id"], self.produto_b["id"])
        if item_a is None or item_b is None:
            self.fail("Item de requisição não encontrado.")
        self.assertEqual(item_a["quantidade_enviada"], 4)
        self.assertEqual(item_b["quantidade_enviada"], 6)

    def test_gera_um_movimento_de_saida_por_item(self):
        estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            self.hoje,
        )
        movimentos = [
            m
            for m in self.dados["movimentos"]
            if m["requisicao_id"] == self.requisicao["id"]
        ]
        self.assertEqual(len(movimentos), 2)
        self.assertTrue(all(m["tipo"] == "saida" for m in movimentos))

    def test_requisicao_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados, "REQ-999", self.admin["id"], self.hoje
            )

    def test_requisicao_nao_pendente_e_erro(self):
        estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                self.hoje,
            )

    def test_enviado_por_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados, self.requisicao["id"], "RES-999", self.hoje
            )

    def test_quantidade_enviada_excede_pedida_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                self.hoje,
                quantidades_enviadas={self.produto_a["id"]: 11},
            )

    def test_quantidade_enviada_nao_positiva_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                self.hoje,
                quantidades_enviadas={self.produto_a["id"]: 0},
            )

    def test_produto_fora_da_requisicao_e_erro(self):
        outro = _produto_ativo(self.dados, "Champô")
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                self.hoje,
                quantidades_enviadas={outro["id"]: 1},
            )

    def test_saldo_insuficiente_e_erro(self):
        requisicao_grande = _requisicao_pendente(
            self.dados,
            self.responsavel["id"],
            self.produto_a["id"],
            1000,
            self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados,
                requisicao_grande["id"],
                self.admin["id"],
                self.hoje,
            )

    def test_saldo_insuficiente_num_item_nao_envia_nenhum(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                self.hoje,
                quantidades_enviadas={self.produto_b["id"]: 100},
            )
        self.assertEqual(len(self.dados["movimentos"]), 2)
        item_a = _item_da_requisicao(
            self.dados, self.requisicao["id"], self.produto_a["id"]
        )
        if item_a is None:
            self.fail("Item de requisição não encontrado.")
        self.assertEqual(item_a["quantidade_enviada"], 0)
        self.assertEqual(self.requisicao["estado"], "pendente")

    def test_data_envio_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                None,
            )


class TestRejeitarRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados)
        self.admin = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()
        self.requisicao = _requisicao_pendente(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            10,
            self.hoje,
        )

    def test_rejeita_requisicao_pendente(self):
        r = estoque.rejeitar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            "Sem stock disponível",
        )
        self.assertEqual(r["estado"], "rejeitada")
        self.assertEqual(r["motivo_rejeicao"], "Sem stock disponível")
        self.assertEqual(r["responsavel_rejeicao_id"], self.admin["id"])

    def test_nao_gera_movimento(self):
        estoque.rejeitar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            "Sem stock",
        )
        self.assertEqual(len(self.dados["movimentos"]), 0)

    def test_requisicao_nao_pendente_e_erro(self):
        estoque.rejeitar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            "Sem stock",
        )
        with self.assertRaises(ValueError):
            estoque.rejeitar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                "De novo",
            )

    def test_motivo_vazio_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.rejeitar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                "   ",
            )

    def test_responsavel_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.rejeitar_requisicao(
                self.dados,
                self.requisicao["id"],
                "RES-999",
                "Sem stock",
            )


class TestConfirmarRececaoRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados, "Ana Ferreira")
        self.outro = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()
        self.requisicao = _requisicao_pendente(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            10,
            self.hoje,
        )
        estoque.registar_movimento(
            self.dados, self.produto["id"], "entrada", 20, self.hoje
        )
        estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.outro["id"],
            self.hoje,
        )

    def test_confirma_rececao_fecha_a_requisicao(self):
        amanha = self.hoje + timedelta(days=1)
        r = estoque.confirmar_rececao_requisicao(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            amanha,
        )
        self.assertEqual(r["estado"], "fechada")
        self.assertEqual(r["data_fecho"], amanha)

    def test_requisicao_nao_enviada_e_erro(self):
        pendente = _requisicao_pendente(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            5,
            self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.confirmar_rececao_requisicao(
                self.dados,
                pendente["id"],
                self.responsavel["id"],
                self.hoje,
            )

    def test_responsavel_diferente_do_que_pediu_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.confirmar_rececao_requisicao(
                self.dados,
                self.requisicao["id"],
                self.outro["id"],
                self.hoje,
            )

    def test_responsavel_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.confirmar_rececao_requisicao(
                self.dados, self.requisicao["id"], "RES-999", self.hoje
            )

    def test_data_rececao_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.confirmar_rececao_requisicao(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                None,
            )


# ---------------------------------------------------------------
# Devolucao / ItemDevolucao
# ---------------------------------------------------------------


class TestReportarDevolucao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados, "Ana Ferreira")
        self.outro = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto_a = _produto_ativo(self.dados, "Toalhas")
        self.produto_b = _produto_ativo(self.dados, "Sabonetes")
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            [
                {
                    "produto_id": self.produto_a["id"],
                    "quantidade_pedida": 10,
                },
                {
                    "produto_id": self.produto_b["id"],
                    "quantidade_pedida": 5,
                },
            ],
            self.hoje,
        )
        estoque.registar_movimento(
            self.dados, self.produto_a["id"], "entrada", 20, self.hoje
        )
        estoque.registar_movimento(
            self.dados, self.produto_b["id"], "entrada", 20, self.hoje
        )
        estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.outro["id"],
            self.hoje,
        )
        estoque.confirmar_rececao_requisicao(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            self.hoje,
        )

    def test_reporta_sobra(self):
        d = _reportar_devolucao_1_item(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            self.produto_a["id"],
            3,
            self.hoje,
        )
        self.assertTrue(d["id"].startswith("DEV-"))
        self.assertEqual(d["requisicao_id"], self.requisicao["id"])
        self.assertEqual(d["responsavel_id"], self.responsavel["id"])
        self.assertEqual(d["estado"], "pendente")
        self.assertEqual(d["data_reportada"], self.hoje)
        self.assertIn(d, self.dados["devolucoes"])

        item = _item_da_devolucao(self.dados, d["id"], self.produto_a["id"])
        if item is None:
            self.fail("Item de devolução não encontrado.")
        self.assertTrue(item["id"].startswith("ITD-"))
        self.assertEqual(item["quantidade"], 3)

    def test_reporta_sobra_varios_itens(self):
        d = estoque.reportar_devolucao(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            [
                {"produto_id": self.produto_a["id"], "quantidade": 3},
                {"produto_id": self.produto_b["id"], "quantidade": 2},
            ],
            self.hoje,
        )
        itens = estoque.listar_itens_devolucao(
            self.dados, devolucao_id=d["id"]
        )
        self.assertEqual(len(itens), 2)

    def test_nao_gera_movimento(self):
        total_antes = len(self.dados["movimentos"])
        _reportar_devolucao_1_item(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            self.produto_a["id"],
            3,
            self.hoje,
        )
        self.assertEqual(len(self.dados["movimentos"]), total_antes)

    def test_itens_vazios_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.reportar_devolucao(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                [],
                self.hoje,
            )

    def test_produto_repetido_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.reportar_devolucao(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                [
                    {
                        "produto_id": self.produto_a["id"],
                        "quantidade": 1,
                    },
                    {
                        "produto_id": self.produto_a["id"],
                        "quantidade": 2,
                    },
                ],
                self.hoje,
            )

    def test_produto_fora_da_requisicao_e_erro(self):
        outro_produto = _produto_ativo(self.dados, "Champô")
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                outro_produto["id"],
                1,
                self.hoje,
            )

    def test_quantidade_zero_e_erro(self):
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                self.produto_a["id"],
                0,
                self.hoje,
            )

    def test_quantidade_negativa_e_erro(self):
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                self.produto_a["id"],
                -1,
                self.hoje,
            )

    def test_quantidade_nao_inteira_e_erro(self):
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                self.produto_a["id"],
                "3",
                self.hoje,
            )

    def test_quantidade_excede_enviada_e_erro(self):
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                self.produto_a["id"],
                11,
                self.hoje,
            )

    def test_soma_de_devolucoes_excede_enviada_e_erro(self):
        _reportar_devolucao_1_item(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            self.produto_a["id"],
            6,
            self.hoje,
        )
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                self.produto_a["id"],
                5,
                self.hoje,
            )

    def test_requisicao_nao_fechada_e_erro(self):
        outra = _requisicao_pendente(
            self.dados,
            self.responsavel["id"],
            self.produto_a["id"],
            5,
            self.hoje,
        )
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                outra["id"],
                self.responsavel["id"],
                self.produto_a["id"],
                1,
                self.hoje,
            )

    def test_responsavel_diferente_do_que_pediu_e_erro(self):
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                self.requisicao["id"],
                self.outro["id"],
                self.produto_a["id"],
                1,
                self.hoje,
            )

    def test_data_reportada_none_e_erro(self):
        with self.assertRaises(ValueError):
            _reportar_devolucao_1_item(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                self.produto_a["id"],
                1,
                None,
            )


class TestListarItensDevolucao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados)
        self.outro = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto_a = _produto_ativo(self.dados, "Toalhas")
        self.produto_b = _produto_ativo(self.dados, "Sabonetes")
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            [
                {
                    "produto_id": self.produto_a["id"],
                    "quantidade_pedida": 10,
                },
                {
                    "produto_id": self.produto_b["id"],
                    "quantidade_pedida": 5,
                },
            ],
            self.hoje,
        )
        estoque.registar_movimento(
            self.dados, self.produto_a["id"], "entrada", 20, self.hoje
        )
        estoque.registar_movimento(
            self.dados, self.produto_b["id"], "entrada", 20, self.hoje
        )
        estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.outro["id"],
            self.hoje,
        )
        estoque.confirmar_rececao_requisicao(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            self.hoje,
        )
        self.devolucao = estoque.reportar_devolucao(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            [
                {"produto_id": self.produto_a["id"], "quantidade": 3},
                {"produto_id": self.produto_b["id"], "quantidade": 2},
            ],
            self.hoje,
        )

    def test_lista_todos_os_itens_da_devolucao(self):
        itens = estoque.listar_itens_devolucao(
            self.dados, devolucao_id=self.devolucao["id"]
        )
        self.assertEqual(len(itens), 2)

    def test_filtra_por_produto(self):
        itens = estoque.listar_itens_devolucao(
            self.dados, produto_id=self.produto_a["id"]
        )
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["produto_id"], self.produto_a["id"])

    def test_procurar_encontra_item_existente(self):
        item = _item_da_devolucao(
            self.dados, self.devolucao["id"], self.produto_a["id"]
        )
        if item is None:
            self.fail("Item de devolução não encontrado.")
        encontrado = estoque.procurar_item_devolucao(self.dados, item["id"])
        self.assertEqual(encontrado, item)

    def test_procurar_devolve_none_para_inexistente(self):
        self.assertIsNone(
            estoque.procurar_item_devolucao(self.dados, "ITD-999")
        )

    def test_listar_devolve_lista_nova(self):
        resultado = estoque.listar_itens_devolucao(self.dados)
        resultado.append("intruso")
        self.assertNotIn("intruso", self.dados["itens_devolucao"])


class TestProcurarListarDevolucao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.resp_a = _responsavel_ativo(self.dados, "Ana Ferreira")
        self.resp_b = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()
        self.req_a = _requisicao_pendente(
            self.dados,
            self.resp_a["id"],
            self.produto["id"],
            10,
            self.hoje,
        )
        self.req_b = _requisicao_pendente(
            self.dados,
            self.resp_b["id"],
            self.produto["id"],
            5,
            self.hoje,
        )
        estoque.registar_movimento(
            self.dados, self.produto["id"], "entrada", 30, self.hoje
        )
        estoque.enviar_requisicao(
            self.dados,
            self.req_a["id"],
            self.resp_b["id"],
            self.hoje,
        )
        estoque.enviar_requisicao(
            self.dados,
            self.req_b["id"],
            self.resp_a["id"],
            self.hoje,
        )
        estoque.confirmar_rececao_requisicao(
            self.dados,
            self.req_a["id"],
            self.resp_a["id"],
            self.hoje,
        )
        estoque.confirmar_rececao_requisicao(
            self.dados,
            self.req_b["id"],
            self.resp_b["id"],
            self.hoje,
        )
        self.dev_a = _reportar_devolucao_1_item(
            self.dados,
            self.req_a["id"],
            self.resp_a["id"],
            self.produto["id"],
            2,
            self.hoje,
        )
        self.dev_b = _reportar_devolucao_1_item(
            self.dados,
            self.req_b["id"],
            self.resp_b["id"],
            self.produto["id"],
            1,
            self.hoje,
        )

    def test_procurar_encontra_devolucao_existente(self):
        encontrada = estoque.procurar_devolucao(self.dados, self.dev_a["id"])
        self.assertEqual(encontrada, self.dev_a)

    def test_procurar_devolve_none_para_inexistente(self):
        self.assertIsNone(estoque.procurar_devolucao(self.dados, "DEV-999"))

    def test_listar_sem_filtro_devolve_todas(self):
        resultado = estoque.listar_devolucoes(self.dados)
        self.assertEqual(len(resultado), 2)

    def test_listar_filtra_por_estado(self):
        estoque.fechar_devolucao(
            self.dados,
            self.dev_a["id"],
            self.resp_b["id"],
            self.hoje,
        )
        pendentes = estoque.listar_devolucoes(self.dados, estado="pendente")
        self.assertEqual(pendentes, [self.dev_b])

    def test_listar_filtra_por_requisicao(self):
        resultado = estoque.listar_devolucoes(
            self.dados, requisicao_id=self.req_b["id"]
        )
        self.assertEqual(resultado, [self.dev_b])

    def test_listar_filtra_por_responsavel(self):
        resultado = estoque.listar_devolucoes(
            self.dados, responsavel_id=self.resp_a["id"]
        )
        self.assertEqual(resultado, [self.dev_a])

    def test_listar_devolve_lista_nova(self):
        resultado = estoque.listar_devolucoes(self.dados)
        resultado.append("intruso")
        self.assertNotIn("intruso", self.dados["devolucoes"])


class TestFecharDevolucao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados, "Ana Ferreira")
        self.admin = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto_a = _produto_ativo(self.dados, "Toalhas")
        self.produto_b = _produto_ativo(self.dados, "Sabonetes")
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            [
                {
                    "produto_id": self.produto_a["id"],
                    "quantidade_pedida": 10,
                },
                {
                    "produto_id": self.produto_b["id"],
                    "quantidade_pedida": 5,
                },
            ],
            self.hoje,
        )
        estoque.registar_movimento(
            self.dados, self.produto_a["id"], "entrada", 20, self.hoje
        )
        estoque.registar_movimento(
            self.dados, self.produto_b["id"], "entrada", 20, self.hoje
        )
        estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            self.hoje,
        )
        estoque.confirmar_rececao_requisicao(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            self.hoje,
        )
        self.devolucao = estoque.reportar_devolucao(
            self.dados,
            self.requisicao["id"],
            self.responsavel["id"],
            [
                {"produto_id": self.produto_a["id"], "quantidade": 4},
                {"produto_id": self.produto_b["id"], "quantidade": 2},
            ],
            self.hoje,
        )

    def test_fecha_gera_movimento_de_entrada_por_item(self):
        saldo_a_antes = estoque.saldo_produto(self.dados, self.produto_a["id"])
        saldo_b_antes = estoque.saldo_produto(self.dados, self.produto_b["id"])
        d = estoque.fechar_devolucao(
            self.dados,
            self.devolucao["id"],
            self.admin["id"],
            self.hoje,
        )
        self.assertEqual(d["estado"], "fechada")
        self.assertEqual(d["data_fecho"], self.hoje)
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto_a["id"]),
            saldo_a_antes + 4,
        )
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto_b["id"]),
            saldo_b_antes + 2,
        )

        movimentos = [
            m
            for m in self.dados["movimentos"]
            if m["requisicao_id"] == self.requisicao["id"]
            and m["tipo"] == "entrada"
        ]
        self.assertEqual(len(movimentos), 2)

    def test_devolucao_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.fechar_devolucao(
                self.dados, "DEV-999", self.admin["id"], self.hoje
            )

    def test_devolucao_nao_pendente_e_erro(self):
        estoque.fechar_devolucao(
            self.dados,
            self.devolucao["id"],
            self.admin["id"],
            self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.fechar_devolucao(
                self.dados,
                self.devolucao["id"],
                self.admin["id"],
                self.hoje,
            )

    def test_aceite_por_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.fechar_devolucao(
                self.dados, self.devolucao["id"], "RES-999", self.hoje
            )

    def test_data_fecho_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.fechar_devolucao(
                self.dados,
                self.devolucao["id"],
                self.admin["id"],
                None,
            )


if __name__ == "__main__":
    unittest.main()
