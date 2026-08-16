"""Testes da gestão de propriedades.

Como o módulo recebe a estrutura de dados como argumento, os testes
constroem um dicionário e verificam o resultado. Não é preciso pasta
temporária nem redirecionar caminhos: as funções não acedem a ficheiros.

O identificador não é verificado por igualdade porque o contador está
gravado em ficheiro e avança entre execuções; verifica-se o prefixo.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import propriedades


def estrutura(*nomes):
    """Devolve uma estrutura com as propriedades indicadas já criadas."""
    dados = {"propriedades": []}
    for nome in nomes:
        propriedades.criar(dados, nome)
    return dados


class TesteCriar(unittest.TestCase):
    """Criação de propriedades."""

    def teste_criar_acrescenta_a_lista(self):
        """A propriedade criada fica na estrutura e é devolvida."""
        dados = {"propriedades": []}

        p = propriedades.criar(dados, "Rei Ramiro")

        self.assertEqual(1, len(dados["propriedades"]))
        self.assertEqual("Rei Ramiro", p["nome"])

    def teste_criar_atribui_id_com_prefixo(self):
        """O identificador segue o formato PRO-000 (decisão 2)."""
        dados = {"propriedades": []}

        p = propriedades.criar(dados, "Foz Velha")

        self.assertTrue(p["id"].startswith("PRO-"))

    def teste_criar_nasce_ativa(self):
        """Uma propriedade nova está ativa por omissão."""
        dados = {"propriedades": []}

        p = propriedades.criar(dados, "Aldoar")

        self.assertTrue(p["ativo"])

    def teste_criar_limpa_espacos(self):
        """Os espaços nas extremidades não são guardados.

        Sem a limpeza, " Beco " e "Beco" seriam propriedades distintas
        numa listagem.
        """
        dados = {"propriedades": []}

        p = propriedades.criar(dados, "  Beco  ", "  Rua do Beco  ")

        self.assertEqual("Beco", p["nome"])
        self.assertEqual("Rua do Beco", p["morada"])

    def teste_criar_sem_nome_e_recusado(self):
        """O nome é obrigatório: vazio ou só espaços não passa."""
        for nome in ("", "   "):
            dados = {"propriedades": []}
            with self.assertRaises(ValueError):
                propriedades.criar(dados, nome)

    def teste_criar_sem_morada_e_aceite(self):
        """A morada é opcional e fica vazia."""
        dados = {"propriedades": []}

        p = propriedades.criar(dados, "Casa da Música")

        self.assertEqual("", p["morada"])


class TesteProcurar(unittest.TestCase):
    """Procura de uma propriedade pelo identificador."""

    def teste_procurar_encontra(self):
        """Devolve o registo quando o identificador corresponde."""
        dados = estrutura("Rei Ramiro")
        criada = dados["propriedades"][0]

        encontrada = propriedades.procurar(dados, criada["id"])

        self.assertEqual(criada, encontrada)

    def teste_procurar_inexistente_devolve_none(self):
        """Um identificador que não corresponde a nada devolve None.

        A ausência não é erro: quem chama é que decide se é problema.
        """
        dados = estrutura("Rei Ramiro")

        self.assertIsNone(propriedades.procurar(dados, "PRO-999"))

    def teste_procurar_em_lista_vazia(self):
        """Sem propriedades registadas, devolve None."""
        dados = {"propriedades": []}

        self.assertIsNone(propriedades.procurar(dados, "PRO-001"))

    def teste_procurar_encontra_inativas(self):
        """A procura não filtra: devolve também as desativadas."""
        dados = estrutura("Aldoar")
        pro_id = dados["propriedades"][0]["id"]
        propriedades.desativar(dados, pro_id)

        self.assertIsNotNone(propriedades.procurar(dados, pro_id))


class TesteListar(unittest.TestCase):
    """Listagem com e sem as propriedades inativas."""

    def teste_listar_devolve_todas_as_ativas(self):
        """Por omissão, a listagem tem todas as propriedades ativas."""
        dados = estrutura("Foz Velha", "Aldoar", "Beco")

        self.assertEqual(3, len(propriedades.listar(dados)))

    def teste_listar_omite_as_inativas(self):
        """Uma propriedade desativada não aparece na listagem."""
        dados = estrutura("Foz Velha", "Aldoar")
        propriedades.desativar(dados, dados["propriedades"][0]["id"])

        self.assertEqual(1, len(propriedades.listar(dados)))

    def teste_listar_com_inativas_devolve_todas(self):
        """Com incluir_inativas, a listagem tem também as desativadas."""
        dados = estrutura("Foz Velha", "Aldoar")
        propriedades.desativar(dados, dados["propriedades"][0]["id"])

        todas = propriedades.listar(dados, incluir_inativas=True)

        self.assertEqual(2, len(todas))

    def teste_listar_estrutura_vazia(self):
        """Sem propriedades registadas, a listagem é vazia."""
        self.assertEqual([], propriedades.listar({"propriedades": []}))

    def teste_listar_devolve_lista_nova(self):
        """Alterar a lista devolvida não altera a estrutura de dados."""
        dados = estrutura("Foz Velha")

        listagem = propriedades.listar(dados)
        listagem.clear()

        self.assertEqual(1, len(dados["propriedades"]))


class TesteAtualizar(unittest.TestCase):
    """Alteração do nome e da morada."""

    def teste_atualizar_altera_o_nome(self):
        """O nome indicado substitui o anterior."""
        dados = estrutura("Rei Ramiro")
        pro_id = dados["propriedades"][0]["id"]

        p = propriedades.atualizar(dados, pro_id, nome="Rei Ramiro 1-13")

        self.assertEqual("Rei Ramiro 1-13", p["nome"])

    def teste_atualizar_altera_a_morada(self):
        """A morada indicada substitui a anterior."""
        dados = estrutura("Beco")
        pro_id = dados["propriedades"][0]["id"]

        p = propriedades.atualizar(dados, pro_id, morada="Rua do Beco, 4")

        self.assertEqual("Rua do Beco, 4", p["morada"])

    def teste_atualizar_sem_parametros_nao_altera(self):
        """Parâmetros a None significam não alterar.

        É o que permite mudar só a morada sem passar o nome atual.
        """
        dados = estrutura("Aldoar")
        pro_id = dados["propriedades"][0]["id"]

        p = propriedades.atualizar(dados, pro_id)

        self.assertEqual("Aldoar", p["nome"])

    def teste_atualizar_apaga_a_morada(self):
        """Uma cadeia vazia apaga a morada, ao contrário de None."""
        dados = {"propriedades": []}
        propriedades.criar(dados, "Aldoar", "Rua de Aldoar")
        pro_id = dados["propriedades"][0]["id"]

        p = propriedades.atualizar(dados, pro_id, morada="")

        self.assertEqual("", p["morada"])

    def teste_atualizar_com_nome_vazio_e_recusado(self):
        """O nome não pode ser apagado: a propriedade deixaria de se
        identificar."""
        dados = estrutura("Aldoar")
        pro_id = dados["propriedades"][0]["id"]

        with self.assertRaises(ValueError):
            propriedades.atualizar(dados, pro_id, nome="")

    def teste_atualizar_limpa_espacos(self):
        """Os espaços nas extremidades não são guardados."""
        dados = estrutura("Aldoar")
        pro_id = dados["propriedades"][0]["id"]

        p = propriedades.atualizar(dados, pro_id, nome="  Foz Pinhais  ")

        self.assertEqual("Foz Pinhais", p["nome"])

    def teste_atualizar_inexistente_e_recusado(self):
        """Um identificador desconhecido produz erro."""
        dados = {"propriedades": []}

        with self.assertRaises(ValueError):
            propriedades.atualizar(dados, "PRO-999", nome="Teste")


class TesteDesativarReativar(unittest.TestCase):
    """Desativação e reposição (decisão 8)."""

    def teste_desativar_marca_como_inativa(self):
        """A propriedade continua na estrutura, marcada como inativa.

        Não é eliminada porque os contratos históricos referem as suas
        unidades: eliminar deixaria referências a apontar para nada.
        """
        dados = estrutura("Aldoar")
        pro_id = dados["propriedades"][0]["id"]

        p = propriedades.desativar(dados, pro_id)

        self.assertFalse(p["ativo"])
        self.assertEqual(1, len(dados["propriedades"]))

    def teste_desativar_duas_vezes_e_recusado(self):
        """Desativar uma propriedade já inativa produz erro.

        A recusa expõe o engano em vez de o aceitar em silêncio.
        """
        dados = estrutura("Aldoar")
        pro_id = dados["propriedades"][0]["id"]
        propriedades.desativar(dados, pro_id)

        with self.assertRaises(ValueError):
            propriedades.desativar(dados, pro_id)

    def teste_desativar_inexistente_e_recusado(self):
        """Um identificador desconhecido produz erro."""
        dados = {"propriedades": []}

        with self.assertRaises(ValueError):
            propriedades.desativar(dados, "PRO-999")

    def teste_reativar_repoe_como_ativa(self):
        """Uma propriedade desativada por engano pode ser reposta."""
        dados = estrutura("Aldoar")
        pro_id = dados["propriedades"][0]["id"]
        propriedades.desativar(dados, pro_id)

        p = propriedades.reativar(dados, pro_id)

        self.assertTrue(p["ativo"])

    def teste_reativar_uma_ativa_e_recusado(self):
        """Reativar uma propriedade que já está ativa produz erro."""
        dados = estrutura("Aldoar")
        pro_id = dados["propriedades"][0]["id"]

        with self.assertRaises(ValueError):
            propriedades.reativar(dados, pro_id)

    def teste_reativar_inexistente_e_recusado(self):
        """Um identificador desconhecido produz erro."""
        dados = {"propriedades": []}

        with self.assertRaises(ValueError):
            propriedades.reativar(dados, "PRO-999")


if __name__ == "__main__":
    unittest.main()
