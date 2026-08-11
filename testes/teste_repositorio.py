"""Testes da camada de persistência.

Cada teste corre numa pasta temporária própria, criada antes e eliminada
depois. As constantes de caminho do repositório são redirecionadas para
essa pasta e repostas no fim, para os testes nunca tocarem nos dados
reais de `dados/` e `backups/`.
"""

import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import repositorio


class BaseRepositorio(unittest.TestCase):
    """Preparação comum a todos os testes do repositório."""

    def setUp(self):
        """Cria a pasta temporária e redireciona os caminhos."""
        self.pasta = Path(tempfile.mkdtemp())

        self.originais = (
            repositorio.PASTA_DADOS,
            repositorio.PASTA_BACKUPS,
            repositorio.FICHEIRO_DADOS,
            repositorio.FICHEIRO_CONTADORES,
        )

        repositorio.PASTA_DADOS = self.pasta / "dados"
        repositorio.PASTA_BACKUPS = self.pasta / "backups"
        repositorio.FICHEIRO_DADOS = repositorio.PASTA_DADOS / "dados.json"
        repositorio.FICHEIRO_CONTADORES = repositorio.PASTA_DADOS / "contadores.json"

    def tearDown(self):
        """Repõe os caminhos originais e elimina a pasta temporária."""
        (
            repositorio.PASTA_DADOS,
            repositorio.PASTA_BACKUPS,
            repositorio.FICHEIRO_DADOS,
            repositorio.FICHEIRO_CONTADORES,
        ) = self.originais

        shutil.rmtree(self.pasta, ignore_errors=True)


class TesteContadores(BaseRepositorio):
    """Atribuição de identificadores sequenciais (decisão 2)."""

    def teste_primeiro_id_de_um_prefixo(self):
        """Sem contador gravado, o primeiro identificador é o 001."""
        self.assertEqual("UNI-001", repositorio.proximo_id("UNI"))

    def teste_ids_consecutivos(self):
        """Cada chamada devolve o número seguinte."""
        repositorio.proximo_id("UNI")
        repositorio.proximo_id("UNI")
        self.assertEqual("UNI-003", repositorio.proximo_id("UNI"))

    def teste_prefixos_independentes(self):
        """Cada prefixo tem o seu próprio contador."""
        repositorio.proximo_id("UNI")
        repositorio.proximo_id("UNI")
        self.assertEqual("CLI-001", repositorio.proximo_id("CLI"))

    def teste_contador_nao_recua(self):
        """O contador é lido do ficheiro, nunca da contagem de registos.

        É o erro do protótipo descartado: eliminar registos fazia o
        contador reiniciar e reatribuir identificadores já usados.
        """
        for _ in range(5):
            repositorio.proximo_id("UNI")

        dados = repositorio.carregar()
        dados["unidades"] = []
        repositorio.gravar(dados)

        self.assertEqual("UNI-006", repositorio.proximo_id("UNI"))

    def teste_formato_com_tres_digitos(self):
        """O número é preenchido com zeros até três dígitos."""
        for _ in range(9):
            repositorio.proximo_id("UNI")

        self.assertEqual("UNI-010", repositorio.proximo_id("UNI"))


if __name__ == "__main__":
    unittest.main()
