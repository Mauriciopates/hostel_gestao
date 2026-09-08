"""Módulo Stock na interface gráfica.

Três classes, na ordem em que o utilizador as encontra:

1. `EcraStock` — hub do módulo. Faixa de alertas de reposição no
   topo (`estoque.listar_alertas_stock`) e cinco cartões de área.
   Só "Requisições" está implementado; os outros quatro avisam e
   não navegam, para o percurso ser demonstrável sem ecrãs mortos.

2. `ListaRequisicoes` — lista das requisições, filtrável por estado
   e por responsável. Botão "+ Nova requisição" e, nas linhas em
   estado "enviada", "Confirmar receção".

3. `NovaRequisicaoModal` — popup de criação, com linhas de produto
   acrescentáveis e removíveis e o aviso de stock a atualizar-se
   enquanto se escrevem as quantidades.

Decisões desta entrega (08/09/2026, todas aprovadas por mockup
antes de codar):

- O item da barra lateral chama-se "Stock", não "Requisições": com
  o mesmo nome nos dois sítios repetia-se o problema já corrigido
  em 07/09 entre "Contrato Mensal" e "Novo Contrato Mensal".
- Nenhuma cor nova em `tema.py`. As etiquetas de estado
  reaproveitam pares já existentes: pendente AMARELO_AVISO,
  enviada ID_CHIP_FUNDO/AZUL_PRINCIPAL, fechada VERDE_LIVRE,
  rejeitada VERMELHO_ERRO.
- Sem setas Unicode em texto visível ("< Voltar", "X" de remover) —
  o glifo aparecia como quadrado no Windows.
- Numa linha rejeitada mostra-se o motivo em vez dos produtos: é a
  informação que interessa nesse estado, e `rejeitar_requisicao` já
  obriga a que exista.
- "Confirmar receção" só aparece quando o responsável ativo da
  sessão é quem fez o pedido. `confirmar_rececao_requisicao` já
  recusa qualquer outro, mas mostrar um botão que vai sempre
  falhar é pior do que não o mostrar.
- No modal, "Código" e "Produto" são uma coluna só (um
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
        "titulo": "Aprovação",
        "descricao": "Enviar ou rejeitar pedidos pendentes",
        "ecra": None,
    },
    {
        "titulo": "Devoluções",
        "descricao": "Reportar e aceitar sobras de material",
        "ecra": None,
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

# Estado da requisição -> (fundo da etiqueta, cor do texto). Todos
# os pares já existiam em tema.py antes desta entrega.
_CORES_ESTADO = {
    "pendente": (tema.AMARELO_AVISO, tema.TEXTO_AVISO),
    "enviada": (tema.ID_CHIP_FUNDO, tema.AZUL_PRINCIPAL),
    "fechada": (tema.VERDE_LIVRE, tema.TEXTO_LIVRE),
    "rejeitada": (tema.VERMELHO_ERRO, tema.TEXTO_ERRO),
}

_OPCAO_TODOS_ESTADOS = "Todos os estados"
_OPCAO_TODOS_RESPONSAVEIS = "Todos os responsáveis"
_ESTADOS = ("pendente", "enviada", "fechada", "rejeitada")

_LARGURA_REQUISICAO = 150
_LARGURA_ESTADO = 110

# Altura fixa das colunas em frame de cada linha. Sem isto, um
# CTkFrame sem 'height' assume 200px por omissão e `fill="y"`
# nunca o encolhe — cada linha da tabela passava dos 250px de
# altura, com o texto do meio a flutuar longe do ID (mesmo bug
# do espaçador das tabelas de Gestão de Propriedades, 07/09).
_ALTURA_LINHA = 40

# Larguras das colunas do modal de nova requisição.
_LARGURA_PRODUTO = 240
_LARGURA_ARMAZEM = 90
_LARGURA_PEDIDO = 70


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
    """Devolve a etiqueta colorida de um estado de requisição."""
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
        width=_LARGURA_ESTADO,
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

        grelha = ctk.CTkFrame(self, fg_color="transparent")
        grelha.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        grelha.grid_columnconfigure(0, weight=1, uniform="areas")
        grelha.grid_columnconfigure(1, weight=1, uniform="areas")

        for indice, area in enumerate(_AREAS):
            self._desenhar_cartao(grelha, area, indice)

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
            height=110,
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
            text_color=(
                tema.COR_TEXTO if ativo else tema.TEXTO_INDISPONIVEL
            ),
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            cartao,
            text=area["descricao"],
            text_color=(
                tema.COR_TEXTO_SECUNDARIO
                if ativo
                else tema.TEXTO_INDISPONIVEL
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

        componentes.mostrar_erro(
            f"A área \"{area['titulo']}\" ainda não está "
            "implementada nesta versão.",
            titulo="Por implementar",
        )


class ListaRequisicoes(ctk.CTkFrame):
    """Lista das requisições, filtrável por estado e responsável."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Stock · Requisições").pack(
            fill="x"
        )

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
            values=[_OPCAO_TODOS_ESTADOS] + list(_ESTADOS),
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
            values=(
                [_OPCAO_TODOS_RESPONSAVEIS] + sorted(self.id_por_rotulo)
            ),
            width=240,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_responsavel.set(_OPCAO_TODOS_RESPONSAVEIS)
        self.combo_responsavel.pack(side="left", padx=(10, 0))

        cartao_tabela = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao_tabela.pack(fill="both", expand=True, padx=20, pady=(4, 8))

        cabecalho = ctk.CTkFrame(
            cartao_tabela,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=9)

        ctk.CTkLabel(
            interno,
            text="REQUISIÇÃO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=_LARGURA_REQUISICAO,
            anchor="w",
        ).pack(side="left")

        # Alinhado à direita e com o mesmo padx da etiqueta de
        # estado nas linhas, senão o cabeçalho encosta à margem e
        # as etiquetas ficam recuadas 10px em relação a ele.
        ctk.CTkLabel(
            interno,
            text="ESTADO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=_LARGURA_ESTADO,
            anchor="e",
        ).pack(side="right", padx=(10, 0))

        ctk.CTkLabel(
            interno,
            text="RESPONSÁVEL E PRODUTOS",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(cartao_tabela, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x"
        )

        self.area_lista = ctk.CTkScrollableFrame(
            cartao_tabela, fg_color="transparent"
        )
        self.area_lista.pack(fill="both", expand=True)

        rodape = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO, height=48)
        rodape.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkButton(
            rodape,
            text="+ Nova requisição",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=lambda: NovaRequisicaoModal(self),
        ).pack(side="left")

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _estado_filtro(self):
        valor = self.combo_estado.get()

        return None if valor == _OPCAO_TODOS_ESTADOS else valor

    def _responsavel_filtro(self):
        return self.id_por_rotulo.get(self.combo_responsavel.get())

    def _recarregar(self):
        """Limpa e volta a desenhar a lista de requisições."""
        for widget in self.area_lista.winfo_children():
            widget.destroy()

        # Catálogo lido de uma vez: sem isto era um procurar_produto
        # por item, dezenas de consultas para desenhar uma lista.
        produtos = {
            p["id"]: p
            for p in estoque.listar_produtos(incluir_inativos=True)
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

        for indice, requisicao in enumerate(requisicoes):
            self._desenhar_linha(
                requisicao, produtos, indice % 2 == 1
            )

        if not requisicoes:
            ctk.CTkLabel(
                self.area_lista,
                text="Nenhuma requisição com estes filtros.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            ).pack(pady=30)

    def _texto_produtos(self, requisicao, produtos):
        """Segunda linha da célula do meio.

        Numa requisição rejeitada mostra o motivo: é o que interessa
        nesse estado, e os produtos já não vão sair do armazém.
        """
        if requisicao["estado"] == "rejeitada":
            return f"motivo: {requisicao['motivo_rejeicao']}"

        itens = estoque.listar_itens_requisicao(
            requisicao_id=requisicao["id"]
        )

        if not itens:
            return "sem produtos"

        nomes = []

        for item in itens[:3]:
            produto = produtos.get(item["produto_id"])
            nomes.append(
                produto["nome"] if produto else item["produto_id"]
            )

        texto = ", ".join(nomes)

        if len(itens) > 3:
            texto += ", …"

        plural = "produtos" if len(itens) > 1 else "produto"

        return f"{len(itens)} {plural} · {texto}"

    def _desenhar_linha(self, requisicao, produtos, tingida):
        linha = ctk.CTkFrame(
            self.area_lista,
            fg_color=tema.LINHA_ALTERNADA if tingida else "transparent",
            corner_radius=0,
        )
        linha.pack(fill="x")

        interno = ctk.CTkFrame(linha, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        coluna_id = ctk.CTkFrame(
            interno,
            fg_color="transparent",
            width=_LARGURA_REQUISICAO,
            height=_ALTURA_LINHA,
        )
        coluna_id.pack(side="left")
        coluna_id.pack_propagate(False)

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

        _etiqueta_estado(interno, requisicao["estado"]).pack(
            side="right", padx=(10, 0)
        )

        if self._pode_confirmar(requisicao):
            ctk.CTkButton(
                interno,
                text="Confirmar receção",
                width=150,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.AZUL_PRINCIPAL,
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                command=lambda: self._confirmar_rececao(requisicao),
            ).pack(side="right")

        coluna_meio = ctk.CTkFrame(
            interno, fg_color="transparent", height=_ALTURA_LINHA
        )
        coluna_meio.pack(side="left", fill="x", expand=True)
        coluna_meio.pack_propagate(False)

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
            text=self._texto_produtos(requisicao, produtos),
            text_color=(
                tema.TEXTO_ERRO
                if requisicao["estado"] == "rejeitada"
                else tema.COR_TEXTO_SECUNDARIO
            ),
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")

    # -- ações -------------------------------------------------------

    def _pode_confirmar(self, requisicao):
        """Só quem pediu confirma a receção, e só de uma enviada.

        `confirmar_rececao_requisicao` já recusa qualquer outro
        responsável (decisão 9: quem pede é quem sabe se recebeu) —
        isto evita mostrar um botão que ia falhar sempre.
        """
        if requisicao["estado"] != "enviada":
            return False

        ativo = sessao.obter_responsavel_ativo()

        return ativo is not None and ativo["id"] == (
            requisicao["responsavel_id"]
        )

    def _confirmar_rececao(self, requisicao):
        if not componentes.confirmar(
            f"Confirmar que o material da requisição "
            f"{requisicao['id']} foi recebido?",
            titulo="Confirmar receção",
        ):
            return

        ativo = sessao.obter_responsavel_ativo()

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


class _LinhaProduto:
    """Uma linha da tabela de produtos do modal.

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
        return self.modal.id_por_rotulo_produto.get(
            self.combo_produto.get()
        )

    def quantidade(self):
        """Quantidade escrita, ou None se ainda não for um inteiro.

        None não é erro aqui: é o estado normal de um campo vazio ou
        a meio de ser escrito. Quem recusa de vez é
        `estoque.criar_requisicao`, na submissão.
        """
        texto = self.campo_pedido.get().strip()

        if not texto.isdigit():
            return None

        return int(texto)

    def remover(self):
        self.moldura.destroy()
        self.modal.linhas.remove(self)
        self.modal.ao_mudar_linha()


class NovaRequisicaoModal(ctk.CTkToplevel):
    """Popup de criação de uma requisição de material."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.linhas = []

        self.title("Nova Requisição")
        self.geometry("760x640")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        self.produtos_disponiveis = estoque.listar_produtos()
        self.rotulos_produtos = [
            _rotulo_produto(p) for p in self.produtos_disponiveis
        ]
        self.id_por_rotulo_produto = {
            _rotulo_produto(p): p["id"] for p in self.produtos_disponiveis
        }
        self.produtos_por_id = {
            p["id"]: p for p in self.produtos_disponiveis
        }

        ctk.CTkLabel(
            self,
            text="Stock · Nova requisição",
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

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x"
        )

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
                    tema.TEXTO_ERRO
                    if em_falta
                    else tema.COR_TEXTO_SECUNDARIO
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