import customtkinter as ctk

from . import tema
from . import componentes
from .gui_clientes import ListaClientes
from .gui_contratos import ListaContratosMensais, ListaReservasAirbnb
from .gui_calendario import Calendario
from .gui_estoque import EcraStock
from .gui_propriedades import ListaPropriedades

# Itens da barra lateral — lista simples, sem secções (decisão do
# aluno, 07/09/2026: só 4 ecrãs por agora, secções ficam para quando
# houver mais — Stock, Responsáveis, Dashboard). Ordem pensada pelo
# fluxo de trabalho: primeiro o que se cadastra (Gestão de
# Propriedades, Clientes), depois o que se consulta/usa a partir daí
# (Contrato Mensal, Reservas Airbnb).
#
# 07/09/2026: "Novo Contrato Mensal" saiu da barra lateral — ficava
# parecido demais com "Contrato Mensal" (a lista), um debaixo do
# outro, só a palavra "Novo" a distinguir. Agora só é acessível pelo
# botão "+ Novo Contrato" dentro do próprio ecrã "Contrato Mensal"
# (ver ListaContratosMensais/NovoContratoModal, gui_contratos.py).
# "Contratos e Reservas" (um ecrã só, com dropdown de tipo) também
# saiu — decisão do aluno de separar em dois itens já filtrados,
# "Contrato Mensal" e "Reservas Airbnb", em vez de escolher o tipo
# lá dentro.
#
# 07/09/2026 (mesmo dia, ronda seguinte): "Propriedades e Unidades"
# passou a "Gestão de Propriedades" e "Planta de Lugares" saiu da
# lista — deixou de ser um ecrã à parte, só se chega lá pelo botão
# "Abrir" de uma unidade mensal dentro do popup de unidades de
# ListaPropriedades (ver ponto 10 do docstring de gui_propriedades.
# py). PlantaLugares deixou de ser importada aqui — quem chama
# `mostrar_frame(PlantaLugares, ...)` agora é o próprio
# gui_propriedades.py, que já a importa para isso.
ITENS_MENU = [
    {
        "tipo": "item",
        "texto": "Gestão de Propriedades",
        "ecra": ListaPropriedades,
    },
    {"tipo": "item", "texto": "Clientes", "ecra": ListaClientes},
    {
        "tipo": "item",
        "texto": "Contrato Mensal",
        "ecra": ListaContratosMensais,
    },
    {
        "tipo": "item",
        "texto": "Reservas Airbnb",
        "ecra": ListaReservasAirbnb,
    },
    # 08/09/2026: "Calendário" entra como 5.º item, ainda sem
    # secções (a lista simples continua a ser a decisão em vigor).
    # O ecrã em si só mostra os dois cartões de regime — a grelha
    # da semana abre em popup a partir daí, para não ficar presa à
    # largura da área de conteúdo (ver gui_calendario.py).
    {"tipo": "item", "texto": "Calendário", "ecra": Calendario},
    # 08/09/2026: o item chama-se "Stock", e não "Requisições",
    # porque o hub que ele abre já tem lá dentro um cartão
    # "Requisições" — o mesmo nome nos dois sítios repetia o
    # problema corrigido em 07/09 entre "Contrato Mensal" e
    # "Novo Contrato Mensal". As outras quatro áreas do módulo
    # (Aprovação, Devoluções, Produtos, Movimentos) estão
    # desenhadas no hub mas ainda por implementar.
    {"tipo": "item", "texto": "Stock", "ecra": EcraStock},
]


class Aplicacao(ctk.CTk):
    """Janela principal da aplicação. Estrutura fixa: barra lateral
    de navegação à esquerda (altura toda da janela), área de
    conteúdo à direita — onde os frames de cada ecrã são trocados
    consoante a navegação (decisão: tudo em frames dentro desta
    janela, exceto diálogos pontuais, que usam CTkToplevel). Cada
    ecrã traz o seu próprio cabeçalho (componentes.Cabecalho); não
    há cabeçalho global.
    """

    def __init__(self):
        tema.aplicar_tema()
        super().__init__()

        self.title("Hostel Clean — Gestão de Alojamento")
        # Janela redimensionável, com maximizar/minimizar (07/09/2026
        # — pedido do aluno: o tamanho fixo, sem margem nenhuma, era
        # parte do aperto que as tabelas sentiam para caber tudo).
        # Tamanho de arranque um pouco maior do que o fixo de antes
        # (900x700); `minsize` evita encolher a ponto de as colunas
        # deixarem de caber — grid_columnconfigure(1, weight=1) logo
        # abaixo já fazia a área de conteúdo esticar, só faltava
        # permitir à própria janela esticar também.
        self.geometry("1100x700")
        self.minsize(950, 620)
        self.resizable(True, True)
        self.configure(fg_color=tema.COR_FUNDO)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sem cabeçalho global: cada ecrã já traz o seu próprio
        # componentes.Cabecalho (decisão desde a Parte 2) — um frame
        # extra aqui só criava uma faixa vazia acima do menu e do
        # ecrã, sem função nenhuma (visível pela primeira vez agora
        # que a barra lateral é real). Decisão do aluno, 07/09/2026.
        self.barra_lateral = componentes.BarraLateral(
            self, controlador=self, itens=ITENS_MENU
        )
        self.barra_lateral.configure(width=150)
        self.barra_lateral.grid(row=0, column=0, sticky="ns")
        self.barra_lateral.grid_propagate(False)

        self.area_conteudo = ctk.CTkFrame(
            self, corner_radius=0, fg_color=tema.COR_FUNDO
        )
        self.area_conteudo.grid(row=0, column=1, sticky="nsew")

        self.frame_atual = None

        # Ecrã inicial ao arrancar a aplicação (decisão do aluno,
        # 07/09/2026): Gestão de Propriedades — é o ponto de partida
        # lógico do fluxo, enquanto não existir Dashboard.
        self.mostrar_frame(ListaPropriedades)

    def mostrar_frame(self, classe_frame, **kwargs):
        """Troca o ecrã atual pelo indicado em classe_frame.

        Destrói o frame anterior (se existir) e cria uma nova
        instância de classe_frame dentro de area_conteudo, passando-
        -se a si própria como "controlador" — é assim que o ecrã
        chama de volta mostrar_frame para navegar para outro, ou
        acede a coisas partilhadas (ex. sessao). kwargs são
        argumentos extra específicos do ecrã (ex.: o id de uma
        unidade a abrir).
        """
        if self.frame_atual is not None:
            self.frame_atual.destroy()

        self.frame_atual = classe_frame(
            self.area_conteudo, controlador=self, **kwargs
        )
        self.frame_atual.pack(fill="both", expand=True)
