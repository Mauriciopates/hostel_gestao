"""Testes do esquema oficial `src/bd/esquema.sql` (v1.8.0, INST-03).

O esquema é a fonte única das tabelas (decisão D7): a aplicação usa-o
para criar uma base nova e o `apoio_BD` para a base de teste. Aqui
confirma-se a forma do ficheiro (sem base de dados) e que a criação é
idempotente (com a base de teste).
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest  # noqa: E402

import config  # noqa: E402
import repositorio  # noqa: E402

# As 26 tabelas do sistema (v1.8.0): 25 de negócio + a de controlo
# das migrações. Uma tabela nova obriga a mexer aqui de propósito — e
# no esquema, e numa migração.
_TABELAS = {
    "migracoes_aplicadas",
    "avisos_privacidade", "categorias_despesa", "clientes",
    "configuracoes", "configuracoes_historico", "despesas",
    "devolucoes", "fornecedores", "itens_despesa", "itens_devolucao",
    "itens_requisicao", "lugares", "movimentos", "ocupacoes",
    "ocupacoes_airbnb", "ocupacoes_mensal", "produtos", "propriedades",
    "quartos", "requisicoes", "responsaveis", "responsavel_unidade",
    "rol_lavanderia_regras", "textos_legais", "unidades",
}


class TesteFicheiroEsquema(unittest.TestCase):
    """A forma do ficheiro — não precisa de base de dados."""

    def teste_ficheiro_existe(self):
        self.assertTrue(config.FICHEIRO_ESQUEMA.is_file())

    def teste_tem_as_26_tabelas(self):
        self.assertEqual(_TABELAS, set(repositorio.tabelas_do_esquema()))

    def teste_tabela_de_migracoes_e_a_ultima(self):
        """`migracoes_aplicadas` faz parte do esquema (grupo Sistema),
        no fim — não tem FKs nem é referida por nenhuma tabela."""
        self.assertEqual(
            "migracoes_aplicadas", repositorio.tabelas_do_esquema()[-1]
        )

    def teste_todas_com_if_not_exists(self):
        for instrucao in repositorio.instrucoes_esquema():
            with self.subTest(instrucao=instrucao[:40]):
                self.assertTrue(
                    instrucao.startswith("CREATE TABLE IF NOT EXISTS")
                )

    def teste_tabela_de_migracoes_igual_a_do_codigo(self):
        """A definição no esquema e a rede de segurança do
        `rep_migracoes` têm de ser a mesma tabela."""
        from repositorio import rep_migracoes

        instrucao = repositorio.instrucoes_esquema()[-1]
        for coluna in ("`nome` varchar(100) NOT NULL",
                       "`aplicada_em` datetime NOT NULL",
                       "UNIQUE KEY `uq_migracoes_nome`"):
            with self.subTest(coluna=coluna):
                self.assertIn(coluna, instrucao)
        self.assertIn(
            "nome VARCHAR(100) NOT NULL", rep_migracoes._SQL_TABELA_MIGRACOES
        )

    def teste_sem_auto_increment_fixo(self):
        texto = config.FICHEIRO_ESQUEMA.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"AUTO_INCREMENT=\d", texto))

    def teste_ordem_respeita_as_chaves_estrangeiras(self):
        """Cada tabela só referencia tabelas criadas antes (ou a
        própria) — o esquema corre com as FKs ligadas."""
        criadas = set()
        for instrucao, nome in zip(
            repositorio.instrucoes_esquema(),
            repositorio.tabelas_do_esquema(),
        ):
            referidas = set(re.findall(r"REFERENCES `(\w+)`", instrucao))
            with self.subTest(tabela=nome):
                self.assertTrue(referidas - {nome} <= criadas)
            criadas.add(nome)


class TesteCriarTabelas(BaseMySQLTest):
    """`criar_tabelas` na base de teste (onde as tabelas já existem)."""

    def teste_numa_base_ja_criada_nao_falha_nem_apaga(self):
        repositorio.inserir_propriedade(
            {"id": "PRO-001", "nome": "Teste", "morada": "",
             "iban": "", "ativo": True}
        )

        repositorio.criar_tabelas()
        repositorio.criar_tabelas()

        self.assertIsNotNone(repositorio.procurar_propriedade("PRO-001"))


if __name__ == "__main__":
    unittest.main()
