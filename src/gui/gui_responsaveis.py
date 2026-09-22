"""Ecrã de Gestão de Responsáveis.

Ciclo completo do módulo `responsaveis`: listar, criar, editar,
desativar e reativar. Mesma estrutura da Gestão de Propriedades —
barra de busca, "Mostrar inativos", tabela em `componentes.Tabela`
e botão "Gerir" por linha, que abre um popup com as ações.

ALTERAÇÕES v1.5.0 (17/09/2026):

  - O popup "Gerir" ganha um bloco de CREDENCIAL no topo. Quando
    o responsável ainda não tem credencial definida, mostra um
    aviso e o botão "Definir credencial". Quando já tem, mostra
    o username e o último acesso, e o botão "Alterar password".

  - `_desativar`, `_reativar`, `EditarResponsavelModal._gravar` e
    `NovoResponsavelModal._gravar` passam a passar o dict do
    responsável ativo (o `autor`) às funções de negócio.

  - O combo "Tipo de utilizador" no formulário de criar/editar
    adapta-se a três estados: sem sessão (desativado), Master
    (todos os perfis), Admin (só Staff).

Decisões anteriores que continuam em vigor (09/09/2026):

  1. Colunas: ID, NOME, CONTACTO, ESTADO, AÇÕES. O balão de
     unidades geridas aparece ao passar o rato sobre o crachá.
  2. A ligação responsável-unidade vive em `responsavel_unidade`
     (MySQL), gerida pelas funções de `unidades.py`.
  3. "Definir como responsável ativo" está nas ações.
  4. Definir o responsável ativo reconstrói o ecrã, para o
     `componentes.Cabecalho` refletir a mudança.
  5. Não há anonimização aqui — o responsável não é hóspede.
"""

import customtkinter as ctk

import responsaveis
import termos
import unidades
import utilizadores
from . import componentes
from . import sessao
from . import tema

_colocar_no_topo = componentes.colocar_no_topo


_LARGURA_ID = 70
_LARGURA_NOME = 190
_LARGURA_CONTACTO = 170
_LARGURA_ESTADO = 110
_LARGURA_ACOES = 100

_CORES_ESTADO = {
    True: (tema.VERDE_LIVRE, tema.TEXTO_LIVRE, "ativo"),
    False: (tema.VERMELHO_ERRO, tema.TEXTO_ERRO, "desativado"),
}

_COLUNAS_RESPONSAVEL = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("NOME", peso=3, minimo=_LARGURA_NOME),
    componentes.Coluna("CONTACTO", peso=3, minimo=_LARGURA_CONTACTO),
    componentes.Coluna(
        "ESTADO", peso=1, minimo=_LARGURA_ESTADO, alinhamento="centro"
    ),
    componentes.Coluna("AÇÕES", minimo=_LARGURA_ACOES, alinhamento="centro"),
)

_ALTURA_LINHA = 44
_MAX_UNIDADES_BALAO = 6


class _BalaoUnidades:
    """Balão com as unidades geridas, ao passar o rato sobre o ID.

    Não é um widget: é o objeto que liga os eventos de entrada e
    saída do rato a um `CTkToplevel` sem decoração, criado só
    quando aparece e destruído quando o rato sai.
    """

    ATRASO_MS = 350

    def __init__(self, alvo, responsavel_id):
        self.alvo = alvo
        self.responsavel_id = responsavel_id
        self.janela = None
        self.agendado = None

        alvo.bind("<Enter>", self._agendar, add="+")
        alvo.bind("<Leave>", self._esconder, add="+")
        alvo.bind("<Button-1>", self._esconder, add="+")

    def _agendar(self, evento=None):
        self._cancelar()
        self.agendado = self.alvo.after(self.ATRASO_MS, self._mostrar)

    def _cancelar(self):
        if self.agendado is not None:
            self.alvo.after_cancel(self.agendado)
            self.agendado = None

    def _mostrar(self):
        self.agendado = None

        if self.janela is not None:
            return

        try:
            geridas = unidades.unidades_geridas_por(self.responsavel_id)
        except ValueError:
            return

        janela = ctk.CTkToplevel(self.alvo)
        janela.overrideredirect(True)
        janela.configure(fg_color=tema.COR_FUNDO)
        janela.attributes("-topmost", True)

        moldura = ctk.CTkFrame(
            janela,
            corner_radius=8,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        moldura.pack(fill="both", expand=True)

        ctk.CTkLabel(
            moldura,
            text="UNIDADES GERIDAS",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 4))

        if not geridas:
            ctk.CTkLabel(
                moldura,
                text="Nenhuma unidade atribuída.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).pack(fill="x", padx=12, pady=(0, 10))
        else:
            for unidade in geridas[:_MAX_UNIDADES_BALAO]:
                ctk.CTkLabel(
                    moldura,
                    text=f"{unidade['id']} · {unidade['nome']}",
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                ).pack(fill="x", padx=12, pady=1)

            se_faltam = len(geridas) - _MAX_UNIDADES_BALAO

            if se_faltam > 0:
                ctk.CTkLabel(
                    moldura,
                    text=f"e mais {se_faltam}…",
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                ).pack(fill="x", padx=12, pady=(2, 0))

            ctk.CTkFrame(moldura, height=1, fg_color="transparent").pack(
                pady=(0, 8)
            )

        self._posicionar(janela)
        self.janela = janela

    def _posicionar(self, janela):
        janela.update_idletasks()

        x = self.alvo.winfo_rootx()
        y = self.alvo.winfo_rooty() + self.alvo.winfo_height() + 4

        largura = janela.winfo_reqwidth()
        altura = janela.winfo_reqheight()
        ecra_largura = janela.winfo_screenwidth()
        ecra_altura = janela.winfo_screenheight()

        if y + altura > ecra_altura:
            y = self.alvo.winfo_rooty() - altura - 4

        if x + largura > ecra_largura:
            x = ecra_largura - largura - 8

        janela.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _esconder(self, evento=None):
        self._cancelar()

        if self.janela is not None:
            self.janela.destroy()
            self.janela = None


class ListaResponsaveis(ctk.CTkFrame):
    """Lista de responsáveis, com busca e filtro de inativos."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Gestão de Responsáveis").pack(
            fill="x"
        )

        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Novo Responsável",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovoResponsavelModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome ou ID… (Enter)",
            width=220,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="left")
        self.campo_busca.bind("<Return>", lambda evento: self._recarregar())

        self.mostrar_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativos",
            variable=self.mostrar_inativos,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right")

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_RESPONSAVEL,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia="Ainda não há responsáveis cadastrados.",
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 4))

        ctk.CTkLabel(
            self,
            text="Passe o rato sobre o ID para ver as unidades geridas.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 6))

        self._baloes = []
        self._recarregar()

    # -- autor da sessão ------------------------------------------------

    def _autor(self):
        """Devolve o dict do responsável ativo, ou None.

        Todas as funções de negócio que fazem uma operação com
        autoria recebem este dict — as regras de permissão
        vivem no `utilizadores.py`, não aqui.
        """
        return sessao.obter_responsavel_ativo()

    # -- carregamento ---------------------------------------------------

    def _recarregar(self):
        self.tabela.limpar()
        self._baloes = []

        incluir_inativos = self.mostrar_inativos.get()
        texto_busca = self.campo_busca.get().strip().lower()

        # v1.5.0 — usa `listar_com_estado`, que traz os campos de
        # credencial já normalizados.
        lista = utilizadores.listar_com_estado(
            incluir_inativos=incluir_inativos
        )

        if texto_busca:
            lista = [
                registo
                for registo in lista
                if texto_busca in f"{registo['nome']} {registo['id']}".lower()
            ]

        if not lista:
            self.tabela.mostrar_vazio(
                "Nenhum responsável encontrado para a busca."
                if texto_busca
                else None
            )
            return

        for registo in lista:
            self._desenhar_responsavel(registo)

    def _desenhar_responsavel(self, registo):
        inativo = not registo["ativo"]
        ativo_na_sessao = self._e_o_ativo(registo)

        linha = self.tabela.nova_linha()

        cracha = ctk.CTkLabel(
            linha,
            text=registo["id"],
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=_LARGURA_ID,
            anchor="w",
        )
        self.tabela.colocar(linha, 0, cracha, esticar="w")
        self._baloes.append(_BalaoUnidades(cracha, registo["id"]))

        texto_nome = registo["nome"]
        subtitulo = registo["tipo_utilizador"]

        if ativo_na_sessao:
            subtitulo += " · em sessão"

        texto_nome += f"\n{subtitulo}"

        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=texto_nome,
                text_color=(
                    tema.TEXTO_INDISPONIVEL if inativo else tema.COR_TEXTO
                ),
                font=ctk.CTkFont(size=13),
                width=_LARGURA_NOME,
                anchor="w",
                justify="left",
            ),
        )

        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=registo["contacto"] or "—",
                text_color=(
                    tema.TEXTO_INDISPONIVEL
                    if inativo
                    else tema.COR_TEXTO_SECUNDARIO
                ),
                font=ctk.CTkFont(size=12),
                width=_LARGURA_CONTACTO,
                anchor="w",
            ),
        )

        fundo, cor_texto, rotulo = _CORES_ESTADO[registo["ativo"]]
        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=rotulo,
                text_color=cor_texto,
                fg_color=fundo,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ESTADO,
                height=22,
            ),
        )

        acoes = self.tabela.celula_acoes(linha, 4)
        acoes.adicionar(
            ctk.CTkButton(
                acoes,
                text="Gerir",
                width=76,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda: _AcoesResponsavelModal(self, registo),
            )
        )

    def _e_o_ativo(self, registo):
        ativo = sessao.obter_responsavel_ativo()
        return ativo is not None and ativo["id"] == registo["id"]

    # -- ações ----------------------------------------------------------

    def _definir_ativo(self, registo):
        try:
            sessao.definir_responsavel_ativo(registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"{registo['nome']} passou a ser o responsável ativo."
        )
        self.controlador.mostrar_frame(ListaResponsaveis)

    def _desativar(self, registo):
        if not componentes.confirmar(
            f"Desativar o responsável {registo['nome']}?\n\n"
            "Deixa de poder entrar no sistema e de registar novas "
            "operações em seu nome. O histórico já gravado mantém-se "
            "intacto.",
            titulo="Desativar responsável",
        ):
            return

        try:
            responsaveis.desativar(registo["id"], self._autor())
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        if self._e_o_ativo(registo):
            sessao.limpar_responsavel_ativo()
            componentes.mostrar_sucesso(
                f"{registo['nome']} foi desativado. A sessão ficou sem "
                "responsável ativo."
            )
            self.controlador.mostrar_frame(ListaResponsaveis)
            return

        componentes.mostrar_sucesso(
            f"Responsável {registo['nome']} desativado."
        )
        self._recarregar()

    def _reativar(self, registo):
        try:
            responsaveis.reativar(registo["id"], self._autor())
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Responsável {registo['nome']} reativado."
        )
        self._recarregar()


class _AcoesResponsavelModal(ctk.CTkToplevel):
    """Popup pequeno com as ações de um responsável.

    v1.5.0 — ganha o bloco de CREDENCIAL no topo. O bloco encolhe
    quando o responsável já tem credencial definida.

    Ajustes de 17/09/2026: o botão "Fechar" tem contorno azul, e
    os paddings internos foram apertados de 20 para 16.
    """

    def __init__(self, tela_lista, registo):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.registo = registo

        self.title(f"Ações — {registo['id']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=registo["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=16, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=f"{registo['id']} · {registo['tipo_utilizador']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        # ---- BLOCO DE CREDENCIAL (v1.5.0) --------------------------
        self._construir_bloco_credencial()

        # ---- AÇÕES HABITUAIS ---------------------------------------
        if registo["ativo"]:
            self._botao(
                "Definir como responsável ativo",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: self.tela_lista._definir_ativo(registo),
                ativo=not tela_lista._e_o_ativo(registo),
            )
            self._botao(
                "Gerir Unidades",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: UnidadesDoResponsavelModal(
                    self.tela_lista, registo
                ),
            )
            self._botao(
                "Editar",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EditarResponsavelModal(self.tela_lista, registo),
            )
            self._separador()
            self._botao(
                "Desativar",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: self.tela_lista._desativar(registo),
            )
        else:
            self._botao(
                "Reativar",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self.tela_lista._reativar(registo),
            )

        # Botão "Fechar" — contorno azul, texto azul, à altura dos
        # outros botões (17/09/2026).
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
        ).pack(fill="x", padx=16, pady=(10, 16))

        # A altura final calcula-se depois de tudo construído — o
        # bloco de credencial pode ter 2 ou 4 linhas, e o popup tem
        # de se ajustar. Técnica da regra 11.2.
        self.update_idletasks()
        largura = 340
        altura = self.winfo_reqheight()
        self.geometry(f"{largura}x{altura}")
        self._centrar_sobre_com(tela_lista, largura, altura)

    def _construir_bloco_credencial(self):
        """Constrói o bloco CREDENCIAL no topo do popup.

        Dois estados:

          - Sem credencial: aviso + botão "Definir credencial".
          - Com credencial: utilizador + último acesso + botão
            "Alterar password".
        """
        tem_credencial = bool(self.registo.get("username"))

        bloco = ctk.CTkFrame(
            self,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=8,
        )
        bloco.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(
            bloco,
            text="CREDENCIAL",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 4))

        if not tem_credencial:
            ctk.CTkLabel(
                bloco,
                text="Sem credencial definida.",
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=12)

            ctk.CTkLabel(
                bloco,
                text=(
                    "Este responsável não pode entrar no sistema até "
                    "que lhe seja atribuído um utilizador e password."
                ),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                anchor="w",
                justify="left",
                wraplength=280,
            ).pack(fill="x", padx=12, pady=(2, 8))

            ctk.CTkButton(
                bloco,
                text="Definir credencial",
                height=30,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.AZUL_PRINCIPAL,
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                command=lambda: DefinirCredencialModal(
                    self.tela_lista, self.registo
                ).focus(),
            ).pack(fill="x", padx=12, pady=(0, 12))
        else:
            ctk.CTkLabel(
                bloco,
                text=f"Utilizador: {self.registo['username']}",
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).pack(fill="x", padx=12)

            ultimo = self.registo.get("ultimo_login") or ""
            texto_ultimo = (
                f"Último acesso: {ultimo}"
                if ultimo
                else "Último acesso: nunca"
            )

            ctk.CTkLabel(
                bloco,
                text=texto_ultimo,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                anchor="w",
            ).pack(fill="x", padx=12, pady=(2, 8))

            ctk.CTkButton(
                bloco,
                text="Alterar password",
                height=30,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.AZUL_PRINCIPAL,
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                command=lambda: AlterarPasswordModal(
                    self.tela_lista, self.registo
                ).focus(),
            ).pack(fill="x", padx=12, pady=(0, 12))

    def _centrar_sobre_com(self, janela, largura, altura):
        janela.update_idletasks()
        x = janela.winfo_rootx() + (janela.winfo_width() - largura) // 2
        y = janela.winfo_rooty() + (janela.winfo_height() - altura) // 2
        self.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")

    def _separador(self):
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=16, pady=(8, 5)
        )

    def _botao(self, texto, text_color, hover_color, acao, ativo=True):
        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color if ativo else tema.TEXTO_INDISPONIVEL,
            border_width=1,
            border_color=tema.COR_BORDA,
            state="normal" if ativo else "disabled",
            command=executar,
        ).pack(fill="x", padx=16, pady=3)


# =====================================================================
# v1.5.0 — MODAIS DE CREDENCIAL
# =====================================================================


class DefinirCredencialModal(ctk.CTkToplevel):
    """Modal para atribuir credencial a um responsável que não tem."""

    def __init__(self, tela_lista, registo):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.registo = registo

        # v1.6.0 — o termo é condição de acesso: sem texto em vigor
        # não há credencial a atribuir. A verificação vem ANTES do
        # `_colocar_no_topo` de propósito — um `grab_set()` numa
        # janela que vai ser destruída deixa a aplicação sem foco.
        try:
            self.estado_termo = termos.verificar(
                termos.TITULAR_RESPONSAVEL,
                registo["id"],
                termos.CONFIDENCIALIDADE,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            self.after(0, self.destroy)
            return

        self.title(f"Definir credencial — {registo['id']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Definir credencial",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(24, 2))

        ctk.CTkLabel(
            self,
            text=f"{registo['nome']} — {registo['id']} · "
            f"{registo['tipo_utilizador']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 14))

        texto = self.estado_termo["texto"]

        self.bloco_termo = componentes.BlocoTermo(
            self,
            titulo="Termo de confidencialidade e uso do sistema",
            texto=texto["texto"],
            versao=texto["versao"],
            rotulo="Li e aceito o termo de confidencialidade. *",
            ao_mudar=self._ao_mudar_termo,
        )
        self.bloco_termo.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkLabel(
            self,
            text="Utilizador",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_username = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            width=380,
            state="disabled",
            fg_color=tema.LINHA_ALTERNADA,
        )
        self.campo_username.pack(padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Password",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_password = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            width=380,
            show="•",
            state="disabled",
            fg_color=tema.LINHA_ALTERNADA,
        )
        self.campo_password.pack(padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Confirmar password",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_confirmar = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            width=380,
            show="•",
        )
        self.campo_confirmar.pack(padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text=(
                "A password é gravada com hash no formato modular. "
                "Não pode ser consultada depois — só substituída."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            justify="left",
            wraplength=380,
        ).pack(anchor="w", padx=24, pady=(0, 16))

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

        self.botao_definir = ctk.CTkButton(
            rodape,
            text="Definir",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.COR_BORDA,
            hover_color=tema.AZUL_CLARO,
            text_color_disabled=tema.TEXTO_INDISPONIVEL,
            state="disabled",
            command=self._gravar,
        )
        self.botao_definir.pack(side="right")

    def _ao_mudar_termo(self):
        """Destranca (ou volta a trancar) os campos e o botão.

        Bloquear é legítimo aqui porque isto não é consentimento —
        é uma condição de acesso. Um consentimento RGPD nunca
        poderia travar nada.
        """
        aceite = self.bloco_termo.esta_aceite()
        estado = "normal" if aceite else "disabled"
        fundo = tema.COR_FUNDO if aceite else tema.LINHA_ALTERNADA

        for campo in (
            self.campo_username,
            self.campo_password,
            self.campo_confirmar,
        ):
            campo.configure(state=estado, fg_color=fundo)

        self.botao_definir.configure(
            state=estado,
            fg_color=tema.AZUL_PRINCIPAL if aceite else tema.COR_BORDA,
        )

        if aceite:
            self.campo_username.focus_set()

    def _gravar(self):
        username = self.campo_username.get().strip()
        password = self.campo_password.get()
        confirmar = self.campo_confirmar.get()

        if not self.bloco_termo.esta_aceite():
            componentes.mostrar_erro(
                "É preciso aceitar o termo de confidencialidade."
            )
            return

        if password != confirmar:
            componentes.mostrar_erro(
                "A password e a confirmação não coincidem."
            )
            return

        # A aceitação grava-se ANTES da credencial, de propósito. Se
        # falhar, ninguém fica com acesso. Pela ordem contrária, uma
        # falha aqui deixava a pessoa a entrar no sistema sem registo
        # nenhum de ter aceitado — que é exatamente o que esta tabela
        # existe para evitar.
        autor = self.tela_lista._autor()

        try:
            termos.registar(
                termos.TITULAR_RESPONSAVEL,
                self.registo["id"],
                termos.CONFIDENCIALIDADE,
                registado_por_id=autor["id"] if autor else None,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            utilizadores.definir_credencial(
                self.registo["id"],
                username,
                password,
                self.tela_lista._autor(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Credencial definida para {self.registo['nome']}."
        )
        self.destroy()
        self.tela_lista._recarregar()


class AlterarPasswordModal(ctk.CTkToplevel):
    """Modal para trocar a password de um responsável.

    Duas situações, detetadas automaticamente:

      - O PRÓPRIO altera a sua password: mostra 3 campos
        (password atual, nova, confirmar).
      - Um MASTER altera a password de outro: mostra 2 campos
        (nova, confirmar). O Master não sabe a antiga.
    """

    def __init__(self, tela_lista, registo):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.registo = registo

        autor = tela_lista._autor()
        self.e_o_proprio = autor is not None and autor["id"] == registo["id"]

        self.title(f"Alterar password — {registo['id']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Alterar password",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(24, 2))

        ctk.CTkLabel(
            self,
            text=f"{registo['nome']} — {registo['id']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 18))

        if self.e_o_proprio:
            ctk.CTkLabel(
                self,
                text="Password atual",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=24)

            self.campo_atual = ctk.CTkEntry(
                self,
                corner_radius=tema.RAIO_CAMPO,
                width=380,
                show="•",
            )
            self.campo_atual.pack(padx=24, pady=(2, 12))
        else:
            self.campo_atual = None

        ctk.CTkLabel(
            self,
            text="Password nova",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_nova = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            width=380,
            show="•",
        )
        self.campo_nova.pack(padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Confirmar password nova",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_confirmar = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            width=380,
            show="•",
        )
        self.campo_confirmar.pack(padx=24, pady=(2, 18))

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
            text="Guardar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._gravar,
        ).pack(side="right")

        if self.campo_atual is not None:
            self.campo_atual.focus_set()
        else:
            self.campo_nova.focus_set()

    def _gravar(self):
        atual = self.campo_atual.get() if self.campo_atual else ""
        nova = self.campo_nova.get()
        confirmar = self.campo_confirmar.get()

        if nova != confirmar:
            componentes.mostrar_erro(
                "A password nova e a confirmação não coincidem."
            )
            return

        try:
            utilizadores.alterar_password(
                self.registo["id"],
                atual,
                nova,
                self.tela_lista._autor(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso("Password alterada.")
        self.destroy()
        self.tela_lista._recarregar()


# =====================================================================
# Unidades do responsável (inalterado desde a v1.4.0)
# =====================================================================


class UnidadesDoResponsavelModal(ctk.CTkToplevel):
    """Popup para atribuir e remover as unidades que um responsável
    gere."""

    def __init__(self, tela_lista, registo):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.registo = registo

        self.title(f"Gerir Unidades — {registo['id']}")
        self.geometry("520x520")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=registo["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 0))

        ctk.CTkLabel(
            self,
            text="Unidades que este responsável gere",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20)

        self.combo_unidade = componentes.Seletor(
            barra,
            values=["—"],
            width=300,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_unidade.pack(side="left")

        ctk.CTkButton(
            barra,
            text="+ Adicionar",
            width=110,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._adicionar,
        ).pack(side="left", padx=(8, 0))

        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="both", expand=True, padx=20, pady=(14, 8))

        self.area_geridas = ctk.CTkScrollableFrame(
            cartao, fg_color="transparent"
        )
        self.area_geridas.pack(fill="both", expand=True)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self._fechar,
        ).pack(fill="x", padx=20, pady=(0, 16))

        self._recarregar()

    def _fechar(self):
        self.destroy()
        self.tela_lista._recarregar()

    def _recarregar(self):
        for widget in self.area_geridas.winfo_children():
            widget.destroy()

        try:
            geridas = unidades.unidades_geridas_por(self.registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        geridas.sort(key=lambda unidade: unidade["nome"])
        self._preencher_seletor(geridas)

        if not geridas:
            ctk.CTkLabel(
                self.area_geridas,
                text="Nenhuma unidade atribuída.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=13),
            ).pack(pady=30)
            return

        for indice, unidade in enumerate(geridas):
            self._desenhar_gerida(unidade, indice % 2 == 1)

    def _preencher_seletor(self, geridas):
        ja_geridas = {unidade["id"] for unidade in geridas}

        disponiveis = [
            unidade
            for unidade in unidades.listar()
            if unidade["id"] not in ja_geridas
        ]
        disponiveis.sort(key=lambda unidade: unidade["nome"])

        self.id_por_rotulo = {
            f"{unidade['id']} · {unidade['nome']}": unidade["id"]
            for unidade in disponiveis
        }

        if self.id_por_rotulo:
            rotulos = sorted(self.id_por_rotulo)
            self.combo_unidade.configure(values=rotulos, state="normal")
            self.combo_unidade.set(rotulos[0])
        else:
            self.combo_unidade.configure(
                values=["— Sem unidades disponíveis —"], state="disabled"
            )
            self.combo_unidade.set("— Sem unidades disponíveis —")

    def _desenhar_gerida(self, unidade, tingida):
        linha = ctk.CTkFrame(
            self.area_geridas,
            height=38,
            corner_radius=0,
            fg_color=tema.LINHA_ALTERNADA if tingida else "transparent",
        )
        linha.pack(fill="x")
        linha.pack_propagate(False)

        ctk.CTkLabel(
            linha,
            text=f"{unidade['id']} · {unidade['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left", padx=(14, 0))

        ctk.CTkButton(
            linha,
            text="Remover",
            width=80,
            height=24,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=lambda: self._remover(unidade),
        ).pack(side="right", padx=(0, 14))

    def _adicionar(self):
        unidade_id = self.id_por_rotulo.get(self.combo_unidade.get())

        if unidade_id is None:
            componentes.mostrar_erro("Escolha uma unidade a acrescentar.")
            return

        try:
            unidades.atribuir_responsavel(unidade_id, self.registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self._recarregar()

    def _remover(self, unidade):
        if not componentes.confirmar(
            f"Deixar de atribuir {unidade['nome']} a "
            f"{self.registo['nome']}?",
            titulo="Remover unidade",
        ):
            return

        try:
            unidades.remover_atribuicao(unidade["id"], self.registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self._recarregar()


# =====================================================================
# Formulários de criar e editar responsável
# =====================================================================


class _FormularioResponsavel(ctk.CTkToplevel):
    """Base dos formulários de criar e editar.

    v1.5.0 — o combo "Tipo de utilizador" adapta-se ao autor:

      - Sem responsável ativo: desativado.
      - Autor Master: todas as opções.
      - Autor Admin: só Staff (para criar/editar Staff).
    """

    def __init__(
        self,
        tela_lista,
        titulo,
        texto_botao,
        nome="",
        contacto="",
        tipo_utilizador="Staff",
    ):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title(titulo)
        self.geometry("440x420")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 16))

        ctk.CTkLabel(
            self,
            text="Nome",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.pack(fill="x", padx=20, pady=(2, 12))
        self.campo_nome.insert(0, nome)

        ctk.CTkLabel(
            self,
            text="Tipo de utilizador",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        # ---- v1.5.0 — três estados do combo ------------------------
        autor = sessao.obter_responsavel_ativo()

        if autor is None:
            opcoes = list(responsaveis.TIPOS_UTILIZADOR)
            combo_ativo = False
            ajuda = "Entre no sistema para escolher o tipo de utilizador."
        elif autor["tipo_utilizador"] == "Master":
            opcoes = list(responsaveis.TIPOS_UTILIZADOR)
            combo_ativo = True
            ajuda = "Define o perfil de acesso do responsável."
        else:  # Admin
            opcoes = ["Staff"]
            combo_ativo = True
            ajuda = "Um Admin só pode criar ou editar Staff."

        self.campo_tipo_utilizador = componentes.Seletor(
            self,
            values=opcoes,
            corner_radius=tema.RAIO_CAMPO,
            state="normal" if combo_ativo else "disabled",
        )
        self.campo_tipo_utilizador.pack(fill="x", padx=20, pady=(2, 6))

        if tipo_utilizador in opcoes:
            self.campo_tipo_utilizador.set(tipo_utilizador)
        else:
            self.campo_tipo_utilizador.set(opcoes[0])

        ctk.CTkLabel(
            self,
            text=ajuda,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        ctk.CTkLabel(
            self,
            text="Contacto (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_contacto = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="Telefone, email ou extensão interna",
        )
        self.campo_contacto.pack(fill="x", padx=20, pady=(2, 6))
        self.campo_contacto.insert(0, contacto)

        ctk.CTkLabel(
            self,
            text="O formato do contacto é livre e não é validado.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=20)

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16)

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
            text=texto_botao,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._gravar,
        ).pack(side="right")

        self.campo_nome.focus_set()

    def _valores(self):
        return (
            self.campo_nome.get().strip(),
            self.campo_contacto.get().strip(),
            self.campo_tipo_utilizador.get(),
        )

    def _gravar(self):
        raise NotImplementedError


class NovoResponsavelModal(_FormularioResponsavel):
    """Formulário de criação de um responsável."""

    def __init__(self, tela_lista):
        super().__init__(
            tela_lista,
            titulo="Novo Responsável",
            texto_botao="Criar",
        )

    def _gravar(self):
        nome, contacto, tipo_utilizador = self._valores()

        try:
            registo = responsaveis.criar(
                nome,
                contacto,
                tipo_utilizador,
                autor=self.tela_lista._autor(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Responsável criado com sucesso: {registo['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class EditarResponsavelModal(_FormularioResponsavel):
    """Formulário de edição do nome, contacto e tipo."""

    def __init__(self, tela_lista, registo):
        self.registo = registo
        super().__init__(
            tela_lista,
            titulo=f"Editar Responsável — {registo['id']}",
            texto_botao="Guardar",
            nome=registo["nome"],
            contacto=registo["contacto"],
            tipo_utilizador=registo["tipo_utilizador"],
        )

    def _gravar(self):
        nome, contacto, tipo_utilizador = self._valores()

        try:
            responsaveis.atualizar(
                self.registo["id"], nome=nome, contacto=contacto
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        if tipo_utilizador != self.registo["tipo_utilizador"]:
            try:
                responsaveis.alterar_tipo_utilizador(
                    self.registo["id"],
                    tipo_utilizador,
                    self.tela_lista._autor(),
                )
            except ValueError as erro:
                componentes.mostrar_erro(str(erro))
                return

        componentes.mostrar_sucesso("Responsável atualizado.")
        self.destroy()
        self.tela_lista._recarregar()
