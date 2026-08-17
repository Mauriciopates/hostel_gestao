"""Testes de clientes.py — registo, listagem de incompletos e RGPD.

Mesma abordagem de teste_unidades.py: estrutura de dados em memória,
sem pasta temporária. repositorio.proximo_id() é a única exceção que
toca em ficheiro (decisão 1). Os testes de validar_cliente() e
nif_valido() já existem em teste_validacoes.py — aqui confirma-se só
que clientes.py delega corretamente, sem repetir essa cobertura.
"""

import sys
import unittest
from datetime import date

sys.path.insert(0, "src")

import clientes


def dados_base():
    """Devolve uma estrutura de dados nova, sem clientes."""
    return {"clientes": []}


def criar_cliente_mensal(dados, **overrides):
    """Cria um cliente de teste válido para o regime mensal."""
    campos = {
        "nome": "Ana Silva",
        "tipo_documento": "Cartão de Cidadão",
        "numero_documento": "12345678",
        "regime": "mensal",
        "nif": "501442600",
    }
    campos.update(overrides)
    return clientes.criar(dados, **campos)


def criar_cliente_airbnb(dados, **overrides):
    """Cria um cliente de teste válido para o regime Airbnb, sem NIF."""
    campos = {
        "nome": "John Smith",
        "tipo_documento": "Passaporte",
        "numero_documento": "X1234567",
        "regime": "airbnb",
    }
    campos.update(overrides)
    return clientes.criar(dados, **campos)


class TesteCriar(unittest.TestCase):

    def test_cria_cliente_mensal_valido(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        self.assertEqual(cliente["nome"], "Ana Silva")
        self.assertEqual(cliente["nif"], "501442600")
        self.assertTrue(cliente["ativo"])
        self.assertFalse(cliente["anonimizado"])
        self.assertIn(cliente, dados["clientes"])

    def test_cria_cliente_airbnb_sem_nif(self):
        dados = dados_base()
        cliente = criar_cliente_airbnb(dados)
        self.assertEqual(cliente["nif"], "")

    def test_id_com_prefixo_cli(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        self.assertTrue(cliente["id"].startswith("CLI-"))

    def test_regime_nao_fica_guardado(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        self.assertNotIn("regime", cliente)

    def test_completo_fica_marcado_como_nao_incompleto(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(
            dados,
            email="ana@exemplo.pt",
            telefone="912345678",
            morada="Rua do Porto, 12",
            nacionalidade="Portuguesa",
        )
        self.assertFalse(cliente["incompleto"])

    def test_sem_opcionais_fica_marcado_incompleto(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        self.assertTrue(cliente["incompleto"])

    def test_recusa_nome_vazio(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            criar_cliente_mensal(dados, nome="   ")

    def test_recusa_tipo_documento_vazio(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            criar_cliente_mensal(dados, tipo_documento="")

    def test_recusa_tipo_documento_fora_da_lista(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            criar_cliente_mensal(dados, tipo_documento="Carta de Condução")

    def test_recusa_numero_documento_vazio(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            criar_cliente_mensal(dados, numero_documento="  ")

    def test_recusa_nif_vazio_no_mensal(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            criar_cliente_mensal(dados, nif="")

    def test_recusa_nif_invalido_no_mensal(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            criar_cliente_mensal(dados, nif="501442601")

    def test_limpa_espacos_dos_campos_de_texto(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(
            dados, nome="  Ana Silva  ", morada="  Rua do Porto  "
        )
        self.assertEqual(cliente["nome"], "Ana Silva")
        self.assertEqual(cliente["morada"], "Rua do Porto")

    def test_guarda_datas_como_vieram(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(
            dados,
            data_nascimento=date(1990, 5, 20),
            validade_documento=date(2030, 1, 1),
        )
        self.assertEqual(cliente["data_nascimento"], date(1990, 5, 20))
        self.assertEqual(cliente["validade_documento"], date(2030, 1, 1))


class TesteProcurar(unittest.TestCase):

    def test_encontra_cliente_existente(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        encontrado = clientes.procurar(dados, cliente["id"])
        self.assertIs(encontrado, cliente)

    def test_devolve_none_para_id_inexistente(self):
        dados = dados_base()
        self.assertIsNone(clientes.procurar(dados, "CLI-999"))

    def test_encontra_cliente_inativo(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.desativar(dados, cliente["id"])
        self.assertIsNotNone(clientes.procurar(dados, cliente["id"]))


class TesteListar(unittest.TestCase):

    def test_lista_vazia_sem_clientes(self):
        dados = dados_base()
        self.assertEqual(clientes.listar(dados), [])

    def test_lista_so_ativos_por_omissao(self):
        dados = dados_base()
        ativo = criar_cliente_mensal(dados)
        inativo = criar_cliente_airbnb(dados)
        clientes.desativar(dados, inativo["id"])
        self.assertEqual(clientes.listar(dados), [ativo])

    def test_lista_incluir_inativos(self):
        dados = dados_base()
        criar_cliente_mensal(dados)
        inativo = criar_cliente_airbnb(dados)
        clientes.desativar(dados, inativo["id"])
        resultado = clientes.listar(dados, incluir_inativos=True)
        self.assertEqual(len(resultado), 2)

    def test_filtra_por_incompleto_true(self):
        dados = dados_base()
        incompleto = criar_cliente_mensal(dados)
        criar_cliente_airbnb(
            dados,
            email="j@exemplo.com",
            telefone="1",
            morada="Rua X",
            nacionalidade="Americana",
        )
        resultado = clientes.listar(dados, incompleto=True)
        self.assertEqual(resultado, [incompleto])

    def test_filtra_por_incompleto_false(self):
        dados = dados_base()
        criar_cliente_mensal(dados)
        completo = criar_cliente_airbnb(
            dados,
            email="j@exemplo.com",
            telefone="1",
            morada="Rua X",
            nacionalidade="Americana",
        )
        resultado = clientes.listar(dados, incompleto=False)
        self.assertEqual(resultado, [completo])

    def test_devolve_lista_nova(self):
        dados = dados_base()
        criar_cliente_mensal(dados)
        resultado = clientes.listar(dados)
        resultado.append("intruso")
        self.assertEqual(len(dados["clientes"]), 1)


class TesteAtualizar(unittest.TestCase):

    def test_recusa_id_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            clientes.atualizar(dados, "CLI-999", nome="Teste")

    def test_none_nao_altera(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.atualizar(dados, cliente["id"])
        self.assertEqual(cliente["nome"], "Ana Silva")

    def test_altera_email(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.atualizar(dados, cliente["id"], email="nova@exemplo.pt")
        self.assertEqual(cliente["email"], "nova@exemplo.pt")

    def test_limpa_campo_opcional_com_vazio(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados, telefone="912345678")
        clientes.atualizar(dados, cliente["id"], telefone="")
        self.assertEqual(cliente["telefone"], "")

    def test_recusa_apagar_nome(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        with self.assertRaises(ValueError):
            clientes.atualizar(dados, cliente["id"], nome="")

    def test_recusa_apagar_numero_documento(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        with self.assertRaises(ValueError):
            clientes.atualizar(dados, cliente["id"], numero_documento="")

    def test_recusa_tipo_documento_fora_da_lista(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        with self.assertRaises(ValueError):
            clientes.atualizar(
                dados, cliente["id"], tipo_documento="Carta de Condução"
            )

    def test_sem_regime_nif_nao_e_obrigatorio(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.atualizar(dados, cliente["id"], nif="")
        self.assertEqual(cliente["nif"], "")

    def test_sem_regime_nif_invalido_e_recusado(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        with self.assertRaises(ValueError):
            clientes.atualizar(dados, cliente["id"], nif="501442601")

    def test_com_regime_mensal_nif_vazio_e_recusado(self):
        dados = dados_base()
        cliente = criar_cliente_airbnb(dados)
        with self.assertRaises(ValueError):
            clientes.atualizar(dados, cliente["id"], regime="mensal")

    def test_com_regime_mensal_nif_novo_valido_passa(self):
        dados = dados_base()
        cliente = criar_cliente_airbnb(dados)
        clientes.atualizar(
            dados, cliente["id"], regime="mensal", nif="501442600"
        )
        self.assertEqual(cliente["nif"], "501442600")

    def test_atualiza_incompleto_ao_preencher_opcionais(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        self.assertTrue(cliente["incompleto"])
        clientes.atualizar(
            dados,
            cliente["id"],
            email="ana@exemplo.pt",
            telefone="912345678",
            morada="Rua do Porto, 12",
            nacionalidade="Portuguesa",
        )
        self.assertFalse(cliente["incompleto"])

    def test_altera_data_nascimento(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.atualizar(
            dados, cliente["id"], data_nascimento=date(1990, 5, 20)
        )
        self.assertEqual(cliente["data_nascimento"], date(1990, 5, 20))


class TesteDesativarReativar(unittest.TestCase):

    def test_desativa_cliente_ativo(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.desativar(dados, cliente["id"])
        self.assertFalse(cliente["ativo"])

    def test_recusa_desativar_duas_vezes(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.desativar(dados, cliente["id"])
        with self.assertRaises(ValueError):
            clientes.desativar(dados, cliente["id"])

    def test_recusa_desativar_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            clientes.desativar(dados, "CLI-999")

    def test_reativa_cliente_inativo(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.desativar(dados, cliente["id"])
        clientes.reativar(dados, cliente["id"])
        self.assertTrue(cliente["ativo"])

    def test_recusa_reativar_ja_ativo(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        with self.assertRaises(ValueError):
            clientes.reativar(dados, cliente["id"])

    def test_recusa_reativar_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            clientes.reativar(dados, "CLI-999")

    def test_recusa_reativar_cliente_anonimizado(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.anonimizar(dados, cliente["id"], "RES-001", date.today())
        with self.assertRaises(ValueError):
            clientes.reativar(dados, cliente["id"])


class TesteAnonimizar(unittest.TestCase):

    def test_substitui_o_nome(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.anonimizar(dados, cliente["id"], "RES-001", date.today())
        self.assertEqual(
            cliente["nome"], f"Titular anonimizado {cliente['id']}"
        )

    def test_apaga_dados_pessoais(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(
            dados,
            email="ana@exemplo.pt",
            telefone="912345678",
            morada="Rua do Porto, 12",
            contacto_emergencia="Filho: 913456789",
            data_nascimento=date(1990, 5, 20),
        )
        clientes.anonimizar(dados, cliente["id"], "RES-001", date.today())

        self.assertEqual(cliente["email"], "")
        self.assertEqual(cliente["telefone"], "")
        self.assertEqual(cliente["morada"], "")
        self.assertEqual(cliente["nif"], "")
        self.assertEqual(cliente["numero_documento"], "")
        self.assertIsNone(cliente["validade_documento"])
        self.assertIsNone(cliente["data_nascimento"])
        self.assertEqual(cliente["contacto_emergencia"], "")

    def test_conserva_nacionalidade_e_tipo_documento(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados, nacionalidade="Portuguesa")
        clientes.anonimizar(dados, cliente["id"], "RES-001", date.today())

        self.assertEqual(cliente["nacionalidade"], "Portuguesa")
        self.assertEqual(cliente["tipo_documento"], "Cartão de Cidadão")

    def test_marca_anonimizado_e_regista_autoria(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        hoje = date.today()
        clientes.anonimizar(dados, cliente["id"], "RES-001", hoje)

        self.assertTrue(cliente["anonimizado"])
        self.assertEqual(cliente["data_anonimizado"], hoje)
        self.assertEqual(cliente["responsavel_anonimizado_id"], "RES-001")
        self.assertFalse(cliente["ativo"])
        self.assertTrue(cliente["incompleto"])

    def test_recusa_anonimizar_duas_vezes(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        clientes.anonimizar(dados, cliente["id"], "RES-001", date.today())
        with self.assertRaises(ValueError):
            clientes.anonimizar(
                dados, cliente["id"], "RES-001", date.today()
            )

    def test_recusa_anonimizar_inexistente(self):
        dados = dados_base()
        with self.assertRaises(ValueError):
            clientes.anonimizar(dados, "CLI-999", "RES-001", date.today())

    def test_recusa_sem_responsavel(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        with self.assertRaises(ValueError):
            clientes.anonimizar(dados, cliente["id"], "  ", date.today())

    def test_recusa_sem_data(self):
        dados = dados_base()
        cliente = criar_cliente_mensal(dados)
        with self.assertRaises(ValueError):
            clientes.anonimizar(dados, cliente["id"], "RES-001", None)


if __name__ == "__main__":
    unittest.main()