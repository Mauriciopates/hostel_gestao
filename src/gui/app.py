import customtkinter as ctk

from . import tema


class Aplicacao(ctk.CTk):
    """Janela principal da aplicação. Estrutura fixa: cabeçalho no
    topo, barra lateral de navegação à esquerda, área de conteúdo à
    direita — onde os frames de cada ecrã são trocados consoante a
    navegação (decisão: tudo em frames dentro desta janela, exceto
    diálogos pontuais, que usam CTkToplevel).
    """

    def __init__(self):
        tema.aplicar_tema()
        super().__init__()

        self.title("Hostel Clean — Gestão de Alojamento")
        self.geometry("900x700")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.cabecalho = ctk.CTkFrame(
            self, height=60, corner_radius=0, fg_color=tema.COR_FUNDO
        )
        self.cabecalho.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.cabecalho.grid_propagate(False)

        self.barra_lateral = ctk.CTkFrame(
            self, width=150, corner_radius=0, fg_color=tema.NAVY_ESCURO
        )
        self.barra_lateral.grid(row=1, column=0, sticky="ns")
        self.barra_lateral.grid_propagate(False)

        self.area_conteudo = ctk.CTkFrame(
            self, corner_radius=0, fg_color=tema.COR_FUNDO
        )
        self.area_conteudo.grid(row=1, column=1, sticky="nsew")

        self.frame_atual = None


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