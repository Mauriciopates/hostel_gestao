"""Relatórios da área Financeiro: resultado, receita por unidade e
por propriedade, rentabilidade, despesas por categoria e COGS por
produto."""

from decimal import Decimal

import customtkinter as ctk

import estoque
import financeiro
import unidades

from .. import componentes
from .. import sessao
from .. import tema
from ..despesas import gui_desp_atribuir
from . import gui_relat_comum
from .gui_relat_base import RelatorioBase

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_relat_comum).
_formatar_valor = gui_relat_comum.formatar_valor
_mapa_por_id = gui_relat_comum.mapa_por_id
_celula_entidade = gui_relat_comum.celula_entidade
_cor_valor = gui_relat_comum.cor_valor
_simetrico = gui_relat_comum.simetrico


class RelatFinanceiro(RelatorioBase):
    """Relatórios da área Financeiro: resultado, receita por unidade e
    por propriedade, despesas por categoria e COGS por produto.

    Só desenhadores `_desenhar_<id>` e os seus auxiliares. A base
    chama-os por `getattr` em `_recarregar_conteudo`; a classe
    final `RelatorioModal` (gui_relat_hub.py) junta as três áreas.
    """

    # -- 1. RESULTADO -------------------------------------------------

    def _desenhar_resultado(self, master):
        """Relatório "Resultado": 4 KPIs + tabela + COGS à parte.

        Os cartões leem-se como uma conta que fecha (v1.11.1):
        Receita de tabela − Descontos − Despesas = Resultado. A
        receita recebida já vem líquida de desconto; o resultado é
        recebida − despesas (até à 1.11.0 o desconto era tirado duas
        vezes). O COGS fica numa linha separada, com nota — não é
        dinheiro.

        Descontos e despesas entram na tabela e na exportação com
        sinal negativo (são o que se tira), a vermelho.
        """
        dados = financeiro.resultado(self.data_inicio, self.data_fim)

        self._titulo_relatorio(master, "Resultado")

        # ---- 4 KPIs -------------------------------------------------
        kpis = ctk.CTkFrame(master, fg_color="transparent")
        kpis.pack(fill="x", pady=(0, 14))
        for coluna in range(4):
            kpis.grid_columnconfigure(coluna, weight=1, uniform="kpi")

        receita = dados["receita"]
        receita_tabela = dados["receita_tabela"]
        # Descontos e despesas com sinal: são o que se tira.
        descontos = _simetrico(dados["descontos"])
        despesas_op = _simetrico(dados["despesas_operacionais"])
        resultado_liquido = dados["resultado_liquido"]

        # Cor do resultado: verde se positivo, vermelho se negativo.
        cor_resultado = (
            tema.TEXTO_LIVRE if resultado_liquido >= 0 else tema.TEXTO_ERRO
        )

        cartoes = (
            (
                "Receita de tabela",
                _formatar_valor(receita_tabela),
                _cor_valor(receita_tabela),
            ),
            ("Descontos", _formatar_valor(descontos), _cor_valor(descontos)),
            (
                "Despesas",
                _formatar_valor(despesas_op),
                _cor_valor(despesas_op),
            ),
            ("Resultado", _formatar_valor(resultado_liquido), cor_resultado),
        )

        for indice, (rotulo, valor, cor) in enumerate(cartoes):
            self._kpi(kpis, indice, rotulo, valor, cor)

        # ---- Tabela -------------------------------------------------
        colunas = (
            componentes.Coluna("Eixo", peso=3, minimo=220),
            componentes.Coluna("Valor", peso=1, minimo=140, alinhamento="e"),
        )

        por_tipo = financeiro.receita_por_tipo(
            self.data_inicio, self.data_fim
        )
        linhas = (
            ("Receita de tabela", receita_tabela),
            ("Descontos", descontos),
            ("Receita recebida", receita),
            ("Receita recebida (mensal)", por_tipo["mensal"]),
            ("Receita recebida (Airbnb)", por_tipo["airbnb"]),
            ("Despesas operacionais", despesas_op),
            ("Resultado líquido", resultado_liquido),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=38,
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        for rotulo, valor in linhas:
            linha = tabela.nova_linha()
            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=rotulo,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(
                        size=12,
                        weight=(
                            "bold"
                            if rotulo == "Resultado líquido"
                            else "normal"
                        ),
                    ),
                    anchor="w",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(valor),
                    text_color=(
                        cor_resultado
                        if rotulo == "Resultado líquido"
                        else _cor_valor(valor)
                    ),
                    font=ctk.CTkFont(
                        size=12,
                        weight=(
                            "bold"
                            if rotulo == "Resultado líquido"
                            else "normal"
                        ),
                    ),
                    anchor="e",
                ),
            )

        # ---- COGS à parte ------------------------------------------
        # O COGS é quantidade, não dinheiro — fica fora da tabela
        # dos euros, com uma nota a explicar porquê.
        aviso_cogs = ctk.CTkFrame(
            master,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=tema.RAIO_CAMPO,
        )
        aviso_cogs.pack(fill="x", pady=(14, 0))

        ctk.CTkLabel(
            aviso_cogs,
            text=(
                f"COGS (quantidade consumida): "
                f"{dados['cogs_quantidade']} un"
            ),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(8, 2))

        ctk.CTkLabel(
            aviso_cogs,
            text=(
                "Quantidade de stock consumido no período — não "
                "entra no Resultado líquido (a tabela de produtos "
                "não tem preço unitário)."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=780,
        ).pack(fill="x", padx=14, pady=(0, 8))

        # ---- Exportação --------------------------------------------
        self._rodape_export(
            master,
            "resultado",
            colunas=("Eixo", "Valor"),
            linhas=[[rotulo, valor] for rotulo, valor in linhas],
        )

    def _kpi(self, master, coluna, rotulo, valor, cor):
        """Desenha um cartão de KPI. Mesmo formato do
        `gui_dashboard.py`: borda tracejada, rótulo pequeno em cima,
        valor grande em baixo.
        """
        cartao = ctk.CTkFrame(
            master,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.grid(row=0, column=coluna, sticky="nsew", padx=4)

        ctk.CTkLabel(
            cartao,
            text=rotulo.upper(),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=9),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            cartao,
            text=valor,
            text_color=cor,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 10))

    # -- 2. RECEITA POR UNIDADE ---------------------------------------

    def _desenhar_receita_unidade(self, master):
        """Relatório "Receita por unidade" — só tabela, sem total.

        A coluna "Unidade" mostra o nome em cima e o ID por baixo
        (regra fechada em 19/09/2026).
        """
        linhas = financeiro.receita_por_unidade(
            self.data_inicio, self.data_fim
        )

        # Mapa de unidades — uma leitura só, em memória.
        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))

        self._titulo_relatorio(master, "Receita por unidade")

        colunas = (
            componentes.Coluna("Unidade", peso=3, minimo=260),
            componentes.Coluna("Receita", peso=1, minimo=120, alinhamento="e"),
            componentes.Coluna(
                "Desconto", peso=1, minimo=120, alinhamento="e"
            ),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem receita de unidades no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not linhas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "receita_unidade",
                colunas=("Unidade", "Receita", "Desconto"),
                linhas=[],
            )
            return

        linhas_export = []
        for item in linhas:
            unidade = mapa_unidades.get(item["unidade_id"])
            nome = unidade["nome"] if unidade else item["unidade_id"]

            linha = tabela.nova_linha()
            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(nome, item["unidade_id"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(item["receita"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(_simetrico(item["desconto"])),
                    text_color=_cor_valor(_simetrico(item["desconto"])),
                    font=ctk.CTkFont(size=12),
                    anchor="e",
                ),
            )

            linhas_export.append(
                [
                    f"{nome} ({item['unidade_id']})",
                    item["receita"],
                    _simetrico(item["desconto"]),
                ]
            )

        self._rodape_export(
            master,
            "receita_unidade",
            colunas=("Unidade", "Receita", "Desconto"),
            linhas=linhas_export,
        )

    # -- 3. RECEITA POR PROPRIEDADE -----------------------------------

    def _desenhar_receita_propriedade(self, master):
        """Relatório "Receita por propriedade" — com linha de total.

        O nome da propriedade já vem do `financeiro.py` — não é
        preciso mapa nenhum.
        """
        linhas = financeiro.receita_por_propriedade(
            self.data_inicio, self.data_fim
        )

        self._titulo_relatorio(master, "Receita por propriedade")

        colunas = (
            componentes.Coluna("Propriedade", peso=3, minimo=260),
            componentes.Coluna("Receita", peso=1, minimo=120, alinhamento="e"),
            componentes.Coluna(
                "Desconto", peso=1, minimo=120, alinhamento="e"
            ),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem receita de propriedades no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not linhas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "receita_propriedade",
                colunas=("Propriedade", "Receita", "Desconto"),
                linhas=[],
            )
            return

        total_receita = Decimal("0.00")
        total_desconto = Decimal("0.00")
        linhas_export = []

        for item in linhas:
            total_receita += item["receita"]
            total_desconto += item["desconto"]

            linha = tabela.nova_linha()
            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(
                        item["propriedade_nome"],
                        item["propriedade_id"],
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(item["receita"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(_simetrico(item["desconto"])),
                    text_color=_cor_valor(_simetrico(item["desconto"])),
                    font=ctk.CTkFont(size=12),
                    anchor="e",
                ),
            )

            linhas_export.append(
                [
                    f"{item['propriedade_nome']} ({item['propriedade_id']})",
                    item["receita"],
                    _simetrico(item["desconto"]),
                ]
            )

        # Linha de total — fundo destacado, negrito, borda azul.
        linha_total = tabela.nova_linha(fixa=True)
        tabela.colocar(
            linha_total,
            0,
            ctk.CTkLabel(
                linha_total,
                text=f"TOTAL ({len(linhas)} propriedades)",
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ),
        )
        tabela.colocar(
            linha_total,
            1,
            ctk.CTkLabel(
                linha_total,
                text=_formatar_valor(total_receita),
                text_color=tema.AZUL_PRINCIPAL,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="e",
            ),
        )
        tabela.colocar(
            linha_total,
            2,
            ctk.CTkLabel(
                linha_total,
                text=_formatar_valor(_simetrico(total_desconto)),
                text_color=_cor_valor(
                    _simetrico(total_desconto), tema.AZUL_PRINCIPAL
                ),
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="e",
            ),
        )

        linhas_export.append(
            [
                f"TOTAL ({len(linhas)} propriedades)",
                total_receita,
                _simetrico(total_desconto),
            ]
        )

        self._rodape_export(
            master,
            "receita_propriedade",
            colunas=("Propriedade", "Receita", "Desconto"),
            linhas=linhas_export,
        )

    # -- 3b. RENTABILIDADE (v1.12.0) ----------------------------------

    _VISTAS_RENTABILIDADE = ("Por propriedade", "Por unidade")

    def _vista_rentabilidade(self):
        """A vista escolhida ("Por propriedade" / "Por unidade").
        Guardada em `filtros_por_relatorio`, como os filtros dos
        outros relatórios — mantém-se enquanto o popup estiver
        aberto."""
        return self.filtros_por_relatorio.get("rentabilidade", {}).get(
            "vista", self._VISTAS_RENTABILIDADE[0]
        )

    def _mudar_vista_rentabilidade(self, vista):
        self.filtros_por_relatorio.setdefault("rentabilidade", {})[
            "vista"
        ] = vista
        self._recarregar_conteudo()

    def _botao_atribuir_gerais(self, master):
        """"Ver e atribuir (N)" na linha das despesas gerais: abre a
        lista para dar unidade a cada uma (só Master/Admin). Ao
        aplicar, o relatório recarrega."""
        if sessao.tipo_utilizador_ativo() not in ("Master", "Admin"):
            return componentes.Rotulo(master, "")

        quantas = len(
            financeiro.despesas_gerais(self.data_inicio, self.data_fim)
        )
        if not quantas:
            return componentes.Rotulo(master, "")

        return componentes.Botao(
            master,
            f"Ver e atribuir ({quantas})",
            lambda: gui_desp_atribuir.DespesasGeraisModal(
                self,
                self.data_inicio,
                self.data_fim,
                self._recarregar_conteudo,
            ),
            "primario",
            width=122,
            height=26,
        )

    @staticmethod
    def _montar_linhas_rentabilidade(dados, por_unidade):
        """Transforma o resultado de `financeiro.rentabilidade` na
        lista de linhas do relatório — a MESMA lista desenha o ecrã e
        alimenta a exportação (PDF, CSV e Excel), por isso os três
        mostram sempre o mesmo.

        Cada linha é um dicionário:

            tipo      — "propriedade" · "unidade" · "gerais" · "stock"
                        · "total"
            ecra      — texto da primeira coluna no ecrã
            exportar  — texto da primeira coluna nos ficheiros
            valores   — (receita de tabela, descontos, despesas,
                        resultado); descontos e despesas com sinal
                        negativo (são o que se tira)
            rentavel  — True / False, ou None (despesas gerais)
        """
        linhas = []

        def valores(item):
            return (
                item["receita_tabela"],
                _simetrico(item["descontos"]),
                _simetrico(item["despesas"]),
                item["resultado"],
            )

        for propriedade in dados["propriedades"]:
            nome_prop = _celula_entidade(
                propriedade["propriedade_nome"],
                propriedade["propriedade_id"],
            )
            export_prop = (
                f"{propriedade['propriedade_nome']} "
                f"({propriedade['propriedade_id']})"
            )
            linhas.append(
                {
                    "tipo": "propriedade",
                    "ecra": nome_prop,
                    "exportar": export_prop,
                    "valores": valores(propriedade),
                    "rentavel": propriedade["rentavel"],
                }
            )

            if not por_unidade:
                continue

            for unidade in propriedade["unidades"]:
                linhas.append(
                    {
                        "tipo": "unidade",
                        "ecra": "    " + _celula_entidade(
                            unidade["unidade_nome"], unidade["unidade_id"]
                        ).replace("\n", "\n    "),
                        "exportar": (
                            f"{export_prop} / {unidade['unidade_nome']} "
                            f"({unidade['unidade_id']})"
                        ),
                        "valores": valores(unidade),
                        "rentavel": unidade["rentavel"],
                    }
                )

        gerais = dados["gerais"]
        if gerais != 0:
            menos = _simetrico(gerais)
            linhas.append(
                {
                    "tipo": "gerais",
                    "ecra": "Despesas gerais não atribuídas",
                    "exportar": "Despesas gerais não atribuídas",
                    "valores": (
                        Decimal("0.00"),
                        Decimal("0.00"),
                        menos,
                        menos,
                    ),
                    "rentavel": None,
                }
            )

        stock_central = dados.get("stock_central", Decimal("0.00"))
        if stock_central != 0:
            menos = _simetrico(stock_central)
            linhas.append(
                {
                    "tipo": "stock",
                    "ecra": "Stock central (compras de stock)",
                    "exportar": "Stock central (compras de stock)",
                    "valores": (
                        Decimal("0.00"),
                        Decimal("0.00"),
                        menos,
                        menos,
                    ),
                    "rentavel": None,
                }
            )

        total = dados["total"]
        texto_total = f"TOTAL ({len(dados['propriedades'])} propriedades)"
        linhas.append(
            {
                "tipo": "total",
                "ecra": texto_total,
                "exportar": texto_total,
                "valores": valores(total),
                "rentavel": total["rentavel"],
            }
        )

        return linhas

    def _desenhar_rentabilidade(self, master):
        """Relatório "Rentabilidade": por propriedade ou por unidade.

        Receita de tabela − Descontos − Despesas = Resultado, com o
        Estado Rentável (resultado >= 0) / Não rentável. As despesas
        sem unidade aparecem numa linha à parte e só pesam no total.
        Negativos a vermelho (ecrã, PDF e Excel).

        A exportação usa o rodapé comum dos outros relatórios, com
        exatamente as linhas que estão no ecrã.
        """
        dados = financeiro.rentabilidade(self.data_inicio, self.data_fim)
        total = dados["total"]

        self._titulo_relatorio(master, "Rentabilidade")

        # ---- 4 KPIs (iguais aos do Resultado) -----------------------
        kpis = ctk.CTkFrame(master, fg_color="transparent")
        kpis.pack(fill="x", pady=(0, 14))
        for coluna in range(4):
            kpis.grid_columnconfigure(coluna, weight=1, uniform="kpi")

        descontos = _simetrico(total["descontos"])
        despesas_total = _simetrico(total["despesas"])
        cor_resultado = (
            tema.TEXTO_LIVRE if total["resultado"] >= 0 else tema.TEXTO_ERRO
        )
        cartoes = (
            (
                "Receita de tabela",
                _formatar_valor(total["receita_tabela"]),
                _cor_valor(total["receita_tabela"]),
            ),
            ("Descontos", _formatar_valor(descontos), _cor_valor(descontos)),
            (
                "Despesas",
                _formatar_valor(despesas_total),
                _cor_valor(despesas_total),
            ),
            (
                "Resultado",
                _formatar_valor(total["resultado"]),
                cor_resultado,
            ),
        )
        for indice, (rotulo, valor, cor) in enumerate(cartoes):
            self._kpi(kpis, indice, rotulo, valor, cor)

        # ---- Vista ---------------------------------------------------
        vista = self._vista_rentabilidade()
        barra = componentes.Contentor(master)
        barra.pack(fill="x", pady=(0, 10))
        componentes.SeletorVistas(
            barra,
            self._VISTAS_RENTABILIDADE,
            self._mudar_vista_rentabilidade,
            inicial=vista,
        ).pack(side="left")

        # ---- Tabela --------------------------------------------------
        nomes_colunas = (
            "Propriedade / Unidade",
            "Receita tabela",
            "Descontos",
            "Despesas",
            "Resultado",
            "Estado",
        )
        colunas = (
            componentes.Coluna(nomes_colunas[0], peso=3, minimo=180),
            componentes.Coluna(
                nomes_colunas[1], peso=1, minimo=105, alinhamento="e"
            ),
            componentes.Coluna(
                nomes_colunas[2], peso=1, minimo=85, alinhamento="e"
            ),
            componentes.Coluna(
                nomes_colunas[3], peso=1, minimo=85, alinhamento="e"
            ),
            componentes.Coluna(
                nomes_colunas[4], peso=1, minimo=90, alinhamento="e"
            ),
            componentes.Coluna(
                nomes_colunas[5], peso=1, minimo=132, alinhamento="centro"
            ),
        )

        vazio = (
            not dados["propriedades"]
            and dados["gerais"] == 0
            and dados.get("stock_central", 0) == 0
        )
        linhas = (
            []
            if vazio
            else self._montar_linhas_rentabilidade(
                dados, vista == self._VISTAS_RENTABILIDADE[1]
            )
        )

        # O corpo da tabela cresce com as linhas (até 9); a partir daí
        # rola por dentro. Sem isto ficava nos 200 px por omissão e as
        # últimas linhas (gerais, total) escondiam-se.
        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem receita nem despesas no período.",
            tom_alternado=True,
            altura_corpo=44 * min(max(len(linhas), 2), 9) + 4,
        )
        tabela.pack(fill="x")

        if vazio:
            tabela.mostrar_vazio()
            self._rodape_export(
                master, "rentabilidade", colunas=nomes_colunas, linhas=[]
            )
            return

        linhas_export = []

        for item in linhas:
            tipo = item["tipo"]
            e_total = tipo == "total"
            negrito = tipo in ("total", "propriedade") and (
                e_total or vista == self._VISTAS_RENTABILIDADE[1]
            )
            estilo = "forte" if negrito else "texto"
            cor_normal = tema.AZUL_PRINCIPAL if e_total else None

            linha = tabela.nova_linha(fixa=e_total)
            tabela.colocar(
                linha,
                0,
                componentes.Rotulo(
                    linha,
                    item["ecra"],
                    estilo=estilo,
                    cor=(
                        tema.COR_TEXTO_SECUNDARIO
                        if tipo in ("gerais", "stock")
                        else None
                    ),
                    justify="left",
                ),
            )
            for posicao, valor in enumerate(item["valores"], start=1):
                tabela.colocar(
                    linha,
                    posicao,
                    componentes.Rotulo(
                        linha,
                        _formatar_valor(valor),
                        estilo=estilo,
                        cor=_cor_valor(valor, cor_normal),
                        anchor="e",
                    ),
                )

            if item["rentavel"] is None:
                texto_estado = ""
                celula_estado = (
                    self._botao_atribuir_gerais(linha)
                    if tipo == "gerais"
                    else componentes.Rotulo(linha, "")
                )
            elif item["rentavel"]:
                texto_estado = "Rentável"
                celula_estado = componentes.Etiqueta(
                    linha, texto_estado, "livre", largura=96
                )
            else:
                texto_estado = "Não rentável"
                celula_estado = componentes.Etiqueta(
                    linha, texto_estado, "erro", largura=96
                )
            tabela.colocar(linha, 5, celula_estado)

            linhas_export.append(
                [item["exportar"], *item["valores"], texto_estado]
            )

        ctk.CTkLabel(
            master,
            text=(
                "Resultado = Receita de tabela − Descontos − Despesas. "
                "As despesas gerais (sem unidade) e o stock central "
                "(compras de stock, que ficam no armazém) entram só no "
                "total, não em cada unidade."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=780,
        ).pack(fill="x", pady=(10, 0))

        self._rodape_export(
            master,
            "rentabilidade",
            colunas=nomes_colunas,
            linhas=linhas_export,
        )

    # -- 4. DESPESAS POR CATEGORIA ------------------------------------

    def _desenhar_despesas_categoria(self, master):
        """Relatório "Despesas por categoria" — com linha de total.

        Duas colunas: Categoria (ID + nome) e Total.
        """
        linhas = financeiro.despesas_por_categoria(
            self.data_inicio, self.data_fim
        )

        self._titulo_relatorio(master, "Despesas por categoria")

        colunas = (
            componentes.Coluna("Categoria", peso=3, minimo=300),
            componentes.Coluna("Total", peso=1, minimo=160, alinhamento="e"),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem despesas pagas no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not linhas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "despesas_categoria",
                colunas=("Categoria", "Total"),
                linhas=[],
            )
            return

        total = Decimal("0.00")
        linhas_export = []

        for item in linhas:
            total += item["total"]

            linha = tabela.nova_linha()
            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(
                        item["categoria_nome"],
                        item["categoria_id"],
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(item["total"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="e",
                ),
            )

            linhas_export.append(
                [
                    f"{item['categoria_nome']} ({item['categoria_id']})",
                    item["total"],
                ]
            )
        # Linha de total
        linha_total = tabela.nova_linha(fixa=True)
        tabela.colocar(
            linha_total,
            0,
            ctk.CTkLabel(
                linha_total,
                text=f"TOTAL ({len(linhas)} categorias)",
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ),
        )
        tabela.colocar(
            linha_total,
            1,
            ctk.CTkLabel(
                linha_total,
                text=_formatar_valor(total),
                text_color=tema.AZUL_PRINCIPAL,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="e",
            ),
        )

        linhas_export.append([f"TOTAL ({len(linhas)} categorias)", total])

        self._rodape_export(
            master,
            "despesas_categoria",
            colunas=("Categoria", "Total"),
            linhas=linhas_export,
        )

    # -- 5. COGS POR PRODUTO ------------------------------------------

    def _desenhar_cogs_produto(self, master):
        """Relatório "COGS por produto" — com coluna de unidade de
        medida, sem total (as unidades não se somam entre produtos
        diferentes).
        """
        linhas = financeiro.cogs_por_produto(self.data_inicio, self.data_fim)

        # Mapa de produtos — para ir buscar a unidade de medida de
        # cada um.
        mapa_produtos = _mapa_por_id(
            estoque.listar_produtos(incluir_inativos=True)
        )

        self._titulo_relatorio(master, "COGS por produto")

        colunas = (
            componentes.Coluna("Produto", peso=3, minimo=260),
            componentes.Coluna(
                "Quantidade", peso=1, minimo=110, alinhamento="e"
            ),
            componentes.Coluna(
                "Unidade", peso=1, minimo=90, alinhamento="centro"
            ),
        )

        tabela = componentes.Tabela(
            master,
            rolagem_horizontal=True,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem consumo de stock no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not linhas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "cogs_produto",
                colunas=("Produto", "Quantidade", "Unidade"),
                linhas=[],
            )
            return

        linhas_export = []
        for item in linhas:
            produto = mapa_produtos.get(item["produto_id"])
            unidade_medida = produto["unidade_medida"] if produto else "—"

            linha = tabela.nova_linha()
            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(
                        item["produto_nome"], item["produto_id"]
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=str(item["quantidade"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=unidade_medida,
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            linhas_export.append(
                [
                    f"{item['produto_nome']} ({item['produto_id']})",
                    item["quantidade"],
                    unidade_medida,
                ]
            )

        # Nota explicativa — sem total, porque unidades não se somam.
        ctk.CTkLabel(
            master,
            text=(
                "Sem linha de total — as unidades de medida não se "
                "somam entre produtos diferentes (12 L + 4 un não "
                "é 16)."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=780,
        ).pack(fill="x", pady=(10, 0))

        self._rodape_export(
            master,
            "cogs_produto",
            colunas=("Produto", "Quantidade", "Unidade"),
            linhas=linhas_export,
        )
