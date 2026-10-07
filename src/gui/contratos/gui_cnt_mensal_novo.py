"""Formulário de novo contrato de arrendamento mensal
(`NovoContratoMensal`) e o popup que o embrulha
(`NovoContratoModal`)."""

import datetime
from decimal import Decimal, InvalidOperation

import customtkinter as ctk

import clientes
import config
import contratos
import responsaveis
import unidades
import validacoes

from gui import componentes, tema
from gui.contratos import gui_cnt_comum

# Aliases locais para helpers que vivem em componentes.py (nomes
# antigos com "_", para o corpo não ter de ser reescrito).
_formatar_valor = componentes.formatar_valor
_colocar_no_topo = componentes.colocar_no_topo

# Helpers partilhados dos contratos (nomes públicos em
# gui_cnt_comum) — alias local, mesmo padrão dos gui_est_*.
_rotulo_lugar = gui_cnt_comum.rotulo_lugar
_abrir_novo_cliente = gui_cnt_comum.abrir_novo_cliente


# =====================================================================
# NOVO CONTRATO MENSAL
# =====================================================================


class NovoContratoMensal(ctk.CTkFrame):
    """Formulário de criação de um contrato de arrendamento mensal."""

    def __init__(
        self, master, controlador, unidade_id=None, lugar_id=None,
        ao_criar=None,
    ):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador
        # Chamado depois de criar o contrato (v1.11.1): o popup passa o
        # seu `_fechar`, que fecha e atualiza a lista. Sem ele, o
        # formulário limpa-se para o próximo registo, como antes.
        self.ao_criar = ao_criar
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
        self.combo_unidade = componentes.Seletor(
            corpo,
            values=[""],
            command=self._ao_escolher_unidade,
        )
        self.combo_unidade.grid(row=0, column=1, sticky="ew", pady=6)

        self._linha(corpo, 1, "Lugar (opcional)")
        self.combo_lugar = componentes.Seletor(corpo, values=["Nenhum"])
        self.combo_lugar.grid(row=1, column=1, sticky="ew", pady=6)

    def _montar_cartao_cliente(self):
        corpo = self._criar_cartao("Cliente")

        self._linha(corpo, 0, "Cliente *")

        # Bloco cliente: dropdown + botão "+ Novo cliente" ao lado.
        bloco = ctk.CTkFrame(corpo, fg_color="transparent")
        bloco.grid(row=0, column=1, sticky="ew", pady=6)
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
            corpo,
            placeholder_text=(
                " Manter vazio para registrar o dia "
                f"{config.DIA_VENCIMENTO}"
            ),
        )
        self.campo_dia_vencimento.grid(row=1, column=1, sticky="ew", pady=6)

        self._linha(corpo, 2, "Renda calculada")
        self.rotulo_renda_calculada = ctk.CTkLabel(
            corpo,
            text="(escolhe a unidade)",
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
            corpo, placeholder_text="opcional, só se a renda for diferente"
        )
        self.campo_motivo_renda.grid(row=4, column=1, sticky="ew", pady=6)

        self._linha(corpo, 5, "Responsável do desconto")
        self.combo_responsavel = componentes.Seletor(
            corpo, values=["Nenhum"]
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
        ] or ["Sem unidades mensais"]
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
        ] or ["Sem clientes"]
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
        nomes = ["Nenhum"] + [
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
            self.combo_lugar.configure(values=["Nenhum"])
            self.combo_lugar.set("Nenhum")
            return

        self.unidade_selecionada = self.unidades_mensais[indice]
        self.rotulo_renda_calculada.configure(
            text=_formatar_valor(self.unidade_selecionada["preco_base"])
        )
        self._recarregar_lugares()

    def _recarregar_lugares(self):
        self.lugares_da_unidade = []
        opcoes = ["Nenhum"]

        if self.unidade_selecionada is None:
            self.combo_lugar.configure(values=opcoes)
            self.combo_lugar.set(opcoes[0])
            return

        for quarto in unidades.listar_quartos(
            unidade_id=self.unidade_selecionada["id"]
        ):
            for lugar in unidades.listar_lugares(quarto_id=quarto["id"]):
                ocupantes = contratos.ocupantes_mensal(
                    self.unidade_selecionada["id"], lugar["id"]
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
        if self.ao_criar is not None:
            self.ao_criar()
            return
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
            ao_criar=self._fechar,
        ).pack(fill="both", expand=True)

    def _fechar(self):
        """Fecha o popup e atualiza a lista de quem o abriu — ao
        carregar no X e depois de criar o contrato."""
        self.tela_lista._recarregar()
        self.destroy()
