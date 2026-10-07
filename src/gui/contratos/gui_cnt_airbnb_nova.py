"""Formulário de nova reserva Airbnb (`NovaReservaAirbnb`) e o
popup que o embrulha (`NovaReservaAirbnbModal`)."""

import datetime
from decimal import Decimal, InvalidOperation

import customtkinter as ctk

import clientes
import contratos
import estoque
import responsaveis
import unidades

from gui import componentes, tema
from gui.contratos import gui_cnt_comum
from gui.contratos.gui_cnt_airbnb_confirm import _ConfirmacaoAirbnb

# Aliases locais para helpers que vivem em componentes.py (nomes
# antigos com "_", para o corpo não ter de ser reescrito).
_formatar_valor = componentes.formatar_valor
_colocar_no_topo = componentes.colocar_no_topo

# Helpers partilhados dos contratos (nomes públicos em
# gui_cnt_comum) — alias local, mesmo padrão dos gui_est_*.
_abrir_novo_cliente = gui_cnt_comum.abrir_novo_cliente


# =====================================================================
# NOVA RESERVA AIRBNB — formulário reformulado (13/09/2026)
# =====================================================================


class NovaReservaAirbnb(ctk.CTkFrame):
    """Formulário de registo de uma reserva Airbnb.

    Recebe `popup_pai` — o `NovaReservaAirbnbModal` que o contém.
    Serve para o `_registar`, no fim, pedir ao popup para se fechar,
    em vez de usar `winfo_toplevel()` (que o Pylance não consegue
    tipar).
    """

    def __init__(self, master, controlador, unidade_id=None, popup_pai=None):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador
        self.unidade_selecionada = None
        self.popup_pai = popup_pai
        # v1.9.0: True enquanto uma reserva está a ser gravada — trava
        # um segundo "Registar" (o duplo envio do teste de 05/10/2026).
        self._a_gravar = False

        componentes.Cabecalho(self, "Nova Reserva Airbnb").pack(fill="x")

        # Área de conteúdo rolável — inclui o resumo e o rodapé, tal
        # como o formulário antigo fazia. Antes o resumo e o rodapé
        # ficavam fora do scroll, presos ao fundo da janela; com o
        # formulário mais alto do que o ecrã, acabavam por sair da
        # área visível. Dentro do scroll, tudo rola junto e nunca
        # desaparece (bug apanhado pelo aluno, 13/09/2026).
        self.area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.area.pack(fill="both", expand=True, padx=20, pady=16)

        self._montar_cartao_unidade_cliente()
        self._montar_cartao_estadia()
        self._montar_cartao_checkin_tardio()
        self._montar_resumo()
        self._montar_rodape()

        self._recarregar_unidades(unidade_id)
        self._recarregar_clientes()
        self._recarregar_responsaveis()
        self.after(50, self.area.update_idletasks)

    # -- montagem dos widgets ------------------------------------------

    def _criar_cartao(self, titulo):
        cartao = ctk.CTkFrame(
            self.area,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(14, 6))
        corpo = ctk.CTkFrame(cartao, fg_color="transparent")
        corpo.pack(fill="x", padx=18, pady=(0, 16))
        corpo.grid_columnconfigure(0, weight=0)
        corpo.grid_columnconfigure(1, weight=1)
        return corpo

    def _linha(self, corpo, linha, rotulo):
        ctk.CTkLabel(
            corpo,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=160,
        ).grid(row=linha, column=0, sticky="w", pady=6, padx=(0, 12))

    def _montar_cartao_unidade_cliente(self):
        corpo = self._criar_cartao("Unidade e cliente")

        self._linha(corpo, 0, "Unidade *")
        self.combo_unidade = componentes.Seletor(
            corpo,
            values=[""],
            command=self._ao_escolher_unidade,
        )
        self.combo_unidade.grid(row=0, column=1, sticky="ew", pady=6)

        self._linha(corpo, 1, "Cliente *")

        bloco = ctk.CTkFrame(corpo, fg_color="transparent")
        bloco.grid(row=1, column=1, sticky="ew", pady=6)
        bloco.grid_columnconfigure(0, weight=1)

        self.combo_cliente = componentes.Seletor(bloco, values=[""], width=1)
        self.combo_cliente.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            bloco,
            text="+ Novo cliente",
            width=120,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=lambda: _abrir_novo_cliente(self, "airbnb"),
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))

    def _montar_cartao_estadia(self):
        corpo = self._criar_cartao("Estadia")

        self._linha(corpo, 0, "Data de entrada *")
        self.campo_data_inicio = componentes.CampoData(corpo)
        self.campo_data_inicio.grid(row=0, column=1, sticky="ew", pady=6)
        self.campo_data_inicio.bind(
            "<FocusOut>", lambda _evento: self._atualizar_resumo()
        )
        self.campo_data_inicio.bind(
            "<Return>", lambda _evento: self._atualizar_resumo()
        )

        self._linha(corpo, 1, "Data de saída *")
        self.campo_data_fim = componentes.CampoData(corpo)
        self.campo_data_fim.grid(row=1, column=1, sticky="ew", pady=6)
        self.campo_data_fim.bind(
            "<FocusOut>", lambda _evento: self._atualizar_resumo()
        )
        self.campo_data_fim.bind(
            "<Return>", lambda _evento: self._atualizar_resumo()
        )

        self._linha(corpo, 2, "Preço calculado")
        self.rotulo_preco_calculado = ctk.CTkLabel(
            corpo,
            text="(escolhe as datas)",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.rotulo_preco_calculado.grid(row=2, column=1, sticky="ew", pady=6)

        self._linha(corpo, 3, "Preço praticado *")
        self.campo_preco_praticado = ctk.CTkEntry(
            corpo, placeholder_text="0,00"
        )
        self.campo_preco_praticado.grid(row=3, column=1, sticky="ew", pady=6)

    def _montar_cartao_checkin_tardio(self):
        corpo = self._criar_cartao("Check-in tardio")

        self.checkin_tardio = ctk.CTkCheckBox(corpo, text="Check-in tardio")
        self.checkin_tardio.grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )

        # Caixa com dois campos lado a lado: hora de chegada e multa.
        caixa = ctk.CTkFrame(corpo, fg_color="transparent")
        caixa.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        caixa.grid_columnconfigure(0, weight=1)
        caixa.grid_columnconfigure(1, weight=1)

        bloco_hora = ctk.CTkFrame(caixa, fg_color="transparent")
        bloco_hora.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.campo_hora_chegada = ctk.CTkEntry(
            bloco_hora, placeholder_text="hh:mm"
        )
        self.campo_hora_chegada.pack(fill="x")

        ctk.CTkLabel(
            bloco_hora,
            text="hora de chegada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        bloco_multa = ctk.CTkFrame(caixa, fg_color="transparent")
        bloco_multa.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.campo_multa_praticada = ctk.CTkEntry(
            bloco_multa, placeholder_text="Enter para a multa calculada"
        )
        self.campo_multa_praticada.pack(fill="x")

        ctk.CTkLabel(
            bloco_multa,
            text="valor automático · editável",
            text_color=tema.TEXTO_LIVRE,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(
            corpo,
            text="Multa calculada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=160,
        ).grid(row=2, column=0, sticky="w", pady=(10, 6), padx=(0, 12))

        self.rotulo_multa_calculada = ctk.CTkLabel(
            corpo,
            text="(escolhe a unidade)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.rotulo_multa_calculada.grid(
            row=2, column=1, sticky="ew", pady=(10, 6)
        )

        ctk.CTkLabel(
            corpo,
            text="Responsável do desconto",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=160,
        ).grid(row=3, column=0, sticky="w", pady=6, padx=(0, 12))

        self.combo_responsavel_multa = componentes.Seletor(
            corpo, values=["Nenhum"]
        )
        self.combo_responsavel_multa.grid(row=3, column=1, sticky="ew", pady=6)

        ctk.CTkLabel(
            corpo,
            text="obrigatório quando a multa praticada é inferior à "
            "calculada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=4, column=1, sticky="w")

    def _montar_resumo(self):
        """Resumo final: N noites × preço / Multa / Total.

        Passa a viver DENTRO da área de scroll (self.area), não em
        `self`. Sem isto, o resumo ficava fixo no fundo da janela e
        saía da vista quando o conteúdo interior era maior do que o
        espaço disponível — bug apanhado pelo aluno, 13/09/2026.
        """
        resumo = ctk.CTkFrame(self.area, fg_color="transparent")
        resumo.pack(fill="x", pady=(4, 4))

        self.linha_noites = self._linha_resumo(resumo, "0 noites × —")
        self.linha_multa = self._linha_resumo(
            resumo, "Multa de check-in tardio"
        )
        self.linha_total = self._linha_resumo(resumo, "Total", total=True)

    def _linha_resumo(self, master, rotulo, total=False):
        """Cria uma linha do resumo e devolve um par
        (rótulo_label, valor_label), para o `_atualizar_resumo`
        poder mexer tanto no texto do rótulo como no valor.
        """
        if total:
            ctk.CTkFrame(master, height=1, fg_color=tema.COR_BORDA).pack(
                fill="x", pady=(6, 4)
            )

        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", pady=2)

        cor = tema.COR_TEXTO if total else tema.COR_TEXTO_SECUNDARIO
        fonte = (
            ctk.CTkFont(size=13, weight="bold")
            if total
            else ctk.CTkFont(size=12)
        )

        rotulo_label = ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=cor,
            font=fonte,
            anchor="w",
        )
        rotulo_label.pack(side="left")

        valor_label = ctk.CTkLabel(
            linha,
            text="—",
            text_color=tema.COR_TEXTO,
            font=fonte,
            anchor="e",
        )
        valor_label.pack(side="right")

        return (rotulo_label, valor_label)

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self.area, fg_color="transparent")
        rodape.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self._cancelar,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Registar reserva",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            corner_radius=tema.RAIO_BOTAO,
            command=self._registar,
        ).pack(side="right")

    # -- carregamento de dados -------------------------------------

    def _recarregar_unidades(self, unidade_id_inicial=None):
        # Mesma mudança da versão mensal (ver comentário lá): rótulo
        # passa a incluir a propriedade, via `listar_com_propriedade`.
        self.unidades_airbnb = unidades.listar_com_propriedade(tipo="airbnb")
        nomes = [
            f"{u['id']} · {u['propriedade_nome']} - {u['nome']}"
            for u in self.unidades_airbnb
        ] or ["Sem unidades Airbnb"]
        self.combo_unidade.configure(values=nomes)

        alvo = None
        if unidade_id_inicial:
            alvo = next(
                (
                    u
                    for u in self.unidades_airbnb
                    if u["id"] == unidade_id_inicial
                ),
                None,
            )
        if alvo is None and self.unidades_airbnb:
            alvo = self.unidades_airbnb[0]

        if alvo is not None:
            indice = self.unidades_airbnb.index(alvo)
            self.combo_unidade.set(nomes[indice])
            self._ao_escolher_unidade(nomes[indice])

    def _recarregar_clientes(self):
        self.clientes_disponiveis = clientes.listar()
        nomes = [
            f"{c['id']} · {c['nome']} (NIF {c['nif'] or '—'})"
            for c in self.clientes_disponiveis
        ] or ["Sem clientes"]
        self.combo_cliente.configure(values=nomes)
        if self.clientes_disponiveis:
            self.combo_cliente.set(nomes[0])

    def _selecionar_cliente_por_id(self, cliente_id):
        """Pré-seleciona o cliente novo criado pelo `NovoClienteModal`."""
        for cliente in self.clientes_disponiveis:
            if cliente["id"] == cliente_id:
                rotulo = (
                    f"{cliente['id']} · {cliente['nome']} "
                    f"(NIF {cliente['nif'] or '—'})"
                )
                self.combo_cliente.set(rotulo)
                return

    def _recarregar_responsaveis(self):
        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["Nenhum"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel_multa.configure(values=nomes)
        self.combo_responsavel_multa.set(nomes[0])

    def _ao_escolher_unidade(self, _valor_escolhido):
        indice = self.combo_unidade.cget("values").index(
            self.combo_unidade.get()
        )
        if indice >= len(self.unidades_airbnb):
            self.unidade_selecionada = None
        else:
            self.unidade_selecionada = self.unidades_airbnb[indice]

        self._atualizar_multa_calculada()
        self._atualizar_resumo()

    # -- valores calculados ------------------------------------------

    def _ler_data(self, campo):
        texto = campo.get().strip()
        if not texto:
            return None
        try:
            return datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            return None

    def _preco_calculado(self):
        """Preço calculado da estadia, ou None se ainda não der para
        calcular (falta unidade ou datas, ou datas inválidas).
        """
        if self.unidade_selecionada is None:
            return None

        data_inicio = self._ler_data(self.campo_data_inicio)
        data_fim = self._ler_data(self.campo_data_fim)

        if data_inicio is None or data_fim is None or data_fim <= data_inicio:
            return None

        return contratos.calcular_preco_airbnb(
            self.unidade_selecionada, data_inicio, data_fim
        )

    def _atualizar_multa_calculada(self):
        if self.unidade_selecionada is None:
            self.rotulo_multa_calculada.configure(text="(escolhe a unidade)")
            return

        self.rotulo_multa_calculada.configure(
            text=_formatar_valor(
                self.unidade_selecionada["multa_check_in_tardio"]
            )
        )

    def _atualizar_resumo(self):
        """Recalcula o rótulo do preço calculado E as três linhas do
        resumo final.

        Chamado quando as datas mudam (FocusOut/Enter nos campos) e
        quando a unidade muda. Antes só mexia no resumo — o rótulo
        "Preço calculado" do cartão Estadia ficava sempre a dizer
        "(escolhe as datas)", mesmo com as datas preenchidas (bug
        apanhado pelo aluno, 13/09/2026).
        """
        resumo = self._resumo() or {}
        preco_calculado = resumo.get("preco_calculado")

        # Rótulo do Preço calculado, dentro do cartão Estadia.
        if preco_calculado is None:
            self.rotulo_preco_calculado.configure(text="(escolhe as datas)")
        else:
            self.rotulo_preco_calculado.configure(
                text=_formatar_valor(preco_calculado)
            )

        # Linha 1: N noites × preço.
        rotulo_noites, valor_noites = self.linha_noites

        if preco_calculado is None:
            rotulo_noites.configure(text="0 noites × —")
            valor_noites.configure(text="—")
        else:
            rotulo_noites.configure(
                text=(
                    f"{resumo.get('noites')} noites × "
                    f"{_formatar_valor(resumo.get('preco_noite'))}"
                )
            )
            valor_noites.configure(text=_formatar_valor(preco_calculado))

        # Linha 2: multa de check-in tardio (regra em
        # contratos.resumo_airbnb).
        multa_valor = resumo.get("multa", Decimal("0.00"))
        _, valor_multa = self.linha_multa
        valor_multa.configure(text=_formatar_valor(multa_valor))

        # Linha 3: total.
        _, valor_total = self.linha_total
        if preco_calculado is None:
            valor_total.configure(text="—")
        else:
            valor_total.configure(text=_formatar_valor(resumo.get("total")))

    def _resumo(self):
        """Pede ao `contratos.resumo_airbnb` os valores do resumo
        (noites, preço, multa, total), ou None sem unidade escolhida.

        Aqui só se converte o texto do campo "Multa praticada": vazio
        ou inválido conta como "não escrita" (usa a da unidade).
        """
        if self.unidade_selecionada is None:
            return None

        multa_praticada = None
        texto_multa = self.campo_multa_praticada.get().strip()
        if texto_multa:
            try:
                multa_praticada = Decimal(texto_multa.replace(",", "."))
            except InvalidOperation:
                multa_praticada = None

        return contratos.resumo_airbnb(
            self.unidade_selecionada,
            self._ler_data(self.campo_data_inicio),
            self._ler_data(self.campo_data_fim),
            check_in_tardio=bool(self.checkin_tardio.get()),
            multa_praticada=multa_praticada,
        )

    # -- submissão ----------------------------------------------------

    def _mostrar_erro(self, texto):
        componentes.mostrar_erro(texto)

    def _mostrar_sucesso(self, texto):
        componentes.mostrar_sucesso(texto)

    def _cancelar(self):
        """Botão "Cancelar" — pede ao popup para fechar."""
        if self.popup_pai is not None:
            self.popup_pai._fechar()
        else:
            self.destroy()

    def _cliente_escolhido_id(self):
        indice = self.combo_cliente.cget("values").index(
            self.combo_cliente.get()
        )
        return self.clientes_disponiveis[indice]["id"]

    def _id_responsavel_multa(self):
        indice = self.combo_responsavel_multa.cget("values").index(
            self.combo_responsavel_multa.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _registar(self):
        """Submete o formulário.

        Se o preço praticado é inferior ao calculado: abre o
        `_AlterarValorCalculadoModal` como sub-confirmação. Só se o
        utilizador confirmar é que `contratos.registar_airbnb` é
        chamado (o modal devolve o responsável do desconto).

        Caso contrário: segue direto para
        `contratos.registar_airbnb`.
        """
        if self._a_gravar:
            return

        if self.unidade_selecionada is None:
            self._mostrar_erro("Escolhe uma unidade Airbnb.")
            return

        data_inicio = self._ler_data(self.campo_data_inicio)
        if data_inicio is None:
            self._mostrar_erro("Data de entrada inválida (usa dd/mm/aaaa).")
            return

        data_fim = self._ler_data(self.campo_data_fim)
        if data_fim is None:
            self._mostrar_erro("Data de saída inválida (usa dd/mm/aaaa).")
            return

        try:
            preco_praticado = Decimal(
                self.campo_preco_praticado.get().strip().replace(",", ".")
            )
        except InvalidOperation:
            self._mostrar_erro("Preço praticado com formato inválido.")
            return

        check_in_tardio = bool(self.checkin_tardio.get())
        hora_chegada = self.campo_hora_chegada.get().strip()

        texto_multa = self.campo_multa_praticada.get().strip()
        multa_praticada = None
        if texto_multa:
            try:
                multa_praticada = Decimal(texto_multa.replace(",", "."))
            except InvalidOperation:
                self._mostrar_erro("Multa praticada com formato inválido.")
                return

        preco_calculado = self._preco_calculado()

        # FASE 4 — em vez de gravar (ou de abrir o antigo
        # `_AlterarValorCalculadoModal`), abre sempre o
        # `_ConfirmacaoAirbnb`. Esse modal mostra a Zona 2 (Rol de
        # Lavanderia) e, se houver desconto, também a Zona 1. Só
        # quando o utilizador clicar "Confirmar" é que a reserva é
        # gravada, já com o responsável do desconto (se aplicável).
        _ConfirmacaoAirbnb(
            self,
            unidade=self.unidade_selecionada,
            cliente=self.clientes_disponiveis[
                self.combo_cliente.cget("values").index(
                    self.combo_cliente.get()
                )
            ],
            data_inicio=data_inicio,
            data_fim=data_fim,
            preco_calculado=preco_calculado,
            preco_praticado=preco_praticado,
            check_in_tardio=check_in_tardio,
            hora_chegada=hora_chegada,
            multa_praticada=multa_praticada,
            responsavel_multa_id=self._id_responsavel_multa(),
            ao_confirmar=self._gravar,
        )

    def _gravar(
        self,
        data_inicio,
        data_fim,
        preco_praticado,
        responsavel_desconto_preco_id="",
        check_in_tardio=False,
        hora_chegada="",
        multa_praticada=None,
    ):
        """Chama `contratos.registar_airbnb` e depois gera o Rol de
        Lavanderia automático.

        Chamado pelo `_ConfirmacaoAirbnb` (via `ao_confirmar`) quando
        o utilizador clica "Confirmar". Os parâmetros do desconto
        (`responsavel_desconto_preco_id`) vêm do
        formulário da Zona 1 desse modal; se não houver desconto, o
        modal chama o método com os valores por omissão.

        v1.9.0: protegido contra duplo envio — enquanto grava, e até o
        utilizador fechar o aviso final, um novo "Registar" é ignorado.
        """
        if self._a_gravar:
            return

        self._a_gravar = True
        try:
            self._gravar_reserva(
                data_inicio,
                data_fim,
                preco_praticado,
                responsavel_desconto_preco_id,
                check_in_tardio,
                hora_chegada,
                multa_praticada,
            )
        finally:
            if self.winfo_exists():
                self._a_gravar = False

    def _gravar_reserva(
        self,
        data_inicio,
        data_fim,
        preco_praticado,
        responsavel_desconto_preco_id,
        check_in_tardio,
        hora_chegada,
        multa_praticada,
    ):
        """O trabalho do `_gravar`: regista a reserva, gera o Rol e
        mostra o resultado."""
        unidade = self.unidade_selecionada

        if unidade is None:
            self._mostrar_erro("Escolhe uma unidade Airbnb.")
            return

        try:
            ocupacao, _airbnb = contratos.registar_airbnb(
                unidade["id"],
                self._cliente_escolhido_id(),
                data_inicio,
                data_fim,
                preco_praticado,
                responsavel_desconto_preco_id=responsavel_desconto_preco_id,
                check_in_tardio=check_in_tardio,
                hora_chegada=hora_chegada,
                multa_praticada=multa_praticada,
                responsavel_desconto_multa_id=self._id_responsavel_multa(),
            )
        except ValueError as erro:
            self._mostrar_erro(str(erro))
            return

        # FASE 4 — geração automática do Rol de Lavanderia.
        # Best-effort: a reserva já está gravada; se o Rol falhar,
        # avisamos mas não desfazemos nada.
        try:
            requisicao = estoque.gerar_rol_lavanderia_automatico(
                ocupacao=ocupacao,
                responsavel_id=self._id_responsavel_ativo(),
            )
        except Exception as erro:
            # Erro inesperado — a reserva está gravada; só o Rol
            # falhou. Avisamos e seguimos.
            self._mostrar_erro(
                f"Reserva {ocupacao['id']} gravada, mas o Rol de "
                f"Lavanderia falhou: {erro}.\n\nCorrige a situação "
                f"e cria o Rol manualmente se for preciso."
            )
            if self.popup_pai is not None:
                self.popup_pai._fechar()
            return

        if requisicao is None:
            # Sem produtos a enviar (unidade sem lugares ativos, ou
            # todos os produtos das regras desativados). A reserva
            # grava-se sempre; só não há Rol a criar.
            aviso = ""
            if ocupacao["aviso_documento"]:
                aviso = " (aviso: documento expira durante a estadia)"

            self._mostrar_sucesso(
                f"Reserva registada com sucesso: {ocupacao['id']}"
                f"{aviso}\n\nSem Rol de Lavanderia — a unidade não "
                f"tem lugares ativos que o justifiquem."
            )
        else:
            aviso = ""
            if ocupacao["aviso_documento"]:
                aviso = " (aviso: documento expira durante a estadia)"

            self._mostrar_sucesso(
                f"Reserva registada com sucesso: {ocupacao['id']}"
                f"{aviso}\n\nRol de Lavanderia criado: "
                f"{requisicao['id']} ({requisicao['estado']})."
            )

        if self.popup_pai is not None:
            self.popup_pai._fechar()

    def _id_responsavel_ativo(self):
        """ID do responsável ativo da sessão — usado como autor do
        Rol de Lavanderia automático (Fase 4)."""
        from gui import sessao

        ativo = sessao.obter_responsavel_ativo()

        if ativo is None:
            return ""

        return ativo["id"]


class NovaReservaAirbnbModal(ctk.CTkToplevel):
    """Popup com o formulário de Nova Reserva Airbnb."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title("Nova Reserva Airbnb")
        self.geometry("640x760")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        NovaReservaAirbnb(
            self,
            controlador=tela_lista.controlador,
            popup_pai=self,
        ).pack(fill="both", expand=True)

    def _fechar(self):
        self.tela_lista._recarregar()
        self.destroy()
