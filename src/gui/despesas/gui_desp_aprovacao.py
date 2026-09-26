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


class Aprovacoes(ctk.CTkFrame):
    """Ecrã "Aprovações" — despesas pendentes + itens VIA 2 por
    confirmar.

    Duas secções, cada uma com a sua tabela:
      - Despesas pendentes (VIA 1) → botão "Gerir" abre o
        `_GerirDespesaPendenteModal`.
      - Itens de despesa via stock por confirmar → botão
        "Confirmar" abre o `ConfirmarItensModal`.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        self._categorias_por_id = {}

        componentes.Cabecalho(self, titulo="Aprovações").pack(fill="x")

        self._area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._area.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento -------------------------------------------------

    def _recarregar(self):
        for w in self._area.winfo_children():
            w.destroy()

        self._categorias_por_id = {
            c["id"]: c for c in despesas.listar_categorias()
        }

        self._desenhar_seccao_pendentes()
        self._desenhar_seccao_itens_via2()

    # -- secção 1 — despesas pendentes --------------------------------

    def _desenhar_seccao_pendentes(self):
        pendentes = despesas.listar_despesas(estado="pendente")

        self._titulo_seccao("Despesas pendentes", len(pendentes))

        if not pendentes:
            self._mensagem_vazio(
                "Sem despesas pendentes. "
                "Todas as despesas lançadas já foram pagas ou "
                "canceladas."
            )
            return

        tabela = ctk.CTkFrame(
            self._area,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        tabela.pack(fill="x", pady=(0, 20))

        # Cabeçalho (grid alinhado com as linhas — mesma largura
        # de coluna em ambos).
        cabecalho = ctk.CTkFrame(
            tabela,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")
        grelha_cab = ctk.CTkFrame(cabecalho, fg_color="transparent")
        grelha_cab.pack(fill="x", padx=16, pady=8)

        for texto, largura, alinhamento in (
            ("ID", 80, "w"),
            ("DESCRIÇÃO", 200, "w"),
            ("CATEGORIA", 110, "w"),
            ("VALOR", 90, "e"),
            ("VENCIMENTO", 100, "center"),
            ("SITUAÇÃO", 130, "w"),
            ("LANÇAMENTO", 100, "center"),
            ("AÇÕES", 100, "center"),
        ):
            ctk.CTkLabel(
                grelha_cab,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor=alinhamento,
            ).pack(side="left")

        ctk.CTkFrame(tabela, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for i, d in enumerate(pendentes):
            self._linha_pendente(tabela, d, i)

    def _linha_pendente(self, master, d, indice):
        vencida = despesas.esta_vencida(d)

        cor_fundo = tema.LINHA_ALTERNADA if indice % 2 else "transparent"

        linha = ctk.CTkFrame(master, fg_color=cor_fundo, height=52)
        linha.pack(fill="x")
        linha.pack_propagate(False)

        # Borda vermelha à esquerda se vencida — simulada com um
        # frame fino à esquerda.
        if vencida:
            ctk.CTkFrame(linha, width=4, fg_color=tema.VERMELHO_ERRO).pack(
                side="left", fill="y"
            )

        grelha = ctk.CTkFrame(linha, fg_color="transparent")
        grelha.pack(fill="x", padx=16, pady=8)

        # ID
        ctk.CTkLabel(
            grelha,
            text=d["id"],
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=90,
            anchor="w",
        ).pack(side="left")

        # Descrição
        ctk.CTkLabel(
            grelha,
            text=d["descricao"] or "(sem descrição)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            width=200,
            anchor="w",
        ).pack(side="left")

        # Categoria
        cat = self._categorias_por_id.get(d["categoria_id"])
        ctk.CTkLabel(
            grelha,
            text=cat["nome"] if cat else "—",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=130,
            anchor="w",
        ).pack(side="left")

        # Valor
        ctk.CTkLabel(
            grelha,
            text=componentes.formatar_valor(d["valor"]),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=110,
            anchor="e",
        ).pack(side="left")

        # Vencimento
        ctk.CTkLabel(
            grelha,
            text=_formatar_data(d["data_vencimento"]),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=100,
            anchor="center",
        ).pack(side="left")

        # Situação (texto descritivo do prazo)
        ctk.CTkLabel(
            grelha,
            text=self._situacao_prazo(d),
            text_color=(
                tema.TEXTO_ERRO if vencida else tema.COR_TEXTO_SECUNDARIO
            ),
            font=ctk.CTkFont(size=11),
            width=130,
            anchor="w",
        ).pack(side="left")

        # Lançamento
        ctk.CTkLabel(
            grelha,
            text=_formatar_data(d["data_lancamento"]),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="center",
        ).pack(side="left")

        # Botão Gerir
        ctk.CTkButton(
            grelha,
            text="Gerir",
            width=76,
            height=26,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=lambda d=d: _AprovarDespesaModal(self, d),
        ).pack(side="left")

    def _situacao_prazo(self, d):
        """Texto descritivo do prazo: 'vencida há X dias',
        'vence em X dias' ou 'sem prazo'."""
        if d["data_vencimento"] is None:
            return "sem prazo"

        delta = (d["data_vencimento"] - datetime.date.today()).days
        if delta < 0:
            return f"vencida há {abs(delta)} dias"
        if delta == 0:
            return "vence hoje"
        return f"vence em {delta} dias"

    # -- secção 2 — itens VIA 2 por confirmar -------------------------

    def _desenhar_seccao_itens_via2(self):
        # Todas as despesas via stock cujos itens ainda não foram
        # confirmados. Filtra pela flag `itens_confirmados`.
        todas = despesas.listar_despesas(estado="paga")
        por_confirmar = [d for d in todas if not d["itens_confirmados"]]

        self._titulo_seccao(
            "Itens de despesa por confirmar (VIA 2)",
            len(por_confirmar),
        )

        if not por_confirmar:
            self._mensagem_vazio(
                "Sem itens por confirmar. Todas as compras via "
                "stock já foram verificadas."
            )
            return

        tabela = ctk.CTkFrame(
            self._area,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        tabela.pack(fill="x", pady=(0, 12))

        cabecalho = ctk.CTkFrame(
            tabela,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")
        grelha_cab = ctk.CTkFrame(cabecalho, fg_color="transparent")
        grelha_cab.pack(fill="x", padx=16, pady=8)

        for texto, largura, alinhamento in (
            ("ID", 90, "w"),
            ("DESCRIÇÃO", 260, "w"),
            ("ITENS", 110, "center"),
            ("VALOR", 110, "e"),
            ("FORNECEDOR", 140, "w"),
            ("PAGO EM", 110, "center"),
            ("AÇÕES", 160, "center"),
        ):
            ctk.CTkLabel(
                grelha_cab,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor=alinhamento,
            ).pack(side="left")

        ctk.CTkFrame(tabela, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for i, d in enumerate(por_confirmar):
            self._linha_itens_via2(tabela, d, i)

    def _linha_itens_via2(self, master, d, indice):
        cor_fundo = tema.LINHA_ALTERNADA if indice % 2 else "transparent"

        linha = ctk.CTkFrame(master, fg_color=cor_fundo, height=52)
        linha.pack(fill="x")
        linha.pack_propagate(False)

        grelha = ctk.CTkFrame(linha, fg_color="transparent")
        grelha.pack(fill="x", padx=16, pady=8)

        # ID
        ctk.CTkLabel(
            grelha,
            text=d["id"],
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=90,
            anchor="w",
        ).pack(side="left")

        # Descrição + badge "via stock"
        bloco_desc = ctk.CTkFrame(grelha, fg_color="transparent")
        bloco_desc.pack(side="left")
        ctk.CTkLabel(
            bloco_desc,
            text=d["descricao"] or "(sem descrição)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            bloco_desc,
            text=" via stock ",
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(side="left", padx=(6, 0))

        # Bloco invisível para reservar largura à descrição (260px)
        # — sem isto, o "pack" encolhia a célula ao tamanho real.
        espacador = ctk.CTkFrame(
            grelha, fg_color="transparent", width=260, height=1
        )
        espacador.pack(side="left")
        espacador.pack_propagate(False)

        # Contagem de itens
        itens = despesas.listar_itens_despesa(d["id"])
        ctk.CTkLabel(
            grelha,
            text=f"{len(itens)} item(ns)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="center",
        ).pack(side="left")

        # Valor
        ctk.CTkLabel(
            grelha,
            text=componentes.formatar_valor(d["valor"]),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=110,
            anchor="e",
        ).pack(side="left")

        # Fornecedor
        fornecedor_nome = "—"
        if d["fornecedor_id"]:
            forn = despesas.procurar_fornecedor(d["fornecedor_id"])
            if forn:
                fornecedor_nome = forn["nome"]
        ctk.CTkLabel(
            grelha,
            text=fornecedor_nome,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=140,
            anchor="w",
        ).pack(side="left")

        # Pago em
        ctk.CTkLabel(
            grelha,
            text=_formatar_data(d["data_pagamento"]),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="center",
        ).pack(side="left")

        # Botão Confirmar
        ctk.CTkButton(
            grelha,
            text="Confirmar itens",
            width=140,
            height=26,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda d=d: ConfirmarItensModal(self, d),
        ).pack(side="left")

    # -- helpers de apresentação --------------------------------------

    def _titulo_seccao(self, texto, contagem):
        bloco = ctk.CTkFrame(self._area, fg_color="transparent")
        bloco.pack(fill="x", pady=(8, 8))

        ctk.CTkLabel(
            bloco,
            text=texto.upper(),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            bloco,
            text=f"  {contagem}",
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=10,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=9,
            pady=2,
        ).pack(side="left")

    def _mensagem_vazio(self, texto):
        ctk.CTkLabel(
            self._area,
            text=texto,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(4, 20))


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
