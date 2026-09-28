"""Vista do Staff no Dashboard (v1.6.0).

Mockup aprovado a 27/09/2026. Só três blocos, sem valores em euros e
sem seletor de vistas:

1. As minhas limpezas — saídas de hoje e amanhã nas unidades
   atribuídas a este staff, urgentes primeiro.
2. Requisições a confirmar — as dele em estado "enviada", com o
   botão que abre o `_ConfirmarRececaoModal` de sempre; por baixo,
   as pendentes (só informação) e "+ Nova requisição".
3. Stock disponível — saldo de cada produto, do mais crítico para o
   menos, com filtro "Abaixo do mínimo". Só leitura.
"""

import datetime

import painel
import responsaveis
import unidades
from .. import componentes
from .. import sessao
from .. import tema
from . import gui_dash_comum as comum

_FILTRO_TODOS = "Todos"
_FILTRO_ABAIXO = "Abaixo do mínimo"

_LARGURA_ETIQUETA_STOCK = 128


class VistaStaff(comum.VistaBase):
    """Dashboard do Staff."""

    def __init__(self, master, controlador):
        self.filtro_stock = _FILTRO_TODOS
        super().__init__(master, controlador)

    def _construir(self):
        responsavel = sessao.obter_responsavel_ativo()
        self.responsavel_id = responsavel["id"] if responsavel else ""

        # O `_ConfirmarRececaoModal` mostra o nome de quem pediu a
        # partir daqui (é o que a lista de Requisições lhe dá).
        self.nomes_por_id = {
            r["id"]: r["nome"]
            for r in responsaveis.listar(incluir_inativos=True)
        }

        amanha = self.hoje + datetime.timedelta(days=1)
        limpezas = painel.limpezas(
            self.hoje, dias=2, responsavel_id=self.responsavel_id
        )
        self.limpezas_hoje = [x for x in limpezas if x["data"] == self.hoje]
        self.limpezas_amanha = [x for x in limpezas if x["data"] == amanha]
        self.requisicoes = painel.requisicoes_do_staff(self.responsavel_id)
        self.stock = painel.stock_disponivel()

        self._construir_kpis()

        fila = componentes.fila_de_cartoes(self.area, 2)
        fila.pack(fill="x", pady=(0, comum.ESPACO))
        self._construir_limpezas(fila)
        self._construir_requisicoes(fila)

        self._construir_stock()

    # -- números ----------------------------------------------------------

    def _construir_kpis(self):
        fila = componentes.fila_de_cartoes(self.area, 3)
        fila.pack(fill="x", pady=(0, comum.ESPACO))

        n_amanha = len(self.limpezas_amanha)
        componentes.CartaoKpi(
            fila,
            "Limpezas hoje",
            str(len(self.limpezas_hoje)),
            f"+{n_amanha} amanhã" if n_amanha else "nenhuma amanhã",
        ).grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        n_confirmar = len(self.requisicoes["a_confirmar"])
        componentes.CartaoKpi(
            fila,
            "Requisições a confirmar",
            str(n_confirmar),
            "enviadas, falta confirmar a receção",
            cor_valor=tema.TEXTO_AVISO if n_confirmar else None,
        ).grid(row=0, column=1, sticky="nsew", padx=6)

        n_abaixo = sum(1 for linha in self.stock if linha["abaixo"])
        n_total = len(self.stock)
        componentes.CartaoKpi(
            fila,
            "Produtos abaixo do mínimo",
            str(n_abaixo),
            f"de {n_total} "
            f"{comum.plural(n_total, 'produto ativo', 'produtos ativos')}",
            cor_valor=tema.TEXTO_ERRO if n_abaixo else None,
        ).grid(row=0, column=2, sticky="nsew", padx=(6, 0))

    # -- limpezas ---------------------------------------------------------

    def _construir_limpezas(self, fila):
        cartao = componentes.Cartao(
            fila, "As minhas limpezas", "unidades atribuídas a mim"
        )
        cartao.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        corpo = cartao.corpo

        if not unidades.unidades_geridas_por(self.responsavel_id):
            comum.texto_vazio(
                corpo,
                "Ainda não tem unidades atribuídas. Peça a um Admin "
                "para o ligar às unidades que limpa.",
            )
            return

        comum.titulo_secao(corpo, "Hoje", primeira=True)
        if not self.limpezas_hoje:
            comum.texto_vazio(corpo, "Nenhuma limpeza hoje.")
        for linha in self.limpezas_hoje:
            self._linha_limpeza(corpo, linha, hoje=True)

        comum.titulo_secao(corpo, "Amanhã")
        if not self.limpezas_amanha:
            comum.texto_vazio(corpo, "Nenhuma limpeza amanhã.")
        for linha in self.limpezas_amanha:
            self._linha_limpeza(corpo, linha, hoje=False)

    def _linha_limpeza(self, master, linha, hoje):
        regime = "Airbnb" if linha["tipo"] == "airbnb" else "Mensal"
        detalhe = f"{regime} · saída de {linha['cliente']}"

        if linha["proxima_entrada"] is not None:
            detalhe += (
                " · próxima entrada "
                f"{comum.data_curta(linha['proxima_entrada'])}"
            )

        if linha["urgente"]:
            etiqueta, estilo = "urgente", "erro"
        elif hoje:
            etiqueta, estilo = "hoje", "aviso"
        else:
            etiqueta, estilo = "amanhã", "info"

        comum.linha_lista(master, linha["unidade"], detalhe, etiqueta, estilo)

    # -- requisições ------------------------------------------------------

    def _construir_requisicoes(self, fila):
        cartao = componentes.Cartao(
            fila, "Requisições a confirmar", "o stock já foi enviado"
        )
        cartao.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        corpo = cartao.corpo

        a_confirmar = self.requisicoes["a_confirmar"]
        if not a_confirmar:
            comum.texto_vazio(corpo, "Nada para confirmar.")

        for indice, requisicao in enumerate(a_confirmar):
            direita = comum.linha_lista(
                corpo,
                _titulo_requisicao(requisicao),
                "enviada a "
                f"{componentes.formatar_data(requisicao['data_envio'])}",
                separador=indice > 0,
            )
            componentes.Botao(
                direita,
                "Confirmar receção",
                lambda r=requisicao: self._confirmar(r),
                "sucesso",
            ).pack(side="right")

        pendentes = self.requisicoes["pendentes"]
        if pendentes:
            comum.titulo_secao(corpo, "À espera de aprovação (informação)")

        for requisicao in pendentes:
            comum.linha_lista(
                corpo,
                _titulo_requisicao(requisicao),
                "pedida a "
                f"{componentes.formatar_data(requisicao['data_pedido'])}",
                "pendente",
                "info",
            )

        rodape = componentes.Contentor(corpo)
        rodape.pack(fill="x", pady=(12, 0))
        componentes.Botao(
            rodape, "+ Nova requisição", self._nova_requisicao, "primario"
        ).pack(side="left")
        componentes.Botao(
            rodape,
            "Todas as minhas requisições ›",
            lambda: comum.abrir_ecra(self.controlador, "ListaRequisicoes"),
            "discreto",
        ).pack(side="right")

    def _confirmar(self, requisicao):
        from ..estoque.gui_est_requisicoes import _ConfirmarRececaoModal

        _ConfirmarRececaoModal(self, requisicao)

    def _nova_requisicao(self):
        from ..estoque.gui_est_requisicoes import NovaRequisicaoModal

        NovaRequisicaoModal(self)

    # -- stock ------------------------------------------------------------

    def _construir_stock(self):
        cartao = componentes.Cartao(self.area, "Stock disponível")
        cartao.pack(fill="x")

        componentes.SeletorVistas(
            cartao.topo,
            (_FILTRO_TODOS, _FILTRO_ABAIXO),
            self._mudar_filtro,
            inicial=self.filtro_stock,
        ).pack(side="right")

        self.lista_stock = componentes.Contentor(cartao.corpo)
        self.lista_stock.pack(fill="x")
        self._desenhar_stock()

    def _mudar_filtro(self, opcao):
        self.filtro_stock = opcao
        self._desenhar_stock()

    def _desenhar_stock(self):
        """Só a lista do cartão é redesenhada ao trocar o filtro — o
        resto da vista fica como está (os dados já estão em memória)."""
        for filho in self.lista_stock.winfo_children():
            filho.destroy()

        linhas = self.stock
        if self.filtro_stock == _FILTRO_ABAIXO:
            linhas = [linha for linha in linhas if linha["abaixo"]]

        if not linhas:
            comum.texto_vazio(
                self.lista_stock,
                "Nenhum produto abaixo do mínimo."
                if self.stock else "Ainda não há produtos no catálogo.",
            )
            return

        for indice, linha in enumerate(linhas):
            self._linha_stock(linha, separador=indice > 0)

    def _linha_stock(self, linha, separador):
        produto = linha["produto"]
        medida = produto["unidade_medida"]

        if linha["minimo"]:
            detalhe = f"mínimo {linha['minimo']} {medida}"
        else:
            detalhe = "sem mínimo definido"

        direita = comum.linha_lista(
            self.lista_stock, produto["nome"], detalhe, separador=separador
        )

        if linha["abaixo"]:
            etiqueta, estilo = "abaixo do mínimo", "erro"
        elif linha["minimo"]:
            etiqueta, estilo = "ok", "livre"
        else:
            etiqueta, estilo = "sem mínimo", "info"

        componentes.Etiqueta(
            direita, etiqueta, estilo, largura=_LARGURA_ETIQUETA_STOCK
        ).pack(side="right")

        componentes.Rotulo(
            direita, f"{linha['saldo']} {medida}", "forte", anchor="e",
            width=80,
        ).pack(side="right", padx=(0, 12))

        componentes.BarraNivel(
            direita, _nivel(linha), _cor_nivel(linha), largura=120
        ).pack(side="right", padx=(0, 12))


def _titulo_requisicao(requisicao):
    origem = "Rol de lavandaria" if requisicao["origem"] == "rol" else "Staff"
    n = requisicao["n_itens"]

    itens = comum.plural(n, "item", "itens")

    return f"{requisicao['id']} · {origem} · {n} {itens}"


def _nivel(linha):
    """Enchimento da barra: o mínimo fica a meio (saldo = 2x mínimo
    enche a barra). Sem mínimo, a barra fica cheia."""
    if not linha["minimo"]:
        return 1.0

    return linha["saldo"] / (2 * linha["minimo"])


def _cor_nivel(linha):
    if not linha["minimo"]:
        return "livre"

    if linha["saldo"] <= linha["minimo"] / 2:
        return "erro"

    return "aviso" if linha["abaixo"] else "livre"
