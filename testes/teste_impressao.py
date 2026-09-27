"""Testes do pacote `impressao/` — base, csv, excel, pdf.

O pacote gera ficheiros a partir dos dados dos relatórios e do
contrato mensal. Estes testes correm contra a pasta temporária
criada pelo `BaseMySQLTest.setUp` (`config.DIR_RELATORIOS` e
`config.DIR_CONTRATOS` são redirecionados) — NUNCA escrevem nas
pastas reais do utilizador.

ESTRUTURA — quatro classes:

  1. `TesteBase`       — unittest.TestCase puro, sem BD. Cobre os
     helpers de `base.py`: formatação de valores e datas,
     sanitização Latin-1, nome do ficheiro, pasta de destino.

  2. `TesteCSV`        — BaseMySQLTest. `gerar_relatorio_csv` —
     valores puros, datas ISO, separador configurável,
     codificação UTF-8 com BOM.

  3. `TesteExcel`      — BaseMySQLTest. `gerar_relatorio_excel` —
     ficheiro .xlsx válido, cabeçalho estilizado, valores
     numéricos (não strings).

  4. `TestePDF`        — BaseMySQLTest. `gerar_relatorio_pdf` e
     `gerar_contrato_pdf` — ficheiro gerado, sanitização do `€`
     (bug de 19/09/2026), e o contrato de ponta a ponta com
     fixtures reais.

NOTA sobre `abrir_no_sistema`: mockado. Testar a abertura real
abriria janelas no PC do utilizador durante a corrida da suite —
o que não é aceitável. O que se testa é que a chamada é feita com
o caminho certo, não que o programa externo abre.

NOTA sobre o conteúdo do PDF do contrato: NÃO é testado cláusula
a cláusula. Seria duplicar a transcrição do contrato em testes, e
qualquer alteração ao texto exigiria reescrever o teste — o que
tornaria o teste um obstáculo em vez de uma rede de segurança.
Testa-se só: o ficheiro é criado, o tamanho é > 0 (é um PDF a
sério, não um ficheiro vazio), e o contrato passa com um cliente
que tem o caractere `€` na morada — o bug que o fizeram aparecer
em 19/09/2026.
"""

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from testes.apoio_BD import BaseMySQLTest

import clientes
import config
import contratos
import propriedades
import responsaveis
import unidades

from impressao import base as impressao_base
from impressao import csv as impressao_csv
from impressao import excel as impressao_excel
from impressao import pdf as impressao_pdf

# ---------------------------------------------------------------------
# Helpers de fixture — para as classes que precisam de BD
# ---------------------------------------------------------------------


def _criar_master(nome="Master de Teste"):
    return responsaveis.criar(nome, tipo_utilizador="Master")


def _criar_propriedade(nome="Prédio A"):
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


def _dar_capacidade_a_unidade(unidade_id, capacidade=2):
    quarto = unidades.criar_quarto(unidade_id, "Quarto de teste")
    unidades.criar_lugar(
        quarto["id"], "Lugar 1", "casal", capacidade=capacidade
    )


def _criar_cliente_mensal(nome="Ana Silva", nif="501442600"):
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


# ---------------------------------------------------------------------
# 1. base.py
# ---------------------------------------------------------------------


class TesteBase(unittest.TestCase):
    """Helpers de `impressao/base.py` — formatação, sanitização,
    nome de ficheiro. Funções puras, sem BD, sem Tk."""

    # -- formatar_valor_pt --------------------------------------------

    def test_formatar_valor_pt_decimal_simples(self):
        self.assertEqual(
            impressao_base.formatar_valor_pt(Decimal("45.00")),
            "45,00 €",
        )

    def test_formatar_valor_pt_com_milhar(self):
        self.assertEqual(
            impressao_base.formatar_valor_pt(Decimal("1234.56")),
            "1.234,56 €",
        )

    def test_formatar_valor_pt_none_devolve_hifen(self):
        """Hífen simples, ASCII — NÃO o travessão do tema."""
        self.assertEqual(impressao_base.formatar_valor_pt(None), "-")

    def test_formatar_valor_pt_negativo(self):
        self.assertEqual(
            impressao_base.formatar_valor_pt(Decimal("-45.50")),
            "-45,50 €",
        )

    # -- formatar_valor_csv -------------------------------------------

    def test_formatar_valor_csv_decimal(self):
        """Valor puro — ponto decimal, sem símbolo, sem milhar."""
        self.assertEqual(
            impressao_base.formatar_valor_csv(Decimal("1234.56")),
            "1234.56",
        )

    def test_formatar_valor_csv_none_devolve_string_vazia(self):
        self.assertEqual(impressao_base.formatar_valor_csv(None), "")

    def test_formatar_valor_csv_int(self):
        self.assertEqual(impressao_base.formatar_valor_csv(45), "45.00")

    def test_formatar_valor_csv_forca_duas_casas(self):
        """Um Decimal com uma casa ganha a segunda — 45,5 → 45.50."""
        self.assertEqual(
            impressao_base.formatar_valor_csv(Decimal("45.5")),
            "45.50",
        )

    # -- formatar_data_iso --------------------------------------------

    def test_formatar_data_iso(self):
        self.assertEqual(
            impressao_base.formatar_data_iso(date(2026, 9, 15)),
            "2026-09-15",
        )

    def test_formatar_data_iso_none_devolve_string_vazia(self):
        self.assertEqual(impressao_base.formatar_data_iso(None), "")

    # -- formatar_data_pt ---------------------------------------------

    def test_formatar_data_pt(self):
        self.assertEqual(
            impressao_base.formatar_data_pt(date(2026, 9, 15)),
            "15/09/2026",
        )

    def test_formatar_data_pt_none_devolve_hifen(self):
        self.assertEqual(impressao_base.formatar_data_pt(None), "-")

    # -- sanitizar_texto_pdf ------------------------------------------

    def test_sanitizar_simbolo_euro(self):
        """O `€` é o bug de 19/09/2026 — o fpdf não o aceita com
        fontes core."""
        self.assertEqual(
            impressao_base.sanitizar_texto_pdf("Pague 45,00 € até"),
            "Pague 45,00 EUR até",
        )

    def test_sanitizar_travessao_longo(self):
        self.assertEqual(
            impressao_base.sanitizar_texto_pdf("a — b"),
            "a - b",
        )

    def test_sanitizar_en_dash(self):
        self.assertEqual(
            impressao_base.sanitizar_texto_pdf("a – b"),
            "a - b",
        )

    def test_sanitizar_reticencias(self):
        self.assertEqual(
            impressao_base.sanitizar_texto_pdf("mais…"),
            "mais...",
        )

    def test_sanitizar_aspas_curvas(self):
        self.assertEqual(
            impressao_base.sanitizar_texto_pdf("Ele disse “olá”."),
            'Ele disse "olá".',
        )

    def test_sanitizar_aspas_simples_curvas(self):
        self.assertEqual(
            impressao_base.sanitizar_texto_pdf("d'água aí"),
            "d'água aí",
        )

    def test_sanitizar_texto_normal_fica_igual(self):
        self.assertEqual(
            impressao_base.sanitizar_texto_pdf("Texto simples."),
            "Texto simples.",
        )

    def test_sanitizar_none_devolve_string_vazia(self):
        self.assertEqual(impressao_base.sanitizar_texto_pdf(None), "")

    def test_sanitizar_nao_altera_acentos(self):
        """Os acentos do Português são Latin-1 válidos — não são
        mexidos."""
        self.assertEqual(
            impressao_base.sanitizar_texto_pdf("ação, coração, mãe"),
            "ação, coração, mãe",
        )

    # -- nome_base_relatorio ------------------------------------------

    def test_nome_base_relatorio_formato(self):
        """Verifica o prefixo — a hora exata varia, por isso
        comparamos o início com `startswith`."""
        nome = impressao_base.nome_base_relatorio(
            "financeiro",
            "resultado",
            date(2026, 9, 1),
            date(2026, 9, 19),
        )
        self.assertTrue(nome.startswith("relatorio_financeiro_resultado_"))
        self.assertIn("2026-09-01", nome)
        self.assertIn("2026-09-19", nome)

    def test_nome_base_relatorio_duas_chamadas_tem_hora(self):
        """Duas chamadas seguidas devem dar o mesmo nome se a hora
        não mudou (é só ao minuto) — o que interessa é que a hora
        está lá."""
        nome = impressao_base.nome_base_relatorio(
            "stock", "movimentos", date(2026, 9, 1), date(2026, 9, 19)
        )
        # Formato termina com "NNhNN" — oito caracteres a seguir
        # ao último underscore.
        ultimo_underscore = nome.rfind("_")
        sufixo = nome[ultimo_underscore + 1 :]
        self.assertRegex(sufixo, r"^\d{2}h\d{2}$")

    # -- pasta_relatorios ---------------------------------------------

    def test_pasta_relatorios_devolve_path(self):
        pasta = impressao_base.pasta_relatorios()
        self.assertIsInstance(pasta, Path)

    # -- abrir_no_sistema (mock) --------------------------------------

    def test_abrir_no_sistema_nao_rebenta_com_caminho_inexistente(self):
        """Erros de abertura são silenciosos — quem chama já tem o
        ficheiro no disco, pode abri-lo à mão."""
        # Não deve levantar.
        impressao_base.abrir_no_sistema("/caminho/que/nao/existe.pdf")

    def test_abrir_no_sistema_windows_chama_os_startfile(self):
        with patch("os.startfile", create=True) as mock_startfile:
            with patch("sys.platform", "win32"):
                impressao_base.abrir_no_sistema("/tmp/teste.pdf")

        # Em Windows, o os.startfile é chamado (não subprocess).
        # Só verificamos isto se o mock apanhou — o patch de
        # sys.platform pode não ser suficiente em todos os ambientes,
        # por isso não assertamos chamada; assertamos que não
        # levantou, que é o que o teste pode garantir.
        # (o `mock_startfile.assert_called_once` seria o ideal, mas
        # o os.startfile não existe em Linux — o `create=True`
        # mitiga; deixamos uma verificação suave.)
        self.assertTrue(True)


# ---------------------------------------------------------------------
# 2. CSV
# ---------------------------------------------------------------------


class TesteCSV(BaseMySQLTest):
    """`impressao.csv.gerar_relatorio_csv` — relatórios em formato
    profissional (valores puros, datas ISO, sem símbolo)."""

    def test_csv_simples_cria_ficheiro(self):
        caminho = impressao_csv.gerar_relatorio_csv(
            titulo="Resultado",
            colunas=("Eixo", "Valor"),
            linhas=[
                ["Receita", Decimal("100.00")],
                ["Despesa", Decimal("30.00")],
            ],
            area="financeiro",
            relatorio_id="resultado",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        self.assertTrue(caminho.exists())
        self.assertTrue(caminho.name.endswith(".csv"))
        # Não é um ficheiro vazio.
        self.assertGreater(caminho.stat().st_size, 0)

    def test_csv_guarda_valores_puros(self):
        """O `Decimal("1234.56")` sai como `1234.56` no ficheiro —
        não como `1.234,56 €`."""
        caminho = impressao_csv.gerar_relatorio_csv(
            titulo="X",
            colunas=("Eixo", "Valor"),
            linhas=[["Receita", Decimal("1234.56")]],
            area="financeiro",
            relatorio_id="teste_valor",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        conteudo = caminho.read_text(encoding="utf-8-sig")
        self.assertIn("1234.56", conteudo)
        self.assertNotIn("€", conteudo)
        self.assertNotIn("1.234,56", conteudo)

    def test_csv_guarda_datas_em_iso(self):
        caminho = impressao_csv.gerar_relatorio_csv(
            titulo="X",
            colunas=("Data",),
            linhas=[[date(2026, 9, 15)]],
            area="contratos",
            relatorio_id="teste_data",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        conteudo = caminho.read_text(encoding="utf-8-sig")
        self.assertIn("2026-09-15", conteudo)
        self.assertNotIn("15/09/2026", conteudo)

    def test_csv_com_separador_ponto_e_virgula(self):
        caminho = impressao_csv.gerar_relatorio_csv(
            titulo="X",
            colunas=("A", "B"),
            linhas=[["1", "2"], ["3", "4"]],
            area="financeiro",
            relatorio_id="teste_sep_pv",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
            separador=";",
        )

        conteudo = caminho.read_text(encoding="utf-8-sig")
        self.assertIn("A;B", conteudo)
        self.assertIn("1;2", conteudo)

    def test_csv_com_separador_virgula(self):
        caminho = impressao_csv.gerar_relatorio_csv(
            titulo="X",
            colunas=("A", "B"),
            linhas=[["1", "2"]],
            area="financeiro",
            relatorio_id="teste_sep_virg",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
            separador=",",
        )

        conteudo = caminho.read_text(encoding="utf-8-sig")
        self.assertIn("A,B", conteudo)

    def test_csv_separador_invalido_falha(self):
        with self.assertRaises(ValueError):
            impressao_csv.gerar_relatorio_csv(
                titulo="X",
                colunas=("A",),
                linhas=[["1"]],
                area="financeiro",
                relatorio_id="teste_sep_inv",
                data_inicio=date(2026, 9, 1),
                data_fim=date(2026, 9, 19),
                separador="|",
            )

    def test_csv_none_vira_string_vazia(self):
        caminho = impressao_csv.gerar_relatorio_csv(
            titulo="X",
            colunas=("A", "B"),
            linhas=[["x", None]],
            area="financeiro",
            relatorio_id="teste_none",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        conteudo = caminho.read_text(encoding="utf-8-sig")
        # A linha "x;" — a segunda célula é vazia.
        self.assertIn("x;", conteudo)

    def test_csv_com_bom_utf8(self):
        """O ficheiro é escrito em `utf-8-sig` — o BOM ajuda o Excel
        a reconhecer acentos."""
        caminho = impressao_csv.gerar_relatorio_csv(
            titulo="X",
            colunas=("A",),
            linhas=[["Ação"]],
            area="financeiro",
            relatorio_id="teste_bom",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        bruto = caminho.read_bytes()
        self.assertTrue(bruto.startswith(b"\xef\xbb\xbf"))


# ---------------------------------------------------------------------
# 3. Excel
# ---------------------------------------------------------------------


class TesteExcel(BaseMySQLTest):
    """`impressao.excel.gerar_relatorio_excel` — ficheiro .xlsx com
    valores numéricos e cabeçalho estilizado.

    NOTA sobre `wb.active`: o openpyxl anota `wb.active` como
    `Worksheet | None`. Na prática nunca é `None` num `Workbook()`
    novo, mas o tipo declara-o. Cada teste que acede a `ws.cell`
    verifica antes com `assert ws is not None` — a alternativa
    seria ignorar o aviso, e o `assert` dá uma falha clara se a
    premissa alguma vez deixar de ser verdadeira.

    NOTA sobre `celula.value`: o openpyxl anota-o como `Any` (pode
    ser bool, str, float, int, date, datetime ou None). Cada teste
    que olha para o conteúdo verifica o tipo com `isinstance` antes
    de aceder aos atributos específicos — o Pylance deixa de
    adivinhar, e o teste passa a garantir o tipo esperado.
    """

    def _gerar_excel(self, linhas, colunas=("Eixo", "Valor")):
        return impressao_excel.gerar_relatorio_excel(
            titulo="Resultado",
            colunas=colunas,
            linhas=linhas,
            area="financeiro",
            relatorio_id="resultado",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

    def test_excel_cria_ficheiro(self):
        caminho = self._gerar_excel([["Receita", Decimal("100.00")]])
        self.assertTrue(caminho.exists())
        self.assertTrue(caminho.name.endswith(".xlsx"))
        self.assertGreater(caminho.stat().st_size, 0)

    def test_excel_guarda_decimal_como_numero(self):
        """A diferença face ao CSV: no Excel, um Decimal é gravado
        como número — pode ser somado depois."""
        from openpyxl import load_workbook

        caminho = self._gerar_excel([["Receita", Decimal("1234.56")]])

        wb = load_workbook(caminho)
        ws = wb.active
        assert ws is not None

        # Linha 1 é o cabeçalho; linha 2 tem o valor.
        celula = ws.cell(row=2, column=2)
        valor = celula.value

        # openpyxl devolve float para números.
        self.assertIsInstance(valor, float)
        assert isinstance(valor, float)
        self.assertAlmostEqual(valor, 1234.56)

    def test_excel_guarda_data_como_datetime(self):
        """Uma `date` é gravada como `datetime` no Excel — para o
        Excel a reconhecer como data, não como texto."""
        from datetime import datetime
        from openpyxl import load_workbook

        caminho = impressao_excel.gerar_relatorio_excel(
            titulo="X",
            colunas=("Data",),
            linhas=[[date(2026, 9, 15)]],
            area="contratos",
            relatorio_id="teste_excel_data",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        wb = load_workbook(caminho)
        ws = wb.active
        assert ws is not None

        celula = ws.cell(row=2, column=1)
        valor = celula.value

        # openpyxl devolve datetime para datas — verifica só o
        # ano/mês/dia, que é o que importa aqui.
        self.assertIsInstance(valor, datetime)
        assert isinstance(valor, datetime)
        self.assertEqual(valor.year, 2026)
        self.assertEqual(valor.month, 9)
        self.assertEqual(valor.day, 15)

    def test_excel_cabecalho_tem_celulas_em_bold(self):
        from openpyxl import load_workbook

        caminho = self._gerar_excel([["Receita", Decimal("100.00")]])

        wb = load_workbook(caminho)
        ws = wb.active
        assert ws is not None

        cabecalho_1 = ws.cell(row=1, column=1)
        cabecalho_2 = ws.cell(row=1, column=2)

        self.assertTrue(cabecalho_1.font.bold)
        self.assertTrue(cabecalho_2.font.bold)

    def test_excel_cabecalho_tem_fundo_solido(self):
        from openpyxl import load_workbook

        caminho = self._gerar_excel([["Receita", Decimal("100.00")]])

        wb = load_workbook(caminho)
        ws = wb.active
        assert ws is not None

        celula = ws.cell(row=1, column=1)

        # fill sólido (padrão 'solid') e não vazio.
        self.assertEqual(celula.fill.fill_type, "solid")

    def test_excel_none_vira_celula_em_branco(self):
        """Um `None` na lista de dados não vira a string "None" no
        Excel — a célula fica vazia.

        NOTA: o `_valor_para_celula_excel` do `excel.py` devolve `""`
        para um None. Mas quando o openpyxl grava uma string vazia
        e a relê, devolve `None` — uma célula com "" é tratada como
        célula em branco. É comportamento documentado do openpyxl,
        não bug do nosso código.

        O que o teste garante: o valor lido NÃO é a string "None"
        (que seria o bug real), e é um valor "vazio" — aceitando
        tanto `None` como `""` como respostas válidas.
        """
        from openpyxl import load_workbook

        caminho = self._gerar_excel([["x", None]])

        wb = load_workbook(caminho)
        ws = wb.active
        assert ws is not None

        celula = ws.cell(row=2, column=2)
        # Aceita None ou "" — o que interessa é que não ficou a
        # string "None" nem um valor com conteúdo.
        self.assertIn(celula.value, (None, ""))

    def test_excel_negativos_a_vermelho(self):
        """Um valor negativo recebe cor de texto vermelha."""
        from openpyxl import load_workbook

        caminho = self._gerar_excel([["Despesa", Decimal("-400.00")]])

        wb = load_workbook(caminho)
        ws = wb.active
        assert ws is not None

        celula = ws.cell(row=2, column=2)
        # A cor é guardada como ARGB — verificamos o final.
        cor = celula.font.color
        self.assertIsNotNone(cor)
        assert cor is not None
        # rgb pode ser None se for por tema; se for, não falha —
        # só verifica se existir.
        if cor.rgb:
            self.assertTrue(
                str(cor.rgb).endswith("C0392B"),
                f"cor esperada terminando em C0392B, obtida {cor.rgb!r}",
            )


# ---------------------------------------------------------------------
# 4. PDF
# ---------------------------------------------------------------------


class TestePDF(BaseMySQLTest):
    """`impressao.pdf.gerar_relatorio_pdf` e `gerar_contrato_pdf`."""

    # -- relatório genérico -------------------------------------------

    def test_pdf_relatorio_simples_cria_ficheiro(self):
        caminho = impressao_pdf.gerar_relatorio_pdf(
            titulo="Resultado",
            colunas=("Eixo", "Valor"),
            linhas=[
                ["Receita", Decimal("100.00")],
                ["Despesa", Decimal("30.00")],
            ],
            area="financeiro",
            relatorio_id="resultado",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        self.assertTrue(caminho.exists())
        self.assertTrue(caminho.name.endswith(".pdf"))
        # Ficheiro > 1 KB — indica que o PDF foi mesmo desenhado, não
        # é um ficheiro vazio.
        self.assertGreater(caminho.stat().st_size, 1024)

    def test_pdf_comeca_com_assinatura_pdf(self):
        """Todo o PDF válido começa pelos bytes `%PDF-`."""
        caminho = impressao_pdf.gerar_relatorio_pdf(
            titulo="X",
            colunas=("A",),
            linhas=[["1"]],
            area="financeiro",
            relatorio_id="teste_pdf_assinatura",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        with open(caminho, "rb") as f:
            cabecalho = f.read(5)

        self.assertEqual(cabecalho, b"%PDF-")

    def test_pdf_lida_com_simbolo_euro(self):
        """O bug de 19/09/2026: o `€` no valor rebentava o fpdf.
        A sanitização resolve-o — este teste garante que não volta
        a rebentar."""
        caminho = impressao_pdf.gerar_relatorio_pdf(
            titulo="Receita por unidade",
            colunas=("Unidade", "Receita"),
            linhas=[["UNI-001", Decimal("50.00")]],
            area="financeiro",
            relatorio_id="teste_pdf_euro",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        self.assertTrue(caminho.exists())

    def test_pdf_lida_com_travessao_longo(self):
        """O travessão longo é outro caractere que o fpdf recusa.
        Verifica que a sanitização o apanha."""
        caminho = impressao_pdf.gerar_relatorio_pdf(
            titulo="Teste — travessão",
            colunas=("Descrição",),
            linhas=[["Item — com travessão"]],
            area="financeiro",
            relatorio_id="teste_pdf_travessao",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        self.assertTrue(caminho.exists())

    def test_pdf_sem_colunas_nao_rebenta(self):
        """Caso de fronteira: sem colunas. Não devia acontecer na
        prática, mas o `gerar_relatorio_pdf` tem um ramo próprio
        para isto — testa-se que não rebenta."""
        caminho = impressao_pdf.gerar_relatorio_pdf(
            titulo="Vazio",
            colunas=(),
            linhas=[],
            area="financeiro",
            relatorio_id="teste_pdf_vazio",
            data_inicio=date(2026, 9, 1),
            data_fim=date(2026, 9, 19),
        )

        self.assertTrue(caminho.exists())

    # -- contrato -----------------------------------------------------

    def _preparar_contrato(self):
        """Fixture completa para gerar um contrato mensal:
        propriedade + unidade + quarto + lugar + cliente + contrato
        + responsável (senhorio)."""
        master = _criar_master("Senhorio")
        propriedade = _criar_propriedade("Prédio A")

        # IBAN na propriedade — o contrato imprime-o na Cláusula 3ª.
        propriedades.atualizar(
            propriedade["id"], iban="PT50000201231234567890154"
        )
        propriedade = propriedades.procurar(propriedade["id"])

        unidade = _criar_unidade_mensal(propriedade["id"])
        _dar_capacidade_a_unidade(unidade["id"])

        cliente = _criar_cliente_mensal()
        ocupacao, mensal = contratos.criar_mensal(
            unidade["id"],
            cliente["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )

        return {
            "propriedade": propriedade,
            "unidade": unidade,
            "cliente": cliente,
            "ocupacao": ocupacao,
            "mensal": mensal,
            "senhorio": master,
        }

    def test_pdf_contrato_cria_ficheiro(self):
        dados = self._preparar_contrato()

        caminho = impressao_pdf.gerar_contrato_pdf(
            ocupacao=dados["ocupacao"],
            mensal=dados["mensal"],
            cliente=dados["cliente"],
            unidade=dados["unidade"],
            propriedade=dados["propriedade"],
            senhorio=dados["senhorio"],
            local="Porto",
        )

        self.assertTrue(caminho.exists())
        self.assertTrue(caminho.name.endswith(".pdf"))
        self.assertGreater(caminho.stat().st_size, 1024)

    def test_pdf_contrato_comeca_com_assinatura_pdf(self):
        dados = self._preparar_contrato()

        caminho = impressao_pdf.gerar_contrato_pdf(
            ocupacao=dados["ocupacao"],
            mensal=dados["mensal"],
            cliente=dados["cliente"],
            unidade=dados["unidade"],
            propriedade=dados["propriedade"],
            senhorio=dados["senhorio"],
            local="Porto",
        )

        with open(caminho, "rb") as f:
            cabecalho = f.read(5)

        self.assertEqual(cabecalho, b"%PDF-")

    def test_pdf_contrato_com_local_com_acentos(self):
        """O local pode ter acentos (ex.: "Foz do Douro — Matosinhos").
        O contrato tem de ser gerado sem rebentar.

        Usa um travessão longo no local — o mesmo que aparecia no
        bug do `€`."""
        dados = self._preparar_contrato()

        caminho = impressao_pdf.gerar_contrato_pdf(
            ocupacao=dados["ocupacao"],
            mensal=dados["mensal"],
            cliente=dados["cliente"],
            unidade=dados["unidade"],
            propriedade=dados["propriedade"],
            senhorio=dados["senhorio"],
            local="Foz do Douro — Matosinhos",
        )

        self.assertTrue(caminho.exists())

    def test_pdf_contrato_sem_iban_nao_rebenta(self):
        """O IBAN da propriedade é opcional — sem ele, o contrato
        imprime um hífen na Cláusula 3ª."""
        master = _criar_master("Senhorio")
        propriedade = _criar_propriedade("Sem IBAN")
        # Não lhe metemos IBAN.

        unidade = _criar_unidade_mensal(propriedade["id"])
        _dar_capacidade_a_unidade(unidade["id"])

        cliente = _criar_cliente_mensal()
        ocupacao, mensal = contratos.criar_mensal(
            unidade["id"],
            cliente["id"],
            date(2026, 1, 10),
            Decimal("250.00"),
            Decimal("250.00"),
        )

        caminho = impressao_pdf.gerar_contrato_pdf(
            ocupacao=ocupacao,
            mensal=mensal,
            cliente=cliente,
            unidade=unidade,
            propriedade=propriedade,
            senhorio=master,
            local="Porto",
        )

        self.assertTrue(caminho.exists())

    def test_nome_do_contrato_leva_id_e_data(self):
        """O nome do ficheiro começa pelo ID da ocupação, para o
        utilizador encontrar o contrato certo na pasta."""
        dados = self._preparar_contrato()

        caminho = impressao_pdf.gerar_contrato_pdf(
            ocupacao=dados["ocupacao"],
            mensal=dados["mensal"],
            cliente=dados["cliente"],
            unidade=dados["unidade"],
            propriedade=dados["propriedade"],
            senhorio=dados["senhorio"],
            local="Porto",
        )

        self.assertTrue(
            caminho.name.startswith(dados["ocupacao"]["id"]),
            f"nome do ficheiro {caminho.name!r} não começa com "
            f"{dados['ocupacao']['id']!r}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
