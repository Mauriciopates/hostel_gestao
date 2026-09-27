"""Testes automáticos do módulo `despesas`.

Corre contra a base de dados de teste (ver `apoio_BD.py`) — NUNCA
contra a base de dados real. Cada teste começa com todas as tabelas
vazias.

Cobre:
  - Ciclo CRUD de categorias e fornecedores
  - VIA 1 — criar despesa manual, editar valor, marcar paga, cancelar
  - Divisão por propriedade — N despesas iguais a partir de uma
  - VIA 2 — criar despesa via stock, confirmar itens, gerar movimentos
  - Recorrências — gerar a do mês seguinte, sem duplicar
  - `esta_vencida` — 3 cenários
  - Verificações de permissão (Staff recusado em tudo o que é escrita)

Corre com:
    python -m unittest testes.teste_despesas -v
(da raiz do projeto)
"""

import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest

import despesas
import responsaveis


# =====================================================================
# Helpers de fixture — criar o mínimo necessário em cada teste
# =====================================================================


def _criar_autor(tipo_utilizador="Master", nome="Autor Teste"):
    """Cria um responsável ativo com o perfil indicado — é o `autor`
    que as funções de escrita esperam. Sem isto, todas as funções
    rebentam em `_validar_autor`.

    Devolve o dict completo (com `id` e `tipo_utilizador`), que é o
    formato que `utilizadores.verificar_permissao` consome.
    """
    return responsaveis.criar(
        nome=nome,
        tipo_utilizador=tipo_utilizador,
        autor=None,  # criação sem validação (bootstrap dos testes)
    )


def _criar_categoria_minima(autor, nome="Categoria Teste"):
    """Cria uma categoria ativa via `despesas.criar_categoria` — o
    caminho normal, não INSERT direto."""
    return despesas.criar_categoria(nome=nome, autor=autor)


def _criar_categoria_compra_stock(autor):
    """A VIA 2 depende da categoria 'Compra de Stock' — semeada na
    migração SQL da BD real, mas a BD de teste nasce vazia. Esta
    função cria-a com o mesmo nome exato, para `_procurar_categoria_
    compra_stock()` a encontrar.
    """
    return despesas.criar_categoria(
        nome="Compra de Stock", autor=autor
    )


# =====================================================================
# 1. Categorias de despesa
# =====================================================================


class TesteCategorias(BaseMySQLTest):
    """CRUD de categorias de despesa — criar, listar, editar,
    desativar, reativar."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_autor("Master")

    def test_criar_categoria_valida(self):
        categoria = despesas.criar_categoria("Água", self.autor)

        self.assertEqual(categoria["nome"], "Água")
        self.assertTrue(categoria["ativo"])
        self.assertTrue(categoria["id"].startswith("CAT-"))

    def test_criar_categoria_nome_vazio_falha(self):
        with self.assertRaises(ValueError):
            despesas.criar_categoria("   ", self.autor)

    def test_criar_categoria_nome_duplicado_falha(self):
        despesas.criar_categoria("Água", self.autor)

        with self.assertRaises(ValueError):
            despesas.criar_categoria("Água", self.autor)

    def test_criar_categoria_duplicado_maiusculas_falha(self):
        despesas.criar_categoria("Água", self.autor)

        with self.assertRaises(ValueError):
            despesas.criar_categoria("ÁGUA", self.autor)

    def test_staff_nao_pode_criar_categoria(self):
        staff = _criar_autor("Staff", nome="Staff Teste")

        with self.assertRaises(ValueError):
            despesas.criar_categoria("Água", staff)

    def test_admin_nao_pode_criar_categoria(self):
        admin = _criar_autor("Admin", nome="Admin Teste")

        with self.assertRaises(ValueError):
            despesas.criar_categoria("Água", admin)

    def test_listar_categorias_ativas_por_omissao(self):
        despesas.criar_categoria("Água", self.autor)
        c2 = despesas.criar_categoria("Luz", self.autor)
        despesas.desativar_categoria(c2["id"], self.autor)

        lista = despesas.listar_categorias()

        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["nome"], "Água")

    def test_listar_categorias_incluindo_inativas(self):
        despesas.criar_categoria("Água", self.autor)
        c2 = despesas.criar_categoria("Luz", self.autor)
        despesas.desativar_categoria(c2["id"], self.autor)

        lista = despesas.listar_categorias(incluir_inativas=True)

        self.assertEqual(len(lista), 2)

    def test_atualizar_categoria_valida(self):
        cat = despesas.criar_categoria("Agua", self.autor)
        atualizada = despesas.atualizar_categoria(
            cat["id"], "Água e Saneamento", self.autor
        )

        self.assertEqual(atualizada["nome"], "Água e Saneamento")

        relida = despesas.procurar_categoria(cat["id"])
        self.assertEqual(relida["nome"], "Água e Saneamento")

    def test_atualizar_categoria_para_nome_duplicado_falha(self):
        despesas.criar_categoria("Água", self.autor)
        luz = despesas.criar_categoria("Luz", self.autor)

        with self.assertRaises(ValueError):
            despesas.atualizar_categoria(luz["id"], "Água", self.autor)

    def test_desativar_e_reativar_categoria(self):
        cat = despesas.criar_categoria("Água", self.autor)

        desativada = despesas.desativar_categoria(cat["id"], self.autor)
        self.assertFalse(desativada["ativo"])

        reativada = despesas.reativar_categoria(cat["id"], self.autor)
        self.assertTrue(reativada["ativo"])

    def test_desativar_categoria_ja_inativa_falha(self):
        cat = despesas.criar_categoria("Água", self.autor)
        despesas.desativar_categoria(cat["id"], self.autor)

        with self.assertRaises(ValueError):
            despesas.desativar_categoria(cat["id"], self.autor)


# =====================================================================
# 2. Fornecedores
# =====================================================================


class TesteFornecedores(BaseMySQLTest):
    """CRUD de fornecedores — criar, listar, editar, desativar,
    reativar. Master E Admin podem gerir (diferente de categorias)."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_autor("Master")

    def test_criar_fornecedor_valido(self):
        forn = despesas.criar_fornecedor(
            "EDP", self.autor, contacto="800 500 505", nif="500123456"
        )

        self.assertEqual(forn["nome"], "EDP")
        self.assertEqual(forn["contacto"], "800 500 505")
        self.assertEqual(forn["nif"], "500123456")
        self.assertTrue(forn["ativo"])
        self.assertTrue(forn["id"].startswith("FOR-"))

    def test_criar_fornecedor_nome_vazio_falha(self):
        with self.assertRaises(ValueError):
            despesas.criar_fornecedor("", self.autor)

    def test_admin_pode_criar_fornecedor(self):
        admin = _criar_autor("Admin", nome="Admin Teste")
        forn = despesas.criar_fornecedor("EDP", admin)

        self.assertEqual(forn["nome"], "EDP")

    def test_staff_nao_pode_criar_fornecedor(self):
        staff = _criar_autor("Staff", nome="Staff Teste")

        with self.assertRaises(ValueError):
            despesas.criar_fornecedor("EDP", staff)

    def test_atualizar_fornecedor_parcial(self):
        forn = despesas.criar_fornecedor("EDP", self.autor)

        atualizado = despesas.atualizar_fornecedor(
            forn["id"], self.autor, contacto="800 500 505"
        )

        self.assertEqual(atualizado["nome"], "EDP")
        self.assertEqual(atualizado["contacto"], "800 500 505")

    def test_atualizar_fornecedor_nome_para_vazio_falha(self):
        forn = despesas.criar_fornecedor("EDP", self.autor)

        with self.assertRaises(ValueError):
            despesas.atualizar_fornecedor(forn["id"], self.autor, nome="")

    def test_desativar_e_reativar_fornecedor(self):
        forn = despesas.criar_fornecedor("EDP", self.autor)

        desativado = despesas.desativar_fornecedor(forn["id"], self.autor)
        self.assertFalse(desativado["ativo"])

        reativado = despesas.reativar_fornecedor(forn["id"], self.autor)
        self.assertTrue(reativado["ativo"])


# =====================================================================
# 3. VIA 1 — despesa manual
# =====================================================================


class TesteVia1(BaseMySQLTest):
    """Despesas manuais — criar, editar valor, marcar paga,
    cancelar."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_autor("Master")
        self.categoria = _criar_categoria_minima(self.autor, "EDP")

    def test_criar_despesa_manual_minima(self):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("45.50"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        self.assertTrue(d["id"].startswith("DSP-"))
        self.assertEqual(d["valor"], Decimal("45.50"))
        self.assertEqual(d["estado"], "pendente")
        self.assertTrue(d["itens_confirmados"])
        self.assertFalse(d["recorrente"])
        self.assertIsNone(d["data_pagamento"])
        self.assertIsNone(d["unidade_id"])

    def test_criar_despesa_manual_valor_negativo_falha(self):
        with self.assertRaises(ValueError):
            despesas.criar_despesa_manual(
                categoria_id=self.categoria["id"],
                valor=Decimal("-10.00"),
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_criar_despesa_manual_categoria_inexistente_falha(self):
        with self.assertRaises(ValueError):
            despesas.criar_despesa_manual(
                categoria_id="CAT-999",
                valor=Decimal("10.00"),
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_criar_despesa_manual_categoria_inativa_falha(self):
        despesas.desativar_categoria(self.categoria["id"], self.autor)

        with self.assertRaises(ValueError):
            despesas.criar_despesa_manual(
                categoria_id=self.categoria["id"],
                valor=Decimal("10.00"),
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_criar_despesa_manual_vencimento_antes_lancamento_falha(self):
        with self.assertRaises(ValueError):
            despesas.criar_despesa_manual(
                categoria_id=self.categoria["id"],
                valor=Decimal("10.00"),
                data_lancamento=date(2026, 6, 1),
                responsavel_id=self.autor["id"],
                autor=self.autor,
                data_vencimento=date(2026, 5, 1),
            )

    def test_staff_nao_pode_criar_despesa(self):
        staff = _criar_autor("Staff", nome="Staff Teste")

        with self.assertRaises(ValueError):
            despesas.criar_despesa_manual(
                categoria_id=self.categoria["id"],
                valor=Decimal("10.00"),
                data_lancamento=date.today(),
                responsavel_id=staff["id"],
                autor=staff,
            )

    def test_editar_valor_despesa_pendente(self):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("10.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        editada = despesas.editar_valor_despesa(
            d["id"], Decimal("25.00"), self.autor
        )

        self.assertEqual(editada["valor"], Decimal("25.00"))

    def test_editar_valor_despesa_paga_falha(self):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("10.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        despesas.marcar_paga(d["id"], date.today(), self.autor)

        with self.assertRaises(ValueError):
            despesas.editar_valor_despesa(
                d["id"], Decimal("25.00"), self.autor
            )

    def test_marcar_paga_despesa_pendente(self):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("10.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        paga = despesas.marcar_paga(d["id"], date.today(), self.autor)

        self.assertEqual(paga["estado"], "paga")
        self.assertEqual(paga["data_pagamento"], date.today())

    def test_marcar_paga_despesa_ja_paga_falha(self):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("10.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        despesas.marcar_paga(d["id"], date.today(), self.autor)

        with self.assertRaises(ValueError):
            despesas.marcar_paga(d["id"], date.today(), self.autor)

    def test_cancelar_despesa_com_motivo(self):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("10.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        cancelada = despesas.cancelar_despesa(
            d["id"], "Erro de lançamento", self.autor
        )

        self.assertEqual(cancelada["estado"], "cancelada")
        self.assertEqual(
            cancelada["motivo_cancelamento"], "Erro de lançamento"
        )
        self.assertEqual(
            cancelada["responsavel_cancelamento_id"], self.autor["id"]
        )

    def test_cancelar_despesa_sem_motivo_falha(self):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("10.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        with self.assertRaises(ValueError):
            despesas.cancelar_despesa(d["id"], "", self.autor)


# =====================================================================
# 4. Divisão por propriedade
# =====================================================================


class TesteDivisaoPorPropriedade(BaseMySQLTest):
    """Dividir uma despesa de valor total por N unidades ativas.
    Usa só a tabela `unidades` (propriedade + unidade) — não precisa
    de clientes nem de contratos."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_autor("Master")
        self.categoria = _criar_categoria_minima(self.autor, "Internet")

        # Import tardio — só este teste precisa de propriedades e
        # unidades, para não puxar dependências nos outros.
        import propriedades
        import unidades

        self.propriedades = propriedades
        self.unidades = unidades

        self.prop = propriedades.criar("Prédio A")

    def _criar_unidade(self, nome):
        return self.unidades.criar(
            propriedade_id=self.prop["id"],
            nome=nome,
            tipo="mensal",
            preco_base=Decimal("250.00"),
            preco_epoca_alta=Decimal("90.00"),
            multa_check_in_tardio=Decimal("20.00"),
        )

    def test_dividir_por_tres_unidades(self):
        self._criar_unidade("A")
        self._criar_unidade("B")
        self._criar_unidade("C")

        resultado = despesas.dividir_despesa_por_propriedade(
            propriedade_id=self.prop["id"],
            valor_total=Decimal("90.00"),
            categoria_id=self.categoria["id"],
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        self.assertEqual(len(resultado), 3)
        for d in resultado:
            self.assertEqual(d["valor"], Decimal("30.00"))
            self.assertEqual(d["estado"], "pendente")
            self.assertTrue(d["unidade_id"])  # preenchido

    def test_dividir_valor_nao_divisivel_arredonda_simples(self):
        # 100 / 3 = 33.3333... → 33.33 por unidade (arredondamento
        # simples). A soma dá 99.99 — a diferença de 1 cêntimo é
        # ACEITE (decisão do handoff, B.5).
        self._criar_unidade("A")
        self._criar_unidade("B")
        self._criar_unidade("C")

        resultado = despesas.dividir_despesa_por_propriedade(
            propriedade_id=self.prop["id"],
            valor_total=Decimal("100.00"),
            categoria_id=self.categoria["id"],
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        for d in resultado:
            self.assertEqual(d["valor"], Decimal("33.33"))

        soma = sum(d["valor"] for d in resultado)
        self.assertEqual(soma, Decimal("99.99"))  # aceita-se

    def test_dividir_sem_unidades_ativas_falha(self):
        # Propriedade existe mas não tem unidades.
        with self.assertRaises(ValueError):
            despesas.dividir_despesa_por_propriedade(
                propriedade_id=self.prop["id"],
                valor_total=Decimal("90.00"),
                categoria_id=self.categoria["id"],
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_dividir_propriedade_inexistente_falha(self):
        with self.assertRaises(ValueError):
            despesas.dividir_despesa_por_propriedade(
                propriedade_id="PRO-999",
                valor_total=Decimal("90.00"),
                categoria_id=self.categoria["id"],
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_dividir_unidade_desativada_nao_conta(self):
        self._criar_unidade("A")
        b = self._criar_unidade("B")
        self._criar_unidade("C")

        self.unidades.desativar(b["id"])

        resultado = despesas.dividir_despesa_por_propriedade(
            propriedade_id=self.prop["id"],
            valor_total=Decimal("60.00"),
            categoria_id=self.categoria["id"],
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        self.assertEqual(len(resultado), 2)
        for d in resultado:
            self.assertEqual(d["valor"], Decimal("30.00"))


# =====================================================================
# 5. VIA 2 — despesa via stock
# =====================================================================


class TesteVia2(BaseMySQLTest):
    """Despesas via stock — criar com itens, confirmar itens,
    verificar que os movimentos são gerados."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_autor("Master")
        # Categoria "Compra de Stock" tem de existir para VIA 2.
        _criar_categoria_compra_stock(self.autor)

    def test_criar_despesa_stock_com_produto_existente(self):
        import estoque

        produto = estoque.criar_produto("Lixívia", "L")

        despesa, itens = despesas.criar_despesa_stock(
            itens=[{"produto_id": produto["id"], "quantidade": 5}],
            valor_total=Decimal("25.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        self.assertEqual(despesa["estado"], "paga")
        self.assertEqual(despesa["data_pagamento"], date.today())
        self.assertFalse(despesa["itens_confirmados"])
        self.assertIsNone(despesa["unidade_id"])

        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["quantidade"], 5)
        self.assertEqual(itens[0]["produto_id"], produto["id"])
        self.assertIsNone(itens[0]["movimento_id"])

    def test_criar_despesa_stock_com_produto_novo(self):
        despesa, itens = despesas.criar_despesa_stock(
            itens=[
                {
                    "produto_id": None,
                    "nome": "Detergente novo",
                    "unidade_medida": "L",
                    "stock_minimo": 3,
                    "tipo_produto": "consumivel",
                    "quantidade": 10,
                }
            ],
            valor_total=Decimal("50.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        self.assertEqual(len(itens), 1)
        self.assertTrue(itens[0]["produto_id"].startswith("PRD-"))

    def test_criar_despesa_stock_categoria_compra_stock_inexistente_falha(self):
        # Sem chamar _criar_categoria_compra_stock, a categoria não
        # existe — a VIA 2 tem de rebentar com mensagem clara.
        import despesas as desp

        # Apaga a categoria compra de stock — vamos "desativá-la"
        # para simular o caso.
        for cat in desp.listar_categorias():
            if cat["nome"] == "Compra de Stock":
                desp.desativar_categoria(cat["id"], self.autor)

        import estoque

        produto = estoque.criar_produto("Lixívia", "L")

        with self.assertRaises(ValueError):
            desp.criar_despesa_stock(
                itens=[{"produto_id": produto["id"], "quantidade": 5}],
                valor_total=Decimal("25.00"),
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_criar_despesa_stock_sem_itens_falha(self):
        with self.assertRaises(ValueError):
            despesas.criar_despesa_stock(
                itens=[],
                valor_total=Decimal("25.00"),
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_criar_despesa_stock_produto_inexistente_falha(self):
        with self.assertRaises(ValueError):
            despesas.criar_despesa_stock(
                itens=[{"produto_id": "PRD-999", "quantidade": 5}],
                valor_total=Decimal("25.00"),
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_criar_despesa_stock_quantidade_zero_falha(self):
        import estoque

        produto = estoque.criar_produto("Lixívia", "L")

        with self.assertRaises(ValueError):
            despesas.criar_despesa_stock(
                itens=[{"produto_id": produto["id"], "quantidade": 0}],
                valor_total=Decimal("25.00"),
                data_lancamento=date.today(),
                responsavel_id=self.autor["id"],
                autor=self.autor,
            )

    def test_confirmar_itens_gera_movimentos_e_marca(self):
        import estoque

        p1 = estoque.criar_produto("Lixívia", "L")
        p2 = estoque.criar_produto("Detergente", "L")

        despesa, itens = despesas.criar_despesa_stock(
            itens=[
                {"produto_id": p1["id"], "quantidade": 5},
                {"produto_id": p2["id"], "quantidade": 3},
            ],
            valor_total=Decimal("30.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )

        # Saldos antes da confirmação: 0 (nada entrou ainda).
        self.assertEqual(estoque.saldo_produto(p1["id"]), 0)
        self.assertEqual(estoque.saldo_produto(p2["id"]), 0)

        despesa_confirmada = despesas.confirmar_itens_despesa(
            despesa["id"], self.autor
        )

        self.assertTrue(despesa_confirmada["itens_confirmados"])
        self.assertEqual(
            despesa_confirmada["itens_confirmados_por_id"],
            self.autor["id"],
        )
        self.assertIsNotNone(
            despesa_confirmada["itens_confirmados_em"]
        )

        # Agora os saldos refletem a entrada.
        self.assertEqual(estoque.saldo_produto(p1["id"]), 5)
        self.assertEqual(estoque.saldo_produto(p2["id"]), 3)

        # Os itens ficaram com movimento_id preenchido.
        itens_relidos = despesas.listar_itens_despesa(despesa["id"])
        for item in itens_relidos:
            self.assertTrue(item["movimento_id"])

    def test_confirmar_duas_vezes_falha(self):
        import estoque

        produto = estoque.criar_produto("Lixívia", "L")

        despesa, _ = despesas.criar_despesa_stock(
            itens=[{"produto_id": produto["id"], "quantidade": 5}],
            valor_total=Decimal("25.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        despesas.confirmar_itens_despesa(despesa["id"], self.autor)

        with self.assertRaises(ValueError):
            despesas.confirmar_itens_despesa(despesa["id"], self.autor)

    def test_movimento_tem_motivo_rastreavel(self):
        import estoque

        produto = estoque.criar_produto("Lixívia", "L")

        despesa, _ = despesas.criar_despesa_stock(
            itens=[{"produto_id": produto["id"], "quantidade": 5}],
            valor_total=Decimal("25.00"),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        despesas.confirmar_itens_despesa(despesa["id"], self.autor)

        movimentos = estoque.listar_movimentos(produto_id=produto["id"])

        self.assertEqual(len(movimentos), 1)
        self.assertEqual(movimentos[0]["tipo"], "entrada")
        self.assertIn(despesa["id"], movimentos[0]["motivo"])


# =====================================================================
# 6. Recorrências
# =====================================================================


class TesteRecorrencias(BaseMySQLTest):
    """Geração automática do lançamento do mês seguinte."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_autor("Master")
        self.categoria = _criar_categoria_minima(self.autor, "EDP")

    def _criar_despesa_recorrente(self, meses_atras=0):
        """Cria uma despesa recorrente há N meses. Se `meses_atras=0`,
        fica no mês atual; se > 0, fica em meses anteriores."""
        hoje = date.today()
        ano = hoje.year
        mes = hoje.month - meses_atras
        while mes <= 0:
            mes += 12
            ano -= 1

        return despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("45.00"),
            data_lancamento=date(ano, mes, 15),
            responsavel_id=self.autor["id"],
            autor=self.autor,
            recorrente=True,
            descricao="Conta EDP mensal",
        )

    def test_sem_recorrentes_nao_gera_nada(self):
        geradas = despesas.gerar_recorrencias_pendentes(self.autor)
        self.assertEqual(geradas, [])

    def test_recorrente_do_mes_atual_nao_duplica(self):
        self._criar_despesa_recorrente(meses_atras=0)

        geradas = despesas.gerar_recorrencias_pendentes(self.autor)

        self.assertEqual(geradas, [])

    def test_recorrente_do_mes_passado_gera_nova(self):
        original = self._criar_despesa_recorrente(meses_atras=1)

        geradas = despesas.gerar_recorrencias_pendentes(self.autor)

        self.assertEqual(len(geradas), 1)
        nova = geradas[0]
        self.assertEqual(nova["valor"], Decimal("0.00"))
        self.assertEqual(nova["estado"], "pendente")
        self.assertEqual(nova["despesa_origem_id"], original["id"])
        self.assertEqual(nova["categoria_id"], original["categoria_id"])
        self.assertTrue(nova["recorrente"])

    def test_recorrente_nao_espera_pagamento(self):
        """Uma recorrente pendente (não paga) do mês passado também
        gera a deste mês — não se espera pelo pagamento (decisão do
        handoff, B.6)."""
        original = self._criar_despesa_recorrente(meses_atras=1)
        # `original` nasce pendente — não se marca paga.

        geradas = despesas.gerar_recorrencias_pendentes(self.autor)

        self.assertEqual(len(geradas), 1)

    def test_gerar_duas_vezes_nao_duplica(self):
        self._criar_despesa_recorrente(meses_atras=1)

        primeira = despesas.gerar_recorrencias_pendentes(self.autor)
        self.assertEqual(len(primeira), 1)

        segunda = despesas.gerar_recorrencias_pendentes(self.autor)
        self.assertEqual(segunda, [])

    def test_staff_nao_pode_gerar_recorrencias(self):
        staff = _criar_autor("Staff", nome="Staff Teste")

        with self.assertRaises(ValueError):
            despesas.gerar_recorrencias_pendentes(staff)


# =====================================================================
# 7. esta_vencida
# =====================================================================


class TesteEstaVencida(BaseMySQLTest):
    """Cálculo de 'vencida' — em tempo de leitura, sem estado novo."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_autor("Master")
        self.categoria = _criar_categoria_minima(self.autor, "EDP")

    def _criar(self, data_vencimento, marcar_paga=False):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("10.00"),
            data_lancamento=date.today() - timedelta(days=30),
            responsavel_id=self.autor["id"],
            autor=self.autor,
            data_vencimento=data_vencimento,
        )
        if marcar_paga:
            d = despesas.marcar_paga(d["id"], date.today(), self.autor)
        return d

    def test_pendente_com_vencimento_no_passado_e_vencida(self):
        d = self._criar(date.today() - timedelta(days=1))
        self.assertTrue(despesas.esta_vencida(d))

    def test_pendente_com_vencimento_no_futuro_nao_e_vencida(self):
        d = self._criar(date.today() + timedelta(days=1))
        self.assertFalse(despesas.esta_vencida(d))

    def test_pendente_sem_vencimento_nao_e_vencida(self):
        d = self._criar(None)
        self.assertFalse(despesas.esta_vencida(d))

    def test_paga_com_vencimento_no_passado_nao_e_vencida(self):
        d = self._criar(
            date.today() - timedelta(days=1), marcar_paga=True
        )
        self.assertFalse(despesas.esta_vencida(d))

    def test_cancelada_nunca_e_vencida(self):
        d = self._criar(date.today() - timedelta(days=1))
        d = despesas.cancelar_despesa(d["id"], "erro", self.autor)
        self.assertFalse(despesas.esta_vencida(d))


# =====================================================================
# 8. Leituras gerais
# =====================================================================


class TesteLeituras(BaseMySQLTest):
    """Filtros de listar_despesas e leituras simples."""

    def setUp(self):
        super().setUp()
        self.autor = _criar_autor("Master")
        self.categoria = _criar_categoria_minima(self.autor, "EDP")

    def _criar(self, valor, estado_alvo="pendente"):
        d = despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal(valor),
            data_lancamento=date.today(),
            responsavel_id=self.autor["id"],
            autor=self.autor,
        )
        if estado_alvo == "paga":
            d = despesas.marcar_paga(d["id"], date.today(), self.autor)
        elif estado_alvo == "cancelada":
            d = despesas.cancelar_despesa(d["id"], "erro", self.autor)
        return d

    def test_listar_despesas_sem_filtro(self):
        self._criar("10.00")
        self._criar("20.00")
        self._criar("30.00")

        lista = despesas.listar_despesas()

        self.assertEqual(len(lista), 3)

    def test_listar_despesas_filtro_estado(self):
        self._criar("10.00", "pendente")
        self._criar("20.00", "paga")
        self._criar("30.00", "cancelada")

        pendentes = despesas.listar_despesas(estado="pendente")

        self.assertEqual(len(pendentes), 1)
        self.assertEqual(pendentes[0]["valor"], Decimal("10.00"))

    def test_listar_despesas_filtro_vencidas(self):
        hoje = date.today()

        despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("10.00"),
            data_lancamento=hoje - timedelta(days=30),
            responsavel_id=self.autor["id"],
            autor=self.autor,
            data_vencimento=hoje - timedelta(days=1),  # vencida
        )
        despesas.criar_despesa_manual(
            categoria_id=self.categoria["id"],
            valor=Decimal("20.00"),
            data_lancamento=hoje,
            responsavel_id=self.autor["id"],
            autor=self.autor,
            data_vencimento=hoje + timedelta(days=30),  # futura
        )

        so_vencidas = despesas.listar_despesas(incluir_vencidas=True)
        self.assertEqual(len(so_vencidas), 1)
        self.assertEqual(so_vencidas[0]["valor"], Decimal("10.00"))

        nao_vencidas = despesas.listar_despesas(incluir_vencidas=False)
        self.assertEqual(len(nao_vencidas), 1)
        self.assertEqual(nao_vencidas[0]["valor"], Decimal("20.00"))

    def test_procurar_despesa_inexistente_devolve_none(self):
        self.assertIsNone(despesas.procurar_despesa("DSP-999"))

    def test_listar_itens_despesa_vazia_devolve_lista_vazia(self):
        d = self._criar("10.00")
        itens = despesas.listar_itens_despesa(d["id"])
        self.assertEqual(itens, [])


# =====================================================================
# Runner manual
# =====================================================================


if __name__ == "__main__":
    unittest.main(verbosity=2)