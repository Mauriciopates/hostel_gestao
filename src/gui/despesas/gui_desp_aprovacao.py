"""Ecrã "Aprovações" de Despesas e os seus modais (aprovar,
cancelar, confirmar itens VIA 2)."""

import datetime

import customtkinter as ctk

import despesas
import estoque
import unidades

from .. import componentes
from .. import tema
from . import gui_desp_comum

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_desp_comum).
_autor_atual = gui_desp_comum.autor_atual
_formatar_data = gui_desp_comum.formatar_data


class ConfirmarItensModal(ctk.CTkToplevel):
    """Confirmação dos itens de uma despesa VIA 2.

    Mostra os itens da despesa (só leitura) e um botão grande
    "Confirmar — gerar entradas no stock". Quando confirmado,
    chama `despesas.confirmar_itens_despesa`, que gera um movimento
    de entrada por item.

    A partir do ecrã Aprovações (Bloco B.4), o botão "Confirmar" de
    uma linha VIA 2 abre isto.
    """

    def __init__(self, tela_aprovacoes, despesa):
        super().__init__(tela_aprovacoes)
        self.tela_aprovacoes = tela_aprovacoes
        self.despesa = despesa

        itens = despesas.listar_itens_despesa(despesa["id"])
        self.itens = itens

        largura, altura = 620, 520
        self.title(f"Confirmar itens — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_aprovacoes)
        componentes.centrar_sobre(self, tela_aprovacoes, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self,
            text=f"Confirmar itens — {despesa['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "Ao confirmar, é gerada uma entrada em stock por "
                "cada item. A despesa fica marcada como confirmada."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=24, pady=(0, 14))

        self._montar_tabela()
        self._montar_rodape()

    def _montar_tabela(self):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=24)

        cabecalho = ctk.CTkFrame(
            cartao,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")
        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)
        for texto, largura, alinhamento in (
            ("PRODUTO", 320, "w"),
            ("QUANTIDADE", 120, "center"),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor=alinhamento,
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for item in self.itens:
            produto = estoque.procurar_produto(item["produto_id"])
            nome = produto["nome"] if produto else item["produto_id"]

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=320,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["quantidade"]),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=100,
                anchor="center",
            ).pack(side="left")

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=36,
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
            text="Confirmar — gerar entradas no stock",
            width=300,
            height=36,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._confirmar,
        ).pack(side="right")

    def _confirmar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.confirmar_itens_despesa(self.despesa["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Itens de {self.despesa['id']} confirmados. "
            f"Entradas geradas no stock."
        )
        self.destroy()
        self.tela_aprovacoes._recarregar()


# =====================================================================
# ECRÃ APROVAÇÕES
# =====================================================================


# Colunas das duas tabelas (21/09/2026 era o ponto aberto do
# CHANGELOG da v1.5.0: "a tabela das Aprovações tem de passar para
# `componentes.Tabela`"). Feito a 27/09/2026: as linhas antigas eram
# `pack(side="left")` com larguras fixas célula a célula — bastava um
# texto maior (ou a escala do Windows) para uma coluna empurrar as
# seguintes e o cabeçalho deixar de bater com as linhas. A `Tabela`
# alinha o cabeçalho pelas larguras REAIS do corpo.
_COLUNAS_PENDENTES = (
    componentes.Coluna("ID", minimo=92, espaco=8),
    componentes.Coluna("DESCRIÇÃO", peso=3, minimo=150),
    componentes.Coluna("CATEGORIA", peso=2, minimo=96),
    componentes.Coluna("VALOR", peso=1, minimo=80, alinhamento="e", espaco=8),
    componentes.Coluna("VENCIMENTO", peso=1, minimo=84, alinhamento="centro"),
    componentes.Coluna("SITUAÇÃO", peso=1, minimo=124, alinhamento="centro"),
    componentes.Coluna("AÇÕES", minimo=80, alinhamento="centro"),
)

_COLUNAS_VIA2 = (
    componentes.Coluna("ID", minimo=92, espaco=8),
    componentes.Coluna("DESCRIÇÃO", peso=3, minimo=170),
    componentes.Coluna("ITENS", peso=1, minimo=60, alinhamento="centro"),
    componentes.Coluna("VALOR", peso=1, minimo=80, alinhamento="e", espaco=8),
    componentes.Coluna("FORNECEDOR", peso=2, minimo=100),
    componentes.Coluna("PAGO EM", peso=1, minimo=84, alinhamento="centro"),
    componentes.Coluna("AÇÕES", minimo=126, alinhamento="centro"),
)

# Descrições compridas são cortadas com "…" — o texto inteiro está no
# "Gerir". Sem corte, uma descrição longa entrava pela coluna seguinte.
_MAX_DESCRICAO = 34

_ALTURA_LINHA = 48

# Uma despesa que vence dentro destes dias fica com a etiqueta
# amarela ("vence em 3 dias"); mais longe, cinzenta.
_DIAS_AVISO_PRAZO = 7


class Aprovacoes(ctk.CTkFrame):
    """Ecrã "Aprovações" — despesas pendentes + itens VIA 2 por
    confirmar.

    Duas secções, cada uma com a sua `componentes.Tabela` (cabeçalho
    fixo, corpo com scroll próprio):
      - Despesas pendentes (VIA 1) → botão "Gerir" abre o
        `_AprovarDespesaModal`.
      - Itens de despesa via stock por confirmar → botão
        "Confirmar itens" abre o `ConfirmarItensModal`.

    O ecrã em si NÃO tem scroll: cada tabela rola sozinha. Scroll
    dentro de scroll era o que deixava a roda do rato "presa".
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        self._categorias_por_id = {}

        componentes.Cabecalho(self, titulo="Aprovações").pack(fill="x")

        self._area = componentes.Contentor(self)
        self._area.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento -------------------------------------------------

    def _recarregar(self):
        for w in self._area.winfo_children():
            w.destroy()

        self._categorias_por_id = {
            c["id"]: c for c in despesas.listar_categorias()
        }

        pendentes = despesas.listar_despesas(estado="pendente")
        por_confirmar = [
            d for d in despesas.listar_despesas(estado="paga")
            if not d["itens_confirmados"]
        ]

        # A secção com linhas fica com o espaço que sobra; a vazia
        # fica só com a altura da mensagem.
        self._area.grid_columnconfigure(0, weight=1)
        self._area.grid_rowconfigure(1, weight=3 if pendentes else 0)
        self._area.grid_rowconfigure(3, weight=2 if por_confirmar else 0)

        self._desenhar_seccao_pendentes(pendentes)
        self._desenhar_seccao_itens_via2(por_confirmar)

    # -- secção 1 — despesas pendentes --------------------------------

    def _desenhar_seccao_pendentes(self, pendentes):
        self._titulo_seccao("Despesas pendentes", len(pendentes), fila=0)

        if not pendentes:
            self._mensagem_vazio(
                "Sem despesas pendentes. Todas as despesas lançadas já "
                "foram pagas ou canceladas.",
                fila=1,
            )
            return

        tabela = componentes.Tabela(
            self._area,
            colunas=_COLUNAS_PENDENTES,
            altura_linha=_ALTURA_LINHA,
            tom_alternado=True,
        )
        tabela.grid(row=1, column=0, sticky="nsew", pady=(0, 16))

        for d in pendentes:
            self._linha_pendente(tabela, d)

    def _linha_pendente(self, tabela, d):
        linha = tabela.nova_linha()
        cat = self._categorias_por_id.get(d["categoria_id"])

        tabela.colocar(
            linha, 0,
            componentes.ChipId(linha, d["id"], largura=80),
            esticar="w",
        )
        tabela.colocar(
            linha, 1,
            componentes.Rotulo(linha, _descricao(d)),
        )
        tabela.colocar(
            linha, 2,
            componentes.Rotulo(linha, cat["nome"] if cat else "—",
                               "secundario"),
        )
        tabela.colocar(
            linha, 3,
            componentes.Rotulo(
                linha, componentes.formatar_valor(d["valor"]), "forte",
                anchor="e",
            ),
        )
        tabela.colocar(
            linha, 4,
            componentes.Rotulo(
                linha, _formatar_data(d["data_vencimento"]), "secundario",
                anchor="center",
            ),
        )

        texto, estilo = self._situacao_prazo(d)
        tabela.colocar(
            linha, 5,
            componentes.Etiqueta(linha, texto, estilo, largura=116),
            chave=d["data_vencimento"] or datetime.date.max,
        )
        acoes = tabela.celula_acoes(linha, 6)
        acoes.adicionar(
            componentes.Botao(
                acoes, "Gerir", lambda d=d: _AprovarDespesaModal(self, d),
                "contorno", width=64, height=26,
            )
        )

    def _situacao_prazo(self, d):
        """(texto, estilo da etiqueta) do prazo: 'vencida há X dias'
        a vermelho, 'vence hoje'/'vence em X dias' a amarelo quando
        está perto, cinzento quando está longe ou não tem prazo."""
        if d["data_vencimento"] is None:
            return "sem prazo", "info"

        delta = (d["data_vencimento"] - datetime.date.today()).days
        if delta < 0:
            dias = abs(delta)
            return f"vencida há {dias} {'dia' if dias == 1 else 'dias'}", (
                "erro"
            )
        if delta == 0:
            return "vence hoje", "aviso"

        texto = f"vence em {delta} {'dia' if delta == 1 else 'dias'}"
        return texto, "aviso" if delta <= _DIAS_AVISO_PRAZO else "info"

    # -- secção 2 — itens VIA 2 por confirmar -------------------------

    def _desenhar_seccao_itens_via2(self, por_confirmar):
        self._titulo_seccao(
            "Itens de despesa por confirmar (VIA 2)",
            len(por_confirmar),
            fila=2,
        )

        if not por_confirmar:
            self._mensagem_vazio(
                "Sem itens por confirmar. Todas as compras via "
                "stock já foram verificadas.",
                fila=3,
            )
            return

        tabela = componentes.Tabela(
            self._area,
            colunas=_COLUNAS_VIA2,
            altura_linha=_ALTURA_LINHA,
            tom_alternado=True,
        )
        tabela.grid(row=3, column=0, sticky="nsew")

        for d in por_confirmar:
            self._linha_itens_via2(tabela, d)

    def _linha_itens_via2(self, tabela, d):
        linha = tabela.nova_linha()

        tabela.colocar(
            linha, 0,
            componentes.ChipId(linha, d["id"], largura=80),
            esticar="w",
        )

        # Descrição + etiqueta "via stock" na mesma célula.
        bloco = componentes.Contentor(linha)
        componentes.Rotulo(bloco, _descricao(d, _MAX_DESCRICAO - 10)).pack(
            side="left"
        )
        componentes.Etiqueta(bloco, "via stock", "azul").pack(
            side="left", padx=(6, 0)
        )
        tabela.colocar(linha, 1, bloco, esticar="w")

        n_itens = len(despesas.listar_itens_despesa(d["id"]))
        tabela.colocar(
            linha, 2,
            componentes.Rotulo(
                linha, f"{n_itens} {'item' if n_itens == 1 else 'itens'}",
                "secundario", anchor="center",
            ),
            chave=n_itens,
        )
        tabela.colocar(
            linha, 3,
            componentes.Rotulo(
                linha, componentes.formatar_valor(d["valor"]), "forte",
                anchor="e",
            ),
        )

        fornecedor_nome = "—"
        if d["fornecedor_id"]:
            forn = despesas.procurar_fornecedor(d["fornecedor_id"])
            if forn:
                fornecedor_nome = forn["nome"]
        tabela.colocar(
            linha, 4, componentes.Rotulo(linha, fornecedor_nome, "secundario")
        )
        tabela.colocar(
            linha, 5,
            componentes.Rotulo(
                linha, _formatar_data(d["data_pagamento"]), "secundario",
                anchor="center",
            ),
        )

        acoes = tabela.celula_acoes(linha, 6)
        acoes.adicionar(
            componentes.Botao(
                acoes, "Confirmar itens",
                lambda d=d: ConfirmarItensModal(self, d),
                "sucesso", width=112, height=26,
            )
        )

    # -- helpers de apresentação --------------------------------------

    def _titulo_seccao(self, texto, contagem, fila):
        bloco = componentes.Contentor(self._area)
        bloco.grid(row=fila, column=0, sticky="ew", pady=(8, 8))

        componentes.Rotulo(bloco, texto.upper(), "cartao").pack(side="left")
        componentes.Etiqueta(bloco, str(contagem), "azul", largura=30).pack(
            side="left", padx=(8, 0)
        )

    def _mensagem_vazio(self, texto, fila):
        componentes.Rotulo(
            self._area, texto, "secundario", wraplength=760, justify="left"
        ).grid(row=fila, column=0, sticky="nw", pady=(4, 20))


def _descricao(d, maximo=_MAX_DESCRICAO):
    """Descrição da despesa, cortada com "…" acima de `maximo`."""
    texto = d["descricao"] or "(sem descrição)"

    if len(texto) <= maximo:
        return texto

    return texto[: maximo - 1].rstrip() + "…"


# =====================================================================
# MODAL GERIR (despesa pendente) + SUB-MODAIS
# =====================================================================


class _AprovarDespesaModal(ctk.CTkToplevel):
    """Modal de aprovação de uma despesa pendente.

    Ficha read-only, aviso de vencida quando aplicável, e duas
    ações: Marcar como paga · Cancelar despesa.

    Só aparece no ecrã Aprovações. Edição de dados vive no
    `_EditarDespesaModal` (ecrã Despesas) — são sítios diferentes
    com propósitos diferentes.
    """

    def __init__(self, tela_aprovacoes, despesa):
        super().__init__(tela_aprovacoes)
        self.tela_aprovacoes = tela_aprovacoes
        self.despesa = despesa

        largura, altura = 520, 620
        self.title(f"Gerir — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_aprovacoes)
        componentes.centrar_sobre(self, tela_aprovacoes, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._montar_header()
        self._montar_ficha()
        self._montar_acoes()

    def _montar_header(self):
        ctk.CTkLabel(
            self,
            text=self.despesa["descricao"] or "(sem descrição)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=460,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=22, pady=(18, 2))

        categoria_nome = "—"
        categoria = despesas.procurar_categoria(self.despesa["categoria_id"])
        if categoria:
            categoria_nome = categoria["nome"]

        fornecedor_nome = ""
        if self.despesa["fornecedor_id"]:
            forn = despesas.procurar_fornecedor(self.despesa["fornecedor_id"])
            if forn:
                fornecedor_nome = f" · {forn['nome']}"

        ctk.CTkLabel(
            self,
            text=(
                f"{self.despesa['id']} · {categoria_nome}" f"{fornecedor_nome}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(0, 12))

    def _montar_ficha(self):
        # Aviso de vencida (só se aplicável).
        if despesas.esta_vencida(self.despesa):
            delta = (
                datetime.date.today() - self.despesa["data_vencimento"]
            ).days
            aviso = ctk.CTkFrame(
                self,
                fg_color=tema.VERMELHO_ERRO,
                corner_radius=tema.RAIO_CAMPO,
            )
            aviso.pack(fill="x", padx=22, pady=(0, 12))
            ctk.CTkLabel(
                aviso,
                text=(
                    f"⚠ Esta despesa está vencida.\n"
                    f"Data de vencimento: "
                    f"{_formatar_data(self.despesa['data_vencimento'])}"
                    f" · vencida há {delta} dias."
                ),
                text_color=tema.TEXTO_ERRO,
                font=ctk.CTkFont(size=11),
                justify="left",
                anchor="w",
                wraplength=440,
            ).pack(fill="x", padx=14, pady=10)

        ficha = ctk.CTkFrame(
            self,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=tema.RAIO_CAMPO,
        )
        ficha.pack(fill="x", padx=22, pady=(0, 14))

        interno = ctk.CTkFrame(ficha, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=12)

        self._linha_ficha(interno, "Categoria", self._nome_categoria())
        self._linha_ficha(interno, "Fornecedor", self._nome_fornecedor())
        self._linha_ficha(
            interno,
            "Valor",
            componentes.formatar_valor(self.despesa["valor"]),
            forte=True,
        )
        self._linha_ficha(
            interno,
            "Lançamento",
            _formatar_data(self.despesa["data_lancamento"]),
        )
        self._linha_ficha(
            interno,
            "Vencimento",
            _formatar_data(self.despesa["data_vencimento"]),
        )
        if self.despesa["unidade_id"]:
            uni = unidades.procurar(self.despesa["unidade_id"])
            self._linha_ficha(
                interno,
                "Unidade",
                (
                    f"{uni['nome']} ({uni['id']})"
                    if uni
                    else self.despesa["unidade_id"]
                ),
            )

    def _nome_categoria(self):
        c = despesas.procurar_categoria(self.despesa["categoria_id"])
        return c["nome"] if c else "—"

    def _nome_fornecedor(self):
        if not self.despesa["fornecedor_id"]:
            return "—"
        f = despesas.procurar_fornecedor(self.despesa["fornecedor_id"])
        return f["nome"] if f else "—"

    def _linha_ficha(self, master, rotulo, valor, forte=False):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", pady=3)

        ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=valor,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold" if forte else "normal"),
            anchor="w",
        ).pack(side="left")

    def _montar_acoes(self):
        bloco = ctk.CTkFrame(self, fg_color="transparent")
        bloco.pack(fill="x", padx=22, pady=(6, 18), side="bottom")

        ctk.CTkButton(
            bloco,
            text="Marcar como paga",
            height=36,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.VERDE,
            text_color=tema.VERDE,
            hover_color=tema.VERDE_LIVRE,
            command=self._marcar_paga,
        ).pack(fill="x", pady=3)

        ctk.CTkFrame(bloco, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", pady=(8, 5)
        )

        ctk.CTkButton(
            bloco,
            text="Cancelar despesa",
            height=36,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.TEXTO_ERRO,
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._cancelar_despesa,
        ).pack(fill="x", pady=3)

        ctk.CTkButton(
            bloco,
            text="Fechar",
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", pady=(8, 0))

    # -- ações --------------------------------------------------------

    def _marcar_paga(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        if not componentes.confirmar(
            f"Marcar {self.despesa['id']} como paga hoje?"
        ):
            return

        try:
            despesas.marcar_paga(
                self.despesa["id"],
                datetime.date.today(),
                autor,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Despesa {self.despesa['id']} marcada como paga."
        )
        self.destroy()
        self.tela_aprovacoes._recarregar()

    def _cancelar_despesa(self):
        self.destroy()
        _CancelarDespesaModal(self.tela_aprovacoes, self.despesa)


class _CancelarDespesaModal(ctk.CTkToplevel):
    """Sub-modal para cancelar uma despesa — exige motivo."""

    def __init__(self, tela_aprovacoes, despesa):
        super().__init__(tela_aprovacoes)
        self.tela_aprovacoes = tela_aprovacoes
        self.despesa = despesa

        largura, altura = 460, 380
        self.title(f"Cancelar — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_aprovacoes)
        componentes.centrar_sobre(self, tela_aprovacoes, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self,
            text="Cancelar despesa",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                f"{despesa['id']} · "
                f"{despesa['descricao'] or '(sem descrição)'}\n"
                f"Valor: {componentes.formatar_valor(despesa['valor'])}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text=(
                "A despesa não desaparece — fica com o estado "
                "'cancelada' no histórico."
            ),
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w",
            wraplength=400,
            padx=12,
            pady=10,
        ).pack(fill="x", padx=24, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Motivo do cancelamento *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_motivo = ctk.CTkTextbox(
            self, height=70, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_motivo.pack(fill="x", padx=24, pady=(2, 6))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(0, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Voltar",
            width=130,
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
            text="Cancelar despesa",
            width=160,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            text_color="#FFFFFF",
            command=self._cancelar,
        ).pack(side="right")

    def _cancelar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        motivo = self.campo_motivo.get("1.0", "end").strip()
        if not motivo:
            componentes.mostrar_erro("O motivo é obrigatório para cancelar.")
            return

        try:
            despesas.cancelar_despesa(self.despesa["id"], motivo, autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Despesa {self.despesa['id']} cancelada.")
        self.destroy()
        self.tela_aprovacoes._recarregar()
