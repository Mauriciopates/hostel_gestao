import collections
import datetime
from tkinter import messagebox

import customtkinter as ctk

import config
from . import tema
from . import sessao


def mostrar_erro(mensagem, titulo="Erro"):
    """Mostra um erro num popup nativo (triângulo de aviso, mensagem,
    botão OK) — convenção única de toda a interface gráfica para
    avisos de erro (decisão do aluno, 06/09/2026, ao testar o ecrã
    de Novo Contrato Mensal): substitui a legenda vermelha que cada
    ecrã desenhava por si, por um popup do próprio sistema
    operativo. É bloqueante (o resto do ecrã só volta a responder
    depois de clicar OK), mas não fecha nem limpa nada à volta —
    o formulário fica exatamente como estava, pronto a continuar a
    editar.
    """
    messagebox.showwarning(titulo, mensagem)


def mostrar_sucesso(mensagem, titulo="Sucesso"):
    """Mostra uma confirmação de sucesso num popup nativo (ícone de
    informação, mensagem, botão OK) — mesma convenção de
    mostrar_erro, agora para o caso contrário (decisão do aluno,
    06/09/2026, logo a seguir a pedir o popup de erro): "após criado,
    apareça um pop up, contrato criado com sucesso: CNT-XXX".
    """
    messagebox.showinfo(titulo, mensagem)


def confirmar(mensagem, titulo="Confirmar"):
    """Pergunta sim/não num popup nativo antes de uma ação
    destrutiva ou irreversível (ex.: desativar uma propriedade ou
    unidade) — terceira convenção de popup da GUI, ao lado de
    mostrar_erro/mostrar_sucesso (decisão do aluno, 06/09/2026, ao
    acrescentar desativar/reativar ao ecrã de Propriedades e
    Unidades: a GUI nunca força uma desativação com dependências
    ativas — só confirma a intenção antes de tentar, o próprio
    `propriedades.desativar`/`unidades.desativar` continua a
    recusar sozinho quando há dependências, e esse erro aparece
    depois em mostrar_erro).

    Devolve True só se o utilizador confirmar ("Sim").
    """
    return messagebox.askyesno(titulo, mensagem)


class BarraLateral(ctk.CTkFrame):
    """Barra lateral de navegação. Recebe uma lista de itens — cada
    um ou uma secção (rótulo não clicável, ex. "MENSAL") ou um item
    de navegação (rótulo + ecrã de destino) — e monta os widgets
    correspondentes. Não sabe nada sobre os ecrãs reais: quem decide
    o que lá vai é quem a instancia (app.py), por isso dá para testar
    com ecrãs falsos sem Unidades/Clientes/etc. já existirem. Mostra
    sempre a versão do sistema (config.VERSAO) no rodapé (decisão 21).

    Cabeçalho de marca "HOSTEL CLEAN" no topo (07/09/2026, aprovado
    por mockup antes de codar, junto com os itens 2/3/5 do checklist
    de wireframes) — só decorativo, sem lógica nenhuma, por isso fica
    fixo aqui em vez de vir na lista `itens`.

    Botão "Trocar utilizador" no rodapé, acima da versão (09/09/2026
    — pedido explícito do aluno, "botão cinza"). Mesma ideia de
    `mostrar_frame`: `controlador` tem de ter também um método
    `trocar_utilizador()` — quem o chama é só este botão, por isso é
    o único sítio que precisa dessa segunda parte do "contrato" com
    o controlador (`Aplicacao.trocar_utilizador`, em app.py, reabre
    `SelecionarUtilizadorModal`).
    """

    def __init__(self, master, controlador, itens):
        super().__init__(master, corner_radius=0, fg_color=tema.NAVY_ESCURO)

        marca = ctk.CTkFrame(self, fg_color="transparent")
        marca.pack(fill="x", padx=16, pady=(20, 14))
        ctk.CTkLabel(
            marca,
            text="●",
            text_color=tema.AZUL_CLARO,
            font=ctk.CTkFont(size=14),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            marca,
            text="HOSTEL CLEAN",
            text_color=tema.COR_TEXTO_SIDEBAR,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        ctk.CTkFrame(
            self,
            height=1,
            fg_color=tema.COR_TEXTO_SIDEBAR_SECAO,
        ).pack(fill="x", padx=16, pady=(0, 10))

        for item in itens:
            if item["tipo"] == "secao":
                ctk.CTkLabel(
                    self,
                    text=item["texto"],
                    text_color=tema.COR_TEXTO_SIDEBAR_SECAO,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ).pack(fill="x", padx=16, pady=(16, 4))
            else:
                ctk.CTkButton(
                    self,
                    text=item["texto"],
                    fg_color="transparent",
                    text_color=tema.COR_TEXTO_SIDEBAR,
                    hover_color=tema.AZUL_PRINCIPAL,
                    corner_radius=tema.RAIO_BOTAO,
                    anchor="w",
                    command=lambda ecra=item["ecra"]: (
                        controlador.mostrar_frame(ecra)
                    ),
                ).pack(fill="x", padx=8, pady=2)

        ctk.CTkLabel(
            self,
            text=f"v{config.VERSAO}",
            text_color=tema.COR_TEXTO_SIDEBAR_SECAO,
            font=ctk.CTkFont(size=9),
        ).pack(side="bottom", pady=10)

        # Botão cinza, colado acima da versão (empacotado DEPOIS
        # dela — em pack(side="bottom") cada widget novo fica por
        # cima do anterior, não por baixo). Cinzento reaproveita
        # COR_TEXTO_SIDEBAR_SECAO, já usado nesta mesma barra (versão
        # e rótulos de secção) — sem cor nova em tema.py.
        ctk.CTkButton(
            self,
            text="Trocar utilizador",
            fg_color=tema.COR_TEXTO_SIDEBAR_SECAO,
            text_color=tema.COR_TEXTO_SIDEBAR,
            hover_color=tema.AZUL_CLARO,
            corner_radius=tema.RAIO_BOTAO,
            height=30,
            command=controlador.trocar_utilizador,
        ).pack(side="bottom", fill="x", padx=12, pady=(4, 0))


class Cabecalho(ctk.CTkFrame):
    """Cabeçalho comum a todos os ecrãs: título à esquerda, data e
    responsável ativo à direita. O título é o único parâmetro — data
    e responsável vêm sempre de sessao.obter_responsavel_ativo().
    """

    def __init__(self, master, titulo):
        super().__init__(master, corner_radius=0, fg_color=tema.COR_FUNDO)

        ctk.CTkLabel(
            self,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left", padx=20, pady=15)

        responsavel = sessao.obter_responsavel_ativo()
        nome = responsavel["nome"] if responsavel else "sem responsável"
        hoje = datetime.date.today().strftime("%d/%m/%Y")

        ctk.CTkLabel(
            self,
            text=f"{hoje} · {nome}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=20)


Coluna = collections.namedtuple(
    "Coluna",
    ("titulo", "peso", "minimo", "alinhamento", "espaco"),
    defaults=("", 0, 0, "w", 0),
)
Coluna.__doc__ = """Definição de uma coluna de `Tabela`.

- titulo: texto do cabeçalho, já em maiúsculas.
- peso: quanto esta coluna cresce quando sobra espaço. 0 = largura
  fixa. Uma coluna de peso 3 cresce o triplo de uma de peso 1.
- minimo: largura mínima em pixéis, abaixo da qual não encolhe.
- alinhamento: "w" (esquerda), "centro" ou "e" (direita). Vale para
  o título E para a célula: é daqui que sai o anchor do cabeçalho e
  o sticky do conteúdo, para os dois não poderem discordar.
- espaco: folga em pixéis à direita da célula.
"""

# Alinhamento da coluna -> (anchor do título, sticky da célula).
#
# Nenhum sticky tem "n" nem "s", de propósito: em Tk, "ns" ESTICA o
# widget do topo ao fundo da linha, não o centra. Numa etiqueta de
# texto não se notaria, mas num crachá com fundo colorido a pílula
# deixaria de ser pílula e passaria a uma barra da altura toda. O
# que centra na vertical é o contrário — sticky sem n/s, mais um
# `grid_rowconfigure` com peso na linha.
#
# "centro" também não leva "ew": esticar horizontalmente faria a
# célula ocupar a largura toda e o conteúdo alinhar-se pelo seu
# próprio anchor, não pelo centro da coluna.
_ALINHAMENTOS = {
    "w": ("w", "ew"),
    "e": ("e", "ew"),
    "centro": ("center", ""),
}

# Margem lateral: distância da primeira e da última coluna às bordas
# do cartão.
_MARGEM_TABELA = 16

_PADY_CABECALHO = 9

# Folga entre botões dentro de uma célula de ações.
_ESPACO_BOTOES = 6


class _CelulaAcoes(ctk.CTkFrame):
    """Célula que agrupa os botões de ação de uma linha.

    Existe para os botões terem sempre a mesma folga entre si e para
    a célula ter largura fixa. O `width` com `pack_propagate(False)`
    é obrigatório: um CTkFrame sem largura fica nos 200px por
    omissão, e um botão que não coubesse nesses 200px era desenhado
    espremido a poucos pixéis em vez de ficar de fora de forma
    visível (08/09/2026).
    """

    def __init__(self, master, largura, altura, espaco=_ESPACO_BOTOES):
        # A altura é tão obrigatória como a largura, e por baixo é o
        # mesmo problema: com `pack_propagate(False)` o frame fica
        # com os 200px de altura por omissão do CTkFrame e obriga a
        # fila inteira da grelha a esticar até lá (08/09/2026,
        # apanhado a medir a tabela num ecrã virtual).
        super().__init__(
            master, fg_color="transparent", width=largura, height=altura
        )
        self.pack_propagate(False)
        self._espaco = espaco
        self._primeiro = True

    def adicionar(self, widget):
        """Junta um botão à direita dos que já lá estão."""
        widget.pack(
            side="left", padx=(0 if self._primeiro else self._espaco, 0)
        )
        self._primeiro = False

        return widget


class Tabela(ctk.CTkFrame):
    """Tabela com cabeçalho e corpo na MESMA grelha.

    Porque é que isto é uma grelha só, e não um cabeçalho mais uma
    lista de linhas: o Tk não decide a largura de uma coluna só a
    partir do peso e do mínimo que lhe damos — parte do que os
    próprios filhos pedem e só depois reparte o que sobra. Duas
    grelhas com configuração idêntica dão colunas diferentes se os
    conteúdos forem diferentes, e são sempre: no cabeçalho estão
    títulos curtos, nas linhas estão crachás de 90px e botões de
    100px. Foi essa a causa do desalinhamento que se arrastou por
    várias tentativas em 08/09/2026, e nenhum acerto de `padx` ou de
    peso o resolvia.

    Com uma grelha única não há duas colunas para fazer coincidir:
    há uma. O cabeçalho é a linha 0, cada registo é uma linha a
    seguir, e o alinhamento deixa de ser uma propriedade que se
    ajusta para passar a ser uma que não pode falhar.

    Como o fundo de cada linha (tom alternado e faixa do cabeçalho)
    já não pode ser um frame que contém as células, é um frame
    colocado na mesma célula da grelha com `columnspan`, criado
    ANTES delas — no Tk, widgets criados depois ficam por cima.

    Uso típico:

        self.tabela = componentes.Tabela(
            self,
            colunas=(
                componentes.Coluna("ID", minimo=94, espaco=8),
                componentes.Coluna("NOME", peso=3, minimo=190),
                componentes.Coluna(
                    "ESTADO", peso=1, minimo=90, alinhamento="centro"
                ),
                componentes.Coluna(
                    "PREÇO", peso=1, minimo=80, alinhamento="e", espaco=8
                ),
                componentes.Coluna(
                    "AÇÕES", minimo=100, alinhamento="e"
                ),
            ),
            altura_linha=52,
        )
        self.tabela.pack(fill="both", expand=True, padx=16, pady=10)

        ...

        self.tabela.limpar()

        for registo in registos:
            linha = self.tabela.nova_linha()

            self.tabela.colocar(
                linha, 0, ctk.CTkLabel(linha, text=registo["id"])
            )

            acoes = self.tabela.celula_acoes(linha, 4)
            acoes.adicionar(ctk.CTkButton(acoes, text="Ações"))

        if self.tabela.vazia:
            self.tabela.mostrar_vazio()

    `nova_linha` devolve a própria grelha, para os widgets serem
    criados com o master certo; qual é a linha em que ficam é a
    tabela que sabe.
    """

    def __init__(
        self,
        master,
        colunas,
        altura_linha=44,
        mensagem_vazia="Sem registos.",
        divisorias=True,
        linhas_verticais=True,
        tom_alternado=False,
    ):
        # Nota sobre `tom_alternado`: se algum dia for ligado, as
        # células das linhas tingidas precisam de receber o
        # fg_color da linha, pela mesma razão dos títulos abaixo —
        # transparente herda o branco da grelha, não o tom do fundo
        # que está por trás.
        super().__init__(
            master,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )

        self._colunas = tuple(colunas)
        self._altura_linha = altura_linha
        self._mensagem_vazia = mensagem_vazia
        self._divisorias = divisorias
        self._linhas_verticais = linhas_verticais
        self._tom_alternado = tom_alternado
        self._desenhadas = 0

        self.corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.corpo.pack(fill="both", expand=True)

        self.grelha = ctk.CTkFrame(self.corpo, fg_color="transparent")
        # fill="x" e não "both": as linhas empilham-se a partir
        # do topo, e a mensagem de "sem registos" cabe por baixo.
        self.grelha.pack(fill="x")

        # Colunas de conteúdo em índices pares; entre elas, colunas
        # de 1px para as divisórias verticais. É o que faz a tabela
        # ler-se como tabela e o que torna impossível esconder um
        # desalinhamento: a linha vertical passa exatamente na
        # fronteira de que estamos a falar.
        for indice, coluna in enumerate(self._colunas):
            self.grelha.grid_columnconfigure(
                indice * 2, weight=coluna.peso, minsize=coluna.minimo
            )

            if indice < len(self._colunas) - 1:
                self.grelha.grid_columnconfigure(
                    indice * 2 + 1,
                    weight=0,
                    minsize=1 if linhas_verticais else 0,
                )

        self._proxima_linha = 0
        self._desenhar_cabecalho()

    # -- construção interna ------------------------------------------

    @property
    def _ultima_coluna(self):
        return (len(self._colunas) - 1) * 2

    def _espaco(self, indice):
        """Folga de uma célula.

        As margens laterais são da tabela, não de quem a usa: é o
        que garante que o cabeçalho e as linhas começam e acabam
        exatamente no mesmo sítio.
        """
        esquerda = _MARGEM_TABELA if indice == 0 else 0

        if indice == len(self._colunas) - 1:
            direita = _MARGEM_TABELA
        else:
            direita = self._colunas[indice].espaco

        return (esquerda, direita)

    def _fundo(self, fila, cor):
        """Fundo de uma fila da grelha, por trás das células.

        `height=1` não é a altura real — é a altura PEDIDA. Sem ela,
        o CTkFrame pede os seus 200px por omissão e obriga a fila
        inteira da grelha a esticar até lá. Com 1, quem manda na
        altura da fila é o `minsize` que lhe demos e o conteúdo das
        células, que é o correto. O `sticky="nsew"` faz o resto.
        """
        fundo = ctk.CTkFrame(
            self.grelha, corner_radius=0, fg_color=cor, height=1
        )
        fundo.grid(
            row=fila,
            column=0,
            columnspan=self._ultima_coluna + 1,
            sticky="nsew",
        )

        return fundo

    def _verticais(self, fila):
        """Divisórias verticais de uma fila."""
        if not self._linhas_verticais:
            return

        for indice in range(len(self._colunas) - 1):
            # height=1 pela mesma razão do `_fundo`: sem ela, cada
            # divisória vertical pedia 200px de altura e esticava a
            # fila toda.
            ctk.CTkFrame(
                self.grelha,
                width=1,
                height=1,
                corner_radius=0,
                fg_color=tema.COR_BORDA,
            ).grid(row=fila, column=indice * 2 + 1, sticky="ns")

    def _divisoria_horizontal(self):
        """Risco de 1px a toda a largura, entre duas filas."""
        fila = self._proxima_linha
        self._proxima_linha += 1
        self.grelha.grid_rowconfigure(fila, minsize=1)

        ctk.CTkFrame(
            self.grelha,
            height=1,
            corner_radius=0,
            fg_color=tema.COR_BORDA,
        ).grid(
            row=fila,
            column=0,
            columnspan=self._ultima_coluna + 1,
            sticky="ew",
        )

    def _desenhar_cabecalho(self):
        fila = self._proxima_linha
        self._proxima_linha += 1

        self._fundo(fila, tema.CABECALHO_TABELA_FUNDO)
        self._verticais(fila)

        for indice, coluna in enumerate(self._colunas):
            ancora, sticky = _ALINHAMENTOS[coluna.alinhamento]
            # O fg_color tem de ser dito, não pode ficar
            # transparente: no CustomTkinter um widget transparente
            # herda o fundo do seu PAI, e o pai destas etiquetas é a
            # grelha (branca) — a faixa cinzenta é um irmão que está
            # por trás, não à volta. Sem isto, o cabeçalho ficava
            # cinzento com retângulos brancos por baixo de cada
            # título (08/09/2026).
            ctk.CTkLabel(
                self.grelha,
                text=coluna.titulo,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                fg_color=tema.CABECALHO_TABELA_FUNDO,
                font=ctk.CTkFont(size=10, weight="bold"),
                anchor=ancora,
            ).grid(
                row=fila,
                column=indice * 2,
                sticky=sticky or "ew",
                padx=self._espaco(indice),
                pady=_PADY_CABECALHO,
            )

        self._divisoria_horizontal()

        # Tudo o que existe até aqui é cabeçalho: `limpar` não lhe
        # toca.
        self._fixos = tuple(self.grelha.winfo_children())
        self._primeira_fila_de_dados = self._proxima_linha

    # -- corpo -------------------------------------------------------

    def limpar(self):
        """Apaga todas as linhas e reinicia o tom alternado."""
        for widget in self.grelha.winfo_children():
            if widget not in self._fixos:
                widget.destroy()

        for widget in self.corpo.winfo_children():
            if widget is not self.grelha:
                widget.destroy()

        self._proxima_linha = self._primeira_fila_de_dados
        self._desenhadas = 0

    def nova_linha(self):
        """Abre uma linha nova e devolve a grelha, que é o master a
        usar para criar as células.

        O tom alternado e a divisória são contados aqui: quem usa a
        tabela não precisa de saber em que linha vai.
        """
        if self._divisorias and self._desenhadas:
            self._divisoria_horizontal()

        self._fila_atual = self._proxima_linha
        self._proxima_linha += 1
        self.grelha.grid_rowconfigure(
            self._fila_atual, minsize=self._altura_linha, weight=0
        )

        if self._tom_alternado and self._desenhadas % 2 == 1:
            self._fundo(self._fila_atual, tema.LINHA_ALTERNADA)

        self._verticais(self._fila_atual)
        self._desenhadas += 1

        return self.grelha

    def colocar(self, linha, coluna, widget, esticar=None):
        """Coloca um widget numa coluna da linha aberta.

        'linha' é a grelha devolvida por `nova_linha` — está na
        assinatura para o código de quem usa a tabela se ler bem e
        para o master das células ser óbvio. A fila é a tabela que
        a sabe.

        Por omissão o sticky vem do `alinhamento` da coluna, para a
        célula não poder discordar do seu próprio título.
        """
        if esticar is None:
            esticar = _ALINHAMENTOS[self._colunas[coluna].alinhamento][1]

        widget.grid(
            row=self._fila_atual,
            column=coluna * 2,
            sticky=esticar,
            padx=self._espaco(coluna),
        )

        return widget

    def celula_acoes(
        self, linha, coluna, largura=None, altura=None, espaco=None
    ):
        """Cria e coloca a célula de botões da linha aberta.

        Devolve um frame com `adicionar(botao)`, que empacota os
        botões lado a lado com folga uniforme. A largura vem do
        `minimo` da coluna quando não é indicada, para a célula ter
        sempre o mesmo tamanho de linha para linha — botões de
        larguras diferentes não podem deslocar a coluna.
        """
        if largura is None:
            largura = self._colunas[coluna].minimo

        if altura is None:
            altura = max(self._altura_linha - 16, 24)

        acoes = _CelulaAcoes(
            self.grelha,
            largura,
            altura,
            espaco if espaco is not None else _ESPACO_BOTOES,
        )
        self.colocar(linha, coluna, acoes)

        return acoes

    def mostrar_vazio(self, mensagem=None):
        """Mensagem central para quando não há nada a listar."""
        ctk.CTkLabel(
            self.corpo,
            text=mensagem or self._mensagem_vazia,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=13),
        ).pack(pady=40)

    @property
    def vazia(self):
        return self._desenhadas == 0