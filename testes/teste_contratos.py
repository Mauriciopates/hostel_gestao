"""Testes de contratos.py — contratos mensais e reservas Airbnb.

sys.path.insert(0, 'src') porque o unittest corre a partir da raiz
do projeto, e sem isto não encontraria os módulos.
"""

import sys
import unittest
from datetime import date
from decimal import Decimal

sys.path.insert(0, "src")

import clientes
import contratos
import propriedades
import repositorio
import unidades


class BaseContratosTest(unittest.TestCase):
    """Fornece uma estrutura de dados com uma unidade mensal (com
    um quarto e um lugar de capacidade 2), uma unidade Airbnb, e
    um cliente para cada regime — reutilizada por todas as
    subclasses abaixo.
    """

    def setUp(self):
        self.dados = repositorio._estrutura_vazia()

        self.propriedade = propriedades.criar(self.dados, "Foz Velha")

        self.unidade_mensal = unidades.criar(
            self.dados,
            self.propriedade["id"],
            "mensal",
            Decimal("250.00"),
            Decimal("250.00"),
            Decimal("20.00"),
        )
        self.quarto = unidades.criar_quarto(
            self.dados, self.unidade_mensal["id"], "Quarto 1"
        )
        self.lugar = unidades.criar_lugar(
            self.dados, self.quarto["id"], "Cama 1", capacidade=2
        )

        self.unidade_airbnb = unidades.criar(
            self.dados,
            self.propriedade["id"],
            "airbnb",
            Decimal("45.00"),
            Decimal("90.00"),
            Decimal("20.00"),
            epoca_alta_ativa=True,
        )

        self.cliente_mensal = clientes.criar(
            self.dados,
            "João Silva",
            "Cartão de Cidadão",
            "11111111",
            "mensal",
            nif="123456789",
        )
        self.cliente_airbnb = clientes.criar(
            self.dados,
            "Ana Costa",
            "Passaporte",
            "X9999999",
            "airbnb",
        )


class TesteCriarMensal(BaseContratosTest):

    def test_cria_contrato_com_sucesso(self):
        ocupacao, mensal = contratos.criar_mensal(
            self.dados,
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertEqual(ocupacao["tipo"], "mensal")
        self.assertIsNone(ocupacao["data_fim"])
        self.assertTrue(ocupacao["ativo"])
        self.assertEqual(mensal["renda_calculada"], Decimal("250.00"))
        self.assertIn(ocupacao, self.dados["ocupacoes"])
        self.assertIn(mensal, self.dados["ocupacoes_mensal"])

    def test_id_gerado_com_prefixo_ocu(self):
        ocupacao, _ = contratos.criar_mensal(
            self.dados,
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertTrue(ocupacao["id"].startswith("OCU-"))

    def test_unidade_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados,
                "UNI-999",
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_unidade_airbnb_recusada(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados,
                self.unidade_airbnb["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_cliente_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados,
                self.unidade_mensal["id"],
                "CLI-999",
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_cliente_inativo_recusado(self):
        clientes.desativar(self.dados, self.cliente_mensal["id"])
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados,
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_bloqueia_ao_atingir_capacidade(self):
        # capacidade da unidade = 2 (um único lugar, capacidade 2)
        cliente_2 = clientes.criar(
            self.dados, "Maria", "Cartão de Cidadão", "222", "mensal",
            nif="222222220",
        )
        cliente_3 = clientes.criar(
            self.dados, "Pedro", "Cartão de Cidadão", "333", "mensal",
            nif="333333330",
        )
        contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"], self.cliente_mensal["id"],
            date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
        )
        contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"], cliente_2["id"],
            date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
        )
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados, self.unidade_mensal["id"], cliente_3["id"],
                date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
            )

    def test_lugar_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados,
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
                lugar_id="LUG-999",
            )

    def test_lugar_de_outra_unidade_recusado(self):
        outra_unidade = unidades.criar(
            self.dados, self.propriedade["id"], "mensal",
            Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
        )
        outro_quarto = unidades.criar_quarto(
            self.dados, outra_unidade["id"], "Quarto X"
        )
        outro_lugar = unidades.criar_lugar(
            self.dados, outro_quarto["id"], "Cama X"
        )
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados,
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
                lugar_id=outro_lugar["id"],
            )

    def test_lugar_de_casal_admite_dois_contratos(self):
        cliente_2 = clientes.criar(
            self.dados, "Maria", "Cartão de Cidadão", "222", "mensal",
            nif="222222220",
        )
        contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"], self.cliente_mensal["id"],
            date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
            lugar_id=self.lugar["id"],
        )
        # segundo contrato no mesmo lugar (capacidade 2) tem de passar
        ocupacao, _ = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"], cliente_2["id"],
            date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
            lugar_id=self.lugar["id"],
        )
        self.assertEqual(ocupacao["lugar_id"], self.lugar["id"])

    def test_lugar_esgotado_recusa_terceiro_contrato(self):
        cliente_2 = clientes.criar(
            self.dados, "Maria", "Cartão de Cidadão", "222", "mensal",
            nif="222222220",
        )
        # capacidade total da unidade sobe para 3, para isolar o teste
        # do lugar (capacidade 2) e não colidir com a capacidade total
        outro_quarto = unidades.criar_quarto(
            self.dados, self.unidade_mensal["id"], "Quarto 2"
        )
        unidades.criar_lugar(self.dados, outro_quarto["id"], "Cama 2")

        cliente_3 = clientes.criar(
            self.dados, "Pedro", "Cartão de Cidadão", "333", "mensal",
            nif="333333330",
        )
        contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"], self.cliente_mensal["id"],
            date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
            lugar_id=self.lugar["id"],
        )
        contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"], cliente_2["id"],
            date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
            lugar_id=self.lugar["id"],
        )
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados, self.unidade_mensal["id"], cliente_3["id"],
                date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
                lugar_id=self.lugar["id"],
            )

    def test_renda_invalida_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados, self.unidade_mensal["id"],
                self.cliente_mensal["id"], date(2026, 1, 10),
                Decimal("0.00"), Decimal("0.00"),
            )

    def test_caucao_acima_do_teto_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.dados, self.unidade_mensal["id"],
                self.cliente_mensal["id"], date(2026, 1, 10),
                Decimal("250.00"), Decimal("600.00"),
            )

    def test_documento_ja_caducado_marca_aviso(self):
        cliente = clientes.criar(
            self.dados, "Expirado", "Passaporte", "999", "mensal",
            nif="444444440",
            validade_documento=date(2025, 12, 31),
        )
        ocupacao, _ = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"], cliente["id"],
            date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
        )
        self.assertTrue(ocupacao["aviso_documento"])

    def test_documento_valido_nao_marca_aviso(self):
        cliente = clientes.criar(
            self.dados, "Válido", "Passaporte", "888", "mensal",
            nif="555555550",
            validade_documento=date(2030, 1, 1),
        )
        ocupacao, _ = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"], cliente["id"],
            date(2026, 1, 10), Decimal("250.00"), Decimal("250.00"),
        )
        self.assertFalse(ocupacao["aviso_documento"])


class TesteAtualizarMensal(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.ocupacao, self.mensal = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"],
            self.cliente_mensal["id"], date(2026, 1, 10),
            Decimal("250.00"), Decimal("250.00"),
        )

    def test_altera_renda_praticada(self):
        _, mensal = contratos.atualizar_mensal(
            self.dados, self.ocupacao["id"], renda_praticada=Decimal("260.00")
        )
        self.assertEqual(mensal["renda_praticada"], Decimal("260.00"))
        # renda_calculada nunca muda
        self.assertEqual(mensal["renda_calculada"], Decimal("250.00"))

    def test_revalida_caucao_quando_so_a_renda_muda(self):
        # caução igual à renda original (250); baixar a renda para 100
        # faz o teto (100 * 2 = 200) ficar abaixo da caução guardada (250)
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal(
                self.dados, self.ocupacao["id"],
                renda_praticada=Decimal("100.00"),
            )

    def test_dia_vencimento_invalido_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal(
                self.dados, self.ocupacao["id"], dia_vencimento=31
            )

    def test_dia_vencimento_valido_grava(self):
        _, mensal = contratos.atualizar_mensal(
            self.dados, self.ocupacao["id"], dia_vencimento=10
        )
        self.assertEqual(mensal["dia_vencimento"], 10)

    def test_contrato_encerrado_nao_pode_ser_alterado(self):
        contratos.encerrar_mensal(
            self.dados, self.ocupacao["id"], date(2026, 6, 1)
        )
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal(
                self.dados, self.ocupacao["id"],
                renda_praticada=Decimal("260.00"),
            )

    def test_ocupacao_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal(self.dados, "OCU-999")


class TesteEncerrarMensal(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.ocupacao, self.mensal = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"],
            self.cliente_mensal["id"], date(2026, 1, 10),
            Decimal("250.00"), Decimal("250.00"),
        )

    def test_encerra_com_sucesso(self):
        ocupacao, mensal = contratos.encerrar_mensal(
            self.dados, self.ocupacao["id"], date(2026, 6, 10),
            motivo="fim de contrato",
        )
        self.assertEqual(ocupacao["data_fim"], date(2026, 6, 10))
        self.assertFalse(ocupacao["ativo"])
        self.assertEqual(mensal["motivo_encerramento"], "fim de contrato")

    def test_data_fim_obrigatoria(self):
        with self.assertRaises(ValueError):
            contratos.encerrar_mensal(self.dados, self.ocupacao["id"], None)

    def test_data_fim_antes_do_inicio_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.encerrar_mensal(
                self.dados, self.ocupacao["id"], date(2026, 1, 1)
            )

    def test_ja_encerrado_gera_erro(self):
        contratos.encerrar_mensal(
            self.dados, self.ocupacao["id"], date(2026, 6, 10)
        )
        with self.assertRaises(ValueError):
            contratos.encerrar_mensal(
                self.dados, self.ocupacao["id"], date(2026, 8, 1)
            )

    def test_reserva_airbnb_recusada(self):
        oa, _ = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )
        with self.assertRaises(ValueError):
            contratos.encerrar_mensal(self.dados, oa["id"], date(2026, 2, 1))

    def test_duracao_abaixo_minima_fica_sinalizada_nao_bloqueia(self):
        ocupacao, mensal = contratos.encerrar_mensal(
            self.dados, self.ocupacao["id"], date(2026, 2, 1)
        )
        # início 10/01, fim 01/02 -> menos de 3 meses
        self.assertTrue(mensal["duracao_abaixo_minima"])
        self.assertFalse(ocupacao["ativo"])

    def test_duracao_normal_nao_fica_sinalizada(self):
        _, mensal = contratos.encerrar_mensal(
            self.dados, self.ocupacao["id"], date(2026, 6, 10)
        )
        self.assertFalse(mensal["duracao_abaixo_minima"])


class TesteReativar(BaseContratosTest):

    def test_reativa_contrato_mensal_repoe_data_fim_nula(self):
        ocupacao, _ = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"],
            self.cliente_mensal["id"], date(2026, 1, 10),
            Decimal("250.00"), Decimal("250.00"),
        )
        contratos.encerrar_mensal(
            self.dados, ocupacao["id"], date(2026, 6, 10)
        )
        reativada = contratos.reativar(self.dados, ocupacao["id"])
        self.assertTrue(reativada["ativo"])
        self.assertIsNone(reativada["data_fim"])

    def test_reativa_reserva_airbnb_mantem_data_fim(self):
        oa, _ = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )
        contratos.cancelar_airbnb(self.dados, oa["id"])
        reativada = contratos.reativar(self.dados, oa["id"])
        self.assertTrue(reativada["ativo"])
        self.assertEqual(reativada["data_fim"], date(2026, 1, 15))

    def test_ja_ativa_gera_erro(self):
        ocupacao, _ = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"],
            self.cliente_mensal["id"], date(2026, 1, 10),
            Decimal("250.00"), Decimal("250.00"),
        )
        with self.assertRaises(ValueError):
            contratos.reativar(self.dados, ocupacao["id"])

    def test_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.reativar(self.dados, "OCU-999")


class TesteRegistarAirbnb(BaseContratosTest):

    def test_regista_com_sucesso(self):
        ocupacao, airbnb = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )
        self.assertEqual(ocupacao["tipo"], "airbnb")
        self.assertEqual(ocupacao["lugar_id"], "")
        self.assertEqual(ocupacao["data_fim"], date(2026, 1, 15))
        self.assertEqual(airbnb["preco_praticado"], Decimal("50.00"))

    def test_unidade_mensal_recusada(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.dados, self.unidade_mensal["id"],
                self.cliente_airbnb["id"], date(2026, 1, 10),
                date(2026, 1, 15), Decimal("50.00"),
            )

    def test_estadia_abaixo_do_minimo_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.dados, self.unidade_airbnb["id"],
                self.cliente_airbnb["id"], date(2026, 1, 10),
                date(2026, 1, 11), Decimal("50.00"),
            )

    def test_estadia_acima_do_maximo_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.dados, self.unidade_airbnb["id"],
                self.cliente_airbnb["id"], date(2026, 1, 1),
                date(2026, 2, 15), Decimal("50.00"),
            )

    def test_sobreposicao_recusada(self):
        contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.dados, self.unidade_airbnb["id"],
                self.cliente_airbnb["id"], date(2026, 1, 12),
                date(2026, 1, 18), Decimal("50.00"),
            )

    def test_reservas_consecutivas_nao_sobrepoem(self):
        contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )
        # entra exatamente no dia em que a outra sai — não é conflito
        ocupacao, _ = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 15), date(2026, 1, 20), Decimal("50.00"),
        )
        self.assertEqual(ocupacao["data_inicio"], date(2026, 1, 15))

    def test_preco_calculado_soma_epoca_alta_por_noite(self):
        # 29/06 e 30/06 fora de época alta (45 cada); 01/07 e 02/07
        # dentro (90 cada) -> total 270.00
        _, airbnb = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 6, 29), date(2026, 7, 3), Decimal("270.00"),
        )
        self.assertEqual(airbnb["preco_calculado"], Decimal("270.00"))

    def test_epoca_alta_ignorada_se_indicador_desligado(self):
        unidades.atualizar(
            self.dados, self.unidade_airbnb["id"], epoca_alta_ativa=False
        )
        _, airbnb = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 7, 1), date(2026, 7, 4), Decimal("135.00"),
        )
        # sem o indicador ativo, mesmo em julho, preço fica sempre base
        self.assertEqual(airbnb["preco_calculado"], Decimal("135.00"))

    def test_preco_invalido_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.dados, self.unidade_airbnb["id"],
                self.cliente_airbnb["id"], date(2026, 1, 10),
                date(2026, 1, 15), Decimal("0.00"),
            )

    def test_check_in_tardio_sem_hora_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.dados, self.unidade_airbnb["id"],
                self.cliente_airbnb["id"], date(2026, 1, 10),
                date(2026, 1, 15), Decimal("50.00"),
                check_in_tardio=True,
            )

    def test_check_in_tardio_usa_multa_da_unidade(self):
        _, airbnb = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
            check_in_tardio=True, hora_chegada="18:00",
        )
        self.assertEqual(airbnb["multa_calculada"], Decimal("20.00"))
        self.assertEqual(airbnb["multa_praticada"], Decimal("20.00"))

    def test_check_in_tardio_multa_praticada_editavel(self):
        _, airbnb = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
            check_in_tardio=True, hora_chegada="18:00",
            multa_praticada=Decimal("0.00"),
        )
        self.assertEqual(airbnb["multa_calculada"], Decimal("20.00"))
        self.assertEqual(airbnb["multa_praticada"], Decimal("0.00"))

    def test_sem_check_in_tardio_multa_fica_zero(self):
        _, airbnb = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )
        self.assertEqual(airbnb["multa_calculada"], Decimal("0.00"))
        self.assertEqual(airbnb["multa_praticada"], Decimal("0.00"))
        self.assertEqual(airbnb["hora_chegada"], "")


class TesteAtualizarAirbnb(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.ocupacao, self.airbnb = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )

    def test_altera_preco_praticado(self):
        _, airbnb = contratos.atualizar_airbnb(
            self.dados, self.ocupacao["id"], preco_praticado=Decimal("55.00")
        )
        self.assertEqual(airbnb["preco_praticado"], Decimal("55.00"))

    def test_multa_sem_check_in_tardio_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.atualizar_airbnb(
                self.dados, self.ocupacao["id"],
                multa_praticada=Decimal("10.00"),
            )

    def test_multa_negativa_gera_erro(self):
        ocupacao, _ = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 2, 1), date(2026, 2, 5), Decimal("50.00"),
            check_in_tardio=True, hora_chegada="18:00",
        )
        with self.assertRaises(ValueError):
            contratos.atualizar_airbnb(
                self.dados, ocupacao["id"], multa_praticada=Decimal("-1.00")
            )

    def test_multa_zero_admitida_como_perdao(self):
        ocupacao, _ = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 2, 1), date(2026, 2, 5), Decimal("50.00"),
            check_in_tardio=True, hora_chegada="18:00",
        )
        _, airbnb = contratos.atualizar_airbnb(
            self.dados, ocupacao["id"], multa_praticada=Decimal("0.00")
        )
        self.assertEqual(airbnb["multa_praticada"], Decimal("0.00"))

    def test_reserva_cancelada_nao_pode_ser_alterada(self):
        contratos.cancelar_airbnb(self.dados, self.ocupacao["id"])
        with self.assertRaises(ValueError):
            contratos.atualizar_airbnb(
                self.dados, self.ocupacao["id"],
                preco_praticado=Decimal("55.00"),
            )


class TesteCancelarAirbnb(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.ocupacao, self.airbnb = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )

    def test_cancela_com_sucesso(self):
        ocupacao, airbnb = contratos.cancelar_airbnb(
            self.dados, self.ocupacao["id"], motivo="cliente desistiu"
        )
        self.assertFalse(ocupacao["ativo"])
        self.assertEqual(airbnb["motivo_cancelamento"], "cliente desistiu")
        # data_fim original não se mexe
        self.assertEqual(ocupacao["data_fim"], date(2026, 1, 15))

    def test_ja_cancelada_gera_erro(self):
        contratos.cancelar_airbnb(self.dados, self.ocupacao["id"])
        with self.assertRaises(ValueError):
            contratos.cancelar_airbnb(self.dados, self.ocupacao["id"])

    def test_contrato_mensal_recusado(self):
        oc, _ = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"],
            self.cliente_mensal["id"], date(2026, 1, 10),
            Decimal("250.00"), Decimal("250.00"),
        )
        with self.assertRaises(ValueError):
            contratos.cancelar_airbnb(self.dados, oc["id"])

    def test_liberta_as_datas_para_nova_reserva(self):
        contratos.cancelar_airbnb(self.dados, self.ocupacao["id"])
        # as mesmas datas, agora livres, têm de ser aceites
        ocupacao, _ = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )
        self.assertTrue(ocupacao["ativo"])


class TesteProcurarListar(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.mensal, _ = contratos.criar_mensal(
            self.dados, self.unidade_mensal["id"],
            self.cliente_mensal["id"], date(2026, 1, 10),
            Decimal("250.00"), Decimal("250.00"),
        )
        self.airbnb, _ = contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], self.cliente_airbnb["id"],
            date(2026, 1, 10), date(2026, 1, 15), Decimal("50.00"),
        )

    def test_procurar_encontra_por_id(self):
        encontrada = contratos.procurar(self.dados, self.mensal["id"])
        self.assertEqual(encontrada["id"], self.mensal["id"]) # type: ignore

    def test_procurar_inexistente_devolve_none(self):
        self.assertIsNone(contratos.procurar(self.dados, "OCU-999"))

    def test_listar_sem_filtro_devolve_todas_ativas(self):
        resultado = contratos.listar(self.dados)
        self.assertEqual(len(resultado), 2)

    def test_listar_filtra_por_tipo(self):
        resultado = contratos.listar(self.dados, tipo="mensal")
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["tipo"], "mensal")

    def test_listar_filtra_por_unidade(self):
        resultado = contratos.listar(
            self.dados, unidade_id=self.unidade_airbnb["id"]
        )
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], self.airbnb["id"])

    def test_listar_nao_inclui_inativas_por_omissao(self):
        contratos.cancelar_airbnb(self.dados, self.airbnb["id"])
        resultado = contratos.listar(self.dados)
        self.assertEqual(len(resultado), 1)

    def test_listar_inclui_inativas_quando_pedido(self):
        contratos.cancelar_airbnb(self.dados, self.airbnb["id"])
        resultado = contratos.listar(self.dados, incluir_inativas=True)
        self.assertEqual(len(resultado), 2)

    def test_listar_filtra_por_aviso_documento(self):
        # validade cai a meio da estadia (1 a 5 de março) — é o caso
        # que documento_expira_durante_estadia() sinaliza para uma
        # reserva com termo definido (ao contrário do mensal, que
        # compara só com o início)
        cliente_expirado = clientes.criar(
            self.dados, "Expirado", "Passaporte", "777", "airbnb",
            validade_documento=date(2026, 3, 3),
        )
        contratos.registar_airbnb(
            self.dados, self.unidade_airbnb["id"], cliente_expirado["id"],
            date(2026, 3, 1), date(2026, 3, 5), Decimal("50.00"),
        )
        resultado = contratos.listar(self.dados, aviso_documento=True)
        self.assertEqual(len(resultado), 1)
        self.assertTrue(resultado[0]["aviso_documento"])

    def test_listar_devolve_lista_nova(self):
        resultado = contratos.listar(self.dados)
        resultado.append("intruso")
        self.assertEqual(len(contratos.listar(self.dados)), 2)

    def test_procurar_nao_filtra_inativos(self):
        contratos.cancelar_airbnb(self.dados, self.airbnb["id"])
        encontrada = contratos.procurar(self.dados, self.airbnb["id"])
        self.assertIsNotNone(encontrada)
        self.assertFalse(encontrada["ativo"]) # type: ignore


class TesteSobreposicao(unittest.TestCase):
    """Testes diretos à fórmula da secção 4 — isolada, sem
    depender de 'dados' nem de nenhuma outra estrutura.
    """

    def test_sem_sobreposicao_quando_saida_coincide_com_entrada(self):
        self.assertFalse(
            contratos._sobrepoe(
                date(2026, 1, 10), date(2026, 1, 15),
                date(2026, 1, 15), date(2026, 1, 20),
            )
        )

    def test_sobreposicao_quando_intervalos_se_cruzam(self):
        self.assertTrue(
            contratos._sobrepoe(
                date(2026, 1, 10), date(2026, 1, 15),
                date(2026, 1, 12), date(2026, 1, 18),
            )
        )

    def test_sobreposicao_quando_um_intervalo_contem_o_outro(self):
        self.assertTrue(
            contratos._sobrepoe(
                date(2026, 1, 1), date(2026, 1, 31),
                date(2026, 1, 10), date(2026, 1, 15),
            )
        )

    def test_sem_sobreposicao_quando_intervalos_totalmente_separados(self):
        self.assertFalse(
            contratos._sobrepoe(
                date(2026, 1, 1), date(2026, 1, 5),
                date(2026, 2, 1), date(2026, 2, 5),
            )
        )


if __name__ == "__main__":
    unittest.main()