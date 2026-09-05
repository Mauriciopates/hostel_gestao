"""Testes da gestão de propriedades.

MIGRAÇÃO MySQL (Fase 2): desde que `propriedades.py` passou a falar
diretamente com a base de dados (já não recebe nem devolve a
estrutura `dados`), estes testes correm contra uma base de dados
MySQL de teste, dedicada e isolada da base de dados real do aluno —
ver `apoio_bd.py` para os detalhes. Cada teste começa com a tabela
vazia (TRUNCATE) e com os contadores de identificadores reiniciados,
tal como antes cada teste começava com um dicionário `dados` novo.

O identificador não é verificado por igualdade porque o contador é
reiniciado por teste mas mantém-se sequencial: verifica-se sempre o
prefixo (decisão antiga, mantida) — exceto quando um teste cria só
UMA propriedade nessa base de dados vazia, caso em que "PRO-001" é
previsível e serve para confirmar o formato com três dígitos.

NOTA sobre identidade: `procurar()` faz sempre um SELECT novo à base
de dados — já não devolve o MESMO objeto Python que `criar()`
devolveu. Por isso comparamos com `assertEqual` (valores iguais),
nunca com `assertIs` (mesmo objeto).
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from apoio_BD import BaseMySQLTest

import propriedades
import unidades


class TesteCriar(BaseMySQLTest):
    """Criação de propriedades."""

    def teste_criar_devolve_a_propriedade_criada(self):
        """A propriedade criada é devolvida, com o nome indicado."""
        p = propriedades.criar("Rei Ramiro")

        self.assertEqual("Rei Ramiro", p["nome"])
        self.assertEqual(1, len(propriedades.listar()))

    def teste_criar_atribui_id_com_prefixo(self):
        """O identificador segue o formato PRO-000 (decisão 2)."""
        p = propriedades.criar("Foz Velha")

        self.assertTrue(p["id"].startswith("PRO-"))

    def teste_criar_primeiro_id_e_pro_001(self):
        """Numa base de dados de teste vazia, o primeiro id é
        previsível: PRO-001, com três dígitos."""
        p = propriedades.criar("Foz Velha")

        self.assertEqual("PRO-001", p["id"])

    def teste_criar_nasce_ativa(self):
        """Uma propriedade nova está ativa por omissão."""
        p = propriedades.criar("Aldoar")

        self.assertTrue(p["ativo"])

    def teste_criar_limpa_espacos(self):
        """Os espaços nas extremidades não são guardados.

        Sem a limpeza, " Beco " e "Beco" seriam propriedades distintas
        numa listagem.
        """
        p = propriedades.criar("  Beco  ", "  Rua do Beco  ")

        self.assertEqual("Beco", p["nome"])
        self.assertEqual("Rua do Beco", p["morada"])

    def teste_criar_sem_nome_e_recusado(self):
        """O nome é obrigatório: vazio ou só espaços não passa."""
        for nome in ("", "   "):
            with self.assertRaises(ValueError):
                propriedades.criar(nome)

    def teste_criar_sem_morada_e_aceite(self):
        """A morada é opcional e fica vazia."""
        p = propriedades.criar("Casa da Música")

        self.assertEqual("", p["morada"])


class TesteProcurar(BaseMySQLTest):
    """Procura de uma propriedade pelo identificador."""

    def teste_procurar_encontra(self):
        """Devolve o registo quando o identificador corresponde."""
        criada = propriedades.criar("Rei Ramiro")

        encontrada = propriedades.procurar(criada["id"])

        self.assertEqual(criada, encontrada)

    def teste_procurar_inexistente_devolve_none(self):
        """Um identificador que não corresponde a nada devolve None.

        A ausência não é erro: quem chama é que decide se é problema.
        """
        propriedades.criar("Rei Ramiro")

        self.assertIsNone(propriedades.procurar("PRO-999"))

    def teste_procurar_em_base_vazia(self):
        """Sem propriedades registadas, devolve None."""
        self.assertIsNone(propriedades.procurar("PRO-001"))

    def teste_procurar_encontra_inativas(self):
        """A procura não filtra: devolve também as desativadas."""
        pro_id = propriedades.criar("Aldoar")["id"]
        propriedades.desativar(pro_id)

        self.assertIsNotNone(propriedades.procurar(pro_id))


class TesteListar(BaseMySQLTest):
    """Listagem com e sem as propriedades inativas."""

    def teste_listar_devolve_todas_as_ativas(self):
        """Por omissão, a listagem tem todas as propriedades ativas."""
        propriedades.criar("Foz Velha")
        propriedades.criar("Aldoar")
        propriedades.criar("Beco")

        self.assertEqual(3, len(propriedades.listar()))

    def teste_listar_omite_as_inativas(self):
        """Uma propriedade desativada não aparece na listagem."""
        inativa_id = propriedades.criar("Foz Velha")["id"]
        propriedades.criar("Aldoar")
        propriedades.desativar(inativa_id)

        self.assertEqual(1, len(propriedades.listar()))

    def teste_listar_com_inativas_devolve_todas(self):
        """Com incluir_inativas, a listagem tem também as desativadas."""
        inativa_id = propriedades.criar("Foz Velha")["id"]
        propriedades.criar("Aldoar")
        propriedades.desativar(inativa_id)

        todas = propriedades.listar(incluir_inativas=True)

        self.assertEqual(2, len(todas))

    def teste_listar_base_vazia(self):
        """Sem propriedades registadas, a listagem é vazia."""
        self.assertEqual([], propriedades.listar())

    def teste_listar_devolve_lista_nova(self):
        """Alterar a lista devolvida não altera a base de dados."""
        propriedades.criar("Foz Velha")

        listagem = propriedades.listar()
        listagem.clear()

        self.assertEqual(1, len(propriedades.listar()))


class TesteAtualizar(BaseMySQLTest):
    """Alteração do nome e da morada."""

    def teste_atualizar_altera_o_nome(self):
        """O nome indicado substitui o anterior."""
        pro_id = propriedades.criar("Rei Ramiro")["id"]

        p = propriedades.atualizar(pro_id, nome="Rei Ramiro 1-13")

        self.assertEqual("Rei Ramiro 1-13", p["nome"])
        self.assertEqual("Rei Ramiro 1-13", propriedades.procurar(pro_id)["nome"])

    def teste_atualizar_altera_a_morada(self):
        """A morada indicada substitui a anterior."""
        pro_id = propriedades.criar("Beco")["id"]

        p = propriedades.atualizar(pro_id, morada="Rua do Beco, 4")

        self.assertEqual("Rua do Beco, 4", p["morada"])

    def teste_atualizar_sem_parametros_nao_altera(self):
        """Parâmetros a None significam não alterar.

        É o que permite mudar só a morada sem passar o nome atual.
        """
        pro_id = propriedades.criar("Aldoar")["id"]

        p = propriedades.atualizar(pro_id)

        self.assertEqual("Aldoar", p["nome"])

    def teste_atualizar_apaga_a_morada(self):
        """Uma cadeia vazia apaga a morada, ao contrário de None."""
        pro_id = propriedades.criar("Aldoar", "Rua de Aldoar")["id"]

        p = propriedades.atualizar(pro_id, morada="")

        self.assertEqual("", p["morada"])

    def teste_atualizar_com_nome_vazio_e_recusado(self):
        """O nome não pode ser apagado: a propriedade deixaria de se
        identificar."""
        pro_id = propriedades.criar("Aldoar")["id"]

        with self.assertRaises(ValueError):
            propriedades.atualizar(pro_id, nome="")

    def teste_atualizar_limpa_espacos(self):
        """Os espaços nas extremidades não são guardados."""
        pro_id = propriedades.criar("Aldoar")["id"]

        p = propriedades.atualizar(pro_id, nome="  Foz Pinhais  ")

        self.assertEqual("Foz Pinhais", p["nome"])

    def teste_atualizar_inexistente_e_recusado(self):
        """Um identificador desconhecido produz erro."""
        with self.assertRaises(ValueError):
            propriedades.atualizar("PRO-999", nome="Teste")


class TesteDesativarReativar(BaseMySQLTest):
    """Desativação e reposição (decisão 8)."""

    def teste_desativar_marca_como_inativa(self):
        """A propriedade continua a existir, marcada como inativa.

        Não é eliminada porque os contratos históricos referem as suas
        unidades: eliminar deixaria referências a apontar para nada.
        """
        pro_id = propriedades.criar("Aldoar")["id"]

        p = propriedades.desativar(pro_id)

        self.assertFalse(p["ativo"])
        self.assertEqual(1, len(propriedades.listar(incluir_inativas=True)))

    def teste_desativar_duas_vezes_e_recusado(self):
        """Desativar uma propriedade já inativa produz erro.

        A recusa expõe o engano em vez de o aceitar em silêncio.
        """
        pro_id = propriedades.criar("Aldoar")["id"]
        propriedades.desativar(pro_id)

        with self.assertRaises(ValueError):
            propriedades.desativar(pro_id)

    def teste_desativar_inexistente_e_recusado(self):
        """Um identificador desconhecido produz erro."""
        with self.assertRaises(ValueError):
            propriedades.desativar("PRO-999")

    def teste_reativar_repoe_como_ativa(self):
        """Uma propriedade desativada por engano pode ser reposta."""
        pro_id = propriedades.criar("Aldoar")["id"]
        propriedades.desativar(pro_id)

        p = propriedades.reativar(pro_id)

        self.assertTrue(p["ativo"])

    def teste_reativar_uma_ativa_e_recusado(self):
        """Reativar uma propriedade que já está ativa produz erro."""
        pro_id = propriedades.criar("Aldoar")["id"]

        with self.assertRaises(ValueError):
            propriedades.reativar(pro_id)

    def teste_reativar_inexistente_e_recusado(self):
        """Um identificador desconhecido produz erro."""
        with self.assertRaises(ValueError):
            propriedades.reativar("PRO-999")

    def teste_desativar_com_unidade_ativa_e_recusado_sem_forcar(self):
        """Novo (decisão de 27/08, item 9): sem forcar=True, recusa
        desativar se existir alguma unidade ativa dependente."""
        pro_id = propriedades.criar("Aldoar")["id"]
        unidades.criar(
            pro_id, "Unidade Teste", "mensal",
            Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
        )

        with self.assertRaises(ValueError):
            propriedades.desativar(pro_id)

    def teste_desativar_com_forcar_ignora_unidades_ativas(self):
        """Com forcar=True, desativa mesmo com unidades ativas
        dependentes — decisão consciente de quem chama."""
        pro_id = propriedades.criar("Aldoar")["id"]
        unidades.criar(
            pro_id, "Unidade Teste", "mensal",
            Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
        )

        p = propriedades.desativar(pro_id, forcar=True)

        self.assertFalse(p["ativo"])

    def teste_desativar_ignora_unidade_ja_inativa(self):
        """Uma unidade já inativa não conta como dependência ativa —
        não exige forcar."""
        pro_id = propriedades.criar("Aldoar")["id"]
        unidade = unidades.criar(
            pro_id, "Unidade Teste", "mensal",
            Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
        )
        unidades.desativar(unidade["id"])

        p = propriedades.desativar(pro_id)

        self.assertFalse(p["ativo"])


if __name__ == "__main__":
    unittest.main()