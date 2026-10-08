"""Ecrã "Despesas" (`ListaDespesas`) e os modais abertos a partir
da lista: escolha de via, editar e detalhe."""

import tkinter.font as tkfont

import customtkinter as ctk

import despesas
import estoque
import responsaveis
import unidades

from .. import componentes
from .. import tema
from . import gui_desp_atribuir
from . import gui_desp_comum
from .gui_desp_manual import NovaDespesaManualModal
from .gui_desp_stock import NovaDespesaStockModal

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_desp_comum).
_parse_decimal = gui_desp_comum.parse_decimal
_autor_atual = gui_desp_comum.autor_atual
_formatar_data = gui_desp_comum.formatar_data
_parse_data = gui_desp_comum.parse_data
_rotulo_unidade = gui_desp_comum.rotulo_unidade
_rotulo_categoria = gui_desp_comum.rotulo_categoria


# =====================================================================
# CONSTANTES
# =====================================================================

# Rótulos das opções de filtro (dropdowns) — mesmas convenções
# dos outros ecrãs (`"Todos …"` para "sem filtro").
_OPCAO_TODAS_CATEGORIAS = "Todas as categorias"
_OPCAO_TODOS_ESTADOS = "Todos os estados"
_OPCAO_TODAS_UNIDADES = "Todas as unidades"

# Larguras fixas das colunas da tabela de despesas (mesma
# disciplina dos outros módulos: uma constante por coluna,
# lida tanto pelo cabeçalho como pelas linhas).
#
# v1.8.2 (04/10/2026): as larguras antigas somavam ~1060 px e a
# área da tabela, com a janela no tamanho mínimo (950 px menos a
# barra lateral), só tem ~730 — as colunas Estado e Ações ficavam
# fora do ecrã e o "Gerir" não se via (teste F9 do manual). Agora
# somam ~720; a Descrição continua a crescer (peso 3) quando há
# espaço, e textos compridos são cortados com "…" (o texto inteiro
# vê-se no detalhe, clicando no ID).
_LARGURA_ID = 84
_LARGURA_DESCRICAO = 130
_LARGURA_CATEGORIA = 90
_LARGURA_VALOR = 76
_LARGURA_LANCAMENTO = 80
_LARGURA_VENCIMENTO = 80
_LARGURA_ESTADO = 88
_LARGURA_ACOES = 80
_LARGURA_CHIP_ESTADO = 72

_COLUNAS_DESPESA = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 10, espaco=8),
    componentes.Coluna("DESCRIÇÃO", peso=3, minimo=_LARGURA_DESCRICAO),
    componentes.Coluna("CATEGORIA", peso=1, minimo=_LARGURA_CATEGORIA),
    componentes.Coluna(
        "VALOR", peso=1, minimo=_LARGURA_VALOR, alinhamento="e"
    ),
    componentes.Coluna(
        "LANÇAMENTO",
        peso=1,
        minimo=_LARGURA_LANCAMENTO,
        alinhamento="centro",
    ),
    componentes.Coluna(
        "VENCIMENTO",
        peso=1,
        minimo=_LARGURA_VENCIMENTO,
        alinhamento="centro",
    ),
    componentes.Coluna(
        "ESTADO", peso=1, minimo=_LARGURA_ESTADO, alinhamento="centro"
    ),
    componentes.Coluna("AÇÕES", minimo=_LARGURA_ACOES, alinhamento="centro"),
)

_ALTURA_LINHA = 52


# =====================================================================
# ECRÃ LISTA — ListaDespesas
# =====================================================================


class ListaDespesas(ctk.CTkFrame):
    """Ecrã principal do módulo — a lista de todas as despesas.

    Estrutura (mockup A.2):
      - Cabeçalho "Despesas" (componentes.Cabecalho)
      - Barra de ações: botão verde "+ Nova Despesa" + 4 filtros
        (categoria · estado · unidade · checkbox "Só vencidas")
      - Tabela com 8 colunas: ID · Descrição · Categoria · Valor ·
        Lançamento · Vencimento · Estado · Ações
      - Botão "Gerir" em cada linha, que abre o modal certo
        conforme o estado (pendente → Aprovações-style modal;
        paga → modal de leitura; cancelada → modal de leitura)
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        # Referências vivas aos dados, preenchidas em _recarregar.
        self._categorias = []
        self._unidades = []

        # Fontes reais para medir texto (`componentes.truncar_texto`)
        # — criadas uma vez, não por linha (mesmo padrão das
        # Propriedades).
        self._fonte_descricao = tkfont.Font(size=12)
        self._fonte_categoria = tkfont.Font(size=11)

        componentes.Cabecalho(self, titulo="Despesas").pack(fill="x")

        self._montar_barra_acoes()

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_DESPESA,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia="Ainda não há despesas lançadas.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- barra de ações -----------------------------------------------

    def _montar_barra_acoes(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 8))

        ctk.CTkButton(
            barra,
            text="+ Nova Despesa",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._abrir_escolha_via,
        ).pack(side="left")

        filtros = ctk.CTkFrame(barra, fg_color="transparent")
        filtros.pack(side="right")

        self.combo_categoria = componentes.Seletor(
            filtros,
            values=[_OPCAO_TODAS_CATEGORIAS],
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _v: self._recarregar(),
        )
        self.combo_categoria.set(_OPCAO_TODAS_CATEGORIAS)
        self.combo_categoria.pack(side="left")

        self.combo_estado = componentes.Seletor(
            filtros,
            values=[
                _OPCAO_TODOS_ESTADOS,
                "pendente",
                "paga",
                "cancelada",
            ],
            width=160,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _v: self._recarregar(),
        )
        self.combo_estado.set(_OPCAO_TODOS_ESTADOS)
        self.combo_estado.pack(side="left", padx=(8, 0))

        self.combo_unidade = componentes.Seletor(
            filtros,
            values=[_OPCAO_TODAS_UNIDADES],
            width=200,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _v: self._recarregar(),
        )
        self.combo_unidade.set(_OPCAO_TODAS_UNIDADES)
        self.combo_unidade.pack(side="left", padx=(8, 0))

        self.so_vencidas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            filtros,
            text="Só vencidas",
            variable=self.so_vencidas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(10, 0))

    # -- filtros ------------------------------------------------------

    def _carregar_filtros(self):
        """Recarrega as opções dos dropdowns de filtro a partir da
        BD — chamada uma vez no arranque. Se ficar sempre a
        recarregar, o utilizador perde a seleção a cada refresh."""
        self._categorias = despesas.listar_categorias()
        self._unidades = unidades.listar_com_propriedade()

        nomes_categorias = [_OPCAO_TODAS_CATEGORIAS] + [
            _rotulo_categoria(c) for c in self._categorias
        ]
        self.combo_categoria.configure(values=nomes_categorias)

        self._unidade_por_rotulo = {
            _rotulo_unidade(u): u["id"] for u in self._unidades
        }
        rotulos_unidades = [_OPCAO_TODAS_UNIDADES] + sorted(
            self._unidade_por_rotulo
        )
        self.combo_unidade.configure(values=rotulos_unidades)

    def _categoria_filtro(self):
        valor = self.combo_categoria.get()
        if valor == _OPCAO_TODAS_CATEGORIAS:
            return None
        for c in self._categorias:
            if c["nome"] == valor:
                return c["id"]
        return None

    def _estado_filtro(self):
        valor = self.combo_estado.get()
        if valor == _OPCAO_TODOS_ESTADOS:
            return None
        return valor

    def _unidade_filtro(self):
        valor = self.combo_unidade.get()
        if valor == _OPCAO_TODAS_UNIDADES:
            return None
        return self._unidade_por_rotulo.get(valor)

    # -- carregamento -------------------------------------------------

    def _recarregar(self):
        """Recarrega a lista de despesas com os filtros atuais.

        Chamada na abertura, ao mexer em qualquer filtro, e depois
        de qualquer criação/edição/cancelamento.
        """
        self._carregar_filtros()
        self.tabela.limpar()

        incluir_vencidas = None
        if self.so_vencidas.get():
            incluir_vencidas = True

        lista = despesas.listar_despesas(
            estado=self._estado_filtro(),
            unidade_id=self._unidade_filtro(),
            categoria_id=self._categoria_filtro(),
            incluir_vencidas=incluir_vencidas,
        )

        if not lista:
            self.tabela.mostrar_vazio()
            return

        # Guarda referências para consulta rápida ao desenhar.
        cat_por_id = {c["id"]: c for c in self._categorias}
        uni_por_id = {u["id"]: u for u in self._unidades}

        for despesa in lista:
            self._desenhar_despesa(despesa, cat_por_id, uni_por_id)

    def _desenhar_despesa(self, d, cat_por_id, uni_por_id):
        """Desenha uma linha da tabela com uma despesa."""
        linha = self.tabela.nova_linha()

        # ID — clicar abre o detalhe (só leitura) da despesa.
        self.tabela.colocar(
            linha,
            0,
            componentes.ChipId(
                linha,
                d["id"],
                ao_clicar=lambda: _DetalheDespesaModal(self, d),
                largura=_LARGURA_ID,
            ),
            esticar="w",
        )

        # Descrição (corta com "…" se for longa)
        # v1.8.2: até 2 linhas (quebra na largura da coluna) e só
        # depois corta com "…" — cabe na altura da linha da tabela.
        texto_desc = componentes.truncar_texto(
            self._fonte_descricao,
            d["descricao"] or "(sem descrição)",
            2 * _LARGURA_DESCRICAO - 20,
        )
        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=texto_desc,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_DESCRICAO,
                wraplength=_LARGURA_DESCRICAO,
                justify="left",
                anchor="w",
            ),
        )

        # Categoria (por nome, via lookup)
        categoria = cat_por_id.get(d["categoria_id"])
        nome_cat = componentes.truncar_texto(
            self._fonte_categoria,
            categoria["nome"] if categoria else "—",
            _LARGURA_CATEGORIA,
        )
        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=nome_cat,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                width=_LARGURA_CATEGORIA,
                anchor="w",
            ),
        )

        # Valor
        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=componentes.formatar_valor(d["valor"]),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=_LARGURA_VALOR,
                anchor="e",
            ),
        )

        # Lançamento
        self.tabela.colocar(
            linha,
            4,
            ctk.CTkLabel(
                linha,
                text=_formatar_data(d["data_lancamento"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                width=_LARGURA_LANCAMENTO,
                anchor="center",
            ),
        )

        # Vencimento
        self.tabela.colocar(
            linha,
            5,
            ctk.CTkLabel(
                linha,
                text=_formatar_data(d["data_vencimento"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                width=_LARGURA_VENCIMENTO,
                anchor="center",
            ),
        )

        # Estado — chip + ponto vermelho se vencida
        bloco_estado = ctk.CTkFrame(linha, fg_color="transparent", height=26)
        bloco_estado.pack_propagate(False)

        ctk.CTkLabel(
            bloco_estado,
            text=d["estado"],
            text_color=self._cor_texto_estado(d["estado"]),
            fg_color=self._cor_fundo_estado(d["estado"]),
            corner_radius=8,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=_LARGURA_CHIP_ESTADO,
            height=22,
        ).pack(side="left")

        if despesas.esta_vencida(d):
            ctk.CTkLabel(
                bloco_estado,
                text="●",
                text_color=tema.TEXTO_ERRO,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="left", padx=(6, 0))

        self.tabela.colocar(linha, 6, bloco_estado)

        # Botão Gerir
        acoes = self.tabela.celula_acoes(linha, 7)
        acoes.adicionar(
            ctk.CTkButton(
                acoes,
                text="Gerir",
                width=_LARGURA_ACOES - 6,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda d=d: self._abrir_gerir(d),
            )
        )

    def _cor_fundo_estado(self, estado):
        return {
            "pendente": tema.AMARELO_AVISO,
            "paga": tema.VERDE_LIVRE,
            "cancelada": tema.CINZA_INDISPONIVEL,
        }.get(estado, tema.CINZA_INDISPONIVEL)

    def _cor_texto_estado(self, estado):
        return {
            "pendente": tema.TEXTO_AVISO,
            "paga": tema.TEXTO_LIVRE,
            "cancelada": tema.TEXTO_INDISPONIVEL,
        }.get(estado, tema.TEXTO_INDISPONIVEL)

    # -- ações --------------------------------------------------------

    def _abrir_escolha_via(self):
        """Abre o popup intermédio que pergunta se é despesa manual
        ou via stock (mockup A.3a). Esse popup, depois, abre o
        modal certo."""
        _EscolherViaModal(self)

    def _abrir_gerir(self, despesa):
        if despesa["estado"] == "pendente":
            _EditarDespesaModal(self, despesa)
        else:
            _DetalheDespesaModal(self, despesa)


# =====================================================================
# MODAIS DA VIA 1 — escolha da via, formulário manual, divisão
# =====================================================================


class _EscolherViaModal(ctk.CTkToplevel):
    """Popup intermédio do botão "+ Nova Despesa".

    Pergunta se é despesa manual (VIA 1) ou via stock (VIA 2).
    Fecha-se e abre o modal correspondente. Mesmo padrão do
    `_EscolherTipoRequisicaoModal` do Stock (gui_est_requisicoes.py).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 380, 300
        self.title("Nova Despesa")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="O que pretende criar?",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 14))

        self._cartao(
            "Despesa manual",
            "EDP, água, internet, obras. Sem itens de produto.",
            self._abrir_manual,
        )
        self._cartao(
            "Despesa via stock",
            "Compra de produtos para o armazém. Gera movimentos "
            "de entrada depois da confirmação.",
            self._abrir_stock,
        )

        ctk.CTkButton(
            self,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(6, 20))

    def _cartao(self, titulo, descricao, ao_clicar):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 2))

        ctk.CTkLabel(
            cartao,
            text=descricao,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", padx=14, pady=(0, 12))

        componentes.tornar_cliclavel(cartao, ao_clicar)

    def _abrir_manual(self):
        self.destroy()
        NovaDespesaManualModal(self.tela_lista)

    def _abrir_stock(self):
        self.destroy()
        # Import local para evitar que o ficheiro falhe a importar
        # enquanto o B.3 ainda não está colado.
        NovaDespesaStockModal(self.tela_lista)


class _EditarDespesaModal(ctk.CTkToplevel):
    """Modal de edição completa de uma despesa pendente.

    Permite editar: valor, descrição, categoria, fornecedor, data
    de lançamento, data de vencimento. Não permite editar unidade
    nem recorrente (decisão tomada com o aluno — são estruturais).

    Aberto pelo "Gerir" da Lista Despesas, quando a despesa está
    pendente. Para despesas pagas/canceladas abre o
    `_DetalheDespesaModal` (só leitura).
    """

    def __init__(self, tela_lista, despesa):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.despesa = despesa

        self._categorias = []
        self._fornecedores = []

        largura, altura = 620, 720
        self.title(f"Editar — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._montar_header()
        self._montar_campos()
        self._montar_rodape()
        self._carregar_dados()

    def _montar_header(self):
        ctk.CTkLabel(
            self,
            text=f"Editar {self.despesa['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "Fica pendente até ser marcada como paga. "
                "A unidade e a recorrência não se alteram aqui."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=24, pady=(0, 14))

    def _montar_campos(self):
        area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=24)

        # Descrição
        ctk.CTkLabel(
            area,
            text="Descrição *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        self.campo_descricao = ctk.CTkEntry(
            area, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_descricao.insert(0, self.despesa["descricao"])
        self.campo_descricao.pack(fill="x")

        # Categoria + Fornecedor
        linha = ctk.CTkFrame(area, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(0, weight=1, uniform="col")
        linha.grid_columnconfigure(1, weight=1, uniform="col")

        bloco_cat = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_cat.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_cat,
            text="Categoria *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_categoria = componentes.Seletor(
            bloco_cat, values=[""], corner_radius=tema.RAIO_CAMPO
        )
        self.combo_categoria.pack(fill="x", pady=(2, 0))

        bloco_forn = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_forn.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_forn,
            text="Fornecedor",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_fornecedor = componentes.Seletor(
            bloco_forn, values=["Nenhum"], corner_radius=tema.RAIO_CAMPO
        )
        self.combo_fornecedor.pack(fill="x", pady=(2, 0))

        # Valor + Lançamento
        linha2 = ctk.CTkFrame(area, fg_color="transparent")
        linha2.pack(fill="x", pady=4)
        linha2.grid_columnconfigure(0, weight=1, uniform="col")
        linha2.grid_columnconfigure(1, weight=1, uniform="col")

        bloco_valor = ctk.CTkFrame(linha2, fg_color="transparent")
        bloco_valor.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_valor,
            text="Valor *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.campo_valor = ctk.CTkEntry(
            bloco_valor, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_valor.insert(
            0, str(self.despesa["valor"]).replace(".", ",")
        )
        self.campo_valor.pack(fill="x", pady=(2, 0))

        bloco_lanc = ctk.CTkFrame(linha2, fg_color="transparent")
        bloco_lanc.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_lanc,
            text="Data de lançamento *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.campo_data_lancamento = componentes.CampoData(bloco_lanc)
        self.campo_data_lancamento.insert(
            0, _formatar_data(self.despesa["data_lancamento"])
        )
        self.campo_data_lancamento.pack(fill="x", pady=(2, 0))

        # Vencimento
        ctk.CTkLabel(
            area,
            text="Data de vencimento",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        self.campo_data_vencimento = componentes.CampoData(
            area,
            placeholder_text="dd/mm/aaaa (deixa em branco para limpar)",
        )
        if self.despesa["data_vencimento"]:
            self.campo_data_vencimento.insert(
                0, _formatar_data(self.despesa["data_vencimento"])
            )
        self.campo_data_vencimento.pack(fill="x")

        ctk.CTkLabel(
            area,
            text=(
                "Deixa em branco para limpar a data de vencimento. "
                "Não pode ser anterior à data de lançamento."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", pady=(2, 0))

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(8, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=150,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Guardar",
            width=170,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _carregar_dados(self):
        self._categorias = [
            c
            for c in despesas.listar_categorias()
            if c["nome"] != "Compra de Stock"
        ]
        nomes_cat = [c["nome"] for c in self._categorias] or ["Sem categorias"]
        self.combo_categoria.configure(values=nomes_cat)

        cat_atual = None
        for c in self._categorias:
            if c["id"] == self.despesa["categoria_id"]:
                cat_atual = c["nome"]
                break
        self.combo_categoria.set(cat_atual or nomes_cat[0])

        self._fornecedores = despesas.listar_fornecedores()
        nomes_forn = ["Nenhum"] + [f["nome"] for f in self._fornecedores]
        self.combo_fornecedor.configure(values=nomes_forn)

        forn_atual = "Nenhum"
        if self.despesa["fornecedor_id"]:
            for f in self._fornecedores:
                if f["id"] == self.despesa["fornecedor_id"]:
                    forn_atual = f["nome"]
                    break
        self.combo_fornecedor.set(forn_atual)

    def _id_categoria(self):
        nome = self.combo_categoria.get()
        for c in self._categorias:
            if c["nome"] == nome:
                return c["id"]
        return None

    def _id_fornecedor(self):
        nome = self.combo_fornecedor.get()
        if nome == "Nenhum":
            return ""
        for f in self._fornecedores:
            if f["nome"] == nome:
                return f["id"]
        return ""

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            descricao = self.campo_descricao.get().strip()
            if not descricao:
                raise ValueError("A descrição é obrigatória.")

            categoria_id = self._id_categoria()
            if categoria_id is None:
                raise ValueError("Escolhe uma categoria.")

            valor = _parse_decimal(self.campo_valor.get(), "Valor")

            data_lancamento = _parse_data(
                self.campo_data_lancamento.get(), "Data de lançamento"
            )
            if data_lancamento is None:
                raise ValueError("A data de lançamento é obrigatória.")

            texto_venc = self.campo_data_vencimento.get().strip()
            if texto_venc:
                data_vencimento = _parse_data(texto_venc, "Data de vencimento")
            else:
                data_vencimento = None
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            despesas.editar_despesa_pendente(
                despesa_id=self.despesa["id"],
                autor=autor,
                valor=valor,
                descricao=descricao,
                categoria_id=categoria_id,
                fornecedor_id=self._id_fornecedor(),
                data_lancamento=data_lancamento,
                data_vencimento=data_vencimento,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Despesa {self.despesa['id']} atualizada."
        )
        self.destroy()
        self.tela_lista._recarregar()


class _DetalheDespesaModal(ctk.CTkToplevel):
    """Modal de leitura de uma despesa paga ou cancelada.

    Aberto pelo botão "Gerir" na Lista Despesas, para despesas que
    já não estão pendentes. Mostra a ficha completa (v1.12.0): a
    imputação, quem lançou, se é recorrente, o comprovativo, os itens
    de stock e quem os confirmou, e quem cancelou e porquê — só as
    linhas que fazem sentido para o estado e a origem da despesa.
    Quando a despesa não tem unidade, oferece "Atribuir unidade".
    """

    _LARGURA = 560

    def __init__(self, tela_lista, despesa):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.despesa = despesa
        self.itens = despesas.listar_itens_despesa(despesa["id"])

        self.title(f"Detalhe — {despesa['id']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.corpo = componentes.Contentor(self)
        self.corpo.pack(fill="both", expand=True, padx=22, pady=(18, 16))

        origem = "via stock" if self.itens else "manual"
        ctk.CTkLabel(
            self.corpo,
            text=despesa["descricao"] or "(sem descrição)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=self._LARGURA - 50,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(
            self.corpo,
            text=f"{despesa['id']} · estado: {despesa['estado']} · {origem}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(0, 12))

        ficha = ctk.CTkFrame(
            self.corpo,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=tema.RAIO_CAMPO,
        )
        ficha.pack(fill="x")
        interno = ctk.CTkFrame(ficha, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=12)

        self._linha(interno, "Categoria", self._nome_categoria())
        self._linha(interno, "Fornecedor", self._nome_fornecedor())
        self._linha(
            interno,
            "Valor",
            componentes.formatar_valor(despesa["valor"]),
            forte=True,
        )
        self._linha_imputacao(interno)
        self._linha(
            interno,
            "Lançamento",
            _formatar_data(despesa["data_lancamento"]),
        )
        self._linha(
            interno,
            "Vencimento",
            _formatar_data(despesa["data_vencimento"]),
        )
        self._linha(
            interno,
            "Pagamento",
            _formatar_data(despesa["data_pagamento"]),
        )
        self._linha(
            interno,
            "Lançada por",
            self._nome_responsavel(despesa["responsavel_lancamento_id"]),
        )
        self._linha(
            interno, "Recorrente", "Sim" if despesa["recorrente"] else "Não"
        )
        self._linha(
            interno,
            "Comprovativo",
            despesa["comprovativo_caminho"] or "Nenhum anexado",
        )

        if despesa.get("unidade_atribuida_por_id"):
            quem = self._nome_responsavel(
                despesa["unidade_atribuida_por_id"]
            )
            self._linha(
                interno,
                "Unidade atribuída",
                f"por {quem} em "
                f"{self._data_curta(despesa.get('unidade_atribuida_em'))}",
            )

        if self.itens:
            self._bloco_itens(interno)

        if despesa["estado"] == "cancelada":
            self._linha(
                interno,
                "Cancelada por",
                self._nome_responsavel(
                    despesa["responsavel_cancelamento_id"]
                ),
            )
            self._linha(
                interno,
                "Motivo",
                despesa["motivo_cancelamento"] or "—",
            )

        ctk.CTkButton(
            self.corpo,
            text="Fechar",
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", pady=(14, 0))

        self.update_idletasks()
        fator = componentes.escala(self)
        altura = int(self.corpo.winfo_reqheight() / fator) + 40
        componentes.centrar_sobre(
            self, tela_lista.winfo_toplevel(), self._LARGURA, altura
        )
        componentes.colocar_no_topo(self)

    # -- partes da ficha ----------------------------------------------

    def _linha_imputacao(self, interno):
        """"Imputação": a unidade (com a propriedade), "Armazém" nas
        compras de stock, ou "Geral, sem unidade" com o botão de
        atribuir (só se a despesa não estiver cancelada)."""
        despesa = self.despesa

        if despesa["unidade_id"]:
            unidade = unidades.procurar(despesa["unidade_id"])
            texto = (
                f"{unidade['nome']} ({unidade['id']})" if unidade else "—"
            )
            self._linha(interno, "Imputação", texto)
            return

        texto = "Armazém (geral)" if self.itens else "Geral, sem unidade"
        linha = self._linha(interno, "Imputação", texto)

        # Compra de stock: o stock é central, não se atribui a unidade.
        if despesa["estado"] != "cancelada" and not self.itens:
            ctk.CTkButton(
                linha,
                text="Atribuir unidade",
                width=120,
                height=24,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                font=ctk.CTkFont(size=11),
                command=self._atribuir,
            ).pack(side="left", padx=(10, 0))

    def _bloco_itens(self, interno):
        """Confirmação dos itens e a lista do que entrou no stock."""
        despesa = self.despesa

        if despesa["itens_confirmados"]:
            quem = self._nome_responsavel(
                despesa["itens_confirmados_por_id"]
            )
            quando = self._data_curta(despesa.get("itens_confirmados_em"))
            texto = f"Sim, por {quem} em {quando}"
        else:
            texto = "Não — ainda por confirmar"
        self._linha(interno, "Itens confirmados", texto)

        for item in self.itens:
            produto = estoque.procurar_produto(item["produto_id"])
            nome = produto["nome"] if produto else item["produto_id"]
            self._linha(
                interno,
                "Item" if item is self.itens[0] else "",
                f"{item['produto_id']} {nome} — {item['quantidade']}",
            )

    def _atribuir(self):
        def depois():
            self.destroy()
            self.tela_lista._recarregar()

        gui_desp_atribuir.AtribuirUnidadeModal(
            self, self.despesa, depois
        )

    # -- leitura ------------------------------------------------------

    @staticmethod
    def _data_curta(valor):
        if not valor:
            return "—"
        return valor.strftime("%d/%m/%Y")

    @staticmethod
    def _nome_responsavel(responsavel_id):
        if not responsavel_id:
            return "—"
        responsavel = responsaveis.procurar(responsavel_id)
        return responsavel["nome"] if responsavel else responsavel_id

    def _nome_categoria(self):
        c = despesas.procurar_categoria(self.despesa["categoria_id"])
        return c["nome"] if c else "—"

    def _nome_fornecedor(self):
        if not self.despesa["fornecedor_id"]:
            return "—"
        f = despesas.procurar_fornecedor(self.despesa["fornecedor_id"])
        return f["nome"] if f else "—"

    def _linha(self, master, rotulo, valor, forte=False):
        """Uma linha "rótulo  valor". Devolve a linha, para se poder
        juntar um botão à direita."""
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", pady=3)

        ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=120,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            linha,
            text=valor,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold" if forte else "normal"),
            anchor="w",
            justify="left",
            wraplength=self._LARGURA - 220,
        ).pack(side="left")
        return linha
