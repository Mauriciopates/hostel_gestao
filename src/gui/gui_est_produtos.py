"""Ecrã de Gestão de Produtos — o catálogo do armazém central.

Uma das quatro subáreas do módulo Stock (`gui_est_hub.py`). Mesma
estrutura visual da Gestão de Propriedades: barra de busca,
"Mostrar inativos", tabela em `componentes.Tabela` e botão "Gerir"
por linha, que abre um popup com as ações.

Decisões desta entrega (10/09/2026, mockup em HTML aprovado antes
de codar):

1. Tabela com cinco colunas: ID, NOME, STOCK MÍNIMO, SALDO ATUAL,
   AÇÕES. A coluna AÇÕES tem um único botão "Gerir" — mesmo padrão
   de Propriedades e Unidades.

2. A unidade de medida aparece como abreviatura depois da
   quantidade, em letra pequena ("12 un", "8 cx", "15 L") — não
   como coluna isolada. Decisão explícita do aluno na validação do
   mockup: evita uma coluna só para "un"/"cx"/"L", e a quantidade
   fica mais legível.

3. A coluna SALDO ATUAL pinta o número a vermelho quando o saldo
   está abaixo do stock mínimo. O aviso também aparece agregado
   numa faixa no topo (mesma linguagem da faixa do hub Stock), com
   a lista dos produtos abaixo do mínimo — dá a visão geral de um
   relance. Decisão do aluno: as duas coisas, não uma só.

4. Popup Gerir com Editar / Desativar (separador antes) /
   Reativar (só se inativo) — mesma convenção do Gerir de
   Propriedades.

   Desativar um produto com dependências ativas (movimentos, itens
   de requisição ou itens de devolução) passa por
   `_ConfirmarForcarProdutoModal`: mensagem com a contagem exata +
   dropdown de responsável obrigatório. Só ao escolher "Forçar
   desativação" é que `estoque.desativar_produto` é chamado com
   `forcar=True, responsavel_id=...`, e a desativação fica
   registada em `desativado_por_id`/`data_desativacao` — mesma
   convenção de `propriedades.desativar`/`unidades.desativar`
   (ALTER TABLE produtos, 10/09/2026).

   Sem dependências ativas, é só uma confirmação simples
   (`componentes.confirmar`).

5. Modal de criação/edição tem os três campos de
   `estoque.criar_produto` (nome, unidade de medida, stock mínimo),
   com uma ajuda por baixo a explicar o que cada um faz. "Stock
   mínimo" tem valor por omissão 0.

6. Unidade de medida como seletor (10/09/2026, mesma ronda de
   ajustes do mockup de HTML): em vez de caixa de texto livre,
   um dropdown com uma lista curta de unidades comuns mais
   "Outro (escrever ao lado)". Escolher um valor da lista preenche
   a caixa de texto que está por baixo E ESCONDE-A (só o seletor
   mostra o valor — mostrar as duas era redundante); escolher
   "Outro (escrever ao lado)" revela a caixa, vazia, para escrita
   livre. A caixa de texto continua a ser o valor realmente
   gravado, o seletor é só um atalho. Exatamente o mesmo padrão
   já usado em Clientes para a Nacionalidade (gui_clientes.py,
   ponto 9c/9d da docstring daquele módulo) — decisão do aluno,
   para o sistema ter uma linguagem visual consistente.
"""

import customtkinter as ctk

import estoque
import responsaveis
from . import componentes
from . import tema

# =====================================================================
# Lista de unidades de medida comuns — dropdown do formulário
# =====================================================================

UNIDADES_MEDIDA = (
    "un",  # unidade
    "cx",  # caixa
    "par",  # par
    "kg",  # quilograma
    "g",  # grama
    "L",  # litro
    "ml",  # mililitro
    "m",  # metro
    "rolo",  # rolo
    "frasco",  # frasco
    "pacote",  # pacote
)

UNIDADE_PLACEHOLDER = "— Escolher —"
OUTRA_UNIDADE = "Outro (escrever ao lado)"

# Tipos de produto (Fase 4, v1.4.0). Os mesmos quatro valores do
# ENUM na base de dados — a lista fica aqui, do lado da GUI, para
# o dropdown poder ser construído sem ir buscar nada ao MySQL. O
# valor gravado é sempre minúsculo, como no ENUM.

TIPOS_PRODUTO_GUI = (
    "consumivel",
    "roupa_cama",
    "roupa_banho",
    "outro",
)


# =====================================================================
# Larguras das colunas da tabela
# =====================================================================

_LARGURA_ID = 100
_LARGURA_NOME = 220
_LARGURA_STOCK_MIN = 130
_LARGURA_SALDO = 130
_LARGURA_ACOES = 100

# Altura da linha — o mesmo valor da tabela de Propriedades, para as
# linhas terem o mesmo peso visual entre ecrãs.
_ALTURA_LINHA = 44

# Colunas da tabela, no formato de `componentes.Coluna`. NOME
# reparte o espaço que sobra; ID, STOCK MÍNIMO, SALDO e AÇÕES não
# crescem.
_COLUNAS_PRODUTO = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("NOME", peso=3, minimo=_LARGURA_NOME),
    componentes.Coluna(
        "STOCK MÍNIMO",
        peso=1,
        minimo=_LARGURA_STOCK_MIN,
        alinhamento="centro",
    ),
    componentes.Coluna(
        "SALDO ATUAL",
        peso=1,
        minimo=_LARGURA_SALDO,
        alinhamento="centro",
    ),
    componentes.Coluna("AÇÕES", minimo=_LARGURA_ACOES, alinhamento="centro"),
)


class ListaProdutos(ctk.CTkFrame):
    """Ecrã principal do catálogo: tabela, busca, alerta de stock."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Stock · Produtos").pack(fill="x")

        # Botão de criação numa barra própria, logo abaixo do
        # cabeçalho e a verde — mesma convenção dos outros ecrãs.
        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Novo Produto",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovoProdutoModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome ou ID… (Enter)",
            width=220,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="left")
        # Só filtra ao premir Enter (mesmo padrão dos outros ecrãs):
        # filtrar a cada tecla redesenhava a lista inteira a cada letra.
        self.campo_busca.bind("<Return>", lambda evento: self._recarregar())

        self.mostrar_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativos",
            variable=self.mostrar_inativos,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right")

        # Faixa de alerta: só aparece quando há produtos abaixo do
        # mínimo. Criada uma vez e escondida com pack_forget quando
        # não há nada a assinalar — recriá-la a cada recarregamento
        # fazia a tabela saltar.
        self.faixa_alerta = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.rotulo_alerta = ctk.CTkLabel(
            self.faixa_alerta,
            text="",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
        )
        self.rotulo_alerta.pack(fill="x", padx=12, pady=8)

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_PRODUTO,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia="Ainda não há produtos cadastrados.",
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela + faixa de alerta.

        Chamada na abertura do ecrã, ao mexer em "Mostrar inativos",
        ao confirmar uma busca, e depois de qualquer criação,
        edição, desativação ou reativação.
        """
        self.tabela.limpar()

        incluir_inativos = self.mostrar_inativos.get()
        texto_busca = self.campo_busca.get().strip().lower()

        lista = estoque.listar_produtos(incluir_inativos=incluir_inativos)

        if texto_busca:
            lista = [
                produto
                for produto in lista
                if texto_busca in f"{produto['nome']} {produto['id']}".lower()
            ]

        self._atualizar_faixa_alerta()

        if not lista:
            self.tabela.mostrar_vazio(
                "Nenhum produto encontrado para a busca."
                if texto_busca
                else None
            )
            return

        for produto in lista:
            self._desenhar_produto(produto)

    def _atualizar_faixa_alerta(self):
        """Mostra a faixa amarela no topo, se houver produtos abaixo
        do mínimo — e esconde-a se não houver nada a assinalar.

        A lista vem de `estoque.listar_alertas_stock()`, já ordenada
        pelo negócio (o que falta mais primeiro). Só mostra os
        primeiros quatro nomes, com "…" se houver mais — a faixa
        existe para dar o sinal, não para ser a listagem completa
        (para isso já há a própria tabela).
        """
        try:
            alertas = estoque.listar_alertas_stock()
        except ValueError:
            self.faixa_alerta.pack_forget()
            return

        if not alertas:
            self.faixa_alerta.pack_forget()
            return

        nomes = ", ".join(a["produto"]["nome"] for a in alertas[:4])

        if len(alertas) > 4:
            nomes += ", …"

        self.rotulo_alerta.configure(
            text=(f"{len(alertas)} produtos abaixo do mínimo: {nomes}.")
        )
        self.faixa_alerta.pack(
            fill="x", padx=20, pady=(4, 8), before=self.tabela
        )

    # -- desenho ------------------------------------------------------

    def _desenhar_produto(self, produto):
        """Desenha uma linha da tabela para um produto.

        O saldo é calculado por `estoque.saldo_produto()` — nunca
        um campo guardado (decisão 9). Se estiver abaixo do mínimo
        (`estoque.abaixo_do_minimo`), o número fica a vermelho, para
        a linha do produto afetado se distinguir das outras sem
        precisar de olhar para a faixa do topo.
        """
        inativo = not produto["ativo"]
        unidade = produto["unidade_medida"]

        try:
            saldo = estoque.saldo_produto(produto["id"])
            abaixo = estoque.abaixo_do_minimo(produto["id"])
        except ValueError:
            saldo = 0
            abaixo = False

        linha = self.tabela.nova_linha()

        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=produto["id"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL if inativo else tema.AZUL_PRINCIPAL
                ),
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ID,
                anchor="w",
            ),
            esticar="w",
        )

        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=produto["nome"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL if inativo else tema.COR_TEXTO
                ),
                font=ctk.CTkFont(size=13),
                width=_LARGURA_NOME,
                anchor="w",
            ),
        )

        self.tabela.colocar(
            linha,
            2,
            self._celula_quantidade(
                produto["stock_minimo"], unidade, inativo, destacar=False
            ),
        )

        self.tabela.colocar(
            linha,
            3,
            self._celula_quantidade(saldo, unidade, inativo, destacar=abaixo),
        )

        acoes = self.tabela.celula_acoes(linha, 4)
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
                command=lambda: _AcoesProdutoModal(self, produto),
            )
        )

    def _celula_quantidade(self, quantidade, unidade, inativo, destacar):
        """Célula com número + abreviatura de unidade em letra pequena.

        A unidade fica em tamanho menor e cor secundária, colada ao
        número — "12 un" lê-se como uma coisa só, sem precisar de
        uma coluna à parte.

        'destacar' pinta o número a vermelho (usado na coluna SALDO
        quando está abaixo do mínimo).
        """
        bloco = ctk.CTkFrame(self.tabela.grelha, fg_color="transparent")

        numero = ctk.CTkLabel(
            bloco,
            text=str(quantidade),
            text_color=self._cor_quantidade(inativo, destacar),
            font=ctk.CTkFont(size=12, weight="bold" if destacar else "normal"),
        )
        numero.pack(side="left")

        ctk.CTkLabel(
            bloco,
            text=unidade,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(side="left", padx=(3, 0))

        return bloco

    def _cor_quantidade(self, inativo, destacar):
        if inativo:
            return tema.TEXTO_INDISPONIVEL
        if destacar:
            return tema.TEXTO_ERRO
        return tema.COR_TEXTO

    # -- ações -------------------------------------------------------

    def _desativar(self, produto):
        """Desativa um produto, pedindo forçar se tiver dependências.

        Mesma lógica de `_desativar_propriedade` (gui_propriedades.py):
        conta as dependências ativas (movimentos + itens de
        requisição + itens de devolução) antes de tentar; se houver,
        abre o popup de forçar com pedido de responsável. Se não
        houver, confirmação simples.
        """
        total_dependencias = estoque.contar_dependencias_produto(produto["id"])

        if total_dependencias:
            mensagem = (
                f"O produto {produto['nome']} tem "
                f"{total_dependencias} registo(s) associado(s) "
                f"(movimentos, requisições ou devoluções) — deseja "
                f"mesmo desativá-lo?"
            )
            _ConfirmarForcarProdutoModal(
                self,
                mensagem,
                lambda responsavel_id: self._forcar_desativar(
                    produto, responsavel_id
                ),
            )
            return

        if not componentes.confirmar(
            f"Desativar o produto {produto['nome']} ({produto['id']})?",
            titulo="Desativar produto",
        ):
            return

        try:
            estoque.desativar_produto(produto["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Produto {produto['nome']} desativado.")
        self._recarregar()

    def _forcar_desativar(self, produto, responsavel_id):
        """Chamado pelo `_ConfirmarForcarProdutoModal` quando o
        utilizador confirma a desativação forçada com um responsável
        escolhido.
        """
        try:
            estoque.desativar_produto(
                produto["id"], forcar=True, responsavel_id=responsavel_id
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Produto {produto['nome']} desativado.")
        self._recarregar()

    def _reativar(self, produto):
        """Reativa um produto desativado — sem confirmação."""
        try:
            estoque.reativar_produto(produto["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Produto {produto['nome']} reativado.")
        self._recarregar()


class _ConfirmarForcarProdutoModal(ctk.CTkToplevel):
    """Modal de duas opções — "Cancelar" ou "Forçar desativação" —
    mostrado quando desativar um produto encontra dependências
    ativas (movimentos, itens de requisição ou itens de devolução).

    Mesmo padrão do `_ConfirmarForcarModal` de gui_propriedades.py:
    mensagem + dropdown de responsável obrigatório + botão vermelho
    de confirmação. `ao_forcar(responsavel_id)` só é chamado se
    "Forçar desativação" for escolhido com um responsável
    selecionado.
    """

    def __init__(self, master, mensagem, ao_forcar):
        super().__init__(master)
        self.ao_forcar = ao_forcar

        self.title("Confirmar desativação")
        self.geometry("380x300")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=mensagem,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            wraplength=330,
            justify="left",
        ).pack(padx=20, pady=(24, 14), fill="x")

        ctk.CTkLabel(
            self,
            text="Responsável que autoriza *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel = componentes.Seletor(self, values=nomes)
        self.combo_responsavel.set(nomes[0])
        self.combo_responsavel.pack(fill="x", padx=20, pady=(2, 10))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Forçar desativação",
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._forcar,
        ).pack(side="right")

    def _responsavel_escolhido_id(self):
        indice = self.combo_responsavel.cget("values").index(
            self.combo_responsavel.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _forcar(self):
        responsavel_id = self._responsavel_escolhido_id()

        if not responsavel_id:
            componentes.mostrar_erro(
                "Escolhe o responsável que autoriza a desativação " "forçada."
            )
            return

        self.destroy()
        self.ao_forcar(responsavel_id)


class _AcoesProdutoModal(ctk.CTkToplevel):
    """Popup de "Gerir" de um produto.

    Mesmo padrão dos popups de Propriedades, Unidades e
    Responsáveis: nome/ID no topo, botões de ação com a mesma forma
    e contorno (só a cor do texto muda), separador antes da ação
    destrutiva, "Fechar" no fim.

    Um produto ativo tem Editar + Desativar (com separador); um
    inativo tem só Reativar.
    """

    def __init__(self, tela_lista, produto):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.produto = produto

        altura = 230
        self.title(f"Ações — {produto['id']}")
        self.geometry(f"300x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, 300, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=produto["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=260,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=produto["id"],
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if produto["ativo"]:
            self._botao(
                "Editar",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EditarProdutoModal(tela_lista, produto),
            )
            self._separador()
            self._botao(
                "Desativar",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: tela_lista._desativar(produto),
            )
        else:
            self._botao(
                "Reativar",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: tela_lista._reativar(produto),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=(10, 16))

    def _separador(self):
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, text_color, hover_color, acao):
        """Botão de ação: fecha o popup antes de agir.

        A ordem importa — as ações recarregam a tabela por trás, e
        deixar este popup aberto por cima deixava-o órfão sobre
        coisas que entretanto mudaram.
        """

        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)


class _FormularioProduto(ctk.CTkToplevel):
    """Base comum a NovoProdutoModal e EditarProdutoModal.

    Os dois têm os mesmos três campos e a mesma disposição; só muda
    o título, os valores iniciais e o que acontece ao gravar.
    Duplicar o formulário era duplicar também cada correção futura
    de layout.

    A unidade de medida é um campo composto (dropdown + caixa de
    texto), ao estilo do campo "Nacionalidade" em gui_clientes.py —
    ver ponto 6 da docstring do módulo.
    """

    def __init__(
        self,
        tela_lista,
        titulo,
        texto_botao,
        nome="",
        unidade_medida="",
        stock_minimo="",
        tipo_produto="consumivel",
    ):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 480, 620

        self.title(titulo)
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        # ---- Nome ----

        ctk.CTkLabel(
            self,
            text="Nome *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 12))
        self.campo_nome.insert(0, nome)

        # ---- Unidade de medida (dropdown + caixa composta) ----

        ctk.CTkLabel(
            self,
            text="Unidade de medida *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self._construir_campo_unidade(unidade_medida)

        ctk.CTkLabel(
            self,
            text=(
                "Aparece ao lado da quantidade nas tabelas — "
                "12 un, 8 cx, 15 L."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=24, pady=(0, 10))

        # ---- Stock mínimo ----

        ctk.CTkLabel(
            self,
            text="Stock mínimo",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_stock_minimo = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="Enter para 0",
        )
        self.campo_stock_minimo.pack(fill="x", padx=24, pady=(2, 2))
        self.campo_stock_minimo.insert(0, str(stock_minimo))

        ctk.CTkLabel(
            self,
            text=(
                "Abaixo deste valor, o produto aparece na faixa de "
                "alerta no topo."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=24)

        # ---- Tipo de produto (Fase 4, v1.4.0) ----

        ctk.CTkLabel(
            self,
            text="Tipo de produto *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(10, 0))

        self.combo_tipo_produto = componentes.Seletor(
            self,
            values=list(TIPOS_PRODUTO_GUI),
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_tipo_produto.pack(fill="x", padx=24, pady=(2, 2))
        self.combo_tipo_produto.set(tipo_produto)

        ctk.CTkLabel(
            self,
            text=(
                "Só os produtos de roupa de cama / roupa de banho "
                "entram no Rol de Lavanderia automático."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=430,
            justify="left",
        ).pack(anchor="w", padx=24)

        # ---- Rodapé ----

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=20, side="bottom")

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
            text=texto_botao,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._gravar,
        ).pack(side="right")

        self.campo_nome.focus_set()

    # -- montagem do campo composto da unidade -----------------------

    def _construir_campo_unidade(self, valor_inicial):
        """Campo composto: um seletor com a lista curta de unidades
        comuns + "Outro (escrever ao lado)", por baixo do qual vive
        uma caixa de texto.

        Regra de visibilidade (mesma de gui_clientes.py para a
        Nacionalidade):

        - valor_inicial vazio ou já na lista → seletor mostra o
          valor (ou o placeholder); caixa escondida.
        - valor_inicial fora da lista (ex.: "Toalha") → seletor em
          "Outro (escrever ao lado)", caixa visível com o valor.
        """
        bloco = ctk.CTkFrame(self, fg_color="transparent")
        bloco.pack(fill="x", padx=24, pady=(2, 2))
        bloco.grid_columnconfigure(0, weight=1)

        # Caixa de texto (valor realmente gravado) — criada primeiro
        # e colocada na linha 1, mas ESCONDIDA por omissão; só
        # aparece quando o seletor está em "Outro (escrever ao
        # lado)".
        self.campo_unidade = ctk.CTkEntry(
            bloco,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="Escreve a unidade de medida",
        )
        self.campo_unidade.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.campo_unidade.grid_remove()

        # Seletor — dropdown com placeholder + lista + "Outro".
        self.combo_unidade = componentes.Seletor(
            bloco,
            values=(
                [UNIDADE_PLACEHOLDER] + list(UNIDADES_MEDIDA) + [OUTRA_UNIDADE]
            ),
            command=self._ao_escolher_unidade,
        )
        self.combo_unidade.grid(row=0, column=0, sticky="ew")

        # Estado inicial — depende do valor que veio do produto
        # (vazio ao criar; preenchido ao editar).
        if not valor_inicial:
            self.combo_unidade.set(UNIDADE_PLACEHOLDER)
        elif valor_inicial in UNIDADES_MEDIDA:
            self.combo_unidade.set(valor_inicial)
            self.campo_unidade.insert(0, valor_inicial)
            self.campo_unidade.grid_remove()
        else:
            # Valor fora da lista — passa a "Outro" e revela a caixa.
            self.combo_unidade.set(OUTRA_UNIDADE)
            self.campo_unidade.insert(0, valor_inicial)
            self.campo_unidade.grid()

    def _ao_escolher_unidade(self, valor):
        """Chamada pelo dropdown sempre que a escolha muda.

        Mesma lógica de `_ao_escolher_nacionalidade` em
        gui_clientes.py:

        - "Outro (escrever ao lado)" → limpa a caixa, mostra-a e põe
          o foco.
        - placeholder ("— Escolher —") → esconde a caixa.
        - valor da lista → preenche a caixa e esconde-a (só o
          seletor mostra o valor).
        """
        if valor == OUTRA_UNIDADE:
            self.campo_unidade.delete(0, "end")
            self.campo_unidade.grid()
            self.campo_unidade.focus_set()
        elif valor == UNIDADE_PLACEHOLDER:
            self.campo_unidade.grid_remove()
        else:
            self.campo_unidade.delete(0, "end")
            self.campo_unidade.insert(0, valor)
            self.campo_unidade.grid_remove()

    # -- leitura dos valores -----------------------------------------

    def _valores(self):
        """Devolve (nome, unidade_medida, stock_minimo, tipo_produto)
        já normalizados.

        A unidade de medida vem da CAIXA (o seletor é só atalho);
        pode vir preenchida pela lista ou escrita à mão no caso
        "Outro". Se o seletor estiver num valor da lista, a caixa
        foi preenchida programaticamente; se estiver em "Outro", é
        o que o utilizador escreveu.

        O stock mínimo é convertido para int — se o campo vier
        vazio, assume 0 (mesmo comportamento do CLI).

        O tipo de produto (Fase 4, v1.4.0) vem sempre do dropdown,
        que só aceita os quatro valores do ENUM — não há validação
        extra aqui. A validação final (raise ValueError se inválido)
        vive em `estoque.criar_produto`/`atualizar_produto`.
        """
        nome = self.campo_nome.get().strip()
        unidade_medida = self.campo_unidade.get().strip()

        if not unidade_medida:
            raise ValueError("A unidade de medida é obrigatória.")

        texto_minimo = self.campo_stock_minimo.get().strip()

        if not texto_minimo:
            stock_minimo = 0
        elif texto_minimo.isdigit():
            stock_minimo = int(texto_minimo)
        else:
            raise ValueError("O stock mínimo tem de ser um número inteiro.")

        tipo_produto = self.combo_tipo_produto.get()

        return nome, unidade_medida, stock_minimo, tipo_produto

    def _gravar(self):
        raise NotImplementedError


class NovoProdutoModal(_FormularioProduto):
    """Modal de criação de um produto."""

    def __init__(self, tela_lista):
        super().__init__(
            tela_lista,
            titulo="Novo Produto",
            texto_botao="Criar",
        )

    def _gravar(self):
        try:
            (
                nome,
                unidade_medida,
                stock_minimo,
                tipo_produto,
            ) = self._valores()
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            produto = estoque.criar_produto(
                nome,
                unidade_medida,
                stock_minimo=stock_minimo,
                tipo_produto=tipo_produto,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Produto criado com sucesso: {produto['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class EditarProdutoModal(_FormularioProduto):
    """Modal de edição de um produto existente."""

    def __init__(self, tela_lista, produto):
        self.produto = produto
        super().__init__(
            tela_lista,
            titulo=f"Editar Produto — {produto['id']}",
            texto_botao="Guardar",
            nome=produto["nome"],
            unidade_medida=produto["unidade_medida"],
            stock_minimo=produto["stock_minimo"],
            tipo_produto=produto["tipo_produto"],
        )

    def _gravar(self):
        try:
            (
                nome,
                unidade_medida,
                stock_minimo,
                tipo_produto,
            ) = self._valores()
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            estoque.atualizar_produto(
                self.produto["id"],
                nome=nome,
                unidade_medida=unidade_medida,
                stock_minimo=stock_minimo,
                tipo_produto=tipo_produto,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Produto {self.produto['id']} atualizado."
        )
        self.destroy()
        self.tela_lista._recarregar()
