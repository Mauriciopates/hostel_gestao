import datetime

import customtkinter as ctk

from . import tema
from . import sessao


class BarraLateral(ctk.CTkFrame):
    """Barra lateral de navegação. Recebe uma lista de itens — cada
    um ou uma secção (rótulo não clicável, ex. "MENSAL") ou um item
    de navegação (rótulo + ecrã de destino) — e monta os widgets
    correspondentes. Não sabe nada sobre os ecrãs reais: quem decide
    o que lá vai é quem a instancia (app.py), por isso dá para testar
    com ecrãs falsos sem Unidades/Clientes/etc. já existirem.
    """

    def __init__(self, master, controlador, itens):
        super().__init__(master, corner_radius=0, fg_color=tema.NAVY_ESCURO)

        for item in itens:
            if item["tipo"] == "secao":
                ctk.CTkLabel(
                    self,
                    text=item["texto"],
                    text_color=tema.COR_TEXTO_SIDEBAR_SECAO,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ).pack(fill="x", padx=16, pady=(16, 4))
            else:
                ctk.CTkButton(
                    self,
                    text=item["texto"],
                    fg_color="transparent",
                    text_color=tema.COR_TEXTO_SIDEBAR,
                    hover_color=tema.AZUL_PRINCIPAL,
                    corner_radius=tema.RAIO_BOTAO,
                    anchor="w",
                    command=lambda ecra=item["ecra"]: controlador.mostrar_frame(ecra),
                ).pack(fill="x", padx=8, pady=2)

class Cabecalho(ctk.CTkFrame):
    """Cabeçalho comum a todos os ecrãs: título à esquerda, data e
    responsável ativo à direita. O título é o único parâmetro — data
    e responsável vêm sempre de sessao.obter_responsavel_ativo().
    """

    def __init__(self, master, titulo):
        super().__init__(master, corner_radius=0, fg_color=tema.COR_FUNDO)

        ctk.CTkLabel(
            self,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left", padx=20, pady=15)

        responsavel = sessao.obter_responsavel_ativo()
        nome = responsavel["nome"] if responsavel else "sem responsável"
        hoje = datetime.date.today().strftime("%d/%m/%Y")

        ctk.CTkLabel(
            self,
            text=f"{hoje} · {nome}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=20)