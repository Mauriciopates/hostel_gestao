"""Ecrã "Planta de Lugares": mostra visualmente os quartos e lugares
de uma unidade mensal, com o estado de ocupação de cada lugar à
data de hoje — e permite criar, editar, desativar e reativar quartos
e lugares sem sair do ecrã.

Cada lugar aparece como uma caixa cujo tamanho depende do
'tipo_cama' — maior para "casal", pequena para "solteiro". As caixas
de "beliche" aparecem em pares empilhados, porque um beliche físico
são sempre dois lugares distintos de capacidade 1 cada, nunca um só
de capacidade 2 (decisão 17); esse emparelhamento é só visual — sem
nenhum campo na base de dados que ligue formalmente as duas camas
de um beliche, agrupa pela palavra de lado no nome ("esquerdo" com
"esquerdo", "direito" com "direito") quando existe, e cai para a
ordem de chegada quando não existe (ex.: "Beliche cima"/"Beliche
baixo") — ver `_chave_lado` e `_agrupar_para_planta`.

A capacidade nunca deriva do tipo de cama: continua um campo à
parte (decisão 17), por isso um lugar de casal com capacidade 2
pode mostrar dois ocupantes na mesma caixa.

Um lugar sem ocupante atual mas já com um contrato futuro registado
(início ainda por chegar) aparece como "Reservado", em cinzento —
indisponibilidade, distinta tanto do aviso/parcial (amarelo) como
do erro/ocupado (vermelho) — em vez de "Livre".

Só se aplica a unidades do regime mensal — uma reserva Airbnb ocupa
a unidade inteira, sem 'lugar_id' (decisão 5), por isso não há
estado de ocupação por lugar para mostrar numa unidade Airbnb.

Clique — cada ação tem o seu sítio próprio, sem se cruzarem:

- ⋮ (canto inferior direito)  → abre o Gerir lugar (editar /
  desativar / reativar). O ⋮ não está no percurso de clique do
  corpo da caixa, por isso o clique nele nunca dispara a ação do
  estado.
- Corpo da caixa (nome, estado, nomes dos ocupantes):
    Livre     → pergunta "Deseja criar um contrato mensal neste
                lugar?" e, se sim, abre o Novo Contrato Mensal já
                pré-preenchido.
    Reservado → abre o Detalhe do lugar, com chip amarelo e faixa
                amarela a avisar da reserva futura.
    Ocupado   → abre o Detalhe do lugar, com chip vermelho.

ACRESCENTADO 11/09/2026 — gestão completa a partir deste ecrã:

- Botão "+ Novo quarto" no topo, com popup "Deseja criar lugares?"
  a seguir (opção A: quarto e lugares são operações independentes
  — se o utilizador cancelar o 2º lugar, o quarto fica criado).
- Botões "+ Novo lugar" e "Gerir quarto" no rodapé de cada cartão
  de quarto.
- Botão ⋮ no canto inferior direito de cada caixa de lugar, que
  abre o modal "Gerir lugar".
- Modais Editar Quarto, Editar Lugar, Detalhe do lugar (Ocupado e
  Reservado) e Confirmar Criação de Contrato — todos no padrão de
  modais da aplicação (título, campos, rodapé com Cancelar/ação).

ALTERAÇÕES 11/09/2026 (ronda seguinte, aprovada por mockup HTML):

- `_DetalheOcupadoModal` passou a `_DetalheLugarModal` e serve os
  dois estados — Ocupado (chip vermelho, sem faixa) e Reservado
  (chip amarelo + faixa amarela "Reservado para dd/mm/aaaa"). O
  botão principal é "Abrir contrato" nos dois casos.
- Caixa Reservado deixa de abrir o Novo Contrato Mensal
  pré-preenchido: passa a abrir o Detalhe do lugar, com o aviso
  da reserva — antes, clicar abria o formulário de criação como
  se o lugar estivesse livre, o que contradizia a informação
  mostrada na própria caixa.
- Clique no ⋮ e clique no corpo deixam de competir: o ⋮ abre só
  o Gerir lugar; o corpo abre a ação do estado. `_tornar_clicavel`
  passou a ser chamado só nos filhos do `conteudo`, nunca na
  `caixa` nem no próprio `conteudo` — o ⋮ fica naturalmente fora
  do percurso do clique do corpo, sem precisar de `"break"` nem
  de listas de exclusão.
- Botões dos modais `_NovoQuartoModal`, `_NovoLugarModal`,
  `_GerirQuartoModal` e `_GerirLugarModal` passam a ter a mesma
  receita do `_EditarQuartoModal` (que estava correto): `width`
  fixa, `height=34`, sem `pady` vertical — antes ficavam
  encolhidos ao lado dos campos.
- Botões "Abrir contrato" e "Fechar" do `_DetalheLugarModal`
  passam a ter largura fixa, um à esquerda e um à direita — antes
  estavam com `expand=True` e `fill="x"` e ficavam esticados de
  ponta a ponta como uma barra.
- Janela do `_DetalheLugarModal` passa de 520x420 para 560x480 — o
  conteúdo no caso Reservado (chip + faixa amarela + cartão do
  contrato) ficava apertado. Aplica-se aos dois estados, para a
  janela não mudar de tamanho entre um e outro.

CONSOLIDAÇÃO DE HELPERS EM componentes.py (13/09/2026) — os
helpers visuais duplicados localmente passaram a viver só no
`componentes.py`:

- `_tornar_clicavel` local → `componentes.tornar_cliclavel`.
- O resto do ficheiro não mudou.

Segue a mesma separação de camadas do resto do sistema (decisão 7):
só fala com `unidades`, `contratos` e `clientes` — nunca com
`repositorio` diretamente.
"""

from datetime import date

import customtkinter as ctk

import clientes
import contratos
import unidades
from . import componentes
from . import tema
from .gui_contratos import NovoContratoMensal

# Alias local para o helper que vivia neste ficheiro e passou a
# viver em componentes.py. Mantém-se o nome antigo com "_" para o
# corpo do ficheiro não ter de ser reescrito — mesma técnica já
# usada no gui_propriedades.py, gui_contratos.py, gui_calendario.py e
# gui_est_requisicoes.py.
_tornar_clicavel = componentes.tornar_cliclavel


LARGURA_CAIXA = {
    "solteiro": 120,
    "casal": 190,
    "beliche": 120,
}

ALTURA_CAIXA = {
    "solteiro": 130,
    "casal": 160,
    "beliche": 74,
}

# Número máximo de caracteres de um nome (lugar ou ocupante) em cada
# tipo de caixa, antes de cortar com reticências (_truncar) — evita
# que um nome comprido transborde para fora de uma caixa estreita.
LIMITE_CARATERES = {
    "solteiro": 20,
    "casal": 26,
    "beliche": 18,
}

# Receita única dos botões de rodapé dos modais de formulário
# (Novo Quarto, Novo Lugar, Gerir Quarto, Gerir Lugar, Editar
# Quarto, Editar Lugar). Estavam minúsculos porque ficavam com
# `pady` vertical a comprimir e sem `width` explícito; agora usam
# a mesma receita do `_EditarQuartoModal`, que já estava correta.
_LARGURA_BOTAO_MODAL = 150
_ALTURA_BOTAO_MODAL = 34

# Botões do rodapé do Detalhe do lugar — um à esquerda, um à
# direita, ambos com a mesma largura fixa. Sem `expand=True` nem
# `fill="x"`, que os esticavam de ponta a ponta como uma barra.
_LARGURA_BOTAO_DETALHE = 150

# Geometria da janela do Detalhe do lugar. Passou de 520x420 para
# 560x480 (11/09/2026) — o conteúdo no caso Reservado (chip amarelo
# + faixa amarela + cartão do contrato) ficava apertado, e a faixa
# amarela em particular encostava às bordas. Aumentada para os dois
# estados para a janela não mudar de tamanho entre um e outro.
_LARGURA_DETALHE = 560
_ALTURA_DETALHE = 480


def _chave_lado(nome):
    """Procura "esquerdo"/"direito" (ou variações, ex. "esquerda")
    no nome do lugar.

    Devolve "esquerdo", "direito" ou None se o nome não indicar
    lado nenhum — usado para emparelhar beliches por lado, em vez
    de só pela ordem de inserção.
    """
    nome_lower = nome.lower()

    if "esquerd" in nome_lower:
        return "esquerdo"

    if "direit" in nome_lower:
        return "direito"

    return None


def _ordenar_par(par):
    """Dentro de um par de beliche, põe quem tem "inferior" no nome
    sempre em baixo — independente da ordem em que os lugares foram
    cadastrados.
    """

    def peso(lugar):
        return 1 if "inferior" in lugar["nome"].lower() else 0

    return tuple(sorted(par, key=peso))


def _agrupar_para_planta(lugares):
    """Agrupa os lugares de um quarto nas unidades visuais da planta.

    Um lugar de "solteiro" ou "casal" forma o seu próprio grupo, com
    uma caixa só. Os de "beliche" são emparelhados dois a dois — por
    palavra de lado no nome quando existe; os restantes são
    emparelhados pela ordem em que chegam. Um beliche que sobre
    sozinho fica num grupo de um, para não desaparecer da planta.

    Devolve uma lista de tuplos: (lugar,) ou (lugar_cima, lugar_baixo).
    """
    grupos = []
    soltos = []
    por_lado = {"esquerdo": [], "direito": []}

    for lugar in lugares:
        if lugar["tipo_cama"] != "beliche":
            grupos.append((lugar,))
            continue

        lado = _chave_lado(lugar["nome"])

        if lado is not None:
            por_lado[lado].append(lugar)
        else:
            soltos.append(lugar)

    for lado in ("esquerdo", "direito"):
        pendente = None

        for lugar in por_lado[lado]:
            if pendente is None:
                pendente = lugar
            else:
                grupos.append(_ordenar_par((pendente, lugar)))
                pendente = None

        if pendente is not None:
            grupos.append((pendente,))

    pendente = None

    for lugar in soltos:
        if pendente is None:
            pendente = lugar
        else:
            grupos.append(_ordenar_par((pendente, lugar)))
            pendente = None

    if pendente is not None:
        grupos.append((pendente,))

    return grupos


def _ocupantes_atuais(ocupacoes_mensais, lugar_id, hoje):
    """Filtra as ocupações mensais em vigor no lugar indicado, na
    data indicada.
    """
    atuais = []

    for ocupacao in ocupacoes_mensais:
        if ocupacao["lugar_id"] != lugar_id:
            continue

        if ocupacao["data_inicio"] > hoje:
            continue

        if ocupacao["data_fim"] is not None and ocupacao["data_fim"] <= hoje:
            continue

        atuais.append(ocupacao)

    return atuais


def _proxima_reserva(ocupacoes_mensais, lugar_id, hoje):
    """Devolve a ocupação futura mais próxima desse lugar, ou None."""
    futuras = [
        o
        for o in ocupacoes_mensais
        if o["lugar_id"] == lugar_id and o["data_inicio"] > hoje
    ]

    if not futuras:
        return None

    return min(futuras, key=lambda o: o["data_inicio"])


def _nomes_ocupantes(ocupacoes):
    """Devolve os nomes dos clientes de uma lista de ocupações."""
    nomes = []

    for ocupacao in ocupacoes:
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nomes.append(cliente["nome"] if cliente else "Cliente desconhecido")

    return nomes


def _estado_ocupacao(total_ocupantes, capacidade, tem_reserva_futura):
    """Classifica a ocupação de um lugar em livre / reservado /
    parcial / ocupado.
    """
    if total_ocupantes == 0:
        return "reservado" if tem_reserva_futura else "livre"

    if total_ocupantes < capacidade:
        return "parcial"

    return "ocupado"


def _texto_estado(estado, ocupantes, capacidade, reserva):
    """Formata a linha de estado da caixa."""
    if estado == "livre":
        return "Livre"

    if estado == "reservado" and reserva is not None:
        data = reserva["data_inicio"].strftime("%d/%m/%Y")
        return f"Reservado · {data}"

    rotulo = "Ocupado" if estado == "ocupado" else "Parcial"
    return f"{rotulo} · {len(ocupantes)}/{capacidade}"


def _truncar(texto, limite):
    """Corta um texto no limite indicado, com reticências."""
    if len(texto) <= limite:
        return texto

    return texto[: limite - 1] + "…"


def _cores_estado(estado):
    """Devolve (cor_fundo, cor_texto) da caixa."""
    if estado == "livre":
        return tema.COR_FUNDO, tema.VERDE

    if estado == "parcial":
        return tema.AMARELO_AVISO, tema.TEXTO_AVISO

    if estado == "reservado":
        return tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL

    return tema.VERMELHO_ERRO, tema.TEXTO_ERRO


class PlantaLugares(ctk.CTkFrame):
    """Ecrã da planta de lugares de uma unidade mensal.

    Recebe 'unidade_id' opcional (kwarg de `controlador.mostrar_frame`)
    — sem ele, abre na primeira unidade mensal ativa encontrada.
    """

    def __init__(self, master, controlador, unidade_id=None):
        super().__init__(master, fg_color=tema.COR_FUNDO)

        self.controlador = controlador
        self.unidade_id = unidade_id
        self._opcoes_unidade = {}  # rótulo mostrado -> id da unidade

        componentes.Cabecalho(self, titulo="Planta de Lugares").pack(fill="x")

        self._montar_barra_unidade()

        self.area_planta = ctk.CTkScrollableFrame(
            self, fg_color=tema.COR_FUNDO
        )
        self.area_planta.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._recarregar_unidades()

    # -- barra de unidade (topo) -------------------------------------

    def _montar_barra_unidade(self):
        barra = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO)
        barra.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(
            barra,
            text="Unidade:",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        self.seletor_unidade = ctk.CTkOptionMenu(
            barra,
            values=["Sem unidades mensais"],
            command=self._ao_escolher_unidade,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.AZUL_PRINCIPAL,
            button_color=tema.AZUL_PRINCIPAL,
            button_hover_color=tema.AZUL_CLARO,
        )
        self.seletor_unidade.pack(side="left")

        ctk.CTkButton(
            barra,
            text="Atualizar",
            width=90,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._recarregar_unidades,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            barra,
            text="+ Novo quarto",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _NovoQuartoModal(self),
        ).pack(side="right")

    # -- carregamento da lista de unidades --------------------------

    def _recarregar_unidades(self):
        """Lê as unidades mensais ativas e povoa o seletor."""
        unidades_mensais = unidades.listar(tipo="mensal")

        self._opcoes_unidade = {
            f"{u['nome']} ({u['id']})": u["id"] for u in unidades_mensais
        }

        if not self._opcoes_unidade:
            self.seletor_unidade.configure(
                values=["Sem unidades mensais"], state="disabled"
            )
            self.seletor_unidade.set("Sem unidades mensais")
            self.unidade_id = None
            self._desenhar_planta()
            return

        self.seletor_unidade.configure(
            values=list(self._opcoes_unidade), state="normal"
        )

        if self.unidade_id not in self._opcoes_unidade.values():
            self.unidade_id = next(iter(self._opcoes_unidade.values()))

        rotulo_atual = next(
            rotulo
            for rotulo, id_unidade in self._opcoes_unidade.items()
            if id_unidade == self.unidade_id
        )
        self.seletor_unidade.set(rotulo_atual)

        self._desenhar_planta()

    def _ao_escolher_unidade(self, rotulo):
        """Chamada pelo CTkOptionMenu quando a escolha muda."""
        self.unidade_id = self._opcoes_unidade.get(rotulo)
        self._desenhar_planta()

    # -- abertura de contrato (a partir de uma caixa) ----------------

    def _pedir_contrato(self, lugar_id):
        """Pergunta se quer criar contrato, e se sim, abre o
        formulário. Chamada só para caixas Livres.
        """
        if not componentes.confirmar(
            f"Deseja criar um contrato mensal neste lugar " f"({lugar_id})?",
            titulo="Lugar disponível",
        ):
            return

        self._abrir_contrato(lugar_id)

    def _abrir_contrato(self, lugar_id):
        """Abre o Novo Contrato Mensal já pré-preenchido com a
        unidade atual e o lugar clicado.
        """
        self.controlador.mostrar_frame(
            NovoContratoMensal,
            unidade_id=self.unidade_id,
            lugar_id=lugar_id,
        )

    # -- desenho da planta ------------------------------------------

    def _limpar_planta(self):
        for widget in self.area_planta.winfo_children():
            widget.destroy()

    def _mostrar_mensagem(self, texto):
        ctk.CTkLabel(
            self.area_planta,
            text=texto,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=13),
        ).pack(pady=40)

    def _desenhar_planta(self):
        """Redesenha a planta inteira da unidade selecionada."""
        self._limpar_planta()

        if self.unidade_id is None:
            self._mostrar_mensagem(
                "Ainda não existem unidades mensais ativas."
            )
            return

        unidade = unidades.procurar(self.unidade_id)

        if unidade is None or not unidade["ativo"]:
            self._mostrar_mensagem(
                "A unidade selecionada já não está disponível."
            )
            return

        if unidade["tipo"] != "mensal":
            self._mostrar_mensagem(
                "A planta de lugares aplica-se apenas a unidades do "
                "regime mensal."
            )
            return

        quartos = unidades.listar_quartos(unidade_id=self.unidade_id)

        if not quartos:
            self._mostrar_mensagem(
                "Esta unidade ainda não tem quartos. "
                'Use o botão "+ Novo quarto" para criar o primeiro.'
            )
            return

        ocupacoes_mensais = contratos.listar(
            unidade_id=self.unidade_id, tipo="mensal"
        )
        hoje = date.today()

        for quarto in quartos:
            self._desenhar_quarto(quarto, ocupacoes_mensais, hoje)

    def _desenhar_quarto(self, quarto, ocupacoes_mensais, hoje):
        """Desenha o cartão de um quarto: cabeçalho com o nome e os
        indicadores, fila de caixas de lugares, e rodapé com os
        botões de criação/gestão.
        """
        cartao = ctk.CTkFrame(
            self.area_planta,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", pady=(0, 16))

        # Cabeçalho
        cabecalho_quarto = ctk.CTkFrame(cartao, fg_color="transparent")
        cabecalho_quarto.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            cabecalho_quarto,
            text=quarto["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        indicador = "Privativo" if quarto["privativo"] else "Partilhado"
        ctk.CTkLabel(
            cabecalho_quarto,
            text=f"· {indicador}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(8, 0))

        if quarto["limpeza_incluida"]:
            ctk.CTkLabel(
                cabecalho_quarto,
                text="· Limpeza incluída",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=(8, 0))

        # Corpo com as caixas — scroll horizontal próprio do cartão
        linha_lugares = ctk.CTkFrame(cartao, fg_color="transparent")
        linha_lugares.pack(fill="x", padx=16, pady=(4, 12))

        lugares = unidades.listar_lugares(quarto_id=quarto["id"])

        if not lugares:
            ctk.CTkLabel(
                linha_lugares,
                text="Sem lugares cadastrados.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
            ).pack(side="left")
        else:
            for grupo in _agrupar_para_planta(lugares):
                if len(grupo) == 2:
                    self._desenhar_beliche(
                        linha_lugares, grupo, ocupacoes_mensais, hoje
                    )
                else:
                    self._desenhar_caixa(
                        linha_lugares, grupo[0], ocupacoes_mensais, hoje
                    )

        # Rodapé com os dois botões
        rodape = ctk.CTkFrame(cartao, fg_color="transparent")
        rodape.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            rodape,
            text="+ Novo lugar",
            width=120,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _NovoLugarModal(self, quarto),
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Gerir quarto",
            width=120,
            height=28,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=lambda: _GerirQuartoModal(self, quarto),
        ).pack(side="left", padx=(8, 0))

    # -- desenho de uma caixa (solteiro/casal) ----------------------

    def _desenhar_caixa(self, master, lugar, ocupacoes_mensais, hoje):
        """Desenha a caixa de um lugar "solteiro" ou "casal".

        Estrutura de clique:
        - O ⋮ é colocado com `.place()` na `caixa` (não no
          `conteudo`), por isso fica fora do percurso de clique do
          corpo — o seu `command` abre só o Gerir lugar.
        - O corpo (`conteudo` e os seus filhos) é ligado ao
          `_tornar_clicavel` só depois de tudo montado, para a ação
          do estado. O `conteudo` e a `caixa` NÃO são ligados,
          para não haver dois sítios a disparar a mesma coisa.
        """
        ocupantes = _ocupantes_atuais(ocupacoes_mensais, lugar["id"], hoje)
        reserva = _proxima_reserva(ocupacoes_mensais, lugar["id"], hoje)
        estado = _estado_ocupacao(
            len(ocupantes), lugar["capacidade"], reserva is not None
        )
        cor_fundo, cor_texto = _cores_estado(estado)

        largura = LARGURA_CAIXA[lugar["tipo_cama"]]
        limite_nomes = LIMITE_CARATERES[lugar["tipo_cama"]]

        caixa = ctk.CTkFrame(
            master,
            width=largura,
            height=ALTURA_CAIXA[lugar["tipo_cama"]],
            fg_color=cor_fundo,
            border_width=2,
            border_color=cor_texto,
            corner_radius=tema.RAIO_CAMPO,
        )
        caixa.pack(side="left", padx=10, pady=10)
        caixa.pack_propagate(False)

        conteudo = ctk.CTkFrame(caixa, fg_color="transparent")
        conteudo.pack(expand=True, fill="both", padx=10, pady=8)

        etiqueta_nome = ctk.CTkLabel(
            conteudo,
            text=_truncar(lugar["nome"], limite_nomes),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=largura - 30,
        )
        etiqueta_nome.pack(pady=(0, 4))

        etiqueta_estado = ctk.CTkLabel(
            conteudo,
            text=_texto_estado(
                estado, ocupantes, lugar["capacidade"], reserva
            ),
            text_color=cor_texto,
            font=ctk.CTkFont(size=10),
            wraplength=largura - 30,
        )
        etiqueta_estado.pack(pady=(0, 4))

        etiquetas_ocupantes = []

        for nome in _nomes_ocupantes(ocupantes):
            etiqueta = ctk.CTkLabel(
                conteudo,
                text=_truncar(nome, limite_nomes),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=9),
                wraplength=largura - 30,
            )
            etiqueta.pack()
            etiquetas_ocupantes.append(etiqueta)

        # Botão ⋮ — colocado na `caixa` (fora do `conteudo`), por
        # isso o clique nele não passa pelo binding do corpo.
        self._botao_tres_pontos(caixa, lugar)

        # Clique no corpo — só nas etiquetas dentro do `conteudo`.
        # O `conteudo` em si e a `caixa` não são ligados, para não
        # haver dois sítios com o mesmo binding (o clique no ⋮ fica
        # fora do percurso, porque está na `caixa` e não no
        # `conteudo`).
        widgets_corpo = [etiqueta_nome, etiqueta_estado] + etiquetas_ocupantes

        if estado == "livre":
            for widget in widgets_corpo:
                _tornar_clicavel(
                    widget,
                    lambda lugar_id=lugar["id"]: self._pedir_contrato(
                        lugar_id
                    ),
                )
        elif estado == "reservado":
            for widget in widgets_corpo:
                _tornar_clicavel(
                    widget,
                    lambda lugar=lugar, reserva=reserva, estado=estado: (
                        _DetalheLugarModal(self, lugar, reserva, estado)
                    ),
                )
        elif estado == "ocupado":
            for widget in widgets_corpo:
                _tornar_clicavel(
                    widget,
                    lambda lugar=lugar, ocupantes=ocupantes, estado=estado: (
                        _DetalheLugarModal(self, lugar, ocupantes[0], estado)
                    ),
                )

    def _desenhar_beliche(self, master, par, ocupacoes_mensais, hoje):
        """Desenha um par de lugares "beliche" como duas caixas
        pequenas empilhadas dentro de um contentor comum.

        Mesma estrutura de clique da `_desenhar_caixa`: o ⋮ fica na
        `caixa`, fora do `conteudo`; o corpo (etiquetas dentro do
        `conteudo`) é que reage à ação do estado.
        """
        contentor = ctk.CTkFrame(master, fg_color="transparent")
        contentor.pack(side="left", padx=10, pady=10)

        largura = LARGURA_CAIXA["beliche"]
        limite = LIMITE_CARATERES["beliche"]

        for lugar in par:
            ocupantes = _ocupantes_atuais(ocupacoes_mensais, lugar["id"], hoje)
            reserva = _proxima_reserva(ocupacoes_mensais, lugar["id"], hoje)
            estado = _estado_ocupacao(
                len(ocupantes), lugar["capacidade"], reserva is not None
            )
            cor_fundo, cor_texto = _cores_estado(estado)

            caixa = ctk.CTkFrame(
                contentor,
                width=largura,
                height=ALTURA_CAIXA["beliche"],
                fg_color=cor_fundo,
                border_width=2,
                border_color=cor_texto,
                corner_radius=tema.RAIO_CAMPO,
            )
            caixa.pack(pady=(0, 4))
            caixa.pack_propagate(False)

            conteudo = ctk.CTkFrame(caixa, fg_color="transparent")
            conteudo.pack(expand=True, fill="both", padx=10, pady=4)

            etiqueta_nome = ctk.CTkLabel(
                conteudo,
                text=_truncar(lugar["nome"], limite),
                text_color=cor_texto,
                font=ctk.CTkFont(size=10, weight="bold"),
                wraplength=largura - 24,
            )
            etiqueta_nome.pack(expand=True)

            nomes = _nomes_ocupantes(ocupantes)
            etiquetas_corpo = [etiqueta_nome]

            if nomes:
                etiqueta_nome_ocupante = ctk.CTkLabel(
                    conteudo,
                    text=_truncar(nomes[0], limite),
                    text_color=cor_texto,
                    font=ctk.CTkFont(size=9),
                    wraplength=largura - 24,
                )
                etiqueta_nome_ocupante.pack(expand=True)
                etiquetas_corpo.append(etiqueta_nome_ocupante)
            elif estado == "reservado" and reserva is not None:
                etiqueta_data = ctk.CTkLabel(
                    conteudo,
                    text=reserva["data_inicio"].strftime("%d/%m"),
                    text_color=cor_texto,
                    font=ctk.CTkFont(size=9),
                )
                etiqueta_data.pack(expand=True)
                etiquetas_corpo.append(etiqueta_data)

            # ⋮ na `caixa`, fora do `conteudo`.
            self._botao_tres_pontos(caixa, lugar, tamanho=18)

            # Corpo — só nas etiquetas.
            if estado == "livre":
                for widget in etiquetas_corpo:
                    _tornar_clicavel(
                        widget,
                        lambda lugar_id=lugar["id"]: self._pedir_contrato(
                            lugar_id
                        ),
                    )
            elif estado == "reservado":
                for widget in etiquetas_corpo:
                    _tornar_clicavel(
                        widget,
                        lambda lugar=lugar, reserva=reserva, estado=estado: (
                            _DetalheLugarModal(self, lugar, reserva, estado)
                        ),
                    )
            elif estado == "ocupado":
                for widget in etiquetas_corpo:
                    _tornar_clicavel(
                        widget,
                        lambda lugar=lugar, ocupantes=ocupantes, estado=estado: (
                            _DetalheLugarModal(
                                self, lugar, ocupantes[0], estado
                            )
                        ),
                    )

    def _botao_tres_pontos(self, caixa, lugar, tamanho=22):
        """Coloca um botão ⋮ no canto inferior direito de uma caixa.

        Colocado com `.place()` na `caixa` — NÃO no `conteudo`.
        Assim fica fora do percurso do `_tornar_clicavel` (que só
        liga as etiquetas dentro do `conteudo`), e o seu clique
        dispara só o próprio `command`, sem passar pela ação do
        corpo. É esta separação de sítios que resolve o problema
        do clique a passar para trás — sem `"break"` nenhum.
        """
        fonte_tamanho = 14 if tamanho >= 22 else 11

        ctk.CTkButton(
            caixa,
            text="⋮",
            width=tamanho,
            height=tamanho,
            corner_radius=tamanho // 2,
            fg_color=tema.COR_FUNDO,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            font=ctk.CTkFont(size=fonte_tamanho, weight="bold"),
            command=lambda: _GerirLugarModal(self, lugar),
        ).place(relx=1.0, rely=1.0, x=-4, y=-4, anchor="se")


# =====================================================================
# Modais de gestão
# =====================================================================


class _NovoQuartoModal(ctk.CTkToplevel):
    """Modal de criação de um quarto — só nome, privativo e limpeza
    incluída (o mesmo que `unidades.criar_quarto` recebe).

    Botões do rodapé com a mesma receita do `_EditarQuartoModal` —
    `width=150`, `height=34`, sem `pady` vertical a comprimir.
    """

    def __init__(self, tela_planta):
        super().__init__(tela_planta)
        self.tela_planta = tela_planta

        self.title("Novo Quarto")
        self.geometry("440x360")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_planta)
        componentes.colocar_no_topo(self)

        unidade = unidades.procurar(tela_planta.unidade_id)
        nome_unidade = (
            f"{unidade['nome']} ({unidade['id']})"
            if unidade
            else tela_planta.unidade_id
        )

        ctk.CTkLabel(
            self,
            text="Novo Quarto",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 4))

        ctk.CTkLabel(
            self,
            text=f"Unidade: {nome_unidade}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 16))

        ctk.CTkLabel(
            self,
            text="Nome do quarto *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_nome = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: Quarto 3 — Vista Jardim",
        )
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Privativo",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.combo_privativo = ctk.CTkOptionMenu(
            self,
            values=["Não — partilhado", "Sim — privativo"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_privativo.set("Não — partilhado")
        self.combo_privativo.pack(fill="x", padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Limpeza incluída no cálculo de roupa?",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.combo_limpeza = ctk.CTkOptionMenu(
            self,
            values=["Sim", "Não"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_limpeza.set("Sim")
        self.combo_limpeza.pack(fill="x", padx=24, pady=(2, 12))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(10, 20), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
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
            text="Criar quarto",
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._criar,
        ).pack(side="right")

        self.campo_nome.focus_set()

    def _criar(self):
        privativo = self.combo_privativo.get() == "Sim — privativo"
        limpeza_incluida = self.combo_limpeza.get() == "Sim"

        try:
            quarto = unidades.criar_quarto(
                self.tela_planta.unidade_id,
                self.campo_nome.get(),
                privativo=privativo,
                limpeza_incluida=limpeza_incluida,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.destroy()
        self.tela_planta._desenhar_planta()

        if componentes.confirmar(
            f"Quarto criado com sucesso: {quarto['id']}.\n\n"
            f"Deseja criar os lugares deste quarto agora?",
            titulo="Criar lugares",
        ):
            _NovoLugarModal(self.tela_planta, quarto)


class _NovoLugarModal(ctk.CTkToplevel):
    """Modal de criação de um lugar — nome, tipo de cama, capacidade.

    Botões do rodapé com a mesma receita do `_EditarQuartoModal`.
    """

    def __init__(self, tela_planta, quarto):
        super().__init__(tela_planta)
        self.tela_planta = tela_planta
        self.quarto = quarto

        self.title("Novo Lugar")
        self.geometry("440x360")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_planta)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Novo Lugar",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 4))

        ctk.CTkLabel(
            self,
            text=f"Quarto: {quarto['nome']} ({quarto['id']})",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 16))

        ctk.CTkLabel(
            self,
            text="Nome do lugar *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_nome = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: Cama 3 — janela",
        )
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Tipo de cama *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.combo_tipo_cama = ctk.CTkOptionMenu(
            self,
            values=["solteiro", "casal", "beliche"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_tipo_cama.set("solteiro")
        self.combo_tipo_cama.pack(fill="x", padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Capacidade",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_capacidade = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="Enter para 1",
        )
        self.campo_capacidade.pack(fill="x", padx=24, pady=(2, 12))
        self.campo_capacidade.insert(0, "1")

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(10, 20), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
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
            text="Criar lugar",
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=self._criar,
        ).pack(side="right")

        self.campo_nome.focus_set()

    def _criar(self):
        texto_capacidade = self.campo_capacidade.get().strip()

        if not texto_capacidade:
            capacidade = 1
        elif texto_capacidade.isdigit():
            capacidade = int(texto_capacidade)
        else:
            componentes.mostrar_erro(
                "A capacidade tem de ser um número inteiro."
            )
            return

        try:
            lugar = unidades.criar_lugar(
                self.quarto["id"],
                self.campo_nome.get(),
                self.combo_tipo_cama.get(),
                capacidade=capacidade,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.destroy()
        self.tela_planta._desenhar_planta()

        if componentes.confirmar(
            f"Lugar criado: {lugar['id']} — {lugar['nome']}.\n\n"
            f"Sobrou mais algum lugar para criar neste quarto?",
            titulo="Criar lugar",
        ):
            _NovoLugarModal(self.tela_planta, self.quarto)


class _GerirQuartoModal(ctk.CTkToplevel):
    """Popup com as ações de um quarto — Editar ou Desativar.

    Botões com a mesma receita do `_EditarQuartoModal` — largura
    fixa, altura 34.
    """

    def __init__(self, tela_planta, quarto):
        super().__init__(tela_planta)
        self.tela_planta = tela_planta
        self.quarto = quarto

        self.title(f"Gerir quarto — {quarto['id']}")
        self.geometry("340x280")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_planta)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=quarto["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 2))

        privativo = "Privativo" if quarto["privativo"] else "Partilhado"
        limpeza = " · Limpeza incluída" if quarto["limpeza_incluida"] else ""
        ctk.CTkLabel(
            self,
            text=f"{quarto['id']} · {privativo}{limpeza}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if quarto["ativo"]:
            self._botao(
                "Editar quarto",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: _EditarQuartoModal(tela_planta, quarto),
            )
            self._separador()
            self._botao(
                "Desativar quarto",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: self._desativar(),
            )
        else:
            self._botao(
                "Reativar quarto",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self._reativar(),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", pady=(10, 16))

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
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)

    def _desativar(self):
        if not componentes.confirmar(
            f"Desativar o quarto {self.quarto['nome']}?",
            titulo="Desativar quarto",
        ):
            return

        try:
            unidades.desativar_quarto(self.quarto["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Quarto {self.quarto['nome']} desativado."
        )
        self.tela_planta._desenhar_planta()

    def _reativar(self):
        try:
            unidades.reativar_quarto(self.quarto["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Quarto {self.quarto['nome']} reativado.")
        self.tela_planta._desenhar_planta()


class _EditarQuartoModal(ctk.CTkToplevel):
    """Modal de edição de um quarto — mesmos campos do Novo Quarto,
    pré-preenchidos. A receita dos botões deste modal é a referência
    para todos os outros (é o que está no print do aluno).
    """

    def __init__(self, tela_planta, quarto):
        super().__init__(tela_planta)
        self.tela_planta = tela_planta
        self.quarto = quarto

        self.title(f"Editar quarto — {quarto['id']}")
        self.geometry("440x360")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_planta)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {quarto['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        ctk.CTkLabel(
            self,
            text="Nome do quarto *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 12))
        self.campo_nome.insert(0, quarto["nome"])

        ctk.CTkLabel(
            self,
            text="Privativo",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.combo_privativo = ctk.CTkOptionMenu(
            self,
            values=["Não — partilhado", "Sim — privativo"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_privativo.set(
            "Sim — privativo" if quarto["privativo"] else "Não — partilhado"
        )
        self.combo_privativo.pack(fill="x", padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Limpeza incluída no cálculo de roupa?",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.combo_limpeza = ctk.CTkOptionMenu(
            self,
            values=["Sim", "Não"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_limpeza.set("Sim" if quarto["limpeza_incluida"] else "Não")
        self.combo_limpeza.pack(fill="x", padx=24, pady=(2, 12))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(10, 20), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
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
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):
        privativo = self.combo_privativo.get() == "Sim — privativo"
        limpeza_incluida = self.combo_limpeza.get() == "Sim"

        try:
            unidades.atualizar_quarto(
                self.quarto["id"],
                nome=self.campo_nome.get(),
                privativo=privativo,
                limpeza_incluida=limpeza_incluida,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Quarto {self.quarto['id']} atualizado.")
        self.destroy()
        self.tela_planta._desenhar_planta()


class _GerirLugarModal(ctk.CTkToplevel):
    """Popup com as ações de um lugar — Editar, Desativar ou Reativar.

    Botões com a mesma receita do `_EditarQuartoModal`.
    """

    def __init__(self, tela_planta, lugar):
        super().__init__(tela_planta)
        self.tela_planta = tela_planta
        self.lugar = lugar

        self.title(f"Gerir lugar — {lugar['id']}")
        self.geometry("340x280")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_planta)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=lugar["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=(
                f"{lugar['id']} · {lugar['tipo_cama']} · "
                f"capacidade {lugar['capacidade']}"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if lugar["ativo"]:
            self._botao(
                "Editar lugar",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: _EditarLugarModal(tela_planta, lugar),
            )
            self._separador()
            self._botao(
                "Desativar lugar",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: self._desativar(),
            )
        else:
            self._botao(
                "Reativar lugar",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self._reativar(),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="bottom", pady=(10, 16))

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
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)

    def _desativar(self):
        if not componentes.confirmar(
            f"Desativar o lugar {self.lugar['nome']}?",
            titulo="Desativar lugar",
        ):
            return

        try:
            unidades.desativar_lugar(self.lugar["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Lugar {self.lugar['nome']} desativado.")
        self.tela_planta._desenhar_planta()

    def _reativar(self):
        try:
            unidades.reativar_lugar(self.lugar["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Lugar {self.lugar['nome']} reativado.")
        self.tela_planta._desenhar_planta()


class _EditarLugarModal(ctk.CTkToplevel):
    """Modal de edição de um lugar — nome, tipo de cama, capacidade.

    Botões com a mesma receita do `_EditarQuartoModal`.
    """

    def __init__(self, tela_planta, lugar):
        super().__init__(tela_planta)
        self.tela_planta = tela_planta
        self.lugar = lugar

        self.title(f"Editar lugar — {lugar['id']}")
        self.geometry("440x360")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_planta)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {lugar['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 16))

        ctk.CTkLabel(
            self,
            text="Nome do lugar *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 12))
        self.campo_nome.insert(0, lugar["nome"])

        ctk.CTkLabel(
            self,
            text="Tipo de cama *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.combo_tipo_cama = ctk.CTkOptionMenu(
            self,
            values=["solteiro", "casal", "beliche"],
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_tipo_cama.set(lugar["tipo_cama"])
        self.combo_tipo_cama.pack(fill="x", padx=24, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text="Capacidade",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24)

        self.campo_capacidade = ctk.CTkEntry(
            self, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_capacidade.pack(fill="x", padx=24, pady=(2, 12))
        self.campo_capacidade.insert(0, str(lugar["capacidade"]))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(10, 20), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
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
            width=_LARGURA_BOTAO_MODAL,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):
        texto_capacidade = self.campo_capacidade.get().strip()

        if not texto_capacidade:
            componentes.mostrar_erro("A capacidade é obrigatória.")
            return

        if not texto_capacidade.isdigit():
            componentes.mostrar_erro(
                "A capacidade tem de ser um número inteiro."
            )
            return

        try:
            unidades.atualizar_lugar(
                self.lugar["id"],
                nome=self.campo_nome.get(),
                tipo_cama=self.combo_tipo_cama.get(),
                capacidade=int(texto_capacidade),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Lugar {self.lugar['id']} atualizado.")
        self.destroy()
        self.tela_planta._desenhar_planta()


class _DetalheLugarModal(ctk.CTkToplevel):
    """Popup com o detalhe de um lugar ocupado OU reservado.

    Serve os dois estados desde 11/09/2026 (antes chamava-se
    `_DetalheOcupadoModal` e só servia o Ocupado). A diferença é
    visual:

    - Ocupado: chip vermelho "Ocupado", sem faixa.
    - Reservado: chip amarelo "Reservado" + faixa amarela a dizer
      "Reservado para dd/mm/aaaa" — o mesmo tom de aviso usado em
      toda a aplicação (AMARELO_AVISO/TEXTO_AVISO).

    O botão principal é "Abrir contrato" nos dois casos — é o
    contrato (o que está em vigor, ou o que vai entrar em vigor)
    que interessa a quem clica.

    Botões do rodapé com largura fixa, um à esquerda e um à
    direita — antes estavam com `expand=True` e `fill="x"` e
    ficavam esticados de ponta a ponta como uma barra.

    Janela com 560x480 — o conteúdo no caso Reservado (chip +
    faixa amarela + cartão do contrato) ficava apertado em 520x420.
    Aplica-se aos dois estados, para a janela não mudar de tamanho
    entre um e outro.
    """

    def __init__(self, tela_planta, lugar, ocupacao, estado):
        super().__init__(tela_planta)
        self.tela_planta = tela_planta
        self.lugar = lugar
        self.ocupacao = ocupacao
        self.estado = estado

        titulo_janela = (
            "Detalhe — reservado"
            if estado == "reservado"
            else "Detalhe — ocupado"
        )
        self.title(f"{titulo_janela} · {lugar['id']}")
        self.geometry(f"{_LARGURA_DETALHE}x{_ALTURA_DETALHE}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_planta)
        componentes.colocar_no_topo(self)

        # Título + subtítulo
        ctk.CTkLabel(
            self,
            text=f"{lugar['id']} · {lugar['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 2))

        if estado == "reservado":
            subtitulo = (
                f"Reserva a partir de "
                f"{ocupacao['data_inicio'].strftime('%d/%m/%Y')}"
            )
        else:
            subtitulo = (
                f"Ocupado desde "
                f"{ocupacao['data_inicio'].strftime('%d/%m/%Y')}"
            )

        ctk.CTkLabel(
            self,
            text=subtitulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 12))

        # Chip de estado
        if estado == "reservado":
            chip_fundo = tema.AMARELO_AVISO
            chip_texto = tema.TEXTO_AVISO
            chip_label = "Reservado"
        else:
            chip_fundo = tema.VERMELHO_ERRO
            chip_texto = tema.TEXTO_ERRO
            chip_label = "Ocupado"

        ctk.CTkLabel(
            self,
            text=chip_label,
            text_color=chip_texto,
            fg_color=chip_fundo,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=90,
            height=22,
        ).pack(anchor="w", padx=24, pady=(0, 14))

        # Faixa amarela, só no caso Reservado
        if estado == "reservado":
            faixa = ctk.CTkFrame(
                self,
                fg_color=tema.AMARELO_AVISO,
                corner_radius=tema.RAIO_CAMPO,
            )
            faixa.pack(fill="x", padx=24, pady=(0, 14))

            ctk.CTkLabel(
                faixa,
                text=(
                    f"⚠  Este lugar já tem uma reserva para "
                    f"{ocupacao['data_inicio'].strftime('%d/%m/%Y')}. "
                    f"Não é possível criar um contrato mensal para "
                    f"esta data."
                ),
                text_color=tema.TEXTO_AVISO,
                font=ctk.CTkFont(size=11),
                wraplength=480,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=14, pady=10)

        # Cartão do contrato
        cartao = ctk.CTkFrame(
            self,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CAMPO,
        )
        cartao.pack(fill="x", padx=24, pady=(0, 14))

        ctk.CTkLabel(
            cartao,
            text=f"{ocupacao['id']} — contrato mensal",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(12, 8))

        cliente = clientes.procurar(ocupacao["cliente_id"])
        nome_cliente = (
            f"{cliente['nome']} ({cliente['id']})"
            if cliente
            else ocupacao["cliente_id"]
        )

        self._linha_detalhe(cartao, "Inquilino", nome_cliente)
        self._linha_detalhe(
            cartao,
            "Início",
            ocupacao["data_inicio"].strftime("%d/%m/%Y"),
        )
        self._linha_detalhe(
            cartao,
            "Renda mensal",
            self._formatar_valor(ocupacao.get("renda_praticada")),
        )
        self._linha_detalhe(
            cartao,
            "Dia de vencimento",
            str(ocupacao.get("dia_vencimento") or "—"),
        )

        # Rodapé — largura fixa nos dois botões, um à esquerda, um à
        # direita. Sem `expand=True` nem `fill="x"`.
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=16, side="bottom")

        ctk.CTkButton(
            rodape,
            text="Abrir contrato",
            width=_LARGURA_BOTAO_DETALHE,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._abrir_contrato,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text="Fechar",
            width=_LARGURA_BOTAO_DETALHE,
            height=_ALTURA_BOTAO_MODAL,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="right")

    def _linha_detalhe(self, master, rotulo, valor):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=2)

        ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            width=140,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=valor,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left")

    def _formatar_valor(self, valor):
        if valor is None:
            return "—"
        return f"{valor:.2f} €".replace(".", ",")

    def _abrir_contrato(self):
        self.destroy()
        self.tela_planta.controlador.mostrar_frame(
            __import__(
                "gui.gui_contratos", fromlist=["ListaContratosMensais"]
            ).ListaContratosMensais
        )
