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

import logging
import sys
import tkinter
import traceback
from types import TracebackType

import customtkinter as ctk

import config
import estoque
import servidores
import termos
import utilizadores
from . import tema
from . import componentes
from . import sessao
from .dashboard.gui_dash_hub import Dashboard
from .gui_clientes import ListaClientes
from .contratos.gui_cnt_mensal_lista import ListaContratosMensais
from .contratos.gui_cnt_airbnb_lista import ListaReservasAirbnb
from .gui_calendario import Calendario
from .estoque.gui_est_hub import EcraStock
from .despesas.gui_desp_hub import EcraDespesas
from .gui_responsaveis import ListaResponsaveis
from .gui_propriedades import ListaPropriedades
from .relatorios.gui_relat_hub import Relatorios
from .gui_configuracoes import Configuracoes
from .sessao import tipo_utilizador_ativo  # <<< NOVO >>> — filtro de itens

logger = logging.getLogger(__name__)

# O `iconbitmap` do Windows só aceita `.ico` (com o `.png` falhava em
# silêncio, dentro do try). O mesmo `.ico` é o ícone do executável.
_ICONE_JANELA = config.PASTA_IMG / "ico_hostel.ico"

# Nome na barra de título de todas as janelas, com a versão logo a
# seguir (v1.8.0) — vê-se sempre, mesmo quando o rodapé fica cortado.
_NOME_APP = f"Hostel Clean v{config.VERSAO}"


# Perfis que veem cada item da sidebar (26/09/2026). A barreira
# real está nos módulos de negócio; isto é a camada visual.
_TODOS = ("Master", "Admin", "Staff")
_GESTAO = ("Master", "Admin")
_SO_MASTER = ("Master",)

ITENS_MENU = [
    # ---- PAINEL -----------------------------------------------------
    {"tipo": "secao", "texto": "Painel"},
    {
        "tipo": "item",
        "texto": "Dashboard",
        "ecra": Dashboard,
        "perfis": _TODOS,
    },
    # ---- GESTÃO -----------------------------------------------------
    {"tipo": "secao", "texto": "Gestão"},
    {
        "tipo": "item",
        "texto": "Gestão de Propriedades",
        "ecra": ListaPropriedades,
        "perfis": _GESTAO,
    },
    {
        "tipo": "item",
        "texto": "Clientes",
        "ecra": ListaClientes,
        "perfis": _GESTAO,
    },
    {
        "tipo": "item",
        "texto": "Contratos Mensais",
        "ecra": ListaContratosMensais,
        "perfis": _GESTAO,
    },
    {
        "tipo": "item",
        "texto": "Reservas Airbnb",
        "ecra": ListaReservasAirbnb,
        "perfis": _GESTAO,
    },
    # ---- OPERAÇÃO ---------------------------------------------------
    {"tipo": "secao", "texto": "Operação"},
    {
        "tipo": "item",
        "texto": "Calendário",
        "ecra": Calendario,
        "perfis": _GESTAO,
    },
    {"tipo": "item", "texto": "Stock", "ecra": EcraStock, "perfis": _TODOS},
    {
        "tipo": "item",
        "texto": "Despesas",
        "ecra": EcraDespesas,
        "perfis": _GESTAO,
    },
    {
        "tipo": "item",
        "texto": "Responsáveis",
        "ecra": ListaResponsaveis,
        "perfis": _TODOS,
    },
    # ---- SISTEMA ----------------------------------------------------
    {"tipo": "secao", "texto": "Sistema"},
    {
        "tipo": "item",
        "texto": "Relatórios",
        "ecra": Relatorios,
        "perfis": _GESTAO,
    },
    {
        "tipo": "item",
        "texto": "Configurações",
        "ecra": Configuracoes,
        "perfis": _SO_MASTER,
    },
]


def _itens_visiveis():
    """Devolve a lista do ITENS_MENU filtrada pelo perfil ativo.

    26/09/2026 — cada item tem a chave `perfis` com os perfis que o
    veem. Uma secção só aparece se tiver pelo menos um item visível
    (o Staff, por exemplo, só vê a secção "Operação").

    Chamada uma única vez, na construção da `BarraLateral` —
    quando já há sessão ativa (o LoginModal já correu).
    """
    tipo = tipo_utilizador_ativo()
    visiveis = []
    secao_pendente = None

    for item in ITENS_MENU:
        if item["tipo"] == "secao":
            secao_pendente = item
            continue

        if tipo not in item["perfis"]:
            continue

        if secao_pendente is not None:
            visiveis.append(secao_pendente)
            secao_pendente = None

        visiveis.append(item)

    return visiveis


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

        # 28/09/2026 — True quando entrou com a password de fábrica.
        # Lida pela `Aplicacao`, que obriga a trocá-la antes de
        # desenhar o que quer que seja.
        self.password_padrao = False

        # v1.8.0 — id do `after` da contagem do bloqueio; None = sem
        # bloqueio a decorrer.
        self._contagem_id = None

        self.title(f"{_NOME_APP} — Entrar")
        largura = 380
        altura = 400
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)

        componentes.centrar_no_ecra(self, largura, altura)

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
        # A versão passou para a barra de título (_NOME_APP): aqui em
        # baixo ficava cortada pela altura da janela.
        self.botao_sair.pack(fill="x", padx=24, pady=(0, 16))

        self.campo_username.focus_set()

        self.after(
            10,
            lambda: (self.lift(), self.focus_force(), self.grab_set()),
        )

    # -- validação ---------------------------------------------------

    def _entrar(self):
        """Inicia a validação com feedback visual."""
        # Durante o bloqueio o botão está desativado, mas o Enter
        # continua ligado aos campos — este `if` trava-o também.
        if self._contagem_id is not None:
            return

        username = self.campo_username.get().strip()
        password = self.campo_password.get()

        self._bloquear_interface()
        self._arrancar_animacao()

        self.update_idletasks()

        registo, motivo = utilizadores.autenticar(username, password)

        self._parar_animacao()
        self._restaurar_interface()

        if registo is None:
            self.campo_password.delete(0, "end")
            # v1.8.0 — esta falha pode ter sido a que ativou o
            # bloqueio: nesse caso mostra logo a contagem.
            if utilizadores.segundos_bloqueio(username) > 0:
                self._contar_bloqueio(username)
                return
            self.erro.configure(
                text=_MENSAGENS_ERRO.get(motivo, "Credenciais inválidas.")
            )
            self.campo_password.focus_set()
            return

        try:
            sessao.definir_responsavel_ativo(registo["id"])
        except ValueError as erro:
            logger.warning(
                "Autenticado mas sessão recusada — responsavel_id=%s",
                registo["id"],
            )
            self.erro.configure(text=str(erro))
            self.campo_password.delete(0, "end")
            self.campo_password.focus_set()
            return

        self.password_padrao = utilizadores.usa_password_padrao(password)

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

    # -- bloqueio por tentativas falhadas (v1.8.0) -------------------

    def _contar_bloqueio(self, username):
        """Contagem decrescente, de segundo a segundo.

        Quem sabe quanto falta é o módulo
        (`utilizadores.segundos_bloqueio`) — o ecrã só pergunta e
        mostra. Enquanto dura, o "Entrar" fica desativado; o
        "Sair" continua a funcionar. No fim, limpa a mensagem e
        devolve o foco à password.
        """
        segundos = utilizadores.segundos_bloqueio(username)
        if segundos <= 0:
            self._contagem_id = None
            self.botao_entrar.configure(state="normal")
            self.erro.configure(text="")
            self.campo_password.focus_set()
            return

        self.botao_entrar.configure(state="disabled")
        self.erro.configure(
            text=f"Demasiadas tentativas. Aguarde {segundos} s."
        )
        self._contagem_id = self.after(
            1000, lambda: self._contar_bloqueio(username)
        )

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
        if self._contagem_id is not None:
            self.after_cancel(self._contagem_id)
            self._contagem_id = None
        self.grab_release()
        componentes.cancelar_agendamentos(self)
        # v1.8.0: destruir DEPOIS de o clique terminar. Destruído aqui
        # dentro, o Tk apagava o próprio botão "Sair" enquanto ainda
        # corria o comando dele — "TclError: can't delete Tcl command"
        # e a janela ficava em branco, pendurada.
        self.master.after(0, self.master.destroy)


class TermoModal(ctk.CTkToplevel):
    """Pede a aceitação do termo a quem ainda não aceitou a versão
    em vigor.

    <<< NOVO v1.6.0 >>>

    Só aparece quando o `termos.verificar` diz que é preciso. Quem
    já aceitou entra direto e nunca vê este ecrã — e é esta
    verificação que resolve sozinha os utilizadores que já existiam
    antes da v1.6.0: cada um aceita no seu próximo acesso, sem
    migração nenhuma à tabela.

    Bloqueante como o `LoginModal`: não se fecha pelo "X". Ou
    aceita, ou sai — porque o termo é condição de acesso, não um
    pedido de consentimento (esse nunca poderia bloquear).

    `self.aceite` é lido pela `Aplicacao` depois do `wait_window`.
    Fica False quando a pessoa clicou "Sair".
    """

    def __init__(self, master, responsavel, estado):
        super().__init__(master)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self.aceite = False
        self.responsavel = responsavel

        self.title(f"{_NOME_APP} — Termo de uso")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)

        ctk.CTkLabel(
            self,
            text="Antes de entrar",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(24, 2))

        ctk.CTkLabel(
            self,
            text=f"{responsavel['nome']} — {responsavel['id']} · "
            f"{responsavel['tipo_utilizador']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 16))

        texto = estado["texto"]
        versao = texto["versao"]

        # A faixa de aviso só aparece a quem já tinha aceitado uma
        # versão anterior. A quem nunca aceitou não há "atualização"
        # nenhuma a anunciar — seria uma mensagem falsa.
        aviso = None

        if estado["versao_aceite"]:
            aviso = (
                "O termo de confidencialidade foi atualizado. Para "
                "continuar a usar o sistema, é preciso aceitar a "
                "versão em vigor."
            )

        self.bloco_termo = componentes.BlocoTermo(
            self,
            titulo="Termo de confidencialidade e uso do sistema",
            texto=texto["texto"],
            versao=versao,
            rotulo=f"Li e aceito a versão {versao} do termo. *",
            versao_anterior=estado["versao_aceite"],
            data_anterior=estado["data_aceite"],
            aviso=aviso,
            ao_mudar=self._ao_mudar,
        )
        self.bloco_termo.pack(fill="x", padx=24)

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(16, 20))

        ctk.CTkButton(
            rodape,
            text="Sair",
            width=100,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        self.botao_aceitar = ctk.CTkButton(
            rodape,
            text="Aceitar e entrar",
            width=170,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.COR_BORDA,
            hover_color=tema.AZUL_CLARO,
            text_color_disabled=tema.TEXTO_INDISPONIVEL,
            state="disabled",
            command=self._aceitar,
        )
        self.botao_aceitar.pack(side="right")

        # A altura sai do conteúdo, não de um número à mão: a faixa
        # de aviso só existe em metade dos casos, e um valor fixo
        # deixava um vazio grande no outro. Mesma técnica do
        # `_AcoesResponsavelModal` no gui_responsaveis.
        self.update_idletasks()
        largura = 520
        altura = round(self.winfo_reqheight() / componentes.escala(self))
        componentes.centrar_no_ecra(self, largura, altura)

        self.after(
            10,
            lambda: (self.lift(), self.focus_force(), self.grab_set()),
        )

    def _ao_mudar(self):
        """Liga e desliga o botão conforme a caixa."""
        ligado = self.bloco_termo.esta_aceite()

        self.botao_aceitar.configure(
            state="normal" if ligado else "disabled",
            fg_color=tema.AZUL_PRINCIPAL if ligado else tema.COR_BORDA,
        )

    def _aceitar(self):
        """Grava a aceitação e deixa entrar.

        O `registado_por_id` é a própria pessoa: ninguém aceita um
        termo por outra. Na atribuição da credencial é diferente —
        aí há um Master a registar.
        """
        try:
            termos.registar(
                termos.TITULAR_RESPONSAVEL,
                self.responsavel["id"],
                termos.CONFIDENCIALIDADE,
                registado_por_id=self.responsavel["id"],
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.aceite = True
        self.grab_release()
        self.destroy()


class KitRoupaModal(ctk.CTkToplevel):
    """Pergunta do 1.º arranque: criar a roupa de base? (v1.9.0,
    mockup aprovado a 05/10/2026). Mostra os produtos do
    `estoque.KIT_ROUPA_BASE` e as quantidades por tipo de cama.
    """

    _COLUNAS_CAMA = (
        ("solteiro", "SOLTEIRO"),
        ("casal", "CASAL"),
        ("beliche", "BELICHE (PAR)"),
    )

    def __init__(self, master):
        super().__init__(master)
        self.title("Instalação")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        corpo = componentes.Contentor(self)
        corpo.pack(fill="both", expand=True, padx=20, pady=16)

        componentes.Rotulo(
            corpo, "Criar a roupa de base?", "titulo"
        ).pack(anchor="w")
        componentes.Rotulo(
            corpo,
            "O Rol de lavandaria precisa de saber que roupa vai para "
            "cada tipo de cama. Pode começar com este kit e mudar tudo "
            "depois em Stock → Regras do Rol.",
            "secundario",
            wraplength=500,
            justify="left",
            height=0,
        ).pack(anchor="w", pady=(4, 10))

        grelha = componentes.Contentor(corpo)
        grelha.pack(fill="x")
        grelha.grid_columnconfigure(0, weight=1)
        componentes.Rotulo(grelha, "PRODUTO A CRIAR", "secao").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        for coluna, (_tipo, titulo) in enumerate(self._COLUNAS_CAMA, 1):
            componentes.Rotulo(
                grelha, titulo, "secao", anchor="center", width=100
            ).grid(row=0, column=coluna)

        for linha, (nome, _tipo_produto, quantidades) in enumerate(
            estoque.KIT_ROUPA_BASE, 1
        ):
            componentes.Rotulo(grelha, nome, "texto").grid(
                row=linha, column=0, sticky="w", pady=2
            )
            for coluna, (tipo, _titulo) in enumerate(
                self._COLUNAS_CAMA, 1
            ):
                componentes.Rotulo(
                    grelha,
                    str(quantidades.get(tipo, "–")),
                    "forte",
                    anchor="center",
                    width=100,
                ).grid(row=linha, column=coluna)

        componentes.Rotulo(
            corpo,
            "As camas extra copiam a regra do seu tamanho. Os produtos "
            "são criados com stock 0: as entradas fazem-se em Stock → "
            "Movimentos.",
            "secundario",
            wraplength=500,
            justify="left",
            height=0,
        ).pack(anchor="w", pady=(10, 14))

        rodape = componentes.Contentor(corpo)
        rodape.pack(fill="x")
        componentes.Botao(rodape, "Agora não", self.destroy).pack(
            side="left"
        )
        componentes.Botao(
            rodape, "Criar kit de roupa", self._criar, estilo="primario"
        ).pack(side="right")

        componentes.centrar_sobre(self, master, 560, 390)
        componentes.colocar_no_topo(self)

    def _criar(self):
        ativo = sessao.obter_responsavel_ativo()
        try:
            resultado = estoque.criar_kit_roupa_base(
                ativo["id"] if ativo else None
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Kit criado: {len(resultado['produtos'])} produtos e "
            f"{resultado['regras']} regras.",
            titulo="Kit de roupa",
        )
        self.destroy()


class TrocarPasswordModal(ctk.CTkToplevel):
    """Obriga a trocar a password de fábrica (28/09/2026).

    Aparece a seguir ao login quando a password usada foi a
    `config.PASSWORD_PADRAO` — a que a instalação e o "Começar do
    zero" deixam ao Master, e que está escrita no código e no
    manual. Bloqueante como o `TermoModal`: não fecha pelo "X"; ou
    troca, ou sai.

    A regra (política, "não pode ser a de fábrica") vive em
    `utilizadores.alterar_password`; aqui só se recolhe e mostra o
    erro. `self.trocada` é lido pela `Aplicacao` depois do
    `wait_window`.
    """

    _LARGURA = 420

    def __init__(self, master, responsavel):
        super().__init__(master)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self.trocada = False
        self.responsavel = responsavel

        self.title(f"{_NOME_APP} — Nova password")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)

        corpo = componentes.Contentor(self)
        corpo.pack(fill="both", expand=True, padx=24, pady=22)

        componentes.Rotulo(corpo, "Defina uma password nova", "titulo").pack(
            fill="x"
        )
        componentes.Rotulo(
            corpo,
            "Entrou com a password de fábrica. Por segurança, escolha "
            "uma password só sua antes de continuar (mínimo de 8 "
            "caracteres).",
            "secundario",
            wraplength=self._LARGURA - 50,
            justify="left",
        ).pack(fill="x", pady=(6, 16))

        componentes.Rotulo(corpo, "Password nova", "secundario").pack(
            fill="x"
        )
        self.campo_nova = componentes.CampoTexto(corpo, secreto=True)
        self.campo_nova.pack(fill="x", pady=(2, 10))

        componentes.Rotulo(
            corpo, "Confirmar password nova", "secundario"
        ).pack(fill="x")
        self.campo_confirmar = componentes.CampoTexto(corpo, secreto=True)
        self.campo_confirmar.pack(fill="x", pady=(2, 6))

        self.erro = componentes.Rotulo(
            corpo, "", "secundario", cor=tema.TEXTO_ERRO,
            wraplength=self._LARGURA - 50, justify="left",
        )
        self.erro.pack(fill="x", pady=(0, 10))

        rodape = componentes.Contentor(corpo)
        rodape.pack(fill="x")
        componentes.Botao(rodape, "Sair", self.destroy, "contorno").pack(
            side="left"
        )
        componentes.Botao(
            rodape, "Guardar e entrar", self._gravar, "primario"
        ).pack(side="right")

        self.campo_confirmar.bind("<Return>", lambda _e: self._gravar())

        self.update_idletasks()
        altura = round(self.winfo_reqheight() / componentes.escala(self))
        componentes.centrar_no_ecra(self, self._LARGURA, altura)

        self.after(
            10,
            lambda: (
                self.lift(),
                self.focus_force(),
                self.grab_set(),
                self.campo_nova.focus_set(),
            ),
        )

    def _gravar(self):
        nova = self.campo_nova.get()

        if nova != self.campo_confirmar.get():
            self.erro.configure(
                text="A password nova e a confirmação não coincidem."
            )
            return

        try:
            utilizadores.alterar_password(
                self.responsavel["id"],
                config.PASSWORD_PADRAO,
                nova,
                self.responsavel,
            )
        except ValueError as erro:
            self.erro.configure(text=str(erro))
            return

        self.trocada = True
        self.destroy()


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

        # Erros inesperados de qualquer botão/evento, em qualquer
        # janela, vêm parar aqui. Atribui-se em vez de fazer override:
        # no Tk isto é um ATRIBUTO que se substitui, não um método
        # (é assim que o typeshed o declara, e um `def` com o mesmo
        # nome dava aviso de override incompatível no Pylance).
        # Fica logo no início para cobrir também o LoginModal.
        self.report_callback_exception = self._tratar_erro_interface

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

        self.title(f"{_NOME_APP} — Gestão de Alojamento")

        try:
            self.iconbitmap(str(_ICONE_JANELA))
        except Exception:
            pass

        componentes.centrar_no_ecra(self, 1100, 700)
        self.minsize(*componentes.tamanho_minimo(self, 950, 620))
        self.resizable(True, True)
        self.configure(fg_color=tema.COR_FUNDO)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # A barra lateral e a área de conteúdo são construídas
        # DEPOIS do login — o `_itens_visiveis()` só funciona com
        # sessão ativa (antes disso, `tipo_utilizador_ativo()`
        # devolve None e o filtro não deixa passar nenhum item).
        self.frame_atual = None

        self.update_idletasks()
        popup_login = LoginModal(self)
        self.wait_window(popup_login)

        if popup_login.sair_pedido:
            self.terminar_pedido = True
            return

        # ORDEM (v1.8.0, decisão D9): login → troca da password de
        # fábrica → termo. A conta fica segura ANTES de se registar a
        # aceitação, que fica assim ligada a uma credencial que só a
        # própria pessoa conhece.

        # 28/09/2026 — password de fábrica: tem de ser trocada antes
        # de entrar. Quem sai sem trocar não entra.
        if popup_login.password_padrao and not self._trocar_password():
            self.terminar_pedido = True
            componentes.cancelar_agendamentos(self)
            self.destroy()
            return

        # v1.6.0 — o termo. Corre DEPOIS do login (é preciso saber
        # quem é) e ANTES de desenhar seja o que for. Quem já
        # aceitou a versão em vigor nem dá por isto.
        if not self._verificar_termo():
            ativo = sessao.obter_responsavel_ativo()
            logger.info(
                "Termo não aceite — acesso recusado, responsavel_id=%s",
                ativo["id"] if ativo else None,
            )
            self.terminar_pedido = True
            componentes.cancelar_agendamentos(self)
            self.destroy()
            return

        # v1.9.0 — kit de roupa de base. Só no 1.º arranque a sério:
        # a password de fábrica acabou de ser trocada (isso só
        # acontece uma vez) e a base ainda não tem produto nenhum.
        if popup_login.password_padrao:
            self._oferecer_kit_roupa()

        # Agora sim — já há sessão ativa.
        itens = _itens_visiveis()
        self.barra_lateral = componentes.BarraLateral(
            self,
            controlador=self,
            itens=itens,
        )
        self.barra_lateral.configure(width=160)
        self.barra_lateral.grid(row=0, column=0, sticky="ns")
        self.barra_lateral.grid_propagate(False)

        self.area_conteudo = ctk.CTkFrame(
            self, corner_radius=0, fg_color=tema.COR_FUNDO
        )
        self.area_conteudo.grid(row=0, column=1, sticky="nsew")

        # Primeiro ecrã = primeiro item visível do perfil — desde a
        # v1.6.0 é o Dashboard para todos (o Staff tem vista própria).
        primeiro_ecra = next(
            item["ecra"] for item in itens if item["tipo"] == "item"
        )
        self.mostrar_frame(primeiro_ecra)

    def _tratar_erro_interface(
        self,
        exc: type[BaseException],
        val: BaseException,
        tb: TracebackType | None,
    ) -> None:
        """Apanha os erros inesperados de TODOS os ecrãs e modais.

        Ligado no `__init__` (`self.report_callback_exception = ...`).

        O Tkinter encaminha para a janela raiz qualquer exceção que
        rebente dentro de um botão, de um evento ou de um `after` —
        seja em que janela for. A raiz é sempre esta `Aplicacao`, por
        isso este método único cobre o sistema inteiro.

        Faz três coisas, por esta ordem:
          1. Regista no log, com o traceback completo.
          2. Mantém o comportamento normal do Tkinter (imprimir no
             terminal) — útil durante o desenvolvimento.
          3. Avisa o utilizador com um popup genérico. Antes disto, o
             botão simplesmente "não fazia nada" e ninguém sabia que
             tinha havido um erro.

        Os `ValueError` de validação NÃO chegam aqui: esses são
        apanhados pelos `try/except` de cada ecrã, que mostram a
        mensagem própria. Aqui só cai o que ninguém previu.

        Duas proteções no popup:
          - Se a janela já foi destruída (erro durante um logoff, por
            exemplo), não se mostra nada: abrir um popup sem janela
            criava uma janela Tk nova e vazia.
          - Se um erro se repetir em cadeia (um `after` que rebenta a
            cada ciclo), só aparece um popup de cada vez.
          Uma falha a mostrar o popup nunca pode gerar outro erro por
          cima — fica só registada.
        """
        logger.error(
            "Erro inesperado num evento da interface",
            exc_info=(exc, val, tb),
        )

        # O que o Tkinter faria por omissão: imprimir no terminal.
        print("Exception in Tkinter callback", file=sys.stderr)
        traceback.print_exception(exc, val, tb)

        if getattr(self, "_popup_erro_aberto", False):
            return

        try:
            if not self.winfo_exists():
                return
        except tkinter.TclError:
            return

        # Ligação perdida não é um bug: a pessoa só precisa de saber
        # que pode tentar outra vez (o túnel já foi reaberto, se deu)
        # ou que tem de verificar o servidor (v1.8.2).
        if servidores.e_falha_de_ligacao(val):
            mensagem = (
                "Perdeu-se a ligação ao servidor da base de dados e a "
                "operação não foi concluída.\n\nTente outra vez. Se "
                "o aviso se repetir, confirme que o servidor está "
                "ligado e reinicie a aplicação."
            )
        else:
            mensagem = (
                "Ocorreu um erro inesperado e a operação não foi "
                "concluída.\n\nO erro ficou registado no ficheiro de "
                "log. Se voltar a acontecer, avise quem mantém o "
                "sistema."
            )

        self._popup_erro_aberto = True
        try:
            componentes.mostrar_erro(mensagem)
        except Exception:
            logger.exception("Falha ao mostrar o aviso de erro inesperado")
        finally:
            self._popup_erro_aberto = False

    def _verificar_termo(self):
        """True se a pessoa pode entrar; False se deve sair.

        <<< NOVO v1.6.0 >>>
        """
        responsavel = sessao.obter_responsavel_ativo()

        if responsavel is None:
            return False

        try:
            estado = termos.verificar(
                termos.TITULAR_RESPONSAVEL,
                responsavel["id"],
                termos.CONFIDENCIALIDADE,
            )
        except ValueError:
            logger.warning(
                "Entrada sem verificação do termo (nenhuma versão em "
                "vigor) — responsavel_id=%s",
                responsavel["id"],
            )
            # Não há texto publicado. Entra em silêncio: a falta de
            # um documento é falha de configuração, não do
            # utilizador. Quem publica vê o estado nas Configurações
            # — avisar aqui, em todos os arranques, só treinava as
            # pessoas a fechar caixas sem ler.
            return True

        if not estado["precisa_aceitar"]:
            return True

        popup = TermoModal(self, responsavel, estado)
        self.wait_window(popup)

        return popup.aceite

    def _oferecer_kit_roupa(self):
        """Pergunta se se cria o kit de roupa de base (v1.9.0).

        Só numa base sem produtos. "Agora não" não cria nada e não
        volta a perguntar no arranque — o ecrã Stock → Regras do Rol
        mantém o botão "Criar kit de roupa" enquanto a base estiver
        sem produtos. Uma falha aqui nunca impede a entrada.
        """
        try:
            if not estoque.pode_criar_kit_roupa():
                return
        except Exception:
            logger.exception("Não foi possível verificar o kit de roupa")
            return

        popup = KitRoupaModal(self)
        self.wait_window(popup)

    def _trocar_password(self):
        """True se a password de fábrica foi trocada; False se a
        pessoa saiu sem trocar."""
        responsavel = sessao.obter_responsavel_ativo()

        if responsavel is None:
            return False

        popup = TrocarPasswordModal(self, responsavel)
        self.wait_window(popup)

        return popup.trocada

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

        ativo = sessao.obter_responsavel_ativo()
        logger.info(
            "Logoff — responsavel_id=%s", ativo["id"] if ativo else None
        )

        sessao.limpar_responsavel_ativo()

        self.reabrir = True
        componentes.cancelar_agendamentos(self)
        self.destroy()
