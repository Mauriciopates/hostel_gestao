"""Ecrã de Relatórios — placeholder.

Decisão do aluno, 13/09/2026: fica por implementar. O item existe
na barra lateral (secção "SISTEMA") para a estrutura do menu estar
completa desde já, e o ecrã que ele abre diz claramente que ainda
não faz nada — em vez de o item não existir e a secção ficar com
um buraco.

O que vai lá viver (ideias, por ordem de valor):

1. Receita por mês — barras verticais dos últimos 6 meses,
   mensal e Airbnb em séries separadas. É a métrica que qualquer
   gestor quer ver; foi deixada de fora do Dashboard exatamente
   para dar razão de existir a este ecrã.

2. Taxa de ocupação média por propriedade — uma tabela simples,
   "Propriedade | Unidades | Ocupação média 30d | Receita 30d".

3. Clientes por regime — quantos mensais, quantos Airbnb, ao
   longo do tempo. Útil para perceber de que lado está a crescer
   o negócio.

4. Exportação para CSV — botão que despeja a tabela ou o
   gráfico em ficheiro, para o utilizador abrir no Excel.

A infraestrutura de gráficos já existe (`componentes_graficos.py`,
criado em 13/09/2026 para o Dashboard) — quando este ecrã for
implementado, é só acrescentar uma subclasse `Grafico` nova
(ex.: `GraficoReceitaMensal`) sem tocar em nada do que já está
feito.
"""

import customtkinter as ctk

from . import componentes
from . import tema


class Relatorios(ctk.CTkFrame):
    """Ecrã placeholder — cabeçalho + cartão "por implementar"."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Relatórios").pack(fill="x")

        # Área central: um cartão ao meio do ecrã, com a mensagem.
        # `expand=True` no `pack` faz com que fique centrado
        # verticalmente — sem isto, ficava encostado ao topo e
        # parecia que faltava conteúdo por baixo.
        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.pack(expand=True, fill="both")

        cartao = ctk.CTkFrame(
            centro,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(expand=True, padx=40, pady=40)

        ctk.CTkLabel(
            cartao,
            text="Relatórios",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(padx=40, pady=(30, 8))

        ctk.CTkLabel(
            cartao,
            text="Por implementar.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=13),
        ).pack(padx=40, pady=(0, 6))

        ctk.CTkLabel(
            cartao,
            text=(
                "Esta área vai mostrar receita por mês, taxa de\n"
                "ocupação por propriedade e exportação para CSV."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="center",
        ).pack(padx=40, pady=(0, 30))