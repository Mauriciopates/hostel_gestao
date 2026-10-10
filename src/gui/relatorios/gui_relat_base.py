"""Base do popup de relatórios: layout, lista lateral, barra de
período, calendário e exportação (PDF/CSV/Excel).

Os desenhadores de cada relatório vivem nas subclasses por área
(gui_relat_financeiro / _contratos / _stock)."""

from datetime import date, timedelta

import customtkinter as ctk
from tkcalendar import Calendar

import impressao

from .. import componentes
from .. import tema
from . import gui_relat_comum
from .gui_relat_comum import (
    PERIODO_PERSONALIZADO,
    CHIPS_PERIODO,
    PERIODO_DEFAULT,
    RELATORIOS,
)

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_relat_comum).
_autor_atual = gui_relat_comum.autor_atual
_intervalo_do_atalho = gui_relat_comum.intervalo_do_atalho
_intervalo_personalizado = gui_relat_comum.intervalo_personalizado
_intervalo_visivel = gui_relat_comum.intervalo_visivel

# =====================================================================


# POPUP DE UMA ÁREA — RelatorioModal
# =====================================================================


class RelatorioBase(ctk.CTkToplevel):
    """Popup grande com os relatórios de UMA área.

    Estrutura (mockup consolidado):

      - Cabeçalho: "Relatórios · <Área>" + data + responsável ativo.
      - Barra de período: chips de atalho + campo único de calendário.
        (Vazia neste bloco — preenchida no Bloco 3b.)
      - Corpo: lista lateral (só os relatórios da área aberta) +
        área de conteúdo (o relatório escolhido).
      - Rodapé: "Fechar" → volta ao hub.

    O popup é `transient` do hub (`tela_hub`), e fecha pela X nativa
    ou pelo botão "Fechar" — os dois voltam ao hub, que fica
    visível por trás.

    Estado interno:

      - `area` — a chave da área ("financeiro" / "contratos" / "stock"),
        fixa durante a vida do popup.
      - `relatorio_atual` — o id do relatório escolhido. Começa no
        primeiro da área, muda quando o utilizador clica na lista
        lateral.
      - `periodo_atual` — a chave do atalho escolhido ("mes_atual" /
        "mes_anterior" / "ultimos_30" / "este_ano"). O personalizado
        é gerido à parte (Bloco 3b). Default: `PERIODO_DEFAULT`.
      - `data_inicio` / `data_fim` — o intervalo já convertido para
        o motor (`data_fim` exclusivo). Recalculado sempre que o
        período muda. Os relatórios leem estes dois atributos.
      - `filtros_por_relatorio` — dicionário {id_relatorio: {chave:
        valor}} com as escolhas de filtros próprios de cada
        relatório. Persiste enquanto o popup estiver aberto — se o
        utilizador muda de relatório e volta, os filtros mantêm-se.
    """

    _LARGURA = 1000
    _ALTURA = 700

    def __init__(self, tela_hub, area, ao_pronto=None):
        super().__init__(tela_hub)
        # Chamado depois do primeiro relatório desenhado (v2.3.0): o hub
        # tira o seu "A abrir relatórios…".
        self._ao_pronto = ao_pronto
        self.tela_hub = tela_hub
        self.controlador = tela_hub.controlador

        self.area = area
        self.relatorio_atual = RELATORIOS[area][0]["id"]

        # Período inicial — sempre o default. O intervalo é calculado
        # agora e recalculado no Bloco 3b sempre que o período muda.
        self.periodo_atual = PERIODO_DEFAULT
        self.data_inicio, self.data_fim = _intervalo_do_atalho(
            self.periodo_atual
        )

        # Filtros próprios por relatório. Guarda as escolhas enquanto
        # o popup estiver aberto.
        self.filtros_por_relatorio = {}

        # Referências aos widgets que mudam com o estado — o Bloco 3b
        # e os blocos 5/6/7 precisam de os alcançar.
        self._rotulo_periodo = None
        self._campo_unico = None
        self._chips = {}

        # Seleção provisória do calendário personalizado. Tuplo
        # (inicio, fim) enquanto o utilizador escolhe — `None` quando
        # ainda não clicou, ou depois de Aplicar. Guardado aqui (e
        # não no calendário) porque o `tkcalendar` desta versão só
        # aceita `selectmode="day"`; o intervalo em dois cliques é
        # gerido por nós.
        self._selecao_personalizada = None

        self.title(f"Relatórios · {area.capitalize()}")
        self.geometry(f"{self._LARGURA}x{self._ALTURA}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_hub)
        componentes.colocar_no_topo(self)

        # Fechar pela X nativa da janela — mesmo comportamento do
        # botão "Fechar".
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self._construir_cabecalho()
        self._construir_barra_periodo()
        self._construir_corpo()
        self._construir_rodape()

        # Desenha a primeira vez. O conteúdo só vem quando a janela já
        # está no ecrã (no Windows o CTkToplevel aparece ~200 ms depois
        # de criado), para o "A calcular o relatório…" (v2.3.0) se ver
        # por cima dela.
        self._recarregar_lista_lateral()
        self.after(300, self._primeiro_desenho)

    def _primeiro_desenho(self):
        try:
            self._recarregar_conteudo()
        finally:
            if self._ao_pronto is not None:
                self._ao_pronto()
                self._ao_pronto = None

    # -- construção ---------------------------------------------------

    def _construir_cabecalho(self):
        """Cabeçalho do popup — título + data + responsável ativo.

        Não usa o `componentes.Cabecalho` porque esse é para ecrãs
        (ocupa a largura toda do frame que o contém); o popup é uma
        janela própria e queremos o cabeçalho dentro dela, com
        espaçamento ligeiro.
        """
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=18, pady=(14, 6))

        ctk.CTkLabel(
            cabecalho,
            text=f"Relatórios · {self.area.capitalize()}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        ativo = _autor_atual()
        nome = ativo["nome"] if ativo else "sem responsável"
        hoje = date.today().strftime("%d/%m/%Y")

        ctk.CTkLabel(
            cabecalho,
            text=f"{hoje} · {nome}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(side="right")

    def _construir_barra_periodo_vazia(self):
        """Cria o frame da barra de período — vazio neste bloco.

        O Bloco 3b preenche-o com os chips de atalho e o campo único
        de calendário. Os dois atributos (`self._chips`,
        `self._campo_unico`) ficam prontos a receber.

        O frame fica guardado em `self._frame_periodo` porque o
        relatório "Stock atual" precisa de o esconder (não tem
        período — é "agora").
        """
        self._frame_periodo = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_periodo.pack(fill="x", padx=18, pady=(0, 8))

    def _construir_corpo(self):
        """Corpo do popup — lista lateral + área de conteúdo.

        Grid de duas colunas: 190px para a lista, o resto para o
        conteúdo. A lista tem barra de scroll vertical própria; a
        área de conteúdo também (para relatórios com muitas linhas).
        """
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        corpo.grid_columnconfigure(0, weight=0, minsize=190)
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(0, weight=1)

        # Lista lateral
        self._lista_lateral = ctk.CTkScrollableFrame(
            corpo,
            fg_color=tema.LINHA_ALTERNADA,
            corner_radius=tema.RAIO_CARTAO,
            width=190,
        )
        self._lista_lateral.grid(row=0, column=0, sticky="nsw", padx=(0, 8))

        # Área de conteúdo — tem scroll vertical para relatórios
        # grandes (Ocupações com muitas linhas, Movimentos, etc.).
        self._area_conteudo = ctk.CTkScrollableFrame(
            corpo,
            fg_color="transparent",
        )
        self._area_conteudo.grid(row=0, column=1, sticky="nsew")

    def _construir_rodape(self):
        """Rodapé do popup — só o botão "Fechar".

        Os botões "Exportar CSV" e "Exportar PDF" NÃO ficam aqui.
        Ficam dentro da área de conteúdo, no fim de cada relatório
        (como no mockup) — porque cada relatório exporta dados
        diferentes, e o botão deve estar ao lado dos dados que
        exporta.
        """
        rodape = ctk.CTkFrame(self, fg_color=tema.LINHA_ALTERNADA)
        rodape.pack(fill="x", side="bottom")

        ctk.CTkButton(
            rodape,
            text="Fechar",
            width=110,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.ID_CHIP_FUNDO,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._fechar,
        ).pack(side="right", padx=18, pady=10)

    # -- recarregamento ----------------------------------------------

    def _recarregar_lista_lateral(self):
        """Desenha os relatórios da área na lista lateral.

        O item do relatório atual fica marcado a azul. Cada item é
        clicável — `tornar_cliclavel` liga o clique ao item e aos
        filhos (a etiqueta dentro dele).
        """
        for widget in self._lista_lateral.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self._lista_lateral,
            text=self.area.upper(),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 4))

        for rel in RELATORIOS[self.area]:
            ativo = rel["id"] == self.relatorio_atual
            botao = ctk.CTkButton(
                self._lista_lateral,
                text=rel["titulo"],
                height=28,
                corner_radius=6,
                fg_color=(tema.AZUL_PRINCIPAL if ativo else "transparent"),
                text_color=("#FFFFFF" if ativo else tema.COR_TEXTO),
                hover_color=tema.ID_CHIP_FUNDO,
                font=ctk.CTkFont(
                    size=11, weight="bold" if ativo else "normal"
                ),
                anchor="w",
                command=lambda r=rel["id"]: self._escolher_relatorio(r),
            )
            botao.pack(fill="x", padx=4, pady=1)

    def _recarregar_conteudo(self):
        """Redesenha o relatório escolhido, com a janelinha "A calcular
        o relatório…" por cima (v2.3.0, mockup aprovado a 10/10/2026):
        abrir, trocar de relatório, de período ou de filtro passa
        todo por aqui."""
        if not self.winfo_exists():
            return
        # A camada vai sobre o popup inteiro e não sobre a área do
        # conteúdo: o desenho começa por apagar os filhos dessa área.
        componentes.com_janela_carregar(
            self, "A calcular o relatório…", self._desenhar_conteudo
        )

    def _desenhar_conteudo(self):
        """Desenha o relatório escolhido na área de conteúdo.

        Despacha para a função `_desenhar_<id>` correspondente. Essas
        funções só existem nos blocos 5, 6 e 7 — neste bloco, mostro
        um placeholder em vez de rebentar, para o ecrã poder abrir
        e ser testado.
        """
        for widget in self._area_conteudo.winfo_children():
            widget.destroy()

        # O `_frame_periodo` é empacotado uma vez, no sítio certo,
        # no `_construir_barra_periodo`. Aqui só o escondemos ou
        # mostramos conforme o relatório aplique período ou não —
        # sem `pack()` outra vez, que dava erro de "already packed".
        aplica_periodo = self._relatorio_atual_aplica_periodo()
        if aplica_periodo:
            self._frame_periodo.pack(fill="x", padx=18, pady=(0, 8))
        else:
            self._frame_periodo.pack_forget()

        # Despacho para o desenhador do relatório. Todos os
        # desenhadores vivem nos blocos 5, 6 e 7. A chamada é feita
        # por getattr, para o método poder não existir ainda (durante
        # a construção por blocos) sem rebentar.
        nome_desenho = f"_desenhar_{self.relatorio_atual}"
        desenha = getattr(self, nome_desenho, None)

        if desenha is None:
            self._placeholder_bloco_seguinte()
            return

        import traceback

        try:
            desenha(self._area_conteudo)
        except Exception as erro:
            tb = traceback.format_exc()
            print(tb)
            componentes.mostrar_erro(
                f"Erro ao desenhar '{self.relatorio_atual}':\n\n"
                f"{type(erro).__name__}: {erro}"
            )

    def _placeholder_bloco_seguinte(self):
        """Ecrã provisório, enquanto o desenhador do relatório não
        existir.

        Não é para ficar em produção — é só para o popup poder abrir
        durante a construção por blocos, sem rebentar. Desaparece
        automaticamente assim que a função `_desenhar_<id>` estiver
        definida no bloco correspondente.
        """
        ctk.CTkLabel(
            self._area_conteudo,
            text=(
                f'Relatório "{self.relatorio_atual}" — '
                f"a implementação chega nos blocos 5, 6 ou 7."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
        ).pack(pady=40)

    # -- navegação ----------------------------------------------------

    def _escolher_relatorio(self, relatorio_id):
        """Troca o relatório ativo e redesenha o conteúdo.

        O `filtros_por_relatorio` mantém-se — se o utilizador tiver
        mexido nos filtros de um relatório e voltar, ficam como os
        deixou. Não re-cria a área de conteúdo nem a lista lateral:
        só redesenha o que é preciso.
        """
        self.relatorio_atual = relatorio_id
        self._recarregar_lista_lateral()
        self._recarregar_conteudo()

    def _relatorio_atual_aplica_periodo(self):
        """Diz se o relatório atual usa período (barra visível) ou
        não (barra escondida).

        Lê do mapa `RELATORIOS` — a chave 'periodo' de cada registo.
        Só o "Stock atual" tem 'periodo': False.
        """
        for rel in RELATORIOS[self.area]:
            if rel["id"] == self.relatorio_atual:
                return rel["periodo"]
        return True

    def _fechar(self):
        """Fecha o popup e volta ao hub.

        O hub já está visível por trás do popup — não é preciso
        fazer nada além de destruir este. A X nativa da janela e o
        botão "Fechar" chamam os dois este método.
        """
        self.destroy()

    # -- barra de período (substitui o método vazio do Bloco 3a) -----

    def _construir_barra_periodo(self):
        """Preenche o `self._frame_periodo` com os chips e o campo
        único de calendário.

        Chamado uma vez no `__init__`, no lugar do
        `_construir_barra_periodo_vazia` do Bloco 3a. Depois disto,
        o estado da barra é gerido por `_destacar_periodo` e
        `_atualizar_campo_periodo` — este método não volta a correr.
        """
        # Cria o frame da barra de período — herdado do
        # `_construir_barra_periodo_vazia` do Bloco 3a, que este
        # método substituiu.
        self._frame_periodo = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_periodo.pack(fill="x", padx=18, pady=(0, 8))

        self._chips = {}

        for chave, rotulo in CHIPS_PERIODO:
            chip = ctk.CTkButton(
                self._frame_periodo,
                text=rotulo,
                width=110,
                height=26,
                corner_radius=tema.RAIO_CAMPO,
                fg_color=tema.ID_CHIP_FUNDO,
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.COR_BORDA,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda c=chave: self._escolher_periodo(c),
            )
            chip.pack(side="left", padx=(0, 6))
            self._chips[chave] = chip

        # Campo único de calendário — alinhado à direita da barra.
        # Mostra o intervalo como o utilizador o lê (as duas pontas
        # inclusivas), não como o motor o recebe.
        self._campo_unico = ctk.CTkButton(
            self._frame_periodo,
            text="",
            height=26,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.COR_FUNDO,
            text_color=tema.COR_TEXTO,
            hover_color=tema.ID_CHIP_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            font=ctk.CTkFont(size=11),
            command=self._abrir_calendario,
        )
        self._campo_unico.pack(side="right")

        # Arranca com o default destacado e o campo preenchido.
        self._destacar_periodo(self.periodo_atual)
        self._atualizar_campo_periodo()

    def _escolher_periodo(self, chave):
        """Chamada ao clicar num chip de atalho.

        Recalcula o intervalo, atualiza o destaque dos chips e o
        texto do campo único, e redesenha o relatório atual com o
        período novo.
        """
        if chave == PERIODO_PERSONALIZADO:
            # O personalizado é só acessível pelo campo único —
            # não há chip para ele. Se chegar aqui, ignoramos.
            return

        self.periodo_atual = chave
        self.data_inicio, self.data_fim = _intervalo_do_atalho(chave)
        self._destacar_periodo(chave)
        self._atualizar_campo_periodo()
        self._recarregar_conteudo()

    def _destacar_periodo(self, chave):
        """Pinta o chip do período ativo a azul cheio; os outros
        ficam claros.

        Com o período personalizado escolhido, NENHUM chip fica
        destacado — o destaque vai para o campo único (que muda de
        borda e fundo). É mais honesto do que fingir que algum dos
        atalhos está ativo quando não está.
        """
        for c, chip in self._chips.items():
            ativo = c == chave and chave != PERIODO_PERSONALIZADO
            if ativo:
                chip.configure(
                    fg_color=tema.AZUL_PRINCIPAL,
                    text_color="#FFFFFF",
                    hover_color=tema.AZUL_CLARO,
                )
            else:
                chip.configure(
                    fg_color=tema.ID_CHIP_FUNDO,
                    text_color=tema.AZUL_PRINCIPAL,
                    hover_color=tema.COR_BORDA,
                )

        if self._campo_unico is not None:
            if chave == PERIODO_PERSONALIZADO:
                self._campo_unico.configure(
                    fg_color=tema.ID_CHIP_FUNDO,
                    border_color=tema.AZUL_PRINCIPAL,
                    text_color=tema.AZUL_PRINCIPAL,
                )
            else:
                self._campo_unico.configure(
                    fg_color=tema.COR_FUNDO,
                    border_color=tema.COR_BORDA,
                    text_color=tema.COR_TEXTO,
                )

    def _atualizar_campo_periodo(self):
        """Atualiza o texto do campo único com o intervalo visível
        (as duas pontas inclusivas).

        O motor recebe o `data_fim` exclusivo (num dia depois), mas
        o utilizador lê o intervalo como o escolheu — o dia final
        incluído.
        """
        if self._campo_unico is None:
            return

        # `_intervalo_visivel` dá-nos as pontas como o utilizador
        # as vê. Se o período atual for personalizado, as datas já
        # estão nas atribuições — usa-as diretamente.
        if self.periodo_atual == PERIODO_PERSONALIZADO:
            inicio = self.data_inicio
            fim = self.data_fim - timedelta(days=1)
        else:
            inicio, fim = _intervalo_visivel(self.periodo_atual)

        texto = (
            f"Período: {inicio.strftime('%d/%m/%Y')} a "
            f"{fim.strftime('%d/%m/%Y')}"
        )
        self._campo_unico.configure(text=texto)

    # -- calendário (tkcalendar) --------------------------------------

    def _abrir_calendario(self):
        """Abre o popup do calendário para escolher o período
        personalizado.

        Cria um `CTkToplevel` novo (a cada chamada) com a moldura
        do projeto, um `tkcalendar.Calendar` embutido, e o rodapé
        de Cancelar/Aplicar.

        ATENÇÃO — `tkcalendar` desta versão só aceita
        `selectmode="day"` (o `"range"` rebenta com
        `ValueError: 'selectmode' option should be 'none' or 'day'`).
        Por isso, o intervalo em dois cliques é gerido por NÓS:
        guardamos cada clique em `self._selecao_personalizada`, e
        usamos esse valor no `_aplicar_calendario`.

        ATENÇÃO — `tkcalendar` só aceita cores em string simples
        ("#FFFFFF"). Os pares `(claro, escuro)` do `tema.py` são
        uma convenção do CustomTkinter e não podem ir para lá. Daí
        o `[0]` em cada par.
        """
        # Reinicia a seleção provisória, para o calendário abrir
        # limpo (ou com o período atual preenchido, se preferires
        # mais à frente).
        self._selecao_personalizada = None

        janela = ctk.CTkToplevel(self)
        janela.title("Período personalizado")
        janela.geometry("420x460")
        janela.resizable(False, False)
        janela.configure(fg_color=tema.COR_FUNDO)
        janela.transient(self)
        componentes.colocar_no_topo(janela)

        # Cabeçalho — moldura do projeto.
        ctk.CTkLabel(
            janela,
            text="Período personalizado",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            janela,
            text=(
                "Clica no dia de início e no dia de fim. "
                "O intervalo aparece em baixo."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # O `tkcalendar.Calendar` embutido. `selectmode="day"` é o
        # único valor aceite nesta versão.
        calendario = Calendar(
            janela,
            selectmode="day",
            locale="pt_PT",
            date_pattern="yyyy-mm-dd",
            background=tema.COR_FUNDO[0],
            foreground=tema.COR_TEXTO[0],
            selectbackground="#2E8B57",
            selectforeground="#FFFFFF",
            normalbackground=tema.COR_FUNDO[0],
            normalforeground=tema.COR_TEXTO[0],
            weekendbackground=tema.COR_FUNDO[0],
            weekendforeground=tema.COR_TEXTO[0],
            othermonthbackground=tema.LINHA_ALTERNADA[0],
            othermonthforeground=tema.COR_TEXTO_SECUNDARIO[0],
            headersbackground=tema.CABECALHO_TABELA_FUNDO[0],
            headersforeground=tema.COR_TEXTO_SECUNDARIO[0],
            bordercolor=tema.COR_BORDA[0],
            font=("Segoe UI", 10),
            headersfont=("Segoe UI", 9, "bold"),
        )
        calendario.pack(padx=16, pady=(0, 10), fill="both", expand=True)

        # Rótulo que mostra a seleção provisória, em baixo do
        # calendário. Atualizado a cada clique.
        self._rotulo_selecao = ctk.CTkLabel(
            janela,
            text="Sem seleção — clica no primeiro dia.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        )
        self._rotulo_selecao.pack(anchor="w", padx=16, pady=(0, 6))

        # O clique num dia passa a chamar `_clicar_dia`, que
        # implementa o intervalo em dois cliques.
        calendario.bind(
            "<<CalendarSelected>>",
            lambda _e: self._clicar_dia(calendario),
        )

        # Rodapé — Cancelar / Aplicar.
        rodape = ctk.CTkFrame(janela, fg_color="transparent")
        rodape.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=110,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            font=ctk.CTkFont(size=11),
            command=janela.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Aplicar",
            width=110,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._aplicar_calendario(janela, calendario),
        ).pack(side="right")

    def _clicar_dia(self, calendario):
        """Regista um clique num dia do calendário, gerindo o
        intervalo em dois cliques (início, depois fim).

        O primeiro clique grava a data como início; o segundo
        grava-a como fim (e, se for anterior ao início, troca as
        duas — o utilizador não devia ser obrigado a clicar da
        esquerda para a direita). Um terceiro clique reinicia:
        passa a ser o novo início.

        Atualiza o rótulo `self._rotulo_selecao` para o utilizador
        ver o que está escolhido.
        """
        try:
            escolhida = calendario.selection_get()
        except Exception:
            return

        if hasattr(escolhida, "date"):
            escolhida = escolhida.date()

        atual = self._selecao_personalizada

        if atual is None:
            # Primeiro clique: início.
            self._selecao_personalizada = (escolhida, None)
            texto = (
                f"Início: {escolhida.strftime('%d/%m/%Y')} "
                f"— clica no dia de fim."
            )
        elif atual[1] is None:
            # Segundo clique: fim.
            inicio, _ = atual
            if escolhida < inicio:
                # Troca — o utilizador clicou o fim antes do início.
                inicio, escolhida = escolhida, inicio
            self._selecao_personalizada = (inicio, escolhida)
            texto = (
                f"Período: {inicio.strftime('%d/%m/%Y')} a "
                f"{escolhida.strftime('%d/%m/%Y')}"
            )
        else:
            # Terceiro clique: reinicia com o novo início.
            self._selecao_personalizada = (escolhida, None)
            texto = (
                f"Início: {escolhida.strftime('%d/%m/%Y')} "
                f"— clica no dia de fim."
            )

        self._rotulo_selecao.configure(text=texto)

    def _aplicar_calendario(self, janela, calendario):
        """Lê o intervalo escolhido, converte-o, e redesenha o
        relatório com o período novo.

        A seleção vem de `self._selecao_personalizada` (o
        intervalo em dois cliques que o `_clicar_dia` construiu) —
        NÃO de `calendario.selection_get()`, que nesta versão do
        `tkcalendar` devolve só o último dia clicado. É `None`
        enquanto o utilizador não clicou em dois dias.
        """
        if (
            self._selecao_personalizada is None
            or self._selecao_personalizada[1] is None
        ):
            componentes.mostrar_erro(
                "Escolhe o dia de início e o dia de fim, com dois " "cliques."
            )
            return

        inicio, fim = self._selecao_personalizada

        try:
            self.data_inicio, self.data_fim = _intervalo_personalizado(
                inicio, fim
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.periodo_atual = PERIODO_PERSONALIZADO
        self._destacar_periodo(PERIODO_PERSONALIZADO)
        self._atualizar_campo_periodo()

        janela.destroy()
        self._recarregar_conteudo()

    # =================================================================
    # RELATÓRIOS — ÁREA FINANCEIRO
    # =================================================================

    # -- helpers partilhados pelos desenhadores ----------------------

    def _titulo_relatorio(self, master, titulo):
        """Escreve a linha de título acima da tabela.

        Ex.: `RESULTADO · 01/09/2026 → 19/09/2026`. Se o relatório
        não aplica período (só o "Stock atual"), mostra só o título,
        sem a parte do período.
        """
        if self._relatorio_atual_aplica_periodo():
            inicio, fim = self._intervalo_visivel_atual()
            texto = (
                f"{titulo.upper()} · {inicio.strftime('%d/%m/%Y')} → "
                f"{fim.strftime('%d/%m/%Y')}"
            )
        else:
            texto = titulo.upper()

        ctk.CTkLabel(
            master,
            text=texto,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

    def _intervalo_visivel_atual(self):
        """Devolve as duas pontas inclusivas do período atual — para
        mostrar no título do relatório.

        Se o período for personalizado, tem de inverter o +1 dia
        que está em `self.data_fim`.
        """
        if self.periodo_atual == PERIODO_PERSONALIZADO:
            return self.data_inicio, self.data_fim - timedelta(days=1)
        return _intervalo_visivel(self.periodo_atual)

    def _rodape_export(self, master, relatorio_id, colunas, linhas):
        """Botões de exportação no fim do relatório.

        Três botões, alinhados à direita, pela ordem visual
        (esquerda → direita): PDF · CSV · Excel.

        Como `pack(side="right")` empilha da direita para a esquerda
        (o primeiro empacotado fica mais à direita), a ordem das
        chamadas é a inversa da ordem visual: Excel primeiro, CSV a
        seguir, PDF por último.

        Cores (handoff 3.4):
        - PDF   → AZUL_PRINCIPAL (fundo azul, texto branco)
        - CSV   → transparente com borda
        - Excel → VERDE
        """
        rodape = ctk.CTkFrame(master, fg_color="transparent")
        rodape.pack(fill="x", pady=(14, 0))

        # Excel — o primeiro empacotado, fica mais à direita.
        ctk.CTkButton(
            rodape,
            text="Exportar Excel",
            width=120,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._exportar(
                relatorio_id, colunas, linhas, formato="excel"
            ),
        ).pack(side="right", padx=(12, 0))

        # CSV — o do meio.
        ctk.CTkButton(
            rodape,
            text="Exportar CSV",
            width=120,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._exportar(
                relatorio_id, colunas, linhas, formato="csv"
            ),
        ).pack(side="right", padx=(12, 0))

        # PDF — o último empacotado, fica mais à esquerda.
        ctk.CTkButton(
            rodape,
            text="Exportar PDF",
            width=120,
            height=30,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._exportar(
                relatorio_id, colunas, linhas, formato="pdf"
            ),
        ).pack(side="right", padx=(12, 0))

    def _exportar(self, relatorio_id, colunas, linhas, formato):
        """Gera o ficheiro de exportação e abre-o no sistema.

        `formato` é "pdf", "csv" ou "excel". Os três usam os mesmos
        dados (`colunas` e `linhas`), já formatados pelo desenhador
        do relatório.
        """

        # Título do relatório — para o cabeçalho do ficheiro.
        titulo = ""
        for rel in RELATORIOS[self.area]:
            if rel["id"] == relatorio_id:
                titulo = rel["titulo"]
                break

        # Datas do intervalo — as pontas inclusivas, como o
        # utilizador as vê. O ficheiro exportado reflete o que está
        # no ecrã, não o intervalo interno do motor.
        inicio, fim = self._intervalo_visivel_atual()

        try:
            if formato == "csv":
                # Sem perguntar (v1.11.1): o separador é o de listas
                # do Windows, o mesmo que o Excel usa ao abrir o CSV.
                caminho = impressao.gerar_relatorio_csv(
                    titulo=titulo,
                    colunas=colunas,
                    linhas=linhas,
                    area=self.area,
                    relatorio_id=relatorio_id,
                    data_inicio=inicio,
                    data_fim=fim,
                )
            elif formato == "pdf":
                caminho = impressao.gerar_relatorio_pdf(
                    titulo=titulo,
                    colunas=colunas,
                    linhas=linhas,
                    area=self.area,
                    relatorio_id=relatorio_id,
                    data_inicio=inicio,
                    data_fim=fim,
                )
            elif formato == "excel":
                caminho = impressao.gerar_relatorio_excel(
                    titulo=titulo,
                    colunas=colunas,
                    linhas=linhas,
                    area=self.area,
                    relatorio_id=relatorio_id,
                    data_inicio=inicio,
                    data_fim=fim,
                )
            else:
                componentes.mostrar_erro(
                    f"Formato de exportação desconhecido: {formato}"
                )
                return
        except Exception as erro:
            componentes.mostrar_erro(
                f"Erro ao gerar o ficheiro {formato.upper()}: {erro}"
            )
            return

        # Abre o ficheiro no sistema — mesma função que o
        # `_ImprimirContratoModal` usa para abrir o PDF do contrato.
        self._abrir_no_sistema(caminho)

        componentes.mostrar_sucesso(
            f"Ficheiro {formato.upper()} gerado e aberto:\n{caminho}"
        )

    @staticmethod
    def _abrir_no_sistema(caminho):
        """Abre um ficheiro no programa por omissão do sistema.

        Mesma função do `_ImprimirContratoModal` (gui_contratos.py):
        `os.startfile` no Windows, `open` no macOS, `xdg-open` no
        Linux. Erros de abertura são silenciosos — o ficheiro já
        está no disco, o utilizador pode abri-lo à mão.
        """
        import os
        import subprocess
        import sys

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(caminho))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(caminho)])
            else:
                subprocess.Popen(["xdg-open", str(caminho)])
        except (FileNotFoundError, OSError):
            pass
