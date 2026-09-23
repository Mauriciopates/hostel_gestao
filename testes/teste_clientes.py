"""Testes de clientes.py — registo, listagem de incompletos e RGPD.

MIGRAÇÃO MySQL (Fase 2): tal como propriedades.py, unidades.py e
responsaveis.py, clientes.py já não recebe nem devolve a estrutura
`dados` em memória — fala diretamente com a base de dados MySQL,
através do repositorio.py. Estes testes correm contra uma base de
dados de teste dedicada e isolada da real (ver apoio_BD.py); cada
teste começa com as tabelas vazias e os contadores de identificadores
reiniciados, tal como antes cada teste começava com um dicionário
`dados` novo.

Os testes de validar_cliente() e nif_valido() já existem em
teste_validacoes.py — aqui confirma-se só que clientes.py delega
corretamente, sem repetir essa cobertura.

Os dois construtores abaixo (criar_cliente_mensal/airbnb) devolvem,
por omissão, um cliente COMPLETO nos dois regimes — mas o que
significa "completo" mudou com a decisão de 16/09/2026:

- Mensal: passou a exigir 'telefone' e 'nacionalidade' como
  obrigatórios (antes eram opcionais). O construtor fornece ambos.
- Airbnb: passou a exigir 'pais_emissor_documento' e
  'pais_residencia' (campos novos do boletim de alojamento). O
  construtor fornece os dois, com "Brasil" — hóspede fora da UE,
  que é o caso típico deste regime e distingue dos mensais.

O conceito de "incompleto" (campos em falta que não bloqueavam a
gravação, decisão 11 antiga) foi DESCARTADO na reestruturação de
16/09/2026: cada regime passou a ter o seu próprio formulário, que
só pede o que precisa, e o que é obrigatório bloqueia com ValueError.
A coluna 'incompleto' sobrevive na base de dados com outro uso —
`clientes.anonimizar` marca-a True para sinalizar dados apagados
por RGPD. É por isso que os testes de filtro 'incompleto' agora
testam esse cenário (um cliente anonimizado), e não clientes a meio
do cadastro.

NOTA sobre 'regime' em clientes.atualizar: quando um teste atualiza
um cliente e NÃO indica o regime explicitamente, o `clientes.atualizar`
assume "airbnb" (decisão de 26/08 — ver docstring da função). Para
um cliente mensal, isto faz com que a validação exija os campos do
Airbnb (país emissor, país residência), que um cliente mensal não
tem — e a atualização rebenta com ValueError, mesmo sendo uma
alteração que nada tem a ver com o regime. Por isso todos os testes
abaixo que atualizam um cliente mensal passam `regime="mensal"`
explicitamente.

NOTA sobre 'ativo' e 'incompleto' nos filtros: `clientes.anonimizar`
marca o cliente como `anonimizado=True`, `incompleto=True` E
`ativo=False`. Por isso, ao filtrar por 'incompleto', é preciso
`incluir_inativos=True` — sem isso, o cliente anonimizado é
excluído pelo filtro de 'ativo' antes sequer de chegar ao filtro
de 'incompleto', e o teste dá falso-positivo.

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

from testes.apoio_BD import BaseMySQLTest

import clientes
import responsaveis


def criar_cliente_mensal(**overrides):
    """Cria um cliente de teste válido e completo para o regime
    mensal. O regime mensal exige (validacoes.validar_cliente):
    nome, tipo_documento, numero_documento, nacionalidade,
    data_nascimento, validade_documento, nif, morada, estado_civil
    e telefone.

    O 'telefone' foi acrescentado em 16/09/2026 (decisão do aluno ao
    reestruturar os formulários por regime) — antes era opcional no
    mensal, agora é obrigatório.
    """
    campos = {
        "nome": "Ana Silva",
        "tipo_documento": "Cartão de Cidadão",
        "numero_documento": "12345678",
        "regime": "mensal",
        "nif": "501442600",
        "morada": "Rua do Porto, 12",
        "nacionalidade": "Portuguesa",
        "estado_civil": "Solteiro(a)",
        "telefone": "912345678",
        "data_nascimento": date(1990, 5, 20),
        "validade_documento": date(2030, 1, 1),
    }
    campos.update(overrides)
    return clientes.criar(**campos)


def criar_cliente_airbnb(**overrides):
    """Cria um cliente de teste válido e completo para o regime
    Airbnb. O regime Airbnb exige (validacoes.validar_cliente):
    nome, tipo_documento, numero_documento, nacionalidade,
    data_nascimento, validade_documento, pais_emissor_documento e
    pais_residencia.

    'pais_emissor_documento' e 'pais_residencia' são campos novos
    de 16/09/2026 (boletim de alojamento) — o valor por omissão é
    "Brasil", para distinguir dos clientes mensais e cobrir o caso
    típico de hóspede fora da UE neste regime.

    Não preenche 'nif' (o regime Airbnb não o exige — decisão de
    26/08 mantida), nem 'morada', 'estado_civil' ou 'telefone'
    (não fazem parte deste regime).
    """
    campos = {
        "nome": "John Smith",
        "tipo_documento": "Passaporte",
        "numero_documento": "X1234567",
        "regime": "airbnb",
        "nacionalidade": "Brasileira",
        "data_nascimento": date(1985, 3, 12),
        "validade_documento": date(2030, 1, 1),
        "pais_emissor_documento": "Brasil",
        "pais_residencia": "Brasil",
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
        """Um cliente novo (não anonimizado) nasce sempre com
        'incompleto' a False — o campo só é marcado True pela
        anonimização (RGPD). 'completo' aqui significa apenas
        'não anonimizado', não 'todos os campos opcionais
        preenchidos' (esse conceito foi descartado em 16/09/2026)."""
        cliente = criar_cliente_mensal(
            email="ana@exemplo.pt",
            telefone="912345678",
            morada="Rua do Porto, 12",
            nacionalidade="Portuguesa",
        )
        self.assertFalse(cliente["incompleto"])

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
        """Obrigatória nos dois regimes (decisão de 26/08, ponto 2)."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(validade_documento=None)

    def test_recusa_data_nascimento_em_falta(self):
        """Obrigatória nos dois regimes (decisão de 26/08, ponto 2)."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(data_nascimento=None)

    def test_recusa_morada_em_falta_no_mensal(self):
        """Obrigatória só no mensal (decisão de 26/08, ponto 2)."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(morada="")

    def test_recusa_estado_civil_em_falta_no_mensal(self):
        """Obrigatório só no mensal (decisão de 26/08, ponto 2)."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(estado_civil="")

    def test_recusa_telefone_em_falta_no_mensal(self):
        """Novo (16/09/2026): o telefone passou a obrigatório no
        regime mensal."""
        with self.assertRaises(ValueError):
            criar_cliente_mensal(telefone="")

    def test_recusa_nacionalidade_em_falta_no_airbnb(self):
        """Obrigatória no Airbnb (decisão de 26/08, ponto 2)."""
        with self.assertRaises(ValueError):
            criar_cliente_airbnb(nacionalidade="")

    def test_recusa_pais_emissor_em_falta_no_airbnb(self):
        """Campo novo (16/09/2026) — boletim de alojamento exige."""
        with self.assertRaises(ValueError):
            criar_cliente_airbnb(pais_emissor_documento="")

    def test_recusa_pais_residencia_em_falta_no_airbnb(self):
        """Campo novo (16/09/2026) — boletim de alojamento exige."""
        with self.assertRaises(ValueError):
            criar_cliente_airbnb(pais_residencia="")

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
        """Decisão de 26/08, item 5: o mesmo NIF não pode pertencer
        a dois clientes ativos."""
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
        """O filtro 'incompleto' devolve, hoje, só clientes
        anonimizados — 'incompleto' passou a ser a marca do RGPD
        (16/09/2026), não um estado de cadastro a meio.

        Nota: 'incluir_inativos=True' é obrigatório aqui, porque
        `clientes.anonimizar` também marca o cliente como inativo.
        Sem isso, o cliente anonimizado seria excluído pelo filtro
        de 'ativo' por omissão, e o teste dava falso-negativo.
        """
        criar_cliente_mensal()
        anonimizado = criar_cliente_airbnb()
        resp = responsaveis.criar("Responsável de teste")
        clientes.anonimizar(anonimizado["id"], resp["id"], date.today())

        resultado = clientes.listar(
            incompleto=True, incluir_inativos=True
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], anonimizado["id"])

    def test_filtra_por_incompleto_false(self):
        """O contrário do teste anterior: só devolve clientes
        não-anonimizados (o estado normal de um cliente novo).

        Usa 'incluir_inativos=True' pela mesma razão do teste
        anterior — para o filtro ser só sobre 'incompleto', e não
        sobre 'ativo' + 'incompleto'.
        """
        nao_anonimizado = criar_cliente_mensal()
        anonimizado = criar_cliente_airbnb()
        resp = responsaveis.criar("Responsável de teste")
        clientes.anonimizar(anonimizado["id"], resp["id"], date.today())

        resultado = clientes.listar(
            incompleto=False, incluir_inativos=True
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], nao_anonimizado["id"])

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
        atualizado = clientes.atualizar(cliente["id"], regime="mensal")
        self.assertEqual(atualizado["nome"], "Ana Silva")

    def test_altera_email(self):
        cliente = criar_cliente_mensal()
        atualizado = clientes.atualizar(
            cliente["id"], regime="mensal", email="nova@exemplo.pt"
        )
        self.assertEqual(atualizado["email"], "nova@exemplo.pt")

    def test_limpa_campo_opcional_com_vazio(self):
        cliente = criar_cliente_mensal(email="a@b.pt")
        atualizado = clientes.atualizar(
            cliente["id"], regime="mensal", email=""
        )
        self.assertEqual(atualizado["email"], "")

    def test_recusa_apagar_nome(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], regime="mensal", nome="")

    def test_recusa_apagar_numero_documento(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(
                cliente["id"], regime="mensal", numero_documento=""
            )

    def test_recusa_tipo_documento_fora_da_lista(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(
                cliente["id"],
                regime="mensal",
                tipo_documento="Carta de Condução",
            )

    def test_sem_regime_nif_nao_e_obrigatorio(self):
        """Sem regime explícito, o `atualizar` assume 'airbnb' — e o
        NIF não é obrigatório nesse regime. Este teste é a razão pela
        qual o regime OMISSO tem o comportamento oposto dos outros:
        confirma-o com um cliente Airbnb como base.
        """
        cliente = criar_cliente_airbnb()
        atualizado = clientes.atualizar(cliente["id"], nif="")
        self.assertEqual(atualizado["nif"], "")

    def test_sem_regime_nif_invalido_e_recusado(self):
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(
                cliente["id"], regime="mensal", nif="501442601"
            )

    def test_com_regime_mensal_nif_vazio_e_recusado(self):
        cliente = criar_cliente_airbnb()
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], regime="mensal")

    def test_com_regime_mensal_nif_novo_valido_passa(self):
        """Um cliente que foi criado no regime Airbnb pode passar a
        mensal, DESDE QUE traga os campos obrigatórios do mensal
        (morada, estado civil, telefone) — o regime mensal exige
        todos eles (decisão 26/08 + 16/09/2026). Sem os fornecer,
        o `validar_cliente` recusa antes mesmo de olhar para o NIF.
        """
        cliente = criar_cliente_airbnb()
        atualizado = clientes.atualizar(
            cliente["id"],
            regime="mensal",
            nif="501442600",
            morada="Rua X, 1",
            estado_civil="Solteiro(a)",
            telefone="912345678",
        )
        self.assertEqual(atualizado["nif"], "501442600")

    def test_recusa_atualizar_nif_para_valor_de_outro_cliente_ativo(self):
        """Decisão de 26/08, item 5."""
        criar_cliente_mensal(nif="501442600")
        cliente_2 = criar_cliente_mensal(
            numero_documento="99999999", nif="222222220"
        )
        with self.assertRaises(ValueError):
            clientes.atualizar(
                cliente_2["id"], regime="mensal", nif="501442600"
            )

    def test_atualizar_mantendo_o_proprio_nif_nao_e_recusado(self):
        cliente = criar_cliente_mensal(nif="501442600")
        atualizado = clientes.atualizar(
            cliente["id"], regime="mensal", nif="501442600"
        )
        self.assertEqual(atualizado["nif"], "501442600")

    def test_permite_atualizar_nif_para_valor_de_cliente_inativo(self):
        cliente_1 = criar_cliente_mensal(nif="501442600")
        clientes.desativar(cliente_1["id"])
        cliente_2 = criar_cliente_mensal(
            numero_documento="99999999", nif="222222220"
        )
        atualizado = clientes.atualizar(
            cliente_2["id"], regime="mensal", nif="501442600"
        )
        self.assertEqual(atualizado["nif"], "501442600")

    def test_recusa_apagar_morada_no_regime_mensal(self):
        """Tentar limpar a morada com regime='mensal' é recusado
        por validar_cliente."""
        cliente = criar_cliente_mensal()
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], regime="mensal", morada="")

    def test_recusa_apagar_nacionalidade_no_regime_airbnb(self):
        """Tentar limpar a nacionalidade com regime='airbnb' é
        recusado por validar_cliente."""
        cliente = criar_cliente_airbnb()
        with self.assertRaises(ValueError):
            clientes.atualizar(
                cliente["id"], regime="airbnb", nacionalidade=""
            )

    def test_altera_estado_civil(self):
        cliente = criar_cliente_mensal()
        atualizado = clientes.atualizar(
            cliente["id"], regime="mensal", estado_civil="Casado(a)"
        )
        self.assertEqual(atualizado["estado_civil"], "Casado(a)")

    def test_altera_data_nascimento(self):
        cliente = criar_cliente_mensal()
        atualizado = clientes.atualizar(
            cliente["id"],
            regime="mensal",
            data_nascimento=date(1990, 5, 20),
        )
        self.assertEqual(atualizado["data_nascimento"], date(1990, 5, 20))

    def test_recusa_atualizar_cliente_anonimizado(self):
        resp = responsaveis.criar("Responsável de teste")
        cliente = criar_cliente_mensal()
        clientes.anonimizar(cliente["id"], resp["id"], date.today())
        with self.assertRaises(ValueError):
            clientes.atualizar(cliente["id"], regime="mensal", nome="X")


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
        """Decisão de 26/08, item 6: fecha o 'gap' que deixava dois
        clientes ativos com o mesmo NIF."""
        cliente_1 = criar_cliente_mensal(nif="501442600")
        clientes.desativar(cliente_1["id"])
        criar_cliente_mensal(numero_documento="99999999", nif="501442600")
        with self.assertRaises(ValueError):
            clientes.reativar(cliente_1["id"])

    def test_permite_reativar_quando_nif_esta_livre(self):
        """A verificação nova não bloqueia o caso normal: NIF que
        continua livre."""
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