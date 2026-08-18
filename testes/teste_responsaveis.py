"""Testes do módulo responsaveis.

Cobrem as sete funções: as seis do padrão (criar, procurar, listar,
atualizar, desativar, reativar) e a validar_autoria, que autoriza
operações de outros módulos.

Os dados são construídos em memória — nenhum teste lê ou grava o
ficheiro de dados. A exceção conhecida é `repositorio.proximo_id()`,
que escreve em dados/contadores.json mesmo durante os testes; é o
precedente já aceite em teste_propriedades.py e teste_unidades.py.
"""

import sys
import unittest

sys.path.insert(0, "src")

import responsaveis  # noqa: E402


def estrutura():
    """Devolve a estrutura mínima de dados usada pelos testes."""
    return {"responsaveis": []}


class TesteCriar(unittest.TestCase):
    """criar() — o nome bloqueia, o contacto não."""

    def setUp(self):
        self.dados = estrutura()

    def teste_devolve_registo_com_todos_os_campos(self):
        r = responsaveis.criar(self.dados, "Ana Silva", "912345678")

        self.assertEqual(sorted(r.keys()), ["ativo", "contacto", "id", "nome"])

    def teste_id_comeca_pelo_prefixo(self):
        r = responsaveis.criar(self.dados, "Ana Silva")

        self.assertTrue(r["id"].startswith("RES-"))

    def teste_prefixo_do_modulo_e_res(self):
        self.assertEqual(responsaveis.PREFIXO, "RES")

    def teste_ids_seguidos_sao_diferentes(self):
        primeiro = responsaveis.criar(self.dados, "Ana")
        segundo = responsaveis.criar(self.dados, "Bruno")

        self.assertNotEqual(primeiro["id"], segundo["id"])

    def teste_nasce_ativo(self):
        r = responsaveis.criar(self.dados, "Ana Silva")

        self.assertTrue(r["ativo"])

    def teste_contacto_por_omissao_fica_vazio(self):
        r = responsaveis.criar(self.dados, "Ana Silva")

        self.assertEqual(r["contacto"], "")

    def teste_guarda_o_contacto_indicado(self):
        r = responsaveis.criar(self.dados, "Ana Silva", "912345678")

        self.assertEqual(r["contacto"], "912345678")

    def teste_retira_espacos_do_nome(self):
        r = responsaveis.criar(self.dados, "  Ana Silva  ")

        self.assertEqual(r["nome"], "Ana Silva")

    def teste_retira_espacos_do_contacto(self):
        r = responsaveis.criar(self.dados, "Ana", "  912345678  ")

        self.assertEqual(r["contacto"], "912345678")

    def teste_acrescenta_a_estrutura_de_dados(self):
        r = responsaveis.criar(self.dados, "Ana Silva")

        self.assertIn(r, self.dados["responsaveis"])
        self.assertEqual(len(self.dados["responsaveis"]), 1)

    def teste_nome_vazio_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.criar(self.dados, "")

    def teste_nome_so_com_espacos_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.criar(self.dados, "   ")

    def teste_nome_recusado_nao_deixa_registo(self):
        with self.assertRaises(ValueError):
            responsaveis.criar(self.dados, "  ")

        self.assertEqual(self.dados["responsaveis"], [])


class TesteProcurar(unittest.TestCase):
    """procurar() — não filtra inativos: lê o passado."""

    def setUp(self):
        self.dados = estrutura()
        self.ana = responsaveis.criar(self.dados, "Ana Silva")

    def teste_encontra_pelo_id(self):
        encontrado = responsaveis.procurar(self.dados, self.ana["id"])

        self.assertEqual(encontrado["nome"], "Ana Silva")  # type: ignore

    def teste_devolve_o_proprio_registo(self):
        encontrado = responsaveis.procurar(self.dados, self.ana["id"])

        self.assertIs(encontrado, self.ana)

    def teste_id_inexistente_devolve_none(self):
        self.assertIsNone(responsaveis.procurar(self.dados, "RES-999"))

    def teste_estrutura_vazia_devolve_none(self):
        self.assertIsNone(responsaveis.procurar(estrutura(), "RES-001"))

    def teste_encontra_responsavel_inativo(self):
        responsaveis.desativar(self.dados, self.ana["id"])
        encontrado = responsaveis.procurar(self.dados, self.ana["id"])

        self.assertIsNotNone(encontrado)
        self.assertFalse(encontrado["ativo"])  # type: ignore


class TesteListar(unittest.TestCase):
    """listar() — ativos por omissão, lista sempre nova."""

    def setUp(self):
        self.dados = estrutura()
        self.ana = responsaveis.criar(self.dados, "Ana Silva")
        self.bruno = responsaveis.criar(self.dados, "Bruno Costa")

    def teste_estrutura_vazia_devolve_lista_vazia(self):
        self.assertEqual(responsaveis.listar(estrutura()), [])

    def teste_devolve_todos_os_ativos(self):
        self.assertEqual(len(responsaveis.listar(self.dados)), 2)

    def teste_omite_inativos_por_omissao(self):
        responsaveis.desativar(self.dados, self.bruno["id"])
        resultado = responsaveis.listar(self.dados)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], self.ana["id"])

    def teste_inclui_inativos_quando_pedido(self):
        responsaveis.desativar(self.dados, self.bruno["id"])
        resultado = responsaveis.listar(self.dados, incluir_inativos=True)

        self.assertEqual(len(resultado), 2)

    def teste_devolve_lista_nova(self):
        resultado = responsaveis.listar(self.dados)
        resultado.append({"id": "RES-999"})

        self.assertEqual(len(self.dados["responsaveis"]), 2)

    def teste_mantem_a_ordem_de_insercao(self):
        resultado = responsaveis.listar(self.dados)

        self.assertEqual(resultado[0]["id"], self.ana["id"])
        self.assertEqual(resultado[1]["id"], self.bruno["id"])


class TesteAtualizar(unittest.TestCase):
    """atualizar() — None não altera, "" limpa, nome não fica vazio."""

    def setUp(self):
        self.dados = estrutura()
        self.ana = responsaveis.criar(self.dados, "Ana Silva", "912345678")

    def teste_altera_o_nome(self):
        responsaveis.atualizar(self.dados, self.ana["id"], nome="Ana Sousa")

        self.assertEqual(self.ana["nome"], "Ana Sousa")

    def teste_altera_o_contacto(self):
        responsaveis.atualizar(self.dados, self.ana["id"], contacto="967654321")

        self.assertEqual(self.ana["contacto"], "967654321")

    def teste_none_nao_altera_nada(self):
        responsaveis.atualizar(self.dados, self.ana["id"])

        self.assertEqual(self.ana["nome"], "Ana Silva")
        self.assertEqual(self.ana["contacto"], "912345678")

    def teste_alterar_o_nome_nao_toca_no_contacto(self):
        responsaveis.atualizar(self.dados, self.ana["id"], nome="Ana Sousa")

        self.assertEqual(self.ana["contacto"], "912345678")

    def teste_cadeia_vazia_limpa_o_contacto(self):
        responsaveis.atualizar(self.dados, self.ana["id"], contacto="")

        self.assertEqual(self.ana["contacto"], "")

    def teste_retira_espacos_do_nome(self):
        responsaveis.atualizar(self.dados, self.ana["id"], nome="  Ana Sousa  ")

        self.assertEqual(self.ana["nome"], "Ana Sousa")

    def teste_retira_espacos_do_contacto(self):
        responsaveis.atualizar(self.dados, self.ana["id"], contacto="  967654321  ")

        self.assertEqual(self.ana["contacto"], "967654321")

    def teste_nome_vazio_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.atualizar(self.dados, self.ana["id"], nome="")

    def teste_nome_so_com_espacos_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.atualizar(self.dados, self.ana["id"], nome="   ")

    def teste_nome_recusado_nao_altera_o_registo(self):
        with self.assertRaises(ValueError):
            responsaveis.atualizar(self.dados, self.ana["id"], nome=" ")

        self.assertEqual(self.ana["nome"], "Ana Silva")

    def teste_id_inexistente_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.atualizar(self.dados, "RES-999", nome="Ana")

    def teste_devolve_o_registo_atualizado(self):
        devolvido = responsaveis.atualizar(self.dados, self.ana["id"], nome="Ana Sousa")

        self.assertIs(devolvido, self.ana)

    def teste_nao_altera_o_estado(self):
        responsaveis.atualizar(self.dados, self.ana["id"], nome="Ana Sousa")

        self.assertTrue(self.ana["ativo"])

    def teste_atualiza_responsavel_inativo(self):
        responsaveis.desativar(self.dados, self.ana["id"])
        responsaveis.atualizar(self.dados, self.ana["id"], contacto="967654321")

        self.assertEqual(self.ana["contacto"], "967654321")
        self.assertFalse(self.ana["ativo"])


class TesteDesativar(unittest.TestCase):
    """desativar() — recusa a segunda vez, para expor o engano."""

    def setUp(self):
        self.dados = estrutura()
        self.ana = responsaveis.criar(self.dados, "Ana Silva", "912345678")

    def teste_marca_como_inativo(self):
        responsaveis.desativar(self.dados, self.ana["id"])

        self.assertFalse(self.ana["ativo"])

    def teste_devolve_o_registo(self):
        devolvido = responsaveis.desativar(self.dados, self.ana["id"])

        self.assertIs(devolvido, self.ana)

    def teste_nao_elimina_o_registo(self):
        responsaveis.desativar(self.dados, self.ana["id"])

        self.assertEqual(len(self.dados["responsaveis"]), 1)

    def teste_nao_apaga_dados_pessoais(self):
        responsaveis.desativar(self.dados, self.ana["id"])

        self.assertEqual(self.ana["nome"], "Ana Silva")
        self.assertEqual(self.ana["contacto"], "912345678")

    def teste_desativar_duas_vezes_e_recusado(self):
        responsaveis.desativar(self.dados, self.ana["id"])

        with self.assertRaises(ValueError):
            responsaveis.desativar(self.dados, self.ana["id"])

    def teste_id_inexistente_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.desativar(self.dados, "RES-999")


class TesteReativar(unittest.TestCase):
    """reativar() — inversa exata da desativar, sem exceções."""

    def setUp(self):
        self.dados = estrutura()
        self.ana = responsaveis.criar(self.dados, "Ana Silva")

    def teste_repoe_como_ativo(self):
        responsaveis.desativar(self.dados, self.ana["id"])
        responsaveis.reativar(self.dados, self.ana["id"])

        self.assertTrue(self.ana["ativo"])

    def teste_devolve_o_registo(self):
        responsaveis.desativar(self.dados, self.ana["id"])
        devolvido = responsaveis.reativar(self.dados, self.ana["id"])

        self.assertIs(devolvido, self.ana)

    def teste_volta_a_aparecer_na_listagem(self):
        responsaveis.desativar(self.dados, self.ana["id"])
        responsaveis.reativar(self.dados, self.ana["id"])

        self.assertEqual(len(responsaveis.listar(self.dados)), 1)

    def teste_reativar_quem_esta_ativo_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.reativar(self.dados, self.ana["id"])

    def teste_id_inexistente_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.reativar(self.dados, "RES-999")

    def teste_ciclo_completo_nao_altera_os_dados(self):
        responsaveis.desativar(self.dados, self.ana["id"])
        responsaveis.reativar(self.dados, self.ana["id"])

        self.assertEqual(self.ana["nome"], "Ana Silva")
        self.assertTrue(self.ana["ativo"])


class TesteValidarAutoria(unittest.TestCase):
    """validar_autoria() — autoriza o presente: exige existir E ativo."""

    def setUp(self):
        self.dados = estrutura()
        self.ana = responsaveis.criar(self.dados, "Ana Silva")

    def teste_responsavel_ativo_e_aceite(self):
        devolvido = responsaveis.validar_autoria(self.dados, self.ana["id"])

        self.assertIs(devolvido, self.ana)

    def teste_aceita_id_com_espacos_a_volta(self):
        devolvido = responsaveis.validar_autoria(self.dados, f"  {self.ana['id']}  ")

        self.assertIs(devolvido, self.ana)

    def teste_none_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.validar_autoria(self.dados, None)

    def teste_cadeia_vazia_e_recusada(self):
        with self.assertRaises(ValueError):
            responsaveis.validar_autoria(self.dados, "")

    def teste_so_espacos_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.validar_autoria(self.dados, "   ")

    def teste_id_inexistente_e_recusado(self):
        with self.assertRaises(ValueError):
            responsaveis.validar_autoria(self.dados, "RES-999")

    def teste_responsavel_inativo_e_recusado(self):
        responsaveis.desativar(self.dados, self.ana["id"])

        with self.assertRaises(ValueError):
            responsaveis.validar_autoria(self.dados, self.ana["id"])

    def teste_mensagem_do_inativo_distingue_do_inexistente(self):
        responsaveis.desativar(self.dados, self.ana["id"])

        with self.assertRaises(ValueError) as contexto:
            responsaveis.validar_autoria(self.dados, self.ana["id"])

        self.assertIn("inativo", str(contexto.exception))

    def teste_reativado_volta_a_poder_assumir_autoria(self):
        responsaveis.desativar(self.dados, self.ana["id"])
        responsaveis.reativar(self.dados, self.ana["id"])

        devolvido = responsaveis.validar_autoria(self.dados, self.ana["id"])

        self.assertIs(devolvido, self.ana)

    def teste_nao_altera_a_estrutura_de_dados(self):
        responsaveis.validar_autoria(self.dados, self.ana["id"])

        self.assertEqual(len(self.dados["responsaveis"]), 1)
        self.assertTrue(self.ana["ativo"])


if __name__ == "__main__":
    unittest.main()
