"""Ecrã de Configurações — 3 tabs por área (Operação · Financeiro · Sistema).

Substitui o placeholder que existia até à v1.5.x. Segue o mockup
HTML validado em 19/09/2026, com duas vistas:

  - Master: vê as 3 tabs completas.
  - Admin:  vê apenas Operação + Financeiro, e dentro da Financeiro
            só as chaves que lhe pertencem (as de caução ficam de
            fora, com aviso).

Cada opção é uma linha com título + descrição + valor atual (só
leitura) + botão "Gerir" (v1.11.2, mockup aprovado a 07/10/2026). O
Gerir abre o `GerirConfiguracaoModal`: campo, resumo antes → depois
enquanto se escreve, e "Confirmar alteração" (só ativo com um valor
novo e válido). Até à v1.11.1 o controlo estava na própria linha e
gravava logo, com um segundo modal de confirmação.

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

ALTERAÇÃO 04/10/2026 (v1.8.2) — separador "Financeiro" inteiro em
desenvolvimento:

- Caução, Época alta e Documentos gerados ainda não têm efeito no
  resto do sistema, por isso o separador inteiro fica bloqueado
  (`_TABS_BLOQUEADAS`): uma só faixa amarela no topo e todos os
  controlos desativados.
- Os controlos desativados passam a ficar CINZENTOS. Antes só
  ficavam `disabled`, e o CustomTkinter mantém o fundo azul dos
  botões e dos seletores — no ecrã pareciam ativos (teste F12).
- Para reativar: tirar "financeiro" de `_TABS_BLOQUEADAS`.
"""

import logging

import customtkinter as ctk

import configuracoes
import sistema
import termos
import utilizadores
from . import componentes
from . import sessao
from . import tema
from .gui_configuracoes_modal import GerirConfiguracaoModal, formatar_valor
from .gui_documentos_legais import publicar_documento, ver_texto
from . import gui_servidores

logger = logging.getLogger(__name__)

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
                "titulo": "Servidor da base de dados",
                "chaves": ("_acao_servidores",),
            },
            {
                "titulo": "Documentos legais",
                "chaves": ("_acao_documentos_legais",),
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

# Separadores inteiros em desenvolvimento (pelo "id" do `_TABS`).
# Todas as secções do separador ficam bloqueadas e aparece uma só
# faixa amarela no topo, em vez de uma por secção.
_TABS_BLOQUEADAS = {
    "financeiro",
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

        tab_bloqueada = tab_def["id"] in _TABS_BLOQUEADAS
        if tab_bloqueada:
            self._aviso_em_desenvolvimento(area, separador=True)

        # Aviso para Admin na tab Financeiro
        if (
            tab_def["id"] == "financeiro"
            and sessao.tipo_utilizador_ativo() == "Admin"
        ):
            self._avisar_permissao(area)

        # Secções
        for secao in tab_def["secoes"]:
            self._desenhar_secao(area, secao, tab_bloqueada=tab_bloqueada)

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

    def _desenhar_secao(self, master, secao, tab_bloqueada=False):
        """Desenha uma secção — título cinza em maiúsculas + cartão
        com as opções.

        Se a secção estiver em `_SECOES_BLOQUEADAS`, aparece um
        aviso amarelo antes do título e os controlos das chaves
        ficam disabled. Com `tab_bloqueada` (separador inteiro em
        `_TABS_BLOQUEADAS`) os controlos também ficam disabled, mas
        sem aviso próprio — o do topo do separador chega.
        """
        bloqueada = tab_bloqueada or secao["titulo"] in _SECOES_BLOQUEADAS

        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.pack(fill="x", pady=(0, 20))

        # Aviso amarelo por cima do título, quando a secção está
        # bloqueada (em desenvolvimento).
        if bloqueada and not tab_bloqueada:
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

    def _aviso_em_desenvolvimento(self, master, separador=False):
        """Faixa amarela a avisar que a secção (ou, com `separador`,
        o separador inteiro) está em desenvolvimento.

        Desenhada por cima do título da secção — dá uma pausa antes
        de o utilizador chegar aos controlos bloqueados.
        """
        alvo = "deste separador" if separador else "desta secção"
        aviso = ctk.CTkFrame(
            master,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        aviso.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            aviso,
            text=(
                f"⚠  Em desenvolvimento — as opções {alvo} estão "
                "temporariamente bloqueadas."
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
        """Desenha uma linha da secção — título + descrição + valor
        atual (só leitura) + botão "Gerir" (v1.11.2, mockup aprovado
        a 07/10/2026).

        O valor muda-se no `GerirConfiguracaoModal`, que mostra o
        resumo antes → depois e grava. 'bloqueada' — quando True, o
        Gerir fica cinzento e não responde (secções em
        `_SECOES_BLOQUEADAS` e separadores em `_TABS_BLOQUEADAS`).
        """
        chave = definicao["chave"]
        valor_atual = configuracoes.obter(chave)

        linha = componentes.Contentor(master)
        linha.pack(fill="x", padx=16, pady=14)

        # Texto (título + descrição)
        bloco_texto = componentes.Contentor(linha)
        bloco_texto.pack(side="left", fill="x", expand=True)

        componentes.Rotulo(
            bloco_texto, self._titulo_amigavel(chave), "texto"
        ).pack(fill="x")

        componentes.Rotulo(
            bloco_texto, definicao["descricao"], "secundario",
            justify="left", wraplength=600, height=0,
        ).pack(fill="x", pady=(2, 0))

        # Gerir à direita, valor atual logo antes dele.
        botao = componentes.Botao(
            linha, "Gerir",
            lambda: self._gerir(definicao, celula_valor),
            width=80,
        )
        botao.pack(side="right", padx=(16, 0))

        celula_valor = componentes.Contentor(linha)
        celula_valor.pack(side="right", padx=(20, 0))
        self._mostrar_valor(celula_valor, definicao, valor_atual)

        if bloqueada:
            self._bloquear_controlo(botao)

        # Linha fina em baixo (exceto na última — tratada pelo cartão)
        componentes.Separador(master).pack(fill="x")

    def _mostrar_valor(self, celula, definicao, valor):
        """(Re)desenha o valor atual de uma linha: pílula Sim/Não nos
        sim/não, texto forte nos outros."""
        for filho in celula.winfo_children():
            filho.destroy()

        texto = formatar_valor(definicao["chave"], valor, definicao["tipo"])

        if definicao["tipo"] == "bool":
            componentes.Etiqueta(
                celula, texto, estilo="livre" if valor else "info"
            ).pack(anchor="e")
            return

        componentes.Rotulo(
            celula, texto, "forte", anchor="e", justify="right",
            wraplength=300, height=0,
        ).pack(anchor="e")

    def _gerir(self, definicao, celula_valor):
        """Abre o modal Gerir; depois de gravar, atualiza a linha."""
        if sessao.obter_responsavel_ativo() is None:
            componentes.mostrar_erro(
                "Não há responsável ativo. Entre novamente no sistema."
            )
            return

        GerirConfiguracaoModal(
            self,
            titulo=self._titulo_amigavel(definicao["chave"]),
            definicao=definicao,
            valor_atual=configuracoes.obter(definicao["chave"]),
            ao_gravar=lambda novo: self._mostrar_valor(
                celula_valor, definicao, novo
            ),
        )

    def _bloquear_controlo(self, controlo):
        """Põe um controlo já criado em modo disabled.

        O `controlo` pode ser:
        - um `CTkSwitch` (bool)
        - um `CTkFrame` com filhos (número, texto, tupla)

        No caso do frame, percorre os filhos recursivamente e
        desativa todos os widgets interativos que encontrar.
        """
        if isinstance(controlo, ctk.CTkSwitch):
            controlo.configure(
                state="disabled", progress_color=tema.CINZA_INDISPONIVEL
            )
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
        #
        # v1.8.2: além do `state`, as cores passam a cinzento. Um
        # CTkButton ou CTkOptionMenu `disabled` mantém o fundo azul e
        # parecia ativo no ecrã.
        try:
            if isinstance(widget, ctk.CTkButton):
                widget.configure(
                    state="disabled",
                    fg_color=tema.CINZA_INDISPONIVEL,
                    text_color_disabled=tema.TEXTO_INDISPONIVEL,
                )
            elif isinstance(widget, ctk.CTkOptionMenu):
                widget.configure(
                    state="disabled",
                    fg_color=tema.CINZA_INDISPONIVEL,
                    button_color=tema.CINZA_INDISPONIVEL,
                    text_color_disabled=tema.TEXTO_INDISPONIVEL,
                )
            elif isinstance(widget, ctk.CTkEntry):
                widget.configure(
                    state="disabled",
                    fg_color=tema.CINZA_INDISPONIVEL,
                    text_color=tema.TEXTO_INDISPONIVEL,
                )
            elif isinstance(widget, (ctk.CTkSwitch, ctk.CTkTextbox)):
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
            "operacao.duracao_minima_meses": (
                "Duração mínima de contrato (meses)"
            ),
            "financeiro.multiplicador_caucao": (
                "Multiplicador de caução sugerido"
            ),
            "financeiro.multiplicador_maximo_caucao": (
                "Multiplicador máximo de caução"
            ),
            "financeiro.epoca_alta_inicio": "Início da época alta",
            "financeiro.epoca_alta_fim": "Fim da época alta",
            "empresa.pasta_relatorios": "Pasta dos relatórios",
            "stock.rol_automatico_airbnb": (
                "Enviar rol automaticamente ao criar reserva Airbnb"
            ),
            "stock.permitir_envio_parcial": "Permitir envio parcial",
        }

        return str(mapa.get(chave, chave))

    # -- ações ---------------------------------------------------------

    def _desenhar_acao(self, master, chave_acao):
        """Desenha uma linha especial para ações (backup, reset)."""
        if chave_acao == "_acao_forcar_backup":
            self._linha_forcar_backup(master)
        elif chave_acao == "_acao_comecar_do_zero":
            self._linha_comecar_do_zero(master)
        elif chave_acao == "_acao_documentos_legais":
            self._linha_documentos_legais(master)
        elif chave_acao == "_acao_servidores":
            gui_servidores.desenhar_seletor(master)

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

    # -- documentos legais (v1.6.0) ------------------------------------

    def _linha_documentos_legais(self, master):
        """Uma linha por documento legal, dentro do cartão da secção.

        Guarda o cartão em `self._cartao_documentos` para poder
        redesenhar só esta secção depois de publicar — em vez de
        reconstruir o ecrã todo, que devolvia o utilizador à tab
        Operação a meio do trabalho dele.
        """
        self._cartao_documentos = master
        self._desenhar_documentos(master)

    def _desenhar_documentos(self, master):
        documentos = termos.estado_documentos()
        total = self._total_colaboradores()

        for indice, documento in enumerate(documentos):
            if indice > 0:
                ctk.CTkFrame(master, height=1, fg_color=tema.COR_BORDA).pack(
                    fill="x"
                )

            self._linha_documento(master, documento, total)

    def _recarregar_documentos(self):
        """Redesenha só a secção dos documentos."""
        for filho in self._cartao_documentos.winfo_children():
            filho.destroy()

        self._desenhar_documentos(self._cartao_documentos)

    def _total_colaboradores(self):
        """Quantas pessoas podem entrar no sistema.

        É o denominador do "2 de 4": conta os responsáveis ativos
        que já têm credencial definida. Quem não tem credencial não
        entra, logo não tem termo nenhum para aceitar e não faz
        sentido aparecer na conta.
        """
        try:
            lista = utilizadores.listar_com_estado(incluir_inativos=False)
        except ValueError:
            return 0

        return len([r for r in lista if r.get("username")])

    def _linha_documento(self, master, documento, total_colaboradores):
        texto = documento["texto"]
        publicado = texto is not None

        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=14)

        bloco_texto = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_texto.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            bloco_texto,
            text=documento["rotulo"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            bloco_texto,
            text=self._resumo_documento(documento, total_colaboradores),
            text_color=(
                tema.COR_TEXTO_SECUNDARIO if publicado else tema.TEXTO_ERRO
            ),
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=520,
        ).pack(fill="x", pady=(2, 0))

        acoes = ctk.CTkFrame(linha, fg_color="transparent")
        acoes.pack(side="right", padx=(20, 0))

        ctk.CTkButton(
            acoes,
            text="Ver texto",
            width=90,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            font=ctk.CTkFont(size=11),
            state="normal" if publicado else "disabled",
            command=lambda: ver_texto(self, documento),
        ).pack(side="left")

        ctk.CTkButton(
            acoes,
            text=(
                "Publicar versão nova" if publicado else "Publicar 1.ª versão"
            ),
            width=150,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=("transparent" if publicado else tema.AZUL_PRINCIPAL),
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=(tema.AZUL_PRINCIPAL if publicado else "#FFFFFF"),
            hover_color=(tema.ID_CHIP_FUNDO if publicado else tema.AZUL_CLARO),
            font=ctk.CTkFont(size=11),
            command=lambda: self._publicar_documento(documento),
        ).pack(side="left", padx=(8, 0))

    def _resumo_documento(self, documento, total_colaboradores):
        """A linha pequena por baixo do nome do documento."""
        texto = documento["texto"]

        if texto is None:
            return (
                "Sem versão publicada — o sistema não tem nada para "
                "mostrar a quem entra."
            )

        publicado_em = texto["publicado_em"]
        data = (
            publicado_em.strftime("%d/%m/%Y")
            if hasattr(publicado_em, "strftime")
            else str(publicado_em)
        )

        base = f"Versão {texto['versao']} · publicada em {data}"
        aceites = documento["aceitacoes"]

        if documento["bloqueia"]:
            return (
                f"{base}  ·  {aceites} de {total_colaboradores} "
                "colaboradores aceitaram"
            )

        return (
            f"{base}  ·  entregue a {aceites} — é informação, não "
            "aceitação, e por isso não bloqueia ninguém"
        )

    def _publicar_documento(self, documento):
        """Abre o modal e, se publicou, redesenha a secção."""
        if publicar_documento(self, documento):
            self._recarregar_documentos()

    # -- ações específicas --------------------------------------------

    def _forcar_backup(self):
        """Executa o backup fora do arranque normal.

        28/09/2026 — a chamada ao `repositorio` passou para
        `sistema.criar_backup_manual` (a GUI não fala com a base).
        """
        caminho = sistema.criar_backup_manual(
            sessao.obter_responsavel_ativo()
        )

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

        password = confirmar_reset_sistema(self)

        if password is None:
            autor = sessao.obter_responsavel_ativo()
            logger.info(
                "Reset do sistema cancelado na confirmação — autor_id=%s",
                autor["id"] if autor else None,
            )
            return

        autor = sessao.obter_responsavel_ativo()

        if autor is None:
            componentes.mostrar_erro(
                "Não há responsável ativo. Entre novamente no sistema."
            )
            return

        try:
            sistema.comecar_do_zero(autor, password)
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
        componentes.cancelar_agendamentos(self)
        self.controlador.destroy()
