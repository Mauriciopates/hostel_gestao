"""Testes do sistema de migrações (v1.8.0, passo C).

Correm contra a base de teste dedicada (`apoio_BD.BaseMySQLTest`),
com listas de migrações PRÓPRIAS — nunca a lista oficial, que tem
seeds (decisão 4 do passo C: a base de testes precisa das tabelas
vazias). As migrações de teste só mexem numa tabela `migracao_teste`,
criada e apagada aqui.

A tabela `migracoes_aplicadas` não está na lista do TRUNCATE do
`apoio_BD` (é criada pelo próprio sistema de migrações), por isso
cada teste apaga-a no início — cada teste começa como uma base que
nunca correu migrações.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest  # noqa: E402

import migracoes  # noqa: E402
import repositorio  # noqa: E402

_CRIAR_TABELA_TESTE = (
    "CREATE TABLE IF NOT EXISTS migracao_teste ("
    "id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
    "nome VARCHAR(50) NOT NULL)"
)
_INSERIR_A = (
    "INSERT INTO migracao_teste (nome) SELECT 'A' FROM DUAL "
    "WHERE NOT EXISTS (SELECT 1 FROM migracao_teste WHERE nome = 'A')"
)
_INSERIR_B = (
    "INSERT INTO migracao_teste (nome) SELECT 'B' FROM DUAL "
    "WHERE NOT EXISTS (SELECT 1 FROM migracao_teste WHERE nome = 'B')"
)


def _executar(sql):
    """Corre uma instrução avulsa na base de teste (preparação)."""
    conexao = repositorio.obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(sql)
        conexao.commit()
    finally:
        conexao.close()


def _nomes_em_teste():
    """Devolve a lista ordenada dos nomes gravados em migracao_teste."""
    conexao = repositorio.obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT nome FROM migracao_teste ORDER BY nome")
        return [str(linha[0]) for linha in cursor.fetchall()]
    finally:
        conexao.close()


class BaseMigracoesTest(BaseMySQLTest):
    """Cada teste começa sem `migracoes_aplicadas` nem
    `migracao_teste`."""

    def setUp(self):
        super().setUp()
        _executar("DROP TABLE IF EXISTS migracoes_aplicadas")
        _executar("DROP TABLE IF EXISTS migracao_teste")

    def tearDown(self):
        _executar("DROP TABLE IF EXISTS migracao_teste")
        super().tearDown()


class TesteAplicarPendentes(BaseMigracoesTest):
    """O ciclo normal: criar a tabela, aplicar, não repetir."""

    def teste_cria_a_tabela_de_controlo(self):
        """Numa base sem `migracoes_aplicadas`, a tabela é criada e
        uma lista vazia não aplica nada."""
        self.assertEqual([], migracoes.aplicar_pendentes([]))
        self.assertEqual(set(), repositorio.listar_migracoes_aplicadas())

    def teste_aplica_por_ordem_e_regista(self):
        lista = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_inserir_a", [_INSERIR_A]),
        ]

        feitas = migracoes.aplicar_pendentes(lista)

        self.assertEqual(["0001_criar_tabela", "0002_inserir_a"], feitas)
        self.assertEqual(
            {"0001_criar_tabela", "0002_inserir_a"},
            repositorio.listar_migracoes_aplicadas(),
        )
        self.assertEqual(["A"], _nomes_em_teste())

    def teste_segunda_vez_nao_repete(self):
        """Num segundo arranque não há nada a aplicar."""
        lista = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_inserir_a", [_INSERIR_A]),
        ]
        migracoes.aplicar_pendentes(lista)

        self.assertEqual([], migracoes.aplicar_pendentes(lista))
        self.assertEqual(["A"], _nomes_em_teste())

    def teste_so_aplica_as_novas(self):
        """Uma migração acrescentada no fim é a única a correr."""
        lista = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_inserir_a", [_INSERIR_A]),
        ]
        migracoes.aplicar_pendentes(lista)

        lista.append(("0003_inserir_b", [_INSERIR_B]))

        self.assertEqual(
            ["0003_inserir_b"], migracoes.aplicar_pendentes(lista)
        )
        self.assertEqual(["A", "B"], _nomes_em_teste())

    def teste_varias_instrucoes_numa_migracao(self):
        lista = [
            ("0001_tudo", [_CRIAR_TABELA_TESTE, _INSERIR_A, _INSERIR_B]),
        ]

        migracoes.aplicar_pendentes(lista)

        self.assertEqual(["A", "B"], _nomes_em_teste())


class TesteFalha(BaseMigracoesTest):
    """Uma migração que falha não fica registada e trava as seguintes."""

    def _lista_com_falha(self):
        return [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            (
                "0002_partida",
                [_INSERIR_A, "INSERT INTO nao_existe VALUES (1)"],
            ),
            ("0003_inserir_b", [_INSERIR_B]),
        ]

    def teste_falha_levanta_value_error_com_o_nome(self):
        with self.assertRaises(ValueError) as contexto:
            migracoes.aplicar_pendentes(self._lista_com_falha())

        self.assertIn("0002_partida", str(contexto.exception))

    def teste_falha_nao_regista_e_nao_continua(self):
        with self.assertRaises(ValueError):
            migracoes.aplicar_pendentes(self._lista_com_falha())

        self.assertEqual(
            {"0001_criar_tabela"}, repositorio.listar_migracoes_aplicadas()
        )
        # O INSERT de 'A' da migração partida foi desfeito (rollback) e
        # a 0003 não correu.
        self.assertEqual([], _nomes_em_teste())

    def teste_depois_de_corrigida_volta_a_tentar(self):
        """No arranque seguinte, a migração em falta é tentada outra
        vez (aqui já corrigida)."""
        with self.assertRaises(ValueError):
            migracoes.aplicar_pendentes(self._lista_com_falha())

        corrigida = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_partida", [_INSERIR_A]),
            ("0003_inserir_b", [_INSERIR_B]),
        ]

        self.assertEqual(
            ["0002_partida", "0003_inserir_b"],
            migracoes.aplicar_pendentes(corrigida),
        )
        self.assertEqual(["A", "B"], _nomes_em_teste())


class TesteValidarLista(unittest.TestCase):
    """Validação da lista — não precisa de base de dados."""

    def teste_lista_oficial_e_valida(self):
        migracoes.validar_lista(migracoes.MIGRACOES)

    def teste_nome_fora_do_formato_recusa(self):
        for nome in ("1_curto", "0001-hifen", "0001_Maiusculas", "abcd_x"):
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    migracoes.validar_lista([(nome, ["SELECT 1"])])

    def teste_nome_repetido_recusa(self):
        with self.assertRaises(ValueError):
            migracoes.validar_lista(
                [("0001_a", ["SELECT 1"]), ("0001_a", ["SELECT 1"])]
            )

    def teste_fora_de_ordem_recusa(self):
        with self.assertRaises(ValueError):
            migracoes.validar_lista(
                [("0002_b", ["SELECT 1"]), ("0001_a", ["SELECT 1"])]
            )

    def teste_sem_instrucoes_recusa(self):
        with self.assertRaises(ValueError):
            migracoes.validar_lista([("0001_vazia", [])])


if __name__ == "__main__":
    unittest.main()
