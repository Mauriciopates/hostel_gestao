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
from datetime import date, timedelta
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


class TestePersistencia(BaseRepositorio):
    """Gravação e leitura de dados, com conversão de tipos (decisão 4)."""

    def teste_carregar_sem_ficheiro_devolve_estrutura_vazia(self):
        """Na primeira execução não há ficheiro: devolve estrutura vazia."""
        dados = repositorio.carregar()

        self.assertEqual(repositorio.config.VERSAO_DADOS, dados["versao_dados"])
        self.assertEqual([], dados["unidades"])
        self.assertEqual([], dados["clientes"])

    def teste_gravar_e_carregar_preserva_decimal(self):
        """Um Decimal gravado e relido continua a ser o mesmo valor.

        É a decisão 4: o JSON não conhece Decimal, e converter para float
        introduziria erros de arredondamento que se acumulam nos totais.
        """
        dados = repositorio.carregar()
        dados["unidades"].append(
            {
                "id": "UNI-001",
                "preco_base": Decimal("45.00"),
            }
        )
        repositorio.gravar(dados)

        lido = repositorio.carregar()
        unidade = lido["unidades"][0]

        self.assertEqual(Decimal("45.00"), unidade["preco_base"])
        self.assertIsInstance(unidade["preco_base"], Decimal)

    def teste_gravar_e_carregar_preserva_data(self):
        """Uma data gravada e relida continua a ser a mesma data.

        As datas são guardadas em ISO (AAAA-MM-DD) porque ordenam
        corretamente como texto e não são ambíguas — 03/04 é 3 de abril
        ou 4 de março consoante o país.
        """
        dados = repositorio.carregar()
        dados["ocupacoes"].append(
        {
            "id": "OCU-001",
            "data_inicio": date(2026, 3, 15),
        }
    )
        repositorio.gravar(dados)

        lido = repositorio.carregar()
        ocupacao = lido["ocupacoes"][0]

        self.assertEqual(date(2026, 3, 15), ocupacao["data_inicio"])
        self.assertIsInstance(ocupacao["data_inicio"], date)

    def teste_gravacao_atomica_nao_deixa_temporario(self):
        """Depois de gravar não sobra o ficheiro temporário.

        A gravação passa por um .tmp que só substitui o definitivo no
        fim: uma interrupção a meio deixaria o ficheiro truncado e os
        dados perdidos. Se o .tmp sobrevive à gravação, a substituição
        não aconteceu.
        """
        dados = repositorio.carregar()
        dados["produtos"].append({"id": "PRD-001", "nome": "Lixívia"})
        repositorio.gravar(dados)

        temporario = repositorio.FICHEIRO_DADOS.with_suffix(".tmp")

        self.assertTrue(repositorio.FICHEIRO_DADOS.exists())
        self.assertFalse(temporario.exists())

    def teste_versao_posterior_e_recusada(self):
        """Dados gravados por uma versão mais recente não são carregados.

        Se carregasse, os campos que esta versão desconhece
        desapareceriam na gravação seguinte. Recusar arrancar é
        preferível a apagar informação em silêncio.
        """
        repositorio._garantir_pastas()
        conteudo = {
            "versao_dados": repositorio.config.VERSAO_DADOS + 1,
            "unidades": [],
        }

        with open(repositorio.FICHEIRO_DADOS, "w", encoding="utf-8") as f:
            json.dump(conteudo, f)

        with self.assertRaises(ValueError):
            repositorio.carregar()


class TesteBackups(BaseRepositorio):
    """Cópias de segurança diárias e eliminação das antigas."""

    def teste_backup_sem_dados_devolve_none(self):
        """Sem ficheiro de dados não há nada para copiar.

        É a primeira execução da aplicação. Devolver None em vez de dar
        erro permite a quem chama distinguir este caso do normal, sem
        envolver cada arranque num tratamento de exceção.
        """
        self.assertIsNone(repositorio.criar_backup())

    def teste_backup_cria_ficheiro_com_data_de_hoje(self):
        """A cópia é criada com a data no nome, em formato ISO.

        A data no nome permite à limpeza saber a idade de cada cópia sem
        consultar o sistema de ficheiros — a data de modificação diria
        quando foi copiada, não a que estado corresponde.
        """
        dados = repositorio.carregar()
        repositorio.gravar(dados)

        copia = repositorio.criar_backup()
        esperado = f"dados_{date.today().isoformat()}.json"

        self.assertIsNotNone(copia)
        assert copia is not None
        self.assertEqual(esperado, copia.name)
        assert copia is not None
        self.assertTrue(copia.exists())

    def teste_limpeza_elimina_apenas_as_antigas(self):
        """Cópias além do prazo são eliminadas; as de dentro do prazo ficam.

        O prazo de 30 dias cobre um ciclo de negócio completo: vencimento
        ao dia 5, avisos a 15 dias. Um erro de lançamento pode só ser
        detetado no fecho do mês seguinte.
        """
        repositorio._garantir_pastas()
        hoje = date.today()

        for dias in (5, 20, 31, 60):
            data_copia = hoje - timedelta(days=dias)
            ficheiro = (
                repositorio.PASTA_BACKUPS / f"dados_{data_copia.isoformat()}.json"
            )
            ficheiro.write_text("{}", encoding="utf-8")

        eliminadas = repositorio.limpar_backups_antigos(dias=30)
        restantes = list(repositorio.PASTA_BACKUPS.glob("dados_*.json"))

        self.assertEqual(2, eliminadas)
        self.assertEqual(2, len(restantes))

    def teste_backup_nao_sobrescreve_o_do_mesmo_dia(self):
        """Chamar duas vezes no mesmo dia não substitui a cópia da manhã.

        A cópia protege o estado com que o dia começou. Se cada arranque
        a sobrescrevesse, um erro detetado à tarde já estaria dentro da
        cópia — e a proteção desaparecia quando fosse precisa.
        """
        dados = repositorio.carregar()
        repositorio.gravar(dados)
        copia = repositorio.criar_backup()

        assert copia is not None
        conteudo_manha = copia.read_text(encoding="utf-8")

        dados["produtos"].append({"id": "PRD-001", "nome": "Lixívia"})
        repositorio.gravar(dados)
        repositorio.criar_backup()

        self.assertEqual(conteudo_manha, copia.read_text(encoding="utf-8"))

    def teste_limpeza_usa_o_prazo_da_configuracao(self):
        """Sem prazo indicado, a limpeza usa o valor configurado.

        A configuração é consultada a cada chamada e não fixada quando o
        módulo é lido, para uma alteração ao prazo produzir efeito sem
        reiniciar a aplicação.
        """
        repositorio._garantir_pastas()
        hoje = date.today()
        prazo = repositorio.config.DIAS_BACKUP

        for dias in (prazo - 1, prazo + 1):
            data_copia = hoje - timedelta(days=dias)
            ficheiro = (
                repositorio.PASTA_BACKUPS / f"dados_{data_copia.isoformat()}.json"
            )
            ficheiro.write_text("{}", encoding="utf-8")

        eliminadas = repositorio.limpar_backups_antigos()

        self.assertEqual(1, eliminadas)


if __name__ == "__main__":
    unittest.main()
