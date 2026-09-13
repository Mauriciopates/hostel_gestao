"""Ecrã de Aprovação de Requisições do módulo Stock.

Ecrã novo, criado em 13/09/2026, quando o fluxo de Stock passou a
ter dois papéis distintos e a lista de Requisições deixou de os
misturar:

- **Requisições** (gui_est_requisicoes.py) — a lista do staff, onde
  cada pessoa pede material, acompanha o estado dos seus pedidos,
  cancela uma pendente antes de ser vista, confirma a receção de
  uma enviada e reporta sobra de uma fechada.

- **Aprovação de Requisições** (este ficheiro) — a lista do admin,
  só com as pendentes, onde se aprova (com envio parcial) ou
  rejeita. Antes de 13/09/2026, estas ações estavam no "Gerir" da
  lista única, misturadas com as do staff — o mesmo botão fazia
  coisas diferentes consoante o estado, e o utilizador tinha de
  saber de cor qual era qual.

Porquê separar em dois ecrãs (decisão tomada em conversa, ao rever
o fluxo com o aluno): a mesma lista servia dois papéis diferentes,
e a ação certa para mim não era a ação certa para ti. Separá-los
torna cada botão legível por si — o "Gerir" da Aprovação só tem
"Aprovar e enviar" e "Rejeitar", o "Gerir" das Requisições só tem
as ações do autor.

Este ecrã só mostra as requisições em estado **pendente** — as que
esperam decisão do admin. As restantes (enviadas, fechadas,
rejeitadas, canceladas) vivem na lista normal de Requisições, onde
cada uma tem o seu próprio "Gerir" com as ações certas.

Estrutura:

- `ListaAprovacao` — lista das pendentes, filtrável por
  responsável. Cada linha tem "Gerir", que abre a tela de resumo.
- `ResumoAprovacaoModal` — a tela de resumo (o "print 3" da
  conversa): ficha do pedido, tabela de produtos com a coluna
  "A enviar" editável, avisos de stock insuficiente, nota ao
  responsável, e os dois botões de decisão.

Segue a mesma disciplina de camadas do resto da GUI (decisão 7):
só fala com `estoque` e `responsaveis` — nunca com `repositorio`
diretamente.

CORREÇÃO 13/09/2026 — alinhamento da coluna ESTADO:

- `_COLUNAS_APROVACAO` tinha `alinhamento="center"` (em inglês) na
  coluna ESTADO. O `_ALINHAMENTOS` do `componentes.py` só conhece
  `"w"`, `"e"` e `"centro"` (em português), e era a única tabela da
  aplicação com este valor — todas as outras já usavam `"centro"`.
  Resultado: `componentes.Tabela` rebentava com `KeyError: 'center'`
  ao desenhar o cabeçalho, e o ecrã de Aprovação não chegava a
  abrir (bug apanhado pelo aluno, 13/09/2026, ao clicar no cartão
  "Aprovação de Requisições" do hub de Stock). Corrigido para
  `"centro"`.
"""

import datetime

import customtkinter as ctk

import estoque
import responsaveis
from . import componentes
from . import gui_est_comum
from . import sessao
from . import tema
from .gui_est_requisicoes import _RejeitarRequisicaoModal

# Aliases dos helpers partilhados — mesma convenção dos outros
# ficheiros do módulo Stock.
_OPCAO_TODOS_RESPONSAVEIS = gui_est_comum.OPCAO_TODOS_RESPONSAVEIS
_LARGURA_PRODUTO = gui_est_comum.LARGURA_PRODUTO
_LARGURA_ARMAZEM = gui_est_comum.LARGURA_ARMAZEM
_LARGURA_PEDIDO = gui_est_comum.LARGURA_PEDIDO

_rotulo_responsavel = gui_est_comum.rotulo_responsavel

_colocar_no_topo = componentes.colocar_no_topo
_centrar_sobre = componentes.centrar_sobre

# Larguras da grelha de produtos dentro do resumo — diferentes das
# do `gui_est_comum` porque aqui há a coluna "A enviar" editável a
# mais, e porque a janela é mais larga (modal isolado, não tabela).
_LARGURA_PRODUTO_RESUMO = 220
_LARGURA_PEDIDO_RESUMO = 80
_LARGURA_ARMAZEM_RESUMO = 100
_LARGURA_ENVIAR_RESUMO = 100


_COLUNAS_APROVACAO = (
    componentes.Coluna("REQUISIÇÃO", minimo=130, espaco=8),
    componentes.Coluna("RESPONSÁVEL", peso=1, minimo=180),
    componentes.Coluna("OBSERVAÇÕES", peso=3, minimo=280),
    componentes.Coluna("ESTADO", minimo=110, alinhamento="centro"),
    componentes.Coluna("GERIR", minimo=90, alinhamento="e"),
)


class ListaAprovacao(ctk.CTkFrame):
    """ "Aprovação de Requisições": lista das pendentes, com Gerir por
    linha que abre a tela de resumo para aprovar ou rejeitar.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(
            self, titulo="Stock · Aprovação de Requisições"
        ).pack(fill="x")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 8))

        ctk.CTkButton(
            barra,
            text="< Voltar ao Stock",
            width=140,
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=lambda: controlador.mostrar_frame(
                __import__("gui.gui_est_hub", fromlist=["EcraStock"]).EcraStock
            ),
        ).pack(side="left")

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=20, pady=(0, 6))

        self.responsaveis_disponiveis = responsaveis.listar(
            incluir_inativos=True
        )
        self.id_por_rotulo = {
            _rotulo_responsavel(r): r["id"]
            for r in self.responsaveis_disponiveis
        }
        self.nomes_por_id = {
            r["id"]: r["nome"] for r in self.responsaveis_disponiveis
        }

        self.combo_responsavel = ctk.CTkOptionMenu(
            filtros,
            values=([_OPCAO_TODOS_RESPONSAVEIS] + sorted(self.id_por_rotulo)),
            width=240,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_responsavel.set(_OPCAO_TODOS_RESPONSAVEIS)
        self.combo_responsavel.pack(side="left")

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_APROVACAO,
            altura_linha=52,
            mensagem_vazia="Não há requisições pendentes de aprovação.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _responsavel_filtro(self):
        return self.id_por_rotulo.get(self.combo_responsavel.get())

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela, só com as pendentes.

        Ordenação: mais recentes primeiro (mesma convenção da lista
        geral) — o que chegou hoje interessa mais do que o que
        chegou há uma semana.
        """
        self.tabela.limpar()

        requisicoes = estoque.listar_requisicoes(
            estado="pendente",
            responsavel_id=self._responsavel_filtro(),
        )
        requisicoes.sort(
            key=lambda r: (
                r["data_pedido"] is not None,
                r["data_pedido"] or datetime.date.min,
            ),
            reverse=True,
        )

        if not requisicoes:
            self.tabela.mostrar_vazio()
            return

        for requisicao in requisicoes:
            self._desenhar_linha(requisicao)

    def _desenhar_linha(self, requisicao):
        """Desenha uma linha da tabela.

        Estrutura das colunas: id + data, responsável, observações,
        chip de estado, botão "Gerir". Sem a lista de produtos na
        coluna do meio — essa informação está no resumo, e aqui só
        fazia ruído (é o mesmo que já se decidiu na lista de
        Requisições).
        """
        linha = self.tabela.nova_linha()

        # ---- Requisição (id + data) ----
        coluna_id = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            coluna_id,
            text=requisicao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        data = requisicao["data_pedido"]
        ctk.CTkLabel(
            coluna_id,
            text=data.strftime("%d/%m/%Y") if data else "sem data",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 0, coluna_id)

        # ---- Responsável ----
        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=self.nomes_por_id.get(
                    requisicao["responsavel_id"],
                    requisicao["responsavel_id"],
                ),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ),
        )

        # ---- Observações ----
        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=requisicao["observacoes"] or "—",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                anchor="w",
            ),
        )

        # ---- Estado ----
        self.tabela.colocar(
            linha,
            3,
            gui_est_comum.etiqueta_estado(linha, requisicao["estado"]),
        )

        # ---- Gerir ----
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
                command=lambda: ResumoAprovacaoModal(self, requisicao),
            )
        )


class ResumoAprovacaoModal(ctk.CTkToplevel):
    """Tela de resumo antes de aprovar (ou rejeitar) uma requisição.

    O "print 3" da conversa com o aluno: mostra a ficha do pedido,
    a tabela de produtos com uma coluna "A enviar" editável, os
    avisos de stock insuficiente (um por produto em falta, dentro de
    uma faixa amarela) e uma nota ao responsável (opcional). No
    rodapé, os dois botões de decisão.

    Substitui a antiga combinação de `messagebox` (Sim/Não) +
    "Confirmar requisição" que existia na lista — ninguém decidia
    com informação suficiente, porque nunca via os produtos.

    Não é editável depois de confirmado: assim que se clica em
    "Aprovar e enviar", o `estoque.enviar_requisicao` gera os
    movimentos de saída e a requisição passa a `enviada`. Se algum
    valor ficou mal, o caminho é um movimento de ajuste (decisão 9),
    não uma edição à requisição.
    """

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        # Lê o que a requisição pediu, e o saldo atual de cada
        # produto. Os dois números ficam guardados porque a coluna
        # "Em armazém" é só de leitura (o saldo não muda de abrir
        # para fechar o modal), e a coluna "A enviar" começa com o
        # valor pedido — mas o utilizador pode baixá-lo para envio
        # parcial.
        self.itens = estoque.listar_itens_requisicao(
            requisicao_id=requisicao["id"]
        )
        self.produtos_por_id = {
            p["id"]: p for p in estoque.listar_produtos(incluir_inativos=True)
        }
        self.saldos_por_produto = {
            item["produto_id"]: estoque.saldo_produto(item["produto_id"])
            for item in self.itens
        }
        self.campos_por_produto = {}

        largura, altura = 640, 620
        self.title(f"Aprovar requisição — {requisicao['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        self._construir_cabecalho()
        self._construir_ficha()
        self._construir_tabela()
        self._construir_avisos()
        self._construir_nota()
        self._construir_rodape()

    # -- construção --------------------------------------------------

    def _construir_cabecalho(self):
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=24, pady=(20, 4))

        ctk.CTkLabel(
            cabecalho,
            text=f"Aprovar requisição — {self.requisicao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")

        gui_est_comum.etiqueta_estado(
            cabecalho, self.requisicao["estado"]
        ).pack(side="right")

    def _construir_ficha(self):
        """Cartão com a ficha do pedido (responsável, data,
        observações)."""
        cartao = ctk.CTkFrame(
            self,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", padx=24, pady=(8, 12))

        corpo = ctk.CTkFrame(cartao, fg_color="transparent")
        corpo.pack(fill="x", padx=16, pady=12)

        nome = self.tela_lista.nomes_por_id.get(
            self.requisicao["responsavel_id"],
            self.requisicao["responsavel_id"],
        )

        self._linha_ficha(corpo, "Responsável", nome)

        if self.requisicao["data_pedido"]:
            self._linha_ficha(
                corpo,
                "Pedido em",
                self.requisicao["data_pedido"].strftime("%d/%m/%Y"),
            )

        if self.requisicao["observacoes"]:
            self._linha_ficha(
                corpo, "Observações", self.requisicao["observacoes"]
            )

    def _linha_ficha(self, master, rotulo, valor):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", pady=2)

        ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            width=130,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=valor,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=440,
        ).pack(side="left", fill="x", expand=True)

    def _construir_tabela(self):
        ctk.CTkLabel(
            self,
            text="PRODUTOS",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(0, 6))

        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=24)

        cabecalho = ctk.CTkFrame(
            cartao, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO_RESUMO),
            ("PEDIDO", _LARGURA_PEDIDO_RESUMO),
            ("EM ARMAZÉM", _LARGURA_ARMAZEM_RESUMO),
            ("A ENVIAR", _LARGURA_ENVIAR_RESUMO),
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

        for item in self.itens:
            produto = self.produtos_por_id.get(item["produto_id"])
            nome_produto = produto["nome"] if produto else item["produto_id"]
            saldo = self.saldos_por_produto[item["produto_id"]]

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome_produto,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PRODUTO_RESUMO,
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_pedida"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PEDIDO_RESUMO,
                anchor="w",
            ).pack(side="left")

            # "Em armazém" a vermelho quando o saldo é insuficiente
            # para o que foi pedido — a faixa amarela abaixo também
            # o dirá por extenso, mas o número vermelho ajuda a
            # localizar o produto certo na linha.
            cor_saldo = (
                tema.TEXTO_ERRO
                if saldo < item["quantidade_pedida"]
                else tema.COR_TEXTO_SECUNDARIO
            )
            ctk.CTkLabel(
                linha,
                text=str(saldo),
                text_color=cor_saldo,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_ARMAZEM_RESUMO,
                anchor="w",
            ).pack(side="left")

            # Campo "A enviar" — arranca com o valor pedido, mas
            # editável para baixo (envio parcial). Nunca aceita
            # mais do que o pedido nem mais do que o saldo; a
            # validação fina fica em `_quantidades_enviadas`, aqui
            # só se limita o número a um inteiro.
            campo = ctk.CTkEntry(
                linha,
                width=_LARGURA_ENVIAR_RESUMO - 20,
                corner_radius=tema.RAIO_CAMPO,
                justify="center",
            )
            campo.insert(0, str(item["quantidade_pedida"]))
            campo.pack(side="left")
            # Atualiza a faixa amarela a cada tecla: o aviso tem de
            # acompanhar o que está escrito, não só o que já foi
            # submetido (mesma convenção de `_LinhaProduto`).
            campo.bind(
                "<KeyRelease>",
                lambda _evento, pid=item["produto_id"]: self._atualizar_avisos(
                    pid
                ),
            )
            self.campos_por_produto[item["produto_id"]] = campo

    def _construir_avisos(self):
        """Faixa amarela com os avisos de stock insuficiente.

        Recriada a cada tecla (o `_atualizar_avisos` destrói os
        filhos e volta a montar), em vez de mostrar/esconder uma
        caixa fixa: os avisos são por produto, e um produto pode
        entrar e sair da lista conforme o utilizador mexe nas
        quantidades.
        """
        self.caixa_avisos = ctk.CTkFrame(self, fg_color="transparent")
        self.caixa_avisos.pack(fill="x", padx=24, pady=(10, 0))

        self._atualizar_avisos()

    def _atualizar_avisos(self, _produto_id=None):
        for filho in self.caixa_avisos.winfo_children():
            filho.destroy()

        avisos = self._avisos_stock()

        if not avisos:
            return

        faixa = ctk.CTkFrame(
            self.caixa_avisos,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        faixa.pack(fill="x")

        ctk.CTkLabel(
            faixa,
            text="\n".join(avisos),
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=11),
            wraplength=560,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=8)

    def _avisos_stock(self):
        """Frases a mostrar na faixa amarela, uma por produto em
        falta.

        Um produto está "em falta" quando a quantidade que se está a
        tentar enviar (o valor atual do campo "A enviar") é maior do
        que o saldo em armazém. Produtos com saldo suficiente não
        geram aviso nenhum.

        Quantidades inválidas (não inteiras, vazias, zero ou
        negativas) são ignoradas — o campo está a ser editado, e
        não é aqui que isso se valida; a validação fina fica no
        `_quantidades_enviadas`, na submissão.
        """
        avisos = []

        for item in self.itens:
            produto_id = item["produto_id"]
            produto = self.produtos_por_id.get(produto_id)
            nome = produto["nome"] if produto else produto_id
            unidade = produto["unidade_medida"] if produto else ""

            texto = self.campos_por_produto[produto_id].get().strip()

            if not texto.isdigit():
                continue

            quantidade = int(texto)

            if quantidade <= 0:
                continue

            saldo = self.saldos_por_produto[produto_id]

            if quantidade <= saldo:
                continue

            avisos.append(
                f"{nome}: só existem {saldo} {unidade} dos "
                f"{item['quantidade_pedida']} pedidos. Enviando "
                f"{quantidade}, ficam "
                f"{item['quantidade_pedida'] - quantidade} em falta."
            )

        return avisos

    def _construir_nota(self):
        """Nota ao responsável (opcional) — texto livre que fica
        gravado na requisição, para o autor ver no detalhe.
        """
        ctk.CTkLabel(
            self,
            text="Nota ao responsável (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(12, 4))

        self.campo_nota = ctk.CTkTextbox(
            self, height=60, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_nota.pack(fill="x", padx=24, pady=(0, 12))

    def _construir_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(4, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Rejeitar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._rejeitar,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Aprovar e enviar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._aprovar,
        ).pack(side="right")

    # -- submissão ---------------------------------------------------

    def _quantidades_enviadas(self):
        """Lê a coluna "A enviar" e devolve o dicionário no formato
        que `estoque.enviar_requisicao` espera — ou None se o
        utilizador não mexeu em nada.

        O None significa "envia tudo pela quantidade pedida": é o
        que o `enviar_requisicao` faz por omissão, e é o caminho
        normal. Só quando alguém mexe numa quantidade é que o
        dicionário ganha entradas.

        Levanta ValueError se alguma quantidade estiver inválida
        (não inteira, negativa ou zero) — é apanhado pelo `_aprovar`
        e mostrado com `mostrar_erro`.
        """
        quantidades = {}
        mexeu_em_alguma = False

        for item in self.itens:
            produto_id = item["produto_id"]
            texto = self.campos_por_produto[produto_id].get().strip()

            if not texto.isdigit():
                raise ValueError(f"Quantidade inválida em '{produto_id}'.")

            quantidade = int(texto)

            if quantidade <= 0:
                raise ValueError(
                    f"A quantidade a enviar de '{produto_id}' tem de "
                    f"ser positiva."
                )

            if quantidade > item["quantidade_pedida"]:
                raise ValueError(
                    f"A quantidade a enviar de '{produto_id}' não "
                    f"pode exceder a quantidade pedida."
                )

            if quantidade != item["quantidade_pedida"]:
                mexeu_em_alguma = True

            quantidades[produto_id] = quantidade

        if not mexeu_em_alguma:
            return None

        return quantidades

    def _aprovar(self):
        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            quantidades = self._quantidades_enviadas()
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            estoque.enviar_requisicao(
                self.requisicao["id"],
                ativo["id"],
                datetime.date.today(),
                quantidades_enviadas=quantidades,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição {self.requisicao['id']} aprovada e enviada."
        )
        self.destroy()
        self.tela_lista._recarregar()

    def _rejeitar(self):
        """Abre o modal de rejeição (motivo obrigatório) — modal
        que vive em `gui_est_requisicoes.py`, importado no topo.
        """
        self.destroy()
        _RejeitarRequisicaoModal(self.tela_lista, self.requisicao)
