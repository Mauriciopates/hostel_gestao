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
"""

import datetime
from decimal import Decimal, InvalidOperation

import customtkinter as ctk

import despesas
import estoque
import propriedades
import responsaveis
import unidades

from . import componentes
from . import sessao
from . import tema

# =====================================================================
# CONSTANTES
# =====================================================================

# Rótulos das opções de filtro (dropdowns) — mesmas convenções
# dos outros ecrãs (`"Todos …"` para "sem filtro").
_OPCAO_TODAS_CATEGORIAS = "Todas as categorias"
_OPCAO_TODOS_ESTADOS = "Todos os estados"
_OPCAO_TODAS_UNIDADES = "Todas as unidades"
_OPCAO_TODOS_FORNECEDORES = "Todos os fornecedores"

# Larguras fixas das colunas da tabela de despesas (mesma
# disciplina dos outros módulos: uma constante por coluna,
# lida tanto pelo cabeçalho como pelas linhas).
_LARGURA_ID = 90
_LARGURA_DESCRICAO = 260
_LARGURA_CATEGORIA = 130
_LARGURA_VALOR = 110
_LARGURA_LANCAMENTO = 110
_LARGURA_VENCIMENTO = 110
_LARGURA_ESTADO = 130
_LARGURA_ACOES = 90

_COLUNAS_DESPESA = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("DESCRIÇÃO", peso=3, minimo=_LARGURA_DESCRICAO),
    componentes.Coluna("CATEGORIA", peso=1, minimo=_LARGURA_CATEGORIA),
    componentes.Coluna(
        "VALOR", peso=1, minimo=_LARGURA_VALOR, alinhamento="e"
    ),
    componentes.Coluna(
        "LANÇAMENTO",
        peso=1,
        minimo=_LARGURA_LANCAMENTO,
        alinhamento="centro",
    ),
    componentes.Coluna(
        "VENCIMENTO",
        peso=1,
        minimo=_LARGURA_VENCIMENTO,
        alinhamento="centro",
    ),
    componentes.Coluna(
        "ESTADO", peso=1, minimo=_LARGURA_ESTADO, alinhamento="centro"
    ),
    componentes.Coluna("AÇÕES", minimo=_LARGURA_ACOES, alinhamento="centro"),
)

_ALTURA_LINHA = 52


# =====================================================================
# HELPERS INTERNOS
# =====================================================================


def _parse_decimal(texto, nome_campo):
    """Converte texto monetário (obrigatório) para Decimal.

    Aceita vírgula ou ponto. Vazio levanta erro. Devolve SEMPRE
    Decimal — nunca None —, o que deixa o Pylance sossegado nas
    chamadas onde o valor é obrigatório.
    """
    texto = texto.strip()
    if not texto:
        raise ValueError(f"{nome_campo} é obrigatório.")
    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"{nome_campo} tem um valor inválido.")


def _parse_decimal_opcional(texto, nome_campo):
    """Como `_parse_decimal`, mas vazio devolve None.

    Existe separada de propósito: assim o Pylance sabe que
    `_parse_decimal` devolve SEMPRE Decimal.
    """
    texto = texto.strip()
    if not texto:
        return None
    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"{nome_campo} tem um valor inválido.")


def _autor_atual():
    """Devolve o dict do responsável ativo, ou None.

    Toda a escrita no módulo `despesas` exige o `autor`. Esta função
    centraliza o acesso à sessão — a GUI nunca chama
    `sessao.obter_responsavel_ativo()` diretamente nos modais.
    """
    return sessao.obter_responsavel_ativo()


def _formatar_data(valor):
    """Formata uma `date` para dd/mm/aaaa, ou "—" quando None."""
    if valor is None:
        return "—"
    return valor.strftime("%d/%m/%Y")


def _parse_data(texto, nome_campo):
    """Converte texto "dd/mm/aaaa" numa `date`. Devolve None se
    vazio; levanta ValueError se o formato estiver errado.

    Centraliza a conversão — a GUI usa isto em todos os modais
    onde há campos de data.
    """
    texto = texto.strip()
    if not texto:
        return None
    try:
        return datetime.datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"{nome_campo} inválida. Usa o formato dd/mm/aaaa.")


def _rotulo_unidade(unidade):
    """Rótulo de dropdown de unidade: "NOME (ID) · Propriedade"."""
    if unidade is None:
        return "— Nenhuma (despesa geral) —"
    return (
        f"{unidade['nome']} ({unidade['id']}) · "
        f"{unidade.get('propriedade_nome', '')}"
    )


def _rotulo_categoria(categoria):
    """Rótulo de dropdown de categoria: "NOME"."""
    return categoria["nome"]


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


# =====================================================================
# ECRÃ LISTA — ListaDespesas
# =====================================================================


class ListaDespesas(ctk.CTkFrame):
    """Ecrã principal do módulo — a lista de todas as despesas.

    Estrutura (mockup A.2):
      - Cabeçalho "Despesas" (componentes.Cabecalho)
      - Barra de ações: botão verde "+ Nova Despesa" + 4 filtros
        (categoria · estado · unidade · checkbox "Só vencidas")
      - Tabela com 8 colunas: ID · Descrição · Categoria · Valor ·
        Lançamento · Vencimento · Estado · Ações
      - Botão "Gerir" em cada linha, que abre o modal certo
        conforme o estado (pendente → Aprovações-style modal;
        paga → modal de leitura; cancelada → modal de leitura)
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        # Referências vivas aos dados, preenchidas em _recarregar.
        self._categorias = []
        self._unidades = []

        componentes.Cabecalho(self, titulo="Despesas").pack(fill="x")

        self._montar_barra_acoes()

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_DESPESA,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia="Ainda não há despesas lançadas.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- barra de ações -----------------------------------------------

    def _montar_barra_acoes(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 8))

        ctk.CTkButton(
            barra,
            text="+ Nova Despesa",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._abrir_escolha_via,
        ).pack(side="left")

        filtros = ctk.CTkFrame(barra, fg_color="transparent")
        filtros.pack(side="right")

        self.combo_categoria = componentes.Seletor(
            filtros,
            values=[_OPCAO_TODAS_CATEGORIAS],
            width=180,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _v: self._recarregar(),
        )
        self.combo_categoria.set(_OPCAO_TODAS_CATEGORIAS)
        self.combo_categoria.pack(side="left")

        self.combo_estado = componentes.Seletor(
            filtros,
            values=[
                _OPCAO_TODOS_ESTADOS,
                "pendente",
                "paga",
                "cancelada",
            ],
            width=160,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _v: self._recarregar(),
        )
        self.combo_estado.set(_OPCAO_TODOS_ESTADOS)
        self.combo_estado.pack(side="left", padx=(8, 0))

        self.combo_unidade = componentes.Seletor(
            filtros,
            values=[_OPCAO_TODAS_UNIDADES],
            width=200,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _v: self._recarregar(),
        )
        self.combo_unidade.set(_OPCAO_TODAS_UNIDADES)
        self.combo_unidade.pack(side="left", padx=(8, 0))

        self.so_vencidas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            filtros,
            text="Só vencidas",
            variable=self.so_vencidas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(10, 0))

    # -- filtros ------------------------------------------------------

    def _carregar_filtros(self):
        """Recarrega as opções dos dropdowns de filtro a partir da
        BD — chamada uma vez no arranque. Se ficar sempre a
        recarregar, o utilizador perde a seleção a cada refresh."""
        self._categorias = despesas.listar_categorias()
        self._unidades = unidades.listar_com_propriedade()

        nomes_categorias = [_OPCAO_TODAS_CATEGORIAS] + [
            _rotulo_categoria(c) for c in self._categorias
        ]
        self.combo_categoria.configure(values=nomes_categorias)

        self._unidade_por_rotulo = {
            _rotulo_unidade(u): u["id"] for u in self._unidades
        }
        rotulos_unidades = [_OPCAO_TODAS_UNIDADES] + sorted(
            self._unidade_por_rotulo
        )
        self.combo_unidade.configure(values=rotulos_unidades)

    def _categoria_filtro(self):
        valor = self.combo_categoria.get()
        if valor == _OPCAO_TODAS_CATEGORIAS:
            return None
        for c in self._categorias:
            if c["nome"] == valor:
                return c["id"]
        return None

    def _estado_filtro(self):
        valor = self.combo_estado.get()
        if valor == _OPCAO_TODOS_ESTADOS:
            return None
        return valor

    def _unidade_filtro(self):
        valor = self.combo_unidade.get()
        if valor == _OPCAO_TODAS_UNIDADES:
            return None
        return self._unidade_por_rotulo.get(valor)

    # -- carregamento -------------------------------------------------

    def _recarregar(self):
        """Recarrega a lista de despesas com os filtros atuais.

        Chamada na abertura, ao mexer em qualquer filtro, e depois
        de qualquer criação/edição/cancelamento.
        """
        self._carregar_filtros()
        self.tabela.limpar()

        incluir_vencidas = None
        if self.so_vencidas.get():
            incluir_vencidas = True

        lista = despesas.listar_despesas(
            estado=self._estado_filtro(),
            unidade_id=self._unidade_filtro(),
            categoria_id=self._categoria_filtro(),
            incluir_vencidas=incluir_vencidas,
        )

        if not lista:
            self.tabela.mostrar_vazio()
            return

        # Guarda referências para consulta rápida ao desenhar.
        cat_por_id = {c["id"]: c for c in self._categorias}
        uni_por_id = {u["id"]: u for u in self._unidades}

        for despesa in lista:
            self._desenhar_despesa(despesa, cat_por_id, uni_por_id)

    def _desenhar_despesa(self, d, cat_por_id, uni_por_id):
        """Desenha uma linha da tabela com uma despesa."""
        linha = self.tabela.nova_linha()

        # ID
        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=d["id"],
                text_color=tema.AZUL_PRINCIPAL,
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ID,
                anchor="w",
            ),
            esticar="w",
        )

        # Descrição (corta com "…" se for longa)
        texto_desc = d["descricao"] or "(sem descrição)"
        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=texto_desc,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_DESCRICAO,
                anchor="w",
            ),
        )

        # Categoria (por nome, via lookup)
        categoria = cat_por_id.get(d["categoria_id"])
        nome_cat = categoria["nome"] if categoria else "—"
        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=nome_cat,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                width=_LARGURA_CATEGORIA,
                anchor="w",
            ),
        )

        # Valor
        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=componentes.formatar_valor(d["valor"]),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=_LARGURA_VALOR,
                anchor="e",
            ),
        )

        # Lançamento
        self.tabela.colocar(
            linha,
            4,
            ctk.CTkLabel(
                linha,
                text=_formatar_data(d["data_lancamento"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                width=_LARGURA_LANCAMENTO,
                anchor="center",
            ),
        )

        # Vencimento
        self.tabela.colocar(
            linha,
            5,
            ctk.CTkLabel(
                linha,
                text=_formatar_data(d["data_vencimento"]),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                width=_LARGURA_VENCIMENTO,
                anchor="center",
            ),
        )

        # Estado — chip + ponto vermelho se vencida
        bloco_estado = ctk.CTkFrame(linha, fg_color="transparent", height=26)
        bloco_estado.pack_propagate(False)

        ctk.CTkLabel(
            bloco_estado,
            text=d["estado"],
            text_color=self._cor_texto_estado(d["estado"]),
            fg_color=self._cor_fundo_estado(d["estado"]),
            corner_radius=8,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=80,
            height=22,
        ).pack(side="left")

        if despesas.esta_vencida(d):
            ctk.CTkLabel(
                bloco_estado,
                text="●",
                text_color=tema.TEXTO_ERRO,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="left", padx=(6, 0))

        self.tabela.colocar(linha, 6, bloco_estado)

        # Botão Gerir
        acoes = self.tabela.celula_acoes(linha, 7)
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
                command=lambda d=d: self._abrir_gerir(d),
            )
        )

    def _cor_fundo_estado(self, estado):
        return {
            "pendente": tema.AMARELO_AVISO,
            "paga": tema.VERDE_LIVRE,
            "cancelada": tema.CINZA_INDISPONIVEL,
        }.get(estado, tema.CINZA_INDISPONIVEL)

    def _cor_texto_estado(self, estado):
        return {
            "pendente": tema.TEXTO_AVISO,
            "paga": tema.TEXTO_LIVRE,
            "cancelada": tema.TEXTO_INDISPONIVEL,
        }.get(estado, tema.TEXTO_INDISPONIVEL)

    # -- ações --------------------------------------------------------

    def _abrir_escolha_via(self):
        """Abre o popup intermédio que pergunta se é despesa manual
        ou via stock (mockup A.3a). Esse popup, depois, abre o
        modal certo."""
        _EscolherViaModal(self)

    def _abrir_gerir(self, despesa):
        if despesa["estado"] == "pendente":
            _EditarDespesaModal(self, despesa)
        else:
            _DetalheDespesaModal(self, despesa)


# =====================================================================
# MODAIS DA VIA 1 — escolha da via, formulário manual, divisão
# =====================================================================


class _EscolherViaModal(ctk.CTkToplevel):
    """Popup intermédio do botão "+ Nova Despesa".

    Pergunta se é despesa manual (VIA 1) ou via stock (VIA 2).
    Fecha-se e abre o modal correspondente. Mesmo padrão do
    `_EscolherTipoRequisicaoModal` do Stock (gui_est_requisicoes.py).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 380, 300
        self.title("Nova Despesa")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="O que pretende criar?",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 14))

        self._cartao(
            "Despesa manual",
            "EDP, água, internet, obras. Sem itens de produto.",
            self._abrir_manual,
        )
        self._cartao(
            "Despesa via stock",
            "Compra de produtos para o armazém. Gera movimentos "
            "de entrada depois da confirmação.",
            self._abrir_stock,
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

        componentes.tornar_cliclavel(cartao, ao_clicar)

    def _abrir_manual(self):
        self.destroy()
        NovaDespesaManualModal(self.tela_lista)

    def _abrir_stock(self):
        self.destroy()
        # Import local para evitar que o ficheiro falhe a importar
        # enquanto o B.3 ainda não está colado.
        NovaDespesaStockModal(self.tela_lista)


class NovaDespesaManualModal(ctk.CTkToplevel):
    """Formulário da VIA 1 — despesa manual.

    Categoria obrigatória (esconde "Compra de Stock"), descrição
    obrigatória, valor obrigatório, resto opcional. Nasce
    `pendente` — o backend trata disso.
    """

    # Título fixo — usado nos erros, para a mensagem ser coerente.
    _TITULO = "Nova Despesa Manual"

    def __init__(self, tela_lista, despesa_para_editar=None):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.despesa_para_editar = despesa_para_editar

        # Referências preenchidas em _carregar_dados().
        self._categorias = []
        self._fornecedores = []
        self._unidades = []

        largura, altura = 620, 720
        self.title(self._TITULO)
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._montar_header()
        self._montar_campos()
        self._montar_rodape()
        self._carregar_dados()

    # -- montagem ----------------------------------------------------

    def _montar_header(self):
        ctk.CTkLabel(
            self,
            text=self._TITULO,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text="Fica pendente até ser marcada como paga.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 14))

    def _montar_campos(self):
        area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=24)
        self._area = area

        ctk.CTkLabel(
            area,
            text="IDENTIFICAÇÃO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.campo_descricao = self._campo_texto(
            area, "Descrição *", "ex.: Conta EDP — Setembro 2026"
        )

        linha = ctk.CTkFrame(area, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(0, weight=1, uniform="col")
        linha.grid_columnconfigure(1, weight=1, uniform="col")

        self.combo_categoria = self._campo_dropdown(
            linha, 0, "Categoria *", []
        )
        self.combo_fornecedor = self._campo_dropdown(
            linha, 1, "Fornecedor", ["— Nenhum —"]
        )

        linha2 = ctk.CTkFrame(area, fg_color="transparent")
        linha2.pack(fill="x", pady=4)
        linha2.grid_columnconfigure(0, weight=1, uniform="col")
        linha2.grid_columnconfigure(1, weight=1, uniform="col")

        self.campo_valor = self._campo_texto_em_linha(
            linha2, 0, "Valor *", "0,00 €"
        )
        self.campo_data_lancamento = self._campo_texto_em_linha(
            linha2,
            1,
            "Data de lançamento *",
            "dd/mm/aaaa",
            valor_inicial=datetime.date.today().strftime("%d/%m/%Y"),
        )

        linha3 = ctk.CTkFrame(area, fg_color="transparent")
        linha3.pack(fill="x", pady=4)
        linha3.grid_columnconfigure(0, weight=1, uniform="col")
        linha3.grid_columnconfigure(1, weight=1, uniform="col")

        self.campo_data_vencimento = self._campo_texto_em_linha(
            linha3, 0, "Data de vencimento", "dd/mm/aaaa (opcional)"
        )
        self.combo_unidade = self._campo_dropdown(
            linha3, 1, "Unidade", ["— Nenhuma (despesa geral) —"]
        )

        ctk.CTkLabel(
            area,
            text="OBSERVAÇÕES E COMPROVATIVO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        ctk.CTkLabel(
            area,
            text="Notas",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.campo_notas = ctk.CTkTextbox(
            area, height=60, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_notas.pack(fill="x", pady=(2, 8))

        self.campo_comprovativo = self._campo_texto(
            area, "Comprovativo", "ex.: edp_set2026.pdf (opcional)"
        )

        ctk.CTkFrame(area, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", pady=(12, 12)
        )

        self.check_recorrente = ctk.BooleanVar(value=False)
        bloco_rec = ctk.CTkFrame(
            area,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        bloco_rec.pack(fill="x")
        interno_rec = ctk.CTkFrame(bloco_rec, fg_color="transparent")
        interno_rec.pack(fill="x", padx=12, pady=10)
        ctk.CTkCheckBox(
            interno_rec,
            text="Despesa recorrente (mensal)",
            variable=self.check_recorrente,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            interno_rec,
            text="Gera automaticamente o lançamento do mês "
            "seguinte com os mesmos dados. O valor fica em branco.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=520,
        ).pack(anchor="w", pady=(4, 0))

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(8, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=150,
            height=34,
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
            text="Criar despesa",
            width=170,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    # -- helpers de campo --------------------------------------------

    def _campo_texto(self, master, rotulo, placeholder=""):
        ctk.CTkLabel(
            master,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        entrada = ctk.CTkEntry(
            master,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x")
        return entrada

    def _campo_texto_em_linha(
        self, master, coluna, rotulo, placeholder="", valor_inicial=None
    ):
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=0, column=coluna, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        entrada = ctk.CTkEntry(
            bloco,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x", pady=(2, 0))
        if valor_inicial is not None:
            entrada.insert(0, valor_inicial)
        return entrada

    def _campo_dropdown(self, master, coluna, rotulo, opcoes):
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=0, column=coluna, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        combo = componentes.Seletor(
            bloco,
            values=opcoes or ["—"],
            corner_radius=tema.RAIO_CAMPO,
        )
        if opcoes:
            combo.set(opcoes[0])
        combo.pack(fill="x", pady=(2, 0))
        return combo

    # -- carregamento de dados ---------------------------------------

    def _carregar_dados(self):
        # Categorias ativas — esconder "Compra de Stock" (só para
        # VIA 2).
        self._categorias = [
            c
            for c in despesas.listar_categorias()
            if c["nome"] != "Compra de Stock"
        ]
        nomes_cat = [c["nome"] for c in self._categorias] or ["—"]
        self.combo_categoria.configure(values=nomes_cat)
        self.combo_categoria.set(nomes_cat[0])

        # Fornecedores ativos.
        self._fornecedores = despesas.listar_fornecedores()
        nomes_forn = ["— Nenhum —"] + [f["nome"] for f in self._fornecedores]
        self.combo_fornecedor.configure(values=nomes_forn)
        self.combo_fornecedor.set(nomes_forn[0])

        # Unidades ativas com nome da propriedade.
        self._unidades = unidades.listar_com_propriedade()
        self._unidade_por_rotulo = {
            _rotulo_unidade(u): u["id"] for u in self._unidades
        }
        rotulos_uni = ["— Nenhuma (despesa geral) —"] + sorted(
            self._unidade_por_rotulo
        )
        self.combo_unidade.configure(values=rotulos_uni)
        self.combo_unidade.set(rotulos_uni[0])

    # -- leitura dos campos ------------------------------------------

    def _id_categoria(self):
        nome = self.combo_categoria.get()
        for c in self._categorias:
            if c["nome"] == nome:
                return c["id"]
        return None

    def _id_fornecedor(self):
        nome = self.combo_fornecedor.get()
        if nome == "— Nenhum —":
            return None
        for f in self._fornecedores:
            if f["nome"] == nome:
                return f["id"]
        return None

    def _id_unidade(self):
        rotulo = self.combo_unidade.get()
        return self._unidade_por_rotulo.get(rotulo)

    # -- guardar ------------------------------------------------------

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        # Validação de formato (conversões).
        try:
            categoria_id = self._id_categoria()
            if categoria_id is None:
                raise ValueError("Escolhe uma categoria.")

            descricao = self.campo_descricao.get().strip()
            if not descricao:
                raise ValueError("A descrição é obrigatória.")

            valor = _parse_decimal(
                self.campo_valor.get(),
                "Valor",
            )
            data_lancamento = _parse_data(
                self.campo_data_lancamento.get(), "Data de lançamento"
            )
            if data_lancamento is None:
                raise ValueError("A data de lançamento é obrigatória.")

            data_vencimento = _parse_data(
                self.campo_data_vencimento.get(),
                "Data de vencimento",
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        notas = self.campo_notas.get("1.0", "end").strip()
        comprovativo = self.campo_comprovativo.get().strip()

        try:
            despesas.criar_despesa_manual(
                categoria_id=categoria_id,
                valor=valor,
                data_lancamento=data_lancamento,
                responsavel_id=autor["id"],
                autor=autor,
                unidade_id=self._id_unidade(),
                fornecedor_id=self._id_fornecedor(),
                data_vencimento=data_vencimento,
                descricao=descricao,
                comprovativo_caminho=comprovativo,
                recorrente=self.check_recorrente.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso("Despesa criada com sucesso.")
        self.destroy()
        self.tela_lista._recarregar()


class DividirPorPropriedadeModal(ctk.CTkToplevel):
    """Formulário VIA 1 com "Aplicar a · dividir por propriedade".

    É aberto a partir do `NovaDespesaManualModal` (ou diretamente
    pela `ListaDespesas`, se adicionarmos um atalho futuro). Reusa
    a mesma estrutura de campos, só que troca o campo "Unidade" por
    "Aplicar a" + "Propriedade a dividir".
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self._categorias = []
        self._fornecedores = []
        self._propriedades = []
        self._unidades_por_propriedade = {}

        largura, altura = 620, 740
        self.title("Nova Despesa — dividir por propriedade")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._montar_header()
        self._montar_campos()
        self._montar_rodape()
        self._carregar_dados()

    def _montar_header(self):
        ctk.CTkLabel(
            self,
            text="Nova Despesa — dividir por propriedade",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "A mesma despesa é dividida igualmente pelas "
                "unidades ativas da propriedade escolhida."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=24, pady=(0, 14))

    def _montar_campos(self):
        area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=24)
        self._area = area

        ctk.CTkLabel(
            area,
            text="IDENTIFICAÇÃO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.campo_descricao = self._campo_texto(
            area, "Descrição *", "ex.: Internet — Setembro 2026"
        )

        linha = ctk.CTkFrame(area, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(0, weight=1, uniform="col")
        linha.grid_columnconfigure(1, weight=1, uniform="col")

        self.combo_categoria = self._campo_dropdown(
            linha, 0, "Categoria *", []
        )
        self.combo_fornecedor = self._campo_dropdown(
            linha, 1, "Fornecedor", ["— Nenhum —"]
        )

        linha2 = ctk.CTkFrame(area, fg_color="transparent")
        linha2.pack(fill="x", pady=4)
        linha2.grid_columnconfigure(0, weight=1, uniform="col")
        linha2.grid_columnconfigure(1, weight=1, uniform="col")

        self.campo_valor = self._campo_texto_em_linha(
            linha2, 0, "Valor total *", "0,00 €"
        )
        self.campo_data_lancamento = self._campo_texto_em_linha(
            linha2,
            1,
            "Data de lançamento *",
            "dd/mm/aaaa",
            valor_inicial=datetime.date.today().strftime("%d/%m/%Y"),
        )

        linha3 = ctk.CTkFrame(area, fg_color="transparent")
        linha3.pack(fill="x", pady=4)
        linha3.grid_columnconfigure(0, weight=1, uniform="col")
        linha3.grid_columnconfigure(1, weight=1, uniform="col")

        self.campo_data_vencimento = self._campo_texto_em_linha(
            linha3, 0, "Data de vencimento", "dd/mm/aaaa (opcional)"
        )

        # Bloco da propriedade (destacado a azul claro)
        bloco_prop = ctk.CTkFrame(
            linha3,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        bloco_prop.grid(row=0, column=1, sticky="ew", padx=4)

        ctk.CTkLabel(
            bloco_prop,
            text="Propriedade a dividir *",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))

        self.combo_propriedade = componentes.Seletor(
            bloco_prop,
            values=["—"],
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _v: self._atualizar_previsao(),
        )
        self.combo_propriedade.pack(fill="x", padx=10, pady=(0, 4))

        self.rotulo_previsao = ctk.CTkLabel(
            bloco_prop,
            text="",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=240,
        )
        self.rotulo_previsao.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            area,
            text="OBSERVAÇÕES E COMPROVATIVO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        ctk.CTkLabel(
            area,
            text="Notas",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.campo_notas = ctk.CTkTextbox(
            area, height=60, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_notas.pack(fill="x", pady=(2, 8))

        self.campo_comprovativo = self._campo_texto(
            area, "Comprovativo", "ex.: fatura_set2026.pdf (opcional)"
        )

        ctk.CTkFrame(area, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", pady=(12, 12)
        )

        self.check_recorrente = ctk.BooleanVar(value=False)
        bloco_rec = ctk.CTkFrame(
            area,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        bloco_rec.pack(fill="x")
        interno_rec = ctk.CTkFrame(bloco_rec, fg_color="transparent")
        interno_rec.pack(fill="x", padx=12, pady=10)
        ctk.CTkCheckBox(
            interno_rec,
            text="Despesa recorrente (mensal)",
            variable=self.check_recorrente,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            interno_rec,
            text="Gera automaticamente o lançamento do mês "
            "seguinte (todas as unidades).",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(8, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=150,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        self.botao_criar = ctk.CTkButton(
            rodape,
            text="Dividir e criar despesas",
            width=220,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._guardar,
        )
        self.botao_criar.pack(side="right")

    # -- helpers de campo (iguais aos do modal VIA 1) ----------------

    def _campo_texto(self, master, rotulo, placeholder=""):
        ctk.CTkLabel(
            master,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        entrada = ctk.CTkEntry(
            master,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x")
        return entrada

    def _campo_texto_em_linha(
        self, master, coluna, rotulo, placeholder="", valor_inicial=None
    ):
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=0, column=coluna, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        entrada = ctk.CTkEntry(
            bloco,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x", pady=(2, 0))
        if valor_inicial is not None:
            entrada.insert(0, valor_inicial)
        return entrada

    def _campo_dropdown(self, master, coluna, rotulo, opcoes):
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=0, column=coluna, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        combo = componentes.Seletor(
            bloco,
            values=opcoes or ["—"],
            corner_radius=tema.RAIO_CAMPO,
        )
        if opcoes:
            combo.set(opcoes[0])
        combo.pack(fill="x", pady=(2, 0))
        return combo

    # -- carregamento de dados ---------------------------------------

    def _carregar_dados(self):
        self._categorias = [
            c
            for c in despesas.listar_categorias()
            if c["nome"] != "Compra de Stock"
        ]
        nomes_cat = [c["nome"] for c in self._categorias] or ["—"]
        self.combo_categoria.configure(values=nomes_cat)
        self.combo_categoria.set(nomes_cat[0])

        self._fornecedores = despesas.listar_fornecedores()
        nomes_forn = ["— Nenhum —"] + [f["nome"] for f in self._fornecedores]
        self.combo_fornecedor.configure(values=nomes_forn)
        self.combo_fornecedor.set(nomes_forn[0])

        self._propriedades = propriedades.listar()
        # Guarda as unidades ativas de cada propriedade para a
        # previsão e para o `criar_despesa_manual`.
        self._unidades_por_propriedade = {
            p["id"]: unidades.listar(
                propriedade_id=p["id"], incluir_inativas=False
            )
            for p in self._propriedades
        }
        rotulos = [f"{p['nome']} ({p['id']})" for p in self._propriedades]
        self._propriedade_por_rotulo = {
            f"{p['nome']} ({p['id']})": p["id"] for p in self._propriedades
        }
        self.combo_propriedade.configure(values=rotulos or ["—"])
        if rotulos:
            self.combo_propriedade.set(rotulos[0])
        self._atualizar_previsao()

    def _atualizar_previsao(self):
        """Recalcula o texto da previsão por baixo do dropdown de
        propriedade: quantas unidades ativas e quanto vale cada
        despesa."""
        rotulo = self.combo_propriedade.get()
        prop_id = self._propriedade_por_rotulo.get(rotulo)
        if prop_id is None:
            self.rotulo_previsao.configure(text="")
            return

        ativas = self._unidades_por_propriedade.get(prop_id, [])
        n = len(ativas)
        if n == 0:
            self.rotulo_previsao.configure(
                text=(
                    "Esta propriedade não tem unidades ativas — "
                    "não há por quem dividir."
                )
            )
            return

        # Lê o valor total escrito. Se ainda não for válido, mostra
        # só a contagem de unidades.
        try:
            valor_total = _parse_decimal(
                self.campo_valor.get(),
                "Valor",
            )
        except ValueError:
            valor_total = None

        if valor_total is None or valor_total <= 0:
            self.rotulo_previsao.configure(
                text=(
                    f"{n} unidade(s) ativa(s). "
                    f"Introduz o valor total para ver a divisão."
                )
            )
            return

        por_unidade = (valor_total / n).quantize(Decimal("0.01"))
        self.rotulo_previsao.configure(
            text=(
                f"{n} unidade(s) ativa(s). "
                f"Vai criar {n} despesas de "
                f"{componentes.formatar_valor(por_unidade)} cada."
            )
        )

    # -- leitura -----------------------------------------------------

    def _id_categoria(self):
        nome = self.combo_categoria.get()
        for c in self._categorias:
            if c["nome"] == nome:
                return c["id"]
        return None

    def _id_fornecedor(self):
        nome = self.combo_fornecedor.get()
        if nome == "— Nenhum —":
            return None
        for f in self._fornecedores:
            if f["nome"] == nome:
                return f["id"]
        return None

    def _id_propriedade(self):
        return self._propriedade_por_rotulo.get(self.combo_propriedade.get())

    # -- guardar ------------------------------------------------------

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            categoria_id = self._id_categoria()
            if categoria_id is None:
                raise ValueError("Escolhe uma categoria.")

            descricao = self.campo_descricao.get().strip()
            if not descricao:
                raise ValueError("A descrição é obrigatória.")

            valor_total = _parse_decimal(
                self.campo_valor.get(),
                "Valor total",
            )
            if valor_total <= 0:
                raise ValueError("O valor a dividir tem de ser positivo.")

            data_lancamento = _parse_data(
                self.campo_data_lancamento.get(), "Data de lançamento"
            )
            if data_lancamento is None:
                raise ValueError("A data de lançamento é obrigatória.")

            data_vencimento = _parse_data(
                self.campo_data_vencimento.get(),
                "Data de vencimento",
            )

            propriedade_id = self._id_propriedade()
            if propriedade_id is None:
                raise ValueError("Escolhe uma propriedade.")
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        notas = self.campo_notas.get("1.0", "end").strip()
        comprovativo = self.campo_comprovativo.get().strip()

        try:
            criadas = despesas.dividir_despesa_por_propriedade(
                propriedade_id=propriedade_id,
                valor_total=valor_total,
                categoria_id=categoria_id,
                data_lancamento=data_lancamento,
                responsavel_id=autor["id"],
                autor=autor,
                fornecedor_id=self._id_fornecedor(),
                data_vencimento=data_vencimento,
                descricao=descricao,
                comprovativo_caminho=comprovativo,
                recorrente=self.check_recorrente.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"{len(criadas)} despesas criadas com sucesso."
        )
        self.destroy()
        self.tela_lista._recarregar()


# =====================================================================
# MODAIS DA VIA 2 — despesa via stock + confirmação dos itens
# =====================================================================


class NovaDespesaStockModal(ctk.CTkToplevel):
    """Formulário VIA 2 — despesa via stock.

    Categoria fixa "Compra de Stock" (mostrada como campo
    disabled). Sem vencimento, sem unidade, sem recorrente. A
    tabela de produtos é dinâmica: começa com uma linha, "+ Adicionar
    produto" acrescenta mais, o × remove.

    Nasce `paga` — o backend trata disso. Os itens ficam por
    confirmar (`itens_confirmados=False`) e só entram no stock
    quando o Master/Admin os confirmar (no ecrã Aprovações).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        # Referências preenchidas em _carregar_dados.
        self._produtos = []
        self._fornecedores = []

        # Cada elemento é um dict: {"moldura", "combo", "quantidade"}.
        self._linhas = []

        largura, altura = 660, 760
        self.title("Nova Despesa via Stock")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._montar_header()
        self._montar_campos()
        self._montar_rodape()
        self._carregar_dados()

    # -- montagem ----------------------------------------------------

    def _montar_header(self):
        ctk.CTkLabel(
            self,
            text="Nova Despesa via Stock",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "Fica paga na hora. Os itens só entram no stock "
                "depois de confirmados, no ecrã Aprovações."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=24, pady=(0, 14))

    def _montar_campos(self):
        area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=24)
        self._area = area

        ctk.CTkLabel(
            area,
            text="IDENTIFICAÇÃO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.campo_descricao = self._campo_texto(
            area,
            "Descrição *",
            "ex.: Compra de lixívias e detergentes — setembro",
        )

        linha = ctk.CTkFrame(area, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(0, weight=1, uniform="col")
        linha.grid_columnconfigure(1, weight=1, uniform="col")

        # Categoria — campo disabled, cinzento.
        bloco_cat = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_cat.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_cat,
            text="Categoria",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.campo_categoria = ctk.CTkEntry(
            bloco_cat,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.LINHA_ALTERNADA,
            text_color=tema.COR_TEXTO_SECUNDARIO,
        )
        self.campo_categoria.insert(0, "Compra de Stock")
        self.campo_categoria.configure(state="disabled")
        self.campo_categoria.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(
            bloco_cat,
            text="Fixada automaticamente.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        # Fornecedor.
        bloco_forn = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_forn.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_forn,
            text="Fornecedor",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_fornecedor = componentes.Seletor(
            bloco_forn,
            values=["— Nenhum —"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_fornecedor.set("— Nenhum —")
        self.combo_fornecedor.pack(fill="x", pady=(2, 0))

        self.campo_data_lancamento = self._campo_texto(
            area,
            "Data de lançamento *",
            "dd/mm/aaaa",
        )
        self.campo_data_lancamento.insert(
            0, datetime.date.today().strftime("%d/%m/%Y")
        )

        ctk.CTkLabel(
            area,
            text="PRODUTOS",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        # Cartão com cabeçalho + linhas dinâmicas + botão add.
        cartao = ctk.CTkFrame(
            area,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x")

        cabecalho = ctk.CTkFrame(
            cartao,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")
        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)
        for texto, largura in (
            ("PRODUTO", 320),
            ("QUANTIDADE", 110),
            ("", 40),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor="w",
            ).pack(side="left")

        self._area_linhas = ctk.CTkFrame(cartao, fg_color="transparent")
        self._area_linhas.pack(fill="x", padx=16, pady=(6, 8))

        ctk.CTkButton(
            cartao,
            text="+ Adicionar produto",
            width=180,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            command=self._acrescentar_linha,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # Aviso sobre criar produto novo.
        aviso = ctk.CTkFrame(
            area,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        aviso.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(
            aviso,
            text=(
                "Se o produto ainda não existir no catálogo, "
                'escolhe "+ Criar produto novo" na lista — os '
                "dados completos são pedidos a seguir."
            ),
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            area,
            text="VALOR E OBSERVAÇÕES",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 6))

        bloco_valor = ctk.CTkFrame(
            area,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        bloco_valor.pack(fill="x")
        ctk.CTkLabel(
            bloco_valor,
            text="Valor total da despesa *",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 2))
        self.campo_valor = ctk.CTkEntry(
            bloco_valor,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="0,00 €",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.campo_valor.pack(fill="x", padx=12)
        ctk.CTkLabel(
            bloco_valor,
            text=(
                "Digitado à mão. Não é a soma dos itens — o valor "
                "vive só aqui."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=12, pady=(2, 10))

        ctk.CTkLabel(
            area,
            text="Notas",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(10, 2))
        self.campo_notas = ctk.CTkTextbox(
            area, height=60, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_notas.pack(fill="x")

        self.campo_comprovativo = self._campo_texto(
            area,
            "Comprovativo",
            "ex.: fatura_makro_set2026.pdf (opcional)",
        )

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(8, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=150,
            height=34,
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
            text="Criar despesa",
            width=170,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    # -- helpers de campo --------------------------------------------

    def _campo_texto(self, master, rotulo, placeholder=""):
        ctk.CTkLabel(
            master,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        entrada = ctk.CTkEntry(
            master,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x")
        return entrada

    # -- tabela dinâmica de produtos ---------------------------------

    def _rotulos_produtos(self):
        """Rótulos do dropdown de cada linha. Inclui um item
        especial no fim, "+ Criar produto novo…", que abre o
        sub-modal."""
        return [f"{p['nome']} ({p['id']})" for p in self._produtos] + [
            "+ Criar produto novo…"
        ]

    def _produto_por_rotulo(self, rotulo):
        for p in self._produtos:
            if f"{p['nome']} ({p['id']})" == rotulo:
                return p
        return None

    def _acrescentar_linha(self):
        if not self._produtos:
            # Sem produtos no catálogo — não há linha possível. O
            # utilizador tem de criar um produto novo primeiro.
            self._abrir_criar_produto()
            return

        moldura = ctk.CTkFrame(self._area_linhas, fg_color="transparent")
        moldura.pack(fill="x", pady=3)

        combo = componentes.Seletor(
            moldura,
            values=self._rotulos_produtos(),
            width=320,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda valor, m=moldura: self._ao_escolher_produto(
                valor, m
            ),
        )
        combo.set(self._rotulos_produtos()[0])
        combo.pack(side="left")

        campo_qtd = ctk.CTkEntry(
            moldura,
            width=110,
            corner_radius=tema.RAIO_CAMPO,
            justify="center",
            placeholder_text="0",
        )
        campo_qtd.pack(side="left", padx=(10, 0))

        # Guarda a referência antes de a limpar — o botão × vai
        # precisar de apagar a linha inteira.
        linha = {
            "moldura": moldura,
            "combo": combo,
            "quantidade": campo_qtd,
        }
        self._linhas.append(linha)

        ctk.CTkButton(
            moldura,
            text="×",
            width=30,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=lambda l=linha: self._remover_linha(l),
        ).pack(side="left", padx=(10, 0))

    def _remover_linha(self, linha):
        if linha in self._linhas:
            self._linhas.remove(linha)
        linha["moldura"].destroy()

    def _ao_escolher_produto(self, valor, moldura):
        """Se o valor escolhido for "+ Criar produto novo…", abre o
        sub-modal e volta a pôr a linha no primeiro produto real
        (a linha nova criada pelo sub-modal será acrescentada
        automaticamente)."""
        if valor != "+ Criar produto novo…":
            return
        # Volta ao primeiro produto, antes de abrir o sub-modal.
        if self._produtos:
            moldura.destroy()
            self._linhas = [
                l for l in self._linhas if l["moldura"] is not moldura
            ]
        self._abrir_criar_produto()

    def _abrir_criar_produto(self):
        _EscolherProdutoModal(self, ao_criar=self._produto_foi_criado)

    def _produto_foi_criado(self, produto):
        """Chamada pelo `_EscolherProdutoModal` quando um produto
        novo é criado. Adiciona-o à lista local e cria a linha."""
        self._produtos.append(produto)
        self._acrescentar_linha()
        # Põe a última linha no produto novo.
        if self._linhas:
            ultima = self._linhas[-1]
            rotulo = f"{produto['nome']} ({produto['id']})"
            ultima["combo"].set(rotulo)

    # -- carregamento / leitura --------------------------------------

    def _carregar_dados(self):
        # Categoria "Compra de Stock" — valida que existe e está
        # ativa. Se não estiver, avisa e fecha (não há como criar
        # despesa VIA 2 sem ela).
        try:
            despesas.criar_despesa_stock  # noqa: B018 (marca de API)
        except AttributeError:
            pass

        self._produtos = estoque.listar_produtos()
        self._fornecedores = despesas.listar_fornecedores()

        nomes_forn = ["— Nenhum —"] + [f["nome"] for f in self._fornecedores]
        self.combo_fornecedor.configure(values=nomes_forn)
        self.combo_fornecedor.set(nomes_forn[0])

        # Cria a primeira linha, para o utilizador começar com um
        # produto já visível.
        self._acrescentar_linha()

    def _id_fornecedor(self):
        nome = self.combo_fornecedor.get()
        if nome == "— Nenhum —":
            return None
        for f in self._fornecedores:
            if f["nome"] == nome:
                return f["id"]
        return None

    def _itens(self):
        """Devolve a lista de itens no formato que o módulo de
        negócio espera. Levanta ValueError se alguma linha estiver
        mal preenchida."""
        itens = []
        for linha in self._linhas:
            rotulo = linha["combo"].get()
            produto = self._produto_por_rotulo(rotulo)
            if produto is None:
                raise ValueError("Escolhe um produto válido em cada linha.")

            texto_qtd = linha["quantidade"].get().strip()
            if not texto_qtd.isdigit() or int(texto_qtd) <= 0:
                raise ValueError(
                    f"Quantidade inválida para '{produto['nome']}'."
                )

            itens.append(
                {
                    "produto_id": produto["id"],
                    "quantidade": int(texto_qtd),
                }
            )

        if not itens:
            raise ValueError("A despesa tem de ter pelo menos um produto.")
        return itens

    # -- guardar ------------------------------------------------------

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            descricao = self.campo_descricao.get().strip()
            if not descricao:
                raise ValueError("A descrição é obrigatória.")

            valor_total = _parse_decimal(
                self.campo_valor.get(),
                "Valor total",
            )

            data_lancamento = _parse_data(
                self.campo_data_lancamento.get(), "Data de lançamento"
            )
            if data_lancamento is None:
                raise ValueError("A data de lançamento é obrigatória.")

            itens = self._itens()
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        notas = self.campo_notas.get("1.0", "end").strip()
        comprovativo = self.campo_comprovativo.get().strip()

        try:
            despesa, _itens_criados = despesas.criar_despesa_stock(
                itens=itens,
                valor_total=valor_total,
                data_lancamento=data_lancamento,
                responsavel_id=autor["id"],
                autor=autor,
                fornecedor_id=self._id_fornecedor(),
                descricao=descricao,
                comprovativo_caminho=comprovativo,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Despesa {despesa['id']} criada. Os itens aguardam "
            f"confirmação no ecrã Aprovações."
        )
        self.destroy()
        self.tela_lista._recarregar()


class _EscolherProdutoModal(ctk.CTkToplevel):
    """Sub-modal para criar um produto novo — chamado dentro do
    formulário VIA 2, quando o utilizador escolhe "+ Criar produto
    novo…" no dropdown de produto.

    Pede os 4 campos completos (`nome`, `unidade_medida`,
    `stock_minimo`, `tipo_produto`) e chama `estoque.criar_produto`.
    Devolve o produto criado via `ao_criar(produto)`.
    """

    def __init__(self, master, ao_criar):
        super().__init__(master)
        self.ao_criar = ao_criar

        largura, altura = 480, 480
        self.title("Criar produto novo")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        componentes.centrar_sobre(self, master, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self,
            text="Criar produto novo",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "O produto fica logo disponível no catálogo. "
                "Preenche os 4 campos."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=420,
        ).pack(anchor="w", padx=24, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Nome *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 8))

        ctk.CTkLabel(
            self,
            text="Unidade de medida *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_unidade = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: un, L, kg, cx",
        )
        self.campo_unidade.pack(fill="x", padx=24, pady=(2, 8))

        ctk.CTkLabel(
            self,
            text="Stock mínimo",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_stock = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="0",
        )
        self.campo_stock.insert(0, "0")
        self.campo_stock.pack(fill="x", padx=24, pady=(2, 8))

        ctk.CTkLabel(
            self,
            text="Tipo de produto *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.combo_tipo = componentes.Seletor(
            self,
            values=["consumivel", "roupa_cama", "roupa_banho", "outro"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_tipo.set("consumivel")
        self.combo_tipo.pack(fill="x", padx=24, pady=(2, 14))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(0, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=34,
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
            text="Criar produto",
            width=150,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):

        nome = self.campo_nome.get().strip()
        unidade = self.campo_unidade.get().strip()

        if not nome or not unidade:
            componentes.mostrar_erro(
                "Nome e unidade de medida são obrigatórios."
            )
            return

        texto_stock = self.campo_stock.get().strip() or "0"
        if not texto_stock.isdigit():
            componentes.mostrar_erro(
                "O stock mínimo tem de ser um número inteiro."
            )
            return

        try:
            produto = estoque.criar_produto(
                nome=nome,
                unidade_medida=unidade,
                stock_minimo=int(texto_stock),
                tipo_produto=self.combo_tipo.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.ao_criar(produto)
        self.destroy()


class ConfirmarItensModal(ctk.CTkToplevel):
    """Confirmação dos itens de uma despesa VIA 2.

    Mostra os itens da despesa (só leitura) e um botão grande
    "Confirmar — gerar entradas no stock". Quando confirmado,
    chama `despesas.confirmar_itens_despesa`, que gera um movimento
    de entrada por item.

    A partir do ecrã Aprovações (Bloco B.4), o botão "Confirmar" de
    uma linha VIA 2 abre isto.
    """

    def __init__(self, tela_aprovacoes, despesa):
        super().__init__(tela_aprovacoes)
        self.tela_aprovacoes = tela_aprovacoes
        self.despesa = despesa

        itens = despesas.listar_itens_despesa(despesa["id"])
        self.itens = itens

        largura, altura = 620, 520
        self.title(f"Confirmar itens — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_aprovacoes)
        componentes.centrar_sobre(self, tela_aprovacoes, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self,
            text=f"Confirmar itens — {despesa['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "Ao confirmar, é gerada uma entrada em stock por "
                "cada item. A despesa fica marcada como confirmada."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=24, pady=(0, 14))

        self._montar_tabela()
        self._montar_rodape()

    def _montar_tabela(self):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=24)

        cabecalho = ctk.CTkFrame(
            cartao,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")
        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)
        for texto, largura, alinhamento in (
            ("PRODUTO", 320, "w"),
            ("QUANTIDADE", 120, "center"),
        ):
            ctk.CTkLabel(
                interno,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor=alinhamento,
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for item in self.itens:
            produto = estoque.procurar_produto(item["produto_id"])
            nome = produto["nome"] if produto else item["produto_id"]

            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=nome,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=320,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                linha,
                text=str(item["quantidade"]),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=100,
                anchor="center",
            ).pack(side="left")

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=36,
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
            text="Confirmar — gerar entradas no stock",
            width=300,
            height=36,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._confirmar,
        ).pack(side="right")

    def _confirmar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.confirmar_itens_despesa(self.despesa["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Itens de {self.despesa['id']} confirmados. "
            f"Entradas geradas no stock."
        )
        self.destroy()
        self.tela_aprovacoes._recarregar()


# =====================================================================
# ECRÃ APROVAÇÕES
# =====================================================================


class Aprovacoes(ctk.CTkFrame):
    """Ecrã "Aprovações" — despesas pendentes + itens VIA 2 por
    confirmar.

    Duas secções, cada uma com a sua tabela:
      - Despesas pendentes (VIA 1) → botão "Gerir" abre o
        `_GerirDespesaPendenteModal`.
      - Itens de despesa via stock por confirmar → botão
        "Confirmar" abre o `ConfirmarItensModal`.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        self._categorias_por_id = {}

        componentes.Cabecalho(self, titulo="Aprovações").pack(fill="x")

        self._area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._area.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento -------------------------------------------------

    def _recarregar(self):
        for w in self._area.winfo_children():
            w.destroy()

        self._categorias_por_id = {
            c["id"]: c for c in despesas.listar_categorias()
        }

        self._desenhar_seccao_pendentes()
        self._desenhar_seccao_itens_via2()

    # -- secção 1 — despesas pendentes --------------------------------

    def _desenhar_seccao_pendentes(self):
        pendentes = despesas.listar_despesas(estado="pendente")

        self._titulo_seccao(f"Despesas pendentes", len(pendentes))

        if not pendentes:
            self._mensagem_vazio(
                "Sem despesas pendentes. "
                "Todas as despesas lançadas já foram pagas ou "
                "canceladas."
            )
            return

        tabela = ctk.CTkFrame(
            self._area,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        tabela.pack(fill="x", pady=(0, 20))

        # Cabeçalho (grid alinhado com as linhas — mesma largura
        # de coluna em ambos).
        cabecalho = ctk.CTkFrame(
            tabela,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")
        grelha_cab = ctk.CTkFrame(cabecalho, fg_color="transparent")
        grelha_cab.pack(fill="x", padx=16, pady=8)

        for texto, largura, alinhamento in (
            ("ID", 80, "w"),
            ("DESCRIÇÃO", 200, "w"),
            ("CATEGORIA", 110, "w"),
            ("VALOR", 90, "e"),
            ("VENCIMENTO", 100, "center"),
            ("SITUAÇÃO", 130, "w"),
            ("LANÇAMENTO", 100, "center"),
            ("AÇÕES", 100, "center"),
        ):
            ctk.CTkLabel(
                grelha_cab,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor=alinhamento,
            ).pack(side="left")

        ctk.CTkFrame(tabela, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for i, d in enumerate(pendentes):
            self._linha_pendente(tabela, d, i)

    def _linha_pendente(self, master, d, indice):
        vencida = despesas.esta_vencida(d)

        cor_fundo = tema.LINHA_ALTERNADA if indice % 2 else "transparent"

        linha = ctk.CTkFrame(master, fg_color=cor_fundo, height=52)
        linha.pack(fill="x")
        linha.pack_propagate(False)

        # Borda vermelha à esquerda se vencida — simulada com um
        # frame fino à esquerda.
        if vencida:
            ctk.CTkFrame(linha, width=4, fg_color=tema.VERMELHO_ERRO).pack(
                side="left", fill="y"
            )

        grelha = ctk.CTkFrame(linha, fg_color="transparent")
        grelha.pack(fill="x", padx=16, pady=8)

        # ID
        ctk.CTkLabel(
            grelha,
            text=d["id"],
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=90,
            anchor="w",
        ).pack(side="left")

        # Descrição
        ctk.CTkLabel(
            grelha,
            text=d["descricao"] or "(sem descrição)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            width=200,
            anchor="w",
        ).pack(side="left")

        # Categoria
        cat = self._categorias_por_id.get(d["categoria_id"])
        ctk.CTkLabel(
            grelha,
            text=cat["nome"] if cat else "—",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=130,
            anchor="w",
        ).pack(side="left")

        # Valor
        ctk.CTkLabel(
            grelha,
            text=componentes.formatar_valor(d["valor"]),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=110,
            anchor="e",
        ).pack(side="left")

        # Vencimento
        ctk.CTkLabel(
            grelha,
            text=_formatar_data(d["data_vencimento"]),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=100,
            anchor="center",
        ).pack(side="left")

        # Situação (texto descritivo do prazo)
        ctk.CTkLabel(
            grelha,
            text=self._situacao_prazo(d),
            text_color=(
                tema.TEXTO_ERRO if vencida else tema.COR_TEXTO_SECUNDARIO
            ),
            font=ctk.CTkFont(size=11),
            width=130,
            anchor="w",
        ).pack(side="left")

        # Lançamento
        ctk.CTkLabel(
            grelha,
            text=_formatar_data(d["data_lancamento"]),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="center",
        ).pack(side="left")

        # Botão Gerir
        ctk.CTkButton(
            grelha,
            text="Gerir",
            width=76,
            height=26,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=lambda d=d: _AprovarDespesaModal(self, d),
        ).pack(side="left")

    def _situacao_prazo(self, d):
        """Texto descritivo do prazo: 'vencida há X dias',
        'vence em X dias' ou 'sem prazo'."""
        if d["data_vencimento"] is None:
            return "sem prazo"

        delta = (d["data_vencimento"] - datetime.date.today()).days
        if delta < 0:
            return f"vencida há {abs(delta)} dias"
        if delta == 0:
            return "vence hoje"
        return f"vence em {delta} dias"

    # -- secção 2 — itens VIA 2 por confirmar -------------------------

    def _desenhar_seccao_itens_via2(self):
        # Todas as despesas via stock cujos itens ainda não foram
        # confirmados. Filtra pela flag `itens_confirmados`.
        todas = despesas.listar_despesas(estado="paga")
        por_confirmar = [d for d in todas if not d["itens_confirmados"]]

        self._titulo_seccao(
            "Itens de despesa por confirmar (VIA 2)",
            len(por_confirmar),
        )

        if not por_confirmar:
            self._mensagem_vazio(
                "Sem itens por confirmar. Todas as compras via "
                "stock já foram verificadas."
            )
            return

        tabela = ctk.CTkFrame(
            self._area,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        tabela.pack(fill="x", pady=(0, 12))

        cabecalho = ctk.CTkFrame(
            tabela,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")
        grelha_cab = ctk.CTkFrame(cabecalho, fg_color="transparent")
        grelha_cab.pack(fill="x", padx=16, pady=8)

        for texto, largura, alinhamento in (
            ("ID", 90, "w"),
            ("DESCRIÇÃO", 260, "w"),
            ("ITENS", 110, "center"),
            ("VALOR", 110, "e"),
            ("FORNECEDOR", 140, "w"),
            ("PAGO EM", 110, "center"),
            ("AÇÕES", 160, "center"),
        ):
            ctk.CTkLabel(
                grelha_cab,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor=alinhamento,
            ).pack(side="left")

        ctk.CTkFrame(tabela, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        for i, d in enumerate(por_confirmar):
            self._linha_itens_via2(tabela, d, i)

    def _linha_itens_via2(self, master, d, indice):
        cor_fundo = tema.LINHA_ALTERNADA if indice % 2 else "transparent"

        linha = ctk.CTkFrame(master, fg_color=cor_fundo, height=52)
        linha.pack(fill="x")
        linha.pack_propagate(False)

        grelha = ctk.CTkFrame(linha, fg_color="transparent")
        grelha.pack(fill="x", padx=16, pady=8)

        # ID
        ctk.CTkLabel(
            grelha,
            text=d["id"],
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=90,
            anchor="w",
        ).pack(side="left")

        # Descrição + badge "via stock"
        bloco_desc = ctk.CTkFrame(grelha, fg_color="transparent")
        bloco_desc.pack(side="left")
        ctk.CTkLabel(
            bloco_desc,
            text=d["descricao"] or "(sem descrição)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            bloco_desc,
            text=" via stock ",
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(side="left", padx=(6, 0))

        # Bloco invisível para reservar largura à descrição (260px)
        # — sem isto, o "pack" encolhia a célula ao tamanho real.
        espacador = ctk.CTkFrame(
            grelha, fg_color="transparent", width=260, height=1
        )
        espacador.pack(side="left")
        espacador.pack_propagate(False)

        # Contagem de itens
        itens = despesas.listar_itens_despesa(d["id"])
        ctk.CTkLabel(
            grelha,
            text=f"{len(itens)} item(ns)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="center",
        ).pack(side="left")

        # Valor
        ctk.CTkLabel(
            grelha,
            text=componentes.formatar_valor(d["valor"]),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=110,
            anchor="e",
        ).pack(side="left")

        # Fornecedor
        fornecedor_nome = "—"
        if d["fornecedor_id"]:
            forn = despesas.procurar_fornecedor(d["fornecedor_id"])
            if forn:
                fornecedor_nome = forn["nome"]
        ctk.CTkLabel(
            grelha,
            text=fornecedor_nome,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=140,
            anchor="w",
        ).pack(side="left")

        # Pago em
        ctk.CTkLabel(
            grelha,
            text=_formatar_data(d["data_pagamento"]),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="center",
        ).pack(side="left")

        # Botão Confirmar
        ctk.CTkButton(
            grelha,
            text="Confirmar itens",
            width=140,
            height=26,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda d=d: ConfirmarItensModal(self, d),
        ).pack(side="left")

    # -- helpers de apresentação --------------------------------------

    def _titulo_seccao(self, texto, contagem):
        bloco = ctk.CTkFrame(self._area, fg_color="transparent")
        bloco.pack(fill="x", pady=(8, 8))

        ctk.CTkLabel(
            bloco,
            text=texto.upper(),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            bloco,
            text=f"  {contagem}",
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=10,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=9,
            pady=2,
        ).pack(side="left")

    def _mensagem_vazio(self, texto):
        ctk.CTkLabel(
            self._area,
            text=texto,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(4, 20))


# =====================================================================
# MODAL GERIR (despesa pendente) + SUB-MODAIS
# =====================================================================


class _AprovarDespesaModal(ctk.CTkToplevel):
    """Modal de aprovação de uma despesa pendente.

    Ficha read-only, aviso de vencida quando aplicável, e duas
    ações: Marcar como paga · Cancelar despesa.

    Só aparece no ecrã Aprovações. Edição de dados vive no
    `_EditarDespesaModal` (ecrã Despesas) — são sítios diferentes
    com propósitos diferentes.
    """

    def __init__(self, tela_aprovacoes, despesa):
        super().__init__(tela_aprovacoes)
        self.tela_aprovacoes = tela_aprovacoes
        self.despesa = despesa

        largura, altura = 520, 620
        self.title(f"Gerir — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_aprovacoes)
        componentes.centrar_sobre(self, tela_aprovacoes, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._montar_header()
        self._montar_ficha()
        self._montar_acoes()

    def _montar_header(self):
        ctk.CTkLabel(
            self,
            text=self.despesa["descricao"] or "(sem descrição)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=460,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=22, pady=(18, 2))

        categoria_nome = "—"
        categoria = despesas.procurar_categoria(self.despesa["categoria_id"])
        if categoria:
            categoria_nome = categoria["nome"]

        fornecedor_nome = ""
        if self.despesa["fornecedor_id"]:
            forn = despesas.procurar_fornecedor(self.despesa["fornecedor_id"])
            if forn:
                fornecedor_nome = f" · {forn['nome']}"

        ctk.CTkLabel(
            self,
            text=(
                f"{self.despesa['id']} · {categoria_nome}" f"{fornecedor_nome}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(0, 12))

    def _montar_ficha(self):
        # Aviso de vencida (só se aplicável).
        if despesas.esta_vencida(self.despesa):
            delta = (
                datetime.date.today() - self.despesa["data_vencimento"]
            ).days
            aviso = ctk.CTkFrame(
                self,
                fg_color=tema.VERMELHO_ERRO,
                corner_radius=tema.RAIO_CAMPO,
            )
            aviso.pack(fill="x", padx=22, pady=(0, 12))
            ctk.CTkLabel(
                aviso,
                text=(
                    f"⚠ Esta despesa está vencida.\n"
                    f"Data de vencimento: "
                    f"{_formatar_data(self.despesa['data_vencimento'])}"
                    f" · vencida há {delta} dias."
                ),
                text_color=tema.TEXTO_ERRO,
                font=ctk.CTkFont(size=11),
                justify="left",
                anchor="w",
                wraplength=440,
            ).pack(fill="x", padx=14, pady=10)

        ficha = ctk.CTkFrame(
            self,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=tema.RAIO_CAMPO,
        )
        ficha.pack(fill="x", padx=22, pady=(0, 14))

        interno = ctk.CTkFrame(ficha, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=12)

        self._linha_ficha(interno, "Categoria", self._nome_categoria())
        self._linha_ficha(interno, "Fornecedor", self._nome_fornecedor())
        self._linha_ficha(
            interno,
            "Valor",
            componentes.formatar_valor(self.despesa["valor"]),
            forte=True,
        )
        self._linha_ficha(
            interno,
            "Lançamento",
            _formatar_data(self.despesa["data_lancamento"]),
        )
        self._linha_ficha(
            interno,
            "Vencimento",
            _formatar_data(self.despesa["data_vencimento"]),
        )
        if self.despesa["unidade_id"]:
            uni = unidades.procurar(self.despesa["unidade_id"])
            self._linha_ficha(
                interno,
                "Unidade",
                (
                    f"{uni['nome']} ({uni['id']})"
                    if uni
                    else self.despesa["unidade_id"]
                ),
            )

    def _nome_categoria(self):
        c = despesas.procurar_categoria(self.despesa["categoria_id"])
        return c["nome"] if c else "—"

    def _nome_fornecedor(self):
        if not self.despesa["fornecedor_id"]:
            return "—"
        f = despesas.procurar_fornecedor(self.despesa["fornecedor_id"])
        return f["nome"] if f else "—"

    def _linha_ficha(self, master, rotulo, valor, forte=False):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", pady=3)

        ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=valor,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold" if forte else "normal"),
            anchor="w",
        ).pack(side="left")

    def _montar_acoes(self):
        bloco = ctk.CTkFrame(self, fg_color="transparent")
        bloco.pack(fill="x", padx=22, pady=(6, 18), side="bottom")

        ctk.CTkButton(
            bloco,
            text="Marcar como paga",
            height=36,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.VERDE,
            text_color=tema.VERDE,
            hover_color=tema.VERDE_LIVRE,
            command=self._marcar_paga,
        ).pack(fill="x", pady=3)

        ctk.CTkFrame(bloco, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", pady=(8, 5)
        )

        ctk.CTkButton(
            bloco,
            text="Cancelar despesa",
            height=36,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.TEXTO_ERRO,
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._cancelar_despesa,
        ).pack(fill="x", pady=3)

        ctk.CTkButton(
            bloco,
            text="Fechar",
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", pady=(8, 0))

    # -- ações --------------------------------------------------------

    def _marcar_paga(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        if not componentes.confirmar(
            f"Marcar {self.despesa['id']} como paga hoje?"
        ):
            return

        try:
            despesas.marcar_paga(
                self.despesa["id"],
                datetime.date.today(),
                autor,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Despesa {self.despesa['id']} marcada como paga."
        )
        self.destroy()
        self.tela_aprovacoes._recarregar()

    def _cancelar_despesa(self):
        self.destroy()
        _CancelarDespesaModal(self.tela_aprovacoes, self.despesa)


class _CancelarDespesaModal(ctk.CTkToplevel):
    """Sub-modal para cancelar uma despesa — exige motivo."""

    def __init__(self, tela_aprovacoes, despesa):
        super().__init__(tela_aprovacoes)
        self.tela_aprovacoes = tela_aprovacoes
        self.despesa = despesa

        largura, altura = 460, 380
        self.title(f"Cancelar — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_aprovacoes)
        componentes.centrar_sobre(self, tela_aprovacoes, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self,
            text="Cancelar despesa",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                f"{despesa['id']} · "
                f"{despesa['descricao'] or '(sem descrição)'}\n"
                f"Valor: {componentes.formatar_valor(despesa['valor'])}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text=(
                "A despesa não desaparece — fica com o estado "
                "'cancelada' no histórico."
            ),
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w",
            wraplength=400,
            padx=12,
            pady=10,
        ).pack(fill="x", padx=24, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Motivo do cancelamento *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_motivo = ctk.CTkTextbox(
            self, height=70, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_motivo.pack(fill="x", padx=24, pady=(2, 6))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(0, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Voltar",
            width=130,
            height=34,
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
            text="Cancelar despesa",
            width=160,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            text_color="#FFFFFF",
            command=self._cancelar,
        ).pack(side="right")

    def _cancelar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        motivo = self.campo_motivo.get("1.0", "end").strip()
        if not motivo:
            componentes.mostrar_erro("O motivo é obrigatório para cancelar.")
            return

        try:
            despesas.cancelar_despesa(self.despesa["id"], motivo, autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Despesa {self.despesa['id']} cancelada.")
        self.destroy()
        self.tela_aprovacoes._recarregar()


class _EditarDespesaModal(ctk.CTkToplevel):
    """Modal de edição completa de uma despesa pendente.

    Permite editar: valor, descrição, categoria, fornecedor, data
    de lançamento, data de vencimento. Não permite editar unidade
    nem recorrente (decisão tomada com o aluno — são estruturais).

    Aberto pelo "Gerir" da Lista Despesas, quando a despesa está
    pendente. Para despesas pagas/canceladas abre o
    `_DetalheDespesaModal` (só leitura).
    """

    def __init__(self, tela_lista, despesa):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.despesa = despesa

        self._categorias = []
        self._fornecedores = []

        largura, altura = 620, 720
        self.title(f"Editar — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._montar_header()
        self._montar_campos()
        self._montar_rodape()
        self._carregar_dados()

    def _montar_header(self):
        ctk.CTkLabel(
            self,
            text=f"Editar {self.despesa['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            self,
            text=(
                "Fica pendente até ser marcada como paga. "
                "A unidade e a recorrência não se alteram aqui."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=24, pady=(0, 14))

    def _montar_campos(self):
        area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=24)

        # Descrição
        ctk.CTkLabel(
            area,
            text="Descrição *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        self.campo_descricao = ctk.CTkEntry(
            area, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_descricao.insert(0, self.despesa["descricao"])
        self.campo_descricao.pack(fill="x")

        # Categoria + Fornecedor
        linha = ctk.CTkFrame(area, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        linha.grid_columnconfigure(0, weight=1, uniform="col")
        linha.grid_columnconfigure(1, weight=1, uniform="col")

        bloco_cat = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_cat.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_cat,
            text="Categoria *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_categoria = componentes.Seletor(
            bloco_cat, values=["—"], corner_radius=tema.RAIO_CAMPO
        )
        self.combo_categoria.pack(fill="x", pady=(2, 0))

        bloco_forn = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_forn.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_forn,
            text="Fornecedor",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.combo_fornecedor = componentes.Seletor(
            bloco_forn, values=["— Nenhum —"], corner_radius=tema.RAIO_CAMPO
        )
        self.combo_fornecedor.pack(fill="x", pady=(2, 0))

        # Valor + Lançamento
        linha2 = ctk.CTkFrame(area, fg_color="transparent")
        linha2.pack(fill="x", pady=4)
        linha2.grid_columnconfigure(0, weight=1, uniform="col")
        linha2.grid_columnconfigure(1, weight=1, uniform="col")

        bloco_valor = ctk.CTkFrame(linha2, fg_color="transparent")
        bloco_valor.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_valor,
            text="Valor *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.campo_valor = ctk.CTkEntry(
            bloco_valor, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_valor.insert(
            0, str(self.despesa["valor"]).replace(".", ",")
        )
        self.campo_valor.pack(fill="x", pady=(2, 0))

        bloco_lanc = ctk.CTkFrame(linha2, fg_color="transparent")
        bloco_lanc.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkLabel(
            bloco_lanc,
            text="Data de lançamento *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.campo_data_lancamento = ctk.CTkEntry(
            bloco_lanc, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_data_lancamento.insert(
            0, _formatar_data(self.despesa["data_lancamento"])
        )
        self.campo_data_lancamento.pack(fill="x", pady=(2, 0))

        # Vencimento
        ctk.CTkLabel(
            area,
            text="Data de vencimento",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        self.campo_data_vencimento = ctk.CTkEntry(
            area,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="dd/mm/aaaa (deixa em branco para limpar)",
        )
        if self.despesa["data_vencimento"]:
            self.campo_data_vencimento.insert(
                0, _formatar_data(self.despesa["data_vencimento"])
            )
        self.campo_data_vencimento.pack(fill="x")

        ctk.CTkLabel(
            area,
            text=(
                "Deixa em branco para limpar a data de vencimento. "
                "Não pode ser anterior à data de lançamento."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", pady=(2, 0))

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(8, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=150,
            height=34,
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
            text="Guardar",
            width=170,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _carregar_dados(self):
        self._categorias = [
            c
            for c in despesas.listar_categorias()
            if c["nome"] != "Compra de Stock"
        ]
        nomes_cat = [c["nome"] for c in self._categorias] or ["—"]
        self.combo_categoria.configure(values=nomes_cat)

        cat_atual = None
        for c in self._categorias:
            if c["id"] == self.despesa["categoria_id"]:
                cat_atual = c["nome"]
                break
        self.combo_categoria.set(cat_atual or nomes_cat[0])

        self._fornecedores = despesas.listar_fornecedores()
        nomes_forn = ["— Nenhum —"] + [f["nome"] for f in self._fornecedores]
        self.combo_fornecedor.configure(values=nomes_forn)

        forn_atual = "— Nenhum —"
        if self.despesa["fornecedor_id"]:
            for f in self._fornecedores:
                if f["id"] == self.despesa["fornecedor_id"]:
                    forn_atual = f["nome"]
                    break
        self.combo_fornecedor.set(forn_atual)

    def _id_categoria(self):
        nome = self.combo_categoria.get()
        for c in self._categorias:
            if c["nome"] == nome:
                return c["id"]
        return None

    def _id_fornecedor(self):
        nome = self.combo_fornecedor.get()
        if nome == "— Nenhum —":
            return ""
        for f in self._fornecedores:
            if f["nome"] == nome:
                return f["id"]
        return ""

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            descricao = self.campo_descricao.get().strip()
            if not descricao:
                raise ValueError("A descrição é obrigatória.")

            categoria_id = self._id_categoria()
            if categoria_id is None:
                raise ValueError("Escolhe uma categoria.")

            valor = _parse_decimal(self.campo_valor.get(), "Valor")

            data_lancamento = _parse_data(
                self.campo_data_lancamento.get(), "Data de lançamento"
            )
            if data_lancamento is None:
                raise ValueError("A data de lançamento é obrigatória.")

            texto_venc = self.campo_data_vencimento.get().strip()
            if texto_venc:
                data_vencimento = _parse_data(texto_venc, "Data de vencimento")
            else:
                data_vencimento = None
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            despesas.editar_despesa_pendente(
                despesa_id=self.despesa["id"],
                autor=autor,
                valor=valor,
                descricao=descricao,
                categoria_id=categoria_id,
                fornecedor_id=self._id_fornecedor(),
                data_lancamento=data_lancamento,
                data_vencimento=data_vencimento,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Despesa {self.despesa['id']} atualizada."
        )
        self.destroy()
        self.tela_lista._recarregar()


class _DetalheDespesaModal(ctk.CTkToplevel):
    """Modal de leitura de uma despesa paga ou cancelada.

    Aberto pelo botão "Gerir" na Lista Despesas, para despesas que
    já não estão pendentes. Só mostra a ficha — sem ações.
    """

    def __init__(self, tela_lista, despesa):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.despesa = despesa

        largura, altura = 520, 520
        self.title(f"Detalhe — {despesa['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self,
            text=despesa["descricao"] or "(sem descrição)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=460,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=22, pady=(18, 2))

        ctk.CTkLabel(
            self,
            text=(f"{despesa['id']} · estado: {despesa['estado']}"),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(0, 14))

        ficha = ctk.CTkFrame(
            self,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=tema.RAIO_CAMPO,
        )
        ficha.pack(fill="x", padx=22)
        interno = ctk.CTkFrame(ficha, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=12)

        self._linha(interno, "Categoria", self._nome_categoria())
        self._linha(interno, "Fornecedor", self._nome_fornecedor())
        self._linha(
            interno,
            "Valor",
            componentes.formatar_valor(despesa["valor"]),
            forte=True,
        )
        self._linha(
            interno,
            "Lançamento",
            _formatar_data(despesa["data_lancamento"]),
        )
        self._linha(
            interno,
            "Vencimento",
            _formatar_data(despesa["data_vencimento"]),
        )
        self._linha(
            interno,
            "Pagamento",
            _formatar_data(despesa["data_pagamento"]),
        )

        if despesa["estado"] == "cancelada":
            ctk.CTkLabel(
                interno,
                text="",
                font=ctk.CTkFont(size=4),
            ).pack()
            self._linha(
                interno,
                "Motivo",
                despesa["motivo_cancelamento"] or "—",
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=22, pady=(14, 18), side="bottom")

    def _nome_categoria(self):
        c = despesas.procurar_categoria(self.despesa["categoria_id"])
        return c["nome"] if c else "—"

    def _nome_fornecedor(self):
        if not self.despesa["fornecedor_id"]:
            return "—"
        f = despesas.procurar_fornecedor(self.despesa["fornecedor_id"])
        return f["nome"] if f else "—"

    def _linha(self, master, rotulo, valor, forte=False):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", pady=3)

        ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=110,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            linha,
            text=valor,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold" if forte else "normal"),
            anchor="w",
            justify="left",
            wraplength=330,
        ).pack(side="left")


# =====================================================================
# ECRÃ CATEGORIAS
# =====================================================================


class Categorias(ctk.CTkFrame):
    """Ecrã de gestão de categorias de despesa.

    Segue o padrão dos outros ecrãs (botão "+ Nova", busca,
    "Mostrar inativas", tabela, botão "Gerir" por linha). O modal
    Gerir permite Editar, Desativar ou Reativar — a ação
    Desativar/Reativar depende do estado atual.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Categorias").pack(fill="x")

        self._montar_barra()

        self.tabela = componentes.Tabela(
            self,
            colunas=(
                componentes.Coluna("ID", minimo=114, espaco=8),
                componentes.Coluna("NOME", peso=3, minimo=260),
                componentes.Coluna(
                    "ESTADO",
                    peso=1,
                    minimo=110,
                    alinhamento="centro",
                ),
                componentes.Coluna("AÇÕES", minimo=100, alinhamento="centro"),
            ),
            altura_linha=44,
            mensagem_vazia="Ainda não há categorias.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    def _montar_barra(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 8))

        ctk.CTkButton(
            barra,
            text="+ Nova Categoria",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _NovaCategoriaModal(self),
        ).pack(side="left")

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome… (Enter)",
            width=220,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="right")
        self.campo_busca.bind("<Return>", lambda _e: self._recarregar())

        self.mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativas",
            variable=self.mostrar_inativas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

    def _recarregar(self):
        self.tabela.limpar()
        incluir = self.mostrar_inativas.get()
        busca = self.campo_busca.get().strip().lower()

        lista = despesas.listar_categorias(incluir_inativas=incluir)

        if busca:
            lista = [c for c in lista if busca in c["nome"].lower()]

        if not lista:
            self.tabela.mostrar_vazio(
                "Nenhuma categoria encontrada." if busca else None
            )
            return

        for c in lista:
            self._desenhar_categoria(c)

    def _desenhar_categoria(self, c):
        ativa = c["ativo"]
        linha = self.tabela.nova_linha()

        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=c["id"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL
                    if not ativa
                    else tema.AZUL_PRINCIPAL
                ),
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=90,
                anchor="w",
            ),
            esticar="w",
        )

        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=c["nome"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL if not ativa else tema.COR_TEXTO
                ),
                font=ctk.CTkFont(size=13),
                anchor="w",
            ),
        )

        chip_texto = "ativa" if ativa else "inativa"
        chip_fundo = tema.VERDE_LIVRE if ativa else tema.CINZA_INDISPONIVEL
        chip_cor = tema.TEXTO_LIVRE if ativa else tema.TEXTO_INDISPONIVEL

        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=chip_texto,
                text_color=chip_cor,
                fg_color=chip_fundo,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=100,
                height=22,
            ),
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
                command=lambda c=c: _GerirCategoriaModal(self, c),
            )
        )

    def _desativar(self, c):
        if not componentes.confirmar(
            f"Desativar a categoria '{c['nome']}'?\n\n"
            "As despesas antigas continuam a apontar para ela."
        ):
            return

        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.desativar_categoria(c["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Categoria '{c['nome']}' desativada.")
        self._recarregar()

    def _reativar(self, c):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.reativar_categoria(c["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Categoria '{c['nome']}' reativada.")
        self._recarregar()


class _NovaCategoriaModal(ctk.CTkToplevel):
    """Modal simples: só nome."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 400, 280
        self.title("Nova categoria")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Nova categoria",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 14))

        ctk.CTkLabel(
            self,
            text="Nome *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_nome = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: Limpeza, Manutenção, …",
        )
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 6))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=34,
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
            text="Criar",
            width=130,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        nome = self.campo_nome.get().strip()
        try:
            despesas.criar_categoria(nome, autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Categoria '{nome}' criada.")
        self.destroy()
        self.tela_lista._recarregar()


class _GerirCategoriaModal(ctk.CTkToplevel):
    """Popup de ações de uma categoria — Editar + Desativar ou
    Reativar."""

    def __init__(self, tela_lista, categoria):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.categoria = categoria

        ativa = categoria["ativo"]
        altura = 240 if ativa else 200

        largura = 320
        self.title(f"Gerir — {categoria['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=categoria["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=f"{categoria['id']} · " + ("ativa" if ativa else "inativa"),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if ativa:
            self._botao(
                "Editar",
                cor=tema.COR_TEXTO,
                acao=lambda: _EditarCategoriaModal(tela_lista, categoria),
            )
            self._separador()
            self._botao(
                "Desativar",
                cor=tema.TEXTO_ERRO,
                acao=lambda: self._desativar(),
            )
        else:
            self._botao(
                "Reativar",
                cor=tema.TEXTO_LIVRE,
                acao=lambda: self._reativar(),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(10, 16))

    def _separador(self):
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, cor, acao):
        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=cor,
            hover_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)

    def _desativar(self):
        self.tela_lista._desativar(self.categoria)

    def _reativar(self):
        self.tela_lista._reativar(self.categoria)


class _EditarCategoriaModal(ctk.CTkToplevel):
    """Edição do nome de uma categoria existente."""

    def __init__(self, tela_lista, categoria):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.categoria = categoria

        largura, altura = 400, 280
        self.title(f"Editar — {categoria['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {categoria['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 14))

        ctk.CTkLabel(
            self,
            text="Nome *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.insert(0, categoria["nome"])
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 6))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=34,
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
            text="Guardar",
            width=130,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        nome = self.campo_nome.get().strip()
        try:
            despesas.atualizar_categoria(self.categoria["id"], nome, autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Categoria {self.categoria['id']} atualizada."
        )
        self.destroy()
        self.tela_lista._recarregar()


# =====================================================================
# ECRÃ FORNECEDORES
# =====================================================================


class Fornecedores(ctk.CTkFrame):
    """Ecrã de gestão de fornecedores.

    Mesmo padrão do `Categorias`, com uma coluna extra (CONTACTO).
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Fornecedores").pack(fill="x")

        self._montar_barra()

        self.tabela = componentes.Tabela(
            self,
            colunas=(
                componentes.Coluna("ID", minimo=114, espaco=8),
                componentes.Coluna("NOME", peso=3, minimo=220),
                componentes.Coluna("CONTACTO", peso=2, minimo=170),
                componentes.Coluna(
                    "ESTADO",
                    peso=1,
                    minimo=110,
                    alinhamento="centro",
                ),
                componentes.Coluna("AÇÕES", minimo=100, alinhamento="centro"),
            ),
            altura_linha=44,
            mensagem_vazia="Ainda não há fornecedores.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    def _montar_barra(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 8))

        ctk.CTkButton(
            barra,
            text="+ Novo Fornecedor",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _NovoFornecedorModal(self),
        ).pack(side="left")

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome… (Enter)",
            width=220,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="right")
        self.campo_busca.bind("<Return>", lambda _e: self._recarregar())

        self.mostrar_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativos",
            variable=self.mostrar_inativos,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

    def _recarregar(self):
        self.tabela.limpar()
        incluir = self.mostrar_inativos.get()
        busca = self.campo_busca.get().strip().lower()

        lista = despesas.listar_fornecedores(incluir_inativos=incluir)

        if busca:
            lista = [f for f in lista if busca in f["nome"].lower()]

        if not lista:
            self.tabela.mostrar_vazio(
                "Nenhum fornecedor encontrado." if busca else None
            )
            return

        for f in lista:
            self._desenhar_fornecedor(f)

    def _desenhar_fornecedor(self, f):
        ativo = f["ativo"]
        linha = self.tabela.nova_linha()

        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=f["id"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL
                    if not ativo
                    else tema.AZUL_PRINCIPAL
                ),
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=90,
                anchor="w",
            ),
            esticar="w",
        )

        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=f["nome"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL if not ativo else tema.COR_TEXTO
                ),
                font=ctk.CTkFont(size=13),
                anchor="w",
            ),
        )

        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=f["contacto"] or "—",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ),
        )

        chip_texto = "ativo" if ativo else "inativo"
        chip_fundo = tema.VERDE_LIVRE if ativo else tema.CINZA_INDISPONIVEL
        chip_cor = tema.TEXTO_LIVRE if ativo else tema.TEXTO_INDISPONIVEL

        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=chip_texto,
                text_color=chip_cor,
                fg_color=chip_fundo,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=100,
                height=22,
            ),
        )

        acoes = self.tabela.celula_acoes(linha, 4)
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
                command=lambda f=f: _GerirFornecedorModal(self, f),
            )
        )

    def _desativar(self, f):
        if not componentes.confirmar(
            f"Desativar o fornecedor '{f['nome']}'?\n\n"
            "As despesas antigas continuam a apontar para ele."
        ):
            return

        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.desativar_fornecedor(f["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Fornecedor '{f['nome']}' desativado.")
        self._recarregar()

    def _reativar(self, f):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.reativar_fornecedor(f["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Fornecedor '{f['nome']}' reativado.")
        self._recarregar()


class _NovoFornecedorModal(ctk.CTkToplevel):
    """Modal de criação de fornecedor — nome, contacto, nif."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 420, 380
        self.title("Novo fornecedor")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Novo fornecedor",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 14))

        self.campo_nome = self._campo("Nome *")
        self.campo_contacto = self._campo("Contacto")
        self.campo_nif = self._campo("NIF")

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=34,
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
            text="Criar",
            width=130,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _campo(self, rotulo, placeholder=""):
        ctk.CTkLabel(
            self,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(6, 2))
        entrada = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x", padx=24)
        return entrada

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.criar_fornecedor(
                self.campo_nome.get(),
                autor,
                contacto=self.campo_contacto.get(),
                nif=self.campo_nif.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso("Fornecedor criado.")
        self.destroy()
        self.tela_lista._recarregar()


class _GerirFornecedorModal(ctk.CTkToplevel):
    """Popup de ações — Editar + Desativar ou Reativar."""

    def __init__(self, tela_lista, fornecedor):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.fornecedor = fornecedor

        ativo = fornecedor["ativo"]
        altura = 240 if ativo else 200

        largura = 340
        self.title(f"Gerir — {fornecedor['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=fornecedor["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=(
                f"{fornecedor['id']} · " + ("ativo" if ativo else "inativo")
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if ativo:
            self._botao(
                "Editar",
                cor=tema.COR_TEXTO,
                acao=lambda: _EditarFornecedorModal(tela_lista, fornecedor),
            )
            self._separador()
            self._botao(
                "Desativar",
                cor=tema.TEXTO_ERRO,
                acao=lambda: self._desativar(),
            )
        else:
            self._botao(
                "Reativar",
                cor=tema.TEXTO_LIVRE,
                acao=lambda: self._reativar(),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(10, 16))

    def _separador(self):
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, cor, acao):
        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=cor,
            hover_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)

    def _desativar(self):
        self.tela_lista._desativar(self.fornecedor)

    def _reativar(self):
        self.tela_lista._reativar(self.fornecedor)


class _EditarFornecedorModal(ctk.CTkToplevel):
    """Edição dos campos de um fornecedor existente."""

    def __init__(self, tela_lista, fornecedor):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.fornecedor = fornecedor

        largura, altura = 420, 380
        self.title(f"Editar — {fornecedor['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {fornecedor['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 14))

        self.campo_nome = self._campo("Nome *", fornecedor["nome"])
        self.campo_contacto = self._campo("Contacto", fornecedor["contacto"])
        self.campo_nif = self._campo("NIF", fornecedor["nif"])

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=34,
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
            text="Guardar",
            width=130,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _campo(self, rotulo, valor_inicial=""):
        ctk.CTkLabel(
            self,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(6, 2))
        entrada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        entrada.insert(0, valor_inicial)
        entrada.pack(fill="x", padx=24)
        return entrada

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.atualizar_fornecedor(
                self.fornecedor["id"],
                autor,
                nome=self.campo_nome.get(),
                contacto=self.campo_contacto.get(),
                nif=self.campo_nif.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Fornecedor {self.fornecedor['id']} atualizado."
        )
        self.destroy()
        self.tela_lista._recarregar()