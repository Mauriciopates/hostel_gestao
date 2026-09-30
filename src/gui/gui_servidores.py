"""Ecrãs dos servidores de base de dados (26/09/2026).

Tudo o que um cliente precisa para ligar a aplicação a uma base de
dados, sem abrir ficheiros (a lógica está no servidores.py):

1. `desenhar_seletor(master)` — secção "Servidor da base de dados" em
   Configurações → Sistema: um cartão por servidor com Usar / Testar /
   Editar / Remover, e "+ Adicionar servidor".

2. `FormularioServidor` — popup para adicionar ou editar um servidor,
   dentro da aplicação.

3. `JanelaServidorArranque` — o mesmo formulário numa janela própria,
   antes do login: na primeira instalação (lista vazia) e quando se
   escolhe "Corrigir dados" no plano B.

4. `JanelaFalhaLigacao` — plano B do arranque, quando o servidor ativo
   não responde: Tentar de novo / Usar outro / Corrigir dados / Sair.

5. `garantir_ligacao()` — chamado pelo main_gui.py antes de tudo.

INSTALAÇÃO ASSISTIDA (v1.8.0, INST-02): o "Testar" do formulário, o
"Testar"/"Usar" do seletor e o arranque já não se ficam por "liga / não
liga". Se a ligação funciona mas a base de dados não existe, está vazia
ou incompleta, perguntam se querem criá-la/completá-la
(`_diagnosticar_e_oferecer`, lógica em `instalacao.py`).

Vive à parte pela mesma razão que o gui_documentos_legais: o
gui_configuracoes.py já passa das mil linhas.
"""

import logging
import tkinter
from typing import TYPE_CHECKING

import customtkinter as ctk

import config
import instalacao
import servidores
from . import componentes
from . import tema

logger = logging.getLogger(__name__)


# =====================================================================
# FORMULÁRIO (partilhado pelo popup e pela janela de arranque)
# =====================================================================


class _Formulario:
    """Campos de um servidor. Quem herda chama `_construir_formulario`
    depois de criar a janela e implementa `_depois_de_gravar(id)`."""

    # Mixin: a janela real (CTk ou CTkToplevel) vem da outra classe
    # base. Estas duas declarações só existem para o Pylance saber
    # que os métodos existem — não correm (TYPE_CHECKING é False).
    if TYPE_CHECKING:
        def update_idletasks(self) -> None: ...

        def destroy(self) -> None: ...

    def _construir_formulario(self, corpo, id_servidor, titulo, texto_gravar,
                              com_sair=False):
        self._id = id_servidor
        servidor = servidores.obter(id_servidor) if id_servidor else None
        tunel = (servidor or {}).get("tunel") or {}

        ctk.CTkLabel(
            corpo, text=titulo, text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            corpo,
            text=("A password fica guardada no Gestor de Credenciais do "
                  "Windows, nunca num ficheiro."),
            text_color=tema.COR_TEXTO_SECUNDARIO, font=ctk.CTkFont(size=11),
            anchor="w", justify="left", wraplength=440,
        ).pack(fill="x", pady=(2, 12))

        grelha = ctk.CTkFrame(corpo, fg_color="transparent")
        grelha.pack(fill="x")
        grelha.grid_columnconfigure(1, weight=1)
        self._linhas = {}  # próxima linha livre de cada grelha

        self.campo_nome = self._campo(
            grelha, "Nome", (servidor or {}).get("nome", ""),
            "Ex.: Escritório, VM, Servidor da empresa")

        self.var_tunel = ctk.BooleanVar(value=bool(tunel))
        ctk.CTkCheckBox(
            grelha,
            text=(
                "Ligar por túnel SSH (servidor que só aceita ligações "
                "por dentro)"
            ),
            variable=self.var_tunel, command=self._mostrar_modo,
            text_color=tema.COR_TEXTO, font=ctk.CTkFont(size=12),
        ).grid(row=self._proxima(grelha), column=0, columnspan=2,
               sticky="w", pady=(6, 8))

        # Dois blocos, um por baixo do outro; só um está visível de
        # cada vez (ver _mostrar_modo).
        # --- ligação direta ---
        self.bloco_direto = ctk.CTkFrame(grelha, fg_color="transparent")
        self.bloco_direto.grid(row=self._proxima(grelha), column=0,
                               columnspan=2, sticky="ew")
        self.bloco_direto.grid_columnconfigure(1, weight=1)
        self.campo_host = self._campo(
            self.bloco_direto, "Endereço do MySQL",
            (servidor or {}).get("host", "localhost"), "localhost ou IP")
        self.campo_porta = self._campo(
            self.bloco_direto, "Porta do MySQL",
            str((servidor or {}).get("porta", 3306)), "3306")

        # --- túnel ---
        self.bloco_tunel = ctk.CTkFrame(grelha, fg_color="transparent")
        self.bloco_tunel.grid(row=self._proxima(grelha), column=0,
                              columnspan=2, sticky="ew")
        self.bloco_tunel.grid_columnconfigure(1, weight=1)
        self.campo_ssh_utilizador = self._campo(
            self.bloco_tunel, "Utilizador SSH",
            tunel.get("ssh_utilizador", ""),
            "Ex.: db-server")
        self.campo_ssh_host = self._campo(
            self.bloco_tunel, "Endereço da máquina", tunel.get("ssh_host", ""),
            "Ex.: 192.168.56.10")
        self.campo_ssh_porta = self._campo(
            self.bloco_tunel, "Porta SSH",
            str(tunel.get("ssh_porta", 22)), "22")
        self.campo_porta_mysql = self._campo(
            self.bloco_tunel, "Porta do MySQL nessa máquina",
            str(tunel.get("porta_mysql", 3306)), "3306")

        # --- comum ---
        self.campo_utilizador = self._campo(
            grelha, "Utilizador MySQL",
            (servidor or {}).get("utilizador", "root"), "root")
        self.campo_password = self._campo(
            grelha, "Password",
            "", "deixe vazio para manter a atual" if id_servidor else "",
            mostrar="•")
        self.campo_base = self._campo(
            grelha, "Base de dados",
            (servidor or {}).get("base", "hostel_gestao"),
            "hostel_gestao")

        self.resultado = ctk.CTkLabel(
            corpo, text="", font=ctk.CTkFont(size=11), anchor="w",
            justify="left", wraplength=440)
        self.resultado.pack(fill="x", pady=(10, 0))

        botoes = ctk.CTkFrame(corpo, fg_color="transparent")
        botoes.pack(fill="x", pady=(12, 0))
        ctk.CTkButton(
            botoes, text=texto_gravar, height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL, hover_color=tema.AZUL_CLARO,
            command=self._gravar,
        ).pack(side="right")
        ctk.CTkButton(
            botoes, text="Testar ligação", height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent", border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO, hover_color=tema.COR_BORDA,
            command=self._testar,
        ).pack(side="right", padx=(0, 8))
        ctk.CTkButton(
            botoes, text="Sair" if com_sair else "Cancelar", height=34,
            corner_radius=tema.RAIO_BOTAO, fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO, hover_color=tema.COR_BORDA,
            command=self._cancelar,
        ).pack(side="left")

        self._mostrar_modo()
        self.campo_nome.focus_set()

    # -- construção ----------------------------------------------------

    def _proxima(self, grelha):
        linha = self._linhas.get(grelha, 0)
        self._linhas[grelha] = linha + 1
        return linha

    def _campo(self, grelha, rotulo, valor, dica, mostrar=None):
        linha = self._proxima(grelha)
        ctk.CTkLabel(
            grelha, text=rotulo, text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=linha, column=0, sticky="w", padx=(0, 12), pady=4)
        opcoes = {"show": mostrar} if mostrar else {}
        entrada = ctk.CTkEntry(
            grelha, width=260, corner_radius=tema.RAIO_CAMPO,
            placeholder_text=dica, **opcoes)
        if valor:
            entrada.insert(0, valor)
        entrada.grid(row=linha, column=1, sticky="ew", pady=4)
        return entrada

    def _mostrar_modo(self):
        if self.var_tunel.get():
            self.bloco_direto.grid_remove()
            self.bloco_tunel.grid()
        else:
            self.bloco_tunel.grid_remove()
            self.bloco_direto.grid()

    # -- ler e validar -------------------------------------------------

    def _ler(self):
        """Devolve (servidor, password) ou lança ValueError com o erro."""
        def texto(campo):
            return campo.get().strip()

        def porta(campo, nome):
            try:
                valor = int(texto(campo))
            except ValueError:
                raise ValueError(f"'{nome}' tem de ser um número.") from None
            if not 1 <= valor <= 65535:
                raise ValueError(f"'{nome}' tem de estar entre 1 e 65535.")
            return valor

        obrigatorios = [(self.campo_nome, "Nome"),
                        (self.campo_utilizador, "Utilizador MySQL"),
                        (self.campo_base, "Base de dados")]
        if self.var_tunel.get():
            obrigatorios += [(self.campo_ssh_utilizador, "Utilizador SSH"),
                             (self.campo_ssh_host, "Endereço da máquina")]
        else:
            obrigatorios += [(self.campo_host, "Endereço do MySQL")]
        for campo, nome in obrigatorios:
            if not texto(campo):
                raise ValueError(f"Preencha o campo '{nome}'.")

        servidor = {
            "nome": texto(self.campo_nome),
            "host": texto(self.campo_host),
            "porta": porta(self.campo_porta, "Porta do MySQL")
            if not self.var_tunel.get() else 3306,
            "utilizador": texto(self.campo_utilizador),
            "base": texto(self.campo_base),
            "tunel": None,
        }
        if self.var_tunel.get():
            servidor["tunel"] = {
                "ssh_utilizador": texto(self.campo_ssh_utilizador),
                "ssh_host": texto(self.campo_ssh_host),
                "ssh_porta": porta(self.campo_ssh_porta, "Porta SSH"),
                "porta_mysql": porta(self.campo_porta_mysql,
                                     "Porta do MySQL nessa máquina"),
                # Provisória, só para testar; ao gravar o servidores.py
                # atribui a definitiva.
                "porta_local": self._porta_local_para_teste(),
            }

        password = self.campo_password.get()
        if not password and self._id:
            password = None  # manter a que está no cofre
        return servidor, password

    def _porta_local_para_teste(self):
        atual = servidores.obter(self._id) if self._id else None
        if atual and atual.get("tunel"):
            return atual["tunel"]["porta_local"]
        return servidores._porta_local_livre(
            dict(servidores.listar()), self._id)

    # -- ações ---------------------------------------------------------

    def _mostrar(self, texto, ok):
        self.resultado.configure(
            text=("✓ " if ok else "✗ ") + texto,
            text_color=tema.TEXTO_LIVRE if ok else tema.TEXTO_ERRO)

    def _testar(self):
        try:
            servidor, password = self._ler()
        except ValueError as erro:
            self._mostrar(str(erro), False)
            return False
        if password is None:
            password = servidores.obter_password(self._id)
        self.resultado.configure(
            text="A testar…", text_color=tema.COR_TEXTO_SECUNDARIO
        )
        self.update_idletasks()
        ok, texto = _diagnosticar_e_oferecer(servidor, password)
        self._mostrar(texto, ok)
        return ok

    def _gravar(self):
        try:
            servidor, password = self._ler()
        except ValueError as erro:
            self._mostrar(str(erro), False)
            return
        if not self._testar() and not componentes.confirmar(
            "A ligação a este servidor falhou (ver a mensagem no "
            "formulário).\n\n"
            "Gravar mesmo assim?", titulo="Ligação falhou",
        ):
            return
        try:
            id_gravado = servidores.guardar(self._id, servidor, password)
        except servidores.ErroServidor as erro:
            self._mostrar(str(erro), False)
            return
        self._depois_de_gravar(id_gravado)

    def _cancelar(self):
        self.destroy()

    def _depois_de_gravar(self, id_servidor):
        raise NotImplementedError


class FormularioServidor(_Formulario, ctk.CTkToplevel):
    """Popup, dentro da aplicação, para adicionar/editar um servidor."""

    def __init__(self, master, id_servidor=None, ao_gravar=None):
        ctk.CTkToplevel.__init__(self, master)
        self._ao_gravar = ao_gravar
        self.title("Editar servidor" if id_servidor else "Adicionar servidor")
        self.configure(fg_color=tema.COR_FUNDO)
        self.resizable(False, False)
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=24, pady=20)
        self._construir_formulario(
            corpo, id_servidor,
            "Editar servidor" if id_servidor else "Adicionar servidor",
            "Gravar")
        componentes.centrar_sobre(self, master.winfo_toplevel(), 520, 600)
        componentes.colocar_no_topo(self)

    def _depois_de_gravar(self, id_servidor):
        self.destroy()
        if self._ao_gravar:
            self._ao_gravar(id_servidor)


class JanelaServidorArranque(_Formulario, ctk.CTk):
    """O formulário numa janela própria, antes do login.

    Depois do `mainloop()`, `self.gravado` diz se foi gravado.
    """

    def __init__(self, id_servidor=None):
        ctk.CTk.__init__(self)
        self.gravado = False
        self.title("Hostel Gestão — ligação à base de dados")
        self.configure(fg_color=tema.COR_FUNDO)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=24, pady=20)
        self._construir_formulario(
            corpo, id_servidor,
            "Corrigir ligação à base de dados" if id_servidor
            else "Configurar a ligação à base de dados",
            "Gravar e continuar", com_sair=True)
        self.after(10, lambda: (self.lift(), self.focus_force()))

    def _depois_de_gravar(self, id_servidor):
        servidores.definir_ativo(id_servidor)
        self.gravado = True
        self.destroy()


# =====================================================================
# SECÇÃO EM CONFIGURAÇÕES → SISTEMA
# =====================================================================


def desenhar_seletor(master):
    """Desenha a lista de servidores dentro do cartão da secção."""
    for filho in master.winfo_children():
        filho.destroy()

    for id_servidor, servidor in servidores.listar():
        _linha_servidor(master, id_servidor, servidor)

    rodape = ctk.CTkFrame(master, fg_color="transparent")
    rodape.pack(fill="x", padx=16, pady=(14, 14))
    ctk.CTkButton(
        rodape, text="+ Adicionar servidor", width=170, height=32,
        corner_radius=tema.RAIO_BOTAO, fg_color=tema.AZUL_PRINCIPAL,
        hover_color=tema.AZUL_CLARO,
        command=lambda: FormularioServidor(
            master, ao_gravar=lambda _id: desenhar_seletor(master)),
    ).pack(side="left")
    ctk.CTkLabel(
        rodape,
        text=("Cada servidor tem a sua própria base: o que se grava num "
              "não aparece nos outros."),
        text_color=tema.COR_TEXTO_SECUNDARIO, font=ctk.CTkFont(size=11),
        anchor="w", justify="left", wraplength=480,
    ).pack(side="left", padx=(14, 0))


def _linha_servidor(master, id_servidor, servidor):
    ativo = id_servidor == config.SERVIDOR_ID

    linha = ctk.CTkFrame(master, fg_color="transparent")
    linha.pack(fill="x", padx=16, pady=(14, 0))

    texto = ctk.CTkFrame(linha, fg_color="transparent")
    texto.pack(side="left", fill="x", expand=True)

    titulo = ctk.CTkFrame(texto, fg_color="transparent")
    titulo.pack(fill="x")
    ctk.CTkLabel(
        titulo, text=servidor["nome"], text_color=tema.COR_TEXTO,
        font=ctk.CTkFont(size=13, weight="bold" if ativo else "normal"),
        anchor="w",
    ).pack(side="left")
    if ativo:
        ctk.CTkLabel(
            titulo, text="  EM USO  ", fg_color=tema.VERDE_LIVRE,
            text_color=tema.TEXTO_LIVRE, corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(side="left", padx=(8, 0))

    ctk.CTkLabel(
        texto, text=servidores.descrever(servidor),
        text_color=tema.COR_TEXTO_SECUNDARIO, font=ctk.CTkFont(size=11),
        anchor="w", justify="left", wraplength=440,
    ).pack(fill="x", pady=(2, 0))

    resultado = ctk.CTkLabel(
        texto, text="", font=ctk.CTkFont(size=11), anchor="w",
        justify="left", wraplength=440)
    resultado.pack(fill="x", pady=(2, 0))

    def botao(rotulo, comando, principal=False, largura=90):
        return ctk.CTkButton(
            linha, text=rotulo, width=largura, height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL if principal else "transparent",
            hover_color=tema.AZUL_CLARO if principal else tema.COR_BORDA,
            border_width=0 if principal else 1, border_color=tema.COR_BORDA,
            text_color=None if principal else tema.COR_TEXTO,
            command=comando,
        )

    # pack(side="right"): o primeiro fica mais à direita.
    if not ativo:
        botao("Remover", lambda: _remover(master, id_servidor, servidor)
              ).pack(side="right", padx=(6, 0))
    botao("Editar", lambda: _editar(master, id_servidor, ativo)
          ).pack(side="right", padx=(6, 0))
    botao("Testar", lambda: _testar(master, id_servidor, resultado)
          ).pack(side="right", padx=(6, 0))
    if not ativo:
        botao("Usar", lambda: _usar(master, id_servidor, servidor, resultado),
              principal=True).pack(side="right", padx=(6, 0))


def _testar(master, id_servidor, resultado):
    resultado.configure(text="A testar…", text_color=tema.COR_TEXTO_SECUNDARIO)
    master.update_idletasks()
    ok, texto = _diagnosticar_e_oferecer(
        servidores.obter(id_servidor), servidores.obter_password(id_servidor)
    )
    resultado.configure(
        text=("✓ " if ok else "✗ ") + texto,
        text_color=tema.TEXTO_LIVRE if ok else tema.TEXTO_ERRO)
    return ok


def _usar(master, id_servidor, servidor, resultado):
    """Testa primeiro; só muda e reinicia se a ligação funcionar."""
    if not _testar(master, id_servidor, resultado):
        componentes.mostrar_erro(
            f"Não mudei para '{servidor['nome']}' porque a ligação falhou.\n\n"
            "Veja a mensagem por baixo do servidor.",
            titulo="Servidor indisponível")
        return
    if not componentes.confirmar(
        f"A aplicação vai reiniciar e passar a usar '{servidor['nome']}'.\n\n"
        "Trabalho por gravar noutros ecrãs perde-se. Continuar?",
        titulo="Mudar de servidor",
    ):
        return
    servidores.definir_ativo(id_servidor)
    _reiniciar(master)


def _editar(master, id_servidor, ativo):
    def depois(_id):
        if ativo and componentes.confirmar(
            "Alterou o servidor que está em uso. As alterações só contam "
            "depois de reiniciar a aplicação.\n\nReiniciar agora?",
            titulo="Reiniciar",
        ):
            _reiniciar(master)
            return
        desenhar_seletor(master)

    FormularioServidor(master, id_servidor=id_servidor, ao_gravar=depois)


def _remover(master, id_servidor, servidor):
    if not componentes.confirmar(
        f"Remover o servidor '{servidor['nome']}' da lista?\n\n"
        "A base de dados desse servidor não é apagada — só deixa de "
        "aparecer aqui, e a password sai do cofre do Windows.",
        titulo="Remover servidor",
    ):
        return
    try:
        servidores.remover(id_servidor)
    except servidores.ErroServidor as erro:
        componentes.mostrar_erro(str(erro))
        return
    desenhar_seletor(master)


def _reiniciar(master):
    servidores.reiniciar_aplicacao()
    # Fecha esta janela: o main_gui.py vê `reabrir == False` e termina.
    master.winfo_toplevel().destroy()


# =====================================================================
# PLANO B NO ARRANQUE
# =====================================================================


class JanelaFalhaLigacao(ctk.CTk):
    """Depois do `mainloop()`, `self.escolha` é um de:
    ("tentar", None) · ("usar", id) · ("corrigir", id) · ("sair", None)
    """

    def __init__(self, id_atual, nome_atual, erro):
        super().__init__()
        self.escolha = ("sair", None)
        self.title("Hostel Gestão — servidor indisponível")
        self.configure(fg_color=tema.COR_FUNDO)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: self._escolher("sair", None))

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=28, pady=24)

        ctk.CTkLabel(
            corpo, text=f"Não consegui ligar a «{nome_atual}»",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            corpo, text=erro, text_color=tema.TEXTO_ERRO,
            font=ctk.CTkFont(size=12), anchor="w", justify="left",
            wraplength=460,
        ).pack(fill="x", pady=(10, 18))

        def botao(rotulo, acao, id_servidor=None, principal=False):
            ctk.CTkButton(
                corpo, text=rotulo, height=34, corner_radius=tema.RAIO_BOTAO,
                fg_color=tema.AZUL_PRINCIPAL if principal else "transparent",
                hover_color=tema.AZUL_CLARO if principal else tema.COR_BORDA,
                border_width=0 if principal else 1,
                border_color=tema.COR_BORDA,
                text_color=None if principal else tema.COR_TEXTO,
                command=lambda: self._escolher(acao, id_servidor),
            ).pack(fill="x", pady=(0, 8))

        botao("Tentar de novo", "tentar", principal=True)
        for id_servidor, servidor in servidores.listar():
            if id_servidor != id_atual:
                botao(f"Usar «{servidor['nome']}»", "usar", id_servidor)
        botao(f"Corrigir os dados de «{nome_atual}»", "corrigir", id_atual)
        ctk.CTkButton(
            corpo, text="Sair", height=30, corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent", text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=lambda: self._escolher("sair", None),
        ).pack(fill="x", pady=(4, 0))

        self.after(10, lambda: (self.lift(), self.focus_force()))

    def _escolher(self, acao, id_servidor):
        self.escolha = (acao, id_servidor)
        self.destroy()


def _diagnosticar_e_oferecer(servidor, password):
    """Testa o servidor e, se a base se resolve criando-a ou
    completando-a, pergunta e prepara-a (INST-02).

    Devolve (ok, texto) — ok só é True com a base PRONTA. Se o
    utilizador disser que não, ou se a preparação falhar, devolve
    False com o texto do diagnóstico (ou do erro).
    """
    estado, texto, _ = instalacao.diagnosticar(servidor, password)

    if estado == instalacao.PRONTA:
        return True, texto
    if not instalacao.pode_preparar(estado):
        return False, texto

    titulo = "Preparar a base de dados"
    if not componentes.confirmar(
        instalacao.pergunta(estado, servidor), titulo=titulo
    ):
        return False, texto

    try:
        instalacao.preparar(servidor, password)
    except ValueError as erro:
        componentes.mostrar_erro(str(erro), titulo=titulo)
        return False, str(erro)

    estado, texto, _ = instalacao.diagnosticar(servidor, password)
    if estado == instalacao.PRONTA:
        componentes.mostrar_sucesso(
            f"Base de dados '{servidor['base']}' pronta.\n\n"
            f"Os dados iniciais (categorias, textos legais) são "
            f"criados automaticamente quando a aplicação arrancar "
            f"com esta base.",
            titulo=titulo,
        )
    return estado == instalacao.PRONTA, texto


def garantir_ligacao():
    """Chamado pelo main_gui.py antes do backup, do seed e do login.

    Devolve True para continuar o arranque. Devolve False para terminar:
    o utilizador saiu, ou mudou/corrigiu o servidor e já foi lançada uma
    cópia nova da aplicação (o `config` só lê o servidor ao arrancar).
    """
    while True:
        id_servidor, servidor = servidores.servidor_ativo()

        # Primeira instalação: ainda não há nenhum servidor.
        if id_servidor is None:
            janela = JanelaServidorArranque()
            janela.mainloop()
            if janela.gravado:
                servidores.reiniciar_aplicacao()
            return False

        # Ainda não há janela nenhuma: os popups de "criar a base?"
        # precisam de uma raiz Tk, escondida para não aparecer vazia.
        raiz = tkinter.Tk()
        raiz.withdraw()
        try:
            ok, texto = _diagnosticar_e_oferecer(
                servidor, servidores.obter_password(id_servidor)
            )
        finally:
            raiz.destroy()
        if ok:
            logger.info("Servidor '%s': %s", id_servidor, texto)
            return True

        logger.warning("Servidor '%s' indisponível: %s", id_servidor, texto)
        nome = servidor["nome"] if servidor else id_servidor
        janela = JanelaFalhaLigacao(id_servidor, nome, texto)
        janela.mainloop()
        acao, escolhido = janela.escolha

        if acao == "tentar":
            continue
        if acao == "usar":
            servidores.definir_ativo(escolhido)
            servidores.reiniciar_aplicacao()
        elif acao == "corrigir":
            formulario = JanelaServidorArranque(escolhido)
            formulario.mainloop()
            if not formulario.gravado:
                continue
            servidores.reiniciar_aplicacao()
        return False
