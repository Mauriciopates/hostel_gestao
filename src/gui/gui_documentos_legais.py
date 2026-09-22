"""Modais dos documentos legais — ver texto e publicar versão.

<<< NOVO v1.6.0 >>>

Vive num ficheiro próprio, e não dentro do `gui_configuracoes.py`,
pela mesma razão que o `gui_configuracoes_modal.py` existe: o ecrã
de Configurações já passa das mil linhas, e estes dois modais são
uma funcionalidade fechada em si.

Segue a disciplina de camadas do resto da GUI: fala com `termos` (o
módulo de negócio), `sessao` e `componentes` — nunca com o
`repositorio`.

A API pública são duas funções, no mesmo feitio das do
`gui_configuracoes_modal`:

    ver_texto(master, documento)          -> None
    publicar_documento(master, documento) -> bool

O `documento` é um dos dicionários devolvidos pelo
`termos.estado_documentos()`.
"""

import customtkinter as ctk

import termos
from . import componentes
from . import sessao
from . import tema

_LARGURA_MODAL = 620
_ALTURA_TEXTO = 230


# =====================================================================
# VER TEXTO
# =====================================================================


def ver_texto(master, documento):
    """Mostra a redação da versão em vigor, sem deixar editar."""
    texto = documento["texto"]

    if texto is None:
        componentes.mostrar_erro(
            "Este documento ainda não tem nenhuma versão publicada."
        )
        return

    _VerTextoModal(master, documento)


class _VerTextoModal(ctk.CTkToplevel):
    """Janela de leitura. Não tem botão de editar de propósito.

    Uma versão publicada não se edita — publica-se outra. Um botão
    "Guardar" aqui tornava o histórico uma mentira: o texto que as
    pessoas aceitaram deixava de ser o que está gravado.
    """

    def __init__(self, master, documento):
        super().__init__(master)
        texto = documento["texto"]

        self.title(f"{documento['rotulo']} — versão {texto['versao']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=documento["rotulo"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=_LARGURA_MODAL - 60,
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=24, pady=(24, 2))

        ctk.CTkLabel(
            self,
            text=(
                f"Versão {texto['versao']} · publicada em "
                f"{_formatar_data(texto['publicado_em'])}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 14))

        caixa = ctk.CTkTextbox(
            self,
            width=_LARGURA_MODAL - 48,
            height=_ALTURA_TEXTO,
            corner_radius=tema.RAIO_CAMPO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
            font=ctk.CTkFont(size=12),
            wrap="word",
        )
        caixa.pack(padx=24)
        caixa.insert("1.0", texto["texto"])
        caixa.configure(state="disabled")

        ctk.CTkLabel(
            self,
            text=(
                "Uma versão publicada não se edita. Para mudar o "
                "texto, publique uma versão nova — esta fica no "
                "histórico porque é ela que prova o que cada pessoa "
                "aceitou."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=_LARGURA_MODAL - 48,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=24, pady=(10, 0))

        ctk.CTkButton(
            self,
            text="Fechar",
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            command=self.destroy,
        ).pack(fill="x", padx=24, pady=(16, 20))

        _dimensionar(self, master)


# =====================================================================
# PUBLICAR VERSÃO
# =====================================================================


def publicar_documento(master, documento):
    """Abre o modal de publicação. Devolve True se publicou."""
    janela = _PublicarModal(master, documento)
    master.wait_window(janela)

    return janela.publicado


class _PublicarModal(ctk.CTkToplevel):
    """Formulário de publicação de uma versão nova.

    O aviso das consequências não é decoração: publicar obriga
    todos os que já tinham aceitado a aceitar outra vez. Isso é o
    comportamento correto, mas não é coisa que se adivinhe a partir
    de um botão que diz só "Publicar".
    """

    def __init__(self, master, documento):
        super().__init__(master)
        self.documento = documento
        self.publicado = False

        texto = documento["texto"]
        self.versao_atual = texto["versao"] if texto else ""

        self.title(f"Publicar versão — {documento['rotulo']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=(
                "Publicar versão nova"
                if texto
                else "Publicar a primeira versão"
            ),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(24, 2))

        ctk.CTkLabel(
            self,
            text=documento["rotulo"],
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 16))

        self._campos_de_topo(texto)

        ctk.CTkLabel(
            self,
            text="Texto do documento *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)

        self.caixa_texto = ctk.CTkTextbox(
            self,
            width=_LARGURA_MODAL - 48,
            height=_ALTURA_TEXTO,
            corner_radius=tema.RAIO_CAMPO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
            font=ctk.CTkFont(size=12),
            wrap="word",
        )
        self.caixa_texto.pack(padx=24, pady=(2, 14))

        # Arranca com a redação em vigor: na prática publica-se quase
        # sempre uma revisão do que já lá está, não um texto de raiz.
        if texto:
            self.caixa_texto.insert("1.0", texto["texto"])

        self._aviso_consequencias(documento)
        self._rodape()

        _dimensionar(self, master)
        self.campo_versao.focus_set()

    def _campos_de_topo(self, texto):
        """Versão em vigor (bloqueada), versão nova, data."""
        faixa = ctk.CTkFrame(self, fg_color="transparent")
        faixa.pack(fill="x", padx=24, pady=(0, 12))

        for coluna in range(3):
            faixa.grid_columnconfigure(coluna, weight=1, uniform="campos")

        ctk.CTkLabel(
            faixa,
            text="Versão em vigor",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        atual = ctk.CTkEntry(
            faixa,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.LINHA_ALTERNADA,
        )
        atual.insert(0, self.versao_atual or "—")
        atual.configure(state="disabled")
        atual.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(
            faixa,
            text="Versão nova *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(6, 6))

        self.campo_versao = ctk.CTkEntry(
            faixa, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_versao.insert(0, _sugerir_versao(self.versao_atual))
        self.campo_versao.grid(row=1, column=1, sticky="ew", padx=(6, 6))

        ctk.CTkLabel(
            faixa,
            text="Data de publicação",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=(6, 0))

        data = ctk.CTkEntry(
            faixa,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.LINHA_ALTERNADA,
        )
        data.insert(0, _formatar_data(_hoje()))
        data.configure(state="disabled")
        data.grid(row=1, column=2, sticky="ew", padx=(6, 0))

    def _aviso_consequencias(self, documento):
        """A faixa amarela — o que acontece a seguir a publicar."""
        aceites = documento["aceitacoes"]

        if not documento["texto"]:
            mensagem = (
                "Esta é a primeira versão. A partir de agora o sistema "
                "passa a ter texto para mostrar, e quem entrar vai ter "
                "de o aceitar."
                if documento["bloqueia"]
                else "Esta é a primeira versão deste documento."
            )
        elif documento["bloqueia"] and aceites == 0:
            mensagem = (
                f"A versão {self.versao_atual} passa a histórico e fica "
                "guardada. Ainda ninguém a tinha aceitado, por isso não "
                "há quem volte a ser interrompido."
            )
        elif documento["bloqueia"]:
            pessoas = (
                "A pessoa que já a tinha aceitado vai ter"
                if aceites == 1
                else f"As {aceites} pessoas que já a tinham aceitado vão ter"
            )
            mensagem = (
                f"A versão {self.versao_atual} passa a histórico e fica "
                f"guardada. {pessoas} de aceitar a nova no próximo "
                "acesso — cada uma no seu, sem ninguém ficar de fora."
            )
        else:
            mensagem = (
                f"A versão {self.versao_atual} passa a histórico e fica "
                f"guardada. Os {aceites} registos antigos continuam a "
                "apontar para ela, como devem."
            )

        aviso = ctk.CTkFrame(
            self,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        aviso.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkLabel(
            aviso,
            text=f"⚠  O que acontece ao publicar: {mensagem}",
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=_LARGURA_MODAL - 90,
        ).pack(fill="x", padx=14, pady=10)

    def _rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(0, 20))

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Publicar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._publicar,
        ).pack(side="right")

    def _publicar(self):
        """Valida, publica e fecha.

        Não valida nada por sua conta além do óbvio: quem valida é o
        `termos.publicar` — versão vazia, versão repetida, texto
        vazio e perfil insuficiente saem todos de lá como
        `ValueError`, já em português. Repetir as regras aqui era
        garantir que um dia ficavam diferentes.
        """
        versao = self.campo_versao.get().strip()
        texto = self.caixa_texto.get("1.0", "end")

        try:
            publicada = termos.publicar(
                self.documento["tipo"],
                versao,
                texto,
                sessao.obter_responsavel_ativo(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.publicado = True
        self.destroy()

        componentes.mostrar_sucesso(
            f"Versão {publicada} publicada.\n\n"
            f"{self.documento['rotulo']}"
        )


# =====================================================================
# HELPERS
# =====================================================================


def _hoje():
    from datetime import date

    return date.today()


def _formatar_data(valor):
    """dd/mm/aaaa, aceitando `date` ou texto."""
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")

    return str(valor)


def _sugerir_versao(versao_atual):
    """Sugere o número seguinte, sem impor nada.

    "1.0" -> "1.1"; "0.1-dev" ou vazio -> "1.0". A sugestão é só
    isso: o campo fica editável, e quem publica decide. Uma
    numeração automática obrigava-nos a escolher um esquema de
    versões em nome do utilizador, e não é disso que se trata.
    """
    partes = (versao_atual or "").split(".")

    if len(partes) == 2 and partes[0].isdigit() and partes[1].isdigit():
        return f"{partes[0]}.{int(partes[1]) + 1}"

    return "1.0"


def _dimensionar(janela, master):
    """Altura a partir do conteúdo, centrada sobre quem a abriu."""
    janela.update_idletasks()
    componentes.centrar_sobre(
        janela, master, _LARGURA_MODAL, janela.winfo_reqheight()
    )