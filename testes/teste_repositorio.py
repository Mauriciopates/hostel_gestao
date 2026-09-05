"""Testes da camada de persistência.

Cobre só o que continua a existir em repositorio.py fora das funções
por entidade (essas têm teste próprio em cada teste_<entidade>.py,
via apoio_BD.py): os contadores de identificador (contadores.json) e
as cópias de segurança. A antiga TestePersistencia (carregar/gravar/
_estrutura_vazia, conversão de Decimal e date, gravação atómica,
recusa de versão posterior) foi removida nesta sessão — essas
funções saíram de repositorio.py por já não terem nenhum consumidor,
substituídas pelas funções por entidade que falam diretamente com o
MySQL (ver Estado_Projeto_2026-09-05.txt, secção 6).

`criar_backup()`/`limpar_backups_antigos()` passaram a usar mysqldump
em vez de copiar `dados.json` (que já não existe) — ver TesteBackups
para o que isso implica nos testes.

Cada teste corre numa pasta temporária própria, criada antes e eliminada
depois. As constantes de caminho do repositório são redirecionadas para
essa pasta e repostas no fim, para os testes nunca tocarem nos dados
reais de `dados/` e `backups/`.
"""

import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

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
            repositorio.FICHEIRO_CONTADORES,
        )

        repositorio.PASTA_DADOS = self.pasta / "dados"
        repositorio.PASTA_BACKUPS = self.pasta / "backups"
        repositorio.FICHEIRO_CONTADORES = (
            repositorio.PASTA_DADOS / "contadores.json"
        )

    def tearDown(self):
        """Repõe os caminhos originais e elimina a pasta temporária."""
        (
            repositorio.PASTA_DADOS,
            repositorio.PASTA_BACKUPS,
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
        `contadores.json` é independente de qualquer estrutura de
        registos (hoje, das próprias tabelas MySQL) — chamar
        proximo_id() várias vezes seguidas já prova isto sozinho, sem
        precisar de simular nenhuma eliminação.
        """
        for _ in range(5):
            repositorio.proximo_id("UNI")

        self.assertEqual("UNI-006", repositorio.proximo_id("UNI"))

    def teste_formato_com_tres_digitos(self):
        """O número é preenchido com zeros até três dígitos."""
        for _ in range(9):
            repositorio.proximo_id("UNI")

        self.assertEqual("UNI-010", repositorio.proximo_id("UNI"))


class TesteBackups(BaseRepositorio):
    """Cópias de segurança diárias (via mysqldump) e eliminação das antigas.

    `criar_backup()` agora faz um dump real da base de dados configurada
    em config.py — os testes que chamam a função sem simular uma falha
    precisam por isso de um MySQL local acessível com essas credenciais
    (o mesmo que os testes por entidade, via apoio_BD.py, já exigem).
    Só o caso de falha (binário `mysqldump` ausente) é simulado com
    mock, para não depender de desinstalar nada para o testar.
    """

    def teste_backup_sem_mysqldump_devolve_none(self):
        """Sem o binário mysqldump não há como fazer o dump.

        Devolver None em vez de propagar a exceção permite ao arranque
        continuar mesmo sem cópia de segurança (decisão: uma falha no
        backup não deve impedir o arranque do sistema). Simula-se a
        ausência do binário substituindo subprocess.run, em vez de
        depender de o mysqldump estar mesmo desinstalado.
        """
        with patch(
            "repositorio.subprocess.run", side_effect=FileNotFoundError
        ):
            resultado = repositorio.criar_backup()

        self.assertIsNone(resultado)

        destino = (
            repositorio.PASTA_BACKUPS / f"dump_{date.today().isoformat()}.sql"
        )
        self.assertFalse(destino.exists())

    def teste_backup_cria_ficheiro_com_data_de_hoje(self):
        """A cópia é criada com a data no nome, em formato ISO.

        A data no nome permite à limpeza saber a idade de cada cópia sem
        consultar o sistema de ficheiros — a data de modificação diria
        quando foi copiada, não a que estado corresponde.
        """
        copia = repositorio.criar_backup()
        esperado = f"dump_{date.today().isoformat()}.sql"

        self.assertIsNotNone(copia)
        assert copia is not None
        self.assertEqual(esperado, copia.name)
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
                repositorio.PASTA_BACKUPS
                / f"dump_{data_copia.isoformat()}.sql"
            )
            ficheiro.write_text("-- teste", encoding="utf-8")

        eliminadas = repositorio.limpar_backups_antigos(dias=30)
        restantes = list(repositorio.PASTA_BACKUPS.glob("dump_*.sql"))

        self.assertEqual(2, eliminadas)
        self.assertEqual(2, len(restantes))

    def teste_backup_nao_sobrescreve_o_do_mesmo_dia(self):
        """Chamar duas vezes no mesmo dia não substitui a cópia da manhã.

        A cópia protege o estado com que o dia começou. Se cada arranque
        a sobrescrevesse, um erro detetado à tarde já estaria dentro da
        cópia — e a proteção desaparecia quando fosse precisa. Como o
        conteúdo já não é controlado pelo teste (vem do mysqldump real),
        a prova é a data de modificação do ficheiro não mudar entre as
        duas chamadas.
        """
        primeira = repositorio.criar_backup()
        assert primeira is not None
        mtime_primeira = primeira.stat().st_mtime

        segunda = repositorio.criar_backup()

        self.assertEqual(primeira, segunda)
        assert segunda is not None
        self.assertEqual(mtime_primeira, segunda.stat().st_mtime)

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
                repositorio.PASTA_BACKUPS
                / f"dump_{data_copia.isoformat()}.sql"
            )
            ficheiro.write_text("-- teste", encoding="utf-8")

        eliminadas = repositorio.limpar_backups_antigos()

        self.assertEqual(1, eliminadas)


if __name__ == "__main__":
    unittest.main()
