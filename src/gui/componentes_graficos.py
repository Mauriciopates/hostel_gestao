"""Gráficos com matplotlib embutidos em CustomTkinter.

Fica em ficheiro próprio, separado do `componentes.py`, por uma
razão prática: o `componentes.py` é importado por todos os ecrãs,
e o matplotlib é uma dependência pesada. Quem só precisa das
tabelas e dos popups não deve pagar o custo de importar gráficos
sem os usar — `import componentes_graficos` é uma decisão
consciente, não um efeito secundário.

O backend do matplotlib tem de ser forçado para "TkAgg" ANTES de
tocar no pyplot: sem isto, se o ambiente tiver PyQt ou GTK
instalado, o matplotlib escolhe esse e o `FigureCanvasTkAgg` falha
ao embutir em CustomTkinter. Aqui nem sequer importamos `pyplot` —
trabalhamos só com a API orientada a objetos (`Figure`), que é o
que o `FigureCanvasTkAgg` espera.

Tema: fixo em CLARO, porque o matplotlib não segue o
`ctk.set_appearance_mode("System")` sozinho. O gancho para o tema
escuro está em `Grafico._aplicar_tema_ao_axes` e em
`Grafico.aplicar_tema` — quando o ecrã de Configurações passar a
poder alternar o tema, é só chamar `grafico.aplicar_tema()` depois
de `ctk.set_appearance_mode(...)`. Um único sítio a mexer.

As cores usadas são sempre puxadas do `tema.py`. Não há nenhuma
cor nova definida aqui — a única exceção é o nome do backend
("TkAgg"), que não é cor nenhuma.

Nota de desempenho: `FigureCanvasTkAgg.draw()` é o que torna o
gráfico visível, e `draw_idle()` agenda o redesenho para quando o
Tk estiver livre. Uso `draw_idle()` em todos os sítios — chamar
`draw()` a cada atualização bloqueia a UI enquanto o matplotlib
desenha, e num gráfico de 7 pontos isso não se nota, mas num
gráfico de 30 não é agradável. `draw_idle()` deixa o evento
seguinte correr primeiro, e o utilizador não sente o clique.

CORREÇÃO 13/09/2026 (a) — `_cor_para_matplotlib`: o
`CORES_ESTADO` do `gui_est_comum.py` mistura pares do tema
(fundo/texto de aviso, erro, livre) com cores de marca simples (o
`AZUL_PRINCIPAL` em "enviada"). Tirar o elemento claro com um
`[0]` cru funcionava para os pares e dava `"#"` para as strings —
daí o erro "ValueError: '#' is not a valid value for color". A
função normaliza os dois casos, e é usada tanto para o fundo das
barras como para a cor dos números.

CORREÇÃO 13/09/2026 (b) — margens cortadas: os rótulos do eixo X
("seg 7", "ter 8"...) apareciam cortados a meio, porque o
`set_layout_engine("tight")` só recalcula margens no `draw()`
seguinte, e o primeiro `draw()` já usava as margens por omissão
do matplotlib.

CORREÇÃO 13/09/2026 (c) — nomes dos estados cortados: no gráfico
de barras, "pendente" e "rejeitada" apareciam truncados à esquerda
("ndente", "jeitada") porque o `set_layout_engine("tight")` do
matplotlib está a entrar em CONFLITO com o `tight_layout()`
explícito — cada um pensa que o outro vai calcular as margens, e
o resultado é que o espaço do eixo Y fica subestimado. A solução
foi remover o `set_layout_engine` do `__init__` e deixar só o
`tight_layout(pad=1.5)` explícito. O `pad` subiu de 1.2 para 1.5
para os nomes compridos ("rejeitada") terem folga.
"""

import matplotlib

matplotlib.use("TkAgg")   # ANTES de qualquer outro import do matplotlib

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import customtkinter as ctk

from . import tema


def _cor_para_matplotlib(cor):
    """Normaliza um valor de cor do `tema.py` para o formato que o
    matplotlib aceita.

    O `tema.py` mistura dois formatos:

    - Cores de marca (`AZUL_PRINCIPAL`, `VERDE`, `NAVY_ESCURO`) —
      strings simples, iguais nos dois modos de aparência.
    - Cores de conteúdo (`COR_FUNDO`, `AMARELO_AVISO`, `TEXTO_AVISO`,
      etc.) — pares `(claro, escuro)`, porque mudam com o modo.

    O `CORES_ESTADO` do `gui_est_comum.py` herda esta mistura: o
    "fundo" de cada estado é sempre par (vem de um `*_AVISO`, `*_ERRO`
    ou `*_LIVRE`), mas o "texto" pode ser par (idem) ou string
    (o caso do `AZUL_PRINCIPAL`, em "enviada").

    Esta função resolve os dois casos: se `cor` for tuplo, devolve
    o primeiro elemento (o claro — os gráficos estão fixos em modo
    claro, ver `Grafico._aplicar_tema_ao_axes`); se for string,
    devolve a string tal e qual.

    Sem isto, `cores[estado][1][0]` (tirar o claro do par de texto)
    dava `"#"` para o estado "enviada", onde `cores[estado][1]` é
    `"#0E6291"` e `[0]` é só o primeiro caractere.
    """
    if isinstance(cor, tuple):
        return cor[0]

    return cor


# Altura padrão dos gráficos, em pixéis. Só usada quando quem
# instancia não dá outra — o `gui_dashboard.py` passa uma altura
# explícita por cada gráfico, para os dois painéis ficarem do
# mesmo tamanho lado a lado.
ALTURA_PADRAO = 200


class Grafico(ctk.CTkFrame):
    """Base dos gráficos: Figure + Axes + canvas embutido.

    As subclasses só redefinem `_desenhar(**kwargs)` — toda a
    mecânica de criar a Figure, embutir o canvas no CTkFrame,
    limpar antes de redesenhar e aplicar as cores do tema é igual
    para todos os gráficos, e vive aqui uma única vez.

    O padrão de uso é:

        self.grafico = GraficoOcupacao(self)
        self.grafico.pack(fill="both", expand=True)
        ...
        self.grafico.atualizar(
            rotulos=[...],
            airbnb=[...],
            mensal=[...],
        )

    `atualizar` é o único método público que quem chama precisa de
    conhecer. `aplicar_tema` é o segundo, e só interessa quando o
    tema da aplicação mudar em runtime.
    """

    def __init__(self, master, altura=ALTURA_PADRAO):
        super().__init__(master, fg_color="transparent")

        self.altura = altura

        # dpi=100 é o valor por omissão do matplotlib para ecrãs,
        # e dá 1 ponto de dados por pixel no `FigureCanvasTkAgg`.
        # Não exposto como parâmetro: quem quiser ajustar densidade
        # muda aqui.
        self.fig = Figure(figsize=(4, altura / 100), dpi=100)

        # NOTA 13/09/2026 (c): o `set_layout_engine("tight")` que
        # aqui estava foi REMOVIDO. Entrava em conflito com o
        # `tight_layout(pad=1.5)` explícito do
        # `_aplicar_tema_ao_axes` — cada um pensava que o outro ia
        # calcular as margens, e o resultado era o matplotlib a
        # ignorar ambos e usar as margens por omissão (pequenas
        # demais). Sintoma visível: no gráfico de barras, os nomes
        # dos estados apareciam truncados à esquerda ("ndente",
        # "jeitada"). Ficou só o `tight_layout()` explícito — faz
        # o mesmo, sem ambiguidade.

        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self._aplicar_tema_ao_axes()

    # -- ciclo de vida -----------------------------------------------

    def atualizar(self, **kwargs):
        """Limpa o Axes e volta a desenhar com os dados dados.

        É este o ponto de entrada de quem usa o gráfico — nunca se
        chama `_desenhar` diretamente (é o método que as subclasses
        redefinem, não a API pública). O `clear()` no Axes garante
        que uma segunda chamada a `atualizar` não deixa restos da
        primeira (linhas antigas por baixo das novas, legendas
        duplicadas).
        """
        self.ax.clear()
        self._aplicar_tema_ao_axes()
        self._desenhar(**kwargs)
        # `draw_idle` e não `draw`: não bloqueia a UI à espera do
        # redesenho, o que importa quando o utilizador está a
        # arrastar a janela ou a clicar em filtros.
        self.canvas.draw_idle()

    def aplicar_tema(self):
        """Reaplica as cores do tema e redesenha o gráfico atual.

        Só é preciso chamar isto quando o modo de aparência mudar
        em runtime (`ctk.set_appearance_mode("Dark")`). Enquanto
        essa alternância não existir em Configurações, o método
        fica aqui à espera — não é código morto, é o gancho que
        a decisão "tema fixo em claro por agora" deixou em aberto.

        Não guarda os dados do último `atualizar`: quem chama isto
        deve ter uma forma de os voltar a passar (no
        `gui_dashboard.py` é só recalcular, são 7 pontos). Evita
        guardar estado que pode ficar desatualizado se os dados
        mudarem entretanto.
        """
        self._aplicar_tema_ao_axes()
        self.canvas.draw_idle()

    # -- pintura -----------------------------------------------------

    def _aplicar_tema_ao_axes(self):
        """Cores do tema aplicadas à Figure e ao Axes, e recálculo
        explícito das margens.

        Está aqui, e não no `__init__` de cada subclasse, porque é
        igual para todos: fundo, cor dos ticks, cor das linhas dos
        eixos, cor da grelha. Só o que os dados mostram muda de
        subclasse para subclasse.

        O `tema.COR_FUNDO` é um par `(claro, escuro)` — escolho o
        primeiro elemento (claro) e documento isso. Quando o tema
        escuro for implementado a sério, é este método que muda:
        lê a preferência do CustomTkinter e escolhe o elemento
        certo do par. Um sítio só, sem tocar em nenhum gráfico.
        """
        # Os pares de tema são `(claro, escuro)`. `[0]` fixa o
        # claro — ver a nota de topo do ficheiro.
        fundo = tema.COR_FUNDO[0]
        texto_sec = tema.COR_TEXTO_SECUNDARIO[0]
        borda = tema.COR_BORDA[0]

        self.fig.patch.set_facecolor(fundo)
        self.ax.set_facecolor(fundo)

        self.ax.tick_params(
            colors=texto_sec,
            labelsize=9,
            length=3,
            width=0.5,
        )

        # Eixos de cima e da direita desligados — convenção de
        # gráfico de negócio, não de papel científico. Sobram os
        # dois eixos que interessam, sem a moldura completa.
        for lado in ("top", "right"):
            self.ax.spines[lado].set_visible(False)

        for lado in ("left", "bottom"):
            self.ax.spines[lado].set_color(borda)
            self.ax.spines[lado].set_linewidth(0.5)

        # Grelha só horizontal (o eixo dos Y), que é o que ajuda
        # a ler valores. Grelha vertical num gráfico de linhas
        # enche o gráfico de riscos sem ajudar a ler nada.
        self.ax.grid(
            True,
            axis="y",
            color=borda,
            linewidth=0.5,
            alpha=0.5,
        )
        self.ax.set_axisbelow(True)

        # `tight_layout` explícito — calcula as margens para
        # acomodar os rótulos dos eixos sem os cortar. Como o
        # `set_layout_engine("tight")` do `__init__` foi removido
        # (ver nota lá), este é agora o ÚNICO sítio a mexer nas
        # margens, sem conflito.
        #
        # `pad=1.5` (era 1.2): o nome mais comprido no gráfico de
        # barras é "rejeitada" — a 1.2 ainda ficava ligeiramente
        # cortado à esquerda. 1.5 dá folga suficiente para os nomes
        # saírem inteiros, sem afastar o gráfico das bordas do
        # painel ao ponto de parecer desconexo.
        #
        # Se no futuro acrescentares um estado com nome muito mais
        # comprido (ex.: "aguarda aprovação"), o caminho é subir
        # este valor para 1.8 ou 2.0. É a única linha a mexer.
        self.fig.tight_layout(pad=1.5)

    def _desenhar(self, *args, **kwargs):
        """Redefinido pelas subclasses. Recebe os dados do
        `atualizar` diretamente, sem os interpretar.

        A assinatura é `*args, **kwargs` — não por preguiça, mas
        porque cada subclasse recebe um conjunto diferente de
        argumentos por nome (`GraficoOcupacao` recebe
        `rotulos`/`airbnb`/`mensal`; `GraficoRequisicoes` recebe
        `estados`/`contagens`/`cores`). O Pylance precisa de ver
        que a base aceita "qualquer coisa" para não marcar as
        subclasses como incompatíveis — com só `**kwargs` na base,
        ele assume zero argumentos posicionais e avisa a vermelho
        nos `_desenhar` das subclasses. `*args` na assinatura da
        base é o mínimo para ele perceber que a compatibilidade
        é intencional.
        """
        raise NotImplementedError(
            "Cada subclasse de Grafico tem de redefinir _desenhar."
        )


class GraficoOcupacao(Grafico):
    """Ocupação diária dos últimos N dias — uma linha por regime.

    Airbnb em azul, Mensal em verde. As duas linhas partilham o
    mesmo eixo Y (0 a 100%), para a comparação ser visual e
    direta. Os dias ficam no eixo X, com o dia da semana à frente
    do dia do mês ("seg 15") — mais útil que só "15" ou só "seg":
    o dia da semana ajuda a ver o padrão semanal, o dia do mês
    identifica a data exata.
    """

    def _desenhar(self, rotulos, airbnb, mensal):
        """Desenha as duas linhas.

        `rotulos` são as etiquetas do eixo X (já formatadas pelo
        chamador — este widget não sabe o que é um dia da semana),
        `airbnb` e `mensal` são listas de floats entre 0 e 1 (já
        calculados pelo chamador — este widget não sabe o que é
        uma unidade ocupada). Separar as responsabilidades assim
        mantém o gráfico genérico: se amanhã quiseres uma linha
        "Outros", é só acrescentar um `plot` aqui.
        """
        x = list(range(len(rotulos)))

        self.ax.plot(
            x,
            airbnb,
            color=tema.AZUL_PRINCIPAL,
            linewidth=2,
            marker="o",
            markersize=4,
            label="Airbnb",
            zorder=3,
        )
        self.ax.plot(
            x,
            mensal,
            color=tema.VERDE,
            linewidth=2,
            marker="o",
            markersize=4,
            label="Mensal",
            zorder=3,
        )

        # Eixo Y de 0 a 100%, com marcas em 0/25/50/75/100. Sem
        # intervalo dinâmico, porque a pergunta que este gráfico
        # responde é "está cheio ou vazio", e isso lê-se melhor
        # com a escala sempre igual.
        self.ax.set_ylim(0, 1)
        self.ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        self.ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])

        self.ax.set_xticks(x)
        self.ax.set_xticklabels(rotulos, fontsize=8)

        # Legenda sem moldura, encostada ao canto. `frameon=False`
        # tira-lhe a caixa que o matplotlib põe por omissão — não
        # combina com o resto do estilo da aplicação.
        self.ax.legend(
            loc="upper left",
            frameon=False,
            fontsize=9,
            labelcolor=tema.COR_TEXTO[0],
            ncols=2,  # lado a lado, ocupa menos altura
        )


class GraficoRequisicoes(Grafico):
    """Requisições por estado — barras horizontais.

    Ordem das barras é a que o chamador passar (de cima para
    baixo). No `gui_dashboard.py` a ordem é "pendente, enviada,
    fechada, rejeitada" — do que exige ação para o que não
    exige, que é a ordem em que faz sentido olhar para o gráfico.

    Barras horizontais e não verticais: os nomes dos estados
    ("pendente", "rejeitada") são compridos, e em barras
    verticais ou ficavam de lado (a obrigar a rodar a cabeça) ou
    cortados. Na horizontal, o nome fica ao lado da barra e lê-se
    de imediato.

    Cores: cada barra leva o par (fundo, texto) do seu estado,
    passado pelo chamador em `cores`. O fundo da barra é a cor
    principal, e o número no fim leva a cor de texto — a mesma
    linguagem visual dos chips das tabelas de requisições e
    devoluções (o `gui_est_comum.CORES_ESTADO`).
    """

    def _desenhar(self, estados, contagens, cores):
        """Desenha as barras horizontais.

        `estados` é a lista de nomes (já na ordem certa),
        `contagens` a lista paralela de números, `cores` um
        dicionário {estado: (cor_fundo, cor_texto)}.

        As cores que chegam aqui vêm do `gui_est_comum.CORES_ESTADO`
        — cada valor é `(fundo, texto)`, mas cada um desses dois
        elementos pode ser:
        - um par `(claro, escuro)` do `tema.py` (a maioria dos
          casos), ou
        - uma string simples (o `AZUL_PRINCIPAL` em "enviada", e
          as cores de marca em geral).

        O matplotlib quer sempre uma cor só, em string. É a função
        `_cor_para_matplotlib` que normaliza — ver o docstring dela
        para o porquê de não bastar um `[0]` cru.
        """
        y = list(range(len(estados)))

        fundos = [
            _cor_para_matplotlib(cores[estado][0]) for estado in estados
        ]

        barras = self.ax.barh(
            y,
            contagens,
            color=fundos,
            height=0.6,
            zorder=3,
        )

        # Números no fim de cada barra — a cor do texto do estado.
        # O `max(contagens) * 0.02` é a folga entre a barra e o
        # número, proporcional ao maior valor, para não colar em
        # barras curtas nem afastar demasiado em barras longas.
        # Guardado numa variável local porque `contagens` pode
        # ser vazia (o chamador já garante que não, mas evita
        # rebentar num `max()` de lista vazia).
        if contagens:
            margem = max(contagens) * 0.02
        else:
            margem = 0

        for barra, estado, valor in zip(barras, estados, contagens):
            self.ax.text(
                barra.get_width() + margem,
                barra.get_y() + barra.get_height() / 2,
                str(valor),
                va="center",
                ha="left",
                fontsize=10,
                color=_cor_para_matplotlib(cores[estado][1]),
                fontweight="bold",
            )

        self.ax.set_yticks(y)
        self.ax.set_yticklabels(estados, fontsize=9)

        # Sem valores no eixo X — o número ao lado da barra já
        # diz tudo, e os ticks do X só acrescentavam ruído.
        self.ax.set_xticks([])

        # Tira a linha do eixo X (a que fica em baixo do gráfico
        # quando há barras horizontais): sem ela, o gráfico lê-se
        # como uma lista de barras soltas, não como um eixo com
        # valores.
        self.ax.spines["bottom"].set_visible(False)

        # Margem à direita para os números não encostarem à borda.
        if contagens and max(contagens) > 0:
            self.ax.set_xlim(0, max(contagens) * 1.15)

        # Inverte o eixo Y para o primeiro da lista ficar em cima.
        if len(estados) > 1:
            self.ax.set_ylim(len(estados) - 0.5, -0.5)
        else:
            self.ax.set_ylim(0.5, -0.5)