"""Testes da camada de persistência.

Cobre só o que continua a existir em repositorio.py fora das funções
por entidade (essas têm teste próprio em cada teste_<entidade>.py,
via apoio_BD.py): o gerador de identificadores (`proximo_id`) e as
cópias de segurança. A antiga TestePersistencia (carregar/gravar/
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

NOTA (Fase 1, v1.4.0 — pastas persistentes): o `repositorio.py` deixou
de expor `PASTA_DADOS`/`PASTA_BACKUPS` como constantes próprias — os
caminhos vivem em `config.DIR_DADOS` e `config.DIR_BACKUPS`. Por isso
o `setUp` deste ficheiro redireciona `config.DIR_*`,
não `repositorio.PASTA_*` — mesma convenção já usada pelo
`apoio_BD.BaseMySQLTest`.

v1.8.0 (decisão D4): o `contadores.json` deixou de existir. O
`proximo_id` calcula o número a partir do MAX(id) da tabela, por isso
os seus testes passaram a usar a base de teste (`BaseMySQLTest`) e a
gravar propriedades entre chamadas.
"""

import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
import repositorio  # noqa: E402
from testes.apoio_BD import BaseMySQLTest  # noqa: E402


class BaseRepositorio(unittest.TestCase):
    """Preparação comum a todos os testes do repositório."""

    def setUp(self):
        """Cria a pasta temporária e redireciona os caminhos."""
        self.pasta = Path(tempfile.mkdtemp())

        self.originais = (
            config.DIR_DADOS,
            config.DIR_BACKUPS,
        )

        config.DIR_DADOS = self.pasta / "dados"
        config.DIR_BACKUPS = self.pasta / "backups"

    def tearDown(self):
        """Repõe os caminhos originais e elimina a pasta temporária."""
        (
            config.DIR_DADOS,
            config.DIR_BACKUPS,
        ) = self.originais

        shutil.rmtree(self.pasta, ignore_errors=True)


def _gravar_propriedade(id_propriedade):
    """Grava uma propriedade mínima com o id indicado, direto no
    repositório — o que se testa aqui é o `proximo_id`, não o
    `propriedades.criar`."""
    repositorio.inserir_propriedade(
        {
            "id": id_propriedade,
            "nome": f"Teste {id_propriedade}",
            "morada": "",
            "iban": "",
            "ativo": True,
        }
    )


class TesteProximoId(BaseMySQLTest):
    """Identificadores calculados a partir do MAX(id) da tabela
    (v1.8.0, decisão D4). Cada teste começa com as tabelas vazias."""

    def teste_primeiro_id_de_um_prefixo(self):
        """Tabela vazia: o primeiro identificador é o 001."""
        self.assertEqual("PRO-001", repositorio.proximo_id("PRO"))

    def teste_nao_reserva_numeros(self):
        """Sem gravar nada entre as chamadas, o ID repete-se."""
        primeiro = repositorio.proximo_id("PRO")

        self.assertEqual(primeiro, repositorio.proximo_id("PRO"))

    def teste_depois_de_gravar_devolve_o_seguinte(self):
        """Cada ID gravado faz avançar o seguinte."""
        _gravar_propriedade(repositorio.proximo_id("PRO"))
        _gravar_propriedade(repositorio.proximo_id("PRO"))

        self.assertEqual("PRO-003", repositorio.proximo_id("PRO"))

    def teste_registo_semeado_fora_do_gerador_conta(self):
        """Um registo gravado por SQL/migração (sem passar pelo
        gerador) é contado — era o caso da CAT-001 e dos ITD, que
        davam chave duplicada com o antigo contadores.json."""
        _gravar_propriedade("PRO-007")

        self.assertEqual("PRO-008", repositorio.proximo_id("PRO"))

    def teste_comparacao_numerica_e_nao_de_texto(self):
        """Depois do 999 vem o 1000 (numa comparação de texto,
        "PRO-1000" ficaria antes de "PRO-999")."""
        _gravar_propriedade("PRO-999")
        _gravar_propriedade("PRO-1000")

        self.assertEqual("PRO-1001", repositorio.proximo_id("PRO"))

    def teste_formato_com_tres_digitos(self):
        """O número é preenchido com zeros até três dígitos."""
        _gravar_propriedade("PRO-009")

        self.assertEqual("PRO-010", repositorio.proximo_id("PRO"))

    def teste_prefixos_independentes(self):
        """Cada prefixo conta só na sua tabela."""
        _gravar_propriedade("PRO-005")

        self.assertEqual("CLI-001", repositorio.proximo_id("CLI"))

    def teste_ignora_ids_noutro_formato(self):
        """IDs sem o hífen (ex. o antigo seed CAT000001) não entram
        no MAX — só contam os `<prefixo>-<número>`."""
        _gravar_propriedade("PRO000009")

        self.assertEqual("PRO-001", repositorio.proximo_id("PRO"))

    def teste_prefixo_desconhecido_recusa(self):
        """Um prefixo sem tabela associada levanta ValueError."""
        with self.assertRaises(ValueError):
            repositorio.proximo_id("OCU")


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
            config.DIR_BACKUPS / f"dump_{date.today().isoformat()}.sql"
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
                config.DIR_BACKUPS
                / f"dump_{data_copia.isoformat()}.sql"
            )
            ficheiro.write_text("-- teste", encoding="utf-8")

        eliminadas = repositorio.limpar_backups_antigos(dias=30)
        restantes = list(config.DIR_BACKUPS.glob("dump_*.sql"))

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
                config.DIR_BACKUPS
                / f"dump_{data_copia.isoformat()}.sql"
            )
            ficheiro.write_text("-- teste", encoding="utf-8")

        eliminadas = repositorio.limpar_backups_antigos()

        self.assertEqual(1, eliminadas)


if __name__ == "__main__":
    unittest.main()
