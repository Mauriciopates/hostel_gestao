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
de estado vem de `unidades.estados_da_semana(unidade_id, inicio)`,
que devolve os sete dias já classificados e com os números já
contados — a GUI só escolhe a cor e escreve o texto.

ALTERAÇÕES 13/09/2026 — "Detalhe do dia" passou de popup nativo
para modal próprio:

- `_abrir_detalhe_dia` deixa de chamar `componentes.mostrar_sucesso`
  (que abria um `messagebox` do sistema, igual em qualquer estado,
  sem aproveitar nada do que a célula já sabia: ID da ocupação,
  hóspede, valores, próximas datas livres).
- `DetalheDiaModal` substitui-o — um `CTkToplevel` com a mesma
  linguagem visual das outras tabelas da aplicação, adaptado ao
  regime e ao estado da célula clicada. Cinco ramos: livre,
  parcial, ocupado, reservado, manutenção.
- Airbnb mostra a reserva ativa (ID, hóspede, estadia, check-in,
  total) e, quando aplicável, uma faixa amarela com a próxima
  disponibilidade (`unidades.proxima_disponibilidade`).
- Mensal não tem hóspede principal (cada lugar tem o seu contrato)
  — o cartão mostra só a ficha da unidade e a contagem de lugares.
- Manutenção mostra a ficha e um aviso de "fora da oferta", sem
  ação principal.
- Botões do rodapé navegam para o ecrã correspondente
  (`ListaReservasAirbnb` ou `ListaPropriedades`) e fecham os dois
  popups empilhados (detalhe + calendário), pela mesma razão que
  levou o `PlantaLugaresModal` a fechar-se antes de navegar.

CONSOLIDAÇÃO DE HELPERS EM componentes.py (13/09/2026) — os
helpers visuais que estavam duplicados localmente passaram a viver
só no `componentes.py`:

- `_tornar_clicavel` local → `componentes.tornar_cliclavel`.
- `_colocar_no_topo` local → `componentes.colocar_no_topo`.
- `_formatar_valor` local → `componentes.formatar_valor`.

FASE 5, v1.4.0 (16-17/09/2026) — OTIMIZAÇÃO. O ecrã levava 2,9s a
responder a cada mudança de semana no Airbnb com 13 unidades.
Passou a ~0,2s. Quatro alterações, todas medidas antes e depois:

1. Uma leitura à base de dados por unidade, em vez de uma por dia.
   `unidades.estados_da_semana` substituiu sete chamadas a
   `estado_detalhe` — as leituras não recebem a data, por isso as
   sete traziam exatamente as mesmas linhas. 183 ligações ao MySQL
   por semana navegada passaram a 27 (o `repositorio` abre uma
   ligação nova por operação, a ~9ms cada).
2. Widget Pooling: as linhas da grelha são criadas uma vez e
   reutilizadas, em vez de destruídas e recriadas. Ver
   `_criar_linha_pool`.
3. Só se reconfigura o que mudou: no CustomTkinter um `configure`
   redesenha o widget e os filhos, e custava o mesmo que criar
   tudo de raiz. Ver `_atualizar_linha`.
4. Os filtros escolhidos sobrevivem ao fecho da janela, por regime
   (`_ULTIMO_FILTRO`), e a coluna da esquerda mostra a propriedade
   por baixo da unidade (`listar_com_propriedade`).

O que resta é quase tudo base de dados: dos ~220ms de um
recarregamento, ~210 são as leituras. Baixar isso implica mudar o
`repositorio` para reutilizar ligações, decisão parqueada para
depois de a v1.4.0 fechar.

Imports mantidos: `clientes` e `contratos` são usados pelo
`DetalheDiaModal` para ler o hóspede da reserva e o detalhe
Airbnb. `responsaveis` NÃO é preciso — o nome do hóspede vem do
`clientes.procurar`, não do responsável.
"""

import datetime
import tkinter.font as tkfont

import customtkinter as ctk

import clientes
import contratos
import propriedades
import unidades
from . import componentes
from . import tema

# Aliases locais para os helpers que viviam neste ficheiro e passaram
# a viver em componentes.py. Mantêm-se os nomes antigos com "_" para
# o corpo do ficheiro não ter de ser reescrito — mesma técnica já
# usada no gui_propriedades.py, gui_contratos.py e
# gui_est_requisicoes.py.
_tornar_clicavel = componentes.tornar_cliclavel
_colocar_no_topo = componentes.colocar_no_topo
_formatar_valor = componentes.formatar_valor


# Cabeçalhos das colunas. Índice 0 = segunda-feira, a mesma ordem
# que `datetime.date.weekday()` devolve.
_DIAS_SEMANA = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")

_MESES = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)

# Nomes por extenso, usados só no cabeçalho do DetalheDiaModal. Ficam
# aqui e não se calculam com `strftime('%A')` porque `strftime` sem
# locale configurado devolve o nome em inglês ("Saturday"), e mudar
# o locale global do Python só por causa disto trazia mais problemas
# do que resolvia.
_DIAS_SEMANA_EXTENSO = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)

_MESES_EXTENSO = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

# Larguras fixas, como nas tabelas de Gestão de Propriedades: com
# sete colunas de noites, deixar cada uma esticar sozinha desalinha
# o corpo do cabeçalho assim que um nome de unidade é mais comprido.
_LARGURA_NOME = 150
_LARGURA_CELULA = 100
_ALTURA_CELULA = 30

# Largura disponível para o TEXTO da coluna da esquerda, usada pelo
# `componentes.truncar_texto`. Quatro pixéis a menos do que a coluna,
# para o corte acontecer antes de a etiqueta encostar à célula
# seguinte (Fase 5, v1.4.0).
_LARGURA_TEXTO_NOME = _LARGURA_NOME - 4

# Altura de cada uma das duas linhas da coluna da esquerda. Somam
# exatamente `_ALTURA_CELULA`, para a linha da grelha não crescer
# quando o nome da propriedade passou a aparecer por baixo do nome da
# unidade (Fase 5, v1.4.0 — validado por mockup antes de codar).
_ALTURA_NOME = 16
_ALTURA_PROPRIEDADE = 14

# Estado devolvido por `unidades.estados_da_semana` -> (fundo, texto).
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

# As duas mensagens que ocupam o corpo da tabela quando não há
# linhas para mostrar. Reticências em três pontos ASCII e não no
# glifo "…", pela mesma razão das setas da navegação: no Windows o
# glifo Unicode saía como quadrado (tofu).
_TEXTO_A_CARREGAR = "A carregar calendário..."
_TEXTO_SEM_UNIDADES = "Nenhuma unidade a mostrar com estes filtros."

# Último filtro escolhido em cada regime, para o calendário reabrir
# como o utilizador o deixou (Fase 5, v1.4.0). Vive no módulo e não
# no ecrã `Calendario` porque esse frame é recriado a cada
# `mostrar_frame` — a memória tem de sobreviver a isso. Dura o que
# durar o processo: é conveniência de sessão, não configuração para
# gravar em disco.
_ULTIMO_FILTRO = {}


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


def _fonte_de_medida(tamanho):
    """Devolve um `tkinter.font.Font` com a mesma família e tamanho
    do `CTkFont` equivalente, para o `componentes.truncar_texto`
    poder medir texto (Fase 5, v1.4.0).

    A família sai do próprio `CTkFont` em vez de ser escrita à mão:
    assim a medida acompanha o que o CustomTkinter desenha mesmo, e
    continua certa se o tema mudar de fonte um dia. A diferença
    residual entre as duas (o helper mede com Tk, o ecrã desenha com
    CTk) é cosmética — corta um caráter a mais ou a menos no limite,
    nunca deixa texto a colidir.
    """
    base = ctk.CTkFont(size=tamanho)

    return tkfont.Font(family=base.cget("family"), size=base.cget("size"))


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

        # O controlador da aplicação é o que estava por trás do
        # ecrã `Calendario` (que é `tela` aqui) — guardado no
        # `__init__` porque o `DetalheDiaModal` precisa dele para
        # navegar ao fechar ("Abrir reserva" / "Abrir unidade").
        # Sem isto, o modal não teria como chamar `mostrar_frame`.
        self.controlador = tela.controlador

        titulo = "Mensal" if tipo == "mensal" else "Airbnb"
        self.title(f"Calendário — {titulo}")
        self.geometry("1000x640")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela)
        _colocar_no_topo(self)

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

        # Os 60ms (e não 10) são para o `_colocar_no_topo` — que
        # agenda o seu lift/focus/grab_set para os +10ms — ter
        # terminado antes de a construção da grelha começar. Com os
        # dois na mesma volta do loop de eventos, a janela aparecia e
        # piscava a meio da construção.
        self._atualizar_cabecalho()
        self._mostrar_mensagem(_TEXTO_A_CARREGAR)
        self.after(60, self._recarregar)

    # -- construção --------------------------------------------------

    def _construir_barra_filtros(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(16, 4))

        memoria = _ULTIMO_FILTRO.get(self.tipo, {})
        disponibilidade = memoria.get("disponibilidade")

        if disponibilidade not in _OPCOES_DISPONIBILIDADE:
            disponibilidade = _OPCOES_DISPONIBILIDADE[0]

        self.combo_propriedade = ctk.CTkOptionMenu(
            barra,
            values=[_OPCAO_TODAS] + sorted(self.id_por_rotulo),
            width=260,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._filtro_mudou(),
        )
        self.combo_propriedade.set(
            self._rotulo_valido(memoria.get("propriedade"))
        )
        self.combo_propriedade.pack(side="left")

        self.combo_disponibilidade = ctk.CTkOptionMenu(
            barra,
            values=list(_OPCOES_DISPONIBILIDADE),
            width=200,
            corner_radius=tema.RAIO_CAMPO,
            command=lambda _valor: self._filtro_mudou(),
        )
        self.combo_disponibilidade.set(disponibilidade)
        self.combo_disponibilidade.pack(side="left", padx=(10, 0))

    def _rotulo_valido(self, rotulo):
        """Devolve o rótulo de propriedade guardado, se ainda existir
        na lista de agora — senão, "Todas as propriedades".

        Uma propriedade pode ter sido desativada ou mudado de nome
        desde a última abertura. Nesse caso o rótulo antigo já não
        está entre as opções do dropdown, e pô-lo com `set()` deixava
        o combo a mostrar um texto que não corresponde a opção
        nenhuma — o `_propriedade_escolhida_id` não o encontrava no
        `id_por_rotulo`, devolvia None, e a grelha mostrava TODAS as
        propriedades por baixo de um rótulo que dizia só uma. Cair em
        "Todas as propriedades" é o comportamento honesto.
        """
        if rotulo and rotulo in self.id_por_rotulo:
            return rotulo

        return _OPCAO_TODAS

    def _filtro_mudou(self):
        """Um dos dois filtros mudou: guarda a escolha e redesenha."""
        self._guardar_filtros()
        self._recarregar()

    def _guardar_filtros(self):
        """Guarda o filtro atual para a próxima abertura do mesmo
        regime.

        Guarda os RÓTULOS e não os IDs: é o rótulo que o
        `CTkOptionMenu.set()` precisa de receber na abertura
        seguinte, e o `_rotulo_valido` já trata do caso de esse
        rótulo ter deixado de existir entretanto.

        Chamado a partir do `_filtro_mudou` e não do `_recarregar` de
        propósito — só interessa gravar quando o utilizador mexe num
        filtro, não a cada navegação de semana.
        """
        _ULTIMO_FILTRO[self.tipo] = {
            "propriedade": self.combo_propriedade.get(),
            "disponibilidade": self.combo_disponibilidade.get(),
        }

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

        # Guardados para o `_atualizar_cabecalho` lhes trocar o
        # texto: o dia do mês muda a cada semana, o nome do dia não.
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

        # Widget Pooling (Fase 5, v1.4.0): as linhas da grelha são
        # criadas uma vez e reutilizadas, em vez de destruídas e
        # recriadas a cada semana. `pool_linhas` guarda-as todas (só
        # cresce), `linhas_visiveis` diz quantas estão empacotadas
        # neste momento — as restantes ficam em `pack_forget`,
        # prontas a voltar. `rotulo_mensagem` segue a mesma ideia.
        self.pool_linhas = []
        self.linhas_visiveis = 0
        self.rotulo_mensagem = None

        # Fontes de medição do `componentes.truncar_texto`, criadas
        # uma vez por janela e não por linha — é o que a docstring
        # desse helper recomenda, e o que o gui_propriedades.py já
        # faz.
        self.fonte_nome = _fonte_de_medida(12)
        self.fonte_propriedade = _fonte_de_medida(10)

    def _construir_rodape(self):
        legenda = ctk.CTkFrame(self, fg_color="transparent")
        legenda.pack(fill="x", padx=24)

        itens = _LEGENDA_MENSAL if self.tipo == "mensal" else _LEGENDA_AIRBNB

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
            nota = "Cada célula é uma noite. Clicar abre o detalhe do dia."

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

    def _atualizar_cabecalho(self):
        """Escreve o intervalo da semana e o dia do mês em cada uma
        das sete colunas.

        Separado do `_recarregar` (Fase 5, v1.4.0) para a janela
        poder mostrar o cabeçalho certo enquanto a grelha ainda está
        a ser construída — ver o `after` no `__init__`.
        """
        self.rotulo_semana.configure(text=_texto_intervalo(self.inicio_semana))

        for indice, rotulo in enumerate(self.rotulos_dias):
            dia = self.inicio_semana + datetime.timedelta(days=indice)
            rotulo.configure(text=f"{_DIAS_SEMANA[indice]}  {dia.day}")

    def _unidades_a_mostrar(self):
        """As unidades do regime, já com o nome da propriedade e já
        ordenadas, filtradas pela propriedade escolhida.

        Usa `listar_com_propriedade` e não `listar` (Fase 5,
        v1.4.0): traz o `propriedade_nome` que a coluna da esquerda
        passou a mostrar, e já vem com `ORDER BY p.nome, u.nome` do
        SQL — que é exatamente a ordenação que este ecrã fazia à mão
        em Python, com um dicionário de nomes de propriedades lido
        numa query à parte. As duas coisas desapareceram.

        O filtro por propriedade fica em Python porque o
        `listar_com_propriedade` não o aceita, por decisão
        documentada na sua docstring. Com no máximo 22 unidades numa
        lista já em memória, é irrelevante — e continua a ser uma
        query, contra as duas de antes.
        """
        lista = unidades.listar_com_propriedade(tipo=self.tipo)
        propriedade_id = self._propriedade_escolhida_id()

        if propriedade_id is None:
            return lista

        return [
            uni for uni in lista if uni["propriedade_id"] == propriedade_id
        ]

    def _recarregar(self):
        """Volta a desenhar a grelha da semana atual, reutilizando as
        linhas do pool.

        Nunca destrói nada: as linhas a mais são escondidas com
        `pack_forget` e ficam à espera. Ver `_criar_linha_pool` e
        `_atualizar_linha` para o porquê de cada metade.
        """
        self._atualizar_cabecalho()

        if self.rotulo_mensagem is not None:
            self.rotulo_mensagem.pack_forget()

        visiveis = 0

        for uni in self._unidades_a_mostrar():
            estados = self._estados_da_semana(uni["id"])

            if estados is None:
                continue

            if self._so_com_disponibilidade() and not any(
                detalhe["estado"] in _ESTADOS_COM_VAGA for detalhe in estados
            ):
                continue

            entrada = self._obter_linha(visiveis)
            self._atualizar_linha(entrada, uni, estados, visiveis % 2 == 1)

            # Linhas com índice abaixo de `linhas_visiveis` já estavam
            # empacotadas do recarregamento anterior. As de índice
            # igual ou acima estavam escondidas (ou acabaram de ser
            # criadas) e voltam ao fim da pilha — como se preenche
            # sempre de 0 para cima e só se esconde pela cauda, a
            # ordem visual mantém-se correta.
            if visiveis >= self.linhas_visiveis:
                entrada["linha"].pack(fill="x")

            visiveis += 1

        for indice in range(visiveis, self.linhas_visiveis):
            self.pool_linhas[indice]["linha"].pack_forget()

        self.linhas_visiveis = visiveis

        if visiveis == 0:
            self._mostrar_mensagem(_TEXTO_SEM_UNIDADES)
    
    def _estados_da_semana(self, unidade_id):
        """Os sete estados de uma unidade, de segunda a domingo.

        Desde a Fase 5 (v1.4.0) é `unidades.estados_da_semana` que
        faz o trabalho: uma leitura à base de dados por unidade, em
        vez de uma por dia. Antes eram sete chamadas a
        `estado_detalhe`, cada uma a reler as mesmas linhas — as
        leituras não recebem a data, quem filtra por data é o Python
        a seguir.

        Devolve None se a unidade deixar de existir a meio (só pode
        acontecer se for apagada noutra janela enquanto esta está
        aberta) — a linha é simplesmente saltada.
        """
        try:
            return unidades.estados_da_semana(unidade_id, self.inicio_semana)
        except ValueError:
            return None

    def _criar_linha_pool(self):
        """Constrói uma linha da grelha vazia, sem a empacotar, e
        devolve as referências que o `_atualizar_linha` vai
        reconfigurar.

        Fase 5 (v1.4.0) — Widget Pooling. Antes, cada mudança de
        semana destruía todas as linhas e voltava a criá-las: medido
        a 16/09/2026 no Airbnb com 13 unidades, 261ms a destruir,
        372ms a criar e 645ms a desenhar. Os widgets são sempre os
        mesmos por linha — o que muda de semana para semana é só
        texto e cor.

        A coluna da esquerda é um bloco de altura fixa com duas
        etiquetas empilhadas: o nome da unidade e, por baixo e em
        cor secundária, o nome da propriedade. As duas alturas somam
        `_ALTURA_CELULA`, para a linha não crescer por causa da
        segunda etiqueta.

        Além dos widgets, o dicionário devolvido guarda o ÚLTIMO
        valor aplicado a cada um. Serve para o `_atualizar_linha`
        poder saltar os `configure` cujo valor não mudou — ver lá o
        porquê. Os valores iniciais são os que os widgets têm mesmo
        à nascença: a linha, o interior e o bloco do nome nascem
        "transparent", as etiquetas nascem sem texto, e a célula
        nasce com a cor por omissão do CTkFrame, que nunca é nenhuma
        das cores de estado (daí o None).
        """
        linha = ctk.CTkFrame(
            self.area_lista, fg_color="transparent", corner_radius=0
        )

        interno = ctk.CTkFrame(linha, fg_color="transparent")
        interno.pack(fill="x", padx=16, pady=4)

        bloco_nome = ctk.CTkFrame(
            interno,
            width=_LARGURA_NOME,
            height=_ALTURA_CELULA,
            fg_color="transparent",
        )
        bloco_nome.pack(side="left")
        bloco_nome.pack_propagate(False)

        rotulo_nome = ctk.CTkLabel(
            bloco_nome,
            text="",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            height=_ALTURA_NOME,
            anchor="w",
        )
        rotulo_nome.pack(fill="x")

        rotulo_propriedade = ctk.CTkLabel(
            bloco_nome,
            text="",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            height=_ALTURA_PROPRIEDADE,
            anchor="w",
        )
        rotulo_propriedade.pack(fill="x")

        celulas = []

        for _indice in range(7):
            moldura = ctk.CTkFrame(
                interno,
                width=_LARGURA_CELULA,
                height=_ALTURA_CELULA,
                fg_color="transparent",
            )
            moldura.pack(side="left")
            moldura.pack_propagate(False)

            celula = ctk.CTkFrame(moldura, corner_radius=6)
            celula.pack(fill="both", expand=True, padx=2, pady=1)

            rotulo_celula = ctk.CTkLabel(
                celula,
                text="",
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            rotulo_celula.pack(expand=True)

            # O clique é ligado UMA vez, aqui, e nunca mais. O que
            # muda de semana para semana é o conteúdo de `dados`,
            # que o `_atualizar_linha` reescreve — o handler lê-o no
            # momento do clique, por isso vê sempre a unidade e o
            # dia atuais.
            #
            # Não se religa a cada atualização porque o `bind` do
            # CustomTkinter NÃO substitui o handler anterior: o
            # CTkFrame e o CTkLabel sobrepõem-se ao `bind` do Tk e
            # forçam `add=True`, para não perderem as suas próprias
            # ligações internas (hover, etc.). Apanhado a
            # 16/09/2026 ao testar o pooling: religar a cada semana
            # acumulava handlers, e um clique abria um
            # `DetalheDiaModal` por cada semana navegada.
            dados = {"uni": None, "dia": None, "detalhe": None}
            _tornar_clicavel(
                celula,
                lambda dados=dados: self._clique_celula(dados),
            )

            celulas.append(
                {
                    "celula": celula,
                    "rotulo": rotulo_celula,
                    "dados": dados,
                    "fundo": None,
                    "texto": "",
                }
            )

        return {
            "linha": linha,
            "interno": interno,
            "bloco_nome": bloco_nome,
            "nome": rotulo_nome,
            "propriedade": rotulo_propriedade,
            "celulas": celulas,
            "cor": "transparent",
            "texto_nome": "",
            "texto_propriedade": "",
        }

    def _obter_linha(self, indice):
        """A linha número 'indice' do pool, criando-a se ainda não
        existir.

        O pool só cresce, nunca encolhe: uma linha escondida não
        custa nada a manter e volta a ser precisa assim que o filtro
        alargar outra vez.
        """
        while len(self.pool_linhas) <= indice:
            self.pool_linhas.append(self._criar_linha_pool())

        return self.pool_linhas[indice]

    def _atualizar_linha(self, entrada, uni, estados, tingida):
        """Escreve uma unidade numa linha já existente do pool,
        tocando só no que mudou.

        Cada `configure` é comparado com o último valor aplicado
        antes de ser chamado. Não é micro-otimização gratuita: no
        CustomTkinter um `configure` redesenha o widget E percorre
        os filhos a mudar-lhes o `bg_color`, o que os redesenha
        também. Com a cadeia linha → interior → (bloco do nome + 7
        molduras) → 7 células → 7 etiquetas, reconfigurar tudo
        custava o mesmo que criar tudo de raiz — medido a
        16/09/2026: 27ms por linha antes e depois do pooling, sem
        diferença nenhuma. Ao navegar semanas, o nome da unidade e o
        tom zebra quase nunca mudam, e boa parte das células mantém
        a cor.

        O tom zebra é posto na linha, no interior E no bloco do
        nome. Parece redundante (os dois últimos são transparentes e
        herdariam), mas um widget transparente resolve o fundo a
        partir do pai no momento em que é DESENHADO, e ao reutilizar
        widgets ninguém garante que os netos voltam a ser desenhados
        só porque o avô mudou de cor. O `configure(fg_color=...)` de
        um CTkFrame propaga o `bg_color` aos filhos DIRETOS e só a
        esses — daí ter de se dizer a cor em cada nível que tenha
        filhos a pintar.

        Os nomes passam pelo `componentes.truncar_texto` antes de
        serem escritos: a etiqueta tem largura fixa e cortaria a
        meio da letra, sem aviso nenhum. Com duas linhas isso
        acontece mais vezes, porque o nome da propriedade costuma
        ser mais comprido do que o da unidade.

        A cor do texto de uma célula anda sempre com a cor de fundo
        (saem as duas do mesmo par em `_CORES_ESTADO`), por isso é
        tratada dentro da mesma comparação; o texto tem a sua,
        porque muda sozinho de semana para semana no regime mensal.

        O clique NÃO se religa aqui — está ligado desde o
        `_criar_linha_pool` e lê o dicionário `dados` de cada
        célula, que é o que esta função reescreve.
        """
        cor_linha = tema.LINHA_ALTERNADA if tingida else "transparent"

        if entrada["cor"] != cor_linha:
            entrada["linha"].configure(fg_color=cor_linha)
            entrada["interno"].configure(fg_color=cor_linha)
            entrada["bloco_nome"].configure(fg_color=cor_linha)
            entrada["cor"] = cor_linha

        nome = componentes.truncar_texto(
            self.fonte_nome, uni["nome"], _LARGURA_TEXTO_NOME
        )

        if entrada["texto_nome"] != nome:
            entrada["nome"].configure(text=nome)
            entrada["texto_nome"] = nome

        propriedade = componentes.truncar_texto(
            self.fonte_propriedade,
            uni.get("propriedade_nome", ""),
            _LARGURA_TEXTO_NOME,
        )

        if entrada["texto_propriedade"] != propriedade:
            entrada["propriedade"].configure(text=propriedade)
            entrada["texto_propriedade"] = propriedade

        for indice, detalhe in enumerate(estados):
            celula = entrada["celulas"][indice]
            fundo, cor_texto = _CORES_ESTADO[detalhe["estado"]]
            texto = _texto_celula(detalhe, self.tipo)

            if celula["fundo"] != fundo:
                celula["celula"].configure(fg_color=fundo)
                celula["rotulo"].configure(text_color=cor_texto)
                celula["fundo"] = fundo

            if celula["texto"] != texto:
                celula["rotulo"].configure(text=texto)
                celula["texto"] = texto

            celula["dados"]["uni"] = uni
            celula["dados"]["dia"] = self.inicio_semana + datetime.timedelta(
                days=indice
            )
            celula["dados"]["detalhe"] = detalhe

    def _clique_celula(self, dados):
        """Abre o detalhe da noite que esta célula mostra AGORA.

        Lê o `dados` no momento do clique, e não no momento em que o
        clique foi ligado — é isso que permite ligar o clique uma
        única vez, quando a linha é criada, e nunca mais lhe tocar.

        O `None` só acontece numa linha criada e ainda não
        preenchida, situação que não chega ao ecrã (uma linha só é
        empacotada depois de atualizada) — mas sair em silêncio é
        mais barato do que rebentar.
        """
        if dados["uni"] is None:
            return

        self._abrir_detalhe_dia(dados["uni"], dados["dia"], dados["detalhe"])

    def _mostrar_mensagem(self, texto):
        """Mostra uma mensagem centrada no corpo da tabela, criando a
        etiqueta só da primeira vez que for precisa.

        Serve os dois casos em que não há linhas para mostrar: a
        janela ainda está a construir a grelha
        (`_TEXTO_A_CARREGAR`), ou os filtros não deixaram nenhuma
        unidade de fora (`_TEXTO_SEM_UNIDADES`). É a mesma etiqueta
        nos dois — só muda o texto.

        Também entra no pool: criar e destruir uma etiqueta a cada
        recarregamento vazio seria o mesmo desperdício das linhas,
        em ponto pequeno.
        """
        if self.rotulo_mensagem is None:
            self.rotulo_mensagem = ctk.CTkLabel(
                self.area_lista,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            )
        else:
            self.rotulo_mensagem.configure(text=texto)

        self.rotulo_mensagem.pack(pady=30)

    def _abrir_detalhe_dia(self, uni, dia, detalhe):
        """Abre o modal de detalhe de uma noite.

        Substitui o popup nativo que aqui estava (09/2026) — abria
        sempre com o mesmo formato de sistema operativo, sem
        aproveitar nada da informação que a célula já tinha: ID da
        ocupação, hóspede, valores, próximas datas livres. O
        `DetalheDiaModal` mostra isso tudo, com a mesma linguagem
        visual das outras tabelas da aplicação.

        Recebe tudo o que precisa do lado de fora (`uni`, `dia`,
        `detalhe`) para não ter de recalcular nada: a célula já
        sabe isto tudo, e recalculá-lo aqui era abrir uma janela
        para o estado divergir do que a célula mostra.
        """
        DetalheDiaModal(self, uni, dia, detalhe)


# =====================================================================
# Detalhe do dia
# =====================================================================


class DetalheDiaModal(ctk.CTkToplevel):
    """Popup com o detalhe de uma noite do calendário.

    Substitui o antigo `componentes.mostrar_sucesso` que respondia
    ao clique numa célula — o mesmo formato de sistema operativo
    para os cinco estados possíveis, sem IDs, sem valores, sem
    contexto. Este modal adapta-se ao regime da unidade:

    - Mensal: cartão com a unidade, contagem de lugares, preço
      base. Sem ocupação concreta — a entidade OcupacaoMensal não
      tem "hóspede principal", é uma unidade partilhada com N
      lugares (cada um com o seu contrato).
    - Airbnb: cartão com a reserva ativa (ID, hóspede, estadia,
      valores) e faixa amarela com a próxima disponibilidade, quando
      houver.
    - Manutenção (qualquer regime): cartão simples com o estado e
      um aviso de que a unidade está fora da oferta, sem ações.

    Recebe tudo do lado de fora (a `uni`, a `dia`, o `detalhe` da
    célula) — não vai buscar nada ao repositório por si própria,
    exceto o que for específico deste modal (reserva ativa no
    Airbnb, próxima disponibilidade) e que a célula não tem em
    mãos.
    """

    # Largura fixa. A altura varia consoante o ramo: o cartão da
    # reserva Airbnb é mais alto do que o da unidade mensal, e o do
    # manutenção mais baixo do que os dois.
    _LARGURA = 460

    # Altura por ramo. Cada valor foi escolhido a contar as linhas
    # de cada ramo + cabeçalho + rodapé + margens, não a olho: um
    # valor curto demais cortava o rodapé (bug apanhado no
    # `_ResumoDevolucaoModal`, ver gui_est_devolucoes.py), um longo
    # demais deixava uma faixa vazia feia.
    _ALTURAS = {
        "manutencao": 360,
        "livre": 400,
        "parcial": 420,
        "cheia": 440,
        "ocupado": 500,
        "reservado": 500,
    }

    def __init__(self, tela_semana, uni, dia, detalhe):
        super().__init__(tela_semana)
        self.tela_semana = tela_semana
        self.uni = uni
        self.dia = dia
        self.detalhe = detalhe
        self.estado = detalhe["estado"]

        self._construir_geometria()
        self._construir_cabecalho()
        self._construir_corpo()
        self._construir_rodape()

        self.transient(tela_semana)
        _colocar_no_topo(self)

    # -- geometria ----------------------------------------------------

    def _construir_geometria(self):
        """A janela não é redimensionável, por isso a altura tem de
        ser escolhida à cabeça. O título da janela é a data — dá
        contexto sem precisar de uma linha própria no corpo (que
        ficaria redundante com o cabeçalho).
        """
        self.title(f"Detalhe do dia — {self.dia.strftime('%d/%m/%Y')}")

        altura = self._ALTURAS.get(self.estado, 460)
        self.geometry(f"{self._LARGURA}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)

    # -- cabeçalho ----------------------------------------------------

    def _construir_cabecalho(self):
        """Dia da semana por extenso, data grande, chip de estado."""
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=22, pady=(18, 6))

        ctk.CTkLabel(
            cabecalho,
            text=_DIAS_SEMANA_EXTENSO[self.dia.weekday()],
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            cabecalho,
            text=(
                f"{self.dia.day} de "
                f"{_MESES_EXTENSO[self.dia.month - 1]} de "
                f"{self.dia.year}"
            ),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(2, 10))

        # Chip de estado. O texto mostrado depende do estado — no
        # parcial leva a contagem ("parcial · 2/4"), nos outros é só
        # a palavra. O par (fundo, texto) vem do mesmo sítio que o
        # `_atualizar_linha` usa, para os dois nunca poderem
        # discordar.
        fundo, cor_texto = _CORES_ESTADO[self.estado]
        texto_chip = _texto_chip_estado(self.estado, self.detalhe)

        ctk.CTkLabel(
            cabecalho,
            text=texto_chip,
            text_color=cor_texto,
            fg_color=fundo,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=12,
            pady=4,
            anchor="w",
        ).pack(anchor="w")

    # -- corpo --------------------------------------------------------

    def _construir_corpo(self):
        """Cartão principal + (só quando aplicável) faixa amarela da
        próxima disponibilidade.

        Ramifica por estado. Cada ramo é um método próprio, para
        este aqui não virar um `if/elif` de cinquenta linhas.
        """
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=22, pady=(10, 6))

        if self.estado == "manutencao":
            self._corpo_manutencao(corpo)
        elif self.uni["tipo"] == "mensal":
            self._corpo_mensal(corpo)
        else:
            self._corpo_airbnb(corpo)

    def _corpo_manutencao(self, master):
        """Unidade em manutenção — nem ocupação nem próxima
        disponibilidade. Só a ficha da unidade e o aviso de que está
        fora da oferta.
        """
        corpo_cartao = _criar_cartao(master)
        _linha_cartao(
            corpo_cartao,
            "Unidade",
            f"{self.uni['nome']} ({self.uni['id']})",
        )
        _linha_cartao(corpo_cartao, "Estado", "Em manutenção")
        _linha_cartao(corpo_cartao, "Regime", self.uni["tipo"])

        ctk.CTkLabel(
            master,
            text=(
                "Sem ações disponíveis enquanto a unidade estiver "
                "em manutenção."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=self._LARGURA - 60,
            justify="center",
        ).pack(fill="x", pady=(16, 0))

    def _corpo_mensal(self, master):
        """Unidade mensal — a entidade OcupacaoMensal não guarda o
        hóspede principal, cada lugar tem o seu contrato. Por isso
        não há cartão de reserva para mostrar; só a ficha da
        unidade e a contagem de lugares.
        """
        corpo_cartao = _criar_cartao(master)
        _linha_cartao(
            corpo_cartao,
            "Unidade",
            f"{self.uni['nome']} ({self.uni['id']})",
        )
        _linha_cartao(corpo_cartao, "Regime", "mensal")

        if self.detalhe["capacidade"] is not None:
            _linha_cartao(
                corpo_cartao,
                "Ocupação",
                f"{self.detalhe['ocupados']} de "
                f"{self.detalhe['capacidade']} lugares",
                forte=True,
            )
            _linha_cartao(
                corpo_cartao,
                "Preço base",
                _formatar_valor(self.uni["preco_base"]),
            )

    def _corpo_airbnb(self, master):
        """Unidade Airbnb — cartão da reserva ativa e (se houver)
        faixa amarela com a próxima disponibilidade.

        Procura a ocupação cujo intervalo cobre 'dia': o mesmo
        critério de sobreposição da secção 4, aplicado aqui para
        identificar QUAL reserva é a que a célula está a mostrar.
        """
        ocupacao = _ocupacao_ativa_no_dia(self.uni["id"], self.dia)

        corpo_cartao = _criar_cartao(master)

        if ocupacao is None:
            # Estado "livre" ou "reservado" numa unidade Airbnb: não
            # há reserva a decorrer neste dia. No "reservado" há uma
            # reserva futura, mas não é a que interessa mostrar aqui
            # (é a que ainda não começou); o detalhe fica só pela
            # ficha da unidade e pelo estado.
            _linha_cartao(
                corpo_cartao,
                "Unidade",
                f"{self.uni['nome']} ({self.uni['id']})",
            )
            _linha_cartao(corpo_cartao, "Regime", "Airbnb")
            _linha_cartao(
                corpo_cartao,
                "Estado",
                "Reservado" if self.estado == "reservado" else "Livre",
            )
        else:
            _linha_cartao(
                corpo_cartao,
                "Reserva",
                f"{ocupacao['id']} · reserva Airbnb",
                com_chip_id=True,
            )

            cliente = clientes.procurar(ocupacao["cliente_id"])
            nome_cliente = (
                f"{cliente['nome']} ({cliente['id']})"
                if cliente
                else ocupacao["cliente_id"]
            )
            _linha_cartao(corpo_cartao, "Hóspede", nome_cliente)

            noites = (ocupacao["data_fim"] - ocupacao["data_inicio"]).days
            _linha_cartao(
                corpo_cartao,
                "Estadia",
                f"{ocupacao['data_inicio'].strftime('%d/%m')} a "
                f"{ocupacao['data_fim'].strftime('%d/%m')} · "
                f"{noites} noites",
            )

            airbnb = contratos.detalhes_airbnb(ocupacao["id"])

            if airbnb is not None:
                if airbnb["check_in_tardio"]:
                    _linha_cartao(
                        corpo_cartao,
                        "Check-in",
                        f"Tardio · {airbnb['hora_chegada']}",
                    )
                else:
                    _linha_cartao(corpo_cartao, "Check-in", "Automatizado")

                _linha_cartao(
                    corpo_cartao,
                    "Total",
                    _formatar_valor(airbnb["preco_praticado"]),
                    total=True,
                )

        # Faixa amarela com a próxima disponibilidade — só quando
        # faz sentido: unidade Airbnb, ocupada agora ou reservada,
        # e existir mesmo uma janela futura. Sem isto, a faixa
        # aparecia vazia (ou pior: com um intervalo inventado).
        if self.estado in ("ocupado", "reservado"):
            janela = _proxima_disponibilidade_segura(self.uni["id"], self.dia)

            if janela is not None:
                inicio, fim = janela
                noites = (fim - inicio).days if fim is not None else None

                faixa = ctk.CTkFrame(
                    master,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=tema.RAIO_CAMPO,
                )
                faixa.pack(fill="x", pady=(12, 0))

                ctk.CTkLabel(
                    faixa,
                    text="PRÓXIMA DISPONIBILIDADE",
                    text_color=tema.TEXTO_AVISO,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    anchor="w",
                ).pack(fill="x", padx=14, pady=(10, 2))

                if fim is None:
                    texto_periodo = f"a partir de {inicio.strftime('%d/%m')}"
                    texto_sub = "sem fim previsto"
                else:
                    texto_periodo = (
                        f"{inicio.strftime('%d/%m')} a "
                        f"{fim.strftime('%d/%m')}"
                    )
                    texto_sub = f"{noites} noites livres"

                ctk.CTkLabel(
                    faixa,
                    text=texto_periodo,
                    text_color=tema.TEXTO_AVISO,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w",
                ).pack(fill="x", padx=14)

                ctk.CTkLabel(
                    faixa,
                    text=texto_sub,
                    text_color=tema.TEXTO_AVISO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                ).pack(fill="x", padx=14, pady=(0, 10))

    # -- rodapé -------------------------------------------------------

    def _construir_rodape(self):
        """Dois botões de largura igual: "Fechar" à esquerda, ação
        principal à direita. Qual é a ação principal depende do
        estado e do regime — ver `_rotulo_acao_principal` e
        `_executar_acao_principal`.
        """
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=22, pady=(4, 20), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Fechar",
            height=38,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            rodape,
            text=self._rotulo_acao_principal(),
            height=38,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._executar_acao_principal,
        ).pack(side="right", fill="x", expand=True, padx=(5, 0))

    def _rotulo_acao_principal(self):
        """Texto do botão principal, consoante o estado e o regime.

        - Manutenção → "Abrir unidade" (não há mais nada a fazer).
        - Mensal (qualquer estado) → "Abrir unidade".
        - Airbnb ocupado/reservado → "Abrir reserva".
        - Airbnb livre → "Abrir unidade".
        """
        if self.estado == "manutencao":
            return "Abrir unidade"

        if self.uni["tipo"] == "mensal":
            return "Abrir unidade"

        if self.estado in ("ocupado", "reservado"):
            return "Abrir reserva"

        return "Abrir unidade"

    def _executar_acao_principal(self):
        """Navega para o destino correspondente e fecha os dois
        popups empilhados.

        Três destinos possíveis, decididos por regime e estado:

        - Airbnb ocupado/reservado → `ListaReservasAirbnb` (a tabela
          de reservas, onde a reserva em causa vive).
        - Mensal (qualquer estado) ou Airbnb livre → abre o
          `UnidadesDaPropriedadeModal` da propriedade a que a
          unidade pertence, para se ver a unidade em concreto.
          Não `ListaPropriedades`, que é a lista de propriedades —
          ir para lá não mostrava a unidade nenhuma (bug apanhado
          pelo aluno, 13/09/2026: "ao clicar está indo à
          propriedade e não à unidade").

        O `UnidadesDaPropriedadeModal` é aberto como popup próprio,
        não navegando o ecrã principal — é o mesmo que o clique no
        ID da propriedade faz em `ListaPropriedades`. Assim o
        utilizador vê logo as unidades da propriedade certa, sem
        ter de passar pela lista de propriedades toda.

        A ordem importa: fecha o modal de detalhe e o calendário
        ANTES de abrir o popup das unidades. Deixar a pilha de
        popups aberta punha o novo popup por baixo dos antigos.
        """
        from gui.gui_contratos import ListaReservasAirbnb
        from gui.gui_propriedades import (
            ListaPropriedades,
            UnidadesDaPropriedadeModal,
        )

        tela_semana = self.tela_semana
        controlador = tela_semana.controlador

        # Airbnb ocupado ou reservado → vai para a tabela de
        # reservas. É o único caso em que "Abrir reserva" faz
        # sentido: a reserva em causa está nessa lista.
        if self.uni["tipo"] == "airbnb" and self.estado in (
            "ocupado",
            "reservado",
        ):
            self.destroy()
            tela_semana.destroy()
            controlador.mostrar_frame(ListaReservasAirbnb)
            return

        # Todos os outros casos → unidades da propriedade a que a
        # unidade pertence. Precisamos do registo da propriedade
        # (não só do id) porque `UnidadesDaPropriedadeModal` espera
        # o dicionário completo — usa `prop["nome"]` e `prop["id"]`
        # no cabeçalho.
        propriedade = propriedades.procurar(self.uni["propriedade_id"])

        if propriedade is None:
            # A unidade existe mas a propriedade já não — só
            # acontece se algo foi apagado noutra janela. Cai para
            # a lista de propriedades, que é o ecrã mais próximo
            # de "algo a ver".
            self.destroy()
            tela_semana.destroy()
            controlador.mostrar_frame(ListaPropriedades)
            return

        # Fecha os dois popups antes de abrir o novo. A ordem
        # importa: `UnidadesDaPropriedadeModal` é `transient` da
        # `tela_lista` que recebe, e essa `tela_lista` tem de estar
        # visível quando o popup abre — se fosse `ListaPropriedades`
        # por trás dos popups antigos, o novo popup abria por cima
        # de uma janela escondida.
        #
        # Para o `UnidadesDaPropriedadeModal` funcionar, precisa de
        # uma `tela_lista` — um objeto com `.controlador` e
        # `._recarregar()`. O ecrã principal (`ListaPropriedades`)
        # é exatamente isso, e é o sítio onde este popup vive
        # normalmente. Por isso: navega primeiro para
        # `ListaPropriedades`, e só depois abre o popup das
        # unidades por cima.
        self.destroy()
        tela_semana.destroy()

        controlador.mostrar_frame(ListaPropriedades)

        # `controlador.frame_atual` é o `ListaPropriedades` que
        # acabámos de criar em `mostrar_frame`. Passá-lo como
        # `tela_lista` ao popup é o que faz o botão "Voltar" e o
        # `_recarregar` funcionarem como se o popup tivesse sido
        # aberto a partir do clique no ID da propriedade.
        UnidadesDaPropriedadeModal(controlador.frame_atual, propriedade)


# =====================================================================
# Helpers do DetalheDiaModal
#
# Vivem fora da classe para o corpo dos métodos ficar mais curto:
# são construções repetidas (cartão, linha rótulo/valor) e pequenas
# consultas de leitura que não mudam de comportamento com o estado.
# =====================================================================


def _texto_chip_estado(estado, detalhe):
    """Devolve o texto a mostrar dentro do chip de estado no
    cabeçalho. O parcial leva a contagem; os outros ficam-se pela
    palavra.
    """
    if estado == "parcial":
        return f"parcial · {detalhe['ocupados']}/{detalhe['capacidade']}"

    return estado


def _criar_cartao(master):
    """Cartão interior do modal — borda fina, raio 14, mesmo padrão
    dos cartões dos formulários da aplicação.

    Devolve o corpo do cartão (o frame interior), não o cartão em
    si: quem chama usa sempre o corpo, nunca o cartão, e devolver o
    corpo poupa uma linha em cada sítio.
    """
    cartao = ctk.CTkFrame(
        master,
        fg_color=tema.COR_FUNDO,
        border_width=1,
        border_color=tema.COR_BORDA,
        corner_radius=tema.RAIO_CARTAO,
    )
    cartao.pack(fill="x")

    corpo = ctk.CTkFrame(cartao, fg_color="transparent")
    corpo.pack(fill="x", padx=14, pady=12)

    return corpo


def _linha_cartao(
    corpo, rotulo, valor, forte=False, total=False, com_chip_id=False
):
    """Uma linha rótulo → valor dentro de um cartão.

    O rótulo fica à esquerda, largura fixa (130px), em cor
    secundária — mesma convenção de todos os formulários. O valor
    fica à direita, alinhado à esquerda da sua coluna.

    'forte' e 'total' são dois graus de destaque: 'total' é mais
    forte do que 'forte' (é o valor que interessa). Isto porque o
    valor da ocupação merece destaque, mas o total da reserva
    merece outro.

    'com_chip_id' separa o valor em duas partes (ID + descrição) e
    põe o ID num chip colorido — usado só na linha "Reserva", onde
    o ID é o que se procura ao abrir isto.
    """
    linha = ctk.CTkFrame(corpo, fg_color="transparent")
    linha.pack(fill="x", pady=3)

    ctk.CTkLabel(
        linha,
        text=rotulo,
        text_color=tema.COR_TEXTO_SECUNDARIO,
        font=ctk.CTkFont(size=12),
        width=130,
        anchor="w",
    ).pack(side="left")

    if com_chip_id and " · " in valor:
        id_parte, tipo_parte = valor.split(" · ", 1)

        bloco = ctk.CTkFrame(linha, fg_color="transparent")
        bloco.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            bloco,
            text=id_parte,
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=8,
            pady=2,
        ).pack(side="left")

        ctk.CTkLabel(
            bloco,
            text=tipo_parte,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        return

    if total:
        cor = tema.AZUL_PRINCIPAL
        fonte = ctk.CTkFont(size=13, weight="bold")
    elif forte:
        cor = tema.COR_TEXTO
        fonte = ctk.CTkFont(size=12, weight="bold")
    else:
        cor = tema.COR_TEXTO
        fonte = ctk.CTkFont(size=12)

    ctk.CTkLabel(
        linha,
        text=valor,
        text_color=cor,
        font=fonte,
        anchor="w",
    ).pack(side="left", fill="x", expand=True)


def _ocupacao_ativa_no_dia(unidade_id, dia):
    """Devolve a ocupação Airbnb ativa da unidade que cobre 'dia',
    ou None se a unidade estiver livre.

    Sobreposição no mesmo critério da secção 4: inicio < fim_janela
    E dia < fim, com fim_janela = dia + 1 dia. Não é uma pergunta
    que a célula já responda — a célula só sabe o estado ("ocupado"),
    não qual das reservas é a ativa. Como a unidade Airbnb é
    indivisível, só pode haver uma ao mesmo tempo, mas o critério
    continua a ser o de sobreposição (não uma igualdade de datas),
    para nunca apanhar uma reserva adjacente por engano.
    """
    fim_janela = dia + datetime.timedelta(days=1)

    for ocupacao in contratos.listar(unidade_id=unidade_id, tipo="airbnb"):
        if ocupacao["data_inicio"] < fim_janela and dia < ocupacao["data_fim"]:
            return ocupacao

    return None


def _proxima_disponibilidade_segura(unidade_id, dia):
    """Chama `unidades.proxima_disponibilidade` a partir do
    calendário, apanhando o ValueError se a unidade não for Airbnb
    ou já não existir.

    O calendário já sabe que a unidade é Airbnb (está no ramo certo
    do `_corpo_airbnb`), mas `proxima_disponibilidade` continua a
    validar — e uma corrida entre abrir o modal e a unidade ser
    apagada noutra janela é teoricamente possível. Não vale a pena
    rebentar o modal por causa disso: o ramo certo simplesmente não
    mostra a faixa.
    """
    try:
        return unidades.proxima_disponibilidade(unidade_id, dia)
    except ValueError:
        return None