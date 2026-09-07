"""Ecrã "Planta de Lugares": mostra visualmente os quartos e lugares
de uma unidade mensal, com o estado de ocupação de cada lugar à
data de hoje.

Cada lugar aparece como uma caixa cujo tamanho depende do
'tipo_cama' (decisão de 06/09/2026, ao chegar este ecrã) — maior
para "casal", pequena para "solteiro". As caixas de "beliche"
aparecem em pares empilhados, porque um beliche físico são sempre
dois lugares distintos de capacidade 1 cada, nunca um só de
capacidade 2 (decisão 17); esse emparelhamento é só visual — sem
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
do erro/ocupado (vermelho) — em vez de "Livre" (decisão de
06/09/2026, ao validar o mockup). Ver `CINZA_INDISPONIVEL` em
tema.py.

Só se aplica a unidades do regime mensal — uma reserva Airbnb ocupa
a unidade inteira, sem 'lugar_id' (decisão 5), por isso não há
estado de ocupação por lugar para mostrar numa unidade Airbnb.

Ainda não existe um ecrã de lista de unidades (é um dos ecrãs "por
ordem de necessidade" a seguir a este), por isso este ecrã traz o
seu próprio seletor de unidade em vez de depender de uma escolha já
feita noutro sítio.

Clicar numa caixa livre ou reservada abre o Novo Contrato Mensal
(gui/gui_contratos.py) já pré-preenchido com esta unidade e esse
lugar — decisão tomada na Parte 3 (06/09/2026), concretizada em
07/09/2026 quando os ecrãs passaram a partilhar o mesmo controlador
através da barra lateral (gui/app.py). Caixas parciais/ocupadas não
são clicáveis (decisão original: só faz sentido abrir um contrato
novo quando o lugar ainda pode receber alguém agora ou está à
espera de quem já reservou).

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

LARGURA_CAIXA = {
    "solteiro": 120,
    "casal": 190,
    "beliche": 120,
}

ALTURA_CAIXA = {
    "solteiro": 120,
    "casal": 150,
    "beliche": 64,
}

# Número máximo de caracteres de um nome (lugar ou ocupante) em cada
# tipo de caixa, antes de cortar com reticências (_truncar) — evita
# que um nome comprido transborde para fora de uma caixa estreita.
LIMITE_CARATERES = {
    "solteiro": 20,
    "casal": 26,
    "beliche": 18,
}


def _chave_lado(nome):
    """Procura "esquerdo"/"direito" (ou variações, ex. "esquerda")
    no nome do lugar.

    Devolve "esquerdo", "direito" ou None se o nome não indicar
    lado nenhum — usado para emparelhar beliches por lado, em vez
    de só pela ordem de inserção: um quarto cadastrado "por andar"
    (Superior Esquerdo, Superior Direito, Inferior Esquerdo,
    Inferior Direito) ficaria emparelhado errado só pela ordem.
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
    palavra de lado no nome quando existe ("esquerdo" com
    "esquerdo", "direito" com "direito"); os restantes (sem essa
    palavra) são emparelhados pela ordem em que chegam. Um beliche
    que sobre sozinho (número ímpar) fica num grupo de um, para não
    desaparecer da planta.

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
    """Filtra, de uma lista de ocupações mensais, as que estão em
    vigor no lugar indicado, na data indicada.

    Mesma regra de `unidades._estado_mensal`: em vigor não é só
    'ativo' — o início já tem de ter chegado e o fim (quando existe)
    ainda não. Sem este filtro de datas, um contrato ainda por
    começar apareceria como "ocupado" na planta de hoje.
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
    """Devolve a ocupação futura mais próxima desse lugar (a de
    'data_inicio' mais cedo, ainda por começar), ou None.

    Serve para o estado "reservado": um lugar sem ocupante atual mas
    já com um contrato à espera de começar mostra a data em vez de
    "Livre".
    """
    futuras = [
        o
        for o in ocupacoes_mensais
        if o["lugar_id"] == lugar_id and o["data_inicio"] > hoje
    ]

    if not futuras:
        return None

    return min(futuras, key=lambda o: o["data_inicio"])


def _nomes_ocupantes(ocupacoes):
    """Devolve os nomes dos clientes de uma lista de ocupações.

    Um cliente inexistente (não devia acontecer, mas `procurar`
    nunca lança erro) aparece como "Cliente desconhecido", em vez de
    rebentar o ecrã inteiro.
    """
    nomes = []

    for ocupacao in ocupacoes:
        cliente = clientes.procurar(ocupacao["cliente_id"])
        nomes.append(cliente["nome"] if cliente else "Cliente desconhecido")

    return nomes


def _estado_ocupacao(total_ocupantes, capacidade, tem_reserva_futura):
    """Classifica a ocupação de um lugar em livre / reservado /
    parcial / ocupado, para escolher a cor da caixa na planta.

    "Reservado" só se aplica quando não há NENHUM ocupante atual —
    se já há gente lá (mesmo que não a lotação toda), o estado é
    "parcial", não "reservado" (a caixa mostra quem está lá agora,
    não quem vem a seguir).
    """
    if total_ocupantes == 0:
        return "reservado" if tem_reserva_futura else "livre"

    if total_ocupantes < capacidade:
        return "parcial"

    return "ocupado"


def _texto_estado(estado, ocupantes, capacidade, reserva):
    """Formata a linha de estado da caixa: "Livre", "Reservado ·
    data" (casal e solteiro — têm espaço para o texto todo), ou
    "Ocupado"/"Parcial · X/capacidade". As caixas de beliche não
    passam por aqui — têm o seu próprio texto curto, em
    `_desenhar_beliche`, por serem pequenas demais para "Reservado
    · data".
    """
    if estado == "livre":
        return "Livre"

    if estado == "reservado" and reserva is not None:
        data = reserva["data_inicio"].strftime("%d/%m/%Y")
        return f"Reservado · {data}"

    rotulo = "Ocupado" if estado == "ocupado" else "Parcial"
    return f"{rotulo} · {len(ocupantes)}/{capacidade}"


def _truncar(texto, limite):
    """Corta um texto no limite indicado, com reticências.

    As caixas da planta têm largura fixa (decisão de 06/09/2026,
    conforme o tipo de cama) — um nome comprido tem de ser cortado
    aqui, e não deixado a transbordar para fora da caixa.
    """
    if len(texto) <= limite:
        return texto

    return texto[: limite - 1] + "…"


def _cores_estado(estado):
    """Devolve (cor_fundo, cor_texto) da caixa, consoante o estado de
    ocupação.

    "Livre", "parcial" e "ocupado" reaproveitam a paleta de
    avisos/erros já definida em tema.py. "Reservado" usa
    CINZA_INDISPONIVEL — cinzento, para não se confundir nem com o
    amarelo de "parcial" nem com o vermelho de "ocupado" (decisão de
    06/09/2026, a pedido: cinzento lê-se melhor como
    "indisponível").
    """
    if estado == "livre":
        return tema.COR_FUNDO, tema.VERDE

    if estado == "parcial":
        return tema.AMARELO_AVISO, tema.TEXTO_AVISO

    if estado == "reservado":
        return tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL

    return tema.VERMELHO_ERRO, tema.TEXTO_ERRO


def _tornar_clicavel(widget, ao_clicar):
    """Liga um clique (botão esquerdo) a um widget e a todos os seus
    descendentes — precisa de ser feito widget a widget porque, em
    Tkinter, um clique num CTkLabel não propaga sozinho para o
    CTkFrame pai. Muda também o cursor para "mão", sinal visual de
    que a caixa é clicável (decisão de 07/09/2026, ao ligar a planta
    ao Novo Contrato Mensal — só as caixas livres/reservadas passam
    por aqui, nunca as parciais/ocupadas).
    """
    widget.configure(cursor="hand2")
    widget.bind("<Button-1>", lambda evento: ao_clicar())

    for filho in widget.winfo_children():
        _tornar_clicavel(filho, ao_clicar)


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

        componentes.Cabecalho(self, titulo="Planta de Lugares").pack(
            fill="x"
        )

        self._montar_seletor()

        self.area_planta = ctk.CTkScrollableFrame(
            self, fg_color=tema.COR_FUNDO
        )
        self.area_planta.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._recarregar_unidades()

    def _montar_seletor(self):
        """Monta a barra com o seletor de unidade e o botão de
        atualizar, por baixo do cabeçalho.
        """
        barra = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO)
        barra.pack(fill="x", padx=20, pady=(0, 10))

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

    def _recarregar_unidades(self):
        """Lê as unidades mensais ativas e povoa o seletor.

        Chamada na abertura do ecrã e sempre que "Atualizar" é
        premido — uma unidade criada, ou um contrato registado
        noutro ecrã (ou na CLI, enquanto a GUI está aberta), só
        aparece aqui depois disto correr de novo.
        """
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

    def _abrir_contrato(self, lugar_id):
        """Abre o Novo Contrato Mensal já pré-preenchido com a
        unidade atual e o lugar clicado — só chamado a partir de
        caixas livres ou reservadas (ver `_tornar_clicavel`, chamado
        em `_desenhar_caixa`/`_desenhar_beliche`).
        """
        self.controlador.mostrar_frame(
            NovoContratoMensal,
            unidade_id=self.unidade_id,
            lugar_id=lugar_id,
        )

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

        # Defesa extra: o seletor só lista unidades mensais, e o tipo
        # nunca se altera depois de criado (unidades.atualizar não o
        # permite) — mas um futuro ecrã que abra este diretamente com
        # outro unidade_id não deve rebentar por isso.
        if unidade["tipo"] != "mensal":
            self._mostrar_mensagem(
                "A planta de lugares aplica-se apenas a unidades do "
                "regime mensal."
            )
            return

        quartos = unidades.listar_quartos(unidade_id=self.unidade_id)

        if not quartos:
            self._mostrar_mensagem("Esta unidade ainda não tem quartos.")
            return

        ocupacoes_mensais = contratos.listar(
            unidade_id=self.unidade_id, tipo="mensal"
        )
        hoje = date.today()

        for quarto in quartos:
            self._desenhar_quarto(quarto, ocupacoes_mensais, hoje)

    def _desenhar_quarto(self, quarto, ocupacoes_mensais, hoje):
        """Desenha o cartão de um quarto: cabeçalho com o nome e os
        indicadores, seguido da fila de caixas dos seus lugares.
        """
        cartao = ctk.CTkFrame(
            self.area_planta,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x", pady=(0, 16))

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

        lugares = unidades.listar_lugares(quarto_id=quarto["id"])

        linha_lugares = ctk.CTkFrame(cartao, fg_color="transparent")
        linha_lugares.pack(fill="x", padx=16, pady=(4, 16))

        if not lugares:
            ctk.CTkLabel(
                linha_lugares,
                text="Sem lugares cadastrados.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
            ).pack(side="left")
            return

        for grupo in _agrupar_para_planta(lugares):
            if len(grupo) == 2:
                self._desenhar_beliche(
                    linha_lugares, grupo, ocupacoes_mensais, hoje
                )
            else:
                self._desenhar_caixa(
                    linha_lugares, grupo[0], ocupacoes_mensais, hoje
                )

    def _desenhar_caixa(self, master, lugar, ocupacoes_mensais, hoje):
        """Desenha a caixa de um lugar "solteiro" ou "casal" — o
        tamanho vem de LARGURA_CAIXA/ALTURA_CAIXA, indexado pelo
        'tipo_cama' (decisão de 06/09/2026): só decide a aparência,
        nunca a capacidade real do lugar.
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

        # Frame de conteúdo com a sua própria margem interna — em vez
        # de confiar só no wraplength, para o texto nunca tocar a
        # borda mesmo num nome perto do limite (decisão de 06/09/2026,
        # a pedido).
        conteudo = ctk.CTkFrame(caixa, fg_color="transparent")
        conteudo.pack(expand=True, fill="both", padx=12, pady=10)

        ctk.CTkLabel(
            conteudo,
            text=_truncar(lugar["nome"], limite_nomes),
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=largura - 30,
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            conteudo,
            text=_texto_estado(
                estado, ocupantes, lugar["capacidade"], reserva
            ),
            text_color=cor_texto,
            font=ctk.CTkFont(size=10),
            wraplength=largura - 30,
        ).pack(pady=(0, 4))

        for nome in _nomes_ocupantes(ocupantes):
            ctk.CTkLabel(
                conteudo,
                text=_truncar(nome, limite_nomes),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=9),
                wraplength=largura - 30,
            ).pack()

        if estado in ("livre", "reservado"):
            _tornar_clicavel(
                caixa,
                lambda lugar_id=lugar["id"]: self._abrir_contrato(lugar_id),
            )

    def _desenhar_beliche(self, master, par, ocupacoes_mensais, hoje):
        """Desenha um par de lugares "beliche" como duas caixas
        pequenas empilhadas dentro de um contentor comum, para se
        lerem como uma cama só na planta, mesmo sendo dois lugares
        distintos na base de dados (decisão 17). A ordem dentro do
        par vem de `_ordenar_par` — quem tem "inferior" no nome fica
        sempre em baixo.
        """
        contentor = ctk.CTkFrame(master, fg_color="transparent")
        contentor.pack(side="left", padx=10, pady=10)

        largura = LARGURA_CAIXA["beliche"]
        limite = LIMITE_CARATERES["beliche"]

        for lugar in par:
            ocupantes = _ocupantes_atuais(
                ocupacoes_mensais, lugar["id"], hoje
            )
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
            conteudo.pack(expand=True, fill="both", padx=10, pady=6)

            ctk.CTkLabel(
                conteudo,
                text=_truncar(lugar["nome"], limite),
                text_color=cor_texto,
                font=ctk.CTkFont(size=10, weight="bold"),
                wraplength=largura - 24,
            ).pack(expand=True)

            nomes = _nomes_ocupantes(ocupantes)

            if nomes:
                ctk.CTkLabel(
                    conteudo,
                    text=_truncar(nomes[0], limite),
                    text_color=cor_texto,
                    font=ctk.CTkFont(size=9),
                    wraplength=largura - 24,
                ).pack(expand=True)
            elif estado == "reservado" and reserva is not None:
                # Caixa pequena demais para "Reservado · data" — só a
                # data, curta (decisão de 06/09/2026, a pedido).
                ctk.CTkLabel(
                    conteudo,
                    text=reserva["data_inicio"].strftime("%d/%m"),
                    text_color=cor_texto,
                    font=ctk.CTkFont(size=9),
                ).pack(expand=True)

            if estado in ("livre", "reservado"):
                _tornar_clicavel(
                    caixa,
                    lambda lugar_id=lugar["id"]: self._abrir_contrato(
                        lugar_id
                    ),
                )
