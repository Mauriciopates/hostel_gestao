"""Módulo Stock na interface gráfica.

Sete classes, na ordem em que o utilizador as encontra:

1. `EcraStock` — hub do módulo. Faixa de alertas de reposição no
   topo (`estoque.listar_alertas_stock`) e quatro cartões de área,
   centrados no ecrã (decisão de 09/09/2026, ver ponto 6 abaixo).
   Só "Requisições" e "Devoluções" estão implementados; "Produtos" e
   "Movimentos" avisam e não navegam, para o percurso ser
   demonstrável sem ecrãs mortos.

2. `ListaRequisicoes` — lista das requisições, filtrável por estado
   e por responsável, numa tabela a sério (`componentes.Tabela`,
   igual à de Gestão de Propriedades). Botão "+ Nova requisição" no
   topo e, no fim de cada linha, um botão só — "Gerir" — que abre um
   popup com as ações possíveis para aquele estado.

3. `_AcoesRequisicaoModal` — popup de "Gerir" de uma requisição:
   "Confirmar requisição" / "Rejeitar requisição" numa pendente,
   "Confirmar receção" numa enviada do próprio responsável ativo,
   ou só uma frase informativa nos restantes casos.

4. `_RejeitarRequisicaoModal` — motivo obrigatório antes de
   rejeitar, aberto a partir do "Rejeitar requisição" do Gerir.

5. `ListaDevolucoes` — "Aceitar Sobra (Devolução)", ecrã novo, mesmo
   padrão de tabela + Gerir de ListaRequisicoes, para as devoluções
   pendentes.

6. `_EscolherTipoRequisicaoModal` — popup intermédio do botão
   "+ Nova requisição": pergunta "Requisição Staff" ou "Rol de
   Lavanderia" antes de abrir o formulário certo.

7. `NovaRequisicaoModal` / `RolLavanderiaModal` — os dois
   formulários. O primeiro já existia (cria uma requisição
   "pendente", à espera de ser confirmada); o segundo é novo — cria
   e envia de imediato, sem passar por aprovação, mesma composição
   de `cli.py:_enviar_rol_lavanderia` (criar_requisicao seguido de
   enviar_requisicao numa só operação).

Decisões desta entrega (09/09/2026, mockups aprovados por imagem
antes de codar):

1. "Gerir" substitui os botões soltos por linha em ListaRequisicoes
   (e nasce assim em ListaDevolucoes) — mesmo padrão já usado em
   Gestão de Propriedades (`_AcoesPropriedadeModal`,
   gui_propriedades.py): um botão só, popup com as ações, "Fechar"
   no fim. O aluno já tinha tentado um menu de contexto (CTkMenuBar)
   nessa altura e revertido por dar problemas — o popup fica.
2. O aprovar/rejeitar de uma requisição pendente (antes seria o
   cartão "Aprovação" do hub, nunca implementado) passa a viver
   dentro do próprio Gerir de Requisições — não há ecrã de
   Aprovação à parte. O botão "Confirmar requisição" chama
   `estoque.enviar_requisicao` com a totalidade pedida; o envio
   parcial por item, se vier a ser pedido, fica para depois.
3. O cartão "Aprovação" SAI do hub (decisão do aluno, 09/09/2026):
   com a aprovação a viver dentro de Requisições, um cartão à parte
   que nunca ia ligar a lado nenhum só confundia. Ficam quatro
   cartões — Requisições, Devoluções, Produtos, Movimentos — na
   MESMA grelha 2×2 esticada de sempre (uma tentativa de os centrar
   num bloco de tamanho fixo, a meio do ecrã, foi testada e
   revertida na ronda seguinte: "achei feio os tamanhos, estava bom,
   use o anterior"). Com só quatro cartões a grelha já não sobra
   nenhum sozinho numa 3.ª linha, como acontecia com cinco.
4. "+ Nova requisição" deixa de abrir `NovaRequisicaoModal`
   diretamente: agora abre `_EscolherTipoRequisicaoModal`, a
   perguntar Requisição Staff (o formulário de sempre, fica
   pendente) ou Rol de Lavanderia (envio direto a um responsável,
   sem pedido prévio — o mesmo caso que o CLI já cobria em
   `_enviar_rol_lavanderia`, agora também na GUI).
5. O item da barra lateral chama-se "Stock", não "Requisições": com
   o mesmo nome nos dois sítios repetia-se o problema já corrigido
   em 07/09 entre "Contrato Mensal" e "Novo Contrato Mensal".
6. Nenhuma cor nova em `tema.py`. As etiquetas de estado reaproveitam
   pares já existentes: pendente AMARELO_AVISO, enviada
   ID_CHIP_FUNDO/AZUL_PRINCIPAL, fechada VERDE_LIVRE, rejeitada
   VERMELHO_ERRO.
7. Sem setas Unicode em texto visível ("< Voltar", "X" de remover) —
   o glifo aparecia como quadrado no Windows.
8. Numa linha rejeitada mostra-se o motivo em vez dos produtos: é a
   informação que interessa nesse estado, e `rejeitar_requisicao` já
   obriga a que exista.
9. No modal, "Código" e "Produto" são uma coluna só (um
   CTkOptionMenu com "PRD-001 · Lixívia"): numa requisição nova o
   produto escolhe-se, não se lê, e duas colunas separadas obrigavam
   a escrever o código à mão.

Camadas: este módulo não compara pedidos com saldos nem decide o
que é um alerta. `estoque.avisos_requisicao` devolve as frases
prontas e `estoque.listar_alertas_stock` devolve os produtos a
repor, já ordenados — a interface só as mostra.
"""

import datetime

import customtkinter as ctk

import estoque
import responsaveis
from . import componentes
from . import sessao
from . import tema

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
        "ecra": None,
    },
    {
        "titulo": "Movimentos",
        "descricao": "Entradas de compra e ajustes de inventário",
        "ecra": None,
    },
)

# Estado da requisição/devolução -> (fundo da etiqueta, cor do
# texto). Todos os pares já existiam em tema.py antes desta entrega.
_CORES_ESTADO = {
    "pendente": (tema.AMARELO_AVISO, tema.TEXTO_AVISO),
    "enviada": (tema.ID_CHIP_FUNDO, tema.AZUL_PRINCIPAL),
    "fechada": (tema.VERDE_LIVRE, tema.TEXTO_LIVRE),
    "rejeitada": (tema.VERMELHO_ERRO, tema.TEXTO_ERRO),
}

_OPCAO_TODOS_ESTADOS = "Todos os estados"
_OPCAO_TODOS_RESPONSAVEIS = "Todos os responsáveis"
_ESTADOS_REQUISICAO = ("pendente", "enviada", "fechada", "rejeitada")
_ESTADOS_DEVOLUCAO = ("pendente", "fechada")

# Altura fixa dos cartões do hub (a largura estica, ver
# EcraStock._desenhar_cartao) e largura do popup de "Gerir".
_ALTURA_CARTAO_AREA = 110
_LARGURA_POPUP_ACOES = 320

# Larguras das colunas dos dois formulários de produtos (Requisição
# Staff e Rol de Lavanderia).
_LARGURA_PRODUTO = 240
_LARGURA_ARMAZEM = 90
_LARGURA_PEDIDO = 70

# Altura extra que o popup de Resumo da devolução precisa quando o
# alerta de ajuste de stock aparece (caixa + campo de motivo) — sem
# isto o rodapé com "Aceitar devolução" fica fora da janela, que não
# é redimensionável (09/09/2026, aluno testou e o botão sumiu).
_ALTURA_ALERTA_AJUSTE = 110


def _colocar_no_topo(janela):
    """Traz um popup (CTkToplevel) para a frente da janela principal.

    Mesma função de gui_propriedades.py e gui_calendario.py.
    `after(10, ...)` dá tempo ao Tk para mapear a janela antes de
    `grab_set()`, que de outro modo falha com "grab failed: window
    not viewable" em alguns sistemas.
    """
    janela.after(
        10, lambda: (janela.lift(), janela.focus_force(), janela.grab_set())
    )


def _centrar_sobre(janela, master, largura, altura):
    """Centra um popup (CTkToplevel) sobre a janela que o abriu.

    Mesmo padrão de `_AcoesPropriedadeModal._centrar_sobre`
    (gui_propriedades.py) — sem isto o Tk abre os popups no canto
    superior esquerdo do ecrã, longe do botão que acabou de ser
    clicado.
    """
    master.update_idletasks()
    x = master.winfo_rootx() + (master.winfo_width() - largura) // 2
    y = master.winfo_rooty() + (master.winfo_height() - altura) // 2
    janela.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")


def _tornar_clicavel(widget, ao_clicar):
    """Liga o clique e o cursor de mão a um widget e aos filhos.

    Sem isto, clicar no texto dentro de um cartão não conta como
    clicar no cartão, porque o evento fica no filho.
    """
    widget.bind("<Button-1>", lambda evento: ao_clicar())
    widget.configure(cursor="hand2")

    for filho in widget.winfo_children():
        _tornar_clicavel(filho, ao_clicar)


def _etiqueta_estado(master, estado):
    """Devolve a etiqueta colorida de um estado (requisição ou
    devolução — os dois partilham "pendente"/"fechada").
    """
    fundo, cor_texto = _CORES_ESTADO.get(
        estado, (tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL)
    )

    return ctk.CTkLabel(
        master,
        text=estado,
        text_color=cor_texto,
        fg_color=fundo,
        corner_radius=tema.RAIO_CAMPO,
        font=ctk.CTkFont(size=11, weight="bold"),
        width=100,
    )


def _rotulo_responsavel(registo):
    """Texto "STF-002 · Ana Ribeiro" de um responsável.

    Mesmo formato já usado no ecrã de Gestão de Propriedades, para o
    utilizador reconhecer a mesma pessoa escrita da mesma maneira em
    toda a aplicação.
    """
    return f"{registo['id']} · {registo['nome']}"


def _rotulo_produto(registo):
    """Texto "PRD-001 · Lixívia" de um produto."""
    return f"{registo['id']} · {registo['nome']}"


def _texto_produtos_requisicao(requisicao, produtos):
    """Segunda linha da célula do meio, numa linha de requisição.

    Numa rejeitada mostra o motivo: é o que interessa nesse estado,
    e os produtos já não vão sair do armazém.
    """
    if requisicao["estado"] == "rejeitada":
        return f"motivo: {requisicao['motivo_rejeicao']}"

    itens = estoque.listar_itens_requisicao(requisicao_id=requisicao["id"])

    if not itens:
        return "sem produtos"

    nomes = []

    for item in itens[:3]:
        produto = produtos.get(item["produto_id"])
        nomes.append(produto["nome"] if produto else item["produto_id"])

    texto = ", ".join(nomes)

    if len(itens) > 3:
        texto += ", …"

    plural = "produtos" if len(itens) > 1 else "produto"

    return f"{len(itens)} {plural} · {texto}"


def _texto_produtos_devolucao(devolucao, produtos):
    """Segunda linha da célula do meio, numa linha de devolução."""
    itens = estoque.listar_itens_devolucao(devolucao_id=devolucao["id"])

    if not itens:
        return "sem produtos"

    nomes = []

    for item in itens[:3]:
        produto = produtos.get(item["produto_id"])
        nomes.append(produto["nome"] if produto else item["produto_id"])

    texto = ", ".join(nomes)

    if len(itens) > 3:
        texto += ", …"

    plural = "produtos" if len(itens) > 1 else "produto"

    return f"{len(itens)} {plural} · {texto}"


def _itens_disponiveis_devolucao(requisicao_id):
    """Itens de uma requisição fechada que ainda podem ser devolvidos.

    Para cada item, desconta da quantidade enviada tudo o que já foi
    reportado noutras devoluções (pendentes ou fechadas) — mesmo
    cálculo que `estoque.reportar_devolucao` usa para validar,
    repetido aqui só para decidir o que mostrar no formulário e no
    "Gerir". Só entram os itens com sobra por reportar (> 0).
    """
    itens = estoque.listar_itens_requisicao(requisicao_id=requisicao_id)
    devolucoes = estoque.listar_devolucoes(requisicao_id=requisicao_id)

    ja_devolvido_por_produto = {}

    for devolucao in devolucoes:
        for item_dev in estoque.listar_itens_devolucao(
            devolucao_id=devolucao["id"]
        ):
            ja_devolvido_por_produto[item_dev["produto_id"]] = (
                ja_devolvido_por_produto.get(item_dev["produto_id"], 0)
                + item_dev["quantidade"]
            )

    disponiveis = []

    for item in itens:
        ja_devolvido = ja_devolvido_por_produto.get(item["produto_id"], 0)
        disponivel = item["quantidade_enviada"] - ja_devolvido

        if disponivel > 0:
            disponiveis.append(
                {
                    "produto_id": item["produto_id"],
                    "quantidade_enviada": item["quantidade_enviada"],
                    "ja_devolvido": ja_devolvido,
                    "disponivel": disponivel,
                }
            )

    return disponiveis


# =====================================================================
# HUB
# =====================================================================


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
        # igual) — o mesmo desenho de sempre. Uma tentativa de
        # centrar os quatro cartões num bloco de tamanho fixo, no
        # meio do ecrã, foi revertida a pedido do aluno (09/09/2026,
        # ronda seguinte): "achei feio os tamanhos, estava bom, use
        # o anterior". Com "Aprovação" fora (ver ponto 3 do
        # docstring do módulo), quatro cartões já enchem a grelha
        # 2×2 sem sobrar nenhum sozinho numa 3.ª linha.
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

        _tornar_clicavel(cartao, lambda: self._abrir_area(area))

    def _abrir_area(self, area):
        if area["ecra"] == "requisicoes":
            self.controlador.mostrar_frame(ListaRequisicoes)
            return

        if area["ecra"] == "devolucoes":
            self.controlador.mostrar_frame(ListaDevolucoes)
            return

        componentes.mostrar_erro(
            f"A área \"{area['titulo']}\" ainda não está "
            "implementada nesta versão.",
            titulo="Por implementar",
        )


# =====================================================================
# REQUISIÇÕES — tabela a sério (componentes.Tabela) + Gerir
# =====================================================================

_COLUNAS_REQUISICAO = (
    componentes.Coluna("REQUISIÇÃO", minimo=130, espaco=8),
    componentes.Coluna("RESPONSÁVEL E PRODUTOS", peso=3, minimo=280),
    componentes.Coluna("ESTADO", minimo=110, alinhamento="centro"),
    componentes.Coluna("GERIR", minimo=90, alinhamento="e"),
)


class ListaRequisicoes(ctk.CTkFrame):
    """Lista das requisições, filtrável por estado e responsável."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Stock · Requisições").pack(
            fill="x"
        )

        # Botão de criação numa barra própria, logo abaixo do
        # cabeçalho e a verde — mesmo padrão de Contrato Mensal e
        # Reservas Airbnb (09/09/2026).
        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Nova requisição",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _EscolherTipoRequisicaoModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkButton(
            barra,
            text="< Voltar ao Stock",
            width=140,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=lambda: controlador.mostrar_frame(EcraStock),
        ).pack(side="left")

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=20, pady=(0, 6))

        self.combo_estado = ctk.CTkOptionMenu(
            filtros,
            values=[_OPCAO_TODOS_ESTADOS] + list(_ESTADOS_REQUISICAO),
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_estado.set(_OPCAO_TODOS_ESTADOS)
        self.combo_estado.pack(side="left")

        self.responsaveis_disponiveis = responsaveis.listar(
            incluir_inativos=True
        )
        self.id_por_rotulo = {
            _rotulo_responsavel(r): r["id"]
            for r in self.responsaveis_disponiveis
        }
        self.nomes_por_id = {
            r["id"]: r["nome"] for r in self.responsaveis_disponiveis
        }

        self.combo_responsavel = ctk.CTkOptionMenu(
            filtros,
            values=([_OPCAO_TODOS_RESPONSAVEIS] + sorted(self.id_por_rotulo)),
            width=240,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_responsavel.set(_OPCAO_TODOS_RESPONSAVEIS)
        self.combo_responsavel.pack(side="left", padx=(10, 0))

        # Cartão, faixa de cabeçalho, zebra striping e divisórias
        # vinham daqui escritos à mão — agora é `componentes.Tabela`,
        # a mesma de Gestão de Propriedades (09/09/2026).
        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_REQUISICAO,
            altura_linha=52,
            mensagem_vazia="Nenhuma requisição com estes filtros.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _estado_filtro(self):
        valor = self.combo_estado.get()

        return None if valor == _OPCAO_TODOS_ESTADOS else valor

    def _responsavel_filtro(self):
        return self.id_por_rotulo.get(self.combo_responsavel.get())

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela de requisições."""
        self.tabela.limpar()

        # Catálogo lido de uma vez: sem isto era um procurar_produto
        # por item, dezenas de consultas para desenhar uma lista.
        produtos = {
            p["id"]: p for p in estoque.listar_produtos(incluir_inativos=True)
        }

        requisicoes = estoque.listar_requisicoes(
            estado=self._estado_filtro(),
            responsavel_id=self._responsavel_filtro(),
        )
        # Mais recentes primeiro. 'data_pedido' pode ser None num
        # registo antigo, e comparar None com date rebenta — daí o
        # par (tem_data, data) como chave.
        requisicoes.sort(
            key=lambda r: (
                r["data_pedido"] is not None,
                r["data_pedido"] or datetime.date.min,
            ),
            reverse=True,
        )

        if not requisicoes:
            self.tabela.mostrar_vazio()
            return

        for requisicao in requisicoes:
            self._desenhar_linha(requisicao, produtos)

    def _desenhar_linha(self, requisicao, produtos):
        linha = self.tabela.nova_linha()

        coluna_id = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            coluna_id,
            text=requisicao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        data = requisicao["data_pedido"]
        ctk.CTkLabel(
            coluna_id,
            text=data.strftime("%d/%m/%Y") if data else "sem data",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 0, coluna_id)

        coluna_meio = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            coluna_meio,
            text=self.nomes_por_id.get(
                requisicao["responsavel_id"], requisicao["responsavel_id"]
            ),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            coluna_meio,
            text=_texto_produtos_requisicao(requisicao, produtos),
            text_color=(
                tema.TEXTO_ERRO
                if requisicao["estado"] == "rejeitada"
                else tema.COR_TEXTO_SECUNDARIO
            ),
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 1, coluna_meio)

        self.tabela.colocar(
            linha, 2, _etiqueta_estado(linha, requisicao["estado"])
        )

        acoes = self.tabela.celula_acoes(linha, 3)
        acoes.adicionar(
            ctk.CTkButton(
                acoes,
                text="Gerir",
                width=76,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda: _AcoesRequisicaoModal(self, requisicao),
            )
        )

    # -- ações -------------------------------------------------------

    def _pode_confirmar(self, requisicao):
        """Só quem pediu confirma a receção, e só de uma enviada.

        `confirmar_rececao_requisicao` já recusa qualquer outro
        responsável (decisão 9: quem pede é quem sabe se recebeu) —
        isto evita mostrar uma ação que ia falhar sempre.
        """
        if requisicao["estado"] != "enviada":
            return False

        ativo = sessao.obter_responsavel_ativo()

        return ativo is not None and ativo["id"] == (
            requisicao["responsavel_id"]
        )

    def _pode_reportar_devolucao(self, requisicao):
        """Só quem pediu reporta sobra, só de uma fechada, e só
        havendo ainda quantidade por devolver (decisão 19: quem
        pede é quem sabe o que sobrou — mesma regra de identidade
        de `reportar_devolucao`, aqui só para não mostrar uma ação
        que ia falhar sempre ou que já não tem nada para fazer).
        """
        if requisicao["estado"] != "fechada":
            return False

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None or ativo["id"] != requisicao["responsavel_id"]:
            return False

        return bool(_itens_disponiveis_devolucao(requisicao["id"]))

    def _confirmar_requisicao(self, requisicao):
        """Aprova e envia a requisição pendente ("Confirmar
        requisição", no Gerir). Envia a totalidade pedida — o ajuste
        por item fica para quando for pedido explicitamente.
        """
        if not componentes.confirmar(
            f"Confirmar e enviar a requisição {requisicao['id']}?",
            titulo="Confirmar requisição",
        ):
            return

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            estoque.enviar_requisicao(
                requisicao["id"], ativo["id"], datetime.date.today()
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição {requisicao['id']} enviada."
        )
        self._recarregar()

    def _confirmar_rececao(self, requisicao):
        if not componentes.confirmar(
            f"Confirmar que o material da requisição "
            f"{requisicao['id']} foi recebido?",
            titulo="Confirmar receção",
        ):
            return

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            estoque.confirmar_rececao_requisicao(
                requisicao["id"], ativo["id"], datetime.date.today()
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição {requisicao['id']} fechada."
        )
        self._recarregar()


class _AcoesRequisicaoModal(ctk.CTkToplevel):
    """Popup de "Gerir" de uma requisição.

    Mesmo padrão de `_AcoesPropriedadeModal` (gui_propriedades.py):
    nome/estado no topo, botões de ação consoante o estado, "Fechar"
    no fim.
    """

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        altura = 230
        self.title(f"Gerir — {requisicao['id']}")
        self.geometry(f"{_LARGURA_POPUP_ACOES}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, _LARGURA_POPUP_ACOES, altura)
        _colocar_no_topo(self)

        nome = tela_lista.nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )
        ctk.CTkLabel(
            self,
            text=requisicao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=nome,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        estado = requisicao["estado"]

        if estado == "pendente":
            self._botao(
                "Confirmar requisição",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: tela_lista._confirmar_requisicao(requisicao),
            )
            self._separador()
            self._botao(
                "Rejeitar requisição",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: _RejeitarRequisicaoModal(tela_lista, requisicao),
            )
        elif estado == "enviada" and tela_lista._pode_confirmar(requisicao):
            self._botao(
                "Confirmar receção",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: tela_lista._confirmar_rececao(requisicao),
            )
        elif estado == "fechada" and tela_lista._pode_reportar_devolucao(
            requisicao
        ):
            self._botao(
                "Reportar sobra (devolução)",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: ReportarDevolucaoModal(tela_lista, requisicao),
            )
        else:
            texto = {
                "enviada": (
                    "Aguarda confirmação de receção pelo "
                    "responsável que pediu."
                ),
                "fechada": (
                    "Requisição já fechada — sem ações disponíveis."
                ),
                "rejeitada": (
                    "Requisição rejeitada — sem ações disponíveis."
                ),
            }.get(estado, "Sem ações disponíveis.")
            ctk.CTkLabel(
                self,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                wraplength=260,
                justify="center",
            ).pack(padx=20, pady=(0, 10))

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=(10, 16))

    def _separador(self):
        """Risco fino antes da ação destrutiva.

        Não é decoração: separa o que se pode desfazer do que não se
        desfaz, e dá uma pausa antes do último botão (mesma ideia de
        `_AcoesPropriedadeModal._separador`).
        """
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, text_color, hover_color, acao):
        """Botão de ação: fecha este popup antes de agir.

        A ordem importa — "Rejeitar requisição" abre outro popup por
        cima, e deixar este aberto por trás confundia qual dos dois
        estava ativo.
        """

        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)


class _RejeitarRequisicaoModal(ctk.CTkToplevel):
    """Motivo obrigatório antes de rejeitar — `rejeitar_requisicao`
    já o exige (decisão 9). Mesmo padrão de campo + rodapé (Voltar /
    botão vermelho de confirmação) de `EncerrarContratoModal`
    (gui_contratos.py).
    """

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao

        largura, altura = 420, 300
        self.title(f"Rejeitar — {requisicao['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Rejeitar requisição {requisicao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))

        nome = tela_lista.nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )
        ctk.CTkLabel(
            self,
            text=f"Pedido por {nome}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Motivo da rejeição",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_motivo = ctk.CTkTextbox(
            self, height=90, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_motivo.pack(fill="x", padx=20, pady=(2, 16))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            rodape,
            text="Voltar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Rejeitar requisição",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERMELHO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            text_color=tema.TEXTO_ERRO,
            command=self._rejeitar,
        ).pack(side="right")

    def _rejeitar(self):
        motivo = self.campo_motivo.get("1.0", "end").strip()

        if not motivo:
            componentes.mostrar_erro("O motivo é obrigatório.")
            return

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            requisicao = estoque.rejeitar_requisicao(
                self.requisicao["id"], ativo["id"], motivo
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição rejeitada: {requisicao['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class ReportarDevolucaoModal(ctk.CTkToplevel):
    """Reportar sobra de uma requisição fechada ("Reportar sobra
    (devolução)", no Gerir) — cria uma devolução "pendente", que
    depois aparece em "Aceitar Sobra (Devolução)" para o armazém
    fechar (`_AcoesDevolucaoModal`).

    Ao contrário de `NovaRequisicaoModal`/`RolLavanderiaModal`, a
    lista de produtos aqui é fixa — os mesmos itens da requisição
    original, cada um com o que ainda pode ser devolvido
    (`_itens_disponiveis_devolucao`) — não há dropdown de produto
    nem linhas para acrescentar/remover, porque não se pode devolver
    o que não foi pedido.
    """

    def __init__(self, tela_lista, requisicao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.requisicao = requisicao
        self.campos_por_produto = {}

        self.itens_disponiveis = _itens_disponiveis_devolucao(
            requisicao["id"]
        )
        produtos = {p["id"]: p for p in estoque.listar_produtos(True)}

        largura = 620
        altura = 220 + 40 * max(len(self.itens_disponiveis), 1)
        self.title(f"Reportar sobra — {requisicao['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Reportar sobra — {requisicao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text=(
                "Indique a quantidade a devolver de cada produto — "
                "deixe a zero o que não sobrou."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 14))

        if not self.itens_disponiveis:
            self._sem_itens()
            return

        self._construir_tabela(produtos)
        self._construir_rodape()

    def _sem_itens(self):
        """Chega aqui só se a sobra for reportada por outra via
        (ex.: CLI) entre abrir a lista e clicar em Gerir — a
        condição já foi checada em `_pode_reportar_devolucao` antes
        de este popup poder abrir.
        """
        ctk.CTkLabel(
            self,
            text="Já não há sobra por reportar nesta requisição.",
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=12),
            wraplength=580,
            justify="left",
            padx=14,
            pady=12,
        ).pack(fill="x", padx=20)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(anchor="w", padx=20, pady=20)

    def _construir_tabela(self, produtos):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20)

        cabecalho = ctk.CTkFrame(
            cartao, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO),
            ("ENVIADO", _LARGURA_ARMAZEM),
            ("JÁ DEVOLVIDO", _LARGURA_ARMAZEM + 20),
            ("A DEVOLVER", _LARGURA_PEDIDO),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for item in self.itens_disponiveis:
            produto = produtos.get(item["produto_id"])
            nome = produto["nome"] if produto else item["produto_id"]

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PRODUTO,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_enviada"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_ARMAZEM,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["ja_devolvido"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_ARMAZEM + 20,
                anchor="w",
            ).pack(side="left")

            campo = ctk.CTkEntry(
                linha,
                width=_LARGURA_PEDIDO,
                corner_radius=tema.RAIO_CAMPO,
                justify="center",
                placeholder_text="0",
            )
            campo.pack(side="left")
            self.campos_por_produto[item["produto_id"]] = campo

    def _construir_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Reportar devolução",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._reportar,
        ).pack(side="right")

    # -- submissão -----------------------------------------------------

    def _itens(self):
        """Itens com quantidade > 0, no formato que
        `estoque.reportar_devolucao` espera. Campo vazio ou "0"
        fica de fora — é assim que se marca "não sobrou nada disto",
        sem ser preciso apagar a linha (não há linhas para apagar
        aqui, ao contrário dos formulários de nova requisição).
        """
        itens = []

        for produto_id, campo in self.campos_por_produto.items():
            texto = campo.get().strip()

            if not texto or not texto.isdigit() or int(texto) == 0:
                continue

            itens.append({"produto_id": produto_id, "quantidade": int(texto)})

        return itens

    def _reportar(self):
        itens = self._itens()

        if not itens:
            componentes.mostrar_erro(
                "Indique pelo menos uma quantidade a devolver."
            )
            return

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            devolucao = estoque.reportar_devolucao(
                requisicao_id=self.requisicao["id"],
                responsavel_id=ativo["id"],
                itens=itens,
                data_reportada=datetime.date.today(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Devolução reportada: {devolucao['id']} — fica "
            f"pendente até o armazém aceitar, em \"Aceitar Sobra "
            f"(Devolução)\"."
        )
        self.destroy()
        self.tela_lista._recarregar()


# =====================================================================
# DEVOLUÇÕES — ecrã novo, "Aceitar Sobra"
# =====================================================================

_COLUNAS_DEVOLUCAO = (
    componentes.Coluna("DEVOLUÇÃO", minimo=130, espaco=8),
    componentes.Coluna("RESPONSÁVEL E PRODUTOS", peso=3, minimo=280),
    componentes.Coluna("ESTADO", minimo=110, alinhamento="centro"),
    componentes.Coluna("GERIR", minimo=90, alinhamento="e"),
)


class ListaDevolucoes(ctk.CTkFrame):
    """"Aceitar Sobra (Devolução)": mesma tabela e mesmo padrão de
    Gerir de ListaRequisicoes, agora para o material devolvido por
    sobra (`estoque.reportar_devolucao` / `fechar_devolucao`).

    Sem "+ Nova": a devolução nasce do lado do responsável, ao
    reportar a sobra de uma requisição fechada — este ecrã só aceita
    o que já foi reportado, filtrado por omissão às pendentes.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(
            self, titulo="Stock · Aceitar Sobra (Devolução)"
        ).pack(fill="x")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 6))
        ctk.CTkButton(
            barra,
            text="< Voltar ao Stock",
            width=140,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=lambda: controlador.mostrar_frame(EcraStock),
        ).pack(side="left")

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=20, pady=(0, 6))
        self.combo_estado = ctk.CTkOptionMenu(
            filtros,
            values=[_OPCAO_TODOS_ESTADOS] + list(_ESTADOS_DEVOLUCAO),
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_estado.set("pendente")
        self.combo_estado.pack(side="left")

        self.nomes_por_id = {
            r["id"]: r["nome"]
            for r in responsaveis.listar(incluir_inativos=True)
        }

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_DEVOLUCAO,
            altura_linha=52,
            mensagem_vazia="Nenhuma devolução com este filtro.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _estado_filtro(self):
        valor = self.combo_estado.get()

        return None if valor == _OPCAO_TODOS_ESTADOS else valor

    def _recarregar(self):
        self.tabela.limpar()

        produtos = {
            p["id"]: p for p in estoque.listar_produtos(incluir_inativos=True)
        }
        devolucoes = estoque.listar_devolucoes(estado=self._estado_filtro())
        devolucoes.sort(
            key=lambda d: (
                d["data_reportada"] is not None,
                d["data_reportada"] or datetime.date.min,
            ),
            reverse=True,
        )

        if not devolucoes:
            self.tabela.mostrar_vazio()
            return

        for devolucao in devolucoes:
            self._desenhar_linha(devolucao, produtos)

    def _desenhar_linha(self, devolucao, produtos):
        linha = self.tabela.nova_linha()

        coluna_id = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            coluna_id,
            text=devolucao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            coluna_id,
            text=f"de {devolucao['requisicao_id']}",
            text_color=tema.AZUL_PRINCIPAL,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        _tornar_clicavel(
            coluna_id,
            lambda: _ResumoRequisicaoModal(
                self, devolucao["requisicao_id"]
            ),
        )
        self.tabela.colocar(linha, 0, coluna_id)

        coluna_meio = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            coluna_meio,
            text=self.nomes_por_id.get(
                devolucao["responsavel_id"], devolucao["responsavel_id"]
            ),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            coluna_meio,
            text=_texto_produtos_devolucao(devolucao, produtos),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 1, coluna_meio)

        self.tabela.colocar(
            linha, 2, _etiqueta_estado(linha, devolucao["estado"])
        )

        acoes = self.tabela.celula_acoes(linha, 3)
        acoes.adicionar(
            ctk.CTkButton(
                acoes,
                text="Gerir",
                width=76,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda: _AcoesDevolucaoModal(self, devolucao),
            )
        )

    # -- ações -------------------------------------------------------

    def _aceitar_devolucao(
        self, devolucao, quantidades_aceites=None, motivo_ajuste=""
    ):
        """Confirma e fecha a devolução — chamada pelo botão "Aceitar
        devolução" de `_ResumoDevolucaoModal`, que já É a confirmação
        (mostra produto a produto o que vai entrar no stock); não há
        aqui um segundo "tem a certeza?" genérico por cima disso.

        'quantidades_aceites' e 'motivo_ajuste' vêm desse resumo só
        quando o admin corrigiu alguma quantidade — passam direto
        para `estoque.fechar_devolucao`, que gera o ajuste de stock
        da diferença (09/09/2026, pedido do aluno).
        """
        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo em Responsáveis "
                "antes de continuar."
            )
            return

        try:
            estoque.fechar_devolucao(
                devolucao["id"],
                ativo["id"],
                datetime.date.today(),
                quantidades_aceites=quantidades_aceites,
                motivo_ajuste=motivo_ajuste,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Devolução aceite: {devolucao['id']}")
        self._recarregar()


class _AcoesDevolucaoModal(ctk.CTkToplevel):
    """Popup de "Gerir" de uma devolução — gémeo de
    `_AcoesRequisicaoModal`, mas com uma única ação possível
    ("Aceitar devolução") em vez de duas.
    """

    def __init__(self, tela_lista, devolucao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        altura = 200
        self.title(f"Gerir — {devolucao['id']}")
        self.geometry(f"{_LARGURA_POPUP_ACOES}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, _LARGURA_POPUP_ACOES, altura)
        _colocar_no_topo(self)

        nome = tela_lista.nomes_por_id.get(
            devolucao["responsavel_id"], devolucao["responsavel_id"]
        )
        ctk.CTkLabel(
            self,
            text=devolucao["id"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=f"Devolvido por {nome}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if devolucao["estado"] == "pendente":

            def executar():
                self.destroy()
                _ResumoDevolucaoModal(tela_lista, devolucao)

            ctk.CTkButton(
                self,
                text="Aceitar devolução",
                height=34,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                hover_color=tema.ID_CHIP_FUNDO,
                text_color=tema.AZUL_PRINCIPAL,
                border_width=1,
                border_color=tema.COR_BORDA,
                command=executar,
            ).pack(fill="x", padx=20, pady=3)
        else:
            ctk.CTkLabel(
                self,
                text="Devolução já aceite — sem ações disponíveis.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                wraplength=260,
                justify="center",
            ).pack(padx=20, pady=(0, 10))

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=(10, 16))


class _ResumoDevolucaoModal(ctk.CTkToplevel):
    """Resumo da devolução, mostrado antes de aceitar — substitui o
    "tem a certeza?" genérico de `componentes.confirmar` (09/09/2026,
    pedido do aluno: "com o que vou aceitar e quanto vai entrar no
    meu estoque atual").

    Aberto a partir de "Aceitar devolução" em `_AcoesDevolucaoModal`.
    Mostra, produto a produto, o stock atual, a quantidade a repor e
    o stock resultante — é esta tabela que serve de confirmação e de
    rasto do que aconteceu (o admin vê exatamente o que vai mudar
    antes de mudar). Só depois de "Aceitar devolução" aqui é que
    `ListaDevolucoes._aceitar_devolucao` corre de facto.

    "A repor" vem preenchido com o reportado, mas pode ser corrigido
    para mais ou para menos — reduzido até 0 (ex.: parte voltou
    danificada e não deve voltar ao stock) ou aumentado (ex.: erro
    de digitação ao reportar, voltou mais do que ficou escrito).
    Quando o valor é corrigido, aparece um alerta a avisar que vai
    ser aberto um movimento de ajuste com a diferença, e exige um
    motivo — a entrada em si continua sempre pela quantidade
    reportada, imutável (decisão 9); é o ajuste, positivo ou
    negativo, que corrige o saldo final.
    """

    def __init__(self, tela_lista, devolucao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.devolucao = devolucao
        self.campos_por_produto = {}
        self.rotulos_apos_por_produto = {}
        self.reportado_por_produto = {}
        self.stock_atual_por_produto = {}
        self.nomes_produto_por_id = {}
        self.frame_alerta = None
        self.entry_motivo = None

        itens = estoque.listar_itens_devolucao(
            devolucao_id=devolucao["id"]
        )
        produtos = {
            p["id"]: p for p in estoque.listar_produtos(True)
        }
        nome = tela_lista.nomes_por_id.get(
            devolucao["responsavel_id"], devolucao["responsavel_id"]
        )

        self.largura_janela = 640
        self.altura_base = 300 + 36 * max(len(itens), 1)
        self.title(f"Resumo da devolução — {devolucao['id']}")
        self.geometry(f"{self.largura_janela}x{self.altura_base}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(
            self, tela_lista, self.largura_janela, self.altura_base
        )
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Resumo da devolução — {devolucao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            self,
            text=(
                f"de {devolucao['requisicao_id']} · devolvido por "
                f"{nome}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        self._construir_tabela(itens, produtos)

        self.rotulo_explicacao = ctk.CTkLabel(
            self,
            text=(
                "\"A repor\" vem preenchido com o que foi reportado, "
                "mas pode ser corrigido para mais ou para menos — "
                "reduzido até 0, se parte voltou danificada, ou "
                "aumentado, se voltou mais do que ficou reportado. "
                "Aceitar gera a entrada da quantidade reportada e "
                "fecha a devolução — deixa de poder ser alterada "
                "depois."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=600,
            justify="left",
        )
        self.rotulo_explicacao.pack(anchor="w", padx=20, pady=(10, 0))

        self._construir_alerta_ajuste()
        self._construir_rodape()

    def _construir_tabela(self, itens, produtos):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20)

        cabecalho = ctk.CTkFrame(
            cartao, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO),
            ("STOCK ATUAL", _LARGURA_ARMAZEM + 20),
            ("A REPOR", _LARGURA_ARMAZEM),
            ("STOCK APÓS", _LARGURA_ARMAZEM + 10),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for item in itens:
            produto_id = item["produto_id"]
            produto = produtos.get(produto_id)
            nome_produto = produto["nome"] if produto else produto_id
            stock_atual = estoque.saldo_produto(produto_id)

            self.reportado_por_produto[produto_id] = item["quantidade"]
            self.stock_atual_por_produto[produto_id] = stock_atual
            self.nomes_produto_por_id[produto_id] = nome_produto

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome_produto,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PRODUTO,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(stock_atual),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_ARMAZEM + 20,
                anchor="w",
            ).pack(side="left")

            campo = ctk.CTkEntry(
                linha,
                width=_LARGURA_ARMAZEM - 20,
                corner_radius=tema.RAIO_CAMPO,
                justify="center",
            )
            campo.insert(0, str(item["quantidade"]))
            campo.pack(side="left")
            campo.bind(
                "<KeyRelease>",
                lambda evento, pid=produto_id: self._atualizar_linha(pid),
            )
            self.campos_por_produto[produto_id] = campo

            ctk.CTkLabel(
                linha,
                text="",
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=_LARGURA_ARMAZEM + 30,
                anchor="w",
            ).pack(side="left", padx=(10, 0))
            self.rotulos_apos_por_produto[produto_id] = (
                linha.winfo_children()[-1]
            )
            self._atualizar_linha(produto_id)

    def _quantidade_aceite(self, produto_id):
        """Lê o campo "a repor" de um produto, sem deixar sair do
        único limite que há: nunca negativo. Pode ser maior ou menor
        do que o reportado — a diferença, para qualquer um dos dois
        lados, é o que o ajuste de stock existe para corrigir
        (09/09/2026, pedido do aluno: "para mais também tem que
        ser", depois de confirmar que só para menos funcionava).
        """
        texto = self.campos_por_produto[produto_id].get().strip()
        quantidade = int(texto) if texto.isdigit() else 0

        return max(0, quantidade)

    def _atualizar_linha(self, produto_id):
        aceite = self._quantidade_aceite(produto_id)
        stock_atual = self.stock_atual_por_produto[produto_id]
        rotulo = self.rotulos_apos_por_produto[produto_id]

        if aceite == 0:
            rotulo.configure(
                text=f"{stock_atual} (sem alteração)",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            )
        else:
            rotulo.configure(
                text=f"{stock_atual + aceite}  (+{aceite})",
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
            )

        if self.frame_alerta is not None:
            self._atualizar_alerta_ajuste()

    def _diferencas_por_produto(self):
        """Produtos cujo valor "a repor" já não bate com o reportado
        — cada um vai precisar de um movimento de ajuste (positivo
        ou negativo) além da entrada da devolução, por isso exigem
        motivo (09/09/2026, pedido do aluno: "abre o ajuste de
        estoque com a quantidade de comparação").
        """
        diferencas = {}

        for produto_id, reportado in self.reportado_por_produto.items():
            aceite = self._quantidade_aceite(produto_id)
            diferenca = aceite - reportado

            if diferenca != 0:
                diferencas[produto_id] = diferenca

        return diferencas

    def _construir_alerta_ajuste(self):
        self.frame_alerta = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )

        self.rotulo_alerta = ctk.CTkLabel(
            self.frame_alerta,
            text="",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=11),
            wraplength=560,
            justify="left",
            anchor="w",
        )
        self.rotulo_alerta.pack(
            anchor="w", fill="x", padx=14, pady=(12, 6)
        )

        linha_motivo = ctk.CTkFrame(
            self.frame_alerta, fg_color="transparent"
        )
        linha_motivo.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(
            linha_motivo,
            text="Motivo do ajuste:",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        self.entry_motivo = ctk.CTkEntry(
            linha_motivo,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: 3 unidades vieram danificadas",
        )
        self.entry_motivo.pack(side="left", fill="x", expand=True)

        self._atualizar_alerta_ajuste()

    def _atualizar_alerta_ajuste(self):
        if self.frame_alerta is None:
            return

        diferencas = self._diferencas_por_produto()

        if not diferencas:
            self.frame_alerta.pack_forget()
            _centrar_sobre(
                self,
                self.tela_lista,
                self.largura_janela,
                self.altura_base,
            )
            return

        linhas = "; ".join(
            f"{self.nomes_produto_por_id[produto_id]}: {diferenca:+d} "
            "unid"
            for produto_id, diferenca in diferencas.items()
        )
        self.rotulo_alerta.configure(
            text=(
                "Vai ser aberto um movimento de ajuste de stock para "
                f"a diferença — {linhas}. O motivo abaixo fica "
                "registado no histórico de stock."
            )
        )
        self.frame_alerta.pack(
            fill="x",
            padx=20,
            pady=(10, 0),
            before=self.rotulo_explicacao,
        )
        # a janela não é redimensionável (resizable(False, False)) e
        # a altura foi calculada sem contar com este alerta — sem
        # crescer aqui, o rodapé com "Aceitar devolução" fica fora
        # da janela, inacessível (09/09/2026, aluno testou e viu o
        # botão sumir com o alerta aberto).
        _centrar_sobre(
            self,
            self.tela_lista,
            self.largura_janela,
            self.altura_base + _ALTURA_ALERTA_AJUSTE,
        )

    def _construir_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Aceitar devolução",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._aceitar,
        ).pack(side="right")

    def _aceitar(self):
        diferencas = self._diferencas_por_produto()
        motivo = ""

        if diferencas:
            if self.entry_motivo is None:
                return

            motivo = self.entry_motivo.get().strip()

            if not motivo:
                componentes.mostrar_erro(
                    "Indique o motivo do ajuste de stock."
                )
                return

        quantidades_aceites = {
            produto_id: self._quantidade_aceite(produto_id)
            for produto_id in diferencas
        }

        self.destroy()
        self.tela_lista._aceitar_devolucao(
            self.devolucao,
            quantidades_aceites=quantidades_aceites,
            motivo_ajuste=motivo,
        )


class _ResumoRequisicaoModal(ctk.CTkToplevel):
    """Resumo (só leitura) da requisição de origem de uma devolução —
    aberto ao clicar no ID/estado "de REQ-..." de uma linha em
    "Aceitar Sobra (Devolução)" (09/09/2026, pedido do aluno: "abre
    resumo da requisição que foi enviada").

    Mostra o que foi pedido e o que foi mesmo enviado por produto —
    é o rasto completo: a devolução já mostra quem devolveu o quê,
    isto mostra a requisição que deu origem a essa sobra.
    """

    def __init__(self, master, requisicao_id):
        super().__init__(master)
        self.master_janela = master

        requisicao = estoque.procurar_requisicao(requisicao_id)
        itens = estoque.listar_itens_requisicao(
            requisicao_id=requisicao_id
        )
        produtos = {
            p["id"]: p for p in estoque.listar_produtos(True)
        }
        nomes_por_id = getattr(master, "nomes_por_id", None) or {
            r["id"]: r["nome"]
            for r in responsaveis.listar(incluir_inativos=True)
        }
        nome = nomes_por_id.get(
            requisicao["responsavel_id"], requisicao["responsavel_id"]
        )

        largura = 620
        altura = 300 + 36 * max(len(itens), 1)
        self.title(f"Resumo da requisição — {requisicao_id}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        _centrar_sobre(self, master, largura, altura)
        _colocar_no_topo(self)

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            cabecalho,
            text=f"Resumo da requisição — {requisicao_id}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")
        _etiqueta_estado(cabecalho, requisicao["estado"]).pack(
            side="left", padx=(10, 0)
        )

        ctk.CTkLabel(
            self,
            text=(
                f"Pedido por {nome} · "
                f"pedida {requisicao['data_pedido']} · "
                f"enviada {requisicao['data_envio'] or '—'} · "
                f"recebida {requisicao['data_fecho'] or '—'}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 14))

        self._construir_tabela(itens, produtos)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=16)

    def _construir_tabela(self, itens, produtos):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20)

        cabecalho = ctk.CTkFrame(
            cartao, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO),
            ("PEDIDO", _LARGURA_PEDIDO + 20),
            ("ENVIADO", _LARGURA_PEDIDO + 20),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for item in itens:
            produto = produtos.get(item["produto_id"])
            nome_produto = produto["nome"] if produto else item["produto_id"]

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome_produto,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PRODUTO,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_pedida"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PEDIDO + 20,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["quantidade_enviada"]),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=_LARGURA_PEDIDO + 20,
                anchor="w",
            ).pack(side="left")


# =====================================================================
# "+ NOVA REQUISIÇÃO" — escolher Requisição Staff / Rol de Lavanderia
# =====================================================================


class _EscolherTipoRequisicaoModal(ctk.CTkToplevel):
    """Popup intermédio do botão "+ Nova requisição": pergunta qual
    dos dois fluxos abrir, antes de qualquer formulário.

    "Requisição Staff" é o formulário que já existia
    (`NovaRequisicaoModal`, sem alterações). "Rol de Lavanderia"
    reutiliza a mesma tabela de produtos, mas cria E envia de
    imediato — mesma composição de `cli.py:_enviar_rol_lavanderia`.
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 380, 300
        self.title("Nova requisição")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="O que pretende criar?",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 14))

        self._cartao(
            "Requisição Staff",
            "Pedido normal: fica pendente até ser aprovado.",
            self._abrir_staff,
        )
        self._cartao(
            "Rol de Lavanderia",
            "Envio direto a um responsável, sem passar por aprovação.",
            self._abrir_lavanderia,
        )

        ctk.CTkButton(
            self,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(6, 20))

    def _cartao(self, titulo, descricao, ao_clicar):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            cartao,
            text=descricao,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", padx=14, pady=(0, 12))

        _tornar_clicavel(cartao, ao_clicar)

    def _abrir_staff(self):
        self.destroy()
        NovaRequisicaoModal(self.tela_lista)

    def _abrir_lavanderia(self):
        self.destroy()
        RolLavanderiaModal(self.tela_lista)


# =====================================================================
# LINHA DE PRODUTO — partilhada pelos dois formulários
# =====================================================================


class _LinhaProduto:
    """Uma linha da tabela de produtos de um dos dois formulários.

    Não é um widget: é o par (dropdown, campo de quantidade) mais a
    moldura que os contém, para o modal poder lê-los e destruí-los
    sem andar a percorrer filhos de frames.
    """

    def __init__(self, modal, master):
        self.modal = modal

        self.moldura = ctk.CTkFrame(master, fg_color="transparent")
        self.moldura.pack(fill="x", padx=16, pady=3)

        self.combo_produto = ctk.CTkOptionMenu(
            self.moldura,
            values=modal.rotulos_produtos,
            width=_LARGURA_PRODUTO,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: modal.ao_mudar_linha(),
        )
        self.combo_produto.set(modal.rotulos_produtos[0])
        self.combo_produto.pack(side="left")

        self.rotulo_armazem = ctk.CTkLabel(
            self.moldura,
            text="",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            width=_LARGURA_ARMAZEM,
            anchor="w",
        )
        self.rotulo_armazem.pack(side="left", padx=(10, 0))

        self.campo_pedido = ctk.CTkEntry(
            self.moldura,
            width=_LARGURA_PEDIDO,
            corner_radius=tema.RAIO_CAMPO,
            justify="center",
        )
        self.campo_pedido.pack(side="left")
        # Atualiza o aviso a cada tecla: o banner tem de acompanhar
        # o que está escrito, não só o que já foi submetido.
        self.campo_pedido.bind(
            "<KeyRelease>", lambda evento: modal.ao_mudar_linha()
        )

        ctk.CTkButton(
            self.moldura,
            text="X",
            width=30,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self.remover,
        ).pack(side="left", padx=(10, 0))

    def produto_id(self):
        return self.modal.id_por_rotulo_produto.get(self.combo_produto.get())

    def quantidade(self):
        """Quantidade escrita, ou None se ainda não for um inteiro.

        None não é erro aqui: é o estado normal de um campo vazio ou
        a meio de ser escrito. Quem recusa de vez é a submissão de
        cada modal.
        """
        texto = self.campo_pedido.get().strip()

        if not texto.isdigit():
            return None

        return int(texto)

    def remover(self):
        self.moldura.destroy()
        self.modal.linhas.remove(self)
        self.modal.ao_mudar_linha()


# =====================================================================
# REQUISIÇÃO STAFF — formulário já existente, sem alterações
# =====================================================================


class NovaRequisicaoModal(ctk.CTkToplevel):
    """Popup de criação de uma requisição de material (fica
    "pendente", à espera de "Confirmar requisição" no Gerir).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.linhas = []

        largura, altura = 760, 640
        self.title("Nova Requisição")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        self.produtos_disponiveis = estoque.listar_produtos()
        self.rotulos_produtos = [
            _rotulo_produto(p) for p in self.produtos_disponiveis
        ]
        self.id_por_rotulo_produto = {
            _rotulo_produto(p): p["id"] for p in self.produtos_disponiveis
        }
        self.produtos_por_id = {p["id"]: p for p in self.produtos_disponiveis}

        ctk.CTkLabel(
            self,
            text="Stock · Nova requisição — Requisição Staff",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 12))

        if not self.produtos_disponiveis:
            self._sem_catalogo()
            return

        self._construir_responsavel()
        self._construir_tabela()
        self._construir_aviso()
        self._construir_observacoes()
        self._construir_rodape()

        self._acrescentar_linha()

    def _sem_catalogo(self):
        """Sem produtos ativos não há requisição possível.

        Acontece enquanto o ecrã de Produtos não existir e a base
        estiver vazia — dizê-lo aqui é mais claro do que abrir um
        formulário com um dropdown sem opções nenhumas.
        """
        ctk.CTkLabel(
            self,
            text=(
                "Não há produtos ativos no catálogo. Sem catálogo "
                "não é possível criar uma requisição."
            ),
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=12),
            wraplength=640,
            justify="left",
            padx=14,
            pady=12,
        ).pack(fill="x", padx=20)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(anchor="w", padx=20, pady=20)

    def _construir_responsavel(self):
        ctk.CTkLabel(
            self,
            text="Responsável pela requisição",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.responsaveis_disponiveis = responsaveis.listar()
        rotulos = [
            _rotulo_responsavel(r) for r in self.responsaveis_disponiveis
        ]
        self.id_por_rotulo_responsavel = {
            _rotulo_responsavel(r): r["id"]
            for r in self.responsaveis_disponiveis
        }

        self.combo_responsavel = ctk.CTkOptionMenu(
            self,
            values=rotulos or ["— Nenhum —"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_responsavel.pack(fill="x", padx=20, pady=(2, 12))

        # Arranca no responsável ativo da sessão, quando há um: é
        # quase sempre quem está a pedir, e poupa uma escolha.
        ativo = sessao.obter_responsavel_ativo()

        if ativo is not None and _rotulo_responsavel(ativo) in rotulos:
            self.combo_responsavel.set(_rotulo_responsavel(ativo))
        elif rotulos:
            self.combo_responsavel.set(rotulos[0])
        else:
            self.combo_responsavel.set("— Nenhum —")

    def _construir_tabela(self):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20)

        cabecalho = ctk.CTkFrame(
            cartao, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO),
            ("EM ARMAZÉM", _LARGURA_ARMAZEM + 10),
            ("PEDIDO", _LARGURA_PEDIDO),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        self.area_linhas = ctk.CTkFrame(cartao, fg_color="transparent")
        self.area_linhas.pack(fill="x", pady=(6, 8))

        ctk.CTkButton(
            self,
            text="+ Acrescentar produto",
            width=180,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            command=self._acrescentar_linha,
        ).pack(anchor="w", padx=20, pady=(8, 10))

    def _construir_aviso(self):
        """Caixa de aviso, escondida enquanto não houver avisos.

        Criada uma vez e mostrada/escondida com pack/pack_forget —
        recriá-la a cada tecla fazia o resto do formulário saltar.
        """
        self.caixa_aviso = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )

        self.rotulo_aviso = ctk.CTkLabel(
            self.caixa_aviso,
            text="",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=12),
            wraplength=660,
            justify="left",
            anchor="w",
        )
        self.rotulo_aviso.pack(fill="x", padx=12, pady=8)

    def _construir_observacoes(self):
        ctk.CTkLabel(
            self,
            text="Observações (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(6, 2))

        self.campo_observacoes = ctk.CTkTextbox(
            self, height=70, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_observacoes.pack(fill="x", padx=20)

    def _construir_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Enviar pedido",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._criar,
        ).pack(side="right")

    # -- linhas e avisos ---------------------------------------------

    def _acrescentar_linha(self):
        self.linhas.append(_LinhaProduto(self, self.area_linhas))
        self.ao_mudar_linha()

    def ao_mudar_linha(self):
        """Recalcula "em armazém" de cada linha e o banner de aviso.

        Chamada a cada tecla escrita e a cada produto escolhido. As
        frases do banner vêm inteiras de
        `estoque.avisos_requisicao` — aqui não se compara nada.
        """
        for linha in self.linhas:
            produto_id = linha.produto_id()

            if produto_id is None:
                linha.rotulo_armazem.configure(text="")
                continue

            produto = self.produtos_por_id.get(produto_id)

            try:
                saldo = estoque.saldo_produto(produto_id)
            except ValueError:
                linha.rotulo_armazem.configure(text="—")
                continue

            unidade = produto["unidade_medida"] if produto else ""
            pedida = linha.quantidade()
            em_falta = pedida is not None and pedida > saldo

            linha.rotulo_armazem.configure(
                text=f"{saldo} {unidade}".strip(),
                text_color=(
                    tema.TEXTO_ERRO if em_falta else tema.COR_TEXTO_SECUNDARIO
                ),
            )

        self._atualizar_aviso()

    def _atualizar_aviso(self):
        try:
            avisos = estoque.avisos_requisicao(self._itens())
        except ValueError:
            avisos = []

        if not avisos:
            self.caixa_aviso.pack_forget()
            return

        self.rotulo_aviso.configure(text="\n".join(avisos))
        self.caixa_aviso.pack(
            fill="x", padx=20, pady=(0, 8), before=self.campo_observacoes
        )

    def _itens(self):
        """Itens no formato que o módulo de negócio espera.

        Linhas sem produto ou sem quantidade válida ficam de fora —
        durante a escrita são o estado normal, não um erro.
        """
        itens = []

        for linha in self.linhas:
            produto_id = linha.produto_id()
            quantidade = linha.quantidade()

            if produto_id is None or quantidade is None:
                continue

            itens.append(
                {
                    "produto_id": produto_id,
                    "quantidade_pedida": quantidade,
                }
            )

        return itens

    # -- submissão ---------------------------------------------------

    def _criar(self):
        responsavel_id = self.id_por_rotulo_responsavel.get(
            self.combo_responsavel.get()
        )

        if responsavel_id is None:
            componentes.mostrar_erro(
                "Escolha o responsável pela requisição."
            )
            return

        itens = self._itens()

        if not itens:
            componentes.mostrar_erro(
                "Acrescente pelo menos um produto com uma "
                "quantidade válida."
            )
            return

        observacoes = self.campo_observacoes.get("1.0", "end").strip()

        try:
            requisicao = estoque.criar_requisicao(
                responsavel_id=responsavel_id,
                itens=itens,
                data_pedido=datetime.date.today(),
                observacoes=observacoes,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Requisição criada com sucesso: {requisicao['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


# =====================================================================
# ROL DE LAVANDERIA — cria e envia numa só operação
# =====================================================================


class RolLavanderiaModal(ctk.CTkToplevel):
    """Envio direto de stock a um responsável, sem requisição prévia
    — mesma composição de `cli.py:_enviar_rol_lavanderia`
    (`criar_requisicao` seguido de `enviar_requisicao`). O
    responsável só entra depois, a confirmar a receção pelo ecrã
    normal (decisão 9: quem recebe é quem confirma, nunca o admin em
    nome dele).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.linhas = []

        largura, altura = 760, 680
        self.title("Rol de Lavanderia")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _centrar_sobre(self, tela_lista, largura, altura)
        _colocar_no_topo(self)

        self.produtos_disponiveis = estoque.listar_produtos()
        self.rotulos_produtos = [
            _rotulo_produto(p) for p in self.produtos_disponiveis
        ]
        self.id_por_rotulo_produto = {
            _rotulo_produto(p): p["id"] for p in self.produtos_disponiveis
        }
        self.produtos_por_id = {p["id"]: p for p in self.produtos_disponiveis}

        ctk.CTkLabel(
            self,
            text="Stock · Rol de Lavanderia",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text="Envio direto — não fica pendente nem passa por "
            "aprovação.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        if not self.produtos_disponiveis:
            self._sem_catalogo()
            return

        self._construir_responsaveis()
        self._construir_tabela()
        self._construir_aviso()
        self._construir_rodape()

        self._acrescentar_linha()

    def _sem_catalogo(self):
        """Mesma frase e botão de `NovaRequisicaoModal._sem_catalogo`
        — sem catálogo não há o que enviar, aqui nem faz sentido
        escolher os dois responsáveis primeiro.
        """
        ctk.CTkLabel(
            self,
            text=(
                "Não há produtos ativos no catálogo. Sem catálogo "
                "não é possível enviar um rol de lavanderia."
            ),
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=12),
            wraplength=640,
            justify="left",
            padx=14,
            pady=12,
        ).pack(fill="x", padx=20)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(anchor="w", padx=20, pady=20)

    def _construir_responsaveis(self):
        self.responsaveis_disponiveis = responsaveis.listar()
        rotulos = [
            _rotulo_responsavel(r) for r in self.responsaveis_disponiveis
        ]
        self.id_por_rotulo_responsavel = {
            _rotulo_responsavel(r): r["id"]
            for r in self.responsaveis_disponiveis
        }

        linha_responsaveis = ctk.CTkFrame(self, fg_color="transparent")
        linha_responsaveis.pack(fill="x", padx=20, pady=(0, 12))

        coluna_recebe = ctk.CTkFrame(
            linha_responsaveis, fg_color="transparent"
        )
        coluna_recebe.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(
            coluna_recebe,
            text="Responsável que vai receber",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_recebe = ctk.CTkOptionMenu(
            coluna_recebe,
            values=rotulos or ["— Nenhum —"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_recebe.pack(fill="x", pady=(2, 0))
        if rotulos:
            self.combo_recebe.set(rotulos[0])

        coluna_envia = ctk.CTkFrame(
            linha_responsaveis, fg_color="transparent"
        )
        coluna_envia.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ctk.CTkLabel(
            coluna_envia,
            text="Enviado por (admin)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_envia = ctk.CTkOptionMenu(
            coluna_envia,
            values=rotulos or ["— Nenhum —"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_envia.pack(fill="x", pady=(2, 0))

        # Arranca no responsável ativo da sessão como "quem envia" —
        # é o admin logado na maior parte dos casos; "quem recebe"
        # arranca no primeiro da lista, sem preferência nenhuma.
        ativo = sessao.obter_responsavel_ativo()

        if ativo is not None and _rotulo_responsavel(ativo) in rotulos:
            self.combo_envia.set(_rotulo_responsavel(ativo))
        elif rotulos:
            self.combo_envia.set(rotulos[-1])
        else:
            self.combo_envia.set("— Nenhum —")

    def _construir_tabela(self):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20)

        cabecalho = ctk.CTkFrame(
            cartao, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        for texto, largura in (
            ("PRODUTO", _LARGURA_PRODUTO),
            ("EM ARMAZÉM", _LARGURA_ARMAZEM + 10),
            ("ENVIAR", _LARGURA_PEDIDO),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        self.area_linhas = ctk.CTkFrame(cartao, fg_color="transparent")
        self.area_linhas.pack(fill="x", pady=(6, 8))

        ctk.CTkButton(
            self,
            text="+ Acrescentar produto",
            width=180,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            command=self._acrescentar_linha,
        ).pack(anchor="w", padx=20, pady=(8, 10))

    def _construir_aviso(self):
        self.caixa_aviso = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.rotulo_aviso = ctk.CTkLabel(
            self.caixa_aviso,
            text="",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=12),
            wraplength=660,
            justify="left",
            anchor="w",
        )
        self.rotulo_aviso.pack(fill="x", padx=12, pady=8)

    def _construir_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16, side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Enviar rol",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._enviar,
        ).pack(side="right")

    # -- linhas e avisos ---------------------------------------------

    def _acrescentar_linha(self):
        self.linhas.append(_LinhaProduto(self, self.area_linhas))
        self.ao_mudar_linha()

    def ao_mudar_linha(self):
        for linha in self.linhas:
            produto_id = linha.produto_id()

            if produto_id is None:
                linha.rotulo_armazem.configure(text="")
                continue

            produto = self.produtos_por_id.get(produto_id)

            try:
                saldo = estoque.saldo_produto(produto_id)
            except ValueError:
                linha.rotulo_armazem.configure(text="—")
                continue

            unidade = produto["unidade_medida"] if produto else ""
            pedida = linha.quantidade()
            em_falta = pedida is not None and pedida > saldo

            linha.rotulo_armazem.configure(
                text=f"{saldo} {unidade}".strip(),
                text_color=(
                    tema.TEXTO_ERRO if em_falta else tema.COR_TEXTO_SECUNDARIO
                ),
            )

        self._atualizar_aviso()

    def _atualizar_aviso(self):
        try:
            avisos = estoque.avisos_requisicao(self._itens())
        except ValueError:
            avisos = []

        if not avisos:
            self.caixa_aviso.pack_forget()
            return

        # Aqui o aviso é mesmo um bloqueio (envio imediato), não só
        # informativo como em NovaRequisicaoModal — a frase original
        # ("o administrador terá de repor") não fazia sentido quando
        # é o próprio administrador que está a tentar enviar agora.
        avisos = [
            aviso.replace(
                "O administrador terá de repor.",
                "Reduza a quantidade ou reponha stock antes de "
                "enviar.",
            )
            for aviso in avisos
        ]
        self.rotulo_aviso.configure(text="\n".join(avisos))
        self.caixa_aviso.pack(fill="x", padx=20, pady=(0, 8))

    def _itens(self):
        itens = []

        for linha in self.linhas:
            produto_id = linha.produto_id()
            quantidade = linha.quantidade()

            if produto_id is None or quantidade is None:
                continue

            itens.append(
                {
                    "produto_id": produto_id,
                    "quantidade_pedida": quantidade,
                }
            )

        return itens

    # -- submissão ---------------------------------------------------

    def _enviar(self):
        recebe_id = self.id_por_rotulo_responsavel.get(
            self.combo_recebe.get()
        )
        envia_id = self.id_por_rotulo_responsavel.get(self.combo_envia.get())

        if recebe_id is None or envia_id is None:
            componentes.mostrar_erro("Escolha os dois responsáveis.")
            return

        itens = self._itens()

        if not itens:
            componentes.mostrar_erro(
                "Acrescente pelo menos um produto com uma "
                "quantidade válida."
            )
            return

        try:
            requisicao = estoque.criar_requisicao(
                responsavel_id=recebe_id,
                itens=itens,
                data_pedido=datetime.date.today(),
                observacoes=(
                    "Enviado sem requisição prévia (rol de lavanderia)."
                ),
            )
            estoque.enviar_requisicao(
                requisicao["id"], envia_id, datetime.date.today()
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Rol de lavanderia enviado: {requisicao['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()