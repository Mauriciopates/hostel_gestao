"""Vista "Hoje" do Dashboard — Master e Admin (v1.6.0).

Mockup aprovado a 27/09/2026. Responde a "o que tenho de fazer
agora?":

1. Quatro números (ocupação Airbnb, lugares mensais, entradas e
   saídas de hoje).
2. À esquerda, o movimento do dia: entradas, saídas, limpezas (com o
   staff da unidade ou "por atribuir") e os próximos 3 dias.
3. À direita, o que precisa de atenção (alertas clicáveis) e as
   ações rápidas.

Clicar numa entrada ou saída abre a ficha da ocupação
(`componentes.FichaModal`), sem sair do Dashboard.
"""

import painel
from .. import componentes
from .. import sessao
from .. import tema
from . import gui_dash_comum as comum

# Ecrã de destino de cada alerta, pela chave que o `painel` devolve.
_ECRA_DO_ALERTA = {
    "prechecking": "ListaPreCheckins",
    "requisicoes": "ListaAprovacao",
    "stock": "ListaProdutos",
    "documentos": "ListaContratosMensais",
    "clientes": "ListaClientes",
}

_NOMES_REGIME = {"airbnb": "Airbnb", "mensal": "Mensal"}


class VistaHoje(comum.VistaBase):
    """Vista operacional do dia, para Master e Admin."""

    def _construir(self):
        # Uma janela de leitura para o ecrã todo: os contratos, os
        # nomes e a ocupação lêem-se uma vez, não uma por bloco.
        with painel.leitura_em_cache():
            self._construir_conteudo()

    def _construir_conteudo(self):
        self._construir_kpis()

        fila = componentes.Contentor(self.area)
        fila.pack(fill="both", expand=True)
        fila.grid_columnconfigure(0, weight=3, uniform="hoje")
        fila.grid_columnconfigure(1, weight=2, uniform="hoje")

        esquerda = componentes.Contentor(fila)
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        direita = componentes.Contentor(fila)
        direita.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._construir_movimento(esquerda)
        self._construir_alertas(direita)
        self._construir_acoes(direita)

    # -- números ----------------------------------------------------------

    def _construir_kpis(self):
        kpis = painel.kpis_hoje(self.hoje)
        self.limpezas = painel.limpezas(self.hoje)
        por_atribuir = sum(1 for linha in self.limpezas if not linha["staff"])

        fila = componentes.fila_de_cartoes(self.area, 4)
        fila.pack(fill="x", pady=(0, comum.ESPACO))

        ocupadas, total = kpis["airbnb"]
        livres = total - ocupadas
        cartao = componentes.CartaoKpi(
            fila,
            "Airbnb ocupadas hoje",
            f"{ocupadas}/{total}" if total else "—",
            f"{livres} "
            f"{comum.plural(livres, 'unidade livre', 'unidades livres')}"
            if total else "sem unidades Airbnb",
            nivel=ocupadas / total if total else 0,
        )
        cartao.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ocupados, lugares = kpis["mensal"]
        vagos = lugares - ocupados
        cartao = componentes.CartaoKpi(
            fila,
            "Lugares mensais",
            f"{ocupados}/{lugares}" if lugares else "—",
            f"{vagos} "
            f"{comum.plural(vagos, 'lugar livre', 'lugares livres')}"
            if lugares else "sem lugares mensais",
            nivel=ocupados / lugares if lugares else 0,
            cor_nivel="livre",
        )
        cartao.grid(row=0, column=1, sticky="nsew", padx=6)

        entradas = kpis["entradas"]
        cartao = componentes.CartaoKpi(
            fila,
            "Entradas hoje",
            str(entradas["airbnb"] + entradas["mensal"]),
            f"{entradas['airbnb']} Airbnb · {entradas['mensal']} mensal",
        )
        cartao.grid(row=0, column=2, sticky="nsew", padx=6)

        saidas = kpis["saidas"]
        if por_atribuir:
            contexto = (
                f"{por_atribuir} "
                f"{comum.plural(por_atribuir, 'limpeza', 'limpezas')} "
                "por atribuir"
            )
            cor = tema.TEXTO_AVISO
        else:
            n = len(self.limpezas)
            contexto = f"{n} {comum.plural(n, 'limpeza', 'limpezas')}"
            cor = None

        cartao = componentes.CartaoKpi(
            fila,
            "Saídas hoje",
            str(saidas["airbnb"] + saidas["mensal"]),
            contexto,
            cor_contexto=cor,
        )
        cartao.grid(row=0, column=3, sticky="nsew", padx=(6, 0))

    # -- movimento ------------------------------------------------------

    def _construir_movimento(self, master):
        cartao = componentes.Cartao(
            master,
            "Movimento de hoje",
            "clique numa entrada ou saída para ver a ficha",
        )
        cartao.pack(fill="both", expand=True)
        corpo = cartao.corpo

        movimento = painel.movimento_do_dia(self.hoje)

        comum.titulo_secao(corpo, "Entradas", primeira=True)
        if not movimento["entradas"]:
            comum.texto_vazio(corpo, "Sem entradas hoje.")
        for linha in movimento["entradas"]:
            self._linha_ocupacao(corpo, linha, "entra hoje", "azul")

        comum.titulo_secao(corpo, "Saídas")
        if not movimento["saidas"]:
            comum.texto_vazio(corpo, "Sem saídas hoje.")
        for linha in movimento["saidas"]:
            self._linha_ocupacao(corpo, linha, "sai hoje", "info")

        comum.titulo_secao(corpo, "Limpezas")
        if not self.limpezas:
            comum.texto_vazio(corpo, "Nenhuma limpeza para hoje.")
        for linha in self.limpezas:
            self._linha_limpeza(corpo, linha)

        comum.titulo_secao(corpo, "Próximos 3 dias")
        for dia in painel.proximos_dias(self.hoje, dias=3):
            detalhe = (
                f"{dia['entradas']} "
                f"{comum.plural(dia['entradas'], 'entrada', 'entradas')}"
                f" · {dia['saidas']} "
                f"{comum.plural(dia['saidas'], 'saída', 'saídas')}"
            )
            if dia["saidas_mensal"]:
                detalhe += f" ({dia['saidas_mensal']} mensal)"

            comum.linha_lista(corpo, comum.data_curta(dia["data"]), detalhe)

    def _linha_ocupacao(self, master, linha, etiqueta, estilo):
        regime = _NOMES_REGIME.get(linha["tipo"], linha["tipo"])
        partes = [linha["unidade"], regime]

        if linha["noites"] is not None and linha["tipo"] == "airbnb":
            partes.append(
                f"{linha['noites']} "
                f"{comum.plural(linha['noites'], 'noite', 'noites')}"
            )

        comum.linha_lista(
            master,
            linha["cliente"],
            " · ".join(partes),
            etiqueta,
            estilo,
            ao_clicar=lambda: self._abrir_ficha(linha),
        )

    def _linha_limpeza(self, master, linha):
        if linha["staff"]:
            staff = "staff: " + ", ".join(linha["staff"])
        else:
            staff = "staff da unidade: por atribuir"

        detalhe = f"saída de {linha['cliente']} · {staff}"
        if linha["proxima_entrada"] is not None:
            detalhe += (
                " · próxima entrada "
                f"{comum.data_curta(linha['proxima_entrada'])}"
            )

        if linha["urgente"]:
            etiqueta, estilo = "urgente", "erro"
        elif not linha["staff"]:
            etiqueta, estilo = "sem staff", "aviso"
        else:
            etiqueta, estilo = "hoje", "livre"

        comum.linha_lista(master, linha["unidade"], detalhe, etiqueta, estilo)

    def _abrir_ficha(self, linha):
        regime = _NOMES_REGIME.get(linha["tipo"], linha["tipo"])
        pares = [
            ("Cliente", linha["cliente"]),
            ("Unidade", linha["unidade"]),
            ("Regime", regime),
            ("Entrada", componentes.formatar_data(linha["data_inicio"])),
            ("Saída", componentes.formatar_data(linha["data_fim"])),
        ]

        if linha["noites"] is not None:
            pares.append(("Noites", str(linha["noites"])))

        componentes.FichaModal(
            self, linha["ocupacao_id"], f"{regime} · {linha['unidade']}", pares
        )

    # -- alertas e ações ---------------------------------------------

    def _construir_alertas(self, master):
        alertas = painel.alertas(sessao.tipo_utilizador_ativo())

        cartao = componentes.Cartao(
            master, "Precisa de atenção", str(len(alertas)) if alertas else ""
        )
        cartao.pack(fill="x", pady=(0, comum.ESPACO))

        if not alertas:
            componentes.Rotulo(
                cartao.corpo,
                "✓  Tudo em ordem. Sem alertas.",
                cor=tema.TEXTO_LIVRE,
            ).pack(fill="x", pady=4)
            return

        for alerta in alertas:
            destino = _ECRA_DO_ALERTA.get(alerta["chave"])
            comum.caixa_alerta(
                cartao.corpo,
                alerta["titulo"],
                alerta["detalhe"],
                alerta["peso"],
                lambda d=destino: comum.abrir_ecra(self.controlador, d),
            )

    def _construir_acoes(self, master):
        cartao = componentes.Cartao(master, "Ações rápidas")
        cartao.pack(fill="x")

        fila = componentes.fila_de_cartoes(cartao.corpo, 3)
        fila.pack(fill="x")

        acoes = (
            ("+ Reserva", self._nova_reserva),
            ("+ Contrato", self._novo_contrato),
            ("+ Cliente", self._novo_cliente),
        )
        for coluna, (texto, comando) in enumerate(acoes):
            componentes.Botao(fila, texto, comando, "primario").grid(
                row=0, column=coluna, sticky="ew",
                padx=(0 if coluna == 0 else 4, 0 if coluna == 2 else 4),
            )

    # Os modais são importados tarde, pela mesma razão do
    # `comum.abrir_ecra`: no topo criavam um ciclo com o `app.py`.
    # Recebem `self` como "tela_lista" — a vista tem o `controlador`
    # e o `_recarregar` que eles chamam depois de gravar.

    def _nova_reserva(self):
        from ..contratos.gui_cnt_airbnb_nova import NovaReservaAirbnbModal

        NovaReservaAirbnbModal(self)

    def _novo_contrato(self):
        from ..contratos.gui_cnt_mensal_novo import NovoContratoModal

        NovoContratoModal(self)

    def _novo_cliente(self):
        from ..gui_clientes import _SeletorRegimeClienteModal

        _SeletorRegimeClienteModal(self)
