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

ALTERAÇÕES 05/10/2026 (v1.9.0, bloco "hubs" — desenho do aluno):

- Os quatro cartões passam a estar em três GRUPOS com título:
  "Lançamentos" (Despesas), "Gestão Administrativa" (Aprovações) e
  "Gestão complementar de despesas" (Categorias, Fornecedores). O
  desenho é o `componentes.GrupoCartoesHub`, partilhado com o hub de
  Stock. Títulos e descrições dos cartões não mudaram.
"""

import logging

import customtkinter as ctk

import despesas
from .. import componentes
from .. import sessao
from .. import tema
from .gui_desp_lista import ListaDespesas
from .gui_desp_aprovacao import Aprovacoes
from .gui_desp_categorias import Categorias
from .gui_desp_fornecedores import Fornecedores


logger = logging.getLogger(__name__)


# =====================================================================
# ECRÃ HUB — EcraDespesas (4 cartões em 3 grupos)
# =====================================================================


class EcraDespesas(ctk.CTkFrame):
    """Hub do módulo Despesas — 4 cartões em 3 grupos com título.

    Mesmo estilo do `EcraStock` (gui_est_hub.py): os grupos são
    `componentes.GrupoCartoesHub`, cada cartão é clicável em qualquer
    ponto, e a navegação é feita por `controlador.mostrar_frame`.
    """

    # (grupo, título, descrição, classe de destino) — a ordem é a de
    # apresentação no Hub; os grupos aparecem pela ordem em que
    # surgem aqui.
    _AREAS = (
        (
            "Lançamentos",
            "Despesas",
            "Lançar despesas manuais (EDP, água, internet) e "
            "despesas via stock. Consultar e filtrar histórico.",
            "ListaDespesas",
        ),
        (
            "Gestão Administrativa",
            "Aprovações",
            "Despesas pendentes a marcar como pagas ou a cancelar. "
            "Itens de stock por confirmar.",
            "Aprovacoes",
        ),
        (
            "Gestão complementar de despesas",
            "Categorias",
            "Criar, editar e desativar categorias de despesa.",
            "Categorias",
        ),
        (
            "Gestão complementar de despesas",
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

        grupos = {}
        for nome_grupo, titulo, descricao, destino in self._AREAS:
            if nome_grupo not in grupos:
                grupos[nome_grupo] = componentes.GrupoCartoesHub(
                    self, nome_grupo
                )
                grupos[nome_grupo].pack(fill="x", padx=14, pady=(0, 12))

            grupos[nome_grupo].adicionar(
                titulo, descricao, lambda d=destino: self._abrir(d)
            )

        # Depois de o ecrã aparecer: um aviso a meio da construção
        # abria antes de o ecrã estar desenhado.
        self.after(200, self._gerar_recorrencias)

    def _gerar_recorrencias(self):
        """Lança as despesas recorrentes do mês (28/09/2026).

        O `despesas.gerar_recorrencias_pendentes` existia e estava
        testado, mas nenhum ecrã o chamava: marcar uma despesa como
        "recorrente" não tinha efeito nenhum. O docstring dele diz
        que corre "ao abrir o ecrã de despesas" — é aqui. Não
        duplica: cada cadeia só ganha um lançamento por mês.
        """
        if not self.winfo_exists():
            return

        try:
            geradas = despesas.gerar_recorrencias_pendentes(
                sessao.obter_responsavel_ativo()
            )
        except ValueError as erro:
            # Staff (ou sessão vazia) não lança despesas — não é erro
            # para mostrar, só para registar.
            logger.info("Recorrências não geradas: %s", erro)
            return

        if not geradas:
            return

        n = len(geradas)
        if n == 1:
            frase = "1 despesa recorrente foi lançada"
        else:
            frase = f"{n} despesas recorrentes foram lançadas"

        componentes.mostrar_sucesso(
            f"{frase} "
            "para este mês, com o valor a 0,00 €.\n\n"
            "Preencha o valor em Despesas (botão Gerir da linha) antes "
            "de a marcar como paga.",
            titulo="Despesas recorrentes",
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
