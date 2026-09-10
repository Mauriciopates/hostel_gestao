"""Hub do módulo Stock: a primeira coisa que se vê ao clicar em
"Stock" na barra lateral.

Tem três partes:

- `_AREAS` — a lista dos quatro cartões (Requisições, Devoluções,
  Produtos, Movimentos). Cada um aponta para o ecrã de destino; o
  destino pode ser None, e nesse caso o cartão avisa em vez de
  navegar (por agora, nenhum é None — os quatro estão implementados).

- `EcraStock` — a classe do ecrã em si. Faixa de alertas de reposição
  no topo (`estoque.listar_alertas_stock`) e a grelha 2×2 de cartões
  clicáveis.

- `_abrir_area` — o método que troca o ecrã consoante o cartão
  clicado. Delega sempre para `controlador.mostrar_frame(...)` com a
  classe do ecrã correspondente.

Este ficheiro é o antigo `gui_estoque.py`, partido em cinco. O que
era um ficheiro de 1200 linhas com 7 classes — no limite do que dá
para navegar — passa a ser cinco ficheiros focados:
`gui_est_hub.py` (este), `gui_est_produtos.py`,
`gui_est_movimentos.py`, `gui_est_requisicoes.py` e
`gui_est_devolucoes.py`. O prefixo `gui_est_` deixa claro que são
irmãos debaixo do mesmo módulo de negócio.
"""

import customtkinter as ctk

import estoque
from . import componentes
from . import tema
from .gui_est_devolucoes import ListaDevolucoes
from .gui_est_movimentos import ListaMovimentos
from .gui_est_produtos import ListaProdutos
from .gui_est_requisicoes import ListaRequisicoes


# Áreas do hub. 'ecra' a None significa "ainda por implementar": o
# cartão continua clicável, mas avisa em vez de navegar — assim o
# módulo mostra-se todo, sem cartões que não reagem ao clique.
_AREAS = (
    {
        "titulo": "Requisições",
        "descricao": "Pedir material e acompanhar os pedidos",
        "ecra": "requisicoes",
    },
    {
        "titulo": "Devoluções",
        "descricao": "Reportar e aceitar sobras de material",
        "ecra": "devolucoes",
    },
    {
        "titulo": "Produtos",
        "descricao": "Catálogo, unidade de medida e stock mínimo",
        "ecra": "produtos",
    },
    {
        "titulo": "Movimentos",
        "descricao": "Entradas de compra e ajustes de inventário",
        "ecra": "movimentos",
    },
)

# Altura fixa dos cartões do hub (a largura estica — ver
# `EcraStock._desenhar_cartao`).
_ALTURA_CARTAO_AREA = 110


class EcraStock(ctk.CTkFrame):
    """Hub do módulo Stock: alertas de reposição e cartões de área."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Stock").pack(fill="x")

        self._desenhar_alertas()

        ctk.CTkLabel(
            self,
            text="Selecionar área",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(4, 8))

        # Grelha esticada de ponta a ponta (duas colunas de peso
        # igual) — com quatro cartões enche a grelha 2×2 sem sobrar
        # nenhum sozinho numa 3.ª linha.
        grelha = ctk.CTkFrame(self, fg_color="transparent")
        grelha.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        grelha.grid_columnconfigure(0, weight=1, uniform="areas")
        grelha.grid_columnconfigure(1, weight=1, uniform="areas")

        for indice, item in enumerate(_AREAS):
            self._desenhar_cartao(grelha, item, indice)

    def _desenhar_alertas(self):
        """Faixa amarela com os produtos abaixo do stock mínimo.

        Só aparece quando há alguma coisa a repor — uma faixa
        permanente a dizer "0 produtos" era ruído fixo no topo do
        ecrã. A ordem vem do negócio (o que falta mais primeiro),
        não é reordenada aqui.
        """
        try:
            alertas = estoque.listar_alertas_stock()
        except ValueError:
            return

        if not alertas:
            return

        faixa = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        faixa.pack(fill="x", padx=20, pady=(4, 8))

        nomes = ", ".join(a["produto"]["nome"] for a in alertas[:4])

        if len(alertas) > 4:
            nomes += ", …"

        ctk.CTkLabel(
            faixa,
            text=f"{len(alertas)} produtos abaixo do mínimo: {nomes}.",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=12, pady=8)

    def _desenhar_cartao(self, master, area, indice):
        cartao = ctk.CTkFrame(
            master,
            height=_ALTURA_CARTAO_AREA,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=(
                tema.AZUL_PRINCIPAL if area["ecra"] else tema.COR_BORDA
            ),
            fg_color=tema.COR_FUNDO,
        )
        cartao.grid(
            row=indice // 2,
            column=indice % 2,
            sticky="nsew",
            padx=6,
            pady=6,
        )
        cartao.grid_propagate(False)

        ativo = area["ecra"] is not None

        ctk.CTkLabel(
            cartao,
            text=area["titulo"],
            text_color=(tema.COR_TEXTO if ativo else tema.TEXTO_INDISPONIVEL),
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            cartao,
            text=area["descricao"],
            text_color=(
                tema.COR_TEXTO_SECUNDARIO if ativo else tema.TEXTO_INDISPONIVEL
            ),
            font=ctk.CTkFont(size=11),
        ).pack()

        if not ativo:
            ctk.CTkLabel(
                cartao,
                text="por implementar",
                text_color=tema.TEXTO_INDISPONIVEL,
                fg_color=tema.CINZA_INDISPONIVEL,
                corner_radius=tema.RAIO_CAMPO,
                font=ctk.CTkFont(size=10),
                padx=10,
                pady=2,
            ).pack(pady=(8, 0))

        componentes.tornar_cliclavel(cartao, lambda: self._abrir_area(area))

    def _abrir_area(self, area):
        if area["ecra"] == "requisicoes":
            self.controlador.mostrar_frame(ListaRequisicoes)
            return

        if area["ecra"] == "devolucoes":
            self.controlador.mostrar_frame(ListaDevolucoes)
            return

        if area["ecra"] == "produtos":
            self.controlador.mostrar_frame(ListaProdutos)
            return

        if area["ecra"] == "movimentos":
            self.controlador.mostrar_frame(ListaMovimentos)
            return

        componentes.mostrar_erro(
            f"A área \"{area['titulo']}\" ainda não está "
            "implementada nesta versão.",
            titulo="Por implementar",
        )