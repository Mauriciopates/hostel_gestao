import collections
import ctypes
import datetime
import decimal
import re
import sys
import tkinter
import unicodedata
from ctypes import wintypes
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

import config
from . import tema
from . import sessao

# =====================================================================
# Caminhos das imagens
#
# O caminho do `img/` vem de `config.PASTA_IMG` (v1.8.0), que sabe
# onde ele está a correr do código E no executável (PyInstaller).
#
# Histórico: antes calculava-se aqui `../../img/` a partir do
# `__file__` deste ficheiro — resolvia o problema de correr a app de
# pastas diferentes, mas no executável apontava para fora do
# `_internal` e o logótipo desaparecia.
# =====================================================================

_PASTA_IMG = config.PASTA_IMG

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
        # RODAPÉ: versão + botão de trocar utilizador
        # =============================================================
        # 26/09/2026 — o rodapé é empacotado ANTES dos itens: no
        # pack, quem entra primeiro tem prioridade no espaço. Com o
        # rodapé depois, o Master (com todos os itens) espremia o
        # botão "Trocar utilizador".
        ctk.CTkLabel(
            self,
            text=f"v{config.VERSAO}",
            text_color=tema.COR_TEXTO_SIDEBAR_SECAO,
            font=ctk.CTkFont(size=9),
        ).pack(side="bottom", pady=10)

        # Servidor em uso (26/09/2026): com Local e VM a terem bases
        # independentes, tem de estar sempre à vista onde se está a gravar.
        ctk.CTkLabel(
            self,
            text=f"● {config.SERVIDOR_NOME}",
            text_color=tema.COR_TEXTO_SIDEBAR,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(side="bottom", pady=(6, 0))

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
                ).pack(fill="x", padx=14, pady=(8, 2))
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
    ("titulo", "peso", "minimo", "alinhamento", "espaco", "ordenavel"),
    defaults=("", 0, 0, "w", 0, None),
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
- ordenavel (27/09/2026): se o clique no título ordena a tabela por
  esta coluna. None (omissão) = decide sozinho: ordena, a não ser que
  o título esteja vazio ou seja uma coluna de botões ("AÇÕES",
  "GERIR"). True/False forçam.
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

# -- Ordenação por clique no cabeçalho (27/09/2026) ---------------------
#
# Títulos que nunca ordenam por omissão: são colunas de botões, não de
# dados. Comparados em maiúsculas.
_TITULOS_SEM_ORDEM = frozenset({"", "AÇÕES", "ACOES", "GERIR"})

# Setas mostradas à frente do título da coluna ativa.
_SETA_CRESCENTE = " ▲"
_SETA_DECRESCENTE = " ▼"

# Textos que contam como "célula vazia" — vão sempre para o fim, seja
# a ordem crescente ou decrescente.
_TEXTOS_VAZIOS = frozenset({"", "—", "-", "–"})

_RE_DATA_PT = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2})[:h](\d{2}))?"
)
_RE_DATA_ISO = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?"
)
_RE_NUMERO_PT = re.compile(
    r"^[-+]?\d{1,3}(\.\d{3})*(,\d+)?$|^[-+]?\d+(,\d+)?$"
)
_RE_PARTES = re.compile(r"(\d+)")


def pintar_fundo(widget, cor, pintados=None):
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

    `pintados` (27/09/2026, opcional): lista onde se acrescenta cada
    widget que foi de facto pintado. A `Tabela` usa-a para, ao
    reordenar, trocar a cor só a esses — e não a um botão que por
    acaso tenha a mesma cor da linha.
    """
    try:
        if widget.cget("fg_color") == "transparent":
            widget.configure(fg_color=cor)

            if pintados is not None:
                pintados.append(widget)
    except (AttributeError, ValueError, tkinter.TclError):
        pass

    for filho in widget.winfo_children():
        pintar_fundo(filho, cor, pintados)


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
        # Botões pintados com a cor da linha — a Tabela troca-lhes a
        # cor quando a linha muda de posição (ordenação, 27/09/2026).
        self._pintados = []

    def adicionar(self, widget):
        """Junta um botão à direita dos que já lá estão."""
        widget.pack(
            side="left", padx=(0 if self._primeiro else self._espaco, 0)
        )
        self._primeiro = False

        if self._cor_fundo:
            pintar_fundo(widget, self._cor_fundo, self._pintados)

        return widget

    def trocar_cor(self, cor):
        """Muda a cor de fundo da célula e dos botões que a herdaram.

        Chamada pela `Tabela` quando a ordenação muda a linha de
        posição e, com ela, o tom alternado.
        """
        self._cor_fundo = cor
        _configurar_fundo(self, cor)

        for widget in self._pintados:
            _configurar_fundo(widget, cor)


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

        # -- ordenação por clique no título (27/09/2026) --
        # Uma entrada por linha de dados, pela ordem em que foram
        # criadas (ver `nova_linha`). `_ordem` é None enquanto
        # ninguém clicou num título, ou (índice da coluna, decrescente).
        self._registos = []
        self._registo_atual = None
        self._ordem = None
        self._titulos = {}
        self._reordenacao_agendada = None

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
        criadas = []

        if not self._linhas_verticais:
            return criadas

        if grelha is None:
            grelha = self.grelha

        for indice in range(len(self._colunas) - 1):
            # height=1 pela mesma razão do `_fundo`: sem ela, cada
            # divisória vertical pedia 200px de altura e esticava a
            # fila toda.
            divisoria = ctk.CTkFrame(
                grelha,
                width=1,
                height=1,
                corner_radius=0,
                fg_color=tema.COR_BORDA,
            )
            divisoria.grid(row=fila, column=indice * 2 + 1, sticky="ns")
            criadas.append(divisoria)

        return criadas

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
            titulo = ctk.CTkLabel(
                self.grelha_cabecalho,
                text=coluna.titulo,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                fg_color=tema.CABECALHO_TABELA_FUNDO,
                font=ctk.CTkFont(size=10, weight="bold"),
                anchor=ancora,
            )
            titulo.grid(
                row=0,
                column=indice * 2,
                sticky=sticky or "ew",
                padx=self._espaco(indice),
                pady=_PADY_CABECALHO,
            )

            if self.coluna_ordenavel(indice):
                self._titulos[indice] = titulo
                titulo.configure(cursor="hand2")
                titulo.bind(
                    "<Button-1>",
                    lambda _evento, i=indice: self.ordenar_por(i),
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

        # A ordem escolhida (`_ordem`) NÃO se esquece: um ecrã que
        # recarrega a lista depois de gravar continua ordenado como o
        # utilizador o deixou. Só os registos das linhas antigas saem.
        self._registos = []
        self._registo_atual = None

        # As larguras copiadas para o cabeçalho eram as da lista
        # anterior; a que vem a seguir pode ter outras (a barra de
        # scroll aparece ou desaparece consoante o número de linhas).
        # Esquecê-las obriga o próximo alinhamento a medir tudo de
        # novo, em vez de confiar em valores já velhos.
        self._larguras_cabecalho.clear()
        self.after(60, self._alinhar_cabecalho)

    def nova_linha(self, fixa=False):
        """Abre uma linha nova e devolve a grelha, que é o master a
        usar para criar as células.

        O tom alternado e a divisória são contados aqui: quem usa a
        tabela não precisa de saber em que linha vai.

        Desde 21/09/2026 a fila tem SEMPRE um fundo próprio (branco
        ou o tom alternado) e a cor fica guardada em
        `_cor_fila_atual`, para o `colocar` poder pintar as células
        com ela.

        `fixa` (27/09/2026): a linha não entra na ordenação e fica
        sempre no fim — é para as linhas de TOTAL dos relatórios.
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

        fundo = self._fundo(self._fila_atual, self._cor_fila_atual)
        verticais = self._verticais(self._fila_atual)
        self._desenhadas += 1

        self._registo_atual = {
            "fila": self._fila_atual,
            "cor": self._cor_fila_atual,
            "fixa": fixa,
            "widgets": [fundo] + verticais,
            "fundo": fundo,
            "pintados": [],
            "acoes": [],
            "celulas": {},
            "chaves": {},
        }
        self._registos.append(self._registo_atual)

        # Lista a ser (re)desenhada com uma ordem já escolhida: a
        # reordenação corre UMA vez, quando o ecrã acabar de acrescentar
        # as linhas todas (`after_idle`), e não a cada linha.
        if self._ordem is not None and self._reordenacao_agendada is None:
            self._reordenacao_agendada = self.after_idle(
                self._reordenar_agendado
            )

        return self.grelha

    def colocar(self, linha, coluna, widget, esticar=None, chave=None):
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

        `chave` (27/09/2026, opcional): valor a usar na ordenação desta
        célula, quando o texto que se vê não serve (ex.: um crachá com
        ícone). Sem ela, ordena-se pelo texto da célula.
        """
        if esticar is None:
            esticar = _ALINHAMENTOS[self._colunas[coluna].alinhamento][1]

        widget.grid(
            row=self._fila_atual,
            column=coluna * 2,
            sticky=esticar,
            padx=self._espaco(coluna),
        )

        registo = self._registo_atual

        if registo is None:
            pintar_fundo(widget, self._cor_fila_atual)
            return widget

        pintar_fundo(widget, self._cor_fila_atual, registo["pintados"])
        registo["widgets"].append(widget)
        registo["celulas"].setdefault(coluna, widget)

        if isinstance(widget, _CelulaAcoes):
            registo["acoes"].append(widget)

        if chave is not None:
            registo["chaves"][coluna] = chave

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

    # -- ordenação ---------------------------------------------------

    def coluna_ordenavel(self, indice):
        """True se o clique no título da coluna `indice` ordena."""
        coluna = self._colunas[indice]

        if coluna.ordenavel is not None:
            return bool(coluna.ordenavel)

        return coluna.titulo.strip().upper() not in _TITULOS_SEM_ORDEM

    @property
    def ordem(self):
        """(índice da coluna, decrescente) ou None se não há ordem."""
        return self._ordem

    def ordenar_por(self, indice, decrescente=None):
        """Ordena as linhas pela coluna `indice`.

        É o que corre ao clicar num título. Sem `decrescente`, o
        primeiro clique numa coluna ordena de forma crescente e cada
        clique seguinte na MESMA coluna inverte (A→Z, Z→A, A→Z...).
        Mudar de coluna recomeça em crescente.
        """
        if not self.coluna_ordenavel(indice):
            return

        if decrescente is None:
            decrescente = (
                self._ordem is not None
                and self._ordem[0] == indice
                and not self._ordem[1]
            )

        self._ordem = (indice, bool(decrescente))
        self._atualizar_setas()
        self._reordenar()

    def _atualizar_setas(self):
        """Mostra ▲/▼ no título da coluna ativa e limpa as outras."""
        for indice, titulo in self._titulos.items():
            texto = self._colunas[indice].titulo

            if self._ordem is not None and self._ordem[0] == indice:
                texto += (
                    _SETA_DECRESCENTE if self._ordem[1] else _SETA_CRESCENTE
                )

            try:
                titulo.configure(text=texto)
            except tkinter.TclError:
                pass

    def _reordenar_agendado(self):
        self._reordenacao_agendada = None
        self._reordenar()

    def _reordenar(self):
        """Muda as linhas de sítio conforme `_ordem`.

        As linhas não são desenhadas de novo: cada widget muda só de
        fila na grelha (`grid_configure(row=...)`). As filas das
        divisórias horizontais ficam onde estão — são todas iguais,
        não é preciso mexer-lhes. As linhas `fixa` vão para o fim,
        pela ordem em que foram criadas.

        Como o tom alternado depende da POSIÇÃO, uma linha que muda de
        posição pode mudar de cor: troca-se a cor do fundo e das
        células que foram pintadas com ela (e só dessas).
        """
        if self._ordem is None or not self._registos:
            return

        indice, decrescente = self._ordem
        moveis = [r for r in self._registos if not r["fixa"]]
        fixas = [r for r in self._registos if r["fixa"]]

        com_valor = []
        vazias = []

        for registo in moveis:
            chave = self._chave_do_registo(registo, indice)

            if chave is None:
                vazias.append(registo)
            else:
                com_valor.append((chave, registo))

        # Crescente e decrescente só trocam a ordem das que têm valor;
        # as vazias vão sempre para o fim. O sort do Python é estável,
        # por isso valores iguais mantêm a ordem em que vieram.
        com_valor.sort(key=lambda par: par[0], reverse=decrescente)
        nova_ordem = [r for _, r in com_valor] + vazias + fixas

        filas = sorted(r["fila"] for r in self._registos)

        for posicao, (fila, registo) in enumerate(zip(filas, nova_ordem)):
            if registo["fila"] != fila:
                for widget in registo["widgets"]:
                    try:
                        widget.grid_configure(row=fila)
                    except tkinter.TclError:
                        pass

                registo["fila"] = fila

            if self._tom_alternado and posicao % 2 == 1:
                cor = tema.LINHA_ALTERNADA
            else:
                cor = tema.COR_FUNDO

            if cor != registo["cor"]:
                self._trocar_cor_registo(registo, cor)

        self._registos = nova_ordem

    @staticmethod
    def _trocar_cor_registo(registo, cor):
        registo["cor"] = cor
        _configurar_fundo(registo["fundo"], cor)

        for widget in registo["pintados"]:
            _configurar_fundo(widget, cor)

        for acoes in registo["acoes"]:
            acoes.trocar_cor(cor)

    @staticmethod
    def _chave_do_registo(registo, indice):
        if indice in registo["chaves"]:
            valor = registo["chaves"][indice]
            return chave_ordenacao(valor)

        widget = registo["celulas"].get(indice)

        if widget is None or isinstance(widget, _CelulaAcoes):
            return None

        return chave_ordenacao(texto_do_widget(widget))

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


def _configurar_fundo(widget, cor):
    """`configure(fg_color=cor)` que não rebenta num widget já
    destruído (o ecrã pode ter fechado entretanto)."""
    try:
        widget.configure(fg_color=cor)
    except (AttributeError, ValueError, tkinter.TclError):
        pass


def texto_do_widget(widget):
    """Primeiro texto não vazio de um widget ou dos seus filhos.

    É o que a `Tabela` usa para ordenar: numa célula simples é o
    texto da etiqueta; num bloco (frame com um crachá e um texto ao
    lado, por exemplo) é o primeiro texto que aparecer.
    """
    try:
        texto = widget.cget("text")
    except (AttributeError, ValueError, tkinter.TclError):
        texto = None

    if isinstance(texto, str) and texto.strip():
        return texto

    for filho in widget.winfo_children():
        texto = texto_do_widget(filho)

        if texto:
            return texto

    return ""


def _sem_acentos(texto):
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def chave_ordenacao(valor):
    """Chave de ordenação de uma célula — None se estiver vazia.

    Um clique no título ordena "por ordem alfabética", mas a ordem
    alfabética pura estraga três casos que aparecem em quase todas as
    tabelas do sistema, e por isso o texto é lido antes de comparar:

    - DATAS (dd/mm/aaaa, com ou sem hora): "02/01/2027" viria antes
      de "15/12/2026" por ordem alfabética. Compara-se (ano, mês,
      dia, hora, minuto).
    - VALORES ("1.234,56 €", "45,00 €", "12"): "9,00 €" viria depois
      de "10,00 €". Compara-se o número.
    - IDs e textos com números ("PRO-2", "PRO-10"): compara-se a parte
      numérica como número ("ordem natural"), e o resto sem acentos
      nem maiúsculas ("Álvaro" ao pé de "Alberto", não no fim).

    O primeiro elemento da chave (0 número, 1 data, 2 texto) só serve
    para numa coluna mista nunca se compararem tipos diferentes.

    Também aceita valores que não são texto (a `chave=` do
    `Tabela.colocar`): números, datas e Decimals comparam-se pelo
    próprio valor.
    """
    if valor is None:
        return None

    if isinstance(valor, bool):
        return (0, decimal.Decimal(int(valor)))

    if isinstance(valor, (int, float, decimal.Decimal)):
        return (0, decimal.Decimal(str(valor)))

    if isinstance(valor, datetime.datetime):
        return (1, valor.timetuple()[:5])

    if isinstance(valor, datetime.date):
        return (1, (valor.year, valor.month, valor.day, 0, 0))

    texto = str(valor).strip()

    if texto in _TEXTOS_VAZIOS:
        return None

    data = _RE_DATA_PT.match(texto)

    if data:
        dia, mes, ano, hora, minuto = data.groups()
        return (
            1,
            (int(ano), int(mes), int(dia), int(hora or 0), int(minuto or 0)),
        )

    data = _RE_DATA_ISO.match(texto)

    if data:
        ano, mes, dia, hora, minuto = data.groups()
        return (
            1,
            (int(ano), int(mes), int(dia), int(hora or 0), int(minuto or 0)),
        )

    numero = texto.replace("€", "").replace("%", "")
    numero = numero.replace("\u00a0", "").replace(" ", "")

    if numero and _RE_NUMERO_PT.match(numero):
        try:
            return (
                0,
                decimal.Decimal(numero.replace(".", "").replace(",", ".")),
            )
        except decimal.InvalidOperation:
            pass

    normalizado = _sem_acentos(texto).casefold()
    partes = tuple(
        (0, int(parte), "") if parte.isdigit() else (1, 0, parte)
        for parte in _RE_PARTES.split(normalizado)
        if parte
    )

    return (2, partes)


# =====================================================================
# SELETOR — o CTkOptionMenu com painel de scroll e pesquisa
#
# Decisão de arquitetura do aluno (21/09/2026): daqui para a frente os
# ecrãs deixam de instanciar widgets do CustomTkinter diretamente e
# passam por uma classe daqui, que HERDA a do CustomTkinter. Foi o que
# faltou no caso do `CTkOptionMenu`: como cada ecrã o instanciava à
# sua maneira, não havia um sítio só onde mudar — ao contrário da
# `Tabela`, onde uma correção chegou a todos os ecrãs de uma vez.
# =====================================================================

# A partir de quantos itens é que o menu nativo deixa de servir. Uma
# lista de meses, de estados civis ou de tipos de cama continua no
# menu de sempre: é mais rápido, é o que o utilizador já conhece, e
# trocá-lo não traria ganho nenhum.
_LIMITE_MENU_NATIVO = 8

# Linhas visíveis no painel antes de ser preciso rolar.
_LINHAS_VISIVEIS = 6

_ALTURA_OPCAO = 30
_LARGURA_MINIMA_PAINEL = 280

# Teto de opções desenhadas de uma vez. Cada linha é um CTkButton, e
# criar centenas deles demora o suficiente para se notar ao abrir.
# Com o teto, o painel abre sempre instantâneo e o rodapé diz que há
# mais — que é também a melhor deixa para usar a pesquisa.
_MAX_OPCOES_DESENHADAS = 60

# Quantas vezes se vai ver se o menu nativo já fechou, de 200 em 200
# ms (ver `_vigiar_menu_nativo`). Sessenta segundos é folgado para
# alguém escolher uma opção; passado isso desiste-se, e a captura
# acaba por ser reposta na interação seguinte.
_TENTATIVAS_MENU_NATIVO = 300


class Seletor(ctk.CTkOptionMenu):
    """`CTkOptionMenu` que troca o menu nativo por um painel com
    scroll e pesquisa quando a lista é grande.

    PORQUÊ: o dropdown do `CTkOptionMenu` é um `DropdownMenu`, que
    herda de `tkinter.Menu` — um menu nativo do sistema operativo.
    Menus nativos não têm barra de scroll interna nem se deixam
    limitar a um número de linhas, e com 100 clientes a lista passa a
    ser impossível de navegar (problema levantado pelo aluno em
    21/09/2026, a partir do campo Cliente da Nova Reserva Airbnb).

    COMO: herda mesmo a classe e substitui UM método —
    `_open_dropdown_menu`, cujo trabalho inteiro é mandar abrir o
    menu. Tudo o resto vem de graça e continua a ser o do
    CustomTkinter: o aspeto, a geometria, a escala, e a API
    (`get`, `set`, `configure(values=...)`, `cget("values")`). Por
    isso entra no lugar de um `CTkOptionMenu` sem mais nenhuma
    alteração no código de quem o usa, e qualquer `isinstance` que
    já exista sobre `CTkOptionMenu` continua a dar verdadeiro.

    Listas curtas continuam no menu nativo. A decisão é tomada em
    execução, pelo comprimento da lista, para os ecrãs não terem de
    classificar campo a campo o que merece o painel novo.

    A LISTA NUNCA É ALTERADA. A pesquisa filtra apenas o que se
    desenha; `self._values` continua a ser a lista original, pela
    ordem original. Isto não é um detalhe de estilo: o código dos
    ecrãs faz `combo.cget("values").index(combo.get())` para voltar
    do texto ao registo real (o cliente, o responsável, a unidade).
    Se a lista fosse substituída pela filtrada, esse `.index()`
    passaria a devolver o registo errado em silêncio — uma reserva
    atribuída a outro cliente, sem erro nenhum no ecrã.

    A escolha é entregue ao `_dropdown_callback` da classe base, o
    mesmo que o menu nativo usa — atualiza o valor, a etiqueta, a
    variável ligada e chama o `command`. Não há aqui uma segunda
    cópia dessa lógica que pudesse divergir.

    Uso — igual ao `CTkOptionMenu`, porque é um:

        self.combo_cliente = componentes.Seletor(
            bloco, values=["—"], width=1, command=self._ao_escolher
        )
    """

    def __init__(
        self,
        master,
        *args,
        limite=_LIMITE_MENU_NATIVO,
        linhas_visiveis=_LINHAS_VISIVEIS,
        pesquisa=True,
        **kwargs,
    ):
        super().__init__(master, *args, **kwargs)

        self._limite = limite
        self._linhas_visiveis = linhas_visiveis
        self._com_pesquisa = pesquisa
        self._painel = None
        self._campo_pesquisa = None
        self._lista_painel = None
        self._rodape_painel = None
        self._grab_anterior = None

    # -- decisão -----------------------------------------------------

    def _open_dropdown_menu(self):
        """Único método da classe base que é substituído.

        O `hasattr` no `super()` não é preciso aqui — este método
        existe porque o estamos a redefinir — mas o caminho da lista
        curta chama o original, e é esse que depende da biblioteca.
        Se uma versão futura do CustomTkinter lhe mudar o nome, é
        este método que deixa de ser chamado: o widget volta a
        comportar-se como um `CTkOptionMenu` normal, com o menu
        nativo, em vez de ficar um campo que não abre.
        """
        if len(self._values) <= self._limite:
            anterior = self.grab_current()
            super()._open_dropdown_menu()
            self._vigiar_menu_nativo(anterior)
            return

        self._alternar_painel()

    def _vigiar_menu_nativo(self, anterior, apareceu=False, tentativas=0):
        """Devolve a captura de eventos ao modal depois de o menu
        nativo fechar.

        BUG ANTIGO, NÃO INTRODUZIDO AQUI (medido em 21/09/2026 com um
        `CTkOptionMenu` original, sem nada deste ficheiro): ao abrir,
        o menu nativo toma a captura de eventos; ao fechar, NÃO a
        devolve — fica ela com o menu já fechado. Consequência real:
        num modal, basta abrir um dropdown uma vez para o modal
        deixar de bloquear a janela por trás, e o utilizador passa a
        poder clicar no que devia estar bloqueado, sem aviso nenhum.

        Como todos os seletores do sistema passam a ser desta classe,
        este é o sítio onde isso se corrige de uma vez.

        O `apareceu` existe por causa do tempo: logo a seguir a pedir
        a abertura, o menu ainda não está no ecrã, e sem esta
        bandeira a primeira verificação concluía "já fechou" e tirava
        a captura ao menu que estava mesmo a abrir.
        """
        if anterior is None:
            return

        try:
            mapeado = bool(self._dropdown_menu.winfo_ismapped())
        except tkinter.TclError:
            return

        if mapeado:
            apareceu = True
        elif apareceu:
            try:
                anterior.grab_set()
            except tkinter.TclError:
                pass

            return

        if tentativas >= _TENTATIVAS_MENU_NATIVO:
            return

        try:
            self.after(
                200,
                lambda: self._vigiar_menu_nativo(
                    anterior, apareceu, tentativas + 1
                ),
            )
        except tkinter.TclError:
            pass

    # -- painel ------------------------------------------------------

    def _alternar_painel(self):
        """Segundo clique no campo fecha o painel, em vez de abrir
        outro por cima.
        """
        if self._painel is not None:
            self._fechar_painel()
            return

        self._abrir_painel()

    def _abrir_painel(self):
        # Quem tem a captura de eventos neste momento — quase sempre
        # o modal de onde este seletor foi aberto (a Nova Reserva
        # Airbnb, por exemplo, chama `grab_set` através do
        # `colocar_no_topo`). Guardar isto agora é o que permite
        # devolver-lhe a captura quando o painel fechar; sem isso, o
        # modal por baixo ficava a não responder a nada.
        self._grab_anterior = self.grab_current()

        painel = ctk.CTkToplevel(self)
        self._painel = painel

        # Sem barra de título nem moldura do sistema: isto é um
        # painel colado ao campo, não uma janela.
        painel.overrideredirect(True)
        painel.configure(fg_color=tema.COR_BORDA)

        moldura = ctk.CTkFrame(
            painel,
            corner_radius=tema.RAIO_CARTAO,
            fg_color=tema.COR_FUNDO,
            border_width=0,
        )
        moldura.pack(fill="both", expand=True, padx=1, pady=1)

        if self._com_pesquisa:
            self._campo_pesquisa = ctk.CTkEntry(
                moldura,
                corner_radius=tema.RAIO_CAMPO,
                placeholder_text="Escrever para filtrar...",
                height=30,
            )
            self._campo_pesquisa.pack(fill="x", padx=8, pady=(8, 4))
            # KeyRelease e não FocusOut: gravar ou reagir no
            # `<FocusOut>` de um campo é fonte de ciclos infinitos
            # neste projeto (lição do `gui_configuracoes.py`,
            # `_controlo_numerico`).
            self._campo_pesquisa.bind(
                "<KeyRelease>", self._ao_filtrar, add=True
            )

        self._lista_painel = ctk.CTkScrollableFrame(
            moldura,
            fg_color="transparent",
            height=self._linhas_visiveis * _ALTURA_OPCAO,
        )
        self._lista_painel.pack(fill="both", expand=True, padx=4)

        self._rodape_painel = ctk.CTkLabel(
            moldura,
            text="",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        )
        self._rodape_painel.pack(fill="x", padx=12, pady=(2, 8))

        self._desenhar_opcoes()
        self._colocar_painel(painel)

        # A captura passa para o painel. É ela que faz os cliques
        # fora chegarem cá (ver `_ao_clicar`) e que deixa o campo de
        # pesquisa receber o que se escreve mesmo com o modal de trás
        # a ter pedido a captura antes.
        painel.bind("<Button-1>", self._ao_clicar, add=True)
        painel.bind("<Escape>", self._fechar_painel, add=True)

        # Rodar a roda do rato FORA do painel fecha-o. Sem isto, um
        # seletor dentro de um formulário com scroll (o
        # `_FormularioCliente` e os cartões dos contratos vivem todos
        # dentro de um `CTkScrollableFrame`) deixava o painel
        # pendurado no sítio antigo enquanto o campo lhe fugia por
        # baixo — medido em 21/09/2026: o campo desceu 360px e o
        # painel não se mexeu um pixel. Rodar DENTRO do painel
        # continua a rolar a lista, como deve ser.
        #
        # `<MouseWheel>` cobre Windows e macOS; `<Button-4>` e
        # `<Button-5>` são o equivalente em Linux.
        for evento_roda in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            painel.bind(evento_roda, self._ao_rodar, add=True)

        painel.after(10, self._capturar)

    def _capturar(self):
        painel = self._painel

        if painel is None:
            return

        try:
            painel.grab_set()
        except tkinter.TclError:
            return

        # Alguém dentro do painel tem de ficar com o foco do teclado,
        # senão o Escape não chega cá: a caixa de pesquisa quando
        # existe, o próprio painel quando não existe.
        if self._campo_pesquisa is not None:
            self._campo_pesquisa.focus_set()
        else:
            painel.focus_set()

    def _colocar_painel(self, painel):
        """Coloca o painel por baixo do campo, ou por cima se não
        houver espaço até ao fundo do ecrã.

        `tkinter.Toplevel.geometry` e não `painel.geometry`: o
        `CTkToplevel` volta a multiplicar o valor pela escala da
        janela, e estes números já vêm em pixéis reais
        (`winfo_rootx`, `winfo_width`). É a lição de geometria de
        16/09/2026 — com o `.geometry()` do CustomTkinter, o painel
        crescia a cada abertura.
        """
        painel.update_idletasks()

        largura = max(self.winfo_width(), _LARGURA_MINIMA_PAINEL)
        altura = painel.winfo_reqheight()

        x = self.winfo_rootx()
        abaixo = self.winfo_rooty() + self.winfo_height() + 2

        if abaixo + altura > painel.winfo_screenheight():
            y = max(self.winfo_rooty() - altura - 2, 0)
        else:
            y = abaixo

        tkinter.Toplevel.geometry(painel, f"{largura}x{altura}+{x}+{y}")
        painel.lift()

    # -- conteúdo ----------------------------------------------------

    def _termo(self):
        if self._campo_pesquisa is None:
            return ""

        return self._campo_pesquisa.get().strip().lower()

    def _desenhar_opcoes(self):
        """Desenha as opções que passam o filtro.

        Lê `self._values` e não lhe toca — ver a nota sobre o
        `.index()` na docstring da classe.
        """
        if self._lista_painel is None:
            return

        for widget in self._lista_painel.winfo_children():
            widget.destroy()

        termo = self._termo()
        correspondem = [v for v in self._values if termo in v.lower()]
        desenhadas = correspondem[:_MAX_OPCOES_DESENHADAS]

        for valor in desenhadas:
            escolhido = valor == self._current_value

            ctk.CTkButton(
                self._lista_painel,
                text=valor,
                anchor="w",
                height=_ALTURA_OPCAO - 4,
                corner_radius=tema.RAIO_BOTAO,
                fg_color=(tema.ID_CHIP_FUNDO if escolhido else "transparent"),
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                font=ctk.CTkFont(size=12),
                command=lambda v=valor: self._escolher(v),
            ).pack(fill="x", pady=1)

        if not correspondem:
            ctk.CTkLabel(
                self._lista_painel,
                text="Sem resultados.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            ).pack(pady=14)

        self._atualizar_rodape(len(correspondem), len(desenhadas))

    def _atualizar_rodape(self, encontradas, desenhadas):
        if self._rodape_painel is None:
            return

        total = len(self._values)

        if desenhadas < encontradas:
            texto = (
                f"a mostrar {desenhadas} de {encontradas} — "
                f"filtra para ver o resto"
            )
        elif self._termo():
            texto = f"{encontradas} de {total}"
        else:
            texto = f"{total} registos"

        self._rodape_painel.configure(text=texto)

    def _ao_filtrar(self, _evento=None):
        self._desenhar_opcoes()

    # -- fecho -------------------------------------------------------

    def _ao_clicar(self, evento):
        """Fecha o painel quando se clica fora dele.

        LIÇÃO (21/09/2026, bug apanhado pelo aluno — o painel abria e
        não havia maneira de sair sem escolher uma opção): com a
        captura de eventos no painel, um clique em qualquer outro
        sítio da aplicação É entregue ao painel, mas chega
        disfarçado. O `evento.widget` aponta para o próprio painel (a
        janela que tem a captura) e não para o sítio onde se clicou,
        por isso perguntar "este widget pertence ao painel?"
        respondia sempre que sim, e o painel nunca fechava. O
        `evento.x`/`evento.y` também não servem: vêm relativos a essa
        janela e caem dentro dos limites dela.

        O que não mente são as coordenadas absolutas do ecrã
        (`x_root`/`y_root`). Comparadas com a posição e o tamanho
        reais do painel, dizem sem ambiguidade se o clique caiu cá
        dentro ou lá fora, independentemente de a quem o evento foi
        entregue.
        """
        if self._fora_do_painel(evento):
            self._fechar_painel()

    def _ao_rodar(self, evento):
        """Fecha o painel se a roda do rato for usada fora dele.

        Mesma pergunta do `_ao_clicar`, mesma resposta: o painel é
        uma janela independente e não acompanha o formulário quando
        este rola. Rodar dentro do painel rola a lista e não fecha
        nada.
        """
        if self._fora_do_painel(evento):
            self._fechar_painel()

    def _fora_do_painel(self, evento):
        """Diz se um evento de rato caiu fora do painel."""
        painel = self._painel

        if painel is None:
            return False

        esquerda = painel.winfo_rootx()
        topo = painel.winfo_rooty()

        return (
            evento.x_root < esquerda
            or evento.y_root < topo
            or evento.x_root >= esquerda + painel.winfo_width()
            or evento.y_root >= topo + painel.winfo_height()
        )

    def _escolher(self, valor):
        self._fechar_painel()
        # O mesmo caminho que o menu nativo usa: atualiza valor,
        # etiqueta, variável ligada e chama o `command`.
        self._dropdown_callback(valor)

    def _fechar_painel(self, _evento=None):
        painel = self._painel

        if painel is None:
            return

        self._painel = None
        self._campo_pesquisa = None
        self._lista_painel = None
        self._rodape_painel = None

        try:
            painel.grab_release()
        except tkinter.TclError:
            pass

        painel.destroy()

        # Devolver a captura a quem a tinha. O Tk não a repõe
        # sozinho quando a janela que a tinha desaparece: sem isto, o
        # modal de onde o seletor foi aberto ficava sem captura e,
        # pior, a janela principal voltava a aceitar cliques por trás
        # de um modal que era suposto bloqueá-la.
        if self._grab_anterior is not None:
            try:
                self._grab_anterior.grab_set()
            except tkinter.TclError:
                pass

        self._grab_anterior = None

    def destroy(self):
        """Fecha o painel se o próprio seletor for destruído.

        Sem isto, fechar o modal com o painel aberto deixava uma
        janela sem dono no ecrã e a captura de eventos por devolver.
        """
        self._fechar_painel()
        super().destroy()

# =====================================================================
# BLOCO DE TERMO LEGAL (v1.6.0)
#
# O quadro que mostra um documento legal e recolhe a confirmação de
# quem o leu. Vive aqui, e não em cada ecrã, porque aparece em dois
# sítios diferentes — na atribuição da credencial e no arranque de
# quem ainda não aceitou a versão em vigor — e vai aparecer num
# terceiro quando a ficha do cliente passar a registar a informação
# prestada ao hóspede.
#
# Não sabe nada de base de dados nem de regras: recebe o texto já
# resolvido pelo `termos.verificar` e devolve, quando perguntado, se
# a caixa está marcada. Quem decide o que fazer com isso é o ecrã.
#
# As duas cores do aviso não estão no `tema.py` porque são as
# primeiras do género no sistema. Se aparecer uma segunda utilização,
# mudam para lá — não vale a pena inventar já uma entrada no tema
# para um sítio só.
# =====================================================================


_ALTURA_TEXTO_TERMO = 150


class BlocoTermo(ctk.CTkFrame):
    """Mostra um documento legal e a caixa de confirmação.

    Parâmetros:

      titulo          - o cabeçalho pequeno em maiúsculas
      texto           - o corpo do documento (string)
      versao          - a versão em vigor, mostrada no rodapé
      rotulo          - o que fica ao lado da caixa de marcar
      versao_anterior - a versão que a pessoa já tinha aceitado,
                        ou None se nunca aceitou nenhuma
      data_anterior   - a data dessa aceitação, ou None
      aviso           - texto da faixa âmbar no topo; None esconde-a
      ao_mudar        - chamado sem argumentos sempre que a caixa
                        muda de estado

    A caixa de texto é um `CTkTextbox` desativado: rola, seleciona-se
    para copiar, mas não se edita. Um `CTkLabel` com o texto todo não
    servia — crescia sem limite e empurrava os botões para fora do
    ecrã num documento comprido.
    """

    def __init__(
        self,
        master,
        titulo,
        texto,
        versao,
        rotulo,
        versao_anterior=None,
        data_anterior=None,
        aviso=None,
        ao_mudar=None,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=8,
            **kwargs,
        )

        self._ao_mudar = ao_mudar
        self.versao = versao

        if aviso:
            faixa = ctk.CTkLabel(
                self,
                text=aviso,
                text_color=tema.TEXTO_AVISO,
                fg_color=tema.AMARELO_AVISO,
                corner_radius=6,
                font=ctk.CTkFont(size=11),
                anchor="w",
                justify="left",
                wraplength=380,
            )
            faixa.pack(fill="x", padx=12, pady=(12, 0))

        ctk.CTkLabel(
            self,
            text=titulo.upper(),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 4))

        self.caixa_texto = ctk.CTkTextbox(
            self,
            height=_ALTURA_TEXTO_TERMO,
            corner_radius=6,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
            font=ctk.CTkFont(size=12),
            wrap="word",
        )
        self.caixa_texto.pack(fill="x", padx=12)
        self.caixa_texto.insert("1.0", texto)
        self.caixa_texto.configure(state="disabled")

        self.aceite = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(
            self,
            text=rotulo,
            variable=self.aceite,
            command=self._mudou,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
        ).pack(anchor="w", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            self,
            text=self._rodape(versao, versao_anterior, data_anterior),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(6, 12))

    @staticmethod
    def _rodape(versao, versao_anterior, data_anterior):
        """A linha pequena do fundo.

        Quem nunca aceitou vê só a versão em vigor. Quem já aceitou
        uma anterior vê as duas, para perceber porque é que o ecrã
        lhe apareceu outra vez.
        """
        if not versao_anterior:
            return f"Versão {versao}"

        data = str(data_anterior)[:10] if data_anterior else "—"

        return (
            f"Aceitou a versão {versao_anterior} em {data} · "
            f"em vigor agora: {versao}"
        )

    def _mudou(self):
        if self._ao_mudar is not None:
            self._ao_mudar()

    def esta_aceite(self):
        """True se a caixa estiver marcada."""
        return bool(self.aceite.get())

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


# Altura da barra de título do Windows, em pixels a 100%. O
# `.geometry()` mede só o interior da janela; a moldura fica por
# cima e também tem de caber no ecrã.
_ALTURA_MOLDURA = 32

# Fora do Windows (Linux, testes) não há API para a área útil:
# reserva-se esta altura no fundo do ecrã para a barra de tarefas.
_ALTURA_BARRA_TAREFAS = 48

# Constante da API do Windows: "devolve a área útil do ecrã".
_SPI_GETWORKAREA = 0x0030


def escala(janela):
    """Fator de escala da janela (DPI do Windows x escala do CTk).

    O `.geometry()` do CustomTkinter recebe tamanhos LÓGICOS e
    multiplica-os por este fator; o `winfo_*` e o ecrã estão em
    pixels REAIS. As contas de posição usam sempre os reais.
    """
    return ctk.ScalingTracker.get_window_scaling(janela)


def area_util_ecra(janela):
    """(x, y, largura, altura) da área útil do ecrã, em pixels reais.

    "Útil" = sem a barra de tarefas. No Windows pergunta-se ao
    sistema (a barra pode estar em baixo, em cima ou de lado).
    """
    if sys.platform == "win32":
        retangulo = wintypes.RECT()
        ok = ctypes.windll.user32.SystemParametersInfoW(
            _SPI_GETWORKAREA, 0, ctypes.byref(retangulo), 0
        )

        if ok:
            return (
                retangulo.left,
                retangulo.top,
                retangulo.right - retangulo.left,
                retangulo.bottom - retangulo.top,
            )

    return (
        0,
        0,
        janela.winfo_screenwidth(),
        janela.winfo_screenheight() - _ALTURA_BARRA_TAREFAS,
    )


def _aplicar_geometria(janela, x, y, largura, altura):
    """Encaixa o retângulo na área útil e aplica-o à janela.

    Se não couber, encolhe; se sair por um lado, é empurrado para
    dentro. Tudo em pixels reais — por isso usa a versão de base do
    Tkinter (`Wm.wm_geometry`): o `.geometry()` do CTk voltava a
    multiplicar pela escala (lição do ficheiro 11).
    """
    area_x, area_y, area_l, area_a = area_util_ecra(janela)
    area_a -= round(_ALTURA_MOLDURA * escala(janela))

    largura = min(largura, area_l)
    altura = min(altura, area_a)
    x = max(area_x, min(x, area_x + area_l - largura))
    y = max(area_y, min(y, area_y + area_a - altura))

    tkinter.Wm.wm_geometry(janela, f"{largura}x{altura}+{x}+{y}")


def centrar_no_ecra(janela, largura, altura):
    """Dá à janela o tamanho LÓGICO pedido, centrada no ecrã.

    Usado pela janela principal e pelos modais que abrem antes dela
    (login, termo). Garante sempre que a janela cabe no ecrã.
    """
    fator = escala(janela)
    largura = round(largura * fator)
    altura = round(altura * fator)

    area_x, area_y, area_l, area_a = area_util_ecra(janela)
    x = area_x + (area_l - largura) // 2
    y = area_y + (area_a - altura) // 2

    _aplicar_geometria(janela, x, y, largura, altura)
    setattr(janela, "_posicionada", True)


def tamanho_minimo(janela, largura, altura):
    """Devolve (largura, altura) mínimas LÓGICAS que cabem no ecrã.

    Um `minsize` maior do que o ecrã obriga o Windows a abrir a
    janela com parte dela fora — acontecia com 950x620 num portátil
    de 1366x768 a 125%.
    """
    fator = escala(janela)
    _, _, area_l, area_a = area_util_ecra(janela)
    area_a -= round(_ALTURA_MOLDURA * fator)

    return (
        min(largura, int(area_l / fator)),
        min(altura, int(area_a / fator)),
    )


def centrar_sobre(janela, master, largura, altura):
    """Centra um popup (CTkToplevel) sobre a janela que o abriu.

    Sem isto o Tk coloca o popup no canto superior esquerdo do ecrã,
    longe do botão que acabou de ser clicado.

    `largura`/`altura` em unidades LÓGICAS (as mesmas do
    `.geometry()`). v1.6.0: passam para pixels reais antes das
    contas — antes, com escala a 125%/150%, o popup ficava
    descentrado — e a janela nunca sai da área útil do ecrã.
    """
    master.update_idletasks()
    fator = escala(janela)
    largura = round(largura * fator)
    altura = round(altura * fator)

    x = master.winfo_rootx() + (master.winfo_width() - largura) // 2
    y = master.winfo_rooty() + (master.winfo_height() - altura) // 2

    _aplicar_geometria(janela, x, y, largura, altura)
    setattr(janela, "_posicionada", True)


def enquadrar(janela):
    """Rede de segurança: garante que o popup está todo no ecrã.

    Chamada pelo `colocar_no_topo`, já com a janela mapeada. Se
    ninguém a posicionou (`centrar_sobre`/`centrar_no_ecra` marcam
    `_posicionada`), centra-a sobre a janela principal; em qualquer
    caso encaixa-a na área útil. Mantém o tamanho que a janela tem.
    """
    janela.update_idletasks()
    medida = re.match(
        r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", tkinter.Wm.wm_geometry(janela)
    )

    if medida is None:
        return

    largura, altura, x, y = (int(valor) for valor in medida.groups())

    if largura <= 1 or altura <= 1:
        return

    if not getattr(janela, "_posicionada", False):
        principal = janela.master.winfo_toplevel()
        x = principal.winfo_rootx() + (principal.winfo_width() - largura) // 2
        y = principal.winfo_rooty() + (principal.winfo_height() - altura) // 2

    _aplicar_geometria(janela, x, y, largura, altura)


def colocar_no_topo(janela):
    """Traz um popup (CTkToplevel) para a frente da janela principal.

    Sem isto, o Windows (e alguns outros gestores de janelas) por
    vezes abre o popup por baixo da janela principal, escondido.
    `after(10, ...)` dá tempo ao Tk para mapear a janela antes de
    `grab_set()` — chamado logo a seguir ao `super().__init__(...)`,
    `grab_set()` falha com "grab failed: window not viewable" em
    alguns sistemas.

    v1.6.0: antes de a trazer para a frente, `enquadrar` põe-na
    dentro do ecrã — é isto que cobre, de uma vez, todos os modais
    que só fazem `.geometry("LxA")` sem posição.
    """

    def _trazer(tentativas=20):
        if not janela.winfo_exists():
            return

        # Ainda não está no ecrã: sem isto o tamanho lido é 1x1 e o
        # `grab_set()` falha. Tenta de novo daqui a 10ms.
        if not janela.winfo_viewable() and tentativas > 0:
            janela.after(10, _trazer, tentativas - 1)
            return

        enquadrar(janela)
        janela.lift()
        janela.focus_force()
        janela.grab_set()

    janela.after(10, _trazer)


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


def cancelar_agendamentos(janela):
    """Cancela os `after(...)` pendentes antes de destruir a janela.

    <<< NOVO v1.6.0 >>>

    Resolve as mensagens que apareciam no terminal ao fazer logoff:

        invalid command name "...update"
        invalid command name "...check_dpi_scaling"
        bgerror failed to handle background error

    Quem as provoca é o próprio CustomTkinter. O `ScalingTracker`
    reagenda-se sozinho de 100 em 100 ms (`scaling_tracker.py`,
    `add_widget` e `check_dpi_scaling`), e escolhe para isso uma
    janela qualquer das que estão registadas. Quando essa janela é
    destruída, o agendamento que já estava marcado dispara contra um
    interpretador Tcl que já não existe — e o Tcl queixa-se. A
    segunda mensagem é o próprio tratador de erros a falhar, pela
    mesma razão.

    Não é possível evitar isto do lado de fora sem cancelar os
    agendamentos primeiro: quem os criou foi a biblioteca, na janela
    que estamos prestes a fechar.

    O `after info` é por interpretador, não por widget, por isso pode
    ser chamado com qualquer widget da janela — o ecrã, o frame, a
    própria `Aplicacao`. Devolve quantos cancelou, o que dá jeito
    para confirmar em depuração.

    Chamar isto só faz sentido imediatamente antes de um `destroy()`
    definitivo. Num sítio qualquer, matava temporizadores que o
    sistema ainda precisa.
    """
    try:
        pendentes = janela.tk.eval("after info").split()
    except tkinter.TclError:
        return 0

    for identificador in pendentes:
        try:
            janela.after_cancel(identificador)
        except (tkinter.TclError, ValueError):
            pass

    return len(pendentes)


# =====================================================================
# VÍNCULOS POR ID (27/09/2026, v1.6.0)
#
# Padrão nascido em Propriedades (clicar no ID da propriedade abre as
# unidades dela) e alargado ao resto do sistema: o crachá de ID de
# uma linha é um atalho para o que está ligado a esse registo.
# `ChipId` é o crachá; `ListaVinculadaModal` e `FichaModal` são as
# duas formas de mostrar o que está do outro lado (uma lista de
# registos ligados, ou os campos de um registo só) — só leitura.
# =====================================================================


def formatar_data(valor):
    """Data em dd/mm/aaaa, ou "—" quando não há data."""
    return valor.strftime("%d/%m/%Y") if valor else "—"


class ChipId(ctk.CTkLabel):
    """Crachá de ID de uma linha de tabela, opcionalmente clicável.

    Com `ao_clicar` (função sem argumentos) fica com cursor de mão e
    reage ao clique simples; sem ele é só o crachá, com o aspeto de
    sempre. `inativo` só muda a cor do texto — quem não quer o
    clique num registo inativo passa `ao_clicar=None`.

    `cor_fundo` só existe para as unidades inativas, que usam o
    fundo cinzento em vez do azul-claro.
    """

    def __init__(
        self,
        master,
        texto,
        ao_clicar=None,
        inativo=False,
        largura=70,
        tamanho_fonte=11,
        cor_fundo=None,
    ):
        clicavel = ao_clicar is not None
        super().__init__(
            master,
            text=texto,
            text_color=(
                tema.TEXTO_INDISPONIVEL if inativo else tema.AZUL_PRINCIPAL
            ),
            fg_color=cor_fundo if cor_fundo else tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=tamanho_fonte, weight="bold"),
            width=largura,
            anchor="w",
            cursor="hand2" if clicavel else "",
        )
        self.clicavel = clicavel
        if ao_clicar is not None:
            self.bind("<Button-1>", lambda evento, f=ao_clicar: f())


class _ModalVinculo(ctk.CTkToplevel):
    """Base das duas janelas de vínculo: título, subtítulo, corpo e
    botão "Fechar". As subclasses só enchem `self.corpo`.
    """

    def __init__(self, master, titulo, subtitulo, largura, altura):
        super().__init__(master)
        self.title(titulo)
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master.winfo_toplevel())

        ctk.CTkLabel(
            self,
            text=subtitulo.upper(),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 0))
        ctk.CTkLabel(
            self,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(0, 10))

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
        ).pack(side="bottom", anchor="e", padx=20, pady=(8, 16))

        self.corpo = ctk.CTkFrame(self, fg_color="transparent")
        self.corpo.pack(fill="both", expand=True, padx=20)

        centrar_sobre(self, master.winfo_toplevel(), largura, altura)
        colocar_no_topo(self)


class ListaVinculadaModal(_ModalVinculo):
    """Lista (só leitura) dos registos ligados a um ID — ex.: os
    contratos de um cliente, os movimentos de um produto.

    'colunas': tuplo de `Coluna`, a primeira é sempre o ID.
    'linhas': lista de tuplos de texto, um valor por coluna. O
    primeiro valor é desenhado como `ChipId`, os outros como texto.
    """

    def __init__(
        self,
        master,
        titulo,
        subtitulo,
        colunas,
        linhas,
        mensagem_vazia="Sem registos ligados.",
        largura=760,
        altura=480,
    ):
        super().__init__(master, titulo, subtitulo, largura, altura)

        self.tabela = Tabela(
            self.corpo,
            colunas=colunas,
            altura_linha=40,
            mensagem_vazia=mensagem_vazia,
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True)

        for valores in linhas:
            linha = self.tabela.nova_linha()
            self.tabela.colocar(
                linha,
                0,
                ChipId(linha, valores[0], largura=colunas[0].minimo - 16),
                esticar="w",
            )
            for indice, valor in enumerate(valores[1:], start=1):
                self.tabela.colocar(
                    linha,
                    indice,
                    ctk.CTkLabel(
                        linha,
                        text=valor,
                        text_color=tema.COR_TEXTO,
                        font=ctk.CTkFont(size=12),
                        anchor="w",
                    ),
                )

        if self.tabela.vazia:
            self.tabela.mostrar_vazio()


class FichaModal(_ModalVinculo):
    """Ficha (só leitura) de UM registo: pares rótulo → valor."""

    def __init__(self, master, titulo, subtitulo, pares, largura=440):
        altura = 180 + 36 * len(pares)
        super().__init__(master, titulo, subtitulo, largura, altura)

        self.corpo.grid_columnconfigure(1, weight=1)
        for fila, (rotulo, valor) in enumerate(pares):
            ctk.CTkLabel(
                self.corpo,
                text=rotulo,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).grid(row=fila, column=0, sticky="w", pady=3, padx=(0, 16))
            ctk.CTkLabel(
                self.corpo,
                text=valor,
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                wraplength=largura - 200,
                justify="left",
            ).grid(row=fila, column=1, sticky="w", pady=3)


# =====================================================================
# Blocos visuais do Dashboard (v1.6.0, 27/09/2026)
#
# Regra de 21/09/2026: os ecrãs não instanciam widgets CustomTkinter
# diretamente — passam por uma classe daqui. Estas nasceram com o
# Dashboard novo, mas são genéricas: qualquer ecrã que precise de um
# cartão com título, um número grande ou uma etiqueta colorida pode
# (e deve) usá-las em vez de repetir `ctk.CTkFrame(...)` com as
# mesmas cinco opções de estilo.
# =====================================================================

# Estilos de texto: (tamanho, negrito, cor). Um estilo é uma
# intenção ("título de cartão", "número de KPI"), não um tamanho —
# mudar o aspeto de todos os títulos de cartão é mudar uma linha.
_ESTILOS_ROTULO = {
    "titulo": (18, True, tema.COR_TEXTO),
    "cartao": (13, True, tema.COR_TEXTO),
    "numero": (26, True, tema.COR_TEXTO),
    "texto": (12, False, tema.COR_TEXTO),
    "forte": (12, True, tema.COR_TEXTO),
    "secundario": (11, False, tema.COR_TEXTO_SECUNDARIO),
    "secao": (10, True, tema.COR_TEXTO_SECUNDARIO),
}

# Estilos de etiqueta (pílula): (fundo, texto). Os mesmos pares do
# `tema.py` que o resto da aplicação já usa para estados.
_ESTILOS_ETIQUETA = {
    "erro": (tema.VERMELHO_ERRO, tema.TEXTO_ERRO),
    "aviso": (tema.AMARELO_AVISO, tema.TEXTO_AVISO),
    "livre": (tema.VERDE_LIVRE, tema.TEXTO_LIVRE),
    "info": (tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL),
    "azul": (tema.ID_CHIP_FUNDO, tema.AZUL_PRINCIPAL),
}

# Cores da barra de nível, pelo mesmo nome das etiquetas.
_CORES_NIVEL = {
    "erro": tema.TEXTO_ERRO,
    "aviso": tema.TEXTO_AVISO,
    "livre": tema.TEXTO_LIVRE,
    "azul": tema.AZUL_PRINCIPAL,
}


class Contentor(ctk.CTkFrame):
    """Frame transparente, sem cantos — só para arrumar widgets."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)


class AreaRolavel(ctk.CTkScrollableFrame):
    """Área com scroll vertical, transparente.

    Lição da v1.6.0 (ficheiro 11, A.5 n.º 1): NUNCA ligar
    `<Configure>` a este widget sem `add=True` — mata o updater do
    `scrollregion` e a área deixa de rolar.
    """

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)


class Rotulo(ctk.CTkLabel):
    """Texto com um dos estilos de `_ESTILOS_ROTULO`.

    `cor` substitui a cor do estilo (ex.: um número a verde). Os
    restantes kwargs vão direitos ao CTkLabel (wraplength, justify).
    """

    def __init__(self, master, texto, estilo="texto", cor=None, **kwargs):
        tamanho, negrito, cor_estilo = _ESTILOS_ROTULO[estilo]
        kwargs.setdefault("anchor", "w")
        # O CTkLabel reserva 28px de altura por omissão, seja qual for
        # a letra — numa lista, título e detalhe ficavam afastados.
        kwargs.setdefault("height", tamanho + 8)
        super().__init__(
            master,
            text=texto,
            text_color=cor if cor is not None else cor_estilo,
            font=ctk.CTkFont(
                size=tamanho, weight="bold" if negrito else "normal"
            ),
            **kwargs,
        )


class Etiqueta(ctk.CTkLabel):
    """Pílula colorida (estado, prioridade, regime).

    `largura` fixa a largura em pixels — numa lista, pílulas com a
    mesma largura deixam as colunas à esquerda alinhadas.
    """

    def __init__(self, master, texto, estilo="info", largura=0):
        fundo, cor = _ESTILOS_ETIQUETA[estilo]
        super().__init__(
            master,
            text=f" {texto} ",
            fg_color=fundo,
            text_color=cor,
            corner_radius=8,
            height=22,
            width=largura,
            font=ctk.CTkFont(size=11, weight="bold"),
        )


class Botao(ctk.CTkButton):
    """Botão com um de quatro estilos.

    - "primario": azul da marca (ação principal do bloco).
    - "sucesso": verde (confirmar, aprovar).
    - "contorno": só a borda (ações secundárias, atalhos).
    - "discreto": sem borda nem fundo (setas ◀ ▶, "Ver ›").
    """

    def __init__(self, master, texto, comando=None, estilo="contorno",
                 **kwargs):
        kwargs.setdefault("height", 30)
        # Largura MÍNIMA: o botão cresce com o texto. Os 140px por
        # omissão do CTkButton faziam "↻ Atualizar" parecer um campo.
        kwargs.setdefault("width", 60)
        kwargs.setdefault("corner_radius", tema.RAIO_BOTAO)
        kwargs.setdefault("font", ctk.CTkFont(size=12))

        if estilo == "primario":
            kwargs.update(
                fg_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.AZUL_CLARO,
                text_color="#FFFFFF",
            )
        elif estilo == "sucesso":
            kwargs.update(
                fg_color=tema.VERDE,
                hover_color=tema.TEXTO_LIVRE,
                text_color="#FFFFFF",
            )
        elif estilo == "discreto":
            kwargs.update(
                fg_color="transparent",
                hover_color=tema.LINHA_ALTERNADA,
                text_color=tema.COR_TEXTO,
            )
        else:
            kwargs.update(
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                hover_color=tema.LINHA_ALTERNADA,
                text_color=tema.COR_TEXTO,
            )

        super().__init__(master, text=texto, command=comando, **kwargs)


class SeletorVistas(ctk.CTkSegmentedButton):
    """Seletor de vistas em pílula ("Hoje | Financeiro").

    A opção escolhida fica em branco, sobre uma faixa cinzenta — o
    mesmo desenho aprovado no mockup de 27/09/2026. `ao_mudar`
    recebe o texto da opção escolhida.
    """

    def __init__(self, master, opcoes, ao_mudar, inicial=None):
        super().__init__(
            master,
            values=list(opcoes),
            command=ao_mudar,
            fg_color=tema.CINZA_INDISPONIVEL,
            selected_color=tema.COR_FUNDO,
            selected_hover_color=tema.COR_FUNDO,
            unselected_color=tema.CINZA_INDISPONIVEL,
            unselected_hover_color=tema.LINHA_ALTERNADA,
            text_color=tema.COR_TEXTO,
            corner_radius=tema.RAIO_CAMPO,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.set(inicial if inicial is not None else opcoes[0])


class BarraNivel(ctk.CTkProgressBar):
    """Barra de nível só de leitura (ocupação, stock, receita).

    `valor` entre 0 e 1 (é cortado a esse intervalo); `cor` é um
    dos nomes de `_CORES_NIVEL`.
    """

    def __init__(self, master, valor, cor="azul", largura=120, altura=8):
        super().__init__(
            master,
            width=largura,
            height=altura,
            corner_radius=altura // 2,
            fg_color=tema.CINZA_INDISPONIVEL,
            progress_color=_CORES_NIVEL[cor],
        )
        self.set(max(0.0, min(1.0, float(valor))))


class Separador(ctk.CTkFrame):
    """Linha horizontal de 1px, na cor das bordas."""

    def __init__(self, master):
        # `bg_color` também: com 1px de altura o CTkFrame não chega a
        # desenhar o retângulo de fundo, e só a cor do canvas aparece.
        super().__init__(
            master,
            height=1,
            corner_radius=0,
            fg_color=tema.COR_BORDA,
            bg_color=tema.COR_BORDA,
        )


class Cartao(ctk.CTkFrame):
    """Cartão com borda, título opcional à esquerda e subtítulo
    opcional à direita. O conteúdo vai para `self.corpo`.
    """

    def __init__(self, master, titulo="", subtitulo=""):
        super().__init__(
            master,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )

        if titulo or subtitulo:
            self.topo = Contentor(self)
            self.topo.pack(fill="x", padx=16, pady=(14, 8))
            Rotulo(self.topo, titulo, "cartao").pack(side="left")

            if subtitulo:
                Rotulo(self.topo, subtitulo, "secundario").pack(
                    side="right"
                )

        self.corpo = Contentor(self)
        self.corpo.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(0 if titulo or subtitulo else 14, 14),
        )


class CartaoKpi(Cartao):
    """Cartão de um número: rótulo, valor grande e uma linha de
    contexto por baixo. Com `nivel` (0 a 1) mostra também uma barra.
    """

    def __init__(self, master, rotulo, valor, contexto="",
                 cor_valor=None, cor_contexto=None, nivel=None,
                 cor_nivel="azul"):
        super().__init__(master)

        Rotulo(self.corpo, rotulo, "secundario").pack(fill="x")
        Rotulo(self.corpo, valor, "numero", cor=cor_valor).pack(
            fill="x", pady=(2, 0)
        )

        if nivel is not None:
            BarraNivel(self.corpo, nivel, cor=cor_nivel).pack(
                fill="x", pady=(4, 2)
            )

        if contexto:
            Rotulo(self.corpo, contexto, "secundario", cor=cor_contexto).pack(
                fill="x", pady=(2, 0)
            )


def fila_de_cartoes(master, colunas):
    """Contentor em grelha com `colunas` colunas iguais (`uniform`).

    Devolve o contentor; quem chama põe cada cartão com
    `.grid(row=0, column=n, sticky="nsew", padx=...)`. Sem o
    `uniform`, cartões com textos de larguras diferentes ficavam com
    larguras diferentes.
    """
    fila = Contentor(master)

    for coluna in range(colunas):
        fila.grid_columnconfigure(coluna, weight=1, uniform="cartoes")

    return fila


class CampoTexto(ctk.CTkEntry):
    """Campo de texto com o estilo da aplicação.

    `secreto=True` esconde o que se escreve (passwords).
    """

    def __init__(self, master, secreto=False, **kwargs):
        kwargs.setdefault("corner_radius", tema.RAIO_CAMPO)
        kwargs.setdefault("height", 32)

        if secreto:
            kwargs.setdefault("show", "•")

        super().__init__(master, **kwargs)
