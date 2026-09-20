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

ALTERAÇÕES 20/09/2026 (Fase 3 — Configurações lidas da BD):

- `import configuracoes` no topo — para ler a chave
  `stock.permitir_envio_parcial`.

- `ResumoAprovacaoModal` ganha o atributo `self.permite_envio_parcial`.
  Quando é False:
  * aparece uma faixa amarela por cima da tabela a avisar;
  * os campos "A enviar" ficam `disabled` (cinzentos, não editáveis);
  * `_quantidades_enviadas` devolve None — o envio é sempre pela
    totalidade pedida.

  A barreira real fica em `estoque.enviar_requisicao` — aqui é
  conforto visual, para o Admin perceber logo que não pode reduzir.
"""

import datetime

import customtkinter as ctk

import configuracoes
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
# FASE 4 — filtros Estado e Tipo da Rota de Envio. Os dois
# primeiros vêm do `gui_est_comum` (já existem lá); o terceiro é
# novo (não havia opção "Todos os tipos" em lado nenhum).
_OPCAO_TODOS_ESTADOS = gui_est_comum.OPCAO_TODOS_ESTADOS
_ESTADOS_REQUISICAO = gui_est_comum.ESTADOS_REQUISICAO
_OPCAO_TODOS_TIPOS = "Todos os tipos"

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


# Colunas da Rota de Envio (Fase 4, 16/09/2026). A ordem segue o
# Mockup 2 validado:
#
# - REQUISIÇÃO: id + data (bloco vertical).
# - TIPO: chip abreviado "Rol" / "Pedido" (azul / cinza).
# - RESPONSÁVEL: nome do dono.
# - OBSERVAÇÕES: texto livre; numa rejeitada, é o motivo.
# - STATUS: chip de estado (pendente/enviada/fechada/rejeitada/cancelada).
# - GERIR: botão.
_COLUNAS_APROVACAO = (
    componentes.Coluna("REQUISIÇÃO", minimo=130, espaco=8),
    componentes.Coluna("TIPO", minimo=90, alinhamento="centro"),
    componentes.Coluna("RESPONSÁVEL", peso=1, minimo=160),
    componentes.Coluna("OBSERVAÇÕES", peso=3, minimo=260),
    componentes.Coluna("STATUS", minimo=110, alinhamento="centro"),
    componentes.Coluna("GERIR", minimo=90, alinhamento="e"),
)


class ListaAprovacao(ctk.CTkFrame):
    """ "Aprovação de Requisições": lista das pendentes, com Gerir por
    linha que abre a tela de resumo para aprovar ou rejeitar.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        # FASE 4 (16/09/2026) — a ListaAprovacao passa a ser a Rota
        # de Envio: mostra TODAS as requisições (não só pendentes),
        # com três filtros e o chip de tipo abreviado na linha.
        # Continua a viver neste ficheiro, com o mesmo nome de
        # classe — o nome interno não aparece ao utilizador.
        componentes.Cabecalho(self, titulo="Stock · Rota de Envio").pack(
            fill="x"
        )

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

        # ---- Filtros: Estado, Tipo, Responsável ----
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=20, pady=(0, 6))

        self.combo_estado = ctk.CTkOptionMenu(
            filtros,
            values=[_OPCAO_TODOS_ESTADOS] + list(_ESTADOS_REQUISICAO),
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_estado.set(_OPCAO_TODOS_ESTADOS)
        self.combo_estado.pack(side="left")

        self.combo_tipo = ctk.CTkOptionMenu(
            filtros,
            values=[_OPCAO_TODOS_TIPOS, "Rol Lavanderia", "Pedido Staff"],
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_tipo.set(_OPCAO_TODOS_TIPOS)
        self.combo_tipo.pack(side="left", padx=(10, 0))

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

        # FASE 4 — o filtro "Responsável" só aparece a Admin/Master.
        # Para Staff, o filtro nem é construído (e o ecrã nem é
        # acessível pelo hub — ver `gui_est_hub.py`).
        tipo_utilizador = sessao.tipo_utilizador_ativo()
        e_administrativo = tipo_utilizador in ("Admin", "Master")

        self.combo_responsavel = None

        if e_administrativo:
            self.combo_responsavel = ctk.CTkOptionMenu(
                filtros,
                values=(
                    [_OPCAO_TODOS_RESPONSAVEIS] + sorted(self.id_por_rotulo)
                ),
                width=240,
                corner_radius=tema.RAIO_CAMPO,
                command=lambda _valor: self._recarregar(),
            )
            self.combo_responsavel.set(_OPCAO_TODOS_RESPONSAVEIS)
            self.combo_responsavel.pack(side="left", padx=(10, 0))

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_APROVACAO,
            altura_linha=52,
            mensagem_vazia="Nenhuma requisição com estes filtros.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _estado_filtro(self):
        """Estado escolhido no filtro, ou None para "todos"."""
        valor = self.combo_estado.get()
        return None if valor == _OPCAO_TODOS_ESTADOS else valor

    def _tipo_filtro(self):
        """Origem escolhida no filtro ("rol" ou "pedido"), ou None.

        No dropdown os rótulos são "Rol Lavanderia" / "Pedido Staff"
        (mais legíveis), mas o `estoque` trabalha com as chaves
        curtas — daí este mapeamento.
        """
        valor = self.combo_tipo.get()

        if valor == "Rol Lavanderia":
            return "rol"

        if valor == "Pedido Staff":
            return "pedido"

        return None

    def _responsavel_filtro(self):
        """ID do responsável filtrado, ou None.

        Devolve None quando o combo não existe (Staff) ou quando
        está em "Todos".
        """
        if self.combo_responsavel is None:
            return None

        return self.id_por_rotulo.get(self.combo_responsavel.get())

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela.

        FASE 4 (16/09/2026) — a Rota de Envio mostra TODAS as
        requisições (não só as pendentes), com três filtros: Estado,
        Tipo e (só para Admin/Master) Responsável. A ordenação
        continua a ser por data do pedido, mais recentes primeiro.
        """
        self.tabela.limpar()

        requisicoes = estoque.listar_requisicoes(
            estado=self._estado_filtro(),
            responsavel_id=self._responsavel_filtro(),
        )

        # O filtro de tipo é aplicado em Python porque `estoque` não
        # o conhece (é `origem` na tabela, mas o módulo de negócio
        # não expõe filtro por origem). Uma lista filtrada é mais
        # simples do que alargar a assinatura de listar_requisicoes
        # só para isto.
        tipo = self._tipo_filtro()

        if tipo is not None:
            requisicoes = [r for r in requisicoes if r["origem"] == tipo]

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

        Estrutura das colunas (Fase 4, 16/09/2026):

        - REQUISIÇÃO: id + data
        - TIPO: chip abreviado "Rol" (azul) / "Pedido" (cinza)
        - RESPONSÁVEL: nome do dono
        - OBSERVAÇÕES: texto livre; numa rejeitada, o motivo
        - STATUS: chip de estado
        - GERIR: botão
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

        # ---- TIPO (chip abreviado) ----
        # "Rol" no chip (azul), "Pedido" (cinza). Os nomes completos
        # ("Rol Lavanderia" / "Pedido Staff") só aparecem no filtro
        # — o chip da coluna tem 90px de largura, e o nome completo
        # não cabe.
        self.tabela.colocar(
            linha,
            1,
            self._chip_tipo(linha, requisicao["origem"]),
        )

        # ---- Responsável ----
        self.tabela.colocar(
            linha,
            2,
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
        texto_obs = requisicao["observacoes"] or "—"
        cor_obs = tema.COR_TEXTO_SECUNDARIO

        if (
            requisicao["estado"] == "rejeitada"
            and requisicao["motivo_rejeicao"]
        ):
            texto_obs = f"motivo: {requisicao['motivo_rejeicao']}"
            cor_obs = tema.TEXTO_ERRO

        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=texto_obs,
                text_color=cor_obs,
                font=ctk.CTkFont(size=11),
                anchor="w",
            ),
        )

        # ---- Status ----
        self.tabela.colocar(
            linha,
            4,
            gui_est_comum.etiqueta_estado(linha, requisicao["estado"]),
        )

        # ---- Gerir ----
        acoes = self.tabela.celula_acoes(linha, 5)
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

    def _chip_tipo(self, master, origem):
        """Devolve o chip do TIPO ("Rol" / "Pedido"). Mesma
        convenção de cores já usada no `gui_est_requisicoes.py`:
        'rol' → azul, 'pedido' → cinza neutro."""
        if origem == "rol":
            texto = "Rol"
            fg_color = tema.ID_CHIP_FUNDO
            text_color = tema.AZUL_PRINCIPAL
        else:
            texto = "Pedido"
            fg_color = tema.CINZA_INDISPONIVEL
            text_color = tema.TEXTO_INDISPONIVEL

        return ctk.CTkLabel(
            master,
            text=texto,
            text_color=text_color,
            fg_color=fg_color,
            corner_radius=8,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=70,
            height=22,
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

    FASE 3 (20/09/2026) — o atributo `self.permite_envio_parcial` é
    lido da chave `stock.permitir_envio_parcial` na abertura do
    modal. Quando é False:
    * aparece uma faixa amarela de aviso por cima da tabela;
    * os campos "A enviar" ficam disabled;
    * `_quantidades_enviadas` devolve None — envio pela totalidade.
    """

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        # FASE 4 (16/09/2026) — o modal já não é só para aprovar.
        # Mostra a ficha em qualquer estado, mas só deixa aprovar/
        # rejeitar quando a requisição está pendente. Os botões, a
        # coluna "A enviar" editável e a nota ao responsável só
        # fazem sentido nesse estado.
        self.e_pendente = requisicao["estado"] == "pendente"

        # FASE 3 (20/09/2026) — o envio parcial é controlado pela
        # chave `stock.permitir_envio_parcial`. Quando está ligada,
        # a coluna "A enviar" é editável (comportamento até agora).
        # Quando está desligada, a coluna passa a ser só de leitura
        # e aparece um aviso por cima da tabela. A barreira real
        # fica em `estoque.enviar_requisicao` — aqui é conforto
        # visual, para o Admin perceber logo que não pode reduzir.
        self.permite_envio_parcial = configuracoes.obter_bool(
            "stock.permitir_envio_parcial"
        )

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

        # FASE 4 (16/09/2026) — altura passa a ser ajustada ao
        # conteúdo, no fim do __init__ (ver `_ajustar_altura`). Antes
        # era fixa em 620px, e com 3+ produtos (ou observação
        # comprida) o rodapé ficava fora da janela — bug apanhado
        # pelo aluno ao testar a REQ-015.
        largura = 640
        altura_inicial = 620

        self.title(f"Aprovar requisição — {requisicao['id']}")
        self.geometry(f"{largura}x{altura_inicial}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura_inicial)
        _colocar_no_topo(self)

        self._construir_cabecalho()
        self._construir_ficha()
        self._construir_tabela()
        self._construir_avisos()
        self._construir_nota()
        self._construir_rodape()
        # Ajusta a altura ao conteúdo real. Com 3+ produtos, ou
        # com observação comprida, o conteúdo excede os 620px
        # iniciais e o rodapé ficava fora da janela.
        self.after(20, self._ajustar_altura)

    def _ajustar_altura(self):
        """Redimensiona o modal à altura que o conteúdo já pede.

        Usa `tkinter.Toplevel.geometry` (a versão de base, não a do
        customtkinter) porque `CTkToplevel.geometry` volta a
        multiplicar o valor pela escala da janela — e o
        `winfo_reqheight()` já vem em pixéis reais, escalados.
        Mesma técnica de `_ajustar_tamanho` em `gui_propriedades.py`
        (ver lição sobre geometria, ficheiro 11).
        """
        import tkinter

        self.update_idletasks()
        largura = 640
        altura = self.winfo_reqheight()

        # Uma folga mínima para o rodapé não colar ao bordo.
        altura = max(altura, 400)

        tkinter.Toplevel.geometry(self, f"{largura}x{altura}")

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

        # FASE 3 (20/09/2026) — aviso só quando o envio parcial
        # está desligado, e só em pendente (é aí que a coluna é
        # editável). Nos outros estados, o aviso não aparece.
        if self.e_pendente and not self.permite_envio_parcial:
            aviso = ctk.CTkFrame(
                self,
                fg_color=tema.AMARELO_AVISO,
                corner_radius=tema.RAIO_CAMPO,
            )
            aviso.pack(fill="x", padx=24, pady=(0, 8))

            ctk.CTkLabel(
                aviso,
                text=(
                    "⚠  O envio parcial está desativado nas "
                    "Configurações → Sistema. A requisição será "
                    "enviada sempre pela totalidade pedida."
                ),
                text_color=tema.TEXTO_AVISO,
                font=ctk.CTkFont(size=11),
                wraplength=560,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=12, pady=8)

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

        # FASE 4 — o cabeçalho muda consoante o estado: em pendente é
        # "A ENVIAR" (editável); nos outros estados é "ENVIADO" (só
        # leitura, mostra o que foi de facto enviado).
        titulo_ultima_coluna = "A ENVIAR" if self.e_pendente else "ENVIADO"

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO_RESUMO),
            ("PEDIDO", _LARGURA_PEDIDO_RESUMO),
            ("EM ARMAZÉM", _LARGURA_ARMAZEM_RESUMO),
            (titulo_ultima_coluna, _LARGURA_ENVIAR_RESUMO),
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

            # "Em armazém" só fica a vermelho em pendente (é aí
            # que o saldo insuficiente importa para decidir);
            # nos outros estados é só informativo.
            cor_saldo = (
                tema.TEXTO_ERRO
                if self.e_pendente and saldo < item["quantidade_pedida"]
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

            if self.e_pendente:
                # Coluna "A enviar" — campo editável, arranca com o
                # valor pedido e pode ser reduzido (envio parcial).
                #
                # FASE 3 (20/09/2026) — quando o envio parcial está
                # desligado (`permite_envio_parcial = False`), o
                # campo aparece disabled: mostra o valor pedido,
                # mas não se pode alterar. O Admin percebe logo que
                # não pode reduzir, sem precisar de tentar e levar
                # com o erro da camada de negócio.
                campo = ctk.CTkEntry(
                    linha,
                    width=_LARGURA_ENVIAR_RESUMO - 20,
                    corner_radius=tema.RAIO_CAMPO,
                    justify="center",
                )
                campo.insert(0, str(item["quantidade_pedida"]))

                if not self.permite_envio_parcial:
                    campo.configure(
                        state="disabled",
                        fg_color=tema.LINHA_ALTERNADA,
                        text_color=tema.COR_TEXTO_SECUNDARIO,
                    )
                else:
                    campo.bind(
                        "<KeyRelease>",
                        lambda _evento, pid=item["produto_id"]: (
                            self._atualizar_avisos(pid)
                        ),
                    )

                campo.pack(side="left")
                self.campos_por_produto[item["produto_id"]] = campo
            else:
                # Coluna "Enviado" — só leitura, mostra o que foi
                # mesmo enviado (o valor gravado em
                # `quantidade_enviada`).
                ctk.CTkLabel(
                    linha,
                    text=str(item["quantidade_enviada"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    width=_LARGURA_ENVIAR_RESUMO,
                    anchor="w",
                ).pack(side="left")

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
        """Nota ao responsável — só faz sentido em pendente (é o
        campo que o admin preenche ao aprovar/rejeitar). Nos outros
        estados, mostra a observação de receção do responsável, se
        houver — é o que interessa ler depois de fechada.
        """
        if self.e_pendente:
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
            return

        # Não-pendente: se houver observação de receção (numa
        # fechada), mostra-a em leitura. Se não houver, não mostra
        # nada — uma caixa vazia não é informação.
        observacao = self.requisicao.get("observacao_rececao") or ""

        if not observacao:
            return

        ctk.CTkLabel(
            self,
            text="Observação de receção",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(12, 4))

        caixa = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        caixa.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            caixa,
            text=observacao,
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=11),
            wraplength=560,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=14, pady=10)

        # Guarda o atributo em falta para o `_quantidades_enviadas`
        # (que só corre em pendente) não falhar ao verificar
        # `self.campo_nota` por engano. Não devia acontecer, mas é
        # defesa.
        self.campo_nota = None

    def _construir_rodape(self):
        """Rodapé do modal — varia consoante o estado.

        Em pendente: dois botões (Rejeitar / Aprovar e enviar).
        Nos outros estados: só um botão "Fechar" (o resumo é só
        leitura).
        """
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(4, 18), side="bottom")

        if not self.e_pendente:
            ctk.CTkButton(
                rodape,
                text="Fechar",
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=self.destroy,
            ).pack(side="right")
            return

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

        FASE 3 (20/09/2026) — quando o envio parcial está
        desligado, nunca passamos quantidades específicas: o
        `estoque.enviar_requisicao` envia pela totalidade pedida
        por omissão. Evita mandar uma estrutura que a camada de
        negócio ia recusar de qualquer forma.

        Levanta ValueError se alguma quantidade estiver inválida
        (não inteira, negativa ou zero) — é apanhado pelo `_aprovar`
        e mostrado com `mostrar_erro`.
        """
        # FASE 3 (20/09/2026) — se o envio parcial está desligado,
        # nunca mandamos quantidades específicas.
        if not self.permite_envio_parcial:
            return None

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