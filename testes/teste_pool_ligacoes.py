"""Testes do reaproveitamento de ligações (`repositorio._base`).

Não precisam de MySQL: a ligação real é um objeto falso que regista o
que lhe fazem. Verificam as garantias que mantêm o comportamento igual
ao de antes de as ligações serem reaproveitadas:

- `close()` devolve a ligação em vez de a fechar, e faz ROLLBACK;
- a próxima `obter_conexao()` reaproveita-a (uma só abertura);
- chamadas encadeadas recebem ligações DIFERENTES;
- servidor/base diferentes nunca partilham ligações;
- uma ligação morta é descartada e abre-se outra;
- depois de `close()` a ligação já não se pode usar;
- HOSTEL_SEM_POOL=1 volta ao comportamento antigo.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
import mysql.connector  # noqa: E402
from repositorio import _base  # noqa: E402


class LigacaoFalsa:
    def __init__(self, base):
        self.base = base
        self.fechada = False
        self.rollbacks = 0
        self.viva = True
        self.falhar_rollback = False

    def cursor(self, *a, **kw):
        return object()

    def rollback(self):
        if self.falhar_rollback:
            raise mysql.connector.Error("Unread result found")
        self.rollbacks += 1

    def is_connected(self):
        return self.viva

    def close(self):
        self.fechada = True


class TestePoolLigacoes(unittest.TestCase):
    def setUp(self):
        self.abertas = []

        def falsa(**kwargs):
            lig = LigacaoFalsa(kwargs["database"])
            self.abertas.append(lig)
            return lig

        self._patches = [
            patch.object(_base.mysql.connector, "connect", side_effect=falsa),
            patch.object(_base.servidores, "garantir_tunel"),
            patch.object(_base, "_REUTILIZAR", True),
        ]
        for p in self._patches:
            p.start()
        _base.fechar_ligacoes()

    def tearDown(self):
        _base.fechar_ligacoes()
        for p in reversed(self._patches):
            p.stop()

    def test_close_devolve_e_reaproveita(self):
        a = _base.obter_conexao()
        a.close()
        b = _base.obter_conexao()
        b.close()

        self.assertEqual(len(self.abertas), 1)
        self.assertFalse(self.abertas[0].fechada)

    def test_close_faz_rollback(self):
        _base.obter_conexao().close()

        self.assertEqual(self.abertas[0].rollbacks, 1)

    def test_fechar_duas_vezes_nao_faz_mal(self):
        a = _base.obter_conexao()
        a.close()
        a.close()

        self.assertEqual(self.abertas[0].rollbacks, 1)

    def test_chamadas_encadeadas_recebem_ligacoes_diferentes(self):
        externa = _base.obter_conexao()
        interna = _base.obter_conexao()

        self.assertEqual(len(self.abertas), 2)
        self.assertIsNot(externa._real, interna._real)

        interna.close()
        # A externa continua intacta: o close da interna não lhe tocou.
        self.assertEqual(externa._real.rollbacks, 0)
        externa.close()

    def test_bases_diferentes_nao_se_misturam(self):
        _base.obter_conexao().close()
        _base.obter_conexao(base="outra_base").close()

        self.assertEqual(len(self.abertas), 2)
        self.assertEqual({lig.base for lig in self.abertas},
                         {config.DB_NAME, "outra_base"})

    def test_mudar_config_db_name_nao_reaproveita(self):
        original = config.DB_NAME
        try:
            _base.obter_conexao().close()
            config.DB_NAME = "base_de_teste_x"
            _base.obter_conexao().close()
        finally:
            config.DB_NAME = original

        self.assertEqual(len(self.abertas), 2)

    def test_ligacao_morta_e_descartada(self):
        _base.obter_conexao().close()
        morta = self.abertas[0]
        morta.viva = False

        with patch.object(_base, "_VERIFICAR_APOS_S", -1):
            nova = _base.obter_conexao()

        self.assertTrue(morta.fechada)
        self.assertEqual(len(self.abertas), 2)
        nova.close()

    def test_rollback_a_falhar_descarta_a_ligacao(self):
        a = _base.obter_conexao()
        a._real.falhar_rollback = True
        a.close()
        _base.obter_conexao().close()

        self.assertTrue(self.abertas[0].fechada)
        self.assertEqual(len(self.abertas), 2)

    def test_usar_depois_de_close_da_erro(self):
        a = _base.obter_conexao()
        a.close()

        with self.assertRaises(mysql.connector.Error):
            a.cursor()

    def test_with_fecha_no_fim(self):
        with _base.obter_conexao() as conexao:
            conexao.cursor()
        _base.obter_conexao().close()

        self.assertEqual(len(self.abertas), 1)

    def test_limite_de_ligacoes_livres(self):
        todas = [_base.obter_conexao() for _ in range(_base._MAX_LIVRES + 2)]
        for c in todas:
            c.close()

        fechadas = [lig for lig in self.abertas if lig.fechada]
        self.assertEqual(len(fechadas), 2)

    def test_fechar_ligacoes_fecha_as_livres(self):
        _base.obter_conexao().close()
        _base.fechar_ligacoes()

        self.assertTrue(self.abertas[0].fechada)

    def test_sem_pool_volta_ao_comportamento_antigo(self):
        with patch.object(_base, "_REUTILIZAR", False):
            a = _base.obter_conexao()
            a.close()
            _base.obter_conexao().close()

        self.assertEqual(len(self.abertas), 2)
        self.assertTrue(self.abertas[0].fechada)


if __name__ == "__main__":
    unittest.main()
