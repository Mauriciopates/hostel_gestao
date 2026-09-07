"""Ecrã "Clientes": lista os clientes (mensais e Airbnb) com o
estado de cada um (ativo/inativo, incompleto, anonimizado) e ações
de criar/editar/desativar/reativar/anonimizar.

Escolhido pelo aluno como o quinto ecrã da GUI, 06/09/2026, entre 4
opções apresentadas — o maior buraco a fechar: para testar o Novo
Contrato Mensal era preciso criar clientes primeiro pelo CLI.

Validado por mockup (Xvfb + CustomTkinter real, dados falsos, sem
tocar no MySQL do aluno) — cinco capturas (lista, novo cliente
vazio, modal de anonimização, lista com inativos, edição de um
cliente existente) — e por um teste de submissão real, com
`clientes.py`/`responsaveis.py` reais e só o `repositorio.py`
monkey-patchado: 10 cenários (recusa de mensal sem NIF, recusa de
NIF duplicado, data em formato inválido, criação incompleta com
aviso, criação completa sem aviso, edição completando os campos em
falta, anonimização sem/com responsável, desativar com confirmação,
reativar recusado por NIF já usado) — TODOS OS TESTES PASSARAM.

Decisões de desenho:

1. 'regime' NÃO é campo do cliente (clientes.criar/atualizar já não
   o guardam) — serve só para saber, no momento da chamada, que
   conjunto de campos é obrigatório (decisão de 26/08: mensal exige
   NIF/morada/estado civil, Airbnb exige nacionalidade; nome, tipo e
   número de documento, data de nascimento e validade do documento
   são sempre obrigatórios, nos dois regimes). Por isso o formulário
   tem sempre um seletor "Regime" (Mensal/Airbnb) — mesma posição do
   CLI, logo a seguir ao número de documento — mesmo ao editar, onde
   o cliente já existe sem regime gravado: o seletor arranca em
   "Mensal" se o cliente já tiver NIF preenchido (sinal de que foi
   criado nesse regime), senão "Airbnb" — só um valor por omissão,
   sempre alterável antes de guardar. Pergunta feita ao aluno em
   06/09/2026 sem resposta; assumida esta opção (a recomendada, em
   vez de arrancar sempre em "Airbnb" como o CLI faz por omissão em
   `atualizar()`) — a rever se o aluno preferir a outra.

2. Todos os campos sempre visíveis, obrigatoriedade só validada ao
   submeter — mesma convenção fixada em Novo Contrato Mensal (parte
   3), reforçada em Propriedades e Unidades (parte 4).

3. Formulário com muitos campos (13, mais o seletor de Regime) — em
   vez do padrão "rótulo em cima, campo em baixo" dos modais mais
   simples de Propriedades e Unidades, uso o mesmo padrão do cartão
   de Novo Contrato Mensal (grelha rótulo-à-esquerda/campo-à-
   direita, dentro de um CTkScrollableFrame, rodapé de botões fixo
   por fora) — cabe melhor num modal desta dimensão.

4. Erro e sucesso sempre por popup nativo (componentes.mostrar_erro/
   mostrar_sucesso), convenção já fixada nas partes 3 e 4. Sucesso
   ao criar inclui o aviso de incompleto, quando aplicável (mesmo
   texto que o CLI imprime): "Cliente criado com sucesso: CLI-XXX
   (incompleto — verifica os campos em falta)".

5. Anonimização — operação irreversível (decisão 8, RGPD secção 6):
   modal próprio (_AnonimizarModal), mesmo padrão do
   _ConfirmarForcarModal de Propriedades e Unidades — mensagem de
   aviso + dropdown de Responsável obrigatório + botão vermelho
   "Anonimizar (irreversível)". A data usa sempre a data de hoje, sem
   campo próprio — decisão do aluno, 06/09/2026 (o CLI permite
   escolher outra data; não é exposto na GUI). Botão só aparece em
   clientes ainda não anonimizados (ativos ou inativos — a regra de
   negócio permite anonimizar um cliente já inativo).

6. Um cliente anonimizado não pode ser editado nem reativado
   (clientes.atualizar/reativar recusam) — por isso o cartão de um
   cliente anonimizado não mostra nenhum botão de ação, só a
   etiqueta "Anonimizado".

7. Etiquetas do cartão: "Anonimizado" (cinza indisponível) tem
   prioridade sobre "Incompleto" (amarelo aviso) — um cliente
   anonimizado fica sempre incompleto=True internamente (dados
   apagados), mas mostrar as duas seria redundante.

8. Filtro de completude (Todos/Incompletos/Completos), ao lado de
   "Mostrar inativos" — mesmas duas opções de filtro que
   `_listar_clientes` já tem no CLI (decisão 11: tem de existir
   listagem de incompletos, senão o aviso não produz efeito).

9. Depois de testar no PC real (06/09/2026), o aluno pediu três
   ajustes, com pesquisa prévia obrigatória antes de codar (pedido
   explícito: "antes de codar me traga os resultados e pergunte se
   tiver que tomar decisões"):

   a) Modal de Novo/Editar Cliente mais largo (460→620) — com 13
      campos, mais o seletor de Regime e o campo composto de
      Nacionalidade, ficava apertado.

   b) Formato de email validado: tem de ter um nome, um "@" e um
      domínio com pelo menos um ponto (ex.: nome@dominio.com) — a
      mesma regra simples que a generalidade dos sistemas usa para
      apanhar erros de digitação óbvios (não confirma que a caixa
      de correio existe de facto). Pergunta feita ao aluno: onde
      aplicar a regra — só respondeu "Só no ecrã Clientes
      (recomendado por agora)", por isso fica só aqui, sem tocar em
      validacoes.py/clientes.py/cli.py. O email continua opcional
      (decisão 11 antiga): a regra só corre quando o campo não está
      vazio.

   c) Nacionalidade com seletor: pesquisadas as bibliotecas
      pycountry, babel, country_converter e pycountry-convert —
      nenhuma traz gentílicos em português (só nomes de país, ex.
      "Portugal", nunca "Portuguesa"), por isso nenhuma serve para
      preencher automaticamente uma lista de nacionalidades como as
      que aparecem num documento de identificação. Pergunta feita
      ao aluno — respondeu "Lista curta + 'Outra' (recomendado)" —
      por isso o campo passa a ser um seletor com uma lista curta
      de nacionalidades comuns mais "Outra", por cima de uma caixa
      de texto: escolher um valor da lista preenche a caixa; a caixa
      continua a ser o valor realmente gravado — o seletor é só um
      atalho.

   d) Ajuste ao ponto (c), pedido pelo aluno ao ver uma captura de
      ecrã do resultado ("SÓ APARECER QUANDO TIVER QUE COLOCAR
      OUTRO, FICA OCULTO PARA NAO PARECER DOIS BRASILEIRA"): a caixa
      de texto deixa de estar sempre visível quando o valor vem da
      lista — mostrar "Brasileira" no seletor E na caixa por baixo
      era redundante. Agora a caixa começa ESCONDIDA; escolher uma
      nacionalidade da lista preenche-a mas mantém-na escondida (só
      o seletor mostra o valor); só escolher "Outra" é que a revela,
      vazia, para escrita livre. Exceção pontual à decisão 2 do
      módulo ("todos os campos sempre visíveis") — aceite porque
      aqui não há obrigatoriedade condicional nenhuma escondida, é
      só um valor mostrado em duplicado a menos.

Segue a mesma disciplina de camadas do resto da GUI (decisão 7): só
fala com `clientes` e `responsaveis` — nunca com `repositorio`
diretamente.
"""

import datetime
import re

import customtkinter as ctk

import clientes
import responsaveis
import validacoes
from . import componentes
from . import tema


NACIONALIDADES = (
    "Portuguesa",
    "Brasileira",
    "Espanhola",
    "Francesa",
    "Alemã",
    "Britânica",
    "Italiana",
    "Neerlandesa",
    "Belga",
    "Suíça",
    "Austríaca",
    "Irlandesa",
    "Polaca",
    "Sueca",
    "Norueguesa",
    "Dinamarquesa",
    "Russa",
    "Ucraniana",
    "Norte-americana",
    "Canadiana",
    "Mexicana",
    "Chinesa",
    "Japonesa",
    "Sul-coreana",
    "Indiana",
    "Australiana",
    "Angolana",
    "Moçambicana",
    "Cabo-verdiana",
)
NACIONALIDADE_PLACEHOLDER = "— Escolher —"
OUTRA_NACIONALIDADE = "Outra (escrever ao lado)"

_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _formatar_data(valor):
    """Formata uma date para dd/mm/aaaa, para pré-preencher um campo
    de edição — "" quando o valor ainda não existe (novo cliente
    sem data escolhida ainda).
    """
    if valor is None:
        return ""
    return valor.strftime("%d/%m/%Y")


def _ler_data(texto, nome_campo):
    """Converte dd/mm/aaaa em date. data_nascimento e
    validade_documento são sempre obrigatórias, nos dois regimes
    (validacoes.validar_cliente) — por isso, ao contrário do dia de
    vencimento em gui/gui_contratos.py, não há aqui um caminho "vazio
    fica por omissão".
    """
    texto = texto.strip()

    if not texto:
        raise ValueError(f"{nome_campo} é obrigatória.")

    try:
        return datetime.datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"{nome_campo} inválida (usa dd/mm/aaaa).")


def _email_valido(email):
    """Formato simples de email (regra pedida pelo aluno, 06/09/2026,
    só para o ecrã Clientes): tem de ter uma parte antes do "@", um
    "@", e um domínio com pelo menos um ponto — a mesma regra base
    que a generalidade dos sistemas usa para apanhar erros de
    digitação óbvios (ex. falta do "@" ou do domínio). Não é uma
    verificação RFC 5322 completa, nem confirma que a caixa de
    correio existe de facto.
    """
    return bool(_PADRAO_EMAIL.match(email))


def _colocar_no_topo(janela):
    """Traz um popup para a frente da janela principal — mesma
    função de gui/gui_propriedades.py, repetida aqui porque cada módulo
    da GUI já a define localmente (não há, ainda, um sítio comum
    para ela em componentes.py).
    """
    janela.after(
        10, lambda: (janela.lift(), janela.focus_force(), janela.grab_set())
    )


class ListaClientes(ctk.CTkFrame):
    """Ecrã principal: lista os clientes, com ações de criar/editar/
    desativar/reativar/anonimizar.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Clientes").pack(fill="x")

        barra = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO)
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.mostrar_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativos",
            variable=self.mostrar_inativos,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

        self.combo_completude = ctk.CTkOptionMenu(
            barra,
            values=["Todos", "Incompletos", "Completos"],
            command=lambda _valor: self._recarregar(),
            width=130,
        )
        self.combo_completude.set("Todos")
        self.combo_completude.pack(side="right")

        self.area_lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.area_lista.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        rodape = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO, height=48)
        rodape.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkButton(
            rodape,
            text="+ Novo Cliente",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=lambda: NovoClienteModal(self),
        ).pack(side="left")

        self._recarregar()

    # -- carregamento / atualização ------------------------------------

    def _incompleto_selecionado(self):
        return {"Todos": None, "Incompletos": True, "Completos": False}[
            self.combo_completude.get()
        ]

    def _recarregar(self):
        """Limpa e volta a desenhar a lista inteira — chamada na
        abertura do ecrã, ao mexer nos filtros, e depois de qualquer
        criação/edição/desativação/reativação/anonimização (mesmo
        princípio de ListaPropriedades._recarregar).
        """
        for widget in self.area_lista.winfo_children():
            widget.destroy()

        lista = clientes.listar(
            incluir_inativos=self.mostrar_inativos.get(),
            incompleto=self._incompleto_selecionado(),
        )

        if not lista:
            ctk.CTkLabel(
                self.area_lista,
                text="Ainda não há clientes cadastrados.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        for cliente in lista:
            self._desenhar_cliente(cliente)

    # -- desenho ---------------------------------------------------------

    def _desenhar_cliente(self, cliente):
        inativo = not cliente["ativo"]

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

        nome = cliente["nome"] + ("  (inativo)" if inativo else "")
        cor_nome = tema.COR_TEXTO_SECUNDARIO if inativo else tema.COR_TEXTO
        ctk.CTkLabel(
            bloco_texto,
            text=nome,
            text_color=cor_nome,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(anchor="w")

        if cliente["anonimizado"]:
            subtitulo = "Dados pessoais removidos (anonimizado)"
        else:
            subtitulo = (
                f"{cliente['tipo_documento']} {cliente['numero_documento']}"
            )
            if cliente["nif"]:
                subtitulo += f" · NIF {cliente['nif']}"

        ctk.CTkLabel(
            bloco_texto,
            text=subtitulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(anchor="w")

        bloco_direita = ctk.CTkFrame(linha, fg_color="transparent")
        bloco_direita.pack(side="right")

        if cliente["anonimizado"]:
            self._etiqueta(
                bloco_direita,
                "Anonimizado",
                tema.CINZA_INDISPONIVEL,
                tema.TEXTO_INDISPONIVEL,
            )
            return

        if cliente["incompleto"]:
            self._etiqueta(
                bloco_direita,
                "Incompleto",
                tema.AMARELO_AVISO,
                tema.TEXTO_AVISO,
            )

        botoes = ctk.CTkFrame(bloco_direita, fg_color="transparent")
        botoes.pack(side="left", padx=(10, 0))

        if inativo:
            ctk.CTkButton(
                botoes,
                text="Reativar",
                width=80,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color=tema.VERDE,
                hover_color=tema.VERDE,
                command=lambda: self._reativar(cliente),
            ).pack(side="left", padx=(0, 6))
        else:
            ctk.CTkButton(
                botoes,
                text="Desativar",
                width=80,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                command=lambda: self._desativar(cliente),
            ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            botoes,
            text="Editar",
            width=70,
            height=26,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=lambda: EditarClienteModal(self, cliente),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            botoes,
            text="Anonimizar",
            width=90,
            height=26,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=lambda: _AnonimizarModal(self, cliente),
        ).pack(side="left")

    def _etiqueta(self, master, texto, fundo, cor_texto):
        ctk.CTkLabel(
            master,
            text=texto,
            text_color=cor_texto,
            fg_color=fundo,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=90,
            height=22,
        ).pack(side="left")

    # -- ações -------------------------------------------------------------

    def _desativar(self, cliente):
        pergunta = f"Desativar o cliente {cliente['nome']} ({cliente['id']})?"
        if not componentes.confirmar(pergunta):
            return

        try:
            clientes.desativar(cliente["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Cliente {cliente['nome']} desativado.")
        self._recarregar()

    def _reativar(self, cliente):
        try:
            clientes.reativar(cliente["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Cliente {cliente['nome']} reativado.")
        self._recarregar()


class _FormularioCliente(ctk.CTkToplevel):
    """Base comum a NovoClienteModal e EditarClienteModal — monta os
    13 campos + o seletor de Regime, sempre na mesma ordem do CLI
    (_criar_cliente/_atualizar_cliente). As duas subclasses só
    diferem no título, na pré-preenchida dos campos e no que
    acontece ao guardar.
    """

    def __init__(self, tela_lista, titulo):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title(titulo)
        self.geometry("620x700")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 8))

        area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=20)

        cartao = ctk.CTkFrame(
            area,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", pady=(0, 12))

        self.corpo = ctk.CTkFrame(cartao, fg_color="transparent")
        self.corpo.pack(fill="x", padx=16, pady=14)
        self.corpo.grid_columnconfigure(0, weight=0)
        self.corpo.grid_columnconfigure(1, weight=1)
        self._linha_atual = 0

        self.campo_nome = self._campo_texto("Nome *")
        self.combo_tipo_documento = self._campo_dropdown(
            "Tipo de documento *", validacoes.TIPOS_DOCUMENTO
        )
        self.campo_numero_documento = self._campo_texto(
            "Número de documento *"
        )
        self.combo_regime = self._campo_dropdown(
            "Regime (define a obrigatoriedade abaixo) *",
            ["Mensal", "Airbnb"],
        )
        self.campo_nif = self._campo_texto("NIF")
        self.campo_email = self._campo_texto("Email")
        self.campo_telefone = self._campo_texto("Telefone")
        self.campo_morada = self._campo_texto("Morada")
        self.campo_nacionalidade, self.combo_nacionalidade = (
            self._campo_nacionalidade()
        )
        self.combo_estado_civil = self._campo_dropdown(
            "Estado civil", validacoes.TIPOS_ESTADO_CIVIL
        )
        self.campo_data_nascimento = self._campo_texto(
            "Data de nascimento *", placeholder="dd/mm/aaaa"
        )
        self.campo_validade_documento = self._campo_texto(
            "Validade do documento *", placeholder="dd/mm/aaaa"
        )
        self.campo_contacto_emergencia = self._campo_texto(
            "Contacto de emergência"
        )

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16, side="bottom")
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
        self.botao_guardar = ctk.CTkButton(
            rodape,
            text="Guardar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        )
        self.botao_guardar.pack(side="right")

    # -- montagem dos campos --------------------------------------------

    def _linha(self, rotulo):
        linha = self._linha_atual
        self._linha_atual += 1

        ctk.CTkLabel(
            self.corpo,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).grid(row=linha, column=0, sticky="w", pady=6, padx=(0, 10))
        return linha

    def _campo_texto(self, rotulo, placeholder=""):
        linha = self._linha(rotulo)
        entrada = ctk.CTkEntry(
            self.corpo,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.grid(row=linha, column=1, sticky="ew", pady=6)
        return entrada

    def _campo_dropdown(self, rotulo, valores):
        linha = self._linha(rotulo)
        combo = ctk.CTkOptionMenu(self.corpo, values=list(valores))
        combo.grid(row=linha, column=1, sticky="ew", pady=6)
        return combo

    def _campo_nacionalidade(self):
        """Campo composto: um seletor com uma lista curta de
        nacionalidades comuns + "Outra", por cima de uma caixa de
        texto — escolher uma nacionalidade da lista preenche a caixa
        E ESCONDE-A (fica só o seletor a mostrar o valor — mostrar
        as duas era redundante, ex. "Brasileira" repetido duas
        vezes; reparado pelo aluno numa captura de ecrã, 06/09/2026);
        escolher "Outra" é que revela a caixa, vazia, para escrita
        livre. A caixa de texto continua a ser o valor realmente
        gravado, o seletor é só um atalho (decisão do aluno,
        06/09/2026 — ver ponto 9c/9d da docstring do módulo).
        """
        linha = self._linha("Nacionalidade")

        bloco = ctk.CTkFrame(self.corpo, fg_color="transparent")
        bloco.grid(row=linha, column=1, sticky="ew", pady=6)
        bloco.grid_columnconfigure(0, weight=1)

        entrada = ctk.CTkEntry(
            bloco,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="Escreve a nacionalidade",
        )
        entrada.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        entrada.grid_remove()  # escondida por omissão, só "Outra" mostra

        combo = ctk.CTkOptionMenu(
            bloco,
            values=(
                [NACIONALIDADE_PLACEHOLDER]
                + list(NACIONALIDADES)
                + [OUTRA_NACIONALIDADE]
            ),
            command=lambda valor: self._ao_escolher_nacionalidade(
                valor, entrada
            ),
        )
        combo.set(NACIONALIDADE_PLACEHOLDER)
        combo.grid(row=0, column=0, sticky="ew")

        return entrada, combo

    def _ao_escolher_nacionalidade(self, valor, campo_entrada):
        if valor == OUTRA_NACIONALIDADE:
            campo_entrada.delete(0, "end")
            campo_entrada.grid()
            campo_entrada.focus_set()
        elif valor == NACIONALIDADE_PLACEHOLDER:
            campo_entrada.grid_remove()
        else:
            campo_entrada.delete(0, "end")
            campo_entrada.insert(0, valor)
            campo_entrada.grid_remove()

    # -- leitura ----------------------------------------------------------

    def _regime_selecionado(self):
        return "mensal" if self.combo_regime.get() == "Mensal" else "airbnb"

    def _ler_campos_comuns(self):
        """Lê e valida (formato, não regra de negócio) os campos
        comuns a criar e atualizar. As datas são as únicas que podem
        levantar ValueError aqui — o resto só é validado pela
        camada de negócio, ao submeter.
        """
        data_nascimento = _ler_data(
            self.campo_data_nascimento.get(), "Data de nascimento"
        )
        validade_documento = _ler_data(
            self.campo_validade_documento.get(), "Validade do documento"
        )

        email = self.campo_email.get().strip()
        if email and not _email_valido(email):
            raise ValueError(
                "Email em formato inválido (esperado algo como "
                "nome@dominio.com)."
            )

        return {
            "nome": self.campo_nome.get(),
            "tipo_documento": self.combo_tipo_documento.get(),
            "numero_documento": self.campo_numero_documento.get(),
            "regime": self._regime_selecionado(),
            "nif": self.campo_nif.get(),
            "email": email,
            "telefone": self.campo_telefone.get(),
            "morada": self.campo_morada.get(),
            "nacionalidade": self.campo_nacionalidade.get(),
            "estado_civil": self.combo_estado_civil.get(),
            "data_nascimento": data_nascimento,
            "validade_documento": validade_documento,
            "contacto_emergencia": self.campo_contacto_emergencia.get(),
        }

    def _guardar(self):
        raise NotImplementedError


class NovoClienteModal(_FormularioCliente):
    """Modal de criação de um cliente novo."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista, "Novo Cliente")

    def _guardar(self):
        try:
            valores = self._ler_campos_comuns()
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            cliente = clientes.criar(
                valores["nome"],
                valores["tipo_documento"],
                valores["numero_documento"],
                valores["regime"],
                nif=valores["nif"],
                email=valores["email"],
                telefone=valores["telefone"],
                morada=valores["morada"],
                nacionalidade=valores["nacionalidade"],
                estado_civil=valores["estado_civil"],
                data_nascimento=valores["data_nascimento"],
                validade_documento=valores["validade_documento"],
                contacto_emergencia=valores["contacto_emergencia"],
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        mensagem = f"Cliente criado com sucesso: {cliente['id']}"
        if cliente["incompleto"]:
            mensagem += "\n(incompleto — verifica os campos em falta)"

        componentes.mostrar_sucesso(mensagem)
        self.destroy()
        self.tela_lista._recarregar()


class EditarClienteModal(_FormularioCliente):
    """Modal de edição de um cliente existente — mesmos campos de
    NovoClienteModal, pré-preenchidos.

    'Regime' não vem gravado no cliente (ver docstring do módulo,
    ponto 1) — arranca em "Mensal" se o cliente já tiver NIF
    preenchido (sinal de que foi criado nesse regime), senão
    "Airbnb". É só um valor por omissão: o utilizador pode trocá-lo
    antes de guardar, se o regime real for outro.
    """

    def __init__(self, tela_lista, cliente):
        super().__init__(tela_lista, f"Editar Cliente — {cliente['nome']}")
        self.cliente = cliente

        self.campo_nome.insert(0, cliente["nome"])
        self.combo_tipo_documento.set(cliente["tipo_documento"])
        self.campo_numero_documento.insert(0, cliente["numero_documento"])
        self.combo_regime.set("Mensal" if cliente["nif"] else "Airbnb")
        self.campo_nif.insert(0, cliente["nif"])
        self.campo_email.insert(0, cliente["email"])
        self.campo_telefone.insert(0, cliente["telefone"])
        self.campo_morada.insert(0, cliente["morada"])
        self.campo_nacionalidade.insert(0, cliente["nacionalidade"])
        if cliente["nacionalidade"] in NACIONALIDADES:
            self.combo_nacionalidade.set(cliente["nacionalidade"])
            self.campo_nacionalidade.grid_remove()
        elif cliente["nacionalidade"]:
            self.combo_nacionalidade.set(OUTRA_NACIONALIDADE)
            self.campo_nacionalidade.grid()
        if cliente["estado_civil"]:
            self.combo_estado_civil.set(cliente["estado_civil"])
        self.campo_data_nascimento.insert(
            0, _formatar_data(cliente["data_nascimento"])
        )
        self.campo_validade_documento.insert(
            0, _formatar_data(cliente["validade_documento"])
        )
        self.campo_contacto_emergencia.insert(
            0, cliente["contacto_emergencia"]
        )

    def _guardar(self):
        try:
            valores = self._ler_campos_comuns()
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            clientes.atualizar(
                self.cliente["id"],
                regime=valores["regime"],
                nome=valores["nome"],
                tipo_documento=valores["tipo_documento"],
                numero_documento=valores["numero_documento"],
                nif=valores["nif"],
                email=valores["email"],
                telefone=valores["telefone"],
                morada=valores["morada"],
                nacionalidade=valores["nacionalidade"],
                estado_civil=valores["estado_civil"],
                data_nascimento=valores["data_nascimento"],
                validade_documento=valores["validade_documento"],
                contacto_emergencia=valores["contacto_emergencia"],
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Cliente {self.cliente['id']} atualizado."
        )
        self.destroy()
        self.tela_lista._recarregar()


class _AnonimizarModal(ctk.CTkToplevel):
    """Modal de anonimização — operação IRREVERSÍVEL (decisão 8,
    RGPD secção 6). Mesmo padrão do _ConfirmarForcarModal de
    Propriedades e Unidades: mensagem de aviso + dropdown de
    Responsável obrigatório + botão vermelho de confirmação. A data
    usa sempre datetime.date.today() (sem campo próprio).
    """

    def __init__(self, tela_lista, cliente):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.cliente = cliente

        self.title("Anonimizar cliente")
        self.geometry("380x320")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        mensagem = (
            f"Anonimizar {cliente['nome']} ({cliente['id']})? Esta "
            f"ação é IRREVERSÍVEL — apaga os dados pessoais do "
            f"cliente (email, telefone, morada, NIF, documento, "
            f"data de nascimento, contacto de emergência) e não "
            f"pode ser desfeita."
        )
        ctk.CTkLabel(
            self,
            text=mensagem,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            wraplength=330,
            justify="left",
        ).pack(padx=20, pady=(24, 14), fill="x")

        ctk.CTkLabel(
            self,
            text="Responsável que autoriza *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel = ctk.CTkOptionMenu(self, values=nomes)
        self.combo_responsavel.set(nomes[0])
        self.combo_responsavel.pack(fill="x", padx=20, pady=(2, 10))

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
            text="Anonimizar (irreversível)",
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._anonimizar,
        ).pack(side="right")

    def _responsavel_escolhido_id(self):
        indice = self.combo_responsavel.cget("values").index(
            self.combo_responsavel.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _anonimizar(self):
        responsavel_id = self._responsavel_escolhido_id()

        if not responsavel_id:
            componentes.mostrar_erro(
                "Escolhe o responsável que autoriza a anonimização."
            )
            return

        try:
            clientes.anonimizar(
                self.cliente["id"],
                responsavel_id,
                datetime.date.today(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Cliente {self.cliente['id']} anonimizado."
        )
        self.destroy()
        self.tela_lista._recarregar()
