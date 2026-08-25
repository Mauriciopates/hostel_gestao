"""Testes de unidades.py — unidades, quartos e lugares.

Cada classe testa uma função (ou par inverso, como
desativar/reativar). Constrói o dicionário de dados em memória, sem
pasta temporária nem setUp: repositorio.proximo_id() é a única
exceção que toca em ficheiro (decisão 1), tal como já acontece nos
testes de propriedades.py.
"""

import sys
import unittest
from datetime import date
from decimal import Decimal

sys.path.insert(0, "src")

import propriedades
import unidades


def dados_base():
    """Devolve uma estrutura de dados nova, com uma propriedade."""
    dados = {
        "propriedades": [],
        "unidades": [],
        "quartos": [],
        "lugares": [],
        "ocupacoes": [],
    }
    propriedades.criar(dados, "Foz Velha", "Rua de Exemplo, 1")
    return dados


def criar_ocupacao(dados, unidade_id, tipo, data_inicio, data_fim=None, ativo=True):
    """Acrescenta uma ocupação em dados['ocupacoes'], só com os
    campos que unidades.estado() lê.
    """
    ocupacao = {
        "id": f"OCU-{len(dados['ocupacoes']) + 1:03d}",
        "unidade_id": unidade_id,
        "cliente_id": "CLI-001",
        "tipo": tipo,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "lugar_id": "",
        "aviso_documento": False,
        "ativo": ativo,
    }
    dados["ocupacoes"].append(ocupacao)
    return ocupacao


def dar_lugares(dados, unidade_id, capacidades):
    """Cria um quarto com um lugar por capacidade indicada, devolve
    a soma — a capacidade total esperada da unidade.
    """
    quarto = unidades.criar_quarto(dados, unidade_id, "Quarto de teste")
    for capacidade in capacidades:
        unidades.criar_lugar(
            dados, quarto["id"], f"Lugar {capacidade}", capacidade=capacidade
        )
    return sum(capacidades)


def criar_unidade_mensal(dados, propriedade_id=None):
    """Cria uma unidade mensal de teste e devolve o registo."""
    if propriedade_id is None:
        propriedade_id = dados["propriedades"][0]["id"]

    return unidades.criar(
        dados,
        propriedade_id,
        "mensal",
        Decimal("250.00"),
        Decimal("250.00"),
        Decimal("20.00"),
    )


def criar_unidade_airbnb(dados, propriedade_id=None):
    """Cria uma unidade Airbnb de teste e devolve o registo."""
    if propriedade_id is None:
        propriedade_id = dados["propriedades"][0]["id"]

    return unidades.criar(
        dados,
        propriedade_id,
        "airbnb",
        Decimal("45.00"),
        Decimal("90.00"),
        Decimal("20.00"),
    )


class TesteCriar(unittest.TestCase):

    def test_cria_unidade_mensal_valida(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        self.assertEqual(unidade["tipo"], "mensal")
        self.assertEqual(unidade["preco_base"], Decimal("250.00"))
        self.assertFalse(unidade["em_manutencao"])
        self.assertTrue(unidade["ativo"])
        self.assertIn(unidade, dados["unidades"])

    def test_cria_unidade_airbnb_valida(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        self.assertEqual(unidade["tipo"], "airbnb")

    def test_recusa_propriedade_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.criar(
                dados, "PRO-999", "mensal",
                Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
            )

    def test_recusa_tipo_desconhecido(self):
        dados = dados_base()
        propriedade_id = dados["propriedades"][0]["id"]
        with self.assertRaises(ValueError):
            unidades.criar(
                dados, propriedade_id, "semanal",
                Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
            )

    def test_recusa_preco_em_falta(self):
        dados = dados_base()
        propriedade_id = dados["propriedades"][0]["id"]
        with self.assertRaises(ValueError):
            unidades.criar(
                dados, propriedade_id, "mensal",
                None, Decimal("250.00"), Decimal("20.00"),
            )

    def test_recusa_preco_nao_decimal(self):
        dados = dados_base()
        propriedade_id = dados["propriedades"][0]["id"]
        with self.assertRaises(ValueError):
            unidades.criar(
                dados, propriedade_id, "mensal",
                250.00, Decimal("250.00"), Decimal("20.00"),
            )

    def test_recusa_preco_negativo(self):
        dados = dados_base()
        propriedade_id = dados["propriedades"][0]["id"]
        with self.assertRaises(ValueError):
            unidades.criar(
                dados, propriedade_id, "mensal",
                Decimal("-1"), Decimal("250.00"), Decimal("20.00"),
            )

    def test_epoca_alta_ativa_por_omissao_falsa(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        self.assertFalse(unidade["epoca_alta_ativa"])

    def test_epoca_alta_ativa_aceita_true(self):
        dados = dados_base()
        propriedade_id = dados["propriedades"][0]["id"]
        unidade = unidades.criar(
            dados, propriedade_id, "airbnb",
            Decimal("45.00"), Decimal("90.00"), Decimal("20.00"),
            epoca_alta_ativa=True,
        )
        self.assertTrue(unidade["epoca_alta_ativa"])


class TesteProcurar(unittest.TestCase):

    def test_encontra_unidade_existente(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        encontrada = unidades.procurar(dados, unidade["id"])
        self.assertIs(encontrada, unidade)

    def test_devolve_none_para_id_inexistente(self):
        dados = dados_base()
        self.assertIsNone(unidades.procurar(dados, "UNI-999"))

    def test_encontra_unidade_inativa(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        unidades.desativar(dados, unidade["id"])
        self.assertIsNotNone(unidades.procurar(dados, unidade["id"]))


class TesteListar(unittest.TestCase):

    def test_lista_vazia_sem_unidades(self):
        dados = dados_base()
        self.assertEqual(unidades.listar(dados), [])

    def test_lista_so_ativas_por_omissao(self):
        dados = dados_base()
        ativa = criar_unidade_mensal(dados)
        inativa = criar_unidade_airbnb(dados)
        unidades.desativar(dados, inativa["id"])
        resultado = unidades.listar(dados)
        self.assertEqual(resultado, [ativa])

    def test_lista_incluir_inativas(self):
        dados = dados_base()
        criar_unidade_mensal(dados)
        inativa = criar_unidade_airbnb(dados)
        unidades.desativar(dados, inativa["id"])
        resultado = unidades.listar(dados, incluir_inativas=True)
        self.assertEqual(len(resultado), 2)

    def test_filtra_por_propriedade(self):
        dados = dados_base()
        outra_propriedade = propriedades.criar(dados, "Aldoar")
        criar_unidade_mensal(dados)
        da_segunda = criar_unidade_mensal(
            dados, propriedade_id=outra_propriedade["id"]
        )
        resultado = unidades.listar(
            dados, propriedade_id=outra_propriedade["id"]
        )
        self.assertEqual(resultado, [da_segunda])

    def test_filtra_por_tipo(self):
        dados = dados_base()
        criar_unidade_mensal(dados)
        airbnb = criar_unidade_airbnb(dados)
        resultado = unidades.listar(dados, tipo="airbnb")
        self.assertEqual(resultado, [airbnb])

    def test_devolve_lista_nova(self):
        dados = dados_base()
        criar_unidade_mensal(dados)
        resultado = unidades.listar(dados)
        resultado.append("intruso")
        self.assertEqual(len(dados["unidades"]), 1)


class TesteAtualizar(unittest.TestCase):

    def test_recusa_id_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.atualizar(
                dados, "UNI-999", preco_base=Decimal("1")
            )

    def test_none_nao_altera(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        preco_original = unidade["preco_base"]
        unidades.atualizar(dados, unidade["id"])
        self.assertEqual(unidade["preco_base"], preco_original)

    def test_altera_preco_base(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        unidades.atualizar(
            dados, unidade["id"], preco_base=Decimal("300.00")
        )
        self.assertEqual(unidade["preco_base"], Decimal("300.00"))

    def test_altera_epoca_alta_ativa(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        unidades.atualizar(dados, unidade["id"], epoca_alta_ativa=True)
        self.assertTrue(unidade["epoca_alta_ativa"])

    def test_recusa_preco_nao_decimal(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        with self.assertRaises(ValueError):
            unidades.atualizar(dados, unidade["id"], preco_base=300.0)

    def test_recusa_preco_negativo(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        with self.assertRaises(ValueError):
            unidades.atualizar(
                dados, unidade["id"],
                multa_check_in_tardio=Decimal("-5"),
            )


class TesteDesativarReativar(unittest.TestCase):

    def test_desativa_unidade_ativa(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        unidades.desativar(dados, unidade["id"])
        self.assertFalse(unidade["ativo"])

    def test_recusa_desativar_duas_vezes(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        unidades.desativar(dados, unidade["id"])
        with self.assertRaises(ValueError):
            unidades.desativar(dados, unidade["id"])

    def test_recusa_desativar_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.desativar(dados, "UNI-999")

    def test_reativa_unidade_inativa(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        unidades.desativar(dados, unidade["id"])
        unidades.reativar(dados, unidade["id"])
        self.assertTrue(unidade["ativo"])

    def test_recusa_reativar_ja_ativa(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        with self.assertRaises(ValueError):
            unidades.reativar(dados, unidade["id"])

    def test_recusa_reativar_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.reativar(dados, "UNI-999")


class TesteManutencao(unittest.TestCase):

    def test_marca_manutencao(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        unidades.marcar_manutencao(dados, unidade["id"])
        self.assertTrue(unidade["em_manutencao"])

    def test_recusa_marcar_duas_vezes(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        unidades.marcar_manutencao(dados, unidade["id"])
        with self.assertRaises(ValueError):
            unidades.marcar_manutencao(dados, unidade["id"])

    def test_desmarca_manutencao(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        unidades.marcar_manutencao(dados, unidade["id"])
        unidades.desmarcar_manutencao(dados, unidade["id"])
        self.assertFalse(unidade["em_manutencao"])

    def test_recusa_desmarcar_sem_estar_em_manutencao(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        with self.assertRaises(ValueError):
            unidades.desmarcar_manutencao(dados, unidade["id"])

    def test_recusa_id_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.marcar_manutencao(dados, "UNI-999")
        with self.assertRaises(ValueError):
            unidades.desmarcar_manutencao(dados, "UNI-999")


class TesteCriarQuarto(unittest.TestCase):

    def test_cria_quarto_valido(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Quarto 1")
        self.assertEqual(quarto["unidade_id"], unidade["id"])
        self.assertFalse(quarto["privativo"])
        self.assertFalse(quarto["limpeza_incluida"])
        self.assertTrue(quarto["ativo"])
        self.assertIn(quarto, dados["quartos"])

    def test_cria_quarto_privativo_com_limpeza(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(
            dados, unidade["id"], "Suite",
            privativo=True, limpeza_incluida=True,
        )
        self.assertTrue(quarto["privativo"])
        self.assertTrue(quarto["limpeza_incluida"])

    def test_recusa_unidade_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.criar_quarto(dados, "UNI-999", "Quarto 1")

    def test_recusa_nome_vazio(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        with self.assertRaises(ValueError):
            unidades.criar_quarto(dados, unidade["id"], "   ")

    def test_remove_espacos_do_nome(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(
            dados, unidade["id"], "  Quarto 1  "
        )
        self.assertEqual(quarto["nome"], "Quarto 1")


class TesteProcurarQuarto(unittest.TestCase):

    def test_encontra_quarto_existente(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Quarto 1")
        encontrado = unidades.procurar_quarto(dados, quarto["id"])
        self.assertIs(encontrado, quarto)

    def test_devolve_none_para_id_inexistente(self):
        dados = dados_base()
        self.assertIsNone(unidades.procurar_quarto(dados, "QRT-999"))


class TesteListarQuartos(unittest.TestCase):

    def test_filtra_por_unidade(self):
        dados = dados_base()
        unidade_a = criar_unidade_mensal(dados)
        unidade_b = criar_unidade_airbnb(dados)
        quarto_a = unidades.criar_quarto(dados, unidade_a["id"], "A1")
        unidades.criar_quarto(dados, unidade_b["id"], "B1")
        resultado = unidades.listar_quartos(
            dados, unidade_id=unidade_a["id"]
        )
        self.assertEqual(resultado, [quarto_a])

    def test_lista_so_ativos_por_omissao(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        ativo = unidades.criar_quarto(dados, unidade["id"], "Q1")
        inativo = unidades.criar_quarto(dados, unidade["id"], "Q2")
        unidades.desativar_quarto(dados, inativo["id"])
        resultado = unidades.listar_quartos(
            dados, unidade_id=unidade["id"]
        )
        self.assertEqual(resultado, [ativo])


class TesteAtualizarQuarto(unittest.TestCase):

    def test_recusa_id_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.atualizar_quarto(dados, "QRT-999", nome="X")

    def test_altera_nome(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        unidades.atualizar_quarto(dados, quarto["id"], nome="Novo nome")
        self.assertEqual(quarto["nome"], "Novo nome")

    def test_recusa_nome_vazio(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.atualizar_quarto(dados, quarto["id"], nome="   ")

    def test_altera_privativo_e_limpeza_independentes(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        unidades.atualizar_quarto(dados, quarto["id"], privativo=True)
        self.assertTrue(quarto["privativo"])
        self.assertFalse(quarto["limpeza_incluida"])

    def test_none_nao_altera(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(
            dados, unidade["id"], "Q1", privativo=True
        )
        unidades.atualizar_quarto(dados, quarto["id"])
        self.assertEqual(quarto["nome"], "Q1")
        self.assertTrue(quarto["privativo"])


class TesteDesativarReativarQuarto(unittest.TestCase):

    def test_desativa_e_reativa(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        unidades.desativar_quarto(dados, quarto["id"])
        self.assertFalse(quarto["ativo"])
        unidades.reativar_quarto(dados, quarto["id"])
        self.assertTrue(quarto["ativo"])

    def test_recusa_desativar_duas_vezes(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        unidades.desativar_quarto(dados, quarto["id"])
        with self.assertRaises(ValueError):
            unidades.desativar_quarto(dados, quarto["id"])

    def test_recusa_reativar_ja_ativo(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.reativar_quarto(dados, quarto["id"])

    def test_recusa_id_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.desativar_quarto(dados, "QRT-999")
        with self.assertRaises(ValueError):
            unidades.reativar_quarto(dados, "QRT-999")


class TesteCriarLugar(unittest.TestCase):

    def test_cria_lugar_valido(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        self.assertEqual(lugar["quarto_id"], quarto["id"])
        self.assertEqual(lugar["capacidade"], 1)
        self.assertTrue(lugar["ativo"])
        self.assertIn(lugar, dados["lugares"])

    def test_cria_lugar_capacidade_dois(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(
            dados, quarto["id"], "Cama casal", capacidade=2
        )
        self.assertEqual(lugar["capacidade"], 2)

    def test_recusa_quarto_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.criar_lugar(dados, "QRT-999", "Cama 1")

    def test_recusa_nome_vazio(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.criar_lugar(dados, quarto["id"], "  ")

    def test_recusa_capacidade_invalida(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.criar_lugar(
                dados, quarto["id"], "Cama 1", capacidade=0
            )

    def test_recusa_capacidade_none(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.criar_lugar(
                dados, quarto["id"], "Cama 1", capacidade=None # type: ignore
            )


class TesteProcurarLugar(unittest.TestCase):

    def test_encontra_lugar_existente(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        encontrado = unidades.procurar_lugar(dados, lugar["id"])
        self.assertIs(encontrado, lugar)

    def test_devolve_none_para_id_inexistente(self):
        dados = dados_base()
        self.assertIsNone(unidades.procurar_lugar(dados, "LUG-999"))


class TesteListarLugares(unittest.TestCase):

    def test_filtra_por_quarto(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto_a = unidades.criar_quarto(dados, unidade["id"], "A")
        quarto_b = unidades.criar_quarto(dados, unidade["id"], "B")
        lugar_a = unidades.criar_lugar(dados, quarto_a["id"], "Cama 1")
        unidades.criar_lugar(dados, quarto_b["id"], "Cama 1")
        resultado = unidades.listar_lugares(
            dados, quarto_id=quarto_a["id"]
        )
        self.assertEqual(resultado, [lugar_a])

    def test_lista_so_ativos_por_omissao(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        ativo = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        inativo = unidades.criar_lugar(dados, quarto["id"], "Cama 2")
        unidades.desativar_lugar(dados, inativo["id"])
        resultado = unidades.listar_lugares(
            dados, quarto_id=quarto["id"]
        )
        self.assertEqual(resultado, [ativo])


class TesteAtualizarLugar(unittest.TestCase):

    def test_recusa_id_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.atualizar_lugar(dados, "LUG-999", nome="X")

    def test_altera_nome(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        unidades.atualizar_lugar(dados, lugar["id"], nome="Cama nova")
        self.assertEqual(lugar["nome"], "Cama nova")

    def test_recusa_nome_vazio(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        with self.assertRaises(ValueError):
            unidades.atualizar_lugar(dados, lugar["id"], nome="  ")

    def test_altera_capacidade(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        unidades.atualizar_lugar(dados, lugar["id"], capacidade=2)
        self.assertEqual(lugar["capacidade"], 2)

    def test_recusa_capacidade_invalida(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        with self.assertRaises(ValueError):
            unidades.atualizar_lugar(dados, lugar["id"], capacidade=0)

    def test_none_nao_altera(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        unidades.atualizar_lugar(dados, lugar["id"])
        self.assertEqual(lugar["nome"], "Cama 1")
        self.assertEqual(lugar["capacidade"], 1)


class TesteDesativarReativarLugar(unittest.TestCase):

    def test_desativa_e_reativa(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        unidades.desativar_lugar(dados, lugar["id"])
        self.assertFalse(lugar["ativo"])
        unidades.reativar_lugar(dados, lugar["id"])
        self.assertTrue(lugar["ativo"])

    def test_recusa_desativar_duas_vezes(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        unidades.desativar_lugar(dados, lugar["id"])
        with self.assertRaises(ValueError):
            unidades.desativar_lugar(dados, lugar["id"])

    def test_recusa_reativar_ja_ativo(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        quarto = unidades.criar_quarto(dados, unidade["id"], "Q1")
        lugar = unidades.criar_lugar(dados, quarto["id"], "Cama 1")
        with self.assertRaises(ValueError):
            unidades.reativar_lugar(dados, lugar["id"])

    def test_recusa_id_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.desativar_lugar(dados, "LUG-999")
        with self.assertRaises(ValueError):
            unidades.reativar_lugar(dados, "LUG-999")


class TesteEstado(unittest.TestCase):

    def test_recusa_id_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            unidades.estado(dados, "UNI-999", date(2026, 9, 5))

    # --- Mensal: proporção ---

    def test_mensal_sem_ocupacoes_e_zero_sobre_capacidade(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        dar_lugares(dados, unidade["id"], [1, 1])
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "0/2")

    def test_mensal_proporcao_com_ocupacao_ativa(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        dar_lugares(dados, unidade["id"], [1, 1])
        criar_ocupacao(dados, unidade["id"], "mensal", date(2026, 9, 1))
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "1/2")

    def test_mensal_ocupacao_futura_nao_conta(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        dar_lugares(dados, unidade["id"], [1, 1])
        criar_ocupacao(dados, unidade["id"], "mensal", date(2026, 9, 10))
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "0/2")

    def test_mensal_ocupacao_encerrada_nao_conta(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        dar_lugares(dados, unidade["id"], [1, 1])
        criar_ocupacao(
            dados, unidade["id"], "mensal",
            date(2026, 9, 1), data_fim=date(2026, 9, 10),
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 15))
        self.assertEqual(resultado, "0/2")

    def test_mensal_ocupacao_ativa_ate_ao_dia_anterior_ao_encerramento(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        dar_lugares(dados, unidade["id"], [1, 1])
        criar_ocupacao(
            dados, unidade["id"], "mensal",
            date(2026, 9, 1), data_fim=date(2026, 9, 10),
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 9))
        self.assertEqual(resultado, "1/2")

    def test_mensal_ocupacao_inativa_nao_conta(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        dar_lugares(dados, unidade["id"], [1, 1])
        criar_ocupacao(
            dados, unidade["id"], "mensal", date(2026, 9, 1), ativo=False
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "0/2")

    def test_mensal_nao_conta_ocupacoes_de_outra_unidade(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        outra = criar_unidade_mensal(dados)
        dar_lugares(dados, unidade["id"], [1, 1])
        criar_ocupacao(dados, outra["id"], "mensal", date(2026, 9, 1))
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "0/2")

    # --- Airbnb: Livre / Ocupado / Reservado ---

    def test_airbnb_livre_sem_ocupacoes(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "Livre")

    def test_airbnb_ocupado_na_noite_de_entrada(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 10))
        self.assertEqual(resultado, "Ocupado")

    def test_airbnb_ocupado_a_meio_da_estadia(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 12))
        self.assertEqual(resultado, "Ocupado")

    def test_airbnb_ocupado_na_ultima_noite(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 14))
        self.assertEqual(resultado, "Ocupado")

    def test_airbnb_livre_no_dia_de_saida(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 15))
        self.assertEqual(resultado, "Livre")

    def test_airbnb_reservado_ocupacao_futura(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "Reservado")

    def test_airbnb_entrada_e_saida_no_mesmo_dia_nao_e_conflito(self):
        """Réplica, ao nível do estado(), do caso já coberto na
        validação de sobreposição: a saída de uma reserva no mesmo
        dia da entrada da seguinte não é conflito — a noite desse
        dia fica com a segunda reserva.
        """
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 15), data_fim=date(2026, 9, 18),
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 15))
        self.assertEqual(resultado, "Ocupado")

    def test_airbnb_reserva_cancelada_nao_conta(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
            ativo=False,
        )
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 12))
        self.assertEqual(resultado, "Livre")

    # --- Manutenção sobrepõe-se a tudo ---

    def test_manutencao_sobrepoe_se_sem_ocupacoes(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        unidades.marcar_manutencao(dados, unidade["id"])
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "Em manutenção")

    def test_manutencao_sobrepoe_se_com_ocupacao_ativa(self):
        dados = dados_base()
        unidade = criar_unidade_airbnb(dados)
        criar_ocupacao(
            dados, unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        unidades.marcar_manutencao(dados, unidade["id"])
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 12))
        self.assertEqual(resultado, "Em manutenção")

    def test_manutencao_sobrepoe_se_no_mensal(self):
        dados = dados_base()
        unidade = criar_unidade_mensal(dados)
        dar_lugares(dados, unidade["id"], [1, 1])
        criar_ocupacao(dados, unidade["id"], "mensal", date(2026, 9, 1))
        unidades.marcar_manutencao(dados, unidade["id"])
        resultado = unidades.estado(dados, unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "Em manutenção")


if __name__ == "__main__":
    unittest.main()