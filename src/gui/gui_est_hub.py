"""Hub do módulo Stock: a primeira coisa que se vê ao clicar em
"Stock" na barra lateral.

Tem três partes:

- `_AREAS` — a lista dos cinco cartões (Requisições, Aprovação de
  Requisições, Devoluções, Produtos, Movimentos). Cada um aponta
  para o ecrã de destino; o destino pode ser None, e nesse caso o
  cartão avisa em vez de navegar (por agora, nenhum é None — os
  cinco estão implementados).

- `EcraStock` — a classe do ecrã em si. Faixa de alertas de reposição
  no topo (`estoque.listar_alertas_stock`) e a grelha de cartões
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

ALTERAÇÕES 13/09/2026 (Aprovação de Requisições):

- O cartão "Aprovação de Requisições" entra como segundo item do
  `_AREAS`, a seguir às Requisições — decisão do aluno, ao fechar
  o fluxo de Stock: o admin precisa de um ecrã próprio para as
  requisições pendentes, separado da lista geral (que serve o
  staff para pedir e acompanhar). A descrição do cartão Devoluções
  ganha "(administrativo)", para distinguir do "Reportar sobra"
  que o staff faz dentro do Gerir de uma requisição fechada.

- Os cartões passam a crescer com o conteúdo (sem `height` fixo em
  `_ALTURA_CARTAO_AREA`), porque a descrição do cartão novo é mais
  comprida do que as outras e ficava a bater na borda de baixo com
  a altura fixa anterior. A grelha ganha margem inferior para
  respirar.
"""

import customtkinter as ctk

import estoque
from . import componentes
from . import tema
from .gui_est_aprovacao import ListaAprovacao
from .gui_est_devolucoes import ListaDevolucoes
from .gui_est_movimentos import ListaMovimentos
from .gui_est_produtos import ListaProdutos
from .gui_est_requisicoes import ListaRequisicoes


# Áreas do hub. 'ecra' a None significa "ainda por implementar": o
# cartão continua clicável, mas avisa em vez de navegar — assim o
# módulo mostra-se todo, sem cartões que não reagem ao clique.
#
# Ordem: Requisições primeiro (é o que a maioria dos utilizadores
# usa), Aprovação a seguir (é o par natural — quem aprova olha para
# este logo depois), depois Devoluções, Produtos e Movimentos.
_AREAS = (
    {
        "titulo": "Requisições",
        "descricao": "Pedir material e acompanhar os pedidos",
        "ecra": "requisicoes",
    },
    {
        "titulo": "Aprovação de Requisições",
        "descricao": "Aprovar ou rejeitar pedidos pendentes",
        "ecra": "aprovacao",
    },
    {
        "titulo": "Devoluções",
        "descricao": "Aceitar sobras de material (administrativo)",
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
        # igual). Com cinco cartões, a última linha fica com um
        # cartão só — o `sticky="nsew"` faz com que ele ocupe
        # metade da largura, alinhado à esquerda, sem se esticar
        # pela linha inteira (que ficava estranho).
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
        """Desenha um cartão da grelha do hub.

        O cartão cresce com o conteúdo (sem `height` fixo) — a
        descrição do cartão "Aprovação de Requisições" é mais
        comprida do que as outras, e a altura fixa anterior
        cortava-a a meio em certas larguras de janela.

        O `pady` interno no `pack` do título e da descrição dá a
        folga que antes não existia, e que era a causa do texto
        bater na borda de baixo.
        """
        cartao = ctk.CTkFrame(
            master,
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

        ativo = area["ecra"] is not None

        ctk.CTkLabel(
            cartao,
            text=area["titulo"],
            text_color=(tema.COR_TEXTO if ativo else tema.TEXTO_INDISPONIVEL),
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(20, 6), padx=16)

        ctk.CTkLabel(
            cartao,
            text=area["descricao"],
            text_color=(
                tema.COR_TEXTO_SECUNDARIO if ativo else tema.TEXTO_INDISPONIVEL
            ),
            font=ctk.CTkFont(size=11),
            wraplength=320,
            justify="center",
        ).pack(padx=16, pady=(0, 18))

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
            ).pack(pady=(0, 16))

        componentes.tornar_cliclavel(cartao, lambda: self._abrir_area(area))

    def _abrir_area(self, area):
        if area["ecra"] == "requisicoes":
            self.controlador.mostrar_frame(ListaRequisicoes)
            return

        if area["ecra"] == "aprovacao":
            self.controlador.mostrar_frame(ListaAprovacao)
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