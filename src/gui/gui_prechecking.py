"""Pré check-in no desktop (F5 — mockup aprovado pelo aluno a
05/10/2026).

- `GerarLinkModal`: aberto no "Gerir" de uma reserva Airbnb. Mostra o
  que o hóspede vai ver, deixa acertar horários, regras e validade, e
  gera o link (só mostrado uma vez — a base guarda o hash).
- `ListaPreCheckins`: ecrã "Pré check-ins" (OPERAÇÃO) com os
  pendentes enviados pelos hóspedes.
- `ValidarPreCheckinModal`: a ficha atual ao lado do que o hóspede
  enviou (diferenças a amarelo), com Importar ou Rejeitar.

Só Master e Admin veem isto (menu `_GESTAO`); o `prechecking.py`
volta a validar o perfil em cada operação.
"""

import customtkinter as ctk

import prechecking
from . import componentes
from . import sessao
from . import tema

_COLUNAS = (
    componentes.Coluna("ID", minimo=40, espaco=8),
    componentes.Coluna("RECEBIDO EM", minimo=110),
    componentes.Coluna("HÓSPEDE (ENVIADO)", peso=2, minimo=170),
    componentes.Coluna("RESERVA", minimo=104, alinhamento="centro"),
    componentes.Coluna("UNIDADE", peso=2, minimo=160),
    componentes.Coluna("ENTRADA", minimo=84, alinhamento="centro"),
    componentes.Coluna("DIFERENÇAS", minimo=100, alinhamento="centro"),
    componentes.Coluna("AÇÕES", minimo=90, alinhamento="centro"),
)
_ALTURA_LINHA = 46


def _autor_id():
    ativo = sessao.obter_responsavel_ativo()
    return ativo["id"] if ativo else None


def _data_hora(valor):
    return valor.strftime("%d/%m/%Y %H:%M") if valor else "—"


def _ligar_duplo_clique(widget, acao):
    """Duplo clique numa célula (e nos filhos) abre o Validar — regra
    do ficheiro 11: nunca na célula de ações nem no ChipId."""
    widget.bind("<Double-1>", lambda _evento: acao(), add="+")
    for filho in widget.winfo_children():
        _ligar_duplo_clique(filho, acao)


def abrir(classe, *argumentos):
    """Abre um dos modais deste ecrã; um ValueError do negócio (reserva
    terminada, pendente já tratado...) vira mensagem em vez de erro."""
    try:
        return classe(*argumentos)
    except ValueError as erro:
        componentes.mostrar_erro(str(erro))
        return None


def _texto_valor(valor):
    if valor is None or valor == "":
        return "—"
    if hasattr(valor, "strftime"):
        return componentes.formatar_data(valor)
    return str(valor)


# =====================================================================
# Gerar link (a partir de uma reserva Airbnb)
# =====================================================================


class GerarLinkModal(ctk.CTkToplevel):
    """Popup "Gerar link de pré check-in" de uma reserva."""

    _LARGURA = 580

    def __init__(self, tela, reserva, nome_cliente=""):
        dados = prechecking.dados_link(reserva["id"])   # pode recusar
        super().__init__(tela)
        self.tela = tela
        self.reserva = reserva
        self.dados = dados

        self.title(f"Pré check-in — {reserva['id']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela.winfo_toplevel())

        corpo = componentes.Contentor(self)
        corpo.pack(fill="both", expand=True, padx=22, pady=18)
        self.corpo = corpo

        componentes.Rotulo(
            corpo, "Gerar link de pré check-in", "titulo"
        ).pack(anchor="w")
        subtitulo = f"{reserva['id']}"
        if nome_cliente:
            subtitulo += f" · {nome_cliente}"
        componentes.Rotulo(
            corpo,
            f"{subtitulo} — o que o hóspede vai ver no site "
            "(sem código da lockbox)",
            "secundario",
        ).pack(anchor="w", pady=(0, 12))

        grelha = componentes.Contentor(corpo)
        grelha.pack(fill="x")
        grelha.grid_columnconfigure(0, weight=1, uniform="campos")
        grelha.grid_columnconfigure(1, weight=1, uniform="campos")

        self._leitura(grelha, 0, 0, "Alojamento", self.dados["unidade"])
        self._leitura(
            grelha, 0, 1, "Morada (da propriedade)",
            self.dados["morada"] or "(sem morada)",
        )
        self._leitura(
            grelha, 1, 0, "Entrada",
            componentes.formatar_data(self.dados["data_entrada"]),
        )
        self._leitura(
            grelha, 1, 1, "Saída",
            componentes.formatar_data(self.dados["data_saida"]),
        )
        self.campo_checkin = self._campo(
            grelha, 2, 0, "Check-in a partir das *",
            self.dados["hora_checkin"],
        )
        self.campo_checkout = self._campo(
            grelha, 2, 1, "Check-out até às *",
            self.dados["hora_checkout"],
        )

        componentes.Rotulo(
            corpo, "Regras da casa (opcional)", "secundario"
        ).pack(anchor="w", pady=(10, 2))
        self.area_regras = componentes.AreaTexto(corpo, altura=64)
        self.area_regras.pack(fill="x")

        grelha2 = componentes.Contentor(corpo)
        grelha2.pack(fill="x", pady=(10, 0))
        grelha2.grid_columnconfigure(0, weight=1, uniform="campos")
        grelha2.grid_columnconfigure(1, weight=1, uniform="campos")
        self.campo_validade = self._campo(
            grelha2, 0, 0, "Link válido até (dd/mm/aaaa hh:mm) *",
            self.dados["valido_ate"].strftime("%d/%m/%Y %H:%M"),
        )
        self._leitura(
            grelha2, 0, 1, "Versão do aviso de privacidade",
            f"{self.dados['versao_aviso']} (em vigor)",
        )

        # Caixa do link: só aparece depois de gerado (um Contentor
        # vazio ocupa espaço — lição 21 do ficheiro 11).
        self.caixa_link = ctk.CTkFrame(
            corpo,
            fg_color=tema.VERDE_LIVRE,
            corner_radius=tema.RAIO_CAMPO,
        )

        rodape = componentes.Contentor(corpo)
        rodape.pack(fill="x", side="bottom", pady=(16, 0))
        componentes.Botao(rodape, "Fechar", self.destroy).pack(side="left")
        self.botao_gerar = componentes.Botao(
            rodape, "Gerar link", self._gerar, estilo="primario"
        )
        self.botao_gerar.pack(side="right")

        self._ajustar_tamanho()
        componentes.colocar_no_topo(self)

    # -- construção ------------------------------------------------------

    def _leitura(self, grelha, linha, coluna, rotulo, valor):
        celula = componentes.Contentor(grelha)
        celula.grid(row=linha, column=coluna, sticky="ew",
                    padx=(0, 8) if coluna == 0 else (8, 0), pady=4)
        componentes.Rotulo(celula, rotulo, "secundario").pack(anchor="w")
        componentes.Rotulo(
            celula, valor, "forte", wraplength=250, justify="left",
            height=0,
        ).pack(anchor="w")

    def _campo(self, grelha, linha, coluna, rotulo, valor):
        celula = componentes.Contentor(grelha)
        celula.grid(row=linha, column=coluna, sticky="ew",
                    padx=(0, 8) if coluna == 0 else (8, 0), pady=4)
        componentes.Rotulo(celula, rotulo, "secundario").pack(anchor="w")
        campo = componentes.CampoTexto(celula)
        campo.insert(0, valor)
        campo.pack(fill="x")
        return campo

    def _ajustar_tamanho(self):
        """Mede o conteúdo e centra sobre a janela principal (regra da
        geometria dos modais: medir e converter para lógico)."""
        self.update_idletasks()
        fator = componentes.escala(self)
        altura = int(self.corpo.winfo_reqheight() / fator) + 40
        componentes.centrar_sobre(
            self, self.tela.winfo_toplevel(), self._LARGURA, altura
        )

    # -- ação ------------------------------------------------------------

    def _ler_validade(self):
        import datetime

        texto = self.campo_validade.get().strip()
        try:
            return datetime.datetime.strptime(texto, "%d/%m/%Y %H:%M")
        except ValueError:
            raise ValueError(
                "Validade: escreva a data como dd/mm/aaaa hh:mm."
            ) from None

    def _gerar(self):
        try:
            link = prechecking.gerar_link(
                self.reserva["id"],
                _autor_id(),
                self.campo_checkin.get(),
                self.campo_checkout.get(),
                regras=self.area_regras.texto(),
                valido_ate=self._ler_validade(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self._mostrar_link(link)
        self.botao_gerar.configure(text="Gerar outro link")
        if hasattr(self.tela, "_recarregar"):
            self.tela._recarregar()

    def _mostrar_link(self, link):
        for filho in self.caixa_link.winfo_children():
            filho.destroy()

        componentes.Rotulo(
            self.caixa_link, "✓ Link gerado", "forte",
            cor=tema.TEXTO_LIVRE,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        fila = componentes.Contentor(self.caixa_link)
        fila.pack(fill="x", padx=12)
        campo = componentes.CampoTexto(fila)
        campo.insert(0, link)
        campo.configure(state="readonly")
        campo.pack(side="left", fill="x", expand=True, padx=(0, 8))
        componentes.Botao(
            fila, "Copiar link", lambda: self._copiar(link),
            estilo="primario",
        ).pack(side="right")

        componentes.Rotulo(
            self.caixa_link,
            "Este link só é mostrado agora — a base guarda apenas o "
            "hash. Se o perder, gere outro: o anterior deixa de "
            "funcionar.",
            "secundario",
            cor=tema.TEXTO_AVISO,
            wraplength=self._LARGURA - 80,
            justify="left",
            height=0,
        ).pack(anchor="w", padx=12, pady=(6, 10))

        if not self.caixa_link.winfo_ismapped():
            self.caixa_link.pack(fill="x", pady=(14, 0))
        self._ajustar_tamanho()

    def _copiar(self, link):
        self.clipboard_clear()
        self.clipboard_append(link)
        componentes.mostrar_sucesso(
            "Link copiado. Cole-o na mensagem do Airbnb.",
            titulo="Pré check-in",
        )


# =====================================================================
# Ecrã "Pré check-ins"
# =====================================================================


class ListaPreCheckins(ctk.CTkFrame):
    """Pendentes enviados pelos hóspedes, à espera de validação."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Pré check-ins").pack(fill="x")

        barra = componentes.Contentor(self)
        barra.pack(fill="x", padx=20, pady=(0, 8))
        componentes.Rotulo(
            barra,
            "Dados enviados pelos hóspedes no site, à espera de "
            "validação. Duplo clique numa linha = Validar.",
            "secundario",
        ).pack(side="left")
        componentes.Botao(
            barra, "↻ Atualizar", self._recarregar
        ).pack(side="right")

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia="Não há pré check-ins por validar.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        self._a_carregar = False
        self._recarregar()

    def _recarregar(self):
        if self._a_carregar:
            return
        self._a_carregar = True
        autor = _autor_id()

        def trabalho():
            return prechecking.listar_pendentes(autor)

        def terminar(lista):
            self._a_carregar = False
            self._desenhar(lista)

        def falhar():
            self._a_carregar = False

        componentes.carregar_em_segundo_plano(
            self, trabalho, terminar, ao_falhar=falhar
        )

    def _desenhar(self, lista):
        self.tabela.limpar()
        if not lista:
            self.tabela.mostrar_vazio()
            return
        for pendente in lista:
            self._linha(pendente)
        # O contador do menu acompanha a lista.
        barra = getattr(self.controlador, "barra_lateral", None)
        if barra is not None:
            barra.atualizar_contadores()

    def _linha(self, pendente):
        def validar(p=pendente):
            if abrir(ValidarPreCheckinModal, self, p["id"]) is None:
                self._recarregar()

        linha = self.tabela.nova_linha()

        celulas: list = [
            self.tabela.colocar(linha, 0, componentes.Rotulo(
                linha, str(pendente["id"]), "texto")),
            self.tabela.colocar(linha, 1, componentes.Rotulo(
                linha, _data_hora(pendente["recebido_em"]), "texto")),
            self.tabela.colocar(linha, 2, componentes.Rotulo(
                linha, pendente["nome"], "forte")),
        ]
        self.tabela.colocar(
            linha, 3,
            componentes.ChipId(linha, pendente["referencia"], largura=96),
        )
        celulas += [
            self.tabela.colocar(linha, 4, componentes.Rotulo(
                linha, pendente["unidade"], "texto")),
            self.tabela.colocar(linha, 5, componentes.Rotulo(
                linha, componentes.formatar_data(pendente["data_entrada"]),
                "texto")),
        ]

        n = pendente["diferencas"]
        if not pendente["reserva_existe"]:
            etiqueta = componentes.Etiqueta(linha, "sem reserva", "erro")
        elif n:
            etiqueta = componentes.Etiqueta(
                linha, f"{n} {'campo' if n == 1 else 'campos'}", "aviso")
        else:
            etiqueta = componentes.Etiqueta(linha, "Iguais", "livre")
        celulas.append(self.tabela.colocar(linha, 6, etiqueta))

        acoes = self.tabela.celula_acoes(linha, 7)
        acoes.adicionar(
            componentes.Botao(acoes, "Validar", validar, width=72, height=26)
        )

        for celula in celulas:
            _ligar_duplo_clique(celula, validar)


# =====================================================================
# Validar (Importar / Rejeitar)
# =====================================================================


class ValidarPreCheckinModal(ctk.CTkToplevel):
    """Ficha atual × enviado pelo hóspede, com Importar ou Rejeitar."""

    _LARGURA = 760

    def __init__(self, tela, pendente_id):
        # Lê ANTES de criar a janela: se o pendente já não existir,
        # o ValueError sobe sem deixar uma janela vazia aberta.
        pendente, cliente, linhas = prechecking.detalhe(
            pendente_id, _autor_id()
        )
        super().__init__(tela)
        self.tela = tela
        self.pendente_id = pendente_id
        self._a_gravar = False
        self.pendente, self.cliente = pendente, cliente
        p = self.pendente

        self.title(f"Validar pré check-in #{pendente_id}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela.winfo_toplevel())

        corpo = componentes.Contentor(self)
        corpo.pack(fill="both", expand=True, padx=22, pady=18)
        self.corpo = corpo

        componentes.Rotulo(
            corpo, f"Validar pré check-in #{pendente_id}", "titulo"
        ).pack(anchor="w")
        componentes.Rotulo(
            corpo,
            f"Reserva {p['referencia']} · {p['unidade']} · "
            f"{componentes.formatar_data(p['data_entrada'])} → "
            f"{componentes.formatar_data(p['data_saida'])} · recebido a "
            f"{_data_hora(p['recebido_em'])}",
            "secundario",
        ).pack(anchor="w", pady=(0, 12))

        self._quadro(corpo, linhas)
        self._confirmacoes(corpo)

        if self.cliente is None:
            texto = (
                "A reserva deste pré check-in já não existe. Não há ficha "
                "para atualizar — rejeite-o."
            )
        else:
            texto = (
                f"Ao importar: a ficha {self.cliente['id']} fica com os "
                "dados da coluna da direita, o aviso de privacidade do "
                f"hóspede fica registado (suporte: web, versão "
                f"{p['versao_aviso']}, registado por quem importa) e o "
                "pré check-in é apagado da caixa de entrada."
            )
        aviso = ctk.CTkFrame(
            corpo, fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
        )
        aviso.pack(fill="x", pady=(12, 0))
        componentes.Rotulo(
            aviso, texto, "texto", cor=tema.TEXTO_AVISO,
            wraplength=self._LARGURA - 80, justify="left", height=0,
        ).pack(anchor="w", padx=12, pady=8)

        rodape = componentes.Contentor(corpo)
        rodape.pack(fill="x", pady=(16, 0))
        componentes.Botao(rodape, "Fechar", self.destroy).pack(side="left")
        self.botao_importar = componentes.Botao(
            rodape, "Importar para a ficha", self._importar,
            estilo="sucesso",
        )
        self.botao_importar.pack(side="right")
        if self.cliente is None:
            self.botao_importar.configure(state="disabled")
        botao_rejeitar = componentes.Botao(
            rodape, "Rejeitar…", self._rejeitar
        )
        # O estilo "contorno" fixa a cor do texto; o vermelho vem
        # depois.
        botao_rejeitar.configure(text_color=tema.TEXTO_ERRO)
        botao_rejeitar.pack(side="right", padx=(0, 8))

        self.update_idletasks()
        fator = componentes.escala(self)
        altura = int(corpo.winfo_reqheight() / fator) + 40
        componentes.centrar_sobre(
            self, tela.winfo_toplevel(), self._LARGURA, altura
        )
        componentes.colocar_no_topo(self)

    def _quadro(self, master, linhas):
        quadro = componentes.Contentor(master)
        quadro.pack(fill="x")
        for coluna, peso in enumerate((1, 2, 2)):
            quadro.grid_columnconfigure(coluna, weight=peso, uniform="q")

        id_ficha = self.cliente["id"] if self.cliente else "—"
        for coluna, titulo in enumerate(
            ("CAMPO", f"FICHA ATUAL — {id_ficha}", "ENVIADO PELO HÓSPEDE")
        ):
            componentes.Rotulo(quadro, titulo, "secao").grid(
                row=0, column=coluna, sticky="w", padx=8, pady=(0, 4)
            )

        email = self.pendente.get("email")
        extra = [("email", "Email",
                  (self.cliente or {}).get("email"), email,
                  bool(email))]

        for numero, (_chave, rotulo, atual, enviado, diferente) in enumerate(
            list(linhas) + extra, start=1
        ):
            fundo = tema.AMARELO_AVISO if diferente else tema.COR_FUNDO
            for coluna, texto in enumerate(
                (rotulo, _texto_valor(atual), _texto_valor(enviado))
            ):
                celula = ctk.CTkFrame(quadro, fg_color=fundo,
                                      corner_radius=0)
                celula.grid(row=numero, column=coluna, sticky="nsew")
                componentes.Rotulo(
                    celula, texto,
                    "forte" if (diferente and coluna == 2) else (
                        "secundario" if coluna == 0 else "texto"),
                    wraplength=280, justify="left", height=0,
                ).pack(anchor="w", padx=8, pady=5)

    def _confirmacoes(self, master):
        p = self.pendente
        cartao = componentes.Cartao(
            master,
            titulo="Confirmações do hóspede",
            subtitulo=f"aviso de privacidade v{p['versao_aviso']}",
        )
        cartao.pack(fill="x", pady=(12, 0))
        fila = componentes.Contentor(cartao.corpo)
        fila.pack(fill="x")

        itens = [
            (p["informado_privacidade"], "Informado sobre o tratamento"),
            (p["aceitou_regulamento"], "Aceitou o regulamento"),
            (p["consente_comunicacoes"], "Aceita comunicações (com email)"
             if p["consente_comunicacoes"] else
             "Não aceita comunicações"),
        ]
        for marcado, texto in itens:
            componentes.Rotulo(
                fila, f"{'✓' if marcado else '—'}  {texto}", "texto",
                cor=tema.TEXTO_LIVRE if marcado else None,
            ).pack(side="left", padx=(0, 18))

    # -- ações -----------------------------------------------------------

    def _depois(self, mensagem):
        componentes.mostrar_sucesso(mensagem, titulo="Pré check-in")
        self.destroy()
        if hasattr(self.tela, "_recarregar"):
            self.tela._recarregar()

    def _importar(self):
        if self._a_gravar:
            return
        self._a_gravar = True
        try:
            cliente = prechecking.importar(self.pendente_id, _autor_id())
        except ValueError as erro:
            self._a_gravar = False
            componentes.mostrar_erro(str(erro))
            return
        self._depois(
            f"Dados importados para a ficha {cliente['id']} "
            f"({cliente['nome']})."
        )

    def _rejeitar(self):
        if self._a_gravar:
            return
        if not componentes.confirmar(
            "Rejeitar este pré check-in?\n\nOs dados enviados são "
            "apagados e a ficha do cliente não muda. Depois pode gerar "
            "um link novo na reserva.",
            titulo="Rejeitar pré check-in",
        ):
            return
        self._a_gravar = True
        try:
            prechecking.rejeitar(self.pendente_id, _autor_id())
        except ValueError as erro:
            self._a_gravar = False
            componentes.mostrar_erro(str(erro))
            return
        self._depois("Pré check-in rejeitado e apagado.")
