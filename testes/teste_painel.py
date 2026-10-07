"""Testes de `painel.py` — os dados do Dashboard (v1.6.0).

Duas classes:

  1. `TesteAuxiliaresPuros` — unittest.TestCase puro, SEM MySQL.
     Datas de período, meses anterior/seguinte, variação %,
     vencimento em meses curtos.

  2. `TestePainel` — BaseMySQLTest (base de TESTE, nunca a real).
     Um cenário pequeno montado no `setUp`: duas propriedades, uma
     unidade mensal e duas Airbnb, um Staff atribuído a uma delas,
     três produtos e requisições em vários estados.

Datas fixas (outubro de 2026) em vez de `date.today()`: o painel
recebe sempre a data de fora, precisamente para poder ser testado
assim.
"""

import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest  # noqa: E402

import clientes  # noqa: E402
import contratos  # noqa: E402
import estoque  # noqa: E402
import painel  # noqa: E402
import propriedades  # noqa: E402
import responsaveis  # noqa: E402
import unidades  # noqa: E402

HOJE = date(2026, 10, 14)


class TesteAuxiliaresPuros(unittest.TestCase):

    def test_periodo_do_mes_fim_exclusivo(self):
        self.assertEqual(
            painel.periodo_do_mes(2026, 9),
            (date(2026, 9, 1), date(2026, 10, 1)),
        )

    def test_periodo_de_dezembro_atravessa_ano(self):
        self.assertEqual(
            painel.periodo_do_mes(2026, 12),
            (date(2026, 12, 1), date(2027, 1, 1)),
        )

    def test_mes_anterior_e_seguinte_nas_fronteiras(self):
        self.assertEqual(painel.mes_anterior(2026, 1), (2025, 12))
        self.assertEqual(painel.mes_anterior(2026, 7), (2026, 6))
        self.assertEqual(painel.mes_seguinte(2026, 12), (2027, 1))
        self.assertEqual(painel.mes_seguinte(2026, 3), (2026, 4))

    def test_variacao_percentual(self):
        self.assertEqual(
            painel.variacao_percentual(Decimal("106"), Decimal("100")), 6
        )
        self.assertEqual(
            painel.variacao_percentual(Decimal("50"), Decimal("100")), -50
        )

    def test_variacao_sem_base_e_none(self):
        self.assertIsNone(
            painel.variacao_percentual(Decimal("100"), Decimal("0"))
        )

    def test_vencimento_encosta_ao_fim_de_fevereiro(self):
        self.assertEqual(
            painel._data_vencimento(31, 2026, 2), date(2026, 2, 28)
        )
        self.assertEqual(
            painel._data_vencimento(31, 2028, 2), date(2028, 2, 29)
        )


def _cliente(nome, nif=""):
    if nif:
        return clientes.criar(
            nome,
            "Cartão de Cidadão",
            "12345678",
            "mensal",
            nif=nif,
            morada="Rua do Porto, 12",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912345678",
            data_nascimento=date(1990, 5, 20),
            validade_documento=date(2030, 1, 1),
            contacto_emergencia="Mãe: 912000000",
        )

    return clientes.criar(
        nome,
        "Passaporte",
        "X1234567",
        "airbnb",
        nacionalidade="Brasileira",
        data_nascimento=date(1985, 3, 12),
        validade_documento=date(2030, 1, 1),
        pais_emissor_documento="Brasil",
        pais_residencia="Brasil",
    )


def _reserva(unidade, cliente, inicio, fim):
    preco = contratos.calcular_preco_airbnb(unidade, inicio, fim)
    ocupacao, _ = contratos.registar_airbnb(
        unidade["id"], cliente["id"], inicio, fim, preco
    )
    return ocupacao


class TestePainel(BaseMySQLTest):

    def setUp(self):
        super().setUp()

        self.master = responsaveis.criar("Mestre", tipo_utilizador="Master")
        self.staff = responsaveis.criar("Rui Costa", tipo_utilizador="Staff")

        ribeira = propriedades.criar("Ribeira", "Rua A, 1")
        bonfim = propriedades.criar("Bonfim", "Rua B, 2")

        self.t1 = unidades.criar(
            ribeira["id"], "T1", "airbnb",
            Decimal("45.00"), Decimal("90.00"), Decimal("20.00"),
            epoca_alta_ativa=False,
        )
        self.t2 = unidades.criar(
            ribeira["id"], "T2", "airbnb",
            Decimal("45.00"), Decimal("90.00"), Decimal("20.00"),
            epoca_alta_ativa=False,
        )
        self.q1 = unidades.criar(
            bonfim["id"], "Q1", "mensal",
            Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
        )
        quarto = unidades.criar_quarto(self.q1["id"], "Quarto")
        unidades.criar_lugar(quarto["id"], "Cama", "casal", capacidade=2)

        # O staff limpa o T1 (e só o T1).
        unidades.atribuir_responsavel(self.t1["id"], self.staff["id"])

        self.ana = _cliente("Ana Ribeiro", nif="501442600")
        self.lena = _cliente("Lena Becker")
        self.jean = _cliente("Jean Moreau")

        # T1: Lena sai hoje, Jean entra amanhã -> limpeza urgente.
        self.saida_t1 = _reserva(
            self.t1, self.lena, HOJE - timedelta(days=3), HOJE
        )
        self.entrada_t1 = _reserva(
            self.t1, self.jean, HOJE + timedelta(days=1),
            HOJE + timedelta(days=4),
        )
        # T2: entra hoje, sai daqui a 2 dias (sem staff atribuído).
        self.entrada_t2 = _reserva(
            self.t2, self.lena, HOJE, HOJE + timedelta(days=2)
        )
        # Q1: contrato mensal com vencimento a dia 18.
        self.contrato, _ = contratos.criar_mensal(
            self.q1["id"],
            self.ana["id"],
            date(2026, 9, 1),
            Decimal("250.00"),
            Decimal("250.00"),
            dia_vencimento=18,
        )

    # -- Hoje ---------------------------------------------------------

    def test_kpis_contam_entradas_e_saidas_por_regime(self):
        kpis = painel.kpis_hoje(HOJE)

        self.assertEqual(kpis["entradas"], {"airbnb": 1, "mensal": 0})
        self.assertEqual(kpis["saidas"], {"airbnb": 1, "mensal": 0})
        self.assertEqual(kpis["airbnb"][1], 2)

    def test_movimento_resolve_nomes(self):
        movimento = painel.movimento_do_dia(HOJE)

        self.assertEqual(len(movimento["entradas"]), 1)
        entrada = movimento["entradas"][0]
        self.assertEqual(entrada["unidade"], "Ribeira · T2")
        self.assertEqual(entrada["cliente"], "Lena Becker")
        self.assertEqual(entrada["noites"], 2)

        self.assertEqual(movimento["saidas"][0]["unidade"], "Ribeira · T1")

    def test_limpeza_urgente_quando_ha_entrada_no_dia_seguinte(self):
        lista = painel.limpezas(HOJE)

        self.assertEqual(len(lista), 1)
        limpeza = lista[0]
        self.assertEqual(limpeza["unidade_id"], self.t1["id"])
        self.assertTrue(limpeza["urgente"])
        self.assertEqual(
            limpeza["proxima_entrada"], HOJE + timedelta(days=1)
        )
        self.assertEqual(limpeza["staff"], ["Rui Costa"])

    def test_limpeza_nao_urgente_sem_entrada_proxima(self):
        lista = painel.limpezas(HOJE + timedelta(days=2))

        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["unidade_id"], self.t2["id"])
        self.assertFalse(lista[0]["urgente"])
        self.assertEqual(lista[0]["staff"], [])

    def test_limpezas_do_staff_so_as_unidades_dele(self):
        lista = painel.limpezas(
            HOJE, dias=3, responsavel_id=self.staff["id"]
        )

        self.assertEqual(
            {linha["unidade_id"] for linha in lista}, {self.t1["id"]}
        )

    def test_limpezas_dias_invalido(self):
        with self.assertRaises(ValueError):
            painel.limpezas(HOJE, dias=0)

    def test_proximos_dias_inclui_dias_sem_movimento(self):
        resumo = painel.proximos_dias(HOJE, dias=3)

        self.assertEqual(
            [d["data"] for d in resumo],
            [HOJE + timedelta(days=n) for n in (1, 2, 3)],
        )
        self.assertEqual(resumo[0]["entradas"], 1)
        self.assertEqual(resumo[1]["saidas"], 1)
        self.assertEqual(resumo[2]["entradas"] + resumo[2]["saidas"], 0)

    # -- Alertas --------------------------------------------------------

    def _preparar_stock_baixo(self):
        lixivia = estoque.criar_produto("Lixívia", "unid", stock_minimo=5)
        estoque.registar_movimento(
            lixivia["id"], "entrada", 1, HOJE,
            responsavel_id=self.master["id"],
        )
        return lixivia

    def test_alerta_stock_para_todos_os_perfis(self):
        self._preparar_stock_baixo()

        for perfil in ("Master", "Admin", "Staff"):
            chaves = [a["chave"] for a in painel.alertas(perfil)]
            self.assertIn("stock", chaves)

        alerta = painel.alertas("Staff")[0]
        self.assertEqual(alerta["detalhe"], "Lixívia (1/5)")
        self.assertEqual(alerta["peso"], "erro")

    def test_requisicoes_pendentes_nao_aparecem_ao_staff(self):
        lixivia = self._preparar_stock_baixo()
        estoque.criar_requisicao(
            self.staff["id"],
            [{"produto_id": lixivia["id"], "quantidade_pedida": 1}],
            HOJE,
        )

        chaves_master = [a["chave"] for a in painel.alertas("Master")]
        chaves_staff = [a["chave"] for a in painel.alertas("Staff")]

        self.assertIn("requisicoes", chaves_master)
        self.assertNotIn("requisicoes", chaves_staff)

    def test_sem_perfil_nao_ha_alertas(self):
        self._preparar_stock_baixo()

        self.assertEqual(painel.alertas(None), [])

    # -- Financeiro ---------------------------------------------------

    def test_renda_a_vencer_dentro_da_janela(self):
        lista = painel.rendas_a_vencer(HOJE, dias=7)

        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["vencimento"], date(2026, 10, 18))
        self.assertEqual(lista[0]["valor"], Decimal("250.00"))
        self.assertEqual(lista[0]["unidade"], "Bonfim · Q1")

    def test_renda_fora_da_janela_nao_aparece(self):
        self.assertEqual(painel.rendas_a_vencer(HOJE, dias=3), [])

    def test_renda_passa_para_o_mes_seguinte(self):
        lista = painel.rendas_a_vencer(date(2026, 10, 25), dias=30)

        self.assertEqual(lista[0]["vencimento"], date(2026, 11, 18))

    def test_evolucao_mensal_ordem_e_rotulos(self):
        lista = painel.evolucao_mensal(2026, 10, meses=3)

        self.assertEqual(
            [linha["rotulo"] for linha in lista], ["ago", "set", "out"]
        )
        # Setembro só tem o contrato mensal; outubro soma as reservas.
        self.assertEqual(lista[1]["receita"], Decimal("250.00"))
        self.assertGreater(lista[2]["receita"], lista[1]["receita"])

    def test_resumo_financeiro_compara_com_mes_anterior(self):
        resumo = painel.resumo_financeiro(2026, 10)

        self.assertIn("receita", resumo["atual"])
        # Setembro e outubro têm o mesmo contrato mensal; a receita
        # Airbnb de outubro sobe a variação acima de zero.
        self.assertIsNotNone(resumo["variacao_receita"])
        self.assertGreater(resumo["variacao_receita"], 0)

    # -- Staff ------------------------------------------------------------

    def test_requisicoes_do_staff_separa_enviadas_e_pendentes(self):
        toalhas = estoque.criar_produto("Toalhas", "unid", stock_minimo=2)
        estoque.registar_movimento(
            toalhas["id"], "entrada", 20, HOJE,
            responsavel_id=self.master["id"],
        )
        itens = [{"produto_id": toalhas["id"], "quantidade_pedida": 2}]

        enviada = estoque.criar_requisicao(self.staff["id"], itens, HOJE)
        estoque.enviar_requisicao(enviada["id"], self.master["id"], HOJE)
        pendente = estoque.criar_requisicao(self.staff["id"], itens, HOJE)
        # Uma do Master — não pode aparecer na lista do staff.
        estoque.criar_requisicao(self.master["id"], itens, HOJE)

        resultado = painel.requisicoes_do_staff(self.staff["id"])

        self.assertEqual(
            [r["id"] for r in resultado["a_confirmar"]], [enviada["id"]]
        )
        self.assertEqual(
            [r["id"] for r in resultado["pendentes"]], [pendente["id"]]
        )
        self.assertEqual(resultado["a_confirmar"][0]["n_itens"], 1)

    def test_stock_disponivel_ordena_do_mais_critico(self):
        lixivia = self._preparar_stock_baixo()           # 1/5
        papel = estoque.criar_produto("Papel", "rolo", stock_minimo=10)
        estoque.registar_movimento(
            papel["id"], "entrada", 30, HOJE,
            responsavel_id=self.master["id"],
        )                                                # 30/10
        estoque.criar_produto("Esponja", "unid", stock_minimo=0)

        lista = painel.stock_disponivel()

        self.assertEqual(
            [linha["produto"]["id"] for linha in lista][:2],
            [lixivia["id"], papel["id"]],
        )
        self.assertTrue(lista[0]["abaixo"])
        self.assertFalse(lista[1]["abaixo"])
        # Sem mínimo definido vai para o fim.
        self.assertIsNone(lista[-1]["proporcao"])


if __name__ == "__main__":
    unittest.main()
