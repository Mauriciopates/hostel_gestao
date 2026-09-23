"""Testes de contratos.py — contratos mensais e reservas Airbnb.

MIGRAÇÃO MySQL (Fase 2): tal como propriedades.py, unidades.py,
clientes.py e responsaveis.py, `contratos.py` já não recebe nem
devolve a estrutura `dados` — fala diretamente com a base de dados
MySQL através do `repositorio.py`. Estes testes correm contra a base
de dados de teste dedicada e isolada da base de dados real do aluno
(ver `apoio_bd.py`); cada teste começa com todas as tabelas vazias
(TRUNCATE) e com os contadores de identificadores reiniciados, tal
como antes cada teste começava com um dicionário `dados` novo.

`BaseContratosTest` (que estende `BaseMySQLTest`) fornece uma unidade
mensal (com um quarto e um lugar de capacidade 2), uma unidade
Airbnb, e um cliente para cada regime — reutilizada por todas as
subclasses abaixo, através de `criar(...)` normal em cada módulo, tal
como qualquer outro código chamaria.

Os clientes de fixture (self.cliente_mensal/self.cliente_airbnb no
setUp, e os avulsos em vários testes) passam sempre TODOS os campos
que o seu regime exige (validacoes.validar_cliente, depois das
decisões de 26/08/2026 e 16/09/2026):

- Mensal: nome, tipo_documento, numero_documento, nacionalidade,
  data_nascimento, validade_documento, nif, morada, estado_civil
  e telefone.
- Airbnb: nome, tipo_documento, numero_documento, nacionalidade,
  data_nascimento, validade_documento, pais_emissor_documento e
  pais_residencia.

Um cliente sem estes campos rebentaria dentro de `clientes.criar`,
antes do teste propriamente dito começar — os testes que o confirmam
já vivem em `teste_clientes.py`, não aqui.

NOTA sobre identidade: `procurar()`/`listar()` fazem sempre um SELECT
novo à base de dados — já não devolvem o MESMO objeto Python que
`criar_mensal`/`registar_airbnb` devolveram. Por isso comparamos com
`assertEqual` (valores iguais), nunca com `assertIs`, e já não é
possível verificar "ficou gravado" com `assertIn(x, dados["algo"])`
— confirma-se antes com `contratos.procurar(...)`/`detalhes_mensal(...)`
a devolver o mesmo valor.
"""

import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest

import clientes
import config
import contratos
import propriedades
import repositorio
import responsaveis
import unidades


class BaseContratosTest(BaseMySQLTest):
    """Fornece uma estrutura de dados com uma unidade mensal (com
    um quarto e um lugar de capacidade 2), uma unidade Airbnb, e
    um cliente para cada regime — reutilizada por todas as
    subclasses abaixo.
    """

    def setUp(self):
        super().setUp()

        self.propriedade = propriedades.criar("Foz Velha")

        self.unidade_mensal = unidades.criar(
            self.propriedade["id"],
            "Unidade Mensal Teste",
            "mensal",
            Decimal("250.00"),
            Decimal("250.00"),
            Decimal("20.00"),
        )
        self.quarto = unidades.criar_quarto(
            self.unidade_mensal["id"], "Quarto 1"
        )
        self.lugar = unidades.criar_lugar(
            self.quarto["id"], "Cama 1", "casal", capacidade=2
        )

        self.unidade_airbnb = unidades.criar(
            self.propriedade["id"],
            "Unidade Airbnb Teste",
            "airbnb",
            Decimal("45.00"),
            Decimal("90.00"),
            Decimal("20.00"),
            epoca_alta_ativa=True,
        )

        self.cliente_mensal = clientes.criar(
            "João Silva",
            "Passaporte",
            "11111111",
            "mensal",
            nif="123456789",
            morada="Rua do Porto, 12",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912345678",
            data_nascimento=date(1990, 5, 20),
            validade_documento=date(2030, 1, 1),
        )
        self.cliente_airbnb = clientes.criar(
            "Ana Costa",
            "Passaporte",
            "X9999999",
            "airbnb",
            nacionalidade="Brasileira",
            pais_emissor_documento="Brasil",
            pais_residencia="Brasil",
            data_nascimento=date(1985, 3, 12),
            validade_documento=date(2030, 1, 1),
        )


class TesteCriarMensal(BaseContratosTest):

    def test_cria_contrato_com_sucesso(self):
        ocupacao, mensal = contratos.criar_mensal(
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
        self.assertEqual(ocupacao, contratos.procurar(ocupacao["id"]))
        persistido = contratos.detalhes_mensal(ocupacao["id"])
        self.assertEqual(
            mensal, {chave: persistido[chave] for chave in mensal}
        )

    def test_id_gerado_com_prefixo_cnt(self):
        ocupacao, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertTrue(ocupacao["id"].startswith("CNT-"))

    def test_unidade_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                "UNI-999",
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_unidade_airbnb_recusada(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_airbnb["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_unidade_inativa_recusada(self):
        unidades.desativar(self.unidade_mensal["id"])

        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_cliente_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                "CLI-999",
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_cliente_inativo_recusado(self):
        clientes.desativar(self.cliente_mensal["id"])
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_bloqueia_ao_atingir_capacidade(self):
        # capacidade da unidade = 2 (um único lugar, capacidade 2)
        cliente_2 = clientes.criar(
            "Maria",
            "Passaporte",
            "222",
            "mensal",
            nif="222222220",
            morada="Rua X, 1",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912222222",
            data_nascimento=date(1992, 4, 10),
            validade_documento=date(2030, 1, 1),
        )
        cliente_3 = clientes.criar(
            "Pedro",
            "Passaporte",
            "333",
            "mensal",
            nif="333333330",
            morada="Rua Y, 2",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912333333",
            data_nascimento=date(1988, 7, 1),
            validade_documento=date(2030, 1, 1),
        )
        contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        contratos.criar_mensal(
            self.unidade_mensal["id"],
            cliente_2["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                cliente_3["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_lugar_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
                lugar_id="LUG-999",
            )

    def test_lugar_de_outra_unidade_recusado(self):
        outra_unidade = unidades.criar(
            self.propriedade["id"],
            "Outra Unidade",
            "mensal",
            Decimal("250.00"),
            Decimal("250.00"),
            Decimal("20.00"),
        )
        outro_quarto = unidades.criar_quarto(outra_unidade["id"], "Quarto X")
        outro_lugar = unidades.criar_lugar(
            outro_quarto["id"], "Cama X", "solteiro"
        )
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
                lugar_id=outro_lugar["id"],
            )

    def test_lugar_de_casal_admite_dois_contratos(self):
        cliente_2 = clientes.criar(
            "Maria",
            "Passaporte",
            "222",
            "mensal",
            nif="222222220",
            morada="Rua X, 1",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912222222",
            data_nascimento=date(1992, 4, 10),
            validade_documento=date(2030, 1, 1),
        )
        contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
            lugar_id=self.lugar["id"],
        )
        ocupacao, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            cliente_2["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
            lugar_id=self.lugar["id"],
        )
        self.assertEqual(ocupacao["lugar_id"], self.lugar["id"])

    def test_lugar_esgotado_recusa_terceiro_contrato(self):
        cliente_2 = clientes.criar(
            "Maria",
            "Passaporte",
            "222",
            "mensal",
            nif="222222220",
            morada="Rua X, 1",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912222222",
            data_nascimento=date(1992, 4, 10),
            validade_documento=date(2030, 1, 1),
        )
        outro_quarto = unidades.criar_quarto(
            self.unidade_mensal["id"], "Quarto 2"
        )
        unidades.criar_lugar(outro_quarto["id"], "Cama 2", "solteiro")

        cliente_3 = clientes.criar(
            "Pedro",
            "Passaporte",
            "333",
            "mensal",
            nif="333333330",
            morada="Rua Y, 2",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912333333",
            data_nascimento=date(1988, 7, 1),
            validade_documento=date(2030, 1, 1),
        )
        contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
            lugar_id=self.lugar["id"],
        )
        contratos.criar_mensal(
            self.unidade_mensal["id"],
            cliente_2["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
            lugar_id=self.lugar["id"],
        )
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                cliente_3["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
                lugar_id=self.lugar["id"],
            )

    def test_renda_invalida_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("0.00"),
                Decimal("0.00"),
            )

    def test_caucao_acima_do_teto_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("600.00"),
            )

    def test_documento_ja_caducado_marca_aviso(self):
        cliente = clientes.criar(
            "Expirado",
            "Passaporte",
            "999",
            "mensal",
            nif="444444440",
            morada="Rua Z, 3",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912444444",
            data_nascimento=date(1991, 2, 2),
            validade_documento=date(2025, 12, 31),
        )
        ocupacao, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            cliente["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertTrue(ocupacao["aviso_documento"])

    def test_documento_valido_nao_marca_aviso(self):
        cliente = clientes.criar(
            "Válido",
            "Passaporte",
            "888",
            "mensal",
            nif="555555550",
            morada="Rua W, 4",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912555555",
            data_nascimento=date(1993, 6, 15),
            validade_documento=date(2030, 1, 1),
        )
        ocupacao, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            cliente["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertFalse(ocupacao["aviso_documento"])

    def test_dia_vencimento_omisso_usa_valor_por_omissao(self):
        _, mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertEqual(mensal["dia_vencimento"], config.DIA_VENCIMENTO)

    def test_dia_vencimento_personalizado_e_aceite(self):
        _, mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
            dia_vencimento=15,
        )
        self.assertEqual(mensal["dia_vencimento"], 15)

    def test_dia_vencimento_fora_do_intervalo_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
                dia_vencimento=31,
            )

    def test_dia_vencimento_nao_inteiro_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
                dia_vencimento="dez",
            )

    def test_caucao_igual_a_renda_nao_exige_confirmacao(self):
        _, mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertFalse(mensal["caucao_exige_confirmacao"])

    def test_caucao_acima_da_renda_exige_confirmacao(self):
        _, mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("400.00"),
        )
        self.assertTrue(mensal["caucao_exige_confirmacao"])

    def test_renda_abaixo_da_calculada_sem_responsavel_e_recusada(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 1, 10),
                Decimal("200.00"),
                Decimal("200.00"),
            )

    def test_renda_abaixo_da_calculada_com_responsavel_valido_grava(self):
        responsavel = responsaveis.criar("Gestor de Turno")
        _, mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("200.00"),
            Decimal("200.00"),
            responsavel_desconto_renda_id=responsavel["id"],
        )
        self.assertEqual(mensal["renda_praticada"], Decimal("200.00"))
        self.assertEqual(
            mensal["responsavel_desconto_renda_id"], responsavel["id"]
        )

    def test_renda_igual_a_calculada_nao_exige_responsavel(self):
        _, mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertEqual(mensal["responsavel_desconto_renda_id"], "")

    def test_renda_acima_da_calculada_ignora_responsavel_passado(self):
        responsavel = responsaveis.criar("Gestor de Turno")
        _, mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("300.00"),
            Decimal("300.00"),
            responsavel_desconto_renda_id=responsavel["id"],
        )
        self.assertEqual(mensal["responsavel_desconto_renda_id"], "")

    def test_recusa_cliente_sem_nif_para_contrato_mensal(self):
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_airbnb["id"],
                date(2026, 1, 10),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_recusa_segundo_contrato_mensal_ativo_mesmo_cliente(self):
        contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                self.cliente_mensal["id"],
                date(2026, 2, 1),
                Decimal("250.00"),
                Decimal("250.00"),
            )

    def test_permite_novo_contrato_apos_encerrar_o_anterior(self):
        ocupacao, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        contratos.encerrar_mensal(ocupacao["id"], date(2026, 3, 1))
        novo_ocupacao, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 3, 5),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.assertTrue(novo_ocupacao["ativo"])

    def test_recusa_segundo_contrato_mensal_por_nif_entre_clientes_diferentes(
        self,
    ):
        cliente_b = clientes.criar(
            "Maria Duplicada",
            "Passaporte",
            "22222222",
            "mensal",
            nif="222222220",
            morada="Rua Nova, 5",
            nacionalidade="Portuguesa",
            estado_civil="Solteiro(a)",
            telefone="912222222",
            data_nascimento=date(1992, 4, 15),
            validade_documento=date(2030, 1, 1),
        )
        repositorio.atualizar_cliente(
            cliente_b["id"], {"nif": self.cliente_mensal["nif"]}
        )

        contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        with self.assertRaises(ValueError):
            contratos.criar_mensal(
                self.unidade_mensal["id"],
                cliente_b["id"],
                date(2026, 2, 1),
                Decimal("250.00"),
                Decimal("250.00"),
            )


class TesteAtualizarMensal(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.ocupacao, self.mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )

    def test_altera_renda_praticada(self):
        _, mensal = contratos.atualizar_mensal(
            self.ocupacao["id"], renda_praticada=Decimal("260.00")
        )
        self.assertEqual(mensal["renda_praticada"], Decimal("260.00"))
        self.assertEqual(mensal["renda_calculada"], Decimal("250.00"))

    def test_revalida_caucao_quando_so_a_renda_muda(self):
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal(
                self.ocupacao["id"],
                renda_praticada=Decimal("100.00"),
            )

    def test_dia_vencimento_invalido_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal(self.ocupacao["id"], dia_vencimento=31)

    def test_dia_vencimento_valido_grava(self):
        _, mensal = contratos.atualizar_mensal(
            self.ocupacao["id"], dia_vencimento=10
        )
        self.assertEqual(mensal["dia_vencimento"], 10)

    def test_caucao_exige_confirmacao_atualizado_ao_mudar_caucao(self):
        _, mensal = contratos.atualizar_mensal(
            self.ocupacao["id"], caucao=Decimal("400.00")
        )
        self.assertTrue(mensal["caucao_exige_confirmacao"])

    def test_contrato_encerrado_nao_pode_ser_alterado(self):
        contratos.encerrar_mensal(self.ocupacao["id"], date(2026, 6, 1))
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal(
                self.ocupacao["id"],
                renda_praticada=Decimal("260.00"),
            )

    def test_ocupacao_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal("CNT-999")

    def test_renda_abaixo_da_calculada_sem_responsavel_e_recusada(self):
        with self.assertRaises(ValueError):
            contratos.atualizar_mensal(
                self.ocupacao["id"],
                renda_praticada=Decimal("200.00"),
            )

    def test_renda_abaixo_da_calculada_com_responsavel_valido_atualiza(self):
        responsavel = responsaveis.criar("Gestor de Turno")
        _, mensal = contratos.atualizar_mensal(
            self.ocupacao["id"],
            renda_praticada=Decimal("200.00"),
            responsavel_desconto_renda_id=responsavel["id"],
        )
        self.assertEqual(mensal["renda_praticada"], Decimal("200.00"))
        self.assertEqual(
            mensal["responsavel_desconto_renda_id"], responsavel["id"]
        )

    def test_renda_de_volta_ao_valor_calculado_limpa_responsavel(self):
        responsavel = responsaveis.criar("Gestor de Turno")
        contratos.atualizar_mensal(
            self.ocupacao["id"],
            renda_praticada=Decimal("200.00"),
            responsavel_desconto_renda_id=responsavel["id"],
        )
        _, mensal = contratos.atualizar_mensal(
            self.ocupacao["id"],
            renda_praticada=Decimal("250.00"),
        )
        self.assertEqual(mensal["responsavel_desconto_renda_id"], "")

    def test_sem_alterar_renda_nao_mexe_no_responsavel(self):
        responsavel = responsaveis.criar("Gestor de Turno")
        contratos.atualizar_mensal(
            self.ocupacao["id"],
            renda_praticada=Decimal("200.00"),
            responsavel_desconto_renda_id=responsavel["id"],
        )
        _, mensal = contratos.atualizar_mensal(
            self.ocupacao["id"], dia_vencimento=10
        )
        self.assertEqual(
            mensal["responsavel_desconto_renda_id"], responsavel["id"]
        )


class TesteEncerrarMensal(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.ocupacao, self.mensal = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )

    def test_encerra_com_sucesso(self):
        ocupacao, mensal = contratos.encerrar_mensal(
            self.ocupacao["id"],
            date(2026, 6, 10),
            motivo="fim de contrato",
        )
        self.assertEqual(ocupacao["data_fim"], date(2026, 6, 10))
        self.assertFalse(ocupacao["ativo"])
        self.assertEqual(mensal["motivo_encerramento"], "fim de contrato")

    def test_data_fim_obrigatoria(self):
        with self.assertRaises(ValueError):
            contratos.encerrar_mensal(self.ocupacao["id"], None)

    def test_data_fim_antes_do_inicio_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.encerrar_mensal(self.ocupacao["id"], date(2026, 1, 1))

    def test_ja_encerrado_gera_erro(self):
        contratos.encerrar_mensal(self.ocupacao["id"], date(2026, 6, 10))
        with self.assertRaises(ValueError):
            contratos.encerrar_mensal(self.ocupacao["id"], date(2026, 8, 1))

    def test_reserva_airbnb_recusada(self):
        oa, _ = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )
        with self.assertRaises(ValueError):
            contratos.encerrar_mensal(oa["id"], date(2026, 2, 1))

    def test_duracao_abaixo_minima_fica_sinalizada_nao_bloqueia(self):
        ocupacao, mensal = contratos.encerrar_mensal(
            self.ocupacao["id"], date(2026, 2, 1)
        )
        self.assertTrue(mensal["duracao_abaixo_minima"])
        self.assertFalse(ocupacao["ativo"])

    def test_duracao_normal_nao_fica_sinalizada(self):
        _, mensal = contratos.encerrar_mensal(
            self.ocupacao["id"], date(2026, 6, 10)
        )
        self.assertFalse(mensal["duracao_abaixo_minima"])


class TesteReativar(BaseContratosTest):

    def test_reativa_contrato_mensal_repoe_data_fim_nula(self):
        ocupacao, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        contratos.encerrar_mensal(ocupacao["id"], date(2026, 6, 10))
        reativada = contratos.reativar(ocupacao["id"])
        self.assertTrue(reativada["ativo"])
        self.assertIsNone(reativada["data_fim"])

    def test_reativa_reserva_airbnb_mantem_data_fim(self):
        oa, _ = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )
        contratos.cancelar_airbnb(oa["id"])
        reativada = contratos.reativar(oa["id"])
        self.assertTrue(reativada["ativo"])
        self.assertEqual(reativada["data_fim"], date(2026, 1, 15))

    def test_ja_ativa_gera_erro(self):
        ocupacao, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        with self.assertRaises(ValueError):
            contratos.reativar(ocupacao["id"])

    def test_inexistente_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.reativar("CNT-999")


class TesteRegistarAirbnb(BaseContratosTest):

    def test_regista_com_sucesso(self):
        ocupacao, airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )
        self.assertEqual(ocupacao["tipo"], "airbnb")
        self.assertEqual(ocupacao["lugar_id"], "")
        self.assertEqual(ocupacao["data_fim"], date(2026, 1, 15))
        self.assertEqual(airbnb["preco_praticado"], Decimal("225.00"))

    def test_unidade_mensal_recusada(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.unidade_mensal["id"],
                self.cliente_airbnb["id"],
                date(2026, 1, 10),
                date(2026, 1, 15),
                Decimal("50.00"),
            )

    def test_unidade_inativa_recusada(self):
        unidades.desativar(self.unidade_airbnb["id"])

        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.unidade_airbnb["id"],
                self.cliente_airbnb["id"],
                date(2026, 1, 10),
                date(2026, 1, 15),
                Decimal("225.00"),
            )

    def test_estadia_de_uma_noite_aceite(self):
        ocupacao, airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 11),
            Decimal("50.00"),
        )
        self.assertEqual(ocupacao["data_fim"], date(2026, 1, 11))
        self.assertEqual(airbnb["preco_praticado"], Decimal("50.00"))

    def test_estadia_acima_do_maximo_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.unidade_airbnb["id"],
                self.cliente_airbnb["id"],
                date(2026, 1, 1),
                date(2026, 2, 15),
                Decimal("50.00"),
            )

    def test_sobreposicao_recusada(self):
        contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.unidade_airbnb["id"],
                self.cliente_airbnb["id"],
                date(2026, 1, 12),
                date(2026, 1, 18),
                Decimal("50.00"),
            )

    def test_reservas_consecutivas_nao_sobrepoem(self):
        contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )
        ocupacao, _ = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 15),
            date(2026, 1, 20),
            Decimal("225.00"),
        )
        self.assertEqual(ocupacao["data_inicio"], date(2026, 1, 15))

    def test_preco_calculado_soma_epoca_alta_por_noite(self):
        _, airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 6, 29),
            date(2026, 7, 3),
            Decimal("270.00"),
        )
        self.assertEqual(airbnb["preco_calculado"], Decimal("270.00"))

    def test_epoca_alta_ignorada_se_indicador_desligado(self):
        unidades.atualizar(self.unidade_airbnb["id"], epoca_alta_ativa=False)
        _, airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 7, 1),
            date(2026, 7, 4),
            Decimal("135.00"),
        )
        self.assertEqual(airbnb["preco_calculado"], Decimal("135.00"))

    def test_preco_invalido_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.unidade_airbnb["id"],
                self.cliente_airbnb["id"],
                date(2026, 1, 10),
                date(2026, 1, 15),
                Decimal("0.00"),
            )

    def test_check_in_tardio_sem_hora_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.registar_airbnb(
                self.unidade_airbnb["id"],
                self.cliente_airbnb["id"],
                date(2026, 1, 10),
                date(2026, 1, 15),
                Decimal("225.00"),
                check_in_tardio=True,
            )

    def test_check_in_tardio_usa_multa_da_unidade(self):
        _, airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
            check_in_tardio=True,
            hora_chegada="18:00",
        )
        self.assertEqual(airbnb["multa_calculada"], Decimal("20.00"))
        self.assertEqual(airbnb["multa_praticada"], Decimal("20.00"))

    def test_check_in_tardio_multa_praticada_editavel(self):
        responsavel = responsaveis.criar("Gestor de Turno")
        _, airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
            check_in_tardio=True,
            hora_chegada="18:00",
            multa_praticada=Decimal("0.00"),
            responsavel_desconto_multa_id=responsavel["id"],
        )
        self.assertEqual(airbnb["multa_calculada"], Decimal("20.00"))
        self.assertEqual(airbnb["multa_praticada"], Decimal("0.00"))
        self.assertEqual(
            airbnb["responsavel_desconto_multa_id"], responsavel["id"]
        )

    def test_sem_check_in_tardio_multa_fica_zero(self):
        _, airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )
        self.assertEqual(airbnb["multa_calculada"], Decimal("0.00"))
        self.assertEqual(airbnb["multa_praticada"], Decimal("0.00"))
        self.assertEqual(airbnb["hora_chegada"], "")

    def test_id_gerado_com_prefixo_rsv(self):
        ocupacao, _ = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 2, 10),
            date(2026, 2, 15),
            Decimal("300.00"),
        )
        self.assertTrue(ocupacao["id"].startswith("RSV-"))


class TesteAtualizarAirbnb(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.ocupacao, self.airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )

    def test_altera_preco_praticado(self):
        _, airbnb = contratos.atualizar_airbnb(
            self.ocupacao["id"], preco_praticado=Decimal("230.00")
        )
        self.assertEqual(airbnb["preco_praticado"], Decimal("230.00"))

    def test_multa_sem_check_in_tardio_gera_erro(self):
        with self.assertRaises(ValueError):
            contratos.atualizar_airbnb(
                self.ocupacao["id"],
                multa_praticada=Decimal("10.00"),
            )

    def test_multa_negativa_gera_erro(self):
        ocupacao, _ = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 2, 1),
            date(2026, 2, 5),
            Decimal("180.00"),
            check_in_tardio=True,
            hora_chegada="18:00",
        )
        with self.assertRaises(ValueError):
            contratos.atualizar_airbnb(
                ocupacao["id"], multa_praticada=Decimal("-1.00")
            )

    def test_multa_zero_admitida_como_perdao(self):
        ocupacao, _ = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 2, 1),
            date(2026, 2, 5),
            Decimal("180.00"),
            check_in_tardio=True,
            hora_chegada="18:00",
        )
        responsavel = responsaveis.criar("Gestor de Turno")
        _, airbnb = contratos.atualizar_airbnb(
            ocupacao["id"],
            multa_praticada=Decimal("0.00"),
            responsavel_desconto_multa_id=responsavel["id"],
        )
        self.assertEqual(airbnb["multa_praticada"], Decimal("0.00"))
        self.assertEqual(
            airbnb["responsavel_desconto_multa_id"], responsavel["id"]
        )

    def test_reserva_cancelada_nao_pode_ser_alterada(self):
        contratos.cancelar_airbnb(self.ocupacao["id"])
        with self.assertRaises(ValueError):
            contratos.atualizar_airbnb(
                self.ocupacao["id"],
                preco_praticado=Decimal("55.00"),
            )


class TesteCancelarAirbnb(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.ocupacao, self.airbnb = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )

    def test_cancela_com_sucesso(self):
        ocupacao, airbnb = contratos.cancelar_airbnb(
            self.ocupacao["id"], motivo="cliente desistiu"
        )
        self.assertFalse(ocupacao["ativo"])
        self.assertEqual(airbnb["motivo_cancelamento"], "cliente desistiu")
        self.assertEqual(ocupacao["data_fim"], date(2026, 1, 15))

    def test_ja_cancelada_gera_erro(self):
        contratos.cancelar_airbnb(self.ocupacao["id"])
        with self.assertRaises(ValueError):
            contratos.cancelar_airbnb(self.ocupacao["id"])

    def test_contrato_mensal_recusado(self):
        oc, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        with self.assertRaises(ValueError):
            contratos.cancelar_airbnb(oc["id"])

    def test_liberta_as_datas_para_nova_reserva(self):
        contratos.cancelar_airbnb(self.ocupacao["id"])
        ocupacao, _ = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )
        self.assertTrue(ocupacao["ativo"])


class TesteProcurarListar(BaseContratosTest):

    def setUp(self):
        super().setUp()
        self.mensal, _ = contratos.criar_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )
        self.airbnb, _ = contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 15),
            Decimal("225.00"),
        )

    def test_procurar_encontra_por_id(self):
        encontrada = contratos.procurar(self.mensal["id"])
        self.assertEqual(encontrada["id"], self.mensal["id"])  # type: ignore

    def test_procurar_inexistente_devolve_none(self):
        self.assertIsNone(contratos.procurar("CNT-999"))

    def test_listar_sem_filtro_devolve_todas_ativas(self):
        resultado = contratos.listar()
        self.assertEqual(len(resultado), 2)

    def test_listar_filtra_por_tipo(self):
        resultado = contratos.listar(tipo="mensal")
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["tipo"], "mensal")

    def test_listar_filtra_por_unidade(self):
        resultado = contratos.listar(unidade_id=self.unidade_airbnb["id"])
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], self.airbnb["id"])

    def test_listar_nao_inclui_inativas_por_omissao(self):
        contratos.cancelar_airbnb(self.airbnb["id"])
        resultado = contratos.listar()
        self.assertEqual(len(resultado), 1)

    def test_listar_inclui_inativas_quando_pedido(self):
        contratos.cancelar_airbnb(self.airbnb["id"])
        resultado = contratos.listar(incluir_inativas=True)
        self.assertEqual(len(resultado), 2)

    def test_listar_filtra_por_aviso_documento(self):
        cliente_expirado = clientes.criar(
            "Expirado",
            "Passaporte",
            "777",
            "airbnb",
            nacionalidade="Britânica",
            pais_emissor_documento="Reino Unido",
            pais_residencia="Reino Unido",
            data_nascimento=date(1980, 11, 5),
            validade_documento=date(2026, 3, 3),
        )
        contratos.registar_airbnb(
            self.unidade_airbnb["id"],
            cliente_expirado["id"],
            date(2026, 3, 1),
            date(2026, 3, 5),
            Decimal("180.00"),
        )
        resultado = contratos.listar(aviso_documento=True)
        self.assertEqual(len(resultado), 1)
        self.assertTrue(resultado[0]["aviso_documento"])

    def test_listar_devolve_lista_nova(self):
        resultado = contratos.listar()
        resultado.append("intruso")
        self.assertEqual(len(contratos.listar()), 2)

    def test_procurar_nao_filtra_inativos(self):
        contratos.cancelar_airbnb(self.airbnb["id"])
        encontrada = contratos.procurar(self.airbnb["id"])
        self.assertIsNotNone(encontrada)
        self.assertFalse(encontrada["ativo"])  # type: ignore


class TesteSobreposicao(unittest.TestCase):

    def test_sem_sobreposicao_quando_saida_coincide_com_entrada(self):
        self.assertFalse(
            contratos._sobrepoe(
                date(2026, 1, 10),
                date(2026, 1, 15),
                date(2026, 1, 15),
                date(2026, 1, 20),
            )
        )

    def test_sobreposicao_quando_intervalos_se_cruzam(self):
        self.assertTrue(
            contratos._sobrepoe(
                date(2026, 1, 10),
                date(2026, 1, 15),
                date(2026, 1, 12),
                date(2026, 1, 18),
            )
        )

    def test_sobreposicao_quando_um_intervalo_contem_o_outro(self):
        self.assertTrue(
            contratos._sobrepoe(
                date(2026, 1, 1),
                date(2026, 1, 31),
                date(2026, 1, 10),
                date(2026, 1, 15),
            )
        )

    def test_sem_sobreposicao_quando_intervalos_totalmente_separados(self):
        self.assertFalse(
            contratos._sobrepoe(
                date(2026, 1, 1),
                date(2026, 1, 5),
                date(2026, 2, 1),
                date(2026, 2, 5),
            )
        )


class TesteAvisosEncerramento(unittest.TestCase):

    def test_duracao_acima_do_minimo_nao_levanta_aviso(self):
        inicio = date.today() - timedelta(days=365)
        fim = date.today() + timedelta(days=60)

        avisos = contratos.avisos_encerramento({"data_inicio": inicio}, fim)

        self.assertFalse(avisos["duracao_abaixo_minima"])

    def test_duracao_abaixo_do_minimo_levanta_aviso(self):
        inicio = date(2026, 3, 1)
        fim = date(2026, 4, 30)

        avisos = contratos.avisos_encerramento({"data_inicio": inicio}, fim)

        self.assertTrue(avisos["duracao_abaixo_minima"])

    def test_duracao_conta_meses_de_calendario_nao_dias(self):
        avisos = contratos.avisos_encerramento(
            {"data_inicio": date(2026, 3, 31)}, date(2026, 4, 1)
        )

        self.assertTrue(avisos["duracao_abaixo_minima"])

    def test_encerrar_hoje_e_aviso_previo_insuficiente(self):
        hoje = date.today()

        avisos = contratos.avisos_encerramento(
            {"data_inicio": hoje - timedelta(days=365)}, hoje
        )

        self.assertTrue(avisos["aviso_previo_insuficiente"])

    def test_aviso_previo_cumprido_nao_levanta_aviso(self):
        fim = date.today() + timedelta(days=config.AVISO_PREVIO_DIAS + 1)

        avisos = contratos.avisos_encerramento(
            {"data_inicio": date.today() - timedelta(days=365)}, fim
        )

        self.assertFalse(avisos["aviso_previo_insuficiente"])

    def test_limite_exato_do_aviso_previo_e_suficiente(self):
        fim = date.today() + timedelta(days=config.AVISO_PREVIO_DIAS)

        avisos = contratos.avisos_encerramento(
            {"data_inicio": date.today() - timedelta(days=365)}, fim
        )

        self.assertFalse(avisos["aviso_previo_insuficiente"])

    def test_devolve_so_as_duas_chaves(self):
        avisos = contratos.avisos_encerramento(
            {"data_inicio": date(2026, 1, 1)}, date(2026, 12, 31)
        )

        self.assertEqual(
            set(avisos),
            {"duracao_abaixo_minima", "aviso_previo_insuficiente"},
        )


if __name__ == "__main__":
    unittest.main()
