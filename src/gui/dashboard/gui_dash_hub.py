"""Dashboard — o ecrã inicial de todos os perfis (v1.6.0).

Substitui o `gui_dashboard.py` (4 KPIs + 2 gráficos + alertas +
ações). Decisões fechadas com o aluno a 27/09/2026, com mockup
aprovado:

- Master e Admin: duas vistas, "Hoje" e "Financeiro", trocadas por
  um seletor no cabeçalho. Abre SEMPRE em "Hoje".
- Staff: uma vista só (limpezas, requisições a confirmar, stock),
  sem seletor e sem valores em euros.

Desempenho — o que torna isto leve:

1. Cada vista só é construída na PRIMEIRA vez que é escolhida. Quem
   nunca abre o Financeiro nunca paga as consultas dele.
2. Uma vista já construída fica guardada; trocar de vista só a
   esconde (`pack_forget`) e mostra a outra — sem voltar à base de
   dados e sem refazer gráficos.
3. Os dados atualizam quando se carrega em "↻ Atualizar" (só a vista
   visível) ou quando se volta ao Dashboard pelo menu (o
   `mostrar_frame` constrói um Dashboard novo). Não há temporizador
   nenhum a correr em fundo.

As regras de quem vê o quê estão em `_VISTAS_POR_PERFIL`; os dados de
cada vista vêm do `painel.py`.
"""

import datetime

import customtkinter as ctk

from .. import componentes
from .. import sessao
from .. import tema
from . import gui_dash_comum as comum
from .gui_dash_financeiro import VistaFinanceiro
from .gui_dash_hoje import VistaHoje
from .gui_dash_staff import VistaStaff

# Vistas de cada perfil, pela ordem do seletor. A primeira é a que
# abre. Um perfil desconhecido fica com a do Staff — a que mostra
# menos (princípio do menor privilégio).
_VISTAS_POR_PERFIL = {
    "Master": (("Hoje", VistaHoje), ("Financeiro", VistaFinanceiro)),
    "Admin": (("Hoje", VistaHoje), ("Financeiro", VistaFinanceiro)),
    "Staff": (("Hoje", VistaStaff),),
}


class Dashboard(ctk.CTkFrame):
    """Ecrã do menu "Dashboard": cabeçalho + vista escolhida."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        self.perfil = sessao.tipo_utilizador_ativo()
        self.opcoes = dict(
            _VISTAS_POR_PERFIL.get(
                self.perfil or "", _VISTAS_POR_PERFIL["Staff"]
            )
        )
        self.vistas = {}
        self.vista_atual = None

        self._construir_cabecalho()

        self.palco = componentes.Contentor(self)
        self.palco.pack(fill="both", expand=True)

        self.mostrar_vista(next(iter(self.opcoes)))

    def _construir_cabecalho(self):
        responsavel = sessao.obter_responsavel_ativo()
        nome = responsavel["nome"] if responsavel else "sem responsável"

        barra = componentes.Contentor(self)
        barra.pack(fill="x", padx=20, pady=(14, 12))

        if self.perfil == "Staff":
            titulo = f"Olá, {nome.split()[0]}" if responsavel else "Olá"
        else:
            titulo = "Dashboard"

        componentes.Rotulo(barra, titulo, "titulo").pack(side="left")

        if len(self.opcoes) > 1:
            componentes.SeletorVistas(
                barra, tuple(self.opcoes), self.mostrar_vista
            ).pack(side="left", padx=(16, 0))

        componentes.Botao(
            barra, "↻ Atualizar", self.atualizar, "contorno"
        ).pack(side="left", padx=(10, 0))

        perfil = f" · {self.perfil}" if self.perfil else ""
        componentes.Rotulo(
            barra,
            f"{comum.data_longa(datetime.date.today())} · {nome}{perfil}",
            "secundario",
        ).pack(side="right")

    def mostrar_vista(self, nome):
        """Mostra a vista `nome`, construindo-a só da primeira vez."""
        if nome not in self.opcoes:
            return

        if self.vista_atual is not None:
            self.vista_atual.pack_forget()

        if nome not in self.vistas:
            classe = self.opcoes[nome]
            self.vistas[nome] = classe(self.palco, self.controlador)

        self.vista_atual = self.vistas[nome]
        self.vista_atual.pack(fill="both", expand=True)

    def atualizar(self):
        """Botão "↻ Atualizar": recarrega a vista visível.

        As outras vistas já construídas são deitadas fora — assim, ao
        voltar a elas, são construídas de novo com dados frescos em
        vez de mostrarem números de antes do "Atualizar".
        """
        for nome, vista in list(self.vistas.items()):
            if vista is not self.vista_atual:
                vista.destroy()
                del self.vistas[nome]

        if self.vista_atual is not None:
            self.vista_atual.atualizar()
