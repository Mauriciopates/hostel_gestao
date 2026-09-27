"""Relatórios da área Stock: movimentos, stock atual, requisições e
devoluções (com os filtros próprios destes relatórios)."""

from datetime import date

import customtkinter as ctk

import estoque
import responsaveis

from .. import componentes
from .. import sessao
from .. import tema
from . import gui_relat_comum
from .gui_relat_base import RelatorioBase

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_relat_comum).
_autor_atual = gui_relat_comum.autor_atual
_formatar_data = gui_relat_comum.formatar_data
_mapa_por_id = gui_relat_comum.mapa_por_id
_celula_entidade = gui_relat_comum.celula_entidade


class RelatStock(RelatorioBase):
    """Relatórios da área Stock: movimentos, stock atual, requisições e
    devoluções (com os filtros próprios destes relatórios).

    Só desenhadores `_desenhar_<id>` e os seus auxiliares. A base
    chama-os por `getattr` em `_recarregar_conteudo`; a classe
    final `RelatorioModal` (gui_relat_hub.py) junta as três áreas.
    """

    # RELATÓRIOS — ÁREA STOCK
    # =================================================================

    def _desenhar_filtros_proprios(self, master, relatorio_id, filtros):
        """Desenha os filtros próprios de um relatório.

        Cada filtro é um par (chave, rótulo, opções). Desenha um
        CTkOptionMenu por filtro, com o valor atual escolhido. A
        escolha é guardada em `self.filtros_por_relatorio` e
        despoleta `_recarregar_conteudo`.

        Para os filtros de "produto" e "responsável", as opções
        são construídas em runtime (a lista do Bloco 1 está vazia
        para esses). Aqui preenche-se com os dados atuais.
        """
        if not filtros:
            return

        barra = ctk.CTkFrame(master, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 10))

        for chave, rotulo, opcoes in filtros:
            # Resolve opções dinâmicas
            opcoes_resolvidas = self._resolver_opcoes_filtro(chave, opcoes)

            ctk.CTkLabel(
                barra,
                text=f"{rotulo}:",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
            ).pack(side="left", padx=(0, 4))

            # Valor atual do filtro (ou primeiro da lista)
            filtros_rel = self.filtros_por_relatorio.setdefault(
                relatorio_id, {}
            )
            valor_atual = filtros_rel.get(chave, opcoes_resolvidas[0])

            combo = componentes.Seletor(
                barra,
                values=opcoes_resolvidas,
                width=170,
                height=26,
                corner_radius=tema.RAIO_CAMPO,
                fg_color=tema.COR_FUNDO,
                button_color=tema.COR_FUNDO,
                button_hover_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=11),
                command=lambda v, c=chave: self._aplicar_filtro(
                    relatorio_id, c, v
                ),
            )
            combo.set(valor_atual)
            combo.pack(side="left", padx=(0, 14))

    def _resolver_opcoes_filtro(self, chave, opcoes):
        """Preenche as opções dinâmicas dos filtros.

        Os filtros de "produto" e "responsável" vêm com tuplo vazio
        no mapa `RELATORIOS` (Bloco 1). Aqui são preenchidos com os
        dados reais:
          - "produto" → "Todos" + "PRD-001 · Lixívia" + ...
          - "responsavel" → "Todos" + "STF-002 · Ana Ribeiro" + ...
        """
        if opcoes:
            return list(opcoes)

        if chave == "produto":
            produtos = estoque.listar_produtos(incluir_inativos=True)
            return ["Todos"] + [f"{p['id']} · {p['nome']}" for p in produtos]

        if chave == "responsavel":
            lista = responsaveis.listar(incluir_inativos=True)
            return ["Todos"] + [f"{r['id']} · {r['nome']}" for r in lista]

        return ["Todos"]

    def _aplicar_filtro(self, relatorio_id, chave, valor):
        """Guarda a escolha do filtro e redesenha o conteúdo."""
        self.filtros_por_relatorio.setdefault(relatorio_id, {})[chave] = valor
        self._recarregar_conteudo()

    def _ler_filtro(self, relatorio_id, chave, default="Todos"):
        """Devolve o valor atual de um filtro, ou o default."""
        return self.filtros_por_relatorio.get(relatorio_id, {}).get(
            chave, default
        )

    def _extrair_id_do_rotulo(self, rotulo):
        """Os rótulos dos filtros são "PRD-001 · Lixívia" ou
        "STF-002 · Ana Ribeiro". Este helper extrai só o ID
        ("PRD-001"), ou devolve None se for "Todos".

        A divisão pelo "·" é a mesma convenção dos rótulos em
        toda a aplicação (gui_est_comum, gui_est_requisicoes, etc.).
        """
        if rotulo == "Todos" or rotulo == "Todas":
            return None
        if " · " in rotulo:
            return rotulo.split(" · ")[0]
        return rotulo

    # -- 10. MOVIMENTOS -----------------------------------------------

    def _desenhar_movimentos(self, master):
        """Relatório "Movimentos" — listagem de registos. Sem total.

        Filtros próprios: tipo, produto. Filtro de período é a barra
        comum.
        """
        rel = "movimentos"

        self._titulo_relatorio(master, "Movimentos")

        # Filtros próprios
        self._desenhar_filtros_proprios(
            master,
            rel,
            [
                ("tipo", "Tipo", ("Todos", "entrada", "saida", "ajuste")),
                ("produto", "Produto", ()),
            ],
        )

        # Lê os filtros
        filtro_tipo = self._ler_filtro(rel, "tipo", "Todos")
        filtro_produto = self._ler_filtro(rel, "produto", "Todos")
        produto_id = self._extrair_id_do_rotulo(filtro_produto)

        # Chama o estoque com os filtros que ele aceita
        movimentos = estoque.listar_movimentos(
            produto_id=produto_id,
            tipo=None if filtro_tipo == "Todos" else filtro_tipo,
        )

        # Filtro de período em Python (o estoque ordena por data
        # desc, mas não filtra por período — é o relatorio que o faz)
        movimentos = [
            m
            for m in movimentos
            if m["data"] is not None
            and self.data_inicio <= m["data"] < self.data_fim
        ]

        # Mapas de produtos e responsáveis
        mapa_produtos = _mapa_por_id(
            estoque.listar_produtos(incluir_inativos=True)
        )
        mapa_responsaveis = _mapa_por_id(
            responsaveis.listar(incluir_inativos=True)
        )

        colunas = (
            componentes.Coluna("ID", minimo=100, espaco=6),
            componentes.Coluna("Produto", peso=3, minimo=200),
            componentes.Coluna("Tipo", minimo=100, alinhamento="centro"),
            componentes.Coluna("Quantidade", minimo=100, alinhamento="e"),
            componentes.Coluna("Data", minimo=100, alinhamento="centro"),
            componentes.Coluna("Responsável", peso=2, minimo=150),
            componentes.Coluna("Requisição", minimo=110, alinhamento="centro"),
            componentes.Coluna("Motivo", peso=2, minimo=150, espaco=8),
        )

        tabela = componentes.Tabela(
            master,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem movimentos no período com estes filtros.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not movimentos:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "movimentos",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []
        for mov in movimentos:
            produto = mapa_produtos.get(mov["produto_id"])
            nome_produto = produto["nome"] if produto else mov["produto_id"]

            # Quantidade efetiva — entrada/saída são positivas na
            # BD; o sinal vem do tipo. Ajuste pode ser negativa.
            tipo = mov["tipo"]
            qtd = mov["quantidade"]
            if tipo == "saida":
                qtd_efetiva = -qtd
            else:
                qtd_efetiva = qtd

            texto_qtd = (
                f"+{qtd_efetiva}" if qtd_efetiva >= 0 else str(qtd_efetiva)
            )
            cor_qtd = tema.TEXTO_LIVRE if qtd_efetiva >= 0 else tema.TEXTO_ERRO

            # Chip do tipo
            cor_tipo = {
                "entrada": ("#E1F5EA", "#2E8B57"),
                "saida": ("#FBE4E1", "#C0392B"),
                "ajuste": ("#FFF3D6", "#9A7B12"),
            }.get(tipo, ("#E4E6E8", "#6B7280"))

            nome_resp = (
                mapa_responsaveis.get(mov["responsavel_id"], {}).get(
                    "nome", ""
                )
                if mov["responsavel_id"]
                else "—"
            )

            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=mov["id"],
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=tema.ID_CHIP_FUNDO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(nome_produto, mov["produto_id"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=tipo,
                    text_color=cor_tipo[1],
                    fg_color=cor_tipo[0],
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=texto_qtd,
                    text_color=cor_qtd,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(mov["data"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                5,
                ctk.CTkLabel(
                    linha,
                    text=nome_resp,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                ),
            )
            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=mov["requisicao_id"] or "—",
                    text_color=(
                        tema.AZUL_PRINCIPAL
                        if mov["requisicao_id"]
                        else tema.COR_TEXTO_SECUNDARIO
                    ),
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text=mov["motivo"] or "",
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=10),
                    anchor="w",
                    justify="left",
                ),
            )

            linhas_export.append(
                [
                    mov["id"],
                    f"{nome_produto} ({mov['produto_id']})",
                    tipo,
                    qtd_efetiva,
                    mov["data"],
                    nome_resp,
                    mov["requisicao_id"] or "",
                    mov["motivo"] or "",
                ]
            )

        self._rodape_export(
            master,
            "movimentos",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )

    # -- 11. STOCK ATUAL ----------------------------------------------

    def _desenhar_stock_atual(self, master):
        """Relatório "Stock atual" — fotografia do presente. SEM
        período (a barra de período é escondida pelo
        `_recarregar_conteudo` porque `periodo=False` no mapa).
        """
        produtos = estoque.listar_produtos(incluir_inativos=False)

        self._titulo_relatorio(master, "Stock atual")

        colunas = (
            componentes.Coluna("Produto", peso=3, minimo=240),
            componentes.Coluna("Unidade", minimo=90, alinhamento="centro"),
            componentes.Coluna("Stock mínimo", minimo=110, alinhamento="e"),
            componentes.Coluna("Saldo atual", minimo=110, alinhamento="e"),
            componentes.Coluna(
                "Estado", minimo=150, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem produtos ativos no catálogo.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not produtos:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "stock_atual",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []
        for produto in produtos:
            try:
                saldo = estoque.saldo_produto(produto["id"])
                abaixo = estoque.abaixo_do_minimo(produto["id"])
            except ValueError:
                saldo = 0
                abaixo = False

            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=_celula_entidade(produto["nome"], produto["id"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=produto["unidade_medida"],
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=str(produto["stock_minimo"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=str(saldo),
                    text_color=(tema.TEXTO_ERRO if abaixo else tema.COR_TEXTO),
                    font=ctk.CTkFont(
                        size=11, weight="bold" if abaixo else "normal"
                    ),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text="abaixo do mínimo" if abaixo else "ok",
                    text_color=(
                        tema.TEXTO_ERRO if abaixo else tema.TEXTO_LIVRE
                    ),
                    fg_color=(
                        tema.VERMELHO_ERRO if abaixo else tema.VERDE_LIVRE
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            linhas_export.append(
                [
                    f"{produto['nome']} ({produto['id']})",
                    produto["unidade_medida"],
                    produto["stock_minimo"],
                    saldo,
                    "abaixo do mínimo" if abaixo else "ok",
                ]
            )

        # Nota explicativa — sem total, sem período.
        ctk.CTkLabel(
            master,
            text=(
                "Fotografia do presente — o período não se aplica. "
                "Sem total (unidades de medida não se somam entre "
                "produtos)."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=780,
        ).pack(fill="x", pady=(10, 0))

        self._rodape_export(
            master,
            "stock_atual",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )

    # -- 12. REQUISIÇÕES ----------------------------------------------

    def _desenhar_requisicoes(self, master):
        """Relatório "Requisições" — listagem de registos. Sem total.

        Filtros próprios: estado, origem, responsável.
        """
        rel = "requisicoes"

        self._titulo_relatorio(master, "Requisições")

        self._desenhar_filtros_proprios(
            master,
            rel,
            [
                (
                    "estado",
                    "Estado",
                    (
                        "Todos",
                        "pendente",
                        "enviada",
                        "fechada",
                        "rejeitada",
                        "cancelada",
                    ),
                ),
                ("origem", "Origem", ("Todas", "pedido", "rol")),
                ("responsavel", "Responsável", ()),
            ],
        )

        filtro_estado = self._ler_filtro(rel, "estado", "Todos")
        filtro_origem = self._ler_filtro(rel, "origem", "Todas")
        filtro_resp = self._ler_filtro(rel, "responsavel", "Todos")

        # `estoque.listar_requisicoes` filtra por estado e
        # responsável; origem tem de ser filtrada em Python.
        requisicoes = estoque.listar_requisicoes(
            estado=None if filtro_estado == "Todos" else filtro_estado,
            responsavel_id=self._extrair_id_do_rotulo(filtro_resp),
        )

        if filtro_origem != "Todas":
            requisicoes = [
                r for r in requisicoes if r["origem"] == filtro_origem
            ]

        # Filtro de período em Python
        requisicoes = [
            r
            for r in requisicoes
            if r["data_pedido"] is not None
            and self.data_inicio <= r["data_pedido"] < self.data_fim
        ]

        requisicoes.sort(
            key=lambda r: r["data_pedido"] or date.min,
            reverse=True,
        )

        mapa_responsaveis = _mapa_por_id(
            responsaveis.listar(incluir_inativos=True)
        )

        colunas = (
            componentes.Coluna("ID", minimo=95, espaco=6),
            componentes.Coluna("Responsável", peso=2, minimo=140),
            componentes.Coluna("Origem", minimo=90, alinhamento="centro"),
            componentes.Coluna("Estado", minimo=100, alinhamento="centro"),
            componentes.Coluna("Pedido em", minimo=95, alinhamento="centro"),
            componentes.Coluna("Envio em", minimo=95, alinhamento="centro"),
            componentes.Coluna("Fecho em", minimo=95, alinhamento="centro"),
            componentes.Coluna("Nº itens", minimo=75, alinhamento="e"),
            componentes.Coluna("Observações", peso=2, minimo=160, espaco=8),
        )

        tabela = componentes.Tabela(
            master,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem requisições no período com estes filtros.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not requisicoes:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "requisicoes",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []
        for req in requisicoes:
            # Conta itens (uma query por req — registado como
            # aceitável para o volume)
            itens = estoque.listar_itens_requisicao(requisicao_id=req["id"])

            nome_resp = mapa_responsaveis.get(req["responsavel_id"], {}).get(
                "nome", req["responsavel_id"]
            )

            # Estado e origem como chips
            cor_estado = {
                "pendente": ("#FFF3D6", "#9A7B12"),
                "enviada": ("#EAF3F8", "#0E6291"),
                "fechada": ("#E1F5EA", "#2E8B57"),
                "rejeitada": ("#FBE4E1", "#C0392B"),
                "cancelada": ("#E4E6E8", "#6B7280"),
            }.get(req["estado"], ("#E4E6E8", "#6B7280"))

            cor_origem = (
                ("#EAF3F8", "#0E6291")
                if req["origem"] == "rol"
                else ("#E4E6E8", "#6B7280")
            )

            # Observações: se rejeitada, mostra o motivo.
            texto_obs = req["observacoes"] or "—"
            cor_obs = tema.COR_TEXTO_SECUNDARIO
            if req["estado"] == "rejeitada" and req["motivo_rejeicao"]:
                texto_obs = f"motivo: {req['motivo_rejeicao']}"
                cor_obs = tema.TEXTO_ERRO

            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=req["id"],
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=tema.ID_CHIP_FUNDO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=nome_resp,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                ),
            )
            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=req["origem"],
                    text_color=cor_origem[1],
                    fg_color=cor_origem[0],
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=req["estado"],
                    text_color=cor_estado[1],
                    fg_color=cor_estado[0],
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(req["data_pedido"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=10),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                5,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(req["data_envio"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=10),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(req["data_fecho"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=10),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text=str(len(itens)),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                8,
                ctk.CTkLabel(
                    linha,
                    text=texto_obs,
                    text_color=cor_obs,
                    font=ctk.CTkFont(size=10),
                    anchor="w",
                    justify="left",
                ),
            )

            linhas_export.append(
                [
                    req["id"],
                    nome_resp,
                    req["origem"],
                    req["estado"],
                    req["data_pedido"],
                    req["data_envio"],
                    req["data_fecho"],
                    len(itens),
                    texto_obs,
                ]
            )

        self._rodape_export(
            master,
            "requisicoes",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )

    # -- 13. DEVOLUÇÕES -----------------------------------------------

    def _desenhar_devolucoes(self, master):
        """Relatório "Devoluções" — listagem de registos. Sem total.

        Filtros próprios: estado, responsável.

        ATENÇÃO: o `estoque.listar_devolucoes` tem visibilidade por
        perfil (Staff vê só as dele e só as pendentes). O relatório
        respeita isso — passa `tipo_utilizador_autor` e `autor_id`
        exatamente como o `gui_est_devolucoes.py` faz.
        """
        rel = "devolucoes"

        self._titulo_relatorio(master, "Devoluções")

        self._desenhar_filtros_proprios(
            master,
            rel,
            [
                ("estado", "Estado", ("Todos", "pendente", "fechada")),
                ("responsavel", "Responsável", ()),
            ],
        )

        filtro_estado = self._ler_filtro(rel, "estado", "Todos")
        filtro_resp = self._ler_filtro(rel, "responsavel", "Todos")

        ativo = _autor_atual()
        tipo_utilizador = sessao.tipo_utilizador_ativo()

        devolucoes = estoque.listar_devolucoes(
            estado=None if filtro_estado == "Todos" else filtro_estado,
            responsavel_id=self._extrair_id_do_rotulo(filtro_resp),
            tipo_utilizador_autor=tipo_utilizador,
            autor_id=ativo["id"] if ativo else None,
        )

        # Filtro de período em Python
        devolucoes = [
            d
            for d in devolucoes
            if d["data_reportada"] is not None
            and self.data_inicio <= d["data_reportada"] < self.data_fim
        ]

        devolucoes.sort(
            key=lambda d: d["data_reportada"] or date.min,
            reverse=True,
        )

        mapa_responsaveis = _mapa_por_id(
            responsaveis.listar(incluir_inativos=True)
        )

        colunas = (
            componentes.Coluna("ID", minimo=95, espaco=6),
            componentes.Coluna("Requisição", minimo=110, alinhamento="centro"),
            componentes.Coluna("Responsável", peso=2, minimo=160),
            componentes.Coluna("Estado", minimo=100, alinhamento="centro"),
            componentes.Coluna(
                "Reportada em", minimo=115, alinhamento="centro"
            ),
            componentes.Coluna("Fecho em", minimo=100, alinhamento="centro"),
            componentes.Coluna(
                "Nº itens", minimo=80, alinhamento="e", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            colunas=colunas,
            altura_linha=44,
            mensagem_vazia="Sem devoluções no período com estes filtros.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not devolucoes:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "devolucoes",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []
        for dev in devolucoes:
            itens = estoque.listar_itens_devolucao(devolucao_id=dev["id"])

            nome_resp = mapa_responsaveis.get(dev["responsavel_id"], {}).get(
                "nome", dev["responsavel_id"]
            )

            cor_estado = (
                ("#E1F5EA", "#2E8B57")
                if dev["estado"] == "fechada"
                else ("#FFF3D6", "#9A7B12")
            )

            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=dev["id"],
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=tema.ID_CHIP_FUNDO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ),
            )
            tabela.colocar(
                linha,
                1,
                ctk.CTkLabel(
                    linha,
                    text=dev["requisicao_id"],
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=tema.ID_CHIP_FUNDO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                2,
                ctk.CTkLabel(
                    linha,
                    text=nome_resp,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                ),
            )
            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=dev["estado"],
                    text_color=cor_estado[1],
                    fg_color=cor_estado[0],
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(dev["data_reportada"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=10),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                5,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(dev["data_fecho"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=10),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=str(len(itens)),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    anchor="e",
                ),
            )

            linhas_export.append(
                [
                    dev["id"],
                    dev["requisicao_id"],
                    nome_resp,
                    dev["estado"],
                    dev["data_reportada"],
                    dev["data_fecho"],
                    len(itens),
                ]
            )

        self._rodape_export(
            master,
            "devolucoes",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )
