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
            estoque.criar_produto(self.dados, "Toalhas", "un", "5") # type: ignore

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
        encontrado = estoque.procurar_produto(
            self.dados, self.produto["id"]
        )
        self.assertEqual(encontrado, self.produto)

    def test_devolve_none_para_id_inexistente(self):
        self.assertIsNone(
            estoque.procurar_produto(self.dados, "PRD-999")
        )


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
        resultado = estoque.listar_produtos(
            self.dados, incluir_inativos=True
        )
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
        atualizado = estoque.atualizar_produto(
            self.dados, self.produto["id"]
        )
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
                self.dados, self.produto["id"], "entrada", None,
                self.hoje,
            )

    def test_quantidade_nao_inteira_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.registar_movimento(
                self.dados, self.produto["id"], "entrada", "10",
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
                self.dados, self.produto["id"], "entrada", -5,
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


# ---------------------------------------------------------------
# Requisicao
# ---------------------------------------------------------------


class TestCriarRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados)
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()

    def test_cria_requisicao_pendente(self):
        r = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            10,
            self.hoje,
        )
        self.assertTrue(r["id"].startswith("REQ-"))
        self.assertEqual(r["estado"], "pendente")
        self.assertEqual(r["quantidade_pedida"], 10)
        self.assertEqual(r["quantidade_enviada"], 0)
        self.assertEqual(r["quantidade_devolvida"], 0)
        self.assertIsNone(r["data_envio"])
        self.assertIn(r, self.dados["requisicoes"])

    def test_responsavel_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados, "RES-999", self.produto["id"], 10,
                self.hoje,
            )

    def test_responsavel_inativo_e_erro(self):
        inativo = _responsavel_inativo(self.dados)
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados, inativo["id"], self.produto["id"], 10,
                self.hoje,
            )

    def test_produto_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados, self.responsavel["id"], "PRD-999", 10,
                self.hoje,
            )

    def test_produto_inativo_e_erro(self):
        inativo = _produto_inativo(self.dados)
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados,
                self.responsavel["id"],
                inativo["id"],
                10,
                self.hoje,
            )

    def test_quantidade_pedida_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados,
                self.responsavel["id"],
                self.produto["id"],
                None,
                self.hoje,
            )

    def test_quantidade_pedida_nao_inteira_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados,
                self.responsavel["id"],
                self.produto["id"],
                "10",
                self.hoje,
            )

    def test_quantidade_pedida_zero_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados,
                self.responsavel["id"],
                self.produto["id"],
                0,
                self.hoje,
            )

    def test_data_pedido_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.criar_requisicao(
                self.dados,
                self.responsavel["id"],
                self.produto["id"],
                10,
                None,
            )

    def test_pode_pedir_mais_do_que_o_saldo(self):
        r = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            1000,
            self.hoje,
        )
        self.assertEqual(r["quantidade_pedida"], 1000)


class TestProcurarListarRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.resp_a = _responsavel_ativo(self.dados, "Ana Ferreira")
        self.resp_b = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto_a = _produto_ativo(self.dados, "Toalhas")
        self.produto_b = _produto_ativo(self.dados, "Sabonetes")
        self.hoje = date.today()
        self.req_a = estoque.criar_requisicao(
            self.dados, self.resp_a["id"], self.produto_a["id"], 10,
            self.hoje,
        )
        self.req_b = estoque.criar_requisicao(
            self.dados, self.resp_b["id"], self.produto_b["id"], 5,
            self.hoje,
        )

    def test_procurar_encontra_requisicao_existente(self):
        encontrada = estoque.procurar_requisicao(
            self.dados, self.req_a["id"]
        )
        self.assertEqual(encontrada, self.req_a)

    def test_procurar_devolve_none_para_inexistente(self):
        self.assertIsNone(
            estoque.procurar_requisicao(self.dados, "REQ-999")
        )

    def test_listar_sem_filtro_devolve_todas(self):
        resultado = estoque.listar_requisicoes(self.dados)
        self.assertEqual(len(resultado), 2)

    def test_listar_filtra_por_estado(self):
        estoque.rejeitar_requisicao(
            self.dados, self.req_b["id"], self.resp_a["id"],
            "Sem stock",
        )
        pendentes = estoque.listar_requisicoes(
            self.dados, estado="pendente"
        )
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
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            10,
            self.hoje,
        )
        estoque.registar_movimento(
            self.dados, self.produto["id"], "entrada", 20, self.hoje
        )

    def test_envia_quantidade_pedida_por_omissao(self):
        r = estoque.enviar_requisicao(
            self.dados, self.requisicao["id"], self.admin["id"],
            self.hoje,
        )
        self.assertEqual(r["estado"], "enviada")
        self.assertEqual(r["quantidade_enviada"], 10)
        self.assertEqual(r["data_envio"], self.hoje)
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto["id"]), 10
        )

    def test_envio_parcial(self):
        r = estoque.enviar_requisicao(
            self.dados,
            self.requisicao["id"],
            self.admin["id"],
            self.hoje,
            quantidade_enviada=4,
        )
        self.assertEqual(r["quantidade_enviada"], 4)
        self.assertEqual(
            estoque.saldo_produto(self.dados, self.produto["id"]), 16
        )

    def test_gera_movimento_de_saida_ligado_a_requisicao(self):
        estoque.enviar_requisicao(
            self.dados, self.requisicao["id"], self.admin["id"],
            self.hoje,
        )
        movimentos = [
            m
            for m in self.dados["movimentos"]
            if m["requisicao_id"] == self.requisicao["id"]
        ]
        self.assertEqual(len(movimentos), 1)
        self.assertEqual(movimentos[0]["tipo"], "saida")

    def test_requisicao_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados, "REQ-999", self.admin["id"], self.hoje
            )

    def test_requisicao_nao_pendente_e_erro(self):
        estoque.enviar_requisicao(
            self.dados, self.requisicao["id"], self.admin["id"],
            self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados, self.requisicao["id"], self.admin["id"],
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
                quantidade_enviada=11,
            )

    def test_quantidade_enviada_nao_positiva_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados,
                self.requisicao["id"],
                self.admin["id"],
                self.hoje,
                quantidade_enviada=0,
            )

    def test_saldo_insuficiente_e_erro(self):
        requisicao_grande = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
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

    def test_data_envio_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.enviar_requisicao(
                self.dados, self.requisicao["id"], self.admin["id"],
                None,
            )


class TestRejeitarRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(self.dados)
        self.admin = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
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
        self.assertEqual(
            r["responsavel_rejeicao_id"], self.admin["id"]
        )

    def test_nao_gera_movimento(self):
        estoque.rejeitar_requisicao(
            self.dados, self.requisicao["id"], self.admin["id"],
            "Sem stock",
        )
        self.assertEqual(len(self.dados["movimentos"]), 0)

    def test_requisicao_nao_pendente_e_erro(self):
        estoque.rejeitar_requisicao(
            self.dados, self.requisicao["id"], self.admin["id"],
            "Sem stock",
        )
        with self.assertRaises(ValueError):
            estoque.rejeitar_requisicao(
                self.dados, self.requisicao["id"], self.admin["id"],
                "De novo",
            )

    def test_motivo_vazio_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.rejeitar_requisicao(
                self.dados, self.requisicao["id"], self.admin["id"],
                "   ",
            )

    def test_responsavel_inexistente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.rejeitar_requisicao(
                self.dados, self.requisicao["id"], "RES-999",
                "Sem stock",
            )


class TestConfirmarRececaoRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(
            self.dados, "Ana Ferreira"
        )
        self.outro = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
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
            self.dados, self.requisicao["id"], self.outro["id"],
            self.hoje,
        )

    def test_confirma_rececao(self):
        amanha = self.hoje + timedelta(days=1)
        r = estoque.confirmar_rececao_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            amanha,
        )
        self.assertEqual(r["estado"], "recebida")
        self.assertEqual(r["data_rececao"], amanha)

    def test_requisicao_nao_enviada_e_erro(self):
        pendente = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            5,
            self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.confirmar_rececao_requisicao(
                self.dados, pendente["id"], self.responsavel["id"],
                self.hoje,
            )

    def test_responsavel_diferente_do_que_pediu_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.confirmar_rececao_requisicao(
                self.dados, self.requisicao["id"], self.outro["id"],
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


class TestDevolverRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(
            self.dados, "Ana Ferreira"
        )
        self.outro = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
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
            self.dados, self.requisicao["id"], self.outro["id"],
            self.hoje,
        )
        estoque.confirmar_rececao_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            self.hoje,
        )

    def test_devolve_sobra(self):
        r = estoque.devolver_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            3, self.hoje,
        )
        self.assertEqual(r["estado"], "devolucao_pendente")
        self.assertEqual(r["quantidade_devolvida"], 3)
        self.assertEqual(r["data_devolucao"], self.hoje)

    def test_devolve_zero_quando_nao_sobra_nada(self):
        r = estoque.devolver_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            0, self.hoje,
        )
        self.assertEqual(r["estado"], "devolucao_pendente")
        self.assertEqual(r["quantidade_devolvida"], 0)

    def test_nao_gera_movimento(self):
        total_antes = len(self.dados["movimentos"])
        estoque.devolver_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            3, self.hoje,
        )
        self.assertEqual(len(self.dados["movimentos"]), total_antes)

    def test_quantidade_negativa_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.devolver_requisicao(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                -1,
                self.hoje,
            )

    def test_quantidade_excede_enviada_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.devolver_requisicao(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                11,
                self.hoje,
            )

    def test_requisicao_nao_recebida_e_erro(self):
        outra = estoque.criar_requisicao(
            self.dados,
            self.responsavel["id"],
            self.produto["id"],
            5,
            self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.devolver_requisicao(
                self.dados, outra["id"], self.responsavel["id"], 1,
                self.hoje,
            )

    def test_responsavel_diferente_do_que_recebeu_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.devolver_requisicao(
                self.dados, self.requisicao["id"], self.outro["id"],
                1, self.hoje,
            )

    def test_data_devolucao_none_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.devolver_requisicao(
                self.dados,
                self.requisicao["id"],
                self.responsavel["id"],
                1,
                None,
            )


class TestFecharRequisicao(unittest.TestCase):

    def setUp(self):
        self.dados = _dados()
        self.responsavel = _responsavel_ativo(
            self.dados, "Ana Ferreira"
        )
        self.admin = _responsavel_ativo(self.dados, "Bruno Alves")
        self.produto = _produto_ativo(self.dados)
        self.hoje = date.today()
        self.requisicao = estoque.criar_requisicao(
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
            self.dados, self.requisicao["id"], self.admin["id"],
            self.hoje,
        )
        estoque.confirmar_rececao_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            self.hoje,
        )

    def test_fecha_com_devolucao_gera_movimento_de_entrada(self):
        estoque.devolver_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            4, self.hoje,
        )
        saldo_antes = estoque.saldo_produto(
            self.dados, self.produto["id"]
        )
        r = estoque.fechar_requisicao(
            self.dados, self.requisicao["id"], self.admin["id"],
            self.hoje,
        )
        self.assertEqual(r["estado"], "fechada")
        saldo_depois = estoque.saldo_produto(
            self.dados, self.produto["id"]
        )
        self.assertEqual(saldo_depois, saldo_antes + 4)

    def test_fecha_sem_devolucao_nao_gera_movimento(self):
        estoque.devolver_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            0, self.hoje,
        )
        total_antes = len(self.dados["movimentos"])
        estoque.fechar_requisicao(
            self.dados, self.requisicao["id"], self.admin["id"],
            self.hoje,
        )
        self.assertEqual(len(self.dados["movimentos"]), total_antes)

    def test_requisicao_sem_devolucao_pendente_e_erro(self):
        with self.assertRaises(ValueError):
            estoque.fechar_requisicao(
                self.dados, self.requisicao["id"], self.admin["id"],
                self.hoje,
            )

    def test_aceite_por_inexistente_e_erro(self):
        estoque.devolver_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            2, self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.fechar_requisicao(
                self.dados, self.requisicao["id"], "RES-999", self.hoje
            )

    def test_data_fecho_none_e_erro(self):
        estoque.devolver_requisicao(
            self.dados, self.requisicao["id"], self.responsavel["id"],
            2, self.hoje,
        )
        with self.assertRaises(ValueError):
            estoque.fechar_requisicao(
                self.dados, self.requisicao["id"], self.admin["id"],
                None,
            )


if __name__ == "__main__":
    unittest.main()