"""Testes da instalação assistida (v1.8.0, INST-02).

`instalacao.diagnosticar` / `preparar` contra o MySQL de teste, numa
base PRÓPRIA e descartável (`hostel_gestao_teste_inst`), criada e
apagada por estes testes — nunca a base real nem a base de testes
normal (`hostel_gestao_teste`). Usa as credenciais do servidor local
(correr com HOSTEL_SERVIDOR=local, como o resto da bateria).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import mysql.connector  # noqa: E402

import config  # noqa: E402
import instalacao  # noqa: E402
import repositorio  # noqa: E402

_BASE = "hostel_gestao_teste_inst"


def _servidor(base=_BASE):
    """Servidor no formato do `servidores.py`, sem túnel."""
    return {
        "nome": "Teste instalação",
        "host": config.DB_HOST,
        "porta": config.DB_PORT,
        "utilizador": config.DB_USER,
        "base": base,
    }


def _executar(*instrucoes):
    """Corre instruções no servidor, sem base escolhida (preparação)."""
    conexao = mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )
    try:
        cursor = conexao.cursor()
        for instrucao in instrucoes:
            cursor.execute(instrucao)
        conexao.commit()
    finally:
        conexao.close()


class BaseInstalacaoTest(unittest.TestCase):
    """Cada teste começa sem a base `hostel_gestao_teste_inst`."""

    def setUp(self):
        _executar(f"DROP DATABASE IF EXISTS {_BASE}")

    def tearDown(self):
        _executar(f"DROP DATABASE IF EXISTS {_BASE}")

    def _diagnosticar(self):
        return instalacao.diagnosticar(_servidor(), config.DB_PASSWORD)


class TesteDiagnosticar(BaseInstalacaoTest):

    def teste_sem_ficheiro_do_esquema_da_erro_e_nao_rebenta(self):
        """v1.11.1: sem src/bd/esquema.sql devolve ERRO com o caminho,
        em vez de levantar FileNotFoundError."""
        original = config.FICHEIRO_ESQUEMA
        config.FICHEIRO_ESQUEMA = original.with_name("nao_existe.sql")
        try:
            estado, texto, em_falta = self._diagnosticar()
        finally:
            config.FICHEIRO_ESQUEMA = original

        self.assertEqual(instalacao.ERRO, estado)
        self.assertIn("nao_existe.sql", texto)
        self.assertEqual([], em_falta)
        self.assertFalse(instalacao.pode_preparar(estado))

    def teste_base_inexistente(self):
        estado, texto, em_falta = self._diagnosticar()

        self.assertEqual(instalacao.SEM_BASE, estado)
        self.assertIn(_BASE, texto)
        self.assertEqual(25, len(em_falta))
        self.assertTrue(instalacao.pode_preparar(estado))

    def teste_base_vazia(self):
        _executar(f"CREATE DATABASE {_BASE}")

        estado, _, _ = self._diagnosticar()

        self.assertEqual(instalacao.VAZIA, estado)
        self.assertTrue(instalacao.pode_preparar(estado))

    def teste_base_de_outra_aplicacao_e_recusada(self):
        _executar(
            f"CREATE DATABASE {_BASE}",
            f"CREATE TABLE {_BASE}.encomendas (id INT PRIMARY KEY)",
        )

        estado, _, _ = self._diagnosticar()

        self.assertEqual(instalacao.ALHEIA, estado)
        self.assertFalse(instalacao.pode_preparar(estado))

    def teste_password_errada_e_erro(self):
        estado, _, _ = instalacao.diagnosticar(
            _servidor(), "password-errada-de-proposito"
        )

        self.assertEqual(instalacao.ERRO, estado)
        self.assertFalse(instalacao.pode_preparar(estado))


class TestePreparar(BaseInstalacaoTest):

    def teste_base_inexistente_fica_pronta(self):
        instalacao.preparar(_servidor(), config.DB_PASSWORD)

        estado, _, _ = self._diagnosticar()
        self.assertEqual(instalacao.PRONTA, estado)

    def teste_cria_as_26_tabelas_do_esquema(self):
        instalacao.preparar(_servidor(), config.DB_PASSWORD)

        existe, tabelas = repositorio.estado_base(
            {
                "host": config.DB_HOST,
                "port": config.DB_PORT,
                "user": config.DB_USER,
                "password": config.DB_PASSWORD,
                "database": _BASE,
            }
        )
        self.assertTrue(existe)
        self.assertEqual(set(repositorio.tabelas_do_esquema()), tabelas)

    def teste_incompleta_e_completada_sem_perder_dados(self):
        instalacao.preparar(_servidor(), config.DB_PASSWORD)
        _executar(
            f"INSERT INTO {_BASE}.propriedades (id, nome, ativo) "
            f"VALUES ('PRO-001', 'Fica', 1)",
            f"DROP TABLE {_BASE}.rol_lavanderia_regras",
        )

        estado, _, em_falta = self._diagnosticar()
        self.assertEqual(instalacao.INCOMPLETA, estado)
        self.assertEqual(["rol_lavanderia_regras"], em_falta)

        instalacao.preparar(_servidor(), config.DB_PASSWORD)

        self.assertEqual(instalacao.PRONTA, self._diagnosticar()[0])
        conexao = mysql.connector.connect(
            host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
            password=config.DB_PASSWORD, database=_BASE,
        )
        try:
            cursor = conexao.cursor()
            cursor.execute("SELECT COUNT(*) FROM propriedades")
            self.assertEqual((1,), cursor.fetchone())
        finally:
            conexao.close()

    def teste_sem_tabela_de_controlo_continua_pronta(self):
        """Base anterior à v1.8.0: sem `migracoes_aplicadas` não é
        incompleta — as migrações criam-na no arranque."""
        instalacao.preparar(_servidor(), config.DB_PASSWORD)
        _executar(f"DROP TABLE {_BASE}.migracoes_aplicadas")

        self.assertEqual(instalacao.PRONTA, self._diagnosticar()[0])

    def teste_nome_de_base_invalido_recusa(self):
        with self.assertRaises(ValueError):
            instalacao.preparar(
                _servidor("base; DROP DATABASE x"), config.DB_PASSWORD
            )


if __name__ == "__main__":
    unittest.main()
