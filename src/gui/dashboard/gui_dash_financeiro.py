"""Vista "Financeiro" do Dashboard — só Master e Admin (v1.6.0).

Mockup aprovado a 27/09/2026. Um mês de cada vez, navegável com
◀ ▶ (não deixa ir além do mês atual):

1. Receita, descontos, despesas operacionais e resultado líquido do
   mês — os quatro números do `financeiro.resultado`, com a
   comparação com o mês anterior.
2. Receita vs. despesas dos últimos 6 meses (gráfico) e receita por
   propriedade.
3. Despesas por categoria (mais o consumo de stock em quantidade,
   só informativo) e as rendas mensais a vencer nos próximos 7 dias.

Nenhuma conta nova aqui: tudo vem do `painel` e do `financeiro`.
"""

import datetime

import financeiro
import painel
from .. import componentes
from .. import componentes_graficos
from .. import tema
from . import gui_dash_comum as comum

_ALTURA_GRAFICO = 230
_MESES_NO_GRAFICO = 6
_DIAS_RENDAS = 7


class VistaFinanceiro(comum.VistaBase):
    """Vista financeira de um mês."""

    def __init__(self, master, controlador):
        # O mês mostrado sobrevive ao "↻ Atualizar" — por isso fica
        # definido antes do primeiro `_construir`.
        hoje = datetime.date.today()
        self.ano = hoje.year
        self.mes = hoje.month
        super().__init__(master, controlador)

    # -- navegação ----------------------------------------------------

    def _mudar_mes(self, passo):
        if passo < 0:
            self.ano, self.mes = painel.mes_anterior(self.ano, self.mes)
        else:
            self.ano, self.mes = painel.mes_seguinte(self.ano, self.mes)

        self.atualizar()

    def _e_mes_atual(self):
        return (self.ano, self.mes) >= (self.hoje.year, self.hoje.month)

    # -- construção ---------------------------------------------------

    def _construir(self):
        inicio, fim = painel.periodo_do_mes(self.ano, self.mes)
        ano_ant, mes_ant = painel.mes_anterior(self.ano, self.mes)
        nome_mes = comum.NOMES_MESES_LONGOS[self.mes - 1]
        nome_ant = comum.NOMES_MESES_LONGOS[mes_ant - 1]

        self._construir_navegacao(nome_mes, nome_ant, inicio, fim)

        resumo = painel.resumo_financeiro(self.ano, self.mes)
        self._construir_kpis(resumo, nome_ant)

        fila = componentes.fila_de_cartoes(self.area, 2)
        fila.pack(fill="x", pady=(0, comum.ESPACO))
        self._construir_grafico(fila)
        self._construir_por_propriedade(fila, inicio, fim, nome_mes)

        fila = componentes.fila_de_cartoes(self.area, 2)
        fila.pack(fill="x")
        self._construir_despesas(fila, inicio, fim, nome_mes, resumo)
        self._construir_rendas(fila)

    def _construir_navegacao(self, nome_mes, nome_ant, inicio, fim):
        barra = componentes.Contentor(self.area)
        barra.pack(fill="x", pady=(0, comum.ESPACO))

        componentes.Botao(
            barra, "◀", lambda: self._mudar_mes(-1), "contorno", width=34
        ).pack(side="left")
        componentes.Rotulo(
            barra, f"{nome_mes} {self.ano}", "cartao", anchor="center",
            width=150,
        ).pack(side="left", padx=6)
        seguinte = componentes.Botao(
            barra, "▶", lambda: self._mudar_mes(1), "contorno", width=34
        )
        seguinte.pack(side="left")

        if self._e_mes_atual():
            seguinte.configure(state="disabled")

        ultimo = fim - datetime.timedelta(days=1)
        componentes.Rotulo(
            barra,
            f"período: {inicio.strftime('%d/%m')} – "
            f"{ultimo.strftime('%d/%m')} · "
            f"comparação com {nome_ant}",
            "secundario",
        ).pack(side="right")

    def _construir_kpis(self, resumo, nome_ant):
        atual = resumo["atual"]
        fila = componentes.fila_de_cartoes(self.area, 4)
        fila.pack(fill="x", pady=(0, comum.ESPACO))

        texto, cor = _texto_variacao(
            resumo["variacao_receita"], nome_ant, subir_e_bom=True
        )
        componentes.CartaoKpi(
            fila, "Receita", componentes.formatar_valor(atual["receita"]),
            texto, cor_contexto=cor,
        ).grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        if atual["descontos"] and atual["receita"]:
            percentagem = round(atual["descontos"] / atual["receita"] * 100)
            texto = f"{percentagem}% da receita"
        else:
            texto = "sem descontos"
        componentes.CartaoKpi(
            fila, "Descontos", componentes.formatar_valor(atual["descontos"]),
            texto,
        ).grid(row=0, column=1, sticky="nsew", padx=6)

        texto, cor = _texto_variacao(
            resumo["variacao_despesas"], nome_ant, subir_e_bom=False
        )
        componentes.CartaoKpi(
            fila,
            "Despesas operacionais",
            componentes.formatar_valor(atual["despesas_operacionais"]),
            texto,
            cor_contexto=cor,
        ).grid(row=0, column=2, sticky="nsew", padx=6)

        liquido = atual["resultado_liquido"]
        componentes.CartaoKpi(
            fila,
            "Resultado líquido",
            componentes.formatar_valor(liquido),
            "receita − descontos − despesas",
            cor_valor=tema.TEXTO_LIVRE if liquido >= 0 else tema.TEXTO_ERRO,
        ).grid(row=0, column=3, sticky="nsew", padx=(6, 0))

    def _construir_grafico(self, fila):
        cartao = componentes.Cartao(
            fila, "Receita vs. despesas",
            f"últimos {_MESES_NO_GRAFICO} meses",
        )
        cartao.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        evolucao = painel.evolucao_mensal(
            self.ano, self.mes, _MESES_NO_GRAFICO
        )

        # Tudo a zero: um gráfico vazio com eixos parece avariado.
        # Decisão de apresentação, por isso vive aqui e não no gráfico
        # (mesma escolha do Dashboard antigo com as requisições).
        if not any(
            linha["receita"] or linha["despesas"] for linha in evolucao
        ):
            comum.texto_vazio(
                cartao.corpo,
                f"Sem receita nem despesas nos últimos {_MESES_NO_GRAFICO}"
                " meses.",
            )
            return

        grafico = componentes_graficos.GraficoReceitaDespesas(
            cartao.corpo, altura=_ALTURA_GRAFICO
        )
        grafico.pack(fill="both", expand=True)
        grafico.atualizar(
            rotulos=[linha["rotulo"] for linha in evolucao],
            receita=[linha["receita"] for linha in evolucao],
            despesas=[linha["despesas"] for linha in evolucao],
        )

    def _construir_por_propriedade(self, fila, inicio, fim, nome_mes):
        cartao = componentes.Cartao(fila, "Receita por propriedade", nome_mes)
        cartao.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        linhas = financeiro.receita_por_propriedade(inicio, fim)
        linhas.sort(key=lambda linha: linha["receita"], reverse=True)

        if not linhas:
            comum.texto_vazio(cartao.corpo, "Sem receita neste mês.")
            return

        maximo = max(linha["receita"] for linha in linhas) or 1
        grelha = componentes.Contentor(cartao.corpo)
        grelha.pack(fill="x")
        grelha.grid_columnconfigure(1, weight=1)

        for fila_n, linha in enumerate(linhas):
            componentes.Rotulo(
                grelha, linha["propriedade_nome"], width=110
            ).grid(row=fila_n, column=0, sticky="w", pady=5)
            componentes.BarraNivel(
                grelha, linha["receita"] / maximo, largura=80
            ).grid(row=fila_n, column=1, sticky="ew", padx=8)
            componentes.Rotulo(
                grelha, componentes.formatar_valor(linha["receita"]),
                anchor="e", width=96,
            ).grid(row=fila_n, column=2, sticky="e")

    def _construir_despesas(self, fila, inicio, fim, nome_mes, resumo):
        cartao = componentes.Cartao(fila, "Despesas por categoria", nome_mes)
        cartao.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        linhas = financeiro.despesas_por_categoria(inicio, fim)
        linhas.sort(key=lambda linha: linha["total"], reverse=True)

        if not linhas:
            comum.texto_vazio(cartao.corpo, "Sem despesas pagas neste mês.")

        for indice, linha in enumerate(linhas):
            direita = comum.linha_lista(
                cartao.corpo, linha["categoria_nome"],
                separador=indice > 0,
            )
            componentes.Rotulo(
                direita, componentes.formatar_valor(linha["total"]), "forte"
            ).pack(side="right")

        quantidade = resumo["atual"]["cogs_quantidade"]
        componentes.Rotulo(
            cartao.corpo,
            f"Consumo de stock no mês: {quantidade} "
            f"{comum.plural(quantidade, 'unidade', 'unidades')} "
            "(informativo — não entra no resultado)",
            "secundario",
            wraplength=420,
            justify="left",
        ).pack(fill="x", pady=(10, 0))

    def _construir_rendas(self, fila):
        cartao = componentes.Cartao(
            fila, "Rendas a vencer",
            f"próximos {_DIAS_RENDAS} dias · contratos mensais",
        )
        cartao.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        rendas = painel.rendas_a_vencer(self.hoje, _DIAS_RENDAS)

        if not rendas:
            comum.texto_vazio(
                cartao.corpo, "Nenhuma renda vence nos próximos dias."
            )
            return

        grelha = componentes.Contentor(cartao.corpo)
        grelha.pack(fill="x")
        grelha.grid_columnconfigure(2, weight=1)

        titulos = ("CONTRATO", "INQUILINO", "UNIDADE", "DIA", "VALOR")
        for coluna, titulo in enumerate(titulos):
            componentes.Rotulo(grelha, titulo, "secao").grid(
                row=0, column=coluna, sticky="w", padx=(0, 10), pady=(0, 4)
            )

        for fila_n, renda in enumerate(rendas, start=1):
            valores = (
                renda["ocupacao_id"],
                renda["cliente"],
                renda["unidade"],
                renda["vencimento"].strftime("%d/%m"),
                componentes.formatar_valor(renda["valor"]),
            )
            for coluna, valor in enumerate(valores):
                componentes.Rotulo(grelha, valor).grid(
                    row=fila_n, column=coluna, sticky="w", padx=(0, 10),
                    pady=3,
                )


def _texto_variacao(variacao, nome_ant, subir_e_bom):
    """("▲ 6% vs. agosto", cor) — verde quando a mudança é boa.

    Na receita subir é bom; nas despesas é ao contrário.
    """
    if variacao is None:
        return f"sem valores de {nome_ant}", None

    if variacao == 0:
        return f"igual a {nome_ant}", None

    seta = "▲" if variacao > 0 else "▼"
    boa = (variacao > 0) == subir_e_bom
    cor = tema.TEXTO_LIVRE if boa else tema.TEXTO_ERRO

    return f"{seta} {abs(variacao)}% vs. {nome_ant}", cor
