"""Ecrã de Devoluções do módulo Stock.

Extraído do antigo `gui_estoque.py` em 10/09/2026, quando o módulo
Stock passou a ter cinco ficheiros focados. Sem alterações de
comportamento.

Inclui:

- `ListaDevolucoes` — tabela de devoluções, com Gerir por linha
- `_AcoesDevolucaoModal` — popup de ação de uma devolução
- `_ResumoDevolucaoModal` — resumo antes de aceitar, com o ajuste
  de stock das quantidades corrigidas
- `_ResumoRequisicaoModal` — resumo da requisição de origem
"""

import datetime

import customtkinter as ctk

import estoque
import responsaveis
from . import componentes
from . import gui_est_comum
from . import sessao
from . import tema


# Aliases dos helpers partilhados — ver o mesmo bloco em
# gui_est_requisicoes.py para o porquê.
_CORES_ESTADO = gui_est_comum.CORES_ESTADO
_OPCAO_TODOS_ESTADOS = gui_est_comum.OPCAO_TODOS_ESTADOS
_ESTADOS_DEVOLUCAO = gui_est_comum.ESTADOS_DEVOLUCAO
_LARGURA_PRODUTO = gui_est_comum.LARGURA_PRODUTO
_LARGURA_ARMAZEM = gui_est_comum.LARGURA_ARMAZEM
_LARGURA_PEDIDO = gui_est_comum.LARGURA_PEDIDO

_etiqueta_estado = gui_est_comum.etiqueta_estado
_texto_produtos_devolucao = gui_est_comum.texto_produtos_devolucao

_colocar_no_topo = componentes.colocar_no_topo
_centrar_sobre = componentes.centrar_sobre
_tornar_cliclavel = componentes.tornar_cliclavel


# Largura do popup de "Gerir".
_LARGURA_POPUP_ACOES = 320

# Altura extra que o popup de Resumo da devolução precisa quando o
# alerta de ajuste de stock aparece (caixa + campo de motivo) — sem
# isto o rodapé com "Aceitar devolução" fica fora da janela, que não
# é redimensionável (09/09/2026, aluno testou e o botão sumiu).
_ALTURA_ALERTA_AJUSTE = 110


_COLUNAS_DEVOLUCAO = (
    componentes.Coluna("DEVOLUÇÃO", minimo=130, espaco=8),
    componentes.Coluna("RESPONSÁVEL E PRODUTOS", peso=3, minimo=280),
    componentes.Coluna("ESTADO", minimo=110, alinhamento="centro"),
    componentes.Coluna("GERIR", minimo=90, alinhamento="e"),
)


class ListaDevolucoes(ctk.CTkFrame):
    """"Aceitar Sobra (Devolução)": mesma tabela e mesmo padrão de
    Gerir de ListaRequisicoes, agora para o material devolvido por
    sobra (`estoque.reportar_devolucao` / `fechar_devolucao`).

    Sem "+ Nova": a devolução nasce do lado do responsável, ao
    reportar a sobra de uma requisição fechada — este ecrã só aceita
    o que já foi reportado, filtrado por omissão às pendentes.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(
            self, titulo="Stock · Aceitar Sobra (Devolução)"
        ).pack(fill="x")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 6))
        ctk.CTkButton(
            barra,
            text="< Voltar ao Stock",
            width=140,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=lambda: controlador.mostrar_frame(
                __import__(
                    "gui.gui_est_hub", fromlist=["EcraStock"]
                ).EcraStock
            ),
        ).pack(side="left")

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=20, pady=(0, 6))
        self.combo_estado = ctk.CTkOptionMenu(
            filtros,
            values=[_OPCAO_TODOS_ESTADOS] + list(_ESTADOS_DEVOLUCAO),
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_estado.set("pendente")
        self.combo_estado.pack(side="left")

        self.nomes_por_id = {
            r["id"]: r["nome"]
            for r in responsaveis.listar(incluir_inativos=True)
        }

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_DEVOLUCAO,
            altura_linha=52,
            mensagem_vazia="Nenhuma devolução com este filtro.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _estado_filtro(self):
        valor = self.combo_estado.get()

        return None if valor == _OPCAO_TODOS_ESTADOS else valor

    def _recarregar(self):
        self.tabela.limpar()

        produtos = {
            p["id"]: p for p in estoque.listar_produtos(incluir_inativos=True)
        }
        devolucoes = estoque.listar_devolucoes(estado=self._estado_filtro())
        devolucoes.sort(
            key=lambda d: (
                d["data_reportada"] is not None,
                d["data_reportada"] or datetime.date.min,
            ),
            reverse=True,
        )

        if not devolucoes:
            self.tabela.mostrar_vazio()
            return

        for devolucao in devolucoes:
            self._desenhar_linha(devolucao, produtos)

    def _desenhar_linha(self, devolucao, produtos):
        linha = self.tabela.nova_linha()

        coluna_id = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            coluna_id,
            text=devolucao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            coluna_id,
            text=f"de {devolucao['requisicao_id']}",
            text_color=tema.AZUL_PRINCIPAL,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        _tornar_cliclavel(
            coluna_id,
            lambda: _ResumoRequisicaoModal(
                self, devolucao["requisicao_id"]
            ),
        )
        self.tabela.colocar(linha, 0, coluna_id)

        coluna_meio = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            coluna_meio,
            text=self.nomes_por_id.get(
                devolucao["responsavel_id"], devolucao["responsavel_id"]
            ),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            coluna_meio,
            text=_texto_produtos_devolucao(devolucao, produtos),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 1, coluna_meio)

        self.tabela.colocar(
            linha, 2, _etiqueta_estado(linha, devolucao["estado"])
        )

        acoes = self.tabela.celula_acoes(linha, 3)
        acoes.adicionar(
            ctk.CTkButton(
                acoes,
                text="Gerir",
                width=76,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda: _AcoesDevolucaoModal(self, devolucao),
            )
        )

    # -- ações -------------------------------------------------------

    def _aceitar_devolucao(
        self, devolucao, quantidades_aceites=None, motivo_ajuste=""
    ):
        """Confirma e fecha a devolução — chamada pelo botão "Aceitar
        devolução" de `_ResumoDevolucaoModal`, que já É a confirmação
        (mostra produto a produto o que vai entrar no stock); não há
        aqui um segundo "tem a certeza?" genérico por cima disso.

        'quantidades_aceites' e 'motivo_ajuste' vêm desse resumo só
        quando o admin corrigiu alguma quantidade — passam direto
        para `estoque.fechar_devolucao`, que gera o ajuste de stock
        da diferença (09/09/2026, pedido do aluno).
        """
        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            estoque.fechar_devolucao(
                devolucao["id"],
                ativo["id"],
                datetime.date.today(),
                quantidades_aceites=quantidades_aceites,
                motivo_ajuste=motivo_ajuste,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Devolução aceite: {devolucao['id']}")
        self._recarregar()


class _AcoesDevolucaoModal(ctk.CTkToplevel):
    """Popup de "Gerir" de uma devolução — gémeo de
    `_AcoesRequisicaoModal`, mas com uma única ação possível
    ("Aceitar devolução") em vez de duas.
    """

    def __init__(self, tela_lista, devolucao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        altura = 200
        self.title(f"Gerir — {devolucao['id']}")
        self.geometry(f"{_LARGURA_POPUP_ACOES}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, _LARGURA_POPUP_ACOES, altura)
        _colocar_no_topo(self)

        nome = tela_lista.nomes_por_id.get(
            devolucao["responsavel_id"], devolucao["responsavel_id"]
        )
        ctk.CTkLabel(
            self,
            text=devolucao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=f"Devolvido por {nome}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if devolucao["estado"] == "pendente":

            def executar():
                self.destroy()
                _ResumoDevolucaoModal(tela_lista, devolucao)

            ctk.CTkButton(
                self,
                text="Aceitar devolução",
                height=34,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                hover_color=tema.ID_CHIP_FUNDO,
                text_color=tema.AZUL_PRINCIPAL,
                border_width=1,
                border_color=tema.COR_BORDA,
                command=executar,
            ).pack(fill="x", padx=20, pady=3)
        else:
            ctk.CTkLabel(
                self,
                text="Devolução já aceite — sem ações disponíveis.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                wraplength=260,
                justify="center",
            ).pack(padx=20, pady=(0, 10))

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=(10, 16))


class _ResumoDevolucaoModal(ctk.CTkToplevel):
    """Resumo da devolução, mostrado antes de aceitar — substitui o
    "tem a certeza?" genérico de `componentes.confirmar` (09/09/2026,
    pedido do aluno: "com o que vou aceitar e quanto vai entrar no
    meu estoque atual").

    Aberto a partir de "Aceitar devolução" em `_AcoesDevolucaoModal`.
    Mostra, produto a produto, o stock atual, a quantidade a repor e
    o stock resultante — é esta tabela que serve de confirmação e de
    rasto do que aconteceu (o admin vê exatamente o que vai mudar
    antes de mudar). Só depois de "Aceitar devolução" aqui é que
    `ListaDevolucoes._aceitar_devolucao` corre de facto.

    "A repor" vem preenchido com o reportado, mas pode ser corrigido
    para mais ou para menos — reduzido até 0 (ex.: parte voltou
    danificada e não deve voltar ao stock) ou aumentado (ex.: erro
    de digitação ao reportar, voltou mais do que ficou escrito).
    Quando o valor é corrigido, aparece um alerta a avisar que vai
    ser aberto um movimento de ajuste com a diferença, e exige um
    motivo — a entrada em si continua sempre pela quantidade
    reportada, imutável (decisão 9); é o ajuste, positivo ou
    negativo, que corrige o saldo final.
    """

    def __init__(self, tela_lista, devolucao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.devolucao = devolucao
        self.campos_por_produto = {}
        self.rotulos_apos_por_produto = {}
        self.reportado_por_produto = {}
        self.stock_atual_por_produto = {}
        self.nomes_produto_por_id = {}
        self.frame_alerta = None
        self.entry_motivo = None

        itens = estoque.listar_itens_devolucao(
            devolucao_id=devolucao["id"]
        )
        produtos = {
            p["id"]: p for p in estoque.listar_produtos(True)
        }
        nome = tela_lista.nomes_por_id.get(
            devolucao["responsavel_id"], devolucao["responsavel_id"]
        )

        self.largura_janela = 640
        self.altura_base = 300 + 36 * max(len(itens), 1)
        self.title(f"Resumo da devolução — {devolucao['id']}")
        self.geometry(f"{self.largura_janela}x{self.altura_base}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(
            self, tela_lista, self.largura_janela, self.altura_base
        )
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Resumo da devolução — {devolucao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            self,
            text=(
                f"de {devolucao['requisicao_id']} · devolvido por "
                f"{nome}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        self._construir_tabela(itens, produtos)

        self.rotulo_explicacao = ctk.CTkLabel(
            self,
            text=(
                "\"A repor\" vem preenchido com o que foi reportado, "
                "mas pode ser corrigido para mais ou para menos — "
                "reduzido até 0, se parte voltou danificada, ou "
                "aumentado, se voltou mais do que ficou reportado. "
                "Aceitar gera a entrada da quantidade reportada e "
                "fecha a devolução — deixa de poder ser alterada "
                "depois."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=600,
            justify="left",
        )
        self.rotulo_explicacao.pack(anchor="w", padx=20, pady=(10, 0))

        self._construir_alerta_ajuste()
        self._construir_rodape()

    def _construir_tabela(self, itens, produtos):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20)

        cabecalho = ctk.CTkFrame(
            cartao, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO),
            ("STOCK ATUAL", _LARGURA_ARMAZEM + 20),
            ("A REPOR", _LARGURA_ARMAZEM),
            ("STOCK APÓS", _LARGURA_ARMAZEM + 10),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for item in itens:
            produto_id = item["produto_id"]
            produto = produtos.get(produto_id)
            nome_produto = produto["nome"] if produto else produto_id
            stock_atual = estoque.saldo_produto(produto_id)

            self.reportado_por_produto[produto_id] = item["quantidade"]
            self.stock_atual_por_produto[produto_id] = stock_atual
            self.nomes_produto_por_id[produto_id] = nome_produto

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome_produto,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PRODUTO,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(stock_atual),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_ARMAZEM + 20,
                anchor="w",
            ).pack(side="left")

            campo = ctk.CTkEntry(
                linha,
                width=_LARGURA_ARMAZEM - 20,
                corner_radius=tema.RAIO_CAMPO,
                justify="center",
            )
            campo.insert(0, str(item["quantidade"]))
            campo.pack(side="left")
            campo.bind(
                "<KeyRelease>",
                lambda evento, pid=produto_id: self._atualizar_linha(pid),
            )
            self.campos_por_produto[produto_id] = campo

            ctk.CTkLabel(
                linha,
                text="",
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=_LARGURA_ARMAZEM + 30,
                anchor="w",
            ).pack(side="left", padx=(10, 0))
            self.rotulos_apos_por_produto[produto_id] = (
                linha.winfo_children()[-1]
            )
            self._atualizar_linha(produto_id)

    def _quantidade_aceite(self, produto_id):
        """Lê o campo "a repor" de um produto, sem deixar sair do
        único limite que há: nunca negativo. Pode ser maior ou menor
        do que o reportado — a diferença, para qualquer um dos dois
        lados, é o que o ajuste de stock existe para corrigir
        (09/09/2026, pedido do aluno: "para mais também tem que
        ser", depois de confirmar que só para menos funcionava).
        """
        texto = self.campos_por_produto[produto_id].get().strip()
        quantidade = int(texto) if texto.isdigit() else 0

        return max(0, quantidade)

    def _atualizar_linha(self, produto_id):
        aceite = self._quantidade_aceite(produto_id)
        stock_atual = self.stock_atual_por_produto[produto_id]
        rotulo = self.rotulos_apos_por_produto[produto_id]

        if aceite == 0:
            rotulo.configure(
                text=f"{stock_atual} (sem alteração)",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            )
        else:
            rotulo.configure(
                text=f"{stock_atual + aceite}  (+{aceite})",
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
            )

        if self.frame_alerta is not None:
            self._atualizar_alerta_ajuste()

    def _diferencas_por_produto(self):
        """Produtos cujo valor "a repor" já não bate com o reportado
        — cada um vai precisar de um movimento de ajuste (positivo
        ou negativo) além da entrada da devolução, por isso exigem
        motivo (09/09/2026, pedido do aluno: "abre o ajuste de
        estoque com a quantidade de comparação").
        """
        diferencas = {}

        for produto_id, reportado in self.reportado_por_produto.items():
            aceite = self._quantidade_aceite(produto_id)
            diferenca = aceite - reportado

            if diferenca != 0:
                diferencas[produto_id] = diferenca

        return diferencas

    def _construir_alerta_ajuste(self):
        self.frame_alerta = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )

        self.rotulo_alerta = ctk.CTkLabel(
            self.frame_alerta,
            text="",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=11),
            wraplength=560,
            justify="left",
            anchor="w",
        )
        self.rotulo_alerta.pack(
            anchor="w", fill="x", padx=14, pady=(12, 6)
        )

        linha_motivo = ctk.CTkFrame(
            self.frame_alerta, fg_color="transparent"
        )
        linha_motivo.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(
            linha_motivo,
            text="Motivo do ajuste:",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        self.entry_motivo = ctk.CTkEntry(
            linha_motivo,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: 3 unidades vieram danificadas",
        )
        self.entry_motivo.pack(side="left", fill="x", expand=True)

        self._atualizar_alerta_ajuste()

    def _atualizar_alerta_ajuste(self):
        if self.frame_alerta is None:
            return

        diferencas = self._diferencas_por_produto()

        if not diferencas:
            self.frame_alerta.pack_forget()
            _centrar_sobre(
                self,
                self.tela_lista,
                self.largura_janela,
                self.altura_base,
            )
            return

        linhas = "; ".join(
            f"{self.nomes_produto_por_id[produto_id]}: {diferenca:+d} "
            "unid"
            for produto_id, diferenca in diferencas.items()
        )
        self.rotulo_alerta.configure(
            text=(
                "Vai ser aberto um movimento de ajuste de stock para "
                f"a diferença — {linhas}. O motivo abaixo fica "
                "registado no histórico de stock."
            )
        )
        self.frame_alerta.pack(
            fill="x",
            padx=20,
            pady=(10, 0),
            before=self.rotulo_explicacao,
        )
        # a janela não é redimensionável (resizable(False, False)) e
        # a altura foi calculada sem contar com este alerta — sem
        # crescer aqui, o rodapé com "Aceitar devolução" fica fora
        # da janela, inacessível (09/09/2026, aluno testou e viu o
        # botão sumir com o alerta aberto).
        _centrar_sobre(
            self,
            self.tela_lista,
            self.largura_janela,
            self.altura_base + _ALTURA_ALERTA_AJUSTE,
        )

    def _construir_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            rodape,
            text="Cancelar",
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
            text="Aceitar devolução",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._aceitar,
        ).pack(side="right")

    def _aceitar(self):
        diferencas = self._diferencas_por_produto()
        motivo = ""

        if diferencas:
            if self.entry_motivo is None:
                return

            motivo = self.entry_motivo.get().strip()

            if not motivo:
                componentes.mostrar_erro(
                    "Indique o motivo do ajuste de stock."
                )
                return

        quantidades_aceites = {
            produto_id: self._quantidade_aceite(produto_id)
            for produto_id in diferencas
        }

        self.destroy()
        self.tela_lista._aceitar_devolucao(
            self.devolucao,
            quantidades_aceites=quantidades_aceites,
            motivo_ajuste=motivo,
        )


class _ResumoRequisicaoModal(ctk.CTkToplevel):
    """Resumo (só leitura) da requisição de origem de uma devolução —
    aberto ao clicar no ID/estado "de REQ-..." de uma linha em
    "Aceitar Sobra (Devolução)" (09/09/2026, pedido do aluno: "abre
    resumo da requisição que foi enviada").

    Mostra o que foi pedido e o que foi mesmo enviado por produto —
    é o rasto completo: a devolução já mostra quem devolveu o quê,
    isto mostra a requisição que deu origem a essa sobra.
    """

    def __init__(self, master, requisicao_id):
        super().__init__(master)
        self.master_janela = master

        requisicao = estoque.procurar_requisicao(requisicao_id)
        itens = estoque.listar_itens_requisicao(
            requisicao_id=requisicao_id
        )
        produtos = {
            p["id"]: p for p in estoque.listar_produtos(True)
        }
        nomes_por_id = getattr(master, "nomes_por_id", None) or {
            r["id"]: r["nome"]
            for r in responsaveis.listar(incluir_inativos=True)
        }
        nome = nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )

        largura = 620
        altura = 300 + 36 * max(len(itens), 1)
        self.title(f"Resumo da requisição — {requisicao_id}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        _centrar_sobre(self, master, largura, altura)
        _colocar_no_topo(self)

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            cabecalho,
            text=f"Resumo da requisição — {requisicao_id}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")
        _etiqueta_estado(cabecalho, requisicao["estado"]).pack(
            side="left", padx=(10, 0)
        )

        ctk.CTkLabel(
            self,
            text=(
                f"Pedido por {nome} · "
                f"pedida {requisicao['data_pedido']} · "
                f"enviada {requisicao['data_envio'] or '—'} · "
                f"recebida {requisicao['data_fecho'] or '—'}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 14))

        self._construir_tabela(itens, produtos)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=16)

    def _construir_tabela(self, itens, produtos):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20)

        cabecalho = ctk.CTkFrame(
            cartao, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO),
            ("PEDIDO", _LARGURA_PEDIDO + 20),
            ("ENVIADO", _LARGURA_PEDIDO + 20),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for item in itens:
            produto = produtos.get(item["produto_id"])
            nome_produto = produto["nome"] if produto else item["produto_id"]

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome_produto,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PRODUTO,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_pedida"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PEDIDO + 20,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_enviada"]),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=_LARGURA_PEDIDO + 20,
                anchor="w",
            ).pack(side="left")