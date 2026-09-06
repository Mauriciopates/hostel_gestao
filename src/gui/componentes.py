import datetime
from tkinter import messagebox

import customtkinter as ctk

import config
from . import tema
from . import sessao


def mostrar_erro(mensagem, titulo="Erro"):
    """Mostra um erro num popup nativo (triângulo de aviso, mensagem,
    botão OK) — convenção única de toda a interface gráfica para
    avisos de erro (decisão do aluno, 06/09/2026, ao testar o ecrã
    de Novo Contrato Mensal): substitui a legenda vermelha que cada
    ecrã desenhava por si, por um popup do próprio sistema
    operativo. É bloqueante (o resto do ecrã só volta a responder
    depois de clicar OK), mas não fecha nem limpa nada à volta —
    o formulário fica exatamente como estava, pronto a continuar a
    editar.
    """
    messagebox.showwarning(titulo, mensagem)


def mostrar_sucesso(mensagem, titulo="Sucesso"):
    """Mostra uma confirmação de sucesso num popup nativo (ícone de
    informação, mensagem, botão OK) — mesma convenção de
    mostrar_erro, agora para o caso contrário (decisão do aluno,
    06/09/2026, logo a seguir a pedir o popup de erro): "após criado,
    apareça um pop up, contrato criado com sucesso: CNT-XXX".
    """
    messagebox.showinfo(titulo, mensagem)


class BarraLateral(ctk.CTkFrame):
    """Barra lateral de navegação. Recebe uma lista de itens — cada
    um ou uma secção (rótulo não clicável, ex. "MENSAL") ou um item
    de navegação (rótulo + ecrã de destino) — e monta os widgets
    correspondentes. Não sabe nada sobre os ecrãs reais: quem decide
    o que lá vai é quem a instancia (app.py), por isso dá para testar
    com ecrãs falsos sem Unidades/Clientes/etc. já existirem. Mostra
    sempre a versão do sistema (config.VERSAO) no rodapé (decisão 21).
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

        ctk.CTkLabel(
            self,
            text=f"v{config.VERSAO}",
            text_color=tema.COR_TEXTO_SIDEBAR_SECAO,
            font=ctk.CTkFont(size=9),
        ).pack(side="bottom", pady=10)


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