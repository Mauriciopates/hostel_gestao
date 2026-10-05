"""Ecrã "Reservas Airbnb" (`ListaReservasAirbnb`) e os modais
abertos a partir dele: ações, editar e cancelar."""

from decimal import Decimal, InvalidOperation

import customtkinter as ctk

import datetime

import clientes
import contratos
import prechecking
import responsaveis
import unidades

from gui import componentes, tema
from gui.contratos import gui_cnt_comum
from gui.contratos.gui_cnt_airbnb_nova import NovaReservaAirbnbModal
from gui.gui_prechecking import GerarLinkModal, abrir

# Aliases locais para helpers que vivem em componentes.py (nomes
# antigos com "_", para o corpo não ter de ser reescrito).
_formatar_valor = componentes.formatar_valor
_colocar_no_topo = componentes.colocar_no_topo

# Helpers partilhados dos contratos (nomes públicos em
# gui_cnt_comum) — alias local, mesmo padrão dos gui_est_*.
_formatar_data = gui_cnt_comum.formatar_data
_identificar_unidade = gui_cnt_comum.identificar_unidade
_identificar_cliente = gui_cnt_comum.identificar_cliente


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


# =====================================================================
# RESERVAS AIRBNB — tabela (13/09/2026)
# =====================================================================


_LARGURA_ID_RESERVA = 110
_LARGURA_UNIDADE_RESERVA = 320
_LARGURA_ESTADO_RESERVA = 200
_LARGURA_ACOES_RESERVA = 100
_LARGURA_PRECHECKING = 130

# Pílula da coluna "PRÉ CHECK-IN" (F5): estado → estilo de Etiqueta.
_ESTILO_PRECHECKING = {
    prechecking.SEM_LINK: "info",
    prechecking.LINK_ENVIADO: "azul",
    prechecking.EXPIRADO: "info",
    prechecking.RECEBIDO: "aviso",
    prechecking.IMPORTADO: "livre",
}

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
        "PRÉ CHECK-IN", minimo=_LARGURA_PRECHECKING, alinhamento="centro"
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

        self.combo_aviso = componentes.Seletor(
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

        # Estado do pré check-in de todas as reservas numa só consulta.
        self.estados_prechecking = prechecking.estados(
            o["id"] for o in lista
        )

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

        # Clicar no ID abre o detalhe da reserva (o mesmo do "Gerir",
        # que já mostra a ficha completa).
        self.tabela.colocar(
            linha,
            0,
            componentes.ChipId(
                linha,
                ocupacao["id"],
                ao_clicar=lambda: _AcoesReservaAirbnbModal(self, ocupacao),
                largura=_LARGURA_ID_RESERVA,
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

        estado = self.estados_prechecking.get(
            ocupacao["id"], prechecking.SEM_LINK
        )
        self.tabela.colocar(
            linha,
            3,
            componentes.Etiqueta(
                linha,
                prechecking.ROTULOS_ESTADO[estado],
                _ESTILO_PRECHECKING[estado],
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

        # F5: "Gerar link de pré check-in" só em reservas ativas que
        # ainda não acabaram.
        pode_link = (
            not inativa and ocupacao["data_fim"] >= datetime.date.today()
        )
        altura = 240 if inativa else (310 if pode_link else 270)

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
            if pode_link:
                self._botao(
                    "Gerar link de pré check-in",
                    text_color=tema.AZUL_PRINCIPAL,
                    hover_color=tema.ID_CHIP_FUNDO,
                    acao=lambda: abrir(
                        GerarLinkModal, self.tela_lista, ocupacao,
                        self._nome_cliente(ocupacao),
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

    @staticmethod
    def _nome_cliente(ocupacao):
        cliente = clientes.procurar(ocupacao["cliente_id"])
        return cliente["nome"] if cliente else ocupacao["cliente_id"]

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
    praticado (e responsável do desconto), e — só quando a reserva
    teve check-in tardio — Multa praticada (e responsável do desconto
    da multa). O campo "Motivo da diferença" saiu a 28/09/2026: era
    pedido mas nunca gravado (a reserva Airbnb não tem onde o
    guardar; a decisão 18 identifica o desconto pelo responsável).

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

        self._linha(corpo, 3, "Responsável do desconto")
        self.combo_responsavel_preco = componentes.Seletor(
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
            self.combo_responsavel_multa = componentes.Seletor(
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
