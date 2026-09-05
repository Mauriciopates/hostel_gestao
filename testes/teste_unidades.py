"""Testes de unidades.py — unidades, quartos e lugares.

MIGRAÇÃO MySQL (Fase 2): `unidades.py` já não recebe nem devolve a
estrutura `dados` em memória — fala diretamente com o MySQL através
do `repositorio.py`. Estes testes correm contra uma base de dados de
teste dedicada e isolada da base de dados real do aluno (ver
`apoio_bd.py`); cada teste começa com todas as tabelas vazias
(TRUNCATE) e com os contadores de identificadores reiniciados, tal
como antes cada teste começava com um dicionário `dados` novo.

NOTA sobre identidade: `procurar()`/`listar()` fazem sempre um SELECT
novo à base de dados — já não devolvem o MESMO objeto Python que
`criar()` devolveu. Por isso comparamos com `assertEqual` (valores
iguais), nunca com `assertIs` (mesmo objeto); e "está na base de
dados" verifica-se com `unidades.listar()` em vez de
`assertIn(x, dados["unidades"])`.

NOTA sobre `atualizar`/`desativar`/`reativar`/`marcar_manutencao`/
`desmarcar_manutencao` (e os equivalentes de quarto e lugar): estas
funções também fazem o seu próprio SELECT interno antes de escrever
— por isso já não mutam o dicionário devolvido por `criar()` que o
teste guardou. Os testes passam a verificar sempre o dicionário
DEVOLVIDO por estas funções, nunca a variável antiga (mesma correção
já aplicada em teste_propriedades.py).

NOTA sobre ocupações: `criar_ocupacao()`, o auxiliar de fixture deste
ficheiro, já não pode simplesmente acrescentar um dicionário a
`dados["ocupacoes"]` — as ocupações passam a ser criadas de verdade,
através de `contratos.py` (`criar_mensal`/`registar_airbnb`), que
aplica as suas próprias regras de negócio (capacidade da unidade,
sobreposição de datas Airbnb, um NIF não pode ter dois contratos
mensais ativos ao mesmo tempo). Por isso cada ocupação mensal criada
por este auxiliar usa sempre um cliente novo, com NIF distinto. Duas
situações que a versão antiga simulava não têm forma de nascer por
este caminho, porque `contratos.py` não as permite através da API
pública (ver TesteEstado, o par de testes "encerrada"/"até ao dia
anterior ao encerramento", e TesteQuartoPrivativoOcupado — caso da
ocupação Airbnb): nesses casos, a linha é inserida diretamente com
`repositorio.inserir_ocupacao`, ao nível dos dados, deliberadamente
por baixo de `contratos.py` — porque o que se testa aí é o próprio
código de `unidades.py` (a comparação de datas em `_estado_mensal`,
o filtro por `tipo` em `quarto_privativo_ocupado`), não as regras de
`contratos.py`.
"""

import itertools
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from apoio_BD import BaseMySQLTest

import clientes
import contratos
import propriedades
import repositorio
import unidades


def criar_propriedade():
    """Devolve uma propriedade nova, para servir de base às unidades
    de teste — substitui o antigo dados_base(), que construía o
    dicionário 'dados' à mão."""
    return propriedades.criar("Foz Velha", "Rua de Exemplo, 1")


def criar_unidade_mensal(propriedade_id):
    """Cria uma unidade mensal de teste e devolve o registo."""
    return unidades.criar(
        propriedade_id,
        "Unidade Mensal Teste",
        "mensal",
        Decimal("250.00"),
        Decimal("250.00"),
        Decimal("20.00"),
    )


def criar_unidade_airbnb(propriedade_id):
    """Cria uma unidade Airbnb de teste e devolve o registo."""
    return unidades.criar(
        propriedade_id,
        "Unidade Airbnb Teste",
        "airbnb",
        Decimal("45.00"),
        Decimal("90.00"),
        Decimal("20.00"),
    )


def dar_lugares(unidade_id, capacidades):
    """Cria um quarto com um lugar por capacidade indicada, devolve
    a soma — a capacidade total esperada da unidade.
    """
    quarto = unidades.criar_quarto(unidade_id, "Quarto de teste")
    for capacidade in capacidades:
        unidades.criar_lugar(
            quarto["id"], f"Lugar {capacidade}", capacidade=capacidade
        )
    return sum(capacidades)


# --- Clientes de apoio, para as ocupações -----------------------------

_contador_nif = itertools.count(1)


def _gerar_nif():
    """Gera um NIF fiscalmente válido (dígito de controlo calculado
    pela mesma fórmula de validacoes.nif_valido), diferente a cada
    chamada — contratos.criar_mensal recusa um NIF que já tenha
    contrato mensal ativo, por isso cada novo contrato mensal de
    teste precisa de um cliente com NIF distinto.
    """
    indice = next(_contador_nif)
    base = f"{10000000 + indice:08d}"[-8:]
    soma = sum(int(base[i]) * (9 - i) for i in range(8))
    resto = soma % 11
    controlo = 0 if resto < 2 else 11 - resto
    return base + str(controlo)


def criar_cliente_mensal():
    """Cliente completo e válido para o regime mensal — nif, morada,
    estado civil, data de nascimento e validade do documento são
    todos obrigatórios (validacoes.validar_cliente, regime mensal).
    Usa "Outro" como tipo de documento para não depender da forma
    exata do texto "Cartão (de) Cidadão", que difere entre
    validacoes.TIPOS_DOCUMENTO e o ENUM da tabela `clientes` — fora
    do âmbito desta migração.
    """
    return clientes.criar(
        "Cliente Mensal Teste",
        "Outro",
        "DOC-MENSAL",
        "mensal",
        nif=_gerar_nif(),
        morada="Rua de Teste, 1",
        estado_civil="Solteiro(a)",
        data_nascimento=date(1990, 1, 1),
        validade_documento=date(2035, 1, 1),
    )


def criar_cliente_airbnb():
    """Cliente completo e válido para o regime Airbnb —
    nacionalidade, data de nascimento e validade do documento são
    obrigatórios (validacoes.validar_cliente, regime airbnb)."""
    return clientes.criar(
        "Cliente Airbnb Teste",
        "Outro",
        "DOC-AIRBNB",
        "airbnb",
        nacionalidade="Portuguesa",
        data_nascimento=date(1990, 1, 1),
        validade_documento=date(2035, 1, 1),
    )


# --- Ocupações de apoio -------------------------------------------------


def criar_ocupacao(unidade_id, tipo, data_inicio, data_fim=None, ativo=True):
    """Cria uma ocupação real: contrato mensal via
    contratos.criar_mensal ou reserva Airbnb via
    contratos.registar_airbnb — já não é possível simular uma
    ocupação só acrescentando um dicionário a uma lista em memória,
    porque contratos.py aplica as suas próprias regras de negócio
    (capacidade da unidade, sobreposição de datas, NIF único por
    contrato mensal ativo).

    'ativo=False' cria a ocupação normalmente e fecha-a logo a
    seguir (encerrar_mensal / cancelar_airbnb) — é assim que uma
    ocupação inativa nasce na base de dados real; a data de fim
    usada para fechar um contrato mensal não é significativa para
    quem chama com ativo=False (só interessa que fique inativa), por
    isso usa-se 'data_fim' se vier indicada, senão um dia a seguir
    ao início.
    """
    if tipo == "mensal":
        cliente = criar_cliente_mensal()
        ocupacao, _ = contratos.criar_mensal(
            unidade_id,
            cliente["id"],
            data_inicio,
            Decimal("250.00"),
            Decimal("250.00"),
        )

        if not ativo:
            fim = data_fim if data_fim is not None else data_inicio + timedelta(days=1)
            ocupacao, _ = contratos.encerrar_mensal(ocupacao["id"], fim)

        return ocupacao

    cliente = criar_cliente_airbnb()
    unidade = unidades.procurar(unidade_id)
    preco = contratos.calcular_preco_airbnb(unidade, data_inicio, data_fim)
    ocupacao, _ = contratos.registar_airbnb(
        unidade_id, cliente["id"], data_inicio, data_fim, preco
    )

    if not ativo:
        ocupacao, _ = contratos.cancelar_airbnb(ocupacao["id"])

    return ocupacao


def criar_ocupacao_mensal_com_fim_marcado(unidade_id, data_inicio, data_fim):
    """Insere diretamente na tabela `ocupacoes` um contrato mensal
    com data de fim marcada mas AINDA ativo — um estado que
    contratos.encerrar_mensal já não permite produzir (encerrar
    desativa sempre o contrato de imediato, os dois campos mudam
    juntos), mas que a comparação de datas em unidades._estado_mensal
    continua preparada para tratar (código defensivo, sem forma de
    lá chegar pela API pública). Testa esse ramo diretamente ao
    nível do repositório, por baixo de contratos.py — só a tabela
    base é preciso preencher, porque _estado_mensal só lê 'ocupacoes',
    nunca 'ocupacoes_mensal'.
    """
    cliente = criar_cliente_mensal()
    ocupacao = {
        "id": repositorio.proximo_id("OCU"),
        "unidade_id": unidade_id,
        "cliente_id": cliente["id"],
        "tipo": "mensal",
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "lugar_id": "",
        "aviso_documento": False,
        "ativo": True,
    }
    repositorio.inserir_ocupacao(ocupacao)
    return ocupacao


class TesteCriar(BaseMySQLTest):

    def test_cria_unidade_mensal_valida(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        self.assertEqual(unidade["tipo"], "mensal")
        self.assertEqual(unidade["preco_base"], Decimal("250.00"))
        self.assertFalse(unidade["em_manutencao"])
        self.assertTrue(unidade["ativo"])
        self.assertIn(unidade["id"], [u["id"] for u in unidades.listar()])

    def test_cria_unidade_airbnb_valida(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        self.assertEqual(unidade["tipo"], "airbnb")

    def test_recusa_propriedade_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.criar(
                "PRO-999", "Unidade Teste", "mensal",
                Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
            )

    def test_recusa_tipo_desconhecido(self):
        propriedade_id = criar_propriedade()["id"]
        with self.assertRaises(ValueError):
            unidades.criar(
                propriedade_id, "Unidade Teste", "semanal",
                Decimal("250.00"), Decimal("250.00"), Decimal("20.00"),
            )

    def test_recusa_preco_em_falta(self):
        propriedade_id = criar_propriedade()["id"]
        with self.assertRaises(ValueError):
            unidades.criar(
                propriedade_id, "Unidade Teste", "mensal",
                None, Decimal("250.00"), Decimal("20.00"),
            )

    def test_recusa_preco_nao_decimal(self):
        propriedade_id = criar_propriedade()["id"]
        with self.assertRaises(ValueError):
            unidades.criar(
                propriedade_id, "Unidade Teste", "mensal",
                250.00, Decimal("250.00"), Decimal("20.00"),
            )

    def test_recusa_preco_negativo(self):
        propriedade_id = criar_propriedade()["id"]
        with self.assertRaises(ValueError):
            unidades.criar(
                propriedade_id, "Unidade Teste", "mensal",
                Decimal("-1"), Decimal("250.00"), Decimal("20.00"),
            )

    def test_epoca_alta_ativa_aceita_true(self):
        propriedade_id = criar_propriedade()["id"]
        unidade = unidades.criar(
            propriedade_id, "Unidade Teste", "airbnb",
            Decimal("45.00"), Decimal("90.00"), Decimal("20.00"),
            epoca_alta_ativa=True,
        )
        self.assertTrue(unidade["epoca_alta_ativa"])


class TesteProcurar(BaseMySQLTest):

    def test_encontra_unidade_existente(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        encontrada = unidades.procurar(unidade["id"])
        self.assertEqual(encontrada, unidade)

    def test_devolve_none_para_id_inexistente(self):
        self.assertIsNone(unidades.procurar("UNI-999"))

    def test_encontra_unidade_inativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        unidades.desativar(unidade["id"])
        self.assertIsNotNone(unidades.procurar(unidade["id"]))


class TesteListar(BaseMySQLTest):

    def test_lista_vazia_sem_unidades(self):
        self.assertEqual(unidades.listar(), [])

    def test_lista_so_ativas_por_omissao(self):
        propriedade = criar_propriedade()
        ativa = criar_unidade_mensal(propriedade["id"])
        inativa = criar_unidade_airbnb(propriedade["id"])
        unidades.desativar(inativa["id"])
        resultado = unidades.listar()
        self.assertEqual(resultado, [ativa])

    def test_lista_incluir_inativas(self):
        propriedade = criar_propriedade()
        criar_unidade_mensal(propriedade["id"])
        inativa = criar_unidade_airbnb(propriedade["id"])
        unidades.desativar(inativa["id"])
        resultado = unidades.listar(incluir_inativas=True)
        self.assertEqual(len(resultado), 2)

    def test_filtra_por_propriedade(self):
        propriedade = criar_propriedade()
        outra_propriedade = propriedades.criar("Aldoar")
        criar_unidade_mensal(propriedade["id"])
        da_segunda = criar_unidade_mensal(outra_propriedade["id"])
        resultado = unidades.listar(propriedade_id=outra_propriedade["id"])
        self.assertEqual(resultado, [da_segunda])

    def test_filtra_por_tipo(self):
        propriedade = criar_propriedade()
        criar_unidade_mensal(propriedade["id"])
        airbnb = criar_unidade_airbnb(propriedade["id"])
        resultado = unidades.listar(tipo="airbnb")
        self.assertEqual(resultado, [airbnb])

    def test_devolve_lista_nova(self):
        propriedade = criar_propriedade()
        criar_unidade_mensal(propriedade["id"])
        resultado = unidades.listar()
        resultado.append("intruso")
        self.assertEqual(len(unidades.listar()), 1)


class TesteAtualizar(BaseMySQLTest):

    def test_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.atualizar("UNI-999", preco_base=Decimal("1"))

    def test_none_nao_altera(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        preco_original = unidade["preco_base"]
        atualizado = unidades.atualizar(unidade["id"])
        self.assertEqual(atualizado["preco_base"], preco_original)

    def test_altera_preco_base(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        atualizado = unidades.atualizar(unidade["id"], preco_base=Decimal("300.00"))
        self.assertEqual(atualizado["preco_base"], Decimal("300.00"))

    def test_altera_epoca_alta_ativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        atualizado = unidades.atualizar(unidade["id"], epoca_alta_ativa=True)
        self.assertTrue(atualizado["epoca_alta_ativa"])

    def test_recusa_preco_nao_decimal(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        with self.assertRaises(ValueError):
            unidades.atualizar(unidade["id"], preco_base=300.0)

    def test_recusa_preco_negativo(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        with self.assertRaises(ValueError):
            unidades.atualizar(
                unidade["id"], multa_check_in_tardio=Decimal("-5"),
            )


class TesteDesativarReativar(BaseMySQLTest):

    def test_desativa_unidade_ativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        resultado = unidades.desativar(unidade["id"])
        self.assertFalse(resultado["ativo"])

    def test_recusa_desativar_duas_vezes(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        unidades.desativar(unidade["id"])
        with self.assertRaises(ValueError):
            unidades.desativar(unidade["id"])

    def test_recusa_desativar_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.desativar("UNI-999")

    def test_reativa_unidade_inativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        unidades.desativar(unidade["id"])
        resultado = unidades.reativar(unidade["id"])
        self.assertTrue(resultado["ativo"])

    def test_recusa_reativar_ja_ativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        with self.assertRaises(ValueError):
            unidades.reativar(unidade["id"])

    def test_recusa_reativar_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.reativar("UNI-999")

    def test_recusa_desativar_com_ocupacao_ativa_sem_forcar(self):
        """Novo (decisão de 27/08, item 9): sem forcar=True, recusa
        desativar se existir alguma ocupação ativa dependente."""
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1])
        criar_ocupacao(unidade["id"], "mensal", date(2026, 9, 1))

        with self.assertRaises(ValueError):
            unidades.desativar(unidade["id"])

    def test_desativar_com_forcar_ignora_ocupacoes_ativas(self):
        """Com forcar=True, desativa mesmo com ocupações ativas
        dependentes — decisão consciente de quem chama."""
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1])
        criar_ocupacao(unidade["id"], "mensal", date(2026, 9, 1))

        resultado = unidades.desativar(unidade["id"], forcar=True)

        self.assertFalse(resultado["ativo"])

    def test_desativar_ignora_ocupacao_ja_inativa(self):
        """Uma ocupação já inativa não conta como dependência ativa
        — não exige forcar."""
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1])
        criar_ocupacao(unidade["id"], "mensal", date(2026, 9, 1), ativo=False)

        resultado = unidades.desativar(unidade["id"])

        self.assertFalse(resultado["ativo"])


class TesteManutencao(BaseMySQLTest):

    def test_marca_manutencao(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        resultado = unidades.marcar_manutencao(unidade["id"])
        self.assertTrue(resultado["em_manutencao"])

    def test_recusa_marcar_duas_vezes(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        unidades.marcar_manutencao(unidade["id"])
        with self.assertRaises(ValueError):
            unidades.marcar_manutencao(unidade["id"])

    def test_desmarca_manutencao(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        unidades.marcar_manutencao(unidade["id"])
        resultado = unidades.desmarcar_manutencao(unidade["id"])
        self.assertFalse(resultado["em_manutencao"])

    def test_recusa_desmarcar_sem_estar_em_manutencao(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        with self.assertRaises(ValueError):
            unidades.desmarcar_manutencao(unidade["id"])

    def test_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.marcar_manutencao("UNI-999")
        with self.assertRaises(ValueError):
            unidades.desmarcar_manutencao("UNI-999")


class TesteCriarQuarto(BaseMySQLTest):

    def test_cria_quarto_valido(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Quarto 1")
        self.assertEqual(quarto["unidade_id"], unidade["id"])
        self.assertFalse(quarto["privativo"])
        self.assertFalse(quarto["limpeza_incluida"])
        self.assertTrue(quarto["ativo"])
        self.assertIn(
            quarto["id"], [q["id"] for q in unidades.listar_quartos(unidade_id=unidade["id"])]
        )

    def test_cria_quarto_privativo_com_limpeza(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(
            unidade["id"], "Suite",
            privativo=True, limpeza_incluida=True,
        )
        self.assertTrue(quarto["privativo"])
        self.assertTrue(quarto["limpeza_incluida"])

    def test_recusa_unidade_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.criar_quarto("UNI-999", "Quarto 1")

    def test_recusa_nome_vazio(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        with self.assertRaises(ValueError):
            unidades.criar_quarto(unidade["id"], "   ")

    def test_remove_espacos_do_nome(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "  Quarto 1  ")
        self.assertEqual(quarto["nome"], "Quarto 1")


class TesteProcurarQuarto(BaseMySQLTest):

    def test_encontra_quarto_existente(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Quarto 1")
        encontrado = unidades.procurar_quarto(quarto["id"])
        self.assertEqual(encontrado, quarto)

    def test_devolve_none_para_id_inexistente(self):
        self.assertIsNone(unidades.procurar_quarto("QRT-999"))


class TesteListarQuartos(BaseMySQLTest):

    def test_filtra_por_unidade(self):
        propriedade = criar_propriedade()
        unidade_a = criar_unidade_mensal(propriedade["id"])
        unidade_b = criar_unidade_airbnb(propriedade["id"])
        quarto_a = unidades.criar_quarto(unidade_a["id"], "A1")
        unidades.criar_quarto(unidade_b["id"], "B1")
        resultado = unidades.listar_quartos(unidade_id=unidade_a["id"])
        self.assertEqual(resultado, [quarto_a])

    def test_lista_so_ativos_por_omissao(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        ativo = unidades.criar_quarto(unidade["id"], "Q1")
        inativo = unidades.criar_quarto(unidade["id"], "Q2")
        unidades.desativar_quarto(inativo["id"])
        resultado = unidades.listar_quartos(unidade_id=unidade["id"])
        self.assertEqual(resultado, [ativo])


class TesteAtualizarQuarto(BaseMySQLTest):

    def test_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.atualizar_quarto("QRT-999", nome="X")

    def test_altera_nome(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        atualizado = unidades.atualizar_quarto(quarto["id"], nome="Novo nome")
        self.assertEqual(atualizado["nome"], "Novo nome")

    def test_recusa_nome_vazio(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.atualizar_quarto(quarto["id"], nome="   ")

    def test_altera_privativo_e_limpeza_independentes(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        atualizado = unidades.atualizar_quarto(quarto["id"], privativo=True)
        self.assertTrue(atualizado["privativo"])
        self.assertFalse(atualizado["limpeza_incluida"])

    def test_none_nao_altera(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1", privativo=True)
        atualizado = unidades.atualizar_quarto(quarto["id"])
        self.assertEqual(atualizado["nome"], "Q1")
        self.assertTrue(atualizado["privativo"])


class TesteDesativarReativarQuarto(BaseMySQLTest):

    def test_desativa_e_reativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        desativado = unidades.desativar_quarto(quarto["id"])
        self.assertFalse(desativado["ativo"])
        reativado = unidades.reativar_quarto(quarto["id"])
        self.assertTrue(reativado["ativo"])

    def test_recusa_desativar_duas_vezes(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        unidades.desativar_quarto(quarto["id"])
        with self.assertRaises(ValueError):
            unidades.desativar_quarto(quarto["id"])

    def test_recusa_reativar_ja_ativo(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.reativar_quarto(quarto["id"])

    def test_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.desativar_quarto("QRT-999")
        with self.assertRaises(ValueError):
            unidades.reativar_quarto("QRT-999")


class TesteCriarLugar(BaseMySQLTest):

    def test_cria_lugar_valido(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        self.assertEqual(lugar["quarto_id"], quarto["id"])
        self.assertEqual(lugar["capacidade"], 1)
        self.assertTrue(lugar["ativo"])
        self.assertIn(
            lugar["id"], [l["id"] for l in unidades.listar_lugares(quarto_id=quarto["id"])]
        )

    def test_cria_lugar_capacidade_dois(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama casal", capacidade=2)
        self.assertEqual(lugar["capacidade"], 2)

    def test_recusa_quarto_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.criar_lugar("QRT-999", "Cama 1")

    def test_recusa_nome_vazio(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.criar_lugar(quarto["id"], "  ")

    def test_recusa_capacidade_invalida(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.criar_lugar(quarto["id"], "Cama 1", capacidade=0)

    def test_recusa_capacidade_none(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        with self.assertRaises(ValueError):
            unidades.criar_lugar(
                quarto["id"], "Cama 1", capacidade=None  # type: ignore
            )


class TesteProcurarLugar(BaseMySQLTest):

    def test_encontra_lugar_existente(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        encontrado = unidades.procurar_lugar(lugar["id"])
        self.assertEqual(encontrado, lugar)

    def test_devolve_none_para_id_inexistente(self):
        self.assertIsNone(unidades.procurar_lugar("LUG-999"))


class TesteListarLugares(BaseMySQLTest):

    def test_filtra_por_quarto(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto_a = unidades.criar_quarto(unidade["id"], "A")
        quarto_b = unidades.criar_quarto(unidade["id"], "B")
        lugar_a = unidades.criar_lugar(quarto_a["id"], "Cama 1")
        unidades.criar_lugar(quarto_b["id"], "Cama 1")
        resultado = unidades.listar_lugares(quarto_id=quarto_a["id"])
        self.assertEqual(resultado, [lugar_a])

    def test_lista_so_ativos_por_omissao(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        ativo = unidades.criar_lugar(quarto["id"], "Cama 1")
        inativo = unidades.criar_lugar(quarto["id"], "Cama 2")
        unidades.desativar_lugar(inativo["id"])
        resultado = unidades.listar_lugares(quarto_id=quarto["id"])
        self.assertEqual(resultado, [ativo])


class TesteAtualizarLugar(BaseMySQLTest):

    def test_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.atualizar_lugar("LUG-999", nome="X")

    def test_altera_nome(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        atualizado = unidades.atualizar_lugar(lugar["id"], nome="Cama nova")
        self.assertEqual(atualizado["nome"], "Cama nova")

    def test_recusa_nome_vazio(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        with self.assertRaises(ValueError):
            unidades.atualizar_lugar(lugar["id"], nome="  ")

    def test_altera_capacidade(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        atualizado = unidades.atualizar_lugar(lugar["id"], capacidade=2)
        self.assertEqual(atualizado["capacidade"], 2)

    def test_recusa_capacidade_invalida(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        with self.assertRaises(ValueError):
            unidades.atualizar_lugar(lugar["id"], capacidade=0)

    def test_none_nao_altera(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        atualizado = unidades.atualizar_lugar(lugar["id"])
        self.assertEqual(atualizado["nome"], "Cama 1")
        self.assertEqual(atualizado["capacidade"], 1)


class TesteDesativarReativarLugar(BaseMySQLTest):

    def test_desativa_e_reativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        desativado = unidades.desativar_lugar(lugar["id"])
        self.assertFalse(desativado["ativo"])
        reativado = unidades.reativar_lugar(lugar["id"])
        self.assertTrue(reativado["ativo"])

    def test_recusa_desativar_duas_vezes(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        unidades.desativar_lugar(lugar["id"])
        with self.assertRaises(ValueError):
            unidades.desativar_lugar(lugar["id"])

    def test_recusa_reativar_ja_ativo(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        quarto = unidades.criar_quarto(unidade["id"], "Q1")
        lugar = unidades.criar_lugar(quarto["id"], "Cama 1")
        with self.assertRaises(ValueError):
            unidades.reativar_lugar(lugar["id"])

    def test_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.desativar_lugar("LUG-999")
        with self.assertRaises(ValueError):
            unidades.reativar_lugar("LUG-999")


class TesteEstado(BaseMySQLTest):

    def test_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            unidades.estado("UNI-999", date(2026, 9, 5))

    # --- Mensal: proporção ---

    def test_mensal_sem_ocupacoes_e_zero_sobre_capacidade(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1, 1])
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "0/2")

    def test_mensal_proporcao_com_ocupacao_ativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1, 1])
        criar_ocupacao(unidade["id"], "mensal", date(2026, 9, 1))
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "1/2")

    def test_mensal_ocupacao_futura_nao_conta(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1, 1])
        criar_ocupacao(unidade["id"], "mensal", date(2026, 9, 10))
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "0/2")

    def test_mensal_ocupacao_encerrada_nao_conta(self):
        """Ocupação inserida diretamente com a data de fim marcada
        (ver criar_ocupacao_mensal_com_fim_marcado) — o mesmo
        resultado se obteria criando o contrato e encerrando-o de
        verdade, aqui, porque a data pedida (15) já é posterior à
        data de fim (10)."""
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1, 1])
        criar_ocupacao_mensal_com_fim_marcado(
            unidade["id"], date(2026, 9, 1), date(2026, 9, 10),
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 15))
        self.assertEqual(resultado, "0/2")

    def test_mensal_ocupacao_ativa_ate_ao_dia_anterior_ao_encerramento(self):
        """contratos.encerrar_mensal desativa o contrato de imediato
        — já não há forma, pela API pública, de um contrato ficar
        com data de fim marcada e continuar ativo até lá chegar; por
        isso a ocupação é inserida diretamente (ver
        criar_ocupacao_mensal_com_fim_marcado), para continuar a
        testar a comparação de datas de unidades._estado_mensal."""
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1, 1])
        criar_ocupacao_mensal_com_fim_marcado(
            unidade["id"], date(2026, 9, 1), date(2026, 9, 10),
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 9))
        self.assertEqual(resultado, "1/2")

    def test_mensal_ocupacao_inativa_nao_conta(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1, 1])
        criar_ocupacao(unidade["id"], "mensal", date(2026, 9, 1), ativo=False)
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "0/2")

    def test_mensal_nao_conta_ocupacoes_de_outra_unidade(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        outra = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1, 1])
        dar_lugares(outra["id"], [1])
        criar_ocupacao(outra["id"], "mensal", date(2026, 9, 1))
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "0/2")

    # --- Airbnb: Livre / Ocupado / Reservado ---

    def test_airbnb_livre_sem_ocupacoes(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "Livre")

    def test_airbnb_ocupado_na_noite_de_entrada(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 10))
        self.assertEqual(resultado, "Ocupado")

    def test_airbnb_ocupado_a_meio_da_estadia(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 12))
        self.assertEqual(resultado, "Ocupado")

    def test_airbnb_ocupado_na_ultima_noite(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 14))
        self.assertEqual(resultado, "Ocupado")

    def test_airbnb_livre_no_dia_de_saida(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 15))
        self.assertEqual(resultado, "Livre")

    def test_airbnb_reservado_ocupacao_futura(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "Reservado")

    def test_airbnb_entrada_e_saida_no_mesmo_dia_nao_e_conflito(self):
        """Réplica, ao nível do estado(), do caso já coberto na
        validação de sobreposição: a saída de uma reserva no mesmo
        dia da entrada da seguinte não é conflito — a noite desse
        dia fica com a segunda reserva.
        """
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 15), data_fim=date(2026, 9, 18),
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 15))
        self.assertEqual(resultado, "Ocupado")

    def test_airbnb_reserva_cancelada_nao_conta(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
            ativo=False,
        )
        resultado = unidades.estado(unidade["id"], date(2026, 9, 12))
        self.assertEqual(resultado, "Livre")

    # --- Manutenção sobrepõe-se a tudo ---

    def test_manutencao_sobrepoe_se_sem_ocupacoes(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        unidades.marcar_manutencao(unidade["id"])
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "Em manutenção")

    def test_manutencao_sobrepoe_se_com_ocupacao_ativa(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_airbnb(propriedade["id"])
        criar_ocupacao(
            unidade["id"], "airbnb",
            date(2026, 9, 10), data_fim=date(2026, 9, 15),
        )
        unidades.marcar_manutencao(unidade["id"])
        resultado = unidades.estado(unidade["id"], date(2026, 9, 12))
        self.assertEqual(resultado, "Em manutenção")

    def test_manutencao_sobrepoe_se_no_mensal(self):
        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        dar_lugares(unidade["id"], [1, 1])
        criar_ocupacao(unidade["id"], "mensal", date(2026, 9, 1))
        unidades.marcar_manutencao(unidade["id"])
        resultado = unidades.estado(unidade["id"], date(2026, 9, 5))
        self.assertEqual(resultado, "Em manutenção")


class TesteQuartoPrivativoOcupado(BaseMySQLTest):
    """Segundo ocupante em quarto privativo (decisão 17)."""

    def setUp(self):
        super().setUp()

        propriedade = criar_propriedade()
        unidade = criar_unidade_mensal(propriedade["id"])
        self.unidade_id = unidade["id"]

        privativo = unidades.criar_quarto(
            unidade["id"], "Quarto privativo",
            privativo=True, limpeza_incluida=True,
        )
        partilhado = unidades.criar_quarto(
            unidade["id"], "Quarto partilhado",
            privativo=False, limpeza_incluida=True,
        )

        self.lugar_privativo_a = unidades.criar_lugar(privativo["id"], "Cama A")["id"]
        self.lugar_privativo_b = unidades.criar_lugar(privativo["id"], "Cama B")["id"]
        self.lugar_partilhado_a = unidades.criar_lugar(
            partilhado["id"], "Beliche cima"
        )["id"]
        self.lugar_partilhado_b = unidades.criar_lugar(
            partilhado["id"], "Beliche baixo"
        )["id"]

    def _ocupar(self, lugar_id, tipo="mensal", ativo=True):
        """Cria uma ocupação real no lugar indicado.

        Um contrato mensal passa por contratos.criar_mensal, com um
        cliente novo (NIF distinto) a cada chamada — um NIF só pode
        ter um contrato mensal ativo de cada vez; 'ativo=False'
        encerra o contrato logo a seguir.

        contratos.registar_airbnb não tem parâmetro de lugar — uma
        reserva Airbnb nunca fica associada a um lugar concreto no
        modelo atual. Para continuar a confirmar que
        quarto_privativo_ocupado ignora ocupações Airbnb mesmo que
        estejam associadas ao mesmo lugar físico (a regra é só dos
        contratos mensais), insere-se aqui a linha diretamente no
        repositório — por baixo de contratos.py, deliberadamente,
        porque o que se testa é o filtro por 'tipo' dentro de
        unidades.quarto_privativo_ocupado, não uma regra de
        negócio de contratos.py.
        """
        if tipo == "mensal":
            cliente = criar_cliente_mensal()
            ocupacao, _ = contratos.criar_mensal(
                self.unidade_id, cliente["id"], date(2026, 9, 1),
                Decimal("250.00"), Decimal("250.00"), lugar_id=lugar_id,
            )
            if not ativo:
                contratos.encerrar_mensal(ocupacao["id"], date(2026, 9, 10))
            return

        cliente = criar_cliente_airbnb()
        ocupacao = {
            "id": repositorio.proximo_id("OCU"),
            "unidade_id": self.unidade_id,
            "cliente_id": cliente["id"],
            "tipo": tipo,
            "data_inicio": date(2026, 9, 1),
            "data_fim": None,
            "lugar_id": lugar_id,
            "aviso_documento": False,
            "ativo": ativo,
        }
        repositorio.inserir_ocupacao(ocupacao)

    def test_quarto_privativo_vazio_nao_alerta(self):
        self.assertFalse(
            unidades.quarto_privativo_ocupado(self.lugar_privativo_a)
        )

    def test_mesmo_lugar_ja_ocupado_alerta(self):
        self._ocupar(self.lugar_privativo_a)
        self.assertTrue(
            unidades.quarto_privativo_ocupado(self.lugar_privativo_a)
        )

    def test_outro_lugar_do_mesmo_quarto_alerta(self):
        """O privativo é regra do quarto, não do lugar isolado."""
        self._ocupar(self.lugar_privativo_a)
        self.assertTrue(
            unidades.quarto_privativo_ocupado(self.lugar_privativo_b)
        )

    def test_quarto_partilhado_nunca_alerta(self):
        self._ocupar(self.lugar_partilhado_a)
        self.assertFalse(
            unidades.quarto_privativo_ocupado(self.lugar_partilhado_b)
        )

    def test_ocupacao_inativa_nao_alerta(self):
        """Um contrato encerrado liberta o quarto."""
        self._ocupar(self.lugar_privativo_a, ativo=False)
        self.assertFalse(
            unidades.quarto_privativo_ocupado(self.lugar_privativo_b)
        )

    def test_ocupacao_airbnb_nao_alerta(self):
        """A regra é dos contratos mensais, por pessoa."""
        self._ocupar(self.lugar_privativo_a, tipo="airbnb")
        self.assertFalse(
            unidades.quarto_privativo_ocupado(self.lugar_privativo_b)
        )

    def test_lugar_inexistente_devolve_falso(self):
        """Não é erro: quem valida a existência é contratos.py."""
        self.assertFalse(unidades.quarto_privativo_ocupado("LUG-999"))

    def test_lugar_inativo_do_quarto_conta_na_verificacao(self):
        """Desativar o lugar não apaga a ocupação que lá está."""
        unidades.desativar_lugar(self.lugar_privativo_a)
        self._ocupar(self.lugar_privativo_a)
        self.assertTrue(
            unidades.quarto_privativo_ocupado(self.lugar_privativo_b)
        )

    def test_ocupacao_sem_lugar_nao_alerta(self):
        """Contrato de apartamento inteiro, sem lugar atribuído."""
        self._ocupar("")
        self.assertFalse(
            unidades.quarto_privativo_ocupado(self.lugar_privativo_a)
        )


if __name__ == "__main__":
    unittest.main()