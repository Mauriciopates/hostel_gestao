"""Ecrã de Requisições do módulo Stock.

Extraído do antigo `gui_estoque.py` em 10/09/2026, quando o módulo
Stock passou a ter cinco ficheiros focados (`gui_est_hub.py` e os
quatro `gui_est_<área>.py`). Sem alterações de comportamento — a
única diferença é que as constantes e os helpers partilhados (cores
de estado, rótulos, larguras, `_itens_disponiveis_devolucao`,
`_texto_produtos_*`) passaram a vir de `gui_est_comum`, e os
helpers genéricos (colocar popups, centrar, tornar clicável) de
`componentes`.

ALTERAÇÕES 13/09/2026 (fluxo com Aprovação de Requisições):

- `_AcoesRequisicaoModal` (que fazia tudo: confirmar, rejeitar,
  confirmar receção, reportar sobra) foi substituído por três
  modais específicos, cada um com a sua única ação possível:

  * `_AcoesRequisicaoPendenteModal` — só "Cancelar requisição"
    (o autor desiste antes de o admin ver).
  * `_ConfirmarRececaoModal` — tela de resumo do que foi enviado
    (só leitura) + campo de observação de receção, onde o
    responsável informa faltas. Não mexe no stock.
  * `_AcoesRequisicaoFechadaModal` — só "Reportar sobra".

  As ações do admin (aprovar, rejeitar) saíram daqui e passaram
  para `gui_est_aprovacao.py`, no ecrã próprio de Aprovação de
  Requisições.

- A lista ganha duas marcas visuais na coluna de estado:
  * Chip "rol lavanderia" ao lado do estado, quando `origem ==
    "rol"` (requisição criada pelo admin, não pedida pelo staff).
  * Aviso amarelo "obs. receção" ao lado do estado, quando
    `estado == "fechada"` e há observação de receção não vazia —
    o admin sabe quais as requisições fechadas a que vale a pena
    ir ler a observação.

- A coluna "Responsável e produtos" foi desdobrada: o nome do
  responsável fica na coluna própria, e a antiga lista de produtos
  dá lugar à coluna "Observações" (mostra o `observacoes` da
  requisição, não os produtos). Decisão do aluno: a lista de
  produtos resumida era ruído — quem quer ver produtos abre o
  Gerir e vê-os lá.

- O `RolLavanderiaModal` passa a criar a requisição com
  `origem="rol"` — o único ponto que mudou neste formulário.

CORREÇÃO 13/09/2026 — três bugs apanhados ao testar o ecrã:

- Linha 90: `_tornar_clicavel = componentes.tornar_cliclavel`
  estava escrito `componentes.tornar_cliclavel` (com um "l" a
  menos). O nome certo da função em `componentes.py` é
  `tornar_cliclavel`. Rebentava com `AttributeError` ao importar
  o ficheiro, e isso quebrava toda a cadeia de imports da GUI
  (o `gui_est_hub.py` importa este ficheiro, e o `app.py` importa
  o hub). Corrigido.

- `ListaRequisicoes._desenhar_linha` criava o `bloco_estado` (a
  célula com o chip de estado + as marcas "rol lavanderia" / "obs.
  receção") com `pack_propagate(False)` mas **sem `height`
  explícita**. Sem altura, um `CTkFrame` assume 200px por omissão,
  e o `pack_propagate(False)` impede-o de encolher até ao tamanho
  dos chips lá dentro — a linha inteira da tabela esticava até aos
  200px, e o resultado era o espaçamento vertical enorme entre as
  requisições (visível no print do aluno, 13/09/2026). Corrigido
  com `height=26` (a altura de um chip de estado, `height=22`, mais
  uma folga pequena).

- Faltavam dois métodos auxiliares na `ListaRequisicoes`:

  * `_e_o_autor(requisicao)` — usado pelo
    `_AcoesRequisicaoPendenteModal` (só o autor pode cancelar) e
    pelo `_AcoesRequisicaoFechadaModal` (só o autor pode reportar
    sobra). Sem ele, abrir o Gerir de uma requisição pendente
    rebentava com `AttributeError`.
  * `_pode_reportar_devolucao(requisicao)` — usado pelo
    `_AcoesRequisicaoFechadaModal` para decidir se mostra o botão
    "Reportar sobra". Sem ele, abrir o Gerir de uma requisição
    fechada rebentava com `AttributeError` (bug apanhado pelo
    aluno, 13/09/2026).

  Os dois modais chamavam estes métodos à `tela_lista` desde o
  primeiro dia, mas nunca tinham sido escritos — só rebentaram
  quando o ecrã de Aprovação de Requisições abriu e a cadeia de
  cliques chegou a estes modais. Corrigido: os dois métodos vivem
  agora na `ListaRequisicoes`, antes do `_recarregar`.

Inclui:

- `ListaRequisicoes` — tabela de requisições, com Gerir por linha
- `_AcoesRequisicaoPendenteModal`, `_ConfirmarRececaoModal`,
  `_AcoesRequisicaoFechadaModal` — popups de ação da requisição
- `_RejeitarRequisicaoModal` — mantido, mas migra para uso do
  `gui_est_aprovacao.py` (fica aqui para não duplicar)
- `ReportarDevolucaoModal` — popup de reportar sobra
- `_EscolherTipoRequisicaoModal`, `NovaRequisicaoModal`,
  `RolLavanderiaModal`, `_LinhaProduto` — criação de requisições
"""

import datetime

import customtkinter as ctk

import estoque
import responsaveis
from . import componentes
from . import gui_est_comum
from . import sessao
from . import tema


# Aliases dos helpers partilhados — os nomes antigos locais eram
# usados no corpo das classes extraídas do gui_estoque.py; estes
# aliases evitam ter de reescrever todas as chamadas no corpo.
_CORES_ESTADO = gui_est_comum.CORES_ESTADO
_OPCAO_TODOS_ESTADOS = gui_est_comum.OPCAO_TODOS_ESTADOS
_OPCAO_TODOS_RESPONSAVEIS = gui_est_comum.OPCAO_TODOS_RESPONSAVEIS
_ESTADOS_REQUISICAO = gui_est_comum.ESTADOS_REQUISICAO
_LARGURA_PRODUTO = gui_est_comum.LARGURA_PRODUTO
_LARGURA_ARMAZEM = gui_est_comum.LARGURA_ARMAZEM
_LARGURA_PEDIDO = gui_est_comum.LARGURA_PEDIDO

_etiqueta_estado = gui_est_comum.etiqueta_estado
_rotulo_responsavel = gui_est_comum.rotulo_responsavel
_rotulo_produto = gui_est_comum.rotulo_produto
_texto_produtos_requisicao = gui_est_comum.texto_produtos_requisicao
_itens_disponiveis_devolucao = gui_est_comum.itens_disponiveis_devolucao

_colocar_no_topo = componentes.colocar_no_topo
_centrar_sobre = componentes.centrar_sobre
_tornar_clicavel = componentes.tornar_cliclavel


# Altura extra que o popup de Reportar devolução precisa quando a
# lista de itens disponíveis é grande — cada linha extra soma 36px.
_ALTURA_LINHA_ITEM = 40

# Largura do popup de "Gerir".
_LARGURA_POPUP_ACOES = 340

_COLUNAS_REQUISICAO = (
    componentes.Coluna("REQUISIÇÃO", minimo=130, espaco=8),
    componentes.Coluna("RESPONSÁVEL", peso=1, minimo=160),
    componentes.Coluna("OBSERVAÇÕES", peso=2, minimo=240),
    componentes.Coluna("ESTADO", minimo=200, alinhamento="centro"),
    componentes.Coluna("GERIR", minimo=90, alinhamento="e"),
)


class ListaRequisicoes(ctk.CTkFrame):
    """Lista das requisições, filtrável por estado e responsável."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Stock · Requisições").pack(
            fill="x"
        )

        # Botão de criação numa barra própria, logo abaixo do
        # cabeçalho e a verde — mesmo padrão de Contrato Mensal e
        # Reservas Airbnb (09/09/2026).
        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Nova requisição",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _EscolherTipoRequisicaoModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 6))

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
            values=[_OPCAO_TODOS_ESTADOS] + list(_ESTADOS_REQUISICAO),
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_estado.set(_OPCAO_TODOS_ESTADOS)
        self.combo_estado.pack(side="left")

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
        self.combo_responsavel.pack(side="left", padx=(10, 0))

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_REQUISICAO,
            altura_linha=52,
            mensagem_vazia="Nenhuma requisição com estes filtros.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _estado_filtro(self):
        valor = self.combo_estado.get()

        return None if valor == _OPCAO_TODOS_ESTADOS else valor

    def _responsavel_filtro(self):
        return self.id_por_rotulo.get(self.combo_responsavel.get())

    def _e_o_autor(self, requisicao):
        """Diz se o responsável ativo da sessão é o autor da
        requisição.

        Usado pelo `_AcoesRequisicaoPendenteModal` (só o autor pode
        cancelar) e pelo `_AcoesRequisicaoFechadaModal` (só o autor
        pode reportar sobra) — as duas ações são do dono do pedido,
        não do admin.

        Sem sessão definida, devolve False: sem responsável ativo,
        não há autor a quem atribuir a ação. Mesma convenção dos
        outros sítios que dependem da sessão.
        """
        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            return False

        return ativo["id"] == requisicao["responsavel_id"]

    def _pode_reportar_devolucao(self, requisicao):
        """Diz se ainda faz sentido mostrar "Reportar sobra" a esta
        requisição — só quando é o autor a olhar para ela E ainda há
        itens por devolver.

        A segunda condição usa `gui_est_comum.itens_disponiveis_devolucao`,
        que é a mesma função que o `ReportarDevolucaoModal` usa para
        montar a lista de produtos — as duas leem a mesma regra, por
        isso nunca podem discordar.

        Requisições que não estão fechadas devolvem False (a
        devolução só nasce de uma requisição fechada), mas isso não
        devia acontecer aqui — este modal só é aberto nesse estado.
        """
        if requisicao["estado"] != "fechada":
            return False

        if not self._e_o_autor(requisicao):
            return False

        return bool(_itens_disponiveis_devolucao(requisicao["id"]))

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela de requisições."""
        self.tabela.limpar()

        requisicoes = estoque.listar_requisicoes(
            estado=self._estado_filtro(),
            responsavel_id=self._responsavel_filtro(),
        )
        # Mais recentes primeiro. 'data_pedido' pode ser None num
        # registo antigo, e comparar None com date rebenta — daí o
        # par (tem_data, data) como chave.
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

        Estrutura de colunas desde 13/09/2026:

        - REQUISIÇÃO: id + data
        - RESPONSÁVEL: nome do dono
        - OBSERVAÇÕES: `observacoes` da requisição (texto livre)
        - ESTADO: chip + (eventuais) marcas — "rol lavanderia" e/ou
          "obs. receção"
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
        texto_obs = requisicao["observacoes"] or "—"
        cor_obs = (
            tema.TEXTO_ERRO
            if requisicao["estado"] == "rejeitada"
            and requisicao["motivo_rejeicao"]
            else tema.COR_TEXTO_SECUNDARIO
        )
        # Numa rejeitada, a coluna "Observações" passa a mostrar o
        # motivo da rejeição — é o que interessa nesse estado, e os
        # produtos/observações já não vão a lado nenhum.
        if requisicao["estado"] == "rejeitada" and requisicao["motivo_rejeicao"]:
            texto_obs = f"motivo: {requisicao['motivo_rejeicao']}"

        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=texto_obs,
                text_color=cor_obs,
                font=ctk.CTkFont(size=11),
                anchor="w",
            ),
        )

        # ---- Estado (chip + marcas) ----
        # O `height=26` é obrigatório: sem ele, o `CTkFrame` assume
        # 200px de altura por omissão, e o `pack_propagate(False)`
        # impede o frame de encolher até ao tamanho dos chips que
        # estão lá dentro — a linha inteira da tabela estica até
        # aos 200px, e o resultado é o espaçamento vertical enorme
        # entre as requisições (bug apanhado pelo aluno, 13/09/2026).
        # 26 é a altura de um chip de estado (`height=22` no
        # `gui_est_comum.etiqueta_estado`) mais uma folga pequena.
        bloco_estado = ctk.CTkFrame(
            linha, fg_color="transparent", height=26
        )
        bloco_estado.pack_propagate(False)

        _etiqueta_estado(bloco_estado, requisicao["estado"]).pack(
            side="left"
        )

        if requisicao["origem"] == "rol":
            ctk.CTkLabel(
                bloco_estado,
                text="rol lavanderia",
                text_color=tema.AZUL_PRINCIPAL,
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=tema.RAIO_CAMPO,
                font=ctk.CTkFont(size=10, weight="bold"),
                padx=8,
                pady=2,
            ).pack(side="left", padx=(6, 0))

        if (
            requisicao["estado"] == "fechada"
            and requisicao["observacao_rececao"]
        ):
            ctk.CTkLabel(
                bloco_estado,
                text="obs. receção",
                text_color=tema.TEXTO_AVISO,
                fg_color=tema.AMARELO_AVISO,
                corner_radius=tema.RAIO_CAMPO,
                font=ctk.CTkFont(size=10, weight="bold"),
                padx=8,
                pady=2,
            ).pack(side="left", padx=(6, 0))

        self.tabela.colocar(linha, 3, bloco_estado)

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
                command=lambda: self._abrir_gerir(requisicao),
            )
        )

    # -- abertura do Gerir -----------------------------------------

    def _abrir_gerir(self, requisicao):
        """Abre o modal de ações certo para o estado da requisição.

        Cada estado tem o seu modal — evita um único modal com
        metade dos botões escondidos por `if`, e cada modal mostra
        só o que faz sentido:

        - pendente → `_AcoesRequisicaoPendenteModal` (só cancelar)
        - enviada → `_ConfirmarRececaoModal` (só confirmar)
        - fechada → `_AcoesRequisicaoFechadaModal` (só reportar sobra)
        - rejeitada → `_AcoesRequisicaoRejeitadaModal` (só ler)
        - cancelada → `_AcoesRequisicaoRejeitadaModal` (só ler, com
          texto próprio)
        """
        estado = requisicao["estado"]

        if estado == "pendente":
            _AcoesRequisicaoPendenteModal(self, requisicao)
        elif estado == "enviada":
            _ConfirmarRececaoModal(self, requisicao)
        elif estado == "fechada":
            _AcoesRequisicaoFechadaModal(self, requisicao)
        else:
            # rejeitada / cancelada — sem ação, só leitura.
            _AcoesRequisicaoRejeitadaModal(self, requisicao)


class _AcoesRequisicaoPendenteModal(ctk.CTkToplevel):
    """Popup de "Gerir" de uma requisição pendente — só "Cancelar
    requisição". O autor desiste antes de o admin a ver."""

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        altura = 220
        self.title(f"Gerir — {requisicao['id']}")
        self.geometry(f"{_LARGURA_POPUP_ACOES}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, _LARGURA_POPUP_ACOES, altura)
        _colocar_no_topo(self)

        nome = tela_lista.nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )
        ctk.CTkLabel(
            self,
            text=requisicao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=f"{nome} · pendente",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        # Só o autor pode cancelar. Se não for ele, esconde a ação
        # e diz porquê — sem isto, o botão aparecia sempre e o
        # `cancelar_requisicao` recusava a seguir, com um erro que
        # o utilizador não conseguia ligar a nada.
        if tela_lista._e_o_autor(requisicao):
            self._botao(
                "Cancelar requisição",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=self._cancelar,
            )
        else:
            ctk.CTkLabel(
                self,
                text=(
                    "Só o responsável que pediu pode cancelar esta "
                    "requisição."
                ),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                wraplength=280,
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

    def _botao(self, texto, text_color, hover_color, acao):
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

    def _cancelar(self):
        if not componentes.confirmar(
            f"Cancelar a requisição {self.requisicao['id']}?\n\n"
            "Deixa de estar pendente de aprovação — se te enganaste em "
            "algum item, podes criar uma nova a seguir.",
            titulo="Cancelar requisição",
        ):
            return

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            estoque.cancelar_requisicao(
                self.requisicao["id"], ativo["id"]
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição {self.requisicao['id']} cancelada."
        )
        self.tela_lista._recarregar()


class _AcoesRequisicaoRejeitadaModal(ctk.CTkToplevel):
    """Popup de "Gerir" de uma requisição rejeitada ou cancelada —
    só leitura, com o motivo/observação."""

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        altura = 240
        self.title(f"Gerir — {requisicao['id']}")
        self.geometry(f"{_LARGURA_POPUP_ACOES}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, _LARGURA_POPUP_ACOES, altura)
        _colocar_no_topo(self)

        nome = tela_lista.nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )
        ctk.CTkLabel(
            self,
            text=requisicao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=f"{nome} · {requisicao['estado']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if requisicao["estado"] == "rejeitada":
            texto = (
                f"Rejeitada: {requisicao['motivo_rejeicao'] or '—'}"
            )
        else:
            texto = "Cancelada pelo autor — sem ações disponíveis."

        ctk.CTkLabel(
            self,
            text=texto,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            wraplength=280,
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


class _AcoesRequisicaoFechadaModal(ctk.CTkToplevel):
    """Popup de "Gerir" de uma requisição fechada — só "Reportar
    sobra", que cria uma devolução pendente."""

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        altura = 240
        self.title(f"Gerir — {requisicao['id']}")
        self.geometry(f"{_LARGURA_POPUP_ACOES}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, _LARGURA_POPUP_ACOES, altura)
        _colocar_no_topo(self)

        nome = tela_lista.nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )
        ctk.CTkLabel(
            self,
            text=requisicao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=f"{nome} · fechada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        # Só o autor pode reportar sobra; se já não houver itens
        # disponíveis, também não mostra o botão. Mesma lógica de
        # hoje (`_pode_reportar_devolucao`), mas agora dentro do
        # modal certo.
        if tela_lista._pode_reportar_devolucao(requisicao):
            def executar():
                self.destroy()
                ReportarDevolucaoModal(tela_lista, requisicao)

            ctk.CTkButton(
                self,
                text="Reportar sobra",
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
                text=(
                    "Sem sobra por reportar — ou já foi reportada "
                    "toda, ou a requisição não é tua."
                ),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                wraplength=280,
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


class _ConfirmarRececaoModal(ctk.CTkToplevel):
    """Popup de "Gerir" de uma requisição enviada — resumo do que
    foi enviado (só leitura) + observação de receção.

    Substitui o antigo `_AcoesRequisicaoModal` neste estado (que só
    tinha um botão "Confirmar receção" que abria um `messagebox`
    Sim/Não). O novo mostra a ficha toda: o que foi pedido, o que
    foi enviado, quem enviou, quando — e um campo de texto livre
    para o responsável informar faltas, se as houve.

    Não mexe no stock: confirmar receção é só mudar o estado para
    `fechada`; a observação fica gravada para o admin ler depois.
    """

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        # Recupera o que foi enviado item a item. O envio parcial
        # pode ter deixado `quantidade_enviada` abaixo da pedida —
        # o responsável tem de ver os dois números, para saber
        # exatamente o que está a confirmar.
        self.itens = estoque.listar_itens_requisicao(
            requisicao_id=requisicao["id"]
        )
        self.produtos_por_id = {
            p["id"]: p
            for p in estoque.listar_produtos(incluir_inativos=True)
        }

        largura, altura = 560, 560
        self.title(f"Confirmar receção — {requisicao['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        # ---- Cabeçalho ----
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=24, pady=(20, 12))

        ctk.CTkLabel(
            topo,
            text=f"Confirmar receção — {requisicao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")

        _etiqueta_estado(topo, requisicao["estado"]).pack(
            side="right"
        )

        # ---- Ficha ----
        ficha = ctk.CTkFrame(
            self,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        ficha.pack(fill="x", padx=24, pady=(0, 12))

        corpo_ficha = ctk.CTkFrame(ficha, fg_color="transparent")
        corpo_ficha.pack(fill="x", padx=16, pady=12)

        nome = tela_lista.nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )

        self._linha_ficha(corpo_ficha, "Responsável", nome)

        if requisicao["data_pedido"]:
            self._linha_ficha(
                corpo_ficha,
                "Pedido em",
                requisicao["data_pedido"].strftime("%d/%m/%Y"),
            )

        if requisicao["data_envio"]:
            self._linha_ficha(
                corpo_ficha,
                "Enviado em",
                requisicao["data_envio"].strftime("%d/%m/%Y"),
            )

        # ---- Produtos enviados ----
        ctk.CTkLabel(
            self,
            text="PRODUTOS ENVIADOS",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(4, 6))

        self._construir_tabela_produtos()

        # ---- Observação de receção ----
        ctk.CTkLabel(
            self,
            text="Observação de receção (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(12, 4))

        self.campo_observacao = ctk.CTkTextbox(
            self, height=70, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_observacao.pack(fill="x", padx=24, pady=(0, 8))

        ctk.CTkLabel(
            self,
            text=(
                "Confirmar a receção não altera o stock. Se faltou "
                "material, escreve acima — o administrador lê a "
                "observação e decide como corrigir."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=510,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 12))

        # ---- Rodapé ----
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(4, 18), side="bottom")

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
            text="Confirmar receção",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._confirmar,
        ).pack(side="right")

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
        ).pack(side="left")

    def _construir_tabela_produtos(self):
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
            ("PRODUTO", 260),
            ("PEDIDO", 90),
            ("ENVIADO", 90),
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

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome_produto,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=260,
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_pedida"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=90,
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_enviada"]),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=90,
                anchor="w",
            ).pack(side="left")

    def _confirmar(self):
        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        observacao = self.campo_observacao.get("1.0", "end").strip()

        try:
            estoque.confirmar_rececao_requisicao(
                self.requisicao["id"],
                ativo["id"],
                datetime.date.today(),
                observacao_rececao=observacao,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição {self.requisicao['id']} fechada."
        )
        self.destroy()
        self.tela_lista._recarregar()


class _RejeitarRequisicaoModal(ctk.CTkToplevel):
    """Motivo obrigatório antes de rejeitar — `rejeitar_requisicao`
    já o exige (decisão 9).

    Vive neste ficheiro porque é chamado a partir do
    `gui_est_aprovacao.py` (o ecrã próprio do admin), mas o módulo
    onde a ação pertence é aqui — a rejeição é uma operação sobre
    uma requisição, o mesmo objeto deste ficheiro. Manter o modal
    aqui evita duplicá-lo, e importa-se do outro lado.
    """

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        largura, altura = 420, 300
        self.title(f"Rejeitar — {requisicao['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Rejeitar requisição {requisicao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))

        nome = tela_lista.nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )
        ctk.CTkLabel(
            self,
            text=f"Pedido por {nome}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Motivo da rejeição",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_motivo = ctk.CTkTextbox(
            self, height=90, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_motivo.pack(fill="x", padx=20, pady=(2, 16))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            rodape,
            text="Voltar",
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
            text="Rejeitar requisição",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERMELHO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            text_color=tema.TEXTO_ERRO,
            command=self._rejeitar,
        ).pack(side="right")

    def _rejeitar(self):
        motivo = self.campo_motivo.get("1.0", "end").strip()

        if not motivo:
            componentes.mostrar_erro("O motivo é obrigatório.")
            return

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            requisicao = estoque.rejeitar_requisicao(
                self.requisicao["id"], ativo["id"], motivo
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição rejeitada: {requisicao['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class ReportarDevolucaoModal(ctk.CTkToplevel):
    """Reportar sobra de uma requisição fechada ("Reportar sobra",
    no Gerir) — cria uma devolução "pendente", que depois aparece
    em "Aceitar Sobra (Devolução)" para o armazém fechar
    (`_AcoesDevolucaoModal`).

    Ao contrário de `NovaRequisicaoModal`/`RolLavanderiaModal`, a
    lista de produtos aqui é fixa — os mesmos itens da requisição
    original, cada um com o que ainda pode ser devolvido
    (`_itens_disponiveis_devolucao`) — não há dropdown de produto
    nem linhas para acrescentar/remover, porque não se pode devolver
    o que não foi pedido.
    """

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao
        self.campos_por_produto = {}

        self.itens_disponiveis = _itens_disponiveis_devolucao(
            requisicao["id"]
        )
        produtos = {p["id"]: p for p in estoque.listar_produtos(True)}

        largura = 620
        altura = 220 + _ALTURA_LINHA_ITEM * max(
            len(self.itens_disponiveis), 1
        )
        self.title(f"Reportar sobra — {requisicao['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Reportar sobra — {requisicao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text=(
                "Indique a quantidade a devolver de cada produto — "
                "deixe a zero o que não sobrou."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 14))

        if not self.itens_disponiveis:
            self._sem_itens()
            return

        self._construir_tabela(produtos)
        self._construir_rodape()

    def _sem_itens(self):
        """Chega aqui só se a sobra for reportada por outra via
        (ex.: CLI) entre abrir a lista e clicar em Gerir — a
        condição já foi checada em `_pode_reportar_devolucao` antes
        de este popup poder abrir.
        """
        ctk.CTkLabel(
            self,
            text="Já não há sobra por reportar nesta requisição.",
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=12),
            wraplength=580,
            justify="left",
            padx=14,
            pady=12,
        ).pack(fill="x", padx=20)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(anchor="w", padx=20, pady=20)

    def _construir_tabela(self, produtos):
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
            ("ENVIADO", _LARGURA_ARMAZEM),
            ("JÁ DEVOLVIDO", _LARGURA_ARMAZEM + 20),
            ("A DEVOLVER", _LARGURA_PEDIDO),
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

        for item in self.itens_disponiveis:
            produto = produtos.get(item["produto_id"])
            nome = produto["nome"] if produto else item["produto_id"]

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PRODUTO,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_enviada"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_ARMAZEM,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["ja_devolvido"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_ARMAZEM + 20,
                anchor="w",
            ).pack(side="left")

            campo = ctk.CTkEntry(
                linha,
                width=_LARGURA_PEDIDO,
                corner_radius=tema.RAIO_CAMPO,
                justify="center",
                placeholder_text="0",
            )
            campo.pack(side="left")
            self.campos_por_produto[item["produto_id"]] = campo

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
            text="Reportar devolução",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._reportar,
        ).pack(side="right")

    # -- submissão -----------------------------------------------------

    def _itens(self):
        """Itens com quantidade > 0, no formato que
        `estoque.reportar_devolucao` espera. Campo vazio ou "0"
        fica de fora — é assim que se marca "não sobrou nada disto",
        sem ser preciso apagar a linha (não há linhas para apagar
        aqui, ao contrário dos formulários de nova requisição).
        """
        itens = []

        for produto_id, campo in self.campos_por_produto.items():
            texto = campo.get().strip()

            if not texto or not texto.isdigit() or int(texto) == 0:
                continue

            itens.append({"produto_id": produto_id, "quantidade": int(texto)})

        return itens

    def _reportar(self):
        itens = self._itens()

        if not itens:
            componentes.mostrar_erro(
                "Indique pelo menos uma quantidade a devolver."
            )
            return

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            devolucao = estoque.reportar_devolucao(
                requisicao_id=self.requisicao["id"],
                responsavel_id=ativo["id"],
                itens=itens,
                data_reportada=datetime.date.today(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Devolução reportada: {devolucao['id']} — fica "
            f"pendente até o armazém aceitar, em \"Aceitar Sobra "
            f"(Devolução)\"."
        )
        self.destroy()
        self.tela_lista._recarregar()


# =====================================================================
# "+ NOVA REQUISIÇÃO" — escolher Requisição Staff / Rol de Lavanderia
# =====================================================================


class _EscolherTipoRequisicaoModal(ctk.CTkToplevel):
    """Popup intermédio do botão "+ Nova requisição": pergunta qual
    dos dois fluxos abrir, antes de qualquer formulário.

    "Requisição Staff" é o formulário que já existia
    (`NovaRequisicaoModal`, sem alterações). "Rol de Lavanderia"
    reutiliza a mesma tabela de produtos, mas cria E envia de
    imediato — mesma composição de `cli.py:_enviar_rol_lavanderia`.
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 380, 300
        self.title("Nova requisição")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="O que pretende criar?",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 14))

        self._cartao(
            "Requisição Staff",
            "Pedido normal: fica pendente até ser aprovado.",
            self._abrir_staff,
        )
        self._cartao(
            "Rol de Lavanderia",
            "Envio direto a um responsável, sem passar por aprovação.",
            self._abrir_lavanderia,
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
        cartao.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            cartao,
            text=descricao,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", padx=14, pady=(0, 12))

        _tornar_clicavel(cartao, ao_clicar)

    def _abrir_staff(self):
        self.destroy()
        NovaRequisicaoModal(self.tela_lista)

    def _abrir_lavanderia(self):
        self.destroy()
        RolLavanderiaModal(self.tela_lista)


# =====================================================================
# LINHA DE PRODUTO — partilhada pelos dois formulários
# =====================================================================


class _LinhaProduto:
    """Uma linha da tabela de produtos de um dos dois formulários.

    Não é um widget: é o par (dropdown, campo de quantidade) mais a
    moldura que os contém, para o modal poder lê-los e destruí-los
    sem andar a percorrer filhos de frames.
    """

    def __init__(self, modal, master):
        self.modal = modal

        self.moldura = ctk.CTkFrame(master, fg_color="transparent")
        self.moldura.pack(fill="x", padx=16, pady=3)

        self.combo_produto = ctk.CTkOptionMenu(
            self.moldura,
            values=modal.rotulos_produtos,
            width=_LARGURA_PRODUTO,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: modal.ao_mudar_linha(),
        )
        self.combo_produto.set(modal.rotulos_produtos[0])
        self.combo_produto.pack(side="left")

        self.rotulo_armazem = ctk.CTkLabel(
            self.moldura,
            text="",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            width=_LARGURA_ARMAZEM,
            anchor="w",
        )
        self.rotulo_armazem.pack(side="left", padx=(10, 0))

        self.campo_pedido = ctk.CTkEntry(
            self.moldura,
            width=_LARGURA_PEDIDO,
            corner_radius=tema.RAIO_CAMPO,
            justify="center",
        )
        self.campo_pedido.pack(side="left")
        # Atualiza o aviso a cada tecla: o banner tem de acompanhar
        # o que está escrito, não só o que já foi submetido.
        self.campo_pedido.bind(
            "<KeyRelease>", lambda evento: modal.ao_mudar_linha()
        )

        ctk.CTkButton(
            self.moldura,
            text="X",
            width=30,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self.remover,
        ).pack(side="left", padx=(10, 0))

    def produto_id(self):
        return self.modal.id_por_rotulo_produto.get(self.combo_produto.get())

    def quantidade(self):
        """Quantidade escrita, ou None se ainda não for um inteiro.

        None não é erro aqui: é o estado normal de um campo vazio ou
        a meio de ser escrito. Quem recusa de vez é a submissão de
        cada modal.
        """
        texto = self.campo_pedido.get().strip()

        if not texto.isdigit():
            return None

        return int(texto)

    def remover(self):
        self.moldura.destroy()
        self.modal.linhas.remove(self)
        self.modal.ao_mudar_linha()


# =====================================================================
# REQUISIÇÃO STAFF — formulário já existente, sem alterações
# =====================================================================


class NovaRequisicaoModal(ctk.CTkToplevel):
    """Popup de criação de uma requisição de material (fica
    "pendente", à espera de "Confirmar requisição" no Gerir).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.linhas = []

        largura, altura = 760, 640
        self.title("Nova Requisição")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        self.produtos_disponiveis = estoque.listar_produtos()
        self.rotulos_produtos = [
            _rotulo_produto(p) for p in self.produtos_disponiveis
        ]
        self.id_por_rotulo_produto = {
            _rotulo_produto(p): p["id"] for p in self.produtos_disponiveis
        }
        self.produtos_por_id = {p["id"]: p for p in self.produtos_disponiveis}

        ctk.CTkLabel(
            self,
            text="Stock · Nova requisição — Requisição Staff",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 12))

        if not self.produtos_disponiveis:
            self._sem_catalogo()
            return

        self._construir_responsavel()
        self._construir_tabela()
        self._construir_aviso()
        self._construir_observacoes()
        self._construir_rodape()

        self._acrescentar_linha()

    def _sem_catalogo(self):
        """Sem produtos ativos não há requisição possível.

        Acontece enquanto o ecrã de Produtos não existir e a base
        estiver vazia — dizê-lo aqui é mais claro do que abrir um
        formulário com um dropdown sem opções nenhumas.
        """
        ctk.CTkLabel(
            self,
            text=(
                "Não há produtos ativos no catálogo. Sem catálogo "
                "não é possível criar uma requisição."
            ),
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=12),
            wraplength=640,
            justify="left",
            padx=14,
            pady=12,
        ).pack(fill="x", padx=20)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(anchor="w", padx=20, pady=20)

    def _construir_responsavel(self):
        ctk.CTkLabel(
            self,
            text="Responsável pela requisição",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.responsaveis_disponiveis = responsaveis.listar()
        rotulos = [
            _rotulo_responsavel(r) for r in self.responsaveis_disponiveis
        ]
        self.id_por_rotulo_responsavel = {
            _rotulo_responsavel(r): r["id"]
            for r in self.responsaveis_disponiveis
        }

        self.combo_responsavel = ctk.CTkOptionMenu(
            self,
            values=rotulos or ["— Nenhum —"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_responsavel.pack(fill="x", padx=20, pady=(2, 12))

        # Arranca no responsável ativo da sessão, quando há um: é
        # quase sempre quem está a pedir, e poupa uma escolha.
        ativo = sessao.obter_responsavel_ativo()

        if ativo is not None and _rotulo_responsavel(ativo) in rotulos:
            self.combo_responsavel.set(_rotulo_responsavel(ativo))
        elif rotulos:
            self.combo_responsavel.set(rotulos[0])
        else:
            self.combo_responsavel.set("— Nenhum —")

    def _construir_tabela(self):
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
            ("EM ARMAZÉM", _LARGURA_ARMAZEM + 10),
            ("PEDIDO", _LARGURA_PEDIDO),
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

        self.area_linhas = ctk.CTkFrame(cartao, fg_color="transparent")
        self.area_linhas.pack(fill="x", pady=(6, 8))

        ctk.CTkButton(
            self,
            text="+ Acrescentar produto",
            width=180,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            command=self._acrescentar_linha,
        ).pack(anchor="w", padx=20, pady=(8, 10))

    def _construir_aviso(self):
        """Caixa de aviso, escondida enquanto não houver avisos.

        Criada uma vez e mostrada/escondida com pack/pack_forget —
        recriá-la a cada tecla fazia o resto do formulário saltar.
        """
        self.caixa_aviso = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )

        self.rotulo_aviso = ctk.CTkLabel(
            self.caixa_aviso,
            text="",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=12),
            wraplength=660,
            justify="left",
            anchor="w",
        )
        self.rotulo_aviso.pack(fill="x", padx=12, pady=8)

    def _construir_observacoes(self):
        ctk.CTkLabel(
            self,
            text="Observações (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(6, 2))

        self.campo_observacoes = ctk.CTkTextbox(
            self, height=70, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_observacoes.pack(fill="x", padx=20)

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
            text="Enviar pedido",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._criar,
        ).pack(side="right")

    # -- linhas e avisos ---------------------------------------------

    def _acrescentar_linha(self):
        self.linhas.append(_LinhaProduto(self, self.area_linhas))
        self.ao_mudar_linha()

    def ao_mudar_linha(self):
        """Recalcula "em armazém" de cada linha e o banner de aviso.

        Chamada a cada tecla escrita e a cada produto escolhido. As
        frases do banner vêm inteiras de
        `estoque.avisos_requisicao` — aqui não se compara nada.
        """
        for linha in self.linhas:
            produto_id = linha.produto_id()

            if produto_id is None:
                linha.rotulo_armazem.configure(text="")
                continue

            produto = self.produtos_por_id.get(produto_id)

            try:
                saldo = estoque.saldo_produto(produto_id)
            except ValueError:
                linha.rotulo_armazem.configure(text="—")
                continue

            unidade = produto["unidade_medida"] if produto else ""
            pedida = linha.quantidade()
            em_falta = pedida is not None and pedida > saldo

            linha.rotulo_armazem.configure(
                text=f"{saldo} {unidade}".strip(),
                text_color=(
                    tema.TEXTO_ERRO if em_falta else tema.COR_TEXTO_SECUNDARIO
                ),
            )

        self._atualizar_aviso()

    def _atualizar_aviso(self):
        try:
            avisos = estoque.avisos_requisicao(self._itens())
        except ValueError:
            avisos = []

        if not avisos:
            self.caixa_aviso.pack_forget()
            return

        self.rotulo_aviso.configure(text="\n".join(avisos))
        self.caixa_aviso.pack(
            fill="x", padx=20, pady=(0, 8), before=self.campo_observacoes
        )

    def _itens(self):
        """Itens no formato que o módulo de negócio espera.

        Linhas sem produto ou sem quantidade válida ficam de fora —
        durante a escrita são o estado normal, não um erro.
        """
        itens = []

        for linha in self.linhas:
            produto_id = linha.produto_id()
            quantidade = linha.quantidade()

            if produto_id is None or quantidade is None:
                continue

            itens.append(
                {
                    "produto_id": produto_id,
                    "quantidade_pedida": quantidade,
                }
            )

        return itens

    # -- submissão ---------------------------------------------------

    def _criar(self):
        responsavel_id = self.id_por_rotulo_responsavel.get(
            self.combo_responsavel.get()
        )

        if responsavel_id is None:
            componentes.mostrar_erro(
                "Escolha o responsável pela requisição."
            )
            return

        itens = self._itens()

        if not itens:
            componentes.mostrar_erro(
                "Acrescente pelo menos um produto com uma "
                "quantidade válida."
            )
            return

        observacoes = self.campo_observacoes.get("1.0", "end").strip()

        try:
            requisicao = estoque.criar_requisicao(
                responsavel_id=responsavel_id,
                itens=itens,
                data_pedido=datetime.date.today(),
                observacoes=observacoes,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição criada com sucesso: {requisicao['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


# =====================================================================
# ROL DE LAVANDERIA — cria e envia numa só operação
# =====================================================================


class RolLavanderiaModal(ctk.CTkToplevel):
    """Envio direto de stock a um responsável, sem requisição prévia
    — mesma composição de `cli.py:_enviar_rol_lavanderia`
    (`criar_requisicao` seguido de `enviar_requisicao`). O
    responsável só entra depois, a confirmar a receção pelo ecrã
    normal (decisão 9: quem recebe é quem confirma, nunca o admin em
    nome dele).

    A requisição é criada com `origem="rol"` (13/09/2026) — assim
    a lista de Requisições consegue distinguir as que foram criadas
    por aqui das que foram pedidas pelo staff, e marcar as
    primeiras com um chip próprio.
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.linhas = []

        largura, altura = 760, 680
        self.title("Rol de Lavanderia")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        self.produtos_disponiveis = estoque.listar_produtos()
        self.rotulos_produtos = [
            _rotulo_produto(p) for p in self.produtos_disponiveis
        ]
        self.id_por_rotulo_produto = {
            _rotulo_produto(p): p["id"] for p in self.produtos_disponiveis
        }
        self.produtos_por_id = {p["id"]: p for p in self.produtos_disponiveis}

        ctk.CTkLabel(
            self,
            text="Stock · Rol de Lavanderia",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text="Envio direto — não fica pendente nem passa por "
            "aprovação.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        if not self.produtos_disponiveis:
            self._sem_catalogo()
            return

        self._construir_responsaveis()
        self._construir_tabela()
        self._construir_aviso()
        self._construir_rodape()

        self._acrescentar_linha()

    def _sem_catalogo(self):
        """Mesma frase e botão de `NovaRequisicaoModal._sem_catalogo`
        — sem catálogo não há o que enviar, aqui nem faz sentido
        escolher os dois responsáveis primeiro.
        """
        ctk.CTkLabel(
            self,
            text=(
                "Não há produtos ativos no catálogo. Sem catálogo "
                "não é possível enviar um rol de lavanderia."
            ),
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=12),
            wraplength=640,
            justify="left",
            padx=14,
            pady=12,
        ).pack(fill="x", padx=20)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(anchor="w", padx=20, pady=20)

    def _construir_responsaveis(self):
        self.responsaveis_disponiveis = responsaveis.listar()
        rotulos = [
            _rotulo_responsavel(r) for r in self.responsaveis_disponiveis
        ]
        self.id_por_rotulo_responsavel = {
            _rotulo_responsavel(r): r["id"]
            for r in self.responsaveis_disponiveis
        }

        linha_responsaveis = ctk.CTkFrame(self, fg_color="transparent")
        linha_responsaveis.pack(fill="x", padx=20, pady=(0, 12))

        coluna_recebe = ctk.CTkFrame(
            linha_responsaveis, fg_color="transparent"
        )
        coluna_recebe.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(
            coluna_recebe,
            text="Responsável que vai receber",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_recebe = ctk.CTkOptionMenu(
            coluna_recebe,
            values=rotulos or ["— Nenhum —"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_recebe.pack(fill="x", pady=(2, 0))
        if rotulos:
            self.combo_recebe.set(rotulos[0])

        coluna_envia = ctk.CTkFrame(
            linha_responsaveis, fg_color="transparent"
        )
        coluna_envia.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ctk.CTkLabel(
            coluna_envia,
            text="Enviado por (admin)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_envia = ctk.CTkOptionMenu(
            coluna_envia,
            values=rotulos or ["— Nenhum —"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_envia.pack(fill="x", pady=(2, 0))

        # Arranca no responsável ativo da sessão como "quem envia" —
        # é o admin logado na maior parte dos casos; "quem recebe"
        # arranca no primeiro da lista, sem preferência nenhuma.
        ativo = sessao.obter_responsavel_ativo()

        if ativo is not None and _rotulo_responsavel(ativo) in rotulos:
            self.combo_envia.set(_rotulo_responsavel(ativo))
        elif rotulos:
            self.combo_envia.set(rotulos[-1])
        else:
            self.combo_envia.set("— Nenhum —")

    def _construir_tabela(self):
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
            ("EM ARMAZÉM", _LARGURA_ARMAZEM + 10),
            ("ENVIAR", _LARGURA_PEDIDO),
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

        self.area_linhas = ctk.CTkFrame(cartao, fg_color="transparent")
        self.area_linhas.pack(fill="x", pady=(6, 8))

        ctk.CTkButton(
            self,
            text="+ Acrescentar produto",
            width=180,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            command=self._acrescentar_linha,
        ).pack(anchor="w", padx=20, pady=(8, 10))

    def _construir_aviso(self):
        self.caixa_aviso = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.rotulo_aviso = ctk.CTkLabel(
            self.caixa_aviso,
            text="",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=12),
            wraplength=660,
            justify="left",
            anchor="w",
        )
        self.rotulo_aviso.pack(fill="x", padx=12, pady=8)

    def _construir_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16, side="bottom")

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
            text="Enviar rol",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._enviar,
        ).pack(side="right")

    # -- linhas e avisos ---------------------------------------------

    def _acrescentar_linha(self):
        self.linhas.append(_LinhaProduto(self, self.area_linhas))
        self.ao_mudar_linha()

    def ao_mudar_linha(self):
        for linha in self.linhas:
            produto_id = linha.produto_id()

            if produto_id is None:
                linha.rotulo_armazem.configure(text="")
                continue

            produto = self.produtos_por_id.get(produto_id)

            try:
                saldo = estoque.saldo_produto(produto_id)
            except ValueError:
                linha.rotulo_armazem.configure(text="—")
                continue

            unidade = produto["unidade_medida"] if produto else ""
            pedida = linha.quantidade()
            em_falta = pedida is not None and pedida > saldo

            linha.rotulo_armazem.configure(
                text=f"{saldo} {unidade}".strip(),
                text_color=(
                    tema.TEXTO_ERRO if em_falta else tema.COR_TEXTO_SECUNDARIO
                ),
            )

        self._atualizar_aviso()

    def _atualizar_aviso(self):
        try:
            avisos = estoque.avisos_requisicao(self._itens())
        except ValueError:
            avisos = []

        if not avisos:
            self.caixa_aviso.pack_forget()
            return

        # Aqui o aviso é mesmo um bloqueio (envio imediato), não só
        # informativo como em NovaRequisicaoModal — a frase original
        # ("o administrador terá de repor") não fazia sentido quando
        # é o próprio administrador que está a tentar enviar agora.
        avisos = [
            aviso.replace(
                "O administrador terá de repor.",
                "Reduza a quantidade ou reponha stock antes de "
                "enviar.",
            )
            for aviso in avisos
        ]
        self.rotulo_aviso.configure(text="\n".join(avisos))
        self.caixa_aviso.pack(fill="x", padx=20, pady=(0, 8))

    def _itens(self):
        itens = []

        for linha in self.linhas:
            produto_id = linha.produto_id()
            quantidade = linha.quantidade()

            if produto_id is None or quantidade is None:
                continue

            itens.append(
                {
                    "produto_id": produto_id,
                    "quantidade_pedida": quantidade,
                }
            )

        return itens

    # -- submissão ---------------------------------------------------

    def _enviar(self):
        recebe_id = self.id_por_rotulo_responsavel.get(
            self.combo_recebe.get()
        )
        envia_id = self.id_por_rotulo_responsavel.get(self.combo_envia.get())

        if recebe_id is None or envia_id is None:
            componentes.mostrar_erro("Escolha os dois responsáveis.")
            return

        itens = self._itens()

        if not itens:
            componentes.mostrar_erro(
                "Acrescente pelo menos um produto com uma "
                "quantidade válida."
            )
            return

        try:
            requisicao = estoque.criar_requisicao(
                responsavel_id=recebe_id,
                itens=itens,
                data_pedido=datetime.date.today(),
                observacoes=(
                    "Enviado sem requisição prévia (rol de lavanderia)."
                ),
                origem="rol",
            )
            estoque.enviar_requisicao(
                requisicao["id"], envia_id, datetime.date.today()
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Rol de lavanderia enviado: {requisicao['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()