import customtkinter as ctk

from pathlib import Path
from PIL import Image

import responsaveis
from . import tema
from . import componentes
from . import sessao
from .gui_dashboard import Dashboard
from .gui_clientes import ListaClientes
from .gui_contratos import ListaContratosMensais, ListaReservasAirbnb
from .gui_calendario import Calendario
from .gui_est_hub import EcraStock
from .gui_responsaveis import ListaResponsaveis
from .gui_propriedades import ListaPropriedades
from .gui_relatorios import Relatorios
from .gui_configuracoes import Configuracoes

# =====================================================================
# Caminho do ícone da janela
#
# O `img/` está na raiz do projeto, e este ficheiro está em
# `src/gui/`. Mesmo esquema do `componentes.py`: calcula-se a partir
# de `__file__` (o caminho DESTE ficheiro), não de um caminho
# relativo frágil.
#
# O ícone (`ico_hostel.png`) aparece na barra de título da janela e
# na barra de tarefas do sistema operativo. É diferente do logo da
# sidebar (`ico_hostel_transparente.png`): este é quadrado, pensado
# para ficar bem num espaço quadrado pequeno.
# =====================================================================

_PASTA_IMG = Path(__file__).resolve().parent.parent.parent / "img"

_ICONE_JANELA = _PASTA_IMG / "ico_hostel.png"


# Itens da barra lateral, organizados em secções (decisão do
# aluno, 13/09/2026, ao desenhar o Dashboard): a lista simples
# deixou de caber quando os ecrãs passaram de 4 a 10. As secções
# agrupam por função — PAINEL (o que se vê ao abrir), GESTÃO (o
# que se cadastra), OPERAÇÃO (o dia-a-dia), SISTEMA (o que ainda
# por implementar). O widget `componentes.BarraLateral` já
# suportava `tipo: "secao"` desde o início — esta é a primeira
# vez que é usado.
#
# Ordem dentro de cada secção pensada pelo fluxo:
#
# - PAINEL: Dashboard primeiro — é o ecrã de arranque, o que a
#   pessoa vê assim que escolhe o responsável ativo.
# - GESTÃO: primeiro o que se cadastra (Propriedades, Clientes),
#   depois o que se consulta/usa a partir daí (Contratos Mensais,
#   Reservas Airbnb).
# - OPERAÇÃO: Calendário antes de Stock — o calendário é consulta
#   diária, o stock é mais esporádico.
# - SISTEMA: Relatórios e Configurações, ambos por implementar
#   (os ecrãs abrem e dizem isso mesmo — ver gui_relatorios.py e
#   gui_configuracoes.py).
#
# Notas de decisões anteriores que continuam em vigor:
#
# 07/09/2026: "Novo Contrato Mensal" saiu da barra lateral — ficava
# parecido demais com "Contrato Mensal" (a lista), um debaixo do
# outro, só a palavra "Novo" a distinguir. Continua acessível pelo
# botão "+ Novo Contrato" dentro do próprio ecrã "Contrato Mensal".
#
# 07/09/2026: "Planta de Lugares" saiu da barra lateral — só se
# chega lá pelo botão "Abrir Mapa" de uma unidade mensal, dentro do
# popup de unidades da Gestão de Propriedades.
#
# 08/09/2026: "Stock" e não "Requisições" — o hub que ele abre já
# tem um cartão "Requisições" lá dentro.
ITENS_MENU = [
    # ---- PAINEL -----------------------------------------------------
    {"tipo": "secao", "texto": "Painel"},
    {"tipo": "item", "texto": "Dashboard", "ecra": Dashboard},
    # ---- GESTÃO -----------------------------------------------------
    {"tipo": "secao", "texto": "Gestão"},
    {
        "tipo": "item",
        "texto": "Gestão de Propriedades",
        "ecra": ListaPropriedades,
    },
    {"tipo": "item", "texto": "Clientes", "ecra": ListaClientes},
    {
        "tipo": "item",
        "texto": "Contratos Mensais",
        "ecra": ListaContratosMensais,
    },
    {
        "tipo": "item",
        "texto": "Reservas Airbnb",
        "ecra": ListaReservasAirbnb,
    },
    # ---- OPERAÇÃO ---------------------------------------------------
    {"tipo": "secao", "texto": "Operação"},
    {"tipo": "item", "texto": "Calendário", "ecra": Calendario},
    {"tipo": "item", "texto": "Stock", "ecra": EcraStock},
    {"tipo": "item", "texto": "Responsáveis", "ecra": ListaResponsaveis},
    # ---- SISTEMA ----------------------------------------------------
    {"tipo": "secao", "texto": "Sistema"},
    {"tipo": "item", "texto": "Relatórios", "ecra": Relatorios},
    {"tipo": "item", "texto": "Configurações", "ecra": Configuracoes},
]


class SelecionarUtilizadorModal(ctk.CTkToplevel):
    """ "Quem está a usar a aplicação?" — obrigatório ao arrancar.

    Substituto provisório de um ecrã de login a sério, enquanto não
    existir um módulo `utilizadores.py` com conta e palavra-passe
    próprios (decisão 09/09/2026: fica documentado aqui para não se
    perder quando esse módulo chegar — a chamada a
    `sessao.definir_responsavel_ativo` é o único ponto a substituir
    então, o resto do ecrã pode manter-se).

    Sem isto, a sessão arrancava sempre com
    `sessao.obter_responsavel_ativo()` a devolver `None` — só se
    resolvia navegando manualmente a Responsáveis → Gerir → "Definir
    como responsável ativo" — e toda a gente esquecia esse passo,
    vendo "Defina um responsável ativo..." na primeira ação que
    exige um responsável (Confirmar requisição, Confirmar receção,
    Rejeitar requisição, Reportar sobra, Aceitar devolução).

    Modal a sério: `protocol("WM_DELETE_WINDOW", ...)` desativa o
    "X" da janela, e só o botão "Entrar" fecha o popup — não dá para
    passar à frente sem escolher (a não ser que ainda não exista
    responsável nenhum, único caso em que "Continuar" aparece, para
    não trancar quem está a arrancar a aplicação pela primeira vez).
    """

    def __init__(self, master):
        super().__init__(master)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self.responsaveis_disponiveis = responsaveis.listar()
        largura = 380
        altura = 230 if self.responsaveis_disponiveis else 190
        self.title("Hostel Clean")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)

        x = self.winfo_screenwidth() // 2 - largura // 2
        y = self.winfo_screenheight() // 2 - altura // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")

        ctk.CTkLabel(
            self,
            text="Quem está a usar a aplicação?",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(padx=20, pady=(24, 4))

        if not self.responsaveis_disponiveis:
            self._sem_responsaveis()
        else:
            self._escolher_responsavel()

        self.after(
            10,
            lambda: (self.lift(), self.focus_force(), self.grab_set()),
        )

    def _sem_responsaveis(self):
        """Ainda não há nenhum responsável criado — acontece só na
        primeira utilização. "Continuar" evita trancar a aplicação
        num ciclo sem saída: cria-se o primeiro responsável já
        dentro do ecrã "Responsáveis", e da próxima vez que a
        aplicação arrancar já há por quem escolher aqui.
        """
        ctk.CTkLabel(
            self,
            text=(
                "Ainda não há nenhum responsável criado. Continue e "
                'crie um em "Responsáveis" — da próxima vez que '
                "abrir a aplicação já pode escolher aqui."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            wraplength=320,
            justify="center",
        ).pack(padx=20, pady=(8, 16))

        ctk.CTkButton(
            self,
            text="Continuar",
            height=36,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._sair_sem_escolher,
        ).pack(padx=20, pady=(0, 20), fill="x")

    def _escolher_responsavel(self):
        rotulos = [r["nome"] for r in self.responsaveis_disponiveis]
        self.id_por_rotulo = {
            r["nome"]: r["id"] for r in self.responsaveis_disponiveis
        }

        self.combo = ctk.CTkOptionMenu(
            self,
            values=rotulos,
            corner_radius=tema.RAIO_CAMPO,
            width=300,
        )
        self.combo.set(rotulos[0])
        self.combo.pack(padx=20, pady=(14, 20))

        ctk.CTkButton(
            self,
            text="Entrar",
            height=36,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._entrar,
        ).pack(padx=20, pady=(0, 20), fill="x")

    def _entrar(self):
        escolhido_id = self.id_por_rotulo.get(self.combo.get())

        if escolhido_id is not None:
            sessao.definir_responsavel_ativo(escolhido_id)

        self.grab_release()
        self.destroy()

    def _sair_sem_escolher(self):
        self.grab_release()
        self.destroy()


class Aplicacao(ctk.CTk):
    """Janela principal da aplicação. Estrutura fixa: barra lateral
    de navegação à esquerda (altura toda da janela), área de
    conteúdo à direita — onde os frames de cada ecrã são trocados
    consoante a navegação (decisão: tudo em frames dentro desta
    janela, exceto diálogos pontuais, que usam CTkToplevel). Cada
    ecrã traz o seu próprio cabeçalho (componentes.Cabecalho); não
    há cabeçalho global.
    """

    def __init__(self):
        tema.aplicar_tema()
        super().__init__()

        self.title("Hostel Clean — Gestão de Alojamento")

        # Ícone da janela (barra de título + barra de tarefas do
        # sistema). Tem de ser aplicado ANTES da janela ficar
        # visível — depois disso, alguns gestores de janelas
        # ignoram a chamada.
        #
        # `iconbitmap` espera um `.ico` no Windows e um `.png` no
        # Linux/Mac; para funcionar em ambos, o caminho é passado
        # como string e o `iconphoto(True, ...)` (usado abaixo)
        # cobre o caso do PNG. O `try/except` evita rebentar o
        # arranque se o ficheiro não existir (por exemplo, num
        # ambiente onde o `img/` não foi copiado) — a janela abre
        # sem ícone, mas abre.
        try:
            self.iconbitmap(str(_ICONE_JANELA))
        except Exception:
            pass

        # Janela redimensionável, com maximizar/minimizar (07/09/2026
        # — pedido do aluno: o tamanho fixo, sem margem nenhuma, era
        # parte do aperto que as tabelas sentiam para caber tudo).
        # Tamanho de arranque um pouco maior do que o fixo de antes
        # (900x700); `minsize` evita encolher a ponto de as colunas
        # deixarem de caber — grid_columnconfigure(1, weight=1) logo
        # abaixo já fazia a área de conteúdo esticar, só faltava
        # permitir à própria janela esticar também.
        self.geometry("1100x700")
        self.minsize(950, 620)
        self.resizable(True, True)
        self.configure(fg_color=tema.COR_FUNDO)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sem cabeçalho global: cada ecrã já traz o seu próprio
        # componentes.Cabecalho (decisão desde a Parte 2) — um frame
        # extra aqui só criava uma faixa vazia acima do menu e do
        # ecrã, sem função nenhuma (visível pela primeira vez agora
        # que a barra lateral é real). Decisão do aluno, 07/09/2026.
        #
        # Largura de 160px (era 150px até 13/09/2026): o logo da
        # sidebar (`ico_hostel_transparente.png`) é renderizado com
        # 110px de largura, mais 12px de padding lateral de cada
        # lado — precisa de pelo menos 134px. Os 160 dão folga para
        # o "Gestão de Propriedades" (o item mais comprido) caber
        # sem truncar.
        self.barra_lateral = componentes.BarraLateral(
            self, controlador=self, itens=ITENS_MENU
        )
        self.barra_lateral.configure(width=160)
        self.barra_lateral.grid(row=0, column=0, sticky="ns")
        self.barra_lateral.grid_propagate(False)

        self.area_conteudo = ctk.CTkFrame(
            self, corner_radius=0, fg_color=tema.COR_FUNDO
        )
        self.area_conteudo.grid(row=0, column=1, sticky="nsew")

        self.frame_atual = None

        # "Quem está a usar a aplicação?" (decisão 09/09/2026, ver
        # SelecionarUtilizadorModal acima): pergunta-se ANTES do
        # ecrã inicial, e `wait_window` bloqueia o arranque até
        # fechar — impede chegar a qualquer ecrã sem um responsável
        # ativo definido, sem depender de ninguém se lembrar de ir a
        # Responsáveis fazê-lo à mão.
        self.update_idletasks()
        popup_utilizador = SelecionarUtilizadorModal(self)
        self.wait_window(popup_utilizador)

        # Ecrã inicial ao arrancar a aplicação — Dashboard desde
        # 13/09/2026 (antes era Gestão de Propriedades, decisão de
        # 07/09/2026 que ficou documentada como provisória "enquanto
        # não existir Dashboard"). O Dashboard mostra os números do
        # dia e os alertas por resolver, que é o que interessa ao
        # abrir a aplicação — as listas de Propriedades/Clientes
        # continuam a um clique na barra lateral.
        self.mostrar_frame(Dashboard)

    def mostrar_frame(self, classe_frame, **kwargs):
        """Troca o ecrã atual pelo indicado em classe_frame.

        Destrói o frame anterior (se existir) e cria uma nova
        instância de classe_frame dentro de area_conteudo, passando-
        -se a si própria como "controlador" — é assim que o ecrã
        chama de volta mostrar_frame para navegar para outro, ou
        acede a coisas partilhadas (ex. sessao). kwargs são
        argumentos extra específicos do ecrã (ex.: o id de uma
        unidade a abrir).

        Depois de trocar o ecrã, avisa a barra lateral para marcar
        o botão correspondente como ativo (azul). O `classe_frame`
        é usado como chave — o mesmo objeto que a barra lateral
        guardou em `_botoes_por_ecra` quando criou o botão. Se a
        classe não estiver na barra (ex.: `NovoContratoMensal`, que
        só se abre por um caminho específico), o `marcar_ativo`
        simplesmente limpa todos os botões — comportamento
        aceitável, ver o docstring de `BarraLateral.marcar_ativo`.
        """
        if self.frame_atual is not None:
            self.frame_atual.destroy()

        self.frame_atual = classe_frame(
            self.area_conteudo, controlador=self, **kwargs
        )
        self.frame_atual.pack(fill="both", expand=True)

        self.barra_lateral.marcar_ativo(classe_frame)

    def trocar_utilizador(self):
        """Reabre o "Quem está a usar a aplicação?" a qualquer altura
        (botão "Trocar utilizador" da barra lateral, 09/09/2026) —
        mesmo popup do arranque, sem precisar de fechar e reabrir a
        aplicação para mudar de responsável ativo.

        Depois de fechar o popup, volta sempre a Gestão de
        Propriedades, em vez de tentar reconstruir o ecrã em que a
        pessoa estava: alguns ecrãs recebem argumentos próprios (ex.
        uma unidade específica) que `mostrar_frame` não tem como
        adivinhar aqui.
        """
        popup_utilizador = SelecionarUtilizadorModal(self)
        self.wait_window(popup_utilizador)
        self.mostrar_frame(ListaPropriedades)
