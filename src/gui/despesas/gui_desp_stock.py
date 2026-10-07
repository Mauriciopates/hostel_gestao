"""VIA 2 — despesa via stock: `NovaDespesaStockModal` e o
seletor de produto."""

import datetime

import customtkinter as ctk

import despesas
import estoque

from .. import componentes
from .. import tema
from . import gui_desp_comum

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_desp_comum).
_parse_decimal = gui_desp_comum.parse_decimal
_autor_atual = gui_desp_comum.autor_atual
_parse_data = gui_desp_comum.parse_data


# =====================================================================
# MODAIS DA VIA 2 — despesa via stock + confirmação dos itens
# =====================================================================


class NovaDespesaStockModal(ctk.CTkToplevel):
    """Formulário VIA 2 — despesa via stock.

    Categoria fixa "Compra de Stock" (mostrada como campo
    disabled). Sem vencimento, sem unidade, sem recorrente. A
    tabela de produtos é dinâmica: começa com uma linha, "+ Adicionar
    produto" acrescenta mais, o × remove.

    Nasce `paga` — o backend trata disso. Os itens ficam por
    confirmar (`itens_confirmados=False`) e só entram no stock
    quando o Master/Admin os confirmar (no ecrã Aprovações).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        # Referências preenchidas em _carregar_dados.
        self._produtos = []
        self._fornecedores = []

        # Cada elemento é um dict: {"moldura", "combo", "quantidade"}.
        self._linhas = []

        largura, altura = 660, 760
        self.title("Nova Despesa via Stock")
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

    # -- montagem ----------------------------------------------------

    def _montar_header(self):
        ctk.CTkLabel(
            self,
            text="Nova Despesa via Stock",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "Fica paga na hora. Os itens só entram no stock "
                "depois de confirmados, no ecrã Aprovações."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=24, pady=(0, 14))

    def _montar_campos(self):
        area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=24)
        self._area = area

        ctk.CTkLabel(
            area,
            text="IDENTIFICAÇÃO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.campo_descricao = self._campo_texto(
            area,
            "Descrição *",
            "ex.: Compra de lixívias e detergentes de setembro",
        )

        linha = ctk.CTkFrame(area, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(0, weight=1, uniform="col")
        linha.grid_columnconfigure(1, weight=1, uniform="col")

        # Categoria — campo disabled, cinzento.
        bloco_cat = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_cat.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_cat,
            text="Categoria",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.campo_categoria = ctk.CTkEntry(
            bloco_cat,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.LINHA_ALTERNADA,
            text_color=tema.COR_TEXTO_SECUNDARIO,
        )
        self.campo_categoria.insert(0, "Compra de Stock")
        self.campo_categoria.configure(state="disabled")
        self.campo_categoria.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(
            bloco_cat,
            text="Fixada automaticamente.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        # Fornecedor.
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
            bloco_forn,
            values=["Nenhum"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_fornecedor.set("Nenhum")
        self.combo_fornecedor.pack(fill="x", pady=(2, 0))

        self.campo_data_lancamento = self._campo_texto(
            area,
            "Data de lançamento *",
            "dd/mm/aaaa",
        )
        self.campo_data_lancamento.insert(
            0, datetime.date.today().strftime("%d/%m/%Y")
        )

        ctk.CTkLabel(
            area,
            text="PRODUTOS",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        # Cartão com cabeçalho + linhas dinâmicas + botão add.
        cartao = ctk.CTkFrame(
            area,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x")

        cabecalho = ctk.CTkFrame(
            cartao,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")
        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)
        for texto, largura in (
            ("PRODUTO", 320),
            ("QUANTIDADE", 110),
            ("", 40),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        self._area_linhas = ctk.CTkFrame(cartao, fg_color="transparent")
        self._area_linhas.pack(fill="x", padx=16, pady=(6, 8))

        ctk.CTkButton(
            cartao,
            text="+ Adicionar produto",
            width=180,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            command=self._acrescentar_linha,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # Aviso sobre criar produto novo.
        aviso = ctk.CTkFrame(
            area,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        aviso.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(
            aviso,
            text=(
                "Se o produto ainda não existir no catálogo, "
                'escolhe "+ Criar produto novo" na lista — os '
                "dados completos são pedidos a seguir."
            ),
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            area,
            text="VALOR E OBSERVAÇÕES",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        bloco_valor = ctk.CTkFrame(
            area,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        bloco_valor.pack(fill="x")
        ctk.CTkLabel(
            bloco_valor,
            text="Valor total da despesa *",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 2))
        self.campo_valor = ctk.CTkEntry(
            bloco_valor,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="0,00 €",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.campo_valor.pack(fill="x", padx=12)
        ctk.CTkLabel(
            bloco_valor,
            text=(
                "Digitado à mão. Não é a soma dos itens — o valor "
                "vive só aqui."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=12, pady=(2, 10))

        self.campo_comprovativo = self._campo_texto(
            area,
            "Comprovativo",
            "ex.: fatura_makro_set2026.pdf (opcional)",
        )

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
            text="Criar despesa",
            width=170,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    # -- helpers de campo --------------------------------------------

    def _campo_texto(self, master, rotulo, placeholder=""):
        ctk.CTkLabel(
            master,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        # Datas com CampoData: só algarismos, barras automáticas.
        classe = (
            componentes.CampoData
            if placeholder.startswith("dd/mm/aaaa")
            else ctk.CTkEntry
        )
        entrada = classe(
            master,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x")
        return entrada

    # -- tabela dinâmica de produtos ---------------------------------

    def _rotulos_produtos(self):
        """Rótulos do dropdown de cada linha. Inclui um item
        especial no fim, "+ Criar produto novo…", que abre o
        sub-modal."""
        return [f"{p['nome']} ({p['id']})" for p in self._produtos] + [
            "+ Criar produto novo…"
        ]

    def _produto_por_rotulo(self, rotulo):
        for p in self._produtos:
            if f"{p['nome']} ({p['id']})" == rotulo:
                return p
        return None

    def _acrescentar_linha(self):
        if not self._produtos:
            # Sem produtos no catálogo — não há linha possível. O
            # utilizador tem de criar um produto novo primeiro.
            self._abrir_criar_produto()
            return

        moldura = ctk.CTkFrame(self._area_linhas, fg_color="transparent")
        moldura.pack(fill="x", pady=3)

        combo = componentes.Seletor(
            moldura,
            values=self._rotulos_produtos(),
            width=320,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda valor, m=moldura: self._ao_escolher_produto(
                valor, m
            ),
        )
        combo.set(self._rotulos_produtos()[0])
        combo.pack(side="left")

        campo_qtd = ctk.CTkEntry(
            moldura,
            width=110,
            corner_radius=tema.RAIO_CAMPO,
            justify="center",
            placeholder_text="0",
        )
        campo_qtd.pack(side="left", padx=(10, 0))

        # Guarda a referência antes de a limpar — o botão × vai
        # precisar de apagar a linha inteira.
        linha = {
            "moldura": moldura,
            "combo": combo,
            "quantidade": campo_qtd,
        }
        self._linhas.append(linha)

        ctk.CTkButton(
            moldura,
            text="×",
            width=30,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=lambda lin=linha: self._remover_linha(lin),
        ).pack(side="left", padx=(10, 0))

    def _remover_linha(self, linha):
        if linha in self._linhas:
            self._linhas.remove(linha)
        linha["moldura"].destroy()

    def _ao_escolher_produto(self, valor, moldura):
        """Se o valor escolhido for "+ Criar produto novo…", abre o
        sub-modal e volta a pôr a linha no primeiro produto real
        (a linha nova criada pelo sub-modal será acrescentada
        automaticamente)."""
        if valor != "+ Criar produto novo…":
            return
        # Volta ao primeiro produto, antes de abrir o sub-modal.
        if self._produtos:
            moldura.destroy()
            self._linhas = [
                lin for lin in self._linhas if lin["moldura"] is not moldura
            ]
        self._abrir_criar_produto()

    def _abrir_criar_produto(self):
        _EscolherProdutoModal(self, ao_criar=self._produto_foi_criado)

    def _produto_foi_criado(self, produto):
        """Chamada pelo `_EscolherProdutoModal` quando um produto
        novo é criado. Adiciona-o à lista local e cria a linha."""
        self._produtos.append(produto)
        self._acrescentar_linha()
        # Põe a última linha no produto novo.
        if self._linhas:
            ultima = self._linhas[-1]
            rotulo = f"{produto['nome']} ({produto['id']})"
            ultima["combo"].set(rotulo)

    # -- carregamento / leitura --------------------------------------

    def _carregar_dados(self):
        # Categoria "Compra de Stock" — valida que existe e está
        # ativa. Se não estiver, avisa e fecha (não há como criar
        # despesa VIA 2 sem ela).
        try:
            despesas.criar_despesa_stock  # noqa: B018 (marca de API)
        except AttributeError:
            pass

        self._produtos = estoque.listar_produtos()
        self._fornecedores = despesas.listar_fornecedores()

        nomes_forn = ["Nenhum"] + [f["nome"] for f in self._fornecedores]
        self.combo_fornecedor.configure(values=nomes_forn)
        self.combo_fornecedor.set(nomes_forn[0])

        # Cria a primeira linha, para o utilizador começar com um
        # produto já visível.
        self._acrescentar_linha()

    def _id_fornecedor(self):
        nome = self.combo_fornecedor.get()
        if nome == "Nenhum":
            return None
        for f in self._fornecedores:
            if f["nome"] == nome:
                return f["id"]
        return None

    def _itens(self):
        """Devolve a lista de itens no formato que o módulo de
        negócio espera. Levanta ValueError se alguma linha estiver
        mal preenchida."""
        itens = []
        for linha in self._linhas:
            rotulo = linha["combo"].get()
            produto = self._produto_por_rotulo(rotulo)
            if produto is None:
                raise ValueError("Escolhe um produto válido em cada linha.")

            texto_qtd = linha["quantidade"].get().strip()
            if not texto_qtd.isdigit() or int(texto_qtd) <= 0:
                raise ValueError(
                    f"Quantidade inválida para '{produto['nome']}'."
                )

            itens.append(
                {
                    "produto_id": produto["id"],
                    "quantidade": int(texto_qtd),
                }
            )

        if not itens:
            raise ValueError("A despesa tem de ter pelo menos um produto.")
        return itens

    # -- guardar ------------------------------------------------------

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

            valor_total = _parse_decimal(
                self.campo_valor.get(),
                "Valor total",
            )

            data_lancamento = _parse_data(
                self.campo_data_lancamento.get(), "Data de lançamento"
            )
            if data_lancamento is None:
                raise ValueError("A data de lançamento é obrigatória.")

            itens = self._itens()
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        comprovativo = self.campo_comprovativo.get().strip()

        try:
            despesa, _itens_criados = despesas.criar_despesa_stock(
                itens=itens,
                valor_total=valor_total,
                data_lancamento=data_lancamento,
                responsavel_id=autor["id"],
                autor=autor,
                fornecedor_id=self._id_fornecedor(),
                descricao=descricao,
                comprovativo_caminho=comprovativo,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Despesa {despesa['id']} criada. Os itens aguardam "
            f"confirmação no ecrã Aprovações."
        )
        self.destroy()
        self.tela_lista._recarregar()


class _EscolherProdutoModal(ctk.CTkToplevel):
    """Sub-modal para criar um produto novo — chamado dentro do
    formulário VIA 2, quando o utilizador escolhe "+ Criar produto
    novo…" no dropdown de produto.

    Pede os 4 campos completos (`nome`, `unidade_medida`,
    `stock_minimo`, `tipo_produto`) e chama `estoque.criar_produto`.
    Devolve o produto criado via `ao_criar(produto)`.
    """

    def __init__(self, master, ao_criar):
        super().__init__(master)
        self.ao_criar = ao_criar

        largura, altura = 480, 480
        self.title("Criar produto novo")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        componentes.centrar_sobre(self, master, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self,
            text="Criar produto novo",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "O produto fica logo disponível no catálogo. "
                "Preenche os 4 campos."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=420,
        ).pack(anchor="w", padx=24, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Nome *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 8))

        ctk.CTkLabel(
            self,
            text="Unidade de medida *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_unidade = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: un, L, kg, cx",
        )
        self.campo_unidade.pack(fill="x", padx=24, pady=(2, 8))

        ctk.CTkLabel(
            self,
            text="Stock mínimo",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_stock = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="0",
        )
        self.campo_stock.insert(0, "0")
        self.campo_stock.pack(fill="x", padx=24, pady=(2, 8))

        ctk.CTkLabel(
            self,
            text="Tipo de produto *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.combo_tipo = componentes.Seletor(
            self,
            values=["consumivel", "roupa_cama", "roupa_banho", "outro"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_tipo.set("consumivel")
        self.combo_tipo.pack(fill="x", padx=24, pady=(2, 14))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(0, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
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
            text="Criar produto",
            width=150,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):

        nome = self.campo_nome.get().strip()
        unidade = self.campo_unidade.get().strip()

        if not nome or not unidade:
            componentes.mostrar_erro(
                "Nome e unidade de medida são obrigatórios."
            )
            return

        texto_stock = self.campo_stock.get().strip() or "0"
        if not texto_stock.isdigit():
            componentes.mostrar_erro(
                "O stock mínimo tem de ser um número inteiro."
            )
            return

        try:
            produto = estoque.criar_produto(
                nome=nome,
                unidade_medida=unidade,
                stock_minimo=int(texto_stock),
                tipo_produto=self.combo_tipo.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.ao_criar(produto)
        self.destroy()
