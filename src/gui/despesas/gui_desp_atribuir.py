"""Atribuir unidade a despesas pagas que ficaram sem unidade (v1.12.0).

Dois modais:

  - `DespesasGeraisModal`: a lista das despesas gerais não atribuídas
    de um período (abre da Rentabilidade), com um seletor por linha e
    um "Aplicar" no fim;
  - `AtribuirUnidadeModal`: atribui UMA despesa (abre do detalhe da
    despesa), com o resultado da unidade antes e depois.

A regra vive em `despesas.atribuir_unidade` e
`despesas.dividir_despesa_sem_unidade`; aqui só se escolhe e se mostra.
"""

from datetime import date
from decimal import Decimal

import customtkinter as ctk

import despesas
import financeiro
import unidades

from .. import componentes
from .. import tema
from . import gui_desp_comum

_formatar_data = gui_desp_comum.formatar_data
_formatar_valor = componentes.formatar_valor

_MANTER_GERAL = "— manter geral —"
_ESCOLHER = "Escolher unidade…"
_VISTAS = ("Uma unidade", "Dividir pelas unidades da propriedade")


# =====================================================================
# AUXILIARES
# =====================================================================


def opcoes_de_destino():
    """Devolve `(unidades_, propriedades)` para os seletores.

    `unidades_` — lista de `(rotulo, unidade_id)` das unidades ativas;
    `propriedades` — lista de `(rotulo, propriedade_id)` das
    propriedades com unidades ativas ("Prédio A (2 unidades)").
    """
    lista = unidades.listar_com_propriedade()

    por_unidade = [
        (f"{u['propriedade_nome']} · {u['nome']} ({u['id']})", u["id"])
        for u in lista
    ]

    contagem = {}
    nomes = {}
    for u in lista:
        contagem[u["propriedade_id"]] = (
            contagem.get(u["propriedade_id"], 0) + 1
        )
        nomes[u["propriedade_id"]] = u["propriedade_nome"]

    por_propriedade = [
        (
            f"Dividir por {nomes[pid]} ({quantas} "
            f"{'unidade' if quantas == 1 else 'unidades'})",
            pid,
        )
        for pid, quantas in contagem.items()
    ]
    return por_unidade, por_propriedade


def periodo_do_mes(dia):
    """`[primeiro dia do mês, primeiro dia do mês seguinte)` de `dia`."""
    inicio = dia.replace(day=1)
    if dia.month == 12:
        return inicio, date(dia.year + 1, 1, 1)
    return inicio, date(dia.year, dia.month + 1, 1)


def _nome_categoria(despesa):
    categoria = despesas.procurar_categoria(despesa["categoria_id"])
    return categoria["nome"] if categoria else "—"


def _ajustar(janela, pai, largura):
    """Mede o conteúdo e centra sobre a janela que abriu."""
    janela.update_idletasks()
    fator = componentes.escala(janela)
    altura = int(janela.corpo.winfo_reqheight() / fator) + 40
    componentes.centrar_sobre(
        janela, pai.winfo_toplevel(), largura, altura
    )


# =====================================================================
# MODAL 1 — DESPESAS GERAIS NÃO ATRIBUÍDAS
# =====================================================================

_LARGURA_GERAIS = 760


class DespesasGeraisModal(ctk.CTkToplevel):
    """Lista as despesas pagas sem unidade de `[data_inicio, data_fim)`
    e deixa atribuir cada uma. Nada muda até clicar em "Aplicar".

    `ao_mudar` é chamado (sem argumentos) depois de aplicar, para o
    relatório se recarregar.
    """

    def __init__(self, pai, data_inicio, data_fim, ao_mudar):
        super().__init__(pai)
        self.pai = pai
        self.ao_mudar = ao_mudar
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self._linhas = []

        self.title("Despesas gerais não atribuídas")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(pai)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.lista = financeiro.despesas_gerais(data_inicio, data_fim)
        self.por_unidade, self.por_propriedade = opcoes_de_destino()
        self.rotulos = (
            [_MANTER_GERAL]
            + [r for r, _ in self.por_unidade]
            + [r for r, _ in self.por_propriedade]
        )

        self.corpo = componentes.Contentor(self)
        self.corpo.pack(fill="both", expand=True, padx=22, pady=(18, 16))

        total = sum((d["valor"] for d in self.lista), Decimal("0.00"))
        componentes.Rotulo(
            self.corpo, "Despesas gerais não atribuídas", "cartao"
        ).pack(fill="x")
        componentes.Rotulo(
            self.corpo,
            f"Período {_formatar_data(data_inicio)} a "
            f"{_formatar_data(date.fromordinal(data_fim.toordinal() - 1))}"
            f" · {len(self.lista)} despesa(s), "
            f"{_formatar_valor(total)} fora de qualquer unidade",
            "secundario",
        ).pack(fill="x", pady=(2, 8))

        aviso = componentes.Contentor(
            self.corpo,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.AMARELO_AVISO,
        )
        aviso.pack(fill="x", pady=(0, 10))
        componentes.Rotulo(
            aviso,
            "Estas despesas pagas não têm unidade, por isso não entram "
            "no resultado de nenhuma propriedade. Escolha a unidade de "
            "cada uma (ou divida pela propriedade) e clique em Aplicar. "
            "As que ficarem sem escolha continuam gerais — pode ser o "
            "certo (renda do prédio, internet…).",
            "secundario",
            cor=tema.TEXTO_AVISO,
            wraplength=_LARGURA_GERAIS - 70,
            justify="left",
            height=0,
        ).pack(fill="x", padx=12, pady=8)

        area = componentes.AreaRolavel(
            self.corpo, height=min(max(len(self.lista), 1), 5) * 62 + 8
        )
        area.pack(fill="x")
        for despesa in self.lista:
            self._desenhar_linha(area, despesa)

        self.rotulo_erro = componentes.Rotulo(
            self.corpo, "", "secundario", cor=tema.TEXTO_ERRO,
            wraplength=_LARGURA_GERAIS - 50, justify="left", height=0,
        )
        self.rotulo_erro.pack(fill="x", pady=(8, 0))

        rodape = componentes.Contentor(self.corpo)
        rodape.pack(fill="x", pady=(10, 0))
        self.botao_aplicar = componentes.Botao(
            rodape, "Aplicar", self._aplicar, "primario",
            width=190, height=34, state="disabled",
        )
        self.botao_aplicar.pack(side="right")
        componentes.Botao(
            rodape, "Cancelar", self.destroy, width=110, height=34
        ).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _e: self.destroy(), add="+")

        _ajustar(self, pai, _LARGURA_GERAIS)
        componentes.colocar_no_topo(self)

    def _desenhar_linha(self, area, despesa):
        moldura = componentes.Contentor(
            area, corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.LINHA_ALTERNADA,
        )
        moldura.pack(fill="x", pady=3)
        moldura.grid_columnconfigure(1, weight=1)

        componentes.Rotulo(moldura, despesa["id"], "forte").grid(
            row=0, column=0, padx=(12, 10), pady=(8, 0), sticky="w"
        )
        componentes.Rotulo(
            moldura,
            despesa["descricao"] or "(sem descrição)",
            "texto",
            wraplength=300,
            justify="left",
        ).grid(row=0, column=1, pady=(8, 0), sticky="w")
        componentes.Rotulo(
            moldura,
            f"{_nome_categoria(despesa)} · pago a "
            f"{_formatar_data(despesa['data_pagamento'])}",
            "secundario",
        ).grid(row=1, column=1, pady=(0, 8), sticky="w")
        componentes.Rotulo(
            moldura, _formatar_valor(despesa["valor"]), "forte"
        ).grid(row=0, column=2, rowspan=2, padx=10)

        seletor = componentes.Seletor(
            moldura,
            values=self.rotulos,
            width=250,
            command=lambda _v: self._ao_escolher(),
        )
        seletor.set(_MANTER_GERAL)
        seletor.grid(row=0, column=3, rowspan=2, padx=(0, 12), pady=8)

        self._linhas.append((despesa, seletor))

    def _escolhas(self):
        """Linhas onde se escolheu algo: `[(despesa, destino)]`, com
        `destino = ("unidade"|"propriedade", id)`."""
        unidades_ = dict(self.por_unidade)
        propriedades = dict(self.por_propriedade)
        escolhas = []
        for despesa, seletor in self._linhas:
            rotulo = seletor.get()
            if rotulo in unidades_:
                escolhas.append((despesa, ("unidade", unidades_[rotulo])))
            elif rotulo in propriedades:
                escolhas.append(
                    (despesa, ("propriedade", propriedades[rotulo]))
                )
        return escolhas

    def _ao_escolher(self):
        quantas = len(self._escolhas())
        if quantas:
            self.botao_aplicar.configure(
                text=f"Aplicar {quantas} "
                f"{'atribuição' if quantas == 1 else 'atribuições'}",
                state="normal",
            )
        else:
            self.botao_aplicar.configure(text="Aplicar", state="disabled")

    def _aplicar(self):
        autor = gui_desp_comum.autor_atual()
        feitas = 0
        erros = []

        for despesa, (tipo, alvo) in self._escolhas():
            try:
                if tipo == "unidade":
                    despesas.atribuir_unidade(despesa["id"], alvo, autor)
                else:
                    despesas.dividir_despesa_sem_unidade(
                        despesa["id"], alvo, autor
                    )
                feitas += 1
            except ValueError as erro:
                erros.append(f"{despesa['id']}: {erro}")

        if feitas:
            self.ao_mudar()

        if erros:
            componentes.mostrar_erro(
                "Algumas atribuições não foram feitas:\n\n"
                + "\n".join(erros),
                "Atribuir unidade",
            )

        self.destroy()


# =====================================================================
# MODAL 2 — ATRIBUIR UMA DESPESA A UMA UNIDADE
# =====================================================================

_LARGURA_ATRIBUIR = 560


class AtribuirUnidadeModal(ctk.CTkToplevel):
    """Atribui uma despesa sem unidade a UMA unidade ou divide-a pelas
    unidades de uma propriedade, mostrando o resultado da unidade antes
    e depois. O botão só fica ativo com uma escolha feita.

    `ao_atribuir` é chamado (sem argumentos) depois de gravar.
    """

    def __init__(self, pai, despesa, ao_atribuir):
        super().__init__(pai)
        self.pai = pai
        self.despesa = despesa
        self.ao_atribuir = ao_atribuir
        self._cache = {}

        dia = despesa["data_pagamento"] or despesa["data_lancamento"]
        self.periodo = periodo_do_mes(dia)

        self.title("Atribuir despesa a uma unidade")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(pai)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.por_unidade, self.por_propriedade = opcoes_de_destino()
        self.e_stock = bool(despesas.listar_itens_despesa(despesa["id"]))

        self.corpo = componentes.Contentor(self)
        self.corpo.pack(fill="both", expand=True, padx=22, pady=(18, 16))

        componentes.Rotulo(
            self.corpo, "Atribuir despesa a uma unidade", "cartao"
        ).pack(fill="x")
        componentes.Rotulo(
            self.corpo,
            f"{despesa['id']}, {despesa['descricao'] or '(sem descrição)'}"
            f", {_formatar_valor(despesa['valor'])}, "
            f"{despesa['estado']} a {_formatar_data(dia)}",
            "secundario",
            wraplength=_LARGURA_ATRIBUIR - 50,
            justify="left",
            height=0,
        ).pack(fill="x", pady=(2, 10))

        self.vista = _VISTAS[0]
        if not self.e_stock and self.por_propriedade:
            componentes.SeletorVistas(
                self.corpo, _VISTAS, self._mudar_vista, inicial=_VISTAS[0]
            ).pack(anchor="w", pady=(0, 10))

        self.zona = componentes.Contentor(self.corpo)
        self.zona.pack(fill="x")

        self.rotulo_erro = componentes.Rotulo(
            self.corpo, "", "secundario", cor=tema.TEXTO_ERRO,
            wraplength=_LARGURA_ATRIBUIR - 50, justify="left", height=0,
        )
        self.rotulo_erro.pack(fill="x", pady=(4, 0))

        self.caixa_resumo = componentes.Contentor(
            self.corpo, corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.LINHA_ALTERNADA,
        )
        self.caixa_resumo.pack(fill="x", pady=(8, 0))
        self.rotulo_resumo = componentes.Rotulo(
            self.caixa_resumo, "", "texto",
            wraplength=_LARGURA_ATRIBUIR - 80, justify="left", height=0,
        )
        self.rotulo_resumo.pack(fill="x", padx=12, pady=(10, 2))
        self.rotulo_nota = componentes.Rotulo(
            self.caixa_resumo,
            "A despesa já está paga e os dados dela continuam "
            "bloqueados. Só a imputação muda, e fica registado quem a "
            "atribuiu e quando. Só se pode fazer uma vez; para mudar "
            "de novo, cancele e lance outra.",
            "secundario",
            wraplength=_LARGURA_ATRIBUIR - 80, justify="left", height=0,
        )
        self.rotulo_nota.pack(fill="x", padx=12, pady=(0, 10))

        rodape = componentes.Contentor(self.corpo)
        rodape.pack(fill="x", pady=(14, 0))
        self.botao_confirmar = componentes.Botao(
            rodape, "Confirmar atribuição", self._confirmar, "primario",
            width=180, height=34, state="disabled",
        )
        self.botao_confirmar.pack(side="right")
        componentes.Botao(
            rodape, "Cancelar", self.destroy, width=110, height=34
        ).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _e: self.destroy(), add="+")

        self._montar_zona()
        self._atualizar()
        _ajustar(self, pai, _LARGURA_ATRIBUIR)
        componentes.colocar_no_topo(self)

    # -- zona do seletor, conforme a vista ----------------------------

    def _mudar_vista(self, vista):
        self.vista = vista
        self._montar_zona()
        self._atualizar()
        _ajustar(self, self.pai, _LARGURA_ATRIBUIR)

    def _montar_zona(self):
        for filho in self.zona.winfo_children():
            filho.destroy()

        if self.vista == _VISTAS[0]:
            componentes.Rotulo(self.zona, "Unidade", "secundario").pack(
                fill="x", pady=(0, 4)
            )
            self.seletor = componentes.Seletor(
                self.zona,
                values=[_ESCOLHER] + [r for r, _ in self.por_unidade],
                width=_LARGURA_ATRIBUIR - 50,
                command=lambda _v: self._atualizar(),
            )
        else:
            componentes.Rotulo(self.zona, "Propriedade", "secundario").pack(
                fill="x", pady=(0, 4)
            )
            self.seletor = componentes.Seletor(
                self.zona,
                values=[_ESCOLHER] + [r for r, _ in self.por_propriedade],
                width=_LARGURA_ATRIBUIR - 50,
                command=lambda _v: self._atualizar(),
            )
        self.seletor.set(_ESCOLHER)
        self.seletor.pack(anchor="w")

    def _destino(self):
        """`("unidade"|"propriedade", id)` ou None se nada escolhido."""
        rotulo = self.seletor.get()
        tabela = (
            self.por_unidade
            if self.vista == _VISTAS[0]
            else self.por_propriedade
        )
        for texto, identificador in tabela:
            if texto == rotulo:
                tipo = "unidade" if self.vista == _VISTAS[0] else (
                    "propriedade"
                )
                return tipo, identificador
        return None

    def _resultado(self, unidade_id):
        if unidade_id not in self._cache:
            self._cache[unidade_id] = financeiro.resultado_da_unidade(
                unidade_id, *self.periodo
            )
        return self._cache[unidade_id]

    def _atualizar(self):
        destino = self._destino()
        mes = f"{self.periodo[0]:%m/%Y}"

        if destino is None:
            self.caixa_resumo.configure(fg_color=tema.LINHA_ALTERNADA)
            self.rotulo_resumo.configure(
                text="Escolha para ver o efeito no resultado.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            )
            self.botao_confirmar.configure(state="disabled")
            return

        valor = self.despesa["valor"]
        tipo, identificador = destino

        if tipo == "unidade":
            antes = self._resultado(identificador)
            texto = (
                f"Resultado da unidade em {mes}:  "
                f"{_formatar_valor(antes)}  →  "
                f"{_formatar_valor(antes - valor)}"
            )
        else:
            quantas = len(
                [
                    u
                    for u in unidades.listar_com_propriedade()
                    if u["propriedade_id"] == identificador
                ]
            )
            texto = (
                f"Cada uma das {quantas} unidades recebe cerca de "
                f"{_formatar_valor(valor / quantas)}. A despesa original "
                f"é cancelada e substituída por {quantas} partes."
            )

        self.caixa_resumo.configure(fg_color=tema.AMARELO_AVISO)
        self.rotulo_resumo.configure(
            text=texto,
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.botao_confirmar.configure(state="normal")

    def _confirmar(self):
        destino = self._destino()
        if destino is None:
            return

        autor = gui_desp_comum.autor_atual()
        tipo, identificador = destino

        try:
            if tipo == "unidade":
                despesas.atribuir_unidade(
                    self.despesa["id"], identificador, autor
                )
            else:
                despesas.dividir_despesa_sem_unidade(
                    self.despesa["id"], identificador, autor
                )
        except ValueError as erro:
            self.rotulo_erro.configure(text=str(erro))
            return

        self.destroy()
        self.ao_atribuir()
