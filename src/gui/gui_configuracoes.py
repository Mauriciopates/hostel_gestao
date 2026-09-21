"""Ecrã de Configurações — 3 tabs por área (Operação · Financeiro · Sistema).

Substitui o placeholder que existia até à v1.5.x. Segue o mockup
HTML validado em 19/09/2026, com duas vistas:

  - Master: vê as 3 tabs completas.
  - Admin:  vê apenas Operação + Financeiro, e dentro da Financeiro
            só as chaves que lhe pertencem (as de caução ficam de
            fora, com aviso).

Cada opção é uma linha com título + descrição + controlo à direita.
Ao alterar um valor, aparece um modal de confirmação (antes → depois)
— exceto para as chaves que não mudam regra de negócio (pasta dos
relatórios, por exemplo). Se o utilizador cancelar, o controlo volta
ao valor antigo.

Segue a mesma disciplina de camadas do resto da GUI (decisão 7):
fala só com `configuracoes` (o módulo de negócio), `sessao` e
`componentes`. Nunca com `repositorio` diretamente.

ALTERAÇÃO 20/09/2026 — secção "Caução" temporariamente bloqueada:

- Os dois controlos da secção Caução
  (`financeiro.multiplicador_caucao` e
  `financeiro.multiplicador_maximo_caucao`) aparecem `disabled`
  (cinzentos, não editáveis).
- Por cima do título da secção, uma faixa amarela avisa que a
  secção está em desenvolvimento.
- O resto do ecrã (Operação, Época alta, Documentos gerados,
  Stock, Sistema) fica exatamente como estava.
- Quando a secção for reativada, basta remover a chave
  `"financeiro.multiplicador_caucao"` e
  `"financeiro.multiplicador_maximo_caucao"` do conjunto
  `_SECOES_BLOQUEADAS` e apagar o método `_aviso_em_desenvolvimento`.
"""

import customtkinter as ctk

import configuracoes
import sistema
from . import componentes
from . import sessao
from . import tema
from .gui_configuracoes_modal import confirmar_alteracao

# =====================================================================
# MAPA DAS SECÇÕES
# =====================================================================
#
# Cada tab tem uma lista de secções. Cada secção tem um título e uma
# lista de chaves (do `configuracoes._CHAVES`).
#
# Este mapa é a única coisa que a GUI precisa de saber sobre a
# estrutura — o tipo de controlo de cada chave vem do
# `configuracoes.listar_definicoes`.

_TABS = (
    {
        "id": "operacao",
        "titulo": "Operação",
        "so_master": False,
        "secoes": (
            {
                "titulo": "Regime mensal",
                "chaves": (
                    "operacao.dia_vencimento",
                    "operacao.aviso_previo_dias",
                    "operacao.duracao_minima_meses",
                ),
            },
        ),
    },
    {
        "id": "financeiro",
        "titulo": "Financeiro",
        "so_master": False,
        "secoes": (
            {
                "titulo": "Caução",
                "chaves": (
                    "financeiro.multiplicador_caucao",
                    "financeiro.multiplicador_maximo_caucao",
                ),
            },
            {
                "titulo": "Época alta",
                "chaves": (
                    "financeiro.epoca_alta_inicio",
                    "financeiro.epoca_alta_fim",
                ),
            },
            {
                "titulo": "Documentos gerados",
                "chaves": ("empresa.pasta_relatorios",),
            },
        ),
    },
    {
        "id": "sistema",
        "titulo": "Sistema",
        "so_master": True,
        "secoes": (
            {
                "titulo": "Stock",
                "chaves": (
                    "stock.rol_automatico_airbnb",
                    "stock.permitir_envio_parcial",
                ),
            },
            {
                "titulo": "Cópias de segurança",
                "chaves": ("_acao_forcar_backup",),
            },
            {
                "titulo": "Zona de perigo",
                "chaves": ("_acao_comecar_do_zero",),
            },
        ),
    },
)


# =====================================================================
# SECÇÕES EM DESENVOLVIMENTO
# =====================================================================
#
# Conjunto de títulos de secção cujos controlos ficam bloqueados e
# que ganham um aviso amarelo por cima. Os títulos têm de bater
# certo com o `"titulo"` de uma secção no `_TABS` acima.
#
# Para desbloquear uma secção: remover o título daqui. Fica tudo
# normal outra vez.

_SECOES_BLOQUEADAS = {
    "Caução",
}


# =====================================================================
# ECRÃ PRINCIPAL
# =====================================================================


class Configuracoes(ctk.CTkFrame):
    """Ecrã de Configurações — o substitui o placeholder."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        cabecalho = componentes.Cabecalho(self, titulo="Configurações")
        cabecalho.pack(fill="x", side="top")

        self._tabs_visiveis = self._calcular_tabs_visiveis()

        # Guarda: {id_tab: {"botao": CTkButton, "frame": CTkFrame}}
        self._tabs_ui = {}

        # Tab ativa — começa por None para o `_mostrar_tab` correr
        # sempre no fim do __init__ (sem o atalho que o faria sair).
        self._tab_ativa = None

        # ---- Barra de tabs (fila de botões) ---------------------------
        barra_tabs = ctk.CTkFrame(self, fg_color="transparent")
        barra_tabs.pack(fill="x", padx=20, pady=(4, 0))

        for tab_def in self._tabs_visiveis:
            botao = ctk.CTkButton(
                barra_tabs,
                text=tab_def["titulo"],
                width=120,
                height=32,
                corner_radius=0,
                fg_color="transparent",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.LINHA_ALTERNADA,
                font=ctk.CTkFont(size=12),
                command=lambda t=tab_def["id"]: self._mostrar_tab(t),
            )
            botao.pack(side="left")

            self._tabs_ui[tab_def["id"]] = {"botao": botao, "frame": None}

        # Linha fina por baixo da barra de tabs (para separar do conteúdo)
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20
        )

        # ---- Contentor onde os frames das tabs vivem ------------------
        self._area_tabs = ctk.CTkFrame(self, fg_color="transparent")
        self._area_tabs.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        # ---- Constrói os frames de cada tab ---------------------------
        for tab_def in self._tabs_visiveis:
            self._desenhar_tab(tab_def)

        # Mostra a tab inicial (a primeira da lista)
        if self._tabs_visiveis:
            self._mostrar_tab(self._tabs_visiveis[0]["id"])

    def _mostrar_tab(self, tab_id):
        """Troca a tab visível e pinta o botão correspondente.

        Chamada pelo clique num botão de tab. Esconde o frame da
        tab anterior (se existia), mostra o novo, e ajusta as
        cores dos botões para refletirem qual está ativo.
        """
        if tab_id == self._tab_ativa:
            return  # já está ativa

        self._tab_ativa = tab_id

        # ---- Mostra só o frame da tab ativa ---------------------------
        for tid, dados in self._tabs_ui.items():
            frame = dados["frame"]
            botao = dados["botao"]

            if tid == tab_id:
                if frame is not None:
                    frame.pack(fill="both", expand=True)
                    # Força o layout a recalcular-se depois de
                    # mostrar — sem isto, o CTkScrollableFrame pode
                    # ficar com altura 0 no primeiro `pack`.
                    self.update_idletasks()
                botao.configure(
                    fg_color=tema.AZUL_PRINCIPAL,
                    text_color="#FFFFFF",
                    hover_color=tema.AZUL_CLARO,
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
            else:
                if frame is not None:
                    frame.pack_forget()
                botao.configure(
                    fg_color="transparent",
                    text_color=tema.AZUL_PRINCIPAL,
                    hover_color=tema.LINHA_ALTERNADA,
                    font=ctk.CTkFont(size=12),
                )

    # -- perfil --------------------------------------------------------

    def _calcular_tabs_visiveis(self):
        """Devolve a lista de tabs que este perfil pode ver.

        Master: todas.
        Admin:  só as que não têm `so_master=True`.
        Outros (Staff): não devia chegar aqui, mas devolve lista vazia.
        """
        perfil = sessao.tipo_utilizador_ativo()

        if perfil == "Master":
            return list(_TABS)

        if perfil == "Admin":
            return [t for t in _TABS if not t["so_master"]]

        # Staff nunca chega aqui — a sidebar esconde "Configurações".
        # Mas se por algum caminho chegar, não mostra nada.
        return []

    def _pode_ver_chave(self, definicao):
        """Confirma se o perfil atual pode ver/alterar a chave.

        Master vê tudo. Admin só vê chaves com perfil 'master_admin'.
        """
        perfil = sessao.tipo_utilizador_ativo()

        if perfil == "Master":
            return True

        if perfil == "Admin":
            return definicao["perfil"] == "master_admin"

        return False

    # -- desenho -------------------------------------------------------

    def _desenhar_tab(self, tab_def):
        """Constrói o frame de uma tab — secções + opções.

        O frame NÃO é mostrado aqui — só criado. Quem decide se
        ele está visível é o `_mostrar_tab`, chamado no fim do
        `__init__` e a cada clique na barra de tabs.
        """
        # Frame da tab — vive dentro da `_area_tabs`, mas começa
        # escondido (o `_mostrar_tab` decide quando o mostrar).
        frame_tab = ctk.CTkFrame(self._area_tabs, fg_color="transparent")

        # Área com scroll, dentro do frame
        area = ctk.CTkScrollableFrame(frame_tab, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=4, pady=4)

        # Aviso para Admin na tab Financeiro
        if (
            tab_def["id"] == "financeiro"
            and sessao.tipo_utilizador_ativo() == "Admin"
        ):
            self._avisar_permissao(area)

        # Secções
        for secao in tab_def["secoes"]:
            self._desenhar_secao(area, secao)

        # Guarda a referência do frame no dicionário
        self._tabs_ui[tab_def["id"]]["frame"] = frame_tab

    def _avisar_permissao(self, master):
        """Aviso azul, só para Admin, a explicar o que não vê."""
        aviso = ctk.CTkFrame(
            master,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        aviso.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            aviso,
            text=(
                "ℹ  Nota: As opções de caução (secção abaixo) só podem "
                "ser alteradas por um utilizador Master."
            ),
            text_color=tema.AZUL_PRINCIPAL,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", padx=14, pady=10)

    def _desenhar_secao(self, master, secao):
        """Desenha uma secção — título cinza em maiúsculas + cartão
        com as opções.

        Se a secção estiver em `_SECOES_BLOQUEADAS`, aparece um
        aviso amarelo antes do título e os controlos das chaves
        ficam disabled.
        """
        bloqueada = secao["titulo"] in _SECOES_BLOQUEADAS

        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.pack(fill="x", pady=(0, 20))

        # Aviso amarelo por cima do título, quando a secção está
        # bloqueada (em desenvolvimento).
        if bloqueada:
            self._aviso_em_desenvolvimento(bloco)

        # Título da secção
        ctk.CTkLabel(
            bloco,
            text=secao["titulo"].upper(),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        # Cartão com borda
        cartao = ctk.CTkFrame(
            bloco,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x")

        # Para cada chave da secção
        for chave in secao["chaves"]:
            # Chaves especiais que não são configs — são ações
            if chave.startswith("_acao_"):
                self._desenhar_acao(cartao, chave)
                continue

            # Chave normal — buscar a definição
            definicao = self._definicao(chave)

            # Se o perfil não pode ver, salta (sem criar widget)
            if not self._pode_ver_chave(definicao):
                continue

            # Desenha a linha, passando se a secção está bloqueada
            self._desenhar_linha(cartao, definicao, bloqueada=bloqueada)

    def _aviso_em_desenvolvimento(self, master):
        """Faixa amarela a avisar que a secção está em desenvolvimento.

        Desenhada por cima do título da secção — dá uma pausa antes
        de o utilizador chegar aos controlos bloqueados.
        """
        aviso = ctk.CTkFrame(
            master,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        aviso.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            aviso,
            text=(
                "⚠  Em desenvolvimento — as opções desta secção "
                "estão temporariamente bloqueadas."
            ),
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", padx=14, pady=10)

    def _definicao(self, chave):
        """Vai buscar a definição de uma chave ao `configuracoes`.

        Usa `listar_definicoes` e procura pela chave — assim não
        duplicamos o mapa aqui. É mais lento (percorre a lista) mas
        é a única forma de manter a fonte de verdade num só sítio.
        """
        for d in configuracoes.listar_definicoes():
            if d["chave"] == chave:
                return d

        raise ValueError(f"Chave sem definição no configuracoes: {chave}")

    # -- linhas --------------------------------------------------------

    def _desenhar_linha(self, master, definicao, bloqueada=False):
        """Desenha uma linha da secção — título + descrição + controlo.

        'bloqueada' — quando True, o controlo é criado mas fica
        disabled (cinzento, sem responder ao clique). Usado pelas
        secções em `_SECOES_BLOQUEADAS`.
        """
        chave = definicao["chave"]
        valor_atual = configuracoes.obter(chave)

        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=14)

        # Texto (título + descrição)
        bloco_texto = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_texto.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            bloco_texto,
            text=self._titulo_amigavel(chave),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            bloco_texto,
            text=definicao["descricao"],
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=600,
        ).pack(fill="x", pady=(2, 0))

        # Controlo — consoante o tipo da chave
        controlo = self._criar_controlo(linha, definicao, valor_atual)
        controlo.pack(side="right", padx=(20, 0))

        # Bloquear depois de criar — os controlos não expõem o
        # `state` de forma uniforme, por isso cada um é tratado
        # pelo seu método `_bloquear_controlo`.
        if bloqueada:
            self._bloquear_controlo(controlo)

        # Linha fina em baixo (exceto na última — tratada pelo cartão)
        ctk.CTkFrame(master, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

    def _bloquear_controlo(self, controlo):
        """Põe um controlo já criado em modo disabled.

        O `controlo` pode ser:
        - um `CTkSwitch` (bool)
        - um `CTkFrame` com filhos (número, texto, tupla)

        No caso do frame, percorre os filhos recursivamente e
        desativa todos os widgets interativos que encontrar.
        """
        if isinstance(controlo, ctk.CTkSwitch):
            controlo.configure(state="disabled")
            return

        # Frame que contém outros widgets — percorre os filhos
        # (recursivamente) e desativa tudo o que seja interativo.
        self._desativar_recursivo(controlo)

    def _desativar_recursivo(self, widget):
        """Percorre um widget e os seus filhos, desativando os
        que aceitam input (CTkEntry, CTkButton, CTkOptionMenu,
        CTkSwitch, CTkTextbox).

        Widgets que não são interativos (CTkFrame, CTkLabel) são
        atravessados sem mexer, mas os seus filhos ainda são
        visitados.
        """
        # Cada tipo interativo tem o seu `configure(state=...)`.
        # Apanhamos as exceções individualmente — `CTkLabel` e
        # `CTkFrame` não aceitam `state`, e não queremos rebentar.
        try:
            if isinstance(
                widget,
                (
                    ctk.CTkEntry,
                    ctk.CTkButton,
                    ctk.CTkOptionMenu,
                    ctk.CTkSwitch,
                    ctk.CTkTextbox,
                ),
            ):
                widget.configure(state="disabled")
        except Exception:
            # Se algum widget específico não aceitar `state` por
            # alguma razão, não fazemos nada — o bloqueio é
            # cosmético, não é crítico.
            pass

        # Visitar os filhos (se houver)
        try:
            for filho in widget.winfo_children():
                self._desativar_recursivo(filho)
        except Exception:
            pass

    def _titulo_amigavel(self, chave):
        """Converte "operacao.dia_vencimento" num título legível.

        Não é tradução completa — o título humano já vive na GUI
        por não estar no `_CHAVES`. Mapeamos aqui.
        """
        mapa = {
            "operacao.dia_vencimento": "Dia de vencimento padrão",
            "operacao.aviso_previo_dias": "Aviso prévio padrão (dias)",
            "operacao.duracao_minima_meses": "Duração mínima de contrato (meses)",
            "financeiro.multiplicador_caucao": "Multiplicador de caução sugerido",
            "financeiro.multiplicador_maximo_caucao": "Multiplicador máximo de caução",
            "financeiro.epoca_alta_inicio": "Início da época alta",
            "financeiro.epoca_alta_fim": "Fim da época alta",
            "empresa.pasta_relatorios": "Pasta dos relatórios",
            "stock.rol_automatico_airbnb": (
                "Enviar rol automaticamente ao criar reserva Airbnb"
            ),
            "stock.permitir_envio_parcial": "Permitir envio parcial",
        }

        return str(mapa.get(chave, chave))

    # -- controlos -----------------------------------------------------

    def _criar_controlo(self, master, definicao, valor_atual):
        """Cria o widget certo para o tipo da chave.

        - int / decimal  → campo de texto pequeno + botão Guardar
        - bool           → pílula deslizante (CTkSwitch)
        - texto          → campo de texto + botão "Escolher" (se for pasta)
        - tupla_mes_dia  → dois dropdowns (dia + mês)
        """
        tipo = definicao["tipo"]

        if tipo == "bool":
            return self._controlo_bool(master, definicao, valor_atual)

        if tipo == "tupla_mes_dia":
            return self._controlo_tupla(master, definicao, valor_atual)

        if tipo == "texto":
            return self._controlo_texto(master, definicao, valor_atual)

        # int e decimal caem aqui
        return self._controlo_numerico(master, definicao, valor_atual)

    def _controlo_bool(self, master, definicao, valor_atual):
        """Pílula deslizante (CTkSwitch)."""
        chave = definicao["chave"]

        variavel = ctk.BooleanVar(value=bool(valor_atual))

        def ao_mudar():
            novo = variavel.get()
            self._tentar_gravar(chave, novo, None, valor_atual, "bool")

        switch = ctk.CTkSwitch(
            master,
            text="",
            variable=variavel,
            command=ao_mudar,
            progress_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.CINZA_INDISPONIVEL,
        )

        return switch

    def _controlo_numerico(self, master, definicao, valor_atual):
        """Campo de texto pequeno + botão Guardar ao lado.

        A gravação acontece só ao clicar em "Guardar" ou ao premir
        Enter no campo — nunca no `<FocusOut>`. O `FocusOut` era a
        origem de um ciclo infinito: cada vez que o modal de
        confirmação abria, roubava o foco ao campo, e ao fechar o
        foco voltava a sair, disparando o `FocusOut` outra vez.

        Com o botão explícito, a intenção é clara e o ciclo
        desaparece.
        """
        chave = definicao["chave"]
        tipo = definicao["tipo"]

        bloco = ctk.CTkFrame(master, fg_color="transparent")

        entrada = ctk.CTkEntry(
            bloco,
            width=70,
            corner_radius=tema.RAIO_CAMPO,
            justify="center",
        )
        entrada.insert(0, str(valor_atual))
        entrada.pack(side="left")

        def guardar(_evento=None):
            texto = entrada.get().strip()

            try:
                if tipo == "int":
                    novo = int(texto)
                else:
                    from decimal import Decimal

                    novo = Decimal(texto)
            except Exception:
                componentes.mostrar_erro("Valor inválido.")
                entrada.delete(0, "end")
                entrada.insert(0, str(valor_atual))
                return

            self._tentar_gravar(chave, novo, entrada, valor_atual, tipo)

        ctk.CTkButton(
            bloco,
            text="Guardar",
            width=70,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            font=ctk.CTkFont(size=11),
            command=guardar,
        ).pack(side="left", padx=(6, 0))

        # Enter no campo também grava — atalho útil.
        entrada.bind("<Return>", guardar)

        return bloco

    def _controlo_texto(self, master, definicao, valor_atual):
        """Campo de texto largo + botão Escolher (para pastas)."""
        chave = definicao["chave"]

        bloco = ctk.CTkFrame(master, fg_color="transparent")

        entrada = ctk.CTkEntry(
            bloco,
            width=280,
            corner_radius=tema.RAIO_CAMPO,
        )
        entrada.insert(0, str(valor_atual))
        entrada.pack(side="left")

        ctk.CTkButton(
            bloco,
            text="Escolher",
            width=90,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            font=ctk.CTkFont(size=11),
            command=lambda: self._escolher_pasta(chave, entrada, valor_atual),
        ).pack(side="left", padx=(8, 0))

        return bloco

    def _controlo_tupla(self, master, definicao, valor_atual):
        """Dois dropdowns (dia + mês) lado a lado."""
        chave = definicao["chave"]
        mes_atual, dia_atual = valor_atual

        bloco = ctk.CTkFrame(master, fg_color="transparent")

        # Mês
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
        combo_mes = componentes.Seletor(
            bloco,
            values=list(meses),
            width=80,
            corner_radius=tema.RAIO_CAMPO,
        )
        combo_mes.set(meses[mes_atual - 1])
        combo_mes.pack(side="left")

        # Dia
        dias = tuple(str(d) for d in range(1, 32))
        combo_dia = componentes.Seletor(
            bloco,
            values=list(dias),
            width=70,
            corner_radius=tema.RAIO_CAMPO,
        )
        combo_dia.set(str(dia_atual))
        combo_dia.pack(side="left", padx=(6, 0))

        def ao_mudar(_valor=None):
            novo_mes = meses.index(combo_mes.get()) + 1
            novo_dia = int(combo_dia.get())
            self._tentar_gravar(
                chave, (novo_mes, novo_dia), None, valor_atual, "tupla"
            )

        combo_mes.configure(command=ao_mudar)
        combo_dia.configure(command=ao_mudar)

        return bloco

    # -- ações ---------------------------------------------------------

    def _desenhar_acao(self, master, chave_acao):
        """Desenha uma linha especial para ações (backup, reset)."""
        if chave_acao == "_acao_forcar_backup":
            self._linha_forcar_backup(master)
        elif chave_acao == "_acao_comecar_do_zero":
            self._linha_comecar_do_zero(master)

    def _linha_forcar_backup(self, master):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=14)

        bloco_texto = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_texto.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            bloco_texto,
            text="Forçar backup agora",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            bloco_texto,
            text=(
                "Executa um dump da base de dados imediatamente, "
                "mesmo que já exista o de hoje."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=600,
        ).pack(fill="x", pady=(2, 0))

        ctk.CTkButton(
            linha,
            text="Forçar backup",
            width=140,
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._forcar_backup,
        ).pack(side="right", padx=(20, 0))

    def _linha_comecar_do_zero(self, master):
        # Cartão vermelho dentro da secção
        cartao = ctk.CTkFrame(
            master,
            fg_color=tema.VERMELHO_ERRO,
            border_width=1,
            border_color=tema.TEXTO_ERRO,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", padx=16, pady=14)

        linha = ctk.CTkFrame(cartao, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=14)

        bloco_texto = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_texto.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            bloco_texto,
            text="⚠  Começar do zero",
            text_color=tema.TEXTO_ERRO,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            bloco_texto,
            text=(
                "Apaga TODOS os dados e recria o sistema com um "
                "único utilizador Master padrão. Operação irreversível."
            ),
            text_color=tema.TEXTO_ERRO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=600,
        ).pack(fill="x", pady=(2, 0))

        ctk.CTkButton(
            linha,
            text="Começar do zero",
            width=160,
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.TEXTO_ERRO,
            hover_color="#A02D22",
            command=self._comecar_do_zero,
        ).pack(side="right", padx=(20, 0))

    # -- gravação ------------------------------------------------------

    def _tentar_gravar(self, chave, novo, widget, valor_antigo, tipo):
        """Chama o modal de confirmação, e só grava se o utilizador
        confirmar.

        'tipo' é o tipo do valor (int, decimal, bool, tupla, texto).
        'widget' é o controlo (para repor o valor antigo se cancelar);
        pode ser None nos casos em que não há repor (bool, tupla).
        """
        if novo == valor_antigo:
            return

        autor = sessao.obter_responsavel_ativo()

        if autor is None:
            componentes.mostrar_erro(
                "Não há responsável ativo. Entre novamente no sistema."
            )
            self._repor_widget(widget, valor_antigo)
            return

        # Modal de confirmação
        titulo = self._titulo_amigavel(chave)
        confirmado = confirmar_alteracao(
            self,
            titulo=titulo,
            chave=chave,
            valor_antigo=valor_antigo,
            valor_novo=novo,
        )

        if not confirmado:
            # Volta ao valor antigo
            self._repor_widget(widget, valor_antigo)
            return

        # Gravar via módulo de negócio (que valida permissão de novo)
        try:
            configuracoes.definir(chave, novo, autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            self._repor_widget(widget, valor_antigo)
            return

        componentes.mostrar_sucesso(
            f"{titulo} alterado para {self._formatar_valor(novo, tipo)}."
        )

    def _repor_widget(self, widget, valor_antigo):
        """Repõe o valor antigo no controlo, quando o utilizador
        cancela ou há erro.

        Só se aplica a campos de texto (`CTkEntry`). Os outros
        controlos (`CTkSwitch`, `CTkOptionMenu`) ficam como estão —
        repor um switch ou um dropdown seria mais complexo e o
        ganho é pequeno.
        """
        if widget is None:
            return

        if isinstance(widget, ctk.CTkEntry):
            widget.delete(0, "end")
            widget.insert(0, str(valor_antigo))

    def _formatar_valor(self, valor, tipo):
        """Formata um valor para mostrar na mensagem de sucesso."""
        if tipo == "bool":
            return "Ligado" if valor else "Desligado"

        if tipo == "tupla":
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

    # -- ações específicas --------------------------------------------

    def _escolher_pasta(self, chave, entrada, valor_atual):
        """Abre um diálogo nativo para escolher uma pasta."""
        from tkinter import filedialog

        pasta = filedialog.askdirectory(
            title="Escolher pasta",
            initialdir=str(valor_atual),
        )

        if not pasta:
            return

        entrada.delete(0, "end")
        entrada.insert(0, pasta)

        autor = sessao.obter_responsavel_ativo()

        if autor is None:
            return

        try:
            configuracoes.definir(chave, pasta, autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Pasta alterada: {pasta}")

    def _forcar_backup(self):
        """Executa o backup fora do arranque normal."""
        import repositorio

        try:
            caminho = repositorio.criar_backup_com_nome("manual")
        except AttributeError:
            # Se ainda não existir `criar_backup_com_nome`, cai no
            # `criar_backup` normal.
            caminho = repositorio.criar_backup()

        if caminho is None:
            componentes.mostrar_erro(
                "Não foi possível criar o backup. Verifique o MySQL "
                "e o `mysqldump`."
            )
            return

        componentes.mostrar_sucesso(f"Backup criado: {caminho}")

    def _comecar_do_zero(self):
        """Abre o modal de confirmação dupla e, se confirmado, executa
        o reset do sistema."""
        from .gui_configuracoes_modal import confirmar_reset_sistema

        confirmado = confirmar_reset_sistema(self)

        if not confirmado:
            return

        autor = sessao.obter_responsavel_ativo()

        if autor is None:
            componentes.mostrar_erro(
                "Não há responsável ativo. Entre novamente no sistema."
            )
            return

        try:
            sistema.comecar_do_zero(autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            "Sistema reiniciado.\n\n"
            "Vai ser necessário entrar de novo com as credenciais padrão:\n"
            "    Utilizador: admin\n"
            "    Password:   adm12345678"
        )

        # Logoff — adiado com `after_idle` para o `destroy()` não correr
        # a meio da callback do botão. Sem isto, ficavam `after(...)`
        # pendentes do Tk antigo a tentar correr depois de a janela já
        # estar destruída (mensagens "invalid command name ...update" no
        # terminal) e a nova Aplicacao não chegava a arrancar.
        self.after_idle(self._executar_logoff)

    def _executar_logoff(self):
        """Fecha a janela e pede ao `main_gui` para reabrir."""
        sessao.limpar_responsavel_ativo()
        self.controlador.reabrir = True
        self.controlador.destroy()
