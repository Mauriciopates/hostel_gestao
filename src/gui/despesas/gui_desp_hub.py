"""GUI do módulo de Despesas — ecrãs e modais.

Contém quatro ecrãs principais ligados pelo Hub (`EcraDespesas`):

- `ListaDespesas` — o ecrã "Despesas" da sidebar. Lista todas as
  despesas lançadas, com filtros (categoria, estado, unidade, "só
  vencidas") e o botão "+ Nova Despesa" que abre o popup intermédio
  de escolha de via (A.3a — VIA 1 ou VIA 2).

- `Aprovacoes` — as despesas pendentes (para marcar como pagas ou
  cancelar) e os itens de despesas VIA 2 por confirmar. Segue o
  padrão do `gui_est_aprovacao.py` do Stock.

- `Categorias` — gestão de categorias de despesa.

- `Fornecedores` — gestão de fornecedores.

Segue a mesma disciplina de camadas do resto da GUI (decisão 7):
só fala com `despesas` (o módulo de negócio) e com os módulos que
ele precisa (`responsaveis`, `unidades`, `propriedades`, `estoque`
via `despesas`); nunca fala com o `repositorio` diretamente.

Os modais estão agrupados por via (VIA 1, VIA 2) e por tipo de
entidade, seguindo o padrão dos outros módulos da GUI. Todos
usam os helpers partilhados de `componentes.py` (`mostrar_erro`,
`mostrar_sucesso`, `confirmar`, `colocar_no_topo`, `centrar_sobre`,
`tornar_cliclavel`, `formatar_valor`, `Cabecalho`, `Tabela`).

ALTERAÇÕES 26/09/2026 (divisão em ficheiros):

- O antigo `gui_despesas.py` (4 645 linhas) foi dividido
  por ecrã, como os `gui_est_*` do Stock: gui_desp_hub
  (este), gui_desp_lista, gui_desp_manual (VIA 1),
  gui_desp_stock (VIA 2), gui_desp_aprovacao,
  gui_desp_categorias, gui_desp_fornecedores e
  gui_desp_comum (helpers). Código movido sem alterações.
"""

import customtkinter as ctk

from .. import componentes
from .. import tema
from .gui_desp_lista import ListaDespesas
from .gui_desp_aprovacao import Aprovacoes
from .gui_desp_categorias import Categorias
from .gui_desp_fornecedores import Fornecedores


# =====================================================================
# ECRÃ HUB — EcraDespesas (4 cartões)
# =====================================================================


class EcraDespesas(ctk.CTkFrame):
    """Hub do módulo Despesas — 4 cartões em grelha 2×2.

    Mesmo estilo do `EcraStock` (gui_est_hub.py): cada cartão é
    clicável em qualquer ponto (via `componentes.tornar_cliclavel`),
    e a navegação é feita por `controlador.mostrar_frame`.
    """

    # Pares (título, descrição, classe de destino) — a ordem é a
    # ordem de apresentação no Hub.
    _AREAS = (
        (
            "Despesas",
            "Lançar despesas manuais (EDP, água, internet) e "
            "despesas via stock. Consultar e filtrar histórico.",
            "ListaDespesas",
        ),
        (
            "Aprovações",
            "Despesas pendentes a marcar como pagas ou a cancelar. "
            "Itens de stock por confirmar.",
            "Aprovacoes",
        ),
        (
            "Categorias",
            "Criar, editar e desativar categorias de despesa.",
            "Categorias",
        ),
        (
            "Fornecedores",
            "Criar, editar e desativar fornecedores de despesas.",
            "Fornecedores",
        ),
    )

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Despesas").pack(fill="x")

        ctk.CTkLabel(
            self,
            text="Selecionar área",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(4, 8))

        grelha = ctk.CTkFrame(self, fg_color="transparent")
        grelha.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        grelha.grid_columnconfigure(0, weight=1, uniform="areas")
        grelha.grid_columnconfigure(1, weight=1, uniform="areas")

        for indice, (titulo, descricao, destino) in enumerate(self._AREAS):
            self._desenhar_cartao(grelha, titulo, descricao, destino, indice)

    def _desenhar_cartao(self, master, titulo, descricao, destino, indice):
        cartao = ctk.CTkFrame(
            master,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.grid(
            row=indice // 2,
            column=indice % 2,
            sticky="nsew",
            padx=6,
            pady=6,
        )

        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(22, 6), padx=16)

        ctk.CTkLabel(
            cartao,
            text=descricao,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=320,
            justify="center",
        ).pack(padx=16, pady=(0, 22))

        # Navegação: o clique resolve o destino por nome (evita
        # import circular — a classe real é procurada em
        # `_resolver_ecra`).
        componentes.tornar_cliclavel(
            cartao,
            lambda d=destino: self._abrir(d),
        )

    def _abrir(self, nome_destino):
        classe = {
            "ListaDespesas": ListaDespesas,
            "Aprovacoes": Aprovacoes,
            "Categorias": Categorias,
            "Fornecedores": Fornecedores,
        }.get(nome_destino)
        if classe is None:
            componentes.mostrar_erro(
                f"Ecrã {nome_destino} não está implementado."
            )
            return
        self.controlador.mostrar_frame(classe)
