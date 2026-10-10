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
  o rótulo ficava sempre a dizer "(escolhe as datas)" mesmo
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

ALTERAÇÕES 26/09/2026 (divisão em ficheiros):

- O antigo `gui_contratos.py` (3 560 linhas) foi dividido por
  regime e por tarefa: gui_cnt_mensal_novo, gui_cnt_mensal_lista
  (este — guarda o histórico de alterações do ficheiro antigo),
  gui_cnt_airbnb_nova, gui_cnt_airbnb_confirm,
  gui_cnt_airbnb_lista e gui_cnt_comum (helpers). Classes
  movidas sem alterações.
"""

import datetime
import os
import subprocess
import sys

import customtkinter as ctk

import clientes
import configuracoes
import contratos
import impressao
import propriedades
import unidades

from gui import componentes, tema
from gui.contratos import gui_cnt_comum
from gui.contratos.gui_cnt_mensal_novo import NovoContratoModal

# Aliases locais para helpers que vivem em componentes.py (nomes
# antigos com "_", para o corpo não ter de ser reescrito).
_colocar_no_topo = componentes.colocar_no_topo

# Helpers partilhados dos contratos (nomes públicos em
# gui_cnt_comum) — alias local, mesmo padrão dos gui_est_*.
_formatar_data = gui_cnt_comum.formatar_data
_identificar_unidade = gui_cnt_comum.identificar_unidade
_identificar_cliente = gui_cnt_comum.identificar_cliente


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

        self.campo_data_fim = componentes.CampoData(self)
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

        # Lê as configurações da BD (podem ter sido alteradas na GUI),
        # com o mesmo fallback automático que o
        # `contratos.avisos_encerramento` usa para decidir se o aviso
        # se aplica. Sem isto, o texto entre parênteses ficava
        # dessincronizado do valor real (bug apanhado pelo aluno,
        # 20/09/2026).
        duracao_minima = configuracoes.obter_int(
            "operacao.duracao_minima_meses"
        )
        aviso_previo = configuracoes.obter_int("operacao.aviso_previo_dias")

        if avisos["duracao_abaixo_minima"]:
            linhas.append(
                f"⚠  Duração abaixo do mínimo "
                f"({duracao_minima} meses)"
            )

        if avisos["aviso_previo_insuficiente"]:
            linhas.append(
                f"⚠  Aviso prévio insuficiente "
                f"({aviso_previo} dias)"
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


class ListaContratosMensais(ctk.CTkFrame):
    """Lista dos contratos mensais — ecrã "Contrato Mensal" da barra
    lateral.

    Em tabela desde 13/09/2026. Colunas: ID, NOME UNIDADE, NOME DO
    CLIENTE, DATA, STATUS, AÇÕES. Cada linha tem um único botão
    "Gerir", que abre `_AcoesContratoModal`.
    """

    def __init__(self, master, controlador, novo_contrato=None):
        """`novo_contrato` (opcional): {"unidade_id", "lugar_id"} —
        abre logo o popup "Novo Contrato Mensal" por cima da lista,
        já preenchido. Usado pela Planta de Lugares (10/10/2026: o
        contrato deixou de abrir em ecrã inteiro e, ao ser criado,
        volta-se a esta lista).
        """
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

        if novo_contrato is not None:
            # Depois de a lista estar no ecrã: o popup é `transient`
            # dela e tem de abrir por cima, não por trás.
            self.after(
                50,
                lambda: NovoContratoModal(
                    self,
                    unidade_id=novo_contrato.get("unidade_id"),
                    lugar_id=novo_contrato.get("lugar_id"),
                ),
            )

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

        # Clicar no ID abre a ficha (só leitura) do contrato.
        self.tabela.colocar(
            linha,
            0,
            componentes.ChipId(
                linha,
                ocupacao["id"],
                ao_clicar=lambda: self._abrir_ficha(ocupacao),
                largura=110,
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

    def _abrir_ficha(self, ocupacao):
        """Ficha do contrato: o que o "Gerir" não mostra (valores,
        caução, vencimento, motivo de encerramento)."""
        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        mensal = contratos.detalhes_mensal(ocupacao["id"]) or {}

        def texto(chave):
            return str(mensal.get(chave) or "—")

        pares = [
            (
                "Unidade",
                f"{unidade['nome'] if unidade else '—'} "
                f"({ocupacao['unidade_id']})",
            ),
            (
                "Cliente",
                f"{cliente['nome'] if cliente else '—'} "
                f"({ocupacao['cliente_id']})",
            ),
            ("Lugar", ocupacao["lugar_id"] or "—"),
            ("Início", componentes.formatar_data(ocupacao["data_inicio"])),
            ("Fim", componentes.formatar_data(ocupacao["data_fim"])),
            (
                "Renda calculada",
                componentes.formatar_valor(mensal.get("renda_calculada")),
            ),
            (
                "Renda praticada",
                componentes.formatar_valor(mensal.get("renda_praticada")),
            ),
            ("Caução", componentes.formatar_valor(mensal.get("caucao"))),
            ("Dia de vencimento", texto("dia_vencimento")),
            ("Estado", "Ativo" if ocupacao["ativo"] else "Encerrado"),
        ]
        if not ocupacao["ativo"]:
            pares.append(
                ("Motivo de encerramento", texto("motivo_encerramento"))
            )

        componentes.FichaModal(
            self,
            titulo=f"Contrato {ocupacao['id']}",
            subtitulo="Contrato mensal",
            pares=pares,
        )

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
    """Popup intermédio do "Imprimir contrato" — mostra o senhorio
    e pede o local, antes de gerar o PDF.

    10/10/2026: o senhorio deixou de ser escolhido aqui entre os
    responsáveis — passou a ser o da propriedade (campo "Senhorio"
    na ficha da propriedade). Aqui só se mostra, para confirmar.
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
        propriedade = (
            propriedades.procurar(unidade["propriedade_id"])
            if unidade
            else None
        )
        self.nome_senhorio = (
            propriedade.get("senhorio_nome") if propriedade else ""
        ) or ""
        self.nome_propriedade = propriedade["nome"] if propriedade else ""

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

        ctk.CTkLabel(
            self,
            text=self.nome_senhorio or "Sem senhorio na propriedade",
            text_color=(
                tema.COR_TEXTO if self.nome_senhorio else tema.TEXTO_ERRO
            ),
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text=(
                f"Vem da propriedade {self.nome_propriedade} "
                "(Propriedades → Editar → Senhorio). Aparece no PDF "
                'como "Primeiro Contraente".'
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

    def _gerar_pdf(self):
        if not self.nome_senhorio:
            componentes.mostrar_erro(
                f"A propriedade {self.nome_propriedade} não tem senhorio "
                "preenchido.\n\nPreenche-o em Propriedades → Editar "
                "antes de imprimir o contrato."
            )
            return

        local = self.campo_local.get().strip()

        if not local:
            componentes.mostrar_erro(
                "Escreve o local (cidade) onde o contrato é assinado."
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
