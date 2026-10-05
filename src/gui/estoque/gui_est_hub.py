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

ALTERAÇÕES 05/10/2026 (v1.9.0, bloco "hubs" — desenho do aluno):

- Os cartões passam a estar em três GRUPOS com título, em vez de uma
  grelha só: "Solicitações e listagem" (Requisições), "Gestão
  Administrativa" (Rota de Envio, Devoluções) e "Gestão de Stock"
  (Produtos, Movimentos). Motivo (aluno): misturava-se o que é para
  criar registos e ver listagens, o que é administrativo e o que é
  catálogo/inventário.
- Cada cartão ganhou a chave "grupo"; a ordem dos grupos está em
  `_GRUPOS`. O desenho do grupo é o `componentes.GrupoCartoesHub`,
  partilhado com o hub de Despesas. Títulos e descrições dos cartões
  não mudaram.
- Permissões: o cartão Devoluções passa a ser só de Admin/Master
  (decisão do aluno) — o Staff vê só Requisições. Um grupo sem
  cartões visíveis não aparece.
- O selo "por implementar" (cartões com `ecra` None) saiu: os cinco
  estão implementados há muito, e o `_abrir_area` continua a avisar
  se um dia aparecer um destino desconhecido.
"""

import customtkinter as ctk

import estoque
from .. import componentes
from .. import sessao
from .. import tema
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
# Grupos do hub, pela ordem em que aparecem (v1.9.0).
_GRUPOS = (
    "Solicitações e listagem",
    "Gestão Administrativa",
    "Gestão de Stock",
)

_AREAS = (
    {
        "grupo": "Solicitações e listagem",
        "titulo": "Requisições",
        "descricao": "Pedir material e acompanhar os pedidos",
        "ecra": "requisicoes",
        "so_admin": False,
    },
    {
        "grupo": "Gestão Administrativa",
        "titulo": "Rota de Envio",
        "descricao": "Acompanhar e gerir todas as requisições",
        "ecra": "aprovacao",
        "so_admin": True,
    },
    {
        "grupo": "Gestão Administrativa",
        "titulo": "Devoluções",
        "descricao": "Aceitar sobras de material (administrativo)",
        "ecra": "devolucoes",
        # v1.9.0 (aluno): só administrativo. O Staff reporta sobras
        # no "Gerir" da própria requisição; aceitá-las é do Admin.
        "so_admin": True,
    },
    {
        "grupo": "Gestão de Stock",
        "titulo": "Produtos",
        "descricao": "Catálogo, unidade de medida e stock mínimo",
        "ecra": "produtos",
        "so_admin": True,
    },
    {
        "grupo": "Gestão de Stock",
        "titulo": "Movimentos",
        "descricao": "Entradas de compra e ajustes de inventário",
        "ecra": "movimentos",
        "so_admin": True,
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

        # FASE 4 — visibilidade por perfil. Staff só vê os cartões
        # marcados com so_admin=False (desde a v1.9.0, só Requisições);
        # Admin/Master vê todos. v1.9.0: os cartões vão para o seu
        # grupo, e um grupo que fique sem cartões não se desenha.
        tipo = sessao.tipo_utilizador_ativo()
        e_administrativo = tipo in ("Admin", "Master")

        for nome_grupo in _GRUPOS:
            grupo = componentes.GrupoCartoesHub(
                self, nome_grupo, cor_borda=tema.AZUL_PRINCIPAL
            )

            for item in _AREAS:
                if item["grupo"] != nome_grupo:
                    continue
                if item.get("so_admin") and not e_administrativo:
                    continue

                grupo.adicionar(
                    item["titulo"],
                    item["descricao"],
                    lambda area=item: self._abrir_area(area),
                )

            if grupo.vazio:
                grupo.destroy()
                continue

            grupo.pack(fill="x", padx=14, pady=(0, 12))

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

    def _abrir_area(self, area):
        # FASE 4 — dupla barreira: o cartão já não aparece ao Staff
        # (o `_AREAS` tem `so_admin`), mas se por algum motivo este
        # método for chamado com uma área administrativa num perfil
        # Staff, recusa antes de navegar. É a mesma disciplina do
        # resto do sistema: a barreira de negócio não pode depender
        # da GUI ter escondido o botão.
        if area.get("so_admin"):
            tipo = sessao.tipo_utilizador_ativo()

            if tipo not in ("Admin", "Master"):
                componentes.mostrar_erro(
                    "Só Admin/Master podem aceder a esta área."
                )
                return

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
