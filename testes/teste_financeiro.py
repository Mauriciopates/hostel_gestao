"""Testes de `financeiro.py` — motor puro de leitura.

`financeiro.py` NÃO escreve na base de dados. Lê o que já existe,
soma, e devolve números. Estes testes correm contra a base de dados
de teste dedicada (ver `apoio_BD.py`) — NUNCA contra a base de dados
real.

ESTRUTURA DO FICHEIRO — quatro classes:

  1. `TesteHelpersPuros`   — unittest.TestCase puro, SEM MySQL.
     Cobre os helpers de cálculo de datas e de rateio do Bloco 1
     (`_validar_periodo`, `_meses_do_periodo`, `_primeiro_dia_do_mes`,
     `_ultimo_dia_do_mes`, `_mes_de`, `_mes_tocado_pela_ocupacao`,
     `_meses_de_vigencia_no_periodo`, `_noites_totais`,
     `_noites_no_periodo`, `_ratear`). É aqui que vivem os casos de
     fronteira (mês bissexto, ano bissexto, fronteira de mês,
     período de um dia, rateio com total zero).

  2. `TesteReceita`        — BaseMySQLTest. `receita_por_unidade` e
     `receita_por_propriedade`.

  3. `TesteDespesasCogs`   — BaseMySQLTest. `despesas_por_categoria`
     e `cogs_por_produto`.

  4. `TesteResultado`      — BaseMySQLTest. `resultado` agregado.

NOTA sobre helpers privados testados diretamente: `_meses_do_periodo`,
`_listar_ocupacoes_do_periodo`, `_meses_de_vigencia_no_periodo`,
`_noites_totais`, `_noites_no_periodo` e `_ratear` são privados pela
convenção do underscore, mas o `gui_relatorios.py` já os chama
diretamente (ver `_receita_mensal_do_periodo` e `_receita_airbnb_do_periodo`
nesse ficheiro). São privados na convenção, públicos de facto dentro
do projeto. Testá-los diretamente garante os cálculos de datas — a
parte mais frágil — sem depender de os exercitar todos via as funções
públicas. Mesma convenção já usada em `teste_contratos.py`
(`_sobrepoe`) e `teste_unidades.py` (`_contagem_mensal`).

NOTA sobre o `data_fim` EXCLUSIVO: `financeiro._validar_periodo` é
explícita — o `data_fim` do motor é exclusivo ("um período com o
mesmo dia de início e fim não contém nenhum"). Os testes das funções
públicas criam ocupações com esta convenção em mente, para que as
asserções fiquem legíveis.

CORREÇÃO 22/09/2026 (PASSO 9): o `_meses_do_periodo` foi corrigido
em produção (ver `financeiro.py`) — um `data_fim` que calhasse no
dia 1 de um mês estava a acrescentar esse mês à lista, mesmo que o
período não o cobrisse. Os testes `test_meses_do_periodo_atravessa_
ano` e `test_meses_do_periodo_fim_a_meio_do_mes_inclui_esse_mes`
blindam a convenção nos dois sentidos.

NOTA sobre a fronteira de cêntimo: `_ratear` arredonda por linha, com
`Decimal.quantize(Decimal("0.01"))`. Uma soma de parcelas rateadas
pode ficar 1 cêntimo acima ou abaixo de um cálculo em precisão
infinita — é aceite, mesma convenção de
`despesas.dividir_despesa_por_propriedade` e
`teste_despesas.teste_dividir_valor_nao_divisivel_arredonda_simples`.
Os testes de agregação não forçam igualdades exatas ao cêntimo onde
o rateio está envolvido; comparam contra o valor calculado com o
mesmo arredondamento.
"""

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest

import clientes
import contratos
import despesas
import estoque
import financeiro
import propriedades
import responsaveis
import unidades

# =====================================================================
# Helpers de fixture — só usados pelos testes com MySQL
# =====================================================================


def _criar_master(nome="Master de Teste"):
    """Autor para as operações que exigem autoria (despesas,
    categorias, fornecedores). Sempre criado dentro do teste."""
    return responsaveis.criar(nome, tipo_utilizador="Master")


def _criar_propriedade(nome="Foz Velha"):
    return propriedades.criar(nome, "Rua de Exemplo, 1")


def _criar_unidade_mensal(propriedade_id, preco_base="250.00"):
    return unidades.criar(
        propriedade_id,
        "Unidade Mensal",
        "mensal",
        Decimal(preco_base),
        Decimal(preco_base),
        Decimal("20.00"),
    )


def _criar_unidade_airbnb(
    propriedade_id, preco_base="45.00", preco_epoca_alta="90.00"
):
    return unidades.criar(
        propriedade_id,
        "Unidade Airbnb",
        "airbnb",
        Decimal(preco_base),
        Decimal(preco_epoca_alta),
        Decimal("20.00"),
        epoca_alta_ativa=False,  # desligada: os testes não querem época alta automática
    )


def _dar_capacidade_a_unidade(unidade_id, capacidade=2):
    """Cria um quarto com um lugar de capacidade `capacidade`.

    Uma unidade mensal sem lugares tem capacidade 0 — e
    `contratos.criar_mensal` recusa qualquer contrato numa unidade
    com capacidade zero. Este helper é o que faltava para os testes
    deste ficheiro poderem criar contratos.

    Capacidade 2 por omissão: alguns testes criam dois contratos
    seguidos na mesma unidade (para testar duas propriedades,
    cenários com múltiplas unidades, etc.); capacidade 2 dá margem
    sem ter de re-ajustar cada teste.

    Mesma convenção de `BaseContratosTest` em teste_contratos.py.
    """
    quarto = unidades.criar_quarto(unidade_id, "Quarto de teste")
    unidades.criar_lugar(
        quarto["id"], "Lugar 1", "casal", capacidade=capacidade
    )


def _criar_cliente_mensal(nome="Ana Silva", nif="501442600"):
    """Cliente completo para o regime mensal — todos os obrigatórios
    que `validacoes.validar_cliente` exige."""
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
    )


def _criar_cliente_airbnb(nome="John Smith"):
    """Cliente completo para o regime Airbnb — todos os obrigatórios
    que `validacoes.validar_cliente` exige (16/09/2026)."""
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


def _criar_contrato_mensal(
    unidade_id,
    cliente_id,
    data_inicio,
    renda="250.00",
    data_fim=None,
):
    """Cria um contrato mensal. Se `data_fim` for indicado, encerra
    o contrato logo a seguir.

    Não aceita renda abaixo da calculada — para esse caso usar
    `_criar_contrato_mensal_com_desconto`, que passa um responsável
    a autorizar.
    """
    ocupacao, mensal = contratos.criar_mensal(
        unidade_id,
        cliente_id,
        data_inicio,
        Decimal(renda),
        Decimal(renda),
    )
    if data_fim is not None:
        ocupacao, mensal = contratos.encerrar_mensal(ocupacao["id"], data_fim)
    return ocupacao, mensal


def _criar_contrato_mensal_com_desconto(
    unidade_id,
    cliente_id,
    data_inicio,
    renda_calculada,
    renda_praticada,
    autor,
    data_fim=None,
):
    """Cria um contrato mensal com renda abaixo da calculada — exige
    um autor que valide o desconto.

    `renda_calculada` só entra nos testes para documentar a intenção
    (o `criar_mensal` calcula-a sozinho, a partir do preço base da
    unidade); o valor que efetivamente é gravado como renda é
    `renda_praticada`.
    """
    ocupacao, mensal = contratos.criar_mensal(
        unidade_id,
        cliente_id,
        data_inicio,
        Decimal(renda_praticada),
        Decimal(renda_praticada),
        responsavel_desconto_renda_id=autor["id"],
    )
    if data_fim is not None:
        ocupacao, mensal = contratos.encerrar_mensal(ocupacao["id"], data_fim)
    return ocupacao, mensal


def _criar_reserva_airbnb(
    unidade_id, cliente_id, data_inicio, data_fim, preco=None
):
    """Cria uma reserva Airbnb. Se `preco` não for indicado, usa o
    preço calculado pela própria unidade — o caso normal."""
    unidade = unidades.procurar(unidade_id)
    if preco is None:
        preco = contratos.calcular_preco_airbnb(unidade, data_inicio, data_fim)
    ocupacao, airbnb = contratos.registar_airbnb(
        unidade_id,
        cliente_id,
        data_inicio,
        data_fim,
        preco,
    )
    return ocupacao, airbnb


def _criar_categoria(nome, autor):
    return despesas.criar_categoria(nome, autor)


def _criar_despesa_paga(
    categoria_id,
    valor,
    data_pagamento,
    autor,
    unidade_id=None,
):
    """Cria uma despesa manual e marca-a paga na data indicada —
    só as pagas entram em `despesas_por_categoria`."""
    d = despesas.criar_despesa_manual(
        categoria_id=categoria_id,
        valor=Decimal(valor),
        data_lancamento=data_pagamento,
        responsavel_id=autor["id"],
        autor=autor,
        unidade_id=unidade_id,
    )
    return despesas.marcar_paga(d["id"], data_pagamento, autor)


# =====================================================================
# 1. Helpers puros — sem MySQL
# =====================================================================


class TesteHelpersPuros(unittest.TestCase):
    """Funções de cálculo de datas e rateio do Bloco 1.

    Funções puras — não tocam em BD, não guardam estado. Correm em
    milissegundos.
    """

    # -- _validar_periodo ---------------------------------------------

    def test_validar_periodo_aceita_intervalo_coerente(self):
        # Não deve levantar nada.
        financeiro._validar_periodo(date(2026, 1, 1), date(2026, 2, 1))

    def test_validar_periodo_recusa_inicio_none(self):
        with self.assertRaises(ValueError):
            financeiro._validar_periodo(None, date(2026, 2, 1))

    def test_validar_periodo_recusa_fim_none(self):
        with self.assertRaises(ValueError):
            financeiro._validar_periodo(date(2026, 1, 1), None)

    def test_validar_periodo_recusa_tipo_invalido(self):
        with self.assertRaises(ValueError):
            financeiro._validar_periodo("2026-01-01", date(2026, 2, 1))

        with self.assertRaises(ValueError):
            financeiro._validar_periodo(date(2026, 1, 1), "2026-02-01")

    def test_validar_periodo_recusa_fim_igual_ao_inicio(self):
        """O fim é exclusivo: mesmo dia não contém nenhum período."""
        with self.assertRaises(ValueError):
            financeiro._validar_periodo(date(2026, 1, 1), date(2026, 1, 1))

    def test_validar_periodo_recusa_fim_antes_do_inicio(self):
        with self.assertRaises(ValueError):
            financeiro._validar_periodo(date(2026, 2, 1), date(2026, 1, 1))

    # -- _meses_do_periodo --------------------------------------------

    def test_meses_do_periodo_mes_unico(self):
        meses = financeiro._meses_do_periodo(
            date(2026, 6, 1), date(2026, 6, 30)
        )
        self.assertEqual(meses, [(2026, 6)])

    def test_meses_do_periodo_varios_meses_no_mesmo_ano(self):
        meses = financeiro._meses_do_periodo(
            date(2026, 6, 15), date(2026, 8, 2)
        )
        self.assertEqual(meses, [(2026, 6), (2026, 7), (2026, 8)])

    def test_meses_do_periodo_atravessa_ano(self):
        """O `data_fim` (2026-02-01) é exclusivo — como calha no
        primeiro dia do mês, fevereiro NÃO pertence ao período. Só
        novembro, dezembro e janeiro. Mesma convenção que a
        correção de 22/09/2026 fixou no `_meses_do_periodo`."""
        meses = financeiro._meses_do_periodo(
            date(2025, 11, 15), date(2026, 2, 1)
        )
        self.assertEqual(
            meses,
            [(2025, 11), (2025, 12), (2026, 1)],
        )

    def test_meses_do_periodo_fim_a_meio_do_mes_inclui_esse_mes(self):
        """O complemento do teste anterior: se o `data_fim` não
        calhar no dia 1, o mês em que cai PERTENCE ao período.

        (2026-06-15, 2026-08-02) → junho, julho e agosto. Agosto
        entra porque o dia 2 de agosto está dentro do período.
        """
        meses = financeiro._meses_do_periodo(
            date(2026, 6, 15), date(2026, 8, 2)
        )
        self.assertEqual(meses, [(2026, 6), (2026, 7), (2026, 8)])

    def test_meses_do_periodo_um_dia(self):
        """Um período de um dia (início + 1 dia) devolve um só mês."""
        meses = financeiro._meses_do_periodo(
            date(2026, 6, 15), date(2026, 6, 16)
        )
        self.assertEqual(meses, [(2026, 6)])

    # -- _primeiro_dia_do_mes / _ultimo_dia_do_mes --------------------

    def test_primeiro_dia_do_mes(self):
        self.assertEqual(
            financeiro._primeiro_dia_do_mes(2026, 3), date(2026, 3, 1)
        )

    def test_ultimo_dia_do_mes_fevereiro_ano_normal(self):
        self.assertEqual(
            financeiro._ultimo_dia_do_mes(2026, 2), date(2026, 2, 28)
        )

    def test_ultimo_dia_do_mes_fevereiro_ano_bissexto(self):
        self.assertEqual(
            financeiro._ultimo_dia_do_mes(2024, 2), date(2024, 2, 29)
        )

    def test_ultimo_dia_do_mes_30_dias(self):
        self.assertEqual(
            financeiro._ultimo_dia_do_mes(2026, 4), date(2026, 4, 30)
        )

    def test_ultimo_dia_do_mes_31_dias(self):
        self.assertEqual(
            financeiro._ultimo_dia_do_mes(2026, 1), date(2026, 1, 31)
        )

    # -- _mes_de ------------------------------------------------------

    def test_mes_de(self):
        self.assertEqual(financeiro._mes_de(date(2026, 9, 15)), (2026, 9))

    # -- _mes_tocado_pela_ocupacao ------------------------------------

    def _ocupacao(self, inicio, fim=None):
        """Só a forma mínima que `_mes_tocado_pela_ocupacao` lê."""
        return {"data_inicio": inicio, "data_fim": fim}

    def test_mes_tocado_ocupacao_em_vigor(self):
        """data_fim=None → toca todos os meses desde o início."""
        o = self._ocupacao(date(2026, 1, 15))
        self.assertTrue(financeiro._mes_tocado_pela_ocupacao(o, 2026, 1))
        self.assertTrue(financeiro._mes_tocado_pela_ocupacao(o, 2026, 6))
        self.assertTrue(financeiro._mes_tocado_pela_ocupacao(o, 2030, 1))

    def test_mes_tocado_ocupacao_encerrada_antes_do_mes(self):
        """data_fim <= primeiro dia do mês → NÃO toca esse mês."""
        o = self._ocupacao(date(2026, 1, 10), date(2026, 3, 1))
        # Março: primeiro dia do mês == data_fim → não toca.
        self.assertFalse(financeiro._mes_tocado_pela_ocupacao(o, 2026, 3))

    def test_mes_tocado_ocupacao_encerrada_no_mesmo_mes(self):
        """Um contrato que acaba a 15 de junho toca junho todo."""
        o = self._ocupacao(date(2026, 5, 1), date(2026, 6, 15))
        self.assertTrue(financeiro._mes_tocado_pela_ocupacao(o, 2026, 6))

    def test_mes_tocado_ocupacao_comeca_a_meio_do_mes(self):
        """Um contrato que começa a 20 de junho toca junho todo."""
        o = self._ocupacao(date(2026, 6, 20))
        self.assertTrue(financeiro._mes_tocado_pela_ocupacao(o, 2026, 6))

    def test_mes_tocado_ocupacao_comeca_depois_do_mes(self):
        o = self._ocupacao(date(2026, 7, 1))
        self.assertFalse(financeiro._mes_tocado_pela_ocupacao(o, 2026, 6))

    def test_mes_tocado_ocupacao_antes_do_periodo(self):
        o = self._ocupacao(date(2024, 1, 1), date(2024, 12, 31))
        self.assertFalse(financeiro._mes_tocado_pela_ocupacao(o, 2026, 6))

    # -- _meses_de_vigencia_no_periodo --------------------------------

    def test_meses_de_vigencia_conta_todos_os_meses_tocados(self):
        o = self._ocupacao(date(2026, 1, 10), date(2026, 3, 20))
        meses = [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]
        self.assertEqual(financeiro._meses_de_vigencia_no_periodo(o, meses), 3)

    def test_meses_de_vigencia_ocupacao_em_vigor_conta_todos(self):
        o = self._ocupacao(date(2025, 1, 1))
        meses = [(2026, 1), (2026, 2), (2026, 3)]
        self.assertEqual(financeiro._meses_de_vigencia_no_periodo(o, meses), 3)

    def test_meses_de_vigencia_sem_sobreposicao_e_zero(self):
        o = self._ocupacao(date(2024, 1, 1), date(2024, 12, 31))
        meses = [(2026, 6), (2026, 7)]
        self.assertEqual(financeiro._meses_de_vigencia_no_periodo(o, meses), 0)

    # -- _noites_totais -----------------------------------------------

    def test_noites_totais_intervalo_de_uma_noite(self):
        o = self._ocupacao(date(2026, 1, 10), date(2026, 1, 11))
        self.assertEqual(financeiro._noites_totais(o), 1)

    def test_noites_totais_intervalo_longo(self):
        o = self._ocupacao(date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual(financeiro._noites_totais(o), 30)

    def test_noites_totais_sem_data_fim_e_zero(self):
        o = self._ocupacao(date(2026, 1, 1))
        self.assertEqual(financeiro._noites_totais(o), 0)

    # -- _noites_no_periodo -------------------------------------------

    def test_noites_no_periodo_total_dentro(self):
        o = self._ocupacao(date(2026, 1, 10), date(2026, 1, 15))
        self.assertEqual(
            financeiro._noites_no_periodo(
                o, date(2026, 1, 1), date(2026, 2, 1)
            ),
            5,
        )

    def test_noites_no_periodo_parcial_inicio(self):
        """O período começa a meio da ocupação."""
        o = self._ocupacao(date(2026, 1, 1), date(2026, 1, 20))
        self.assertEqual(
            financeiro._noites_no_periodo(
                o, date(2026, 1, 10), date(2026, 1, 20)
            ),
            10,
        )

    def test_noites_no_periodo_parcial_fim(self):
        """O período acaba a meio da ocupação."""
        o = self._ocupacao(date(2026, 1, 1), date(2026, 1, 20))
        self.assertEqual(
            financeiro._noites_no_periodo(
                o, date(2026, 1, 1), date(2026, 1, 10)
            ),
            9,
        )

    def test_noites_no_periodo_ocupacao_contem_periodo(self):
        o = self._ocupacao(date(2025, 12, 1), date(2026, 2, 1))
        self.assertEqual(
            financeiro._noites_no_periodo(
                o, date(2026, 1, 10), date(2026, 1, 20)
            ),
            10,
        )

    def test_noites_no_periodo_sem_intersecao_e_zero(self):
        o = self._ocupacao(date(2026, 3, 1), date(2026, 3, 5))
        self.assertEqual(
            financeiro._noites_no_periodo(
                o, date(2026, 1, 1), date(2026, 2, 1)
            ),
            0,
        )

    def test_noites_no_periodo_sem_data_fim_e_zero(self):
        o = self._ocupacao(date(2026, 1, 1))
        self.assertEqual(
            financeiro._noites_no_periodo(
                o, date(2026, 1, 1), date(2026, 2, 1)
            ),
            0,
        )

    # -- _ratear ------------------------------------------------------

    def test_ratear_valor_proporcional_exato(self):
        self.assertEqual(
            financeiro._ratear(Decimal("100.00"), 5, 10),
            Decimal("50.00"),
        )

    def test_ratear_total_do_periodo(self):
        self.assertEqual(
            financeiro._ratear(Decimal("100.00"), 10, 10),
            Decimal("100.00"),
        )

    def test_ratear_arredonda_duas_casas(self):
        """100 / 3 = 33.333... → 33.33, arredondamento normal."""
        self.assertEqual(
            financeiro._ratear(Decimal("100.00"), 1, 3),
            Decimal("33.33"),
        )

    def test_ratear_total_zero_devolve_zero(self):
        """Proteção contra divisão por zero — devolve o neutro da soma."""
        self.assertEqual(
            financeiro._ratear(Decimal("100.00"), 5, 0),
            Decimal("0.00"),
        )

    def test_ratear_valor_zero_devolve_zero(self):
        self.assertEqual(
            financeiro._ratear(Decimal("0.00"), 3, 10),
            Decimal("0.00"),
        )


# =====================================================================
# 2. Receita
# =====================================================================


class TesteReceita(BaseMySQLTest):
    """`receita_por_unidade` e `receita_por_propriedade`."""

    def setUp(self):
        super().setUp()
        self.propriedade = _criar_propriedade("Prédio A")
        self.propriedade_b = _criar_propriedade("Prédio B")

        self.unidade_mensal = _criar_unidade_mensal(
            self.propriedade["id"], preco_base="250.00"
        )
        _dar_capacidade_a_unidade(self.unidade_mensal["id"])

        self.unidade_airbnb = _criar_unidade_airbnb(self.propriedade["id"])

        self.cliente_mensal = _criar_cliente_mensal(nif="501442600")
        self.cliente_airbnb = _criar_cliente_airbnb()

    # -- receita_por_unidade, sem ocupações ---------------------------

    def test_receita_por_unidade_sem_ocupacoes_e_lista_vazia(self):
        self.assertEqual(
            financeiro.receita_por_unidade(date(2026, 1, 1), date(2026, 2, 1)),
            [],
        )

    # -- receita mensal -----------------------------------------------

    def test_receita_mensal_um_mes_inteiro(self):
        """Um contrato a cobrir todo o mês de janeiro conta uma vez."""
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            renda="250.00",
            data_fim=date(2026, 2, 1),
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["unidade_id"], self.unidade_mensal["id"])
        self.assertEqual(resultado[0]["receita"], Decimal("250.00"))

    def test_receita_mensal_tres_meses(self):
        """Um contrato que cobre três meses conta três vezes."""
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            renda="250.00",
            data_fim=date(2026, 4, 1),
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 4, 1)
        )

        self.assertEqual(resultado[0]["receita"], Decimal("750.00"))

    def test_receita_mensal_periodo_parcial_conta_mes_inteiro(self):
        """Um contrato que só tocou junho (começou a 20) conta junho
        todo — sem rateio de dias."""
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 6, 20),
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 6, 1), date(2026, 7, 1)
        )

        self.assertEqual(resultado[0]["receita"], Decimal("250.00"))

    def test_receita_mensal_em_vigor_conta_todos_os_meses_do_periodo(self):
        """Contrato sem data_fim → toca todos os meses do período."""
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            renda="250.00",
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 3, 1), date(2026, 6, 1)
        )

        # 3 meses (março, abril, maio) × 250 — o data_fim (1 de
        # junho) é exclusivo, junho não conta.
        self.assertEqual(resultado[0]["receita"], Decimal("750.00"))

    def test_receita_mensal_desconto_rateado_por_mes(self):
        """O desconto é (renda_calculada − renda_praticada) × meses."""
        autor = _criar_master()
        _criar_contrato_mensal_com_desconto(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            renda_calculada="250.00",
            renda_praticada="200.00",
            autor=autor,
            data_fim=date(2026, 4, 1),
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 4, 1)
        )

        # 3 meses × 200 = 600 de receita; desconto 3 × 50 = 150.
        self.assertEqual(resultado[0]["receita"], Decimal("600.00"))
        self.assertEqual(resultado[0]["desconto"], Decimal("150.00"))

    # -- receita airbnb -----------------------------------------------

    def test_receita_airbnb_total_dentro_do_periodo(self):
        """Reserva de 4 noites, período maior: receita = preço total."""
        _criar_reserva_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 14),
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["unidade_id"], self.unidade_airbnb["id"])
        # Preço base 45 × 4 noites = 180.
        self.assertEqual(resultado[0]["receita"], Decimal("180.00"))

    def test_receita_airbnb_rateada_no_periodo(self):
        """Reserva de 10 noites, período cobre 4 delas: receita rateada."""
        _criar_reserva_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 1),
            date(2026, 1, 11),
        )

        # Período de 1 a 5 de janeiro = 4 noites dentro (1,2,3,4).
        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 1, 5)
        )

        # Preço total = 10 × 45 = 450. Rateio: 450 × (4/10) = 180.
        self.assertEqual(resultado[0]["receita"], Decimal("180.00"))

    def test_receita_airbnb_epoca_alta(self):
        """Reserva que atravessa a época alta calcula o preço por
        noite — o `preco_calculado` já vem com isso."""
        # Liga época alta na unidade.
        unidades.atualizar(self.unidade_airbnb["id"], epoca_alta_ativa=True)

        _criar_reserva_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 7, 1),
            date(2026, 7, 4),
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 7, 1), date(2026, 7, 5)
        )

        # 3 noites em época alta × 90 = 270.
        self.assertEqual(resultado[0]["receita"], Decimal("270.00"))

    def test_receita_airbnb_reserva_encerrada_conta_na_mesma(self):
        """Reserva cancelada — o `incluir_inativas=True` do motor
        traz-na. Um relatório histórico não muda conforme as reservas
        vão sendo canceladas."""
        ocupacao, _ = _criar_reserva_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 14),
        )
        contratos.cancelar_airbnb(ocupacao["id"])

        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["receita"], Decimal("180.00"))

    # -- agregação por unidade ----------------------------------------

    def test_receita_por_unidade_agrega_mensal_e_airbnb(self):
        """Uma unidade mensal e uma Airbnb, cada uma com a sua
        contribuição; a lista tem duas entradas ordenadas por id."""
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            renda="250.00",
            data_fim=date(2026, 2, 1),
        )
        _criar_reserva_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 14),
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(len(resultado), 2)
        ids = [r["unidade_id"] for r in resultado]
        self.assertEqual(ids, sorted(ids))  # ordenado por id

    def test_receita_por_unidade_ordena_por_id(self):
        """Verifica que o sort é estável por unidade_id."""
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            data_fim=date(2026, 2, 1),
        )
        _criar_reserva_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 14),
        )

        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        ids = [r["unidade_id"] for r in resultado]
        # A unidade mensal foi criada primeiro (UNI-001); a airbnb
        # depois (UNI-002). A lista vem ordenada.
        self.assertEqual(ids[0], self.unidade_mensal["id"])
        self.assertEqual(ids[1], self.unidade_airbnb["id"])

    def test_receita_por_unidade_ignora_sem_receita(self):
        """Unidades sem ocupações no período não aparecem."""
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            data_fim=date(2026, 2, 1),
        )

        # A airbnb existe mas não tem reservas no período.
        resultado = financeiro.receita_por_unidade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        ids = [r["unidade_id"] for r in resultado]
        self.assertNotIn(self.unidade_airbnb["id"], ids)

    # -- receita_por_propriedade --------------------------------------

    def test_receita_por_propriedade_agrega_unidades(self):
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            data_fim=date(2026, 2, 1),
        )
        _criar_reserva_airbnb(
            self.unidade_airbnb["id"],
            self.cliente_airbnb["id"],
            date(2026, 1, 10),
            date(2026, 1, 14),
        )

        resultado = financeiro.receita_por_propriedade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        # As duas unidades estão na mesma propriedade: uma só entrada.
        self.assertEqual(len(resultado), 1)
        self.assertEqual(
            resultado[0]["propriedade_id"], self.propriedade["id"]
        )
        # 250 (mensal) + 180 (airbnb) = 430.
        self.assertEqual(resultado[0]["receita"], Decimal("430.00"))

    def test_receita_por_propriedade_traz_o_nome(self):
        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            data_fim=date(2026, 2, 1),
        )

        resultado = financeiro.receita_por_propriedade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado[0]["propriedade_nome"], "Prédio A")

    def test_receita_por_propriedade_duas_propriedades(self):
        unidade_b = _criar_unidade_mensal(
            self.propriedade_b["id"], preco_base="300.00"
        )
        _dar_capacidade_a_unidade(unidade_b["id"])
        cliente_b = _criar_cliente_mensal(nome="Bruno", nif="222222220")

        _criar_contrato_mensal(
            self.unidade_mensal["id"],
            self.cliente_mensal["id"],
            date(2026, 1, 1),
            data_fim=date(2026, 2, 1),
        )
        _criar_contrato_mensal(
            unidade_b["id"],
            cliente_b["id"],
            date(2026, 1, 1),
            renda="300.00",
            data_fim=date(2026, 2, 1),
        )

        resultado = financeiro.receita_por_propriedade(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(len(resultado), 2)
        por_id = {r["propriedade_id"]: r for r in resultado}
        self.assertEqual(
            por_id[self.propriedade["id"]]["receita"], Decimal("250.00")
        )
        self.assertEqual(
            por_id[self.propriedade_b["id"]]["receita"], Decimal("300.00")
        )

    def test_receita_por_propriedade_sem_dados_e_lista_vazia(self):
        self.assertEqual(
            financeiro.receita_por_propriedade(
                date(2026, 1, 1), date(2026, 2, 1)
            ),
            [],
        )


# =====================================================================
# 3. Despesas e COGS
# =====================================================================


class TesteDespesasCogs(BaseMySQLTest):
    """`despesas_por_categoria` e `cogs_por_produto`."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_master()

    # -- despesas_por_categoria ---------------------------------------

    def test_despesas_por_categoria_sem_despesas_e_lista_vazia(self):
        self.assertEqual(
            financeiro.despesas_por_categoria(
                date(2026, 1, 1), date(2026, 2, 1)
            ),
            [],
        )

    def test_despesas_por_categoria_agrega_por_categoria(self):
        agua = _criar_categoria("Água", self.autor)
        luz = _criar_categoria("Luz", self.autor)

        _criar_despesa_paga(agua["id"], "30.00", date(2026, 1, 15), self.autor)
        _criar_despesa_paga(agua["id"], "20.00", date(2026, 1, 20), self.autor)
        _criar_despesa_paga(luz["id"], "60.00", date(2026, 1, 10), self.autor)

        resultado = financeiro.despesas_por_categoria(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(len(resultado), 2)
        por_id = {r["categoria_id"]: r for r in resultado}
        self.assertEqual(por_id[agua["id"]]["total"], Decimal("50.00"))
        self.assertEqual(por_id[luz["id"]]["total"], Decimal("60.00"))

    def test_despesas_por_categoria_traz_o_nome(self):
        agua = _criar_categoria("Água", self.autor)
        _criar_despesa_paga(agua["id"], "30.00", date(2026, 1, 15), self.autor)

        resultado = financeiro.despesas_por_categoria(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado[0]["categoria_nome"], "Água")

    def test_despesas_por_categoria_ignora_pendentes(self):
        """Só as pagas contam — o lado da despesa é fluxo de caixa."""
        agua = _criar_categoria("Água", self.autor)

        # Pendente — criada mas NÃO marcada paga.
        despesas.criar_despesa_manual(
            categoria_id=agua["id"],
            valor=Decimal("100.00"),
            data_lancamento=date(2026, 1, 15),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        # Paga.
        _criar_despesa_paga(agua["id"], "30.00", date(2026, 1, 20), self.autor)

        resultado = financeiro.despesas_por_categoria(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado[0]["total"], Decimal("30.00"))

    def test_despesas_por_categoria_ignora_canceladas(self):
        agua = _criar_categoria("Água", self.autor)

        d = despesas.criar_despesa_manual(
            categoria_id=agua["id"],
            valor=Decimal("100.00"),
            data_lancamento=date(2026, 1, 15),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        despesas.cancelar_despesa(d["id"], "erro", self.autor)

        _criar_despesa_paga(agua["id"], "30.00", date(2026, 1, 20), self.autor)

        resultado = financeiro.despesas_por_categoria(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado[0]["total"], Decimal("30.00"))

    def test_despesas_por_categoria_usa_data_pagamento(self):
        """Uma despesa lançada em dezembro mas paga em janeiro
        conta em janeiro."""
        agua = _criar_categoria("Água", self.autor)

        d = despesas.criar_despesa_manual(
            categoria_id=agua["id"],
            valor=Decimal("100.00"),
            data_lancamento=date(2025, 12, 20),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        despesas.marcar_paga(d["id"], date(2026, 1, 5), self.autor)

        # Dentro do período (janeiro):
        resultado = financeiro.despesas_por_categoria(
            date(2026, 1, 1), date(2026, 2, 1)
        )
        self.assertEqual(len(resultado), 1)

        # Fora do período (dezembro):
        resultado_dez = financeiro.despesas_por_categoria(
            date(2025, 12, 1), date(2026, 1, 1)
        )
        self.assertEqual(resultado_dez, [])

    # -- cogs_por_produto ---------------------------------------------

    def test_cogs_sem_movimentos_e_lista_vazia(self):
        self.assertEqual(
            financeiro.cogs_por_produto(date(2026, 1, 1), date(2026, 2, 1)),
            [],
        )

    def test_cogs_soma_saidas(self):
        produto = estoque.criar_produto("Lixívia", "L")
        estoque.registar_movimento(
            produto["id"], "saida", 5, date(2026, 1, 15)
        )
        estoque.registar_movimento(
            produto["id"], "saida", 3, date(2026, 1, 20)
        )

        resultado = financeiro.cogs_por_produto(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["produto_id"], produto["id"])
        self.assertEqual(resultado[0]["quantidade"], 8)

    def test_cogs_traz_o_nome_do_produto(self):
        produto = estoque.criar_produto("Lixívia", "L")
        estoque.registar_movimento(
            produto["id"], "saida", 5, date(2026, 1, 15)
        )

        resultado = financeiro.cogs_por_produto(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado[0]["produto_nome"], "Lixívia")

    def test_cogs_ignora_entradas_de_compra(self):
        """Uma entrada normal (sem requisicao_id) é compra — não
        abate o COGS."""
        produto = estoque.criar_produto("Lixívia", "L")
        estoque.registar_movimento(
            produto["id"], "entrada", 20, date(2026, 1, 10)
        )
        estoque.registar_movimento(
            produto["id"], "saida", 5, date(2026, 1, 15)
        )

        resultado = financeiro.cogs_por_produto(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado[0]["quantidade"], 5)

    def test_cogs_abate_entrada_de_devolucao(self):
        """Uma entrada com requisicao_id (devolução) abate o COGS
        do produto."""
        # Cria um produto, uma requisição, e movimentos ligados.
        produto = estoque.criar_produto("Lixívia", "L")
        responsavel = _criar_master("Responsável Requisições")
        requisicao = estoque.criar_requisicao(
            responsavel["id"],
            [{"produto_id": produto["id"], "quantidade_pedida": 5}],
            date(2026, 1, 5),
        )
        # Entrada de stock para ter saldo.
        estoque.registar_movimento(
            produto["id"], "entrada", 20, date(2026, 1, 5)
        )
        # Saída via requisição.
        estoque.enviar_requisicao(
            requisicao["id"], responsavel["id"], date(2026, 1, 10)
        )
        # Devolução: entrada com requisicao_id.
        estoque.registar_movimento(
            produto["id"],
            "entrada",
            2,
            date(2026, 1, 20),
            requisicao_id=requisicao["id"],
        )

        resultado = financeiro.cogs_por_produto(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        # COGS: 5 saídas − 2 devolvidas = 3.
        self.assertEqual(resultado[0]["quantidade"], 3)

    def test_cogs_ignora_ajustes(self):
        """Ajustes não entram no COGS — não são consumo de operação."""
        produto = estoque.criar_produto("Lixívia", "L")
        estoque.registar_movimento(
            produto["id"], "saida", 5, date(2026, 1, 15)
        )
        estoque.registar_movimento(
            produto["id"],
            "ajuste",
            -2,
            date(2026, 1, 20),
            motivo="Contagem",
        )

        resultado = financeiro.cogs_por_produto(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado[0]["quantidade"], 5)

    def test_cogs_produto_totalmente_devolvido_nao_aparece(self):
        """Saída 5, entrada de devolução 5 → COGS líquido 0, não
        aparece na lista."""
        produto = estoque.criar_produto("Lixívia", "L")
        responsavel = _criar_master("Responsável Requisições")
        requisicao = estoque.criar_requisicao(
            responsavel["id"],
            [{"produto_id": produto["id"], "quantidade_pedida": 5}],
            date(2026, 1, 5),
        )
        estoque.registar_movimento(
            produto["id"], "entrada", 20, date(2026, 1, 5)
        )
        estoque.enviar_requisicao(
            requisicao["id"], responsavel["id"], date(2026, 1, 10)
        )
        estoque.registar_movimento(
            produto["id"],
            "entrada",
            5,
            date(2026, 1, 20),
            requisicao_id=requisicao["id"],
        )

        resultado = financeiro.cogs_por_produto(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado, [])

    def test_cogs_filtra_por_data_do_movimento(self):
        produto = estoque.criar_produto("Lixívia", "L")
        estoque.registar_movimento(
            produto["id"], "saida", 5, date(2025, 12, 30)
        )
        estoque.registar_movimento(
            produto["id"], "saida", 3, date(2026, 1, 15)
        )

        resultado = financeiro.cogs_por_produto(
            date(2026, 1, 1), date(2026, 2, 1)
        )

        self.assertEqual(resultado[0]["quantidade"], 3)


# =====================================================================
# 4. Resultado agregado
# =====================================================================


class TesteResultado(BaseMySQLTest):
    """`resultado` — a soma final."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_master()
        self.propriedade = _criar_propriedade("Prédio A")
        self.unidade = _criar_unidade_mensal(self.propriedade["id"])
        _dar_capacidade_a_unidade(self.unidade["id"])
        self.cliente = _criar_cliente_mensal()

    def test_resultado_sem_dados(self):
        """Numa BD vazia, todos os números são zero."""
        r = financeiro.resultado(date(2026, 1, 1), date(2026, 2, 1))

        self.assertEqual(r["receita"], Decimal("0.00"))
        self.assertEqual(r["descontos"], Decimal("0.00"))
        self.assertEqual(r["despesas_operacionais"], Decimal("0.00"))
        self.assertEqual(r["resultado_liquido"], Decimal("0.00"))
        self.assertEqual(r["cogs_quantidade"], 0)

    def test_resultado_estrutura_tem_cinco_chaves(self):
        r = financeiro.resultado(date(2026, 1, 1), date(2026, 2, 1))

        self.assertEqual(
            set(r),
            {
                "receita",
                "descontos",
                "despesas_operacionais",
                "resultado_liquido",
                "cogs_quantidade",
            },
        )

    def test_resultado_receita_so(self):
        """Sem despesas, o resultado líquido = receita − descontos."""
        _criar_contrato_mensal(
            self.unidade["id"],
            self.cliente["id"],
            date(2026, 1, 1),
            renda="250.00",
            data_fim=date(2026, 2, 1),
        )

        r = financeiro.resultado(date(2026, 1, 1), date(2026, 2, 1))

        self.assertEqual(r["receita"], Decimal("250.00"))
        self.assertEqual(r["resultado_liquido"], Decimal("250.00"))

    def test_resultado_despesas_operacionais(self):
        _criar_contrato_mensal(
            self.unidade["id"],
            self.cliente["id"],
            date(2026, 1, 1),
            renda="250.00",
            data_fim=date(2026, 2, 1),
        )
        agua = _criar_categoria("Água", self.autor)
        _criar_despesa_paga(agua["id"], "30.00", date(2026, 1, 15), self.autor)

        r = financeiro.resultado(date(2026, 1, 1), date(2026, 2, 1))

        self.assertEqual(r["receita"], Decimal("250.00"))
        self.assertEqual(r["despesas_operacionais"], Decimal("30.00"))
        self.assertEqual(r["resultado_liquido"], Decimal("220.00"))

    def test_resultado_com_desconto(self):
        """O desconto entra na conta final: receita − descontos."""
        _criar_contrato_mensal_com_desconto(
            self.unidade["id"],
            self.cliente["id"],
            date(2026, 1, 1),
            renda_calculada="250.00",
            renda_praticada="200.00",
            autor=self.autor,
            data_fim=date(2026, 2, 1),
        )

        r = financeiro.resultado(date(2026, 1, 1), date(2026, 2, 1))

        self.assertEqual(r["receita"], Decimal("200.00"))
        self.assertEqual(r["descontos"], Decimal("50.00"))
        self.assertEqual(r["resultado_liquido"], Decimal("150.00"))

    def test_resultado_negativo_quando_despesas_superam_receita(self):
        """Caso com desconto E despesa alta, para confirmar que a
        fórmula do `resultado` subtrai os dois.

        Renda praticada 100, calculada 250 → desconto 150.
        Despesa 500.

        Conta final: 100 − 150 − 500 = −550.

        O desconto entra na conta como valor a subtrair, não como
        mera informação — foi o que a primeira versão deste teste
        assumiu mal (esperava -400, como se o desconto não
        contasse).
        """
        _criar_contrato_mensal_com_desconto(
            self.unidade["id"],
            self.cliente["id"],
            date(2026, 1, 1),
            renda_calculada="250.00",
            renda_praticada="100.00",
            autor=self.autor,
            data_fim=date(2026, 2, 1),
        )
        agua = _criar_categoria("Água", self.autor)
        _criar_despesa_paga(
            agua["id"], "500.00", date(2026, 1, 15), self.autor
        )

        r = financeiro.resultado(date(2026, 1, 1), date(2026, 2, 1))

        self.assertEqual(r["receita"], Decimal("100.00"))
        self.assertEqual(r["descontos"], Decimal("150.00"))
        self.assertEqual(r["despesas_operacionais"], Decimal("500.00"))
        self.assertEqual(r["resultado_liquido"], Decimal("-550.00"))

    def test_resultado_cogs_quantidade_soma_saidas(self):
        produto = estoque.criar_produto("Lixívia", "L")
        estoque.registar_movimento(
            produto["id"], "saida", 5, date(2026, 1, 15)
        )

        r = financeiro.resultado(date(2026, 1, 1), date(2026, 2, 1))

        self.assertEqual(r["cogs_quantidade"], 5)

    def test_resultado_cogs_nao_entra_no_liquido(self):
        """COGS é quantidade, não dinheiro — não entra no resultado
        líquido."""
        _criar_contrato_mensal(
            self.unidade["id"],
            self.cliente["id"],
            date(2026, 1, 1),
            renda="250.00",
            data_fim=date(2026, 2, 1),
        )
        produto = estoque.criar_produto("Lixívia", "L")
        estoque.registar_movimento(
            produto["id"], "saida", 5, date(2026, 1, 15)
        )

        r = financeiro.resultado(date(2026, 1, 1), date(2026, 2, 1))

        self.assertEqual(r["receita"], Decimal("250.00"))
        self.assertEqual(r["resultado_liquido"], Decimal("250.00"))
        self.assertEqual(r["cogs_quantidade"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
