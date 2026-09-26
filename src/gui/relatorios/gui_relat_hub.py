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

ALTERAÇÕES 26/09/2026 (divisão em ficheiros):

- O antigo `gui_relatorios.py` (4 297 linhas) foi dividido:
  gui_relat_hub (este: EcraRelatorios + classe final
  RelatorioModal), gui_relat_base (RelatorioBase: layout,
  período, exportar), gui_relat_financeiro / _contratos /
  _stock (desenhadores por área, subclasses da base) e
  gui_relat_comum (constantes + helpers). Métodos movidos
  sem alterações.
"""

import customtkinter as ctk

from .. import componentes
from .. import tema
from .gui_relat_comum import AREAS
from .gui_relat_contratos import RelatContratos
from .gui_relat_financeiro import RelatFinanceiro
from .gui_relat_stock import RelatStock


# =====================================================================
# ECRÃ HUB — EcraRelatorios
# =====================================================================


class EcraRelatorios(ctk.CTkFrame):
    """Hub de Relatórios — 3 cartões clicáveis.

    Mesmo estilo do `EcraStock` (gui_est_hub.py) e do `EcraDespesas`
    (gui_desp_hub.py): um cartão por área, cada um com título e
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


class RelatorioModal(RelatFinanceiro, RelatContratos, RelatStock):
    """Popup de relatórios de UMA área — a classe que o hub abre.

    Junta a `RelatorioBase` (layout, período, calendário, exportar)
    com os desenhadores das três áreas. A base despacha por
    `getattr(self, f"_desenhar_{id}")`, por isso cada desenhador
    pode viver no ficheiro da sua área sem a base o conhecer.
    """


# Alias para o `app.py` continuar a importar `Relatorios` — o
# `app.py` já espera este nome desde a v1.4.0, e não vale a pena
# mudá-lo só por causa do novo nome interno (`EcraRelatorios`).
# Quando o `ITENS_MENU` for revisto (v2.0), pode trocar-se lá e
# apagar isto.
Relatorios = EcraRelatorios
