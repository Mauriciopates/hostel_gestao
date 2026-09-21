"""Ecrã de Movimentos de Stock — o histórico imutável de entradas,
saídas e ajustes de cada produto.

Uma das quatro subáreas do módulo Stock (`gui_est_hub.py`).

Decisões desta entrega (10/09/2026, mockup em HTML aprovado antes
de codar):

1. Tabela com seis colunas: ID, PRODUTO, TIPO, QUANTIDADE, DATA,
   RESPONSÁVEL — sem coluna AÇÕES. Movimentos são imutáveis
   (decisão 9): não há "editar", "desativar" nem "reativar" para
   esta entidade. Uma correção faz-se com um novo movimento de
   ajuste, nunca alterando o antigo.

2. O único botão de criação é "+ Registar Movimento" no topo
   (verde), que abre um popup intermédio a perguntar o tipo
   (Entrada / Saída / Ajuste) antes de abrir o formulário — mesmo
   padrão do `_EscolherTipoRequisicaoModal` das requisições.

3. A coluna QUANTIDADE mostra sempre o sinal explícito (+20, -12,
   -2, +3): a cor da linha e a cor do chip do tipo distinguem
   entrada de saída; o sinal evita ter de olhar para o tipo para
   saber de que lado está o movimento. Decisão do aluno na
   validação do mockup.

4. O dropdown de tipo no filtro usa os valores em minúsculas
   ("entrada", "saida", "ajuste") — coerente com as outras tabelas
   da aplicação (requisições e devoluções também mostram o estado
   em minúsculas). Decisão do aluno.

5. Filtros por produto e por tipo no topo. O filtro de produto
   pré-seleciona o produto no formulário de registo (decisão (ii)
   do aluno, 10/09/2026) — poupa uma escolha quando se está a
   registar vários movimentos seguidos do mesmo produto.

6. O formulário de registo (RegistarMovimentoModal) tem produto
   via dropdown (com o saldo atual visível), tipo pré-selecionado
   pelo cartão do popup intermédio, quantidade, data e
   responsável. Motivo disponível para escrita sempre, mas só
   obrigatório em ajuste — mesma regra de
   `estoque.registar_movimento`.
"""

import datetime

import customtkinter as ctk

import estoque
import responsaveis
from . import componentes
from . import gui_est_comum
from . import tema


# =====================================================================
# Larguras das colunas da tabela
# =====================================================================

_LARGURA_ID = 100
_LARGURA_PRODUTO = 220
_LARGURA_TIPO = 110
_LARGURA_QUANTIDADE = 110
_LARGURA_DATA = 120
_LARGURA_RESPONSAVEL = 180

_ALTURA_LINHA = 44

_COLUNAS_MOVIMENTO = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("PRODUTO", peso=3, minimo=_LARGURA_PRODUTO),
    componentes.Coluna(
        "TIPO", peso=1, minimo=_LARGURA_TIPO, alinhamento="centro"
    ),
    componentes.Coluna(
        "QUANTIDADE",
        peso=1,
        minimo=_LARGURA_QUANTIDADE,
        alinhamento="centro",
    ),
    componentes.Coluna(
        "DATA", peso=1, minimo=_LARGURA_DATA, alinhamento="centro"
    ),
    componentes.Coluna(
        "RESPONSÁVEL", peso=2, minimo=_LARGURA_RESPONSAVEL
    ),
)

_OPCAO_TODOS_PRODUTOS = "Todos os produtos"
_OPCAO_TODOS_TIPOS = "Todos os tipos"


class ListaMovimentos(ctk.CTkFrame):
    """Ecrã principal do histórico de movimentos: tabela + filtros."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Stock · Movimentos").pack(
            fill="x"
        )

        # Botão de criação + "< Voltar ao Stock" na mesma barra.
        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))

        ctk.CTkButton(
            barra_criar,
            text="+ Registar Movimento",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _EscolherTipoMovimentoModal(self),
        ).pack(side="left")

        ctk.CTkButton(
            barra_criar,
            text="< Voltar ao Stock",
            width=140,
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=lambda: controlador.mostrar_frame(
                __import__(
                    "gui.gui_est_hub", fromlist=["EcraStock"]
                ).EcraStock
            ),
        ).pack(side="left", padx=(10, 0))

        # Filtros: produto e tipo. O produto pré-seleciona o que for
        # escolhido aqui no formulário de registo (decisão (ii)).
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=20, pady=(0, 6))

        self.produtos_disponiveis = estoque.listar_produtos(
            incluir_inativos=True
        )
        self.id_por_rotulo_produto = {
            gui_est_comum.rotulo_produto(p): p["id"]
            for p in self.produtos_disponiveis
        }

        self.combo_produto = componentes.Seletor(
            filtros,
            values=(
                [_OPCAO_TODOS_PRODUTOS]
                + sorted(self.id_por_rotulo_produto)
            ),
            width=240,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_produto.set(_OPCAO_TODOS_PRODUTOS)
        self.combo_produto.pack(side="left")

        self.combo_tipo = componentes.Seletor(
            filtros,
            values=[_OPCAO_TODOS_TIPOS] + list(
                gui_est_comum.TIPOS_MOVIMENTO
            ),
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_tipo.set(_OPCAO_TODOS_TIPOS)
        self.combo_tipo.pack(side="left", padx=(10, 0))

        # Nomes dos responsáveis, para mostrar em vez do ID cru.
        self.nomes_por_id = {
            r["id"]: r["nome"]
            for r in responsaveis.listar(incluir_inativos=True)
        }

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_MOVIMENTO,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia="Sem movimentos com estes filtros.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _produto_filtro(self):
        """ID do produto filtrado, ou None para "todos"."""
        return self.id_por_rotulo_produto.get(self.combo_produto.get())

    def _tipo_filtro(self):
        """Tipo filtrado, ou None para "todos"."""
        valor = self.combo_tipo.get()
        if valor == _OPCAO_TODOS_TIPOS:
            return None
        return valor

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela de movimentos."""
        self.tabela.limpar()

        produto_id = self._produto_filtro()
        tipo = self._tipo_filtro()

        # `estoque` não tem `listar_movimentos` próprio no módulo de
        # negócio (só existe `listar_movimentos` no repositório); a
        # leitura correta para a interface é pedir os movimentos ao
        # repositório via `estoque`, ou usar `estoque.saldo_produto`
        # por produto. Aqui usamos `repositorio.listar_movimentos`
        # indiretamente — ver nota em baixo, no comentário do
        # `import`.
        #
        # NOTA DE ARQUITETURA: este ecrã precisa de uma função
        # pública `estoque.listar_movimentos(produto_id=None,
        # tipo=None)` que ainda não existe. A M3 acrescenta-a. Por
        # agora, este ficheiro assume que ela existe e importa-a de
        # `estoque`; se quiseres testar já antes da M3, cria uma
        # função provisória em `estoque.py` que reencaminhe para
        # `repositorio.listar_movimentos` com os filtros aplicados
        # em Python.
        movimentos = estoque.listar_movimentos(
            produto_id=produto_id, tipo=tipo
        )

        # Mais recentes primeiro. `data` pode ser None num registo
        # antigo — comparar None com date rebenta; daí o par
        # (tem_data, data) como chave.
        movimentos.sort(
            key=lambda m: (
                m["data"] is not None,
                m["data"] or datetime.date.min,
            ),
            reverse=True,
        )

        if not movimentos:
            self.tabela.mostrar_vazio()
            return

        produtos_por_id = {
            p["id"]: p for p in self.produtos_disponiveis
        }

        for movimento in movimentos:
            self._desenhar_movimento(movimento, produtos_por_id)

    # -- desenho ------------------------------------------------------

    def _desenhar_movimento(self, movimento, produtos_por_id):
        """Desenha uma linha da tabela para um movimento.

        A coluna QUANTIDADE mostra sempre o sinal explícito: `+20`
        para entrada, `-20` para saída, `+3` / `-2` para ajuste. A
        cor do texto segue o sinal (verde para positivo, vermelho
        para negativo), e o chip da coluna TIPO tem a cor do tipo —
        dois sinais visuais distintos, um para o lado do movimento,
        outro para o tipo.
        """
        produto = produtos_por_id.get(movimento["produto_id"])
        nome_produto = (
            produto["nome"] if produto else movimento["produto_id"]
        )

        # Em "entrada" e "saida" a quantidade está sempre positiva
        # no registo (o sinal vem do tipo); em "ajuste" pode vir
        # negativa. Aplicamos o sinal "efetivo" para o utilizador
        # ler o que aconteceu ao stock, sem ter de cruzar com o tipo.
        tipo = movimento["tipo"]
        quantidade = movimento["quantidade"]

        if tipo == "saida":
            quantidade_efetiva = -quantidade
        else:
            quantidade_efetiva = quantidade

        if quantidade_efetiva >= 0:
            texto_quantidade = f"+{quantidade_efetiva}"
            cor_quantidade = tema.TEXTO_LIVRE
        else:
            texto_quantidade = str(quantidade_efetiva)
            cor_quantidade = tema.TEXTO_ERRO

        unidade = produto["unidade_medida"] if produto else ""

        linha = self.tabela.nova_linha()

        # ID
        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=movimento["id"],
                text_color=tema.AZUL_PRINCIPAL,
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ID,
                anchor="w",
            ),
            esticar="w",
        )

        # Produto
        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=nome_produto,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=13),
                width=_LARGURA_PRODUTO,
                anchor="w",
            ),
        )

        # Tipo (chip colorido)
        self.tabela.colocar(
            linha,
            2,
            gui_est_comum.etiqueta_estado(linha, tipo),
        )

        # Quantidade (com sinal e unidade)
        self.tabela.colocar(
            linha,
            3,
            self._celula_quantidade(
                texto_quantidade, unidade, cor_quantidade
            ),
        )

        # Data
        data = movimento["data"]
        self.tabela.colocar(
            linha,
            4,
            ctk.CTkLabel(
                linha,
                text=data.strftime("%d/%m/%Y") if data else "—",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_DATA,
            ),
        )

        # Responsável
        responsavel_id = movimento["responsavel_id"]
        nome_responsavel = (
            self.nomes_por_id.get(responsavel_id)
            if responsavel_id
            else None
        )

        self.tabela.colocar(
            linha,
            5,
            ctk.CTkLabel(
                linha,
                text=nome_responsavel or "—",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_RESPONSAVEL,
                anchor="w",
            ),
        )

    def _celula_quantidade(self, texto, unidade, cor):
        """Célula com número + unidade em letra pequena — mesma
        convenção dos Produtos."""
        bloco = ctk.CTkFrame(
            self.tabela.grelha, fg_color="transparent"
        )

        ctk.CTkLabel(
            bloco,
            text=texto,
            text_color=cor,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left")

        if unidade:
            ctk.CTkLabel(
                bloco,
                text=unidade,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10),
            ).pack(side="left", padx=(3, 0))

        return bloco


class _EscolherTipoMovimentoModal(ctk.CTkToplevel):
    """Popup intermédio do botão "+ Registar Movimento".

    Pergunta o tipo (Entrada / Saída / Ajuste) antes de abrir o
    formulário. Mesmo padrão do `_EscolherTipoRequisicaoModal`
    (gui_est_requisicoes.py): cartões clicáveis, um por opção, com
    o formulário correspondente a abrir a seguir.

    Escolha por cartões (e não por dropdown dentro do formulário)
    porque foi decisão explícita do aluno: separa a intenção
    ("o que quero registar?") do preenchimento do formulário, e o
    formulário já abre com o tipo certo.
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 380, 320
        self.title("Registar movimento")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(
            self, tela_lista, largura, altura
        )
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="O que pretende registar?",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 14))

        self._cartao(
            "Entrada",
            "Compra ou reposição de stock",
            lambda: self._abrir("entrada"),
        )
        self._cartao(
            "Saída",
            "Consumo, envio ou baixa",
            lambda: self._abrir("saida"),
        )
        self._cartao(
            "Ajuste",
            "Correção de inventário — motivo obrigatório",
            lambda: self._abrir("ajuste"),
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
        cartao.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            cartao,
            text=descricao,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", padx=14, pady=(0, 10))

        componentes.tornar_cliclavel(cartao, ao_clicar)

    def _abrir(self, tipo):
        self.destroy()
        # Pré-seleção: se o filtro de produto da lista estiver ativo,
        # o formulário abre já com esse produto escolhido (decisão
        # (ii) do aluno, 10/09/2026).
        produto_id_inicial = self.tela_lista._produto_filtro()
        RegistarMovimentoModal(
            self.tela_lista, tipo, produto_id_inicial=produto_id_inicial
        )


class RegistarMovimentoModal(ctk.CTkToplevel):
    """Formulário de registo de um movimento de stock.

    Recebe o tipo já pré-selecionado pelo popup intermédio
    (`_EscolherTipoMovimentoModal`) e, opcionalmente, um produto
    pré-selecionado (se o filtro da lista estiver ativo).

    Regras de validação (todas herdadas de `estoque.registar_movimento`):

    - Quantidade obrigatória, inteira, não nula.
    - Em `entrada` e `saida`, quantidade positiva.
    - Em `ajuste`, quantidade pode ser negativa.
    - Motivo obrigatório só em `ajuste`.
    - Data obrigatória.
    - Responsável opcional (valida-se contra responsáveis ativos,
      se preenchido).

    A validação de formato faz-se aqui (conversões de texto para
    int/date); a validação de regra de negócio fica toda em
    `estoque.registar_movimento`, que levanta ValueError com
    mensagem pronta a mostrar.
    """

    def __init__(self, tela_lista, tipo, produto_id_inicial=None):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.tipo = tipo

        largura, altura = 520, 620
        self.title("Registo de Movimento")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(
            self, tela_lista, largura, altura
        )
        componentes.colocar_no_topo(self)

        # ---- Cabeçalho ----

        ctk.CTkLabel(
            self,
            text="Registo de Movimento",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 4))

        linha_subtitulo = ctk.CTkFrame(self, fg_color="transparent")
        linha_subtitulo.pack(fill="x", padx=24, pady=(0, 14))

        ctk.CTkLabel(
            linha_subtitulo,
            text="Tipo pré-selecionado:",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="left")

        # Chip do tipo — mesma linguagem visual da tabela.
        fundo, cor_texto = gui_est_comum.CORES_ESTADO[tipo]
        ctk.CTkLabel(
            linha_subtitulo,
            text=tipo,
            text_color=cor_texto,
            fg_color=fundo,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=10,
            pady=3,
        ).pack(side="left", padx=(6, 0))

        # ---- Produto (dropdown com saldo visível) ----

        ctk.CTkLabel(
            self,
            text="Produto *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.produtos_disponiveis = estoque.listar_produtos()
        self.id_por_rotulo_produto = {
            gui_est_comum.rotulo_produto(p): p["id"]
            for p in self.produtos_disponiveis
        }

        rotulos = sorted(self.id_por_rotulo_produto)

        self.combo_produto = componentes.Seletor(
            self,
            values=rotulos or ["— Sem produtos —"],
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._atualizar_saldo(),
        )
        self.combo_produto.pack(fill="x", padx=24, pady=(2, 2))

        # Pré-seleção a partir do filtro da lista
        if produto_id_inicial is not None:
            for rotulo, pid in self.id_por_rotulo_produto.items():
                if pid == produto_id_inicial:
                    self.combo_produto.set(rotulo)
                    break
        elif rotulos:
            self.combo_produto.set(rotulos[0])

        self.rotulo_saldo = ctk.CTkLabel(
            self,
            text="",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        )
        self.rotulo_saldo.pack(fill="x", padx=24, pady=(2, 12))
        self._atualizar_saldo()

        # ---- Quantidade + Data (lado a lado) ----

        linha_campos = ctk.CTkFrame(self, fg_color="transparent")
        linha_campos.pack(fill="x", padx=24)

        coluna_qtd = ctk.CTkFrame(
            linha_campos, fg_color="transparent"
        )
        coluna_qtd.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkLabel(
            coluna_qtd,
            text=(
                "Quantidade * (pode ser negativa)"
                if tipo == "ajuste"
                else "Quantidade *"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")

        self.campo_quantidade = ctk.CTkEntry(
            coluna_qtd,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: 20",
        )
        self.campo_quantidade.pack(fill="x", pady=(2, 0))

        coluna_data = ctk.CTkFrame(
            linha_campos, fg_color="transparent"
        )
        coluna_data.pack(side="left", fill="x", expand=True, padx=(6, 0))

        ctk.CTkLabel(
            coluna_data,
            text="Data *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")

        self.campo_data = ctk.CTkEntry(
            coluna_data,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="dd/mm/aaaa",
        )
        self.campo_data.insert(
            0, datetime.date.today().strftime("%d/%m/%Y")
        )
        self.campo_data.pack(fill="x", pady=(2, 0))

        # ---- Responsável ----

        ctk.CTkLabel(
            self,
            text="Responsável",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(14, 0))

        self.responsaveis_disponiveis = responsaveis.listar()
        self.id_por_rotulo_responsavel = {
            gui_est_comum.rotulo_responsavel(r): r["id"]
            for r in self.responsaveis_disponiveis
        }

        self.combo_responsavel = componentes.Seletor(
            self,
            values=(
                ["— Nenhum —"]
                + sorted(self.id_por_rotulo_responsavel)
            ),
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_responsavel.set("— Nenhum —")
        self.combo_responsavel.pack(fill="x", padx=24, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text=(
                "Opcional. Se preenchido, fica registado no histórico "
                "de stock."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 12))

        # ---- Motivo ----

        self.rotulo_motivo = ctk.CTkLabel(
            self,
            text="Motivo *" if tipo == "ajuste" else "Motivo",
            text_color=(
                tema.TEXTO_ERRO
                if tipo == "ajuste"
                else tema.COR_TEXTO_SECUNDARIO
            ),
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.rotulo_motivo.pack(fill="x", padx=24)

        self.campo_motivo = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=(
                "ex.: 3 unidades vieram danificadas do fornecedor"
                if tipo == "ajuste"
                else "opcional em entrada/saída"
            ),
            border_color=(
                tema.TEXTO_ERRO if tipo == "ajuste" else tema.COR_BORDA
            ),
        )
        self.campo_motivo.pack(fill="x", padx=24, pady=(2, 2))

        if tipo == "ajuste":
            texto_ajuda = (
                "Obrigatório em ajuste — explica o que motivou a "
                "correção."
            )
            cor_ajuda = tema.TEXTO_ERRO
        else:
            texto_ajuda = "Só é obrigatório em ajustes."
            cor_ajuda = tema.COR_TEXTO_SECUNDARIO

        ctk.CTkLabel(
            self,
            text=texto_ajuda,
            text_color=cor_ajuda,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", padx=24)

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
            text="Registar movimento",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._registar,
        ).pack(side="right")

    # -- helpers -----------------------------------------------------

    def _produto_id(self):
        return self.id_por_rotulo_produto.get(self.combo_produto.get())

    def _responsavel_id(self):
        return self.id_por_rotulo_responsavel.get(
            self.combo_responsavel.get()
        )

    def _atualizar_saldo(self):
        """Mostra o saldo atual do produto escolhido, em armazém.

        Chamado na abertura e sempre que o produto muda — dá ao
        utilizador o contexto de que precisa antes de escrever uma
        quantidade.
        """
        produto_id = self._produto_id()

        if produto_id is None:
            self.rotulo_saldo.configure(text="")
            return

        try:
            saldo = estoque.saldo_produto(produto_id)
        except ValueError:
            self.rotulo_saldo.configure(text="")
            return

        produto = next(
            (
                p
                for p in self.produtos_disponiveis
                if p["id"] == produto_id
            ),
            None,
        )
        unidade = produto["unidade_medida"] if produto else ""

        self.rotulo_saldo.configure(
            text=f"Em armazém: {saldo} {unidade}".strip()
        )

    # -- submissão ---------------------------------------------------

    def _registar(self):
        produto_id = self._produto_id()

        if produto_id is None:
            componentes.mostrar_erro("Escolhe um produto.")
            return

        # Quantidade: pode ser negativa em ajuste, positiva em
        # entrada/saída. A regra fina fica em registar_movimento;
        # aqui só se converte.
        texto_quantidade = self.campo_quantidade.get().strip()

        try:
            quantidade = int(texto_quantidade)
        except ValueError:
            componentes.mostrar_erro(
                "A quantidade tem de ser um número inteiro."
            )
            return

        texto_data = self.campo_data.get().strip()

        try:
            data = datetime.datetime.strptime(
                texto_data, "%d/%m/%Y"
            ).date()
        except ValueError:
            componentes.mostrar_erro(
                "Data inválida (usa dd/mm/aaaa)."
            )
            return

        try:
            estoque.registar_movimento(
                produto_id=produto_id,
                tipo=self.tipo,
                quantidade=quantidade,
                data=data,
                responsavel_id=self._responsavel_id() or "",
                motivo=self.campo_motivo.get().strip(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Movimento de {self.tipo} registado."
        )
        self.destroy()
        self.tela_lista._recarregar()