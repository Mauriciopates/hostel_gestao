"""Ecrãs de Contratos e Reservas: criação de um contrato de
arrendamento mensal (NovoContratoMensal), registo de uma reserva
Airbnb (NovaReservaAirbnb, 07/09/2026 — ver docstring da própria
classe) e listagem das ocupações já existentes, mensais e Airbnb
(ListaContratosMensais / ListaReservasAirbnb, com botão fixo "+
Novo Contrato" / "+ Nova Reserva Airbnb" e popup, ver docstring de
_ListaOcupacoesBase).

Só fala com os módulos de negócio (unidades, clientes, responsaveis,
contratos, validacoes) — nunca com repositorio diretamente, mesma
disciplina de gui/gui_unidades.py.

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

8. NovaReservaAirbnb (07/09/2026): mockup (imagem, sem código real)
   validado com o aluno antes de codar, mesmo padrão de botão fixo
   + popup já fechado em "Contrato Mensal". Duas perguntas feitas ao
   aluno (AskUserQuestion) sobre pontos sem convenção prévia — ambas
   respondidas com a opção recomendada:
   - Recalcular o "Preço calculado" ao sair do campo de data
     (<FocusOut>, só quando as duas datas já estão preenchidas e
     válidas) — não há aqui um combo único (como a Unidade, no
     mensal) que dispare um evento de recálculo.
   - Combo "Cliente" já vem pré-selecionado com o primeiro da lista
     (mesmo comportamento de NovoContratoMensal), em vez de vazio.
   Ver a docstring da própria classe para as restantes decisões
   (sem "Lugar", sem "Nacionalidade"/"Data de nascimento").
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


def _formatar_data(valor):
    """Formata uma date para dd/mm/aaaa — "em aberto" quando None
    (contrato mensal ainda ativo, sem data de fim marcada).
    """
    if valor is None:
        return "em aberto"
    return valor.strftime("%d/%m/%Y")


def _identificar_unidade(unidade, unidade_id):
    """Devolve "nome (ID)" para mostrar num cartão de ocupação, ou só
    o ID se a unidade não existir — mesma convenção de
    cli.py:_identificar_unidade (decisão 8 de
    Pendencias_Antes_v1.0.0.txt: o nome sozinho não chega para
    rastrear, os ecrãs precisam também do código).
    """
    if unidade is None:
        return unidade_id
    return f"{unidade['nome']} ({unidade['id']})"


def _identificar_cliente(cliente, cliente_id):
    """Mesma ideia de `_identificar_unidade`, para clientes."""
    if cliente is None:
        return cliente_id
    return f"{cliente['nome']} ({cliente['id']})"


def _colocar_no_topo(janela):
    """Traz um popup para a frente da janela principal — mesma
    função de gui/gui_clientes.py e gui/gui_propriedades.py, repetida
    aqui porque cada módulo da GUI já a define localmente (não há,
    ainda, um sítio comum para ela em componentes.py).
    """
    janela.after(
        10, lambda: (janela.lift(), janela.focus_force(), janela.grab_set())
    )


class NovoContratoModal(ctk.CTkToplevel):
    """Popup com o formulário de Novo Contrato Mensal — 07/09/2026,
    substituindo o item "Novo Contrato Mensal" que a barra lateral
    tinha antes (decisão do aluno: ficava parecido demais com
    "Contrato Mensal", a lista; ao mover para um botão fixo dentro
    da própria lista, deixa de haver os dois nomes lado a lado).

    Reaproveita a classe NovoContratoMensal tal e qual — ela já traz
    o seu próprio cabeçalho, cartões e botão "Criar contrato"; esta
    janela só a encaixa num popup, mesmo padrão de NovoClienteModal/
    EditarClienteModal em gui_clientes.py (CTkToplevel, geometria
    fixa, _colocar_no_topo). Nenhuma lógica do formulário foi
    duplicada nem alterada.

    A lista por trás (`tela_lista`) só recarrega quando a janela
    fecha, não a cada contrato criado — de propósito: o próprio
    NovoContratoMensal já se limpa sozinho depois de cada sucesso
    para permitir criar vários contratos seguidos na mesma unidade
    (decisão da Parte 3 de 06/09/2026); fechar o popup é o sinal de
    "terminei", e é aí que a lista precisa de estar atualizada.
    """

    def __init__(self, tela_lista, unidade_id=None, lugar_id=None):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title("Novo Contrato Mensal")
        self.geometry("640x700")
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


class NovaReservaAirbnb(ctk.CTkFrame):
    """Formulário de registo de uma reserva Airbnb — 07/09/2026,
    mesmo espírito de NovoContratoMensal (cartões, tudo sempre
    visível, popup de erro/sucesso, formulário que se limpa sozinho
    depois de um registo com sucesso), adaptado aos campos de
    `contratos.registar_airbnb`.

    Diferenças de propósito em relação ao Contrato Mensal:

    - Sem "Lugar": o regime Airbnb nunca usa quarto/lugar (decisão
      da Fase 2, item 3 de Decisoes_Pendentes_Fase2.txt) — só o
      mensal usa essa hierarquia para capacidade.
    - Sem "Nacionalidade"/"Data de nascimento": não são campos da
      reserva, são campos da ficha do cliente — já validados
      (incondicionalmente, por agora) em `validacoes.py` quando o
      cliente é criado/atualizado no regime Airbnb.
    - "Preço calculado" não tem um combo único (como a Unidade) que
      dispare um evento — recalcula ao sair de qualquer um dos dois
      campos de data (evento <FocusOut>), quando as duas já estão
      preenchidas e válidas. Mockup validado com o aluno,
      07/09/2026.
    - "Multa calculada" só depende da unidade escolhida (vem de
      unidade["multa_check_in_tardio"]), por isso recalcula já
      junto com a própria escolha da unidade — não precisa de
      esperar por nenhuma data.
    - Cliente já vem pré-selecionado com o primeiro da lista, mesmo
      comportamento do Contrato Mensal (consistência entre os dois
      formulários, decisão do aluno, 07/09/2026).
    """

    def __init__(self, master, controlador, unidade_id=None):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador
        self.unidade_selecionada = None

        componentes.Cabecalho(self, "Nova Reserva Airbnb").pack(fill="x")

        self.area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.area.pack(fill="both", expand=True, padx=24, pady=16)

        self._montar_cartao_unidade_cliente()
        self._montar_cartao_estadia()
        self._montar_cartao_checkin_tardio()
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
        self.combo_cliente = ctk.CTkOptionMenu(corpo, values=["—"])
        self.combo_cliente.grid(row=1, column=1, sticky="ew", pady=6)

    def _montar_cartao_estadia(self):
        corpo = self._criar_cartao("Estadia e valores")

        self._linha(corpo, 0, "Data de entrada *")
        self.campo_data_inicio = ctk.CTkEntry(
            corpo, placeholder_text="dd/mm/aaaa"
        )
        self.campo_data_inicio.grid(row=0, column=1, sticky="ew", pady=6)
        self.campo_data_inicio.bind(
            "<FocusOut>", lambda _evento: self._recalcular_preco()
        )

        self._linha(corpo, 1, "Data de saída *")
        self.campo_data_fim = ctk.CTkEntry(
            corpo, placeholder_text="dd/mm/aaaa"
        )
        self.campo_data_fim.grid(row=1, column=1, sticky="ew", pady=6)
        self.campo_data_fim.bind(
            "<FocusOut>", lambda _evento: self._recalcular_preco()
        )

        self._linha(corpo, 2, "Preço calculado")
        self.rotulo_preco_calculado = ctk.CTkLabel(
            corpo,
            text="— (escolhe as datas)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.rotulo_preco_calculado.grid(row=2, column=1, sticky="ew", pady=6)

        self._linha(corpo, 3, "Preço praticado *")
        self.campo_preco_praticado = ctk.CTkEntry(
            corpo, placeholder_text="0,00"
        )
        self.campo_preco_praticado.grid(row=3, column=1, sticky="ew", pady=6)

        self._linha(corpo, 4, "Motivo da diferença")
        self.campo_motivo_preco = ctk.CTkEntry(
            corpo,
            placeholder_text="opcional — só se o preço for diferente",
        )
        self.campo_motivo_preco.grid(row=4, column=1, sticky="ew", pady=6)

        self._linha(corpo, 5, "Responsável do desconto")
        self.combo_responsavel_preco = ctk.CTkOptionMenu(
            corpo, values=["— Nenhum —"]
        )
        self.combo_responsavel_preco.grid(
            row=5, column=1, sticky="ew", pady=6
        )
        ctk.CTkLabel(
            corpo,
            text="obrigatório quando o preço praticado é inferior ao "
            "calculado",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=6, column=1, sticky="w")

    def _montar_cartao_checkin_tardio(self):
        corpo = self._criar_cartao("Check-in tardio")

        self.checkin_tardio = ctk.CTkCheckBox(corpo, text="Check-in tardio")
        self.checkin_tardio.grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )

        self._linha(corpo, 1, "Hora de chegada")
        self.campo_hora_chegada = ctk.CTkEntry(
            corpo, placeholder_text="hh:mm"
        )
        self.campo_hora_chegada.grid(row=1, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(
            corpo,
            text="obrigatória quando o check-in é tardio",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=2, column=1, sticky="w")

        self._linha(corpo, 3, "Multa calculada")
        self.rotulo_multa_calculada = ctk.CTkLabel(
            corpo,
            text="— (escolhe a unidade)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.rotulo_multa_calculada.grid(row=3, column=1, sticky="ew", pady=6)

        self._linha(corpo, 4, "Multa praticada")
        self.campo_multa_praticada = ctk.CTkEntry(
            corpo, placeholder_text="Enter para a multa calculada"
        )
        self.campo_multa_praticada.grid(row=4, column=1, sticky="ew", pady=6)

        self._linha(corpo, 5, "Responsável do desconto")
        self.combo_responsavel_multa = ctk.CTkOptionMenu(
            corpo, values=["— Nenhum —"]
        )
        self.combo_responsavel_multa.grid(
            row=5, column=1, sticky="ew", pady=6
        )
        ctk.CTkLabel(
            corpo,
            text="obrigatório quando a multa praticada é inferior à "
            "calculada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).grid(row=6, column=1, sticky="w")

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self.area, fg_color="transparent")
        rodape.pack(fill="x", pady=(4, 0))

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
        self.unidades_airbnb = unidades.listar(tipo="airbnb")
        nomes = [
            f"{u['id']} · {u['nome']}" for u in self.unidades_airbnb
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

    def _recarregar_responsaveis(self):
        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel_preco.configure(values=nomes)
        self.combo_responsavel_preco.set(nomes[0])
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
        self._recalcular_preco()

    # -- valores calculados ------------------------------------------

    def _ler_data(self, campo):
        texto = campo.get().strip()
        if not texto:
            return None
        try:
            return datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            return None

    def _recalcular_preco(self):
        if self.unidade_selecionada is None:
            self.rotulo_preco_calculado.configure(text="—")
            return

        data_inicio = self._ler_data(self.campo_data_inicio)
        data_fim = self._ler_data(self.campo_data_fim)

        if data_inicio is None or data_fim is None or data_fim <= data_inicio:
            self.rotulo_preco_calculado.configure(
                text="— (escolhe as datas)"
            )
            return

        preco = contratos.calcular_preco_airbnb(
            self.unidade_selecionada, data_inicio, data_fim
        )
        self.rotulo_preco_calculado.configure(text=_formatar_valor(preco))

    def _atualizar_multa_calculada(self):
        if self.unidade_selecionada is None:
            self.rotulo_multa_calculada.configure(
                text="— (escolhe a unidade)"
            )
            return

        self.rotulo_multa_calculada.configure(
            text=_formatar_valor(
                self.unidade_selecionada["multa_check_in_tardio"]
            )
        )

    # -- submissão ----------------------------------------------------

    def _mostrar_erro(self, texto):
        componentes.mostrar_erro(texto)

    def _mostrar_sucesso(self, texto):
        componentes.mostrar_sucesso(texto)

    def _cliente_escolhido_id(self):
        indice = self.combo_cliente.cget("values").index(
            self.combo_cliente.get()
        )
        return self.clientes_disponiveis[indice]["id"]

    def _id_responsavel(self, combo):
        indice = combo.cget("values").index(combo.get())
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _registar(self):
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

        try:
            ocupacao, _airbnb = contratos.registar_airbnb(
                self.unidade_selecionada["id"],
                self._cliente_escolhido_id(),
                data_inicio,
                data_fim,
                preco_praticado,
                responsavel_desconto_preco_id=self._id_responsavel(
                    self.combo_responsavel_preco
                ),
                check_in_tardio=check_in_tardio,
                hora_chegada=hora_chegada,
                multa_praticada=multa_praticada,
                responsavel_desconto_multa_id=self._id_responsavel(
                    self.combo_responsavel_multa
                ),
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
            f"Reserva registada com sucesso: {ocupacao['id']}{aviso}"
        )
        self._limpar_formulario()

    def _limpar_formulario(self):
        """Mesma ideia de NovoContratoMensal._limpar_formulario: repõe
        o formulário para o próximo registo, mantendo a unidade
        escolhida (comum registar várias reservas seguidas na mesma
        unidade Airbnb) e recarregando cliente/responsáveis, para já
        refletirem a reserva acabada de criar.
        """
        self.campo_data_inicio.delete(0, "end")
        self.campo_data_fim.delete(0, "end")
        self.campo_preco_praticado.delete(0, "end")
        self.campo_motivo_preco.delete(0, "end")
        self.checkin_tardio.deselect()
        self.campo_hora_chegada.delete(0, "end")
        self.campo_multa_praticada.delete(0, "end")

        self._recarregar_clientes()
        self._recarregar_responsaveis()
        self._recalcular_preco()


class NovaReservaAirbnbModal(ctk.CTkToplevel):
    """Popup com o formulário de Nova Reserva Airbnb — 07/09/2026,
    mesmo padrão de NovoContratoModal (CTkToplevel, geometria fixa,
    _colocar_no_topo, a lista só recarrega quando a janela fecha).

    Ao contrário do NovoContratoModal, não embrulha um formulário já
    existente — NovaReservaAirbnb é construído de raiz nesta mesma
    entrega (contratos.registar_airbnb já existia, mas não havia
    nenhum ecrã de GUI para lá chegar).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title("Nova Reserva Airbnb")
        self.geometry("640x700")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        NovaReservaAirbnb(
            self, controlador=tela_lista.controlador
        ).pack(fill="both", expand=True)

    def _fechar(self):
        self.tela_lista._recarregar()
        self.destroy()


class _ListaOcupacoesBase(ctk.CTkFrame):
    """Base comum a ListaContratosMensais e ListaReservasAirbnb —
    07/09/2026, substitui a antiga ListaOcupacoes (um ecrã só, com
    dropdown de tipo Todos/Mensal/Airbnb misturando os dois regimes)
    por dois itens separados na barra lateral, cada um já filtrado
    por tipo — decisão do aluno: mais direto do que abrir um ecrã e
    ainda ter de escolher o tipo lá dentro.

    Cada subclasse só define `tipo` ("mensal"/"airbnb") e `titulo`
    (cabeçalho do ecrã); o resto — filtros, cartões, Reativar — é
    igual nos dois. `_botao_criar` é um "gancho" que por omissão não
    desenha nada: só ListaContratosMensais o usa, para o botão fixo
    "+ Novo Contrato" (Registar reserva Airbnb ainda não existe).

    Mesmos filtros do CLI (`_listar_ocupacoes`, cli.py) — mostrar
    inativas/encerradas, aviso de documento. Filtro por unidade/
    cliente (que no CLI pede o ID por texto livre) fica de fora: os
    ecrãs da GUI não pedem para escrever IDs à mão, só selecionam
    registos existentes.

    Cada cartão identifica a unidade e o cliente por "nome (ID)"
    (mesma convenção do CLI, decisão 8) e mostra o período, o estado
    (Ativa / Encerrada / Cancelada) e o aviso de documento, quando
    aplicável. Só "Reativar" está ligado — não precisa de formulário,
    só confirmação (mesmo padrão de Clientes/Propriedades). Editar/
    Encerrar/Cancelar ficam para as próximas entregas, cada um com o
    seu modal — decisão de não entregar botões sem ação nenhuma por
    trás, para não confundir o aluno a testar.
    """

    # Strings vazias (não None) de propósito: cada subclasse
    # substitui pelo valor real, e assim o Pylance não acusa
    # falso positivo em `self.titulo.lower()` (str sempre tem
    # `.lower()`; None não).
    tipo: str = ""
    titulo: str = ""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo=self.titulo).pack(fill="x")

        barra = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO)
        barra.pack(fill="x", padx=20, pady=(8, 4))

        self._botao_criar(barra)

        self.mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativas/encerradas",
            variable=self.mostrar_inativas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

        self.combo_aviso = ctk.CTkOptionMenu(
            barra,
            values=["Todos", "Com aviso", "Sem aviso"],
            command=lambda _valor: self._recarregar(),
            width=130,
        )
        self.combo_aviso.set("Todos")
        self.combo_aviso.pack(side="right")

        self.area_lista = ctk.CTkScrollableFrame(
            self, fg_color="transparent"
        )
        self.area_lista.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        self._recarregar()

    # -- gancho para o botão de criação (só ListaContratosMensais) --

    def _botao_criar(self, barra):
        return

    # -- carregamento / atualização ----------------------------------

    def _aviso_selecionado(self):
        return {"Todos": None, "Com aviso": True, "Sem aviso": False}[
            self.combo_aviso.get()
        ]

    def _recarregar(self):
        """Limpa e volta a desenhar a lista inteira — chamada na
        abertura do ecrã, ao mexer nos filtros, depois de reativar
        uma ocupação, e ao fechar o popup de Novo Contrato (mesmo
        princípio de ListaClientes._recarregar).
        """
        for widget in self.area_lista.winfo_children():
            widget.destroy()

        lista = contratos.listar(
            incluir_inativas=self.mostrar_inativas.get(),
            tipo=self.tipo,
            aviso_documento=self._aviso_selecionado(),
        )

        if not lista:
            ctk.CTkLabel(
                self.area_lista,
                text=f"Nenhum(a) {self.titulo.lower()} encontrado(a).",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        for ocupacao in lista:
            self._desenhar_ocupacao(ocupacao)

    # -- desenho -------------------------------------------------------

    def _desenhar_ocupacao(self, ocupacao):
        inativa = not ocupacao["ativo"]

        unidade = unidades.procurar(ocupacao["unidade_id"])
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_unidade = _identificar_unidade(unidade, ocupacao["unidade_id"])
        nome_cliente = _identificar_cliente(cliente, ocupacao["cliente_id"])

        cartao = ctk.CTkFrame(
            self.area_lista,
            corner_radius=tema.RAIO_CARTAO,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
        )
        cartao.pack(fill="x", pady=6)

        linha = ctk.CTkFrame(cartao, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=12)

        bloco_texto = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_texto.pack(side="left", anchor="w")

        cor_titulo = tema.COR_TEXTO_SECUNDARIO if inativa else tema.COR_TEXTO
        ctk.CTkLabel(
            bloco_texto,
            text=f"{ocupacao['id']} · {nome_unidade}",
            text_color=cor_titulo,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(anchor="w")

        periodo = (
            f"{_formatar_data(ocupacao['data_inicio'])} → "
            f"{_formatar_data(ocupacao['data_fim'])}"
        )
        ctk.CTkLabel(
            bloco_texto,
            text=f"{nome_cliente} · {periodo}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(anchor="w")

        bloco_direita = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_direita.pack(side="right")

        if inativa:
            rotulo_estado = (
                "Encerrado" if ocupacao["tipo"] == "mensal" else "Cancelada"
            )
            self._etiqueta(
                bloco_direita,
                rotulo_estado,
                tema.CINZA_INDISPONIVEL,
                tema.TEXTO_INDISPONIVEL,
            )
        else:
            self._etiqueta(
                bloco_direita, "Ativa", tema.VERDE_LIVRE, tema.TEXTO_LIVRE
            )

        if ocupacao["aviso_documento"]:
            self._etiqueta(
                bloco_direita,
                "Doc. a expirar",
                tema.AMARELO_AVISO,
                tema.TEXTO_AVISO,
            )

        if inativa:
            ctk.CTkButton(
                bloco_direita,
                text="Reativar",
                width=80,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color=tema.VERDE,
                hover_color=tema.VERDE,
                command=lambda: self._reativar(ocupacao),
            ).pack(side="left", padx=(10, 0))

    def _etiqueta(self, master, texto, fundo, cor_texto):
        ctk.CTkLabel(
            master,
            text=texto,
            text_color=cor_texto,
            fg_color=fundo,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=110,
            height=22,
        ).pack(side="left", padx=(6, 0))

    # -- ações -----------------------------------------------------------

    def _reativar(self, ocupacao):
        pergunta = f"Reativar a ocupação {ocupacao['id']}?"
        if not componentes.confirmar(pergunta):
            return

        try:
            contratos.reativar(ocupacao["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Ocupação {ocupacao['id']} reativada.")
        self._recarregar()


class ListaContratosMensais(_ListaOcupacoesBase):
    """Lista só os contratos mensais — item "Contrato Mensal" na
    barra lateral. Traz o botão fixo "+ Novo Contrato" (verde,
    decisão do aluno, 07/09/2026), que abre NovoContratoModal por
    cima da própria lista.
    """

    tipo = "mensal"
    titulo = "Contrato Mensal"

    def _botao_criar(self, barra):
        ctk.CTkButton(
            barra,
            text="+ Novo Contrato",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovoContratoModal(self),
        ).pack(side="left")


class ListaReservasAirbnb(_ListaOcupacoesBase):
    """Lista só as reservas Airbnb — item "Reservas Airbnb" na barra
    lateral. Traz o botão fixo "+ Nova Reserva Airbnb" (verde, mesmo
    padrão do "+ Novo Contrato" em ListaContratosMensais, decisão do
    aluno em 07/09/2026), que abre NovaReservaAirbnbModal por cima
    da própria lista.
    """

    tipo = "airbnb"
    titulo = "Reservas Airbnb"

    def _botao_criar(self, barra):
        ctk.CTkButton(
            barra,
            text="+ Nova Reserva Airbnb",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovaReservaAirbnbModal(self),
        ).pack(side="left")
