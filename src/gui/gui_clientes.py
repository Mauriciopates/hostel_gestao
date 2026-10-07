"""Ecrã "Clientes": lista os clientes (mensais e Airbnb) em tabela
padrão — a mesma estrutura da Gestão de Propriedades — com o estado
de cada um (ativo/inativo/anonimizado) e um botão "Gerir" por linha
que abre o popup com as ações.

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
07/09/2026, ATUALIZADAS pela reestruturação de 16/09/2026 — ver
secção própria mais abaixo):

1. 'regime' NÃO é campo do cliente (clientes.criar/atualizar já não
   o guardam) — serve só para saber, no momento da chamada, que
   conjunto de campos é obrigatório. Desde 16/09/2026 a escolha do
   regime já não é um seletor dentro de um formulário único — é um
   popup prévio (`_SeletorRegimeClienteModal`) que abre já o modal
   certo (`NovoClienteMensalModal`/`NovoClienteAirbnbModal`). O
   `EditarClienteModal` é a EXCEÇÃO: continua com o formulário único
   de sempre e o seletor "Regime" lá dentro (mesma posição do CLI,
   logo a seguir ao número de documento), porque a edição não foi
   repartida por regime nesta entrega — arranca em "Mensal" se o
   cliente já tiver NIF preenchido, senão "Airbnb", só um valor por
   omissão, sempre alterável antes de guardar.

2. Todos os campos sempre visíveis, obrigatoriedade só validada ao
   submeter — mesma convenção fixada em Novo Contrato Mensal (parte
   3), reforçada em Propriedades e Unidades (parte 4).

3. Cada modal usa o mesmo padrão visual (grelha rótulo-à-esquerda/
   campo-à-direita, dentro de um CTkScrollableFrame, rodapé de
   botões fixo por fora — o mesmo do cartão de Novo Contrato Mensal),
   mas desde 16/09/2026 cada um só tem os campos do seu regime: o
   `_FormularioCliente` deixou de construir uma lista fixa de 13
   campos + seletor — é só a moldura (título, geometria, cartão,
   rodapé) e os helpers de campo; cada subclasse decide os seus.

4. Erro e sucesso sempre por popup nativo (componentes.mostrar_erro/
   mostrar_sucesso), convenção já fixada nas partes 3 e 4. Desde
   16/09/2026 já não existe o aviso de "incompleto" na mensagem de
   sucesso — ver a secção "incompleto" mais abaixo.

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

7. (Removida em 16/09/2026 — ver secção "incompleto" mais abaixo. O
   filtro de completude ao lado de "Mostrar inativos" deixou de
   existir.)

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

CONSOLIDAÇÃO DE HELPERS EM componentes.py (13/09/2026) — o helper
visual que estava duplicado localmente passou a viver só no
`componentes.py`:

- `_colocar_no_topo` local → `componentes.colocar_no_topo`
  (alias no topo, mesmo nome antigo, para o corpo do ficheiro não
  ter de ser reescrito). O resto do ficheiro não mudou.

CORREÇÃO 13/09/2026 — fecho do `NovoClienteModal` / `EditarClienteModal`
quando abertos de dentro de um formulário de contrato/reserva:

- O botão "+ Novo cliente" existe em três sítios: na `ListaClientes`
  e nos cartões "Cliente" do `NovoContratoMensal` e do
  `NovaReservaAirbnb` (gui_contratos.py). O `NovoClienteModal` não
  sabia disto e chamava sempre `self.tela_lista._recarregar()` no
  fim — quando a `tela_lista` era o contrato ou a reserva, esse
  método não existe e rebentava com `AttributeError` (bug apanhado
  pelo aluno, 13/09/2026). Agora a chamada tolera os dois casos: usa
  `_recarregar` se existir, senão `_recarregar_clientes`. O
  `EditarClienteModal` ganhou a mesma defesa por consistência,
  mesmo não sendo aberto a partir dos contratos hoje.

REESTRUTURAÇÃO 16/09/2026 — decisão do aluno, mockup HTML aprovado
("perfeito no modal novo cliente também coloque como nome completo
ok validado achei perfeito"). Fase 3, checklist "Alternância de
campos no formulário de Cliente (Airbnb vs Mensal)":

1. "+ Novo Cliente" deixou de abrir um formulário único com um
   seletor "Regime" lá dentro. Abre agora `_SeletorRegimeClienteModal`
   — dois cartões clicáveis (mesmo padrão do "O que pretende criar?"
   do módulo de Stock, `componentes.tornar_cliclavel`) — que já abre
   o modal certo: `NovoClienteMensalModal` (620x680, 12 campos, todos
   obrigatórios exceto Email e Contacto de emergência — Nacionalidade
   e Telefone passaram a obrigatórios, deixaram de ser opcionais) ou
   `NovoClienteAirbnbModal` (580x460, só 7 campos, todos
   obrigatórios: nome, nacionalidade, data de nascimento, tipo/
   número de documento, país emissor do documento, país de
   residência).

2. Campos novos (só Airbnb): 'pais_emissor_documento' e
   'pais_residencia' — texto livre, sem lista de países pré-definida
   (a Nacionalidade continua com o seletor de sempre). Exigem
   ALTER TABLE clientes (ver aviso em separado) — colunas novas em
   `repositorio.inserir_cliente`, parâmetros novos em
   `clientes.criar`/`atualizar`.

3. O conceito de "incompleto" (campos em falta que não bloqueavam a
   gravação, decisão 11 antiga) foi DESCARTADO nesta reestruturação
   — decisão do aluno: como cada modal já só pede o que o regime
   exige, um cliente novo nunca fica "a meio". `validacoes.
   validar_cliente` deixou de devolver uma lista de em_falta — só
   bloqueia (ValueError). `clientes.criar`/`atualizar` gravam sempre
   `incompleto=False` num cliente novo/atualizado (a coluna
   'incompleto' continua a existir na BD e `clientes.anonimizar`
   continua a marcá-la True — esse uso é outro, sinaliza dados
   apagados por RGPD, não foi tocado). O filtro "Todos/Incompletos/
   Completos" e o chip "incompleto" na tabela foram removidos do
   ecrã — deixaram de ter efeito.

4. `EditarClienteModal` NÃO foi repartido por regime nesta entrega
   (decisão do aluno: "fico só com Novo Cliente nesta entrega") —
   continua com o formulário único de sempre, sem os dois campos de
   país. PENDÊNCIA conhecida: um cliente Airbnb criado antes desta
   data (sem país emissor/residência preenchidos) só volta a poder
   ser editado depois de esses dois campos serem preenchidos nalgum
   sítio — hoje não há onde os preencher no Editar. Não bloqueia
   clientes Mensais nem Airbnb já criados com os campos novos.
"""

import datetime

import customtkinter as ctk

import clientes
import contratos
import responsaveis
import termos
import unidades
import validacoes
from . import componentes
from . import sessao
from . import tema

# Alias local para o helper que vivia neste ficheiro e passou a
# viver em componentes.py. Mantém-se o nome antigo com "_" para o
# corpo do ficheiro não ter de ser reescrito — mesma técnica já
# usada no gui_propriedades.py, gui_contratos.py, gui_calendario.py,
# gui_unidades.py, gui_responsaveis.py e gui_est_requisicoes.py.
_colocar_no_topo = componentes.colocar_no_topo


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
NACIONALIDADE_PLACEHOLDER = "Escolher"
OUTRA_NACIONALIDADE = "Outra (escrever ao lado)"


# =====================================================================
# Larguras fixas das colunas da tabela (mesma disciplina de
# gui_propriedades.py, ponto 12): uma constante por coluna, lida
# tanto pelo cabeçalho como pelas linhas, para os dois nunca poderem
# desalinhar por um número esquecido num dos dois sítios.
# =====================================================================

_LARGURA_ID = 90
_LARGURA_NOME = 260
_LARGURA_ESTADO = 120
_LARGURA_TIPO = 100
_LARGURA_ACOES = 100

_ALTURA_LINHA = 52

# Filtro "Tipo" do topo (v1.9.0, bloco C): rótulo da pílula -> tipo
# pedido a `clientes.filtrar_por_tipo` (None = todos).
_FILTROS_TIPO = (
    ("Todos", None, "todos"),
    ("Mensal", clientes.TIPO_MENSAL, clientes.TIPO_MENSAL),
    ("Airbnb", clientes.TIPO_AIRBNB, clientes.TIPO_AIRBNB),
)

# Chip da coluna TIPO: (texto, fundo, cor do texto). Azul = Mensal
# (a cor dos contratos mensais), rosa = Airbnb; claro/escuro.
_CHIP_TIPO = {
    clientes.TIPO_MENSAL: ("Mensal", ("#E3EEF7", "#16323F"),
                           (tema.AZUL_PRINCIPAL, "#8CC8E8")),
    clientes.TIPO_AIRBNB: ("Airbnb", ("#FDE8EC", "#3F1A24"),
                           ("#B4234A", "#F2A0B4")),
    None: ("—", tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL),
}

_COLUNAS_CLIENTE = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("NOME DO CLIENTE", peso=3, minimo=_LARGURA_NOME),
    componentes.Coluna(
        "TIPO", minimo=_LARGURA_TIPO + 20, alinhamento="centro"
    ),
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


# =====================================================================
# Aviso de privacidade do hóspede (v1.9.0, bloco D)
# =====================================================================
#
# RGPD art. 13.º: a informação é dada NO MOMENTO da recolha; art. 5.º,
# n.º 2: a empresa tem de conseguir provar que a deu. Ao hóspede NÃO
# se pede consentimento (o fundamento é o contrato e a obrigação
# legal do boletim — ver docstring de termos.py): a caixa é o
# funcionário a confirmar que ENTREGOU a informação, e por isso pode
# trancar o Guardar. Decisão do aluno, 05/10/2026.

_SUPORTES_AVISO_HOSPEDE = {"Papel": "papel", "Contrato": "contrato"}

_ROTULO_AVISO_HOSPEDE = "Confirmo que entreguei esta informação ao cliente. *"

_ALTURA_TEXTO_AVISO = 110


def _bloco_aviso_hospede(master, texto, ao_mudar, estado=None):
    """Monta o `BlocoTermo` do aviso ao hóspede com a escolha
    "Entregue em Papel | Contrato".

    Devolve (bloco, função que diz o suporte escolhido). `estado` é o
    dicionário do `termos.verificar` (só existe quando o cliente já
    existe — Gerir → Aviso de privacidade).
    """
    escolha = {}

    def montar_suporte(pai):
        linha = ctk.CTkFrame(pai, fg_color="transparent")
        ctk.CTkLabel(
            linha,
            text="Entregue em",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 10))
        escolha["seletor"] = componentes.SeletorVistas(
            linha, list(_SUPORTES_AVISO_HOSPEDE), ao_mudar=lambda _v: None
        )
        escolha["seletor"].pack(side="left")
        return linha

    bloco = componentes.BlocoTermo(
        master,
        titulo="Aviso de privacidade do hóspede (RGPD art. 13.º)",
        texto=texto["texto"],
        versao=texto["versao"],
        rotulo=_ROTULO_AVISO_HOSPEDE,
        versao_anterior=estado["versao_aceite"] if estado else None,
        data_anterior=estado["data_aceite"] if estado else None,
        ao_mudar=ao_mudar,
        altura_texto=_ALTURA_TEXTO_AVISO,
        extra=montar_suporte,
    )

    def suporte():
        return _SUPORTES_AVISO_HOSPEDE[escolha["seletor"].get()]

    return bloco, suporte


def _id_responsavel_ativo():
    ativo = sessao.obter_responsavel_ativo()
    return ativo["id"] if ativo else None


def _recarregar_tela_lista(tela_lista):
    """Recarrega a lista por trás de um modal de cliente.

    `NovoClienteMensalModal`, `NovoClienteAirbnbModal` e
    `EditarClienteModal` são abertos em dois contextos diferentes:

    - A partir da `ListaClientes` (o ecrã "Clientes", botão
      "+ Novo Cliente" e "Gerir → Editar") — a `tela_lista` é uma
      `ListaClientes`, que tem `_recarregar`.

    - A partir do botão "+ Novo cliente" do `NovoContratoMensal` ou
      do `NovaReservaAirbnb` (gui_contratos.py) — a `tela_lista` é
      um desses formulários, que têm `_recarregar_clientes`, não
      `_recarregar`.

    Chamar `tela_lista._recarregar()` sem pensar rebentava com
    `AttributeError` no segundo caso (bug apanhado pelo aluno,
    13/09/2026). Esta função resolve os dois casos sem o modal
    precisar de saber de onde foi aberto.
    """
    recarregar = getattr(tela_lista, "_recarregar", None)

    if recarregar is not None:
        recarregar()
    else:
        tela_lista._recarregar_clientes()


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
            command=lambda: _SeletorRegimeClienteModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO)
        barra.pack(fill="x", padx=20, pady=(0, 4))

        # Filtro por tipo (v1.9.0, bloco C). Os rótulos levam a
        # contagem — "Mensal (2)" — e são refeitos em cada _recarregar;
        # o filtro escolhido guarda-se pelo índice para sobreviver.
        self._indice_filtro_tipo = 0
        self.filtro_tipo = componentes.SeletorVistas(
            barra,
            [rotulo for rotulo, _tipo, _chave in _FILTROS_TIPO],
            ao_mudar=self._ao_mudar_filtro_tipo,
        )
        self.filtro_tipo.pack(side="left")

        self.mostrar_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativos",
            variable=self.mostrar_inativos,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

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

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela — chamada na abertura do
        ecrã, ao mexer nos filtros, e depois de qualquer criação/
        edição/desativação/reativação/anonimização (mesmo princípio
        de ListaPropriedades._recarregar).

        REESTRUTURAÇÃO 16/09/2026: já não filtra por "incompleto" —
        ver docstring do módulo e de `validacoes.validar_cliente`.
        """
        self.tabela.limpar()

        todos = clientes.listar(incluir_inativos=self.mostrar_inativos.get())
        self._atualizar_rotulos_filtro(clientes.contar_por_tipo(todos))

        _rotulo, tipo_pedido, _chave = _FILTROS_TIPO[self._indice_filtro_tipo]
        lista = clientes.filtrar_por_tipo(todos, tipo_pedido)

        if not lista:
            self.tabela.mostrar_vazio()
            return

        for cliente in lista:
            self._desenhar_cliente(cliente)

    def _rotulos_filtro(self, contagem):
        return [
            f"{rotulo} ({contagem[chave]})"
            for rotulo, _tipo, chave in _FILTROS_TIPO
        ]

    def _atualizar_rotulos_filtro(self, contagem):
        """Põe as contagens nas pílulas, mantendo a escolhida."""
        rotulos = self._rotulos_filtro(contagem)
        self.filtro_tipo.configure(values=rotulos)
        self.filtro_tipo.set(rotulos[self._indice_filtro_tipo])

    def _ao_mudar_filtro_tipo(self, rotulo_escolhido):
        valores = list(self.filtro_tipo.cget("values"))
        self._indice_filtro_tipo = valores.index(rotulo_escolhido)
        self._recarregar()

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
        # Clicar no ID abre os contratos e reservas do cliente.
        chip_id = componentes.ChipId(
            linha,
            cliente["id"],
            ao_clicar=lambda: abrir_contratos_do_cliente(self, cliente),
            largura=_LARGURA_ID,
        )
        chip_id.configure(text_color=cor_id)
        self.tabela.colocar(linha, 0, chip_id, esticar="w")

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

        # ---- TIPO (chip Mensal / Airbnb, v1.9.0) ----
        tipo_texto, tipo_fundo, tipo_cor = _CHIP_TIPO[clientes.tipo(cliente)]
        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=tipo_texto,
                text_color=tipo_cor,
                fg_color=tipo_fundo,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_TIPO,
                height=22,
            ),
        )

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
        else:
            chip_texto, chip_fundo, chip_cor = (
                "ativo",
                tema.VERDE_LIVRE,
                tema.TEXTO_LIVRE,
            )

        self.tabela.colocar(
            linha,
            3,
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


def abrir_contratos_do_cliente(master, cliente):
    """Abre a lista (só leitura) dos contratos mensais e reservas
    Airbnb de um cliente — ativos e encerrados/cancelados.
    """
    linhas = []
    for ocupacao in contratos.listar(
        incluir_inativas=True, cliente_id=cliente["id"]
    ):
        unidade = unidades.procurar(ocupacao["unidade_id"])
        nome_unidade = unidade["nome"] if unidade else ocupacao["unidade_id"]
        periodo = (
            f"{componentes.formatar_data(ocupacao['data_inicio'])} → "
            f"{componentes.formatar_data(ocupacao['data_fim'])}"
        )
        linhas.append(
            (
                ocupacao["id"],
                "Mensal" if ocupacao["tipo"] == "mensal" else "Airbnb",
                f"{nome_unidade} ({ocupacao['unidade_id']})",
                periodo,
                "Ativo" if ocupacao["ativo"] else "Inativo",
            )
        )

    componentes.ListaVinculadaModal(
        master,
        titulo=f"{cliente['nome']} ({cliente['id']})",
        subtitulo="Contratos e reservas do cliente",
        colunas=(
            componentes.Coluna("ID", minimo=110, espaco=8),
            componentes.Coluna("TIPO", minimo=70),
            componentes.Coluna("UNIDADE", peso=3, minimo=180),
            componentes.Coluna("PERÍODO", peso=2, minimo=170),
            componentes.Coluna("ESTADO", minimo=70),
        ),
        linhas=linhas,
        mensagem_vazia="Este cliente ainda não tem contratos nem reservas.",
    )


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

        # v1.9.0, bloco D — estado do aviso de privacidade. Sem texto
        # publicado (erro de configuração) a ação simplesmente não
        # aparece; num anonimizado não faz sentido.
        self._estado_aviso = None
        if not anonimizado:
            try:
                self._estado_aviso = termos.verificar(
                    termos.TITULAR_CLIENTE,
                    cliente["id"],
                    termos.PRIVACIDADE_HOSPEDE,
                )
            except ValueError:
                self._estado_aviso = None
        if self._estado_aviso is not None:
            altura += 40

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

        # 26/09/2026 — só o Master vê "Anonimizar".
        pode_anonimizar = sessao.tipo_utilizador_ativo() == "Master"

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
            self._botao_aviso(tela_lista, cliente)
            if pode_anonimizar:
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
            self._botao_aviso(tela_lista, cliente)
            if pode_anonimizar:
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

    def _botao_aviso(self, tela_lista, cliente):
        """Ação "Aviso de privacidade" com o estado no próprio texto:
        "✓ v1.0 · 05/10/2026" quando o aviso foi registado (em
        qualquer versão — decisão de 05/10/2026, ver
        `termos.verificar`), âmbar "por registar" quando nunca foi."""
        estado = self._estado_aviso
        if estado is None:
            return

        if estado["em_dia"]:
            texto = (
                f"Aviso de privacidade  ✓ v{estado['versao_aceite']}"
                f" · {componentes.formatar_data(estado['data_aceite'])}"
            )
            cor, hover = tema.COR_TEXTO, tema.COR_BORDA
        else:
            texto = "Aviso de privacidade · por registar"
            cor, hover = tema.TEXTO_AVISO, tema.AMARELO_AVISO

        self._botao(
            texto,
            text_color=cor,
            hover_color=hover,
            acao=lambda: AvisoPrivacidadeClienteModal(tela_lista, cliente),
        )

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


class _SeletorRegimeClienteModal(ctk.CTkToplevel):
    """Popup de escolha, aberto pelo "+ Novo Cliente" — dois cartões
    clicáveis (Cliente Mensal / Cliente Airbnb), mesmo padrão do
    seletor "O que pretende criar?" do módulo de Stock
    (NovaRequisicaoModal). Substitui o antigo seletor "Regime" de
    dentro do formulário único (decisão do aluno, mockup HTML
    aprovado, 16/09/2026): cada regime passou a ter o seu próprio
    modal, com só os campos que exige — ver `NovoClienteMensalModal`
    e `NovoClienteAirbnbModal`.
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 380, 260
        self.title("Novo Cliente")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Que tipo de cliente?",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 14))

        self._cartao(
            "Cliente Mensal",
            "Contrato de arrendamento: formulário completo (NIF, "
            "morada, estado civil, etc.).",
            self._abrir_mensal,
        )
        self._cartao(
            "Cliente Airbnb",
            "Reserva de curta duração: só os dados exigidos para o "
            "boletim de alojamento.",
            self._abrir_airbnb,
        )

        ctk.CTkButton(
            self,
            text="Cancelar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(6, 20))

    def _cartao(self, titulo, descricao, ao_clicar):
        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            cartao,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            cartao,
            text=descricao,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=300,
        ).pack(fill="x", padx=14, pady=(0, 12))

        componentes.tornar_cliclavel(cartao, ao_clicar)

    def _abrir_mensal(self):
        self.destroy()
        NovoClienteMensalModal(self.tela_lista)

    def _abrir_airbnb(self):
        self.destroy()
        NovoClienteAirbnbModal(self.tela_lista)


class AvisoPrivacidadeClienteModal(ctk.CTkToplevel):
    """Regista a entrega do aviso de privacidade a um cliente que já
    existe (v1.9.0, bloco D) — clientes de antes da v1.9.0, ou uma
    versão nova do texto entretanto publicada. Mesmo bloco do Novo
    Cliente; o "Registar" fica trancado até a caixa ser marcada."""

    def __init__(self, tela_lista, cliente):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.cliente = cliente

        try:
            estado = termos.verificar(
                termos.TITULAR_CLIENTE,
                cliente["id"],
                termos.PRIVACIDADE_HOSPEDE,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            self.after(0, self.destroy)
            return

        self.title(f"Aviso de privacidade — {cliente['id']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Aviso de privacidade",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=f"{cliente['nome']} — {cliente['id']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 12))

        self.bloco, self.suporte = _bloco_aviso_hospede(
            self, estado["texto"], ao_mudar=self._ao_mudar, estado=estado
        )
        self.bloco.configure(width=460)
        self.bloco.pack(fill="x", padx=24)

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 20))
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
        self.botao_registar = ctk.CTkButton(
            rodape,
            text="Registar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.COR_BORDA,
            hover_color=tema.AZUL_CLARO,
            text_color_disabled=tema.TEXTO_INDISPONIVEL,
            state="disabled",
            command=self._registar,
        )
        self.botao_registar.pack(side="right")

    def _ao_mudar(self):
        aceite = self.bloco.esta_aceite()
        self.botao_registar.configure(
            state="normal" if aceite else "disabled",
            fg_color=tema.AZUL_PRINCIPAL if aceite else tema.COR_BORDA,
        )

    def _registar(self):
        if not self.bloco.esta_aceite():
            return

        try:
            versao = termos.registar(
                termos.TITULAR_CLIENTE,
                self.cliente["id"],
                termos.PRIVACIDADE_HOSPEDE,
                registado_por_id=_id_responsavel_ativo(),
                suporte=self.suporte(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Aviso de privacidade registado para {self.cliente['id']} "
            f"(versão {versao})."
        )
        self.destroy()


class _FormularioCliente(ctk.CTkToplevel):
    """Base comum aos modais de cliente — monta a moldura (título,
    geometria, cartão com CTkScrollableFrame, rodapé Cancelar/
    Guardar) e os helpers de campo (`_campo_texto`, `_campo_dropdown`,
    `_campo_nacionalidade`). Cada subclasse constrói os SEUS campos
    depois de `super().__init__(...)`, na ordem que quiser.

    REESTRUTURAÇÃO 16/09/2026 (decisão do aluno, mockup HTML
    aprovado): antes desenhava sempre os mesmos 13 campos + seletor
    de Regime. Passou a existir um seletor prévio (Mensal/Airbnb, ver
    `_SeletorRegimeClienteModal`) que já abre o modal certo —
    `NovoClienteMensalModal` e `NovoClienteAirbnbModal` têm cada um o
    seu conjunto de campos, por isso esta base deixou de impor uma
    lista fixa. `EditarClienteModal` continua com o conjunto completo
    de sempre (ver a própria docstring dessa classe).
    """

    def __init__(self, tela_lista, titulo, largura=620, altura=700):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title(titulo)
        self.geometry(f"{largura}x{altura}")
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
        self._area = area
        self._bloco_aviso = None
        self._suporte_aviso = None

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
        combo = componentes.Seletor(self.corpo, values=list(valores))
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

        combo = componentes.Seletor(
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

    # -- aviso de privacidade (v1.9.0, bloco D) -----------------------

    def _montar_aviso_privacidade(self):
        """Segundo cartão, por baixo dos campos, com o aviso ao
        hóspede. Só os modais de CRIAÇÃO o chamam (o Editar não —
        os clientes já existentes registam em Gerir). O Guardar fica
        trancado até a caixa ser marcada."""
        cartao = ctk.CTkFrame(
            self._area,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", pady=(0, 12))

        try:
            texto = termos.texto_em_vigor(termos.PRIVACIDADE_HOSPEDE)
        except ValueError as erro:
            # Sem texto publicado não há o que entregar: avisa e
            # mantém o Guardar trancado (erro de configuração).
            ctk.CTkLabel(
                cartao,
                text=(
                    f"{erro}\nPublica-o em Configurações → Sistema → "
                    f"Documentos legais."
                ),
                text_color=tema.TEXTO_AVISO,
                fg_color=tema.AMARELO_AVISO,
                corner_radius=6,
                font=ctk.CTkFont(size=11),
                anchor="w",
                justify="left",
                wraplength=480,
            ).pack(fill="x", padx=12, pady=12)
            self._ao_mudar_aviso()
            return

        self._bloco_aviso, self._suporte_aviso = _bloco_aviso_hospede(
            cartao, texto, ao_mudar=self._ao_mudar_aviso
        )
        self._bloco_aviso.pack(fill="x", padx=12, pady=12)
        self._ao_mudar_aviso()

    def _aviso_confirmado(self):
        return (
            self._bloco_aviso is not None and self._bloco_aviso.esta_aceite()
        )

    def _ao_mudar_aviso(self):
        confirmado = self._aviso_confirmado()
        self.botao_guardar.configure(
            state="normal" if confirmado else "disabled",
            fg_color=tema.AZUL_PRINCIPAL if confirmado else tema.COR_BORDA,
        )

    def _registar_aviso(self, cliente):
        """Regista a entrega do aviso a um cliente acabado de criar.

        Corre DEPOIS do `clientes.criar` (antes não há ID). Se falhar,
        o cliente fica gravado e o aviso "por registar" no Gerir —
        devolve o texto a juntar à mensagem de sucesso; senão "".
        """
        try:
            versao = termos.registar(
                termos.TITULAR_CLIENTE,
                cliente["id"],
                termos.PRIVACIDADE_HOSPEDE,
                registado_por_id=_id_responsavel_ativo(),
                suporte=self._suporte_aviso(),
            )
        except ValueError as erro:
            return (
                f"\n\nAtenção: o aviso de privacidade NÃO ficou "
                f"registado ({erro}). Regista-o em Gerir → Aviso de "
                f"privacidade."
            )

        return f"\nAviso de privacidade registado (versão {versao})."

    # -- submissão ----------------------------------------------------

    def _guardar(self):
        raise NotImplementedError


class NovoClienteMensalModal(_FormularioCliente):
    """Modal de criação de um cliente Mensal.

    REGRA 16/09/2026 (aluno): tudo obrigatório, exceto Email e
    Contacto de emergência — inclui Nacionalidade e Telefone, que
    antes (decisão de 26/08) eram opcionais no regime mensal e
    passaram a obrigatórios. Ver `validacoes.validar_cliente`.
    """

    def __init__(self, tela_lista):
        super().__init__(
            tela_lista, "Novo Cliente Mensal", largura=620, altura=720
        )

        self.campo_nome = self._campo_texto("Nome completo *")
        self.combo_tipo_documento = self._campo_dropdown(
            "Tipo de documento *", validacoes.TIPOS_DOCUMENTO
        )
        self.campo_numero_documento = self._campo_texto(
            "Número de documento *"
        )
        self.campo_nif = self._campo_texto("NIF *")
        self.campo_morada = self._campo_texto("Morada *")
        self.combo_estado_civil = self._campo_dropdown(
            "Estado civil *", validacoes.TIPOS_ESTADO_CIVIL
        )
        self.campo_nacionalidade, self.combo_nacionalidade = (
            self._campo_nacionalidade()
        )
        self.campo_telefone = self._campo_texto("Telefone *")
        self.campo_data_nascimento = self._campo_texto(
            "Data de nascimento *", placeholder="dd/mm/aaaa"
        )
        self.campo_validade_documento = self._campo_texto(
            "Validade do documento *", placeholder="dd/mm/aaaa"
        )
        self.campo_email = self._campo_texto("Email")
        self.campo_contacto_emergencia = self._campo_texto(
            "Contacto de emergência"
        )
        self._montar_aviso_privacidade()

    def _guardar(self):
        if not self._aviso_confirmado():
            componentes.mostrar_erro(
                "Confirma que entregaste o aviso de privacidade ao cliente."
            )
            return

        try:
            data_nascimento = _ler_data(
                self.campo_data_nascimento.get(), "Data de nascimento"
            )
            validade_documento = _ler_data(
                self.campo_validade_documento.get(),
                "Validade do documento",
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        # O formato do email é validado em `clientes.criar`
        # (validacoes.validar_cliente) — v1.7.0.
        email = self.campo_email.get().strip()

        try:
            cliente = clientes.criar(
                self.campo_nome.get(),
                self.combo_tipo_documento.get(),
                self.campo_numero_documento.get(),
                "mensal",
                nif=self.campo_nif.get(),
                email=email,
                telefone=self.campo_telefone.get(),
                morada=self.campo_morada.get(),
                nacionalidade=self.campo_nacionalidade.get(),
                estado_civil=self.combo_estado_civil.get(),
                data_nascimento=data_nascimento,
                validade_documento=validade_documento,
                contacto_emergencia=self.campo_contacto_emergencia.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        nota_aviso = self._registar_aviso(cliente)
        componentes.mostrar_sucesso(
            f"Cliente criado com sucesso: {cliente['id']}{nota_aviso}"
        )
        self.destroy()
        _recarregar_tela_lista(self.tela_lista)


class NovoClienteAirbnbModal(_FormularioCliente):
    """Modal de criação de um cliente Airbnb.

    REGRA 16/09/2026 (aluno): só os 7 campos que o boletim de
    alojamento exige — nome, nacionalidade, data de nascimento, tipo/
    número de documento, país emissor do documento e país de
    residência, todos obrigatórios. NIF, morada, estado civil,
    validade do documento, telefone, email e contacto de emergência
    não fazem parte deste regime — ficam de fora do modal.

    'País emissor do documento' e 'País de residência' são texto
    livre (sem lista de países pré-definida, ao contrário da
    Nacionalidade) — simplificação deliberada para não duplicar uma
    segunda lista de países só para estes dois campos.
    """

    def __init__(self, tela_lista):
        super().__init__(
            tela_lista, "Novo Cliente Airbnb", largura=600, altura=680
        )

        self.campo_nome = self._campo_texto("Nome completo *")
        self.campo_nacionalidade, self.combo_nacionalidade = (
            self._campo_nacionalidade()
        )
        self.campo_data_nascimento = self._campo_texto(
            "Data de nascimento *", placeholder="dd/mm/aaaa"
        )
        self.combo_tipo_documento = self._campo_dropdown(
            "Tipo de documento *", validacoes.TIPOS_DOCUMENTO
        )
        self.campo_numero_documento = self._campo_texto(
            "Número de documento *"
        )
        self.campo_pais_emissor = self._campo_texto(
            "País emissor do documento *", placeholder="ex.: Portugal"
        )
        self.campo_pais_residencia = self._campo_texto(
            "País de residência *", placeholder="ex.: Portugal"
        )
        self._montar_aviso_privacidade()

    def _guardar(self):
        if not self._aviso_confirmado():
            componentes.mostrar_erro(
                "Confirma que entregaste o aviso de privacidade ao cliente."
            )
            return

        try:
            data_nascimento = _ler_data(
                self.campo_data_nascimento.get(), "Data de nascimento"
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            cliente = clientes.criar(
                self.campo_nome.get(),
                self.combo_tipo_documento.get(),
                self.campo_numero_documento.get(),
                "airbnb",
                nacionalidade=self.campo_nacionalidade.get(),
                data_nascimento=data_nascimento,
                pais_emissor_documento=self.campo_pais_emissor.get(),
                pais_residencia=self.campo_pais_residencia.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        nota_aviso = self._registar_aviso(cliente)
        componentes.mostrar_sucesso(
            f"Cliente criado com sucesso: {cliente['id']}{nota_aviso}"
        )
        self.destroy()
        _recarregar_tela_lista(self.tela_lista)


class EditarClienteModal(_FormularioCliente):
    """Modal de edição de um cliente existente — os mesmos 13 campos
    + seletor de Regime de sempre (formulário único, inalterado
    desde 06/09/2026), pré-preenchidos.

    ÂMBITO 16/09/2026: a divisão em dois modais dedicados
    (`NovoClienteMensalModal`/`NovoClienteAirbnbModal`) ficou só na
    criação — a edição continua com o formulário único, por decisão
    do aluno ("fico só com Novo Cliente nesta entrega"). Por isso
    NÃO tem campos de País emissor do documento / País de
    residência: ficam inalterados ao editar (ver
    `clientes.atualizar`). Um cliente Airbnb criado só depois desta
    data já os tem gravados; um cliente Airbnb anterior a esta data
    continua sem eles preenchidos, e `validacoes.validar_cliente` vai
    recusar a edição desse cliente específico enquanto os dois
    campos não tiverem conteúdo — pendência registada, não bloqueia
    clientes Mensais nem Airbnb já criados com os campos novos.

    'Regime' não vem gravado no cliente (ver docstring de
    `clientes.criar`) — arranca em "Mensal" se o cliente já tiver
    NIF preenchido (sinal de que foi criado nesse regime), senão
    "Airbnb". É só um valor por omissão: o utilizador pode trocá-lo
    antes de guardar, se o regime real for outro.
    """

    def __init__(self, tela_lista, cliente):
        super().__init__(
            tela_lista,
            f"Editar Cliente — {cliente['nome']}",
            largura=620,
            altura=700,
        )
        self.cliente = cliente

        self.campo_nome = self._campo_texto("Nome completo *")
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

        self.campo_nome.insert(0, cliente["nome"])
        self.combo_tipo_documento.set(cliente["tipo_documento"])
        self.campo_numero_documento.insert(0, cliente["numero_documento"])
        self.combo_regime.set(
            "Mensal"
            if clientes.tipo(cliente) == clientes.TIPO_MENSAL
            else "Airbnb"
        )
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

    def _regime_selecionado(self):
        return "mensal" if self.combo_regime.get() == "Mensal" else "airbnb"

    def _ler_campos_comuns(self):
        """Lê e valida (formato, não regra de negócio) os campos do
        formulário. As datas são as únicas que podem levantar
        ValueError aqui — o resto só é validado pela camada de
        negócio, ao submeter.
        """
        data_nascimento = _ler_data(
            self.campo_data_nascimento.get(), "Data de nascimento"
        )
        validade_documento = _ler_data(
            self.campo_validade_documento.get(), "Validade do documento"
        )

        # Formato do email: validado em `clientes.atualizar`.
        email = self.campo_email.get().strip()

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
        # Mesma defesa do `NovoClienteMensalModal._guardar` — ver
        # `_recarregar_tela_lista`, no topo do módulo. Hoje o
        # "Editar" só é aberto a partir da `ListaClientes`, mas a
        # defesa fica para o caso de o botão se estender aos
        # contratos no futuro.
        _recarregar_tela_lista(self.tela_lista)


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

        # 26/09/2026 — só um Master autoriza (regra em
        # clientes.anonimizar); o combo só mostra Masters.
        self.responsaveis_disponiveis = [
            r
            for r in responsaveis.listar()
            if r["tipo_utilizador"] == "Master"
        ]
        nomes = ["Nenhum"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel = componentes.Seletor(self, values=nomes)
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
