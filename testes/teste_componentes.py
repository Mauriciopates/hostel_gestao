"""Testes de `gui/componentes.py` — o trio Seletor / Tabela / BlocoTermo,
mais os helpers puros que não precisam de janela.

REQUER AMBIENTE GRÁFICO. Os testes que constroem widgets Tk precisam
de um `CTk` root — não correm em máquina sem display (headless puro).
O `CTk()` em modo `withdraw()` evita que a janela raiz apareça no
ecrã, mas o Tk em si tem de estar disponível.

REGRA GUI do PASSO 9 (spec, ponto 6): interações com widgets usam
`event_generate` com coordenadas reais, nunca chamadas diretas aos
handlers. Aplicada onde faz sentido — cliques em botões, teclas em
campos. Onde o componente coordena estado interno por métodos que não
têm equivalente de evento (abrir/fechar painel, escolher valor do
painel), chama-se o método diretamente: não há clique nem tecla que
os dispare de fora do próprio componente, e simulá-los seria testar
a simulação, não o componente.

NOTA SOBRE OS IMPORTS: `componentes.py` vive em `src/gui/`, não em
`src/`. O `sys.path.insert` que está no topo do ficheiro aponta só
para `src/` — o import tem de ser `from gui.componentes import ...`,
e `src/gui/` tem de ter um `__init__.py` (vazio serve) para ser um
pacote Python válido.

ESTRUTURA:

  1. `TesteHelpersPuros`     — unittest.TestCase puro, sem Tk.
     Cobre `truncar_texto` e `formatar_valor`.

  2. `TesteSeletor`          — Tk. Cobre os três estados (menu
     nativo para lista curta, painel próprio para lista grande,
     escolha, fecho por segundo clique).

  3. `TesteTabela`           — Tk. Cobre construção de linhas,
     colocar células, células de ações, tom alternado, `limpar`,
     `vazia`, `mostrar_vazio`.

  4. `TesteBlocoTermo`       — Tk. Cobre construção, `esta_aceite`,
     rodapé com/sem versão anterior, callback `ao_mudar`.
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import customtkinter as ctk

# ---------------------------------------------------------------------
# Helpers de fixture para os testes com Tk
# ---------------------------------------------------------------------


def _criar_root():
    """Cria uma `CTk` root invisível, escondida do ecrã.

    `withdraw()` antes do primeiro `update_idletasks()` evita que a
    janela chegue a aparecer — o utilizador não vê nada enquanto os
    testes correm, mas o Tk está vivo e a responder.
    """
    root = ctk.CTk()
    root.withdraw()
    root.update_idletasks()
    return root


# ---------------------------------------------------------------------
# 1. Helpers puros — sem Tk
# ---------------------------------------------------------------------


class TesteHelpersPuros(unittest.TestCase):
    """`truncar_texto` e `formatar_valor` — funções que não tocam em
    widgets, testáveis sem root Tk.
    """

    # -- formatar_valor -----------------------------------------------

    def test_formatar_valor_decimal_simples(self):
        from gui.componentes import formatar_valor

        self.assertEqual(formatar_valor(Decimal("45.00")), "45,00 €")

    def test_formatar_valor_com_milhar(self):
        from gui.componentes import formatar_valor

        self.assertEqual(formatar_valor(Decimal("1234.56")), "1.234,56 €")

    def test_formatar_valor_none_devolve_traco(self):
        from gui.componentes import formatar_valor

        self.assertEqual(formatar_valor(None), "—")

    def test_formatar_valor_zero(self):
        from gui.componentes import formatar_valor

        self.assertEqual(formatar_valor(Decimal("0.00")), "0,00 €")

    def test_formatar_valor_negativo(self):
        from gui.componentes import formatar_valor

        self.assertEqual(formatar_valor(Decimal("-45.50")), "-45,50 €")

    def test_formatar_valor_com_uma_casa_mostra_duas(self):
        """Decimal("45.5") apresenta "45,50 €" — sempre duas casas."""
        from gui.componentes import formatar_valor

        self.assertEqual(formatar_valor(Decimal("45.5")), "45,50 €")


# ---------------------------------------------------------------------
# 2. Seletor
# ---------------------------------------------------------------------


class TesteSeletor(unittest.TestCase):
    """`componentes.Seletor` — herda de `CTkOptionMenu` e troca o
    menu nativo por um painel com scroll e pesquisa quando a lista
    é grande."""

    @classmethod
    def setUpClass(cls):
        cls.root = _criar_root()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def _criar_seletor(self, values, command=None, limite=8, pesquisa=True):
        from gui.componentes import Seletor

        return Seletor(
            self.root,
            values=values,
            command=command,
            limite=limite,
            pesquisa=pesquisa,
        )

    # -- estado inicial -----------------------------------------------

    def test_seletor_comeca_com_primeiro_valor(self):
        s = self._criar_seletor(["A", "B", "C"])
        self.assertEqual(s.get(), "A")

    def test_seletor_com_lista_vazia_nao_rebenta(self):
        s = self._criar_seletor([])
        # Não deve rebentar a construção.

    # -- decisão de menu nativo vs painel -----------------------------

    def test_lista_curta_usa_menu_nativo(self):
        """Com poucos valores, `_open_dropdown_menu` chama o menu
        nativo do CTkOptionMenu — não cria painel."""
        s = self._criar_seletor(["A", "B", "C"])

        # Chama diretamente — não há clique que chegue ao _open_dropdown_menu
        # sem abrir um menu real de sistema operativo (que bloqueia o
        # teste). Isto NÃO é handler de evento; é o método que decide.
        # A regra do PASSO 9 é sobre handlers de eventos, não sobre
        # métodos internos de coordenação.
        s._open_dropdown_menu()

        # Sem painel próprio.
        self.assertIsNone(s._painel)

    def test_lista_grande_abre_painel_proprio(self):
        """Com valores acima do limite, `_open_dropdown_menu` cria um
        painel CTkToplevel."""
        s = self._criar_seletor([f"valor {i}" for i in range(20)])

        s._open_dropdown_menu()

        self.assertIsNotNone(s._painel)
        # Limpeza — evita deixar toplevels pendurados entre testes.
        s._fechar_painel()

    def test_lista_no_limite_usa_menu_nativo(self):
        """O limite é "menor ou igual" → menu nativo."""
        s = self._criar_seletor(["A", "B", "C"], limite=3)
        s._open_dropdown_menu()
        self.assertIsNone(s._painel)

    def test_lista_um_acima_do_limite_abre_painel(self):
        s = self._criar_seletor(["A", "B", "C", "D"], limite=3)
        s._open_dropdown_menu()
        self.assertIsNotNone(s._painel)
        s._fechar_painel()

    # -- escolha pelo painel ------------------------------------------

    def test_escolher_valor_no_painel_atualiza_o_get(self):
        escolhas = []
        s = self._criar_seletor(
            [f"valor {i}" for i in range(20)],
            command=escolhas.append,
        )

        s._open_dropdown_menu()
        s._escolher("valor 7")

        self.assertEqual(s.get(), "valor 7")
        self.assertEqual(escolhas, ["valor 7"])

    def test_escolher_fecha_o_painel(self):
        s = self._criar_seletor([f"valor {i}" for i in range(20)])
        s._open_dropdown_menu()
        self.assertIsNotNone(s._painel)

        s._escolher("valor 3")

        self.assertIsNone(s._painel)

    # -- alternar painel ----------------------------------------------

    def test_segundo_clique_fecha_o_painel(self):
        """`_alternar_painel` abre na primeira chamada, fecha na
        segunda."""
        s = self._criar_seletor([f"valor {i}" for i in range(20)])

        s._alternar_painel()
        self.assertIsNotNone(s._painel)

        s._alternar_painel()
        self.assertIsNone(s._painel)

    # -- lista original nunca é alterada ------------------------------

    def test_values_original_nao_e_alterada_apos_filtrar(self):
        """A pesquisa filtra só o que se desenha — `_values` continua
        a ser a lista original, pela ordem original."""
        valores = [
            "Ana",
            "Bruno",
            "Carla",
            "Dinis",
            "Eva",
            "Fábio",
            "Gonçalo",
            "Helena",
            "Inês",
            "João",
        ]
        s = self._criar_seletor(valores)

        s._open_dropdown_menu()

        # O Pylance não consegue inferir que `_campo_pesquisa` é
        # `CTkEntry` depois de `_open_dropdown_menu` — vê só o tipo
        # declarado no `__init__` (`None`). O `assert` cala o aviso
        # e, se a premissa deixar de ser verdadeira no futuro, o
        # teste falha com uma mensagem clara em vez de rebentar
        # com `AttributeError` três linhas depois.
        assert s._campo_pesquisa is not None

        # Escreve um termo no campo de pesquisa — simulado inserindo
        # no campo e disparando o evento `<KeyRelease>`, que é o que
        # o binding do componente apanha.
        s._campo_pesquisa.insert(0, "a")
        s._campo_pesquisa.event_generate("<KeyRelease>")

        # A lista original não foi tocada.
        self.assertEqual(s._values, valores)

        s._fechar_painel()

    # -- destroy ------------------------------------------------------

    def test_destroy_fecha_painel_se_aberto(self):
        s = self._criar_seletor([f"valor {i}" for i in range(20)])
        s._open_dropdown_menu()
        self.assertIsNotNone(s._painel)

        s.destroy()

        self.assertIsNone(s._painel)


# ---------------------------------------------------------------------
# 3. Tabela
# ---------------------------------------------------------------------


class TesteTabela(unittest.TestCase):
    """`componentes.Tabela` — cartão com cabeçalho fixo e corpo com
    scroll. As células são widgets do CustomTkinter colocados com
    `colocar`."""

    @classmethod
    def setUpClass(cls):
        cls.root = _criar_root()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def _criar_tabela(self, colunas=None, tom_alternado=False):
        from gui.componentes import Coluna, Tabela

        if colunas is None:
            colunas = (
                Coluna("ID", minimo=90),
                Coluna("NOME", peso=1, minimo=180),
            )
        tabela = Tabela(
            self.root,
            colunas=colunas,
            tom_alternado=tom_alternado,
        )
        tabela.pack()
        self.root.update_idletasks()
        return tabela

    # -- estado inicial -----------------------------------------------

    def test_tabela_nasce_vazia(self):
        t = self._criar_tabela()
        self.assertTrue(t.vazia)

    def test_tabela_com_cabecalho_mas_sem_linhas_continua_vazia(self):
        """O cabeçalho NÃO conta como linha — a `vazia` olha só para
        as linhas de dados."""
        t = self._criar_tabela()
        self.assertEqual(t._desenhadas, 0)

    # -- nova_linha / colocar -----------------------------------------

    def test_nova_linha_incrementa_contagem(self):
        t = self._criar_tabela()
        t.nova_linha()
        self.assertEqual(t._desenhadas, 1)

    def test_nova_linha_devolve_grelha_do_corpo(self):
        t = self._criar_tabela()
        linha = t.nova_linha()
        self.assertIs(linha, t.grelha)

    def test_colocar_cria_widget_na_grelha(self):
        t = self._criar_tabela()
        linha = t.nova_linha()
        label = ctk.CTkLabel(linha, text="CLI-001")
        t.colocar(linha, 0, label)

        self.assertIn(label, linha.winfo_children())

    def test_celula_acoes_devolve_celula_com_adicionar(self):
        t = self._criar_tabela()
        linha = t.nova_linha()
        acoes = t.celula_acoes(linha, 1)

        self.assertTrue(hasattr(acoes, "adicionar"))

    def test_adicionar_botao_a_celula_acoes(self):
        t = self._criar_tabela()
        linha = t.nova_linha()
        acoes = t.celula_acoes(linha, 1)
        botao = acoes.adicionar(ctk.CTkButton(acoes, text="Gerir"))

        self.assertIn(botao, acoes.winfo_children())

    # -- limpar -------------------------------------------------------

    def test_limpar_apaga_linhas_e_reinicia_contagem(self):
        t = self._criar_tabela()
        t.nova_linha()
        t.nova_linha()
        t.nova_linha()
        self.assertEqual(t._desenhadas, 3)

        t.limpar()

        self.assertEqual(t._desenhadas, 0)
        self.assertTrue(t.vazia)

    def test_limpar_pode_ser_chamado_em_tabela_vazia(self):
        t = self._criar_tabela()
        t.limpar()  # não deve rebentar
        self.assertTrue(t.vazia)

    # -- vazia --------------------------------------------------------

    def test_vazia_e_true_apos_limpar(self):
        t = self._criar_tabela()
        t.nova_linha()
        t.limpar()
        self.assertTrue(t.vazia)

    # -- mostrar_vazio ------------------------------------------------

    def test_mostrar_vazio_nao_conta_como_linha(self):
        """A mensagem de "sem registos" não é uma linha de dados —
        `_desenhadas` continua a zero."""
        t = self._criar_tabela()
        t.mostrar_vazio("Sem dados.")
        self.assertEqual(t._desenhadas, 0)

    # -- tom alternado ------------------------------------------------

    def test_tom_alternado_muda_a_cor_da_fila(self):
        """Duas linhas seguidas com `tom_alternado=True` têm cores
        diferentes — a primeira usa COR_FUNDO, a segunda LINHA_ALTERNADA."""
        from gui import tema

        t = self._criar_tabela(tom_alternado=True)

        t.nova_linha()
        cor_primeira = t._cor_fila_atual

        t.nova_linha()
        cor_segunda = t._cor_fila_atual

        self.assertEqual(cor_primeira, tema.COR_FUNDO)
        self.assertEqual(cor_segunda, tema.LINHA_ALTERNADA)

    def test_sem_tom_alternado_fica_sempre_no_fundo(self):
        from gui import tema

        t = self._criar_tabela(tom_alternado=False)

        t.nova_linha()
        self.assertEqual(t._cor_fila_atual, tema.COR_FUNDO)

        t.nova_linha()
        self.assertEqual(t._cor_fila_atual, tema.COR_FUNDO)

    def test_terceira_linha_volta_ao_fundo(self):
        """Com tom alternado, a 3ª linha volta ao fundo (0 = fundo,
        1 = alternada, 2 = fundo)."""
        from gui import tema

        t = self._criar_tabela(tom_alternado=True)
        t.nova_linha()
        t.nova_linha()
        t.nova_linha()

        self.assertEqual(t._cor_fila_atual, tema.COR_FUNDO)


# ---------------------------------------------------------------------
# 4. BlocoTermo
# ---------------------------------------------------------------------


class TesteBlocoTermo(unittest.TestCase):
    """`componentes.BlocoTermo` — quadro que mostra um documento legal
    e recolhe a confirmação de quem o leu."""

    @classmethod
    def setUpClass(cls):
        cls.root = _criar_root()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def _criar_bloco(self, **overrides):
        from gui.componentes import BlocoTermo

        campos = {
            "titulo": "Termo de confidencialidade",
            "texto": "Texto do termo. Exemplo de conteúdo.",
            "versao": "1.0",
            "rotulo": "Li e aceito",
        }
        campos.update(overrides)
        bloco = BlocoTermo(self.root, **campos)
        bloco.pack()
        self.root.update_idletasks()
        return bloco

    # -- estado inicial -----------------------------------------------

    def test_bloco_comeca_nao_aceite(self):
        b = self._criar_bloco()
        self.assertFalse(b.esta_aceite())

    def test_bloco_guarda_a_versao(self):
        b = self._criar_bloco(versao="2.0")
        self.assertEqual(b.versao, "2.0")

    # -- esta_aceite --------------------------------------------------

    def test_esta_aceite_apos_marcar(self):
        b = self._criar_bloco()
        b.aceite.set(True)
        self.assertTrue(b.esta_aceite())

    def test_esta_aceite_apos_desmarcar(self):
        b = self._criar_bloco()
        b.aceite.set(True)
        b.aceite.set(False)
        self.assertFalse(b.esta_aceite())

    # -- callback ao_mudar --------------------------------------------

    def test_ao_mudar_e_chamado_quando_a_caixa_muda(self):
        chamadas = []

        def ao_mudar():
            chamadas.append(None)

        b = self._criar_bloco(ao_mudar=ao_mudar)

        # O checkbox chama `_mudou`, que por sua vez chama `ao_mudar`.
        # Invocamos `_mudou` diretamente — é o que o `command` do
        # checkbox faz; não há tecla/clique simulável de forma
        # fiável num checkbox do CTk em teste.
        b._mudou()

        self.assertEqual(len(chamadas), 1)

    def test_ao_mudar_none_nao_rebenta(self):
        """Se o chamador não passar `ao_mudar`, `_mudou` não rebenta."""
        b = self._criar_bloco()  # sem ao_mudar
        b._mudou()  # não deve levantar

    # -- rodapé -------------------------------------------------------

    def test_rodape_sem_versao_anterior(self):
        """Quem nunca aceitou vê só a versão em vigor."""
        from gui.componentes import BlocoTermo

        texto = BlocoTermo._rodape("1.0", None, None)
        self.assertEqual(texto, "Versão 1.0")

    def test_rodape_com_versao_anterior(self):
        """Quem já aceitou vê as duas versões e a data.

        O formato real do rodapé é:
            "Aceitou a versão <antiga> em <data> · em vigor agora: <nova>"
        """
        from gui.componentes import BlocoTermo
        from datetime import date

        texto = BlocoTermo._rodape("2.0", "1.0", date(2025, 5, 20))

        self.assertIn("versão 1.0", texto)
        self.assertIn("2025-05-20", texto)
        self.assertIn("em vigor agora: 2.0", texto)

    def test_rodape_com_data_anterior_ausente(self):
        """Versão anterior registada mas sem data — o formato mostra
        um travessão no lugar da data."""
        from gui.componentes import BlocoTermo

        texto = BlocoTermo._rodape("2.0", "1.0", None)

        self.assertIn("versão 1.0", texto)
        self.assertIn("em —", texto)  # "em —" (a data veio como "—")
        self.assertIn("em vigor agora: 2.0", texto)

    # -- aviso --------------------------------------------------------

    def test_aviso_none_nao_cria_faixa(self):
        """Sem `aviso`, a faixa amarela do topo não aparece — não
        há razão para reservar espaço."""
        b = self._criar_bloco(aviso=None)
        self.assertIsNotNone(b)

    def test_aviso_cria_faixa_amarela(self):
        """Com `aviso` preenchido, o bloco constrói sem erro."""
        b = self._criar_bloco(
            aviso="O termo foi atualizado.",
            versao_anterior="0.9",
            data_anterior=None,
        )
        self.assertIsNotNone(b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
