"""Ecrã de Calendário de disponibilidade.

Dois passos, por decisão do aluno (08/09/2026, aprovada por mockup
antes de codar):

1. `Calendario` — ecrã de entrada, na área de conteúdo normal, com
   dois cartões clicáveis: "Mensal" e "Airbnb". Cada cartão mostra
   quantas unidades tem o regime e a ocupação de hoje. Serve de
   resumo e de seletor: o calendário nunca mistura os dois regimes.

2. `CalendarioSemanaModal` — popup (CTkToplevel) com a grelha da
   semana, já filtrada pelo regime escolhido. Linhas são unidades,
   colunas são as sete noites de segunda a domingo.

Porquê separar os regimes (ponto que motivou o redesenho): uma
célula não quer dizer o mesmo nos dois. Numa unidade mensal a
unidade divide-se em lugares, por isso a célula mostra a proporção
"ocupados/capacidade" e pode estar parcialmente ocupada. Numa
unidade Airbnb a unidade é indivisível — ou está livre, ou
reservada, ou ocupada. Uma grelha só, com as duas leituras
misturadas, obrigava a legenda a mentir num dos casos.

Decisões visuais, todas com cores já existentes em `tema.py` (não
foi acrescentada nenhuma):

- livre → VERDE_LIVRE, parcial/reservado → AMARELO_AVISO,
  cheia/ocupado → VERMELHO_ERRO, manutenção → CINZA_INDISPONIVEL.
  É a mesma linguagem da Planta de Lugares (gui_unidades.py), para
  não haver dois significados de cor no mesmo sistema.
- Cartão com borda + faixa `CABECALHO_TABELA_FUNDO` no cabeçalho +
  zebra `LINHA_ALTERNADA`, igual às tabelas de Gestão de
  Propriedades (07/09/2026).
- Setas só em ASCII ("<" e ">"): o glifo Unicode aparecia como
  quadrado (tofu) no Windows, bug já apanhado no "< Voltar" e no
  "Ver planta".

Camadas: este módulo não calcula ocupação nenhuma. Toda a leitura
de estado vem de `unidades.estado_detalhe(unidade_id, data)`, que
devolve o estado já classificado e os números já contados — a GUI
só escolhe a cor e escreve o texto.
"""
import datetime

import customtkinter as ctk

import propriedades
import unidades
from . import componentes
from . import tema


# Cabeçalhos das colunas. Índice 0 = segunda-feira, a mesma ordem
# que `datetime.date.weekday()` devolve.
_DIAS_SEMANA = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")

_MESES = (
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
)

# Larguras fixas, como nas tabelas de Gestão de Propriedades: com
# sete colunas de noites, deixar cada uma esticar sozinha desalinha
# o corpo do cabeçalho assim que um nome de unidade é mais comprido.
_LARGURA_NOME = 150
_LARGURA_CELULA = 100
_ALTURA_CELULA = 30

# Estado devolvido por `unidades.estado_detalhe` -> (fundo, texto).
# "parcial"/"cheia" só aparecem no regime mensal; "reservado"/
# "ocupado" só no Airbnb — mas partilham as cores de propósito, para
# a leitura ser a mesma nos dois ecrãs (amarelo = a acompanhar,
# vermelho = sem vaga).
_CORES_ESTADO = {
    "livre": (tema.VERDE_LIVRE, tema.TEXTO_LIVRE),
    "parcial": (tema.AMARELO_AVISO, tema.TEXTO_AVISO),
    "cheia": (tema.VERMELHO_ERRO, tema.TEXTO_ERRO),
    "reservado": (tema.AMARELO_AVISO, tema.TEXTO_AVISO),
    "ocupado": (tema.VERMELHO_ERRO, tema.TEXTO_ERRO),
    "manutencao": (tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL),
}

_LEGENDA_MENSAL = (
    ("livre", "livre"),
    ("parcial", "parcial"),
    ("cheia", "cheia"),
    ("manutencao", "manutenção"),
)

_LEGENDA_AIRBNB = (
    ("livre", "livre"),
    ("reservado", "reservado"),
    ("ocupado", "ocupado"),
    ("manutencao", "manutenção"),
)

# Estados que contam como "ainda dá para entrar aqui", usados pelo
# filtro de disponibilidade. "parcial" nunca aparece no Airbnb e
# "reservado" nunca aparece no mensal, por isso o mesmo par serve
# para os dois regimes.
_ESTADOS_COM_VAGA = ("livre", "parcial")

_OPCAO_TODAS = "Todas as propriedades"
_OPCOES_DISPONIBILIDADE = ("Todas as unidades", "Só com disponibilidade")


def _colocar_no_topo(janela):
    """Traz um popup (CTkToplevel) para a frente da janela principal.

    Mesma função de gui_propriedades.py, repetida aqui para o módulo
    não depender de um ecrã de negócio diferente só por causa de um
    detalhe de janelas. `after(10, ...)` dá tempo ao Tk para mapear a
    janela antes de `grab_set()`, que de outro modo falha com "grab
    failed: window not viewable" em alguns sistemas.
    """
    janela.after(
        10, lambda: (janela.lift(), janela.focus_force(), janela.grab_set())
    )


def _tornar_clicavel(widget, ao_clicar):
    """Liga o clique e o cursor de mão a um widget e a todos os seus
    descendentes.

    Mesmo padrão das caixas da Planta de Lugares: sem isto, clicar em
    cima da etiqueta de texto dentro do cartão não conta como clicar
    no cartão, porque o evento fica no filho.
    """
    widget.bind("<Button-1>", lambda evento: ao_clicar())
    widget.configure(cursor="hand2")

    for filho in widget.winfo_children():
        _tornar_clicavel(filho, ao_clicar)


def _segunda_feira(data):
    """Devolve a segunda-feira da semana a que 'data' pertence."""
    return data - datetime.timedelta(days=data.weekday())


def _texto_intervalo(inicio):
    """Escreve o intervalo da semana, ex. "10 - 16 ago 2026".

    Quando a semana atravessa dois meses (ou dois anos) o mês passa a
    aparecer dos dois lados, senão o intervalo ficava ambíguo.
    """
    fim = inicio + datetime.timedelta(days=6)
    mes_inicio = _MESES[inicio.month - 1]
    mes_fim = _MESES[fim.month - 1]

    if inicio.year != fim.year:
        return (
            f"{inicio.day} {mes_inicio} {inicio.year} - "
            f"{fim.day} {mes_fim} {fim.year}"
        )

    if inicio.month != fim.month:
        return f"{inicio.day} {mes_inicio} - {fim.day} {mes_fim} {fim.year}"

    return f"{inicio.day} - {fim.day} {mes_fim} {fim.year}"


def _texto_celula(detalhe, tipo):
    """Texto a escrever dentro de uma célula do calendário.

    No regime mensal a célula mostra "ocupados/capacidade" — é o que
    dá a leitura de quanto ainda cabe. No Airbnb a unidade é
    indivisível, não há proporção nenhuma a mostrar, por isso a
    célula fica só com a cor.
    """
    if detalhe["estado"] == "manutencao":
        return "manut."

    if tipo != "mensal":
        return ""

    return f"{detalhe['ocupados']}/{detalhe['capacidade']}"


class Calendario(ctk.CTkFrame):
    """Ecrã de entrada do calendário: escolher o regime.

    Não desenha grelha nenhuma — só os dois cartões de resumo. A
    grelha vive no popup, para o ecrã principal não ficar preso a uma
    tabela larga por trás da barra lateral.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Calendário").pack(fill="x")

        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.pack(expand=True)

        ctk.CTkLabel(
            centro,
            text="Selecionar regime",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 20))

        cartoes = ctk.CTkFrame(centro, fg_color="transparent")
        cartoes.pack()

        hoje = datetime.date.today()
        self._desenhar_cartao(cartoes, "mensal", "Mensal", hoje)
        self._desenhar_cartao(cartoes, "airbnb", "Airbnb", hoje)

        ctk.CTkLabel(
            centro,
            text="Clicar num cartão abre o calendário da semana.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(20, 0))

    # -- resumo dos cartões ------------------------------------------

    def _resumo(self, tipo, data):
        """Devolve as duas linhas de resumo de um regime.

        A primeira é sempre a contagem de unidades ativas. A segunda
        muda com o regime: no mensal é a proporção de lugares
        ocupados no conjunto todo, no Airbnb é quantas unidades estão
        ocupadas hoje. Unidades que rebentem o cálculo (ex. apagadas
        entretanto) são saltadas em vez de derrubarem o ecrã.
        """
        lista = unidades.listar(tipo=tipo)
        ocupados = 0
        capacidade = 0

        for uni in lista:
            try:
                detalhe = unidades.estado_detalhe(uni["id"], data)
            except ValueError:
                continue

            if tipo == "mensal":
                if detalhe["capacidade"] is not None:
                    ocupados += detalhe["ocupados"]
                    capacidade += detalhe["capacidade"]
            elif detalhe["estado"] == "ocupado":
                ocupados += 1

        if tipo == "mensal":
            segunda = f"{ocupados}/{capacidade} lugares"
        else:
            segunda = f"{ocupados}/{len(lista)} ocupadas"

        return f"{len(lista)} unidades", segunda

    def _desenhar_cartao(self, master, tipo, titulo, data):
        """Desenha um dos dois cartões de regime, já clicável."""
        linha_unidades, linha_ocupacao = self._resumo(tipo, data)

        cartao = ctk.CTkFrame(
            master,
            width=250,
            height=160,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(side="left", padx=12)
        cartao.pack_propagate(False)

        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(30, 10))

        ctk.CTkLabel(
            cartao,
            text=linha_unidades,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
        ).pack()

        ctk.CTkLabel(
            cartao,
            text=linha_ocupacao,
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=12, weight="bold"),
            padx=12,
            pady=4,
        ).pack(pady=(10, 0))

        _tornar_clicavel(cartao, lambda: self._abrir_semana(tipo))

    def _abrir_semana(self, tipo):
        CalendarioSemanaModal(self, tipo)


class CalendarioSemanaModal(ctk.CTkToplevel):
    """Popup com a grelha da semana de um só regime.

    Filtros: propriedade e disponibilidade. Navegação: semana
    anterior/seguinte, a partir da semana de hoje. Cada célula é uma
    noite e abre o detalhe do dia ao ser clicada.
    """

    def __init__(self, tela, tipo):
        super().__init__(tela)
        self.tela = tela
        self.tipo = tipo
        self.inicio_semana = _segunda_feira(datetime.date.today())

        titulo = "Mensal" if tipo == "mensal" else "Airbnb"
        self.title(f"Calendário — {titulo}")
        self.geometry("1000x640")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela)
        _colocar_no_topo(self)

        self.nomes_por_id = {
            prop["id"]: prop["nome"]
            for prop in propriedades.listar(incluir_inativas=True)
        }

        # Rótulo com o ID atrás do nome: duas propriedades podem
        # chamar-se quase o mesmo, e o dropdown devolve texto, não o
        # objeto — sem o ID, escolher a errada era silencioso.
        self.id_por_rotulo = {
            f"{prop['nome']} · {prop['id']}": prop["id"]
            for prop in propriedades.listar()
        }

        self._construir_barra_filtros()
        self._construir_navegacao()
        self._construir_tabela()
        self._construir_rodape()

        self._recarregar()

    # -- construção --------------------------------------------------

    def _construir_barra_filtros(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(16, 4))

        self.combo_propriedade = ctk.CTkOptionMenu(
            barra,
            values=[_OPCAO_TODAS] + sorted(self.id_por_rotulo),
            width=260,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_propriedade.set(_OPCAO_TODAS)
        self.combo_propriedade.pack(side="left")

        self.combo_disponibilidade = ctk.CTkOptionMenu(
            barra,
            values=list(_OPCOES_DISPONIBILIDADE),
            width=200,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._recarregar(),
        )
        self.combo_disponibilidade.set(_OPCOES_DISPONIBILIDADE[0])
        self.combo_disponibilidade.pack(side="left", padx=(10, 0))

    def _construir_navegacao(self):
        navegacao = ctk.CTkFrame(self, fg_color="transparent")
        navegacao.pack(fill="x", padx=20, pady=(6, 10))

        ctk.CTkButton(
            navegacao,
            text="< Anterior",
            width=100,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=lambda: self._mudar_semana(-1),
        ).pack(side="left")

        ctk.CTkButton(
            navegacao,
            text="Seguinte >",
            width=100,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=lambda: self._mudar_semana(1),
        ).pack(side="right")

        self.rotulo_semana = ctk.CTkLabel(
            navegacao,
            text="",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.rotulo_semana.pack(side="left", expand=True)

    def _construir_tabela(self):
        cartao_tabela = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao_tabela.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        cabecalho = ctk.CTkFrame(
            cartao_tabela,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")

        interno = ctk.CTkFrame(cabecalho, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            interno,
            text="UNIDADE",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=_LARGURA_NOME,
            anchor="w",
        ).pack(side="left")

        # Guardados para o `_recarregar` lhes trocar o texto: o dia do
        # mês muda a cada semana, o nome do dia não.
        self.rotulos_dias = []

        for indice in range(7):
            rotulo = ctk.CTkLabel(
                interno,
                text=_DIAS_SEMANA[indice],
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=_LARGURA_CELULA,
            )
            rotulo.pack(side="left")
            self.rotulos_dias.append(rotulo)

        ctk.CTkFrame(cartao_tabela, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x"
        )

        self.area_lista = ctk.CTkScrollableFrame(
            cartao_tabela, fg_color="transparent"
        )
        self.area_lista.pack(fill="both", expand=True)

    def _construir_rodape(self):
        legenda = ctk.CTkFrame(self, fg_color="transparent")
        legenda.pack(fill="x", padx=24)

        itens = (
            _LEGENDA_MENSAL if self.tipo == "mensal" else _LEGENDA_AIRBNB
        )

        for estado, texto in itens:
            fundo, cor_texto = _CORES_ESTADO[estado]
            caixa = ctk.CTkFrame(legenda, fg_color="transparent")
            caixa.pack(side="left", padx=(0, 18))

            ctk.CTkFrame(
                caixa,
                width=14,
                height=14,
                corner_radius=4,
                fg_color=fundo,
            ).pack(side="left", padx=(0, 6))

            ctk.CTkLabel(
                caixa,
                text=texto,
                text_color=cor_texto,
                font=ctk.CTkFont(size=11),
            ).pack(side="left")

        if self.tipo == "mensal":
            nota = (
                "Cada célula é uma noite: lugares ocupados / "
                "capacidade. Clicar abre o detalhe do dia."
            )
        else:
            nota = (
                "Cada célula é uma noite. Clicar abre o detalhe do dia."
            )

        ctk.CTkLabel(
            self,
            text=nota,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(8, 14))

    # -- carregamento / atualização ----------------------------------

    def _mudar_semana(self, semanas):
        self.inicio_semana += datetime.timedelta(weeks=semanas)
        self._recarregar()

    def _propriedade_escolhida_id(self):
        """ID da propriedade selecionada, ou None para "todas"."""
        return self.id_por_rotulo.get(self.combo_propriedade.get())

    def _so_com_disponibilidade(self):
        return self.combo_disponibilidade.get() == _OPCOES_DISPONIBILIDADE[1]

    def _recarregar(self):
        """Limpa e volta a desenhar a grelha da semana atual."""
        self.rotulo_semana.configure(
            text=_texto_intervalo(self.inicio_semana)
        )

        for indice, rotulo in enumerate(self.rotulos_dias):
            dia = self.inicio_semana + datetime.timedelta(days=indice)
            rotulo.configure(text=f"{_DIAS_SEMANA[indice]}  {dia.day}")

        for widget in self.area_lista.winfo_children():
            widget.destroy()

        lista = unidades.listar(
            tipo=self.tipo,
            propriedade_id=self._propriedade_escolhida_id(),
        )
        lista.sort(
            key=lambda uni: (
                self.nomes_por_id.get(uni["propriedade_id"], ""),
                uni["nome"],
            )
        )

        indice_zebra = 0

        for uni in lista:
            estados = self._estados_da_semana(uni["id"])

            if estados is None:
                continue

            if self._so_com_disponibilidade() and not any(
                detalhe["estado"] in _ESTADOS_COM_VAGA for detalhe in estados
            ):
                continue

            self._desenhar_linha(uni, estados, indice_zebra % 2 == 1)
            indice_zebra += 1

        if indice_zebra == 0:
            ctk.CTkLabel(
                self.area_lista,
                text="Nenhuma unidade a mostrar com estes filtros.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            ).pack(pady=30)

    def _estados_da_semana(self, unidade_id):
        """Os sete estados de uma unidade, de segunda a domingo.

        Devolve None se a unidade deixar de existir a meio (só pode
        acontecer se for apagada noutra janela enquanto esta está
        aberta) — a linha é simplesmente saltada.
        """
        estados = []

        for indice in range(7):
            dia = self.inicio_semana + datetime.timedelta(days=indice)

            try:
                estados.append(unidades.estado_detalhe(unidade_id, dia))
            except ValueError:
                return None

        return estados

    def _desenhar_linha(self, uni, estados, tingida):
        """Desenha a linha de uma unidade: nome + sete células."""
        linha = ctk.CTkFrame(
            self.area_lista,
            fg_color=tema.LINHA_ALTERNADA if tingida else "transparent",
            corner_radius=0,
        )
        linha.pack(fill="x")

        interno = ctk.CTkFrame(linha, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            interno,
            text=uni["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            width=_LARGURA_NOME,
            anchor="w",
        ).pack(side="left")

        for indice, detalhe in enumerate(estados):
            dia = self.inicio_semana + datetime.timedelta(days=indice)
            self._desenhar_celula(interno, uni, dia, detalhe)

    def _desenhar_celula(self, master, uni, dia, detalhe):
        """Desenha uma noite: fundo pela cor do estado, texto pela
        proporção (mensal) ou vazio (Airbnb).
        """
        fundo, cor_texto = _CORES_ESTADO[detalhe["estado"]]

        moldura = ctk.CTkFrame(
            master,
            width=_LARGURA_CELULA,
            height=_ALTURA_CELULA,
            fg_color="transparent",
        )
        moldura.pack(side="left")
        moldura.pack_propagate(False)

        celula = ctk.CTkFrame(
            moldura,
            corner_radius=6,
            fg_color=fundo,
        )
        celula.pack(fill="both", expand=True, padx=2, pady=1)

        ctk.CTkLabel(
            celula,
            text=_texto_celula(detalhe, self.tipo),
            text_color=cor_texto,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(expand=True)

        _tornar_clicavel(
            celula, lambda: self._abrir_detalhe_dia(uni, dia, detalhe)
        )

    def _abrir_detalhe_dia(self, uni, dia, detalhe):
        """Abre o detalhe de uma noite.

        Espaço reservado: o ecrã de detalhe do dia (ecrã 7 dos
        wireframes) ainda não existe. Por agora mostra o que já se
        sabe da célula, para o clique dar sinal de vida e o percurso
        ficar testável.
        """
        linhas = [
            f"Unidade: {uni['nome']} ({uni['id']})",
            f"Noite: {dia.strftime('%d/%m/%Y')}",
            f"Estado: {detalhe['estado']}",
        ]

        if detalhe["capacidade"] is not None:
            linhas.append(
                f"Lugares: {detalhe['ocupados']}/{detalhe['capacidade']}"
            )

        componentes.mostrar_sucesso(
            "\n".join(linhas), titulo="Detalhe do dia"
        )