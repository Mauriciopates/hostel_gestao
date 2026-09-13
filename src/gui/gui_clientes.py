"""Ecrã "Clientes": lista os clientes (mensais e Airbnb) em tabela
padrão — a mesma estrutura da Gestão de Propriedades — com o estado
de cada um (ativo/inativo, incompleto, anonimizado) e um botão
"Gerir" por linha que abre o popup com as ações.

REESTRUTURAÇÃO 13/09/2026 — decisão do aluno, mockup HTML aprovado
antes de codar. A lista deixou de desenhar cartões empilhados e
passou a ser uma tabela igual à de Gestão de Propriedades (o "padrão
base" do sistema). Colunas: ID, NOME DO CLIENTE (nome + subtítulo com
documento/NIF por baixo), ESTADO, AÇÕES. Cada linha tem um único
botão "Gerir" (mesmo padrão do `_AcoesPropriedadeModal`), que abre
`_AcoesClienteModal` — o popup com as ações.

O subtítulo dentro da coluna NOME DO CLIENTE (linha de baixo, dentro
da mesma célula) substitui o antigo subtítulo do cartão: mostra
"{tipo_documento} {numero_documento} · NIF {nif}" quando há NIF, só
"{tipo_documento} {numero_documento}" quando não há, e
"Dados pessoais removidos (anonimizado)" quando o cliente foi
anonimizado — exatamente o mesmo critério que já existia no cartão.

O popup "Gerir" varia com o estado do cliente:

- Cliente ATIVO → Editar · Anonimizar (irreversível) — separador —
  Desativar.
- Cliente INATIVO → Reativar · Anonimizar (irreversível).
- Cliente ANONIMIZADO → sem ações; só texto a explicar que os dados
  foram removidos por RGPD.

A anonimização aparece nos dois estados (ativo e inativo) porque a
regra de negócio (`clientes.anonimizar`) permite anonimizar um
cliente já inativo — confirmado pelo aluno, 13/09/2026.

As duas convenções seguintes mantêm-se do ecrã antigo, agora
aplicadas ao popup novo:

1. Botões com a mesma forma, altura e contorno; só a cor do texto
   muda. Num menu de opções nenhuma delas é mais importante do que
   as outras.
2. Risco fino antes da ação destrutiva (Desativar / Anonimizar),
   para dar uma pausa antes do último botão.

Decisões anteriores que continuam em vigor (do ecrã antigo,
07/09/2026):

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
   sempre alterável antes de guardar.

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
   escolher outra data; não é exposto na GUI).

6. Um cliente anonimizado não pode ser editado nem reativado
   (clientes.atualizar/reativar recusam) — por isso o popup de um
   cliente anonimizado não mostra nenhum botão de ação, só o aviso.

7. Filtro de completude (Todos/Incompletos/Completos), ao lado de
   "Mostrar inativos" — mesmas duas opções de filtro que
   `_listar_clientes` já tem no CLI (decisão 11: tem de existir
   listagem de incompletos, senão o aviso não produz efeito).

8. Email em formato simples validado (tem de ter um nome, um "@" e
   um domínio com pelo menos um ponto), só no ecrã Clientes — a
   mesma regra do formulário antigo, mantida intacta. O email
   continua opcional (decisão 11 antiga): a regra só corre quando o
   campo não está vazio.

9. Nacionalidade com seletor — lista curta de nacionalidades comuns
   mais "Outra", com a caixa de texto escondida por omissão e só
   revelada em "Outra". Mesmo comportamento do formulário antigo,
   mantido intacto.

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


# =====================================================================
# Larguras fixas das colunas da tabela (mesma disciplina de
# gui_propriedades.py, ponto 12): uma constante por coluna, lida
# tanto pelo cabeçalho como pelas linhas, para os dois nunca poderem
# desalinhar por um número esquecido num dos dois sítios.
# =====================================================================

_LARGURA_ID = 90
_LARGURA_NOME = 260
_LARGURA_ESTADO = 120
_LARGURA_ACOES = 100

_ALTURA_LINHA = 52

_COLUNAS_CLIENTE = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("NOME DO CLIENTE", peso=3, minimo=_LARGURA_NOME),
    componentes.Coluna(
        "ESTADO", peso=1, minimo=_LARGURA_ESTADO, alinhamento="centro"
    ),
    componentes.Coluna("AÇÕES", minimo=_LARGURA_ACOES, alinhamento="centro"),
)


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
    """Ecrã principal: lista os clientes em tabela padrão, com um
    único botão "Gerir" por linha que abre o popup de ações.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Clientes").pack(fill="x")

        # Botão de criação numa barra própria, logo abaixo do
        # cabeçalho e a verde — mesmo padrão de Contrato Mensal e
        # Reservas Airbnb (09/09/2026).
        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Novo Cliente",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovoClienteModal(self),
        ).pack(side="left")

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

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_CLIENTE,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia="Ainda não há clientes cadastrados.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ------------------------------------

    def _incompleto_selecionado(self):
        return {"Todos": None, "Incompletos": True, "Completos": False}[
            self.combo_completude.get()
        ]

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela — chamada na abertura do
        ecrã, ao mexer nos filtros, e depois de qualquer criação/
        edição/desativação/reativação/anonimização (mesmo princípio
        de ListaPropriedades._recarregar).
        """
        self.tabela.limpar()

        lista = clientes.listar(
            incluir_inativos=self.mostrar_inativos.get(),
            incompleto=self._incompleto_selecionado(),
        )

        if not lista:
            self.tabela.mostrar_vazio()
            return

        for cliente in lista:
            self._desenhar_cliente(cliente)

    # -- desenho -------------------------------------------------------

    def _desenhar_cliente(self, cliente):
        """Desenha uma linha da tabela para um cliente.

        Cada célula é um widget criado com a linha como master e
        colocado com `self.tabela.colocar`, que trata do grid, do
        alinhamento e das folgas. A altura, as divisórias e o tom
        das linhas são da tabela.
        """
        inativo = not cliente["ativo"]
        anonimizado = cliente["anonimizado"]

        linha = self.tabela.nova_linha()

        # ---- ID (chip, igual a Propriedades) ----
        cor_id = (
            tema.TEXTO_INDISPONIVEL if anonimizado else tema.AZUL_PRINCIPAL
        )
        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=cliente["id"],
                text_color=cor_id,
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ID,
                anchor="w",
            ),
            esticar="w",
        )

        # ---- NOME DO CLIENTE (nome + subtítulo com documento/NIF) ----
        cor_nome = (
            tema.TEXTO_INDISPONIVEL
            if anonimizado
            else (tema.COR_TEXTO_SECUNDARIO if inativo else tema.COR_TEXTO)
        )

        if anonimizado:
            subtitulo = "Dados pessoais removidos (anonimizado)"
        else:
            subtitulo = (
                f"{cliente['tipo_documento']} "
                f"{cliente['numero_documento']}"
            )
            if cliente["nif"]:
                subtitulo += f" · NIF {cliente['nif']}"

        bloco_nome = ctk.CTkFrame(linha, fg_color="transparent")
        ctk.CTkLabel(
            bloco_nome,
            text=cliente["nome"],
            text_color=cor_nome,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            bloco_nome,
            text=subtitulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x")
        self.tabela.colocar(linha, 1, bloco_nome)

        # ---- ESTADO (chip colorido) ----
        if anonimizado:
            chip_texto, chip_fundo, chip_cor = (
                "anonimizado",
                tema.CINZA_INDISPONIVEL,
                tema.TEXTO_INDISPONIVEL,
            )
        elif inativo:
            chip_texto, chip_fundo, chip_cor = (
                "inativo",
                tema.CINZA_INDISPONIVEL,
                tema.TEXTO_INDISPONIVEL,
            )
        elif cliente["incompleto"]:
            chip_texto, chip_fundo, chip_cor = (
                "incompleto",
                tema.AMARELO_AVISO,
                tema.TEXTO_AVISO,
            )
        else:
            chip_texto, chip_fundo, chip_cor = (
                "ativo",
                tema.VERDE_LIVRE,
                tema.TEXTO_LIVRE,
            )

        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=chip_texto,
                text_color=chip_cor,
                fg_color=chip_fundo,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ESTADO,
                height=22,
            ),
        )

        # ---- AÇÕES (um único botão "Gerir") ----
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
                command=lambda: _AcoesClienteModal(self, cliente),
            )
        )

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


class _AcoesClienteModal(ctk.CTkToplevel):
    """Popup pequeno com as ações de um cliente — aberto pelo botão
    "Gerir" de cada linha em `ListaClientes` (13/09/2026, ver
    docstring do módulo).

    Mesmo padrão dos popups de propriedade, unidade e responsável:
    nome/ID no topo, botões de ação com a mesma forma e contorno (só
    a cor do texto muda), separador antes da ação destrutiva,
    "Fechar" no fim.

    As ações variam com o estado do cliente:

    - Cliente ATIVO → Editar · Anonimizar (irreversível) — separador —
      Desativar.
    - Cliente INATIVO → Reativar · Anonimizar (irreversível).
    - Cliente ANONIMIZADO → sem ações; só texto a explicar que os
      dados foram removidos por RGPD.

    A anonimização aparece nos dois estados (ativo e inativo) porque
    `clientes.anonimizar` permite anonimizar um cliente já inativo —
    confirmado pelo aluno, 13/09/2026. Num cliente anonimizado, a
    edição, a reativação e a nova anonimização não fazem sentido
    nenhum: os dados pessoais já foram apagados e não há para onde
    voltar (o próprio `clientes.atualizar`/`reativar` recusariam).
    """

    def __init__(self, tela_lista, cliente):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.cliente = cliente

        anonimizado = cliente["anonimizado"]
        inativo = not cliente["ativo"]

        # Altura consoante o número de ações — a mesma lógica do
        # `_AcoesResponsavelModal`, evita uma janela com espaço a mais
        # no caso anonimizado (só o texto explicativo).
        if anonimizado:
            altura = 220
        elif inativo:
            altura = 250
        else:
            altura = 290

        self.title(f"Ações — {cliente['id']}")
        self.geometry(f"320x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        self._centrar_sobre(tela_lista, altura)
        _colocar_no_topo(self)

        # ---- Título + subtítulo ----
        ctk.CTkLabel(
            self,
            text=cliente["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        if anonimizado:
            subtitulo = f"{cliente['id']} · anonimizado"
        elif inativo:
            subtitulo = f"{cliente['id']} · inativo"
        elif cliente["incompleto"]:
            subtitulo = f"{cliente['id']} · incompleto"
        else:
            subtitulo = f"{cliente['id']} · ativo"

        ctk.CTkLabel(
            self,
            text=subtitulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        # ---- Ações (variam com o estado) ----
        if anonimizado:
            # Sem ações — só o aviso. Mesma ideia do aviso de
            # impressão bloqueada em `_AcoesContratoModal`.
            ctk.CTkLabel(
                self,
                text=(
                    "Os dados pessoais foram removidos (RGPD).\n"
                    "Sem ações disponíveis."
                ),
                text_color=tema.TEXTO_INDISPONIVEL,
                font=ctk.CTkFont(size=11),
                justify="center",
            ).pack(padx=20, pady=(10, 20))

        elif inativo:
            # Cliente inativo: Reativar + Anonimizar. A ordem põe
            # primeiro a ação positiva (Reativar), depois a
            # irreversível — mesma convenção do `_AcoesResponsavelModal`
            # (que põe "Reativar" isolado no ramo inativo).
            self._botao(
                "Reativar",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self.tela_lista._reativar(cliente),
            )
            self._botao(
                "Anonimizar (irreversível)",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: _AnonimizarModal(self.tela_lista, cliente),
            )

        else:
            # Cliente ativo: Editar + Anonimizar — separador —
            # Desativar. A ação destrutiva fica sozinha em baixo do
            # separador, como em `_AcoesPropriedadeModal` e
            # `_AcoesUnidadeModal`.
            self._botao(
                "Editar",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EditarClienteModal(tela_lista, cliente),
            )
            self._botao(
                "Anonimizar (irreversível)",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: _AnonimizarModal(self.tela_lista, cliente),
            )
            self._separador()
            self._botao(
                "Desativar",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: self.tela_lista._desativar(cliente),
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
        """Abre por cima da janela que o chamou.

        Sem isto o Tk coloca o popup no canto superior esquerdo do
        ecrã, longe do botão que acabou de ser clicado.
        """
        janela.update_idletasks()
        x = janela.winfo_rootx() + (janela.winfo_width() - 320) // 2
        y = janela.winfo_rooty() + (janela.winfo_height() - altura) // 2
        self.geometry(f"320x{altura}+{max(x, 0)}+{max(y, 0)}")

    def _separador(self):
        """Risco fino antes da ação destrutiva.

        Não é decoração: separa o que se pode desfazer do que não se
        desfaz, e dá uma pausa antes do último botão.
        """
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, text_color, hover_color, acao):
        """Botão de ação: fecha este popup antes de agir.

        A ordem importa — as ações abrem outro popup (Editar,
        Anonimizar) ou fazem `_recarregar` na tabela por trás
        (Desativar, Reativar); deixar este aberto por cima deixava-o
        pendurado sobre coisas que entretanto mudaram.
        """

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


class _FormularioCliente(ctk.CTkToplevel):
    """Base comum a NovoClienteModal e EditarClienteModal — monta os
    13 campos + o seletor de Regime, sempre na mesma ordem do CLI
    (_criar_cliente/_atualizar_cliente). As duas subclasses só
    diferem no título, na pré-preenchida dos campos e no que
    acontece ao guardar.

    Inalterada desde 06/09/2026, quando foi validada por mockup e
    por um teste de submissão real.
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

    Inalterada desde 06/09/2026.
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
