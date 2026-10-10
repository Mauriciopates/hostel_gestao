"""Testes do modo `--desempenho` (v2.1.0) — unittest, sem base de
dados: o `desempenho` faz contas e embrulha o conector (testa-se com
um conector falso) e o `impressao.desempenho` grava ficheiros (numa
pasta temporária).
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import desempenho  # noqa: E402
import impressao.desempenho as relatorio  # noqa: E402


def _abertura(total, dados=0.0, consultas=0, escritas=0, widgets=10):
    lista = [{"sql": "SELECT * FROM t WHERE id = %s", "ms": dados / max(
        consultas, 1), "escrita": False} for _ in range(consultas)]
    lista += [{"sql": "INSERT INTO t VALUES (%s)", "ms": 1.0,
               "escrita": True} for _ in range(escritas)]
    return desempenho.medicao(
        total=total, construcao_bruta=total / 2, consultas=lista,
        ligacoes=[], consultas_construcao=lista, ligacoes_construcao=[],
        widgets=widgets,
    )


class _CursorFalso:
    def __init__(self):
        self.feitas = []

    def execute(self, sql, *args):
        self.feitas.append(sql)

    def fetchall(self):
        return [(1,)]

    def close(self):
        pass


class _LigacaoFalsa:
    def __init__(self):
        self.cursor_real = _CursorFalso()

    def cursor(self, *args, **kwargs):
        return self.cursor_real

    def is_connected(self):
        return True


class _ModuloFalso:
    def __init__(self):
        self.ligacoes = 0

    def connect(self, *args, **kwargs):
        self.ligacoes += 1
        return _LigacaoFalsa()


class TesteInstrumentar(unittest.TestCase):

    def setUp(self):
        desempenho.ESTADO.consultas.clear()
        desempenho.ESTADO.ligacoes.clear()

    def test_conta_ligacoes_e_consultas_e_deixa_passar_o_resto(self):
        modulo = _ModuloFalso()
        desempenho.instrumentar_mysql(modulo)

        ligacao = modulo.connect(host="x")
        cursor = ligacao.cursor()
        cursor.execute("SELECT 1")
        self.assertEqual(cursor.fetchall(), [(1,)])
        cursor.execute("UPDATE t SET a = %s", (1,))

        self.assertTrue(ligacao.is_connected())
        self.assertEqual(modulo.ligacoes, 1)
        self.assertEqual(len(desempenho.ESTADO.ligacoes), 1)
        self.assertEqual(
            [c["escrita"] for c in desempenho.ESTADO.consultas],
            [False, True],
        )

    def test_marca_e_desde(self):
        modulo = _ModuloFalso()
        desempenho.instrumentar_mysql(modulo)
        modulo.connect().cursor().execute("SELECT 1")
        marca = desempenho.ESTADO.marca()
        modulo.connect().cursor().execute("SELECT 2")

        consultas, ligacoes = desempenho.ESTADO.desde(marca)
        self.assertEqual([c["sql"] for c in consultas], ["SELECT 2"])
        self.assertEqual(len(ligacoes), 1)


class TesteContas(unittest.TestCase):

    def test_e_escrita(self):
        self.assertTrue(desempenho.e_escrita("  insert into x values (1)"))
        self.assertFalse(desempenho.e_escrita("SELECT * FROM x"))

    def test_medicao_parte_o_tempo_em_fases(self):
        m = _abertura(total=100, dados=40, consultas=4)
        self.assertAlmostEqual(m["dados"], 40)
        self.assertAlmostEqual(m["construcao"], 10)  # 50 - 40
        self.assertAlmostEqual(m["desenho"], 50)  # 100 - 40 - 10

    def test_estado_de(self):
        self.assertEqual(desempenho.estado_de(100), "OK")
        self.assertEqual(desempenho.estado_de(500), "Atenção")
        self.assertEqual(desempenho.estado_de(1500), "Lento")

    def test_juntar_repeticoes_faz_a_media_e_guarda_a_primeira(self):
        linha = desempenho.juntar_repeticoes(
            "Clientes",
            [_abertura(300), _abertura(100), _abertura(200)],
        )
        self.assertAlmostEqual(linha["total"], 200)
        self.assertAlmostEqual(linha["primeira"], 300)
        self.assertAlmostEqual(linha["maximo"], 300)
        self.assertEqual(linha["estado"], "OK")
        self.assertTrue(linha["dicas"])

    def test_dica_para_muitas_consultas_e_para_escritas(self):
        linha = desempenho.juntar_repeticoes(
            "Stock", [_abertura(900, dados=600, consultas=20, escritas=1)]
        )
        texto = " ".join(linha["dicas"])
        self.assertIn("21 consultas", texto)  # 20 + 1 escrita
        self.assertIn("Grava 1x", texto)
        self.assertEqual(linha["escritas"], 1)

    def test_resumo_ignora_saltados_e_erros(self):
        linhas = [
            desempenho.juntar_repeticoes("A", [_abertura(1000)]),
            desempenho.juntar_repeticoes("B", [_abertura(200)]),
            desempenho.linha_saltada("Despesas", "grava"),
            desempenho.linha_com_erro("C", ValueError("x")),
        ]
        r = desempenho.resumo(linhas)
        self.assertEqual(r["medidos"], 2)
        self.assertEqual(r["lentos"], 1)
        self.assertEqual(r["mais_lento"]["nome"], "A")

    def test_resumo_sem_nada_medido(self):
        self.assertEqual(desempenho.resumo([])["medidos"], 0)

    def test_hub_de_despesas_esta_na_lista_dos_que_gravam(self):
        self.assertIn("EcraDespesas", desempenho.ECRAS_QUE_GRAVAM)


class TesteRelatorio(unittest.TestCase):

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.patcher = patch(
            "impressao.desempenho.base.pasta_relatorios",
            return_value=self.pasta,
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _linhas(self, total=500):
        return [
            desempenho.juntar_repeticoes("Clientes", [_abertura(total)]),
            desempenho.linha_saltada("Despesas", "lança recorrentes"),
        ]

    def test_grava_html_csv_e_json(self):
        caminho = relatorio.gravar(
            self._linhas(), "nova-vm", 3, agora=datetime(2026, 10, 10, 9)
        )
        self.assertTrue(caminho.exists())
        html = caminho.read_text(encoding="utf-8")
        self.assertNotIn("__JSON__", html)
        self.assertIn("Clientes", html)

        csv_texto = caminho.with_suffix(".csv").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn("Despesas;SALTADO", csv_texto)

        dados = json.loads(
            caminho.with_suffix(".json").read_text(encoding="utf-8")
        )
        self.assertEqual(dados["servidor"], "nova-vm")
        self.assertEqual(dados["resumo"]["medidos"], 1)

    def test_compara_com_a_anterior_do_mesmo_servidor(self):
        relatorio.gravar(self._linhas(800), "nova-vm", 3,
                         agora=datetime(2026, 10, 10, 9))
        relatorio.gravar(self._linhas(100), "Local", 3,
                         agora=datetime(2026, 10, 10, 10))
        caminho = relatorio.gravar(self._linhas(400), "nova-vm", 3,
                                   agora=datetime(2026, 10, 10, 11))

        dados = json.loads(
            caminho.with_suffix(".json").read_text(encoding="utf-8")
        )
        clientes = dados["linhas"][0]
        self.assertAlmostEqual(clientes["anterior"], 800)

    def test_primeira_medicao_nao_tem_anterior(self):
        caminho = relatorio.gravar(self._linhas(), "nova-vm", 3,
                                   agora=datetime(2026, 10, 10, 9))
        dados = json.loads(
            caminho.with_suffix(".json").read_text(encoding="utf-8")
        )
        self.assertIsNone(dados["linhas"][0]["anterior"])


if __name__ == "__main__":
    unittest.main()
