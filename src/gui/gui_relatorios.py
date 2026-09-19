"""Ecrã de Relatórios — hub de 3 áreas + popup de cada área.

O `relatorios.py` é o módulo de apresentação da v1.5.0. Consome o
`financeiro.py` (motor puro) e, para os relatórios de Contratos e
Stock, fala diretamente com os módulos de negócio (`contratos`,
`clientes`, `propriedades`, `estoque`, `unidades`, `responsaveis`) —
nunca com o `repositorio`.

ESTRUTURA DO ECRÃ (mockup consolidado, 19/09/2026):

  Relatórios (menu lateral)
    → hub com 3 cartões: Financeiro · Contratos · Stock
      → clicar num cartão abre popup grande dessa área
        → popup tem barra de período, lista lateral dos relatórios
          dessa área, e área de conteúdo à direita
          → "Fechar" volta ao hub

O hub é um ecrã (como o `EcraStock` e o `EcraDespesas`). O popup é um
`CTkToplevel` (como o `UnidadesDaPropriedadeModal`). Nada disto é novo
— são os padrões que o projeto já usa.

DECISÕES DE NEGÓCIO (fechadas em 19/09/2026):

  - 12 relatórios, distribuídos por 3 áreas (Financeiro=5,
    Contratos=4, Stock=4). A área "Clientes" foi cortada — o modelo
    não tem os dados necessários (regime do cliente, data_registo).
  - Sem gráficos na v1.5.0. PDF e CSV só com tabela.
  - Período: atalhos Mês atual · Mês anterior · Últimos 30 dias ·
    Este ano · Personalizado. Default = Mês atual.
  - "Mês atual" e "Este ano" terminam em HOJE. "Mês anterior" é
    inteiro. "Personalizado" é inclusivo no "Até".
  - Conversão obrigatória: o `financeiro.py` recebe `data_fim`
    EXCLUSIVO. Um helper converte o intervalo mostrado ao utilizador
    no par (data_inicio, data_fim) que o motor espera.
  - Exportação: PDF + CSV, ambos no `impressao.py`. Pasta
    `config.DIR_RELATORIOS`. Nome
    `relatorio_<area>_<nome>_<datas>_<hora>`.
  - O relatório "Stock atual" não tem período — a barra de período
    desaparece nesse relatório.

SEGUE A MESMA DISCIPLINA DE CAMADAS DO RESTO DA GUI (decisão 7): só
fala com módulos de negócio, nunca com o `repositorio`.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from tkcalendar import Calendar

import clientes
import config
import contratos
import despesas
import estoque
import financeiro
import impressao
import propriedades
import responsaveis
import unidades
import utilizadores
from . import componentes
from . import sessao
from . import tema

# =====================================================================
# CONSTANTES DE APRESENTAÇÃO
# =====================================================================

# Chips de período — a ordem é a que aparece na barra.
# 'personalizado' não é um chip próprio: é o campo único que abre o
# calendário. Está aqui só para o rótulo ser único num sítio.
PERIODO_MES_ATUAL = "mes_atual"
PERIODO_MES_ANTERIOR = "mes_anterior"
PERIODO_ULTIMOS_30 = "ultimos_30"
PERIODO_ESTE_ANO = "este_ano"
PERIODO_PERSONALIZADO = "personalizado"

CHIPS_PERIODO = (
    (PERIODO_MES_ATUAL, "Mês atual"),
    (PERIODO_MES_ANTERIOR, "Mês anterior"),
    (PERIODO_ULTIMOS_30, "Últimos 30 dias"),
    (PERIODO_ESTE_ANO, "Este ano"),
)

PERIODO_DEFAULT = PERIODO_MES_ATUAL


# =====================================================================
# MAPA DOS RELATÓRIOS
# =====================================================================
#
# Cada área tem uma lista de relatórios. Cada relatório é um dicionário:
#
#   - 'id':       identificador interno (usado como chave de despacho
#                 e no nome do ficheiro exportado, sem espaços).
#   - 'titulo':   texto mostrado na lista lateral e no cabeçalho do
#                 relatório.
#   - 'periodo':  True se o relatório usa o período escolhido (barra
#                 de período visível); False se é "agora" (barra
#                 escondida). Só "Stock atual" é False.
#   - 'filtros':  lista de filtros adicionais próprios do relatório.
#                 Cada filtro é ("chave", "rótulo", ("opção1", ...)).
#                 Lista vazia quando não há filtros próprios.
#
# A ORDEM das áreas é a ordem dos cartões no hub (Financeiro primeiro,
# porque é o que se usa mais). A ORDEM dos relatórios dentro de cada
# área é a ordem na lista lateral — o "Resultado" primeiro, porque é
# o relatório de topo.

RELATORIOS = {
    "financeiro": [
        {
            "id": "resultado",
            "titulo": "Resultado",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "receita_unidade",
            "titulo": "Receita por unidade",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "receita_propriedade",
            "titulo": "Receita por propriedade",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "despesas_categoria",
            "titulo": "Despesas por categoria",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "cogs_produto",
            "titulo": "COGS por produto",
            "periodo": True,
            "filtros": [],
        },
    ],
    "contratos": [
        {
            "id": "ocupacoes",
            "titulo": "Ocupações no período",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "contratos_mensais",
            "titulo": "Contratos mensais",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "reservas_airbnb",
            "titulo": "Reservas Airbnb",
            "periodo": True,
            "filtros": [],
        },
        {
            "id": "encerramentos",
            "titulo": "Encerramentos",
            "periodo": True,
            "filtros": [],
        },
    ],
    "stock": [
        {
            "id": "movimentos",
            "titulo": "Movimentos",
            "periodo": True,
            "filtros": [
                ("tipo", "Tipo", ("Todos", "entrada", "saida", "ajuste")),
                ("produto", "Produto", ()),  # preenchido em runtime
            ],
        },
        {
            "id": "stock_atual",
            "titulo": "Stock atual",
            "periodo": False,
            "filtros": [],
        },
        {
            "id": "requisicoes",
            "titulo": "Requisições",
            "periodo": True,
            "filtros": [
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
                ("responsavel", "Responsável", ()),  # preenchido em runtime
            ],
        },
        {
            "id": "devolucoes",
            "titulo": "Devoluções",
            "periodo": True,
            "filtros": [
                ("estado", "Estado", ("Todos", "pendente", "fechada")),
                ("responsavel", "Responsável", ()),  # preenchido em runtime
            ],
        },
    ],
}

# Rótulos das áreas no hub — a ordem é a ordem dos cartões.
AREAS = (
    ("financeiro", "Financeiro", "Resultado · Receita · Despesas · COGS"),
    ("contratos", "Contratos", "Ocupações · Mensais · Airbnb · Ocupação"),
    ("stock", "Stock", "Movimentos · Stock atual · Requisições · Devoluções"),
)


# =====================================================================
# HELPERS INTERNOS
# =====================================================================


def _autor_atual():
    """Devolve o dict do responsável ativo, ou None.

    Centraliza o acesso à sessão. Vários sítios deste módulo precisam
    de saber quem está logado (para os exports, para os filtros por
    perfil, para o cabeçalho do popup). Não andamos a chamar
    `sessao.obter_responsavel_ativo()` em cada função.
    """
    return sessao.obter_responsavel_ativo()


def _formatar_data(valor):
    """Formata uma `date` para dd/mm/aaaa, ou '—' quando None."""
    if valor is None:
        return "—"
    return valor.strftime("%d/%m/%Y")


def _formatar_data_iso(valor):
    """Formata uma `date` para AAAA-MM-DD (usado no nome do ficheiro
    exportado — ordena bem no explorador de ficheiros)."""
    return valor.isoformat()


def _formatar_valor(valor):
    """Formata um Decimal em PT-PT, com euro no fim — mesma
    convenção do `componentes.formatar_valor`. Reexportado aqui com
    nome próprio para o corpo do ficheiro não ter de ir buscar
    sempre ao `componentes`.
    """
    return componentes.formatar_valor(valor)


def _primeiro_dia_do_mes(d):
    return date(d.year, d.month, 1)


def _ultimo_dia_do_mes(d):
    """Último dia do mês de `d`.

    Usa o truque do `date.replace(day=28) + timedelta(days=4) - timedelta(days=...)`
    em vez de importar `calendar.monthrange` só para isto — é mais
    curto e faz o mesmo.
    """
    proximo_mes = d.replace(day=28) + timedelta(days=4)
    return proximo_mes - timedelta(days=proximo_mes.day)


def _intervalo_do_atalho(atalho, hoje=None):
    """Converte um atalho de período no par `(data_inicio, data_fim)`
    que o `financeiro.py` espera.

    `data_fim` é EXCLUSIVO no motor — a docstring de
    `financeiro._validar_periodo` é explícita ("um período com o
    mesmo dia de início e fim não contém nenhum"). Este helper é o
    ÚNICO sítio onde essa conversão acontece.

    Regras (fechadas em 19/09/2026):

      - Mês atual    → dia 1 do mês corrente → amanhã (o fim do
                        intervalo é "hoje + 1 dia", para incluir hoje).
      - Mês anterior → dia 1 → dia 1 do mês atual (o mês anterior
                        inteiro, exclusive).
      - Últimos 30   → hoje − 30 dias → amanhã.
      - Este ano     → 1 de janeiro → amanhã.

    Devolve `(data_inicio, data_fim)`, os dois `date`.
    """
    if hoje is None:
        hoje = date.today()

    if atalho == PERIODO_MES_ATUAL:
        return _primeiro_dia_do_mes(hoje), hoje + timedelta(days=1)

    if atalho == PERIODO_MES_ANTERIOR:
        primeiro_dia_deste_mes = _primeiro_dia_do_mes(hoje)
        ultimo_dia_do_mes_anterior = primeiro_dia_deste_mes - timedelta(days=1)
        return (
            _primeiro_dia_do_mes(ultimo_dia_do_mes_anterior),
            primeiro_dia_deste_mes,
        )

    if atalho == PERIODO_ULTIMOS_30:
        return hoje - timedelta(days=30), hoje + timedelta(days=1)

    if atalho == PERIODO_ESTE_ANO:
        return date(hoje.year, 1, 1), hoje + timedelta(days=1)

    raise ValueError(f"Atalho de período desconhecido: {atalho}")


def _intervalo_personalizado(data_inicio, data_fim):
    """Converte um intervalo escolhido no calendário (inclusivo nas
    duas pontas, como o utilizador o vê) no par `(data_inicio,
    data_fim)` que o motor espera (fim exclusivo).

    O utilizador escolhe "1 de agosto a 15 de setembro" — quer dizer
    que o dia 15 está incluído. O motor recebe `date(2026, 9, 16)`
    para incluir o dia 15 (fim exclusivo).
    """
    if data_inicio is None or data_fim is None:
        raise ValueError(
            "As duas datas do período personalizado são obrigatórias."
        )

    if data_fim < data_inicio:
        raise ValueError(
            "A data de fim não pode ser anterior à data de início."
        )

    return data_inicio, data_fim + timedelta(days=1)


def _intervalo_visivel(atalho, hoje=None):
    """Devolve o intervalo como o UTILIZADOR o vê (as duas pontas
    inclusivas), para mostrar no campo único da barra de período.

    É o contrário de `_intervalo_do_atalho`: aquele devolve o que o
    motor come, este devolve o que o utilizador lê. A diferença é
    sempre de 1 dia no fim.
    """
    inicio, fim_exclusivo = _intervalo_do_atalho(atalho, hoje)
    return inicio, fim_exclusivo - timedelta(days=1)


def _mapa_por_id(registo_lista):
    """Constrói um dicionário {id: registo} a partir de uma lista de
    registos com chave 'id'.

    Serve para evitar N chamadas ao MySQL quando um relatório
    precisa do nome (ou outra coisa) de várias entidades — uma
    leitura só, mapa em memória, consulta em O(1).

    Chamado no início de cada relatório que precise:
      - unidades:   `_mapa_por_id(unidades.listar(incluir_inativas=True))`
      - clientes:   `_mapa_por_id(clientes.listar(incluir_inativos=True))`
      - produtos:   `_mapa_por_id(estoque.listar_produtos(incluir_inativos=True))`
      - responsáveis: `_mapa_por_id(responsaveis.listar(incluir_inativos=True))`
    """
    return {r["id"]: r for r in registo_lista}


def _celula_entidade(nome, identificador):
    """Devolve o HTML/markup de uma célula ID + nome, na convenção
    que ficou decidida em 19/09/2026: NOME em cima, ID por baixo em
    letra pequena e cinza.

    Não devolve widget nenhum — devolve o par (texto, config) para
    quem chama construir o CTkLabel. Simplifica: a estrutura é
    sempre a mesma, o sítio é que muda.
    """
    return f"{nome}\n{identificador}"


# =====================================================================
# ECRÃ HUB — EcraRelatorios
# =====================================================================


class EcraRelatorios(ctk.CTkFrame):
    """Hub de Relatórios — 3 cartões clicáveis.

    Mesmo estilo do `EcraStock` (gui_est_hub.py) e do `EcraDespesas`
    (gui_despesas.py): um cartão por área, cada um com título e
    descrição curta, clicável em qualquer ponto.

    O hub NÃO tem barra de período. O período é escolhido dentro do
    popup, quando uma área é aberta — cada área é independente.

    Recebe `controlador` — o mesmo contrato dos outros ecrãs:
    `controlador.mostrar_frame(classe, **kwargs)`.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Relatórios").pack(fill="x")

        ctk.CTkLabel(
            self,
            text="Selecionar área",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(4, 8))

        # Grelha dos 3 cartões — mesmo peso, mesmo tamanho. Com 3
        # cartões e uma janela de 1100px, cada um fica com ~340px.
        grelha = ctk.CTkFrame(self, fg_color="transparent")
        grelha.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        for coluna in range(3):
            grelha.grid_columnconfigure(coluna, weight=1, uniform="areas")

        for indice, (chave, titulo, descricao) in enumerate(AREAS):
            self._desenhar_cartao(grelha, chave, titulo, descricao, indice)

    # -- desenho ------------------------------------------------------

    def _desenhar_cartao(self, master, chave, titulo, descricao, indice):
        """Desenha um cartão de área do hub.

        Borda azul (a área está disponível). Cantos redondos, título
        em bold, descrição em cinza. Clique em qualquer ponto do
        cartão — usa `componentes.tornar_cliclavel`, que liga o
        clique ao cartão e a todos os filhos.
        """
        cartao = ctk.CTkFrame(
            master,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.COR_FUNDO,
        )
        cartao.grid(
            row=0,
            column=indice,
            sticky="nsew",
            padx=6,
            pady=6,
        )

        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(24, 8), padx=16)

        ctk.CTkLabel(
            cartao,
            text=descricao,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=280,
            justify="center",
        ).pack(padx=16, pady=(0, 24))

        componentes.tornar_cliclavel(
            cartao,
            lambda c=chave: self._abrir_area(c),
        )

    # -- navegação ----------------------------------------------------

    def _abrir_area(self, chave_area):
        RelatorioModal(self, chave_area)

    # =====================================================================


# POPUP DE UMA ÁREA — RelatorioModal
# =====================================================================


class RelatorioModal(ctk.CTkToplevel):
    """Popup grande com os relatórios de UMA área.

    Estrutura (mockup consolidado):

      - Cabeçalho: "Relatórios · <Área>" + data + responsável ativo.
      - Barra de período: chips de atalho + campo único de calendário.
        (Vazia neste bloco — preenchida no Bloco 3b.)
      - Corpo: lista lateral (só os relatórios da área aberta) +
        área de conteúdo (o relatório escolhido).
      - Rodapé: "Fechar" → volta ao hub.

    O popup é `transient` do hub (`tela_hub`), e fecha pela X nativa
    ou pelo botão "Fechar" — os dois voltam ao hub, que fica
    visível por trás.

    Estado interno:

      - `area` — a chave da área ("financeiro" / "contratos" / "stock"),
        fixa durante a vida do popup.
      - `relatorio_atual` — o id do relatório escolhido. Começa no
        primeiro da área, muda quando o utilizador clica na lista
        lateral.
      - `periodo_atual` — a chave do atalho escolhido ("mes_atual" /
        "mes_anterior" / "ultimos_30" / "este_ano"). O personalizado
        é gerido à parte (Bloco 3b). Default: `PERIODO_DEFAULT`.
      - `data_inicio` / `data_fim` — o intervalo já convertido para
        o motor (`data_fim` exclusivo). Recalculado sempre que o
        período muda. Os relatórios leem estes dois atributos.
      - `filtros_por_relatorio` — dicionário {id_relatorio: {chave:
        valor}} com as escolhas de filtros próprios de cada
        relatório. Persiste enquanto o popup estiver aberto — se o
        utilizador muda de relatório e volta, os filtros mantêm-se.
    """

    _LARGURA = 1000
    _ALTURA = 700

    def __init__(self, tela_hub, area):
        super().__init__(tela_hub)
        self.tela_hub = tela_hub
        self.controlador = tela_hub.controlador

        self.area = area
        self.relatorio_atual = RELATORIOS[area][0]["id"]

        # Período inicial — sempre o default. O intervalo é calculado
        # agora e recalculado no Bloco 3b sempre que o período muda.
        self.periodo_atual = PERIODO_DEFAULT
        self.data_inicio, self.data_fim = _intervalo_do_atalho(
            self.periodo_atual
        )

        # Filtros próprios por relatório. Guarda as escolhas enquanto
        # o popup estiver aberto.
        self.filtros_por_relatorio = {}

        # Referências aos widgets que mudam com o estado — o Bloco 3b
        # e os blocos 5/6/7 precisam de os alcançar.
        self._rotulo_periodo = None
        self._campo_unico = None
        self._chips = {}

        # Seleção provisória do calendário personalizado. Tuplo
        # (inicio, fim) enquanto o utilizador escolhe — `None` quando
        # ainda não clicou, ou depois de Aplicar. Guardado aqui (e
        # não no calendário) porque o `tkcalendar` desta versão só
        # aceita `selectmode="day"`; o intervalo em dois cliques é
        # gerido por nós.
        self._selecao_personalizada = None

        self.title(f"Relatórios · {area.capitalize()}")
        self.geometry(f"{self._LARGURA}x{self._ALTURA}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_hub)
        componentes.colocar_no_topo(self)

        # Fechar pela X nativa da janela — mesmo comportamento do
        # botão "Fechar".
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self._construir_cabecalho()
        self._construir_barra_periodo()
        self._construir_corpo()
        self._construir_rodape()

        # Desenha a primeira vez.
        self._recarregar_lista_lateral()
        self._recarregar_conteudo()

    # -- construção ---------------------------------------------------

    def _construir_cabecalho(self):
        """Cabeçalho do popup — título + data + responsável ativo.

        Não usa o `componentes.Cabecalho` porque esse é para ecrãs
        (ocupa a largura toda do frame que o contém); o popup é uma
        janela própria e queremos o cabeçalho dentro dela, com
        espaçamento ligeiro.
        """
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=18, pady=(14, 6))

        ctk.CTkLabel(
            cabecalho,
            text=f"Relatórios · {self.area.capitalize()}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        ativo = _autor_atual()
        nome = ativo["nome"] if ativo else "sem responsável"
        hoje = date.today().strftime("%d/%m/%Y")

        ctk.CTkLabel(
            cabecalho,
            text=f"{hoje} · {nome}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(side="right")

    def _construir_barra_periodo_vazia(self):
        """Cria o frame da barra de período — vazio neste bloco.

        O Bloco 3b preenche-o com os chips de atalho e o campo único
        de calendário. Os dois atributos (`self._chips`,
        `self._campo_unico`) ficam prontos a receber.

        O frame fica guardado em `self._frame_periodo` porque o
        relatório "Stock atual" precisa de o esconder (não tem
        período — é "agora").
        """
        self._frame_periodo = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_periodo.pack(fill="x", padx=18, pady=(0, 8))

    def _construir_corpo(self):
        """Corpo do popup — lista lateral + área de conteúdo.

        Grid de duas colunas: 190px para a lista, o resto para o
        conteúdo. A lista tem barra de scroll vertical própria; a
        área de conteúdo também (para relatórios com muitas linhas).
        """
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        corpo.grid_columnconfigure(0, weight=0, minsize=190)
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(0, weight=1)

        # Lista lateral
        self._lista_lateral = ctk.CTkScrollableFrame(
            corpo,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=tema.RAIO_CARTAO,
            width=190,
        )
        self._lista_lateral.grid(row=0, column=0, sticky="nsw", padx=(0, 8))

        # Área de conteúdo — tem scroll vertical para relatórios
        # grandes (Ocupações com muitas linhas, Movimentos, etc.).
        self._area_conteudo = ctk.CTkScrollableFrame(
            corpo,
            fg_color="transparent",
        )
        self._area_conteudo.grid(row=0, column=1, sticky="nsew")

    def _construir_rodape(self):
        """Rodapé do popup — só o botão "Fechar".

        Os botões "Exportar CSV" e "Exportar PDF" NÃO ficam aqui.
        Ficam dentro da área de conteúdo, no fim de cada relatório
        (como no mockup) — porque cada relatório exporta dados
        diferentes, e o botão deve estar ao lado dos dados que
        exporta.
        """
        rodape = ctk.CTkFrame(self, fg_color=tema.LINHA_ALTERNADA)
        rodape.pack(fill="x", side="bottom")

        ctk.CTkButton(
            rodape,
            text="Fechar",
            width=110,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._fechar,
        ).pack(side="right", padx=18, pady=10)

    # -- recarregamento ----------------------------------------------

    def _recarregar_lista_lateral(self):
        """Desenha os relatórios da área na lista lateral.

        O item do relatório atual fica marcado a azul. Cada item é
        clicável — `tornar_cliclavel` liga o clique ao item e aos
        filhos (a etiqueta dentro dele).
        """
        for widget in self._lista_lateral.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self._lista_lateral,
            text=self.area.upper(),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 4))

        for rel in RELATORIOS[self.area]:
            ativo = rel["id"] == self.relatorio_atual
            botao = ctk.CTkButton(
                self._lista_lateral,
                text=rel["titulo"],
                height=28,
                corner_radius=6,
                fg_color=(tema.AZUL_PRINCIPAL if ativo else "transparent"),
                text_color=("#FFFFFF" if ativo else tema.COR_TEXTO),
                hover_color=tema.ID_CHIP_FUNDO,
                font=ctk.CTkFont(
                    size=11, weight="bold" if ativo else "normal"
                ),
                anchor="w",
                command=lambda r=rel["id"]: self._escolher_relatorio(r),
            )
            botao.pack(fill="x", padx=4, pady=1)

    def _recarregar_conteudo(self):
        """Desenha o relatório escolhido na área de conteúdo.

        Despacha para a função `_desenhar_<id>` correspondente. Essas
        funções só existem nos blocos 5, 6 e 7 — neste bloco, mostro
        um placeholder em vez de rebentar, para o ecrã poder abrir
        e ser testado.
        """
        for widget in self._area_conteudo.winfo_children():
            widget.destroy()

        # O `_frame_periodo` é empacotado uma vez, no sítio certo,
        # no `_construir_barra_periodo`. Aqui só o escondemos ou
        # mostramos conforme o relatório aplique período ou não —
        # sem `pack()` outra vez, que dava erro de "already packed".
        aplica_periodo = self._relatorio_atual_aplica_periodo()
        if aplica_periodo:
            self._frame_periodo.pack(fill="x", padx=18, pady=(0, 8))
        else:
            self._frame_periodo.pack_forget()

        # Despacho para o desenhador do relatório. Todos os
        # desenhadores vivem nos blocos 5, 6 e 7. A chamada é feita
        # por getattr, para o método poder não existir ainda (durante
        # a construção por blocos) sem rebentar.
        nome_desenho = f"_desenhar_{self.relatorio_atual}"
        desenha = getattr(self, nome_desenho, None)

        if desenha is None:
            self._placeholder_bloco_seguinte()
            return

        import traceback

        try:
            desenha(self._area_conteudo)
        except Exception as erro:
            tb = traceback.format_exc()
            print(tb)
            componentes.mostrar_erro(
                f"Erro ao desenhar '{self.relatorio_atual}':\n\n"
                f"{type(erro).__name__}: {erro}"
            )

    def _placeholder_bloco_seguinte(self):
        """Ecrã provisório, enquanto o desenhador do relatório não
        existir.

        Não é para ficar em produção — é só para o popup poder abrir
        durante a construção por blocos, sem rebentar. Desaparece
        automaticamente assim que a função `_desenhar_<id>` estiver
        definida no bloco correspondente.
        """
        ctk.CTkLabel(
            self._area_conteudo,
            text=(
                f'Relatório "{self.relatorio_atual}" — '
                f"a implementação chega nos blocos 5, 6 ou 7."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
        ).pack(pady=40)

    # -- navegação ----------------------------------------------------

    def _escolher_relatorio(self, relatorio_id):
        """Troca o relatório ativo e redesenha o conteúdo.

        O `filtros_por_relatorio` mantém-se — se o utilizador tiver
        mexido nos filtros de um relatório e voltar, ficam como os
        deixou. Não re-cria a área de conteúdo nem a lista lateral:
        só redesenha o que é preciso.
        """
        self.relatorio_atual = relatorio_id
        self._recarregar_lista_lateral()
        self._recarregar_conteudo()

    def _relatorio_atual_aplica_periodo(self):
        """Diz se o relatório atual usa período (barra visível) ou
        não (barra escondida).

        Lê do mapa `RELATORIOS` — a chave 'periodo' de cada registo.
        Só o "Stock atual" tem 'periodo': False.
        """
        for rel in RELATORIOS[self.area]:
            if rel["id"] == self.relatorio_atual:
                return rel["periodo"]
        return True

    def _fechar(self):
        """Fecha o popup e volta ao hub.

        O hub já está visível por trás do popup — não é preciso
        fazer nada além de destruir este. A X nativa da janela e o
        botão "Fechar" chamam os dois este método.
        """
        self.destroy()

    # -- barra de período (substitui o método vazio do Bloco 3a) -----

    def _construir_barra_periodo(self):
        """Preenche o `self._frame_periodo` com os chips e o campo
        único de calendário.

        Chamado uma vez no `__init__`, no lugar do
        `_construir_barra_periodo_vazia` do Bloco 3a. Depois disto,
        o estado da barra é gerido por `_destacar_periodo` e
        `_atualizar_campo_periodo` — este método não volta a correr.
        """
        # Cria o frame da barra de período — herdado do
        # `_construir_barra_periodo_vazia` do Bloco 3a, que este
        # método substituiu.
        self._frame_periodo = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_periodo.pack(fill="x", padx=18, pady=(0, 8))

        self._chips = {}

        for chave, rotulo in CHIPS_PERIODO:
            chip = ctk.CTkButton(
                self._frame_periodo,
                text=rotulo,
                width=110,
                height=26,
                corner_radius=tema.RAIO_CAMPO,
                fg_color=tema.ID_CHIP_FUNDO,
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.COR_BORDA,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda c=chave: self._escolher_periodo(c),
            )
            chip.pack(side="left", padx=(0, 6))
            self._chips[chave] = chip

        # Campo único de calendário — alinhado à direita da barra.
        # Mostra o intervalo como o utilizador o lê (as duas pontas
        # inclusivas), não como o motor o recebe.
        self._campo_unico = ctk.CTkButton(
            self._frame_periodo,
            text="",
            height=26,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.COR_FUNDO,
            text_color=tema.COR_TEXTO,
            hover_color=tema.ID_CHIP_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            font=ctk.CTkFont(size=11),
            command=self._abrir_calendario,
        )
        self._campo_unico.pack(side="right")

        # Arranca com o default destacado e o campo preenchido.
        self._destacar_periodo(self.periodo_atual)
        self._atualizar_campo_periodo()

    def _escolher_periodo(self, chave):
        """Chamada ao clicar num chip de atalho.

        Recalcula o intervalo, atualiza o destaque dos chips e o
        texto do campo único, e redesenha o relatório atual com o
        período novo.
        """
        if chave == PERIODO_PERSONALIZADO:
            # O personalizado é só acessível pelo campo único —
            # não há chip para ele. Se chegar aqui, ignoramos.
            return

        self.periodo_atual = chave
        self.data_inicio, self.data_fim = _intervalo_do_atalho(chave)
        self._destacar_periodo(chave)
        self._atualizar_campo_periodo()
        self._recarregar_conteudo()

    def _destacar_periodo(self, chave):
        """Pinta o chip do período ativo a azul cheio; os outros
        ficam claros.

        Com o período personalizado escolhido, NENHUM chip fica
        destacado — o destaque vai para o campo único (que muda de
        borda e fundo). É mais honesto do que fingir que algum dos
        atalhos está ativo quando não está.
        """
        for c, chip in self._chips.items():
            ativo = c == chave and chave != PERIODO_PERSONALIZADO
            if ativo:
                chip.configure(
                    fg_color=tema.AZUL_PRINCIPAL,
                    text_color="#FFFFFF",
                    hover_color=tema.AZUL_CLARO,
                )
            else:
                chip.configure(
                    fg_color=tema.ID_CHIP_FUNDO,
                    text_color=tema.AZUL_PRINCIPAL,
                    hover_color=tema.COR_BORDA,
                )

        if self._campo_unico is not None:
            if chave == PERIODO_PERSONALIZADO:
                self._campo_unico.configure(
                    fg_color=tema.ID_CHIP_FUNDO,
                    border_color=tema.AZUL_PRINCIPAL,
                    text_color=tema.AZUL_PRINCIPAL,
                )
            else:
                self._campo_unico.configure(
                    fg_color=tema.COR_FUNDO,
                    border_color=tema.COR_BORDA,
                    text_color=tema.COR_TEXTO,
                )

    def _atualizar_campo_periodo(self):
        """Atualiza o texto do campo único com o intervalo visível
        (as duas pontas inclusivas).

        O motor recebe o `data_fim` exclusivo (num dia depois), mas
        o utilizador lê o intervalo como o escolheu — o dia final
        incluído.
        """
        if self._campo_unico is None:
            return

        # `_intervalo_visivel` dá-nos as pontas como o utilizador
        # as vê. Se o período atual for personalizado, as datas já
        # estão nas atribuições — usa-as diretamente.
        if self.periodo_atual == PERIODO_PERSONALIZADO:
            inicio = self.data_inicio
            fim = self.data_fim - timedelta(days=1)
        else:
            inicio, fim = _intervalo_visivel(self.periodo_atual)

        texto = (
            f"Período: {inicio.strftime('%d/%m/%Y')} a "
            f"{fim.strftime('%d/%m/%Y')}"
        )
        self._campo_unico.configure(text=texto)

    # -- calendário (tkcalendar) --------------------------------------

    def _abrir_calendario(self):
        """Abre o popup do calendário para escolher o período
        personalizado.

        Cria um `CTkToplevel` novo (a cada chamada) com a moldura
        do projeto, um `tkcalendar.Calendar` embutido, e o rodapé
        de Cancelar/Aplicar.

        ATENÇÃO — `tkcalendar` desta versão só aceita
        `selectmode="day"` (o `"range"` rebenta com
        `ValueError: 'selectmode' option should be 'none' or 'day'`).
        Por isso, o intervalo em dois cliques é gerido por NÓS:
        guardamos cada clique em `self._selecao_personalizada`, e
        usamos esse valor no `_aplicar_calendario`.

        ATENÇÃO — `tkcalendar` só aceita cores em string simples
        ("#FFFFFF"). Os pares `(claro, escuro)` do `tema.py` são
        uma convenção do CustomTkinter e não podem ir para lá. Daí
        o `[0]` em cada par.
        """
        # Reinicia a seleção provisória, para o calendário abrir
        # limpo (ou com o período atual preenchido, se preferires
        # mais à frente).
        self._selecao_personalizada = None

        janela = ctk.CTkToplevel(self)
        janela.title("Período personalizado")
        janela.geometry("420x460")
        janela.resizable(False, False)
        janela.configure(fg_color=tema.COR_FUNDO)
        janela.transient(self)
        componentes.colocar_no_topo(janela)

        # Cabeçalho — moldura do projeto.
        ctk.CTkLabel(
            janela,
            text="Período personalizado",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            janela,
            text=(
                "Clica no dia de início e no dia de fim. "
                "O intervalo aparece em baixo."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # O `tkcalendar.Calendar` embutido. `selectmode="day"` é o
        # único valor aceite nesta versão.
        calendario = Calendar(
            janela,
            selectmode="day",
            locale="pt_PT",
            date_pattern="yyyy-mm-dd",
            background=tema.COR_FUNDO[0],
            foreground=tema.COR_TEXTO[0],
            selectbackground="#2E8B57",
            selectforeground="#FFFFFF",
            normalbackground=tema.COR_FUNDO[0],
            normalforeground=tema.COR_TEXTO[0],
            weekendbackground=tema.COR_FUNDO[0],
            weekendforeground=tema.COR_TEXTO[0],
            othermonthbackground=tema.LINHA_ALTERNADA[0],
            othermonthforeground=tema.COR_TEXTO_SECUNDARIO[0],
            headersbackground=tema.CABECALHO_TABELA_FUNDO[0],
            headersforeground=tema.COR_TEXTO_SECUNDARIO[0],
            bordercolor=tema.COR_BORDA[0],
            font=("Segoe UI", 10),
            headersfont=("Segoe UI", 9, "bold"),
        )
        calendario.pack(padx=16, pady=(0, 10), fill="both", expand=True)

        # Rótulo que mostra a seleção provisória, em baixo do
        # calendário. Atualizado a cada clique.
        self._rotulo_selecao = ctk.CTkLabel(
            janela,
            text="Sem seleção — clica no primeiro dia.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        )
        self._rotulo_selecao.pack(anchor="w", padx=16, pady=(0, 6))

        # O clique num dia passa a chamar `_clicar_dia`, que
        # implementa o intervalo em dois cliques.
        calendario.bind(
            "<<CalendarSelected>>",
            lambda _e: self._clicar_dia(calendario),
        )

        # Rodapé — Cancelar / Aplicar.
        rodape = ctk.CTkFrame(janela, fg_color="transparent")
        rodape.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=110,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            font=ctk.CTkFont(size=11),
            command=janela.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Aplicar",
            width=110,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._aplicar_calendario(janela, calendario),
        ).pack(side="right")

    def _clicar_dia(self, calendario):
        """Regista um clique num dia do calendário, gerindo o
        intervalo em dois cliques (início, depois fim).

        O primeiro clique grava a data como início; o segundo
        grava-a como fim (e, se for anterior ao início, troca as
        duas — o utilizador não devia ser obrigado a clicar da
        esquerda para a direita). Um terceiro clique reinicia:
        passa a ser o novo início.

        Atualiza o rótulo `self._rotulo_selecao` para o utilizador
        ver o que está escolhido.
        """
        try:
            escolhida = calendario.selection_get()
        except Exception:
            return

        if hasattr(escolhida, "date"):
            escolhida = escolhida.date()

        atual = self._selecao_personalizada

        if atual is None:
            # Primeiro clique: início.
            self._selecao_personalizada = (escolhida, None)
            texto = (
                f"Início: {escolhida.strftime('%d/%m/%Y')} "
                f"— clica no dia de fim."
            )
        elif atual[1] is None:
            # Segundo clique: fim.
            inicio, _ = atual
            if escolhida < inicio:
                # Troca — o utilizador clicou o fim antes do início.
                inicio, escolhida = escolhida, inicio
            self._selecao_personalizada = (inicio, escolhida)
            texto = (
                f"Período: {inicio.strftime('%d/%m/%Y')} a "
                f"{escolhida.strftime('%d/%m/%Y')}"
            )
        else:
            # Terceiro clique: reinicia com o novo início.
            self._selecao_personalizada = (escolhida, None)
            texto = (
                f"Início: {escolhida.strftime('%d/%m/%Y')} "
                f"— clica no dia de fim."
            )

        self._rotulo_selecao.configure(text=texto)

    def _aplicar_calendario(self, janela, calendario):
        """Lê o intervalo escolhido, converte-o, e redesenha o
        relatório com o período novo.

        A seleção vem de `self._selecao_personalizada` (o
        intervalo em dois cliques que o `_clicar_dia` construiu) —
        NÃO de `calendario.selection_get()`, que nesta versão do
        `tkcalendar` devolve só o último dia clicado. É `None`
        enquanto o utilizador não clicou em dois dias.
        """
        if (
            self._selecao_personalizada is None
            or self._selecao_personalizada[1] is None
        ):
            componentes.mostrar_erro(
                "Escolhe o dia de início e o dia de fim, com dois " "cliques."
            )
            return

        inicio, fim = self._selecao_personalizada

        try:
            self.data_inicio, self.data_fim = _intervalo_personalizado(
                inicio, fim
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.periodo_atual = PERIODO_PERSONALIZADO
        self._destacar_periodo(PERIODO_PERSONALIZADO)
        self._atualizar_campo_periodo()

        janela.destroy()
        self._recarregar_conteudo()

    # =================================================================
    # RELATÓRIOS — ÁREA FINANCEIRO
    # =================================================================

    # -- helpers partilhados pelos desenhadores ----------------------

    def _titulo_relatorio(self, master, titulo):
        """Escreve a linha de título acima da tabela.

        Ex.: `RESULTADO · 01/09/2026 → 19/09/2026`. Se o relatório
        não aplica período (só o "Stock atual"), mostra só o título,
        sem a parte do período.
        """
        if self._relatorio_atual_aplica_periodo():
            inicio, fim = self._intervalo_visivel_atual()
            texto = f"{titulo.upper()} · {inicio.strftime('%d/%m/%Y')} → {fim.strftime('%d/%m/%Y')}"
        else:
            texto = titulo.upper()

        ctk.CTkLabel(
            master,
            text=texto,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

    def _intervalo_visivel_atual(self):
        """Devolve as duas pontas inclusivas do período atual — para
        mostrar no título do relatório.

        Se o período for personalizado, tem de inverter o +1 dia
        que está em `self.data_fim`.
        """
        if self.periodo_atual == PERIODO_PERSONALIZADO:
            return self.data_inicio, self.data_fim - timedelta(days=1)
        return _intervalo_visivel(self.periodo_atual)

    def _rodape_export(self, master, relatorio_id, colunas, linhas):
        """Botões de exportação no fim do relatório.

        Três botões, alinhados à direita, pela ordem visual
        (esquerda → direita): PDF · CSV · Excel.

        Como `pack(side="right")` empilha da direita para a esquerda
        (o primeiro empacotado fica mais à direita), a ordem das
        chamadas é a inversa da ordem visual: Excel primeiro, CSV a
        seguir, PDF por último.

        Cores (handoff 3.4):
        - PDF   → AZUL_PRINCIPAL (fundo azul, texto branco)
        - CSV   → transparente com borda
        - Excel → VERDE
        """
        rodape = ctk.CTkFrame(master, fg_color="transparent")
        rodape.pack(fill="x", pady=(14, 0))

        # Excel — o primeiro empacotado, fica mais à direita.
        ctk.CTkButton(
            rodape,
            text="Exportar Excel",
            width=120,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._exportar(
                relatorio_id, colunas, linhas, formato="excel"
            ),
        ).pack(side="right", padx=(12, 0))

        # CSV — o do meio.
        ctk.CTkButton(
            rodape,
            text="Exportar CSV",
            width=120,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._exportar(
                relatorio_id, colunas, linhas, formato="csv"
            ),
        ).pack(side="right", padx=(12, 0))

        # PDF — o último empacotado, fica mais à esquerda.
        ctk.CTkButton(
            rodape,
            text="Exportar PDF",
            width=120,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._exportar(
                relatorio_id, colunas, linhas, formato="pdf"
            ),
        ).pack(side="right", padx=(12, 0))

    def _exportar(self, relatorio_id, colunas, linhas, formato):
        """Gera o ficheiro de exportação e abre-o no sistema.

        `formato` é "pdf", "csv" ou "excel". Os três usam os mesmos
        dados (`colunas` e `linhas`), já formatados pelo desenhador
        do relatório.
        """

        # Título do relatório — para o cabeçalho do ficheiro.
        titulo = ""
        for rel in RELATORIOS[self.area]:
            if rel["id"] == relatorio_id:
                titulo = rel["titulo"]
                break

        # Datas do intervalo — as pontas inclusivas, como o
        # utilizador as vê. O ficheiro exportado reflete o que está
        # no ecrã, não o intervalo interno do motor.
        inicio, fim = self._intervalo_visivel_atual()

        try:
            if formato == "csv":
                separador = _perguntar_separador_csv(self)
                if separador is None:
                    # Utilizador cancelou — não gera nada.
                    return

                caminho = impressao.gerar_relatorio_csv(
                    titulo=titulo,
                    colunas=colunas,
                    linhas=linhas,
                    area=self.area,
                    relatorio_id=relatorio_id,
                    data_inicio=inicio,
                    data_fim=fim,
                    separador=separador,
                )
            elif formato == "pdf":
                caminho = impressao.gerar_relatorio_pdf(
                    titulo=titulo,
                    colunas=colunas,
                    linhas=linhas,
                    area=self.area,
                    relatorio_id=relatorio_id,
                    data_inicio=inicio,
                    data_fim=fim,
                )
            elif formato == "excel":
                caminho = impressao.gerar_relatorio_excel(
                    titulo=titulo,
                    colunas=colunas,
                    linhas=linhas,
                    area=self.area,
                    relatorio_id=relatorio_id,
                    data_inicio=inicio,
                    data_fim=fim,
                )
            else:
                componentes.mostrar_erro(
                    f"Formato de exportação desconhecido: {formato}"
                )
                return
        except Exception as erro:
            componentes.mostrar_erro(
                f"Erro ao gerar o ficheiro {formato.upper()}: {erro}"
            )
            return

        # Abre o ficheiro no sistema — mesma função que o
        # `_ImprimirContratoModal` usa para abrir o PDF do contrato.
        self._abrir_no_sistema(caminho)

        componentes.mostrar_sucesso(
            f"Ficheiro {formato.upper()} gerado e aberto:\n{caminho}"
        )

    @staticmethod
    def _abrir_no_sistema(caminho):
        """Abre um ficheiro no programa por omissão do sistema.

        Mesma função do `_ImprimirContratoModal` (gui_contratos.py):
        `os.startfile` no Windows, `open` no macOS, `xdg-open` no
        Linux. Erros de abertura são silenciosos — o ficheiro já
        está no disco, o utilizador pode abri-lo à mão.
        """
        import os
        import subprocess
        import sys

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(caminho))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(caminho)])
            else:
                subprocess.Popen(["xdg-open", str(caminho)])
        except (FileNotFoundError, OSError):
            pass

    # -- 1. RESULTADO -------------------------------------------------

    def _desenhar_resultado(self, master):
        """Relatório "Resultado" — 4 KPIs + COGS em linha à parte +
        tabela com os cinco números.

        O `financeiro.resultado` devolve cinco valores; quatro são
        monetários (Receita, Descontos, Despesas operacionais,
        Resultado líquido) e um é quantidade (COGS). Os quatro
        monetários vão para os cartões de KPI; o COGS fica numa
        linha separada, com nota — não é dinheiro.
        """
        dados = financeiro.resultado(self.data_inicio, self.data_fim)

        self._titulo_relatorio(master, "Resultado")

        # ---- 4 KPIs -------------------------------------------------
        kpis = ctk.CTkFrame(master, fg_color="transparent")
        kpis.pack(fill="x", pady=(0, 14))
        for coluna in range(4):
            kpis.grid_columnconfigure(coluna, weight=1, uniform="kpi")

        receita = dados["receita"]
        descontos = dados["descontos"]
        despesas_op = dados["despesas_operacionais"]
        resultado_liquido = dados["resultado_liquido"]

        # Cor do resultado: verde se positivo, vermelho se negativo.
        # Os outros três ficam em cor neutra — não é uma "boa" ou
        # "má" notícia, é um número.
        cor_resultado = (
            tema.TEXTO_LIVRE if resultado_liquido >= 0 else tema.TEXTO_ERRO
        )

        cartoes = (
            ("Receita", _formatar_valor(receita), tema.COR_TEXTO),
            ("Descontos", f"-{_formatar_valor(descontos)}", tema.COR_TEXTO),
            ("Despesas", f"-{_formatar_valor(despesas_op)}", tema.COR_TEXTO),
            ("Resultado", _formatar_valor(resultado_liquido), cor_resultado),
        )

        for indice, (rotulo, valor, cor) in enumerate(cartoes):
            self._kpi(kpis, indice, rotulo, valor, cor)

        # ---- Tabela -------------------------------------------------
        colunas = (
            componentes.Coluna("Eixo", peso=3, minimo=220),
            componentes.Coluna("Valor", peso=1, minimo=140, alinhamento="e"),
        )

        linhas = (
            ("Receita mensal", self._receita_mensal_do_periodo()),
            ("Receita Airbnb", self._receita_airbnb_do_periodo()),
            ("Descontos", descontos),
            ("Despesas operacionais", despesas_op),
            ("Resultado líquido", resultado_liquido),
        )

        tabela = componentes.Tabela(
            master,
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
                    text_color=(
                        tema.COR_TEXTO
                        if rotulo != "Resultado líquido"
                        else tema.COR_TEXTO
                    ),
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
                        else tema.COR_TEXTO
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

    def _receita_mensal_do_periodo(self):
        """Soma a receita das ocupações do tipo mensal no período.

        Não há no `financeiro.py` uma função que devolva só a
        receita mensal — a `receita_por_unidade` já devolve o total
        misturado (mensal + airbnb). Para o relatório "Resultado"
        precisamos da separação; é feita aqui, em cima das
        ocupações do período.
        """
        # Reaproveita o mesmo mecanismo do `financeiro.py`: lê as
        # ocupações que tocaram o período, e soma mês a mês.
        import contratos as _contratos

        meses = financeiro._meses_do_periodo(self.data_inicio, self.data_fim)
        ocupacoes = financeiro._listar_ocupacoes_do_periodo(
            self.data_inicio, self.data_fim, tipo="mensal"
        )

        total = Decimal("0.00")
        for ocupacao in ocupacoes:
            mensal = _contratos.detalhes_mensal(ocupacao["id"])
            if mensal is None:
                continue
            meses_vigorados = financeiro._meses_de_vigencia_no_periodo(
                ocupacao, meses
            )
            total += mensal["renda_praticada"] * meses_vigorados

        return total.quantize(Decimal("0.01"))

    def _receita_airbnb_do_periodo(self):
        """Soma a receita das ocupações do tipo airbnb no período,
        com rateio por noites — mesma lógica do `financeiro.py`.
        """
        import contratos as _contratos

        ocupacoes = financeiro._listar_ocupacoes_do_periodo(
            self.data_inicio, self.data_fim, tipo="airbnb"
        )

        total = Decimal("0.00")
        for ocupacao in ocupacoes:
            airbnb = _contratos.detalhes_airbnb(ocupacao["id"])
            if airbnb is None:
                continue

            noites_totais = financeiro._noites_totais(ocupacao)
            noites_periodo = financeiro._noites_no_periodo(
                ocupacao, self.data_inicio, self.data_fim
            )

            if noites_totais == 0 or noites_periodo == 0:
                continue

            total += financeiro._ratear(
                airbnb["preco_praticado"],
                noites_periodo,
                noites_totais,
            )

        return total.quantize(Decimal("0.01"))

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
                    text=(
                        f"-{_formatar_valor(item['desconto'])}"
                        if item["desconto"] > 0
                        else _formatar_valor(Decimal("0.00"))
                    ),
                    text_color=(
                        tema.TEXTO_ERRO
                        if item["desconto"] > 0
                        else tema.COR_TEXTO
                    ),
                    font=ctk.CTkFont(size=12),
                    anchor="e",
                ),
            )

            linhas_export.append(
                [
                    f"{nome} ({item['unidade_id']})",
                    item["receita"],
                    item["desconto"],
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
                    text=(
                        f"-{_formatar_valor(item['desconto'])}"
                        if item["desconto"] > 0
                        else _formatar_valor(Decimal("0.00"))
                    ),
                    text_color=(
                        tema.TEXTO_ERRO
                        if item["desconto"] > 0
                        else tema.COR_TEXTO
                    ),
                    font=ctk.CTkFont(size=12),
                    anchor="e",
                ),
            )

            linhas_export.append(
                [
                    f"{item['propriedade_nome']} ({item['propriedade_id']})",
                    item["receita"],
                    item["desconto"],
                ]
            )

        # Linha de total — fundo destacado, negrito, borda azul.
        linha_total = tabela.nova_linha()
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
                text=(
                    f"-{_formatar_valor(total_desconto)}"
                    if total_desconto > 0
                    else _formatar_valor(Decimal("0.00"))
                ),
                text_color=(
                    tema.TEXTO_ERRO
                    if total_desconto > 0
                    else tema.AZUL_PRINCIPAL
                ),
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="e",
            ),
        )

        linhas_export.append(
            [
                f"TOTAL ({len(linhas)} propriedades)",
                total_receita,
                total_desconto,
            ]
        )

        self._rodape_export(
            master,
            "receita_propriedade",
            colunas=("Propriedade", "Receita", "Desconto"),
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
        linha_total = tabela.nova_linha()
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

    # =================================================================
    # RELATÓRIOS — ÁREA CONTRATOS
    # =================================================================

    def _ocupacao_toca_periodo(self, ocupacao):
        """Verifica se uma ocupação tocou o período atual.

        Fórmula de sobreposição do `contratos._sobrepoe`:
            inicio_A < fim_B  E  (fim_A IS NULL  OU  fim_A > inicio_B)

        `self.data_fim` é exclusivo (o +1 dia do motor), por isso
        usar aqui diretamente é correto — uma ocupação que acaba
        exactamente no dia `self.data_fim - 1` é tocada, e uma que
        começa no `self.data_fim` não é.
        """
        inicio = ocupacao["data_inicio"]
        fim = ocupacao["data_fim"]

        if inicio >= self.data_fim:
            return False
        if fim is not None and fim <= self.data_inicio:
            return False
        return True

    # -- 6. OCUPAÇÕES NO PERÍODO --------------------------------------

    def _desenhar_ocupacoes(self, master):
        """Relatório "Ocupações no período" — listagem de registos
        individuais. Sem total.
        """
        todas = contratos.listar(incluir_inativas=True)
        tocadas = [o for o in todas if self._ocupacao_toca_periodo(o)]

        # Ordena por data de início, mais recentes primeiro.
        tocadas.sort(
            key=lambda o: o["data_inicio"] or date.min,
            reverse=True,
        )

        # Mapas de unidades e clientes — uma leitura só cada, em
        # memória.
        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))
        mapa_clientes = _mapa_por_id(clientes.listar(incluir_inativos=True))

        self._titulo_relatorio(master, "Ocupações no período")

        colunas = (
            componentes.Coluna("ID", minimo=110, espaco=6),
            componentes.Coluna("Unidade", peso=3, minimo=180),
            componentes.Coluna("Cliente", peso=3, minimo=160),
            componentes.Coluna("Tipo", minimo=80, alinhamento="centro"),
            componentes.Coluna("Início", minimo=100, alinhamento="centro"),
            componentes.Coluna("Fim", minimo=100, alinhamento="centro"),
            componentes.Coluna("Estado", minimo=100, alinhamento="centro"),
            componentes.Coluna(
                "Aviso doc.", minimo=100, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            colunas=colunas,
            altura_linha=52,
            mensagem_vazia="Sem ocupações no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not tocadas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "ocupacoes",
                colunas=(
                    "ID",
                    "Unidade",
                    "Cliente",
                    "Tipo",
                    "Início",
                    "Fim",
                    "Estado",
                    "Aviso doc.",
                ),
                linhas=[],
            )
            return

        linhas_export = []
        for ocupacao in tocadas:
            unidade = mapa_unidades.get(ocupacao["unidade_id"])
            cliente = mapa_clientes.get(ocupacao["cliente_id"])
            nome_unidade = (
                unidade["nome"] if unidade else ocupacao["unidade_id"]
            )
            nome_cliente = (
                cliente["nome"] if cliente else ocupacao["cliente_id"]
            )

            estado = "ativo" if ocupacao["ativo"] else "encerrado"
            cor_estado = (
                tema.TEXTO_LIVRE
                if ocupacao["ativo"]
                else tema.TEXTO_INDISPONIVEL
            )
            fundo_estado = (
                tema.VERDE_LIVRE
                if ocupacao["ativo"]
                else tema.CINZA_INDISPONIVEL
            )

            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["id"],
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
                    text=_celula_entidade(
                        nome_unidade, ocupacao["unidade_id"]
                    ),
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
                    text=_celula_entidade(
                        nome_cliente, ocupacao["cliente_id"]
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["tipo"],
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_inicio"]),
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
                    text=_formatar_data(ocupacao["data_fim"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=estado,
                    text_color=cor_estado,
                    fg_color=fundo_estado,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text="⚠ doc." if ocupacao["aviso_documento"] else "",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=(
                        tema.AMARELO_AVISO
                        if ocupacao["aviso_documento"]
                        else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            linhas_export.append(
                [
                    ocupacao["id"],
                    f"{nome_unidade} ({ocupacao['unidade_id']})",
                    f"{nome_cliente} ({ocupacao['cliente_id']})",
                    ocupacao["tipo"],
                    ocupacao["data_inicio"],
                    ocupacao["data_fim"],
                    estado,
                    "Sim" if ocupacao["aviso_documento"] else "Não",
                ]
            )

        self._rodape_export(
            master,
            "ocupacoes",
            colunas=(
                "ID",
                "Unidade",
                "Cliente",
                "Tipo",
                "Início",
                "Fim",
                "Estado",
                "Aviso doc.",
            ),
            linhas=linhas_export,
        )

    # -- 7. CONTRATOS MENSAIS -----------------------------------------

    def _desenhar_contratos_mensais(self, master):
        """Relatório "Contratos mensais" — colunas específicas do
        regime mensal (renda, caução, vencimento, autorização).
        """
        todas = contratos.listar(incluir_inativas=True, tipo="mensal")
        tocadas = [o for o in todas if self._ocupacao_toca_periodo(o)]
        tocadas.sort(
            key=lambda o: o["data_inicio"] or date.min,
            reverse=True,
        )

        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))
        mapa_clientes = _mapa_por_id(clientes.listar(incluir_inativos=True))

        self._titulo_relatorio(master, "Contratos mensais")

        colunas = (
            componentes.Coluna("ID", minimo=100, espaco=6),
            componentes.Coluna("Unidade", peso=2, minimo=150),
            componentes.Coluna("Cliente", peso=2, minimo=140),
            componentes.Coluna("Início", minimo=95, alinhamento="centro"),
            componentes.Coluna("Fim", minimo=95, alinhamento="centro"),
            componentes.Coluna("Renda calc.", minimo=100, alinhamento="e"),
            componentes.Coluna("Renda prat.", minimo=100, alinhamento="e"),
            componentes.Coluna("Caução", minimo=95, alinhamento="e"),
            componentes.Coluna("Venc.", minimo=60, alinhamento="centro"),
            componentes.Coluna("Autoriz.", minimo=90, alinhamento="centro"),
            componentes.Coluna(
                "Estado", minimo=95, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            colunas=colunas,
            altura_linha=52,
            mensagem_vazia="Sem contratos mensais no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not tocadas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "contratos_mensais",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []
        for ocupacao in tocadas:
            mensal = contratos.detalhes_mensal(ocupacao["id"])
            if mensal is None:
                # Inconsistência nos dados — salta em vez de rebentar.
                continue

            unidade = mapa_unidades.get(ocupacao["unidade_id"])
            cliente = mapa_clientes.get(ocupacao["cliente_id"])
            nome_unidade = (
                unidade["nome"] if unidade else ocupacao["unidade_id"]
            )
            nome_cliente = (
                cliente["nome"] if cliente else ocupacao["cliente_id"]
            )

            renda_calc = mensal["renda_calculada"]
            renda_prat = mensal["renda_praticada"]
            tem_desconto = renda_prat < renda_calc

            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["id"],
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
                    text=_celula_entidade(
                        nome_unidade, ocupacao["unidade_id"]
                    ),
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
                    text=nome_cliente,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_inicio"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_fim"]),
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
                    text=_formatar_valor(renda_calc),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(renda_prat),
                    text_color=(
                        tema.TEXTO_ERRO if tem_desconto else tema.COR_TEXTO
                    ),
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(mensal["caucao"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            tabela.colocar(
                linha,
                8,
                ctk.CTkLabel(
                    linha,
                    text=str(mensal["dia_vencimento"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                9,
                ctk.CTkLabel(
                    linha,
                    text=(
                        mensal["responsavel_desconto_renda_id"]
                        if tem_desconto
                        else ""
                    ),
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=(
                        tema.ID_CHIP_FUNDO if tem_desconto else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                10,
                ctk.CTkLabel(
                    linha,
                    text="ativo" if ocupacao["ativo"] else "encerrado",
                    text_color=(
                        tema.TEXTO_LIVRE
                        if ocupacao["ativo"]
                        else tema.TEXTO_INDISPONIVEL
                    ),
                    fg_color=(
                        tema.VERDE_LIVRE
                        if ocupacao["ativo"]
                        else tema.CINZA_INDISPONIVEL
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            linhas_export.append(
                [
                    ocupacao["id"],
                    f"{nome_unidade} ({ocupacao['unidade_id']})",
                    nome_cliente,
                    ocupacao["data_inicio"],
                    ocupacao["data_fim"],
                    renda_calc,
                    renda_prat,
                    mensal["caucao"],
                    mensal["dia_vencimento"],
                    (
                        mensal["responsavel_desconto_renda_id"]
                        if tem_desconto
                        else ""
                    ),
                    "ativo" if ocupacao["ativo"] else "encerrado",
                ]
            )

        self._rodape_export(
            master,
            "contratos_mensais",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )

    # -- 8. RESERVAS AIRBNB -------------------------------------------

    def _desenhar_reservas_airbnb(self, master):
        """Relatório "Reservas Airbnb" — colunas específicas do
        regime airbnb (preço, check-in tardio, multas, autorizações).
        """
        todas = contratos.listar(incluir_inativas=True, tipo="airbnb")
        tocadas = [o for o in todas if self._ocupacao_toca_periodo(o)]
        tocadas.sort(
            key=lambda o: o["data_inicio"] or date.min,
            reverse=True,
        )

        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))
        mapa_clientes = _mapa_por_id(clientes.listar(incluir_inativos=True))

        self._titulo_relatorio(master, "Reservas Airbnb")

        colunas = (
            componentes.Coluna("ID", minimo=95, espaco=6),
            componentes.Coluna("Unidade", peso=2, minimo=140),
            componentes.Coluna("Cliente", peso=2, minimo=130),
            componentes.Coluna("Início", minimo=95, alinhamento="centro"),
            componentes.Coluna("Fim", minimo=95, alinhamento="centro"),
            componentes.Coluna("Preço calc.", minimo=100, alinhamento="e"),
            componentes.Coluna("Preço prat.", minimo=100, alinhamento="e"),
            componentes.Coluna("Check-in", minimo=85, alinhamento="centro"),
            componentes.Coluna("Hora", minimo=60, alinhamento="centro"),
            componentes.Coluna("Multa calc.", minimo=95, alinhamento="e"),
            componentes.Coluna("Multa prat.", minimo=95, alinhamento="e"),
            componentes.Coluna("Aut. preço", minimo=90, alinhamento="centro"),
            componentes.Coluna("Aut. multa", minimo=90, alinhamento="centro"),
            componentes.Coluna(
                "Estado", minimo=90, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            colunas=colunas,
            altura_linha=52,
            mensagem_vazia="Sem reservas Airbnb no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not tocadas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "reservas_airbnb",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []
        for ocupacao in tocadas:
            airbnb = contratos.detalhes_airbnb(ocupacao["id"])
            if airbnb is None:
                continue

            unidade = mapa_unidades.get(ocupacao["unidade_id"])
            cliente = mapa_clientes.get(ocupacao["cliente_id"])
            nome_unidade = (
                unidade["nome"] if unidade else ocupacao["unidade_id"]
            )
            nome_cliente = (
                cliente["nome"] if cliente else ocupacao["cliente_id"]
            )

            preco_calc = airbnb["preco_calculado"]
            preco_prat = airbnb["preco_praticado"]
            tem_desc_preco = preco_prat < preco_calc

            tem_checkin_tardio = airbnb["check_in_tardio"]
            multa_calc = airbnb["multa_calculada"]
            multa_prat = airbnb["multa_praticada"]
            tem_desc_multa = tem_checkin_tardio and multa_prat < multa_calc

            linha = tabela.nova_linha()

            # Colunas 0-5
            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["id"],
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
                    text=_celula_entidade(
                        nome_unidade, ocupacao["unidade_id"]
                    ),
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
                    text=nome_cliente,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )
            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_inicio"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_fim"]),
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
                    text=_formatar_valor(preco_calc),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(preco_prat),
                    text_color=(
                        tema.TEXTO_ERRO if tem_desc_preco else tema.COR_TEXTO
                    ),
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            # Check-in tardio + hora
            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text="tardio" if tem_checkin_tardio else "",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=(
                        tema.AMARELO_AVISO
                        if tem_checkin_tardio
                        else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                8,
                ctk.CTkLabel(
                    linha,
                    text=airbnb["hora_chegada"] or "—",
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            # Multas
            tabela.colocar(
                linha,
                9,
                ctk.CTkLabel(
                    linha,
                    text=(
                        _formatar_valor(multa_calc)
                        if tem_checkin_tardio
                        else "—"
                    ),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )
            tabela.colocar(
                linha,
                10,
                ctk.CTkLabel(
                    linha,
                    text=(
                        _formatar_valor(multa_prat)
                        if tem_checkin_tardio
                        else "—"
                    ),
                    text_color=(
                        tema.TEXTO_ERRO if tem_desc_multa else tema.COR_TEXTO
                    ),
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            # Autorizações
            tabela.colocar(
                linha,
                11,
                ctk.CTkLabel(
                    linha,
                    text=(
                        airbnb["responsavel_desconto_preco_id"]
                        if tem_desc_preco
                        else ""
                    ),
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=(
                        tema.ID_CHIP_FUNDO if tem_desc_preco else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )
            tabela.colocar(
                linha,
                12,
                ctk.CTkLabel(
                    linha,
                    text=(
                        airbnb["responsavel_desconto_multa_id"]
                        if tem_desc_multa
                        else ""
                    ),
                    text_color=tema.AZUL_PRINCIPAL,
                    fg_color=(
                        tema.ID_CHIP_FUNDO if tem_desc_multa else "transparent"
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                13,
                ctk.CTkLabel(
                    linha,
                    text="ativa" if ocupacao["ativo"] else "encerrada",
                    text_color=(
                        tema.TEXTO_LIVRE
                        if ocupacao["ativo"]
                        else tema.TEXTO_INDISPONIVEL
                    ),
                    fg_color=(
                        tema.VERDE_LIVRE
                        if ocupacao["ativo"]
                        else tema.CINZA_INDISPONIVEL
                    ),
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="center",
                ),
            )

            linhas_export.append(
                [
                    ocupacao["id"],
                    f"{nome_unidade} ({ocupacao['unidade_id']})",
                    nome_cliente,
                    ocupacao["data_inicio"],
                    ocupacao["data_fim"],
                    preco_calc,
                    preco_prat,
                    "Sim" if tem_checkin_tardio else "Não",
                    airbnb["hora_chegada"] or "",
                    multa_calc if tem_checkin_tardio else None,
                    multa_prat if tem_checkin_tardio else None,
                    (
                        airbnb["responsavel_desconto_preco_id"]
                        if tem_desc_preco
                        else ""
                    ),
                    (
                        airbnb["responsavel_desconto_multa_id"]
                        if tem_desc_multa
                        else ""
                    ),
                    "ativa" if ocupacao["ativo"] else "encerrada",
                ]
            )

        self._rodape_export(
            master,
            "reservas_airbnb",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )

    # -- 9. ENCERRAMENTOS ---------------------------------------------

    def _desenhar_encerramentos(self, master):
        """Relatório "Encerramentos" — contratos mensais encerrados
        fora das regras da casa: duração abaixo do mínimo OU aviso
        prévio insuficiente.

        A flag `duracao_abaixo_minima` e `aviso_previo_insuficiente`
        já são gravadas pelo `contratos.encerrar_mensal`, no registo
        `ocupacoes_mensal`. Aqui só se filtram os que têm pelo menos
        uma das duas — o resto dos encerramentos (dentro das regras)
        não aparece.

        Listagem individual, sem total — como as outras listagens
        da área Contratos. A coluna Avisos mostra um chip por cada
        condição; um contrato pode ter os dois em simultâneo.
        """
        # ---- 1. Ler todas as ocupações mensais (ativas e encerradas)
        todas = contratos.listar(incluir_inativas=True, tipo="mensal")

        # ---- 2. Filtrar as que têm pelo menos um dos avisos
        # O detalhe mensal é lido uma vez por ocupação. Como o
        # volume é pequeno, não vale a pena otimizar com mapas.
        candidatas = []

        for ocupacao in todas:
            mensal = contratos.detalhes_mensal(ocupacao["id"])
            if mensal is None:
                continue

            if not (
                mensal["duracao_abaixo_minima"]
                or mensal["aviso_previo_insuficiente"]
            ):
                continue

            candidatas.append((ocupacao, mensal))

        # ---- 3. Ordenar por data de fim, mais recentes primeiro
        candidatas.sort(
            key=lambda par: par[0]["data_fim"] or date.min,
            reverse=True,
        )

        # ---- 4. Mapas de unidades e clientes — uma leitura só
        mapa_unidades = _mapa_por_id(unidades.listar(incluir_inativas=True))
        mapa_clientes = _mapa_por_id(clientes.listar(incluir_inativos=True))

        self._titulo_relatorio(master, "Encerramentos")

        colunas = (
            componentes.Coluna("ID", minimo=100, espaco=6),
            componentes.Coluna("Unidade", peso=2, minimo=150),
            componentes.Coluna("Cliente", peso=2, minimo=140),
            componentes.Coluna("Início", minimo=95, alinhamento="centro"),
            componentes.Coluna("Fim", minimo=95, alinhamento="centro"),
            componentes.Coluna("Duração", minimo=80, alinhamento="centro"),
            componentes.Coluna("Renda prat.", minimo=105, alinhamento="e"),
            componentes.Coluna("Motivo", peso=3, minimo=180),
            componentes.Coluna(
                "Avisos", minimo=150, alinhamento="centro", espaco=8
            ),
        )

        tabela = componentes.Tabela(
            master,
            colunas=colunas,
            altura_linha=52,
            mensagem_vazia="Sem encerramentos fora das regras no período.",
            tom_alternado=True,
        )
        tabela.pack(fill="x")

        if not candidatas:
            tabela.mostrar_vazio()
            self._rodape_export(
                master,
                "encerramentos",
                colunas=tuple(c.titulo for c in colunas),
                linhas=[],
            )
            return

        linhas_export = []

        for ocupacao, mensal in candidatas:
            unidade = mapa_unidades.get(ocupacao["unidade_id"])
            cliente = mapa_clientes.get(ocupacao["cliente_id"])
            nome_unidade = (
                unidade["nome"] if unidade else ocupacao["unidade_id"]
            )
            nome_cliente = (
                cliente["nome"] if cliente else ocupacao["cliente_id"]
            )

            # Duração em meses — mesma fórmula do
            # `contratos.avisos_encerramento` e do
            # `financeiro._meses_do_periodo`. Diferença simples
            # entre anos/meses, sem dias.
            inicio = ocupacao["data_inicio"]
            fim = ocupacao["data_fim"] or date.today()
            meses = (fim.year - inicio.year) * 12 + (fim.month - inicio.month)
            texto_duracao = f"{meses} mes" if meses == 1 else f"{meses} meses"

            texto_motivo = mensal["motivo_encerramento"] or "—"

            # Dois chips possíveis — um ou os dois podem estar
            # presentes. Desenhados num bloco horizontal, ao lado
            # um do outro, com uma folga pequena.
            linha = tabela.nova_linha()

            tabela.colocar(
                linha,
                0,
                ctk.CTkLabel(
                    linha,
                    text=ocupacao["id"],
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
                    text=_celula_entidade(
                        nome_unidade, ocupacao["unidade_id"]
                    ),
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
                    text=nome_cliente,
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    justify="left",
                ),
            )

            tabela.colocar(
                linha,
                3,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_inicio"]),
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                4,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_data(ocupacao["data_fim"]),
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
                    text=texto_duracao,
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="center",
                ),
            )

            tabela.colocar(
                linha,
                6,
                ctk.CTkLabel(
                    linha,
                    text=_formatar_valor(mensal["renda_praticada"]),
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=11),
                    anchor="e",
                ),
            )

            tabela.colocar(
                linha,
                7,
                ctk.CTkLabel(
                    linha,
                    text=texto_motivo,
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=10),
                    anchor="w",
                    justify="left",
                ),
            )

            # Bloco de chips de aviso. Dois podem estar ativos ao
            # mesmo tempo; a coluna tem 150px, cabem lado a lado.
            bloco_avisos = ctk.CTkFrame(
                linha, fg_color="transparent", height=24
            )
            bloco_avisos.pack_propagate(False)

            if mensal["duracao_abaixo_minima"]:
                ctk.CTkLabel(
                    bloco_avisos,
                    text="curto",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    padx=8,
                    pady=2,
                ).pack(side="left")

            if mensal["aviso_previo_insuficiente"]:
                ctk.CTkLabel(
                    bloco_avisos,
                    text="aviso",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    padx=8,
                    pady=2,
                ).pack(side="left", padx=(6, 0))

            tabela.colocar(linha, 8, bloco_avisos)

            linhas_export.append(
                [
                    ocupacao["id"],
                    f"{nome_unidade} ({ocupacao['unidade_id']})",
                    nome_cliente,
                    ocupacao["data_inicio"],
                    ocupacao["data_fim"],
                    texto_duracao,
                    mensal["renda_praticada"],
                    texto_motivo,
                    # Os avisos vão como texto simples para o CSV/
                    # Excel — o chip é só uma apresentação.
                    " / ".join(
                        filter(
                            None,
                            (
                                (
                                    "curto"
                                    if mensal["duracao_abaixo_minima"]
                                    else None
                                ),
                                (
                                    "aviso"
                                    if mensal["aviso_previo_insuficiente"]
                                    else None
                                ),
                            ),
                        )
                    ),
                ]
            )

        self._rodape_export(
            master,
            "encerramentos",
            colunas=tuple(c.titulo for c in colunas),
            linhas=linhas_export,
        )

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

            combo = ctk.CTkOptionMenu(
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


def _perguntar_separador_csv(janela_pai):
    """Pergunta ao utilizador qual separador usar no CSV.

    Abre um modal pequeno, no estilo do projeto, com duas opções:
    "Ponto e vírgula (;)" (por omissão — o que o Excel em PT-PT
    costuma abrir corretamente) ou "Vírgula (,)" (para instalações
    que preferem a convenção inglesa).

    Devolve `";"`, `","` ou `None` se o utilizador cancelar.

    O modal é `CTkToplevel`, bloqueante (`wait_window`), para o
    `_exportar` poder ler o resultado depois de o utilizador
    escolher. Fecha pela X nativa ou pelo botão Cancelar.
    """
    resultado = {"separador": None}

    janela = ctk.CTkToplevel(janela_pai)
    janela.title("Separador do CSV")
    janela.geometry("380x230")
    janela.resizable(False, False)
    janela.configure(fg_color=tema.COR_FUNDO)
    janela.transient(janela_pai)
    componentes.colocar_no_topo(janela)

    ctk.CTkLabel(
        janela,
        text="Separador do ficheiro CSV",
        text_color=tema.COR_TEXTO,
        font=ctk.CTkFont(size=14, weight="bold"),
    ).pack(anchor="w", padx=20, pady=(18, 4))

    ctk.CTkLabel(
        janela,
        text=(
            "Ponto e vírgula é o que o Excel em PT-PT costuma "
            "abrir corretamente. Vírgula é a convenção inglesa — "
            "usa se o teu Excel abrir tudo na mesma coluna."
        ),
        text_color=tema.COR_TEXTO_SECUNDARIO,
        font=ctk.CTkFont(size=10),
        justify="left",
        wraplength=330,
        anchor="w",
    ).pack(fill="x", padx=20, pady=(0, 12))

    def escolher(valor):
        resultado["separador"] = valor
        janela.destroy()

    ctk.CTkButton(
        janela,
        text="Ponto e vírgula ( ; )",
        height=34,
        corner_radius=tema.RAIO_BOTAO,
        fg_color=tema.AZUL_PRINCIPAL,
        hover_color=tema.AZUL_CLARO,
        font=ctk.CTkFont(size=11, weight="bold"),
        command=lambda: escolher(";"),
    ).pack(fill="x", padx=20, pady=4)

    ctk.CTkButton(
        janela,
        text="Vírgula ( , )",
        height=34,
        corner_radius=tema.RAIO_BOTAO,
        fg_color="transparent",
        border_width=1,
        border_color=tema.COR_BORDA,
        text_color=tema.COR_TEXTO,
        hover_color=tema.COR_BORDA,
        font=ctk.CTkFont(size=11),
        command=lambda: escolher(","),
    ).pack(fill="x", padx=20, pady=4)

    ctk.CTkButton(
        janela,
        text="Cancelar",
        height=28,
        corner_radius=tema.RAIO_BOTAO,
        fg_color="transparent",
        text_color=tema.COR_TEXTO_SECUNDARIO,
        hover_color=tema.COR_BORDA,
        font=ctk.CTkFont(size=10),
        command=janela.destroy,
    ).pack(fill="x", padx=20, pady=(8, 14))

    janela.wait_window()
    return resultado["separador"]


# Alias para o `app.py` continuar a importar `Relatorios` — o
# `app.py` já espera este nome desde a v1.4.0, e não vale a pena
# mudá-lo só por causa do novo nome interno (`EcraRelatorios`).
# Quando o `ITENS_MENU` for revisto (v2.0), pode trocar-se lá e
# apagar isto.
Relatorios = EcraRelatorios
