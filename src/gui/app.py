"""Janela principal da aplicação e popup de login.

Substitui o antigo "SelecionarUtilizadorModal" (placeholder sem
password) por um `LoginModal` a sério, que usa o módulo
`utilizadores.py` para validar credenciais.

ALTERAÇÕES v1.5.0 (17/09/2026):

  - `SelecionarUtilizadorModal` REMOVIDO. Substituído por
    `LoginModal` — pede utilizador e password, e valida contra
    `utilizadores.autenticar`.

  - O arranque da aplicação bloqueia até haver um login válido:
    sem login, a GUI principal não abre.

  - LOGOFF VERDADEIRO: "Trocar utilizador" fecha a janela toda
    (com confirmação prévia) e a aplicação reabre do zero — o
    `main_gui.py` deteta `self.reabrir` e cria uma nova
    `Aplicacao`. Não há Dashboard com dados do utilizador
    anterior em pano de fundo.

  - O `LoginModal` é bloqueante (`protocol("WM_DELETE_WINDOW")`
    desativado): não se fecha pelo "X". Tem um botão "Sair"
    discreto que fecha a aplicação inteira.

  - Volta ao Dashboard depois do login.

  - FEEDBACK VISUAL: como o `autenticar` demora ~0,4s (hash
    PBKDF2), o botão muda para "A valida credenciais" com
    pontos animados enquanto valida. Os campos, o botão "Entrar"
    e o botão "Sair" ficam desativados durante a validação.

  - SAÍDA: o botão "Sair" do LoginModal marca uma flag
    (`sair_pedido`) no PRÓPRIO LoginModal antes de destruir a
    Aplicacao. O `Aplicacao.__init__` lê essa flag depois do
    `wait_window` — se for True, termina sem desenhar o
    Dashboard (a app já foi destruída). O `winfo_exists()` não
    serve aqui: depois do `destroy()`, qualquer chamada ao Tk
    rebenta com "application has been destroyed".

ALTERAÇÕES v1.5.x (19/09/2026):

  - O item "Configurações" da sidebar passa a estar marcado com
    `"so_admin": True` — só aparece a utilizadores Master ou
    Admin. O Staff não vê o item (a barreira real está no
    próprio ecrã de Configurações e no módulo `configuracoes.py`,
    que validam o perfil em cada escrita; esta é a camada de
    conforto visual da sidebar).

  - Nova função `_itens_visiveis()` que filtra o `ITENS_MENU`
    conforme o perfil ativo. É passada à `BarraLateral` em vez
    da lista crua.
"""

import customtkinter as ctk

from pathlib import Path

import utilizadores
from . import tema
from . import componentes
from . import sessao
from .gui_dashboard import Dashboard
from .gui_clientes import ListaClientes
from .gui_contratos import ListaContratosMensais, ListaReservasAirbnb
from .gui_calendario import Calendario
from .gui_est_hub import EcraStock
from .gui_despesas import EcraDespesas
from .gui_responsaveis import ListaResponsaveis
from .gui_propriedades import ListaPropriedades
from .gui_relatorios import Relatorios
from .gui_configuracoes import Configuracoes
from .sessao import tipo_utilizador_ativo  # <<< NOVO >>> — filtro de itens

_PASTA_IMG = Path(__file__).resolve().parent.parent.parent / "img"
_ICONE_JANELA = _PASTA_IMG / "ico_hostel.png"


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
    {"tipo": "item", "texto": "Despesas", "ecra": EcraDespesas},
    {"tipo": "item", "texto": "Responsáveis", "ecra": ListaResponsaveis},
    # ---- SISTEMA ----------------------------------------------------
    {"tipo": "secao", "texto": "Sistema"},
    {"tipo": "item", "texto": "Relatórios", "ecra": Relatorios},
    {
        "tipo": "item",
        "texto": "Configurações",
        "ecra": Configuracoes,
        "so_admin": True,  # <<< NOVO >>> — só Master/Admin veem
    },
]


def _itens_visiveis():
    """Devolve a lista do ITENS_MENU filtrada pelo perfil ativo.

    <<< NOVO >>> — função acrescentada em 19/09/2026.

    Itens marcados com `so_admin=True` (como o "Configurações")
    só aparecem a Master ou Admin. Tudo o resto é visível a
    todos os perfis.

    Chamada uma única vez, na construção da `BarraLateral` —
    quando já há sessão ativa (o LoginModal já correu).
    """
    tipo = tipo_utilizador_ativo()
    e_administrativo = tipo in ("Admin", "Master")

    return [
        item
        for item in ITENS_MENU
        if not item.get("so_admin") or e_administrativo
    ]


_MENSAGENS_ERRO = {
    utilizadores.MOTIVO_NAO_ENCONTRADO: "Utilizador não encontrado.",
    utilizadores.MOTIVO_SEM_CREDENCIAL: (
        "Este utilizador ainda não tem credencial definida. "
        "Peça a um Master."
    ),
    utilizadores.MOTIVO_PASSWORD_ERRADA: "Password incorreta.",
    utilizadores.MOTIVO_INATIVO: (
        "Esta conta está inativa. Contacte um Master."
    ),
}


class LoginModal(ctk.CTkToplevel):
    """Autenticação obrigatória ao arrancar a aplicação.

    Pede utilizador e password, valida contra
    `utilizadores.autenticar`, e define o responsável ativo da
    sessão. Bloqueante: não se fecha pelo "X" nem por Escape — só
    com credenciais válidas, ou pelo botão "Sair" (que fecha a
    aplicação inteira).

    FEEDBACK VISUAL: o PBKDF2 demora ~0,4s por autenticação. Nesse
    intervalo, o botão muda para "A validar credenciais" com os
    pontos animados, e os campos/botões ficam desativados.

    Em caso de falha, mantém o username escrito e limpa a
    password.

    SAÍDA: o botão "Sair" marca `self.sair_pedido = True` antes de
    destruir a Aplicacao. O `Aplicacao.__init__` lê esta flag
    depois do `wait_window` para saber se deve parar sem desenhar
    o Dashboard. A flag vive AQUI (no LoginModal), não no master
    — é uma variável Python pura, sobrevive à destruição do Tk,
    e não dá dores de cabeça ao Pylance.
    """

    _INTERVALO_ANIMACAO = 300

    def __init__(self, master):
        super().__init__(master)
        # Bloqueia o "X": só sai com login válido, ou com "Sair".
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        # Flag lida pelo `Aplicacao.__init__` depois do
        # `wait_window`. True = utilizador clicou "Sair" e a
        # Aplicacao vai ser destruída.
        self.sair_pedido = False

        self.title("Hostel Clean — Entrar")
        largura = 380
        altura = 400
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)

        x = self.winfo_screenwidth() // 2 - largura // 2
        y = self.winfo_screenheight() // 2 - altura // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")

        self._animacao_id = None
        self._animacao_passo = 0

        ctk.CTkLabel(
            self,
            text="Hostel Gestão",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(padx=24, pady=(32, 2))

        ctk.CTkLabel(
            self,
            text="Introduza as suas credenciais para entrar",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
        ).pack(padx=24, pady=(0, 24))

        ctk.CTkLabel(
            self,
            text="Utilizador",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)

        self.campo_username = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            height=36,
        )
        self.campo_username.pack(fill="x", padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Password",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)

        self.campo_password = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            height=36,
            show="•",
        )
        self.campo_password.pack(fill="x", padx=24, pady=(2, 8))

        self._bind_enter_username = self.campo_username.bind(
            "<Return>", lambda e: self._entrar()
        )
        self._bind_enter_password = self.campo_password.bind(
            "<Return>", lambda e: self._entrar()
        )

        self.erro = ctk.CTkLabel(
            self,
            text="",
            text_color=tema.TEXTO_ERRO,
            font=ctk.CTkFont(size=11),
            wraplength=320,
            justify="left",
            anchor="w",
        )
        self.erro.pack(fill="x", padx=24, pady=(4, 8))

        self.botao_entrar = ctk.CTkButton(
            self,
            text="Entrar",
            height=38,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._entrar,
        )
        self.botao_entrar.pack(fill="x", padx=24, pady=(4, 8))

        # Botão "Sair" — fecha a aplicação inteira. Discreto, sem
        # fundo, para não competir com o "Entrar".
        self.botao_sair = ctk.CTkButton(
            self,
            text="Sair",
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self._sair,
        )
        self.botao_sair.pack(fill="x", padx=24, pady=(0, 8))

        ctk.CTkLabel(
            self,
            text="v1.5.0",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(pady=(0, 16))

        self.campo_username.focus_set()

        self.after(
            10,
            lambda: (self.lift(), self.focus_force(), self.grab_set()),
        )

    # -- validação ---------------------------------------------------

    def _entrar(self):
        """Inicia a validação com feedback visual."""
        username = self.campo_username.get().strip()
        password = self.campo_password.get()

        self._bloquear_interface()
        self._arrancar_animacao()

        self.update_idletasks()

        registo, motivo = utilizadores.autenticar(username, password)

        self._parar_animacao()
        self._restaurar_interface()

        if registo is None:
            self.erro.configure(
                text=_MENSAGENS_ERRO.get(motivo, "Credenciais inválidas.")
            )
            self.campo_password.delete(0, "end")
            self.campo_password.focus_set()
            return

        try:
            sessao.definir_responsavel_ativo(registo["id"])
        except ValueError as erro:
            self.erro.configure(text=str(erro))
            self.campo_password.delete(0, "end")
            self.campo_password.focus_set()
            return

        self.grab_release()
        self.destroy()

    def _bloquear_interface(self):
        self.campo_username.configure(state="disabled")
        self.campo_password.configure(state="disabled")
        self.botao_entrar.configure(state="disabled")
        self.botao_sair.configure(state="disabled")

        self.campo_username.unbind("<Return>", self._bind_enter_username)
        self.campo_password.unbind("<Return>", self._bind_enter_password)

    def _restaurar_interface(self):
        self.campo_username.configure(state="normal")
        self.campo_password.configure(state="normal")
        self.botao_entrar.configure(
            state="normal",
            text="Entrar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
        )
        self.botao_sair.configure(state="normal")

        self._bind_enter_username = self.campo_username.bind(
            "<Return>", lambda e: self._entrar()
        )
        self._bind_enter_password = self.campo_password.bind(
            "<Return>", lambda e: self._entrar()
        )

    # -- animação dos pontos -----------------------------------------

    def _arrancar_animacao(self):
        self._animacao_passo = 0
        self._animar()

    def _animar(self):
        pontos = "." * (self._animacao_passo % 4)
        self.botao_entrar.configure(
            text=f"A validar credenciais{pontos}",
        )
        self._animacao_passo += 1

        self._animacao_id = self.after(self._INTERVALO_ANIMACAO, self._animar)

    def _parar_animacao(self):
        if self._animacao_id is not None:
            self.after_cancel(self._animacao_id)
            self._animacao_id = None

    # -- saída -------------------------------------------------------

    def _sair(self):
        """Fecha a aplicação inteira.

        Marca `self.sair_pedido = True` antes de destruir a
        Aplicacao. O `Aplicacao.__init__` lê esta flag depois do
        `wait_window` — se for True, termina sem desenhar o
        Dashboard (a app já foi destruída, e qualquer chamada ao
        Tk rebentava).

        A flag vive AQUI (no LoginModal), não no master — é uma
        variável Python pura, não depende do Tk.
        """
        self.sair_pedido = True
        self.grab_release()
        self.master.destroy()


class Aplicacao(ctk.CTk):
    """Janela principal da aplicação.

    Estrutura fixa: barra lateral de navegação à esquerda, área de
    conteúdo à direita.

    LOGOFF: quando o utilizador pede para trocar, `self.reabrir`
    fica True e a janela é destruída. O `main_gui.py` deteta isso
    e cria uma nova `Aplicacao` (que reabre o LoginModal do zero).
    """

    def __init__(self):
        tema.aplicar_tema()
        super().__init__()

        # Flag lida pelo `main_gui.py` depois do `mainloop()`.
        # False = terminar a aplicação de vez.
        # True = reabrir uma nova instância (o utilizador pediu
        # logoff).
        self.reabrir = False

        # Flag marcada quando o utilizador clica "Sair" no
        # LoginModal. Nesse caso a app foi destruída DENTRO do
        # `__init__`, e o `main_gui.py` não pode chamar
        # `mainloop()` num objeto já destruído. Lê-a antes de
        # arrancar o loop.
        self.terminar_pedido = False

        self.title("Hostel Clean — Gestão de Alojamento")

        try:
            self.iconbitmap(str(_ICONE_JANELA))
        except Exception:
            pass

        self.geometry("1100x700")
        self.minsize(950, 620)
        self.resizable(True, True)
        self.configure(fg_color=tema.COR_FUNDO)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # A barra lateral e a área de conteúdo são construídas
        # DEPOIS do login — o `_itens_visiveis()` só funciona com
        # sessão ativa (antes disso, `tipo_utilizador_ativo()`
        # devolve None e o filtro remove os itens `so_admin`).
        self.frame_atual = None

        self.update_idletasks()
        popup_login = LoginModal(self)
        self.wait_window(popup_login)

        if popup_login.sair_pedido:
            self.terminar_pedido = True
            return

        # Agora sim — já há sessão ativa.
        self.barra_lateral = componentes.BarraLateral(
            self,
            controlador=self,
            itens=_itens_visiveis(),
        )
        self.barra_lateral.configure(width=160)
        self.barra_lateral.grid(row=0, column=0, sticky="ns")
        self.barra_lateral.grid_propagate(False)

        self.area_conteudo = ctk.CTkFrame(
            self, corner_radius=0, fg_color=tema.COR_FUNDO
        )
        self.area_conteudo.grid(row=0, column=1, sticky="nsew")

        self.mostrar_frame(Dashboard)

    def mostrar_frame(self, classe_frame, **kwargs):
        """Troca o ecrã atual pelo indicado em classe_frame."""
        if self.frame_atual is not None:
            self.frame_atual.destroy()

        self.frame_atual = classe_frame(
            self.area_conteudo, controlador=self, **kwargs
        )
        self.frame_atual.pack(fill="both", expand=True)

        self.barra_lateral.marcar_ativo(classe_frame)

    def trocar_utilizador(self):
        """Logoff: fecha a janela e pede reabertura ao `main_gui`.

        Chamado pelo botão "Trocar utilizador" do rodapé da barra
        lateral. Mantém o nome antigo (`trocar_utilizador`) para
        não quebrar a BarraLateral, mas o comportamento mudou: já
        não abre o LoginModal por cima da aplicação — faz logoff
        verdadeiro.

        Pede confirmação antes (é uma operação "de saída"), limpa
        a sessão e marca `self.reabrir = True`. O `main_gui.py`
        vai criar uma nova `Aplicacao`, que abre o LoginModal do
        zero.
        """
        if not componentes.confirmar(
            "Tem a certeza que quer trocar de utilizador?\n\n"
            "A aplicação vai fechar e voltar ao ecrã de entrada.",
            titulo="Trocar utilizador",
        ):
            return

        sessao.limpar_responsavel_ativo()

        self.reabrir = True
        self.destroy()
