"""VIA 1 — despesa manual: `NovaDespesaManualModal` e
`DividirPorPropriedadeModal`."""

import datetime
from decimal import Decimal

import customtkinter as ctk

import despesas
import propriedades
import unidades

from .. import componentes
from .. import tema
from . import gui_desp_comum

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_desp_comum).
_parse_decimal = gui_desp_comum.parse_decimal
_autor_atual = gui_desp_comum.autor_atual
_parse_data = gui_desp_comum.parse_data
_rotulo_unidade = gui_desp_comum.rotulo_unidade


class NovaDespesaManualModal(ctk.CTkToplevel):
    """Formulário da VIA 1 — despesa manual.

    Categoria obrigatória (esconde "Compra de Stock"), descrição
    obrigatória, valor obrigatório, resto opcional. Nasce
    `pendente` — o backend trata disso.
    """

    # Título fixo — usado nos erros, para a mensagem ser coerente.
    _TITULO = "Nova Despesa Manual"

    def __init__(self, tela_lista, despesa_para_editar=None):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.despesa_para_editar = despesa_para_editar

        # Referências preenchidas em _carregar_dados().
        self._categorias = []
        self._fornecedores = []
        self._unidades = []

        largura, altura = 620, 720
        self.title(self._TITULO)
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
            text=self._TITULO,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text="Fica pendente até ser marcada como paga.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
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
            area, "Descrição *", "ex.: Conta EDP — Setembro 2026"
        )

        linha = ctk.CTkFrame(area, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(0, weight=1, uniform="col")
        linha.grid_columnconfigure(1, weight=1, uniform="col")

        self.combo_categoria = self._campo_dropdown(
            linha, 0, "Categoria *", []
        )
        self.combo_fornecedor = self._campo_dropdown(
            linha, 1, "Fornecedor", ["— Nenhum —"]
        )

        linha2 = ctk.CTkFrame(area, fg_color="transparent")
        linha2.pack(fill="x", pady=4)
        linha2.grid_columnconfigure(0, weight=1, uniform="col")
        linha2.grid_columnconfigure(1, weight=1, uniform="col")

        self.campo_valor = self._campo_texto_em_linha(
            linha2, 0, "Valor *", "0,00 €"
        )
        self.campo_data_lancamento = self._campo_texto_em_linha(
            linha2,
            1,
            "Data de lançamento *",
            "dd/mm/aaaa",
            valor_inicial=datetime.date.today().strftime("%d/%m/%Y"),
        )

        linha3 = ctk.CTkFrame(area, fg_color="transparent")
        linha3.pack(fill="x", pady=4)
        linha3.grid_columnconfigure(0, weight=1, uniform="col")
        linha3.grid_columnconfigure(1, weight=1, uniform="col")

        self.campo_data_vencimento = self._campo_texto_em_linha(
            linha3, 0, "Data de vencimento", "dd/mm/aaaa (opcional)"
        )
        self.combo_unidade = self._campo_dropdown(
            linha3, 1, "Unidade", ["— Nenhuma (despesa geral) —"]
        )

        ctk.CTkLabel(
            area,
            text="OBSERVAÇÕES E COMPROVATIVO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        self.campo_comprovativo = self._campo_texto(
            area, "Comprovativo", "ex.: edp_set2026.pdf (opcional)"
        )

        ctk.CTkFrame(area, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", pady=(12, 12)
        )

        self.check_recorrente = ctk.BooleanVar(value=False)
        bloco_rec = ctk.CTkFrame(
            area,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        bloco_rec.pack(fill="x")
        interno_rec = ctk.CTkFrame(bloco_rec, fg_color="transparent")
        interno_rec.pack(fill="x", padx=12, pady=10)
        ctk.CTkCheckBox(
            interno_rec,
            text="Despesa recorrente (mensal)",
            variable=self.check_recorrente,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            interno_rec,
            text="Gera automaticamente o lançamento do mês "
            "seguinte com os mesmos dados. O valor fica em branco.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=520,
        ).pack(anchor="w", pady=(4, 0))

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
        entrada = ctk.CTkEntry(
            master,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x")
        return entrada

    def _campo_texto_em_linha(
        self, master, coluna, rotulo, placeholder="", valor_inicial=None
    ):
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=0, column=coluna, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        entrada = ctk.CTkEntry(
            bloco,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x", pady=(2, 0))
        if valor_inicial is not None:
            entrada.insert(0, valor_inicial)
        return entrada

    def _campo_dropdown(self, master, coluna, rotulo, opcoes):
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=0, column=coluna, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        combo = componentes.Seletor(
            bloco,
            values=opcoes or ["—"],
            corner_radius=tema.RAIO_CAMPO,
        )
        if opcoes:
            combo.set(opcoes[0])
        combo.pack(fill="x", pady=(2, 0))
        return combo

    # -- carregamento de dados ---------------------------------------

    def _carregar_dados(self):
        # Categorias ativas — esconder "Compra de Stock" (só para
        # VIA 2).
        self._categorias = [
            c
            for c in despesas.listar_categorias()
            if c["nome"] != "Compra de Stock"
        ]
        nomes_cat = [c["nome"] for c in self._categorias] or ["—"]
        self.combo_categoria.configure(values=nomes_cat)
        self.combo_categoria.set(nomes_cat[0])

        # Fornecedores ativos.
        self._fornecedores = despesas.listar_fornecedores()
        nomes_forn = ["— Nenhum —"] + [f["nome"] for f in self._fornecedores]
        self.combo_fornecedor.configure(values=nomes_forn)
        self.combo_fornecedor.set(nomes_forn[0])

        # Unidades ativas com nome da propriedade.
        self._unidades = unidades.listar_com_propriedade()
        self._unidade_por_rotulo = {
            _rotulo_unidade(u): u["id"] for u in self._unidades
        }
        rotulos_uni = ["— Nenhuma (despesa geral) —"] + sorted(
            self._unidade_por_rotulo
        )
        self.combo_unidade.configure(values=rotulos_uni)
        self.combo_unidade.set(rotulos_uni[0])

    # -- leitura dos campos ------------------------------------------

    def _id_categoria(self):
        nome = self.combo_categoria.get()
        for c in self._categorias:
            if c["nome"] == nome:
                return c["id"]
        return None

    def _id_fornecedor(self):
        nome = self.combo_fornecedor.get()
        if nome == "— Nenhum —":
            return None
        for f in self._fornecedores:
            if f["nome"] == nome:
                return f["id"]
        return None

    def _id_unidade(self):
        rotulo = self.combo_unidade.get()
        return self._unidade_por_rotulo.get(rotulo)

    # -- guardar ------------------------------------------------------

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        # Validação de formato (conversões).
        try:
            categoria_id = self._id_categoria()
            if categoria_id is None:
                raise ValueError("Escolhe uma categoria.")

            descricao = self.campo_descricao.get().strip()
            if not descricao:
                raise ValueError("A descrição é obrigatória.")

            valor = _parse_decimal(
                self.campo_valor.get(),
                "Valor",
            )
            data_lancamento = _parse_data(
                self.campo_data_lancamento.get(), "Data de lançamento"
            )
            if data_lancamento is None:
                raise ValueError("A data de lançamento é obrigatória.")

            data_vencimento = _parse_data(
                self.campo_data_vencimento.get(),
                "Data de vencimento",
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        comprovativo = self.campo_comprovativo.get().strip()

        try:
            despesas.criar_despesa_manual(
                categoria_id=categoria_id,
                valor=valor,
                data_lancamento=data_lancamento,
                responsavel_id=autor["id"],
                autor=autor,
                unidade_id=self._id_unidade(),
                fornecedor_id=self._id_fornecedor(),
                data_vencimento=data_vencimento,
                descricao=descricao,
                comprovativo_caminho=comprovativo,
                recorrente=self.check_recorrente.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso("Despesa criada com sucesso.")
        self.destroy()
        self.tela_lista._recarregar()


# PENDÊNCIA (26/09/2026): nenhum botão abre este modal ainda. A regra
# de negócio existe (`despesas.dividir_despesa_por_propriedade`);
# falta o atalho no `NovaDespesaManualModal` ou na `ListaDespesas`.
class DividirPorPropriedadeModal(ctk.CTkToplevel):
    """Formulário VIA 1 com "Aplicar a · dividir por propriedade".

    É aberto a partir do `NovaDespesaManualModal` (ou diretamente
    pela `ListaDespesas`, se adicionarmos um atalho futuro). Reusa
    a mesma estrutura de campos, só que troca o campo "Unidade" por
    "Aplicar a" + "Propriedade a dividir".
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self._categorias = []
        self._fornecedores = []
        self._propriedades = []
        self._unidades_por_propriedade = {}

        largura, altura = 620, 740
        self.title("Nova Despesa — dividir por propriedade")
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
            text="Nova Despesa — dividir por propriedade",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "A mesma despesa é dividida igualmente pelas "
                "unidades ativas da propriedade escolhida."
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
            area, "Descrição *", "ex.: Internet — Setembro 2026"
        )

        linha = ctk.CTkFrame(area, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(0, weight=1, uniform="col")
        linha.grid_columnconfigure(1, weight=1, uniform="col")

        self.combo_categoria = self._campo_dropdown(
            linha, 0, "Categoria *", []
        )
        self.combo_fornecedor = self._campo_dropdown(
            linha, 1, "Fornecedor", ["— Nenhum —"]
        )

        linha2 = ctk.CTkFrame(area, fg_color="transparent")
        linha2.pack(fill="x", pady=4)
        linha2.grid_columnconfigure(0, weight=1, uniform="col")
        linha2.grid_columnconfigure(1, weight=1, uniform="col")

        self.campo_valor = self._campo_texto_em_linha(
            linha2, 0, "Valor total *", "0,00 €"
        )
        self.campo_data_lancamento = self._campo_texto_em_linha(
            linha2,
            1,
            "Data de lançamento *",
            "dd/mm/aaaa",
            valor_inicial=datetime.date.today().strftime("%d/%m/%Y"),
        )

        linha3 = ctk.CTkFrame(area, fg_color="transparent")
        linha3.pack(fill="x", pady=4)
        linha3.grid_columnconfigure(0, weight=1, uniform="col")
        linha3.grid_columnconfigure(1, weight=1, uniform="col")

        self.campo_data_vencimento = self._campo_texto_em_linha(
            linha3, 0, "Data de vencimento", "dd/mm/aaaa (opcional)"
        )

        # Bloco da propriedade (destacado a azul claro)
        bloco_prop = ctk.CTkFrame(
            linha3,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        bloco_prop.grid(row=0, column=1, sticky="ew", padx=4)

        ctk.CTkLabel(
            bloco_prop,
            text="Propriedade a dividir *",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))

        self.combo_propriedade = componentes.Seletor(
            bloco_prop,
            values=["—"],
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _v: self._atualizar_previsao(),
        )
        self.combo_propriedade.pack(fill="x", padx=10, pady=(0, 4))

        self.rotulo_previsao = ctk.CTkLabel(
            bloco_prop,
            text="",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=240,
        )
        self.rotulo_previsao.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            area,
            text="OBSERVAÇÕES E COMPROVATIVO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        self.campo_comprovativo = self._campo_texto(
            area, "Comprovativo", "ex.: fatura_set2026.pdf (opcional)"
        )

        ctk.CTkFrame(area, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", pady=(12, 12)
        )

        self.check_recorrente = ctk.BooleanVar(value=False)
        bloco_rec = ctk.CTkFrame(
            area,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        bloco_rec.pack(fill="x")
        interno_rec = ctk.CTkFrame(bloco_rec, fg_color="transparent")
        interno_rec.pack(fill="x", padx=12, pady=10)
        ctk.CTkCheckBox(
            interno_rec,
            text="Despesa recorrente (mensal)",
            variable=self.check_recorrente,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            interno_rec,
            text="Gera automaticamente o lançamento do mês "
            "seguinte (todas as unidades).",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

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

        self.botao_criar = ctk.CTkButton(
            rodape,
            text="Dividir e criar despesas",
            width=220,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._guardar,
        )
        self.botao_criar.pack(side="right")

    # -- helpers de campo (iguais aos do modal VIA 1) ----------------

    def _campo_texto(self, master, rotulo, placeholder=""):
        ctk.CTkLabel(
            master,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        entrada = ctk.CTkEntry(
            master,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x")
        return entrada

    def _campo_texto_em_linha(
        self, master, coluna, rotulo, placeholder="", valor_inicial=None
    ):
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=0, column=coluna, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        entrada = ctk.CTkEntry(
            bloco,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x", pady=(2, 0))
        if valor_inicial is not None:
            entrada.insert(0, valor_inicial)
        return entrada

    def _campo_dropdown(self, master, coluna, rotulo, opcoes):
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=0, column=coluna, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        combo = componentes.Seletor(
            bloco,
            values=opcoes or ["—"],
            corner_radius=tema.RAIO_CAMPO,
        )
        if opcoes:
            combo.set(opcoes[0])
        combo.pack(fill="x", pady=(2, 0))
        return combo

    # -- carregamento de dados ---------------------------------------

    def _carregar_dados(self):
        self._categorias = [
            c
            for c in despesas.listar_categorias()
            if c["nome"] != "Compra de Stock"
        ]
        nomes_cat = [c["nome"] for c in self._categorias] or ["—"]
        self.combo_categoria.configure(values=nomes_cat)
        self.combo_categoria.set(nomes_cat[0])

        self._fornecedores = despesas.listar_fornecedores()
        nomes_forn = ["— Nenhum —"] + [f["nome"] for f in self._fornecedores]
        self.combo_fornecedor.configure(values=nomes_forn)
        self.combo_fornecedor.set(nomes_forn[0])

        self._propriedades = propriedades.listar()
        # Guarda as unidades ativas de cada propriedade para a
        # previsão e para o `criar_despesa_manual`.
        self._unidades_por_propriedade = {
            p["id"]: unidades.listar(
                propriedade_id=p["id"], incluir_inativas=False
            )
            for p in self._propriedades
        }
        rotulos = [f"{p['nome']} ({p['id']})" for p in self._propriedades]
        self._propriedade_por_rotulo = {
            f"{p['nome']} ({p['id']})": p["id"] for p in self._propriedades
        }
        self.combo_propriedade.configure(values=rotulos or ["—"])
        if rotulos:
            self.combo_propriedade.set(rotulos[0])
        self._atualizar_previsao()

    def _atualizar_previsao(self):
        """Recalcula o texto da previsão por baixo do dropdown de
        propriedade: quantas unidades ativas e quanto vale cada
        despesa."""
        rotulo = self.combo_propriedade.get()
        prop_id = self._propriedade_por_rotulo.get(rotulo)
        if prop_id is None:
            self.rotulo_previsao.configure(text="")
            return

        ativas = self._unidades_por_propriedade.get(prop_id, [])
        n = len(ativas)
        if n == 0:
            self.rotulo_previsao.configure(
                text=(
                    "Esta propriedade não tem unidades ativas — "
                    "não há por quem dividir."
                )
            )
            return

        # Lê o valor total escrito. Se ainda não for válido, mostra
        # só a contagem de unidades.
        try:
            valor_total = _parse_decimal(
                self.campo_valor.get(),
                "Valor",
            )
        except ValueError:
            valor_total = None

        if valor_total is None or valor_total <= 0:
            self.rotulo_previsao.configure(
                text=(
                    f"{n} unidade(s) ativa(s). "
                    f"Introduz o valor total para ver a divisão."
                )
            )
            return

        por_unidade = (valor_total / n).quantize(Decimal("0.01"))
        self.rotulo_previsao.configure(
            text=(
                f"{n} unidade(s) ativa(s). "
                f"Vai criar {n} despesas de "
                f"{componentes.formatar_valor(por_unidade)} cada."
            )
        )

    # -- leitura -----------------------------------------------------

    def _id_categoria(self):
        nome = self.combo_categoria.get()
        for c in self._categorias:
            if c["nome"] == nome:
                return c["id"]
        return None

    def _id_fornecedor(self):
        nome = self.combo_fornecedor.get()
        if nome == "— Nenhum —":
            return None
        for f in self._fornecedores:
            if f["nome"] == nome:
                return f["id"]
        return None

    def _id_propriedade(self):
        return self._propriedade_por_rotulo.get(self.combo_propriedade.get())

    # -- guardar ------------------------------------------------------

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            categoria_id = self._id_categoria()
            if categoria_id is None:
                raise ValueError("Escolhe uma categoria.")

            descricao = self.campo_descricao.get().strip()
            if not descricao:
                raise ValueError("A descrição é obrigatória.")

            valor_total = _parse_decimal(
                self.campo_valor.get(),
                "Valor total",
            )
            if valor_total <= 0:
                raise ValueError("O valor a dividir tem de ser positivo.")

            data_lancamento = _parse_data(
                self.campo_data_lancamento.get(), "Data de lançamento"
            )
            if data_lancamento is None:
                raise ValueError("A data de lançamento é obrigatória.")

            data_vencimento = _parse_data(
                self.campo_data_vencimento.get(),
                "Data de vencimento",
            )

            propriedade_id = self._id_propriedade()
            if propriedade_id is None:
                raise ValueError("Escolhe uma propriedade.")
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        comprovativo = self.campo_comprovativo.get().strip()

        try:
            criadas = despesas.dividir_despesa_por_propriedade(
                propriedade_id=propriedade_id,
                valor_total=valor_total,
                categoria_id=categoria_id,
                data_lancamento=data_lancamento,
                responsavel_id=autor["id"],
                autor=autor,
                fornecedor_id=self._id_fornecedor(),
                data_vencimento=data_vencimento,
                descricao=descricao,
                comprovativo_caminho=comprovativo,
                recorrente=self.check_recorrente.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"{len(criadas)} despesas criadas com sucesso."
        )
        self.destroy()
        self.tela_lista._recarregar()
