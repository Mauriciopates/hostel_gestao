import collections
import datetime
import tkinter
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

import config
from . import tema
from . import sessao

# =====================================================================
# Caminhos das imagens
#
# O `img/` está na raiz do projeto, e este ficheiro está em
# `src/gui/`. O caminho é `../../img/`, mas não é escrito à mão —
# calcula-se a partir de `__file__`, que é o caminho DESTE ficheiro
# (independente de onde o `python` foi corrido).
#
# Porquê: se um dia corres a aplicação da raiz, de `src/` ou de
# `src/gui/`, o `__file__` é sempre o mesmo. Um caminho relativo
# simples (`"../../img/x.png"`) funcionava só de um sítio — o resto
# dava `FileNotFoundError` ou, pior, ficava silenciosamente com um
# retângulo vazio.
#
# `.resolve()` normaliza o caminho antes de o usar: resolve `..`,
# symlinks e caminhos relativos, para o `Image.open(...)` receber
# sempre um caminho absoluto.
# =====================================================================

_PASTA_IMG = Path(__file__).resolve().parent.parent.parent / "img"

_LOGO_SIDEBAR = _PASTA_IMG / "ico_hostel_transparente.png"


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

    LOGO no topo (13/09/2026): em vez do antigo cabeçalho "●
    HOSTEL CLEAN" em texto, o topo passa a mostrar
    `ico_hostel_transparente.png` dentro de uma caixa quase-branca.
    A caixa resolve o problema de contraste — o logo tem o texto em
    navy escuro (#0C2F48), exatamente a mesma cor do fundo da
    barra; sem a caixa, o texto desaparecia. Validado por mockup
    antes de codar.

    ESTADO ATIVO (13/09/2026): cada botão de item fica gravado em
    `self._botoes_por_ecra`, com a classe do ecrã como chave. O
    método `marcar_ativo(classe_ecra)` — chamado por
    `Aplicacao.mostrar_frame` a cada troca de ecrã — pinta o botão
    do ecrã atual de azul (AZUL_PRINCIPAL) e os outros de
    transparente. Sem isto, o utilizador perdia-se sobre onde
    estava: nenhum botão marcava o ecrã aberto.

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

        # Guarda o controlador e o dicionário de botões por classe
        # de ecrã — usado pelo `marcar_ativo` para saber que botão
        # pintar de azul quando um ecrã é aberto.
        self.controlador = controlador
        self._botoes_por_ecra = {}

        # =============================================================
        # LOGO no topo, dentro de uma caixa quase-branca
        #
        # O logo (`ico_hostel_transparente.png`) tem o texto em navy
        # escuro (#0C2F48). Sobre a sidebar navy (a mesma cor), o
        # texto desaparecia. Uma caixa quase-branca atrás resolve o
        # contraste — validado por mockup antes de codar.
        #
        # A caixa tem cantos redondos alinhados com os itens da
        # navegação (RAIO_BOTAO = 10), para o conjunto ler como um
        # todo, não como um retângulo colado lá em cima.
        #
        # O `Image.open(...)` é chamado uma única vez, no `__init__`
        # da barra — não a cada `mostrar_frame`. Se a imagem não
        # existir (mudou de sítio, foi apagada), o erro é imediato e
        # claro, em vez de mostrar um retângulo vazio que ninguém
        # percebe de onde vem.
        # =============================================================
        imagem_pil = Image.open(_LOGO_SIDEBAR)
        proporcao = imagem_pil.height / imagem_pil.width
        largura_logo = 110
        altura_logo = int(largura_logo * proporcao)

        # A referência tem de ficar guardada em `self`, senão o
        # garbage collector do Python recolhe-a e a imagem
        # desaparece da sidebar (bug conhecido do Tkinter: o
        # PhotoImage tem de ter uma referência viva).
        self._imagem_logo = ctk.CTkImage(
            light_image=imagem_pil,
            dark_image=imagem_pil,
            size=(largura_logo, altura_logo),
        )

        caixa_logo = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="#F5F7F9",
        )
        caixa_logo.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            caixa_logo,
            text="",
            image=self._imagem_logo,
        ).pack(padx=6, pady=6)

        # =============================================================
        # ITENS da navegação
        #
        # Cada botão de item é guardado em `self._botoes_por_ecra`
        # com a classe do ecrã como chave — é assim que o
        # `marcar_ativo` consegue encontrar e pintar o botão certo
        # quando `Aplicacao.mostrar_frame` lhe diz "estou neste
        # ecrã".
        # =============================================================
        for item in itens:
            if item["tipo"] == "secao":
                # O `.upper()` existe para não obrigar quem escreve
                # o `ITENS_MENU` (em app.py) a lembrar-se de escrever
                # as secções em maiúsculas. Mesma convenção dos
                # títulos das tabelas ("ID", "NOME", "AÇÕES").
                #
                # O `padx=14` alinha o texto da secção com o texto
                # dos itens da navegação (que têm `padx=6` no `pack`
                # do botão + 12 interno do CTkButton, somando 18
                # visíveis — os 14 aqui ficam ligeiramente à
                # esquerda, o que lê melhor do que alinhado ao
                # pixel).
                ctk.CTkLabel(
                    self,
                    text=item["texto"].upper(),
                    text_color=tema.COR_TEXTO_SIDEBAR_SECAO,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ).pack(fill="x", padx=14, pady=(12, 4))
            else:
                botao = ctk.CTkButton(
                    self,
                    text=item["texto"],
                    fg_color="transparent",
                    text_color=tema.COR_TEXTO_SIDEBAR,
                    hover_color=tema.AZUL_PRINCIPAL,
                    corner_radius=tema.RAIO_BOTAO,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    command=lambda ecra=item["ecra"]: (
                        controlador.mostrar_frame(ecra)
                    ),
                )
                botao.pack(fill="x", padx=6, pady=1)

                self._botoes_por_ecra[item["ecra"]] = botao

        # =============================================================
        # RODAPÉ: versão + botão de trocar utilizador
        # =============================================================
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
        ).pack(side="bottom", fill="x", padx=10, pady=(4, 0))

    def marcar_ativo(self, classe_ecra):
        """Pinta de azul o botão do ecrã indicado, e limpa os
        outros.

        Chamado por `Aplicacao.mostrar_frame` sempre que o ecrã
        muda — sem isto, nenhum botão fica marcado como "estou
        aqui", e o utilizador perde-se sobre onde está.

        'classe_ecra' é a classe (não o nome) do ecrã — é a mesma
        que está gravada em `_botoes_por_ecra` como chave, e a
        mesma que é passada a `mostrar_frame`.

        O "azul ativo" é o mesmo AZUL_PRINCIPAL usado no `hover`
        dos botões. Isto é intencional: o item ativo e o item
        sob o rato usam o mesmo azul, porque ambos significam
        "este é o item em foco agora". A diferença é que o ativo
        fica assim até se mudar de ecrã, o hover só enquanto o
        rato está lá.

        Ecrãs que não estão na barra lateral (ex.: um popup, ou
        um ecrã que só se abre por um caminho específico — o
        `NovoContratoMensal` a partir do `PlantaLugaresModal`)
        não têm botão associado. Nesse caso, todos os botões ficam
        transparentes, o que é aceitável: o utilizador está
        dentro de um formulário, não num ecrã de navegação.
        """
        for ecra, botao in self._botoes_por_ecra.items():
            if ecra is classe_ecra:
                botao.configure(fg_color=tema.AZUL_PRINCIPAL)
            else:
                botao.configure(fg_color="transparent")


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

# Largura assumida para a barra de scroll do corpo enquanto ela
# ainda não foi medida (ver `Tabela._ajustar_folga_scroll`). É só o
# valor de partida: mal a tabela aparece no ecrã, a folga real passa
# a ser medida e corrigida.
_FOLGA_SCROLL_INICIAL = 16

# Quantas vezes se tenta medir a folga antes de desistir (60 ms
# entre tentativas, ou seja, cerca de 2 segundos). Existe só para
# uma tabela que nunca chegue a ser mostrada não ficar a repetir a
# medição para sempre.
_TENTATIVAS_FOLGA_MAX = 30

# Quantas passagens de confirmação o alinhamento do cabeçalho pode
# fazer de cada vez. Cada passagem só acontece se a anterior mudou
# alguma coisa; na prática bastam duas ou três, e o limite existe
# para nunca haver um caso a repetir-se sem fim.
_PASSAGENS_ALINHAMENTO_MAX = 6


def pintar_fundo(widget, cor):
    """Dá a `widget`, e a todos os descendentes que estejam
    transparentes, a cor de fundo da linha onde ele está.

    PORQUÊ (correção de 21/09/2026): no CustomTkinter um widget
    transparente herda o fundo do seu PAI. O pai das células de uma
    linha é a grelha da tabela, que é branca — a faixa com o tom
    alternado é um IRMÃO que está por trás, não à volta. Resultado:
    com `tom_alternado=True`, o tom só se via nas folgas entre as
    células, e tudo o resto (o nome do cliente, o subtítulo, os
    botões) aparecia branco por cima. É exatamente o mesmo problema
    que o cabeçalho já tinha tido em 08/09/2026, e que lá foi
    resolvido dizendo o `fg_color` a cada etiqueta em vez de a
    deixar transparente.

    Só pinta o que está transparente: um crachá (ID, ESTADO) ou
    qualquer widget que já tenha cor própria fica exatamente como
    estava. É isso que torna esta função segura de aplicar a todas
    as células de todas as tabelas sem ter de saber o que cada ecrã
    lá pôs.

    O `try` existe porque nem tudo o que pode estar dentro de uma
    célula é um widget do CustomTkinter — um widget do Tkinter de
    base não conhece `fg_color` e responde com um erro em vez de uma
    cor. Nesse caso não há nada a pintar, e a descida aos filhos
    continua na mesma.
    """
    try:
        if widget.cget("fg_color") == "transparent":
            widget.configure(fg_color=cor)
    except (AttributeError, ValueError, tkinter.TclError):
        pass

    for filho in widget.winfo_children():
        pintar_fundo(filho, cor)


class _CelulaAcoes(ctk.CTkFrame):
    """Célula que agrupa os botões de ação de uma linha.

    Existe para os botões terem sempre a mesma folga entre si e para
    a célula ter largura fixa. O `width` com `pack_propagate(False)`
    é obrigatório: um CTkFrame sem largura fica nos 200px por
    omissão, e um botão que não coubesse nesses 200px era desenhado
    espremido a poucos pixéis em vez de ficar de fora de forma
    visível (08/09/2026).

    `cor_fundo` (21/09/2026): a cor da linha onde esta célula está.
    Os botões são acrescentados DEPOIS de a célula já estar colocada
    na grelha, por isso não apanhariam a pintura que a `Tabela` faz
    em `colocar` — ficavam brancos por cima das linhas com tom
    alternado. Guardar a cor aqui é o que permite pintar cada botão
    no momento em que ele entra.
    """

    def __init__(
        self,
        master,
        largura,
        altura,
        espaco=_ESPACO_BOTOES,
        cor_fundo=None,
    ):
        # A altura é tão obrigatória como a largura, e por baixo é o
        # mesmo problema: com `pack_propagate(False)` o frame fica
        # com os 200px de altura por omissão do CTkFrame e obriga a
        # fila inteira da grelha a esticar até lá (08/09/2026,
        # apanhado a medir a tabela num ecrã virtual).
        super().__init__(
            master,
            fg_color=cor_fundo if cor_fundo else "transparent",
            width=largura,
            height=altura,
        )
        self.pack_propagate(False)
        self._espaco = espaco
        self._cor_fundo = cor_fundo
        self._primeiro = True

    def adicionar(self, widget):
        """Junta um botão à direita dos que já lá estão."""
        widget.pack(
            side="left", padx=(0 if self._primeiro else self._espaco, 0)
        )
        self._primeiro = False

        if self._cor_fundo:
            pintar_fundo(widget, self._cor_fundo)

        return widget


class Tabela(ctk.CTkFrame):
    """Tabela com cabeçalho FIXO e corpo com scroll.

    ESTRUTURA (alterada em 21/09/2026, v1.6.0 — mockup aprovado
    pelo aluno). Até aqui o cabeçalho era a linha 0 da mesma grelha
    das linhas de dados, e a grelha inteira vivia dentro do
    `CTkScrollableFrame`: ao descer a lista, o cabeçalho descia com
    ela e desaparecia. Agora são dois blocos:

        Tabela (cartão com borda)
        ├── cabecalho          -> CTkFrame fixo, NÃO faz scroll
        │   └── grelha_cabecalho
        ├── divisória de 1px
        └── corpo              -> CTkScrollableFrame
            └── grelha         -> só as linhas de dados

    O MOTIVO DE ANTES CONTINUA VÁLIDO, e é por isso que a separação
    não é só "tirar o cabeçalho de dentro do scroll": o Tk não
    decide a largura de uma coluna só a partir do peso e do mínimo
    que lhe damos — parte do que os próprios filhos pedem e só
    depois reparte o que sobra. Duas grelhas com conteúdos
    diferentes (títulos curtos em cima, crachás de 90px e botões de
    100px em baixo) dão colunas diferentes. Foi essa a causa do
    desalinhamento de 08/09/2026, que nenhum acerto de `padx` ou de
    peso resolvia.

    O que substitui a garantia que existia quando havia uma grelha
    só são três coisas, e as três têm de estar cá:

    1. `_configurar_colunas` é chamada com a MESMA definição de
       colunas nas duas grelhas — pesos e mínimos saem de um sítio
       só, não podem divergir por um número esquecido de um lado.
       Isto sozinho NÃO chega (ver ponto 3), mas é o que faz a
       tabela nascer com as colunas certas antes de haver linhas
       nenhumas para medir.

    2. A barra de scroll do corpo ocupa largura que o cabeçalho não
       tem. Sem compensar isso, a tabela de cima é mais larga do que
       a de baixo. `_ajustar_folga_scroll` mede a diferença e
       reserva-a à direita do cabeçalho — medida, não assumida: a
       largura da barra muda com a versão do CustomTkinter e com a
       escala do ecrã, e a barra só aparece quando há linhas a mais
       para caber.

    3. Mesmo com a largura total igual e a mesma configuração de
       colunas nos dois lados, o Tk NÃO reparte o espaço da mesma
       maneira: a largura exigida por uma coluna é o maior valor
       entre o mínimo que lhe demos e o que os filhos DAQUELA grelha
       pedem, folgas incluídas. A célula de ações do corpo pede 100px
       mais 16 de margem; o título "AÇÕES" pede pouco mais de 40. Os
       16px de diferença saem das colunas com peso, e as divisórias
       verticais deixam de bater certo — foi este o bug de
       08/09/2026, e é ele que volta se a separação parar no ponto 2.
       `_sincronizar_colunas` resolve-o pela raiz: o corpo é a
       verdade, e o cabeçalho copia dele a largura REAL de cada
       coluna (`grid_bbox`), fixando-a sem peso. Deixa de haver duas
       repartições para fazer coincidir — há uma, e a outra obedece.

    Como o fundo de cada linha já não pode ser um frame que contém
    as células, é um frame colocado na mesma célula da grelha com
    `columnspan`, criado ANTES delas — no Tk, widgets criados depois
    ficam por cima. As células que ficam por cima desse fundo são
    pintadas com a cor da linha em `colocar` (ver `pintar_fundo`),
    senão o tom alternado ficava escondido por baixo de retângulos
    brancos.

    Uso típico:

        self.tabela = componentes.Tabela(
            self,
            colunas=(
                componentes.Coluna("ID", minimo=94, espaco=8),
                componentes.Coluna("NOME", peso=3, minimo=190),
                componentes.Coluna("ESTADO", peso=1, minimo=90),
                componentes.Coluna(
                    "PREÇO", peso=1, minimo=80, alinhamento="e", espaco=8
                ),
                componentes.Coluna("AÇÕES", minimo=100),
            ),
            altura_linha=52,
            tom_alternado=True,
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
        self._fila_atual = 0
        self._cor_fila_atual = tema.COR_FUNDO
        self._folga_scroll = _FOLGA_SCROLL_INICIAL
        self._tentativas_folga = 0
        self._larguras_cabecalho = {}
        self._alinhamento_agendado = None
        self._passagens_alinhamento = 0

        # -- cabeçalho fixo, fora do scroll ---------------------------
        #
        # O `padx=1, pady=(1, 0)` mete a faixa por dentro da borda de
        # 1px do cartão. Sem isso, a faixa (de cantos retos) passava
        # por cima dos cantos redondos do cartão e comia-os.
        self.cabecalho = ctk.CTkFrame(
            self, corner_radius=0, fg_color=tema.CABECALHO_TABELA_FUNDO
        )
        self.cabecalho.pack(fill="x", padx=1, pady=(1, 0))

        self.grelha_cabecalho = ctk.CTkFrame(
            self.cabecalho, fg_color="transparent"
        )
        self.grelha_cabecalho.pack(fill="x", padx=(0, self._folga_scroll))

        ctk.CTkFrame(
            self, height=1, corner_radius=0, fg_color=tema.COR_BORDA
        ).pack(fill="x")

        # -- corpo com scroll -----------------------------------------
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
        # fronteira de que estamos a falar. A MESMA configuração vai
        # para as duas grelhas — ver docstring da classe.
        self._configurar_colunas(self.grelha_cabecalho)
        self._configurar_colunas(self.grelha)

        self._proxima_linha = 0
        self._desenhar_cabecalho()

        # O alinhamento do cabeçalho só pode ser medido depois de o
        # Tk ter desenhado a tabela; daí o `after`, que se repete
        # sozinho enquanto ainda não houver nada para medir. O
        # `<Configure>` volta a medir sempre que a tabela muda de
        # largura.
        #
        # LIÇÃO CARA (21/09/2026): o binding é feito no CABEÇALHO e
        # com `add=True`, e as duas coisas são obrigatórias.
        #
        # - Em Tkinter, um `bind` sem `add` APAGA o que já lá
        #   estava. O `CTkFrame` protege-se disso sozinho (o seu
        #   `bind` reencaminha sempre com `add=True`), mas o
        #   `CTkScrollableFrame` não redefine o `bind` — nele vale a
        #   regra do Tkinter de base. Ligar um `<Configure>` por
        #   cima do corpo apagou o binding interno que mantém a
        #   `scrollregion` do canvas atualizada, e a tabela ficou
        #   impossível de rolar: barra de scroll à vista, roda do
        #   rato sem efeito e nenhum erro no ecrã (o
        #   `_mouse_wheel_all` do CustomTkinter desiste em silêncio
        #   quando o canvas julga que o conteúdo todo já cabe).
        #
        # - `add=True` e não `add="+"`: as duas funcionam em
        #   execução, mas a assinatura do `CTkFrame.bind` declara
        #   `add` como booleano e o Pylance/pyright acusa o `"+"`.
        #
        # - No cabeçalho, e não no corpo, para não se andar sequer à
        #   volta dos bindings internos do `CTkScrollableFrame`. O
        #   cabeçalho é um frame simples e muda de largura sempre
        #   que a tabela muda — que é quando é preciso remedir. O
        #   outro caso (a barra de scroll a aparecer ou a
        #   desaparecer por a lista ter mudado de tamanho) é tratado
        #   pelo `limpar`, que agenda o alinhamento a seguir a cada
        #   redesenho.
        self.after(60, self._alinhar_cabecalho)
        self.cabecalho.bind("<Configure>", self._alinhar_cabecalho, add=True)

    # -- construção interna ------------------------------------------

    def _configurar_colunas(self, grelha):
        """Aplica a definição de colunas a uma grelha.

        Chamada duas vezes, uma por grelha (cabeçalho e corpo), com
        a mesma `self._colunas`. É esta função que substitui a
        garantia de alinhamento que existia quando cabeçalho e
        linhas viviam na mesma grelha.
        """
        for indice, coluna in enumerate(self._colunas):
            grelha.grid_columnconfigure(
                indice * 2, weight=coluna.peso, minsize=coluna.minimo
            )

            if indice < len(self._colunas) - 1:
                grelha.grid_columnconfigure(
                    indice * 2 + 1,
                    weight=0,
                    minsize=1 if self._linhas_verticais else 0,
                )

    def _alinhar_cabecalho(self, _evento=None):
        """PEDE um alinhamento do cabeçalho ao corpo — não o faz já.

        A diferença é o que faz isto funcionar. Este método é
        chamado a partir do `<Configure>` do corpo, ou seja, no meio
        de o Tk estar a refazer o desenho: medir ali dá as larguras
        ANTERIORES, e o cabeçalho ficava uma passagem atrasado (foi
        exatamente o que apanhou o teste de cenários — redimensionar
        a janela deixava o cabeçalho com as colunas antigas). Agendar
        com `after` põe a medição a correr depois de o desenho estar
        feito.

        Vários pedidos seguidos (o `<Configure>` dispara muitas
        vezes por cada redimensionamento) juntam-se todos num só: se
        já há um agendado, não se agenda outro.
        """
        if self._alinhamento_agendado is not None:
            return

        self._alinhamento_agendado = self.after(30, self._aplicar_alinhamento)

    def _aplicar_alinhamento(self):
        """Alinha o cabeçalho pelo corpo, e confirma o resultado.

        Dois passos, sempre por esta ordem: primeiro igualar a
        largura total (`_ajustar_folga_scroll`), depois copiar a
        largura de cada coluna (`_sincronizar_colunas`) — copiar
        colunas de uma tabela com outra largura total não serviria
        de nada.

        Mexer na geometria muda aquilo que estava a ser medido, por
        isso, sempre que alguma coisa foi alterada, agenda-se mais
        uma passagem para confirmar. Na prática convergem em duas ou
        três; o limite existe só para nunca haver um caso patológico
        a repetir isto para sempre.
        """
        self._alinhamento_agendado = None

        try:
            self.update_idletasks()
        except tkinter.TclError:
            # Tabela destruída entretanto (ecrã fechado) — não há
            # nada para alinhar.
            return

        mudou = self._ajustar_folga_scroll()

        if mudou:
            self.update_idletasks()

        if self._sincronizar_colunas():
            mudou = True

        if mudou and self._passagens_alinhamento < _PASSAGENS_ALINHAMENTO_MAX:
            self._passagens_alinhamento += 1
            self._alinhamento_agendado = self.after(
                30, self._aplicar_alinhamento
            )
        else:
            self._passagens_alinhamento = 0

    def _sincronizar_colunas(self):
        """Copia para o cabeçalho a largura real de cada coluna do
        corpo, fixando-a (peso 0).

        É isto que impede o bug de 08/09/2026 de voltar: com pesos
        dos dois lados, cada grelha repartia o espaço à sua maneira,
        porque o que os filhos pedem é diferente em cima e em baixo
        (ver ponto 3 da docstring da classe). Aqui o corpo passa a
        ser a única grelha que decide, e o cabeçalho limita-se a
        obedecer.

        Sem linhas não há nada para copiar — o cabeçalho fica com a
        configuração de partida, que é a certa para uma tabela
        vazia.

        Devolve True se alguma coluna mudou de largura.
        """
        if self._desenhadas == 0:
            return False

        mudou = False

        for indice in range(len(self._colunas) * 2 - 1):
            caixa = self.grelha.grid_bbox(column=indice, row=0)

            # Grelha ainda não desenhada: sai e tenta na próxima
            # chamada, em vez de gravar larguras que não valem nada.
            if not caixa or caixa[2] <= 0:
                return mudou

            largura = caixa[2]

            if self._larguras_cabecalho.get(indice) == largura:
                continue

            self._larguras_cabecalho[indice] = largura
            self.grelha_cabecalho.grid_columnconfigure(
                indice, weight=0, minsize=largura
            )
            mudou = True

        return mudou

    def _ajustar_folga_scroll(self):
        """Iguala a largura útil do cabeçalho à do corpo.

        A conta é direta: `self.cabecalho` é um frame normal e
        ocupa a largura toda do cartão; `self.corpo` é um
        `CTkScrollableFrame`, e a largura que ele responde já é a
        largura INTERIOR — ou seja, o que sobra depois da barra de
        scroll. A diferença entre os dois é exatamente o espaço que
        falta reservar à direita do cabeçalho.

        Medir em vez de assumir um número: a largura da barra muda
        com a versão do CustomTkinter e com a escala do ecrã, e a
        barra só aparece quando há linhas a mais para caber — a
        folga certa muda com a própria lista, não é uma constante.

        Como a folga é calculada por diferença absoluta (e não somada
        à anterior), chamar isto as vezes que o Tk quiser dá sempre o
        mesmo resultado e não há ciclo: quando o valor já está certo,
        a função sai sem mexer em nada.

        Enquanto a tabela ainda não foi desenhada, o Tk responde 1 à
        largura. Nesse caso não há nada a medir e a função volta a
        tentar — com um limite, para uma tabela que nunca chegue a
        aparecer no ecrã (um ecrã criado mas nunca aberto) não ficar
        a acordar o Tk de 60 em 60 ms para sempre. Se esse ecrã for
        aberto mais tarde, é o `<Configure>` do corpo que trata da
        medição.

        Devolve True se a folga mudou.
        """
        largura_cabecalho = self.cabecalho.winfo_width()
        largura_corpo = self.corpo.winfo_width()

        if largura_cabecalho <= 1 or largura_corpo <= 1:
            if self._tentativas_folga < _TENTATIVAS_FOLGA_MAX:
                self._tentativas_folga += 1
                self.after(60, self._alinhar_cabecalho)

            return False

        self._tentativas_folga = 0
        folga = max(largura_cabecalho - largura_corpo, 0)

        if folga == self._folga_scroll:
            return False

        self._folga_scroll = folga
        self.grelha_cabecalho.pack_configure(padx=(0, folga))

        return True

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

    def _verticais(self, fila, grelha=None):
        """Divisórias verticais de uma fila.

        `grelha` existe porque o cabeçalho passou a ser uma grelha
        separada (21/09/2026) e precisa das suas próprias
        divisórias — por omissão continua a ser a grelha do corpo.
        """
        if not self._linhas_verticais:
            return

        if grelha is None:
            grelha = self.grelha

        for indice in range(len(self._colunas) - 1):
            # height=1 pela mesma razão do `_fundo`: sem ela, cada
            # divisória vertical pedia 200px de altura e esticava a
            # fila toda.
            ctk.CTkFrame(
                grelha,
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
        """Desenha os títulos na grelha do cabeçalho (fila 0).

        Só é chamado uma vez, no `__init__`: o cabeçalho vive agora
        fora do corpo, por isso o `limpar` nunca lhe toca e não há
        filas fixas a proteger dentro da grelha de dados.
        """
        self._verticais(0, self.grelha_cabecalho)

        for indice, coluna in enumerate(self._colunas):
            ancora, sticky = _ALINHAMENTOS[coluna.alinhamento]
            # O fg_color continua a ser dito em vez de ficar
            # transparente. Hoje o pai já é a própria faixa cinzenta
            # (o que por si só bastaria), mas dizer a cor mantém o
            # cabeçalho correto mesmo que a estrutura volte a mudar
            # — foi a falta disto que pintou o cabeçalho de branco
            # em 08/09/2026.
            ctk.CTkLabel(
                self.grelha_cabecalho,
                text=coluna.titulo,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                fg_color=tema.CABECALHO_TABELA_FUNDO,
                font=ctk.CTkFont(size=10, weight="bold"),
                anchor=ancora,
            ).grid(
                row=0,
                column=indice * 2,
                sticky=sticky or "ew",
                padx=self._espaco(indice),
                pady=_PADY_CABECALHO,
            )

    # -- corpo -------------------------------------------------------

    def limpar(self):
        """Apaga todas as linhas e reinicia o tom alternado.

        Desde 21/09/2026 pode apagar a grelha toda sem cuidados: o
        cabeçalho já não vive aqui dentro.
        """
        for widget in self.grelha.winfo_children():
            widget.destroy()

        for widget in self.corpo.winfo_children():
            if widget is not self.grelha:
                widget.destroy()

        self._proxima_linha = 0
        self._desenhadas = 0
        self._cor_fila_atual = tema.COR_FUNDO

        # As larguras copiadas para o cabeçalho eram as da lista
        # anterior; a que vem a seguir pode ter outras (a barra de
        # scroll aparece ou desaparece consoante o número de linhas).
        # Esquecê-las obriga o próximo alinhamento a medir tudo de
        # novo, em vez de confiar em valores já velhos.
        self._larguras_cabecalho.clear()
        self.after(60, self._alinhar_cabecalho)

    def nova_linha(self):
        """Abre uma linha nova e devolve a grelha, que é o master a
        usar para criar as células.

        O tom alternado e a divisória são contados aqui: quem usa a
        tabela não precisa de saber em que linha vai.

        Desde 21/09/2026 a fila tem SEMPRE um fundo próprio (branco
        ou o tom alternado) e a cor fica guardada em
        `_cor_fila_atual`, para o `colocar` poder pintar as células
        com ela.
        """
        if self._divisorias and self._desenhadas:
            self._divisoria_horizontal()

        self._fila_atual = self._proxima_linha
        self._proxima_linha += 1
        self.grelha.grid_rowconfigure(
            self._fila_atual, minsize=self._altura_linha, weight=0
        )

        if self._tom_alternado and self._desenhadas % 2 == 1:
            self._cor_fila_atual = tema.LINHA_ALTERNADA
        else:
            self._cor_fila_atual = tema.COR_FUNDO

        self._fundo(self._fila_atual, self._cor_fila_atual)
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

        A pintura no fim é o que faz o tom alternado ser visível:
        sem ela, uma célula transparente herdava o branco da grelha
        e tapava a faixa que está por trás (ver `pintar_fundo`).
        """
        if esticar is None:
            esticar = _ALINHAMENTOS[self._colunas[coluna].alinhamento][1]

        widget.grid(
            row=self._fila_atual,
            column=coluna * 2,
            sticky=esticar,
            padx=self._espaco(coluna),
        )

        pintar_fundo(widget, self._cor_fila_atual)

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
            cor_fundo=self._cor_fila_atual,
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


# =====================================================================
# Helpers visuais genéricos — partilhados por todos os ecrãs
#
# Estavam copiados por 5 módulos da GUI (gui_propriedades, gui_clientes,
# gui_contratos, gui_calendario, gui_estoque). Passam a viver aqui —
# uma definição só, sem depender de quem importa quem.
#
# O prefixo "_" caiu de propósito: eram privados quando viviam dentro
# de cada módulo, agora são API pública de componentes.py.
#
# ALTERAÇÕES 13/09/2026 — consolidação final:
# - `formatar_valor` é nova aqui. Existia em três sítios diferentes
#   (gui_contratos.py, gui_calendario.py, gui_unidades.py), cada um
#   com a sua cópia local com o mesmo nome. Passa a viver aqui, para
#   todas as GUI usarem a mesma formatação PT-PT (vírgula decimal,
#   ponto de milhar, "€" no fim).
# - As cópias locais de `colocar_no_topo` (com prefixo "_") em
#   gui_propriedades, gui_clientes, gui_contratos, gui_calendario e
#   gui_responsaveis foram removidas — todos passaram a chamar
#   `componentes.colocar_no_topo`.
# - As cópias locais de `tornar_cliclavel` em gui_calendario e
#   gui_unidades foram removidas — todas passaram a chamar
#   `componentes.tornar_cliclavel`.
# - A cópia local de `_truncar_texto` em gui_propriedades foi
#   removida — passou a chamar `componentes.truncar_texto`, mantendo
#   o parâmetro `fonte` (a fonte é criada uma vez por recarregamento,
#   não a cada linha).
#
# NOTA 21/09/2026: `pintar_fundo` também é um helper público, mas
# vive lá em cima, logo antes da `Tabela` — está tão colado ao
# funcionamento da tabela que separá-lo daqui só obrigava a saltar o
# ficheiro de uma ponta à outra para perceber o tom alternado.
# =====================================================================


def colocar_no_topo(janela):
    """Traz um popup (CTkToplevel) para a frente da janela principal.

    Sem isto, o Windows (e alguns outros gestores de janelas) por
    vezes abre o popup por baixo da janela principal, escondido.
    `after(10, ...)` dá tempo ao Tk para mapear a janela antes de
    `grab_set()` — chamado logo a seguir ao `super().__init__(...)`,
    `grab_set()` falha com "grab failed: window not viewable" em
    alguns sistemas.
    """
    janela.after(
        10, lambda: (janela.lift(), janela.focus_force(), janela.grab_set())
    )


def centrar_sobre(janela, master, largura, altura):
    """Centra um popup (CTkToplevel) sobre a janela que o abriu.

    Sem isto o Tk coloca o popup no canto superior esquerdo do ecrã,
    longe do botão que acabou de ser clicado.
    """
    master.update_idletasks()
    x = master.winfo_rootx() + (master.winfo_width() - largura) // 2
    y = master.winfo_rooty() + (master.winfo_height() - altura) // 2
    janela.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")


def tornar_cliclavel(widget, ao_clicar):
    """Liga o clique (botão esquerdo) e o cursor de mão a um widget e
    a todos os seus descendentes.

    Em Tkinter, um clique num widget-filho não propaga sozinho para o
    pai — por isso é preciso fazer o binding widget a widget. Usado
    pelas caixas da Planta de Lugares, pelos cartões do hub de Stock,
    e por qualquer sítio onde um "cartão" tem de reagir ao clique
    mesmo quando se clica em cima do texto lá dentro.
    """
    widget.bind("<Button-1>", lambda evento: ao_clicar())
    widget.configure(cursor="hand2")

    for filho in widget.winfo_children():
        tornar_cliclavel(filho, ao_clicar)


def truncar_texto(fonte, texto, largura_max):
    """Corta `texto` com reticências ("…") se a sua largura
    renderizada (medida com `fonte`, um `tkinter.font.Font` real)
    ultrapassar `largura_max` em pixels.

    Existe para um nome ou morada fora do normal nunca mais empurrar
    as colunas seguintes de uma tabela — as larguras das colunas
    continuam fixas (definidas por `Coluna.minimo`), isto é só a
    rede de segurança para o caso raro de um valor mais comprido.

    A fonte é passada de fora, e não criada aqui dentro, por uma
    razão prática: quem chama já a cria uma vez por recarregamento
    (não a cada linha), e criar `tkinter.font.Font` a cada célula
    era mais lento sem nenhum ganho. Ver `gui_propriedades.py`,
    onde isto é usado em série.

    Nota honesta: a fonte usada para medir (`tkinter.font.Font`) não
    é pixel-a-pixel idêntica à que o CustomTkinter usa para desenhar
    (`CTkFont`) — a diferença é cosmética (corta um caráter a mais ou
    a menos no limite), nunca causa colisão nenhuma.
    """
    if fonte.measure(texto) <= largura_max:
        return texto

    reticencias = "…"
    cortado = texto
    while cortado and fonte.measure(cortado + reticencias) > largura_max:
        cortado = cortado[:-1]

    return (cortado + reticencias) if cortado else reticencias


def formatar_valor(valor):
    """Formata um Decimal em texto PT-PT, com vírgula decimal,
    ponto de milhar e símbolo "€" no fim.

    Mesma convenção do `cli.formatar_valor` (a camada de linha de
    comandos) — a formatação tem de ser a mesma nos dois sítios,
    senão o mesmo valor aparece escrito de duas maneiras diferentes
    consoante o sítio de onde se olha.

    Estava duplicada em gui_contratos.py, gui_calendario.py e
    gui_unidades.py, cada uma com a sua própria cópia local. Passou
    a viver aqui em 13/09/2026, na consolidação dos helpers.

    Um valor ausente (`None`) devolve "—" — mesma convenção neutra
    que o `cli.formatar_valor` usa, para não obrigar a aprender dois
    símbolos diferentes para "não há valor aqui".

    Sempre com duas casas decimais ("45,00 €", nunca "45 €") — é
    dinheiro, e dinheiro apresenta-se sempre com duas casas em
    PT-PT. A troca de ponto de milhar com vírgula decimal é feita em
    dois passos com um marcador temporário, para as duas trocas não
    se atropelarem uma à outra.
    """
    if valor is None:
        return "—"

    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{texto} €"
