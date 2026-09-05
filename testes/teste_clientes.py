"""Testes de clientes.py — registo, listagem de incompletos e RGPD.

MIGRAÇÃO MySQL (Fase 2): tal como propriedades.py, unidades.py e
responsaveis.py, clientes.py já não recebe nem devolve a estrutura
`dados` em memória — fala diretamente com a base de dados MySQL,
através do repositorio.py. Estes testes correm contra uma base de
dados de teste dedicada e isolada da real (ver apoio_bd.py); cada
teste começa com as tabelas vazias e os contadores de identificadores
reiniciados, tal como antes cada teste começava com um dicionário
`dados` novo.

Os testes de validar_cliente() e nif_valido() já existem em
teste_validacoes.py — aqui confirma-se só que clientes.py delega
corretamente, sem repetir essa cobertura.

Os dois construtores abaixo (criar_cliente_mensal/airbnb) devolvem,
por omissão, um cliente COMPLETO nos dois regimes (nacionalidade,
morada, estado_civil, data de nascimento e validade do documento
todos preenchidos) — decisão de 26/08, ponto 2, tornou-os
obrigatórios consoante o regime, e um cliente incompleto nalgum
destes campos bloquearia `clientes.atualizar()` em qualquer chamada
que não os toque (ver nota em Pendencias_Antes_v1.0.0.txt, item 2).
Os testes que precisam de um cliente incompleto de propósito limpam
o campo que querem testar, em vez de partir de um cliente incompleto
por omissão.

NOTA sobre identidade: `procurar()` faz sempre um SELECT novo à base
de dados — já não devolve o MESMO objeto Python que `criar()`
devolveu. Por isso comparamos com `assertEqual` (valores iguais),
nunca com `assertIs` (mesmo objeto). As funções que alteram um
cliente (`atualizar`, `desativar`, `reativar`, `anonimizar`) também
fazem o seu próprio `procurar()` interno antes de mutar e devolver o
registo — por isso os testes passaram a verificar sempre o valor
DEVOLVIDO por cada uma destas chamadas, e não o objeto que
`criar_cliente_mensal/airbnb` tinha devolvido antes (esse já não é o
mesmo objeto Python que ficou mutado).

Cada teste que precisa de um responsável cria o seu, com
responsaveis.criar(...), em vez do antigo "RES-001" fixo em
dados_base() — a anonimização valida a autoria através de
responsaveis.validar_autoria.
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from apoio_BD import BaseMySQLTest

import clientes
import responsaveis


def criar_cliente_mensal(**overrides):
    """Cria um cliente de teste válido e completo para o regime
    mensal (nif, morada e estado_civil obrigatórios pela decisão de
    26/08 — ponto 2)."""
    campos = {
        "nome": "Ana Silva",
        "tipo_documento": "Cartão de Cidadão",
        "numero_documento": "12345678",
        "regime": "mensal",
        "nif": "501442600",
        "morada": "Rua do Porto, 12",
        "nacionalidade": "Portuguesa",
        "estado_civil": "Solteiro(a)",
        "data_nascimento": date(1990, 5, 20),
        "validade_documento": date(2030, 1, 1),
    }
    campos.update(overrides)
    return clientes.criar(**campos)


def criar_cliente_airbnb(**overrides):
    """Cria um cliente de teste válido e completo para o regime
    Airbnb, sem NIF (nacionalidade e data de nascimento obrigatórias
    pela decisão de 26/08 — ponto 2)."""
    campos = {
        "nome": "John Smith",
        "tipo_documento": "Passaporte",
        "numero_documento": "X1234567",
        "regime": "airbnb",
        "morada": "123 Main St",
        "nacionalidade": "Americana",
        "estado_civil": "Solteiro(a)",
        "data_nascimento": date(1985, 3, 12),
        "validade_documento": date(2030, 1, 1),
    }
    campos.update(overrides)
    return clientes.criar(**campos)


class TesteCriar(BaseMySQLTest):

    def test_cria_cliente_mensal_valido(self):
        cliente = criar_cliente_mensal()
        self.assertEqual(cliente["nome"], "Ana Silva")
        self.assertEqual(cliente["nif"], "501442600")
        self.assertTrue(cliente["ativo"])
        self.assertFalse(cliente["anonimizado"])
        self.assertEqual(cliente, clientes.procurar(cliente["id"]))

    def test_cria_cliente_airbnb_sem_nif(self):
        cliente = criar_cliente_airbnb()
        self.assertEqual(cliente["nif"], "")

    def test_id_com_prefixo_cli(self):
        cliente = criar_cliente_mensal()
        self.assertTrue(cliente["id"].startswith("CLI-"))

    def test_regime_nao_fica_guardado(self):
        cliente = criar_cliente_mensal()
        self.assertNotIn("regime", cliente)

    def test_completo_fica_marcado_como_nao_incompleto(self):
        cliente = criar_cliente_mensal(
            email="ana@exemplo.pt",
            telefone="912345678",
            morada="Rua do Porto, 12",
            nacionalidade="Portuguesa",
        )
        self.assertFalse(cliente["incompleto"])

    def test_sem_opcionais_fica_marcado_incompleto(self):
        cliente = criar_cliente_mensal()
        self.assertTrue(cliente["incompleto"])

    def test_recusa_nome_vazio(self):
        with self.assertRaises(ValueError):
            criar_cliente_mensal(nome="   ")

    def test_recusa_tipo_documento_vazio(self):
        with self.assertRaises(ValueError):
            criar_cliente_mensal(tipo_documento="")

    def test_recusa_tipo_documento_fora_da_lista(self):
        with self.assertRaises(ValueError):
            criar_cliente_mensal(tipo_documento="Carta de Condução")

    def test_recusa_numero_documento_vazio(self):
        with self.assertRaises(ValueError):
            criar_cliente_mensal(numero_documento="  ")

    def test_recusa_nif_vazio_no_mensal(self):
        with self.assertRaises(ValueError):
            criar_cliente_mensal(nif="")

    def test_recusa_nif_invalido_no_mensal(self):
        with self.assertRaises(ValueError):
            criar_cliente_mensal(nif="501442601")

    def test_recusa_validade_documento_em_falta(self):
        """Novo (decisão de 26/08, ponto 2): obrigatória nos dois
        regimes."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(validade_documento=None)

    def test_recusa_data_nascimento_em_falta(self):
        """Novo (decisão de 26/08, ponto 2, reforçada pelo aluno):
        obrigatória nos dois regimes."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(data_nascimento=None)

    def test_recusa_morada_em_falta_no_mensal(self):
        """Novo (decisão de 26/08, ponto 2): morada obrigatória só
        no mensal."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(morada="")

    def test_recusa_estado_civil_em_falta_no_mensal(self):
        """Campo novo (decisão de 26/08, ponto 2): obrigatório só no
        mensal."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(estado_civil="")

    def test_recusa_nacionalidade_em_falta_no_airbnb(self):
        """Novo (decisão de 26/08, ponto 2): nacionalidade
        obrigatória só no Airbnb."""
        with self.assertRaises(ValueError):
            criar_cliente_airbnb(nacionalidade="")

    def test_limpa_espacos_dos_campos_de_texto(self):
        cliente = criar_cliente_mensal(
            nome="  Ana Silva  ", morada="  Rua do Porto  "
        )
        self.assertEqual(cliente["nome"], "Ana Silva")
        self.assertEqual(cliente["morada"], "Rua do Porto")

    def test_guarda_datas_como_vieram(self):
        cliente = criar_cliente_mensal(
            data_nascimento=date(1990, 5, 20),
            validade_documento=date(2030, 1, 1),
        )
        self.assertEqual(cliente["data_nascimento"], date(1990, 5, 20))
        self.assertEqual(cliente["validade_documento"], date(2030, 1, 1))

    def test_recusa_nif_duplicado_de_cliente_ativo(self):
        """Novo (decisão de 26/08, item 5): o mesmo NIF não pode
        pertencer a dois clientes ativos."""
        criar_cliente_mensal(nif="501442600")
        with self.assertRaises(ValueError):
            criar_cliente_mensal(
                numero_documento="99999999", nif="501442600"
            )

    def test_permite_nif_vazio_repetido(self):
        """Dois clientes Airbnb sem NIF nunca colidem entre si — o
        NIF só é obrigatório no mensal."""
        criar_cliente_airbnb()
        cliente_2 = criar_cliente_airbnb(numero_documento="X999")
        self.assertEqual(cliente_2["nif"], "")

    def test_permite_nif_repetido_de_cliente_inativo(self):
        """Um cliente inativo não bloqueia a reutilização do NIF."""
        cliente_1 = criar_cliente_mensal(nif="501442600")
        clientes.desativar(cliente_1["id"])
        cliente_2 = criar_cliente_mensal(
            numero_documento="99999999", nif="501442600"
        )
        self.assertEqual(cliente_2["nif"], "501442600")


class TesteProcurar(BaseMySQLTest):

    def test_encontra_cliente_existente(self):
        cliente = criar_cliente_mensal()
        encontrado = clientes.procurar(cliente["id"])
        self.assertEqual(encontrado, cliente)

    def test_devolve_none_para_id_inexistente(self):
        self.assertIsNone(clientes.procurar("CLI-999"))

    def test_encontra_cliente_inativo(self):
        cliente = criar_cliente_mensal()
        clientes.desativar(cliente["id"])
        self.assertIsNotNone(clientes.procurar(cliente["id"]))


class TesteListar(BaseMySQLTest):

    def test_lista_vazia_sem_clientes(self):
        self.assertEqual(clientes.listar(), [])

    def test_lista_so_ativos_por_omissao(self):
        ativo = criar_cliente_mensal()
        inativo = criar_cliente_airbnb()
        clientes.desativar(inativo["id"])
        self.assertEqual(clientes.listar(), [ativo])

    def test_lista_incluir_inativos(self):
        criar_cliente_mensal()
        inativo = criar_cliente_airbnb()
        clientes.desativar(inativo["id"])
        resultado = clientes.listar(incluir_inativos=True)
        self.assertEqual(len(resultado), 2)

    def test_filtra_por_incompleto_true(self):
        incompleto = criar_cliente_mensal()
        criar_cliente_airbnb(
            email="j@exemplo.com",
            telefone="1",
            morada="Rua X",
            nacionalidade="Americana",
        )
        resultado = clientes.listar(incompleto=True)
        self.assertEqual(resultado, [incompleto])

    def test_filtra_por_incompleto_false(self):
        criar_cliente_mensal()
        completo = criar_cliente_airbnb(
            email="j@exemplo.com",
            telefone="1",
            morada="Rua X",
            nacionalidade="Americana",
        )
        resultado = clientes.listar(incompleto=False)
        self.assertEqual(resultado, [completo])

    def test_devolve_lista_nova(self):
        criar_cliente_mensal()
        resultado = clientes.listar()
        resultado.append("intruso")
        self.assertEqual(len(clientes.listar()), 1)


class TesteAtualizar(BaseMySQLTest):

    def test_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            clientes.atualizar("CLI-999", nome="Teste")

    def test_none_nao_altera(self):
        cliente = criar_cliente_mensal()
        atualizado = clientes.atualizar(cliente["id"])
        self.assertEqual(atualizado["nome"], "Ana Silva")

    def test_altera_email(self):
        cliente = criar_cliente_mensal()
        atualizado = clientes.atualizar(cliente["id"], email="nova@exemplo.pt")
        self.assertEqual(atualizado["email"], "nova@exemplo.pt")

    def test_limpa_campo_opcional_com_vazio(self):
        cliente = criar_cliente_mensal(telefone="912345678")
        atualizado = clientes.atualizar(cliente["id"], telefone="")
        self.assertEqual(atualizado["telefone"], "")

    def test_recusa_apagar_nome(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], nome="")

    def test_recusa_apagar_numero_documento(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], numero_documento="")

    def test_recusa_tipo_documento_fora_da_lista(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(
                cliente["id"], tipo_documento="Carta de Condução"
            )

    def test_sem_regime_nif_nao_e_obrigatorio(self):
        cliente = criar_cliente_mensal()
        atualizado = clientes.atualizar(cliente["id"], nif="")
        self.assertEqual(atualizado["nif"], "")

    def test_sem_regime_nif_invalido_e_recusado(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], nif="501442601")

    def test_com_regime_mensal_nif_vazio_e_recusado(self):
        cliente = criar_cliente_airbnb()
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], regime="mensal")

    def test_com_regime_mensal_nif_novo_valido_passa(self):
        cliente = criar_cliente_airbnb()
        atualizado = clientes.atualizar(
            cliente["id"], regime="mensal", nif="501442600"
        )
        self.assertEqual(atualizado["nif"], "501442600")

    def test_recusa_atualizar_nif_para_valor_de_outro_cliente_ativo(self):
        """Novo (decisão de 26/08, item 5)."""
        criar_cliente_mensal(nif="501442600")
        cliente_2 = criar_cliente_mensal(
            numero_documento="99999999", nif="222222220"
        )
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente_2["id"], nif="501442600")

    def test_atualizar_mantendo_o_proprio_nif_nao_e_recusado(self):
        cliente = criar_cliente_mensal(nif="501442600")
        atualizado = clientes.atualizar(cliente["id"], nif="501442600")
        self.assertEqual(atualizado["nif"], "501442600")

    def test_permite_atualizar_nif_para_valor_de_cliente_inativo(self):
        cliente_1 = criar_cliente_mensal(nif="501442600")
        clientes.desativar(cliente_1["id"])
        cliente_2 = criar_cliente_mensal(
            numero_documento="99999999", nif="222222220"
        )
        atualizado = clientes.atualizar(cliente_2["id"], nif="501442600")
        self.assertEqual(atualizado["nif"], "501442600")

    def test_recusa_apagar_morada_no_regime_mensal(self):
        """Novo (decisão de 26/08, ponto 2): tentar limpar a morada
        com regime="mensal" é recusado por validar_cliente."""
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], regime="mensal", morada="")

    def test_recusa_apagar_nacionalidade_no_regime_airbnb(self):
        """Novo (decisão de 26/08, ponto 2): tentar limpar a
        nacionalidade com regime="airbnb" é recusado por
        validar_cliente."""
        cliente = criar_cliente_airbnb()
        with self.assertRaises(ValueError):
            clientes.atualizar(
                cliente["id"], regime="airbnb", nacionalidade=""
            )

    def test_altera_estado_civil(self):
        """Campo novo (decisão de 26/08, ponto 2)."""
        cliente = criar_cliente_mensal()
        atualizado = clientes.atualizar(
            cliente["id"], estado_civil="Casado(a)"
        )
        self.assertEqual(atualizado["estado_civil"], "Casado(a)")

    def test_atualiza_incompleto_ao_preencher_opcionais(self):
        cliente = criar_cliente_mensal()
        self.assertTrue(cliente["incompleto"])
        atualizado = clientes.atualizar(
            cliente["id"],
            email="ana@exemplo.pt",
            telefone="912345678",
            morada="Rua do Porto, 12",
            nacionalidade="Portuguesa",
        )
        self.assertFalse(atualizado["incompleto"])

    def test_altera_data_nascimento(self):
        cliente = criar_cliente_mensal()
        atualizado = clientes.atualizar(
            cliente["id"], data_nascimento=date(1990, 5, 20)
        )
        self.assertEqual(atualizado["data_nascimento"], date(1990, 5, 20))

    def test_recusa_atualizar_cliente_anonimizado(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal()
        clientes.anonimizar(cliente["id"], resp["id"], date.today())
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], nome="Novo Nome")


class TesteDesativarReativar(BaseMySQLTest):

    def test_desativa_cliente_ativo(self):
        cliente = criar_cliente_mensal()
        desativado = clientes.desativar(cliente["id"])
        self.assertFalse(desativado["ativo"])

    def test_recusa_desativar_duas_vezes(self):
        cliente = criar_cliente_mensal()
        clientes.desativar(cliente["id"])
        with self.assertRaises(ValueError):
            clientes.desativar(cliente["id"])

    def test_recusa_desativar_inexistente(self):
        with self.assertRaises(ValueError):
            clientes.desativar("CLI-999")

    def test_reativa_cliente_inativo(self):
        cliente = criar_cliente_mensal()
        clientes.desativar(cliente["id"])
        reativado = clientes.reativar(cliente["id"])
        self.assertTrue(reativado["ativo"])

    def test_recusa_reativar_ja_ativo(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.reativar(cliente["id"])

    def test_recusa_reativar_inexistente(self):
        with self.assertRaises(ValueError):
            clientes.reativar("CLI-999")

    def test_recusa_reativar_cliente_anonimizado(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal()
        clientes.anonimizar(cliente["id"], resp["id"], date.today())
        with self.assertRaises(ValueError):
            clientes.reativar(cliente["id"])

    def test_recusa_reativar_quando_nif_pertence_a_outro_ativo(self):
        """Novo (decisão de 26/08, item 6): fecha o "gap" que
        deixava dois clientes ativos ficarem com o mesmo NIF —
        cliente_1 desativado, cliente_2 criado entretanto com o
        mesmo NIF (permitido, item 5, porque cliente_1 está
        inativo), e só então se tenta reativar cliente_1."""
        cliente_1 = criar_cliente_mensal(nif="501442600")
        clientes.desativar(cliente_1["id"])
        criar_cliente_mensal(numero_documento="99999999", nif="501442600")
        with self.assertRaises(ValueError):
            clientes.reativar(cliente_1["id"])

    def test_permite_reativar_quando_nif_esta_livre(self):
        """Confirma que a verificação nova não bloqueia o caso
        normal: NIF que continua livre."""
        cliente = criar_cliente_mensal(nif="501442600")
        clientes.desativar(cliente["id"])
        reativado = clientes.reativar(cliente["id"])
        self.assertTrue(reativado["ativo"])


class TesteAnonimizar(BaseMySQLTest):

    def test_substitui_o_nome(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal()
        anonimizado = clientes.anonimizar(
            cliente["id"], resp["id"], date.today()
        )
        self.assertEqual(
            anonimizado["nome"], f"Titular anonimizado {cliente['id']}"
        )

    def test_apaga_dados_pessoais(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal(
            email="ana@exemplo.pt",
            telefone="912345678",
            morada="Rua do Porto, 12",
            contacto_emergencia="Filho: 913456789",
            data_nascimento=date(1990, 5, 20),
        )
        anonimizado = clientes.anonimizar(
            cliente["id"], resp["id"], date.today()
        )

        self.assertEqual(anonimizado["email"], "")
        self.assertEqual(anonimizado["telefone"], "")
        self.assertEqual(anonimizado["morada"], "")
        self.assertEqual(anonimizado["nif"], "")
        self.assertEqual(anonimizado["numero_documento"], "")
        self.assertIsNone(anonimizado["validade_documento"])
        self.assertIsNone(anonimizado["data_nascimento"])
        self.assertEqual(anonimizado["contacto_emergencia"], "")

    def test_conserva_nacionalidade_e_tipo_documento(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal(nacionalidade="Portuguesa")
        anonimizado = clientes.anonimizar(
            cliente["id"], resp["id"], date.today()
        )

        self.assertEqual(anonimizado["nacionalidade"], "Portuguesa")
        self.assertEqual(anonimizado["tipo_documento"], "Cartão de Cidadão")

    def test_marca_anonimizado_e_regista_autoria(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal()
        hoje = date.today()
        anonimizado = clientes.anonimizar(cliente["id"], resp["id"], hoje)

        self.assertTrue(anonimizado["anonimizado"])
        self.assertEqual(anonimizado["data_anonimizado"], hoje)
        self.assertEqual(anonimizado["responsavel_anonimizado_id"], resp["id"])
        self.assertFalse(anonimizado["ativo"])
        self.assertTrue(anonimizado["incompleto"])

    def test_recusa_anonimizar_duas_vezes(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal()
        clientes.anonimizar(cliente["id"], resp["id"], date.today())
        with self.assertRaises(ValueError):
            clientes.anonimizar(cliente["id"], resp["id"], date.today())

    def test_recusa_anonimizar_inexistente(self):
        resp = responsaveis.criar("Responsável de teste")
        with self.assertRaises(ValueError):
            clientes.anonimizar("CLI-999", resp["id"], date.today())

    def test_recusa_sem_responsavel(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.anonimizar(cliente["id"], "  ", date.today())

    def test_recusa_sem_data(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.anonimizar(cliente["id"], resp["id"], None)


if __name__ == "__main__":
    unittest.main()