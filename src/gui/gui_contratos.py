"""Ecrãs de Contratos e Reservas: criação de um contrato de
arrendamento mensal (NovoContratoMensal), registo de uma reserva
Airbnb (NovaReservaAirbnb) e listagem das ocupações já existentes,
mensais e Airbnb.

REESTRUTURAÇÃO 13/09/2026 (ronda 2) — a lista de Reservas Airbnb
deixa de desenhar cartões empilhados e passa a ser uma TABELA igual
à de Gestão de Propriedades / Clientes (o "padrão base" do
sistema). Colunas: ID, NOME DA UNIDADE (com subtítulo a agregar ID
da unidade + nome do cliente + período), STATUS, AÇÕES. Cada linha
tem um único botão "Gerir" que abre `_AcoesReservaAirbnbModal`.

REESTRUTURAÇÃO 13/09/2026 (ronda 3 — aprovada por mockup HTML):

- O formulário `NovaReservaAirbnb` foi reformulado:
  * Cartão "Unidade e cliente": dropdown de unidade + dropdown de
    cliente com botão "+ Novo cliente" ao lado.
  * Cartão "Estadia": Data de entrada, Data de saída, Preço
    calculado (leitura, negrito) e Preço praticado (editável).
  * Cartão "Check-in tardio": checkbox + hora e multa lado a lado,
    com o combo "Responsável do desconto" da multa ainda dentro
    do cartão (a multa não tem modal de sub-confirmação — pode
    ficar a zero, decisão do aluno).
  * Resumo final: N noites × preço / Multa / Total.
  * O resumo e o rodapé vivem DENTRO da área de scroll — bug
    apanhado pelo aluno ao testar: com o formulário maior do que
    a janela, o resumo ficava fixo no fundo e acabava por sair
    da vista.

- Novo modal `_AlterarValorCalculadoModal` — sub-confirmação que
  aparece só quando o preço praticado é inferior ao calculado.
  Altura 540 — o conteúdo no caso com desconto + responsável +
  motivo não cabia em 440, e os botões "Voltar"/"Confirmar"
  ficavam fora da área visível.

- Botão "+ Novo cliente" acrescentado ao cartão "Cliente" de
  `NovoContratoMensal` e de `NovaReservaAirbnb`. Abre o
  `NovoClienteModal` de `gui_clientes.py` e pré-seleciona o
  cliente novo ao fechar.

- `_atualizar_resumo` passa a atualizar também o rótulo "Preço
  calculado" dentro do cartão Estadia (antes só mexia no resumo —
  o rótulo ficava sempre a dizer "— (escolhe as datas)" mesmo
  com as datas preenchidas).

CORREÇÃO — fecho do popup de Nova Reserva depois de registar. O
`_registar` deixa de fazer `_limpar_formulario()` e passa a pedir
ao popup (`popup_pai._fechar()`) para se fechar.

CONSOLIDAÇÃO DE HELPERS EM componentes.py (13/09/2026) — os
helpers visuais duplicados localmente passaram a viver só no
`componentes.py`:

- `_formatar_valor` local → `componentes.formatar_valor`. Diferença
  visível: o helper do `componentes.py` devolve "—" para `None` em
  vez de rebentar com `TypeError`; nos valores normais o resultado
  é idêntico.
- `_colocar_no_topo` local → `componentes.colocar_no_topo`.
- O resto do ficheiro não mudou.

Segue a mesma disciplina de camadas do resto da GUI (decisão 7): só
fala com `unidades`, `clientes`, `responsaveis`, `contratos`,
`validacoes`, `impressao` — nunca com `repositorio` diretamente.
"""

import datetime
import os
import subprocess
import sys
from decimal import Decimal, InvalidOperation

import customtkinter as ctk

import clientes
import config
import contratos
import impressao
import propriedades
import responsaveis
import unidades
import validacoes
from gui import componentes, tema

# Aliases locais para os helpers que viviam neste ficheiro e passaram
# a viver em componentes.py. Mantêm-se os nomes antigos com "_" para
# o corpo do ficheiro não ter de ser reescrito — mesma técnica já
# usada no gui_propriedades.py e no gui_est_requisicoes.py.
_formatar_valor = componentes.formatar_valor
_colocar_no_topo = componentes.colocar_no_topo


def _rotulo_lugar(lugar, ocupantes, capacidade):
    """Rótulo do dropdown de lugar: nome + estado ao vivo.

    Só distingue livre/parcial/ocupado (nunca "reservado" — decisão
    4 do módulo): aqui só interessa saber se ainda cabe mais gente.
    """
    if ocupantes == 0:
        estado = "livre"
    elif ocupantes >= capacidade:
        estado = "ocupado"
    else:
        estado = "parcial"

    return f"{lugar['nome']} · {estado} ({ocupantes}/{capacidade})"


# =====================================================================
# Botão "+ Novo cliente" — partilhado entre os dois formulários
# =====================================================================


def _abrir_novo_cliente(formulario, regime):
    """Abre o modal de novo cliente certo de `gui_clientes.py` a
    partir de um formulário (reserva Airbnb ou contrato mensal). O
    import é local, dentro da função, para evitar import circular
    entre `gui_contratos` e `gui_clientes`.

    ATUALIZADO 16/09/2026: `gui_clientes.NovoClienteModal` (um único
    formulário com seletor de Regime) foi substituído por dois
    modais dedicados — `NovoClienteMensalModal`/
    `NovoClienteAirbnbModal` — escolhidos normalmente por um popup
    prévio (`_SeletorRegimeClienteModal`). Aqui o regime já é
    conhecido pelo próprio formulário que chama (`NovoContratoMensal`
    passa "mensal", `NovaReservaAirbnb` passa "airbnb"), por isso
    abre-se logo o modal certo, sem passar pelo popup de escolha.

    Ao fechar o modal, recarrega a lista de clientes do formulário e
    pré-seleciona o cliente novo — se ele foi mesmo criado. O modal
    não devolve o cliente criado (chama `tela_lista._recarregar()`
    ou `_recarregar_clientes()` e fecha-se, ver
    `gui_clientes._recarregar_tela_lista`); para o pré-selecionar
    aqui, comparamos a lista antes e depois.
    """
    from gui.gui_clientes import (
        NovoClienteAirbnbModal,
        NovoClienteMensalModal,
    )

    classe_modal = (
        NovoClienteMensalModal
        if regime == "mensal"
        else NovoClienteAirbnbModal
    )

    ids_antes = {c["id"] for c in formulario.clientes_disponiveis}

    modal = classe_modal(formulario)
    formulario.wait_window(modal)

    formulario._recarregar_clientes()

    ids_agora = {c["id"] for c in formulario.clientes_disponiveis}
    novos = ids_agora - ids_antes

    if novos:
        # Só interessa o primeiro — o modal cria um cliente de cada
        # vez, nunca dois.
        cliente_novo_id = next(iter(novos))
        formulario._selecionar_cliente_por_id(cliente_novo_id)


# =====================================================================
# NOVO CONTRATO MENSAL
# =====================================================================


class NovoContratoMensal(ctk.CTkFrame):
    """Formulário de criação de um contrato de arrendamento mensal."""

    def __init__(self, master, controlador, unidade_id=None, lugar_id=None):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador
        self.unidade_selecionada = None
        self.lugares_da_unidade = []
        self.lugar_id_pendente = lugar_id

        componentes.Cabecalho(self, "Novo Contrato Mensal").pack(fill="x")

        self.area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.area.pack(fill="both", expand=True, padx=20, pady=16)

        self._montar_cartao_unidade()
        self._montar_cartao_cliente()
        self._montar_cartao_contrato()
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

    def _montar_cartao_unidade(self):
        corpo = self._criar_cartao("Unidade e lugar")

        self._linha(corpo, 0, "Unidade *")
        self.combo_unidade = ctk.CTkOptionMenu(
            corpo,
            values=["—"],
            command=self._ao_escolher_unidade,
        )
        self.combo_unidade.grid(row=0, column=1, sticky="ew", pady=6)

        self._linha(corpo, 1, "Lugar (opcional)")
        self.combo_lugar = ctk.CTkOptionMenu(corpo, values=["— Nenhum —"])
        self.combo_lugar.grid(row=1, column=1, sticky="ew", pady=6)

    def _montar_cartao_cliente(self):
        corpo = self._criar_cartao("Cliente")

        self._linha(corpo, 0, "Cliente *")

        # Bloco cliente: dropdown + botão "+ Novo cliente" ao lado.
        bloco = ctk.CTkFrame(corpo, fg_color="transparent")
        bloco.grid(row=0, column=1, sticky="ew", pady=6)
        bloco.grid_columnconfigure(0, weight=1)

        self.combo_cliente = ctk.CTkOptionMenu(bloco, values=["—"], width=1)
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
            command=lambda: _abrir_novo_cliente(self, "mensal"),
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))

    def _montar_cartao_contrato(self):
        corpo = self._criar_cartao("Datas e valores")

        self._linha(corpo, 0, "Data de início *")
        self.campo_data_inicio = ctk.CTkEntry(
            corpo, placeholder_text="dd/mm/aaaa"
        )
        self.campo_data_inicio.grid(row=0, column=1, sticky="ew", pady=6)

        self._linha(corpo, 1, "Dia de vencimento")
        self.campo_dia_vencimento = ctk.CTkEntry(
            corpo, placeholder_text=f"Enter para {config.DIA_VENCIMENTO}"
        )
        self.campo_dia_vencimento.grid(row=1, column=1, sticky="ew", pady=6)

        self._linha(corpo, 2, "Renda calculada")
        self.rotulo_renda_calculada = ctk.CTkLabel(
            corpo,
            text="— (escolhe a unidade)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.rotulo_renda_calculada.grid(row=2, column=1, sticky="ew", pady=6)

        self._linha(corpo, 3, "Renda praticada *")
        self.campo_renda_praticada = ctk.CTkEntry(
            corpo, placeholder_text="0,00"
        )
        self.campo_renda_praticada.grid(row=3, column=1, sticky="ew", pady=6)

        self._linha(corpo, 4, "Motivo da diferença")
        self.campo_motivo_renda = ctk.CTkEntry(
            corpo, placeholder_text="opcional — só se a renda for diferente"
        )
        self.campo_motivo_renda.grid(row=4, column=1, sticky="ew", pady=6)

        self._linha(corpo, 5, "Responsável do desconto")
        self.combo_responsavel = ctk.CTkOptionMenu(
            corpo, values=["— Nenhum —"]
        )
        self.combo_responsavel.grid(row=5, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(
            corpo,
            text="obrigatório quando a renda praticada é inferior à "
            "calculada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=6, column=1, sticky="w")

        self._linha(corpo, 7, "Caução *")
        self.campo_caucao = ctk.CTkEntry(corpo, placeholder_text="0,00")
        self.campo_caucao.grid(row=7, column=1, sticky="ew", pady=6)

        self.confirma_caucao = ctk.CTkCheckBox(
            corpo,
            text="Confirmo esta caução (nula ou superior à renda "
            "praticada)",
        )
        self.confirma_caucao.grid(row=8, column=1, sticky="w", pady=(0, 6))

        self._linha(corpo, 9, "Motivo da caução")
        self.campo_motivo_caucao = ctk.CTkEntry(
            corpo, placeholder_text="opcional"
        )
        self.campo_motivo_caucao.grid(row=9, column=1, sticky="ew", pady=6)

    def _montar_rodape(self):
        """Rodapé com o botão de criação.

        Passa a viver DENTRO da área de scroll (`self.area`), não em
        `self`. Sem isto, o rodapé ficava fixo no fundo da janela e
        saía da vista quando o conteúdo interior era maior do que o
        espaço disponível — mesmo bug do `NovaReservaAirbnb`, apanhado
        pelo aluno, 13/09/2026.
        """
        rodape = ctk.CTkFrame(self.area, fg_color="transparent")
        rodape.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(
            rodape,
            text="Criar contrato",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            corner_radius=tema.RAIO_BOTAO,
            command=self._criar,
        ).pack(side="right")

    # -- carregamento de dados -------------------------------------

    def _recarregar_unidades(self, unidade_id_inicial=None):
        # `listar_com_propriedade` em vez de `listar` (Fase 2,
        # v1.4.0): o rótulo passa a incluir o nome da propriedade,
        # para não confundir unidades com o mesmo nome em prédios
        # diferentes — mesmo problema já resolvido na Planta de
        # Lugares, aqui na mesma convenção "ID · texto" já usada
        # neste ficheiro para cliente/responsável.
        self.unidades_mensais = unidades.listar_com_propriedade(tipo="mensal")
        nomes = [
            f"{u['id']} · {u['propriedade_nome']} - {u['nome']}"
            for u in self.unidades_mensais
        ] or ["— Sem unidades mensais —"]
        self.combo_unidade.configure(values=nomes)

        alvo = None
        if unidade_id_inicial:
            alvo = next(
                (
                    u
                    for u in self.unidades_mensais
                    if u["id"] == unidade_id_inicial
                ),
                None,
            )
        if alvo is None and self.unidades_mensais:
            alvo = self.unidades_mensais[0]

        if alvo is not None:
            indice = self.unidades_mensais.index(alvo)
            self.combo_unidade.set(nomes[indice])
            self._ao_escolher_unidade(nomes[indice])

    def _recarregar_clientes(self):
        self.clientes_disponiveis = clientes.listar()
        nomes = [
            f"{c['id']} · {c['nome']} (NIF {c['nif'] or '—'})"
            for c in self.clientes_disponiveis
        ] or ["— Sem clientes —"]
        self.combo_cliente.configure(values=nomes)
        if self.clientes_disponiveis:
            self.combo_cliente.set(nomes[0])

    def _selecionar_cliente_por_id(self, cliente_id):
        """Pré-seleciona no dropdown o cliente com este id — usado
        depois de o `NovoClienteModal` criar um cliente novo.
        """
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
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel.configure(values=nomes)
        self.combo_responsavel.set(nomes[0])

    def _ao_escolher_unidade(self, _valor_escolhido):
        indice = self.combo_unidade.cget("values").index(
            self.combo_unidade.get()
        )
        if indice >= len(self.unidades_mensais):
            self.unidade_selecionada = None
            self.rotulo_renda_calculada.configure(text="—")
            self.combo_lugar.configure(values=["— Nenhum —"])
            self.combo_lugar.set("— Nenhum —")
            return

        self.unidade_selecionada = self.unidades_mensais[indice]
        self.rotulo_renda_calculada.configure(
            text=_formatar_valor(self.unidade_selecionada["preco_base"])
        )
        self._recarregar_lugares()

    def _recarregar_lugares(self):
        self.lugares_da_unidade = []
        opcoes = ["— Nenhum —"]

        if self.unidade_selecionada is None:
            self.combo_lugar.configure(values=opcoes)
            self.combo_lugar.set(opcoes[0])
            return

        contratos_da_unidade = contratos.listar(
            unidade_id=self.unidade_selecionada["id"], tipo="mensal"
        )

        for quarto in unidades.listar_quartos(
            unidade_id=self.unidade_selecionada["id"]
        ):
            for lugar in unidades.listar_lugares(quarto_id=quarto["id"]):
                ocupantes = sum(
                    1
                    for c in contratos_da_unidade
                    if c["lugar_id"] == lugar["id"]
                )
                self.lugares_da_unidade.append(lugar)
                opcoes.append(
                    _rotulo_lugar(lugar, ocupantes, lugar["capacidade"])
                )

        self.combo_lugar.configure(values=opcoes)
        self.combo_lugar.set(opcoes[0])

        if self.lugar_id_pendente:
            for i, lugar in enumerate(self.lugares_da_unidade):
                if lugar["id"] == self.lugar_id_pendente:
                    self.combo_lugar.set(opcoes[i + 1])
                    break
            self.lugar_id_pendente = None

    # -- submissão ----------------------------------------------------

    def _mostrar_erro(self, texto):
        componentes.mostrar_erro(texto)

    def _mostrar_sucesso(self, texto):
        componentes.mostrar_sucesso(texto)

    def _lugar_escolhido_id(self):
        indice = self.combo_lugar.cget("values").index(self.combo_lugar.get())
        if indice == 0:
            return ""
        return self.lugares_da_unidade[indice - 1]["id"]

    def _responsavel_escolhido_id(self):
        indice = self.combo_responsavel.cget("values").index(
            self.combo_responsavel.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _cliente_escolhido_id(self):
        indice = self.combo_cliente.cget("values").index(
            self.combo_cliente.get()
        )
        return self.clientes_disponiveis[indice]["id"]

    def _criar(self):
        if self.unidade_selecionada is None:
            self._mostrar_erro("Escolhe uma unidade mensal.")
            return

        try:
            data_inicio = datetime.datetime.strptime(
                self.campo_data_inicio.get().strip(), "%d/%m/%Y"
            ).date()
        except ValueError:
            self._mostrar_erro("Data de início inválida (usa dd/mm/aaaa).")
            return

        texto_dia = self.campo_dia_vencimento.get().strip()
        dia_vencimento = None
        if texto_dia:
            if not texto_dia.isdigit():
                self._mostrar_erro("O dia de vencimento tem de ser um número.")
                return
            dia_vencimento = int(texto_dia)

        try:
            renda_praticada = Decimal(
                self.campo_renda_praticada.get().strip().replace(",", ".")
            )
            caucao = Decimal(self.campo_caucao.get().strip().replace(",", "."))
        except InvalidOperation:
            self._mostrar_erro("Renda ou caução com formato inválido.")
            return

        if renda_praticada < self.unidade_selecionada["preco_base"]:
            if not self._responsavel_escolhido_id():
                self._mostrar_erro(
                    "É preciso escolher um responsável para autorizar o "
                    "desconto na renda."
                )
                return

        try:
            exige_confirmacao = validacoes.validar_caucao(
                caucao, renda_praticada, config.MULTIPLICADOR_MAXIMO_CAUCAO
            )
        except ValueError as erro:
            self._mostrar_erro(str(erro))
            return

        if exige_confirmacao and not self.confirma_caucao.get():
            self._mostrar_erro(
                "Confirma a caução (nula ou superior à renda praticada) "
                "na caixa de confirmação."
            )
            return

        try:
            ocupacao, _mensal = contratos.criar_mensal(
                self.unidade_selecionada["id"],
                self._cliente_escolhido_id(),
                data_inicio,
                renda_praticada,
                caucao,
                responsavel_desconto_renda_id=self._responsavel_escolhido_id(),
                lugar_id=self._lugar_escolhido_id(),
                dia_vencimento=dia_vencimento,
                motivo_alteracao_renda=self.campo_motivo_renda.get(),
                motivo_alteracao_caucao=self.campo_motivo_caucao.get(),
            )
        except ValueError as erro:
            self._mostrar_erro(str(erro))
            return

        aviso = (
            " (aviso: documento expira durante a estadia)"
            if (ocupacao["aviso_documento"])
            else ""
        )
        self._mostrar_sucesso(
            f"Contrato criado com sucesso: {ocupacao['id']}{aviso}"
        )
        self._limpar_formulario()

    def _limpar_formulario(self):
        """Repõe o formulário no estado inicial depois de criar um
        contrato com sucesso, para o próximo registo. Mantém a
        unidade escolhida; tudo o resto volta ao valor por omissão.
        """
        self.campo_data_inicio.delete(0, "end")
        self.campo_dia_vencimento.delete(0, "end")
        self.campo_renda_praticada.delete(0, "end")
        self.campo_motivo_renda.delete(0, "end")
        self.campo_caucao.delete(0, "end")
        self.campo_motivo_caucao.delete(0, "end")
        self.confirma_caucao.deselect()

        self._recarregar_clientes()
        self._recarregar_responsaveis()
        self._recarregar_lugares()


def _formatar_data(valor):
    """Formata uma date para dd/mm/aaaa — "em aberto" quando None
    (contrato mensal ainda ativo, sem data de fim marcada).
    """
    if valor is None:
        return "em aberto"
    return valor.strftime("%d/%m/%Y")


def _identificar_unidade(unidade, unidade_id):
    """Devolve "nome (ID)" para mostrar num cartão de ocupação, ou só
    o ID se a unidade não existir.
    """
    if unidade is None:
        return unidade_id
    return f"{unidade['nome']} ({unidade['id']})"


def _identificar_cliente(cliente, cliente_id):
    """Mesma ideia de `_identificar_unidade`, para clientes."""
    if cliente is None:
        return cliente_id
    return f"{cliente['nome']} ({cliente['id']})"


class NovoContratoModal(ctk.CTkToplevel):
    """Popup com o formulário de Novo Contrato Mensal."""

    def __init__(self, tela_lista, unidade_id=None, lugar_id=None):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title("Novo Contrato Mensal")
        self.geometry("640x760")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        NovoContratoMensal(
            self,
            controlador=tela_lista.controlador,
            unidade_id=unidade_id,
            lugar_id=lugar_id,
        ).pack(fill="both", expand=True)

    def _fechar(self):
        self.tela_lista._recarregar()
        self.destroy()


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
        self.combo_unidade = ctk.CTkOptionMenu(
            corpo,
            values=["—"],
            command=self._ao_escolher_unidade,
        )
        self.combo_unidade.grid(row=0, column=1, sticky="ew", pady=6)

        self._linha(corpo, 1, "Cliente *")

        bloco = ctk.CTkFrame(corpo, fg_color="transparent")
        bloco.grid(row=1, column=1, sticky="ew", pady=6)
        bloco.grid_columnconfigure(0, weight=1)

        self.combo_cliente = ctk.CTkOptionMenu(bloco, values=["—"], width=1)
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
        self.campo_data_inicio = ctk.CTkEntry(
            corpo, placeholder_text="dd/mm/aaaa"
        )
        self.campo_data_inicio.grid(row=0, column=1, sticky="ew", pady=6)
        self.campo_data_inicio.bind(
            "<FocusOut>", lambda _evento: self._atualizar_resumo()
        )
        self.campo_data_inicio.bind(
            "<Return>", lambda _evento: self._atualizar_resumo()
        )

        self._linha(corpo, 1, "Data de saída *")
        self.campo_data_fim = ctk.CTkEntry(
            corpo, placeholder_text="dd/mm/aaaa"
        )
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
            text="— (escolhe as datas)",
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
            text="— (escolhe a unidade)",
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

        self.combo_responsavel_multa = ctk.CTkOptionMenu(
            corpo, values=["— Nenhum —"]
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
        ] or ["— Sem unidades Airbnb —"]
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
        ] or ["— Sem clientes —"]
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
        nomes = ["— Nenhum —"] + [
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
            self.rotulo_multa_calculada.configure(text="— (escolhe a unidade)")
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
        "— (escolhe as datas)", mesmo com as datas preenchidas (bug
        apanhado pelo aluno, 13/09/2026).
        """
        preco_calculado = self._preco_calculado()

        # Rótulo do Preço calculado, dentro do cartão Estadia.
        if preco_calculado is None:
            self.rotulo_preco_calculado.configure(text="— (escolhe as datas)")
        else:
            self.rotulo_preco_calculado.configure(
                text=_formatar_valor(preco_calculado)
            )

        # Linha 1: N noites × preço.
        data_inicio = self._ler_data(self.campo_data_inicio)
        data_fim = self._ler_data(self.campo_data_fim)

        rotulo_noites, valor_noites = self.linha_noites

        if (
            data_inicio is None
            or data_fim is None
            or data_fim <= data_inicio
            or preco_calculado is None
        ):
            rotulo_noites.configure(text="0 noites × —")
            valor_noites.configure(text="—")
        else:
            noites = (data_fim - data_inicio).days
            preco_noite = preco_calculado / noites
            rotulo_noites.configure(
                text=(f"{noites} noites × " f"{_formatar_valor(preco_noite)}")
            )
            valor_noites.configure(text=_formatar_valor(preco_calculado))

        # Linha 2: multa de check-in tardio (valor praticado escrito,
        # ou a multa calculada, se o campo estiver vazio).
        multa_calculada = Decimal("0.00")
        if self.unidade_selecionada is not None:
            multa_calculada = self.unidade_selecionada["multa_check_in_tardio"]

        texto_multa = self.campo_multa_praticada.get().strip()
        if self.checkin_tardio.get():
            if texto_multa:
                try:
                    multa_valor = Decimal(texto_multa.replace(",", "."))
                except InvalidOperation:
                    multa_valor = multa_calculada
            else:
                multa_valor = multa_calculada
        else:
            multa_valor = Decimal("0.00")

        _, valor_multa = self.linha_multa
        valor_multa.configure(text=_formatar_valor(multa_valor))

        # Linha 3: total.
        _, valor_total = self.linha_total
        if preco_calculado is None:
            valor_total.configure(text="—")
        else:
            valor_total.configure(
                text=_formatar_valor(preco_calculado + multa_valor)
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
        chamado (o modal devolve o responsável e o motivo).

        Caso contrário: segue direto para
        `contratos.registar_airbnb`.
        """
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

        if preco_calculado is not None and preco_praticado < preco_calculado:
            self._abrir_alterar_valor(
                preco_calculado=preco_calculado,
                preco_praticado=preco_praticado,
                data_inicio=data_inicio,
                data_fim=data_fim,
                check_in_tardio=check_in_tardio,
                hora_chegada=hora_chegada,
                multa_praticada=multa_praticada,
            )
            return

        self._gravar(
            data_inicio=data_inicio,
            data_fim=data_fim,
            preco_praticado=preco_praticado,
            responsavel_desconto_preco_id="",
            motivo_preco="",
            check_in_tardio=check_in_tardio,
            hora_chegada=hora_chegada,
            multa_praticada=multa_praticada,
        )

    def _abrir_alterar_valor(
        self,
        preco_calculado,
        preco_praticado,
        data_inicio,
        data_fim,
        check_in_tardio,
        hora_chegada,
        multa_praticada,
    ):
        """Abre o `_AlterarValorCalculadoModal` como sub-confirmação.
        O modal devolve (responsavel_id, motivo) ao confirmar; ao
        "Voltar", fecha-se sem fazer nada.
        """

        def _on_confirmar(responsavel_id, motivo):
            self._gravar(
                data_inicio=data_inicio,
                data_fim=data_fim,
                preco_praticado=preco_praticado,
                responsavel_desconto_preco_id=responsavel_id,
                motivo_preco=motivo,
                check_in_tardio=check_in_tardio,
                hora_chegada=hora_chegada,
                multa_praticada=multa_praticada,
            )

        noites = (data_fim - data_inicio).days

        _AlterarValorCalculadoModal(
            self,
            noites=noites,
            valor_calculado=preco_calculado,
            valor_alterado=preco_praticado,
            ao_confirmar=_on_confirmar,
        )

    def _gravar(
        self,
        data_inicio,
        data_fim,
        preco_praticado,
        responsavel_desconto_preco_id,
        motivo_preco,
        check_in_tardio,
        hora_chegada,
        multa_praticada,
    ):
        """Chama `contratos.registar_airbnb` e trata do sucesso/erro.
        Este método é a única porta para gravar — chamado tanto pelo
        caminho direto do `_registar` como pelo callback de
        confirmação do `_AlterarValorCalculadoModal`.

        Valida a unidade de novo (defesa em profundidade): o
        `_registar` já garante isto no caminho direto, mas o
        `_gravar` também é chamado pelo callback do modal de
        sub-confirmação — e nesse caminho o Pylance não consegue
        provar que `self.unidade_selecionada` não é None (o método
        é chamado por closure, não por análise de fluxo direta).
        Guardar numa variável local resolve o aviso do linter.
        """
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

        aviso = (
            " (aviso: documento expira durante a estadia)"
            if (ocupacao["aviso_documento"])
            else ""
        )
        nota_motivo = f" [motivo: {motivo_preco}]" if motivo_preco else ""
        self._mostrar_sucesso(
            f"Reserva registada com sucesso: {ocupacao['id']}"
            f"{aviso}{nota_motivo}"
        )

        # Fecha o popup que contém este formulário — quem trata do
        # destroy() e do `_recarregar()` da lista por trás é o
        # próprio popup, no seu `_fechar()`.
        if self.popup_pai is not None:
            self.popup_pai._fechar()


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


class _AlterarValorCalculadoModal(ctk.CTkToplevel):
    """Sub-confirmação quando o preço praticado fica abaixo do
    calculado, no momento de registar uma reserva Airbnb (13/09/2026,
    ver docstring do módulo).

    Não é o "Editar reserva" (esse serve para corrigir uma reserva já
    criada) — este modal vive dentro do fluxo de criação.

    Recebe `ao_confirmar(responsavel_id, motivo)` — um callback do
    formulário pai que faz o `contratos.registar_airbnb` final.
    """

    def __init__(
        self,
        master,
        noites,
        valor_calculado,
        valor_alterado,
        ao_confirmar,
    ):
        super().__init__(master)
        self.ao_confirmar = ao_confirmar

        diferenca = valor_alterado - valor_calculado

        # 480x540 — o conteúdo cabe confortavelmente, sem scroll e
        # sem cortar os botões no fundo. Antes eram 440 e os botões
        # "Voltar"/"Confirmar" ficavam fora da área visível (bug
        # apanhado pelo aluno, 13/09/2026).
        largura, altura = 480, 540
        self.title("Alterar valor calculado")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        _colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(
            self,
            text="Alterar valor calculado",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 10))

        ctk.CTkLabel(
            self,
            text=(
                f"O valor calculado para {noites} noites é "
                f"{_formatar_valor(valor_calculado)}."
            ),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(anchor="w", padx=24)

        ctk.CTkLabel(
            self,
            text=(f"Vai gravar {_formatar_valor(valor_alterado)}."),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(anchor="w", padx=24, pady=(2, 12))

        # ---- Cartão calculado / alterado / diferença ----
        cartao = ctk.CTkFrame(
            self,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", padx=24, pady=(0, 12))

        corpo = ctk.CTkFrame(cartao, fg_color="transparent")
        corpo.pack(fill="x", padx=16, pady=12)

        self._linha_cartao(
            corpo, "calculado", _formatar_valor(valor_calculado)
        )
        self._linha_cartao(corpo, "alterado", _formatar_valor(valor_alterado))
        self._linha_cartao(
            corpo,
            "diferença",
            _formatar_valor(diferenca),
            cor_valor=tema.TEXTO_ERRO,
        )

        # ---- Motivo (opcional) ----
        ctk.CTkLabel(
            self,
            text="motivo (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(anchor="w", padx=24)

        self.campo_motivo = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="desconto acordado…",
        )
        self.campo_motivo.pack(fill="x", padx=24, pady=(2, 12))

        # ---- Responsável do desconto (obrigatório) ----
        ctk.CTkLabel(
            self,
            text="Responsável do desconto *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(anchor="w", padx=24)

        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel = ctk.CTkOptionMenu(
            self,
            values=nomes,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_responsavel.set(nomes[0])
        self.combo_responsavel.pack(fill="x", padx=24, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text="obrigatório quando o valor é inferior ao calculado",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(anchor="w", padx=24)

        # ---- Rodapé ----
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(16, 20), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Voltar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Confirmar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._confirmar,
        ).pack(side="right")

    def _linha_cartao(self, master, rotulo, valor, cor_valor=None):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", pady=2)

        ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=valor,
            text_color=cor_valor or tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="e",
        ).pack(side="right")

    def _responsavel_escolhido_id(self):
        indice = self.combo_responsavel.cget("values").index(
            self.combo_responsavel.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _confirmar(self):
        responsavel_id = self._responsavel_escolhido_id()

        if not responsavel_id:
            componentes.mostrar_erro(
                "Escolhe o responsável que autoriza o desconto."
            )
            return

        motivo = self.campo_motivo.get().strip()

        self.destroy()
        self.ao_confirmar(responsavel_id, motivo)


class EncerrarContratoModal(ctk.CTkToplevel):
    """Popup de encerramento de um contrato mensal."""

    def __init__(self, tela_lista, ocupacao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao

        self.title("Encerrar contrato mensal")
        self.geometry("420x400")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = _identificar_unidade(unidade, ocupacao["unidade_id"])
        nome_cliente = _identificar_cliente(cliente, ocupacao["cliente_id"])

        mensagem = (
            f"Encerrar o contrato {ocupacao['id']}?\n"
            f"{nome_cliente} · unidade {nome_unidade}\n"
            f"Início: {_formatar_data(ocupacao['data_inicio'])}"
        )
        ctk.CTkLabel(
            self,
            text=mensagem,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            wraplength=370,
            justify="left",
        ).pack(padx=20, pady=(24, 14), fill="x")

        ctk.CTkLabel(
            self,
            text="Data de fim *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_data_fim = ctk.CTkEntry(
            self,
            placeholder_text="dd/mm/aaaa",
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_data_fim.insert(
            0, datetime.date.today().strftime("%d/%m/%Y")
        )
        self.campo_data_fim.pack(fill="x", padx=20, pady=(2, 10))
        self.campo_data_fim.bind(
            "<FocusOut>", lambda _evento: self._atualizar_avisos()
        )
        self.campo_data_fim.bind(
            "<Return>", lambda _evento: self._atualizar_avisos()
        )

        self.caixa_avisos = ctk.CTkLabel(
            self,
            text="",
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w",
            wraplength=350,
        )

        self.rotulo_motivo = ctk.CTkLabel(
            self,
            text="Motivo do encerramento (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        )
        self.rotulo_motivo.pack(anchor="w", padx=20)

        self.campo_motivo = ctk.CTkEntry(
            self,
            placeholder_text="ex.: saída antecipada do inquilino",
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_motivo.pack(fill="x", padx=20, pady=(2, 10))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Encerrar contrato",
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._encerrar,
        ).pack(side="right")

        self._atualizar_avisos()

    # -- avisos ao vivo ------------------------------------------------

    def _ler_data_fim(self):
        texto = self.campo_data_fim.get().strip()

        if not texto:
            return None

        try:
            return datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            return None

    def _atualizar_avisos(self):
        data_fim = self._ler_data_fim()

        if data_fim is None:
            self.caixa_avisos.pack_forget()
            return

        avisos = contratos.avisos_encerramento(self.ocupacao, data_fim)
        linhas = []

        if avisos["duracao_abaixo_minima"]:
            linhas.append(
                f"⚠  Duração abaixo do mínimo "
                f"({config.DURACAO_MINIMA_MESES} meses)"
            )

        if avisos["aviso_previo_insuficiente"]:
            linhas.append(
                f"⚠  Aviso prévio insuficiente "
                f"({config.AVISO_PREVIO_DIAS} dias)"
            )

        if not linhas:
            self.caixa_avisos.pack_forget()
            return

        self.caixa_avisos.configure(text="\n".join(linhas))
        self.caixa_avisos.pack(
            fill="x",
            padx=20,
            pady=(0, 10),
            ipady=8,
            before=self.rotulo_motivo,
        )

    # -- ação ------------------------------------------------------------

    def _encerrar(self):
        texto = self.campo_data_fim.get().strip()

        try:
            data_fim = datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            componentes.mostrar_erro("Data de fim inválida (usa dd/mm/aaaa).")
            return

        try:
            ocupacao, mensal = contratos.encerrar_mensal(
                self.ocupacao["id"],
                data_fim,
                motivo=self.campo_motivo.get().strip(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        avisos = []
        if mensal["duracao_abaixo_minima"]:
            avisos.append("duração abaixo do mínimo")
        if mensal["aviso_previo_insuficiente"]:
            avisos.append("aviso prévio insuficiente")

        texto_avisos = f" [{', '.join(avisos)}]" if avisos else ""

        componentes.mostrar_sucesso(
            f"Contrato {ocupacao['id']} encerrado em "
            f"{_formatar_data(data_fim)}{texto_avisos}."
        )
        self.destroy()
        self.tela_lista._recarregar()


class CancelarReservaModal(ctk.CTkToplevel):
    """Popup de cancelamento de uma reserva Airbnb."""

    def __init__(self, tela_lista, ocupacao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao

        self.title("Cancelar reserva Airbnb")
        self.geometry("420x300")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = _identificar_unidade(unidade, ocupacao["unidade_id"])
        nome_cliente = _identificar_cliente(cliente, ocupacao["cliente_id"])
        periodo = (
            f"{_formatar_data(ocupacao['data_inicio'])} → "
            f"{_formatar_data(ocupacao['data_fim'])}"
        )

        mensagem = (
            f"Cancelar a reserva {ocupacao['id']}?\n"
            f"{nome_cliente} · unidade {nome_unidade}\n"
            f"Estadia: {periodo}"
        )
        ctk.CTkLabel(
            self,
            text=mensagem,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            wraplength=370,
            justify="left",
        ).pack(padx=20, pady=(24, 14), fill="x")

        ctk.CTkLabel(
            self,
            text="Motivo do cancelamento (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_motivo = ctk.CTkEntry(
            self,
            placeholder_text="ex.: hóspede desistiu",
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_motivo.pack(fill="x", padx=20, pady=(2, 10))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Voltar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Cancelar reserva",
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._cancelar,
        ).pack(side="right")

    def _cancelar(self):
        try:
            ocupacao, airbnb = contratos.cancelar_airbnb(
                self.ocupacao["id"],
                motivo=self.campo_motivo.get().strip(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Reserva {ocupacao['id']} cancelada.")
        self.destroy()
        self.tela_lista._recarregar()


class ListaContratosMensais(ctk.CTkFrame):
    """Lista dos contratos mensais — ecrã "Contrato Mensal" da barra
    lateral.

    Em tabela desde 13/09/2026. Colunas: ID, NOME UNIDADE, NOME DO
    CLIENTE, DATA, STATUS, AÇÕES. Cada linha tem um único botão
    "Gerir", que abre `_AcoesContratoModal`.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Contrato Mensal").pack(fill="x")

        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Novo Contrato",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovoContratoModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.combo_aviso = ctk.CTkOptionMenu(
            barra,
            values=["Todos", "Com aviso", "Sem aviso"],
            command=lambda _valor: self._recarregar(),
            width=130,
        )
        self.combo_aviso.set("Todos")
        self.combo_aviso.pack(side="right")

        self.mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativas/encerradas",
            variable=self.mostrar_inativas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

        self.tabela = componentes.Tabela(
            self,
            colunas=(
                componentes.Coluna("ID", minimo=110, espaco=8),
                componentes.Coluna("NOME UNIDADE", peso=3, minimo=180),
                componentes.Coluna("NOME DO CLIENTE", peso=3, minimo=180),
                componentes.Coluna(
                    "DATA", peso=2, minimo=180, alinhamento="w"
                ),
                componentes.Coluna(
                    "STATUS",
                    peso=1,
                    minimo=110,
                    alinhamento="centro",
                ),
                componentes.Coluna("AÇÕES", minimo=90, alinhamento="centro"),
            ),
            altura_linha=52,
            mensagem_vazia="Nenhum contrato mensal encontrado.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _aviso_selecionado(self):
        return {"Todos": None, "Com aviso": True, "Sem aviso": False}[
            self.combo_aviso.get()
        ]

    def _recarregar(self):
        self.tabela.limpar()

        lista = contratos.listar(
            incluir_inativas=self.mostrar_inativas.get(),
            tipo="mensal",
            aviso_documento=self._aviso_selecionado(),
        )

        if not lista:
            self.tabela.mostrar_vazio()
            return

        for ocupacao in lista:
            self._desenhar_ocupacao(ocupacao)

    # -- desenho -------------------------------------------------------

    def _desenhar_ocupacao(self, ocupacao):
        inativa = not ocupacao["ativo"]

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])

        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        id_unidade = ocupacao["unidade_id"]

        nome_cliente = cliente["nome"] if cliente else ocupacao["cliente_id"]
        id_cliente = ocupacao["cliente_id"]

        linha = self.tabela.nova_linha()

        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=ocupacao["id"],
                text_color=tema.AZUL_PRINCIPAL,
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=110,
                anchor="w",
            ),
            esticar="w",
        )

        bloco_unidade = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            bloco_unidade,
            text=nome_unidade,
            text_color=(
                tema.TEXTO_INDISPONIVEL if inativa else tema.COR_TEXTO
            ),
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            bloco_unidade,
            text=id_unidade,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 1, bloco_unidade)

        bloco_cliente = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            bloco_cliente,
            text=nome_cliente,
            text_color=(
                tema.TEXTO_INDISPONIVEL if inativa else tema.COR_TEXTO
            ),
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            bloco_cliente,
            text=id_cliente,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 2, bloco_cliente)

        data_inicio = _formatar_data(ocupacao["data_inicio"])
        data_fim = _formatar_data(ocupacao["data_fim"])
        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=f"{data_inicio} → {data_fim}",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                anchor="w",
            ),
        )

        bloco_status = ctk.CTkFrame(linha, fg_color="transparent")

        if inativa:
            ctk.CTkLabel(
                bloco_status,
                text="Encerrado",
                text_color=tema.TEXTO_INDISPONIVEL,
                fg_color=tema.CINZA_INDISPONIVEL,
                corner_radius=8,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=90,
                height=22,
            ).pack(side="left")

            if ocupacao["aviso_documento"]:
                ctk.CTkLabel(
                    bloco_status,
                    text="Doc. a expirar",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=8,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    width=100,
                    height=22,
                ).pack(side="left", padx=(6, 0))
        else:
            ctk.CTkLabel(
                bloco_status,
                text="Ativa",
                text_color=tema.TEXTO_LIVRE,
                fg_color=tema.VERDE_LIVRE,
                corner_radius=8,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=70,
                height=22,
            ).pack(side="left")

            if ocupacao["aviso_documento"]:
                ctk.CTkLabel(
                    bloco_status,
                    text="Doc. a expirar",
                    text_color=tema.TEXTO_AVISO,
                    fg_color=tema.AMARELO_AVISO,
                    corner_radius=8,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    width=100,
                    height=22,
                ).pack(side="left", padx=(6, 0))

        self.tabela.colocar(linha, 4, bloco_status)

        acoes = self.tabela.celula_acoes(linha, 5)
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
                command=lambda: _AcoesContratoModal(self, ocupacao),
            )
        )

    # -- ações -------------------------------------------------------

    def _reativar(self, ocupacao):
        pergunta = f"Reativar o contrato {ocupacao['id']}?"
        if not componentes.confirmar(pergunta):
            return

        try:
            contratos.reativar(ocupacao["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Contrato {ocupacao['id']} reativado.")
        self._recarregar()


class _AcoesContratoModal(ctk.CTkToplevel):
    """Popup pequeno com as ações de um contrato mensal — aberto
    pelo botão "Gerir" de cada linha em `ListaContratosMensais`.
    """

    def __init__(self, tela_lista, ocupacao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        nome_cliente = cliente["nome"] if cliente else ocupacao["cliente_id"]

        self.title(f"Ações — {ocupacao['id']}")
        self.geometry("340x300")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=nome_unidade,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=f"{ocupacao['id']} · {nome_cliente}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=280,
        ).pack(pady=(0, 14))

        if ocupacao["ativo"]:
            self._botao(
                "Encerrar contrato",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EncerrarContratoModal(self.tela_lista, ocupacao),
            )
        else:
            self._botao(
                "Reativar contrato",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self.tela_lista._reativar(ocupacao),
            )

        cliente_anonimizado = bool(cliente and cliente["anonimizado"])

        if cliente_anonimizado:
            ctk.CTkLabel(
                self,
                text=(
                    "Impressão indisponível — o cliente deste "
                    "contrato foi anonimizado (RGPD), e os dados "
                    "pessoais foram apagados."
                ),
                text_color=tema.TEXTO_INDISPONIVEL,
                font=ctk.CTkFont(size=10),
                wraplength=280,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=20, pady=(10, 6))
        else:
            ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
                fill="x", padx=20, pady=(8, 5)
            )

            self._botao(
                "Imprimir contrato",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: _ImprimirContratoModal(
                    self.tela_lista, ocupacao, self
                ),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=(10, 16))

    def _botao(self, texto, text_color, hover_color, acao):
        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)


class _ImprimirContratoModal(ctk.CTkToplevel):
    """Popup intermédio do "Imprimir contrato" — pede o senhorio e o
    local, antes de gerar o PDF.
    """

    def __init__(self, tela_lista, ocupacao, popup_pai=None):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao
        self.popup_pai = popup_pai

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        nome_cliente = cliente["nome"] if cliente else ocupacao["cliente_id"]

        self.title(f"Imprimir contrato — {ocupacao['id']}")
        self.geometry("460x400")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Identificar as partes do contrato",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(22, 2))

        ctk.CTkLabel(
            self,
            text=f"{ocupacao['id']} · {nome_unidade} · {nome_cliente}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=410,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 18))

        ctk.CTkLabel(
            self,
            text="Senhorio / Primeiro Contraente",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Escolher responsável —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_senhorio = ctk.CTkOptionMenu(
            self, values=nomes, corner_radius=tema.RAIO_CAMPO
        )
        self.combo_senhorio.set(nomes[0])
        self.combo_senhorio.pack(fill="x", padx=24, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text=(
                "Assina do lado do senhorio. Aparece no PDF como "
                '"Primeiro Contraente".'
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=410,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            self,
            text="Local",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_local = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: Porto",
        )
        self.campo_local.pack(fill="x", padx=24, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text=(
                "Cidade onde o contrato é assinado. Aparece na "
                "linha final do PDF."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=410,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(16, 20), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Gerar PDF",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._gerar_pdf,
        ).pack(side="right")

    def _responsavel_escolhido_id(self):
        indice = self.combo_senhorio.cget("values").index(
            self.combo_senhorio.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _gerar_pdf(self):
        senhorio_id = self._responsavel_escolhido_id()

        if not senhorio_id:
            componentes.mostrar_erro(
                "Escolhe o senhorio que assina pelo lado do Primeiro "
                "Contraente."
            )
            return

        local = self.campo_local.get().strip()

        if not local:
            componentes.mostrar_erro(
                "Escreve o local (cidade) onde o contrato é assinado."
            )
            return

        senhorio = responsaveis.procurar(senhorio_id)

        if senhorio is None:
            componentes.mostrar_erro(
                f"O responsável {senhorio_id} já não existe."
            )
            return

        mensal = contratos.detalhes_mensal(self.ocupacao["id"])

        if mensal is None:
            componentes.mostrar_erro(
                "Faltam os dados mensais deste contrato (inconsistência "
                "nos dados)."
            )
            return

        unidade = unidades.procurar(self.ocupacao["unidade_id"])

        if unidade is None:
            componentes.mostrar_erro("A unidade deste contrato já não existe.")
            return

        propriedade = propriedades.procurar(unidade["propriedade_id"])

        if propriedade is None:
            componentes.mostrar_erro(
                "A propriedade desta unidade já não existe."
            )
            return

        cliente = clientes.procurar(self.ocupacao["cliente_id"])

        if cliente is None:
            componentes.mostrar_erro("O cliente deste contrato já não existe.")
            return

        if cliente["anonimizado"]:
            componentes.mostrar_erro(
                "Não é possível imprimir um contrato cujo cliente "
                "foi anonimizado (RGPD)."
            )
            return

        try:
            caminho = impressao.gerar_contrato_pdf(
                ocupacao=self.ocupacao,
                mensal=mensal,
                cliente=cliente,
                unidade=unidade,
                propriedade=propriedade,
                senhorio=senhorio,
                local=local,
            )
        except Exception as erro:
            componentes.mostrar_erro(f"Erro ao gerar o PDF: {erro}")
            return

        popup_pai = self.popup_pai
        self.destroy()

        if popup_pai is not None:
            try:
                if popup_pai.winfo_exists():
                    popup_pai.destroy()
            except Exception:
                pass

        self._abrir_no_sistema(caminho)

        componentes.mostrar_sucesso(f"Contrato gerado e aberto:\n{caminho}")

    @staticmethod
    def _abrir_no_sistema(caminho):
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(caminho))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(caminho)])
            else:
                subprocess.Popen(["xdg-open", str(caminho)])
        except (FileNotFoundError, OSError):
            pass


# =====================================================================
# RESERVAS AIRBNB — tabela (13/09/2026)
# =====================================================================


_LARGURA_ID_RESERVA = 110
_LARGURA_UNIDADE_RESERVA = 320
_LARGURA_ESTADO_RESERVA = 200
_LARGURA_ACOES_RESERVA = 100

_ALTURA_LINHA_RESERVA = 52

_COLUNAS_RESERVA = (
    componentes.Coluna("ID", minimo=_LARGURA_ID_RESERVA + 24, espaco=8),
    componentes.Coluna(
        "NOME DA UNIDADE", peso=3, minimo=_LARGURA_UNIDADE_RESERVA
    ),
    componentes.Coluna(
        "STATUS",
        peso=1,
        minimo=_LARGURA_ESTADO_RESERVA,
        alinhamento="centro",
    ),
    componentes.Coluna(
        "AÇÕES", minimo=_LARGURA_ACOES_RESERVA, alinhamento="centro"
    ),
)


class ListaReservasAirbnb(ctk.CTkFrame):
    """Lista das reservas Airbnb — ecrã "Reservas Airbnb" da barra
    lateral.

    Reestruturado em 13/09/2026: em tabela igual à de Gestão de
    Propriedades / Clientes.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Reservas Airbnb").pack(fill="x")

        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Nova Reserva Airbnb",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovaReservaAirbnbModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.combo_aviso = ctk.CTkOptionMenu(
            barra,
            values=["Todos", "Com aviso", "Sem aviso"],
            command=lambda _valor: self._recarregar(),
            width=130,
        )
        self.combo_aviso.set("Todos")
        self.combo_aviso.pack(side="right")

        self.mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativas/encerradas",
            variable=self.mostrar_inativas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_RESERVA,
            altura_linha=_ALTURA_LINHA_RESERVA,
            mensagem_vazia="Nenhuma reserva Airbnb encontrada.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _aviso_selecionado(self):
        return {"Todos": None, "Com aviso": True, "Sem aviso": False}[
            self.combo_aviso.get()
        ]

    def _recarregar(self):
        self.tabela.limpar()

        lista = contratos.listar(
            incluir_inativas=self.mostrar_inativas.get(),
            tipo="airbnb",
            aviso_documento=self._aviso_selecionado(),
        )

        if not lista:
            self.tabela.mostrar_vazio()
            return

        for ocupacao in lista:
            self._desenhar_ocupacao(ocupacao)

    # -- desenho -------------------------------------------------------

    def _desenhar_ocupacao(self, ocupacao):
        inativa = not ocupacao["ativo"]

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        nome_cliente = cliente["nome"] if cliente else ocupacao["cliente_id"]
        periodo = (
            f"{_formatar_data(ocupacao['data_inicio'])} → "
            f"{_formatar_data(ocupacao['data_fim'])}"
        )

        linha = self.tabela.nova_linha()

        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=ocupacao["id"],
                text_color=tema.AZUL_PRINCIPAL,
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ID_RESERVA,
                anchor="w",
            ),
            esticar="w",
        )

        subtitulo = (
            f"{ocupacao['unidade_id']} · "
            f"{nome_cliente} ({ocupacao['cliente_id']}) · "
            f"{periodo}"
        )

        bloco_unidade = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            bloco_unidade,
            text=nome_unidade,
            text_color=(
                tema.TEXTO_INDISPONIVEL if inativa else tema.COR_TEXTO
            ),
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            bloco_unidade,
            text=subtitulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 1, bloco_unidade)

        bloco_status = ctk.CTkFrame(linha, fg_color="transparent")

        if inativa:
            ctk.CTkLabel(
                bloco_status,
                text="Cancelada",
                text_color=tema.TEXTO_INDISPONIVEL,
                fg_color=tema.CINZA_INDISPONIVEL,
                corner_radius=8,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=90,
                height=22,
            ).pack(side="left")
        else:
            ctk.CTkLabel(
                bloco_status,
                text="Ativa",
                text_color=tema.TEXTO_LIVRE,
                fg_color=tema.VERDE_LIVRE,
                corner_radius=8,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=70,
                height=22,
            ).pack(side="left")

        if ocupacao["aviso_documento"]:
            ctk.CTkLabel(
                bloco_status,
                text="Doc. a expirar",
                text_color=tema.TEXTO_AVISO,
                fg_color=tema.AMARELO_AVISO,
                corner_radius=8,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=100,
                height=22,
            ).pack(side="left", padx=(6, 0))

        self.tabela.colocar(linha, 2, bloco_status)

        acoes = self.tabela.celula_acoes(linha, 3)
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
                command=lambda: _AcoesReservaAirbnbModal(self, ocupacao),
            )
        )

    # -- ações -------------------------------------------------------

    def _reativar(self, ocupacao):
        pergunta = f"Reativar a reserva {ocupacao['id']}?"
        if not componentes.confirmar(pergunta):
            return

        try:
            contratos.reativar(ocupacao["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Reserva {ocupacao['id']} reativada.")
        self._recarregar()


class _AcoesReservaAirbnbModal(ctk.CTkToplevel):
    """Popup pequeno com as ações de uma reserva Airbnb.

    Duas variantes:
    - Reserva ativa → Editar · separador · Cancelar reserva.
    - Reserva cancelada → Reativar.
    """

    def __init__(self, tela_lista, ocupacao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao

        inativa = not ocupacao["ativo"]

        unidade = unidades.procurar(ocupacao["unidade_id"])
        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]

        altura = 240 if inativa else 270

        self.title(f"Ações — {ocupacao['id']}")
        self.geometry(f"320x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        self._centrar_sobre(tela_lista, altura)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=nome_unidade,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        subtitulo = (
            f"{ocupacao['id']} · cancelada"
            if inativa
            else f"{ocupacao['id']} · ativa"
        )
        ctk.CTkLabel(
            self,
            text=subtitulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if inativa:
            self._botao(
                "Reativar",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self.tela_lista._reativar(ocupacao),
            )
        else:
            self._botao(
                "Editar",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EditarReservaAirbnbModal(
                    self.tela_lista, ocupacao
                ),
            )
            self._separador()
            self._botao(
                "Cancelar reserva",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: CancelarReservaModal(self.tela_lista, ocupacao),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", fill="x", padx=20, pady=(10, 16))

    def _centrar_sobre(self, janela, altura):
        janela.update_idletasks()
        x = janela.winfo_rootx() + (janela.winfo_width() - 320) // 2
        y = janela.winfo_rooty() + (janela.winfo_height() - altura) // 2
        self.geometry(f"320x{altura}+{max(x, 0)}+{max(y, 0)}")

    def _separador(self):
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, text_color, hover_color, acao):
        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)


class EditarReservaAirbnbModal(ctk.CTkToplevel):
    """Popup de edição de uma reserva Airbnb — segue o modelo do
    `NovaReservaAirbnb` (cartões com grelha rótulo → campo), mas só
    com os campos que `contratos.atualizar_airbnb` aceita: Preço
    praticado (e motivo + responsável do desconto), e — só quando a
    reserva teve check-in tardio — Multa praticada (e motivo +
    responsável do desconto da multa).

    Este é o "Editar" para corrigir uma reserva já criada. Não
    confundir com o `_AlterarValorCalculadoModal`, que é a
    sub-confirmação dentro do fluxo de criação — decisão do aluno,
    13/09/2026.
    """

    def __init__(self, tela_lista, ocupacao):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.ocupacao = ocupacao

        self.airbnb = contratos.detalhes_airbnb(ocupacao["id"])

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        nome_cliente = cliente["nome"] if cliente else ocupacao["cliente_id"]
        periodo = (
            f"{_formatar_data(ocupacao['data_inicio'])} → "
            f"{_formatar_data(ocupacao['data_fim'])}"
        )

        altura = 620 + (200 if self.airbnb["check_in_tardio"] else 0)

        self.title(f"Editar Reserva Airbnb — {ocupacao['id']}")
        self.geometry(f"640x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar Reserva Airbnb — {ocupacao['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=(
                f"{nome_unidade} ({ocupacao['unidade_id']}) · "
                f"{nome_cliente} ({ocupacao['cliente_id']}) · "
                f"{periodo}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            wraplength=580,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 14))

        area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=24, pady=(0, 4))

        corpo = self._criar_cartao(area, "Estadia e valores")

        self._linha_leitura(
            corpo,
            0,
            "Preço calculado",
            _formatar_valor(self.airbnb["preco_calculado"]),
        )

        self._linha(corpo, 1, "Preço praticado *")
        self.campo_preco_praticado = ctk.CTkEntry(
            corpo, placeholder_text="0,00"
        )
        self.campo_preco_praticado.insert(
            0, f"{self.airbnb['preco_praticado']:.2f}"
        )
        self.campo_preco_praticado.grid(row=1, column=1, sticky="ew", pady=6)

        self._linha(corpo, 2, "Motivo da diferença")
        self.campo_motivo_preco = ctk.CTkEntry(
            corpo,
            placeholder_text="opcional — só se o preço for diferente",
        )
        self.campo_motivo_preco.grid(row=2, column=1, sticky="ew", pady=6)

        self._linha(corpo, 3, "Responsável do desconto")
        self.combo_responsavel_preco = ctk.CTkOptionMenu(
            corpo, values=["— Nenhum —"]
        )
        self.combo_responsavel_preco.grid(row=3, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(
            corpo,
            text="obrigatório quando o preço praticado é inferior ao "
            "calculado",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=4, column=1, sticky="w")

        if self.airbnb["check_in_tardio"]:
            corpo_ct = self._criar_cartao(area, "Check-in tardio")

            self._linha_leitura(
                corpo_ct,
                0,
                "Multa calculada",
                _formatar_valor(self.airbnb["multa_calculada"]),
            )

            self._linha(corpo_ct, 1, "Multa praticada")
            self.campo_multa_praticada = ctk.CTkEntry(
                corpo_ct,
                placeholder_text="Enter para a multa calculada",
            )
            self.campo_multa_praticada.insert(
                0, f"{self.airbnb['multa_praticada']:.2f}"
            )
            self.campo_multa_praticada.grid(
                row=1, column=1, sticky="ew", pady=6
            )

            self._linha(corpo_ct, 2, "Responsável do desconto")
            self.combo_responsavel_multa = ctk.CTkOptionMenu(
                corpo_ct, values=["— Nenhum —"]
            )
            self.combo_responsavel_multa.grid(
                row=2, column=1, sticky="ew", pady=6
            )
            ctk.CTkLabel(
                corpo_ct,
                text="obrigatório quando a multa praticada é inferior "
                "à calculada",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10),
            ).grid(row=3, column=1, sticky="w")

        ctk.CTkLabel(
            area,
            text=(
                "Unidade, cliente, datas e check-in tardio não se "
                "alteram depois da reserva criada — só o preço "
                "praticado, a multa praticada e os responsáveis "
                "dos descontos."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=580,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 12))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(4, 18), side="bottom")

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
            command=self._guardar,
        ).pack(side="right")

        self._recarregar_responsaveis()

    # -- montagem ----------------------------------------------------

    def _criar_cartao(self, master, titulo):
        cartao = ctk.CTkFrame(
            master,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", pady=(0, 14))
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

    def _linha_leitura(self, corpo, linha, rotulo, valor):
        ctk.CTkLabel(
            corpo,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=160,
        ).grid(row=linha, column=0, sticky="w", pady=6, padx=(0, 12))

        ctk.CTkLabel(
            corpo,
            text=valor,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).grid(row=linha, column=1, sticky="ew", pady=6)

    def _recarregar_responsaveis(self):
        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel_preco.configure(values=nomes)
        self.combo_responsavel_preco.set(nomes[0])

        if self.airbnb["check_in_tardio"]:
            self.combo_responsavel_multa.configure(values=nomes)
            self.combo_responsavel_multa.set(nomes[0])

    # -- submissão ---------------------------------------------------

    def _id_responsavel(self, combo):
        indice = combo.cget("values").index(combo.get())
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _guardar(self):
        texto_preco = self.campo_preco_praticado.get().strip()

        if not texto_preco:
            componentes.mostrar_erro("O preço praticado é obrigatório.")
            return

        try:
            preco_praticado = Decimal(texto_preco.replace(",", "."))
        except InvalidOperation:
            componentes.mostrar_erro("Preço praticado com formato inválido.")
            return

        multa_praticada = None
        if self.airbnb["check_in_tardio"]:
            texto_multa = self.campo_multa_praticada.get().strip()
            if texto_multa:
                try:
                    multa_praticada = Decimal(texto_multa.replace(",", "."))
                except InvalidOperation:
                    componentes.mostrar_erro(
                        "Multa praticada com formato inválido."
                    )
                    return

        try:
            contratos.atualizar_airbnb(
                self.ocupacao["id"],
                preco_praticado=preco_praticado,
                responsavel_desconto_preco_id=self._id_responsavel(
                    self.combo_responsavel_preco
                ),
                multa_praticada=multa_praticada,
                responsavel_desconto_multa_id=(
                    self._id_responsavel(self.combo_responsavel_multa)
                    if self.airbnb["check_in_tardio"]
                    else ""
                ),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Reserva {self.ocupacao['id']} atualizada."
        )
        self.destroy()
        self.tela_lista._recarregar()