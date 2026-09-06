"""Ecrã de criação de um contrato de arrendamento mensal.

Só fala com os módulos de negócio (unidades, clientes, responsaveis,
contratos, validacoes) — nunca com repositorio diretamente, mesma
disciplina de gui/unidades.py.

Mockup validado com o aluno em 06/09/2026 (capturas
screenshot_contrato_vazio.png / screenshot_contrato_preenchido.png,
fluxo completo testado com Xvfb + contratos.criar_mensal real e
dados falsos). Decisões tomadas nessa validação:

1. Todos os campos ficam sempre visíveis — não há campos que
   aparecem/desaparecem consoante o que se escreve nos outros. A
   obrigatoriedade condicional (ex.: responsável do desconto só é
   exigido quando a renda praticada é menor que a calculada) só é
   validada ao submeter.

2. Confirmação do desconto na renda: ao contrário do CLI (que
   pergunta "confirmas o desconto?" antes de pedir o responsável),
   aqui escolher o responsável no dropdown já vale como confirmação
   — não há uma pergunta extra.

3. Confirmação da caução: como este caso não tem responsável
   associado (validacoes.validar_caucao só devolve um sinal
   True/False de "exige confirmação"), usa-se uma caixa de
   confirmação ("Confirmo esta caução") que só bloqueia a criação
   quando é mesmo necessário — equivalente ao confirmar() do CLI.

4. O dropdown de lugar mostra o estado ao vivo (livre/parcial/
   ocupado, com contagem) recalculado sempre que a unidade muda.
   Não usa o estado "reservado" da Planta de Lugares — aqui só
   interessa saber se ainda cabe mais gente.

5. Fecha o ciclo com a Planta de Lugares (unidades.PlantaLugares):
   o construtor aceita 'unidade_id' e 'lugar_id' opcionais, para ser
   aberto já pré-preenchido a partir de um clique numa caixa livre/
   reservada da planta. Essa ligação (o próprio clique a abrir este
   ecrã) fica para quando os ecrãs estiverem ligados ao mesmo
   controlador/menu — não é feita aqui.

6. Erros de validação/negócio (contratos.criar_mensal a levantar
   ValueError, ou erro de formato num campo) e a confirmação de
   sucesso aparecem num popup nativo (componentes.mostrar_erro/
   mostrar_sucesso — ícone, mensagem, botão OK), não numa legenda no
   ecrã — decisão do aluno, 06/09/2026, ao testar este ecrã pela
   primeira vez. É a convenção a partir de agora para toda a
   interface gráfica, não só aqui; não há legenda nenhuma no rodapé,
   só o botão "Criar contrato".

7. Depois de criar com sucesso, o formulário limpa-se sozinho
   (_limpar_formulario) para o próximo registo — o aluno reparou
   que os campos ficavam com os valores do contrato anterior depois
   de fechar o popup. Mantém a unidade escolhida (comum criar vários
   contratos seguidos na mesma unidade); cliente, datas, valores e a
   confirmação da caução voltam ao vazio, e lugar/cliente/responsável
   são recarregados, para já refletirem o contrato acabado de criar.
"""

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


def _formatar_valor(valor):
    return f"{valor:.2f} €".replace(".", ",")


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
        self.area.pack(fill="both", expand=True, padx=24, pady=16)

        self._montar_cartao_unidade()
        self._montar_cartao_cliente()
        self._montar_cartao_contrato()
        self._montar_rodape()

        self._recarregar_unidades(unidade_id)
        self._recarregar_clientes()
        self._recarregar_responsaveis()

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
        self.combo_cliente = ctk.CTkOptionMenu(corpo, values=["—"])
        self.combo_cliente.grid(row=0, column=1, sticky="ew", pady=6)

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
        self.unidades_mensais = unidades.listar(tipo="mensal")
        nomes = [
            f"{u['id']} · {u['nome']}" for u in self.unidades_mensais
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
        contrato com sucesso, para o próximo registo — sem isto, os
        campos ficavam com os valores do contrato anterior (apanhado
        pelo aluno a testar, não era intencional). Mantém a unidade
        escolhida (é comum criar vários contratos seguidos na mesma
        unidade); tudo o resto volta ao valor por omissão, e as
        listas de lugares/clientes/responsáveis são recarregadas,
        para refletirem o contrato que acabou de ser criado (ex.:
        o lugar escolhido já aparece com um ocupante a mais).
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
