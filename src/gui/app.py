import customtkinter as ctk

from . import tema
from . import componentes
from .clientes import ListaClientes
from .contratos import NovoContratoMensal
from .propriedades import ListaPropriedades
from .unidades import PlantaLugares

# Itens da barra lateral — lista simples, sem secções (decisão do
# aluno, 07/09/2026: só 4 ecrãs por agora, secções ficam para quando
# houver mais — Reservas, Stock, Responsáveis, Dashboard). Ordem
# pensada pelo fluxo de trabalho: primeiro o que se cadastra
# (Propriedades e Unidades, Clientes), depois o que se consulta/usa
# a partir daí (Planta de Lugares, Novo Contrato Mensal).
ITENS_MENU = [
    {
        "tipo": "item",
        "texto": "Propriedades e Unidades",
        "ecra": ListaPropriedades,
    },
    {"tipo": "item", "texto": "Clientes", "ecra": ListaClientes},
    {"tipo": "item", "texto": "Planta de Lugares", "ecra": PlantaLugares},
    {
        "tipo": "item",
        "texto": "Novo Contrato Mensal",
        "ecra": NovoContratoMensal,
    },
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
        self.geometry("900x700")
        self.resizable(False, False)
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
        # 07/09/2026): Propriedades e Unidades — é o ponto de partida
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