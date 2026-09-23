"""Modais de confirmação do ecrã de Configurações.

Este módulo tem duas funções públicas, ambas bloqueantes
(`wait_window`) — quem chama fica à espera do resultado:

  - `confirmar_alteracao(...)` — aparece sempre que um valor de
    configuração é alterado. Mostra o antes → depois, um aviso do
    que muda, e um campo de motivo opcional. Devolve `True` se o
    utilizador confirmar, `False` se cancelar.

  - `confirmar_reset_sistema(...)` — aparece quando o Master clica
    em "Começar do zero". Exige confirmação dupla (escrever
    "APAGAR TUDO" + password do Master ativo). Devolve a password
    se confirmar, `None` se cancelar. NÃO executa o reset — só
    recolhe a confirmação; quem executa é o `sistema.py` (Ficheiro 6).

Os dois modais seguem o mesmo estilo dos outros da aplicação:
`CTkToplevel`, `transient` do parent, `colocar_no_topo` para
trazer à frente, cores do `tema.py`.
"""

import logging

import customtkinter as ctk

import utilizadores
from . import componentes
from . import sessao
from . import tema

logger = logging.getLogger(__name__)

# =====================================================================
# MODAL 1 — CONFIRMAR ALTERAÇÃO
# =====================================================================


def confirmar_alteracao(
    pai,
    titulo,
    chave,
    valor_antigo,
    valor_novo,
):
    """Abre o modal de confirmação e devolve True/False.

    Parâmetros:
      - `pai`:      o widget que abre o modal (parent do Toplevel).
      - `titulo`:   o título humano da configuração (ex.: "Aviso
                    prévio padrão (dias)").
      - `chave`:    a chave completa (ex.: "operacao.aviso_previo_dias").
      - `valor_antigo`: valor atual (antes da alteração).
      - `valor_novo`:   valor pretendido.

    Devolve:
      - `True` se o utilizador clicar em "Confirmar alteração".
      - `False` se clicar em "Cancelar" ou fechar pela X.

    Bloqueia até o utilizador decidir. Não grava nada — quem chama
    usa o resultado para decidir se chama `configuracoes.definir`.
    """
    resultado = {"confirmado": False}

    janela = ctk.CTkToplevel(pai)
    janela.title("Confirmar alteração")
    janela.resizable(False, False)
    janela.configure(fg_color=tema.COR_FUNDO)
    janela.transient(pai)
    componentes.colocar_no_topo(janela)

    def fechar(confirmado):
        resultado["confirmado"] = confirmado
        janela.destroy()

    janela.protocol("WM_DELETE_WINDOW", lambda: fechar(False))

    # ---------------------------------------------------------------
    # Cabeçalho — ícone + título + subtítulo
    # ---------------------------------------------------------------
    cabecalho = ctk.CTkFrame(janela, fg_color="transparent")
    cabecalho.pack(fill="x", padx=24, pady=(20, 8))

    ctk.CTkLabel(
        cabecalho,
        text="⚠  Confirmar alteração de regra",
        text_color=tema.COR_TEXTO,
        font=ctk.CTkFont(size=15, weight="bold"),
        anchor="w",
    ).pack(fill="x")

    ctk.CTkLabel(
        cabecalho,
        text="Esta é uma configuração que afeta o comportamento do sistema.",
        text_color=tema.COR_TEXTO_SECUNDARIO,
        font=ctk.CTkFont(size=11),
        anchor="w",
        justify="left",
        wraplength=460,
    ).pack(fill="x", pady=(4, 0))

    # ---------------------------------------------------------------
    # Aviso amarelo
    # ---------------------------------------------------------------
    aviso = ctk.CTkFrame(
        janela,
        fg_color=tema.AMARELO_AVISO,
        corner_radius=tema.RAIO_CAMPO,
    )
    aviso.pack(fill="x", padx=24, pady=(4, 12))

    ctk.CTkLabel(
        aviso,
        text=titulo,
        text_color=tema.TEXTO_AVISO,
        font=ctk.CTkFont(size=12, weight="bold"),
        anchor="w",
    ).pack(fill="x", padx=14, pady=(10, 2))

    ctk.CTkLabel(
        aviso,
        text=(
            "A alteração é imediata e fica registada com o seu nome. "
            "Contratos e registos já criados não são afetados."
        ),
        text_color=tema.TEXTO_AVISO,
        font=ctk.CTkFont(size=11),
        anchor="w",
        justify="left",
        wraplength=440,
    ).pack(fill="x", padx=14, pady=(0, 10))

    # ---------------------------------------------------------------
    # Bloco antes → depois
    # ---------------------------------------------------------------
    mudanca = ctk.CTkFrame(
        janela,
        fg_color=tema.LINHA_ALTERNADA,
        corner_radius=tema.RAIO_CAMPO,
    )
    mudanca.pack(fill="x", padx=24, pady=(0, 12))

    interno = ctk.CTkFrame(mudanca, fg_color="transparent")
    interno.pack(fill="x", padx=16, pady=14)

    # Lado "Antes"
    lado_antes = ctk.CTkFrame(interno, fg_color="transparent")
    lado_antes.pack(side="left", expand=True)

    ctk.CTkLabel(
        lado_antes,
        text="ANTES",
        text_color=tema.COR_TEXTO_SECUNDARIO,
        font=ctk.CTkFont(size=10, weight="bold"),
    ).pack()

    ctk.CTkLabel(
        lado_antes,
        text=_formatar_valor(valor_antigo),
        text_color=tema.COR_TEXTO_SECUNDARIO,
        font=ctk.CTkFont(size=16, overstrike=True),
    ).pack(pady=(2, 0))

    # Seta
    ctk.CTkLabel(
        interno,
        text="→",
        text_color=tema.COR_TEXTO_SECUNDARIO,
        font=ctk.CTkFont(size=18),
    ).pack(side="left", padx=12)

    # Lado "Depois"
    lado_depois = ctk.CTkFrame(interno, fg_color="transparent")
    lado_depois.pack(side="left", expand=True)

    ctk.CTkLabel(
        lado_depois,
        text="DEPOIS",
        text_color=tema.COR_TEXTO_SECUNDARIO,
        font=ctk.CTkFont(size=10, weight="bold"),
    ).pack()

    ctk.CTkLabel(
        lado_depois,
        text=_formatar_valor(valor_novo),
        text_color=tema.AZUL_PRINCIPAL,
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(pady=(2, 0))

    # ---------------------------------------------------------------
    # Campo de motivo (opcional)
    # ---------------------------------------------------------------
    motivo = ctk.CTkFrame(janela, fg_color="transparent")
    motivo.pack(fill="x", padx=24, pady=(0, 16))

    ctk.CTkLabel(
        motivo,
        text="Motivo (opcional)",
        text_color=tema.COR_TEXTO_SECUNDARIO,
        font=ctk.CTkFont(size=11),
        anchor="w",
    ).pack(fill="x")

    campo_motivo = ctk.CTkEntry(
        motivo,
        corner_radius=tema.RAIO_CAMPO,
        placeholder_text="ex.: revisão anual da política",
    )
    campo_motivo.pack(fill="x", pady=(2, 0))

    # ---------------------------------------------------------------
    # Rodapé — Cancelar + Confirmar
    # ---------------------------------------------------------------
    rodape = ctk.CTkFrame(janela, fg_color="transparent")
    rodape.pack(fill="x", padx=24, pady=(0, 20))

    ctk.CTkButton(
        rodape,
        text="Cancelar",
        width=130,
        height=36,
        corner_radius=tema.RAIO_BOTAO,
        fg_color="transparent",
        border_width=1,
        border_color=tema.COR_BORDA,
        text_color=tema.COR_TEXTO,
        hover_color=tema.COR_BORDA,
        command=lambda: fechar(False),
    ).pack(side="left")

    ctk.CTkButton(
        rodape,
        text="Confirmar alteração",
        width=170,
        height=36,
        corner_radius=tema.RAIO_BOTAO,
        fg_color=tema.AZUL_PRINCIPAL,
        hover_color=tema.AZUL_CLARO,
        command=lambda: fechar(True),
    ).pack(side="right")

    # Ajusta a janela ao tamanho do conteúdo e centra
    janela.update_idletasks()
    largura = 520
    altura = janela.winfo_reqheight()
    janela.geometry(f"{largura}x{altura}")

    # Centrar no parent
    _centrar_no_parent(janela, pai, largura, altura)

    # Bloqueia até o utilizador decidir
    janela.wait_window()

    return resultado["confirmado"]


# =====================================================================
# MODAL 2 — CONFIRMAR RESET DO SISTEMA
# =====================================================================


def confirmar_reset_sistema(pai):
    """Abre o modal de confirmação dupla do "Começar do zero".

    Exige:
      - Escrever literalmente "APAGAR TUDO" (case-sensitive).
      - A password do Master ativo.

    Devolve:
      - A PASSWORD introduzida, se as duas confirmações passarem e
        o utilizador clicar em "Começar do zero".
      - `None` em todos os outros casos (cancelar, X).

    Devolve a password, e não só True/False, porque quem executa o
    reset — o `sistema.comecar_do_zero(autor, password)` — volta a
    verificá-la (alteração de 23/09/2026: a confirmação com password
    passou a ser regra do módulo, não só deste ecrã). A verificação
    feita aqui fica só pelo conforto: com a password errada o modal
    não fecha e a pessoa tenta outra vez.

    NÃO executa o reset — só recolhe a confirmação.
    """
    resultado: dict = {"password": None}

    janela = ctk.CTkToplevel(pai)
    janela.title("Começar do zero")
    janela.resizable(False, False)
    janela.configure(fg_color=tema.COR_FUNDO)
    janela.transient(pai)
    componentes.colocar_no_topo(janela)

    def fechar(password):
        resultado["password"] = password
        janela.destroy()

    janela.protocol("WM_DELETE_WINDOW", lambda: fechar(None))

    # ---------------------------------------------------------------
    # Cabeçalho vermelho
    # ---------------------------------------------------------------
    cabecalho = ctk.CTkFrame(
        janela,
        fg_color=tema.VERMELHO_ERRO,
        corner_radius=tema.RAIO_CARTAO,
    )
    cabecalho.pack(fill="x", padx=24, pady=(20, 12))

    ctk.CTkLabel(
        cabecalho,
        text="⚠  Esta operação é IRREVERSÍVEL",
        text_color=tema.TEXTO_ERRO,
        font=ctk.CTkFont(size=15, weight="bold"),
        anchor="w",
    ).pack(fill="x", padx=16, pady=(14, 4))

    ctk.CTkLabel(
        cabecalho,
        text=(
            "Apaga TODOS os dados: propriedades, unidades, clientes, "
            "contratos, stock, despesas, configurações e utilizadores. "
            "Só ficará um utilizador Master padrão."
        ),
        text_color=tema.TEXTO_ERRO,
        font=ctk.CTkFont(size=11),
        anchor="w",
        justify="left",
        wraplength=440,
    ).pack(fill="x", padx=16, pady=(0, 4))

    ctk.CTkLabel(
        cabecalho,
        text=(
            "É criado um backup automático antes do reset, para o "
            "caso de precisares de recuperar algo."
        ),
        text_color=tema.TEXTO_ERRO,
        font=ctk.CTkFont(size=11, weight="bold"),
        anchor="w",
        justify="left",
        wraplength=440,
    ).pack(fill="x", padx=16, pady=(0, 14))

    # ---------------------------------------------------------------
    # Campo 1 — escrever "APAGAR TUDO"
    # ---------------------------------------------------------------
    ctk.CTkLabel(
        janela,
        text='Para continuar, escreve "APAGAR TUDO":',
        text_color=tema.COR_TEXTO,
        font=ctk.CTkFont(size=12),
        anchor="w",
    ).pack(fill="x", padx=24)

    campo_texto = ctk.CTkEntry(
        janela,
        corner_radius=tema.RAIO_CAMPO,
        placeholder_text="APAGAR TUDO",
    )
    campo_texto.pack(fill="x", padx=24, pady=(4, 14))

    # ---------------------------------------------------------------
    # Campo 2 — password do Master ativo
    # ---------------------------------------------------------------
    ctk.CTkLabel(
        janela,
        text="Confirma com a tua password:",
        text_color=tema.COR_TEXTO,
        font=ctk.CTkFont(size=12),
        anchor="w",
    ).pack(fill="x", padx=24)

    campo_password = ctk.CTkEntry(
        janela,
        corner_radius=tema.RAIO_CAMPO,
        show="•",
        placeholder_text="Password do Master ativo",
    )
    campo_password.pack(fill="x", padx=24, pady=(4, 14))

    # ---------------------------------------------------------------
    # Rodapé — Cancelar + Começar do zero (vermelho)
    # ---------------------------------------------------------------
    rodape = ctk.CTkFrame(janela, fg_color="transparent")
    rodape.pack(fill="x", padx=24, pady=(0, 20))

    ctk.CTkButton(
        rodape,
        text="Cancelar",
        width=130,
        height=36,
        corner_radius=tema.RAIO_BOTAO,
        fg_color="transparent",
        border_width=1,
        border_color=tema.COR_BORDA,
        text_color=tema.COR_TEXTO,
        hover_color=tema.COR_BORDA,
        command=lambda: fechar(None),
    ).pack(side="left")

    def tentar_confirmar():
        """Verifica a password UMA vez, só ao clicar.

        Antes (até 23/09/2026) a password era verificada a cada tecla,
        com o `utilizadores.autenticar`: enchia o log de falsas
        "falhas de autenticação" (uma por letra), registava um login
        que não aconteceu e atualizava o `ultimo_login` do Master.
        """
        password = campo_password.get()

        if _password_do_master_valida(password):
            fechar(password)
            return

        ativo = sessao.obter_responsavel_ativo()
        logger.warning(
            "Password errada na confirmação do reset — autor_id=%s",
            ativo["id"] if ativo else None,
        )
        componentes.mostrar_erro(
            "A password não corresponde ao utilizador ativo."
        )
        campo_password.delete(0, "end")
        campo_password.focus_set()
        validar()

    botao_confirmar = ctk.CTkButton(
        rodape,
        text="Começar do zero",
        width=170,
        height=36,
        corner_radius=tema.RAIO_BOTAO,
        fg_color=tema.TEXTO_ERRO,
        hover_color="#A02D22",
        state="disabled",
        command=tentar_confirmar,
    )
    botao_confirmar.pack(side="right")

    # ---------------------------------------------------------------
    # Validação em tempo real dos dois campos
    # ---------------------------------------------------------------
    def validar(*_args):
        # Só liga o botão. A password é verificada ao clicar, em
        # `tentar_confirmar` — nunca a cada tecla.
        texto_ok = campo_texto.get().strip() == "APAGAR TUDO"
        password_ok = bool(campo_password.get())

        if texto_ok and password_ok:
            botao_confirmar.configure(state="normal")
        else:
            botao_confirmar.configure(state="disabled")

    campo_texto.bind("<KeyRelease>", validar)
    campo_password.bind("<KeyRelease>", validar)

    # Ajusta a janela ao conteúdo e centra
    janela.update_idletasks()
    largura = 520
    altura = janela.winfo_reqheight()
    janela.geometry(f"{largura}x{altura}")

    _centrar_no_parent(janela, pai, largura, altura)

    janela.wait_window()

    return resultado["password"]


# =====================================================================
# HELPERS
# =====================================================================


def _password_do_master_valida(password):
    """Confirma se a password bate com o Master ativo.

    Usa o `utilizadores.verificar_password`, e NÃO o `autenticar`:
    isto é uma confirmação, não um login — não deve atualizar o
    `ultimo_login` nem registar acessos no log.
    """
    if not password:
        return False

    ativo = sessao.obter_responsavel_ativo()

    if ativo is None:
        return False

    return utilizadores.verificar_password(ativo["id"], password)


def _formatar_valor(valor):
    """Formata um valor de configuração para mostrar no modal.

    - `bool` → "Ligado" / "Desligado"
    - tuplo (mes, dia) → "1 de jul"
    - resto → str()
    """
    if isinstance(valor, bool):
        return "Ligado" if valor else "Desligado"

    if isinstance(valor, tuple) and len(valor) == 2:
        mes, dia = valor
        meses = (
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
        return f"{dia} de {meses[mes - 1]}"

    return str(valor)


def _centrar_no_parent(janela, pai, largura, altura):
    """Centra um Toplevel sobre a janela que o abriu.

    Reaproveita a lógica do `componentes.centrar_sobre`, mas
    aceita uma geometria já calculada (o modal ajusta-se ao
    conteúdo, por isso a altura só é conhecida no fim).
    """
    pai.update_idletasks()
    x = pai.winfo_rootx() + (pai.winfo_width() - largura) // 2
    y = pai.winfo_rooty() + (pai.winfo_height() - altura) // 2
    janela.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")