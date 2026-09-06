"""Ecrã "Propriedades e Unidades": lista as propriedades (edifícios)
e, dentro de cada uma, as suas unidades — mensais e Airbnb — com o
estado de ocupação de cada unidade (calculado por unidades.estado(),
nunca guardado) e ações de criar/editar/desativar/reativar.

Escolhido pelo aluno como o ecrã seguinte à Planta de Lugares e ao
Novo Contrato Mensal, 06/09/2026. Decisões tomadas na validação por
mockup (Xvfb + CustomTkinter real, dados falsos, sem tocar no MySQL
do aluno), antes deste ficheiro:

1. Unidades mensais E Airbnb aparecem aqui (06/09/2026, ronda 4 —
   antes só mensais; Airbnb era só pelo CLI). A Airbnb não usa
   quarto/lugar (decisão 5), por isso não tem "Ver planta →" nem
   entra na Planta de Lugares — só as duas ações comuns
   (Desativar/Editar). Cada unidade Airbnb mostra "· Airbnb" a
   seguir ao nome, para se distinguir das mensais (que não ganham
   sufixo nenhum, continuam iguais a antes).

2. Além de listar, o ecrã cria e edita Propriedades e Unidades
   (mensais) diretamente aqui, em modais (CTkToplevel) — "+ Nova
   Propriedade" no rodapé, "+ Unidade"/"Editar" em cada cartão de
   propriedade, "Editar" em cada unidade. A propriedade e o tipo
   ("mensal") de uma unidade vêm sempre fixos do modal onde foram
   abertos — não se alteram depois (mesma regra de
   `unidades.atualizar`, que não deixa mudar tipo nem propriedade).

3. "Ver planta →" em cada unidade mensal chama
   `controlador.mostrar_frame(PlantaLugares, unidade_id=...)` —
   liga este ecrã à Planta de Lugares já construída. Ao contrário
   da ligação planta → Novo Contrato Mensal (que ainda não tem
   controlador/menu à volta e fica para mais à frente), este ecrã
   já nasce com um controlador, como todos os ecrãs — por isso a
   ligação já é feita.

4. Cada unidade mostra o resultado de `unidades.estado()` como uma
   etiqueta colorida: verde quando não há nenhum ocupante, amarelo
   quando parcial, vermelho quando cheia, cinza (indisponível) para
   "Em manutenção" — mesma paleta de avisos/erros já usada na
   Planta de Lugares (ver ponto 6 sobre o par verde, novo).

5. Desativar/reativar: pedido do aluno, ao ver o mockup sem forma
   de esconder um quarto fechado para obras. Cada cartão/linha
   ativa tem um botão "Desativar" discreto (texto vermelho, sem
   fundo — para não competir com "Editar"/"+ Unidade"/"Ver planta").

   Primeira versão (06/09/2026, manhã) pedia confirmação simples e
   nunca passava forcar=True — se houvesse dependências ativas, só
   mostrava o erro exato da camada de negócio e parava. O aluno
   testou no MySQL real, viu esse erro para uma unidade com 2
   ocupações ativas, e pediu para mudar: em vez de só bloquear,
   contar as dependências ativas ANTES (mesma lógica de
   `_desativar_propriedade`/`_desativar_unidade` em cli.py:
   `unidades.listar(propriedade_id=...)` e
   `contratos.listar(unidade_id=...)`) e perguntar "tem N
   dependência(s) ativa(s) — deseja mesmo desativar?" com duas
   opções — "Cancelar" ou "Forçar desativação" — em vez do popup de
   erro simples. Só quando o aluno escolhe forçar é que
   `propriedades.desativar`/`unidades.desativar` é chamado com
   forcar=True (ver `_ConfirmarForcarModal`, `_forcar_desativar_*`).
   Sem dependências ativas, continua a simples confirmação por
   popup (componentes.confirmar — terceira convenção de popup da
   GUI) antes de desativar sem forçar.

   Ainda no mesmo pedido: "para saber quem desativou forçadamente",
   `_ConfirmarForcarModal` ganhou um dropdown de Responsável
   (mesmo padrão de "Responsável do desconto" em
   gui/contratos.py) — obrigatório para "Forçar desativação"
   avançar. `propriedades.desativar`/`unidades.desativar` passaram
   a aceitar `responsavel_id` e a gravá-lo (com a data) em
   `desativado_por_id`/`data_desativacao`, só quando a desativação
   é mesmo forçada com dependências ativas — nova coluna em
   propriedades/unidades (ver claude/esquema_mysql.sql, ALTER
   TABLE). cli.py também passou a pedir o responsável ao forçar,
   para as duas interfaces ficarem consistentes.

   Uma caixa "Mostrar inativos" no topo revela as propriedades/
   unidades desativadas, cada uma só com "Reativar".

6. Cor nova em gui/tema.py: VERDE_LIVRE/TEXTO_LIVRE. A Planta de
   Lugares mostra "Livre" só com texto verde sobre o fundo normal;
   aqui as quatro etiquetas de estado precisam de se parecer (são
   todas uma "pílula" colorida), por isso "livre" ganhou o mesmo
   tipo de par (fundo, texto) que amarelo/vermelho/cinza já tinham.

7. BUG reportado pelo aluno, 06/09/2026 (tarde), testando no
   Windows real dele: todos os popups deste ecrã (os 5 CTkToplevel
   — os 4 modais de criar/editar e o `_ConfirmarForcarModal`) às
   vezes abriam ESCONDIDOS atrás da janela principal, exigindo um
   clique extra para os ver. Faltava dizer ao Tk que o popup é uma
   janela "transiente" da principal e trazê-lo para a frente — o
   Xvfb usado para validar por imagem não tem gestor de janelas
   nenhum, por isso este bug nunca apareceu nos mockups. Corrigido
   com `_colocar_no_topo` (função nova, logo antes de
   `_ConfirmarForcarModal`): cada modal chama `self.transient(...)`
   e agenda
   lift()/focus_force()/grab_set() com `after(10, ...)` — o atraso
   dá tempo ao Tk para mapear a janela antes de grab_set(), que
   falha com "not viewable" se chamado logo de seguida.

8. RONDA 4 (mesmo dia, ao juntar a Airbnb a este ecrã): três pedidos
   do aluno.

   Unidades desativadas sempre no final: `_desenhar_propriedade`
   ordena a lista de unidades de cada propriedade (`sort`, estável)
   por "está inativa" — as ativas ficam pela ordem que já vinha de
   `unidades.listar`, as inativas vão sempre a seguir, nunca
   misturadas no meio.

   Criar uma unidade Airbnb aqui: `NovaUnidadeModal` ganhou um
   seletor "Tipo" (Mensal/Airbnb) antes do Nome, a substituir o
   "mensal" antes fixo — passa a escolha diretamente a
   `unidades.criar`. `EditarUnidadeModal` não ganhou seletor (tipo
   não muda ao editar — regra de `unidades.atualizar`), só corrigiu
   o rótulo para mostrar o tipo real da unidade em vez de "mensal"
   escrito à mão.

   "Época alta ativa" só faz sentido na Airbnb: fui conferir
   `contratos.py` antes de mexer e `criar_mensal` usa sempre
   `preco_base` — nunca olha para `epoca_alta_ativa`/
   `preco_epoca_alta`; quem lê os dois é só
   `contratos._preco_calculado_airbnb` (usado nas reservas
   Airbnb). Por isso marcar essa caixa com "Mensal" escolhido (ou
   trocar para "Mensal" com a caixa já marcada) desmarca-a sozinha
   e mostra "Unidade do tipo mensal não existe época alta." —
   `_ao_marcar_epoca_alta`/`_ao_mudar_tipo`, nos dois modais.
   Decisão do aluno, 06/09/2026: validado só aqui na GUI, por
   agora — `unidades.criar`/`atualizar` continuam a aceitar
   qualquer combinação (o cli.py, que já pergunta "Época alta
   ativa?" para os dois tipos, fica exatamente como estava).

Segue a mesma disciplina de camadas do resto da GUI (decisão 7): só
fala com `propriedades` e `unidades` — nunca com `repositorio`
diretamente.
"""

import datetime
from decimal import Decimal, InvalidOperation

import customtkinter as ctk

import contratos
import propriedades
import responsaveis
import unidades
from . import componentes
from . import tema
from .unidades import PlantaLugares


def _cor_estado(texto_estado):
    """Devolve (cor_fundo, cor_texto) da etiqueta de estado de uma
    unidade, a partir do texto de `unidades.estado()`. Duas formas
    possíveis, consoante o tipo da unidade:

    - Mensal (ou "Em manutenção", comum aos dois tipos):
      "ocupados/capacidade" (ex.: "2/4").
    - Airbnb (acrescentado 06/09/2026, ao juntar as unidades Airbnb
      a este ecrã): "Livre", "Ocupado" ou "Reservado" — mesma
      paleta de "Livre"/"Ocupado"/"Reservado" já usada na Planta de
      Lugares (`gui/unidades.py`, `_cores_estado`), sem o estado
      "parcial" (não existe capacidade parcial numa reserva Airbnb —
      ocupa a unidade inteira ou não ocupa nada).
    """
    if texto_estado == "Em manutenção":
        return tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL

    if texto_estado == "Livre":
        return tema.VERDE_LIVRE, tema.TEXTO_LIVRE

    if texto_estado == "Ocupado":
        return tema.VERMELHO_ERRO, tema.TEXTO_ERRO

    if texto_estado == "Reservado":
        return tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL

    ocupados, capacidade = texto_estado.split("/")
    ocupados, capacidade = int(ocupados), int(capacidade)

    if ocupados == 0:
        return tema.VERDE_LIVRE, tema.TEXTO_LIVRE

    if ocupados >= capacidade:
        return tema.VERMELHO_ERRO, tema.TEXTO_ERRO

    return tema.AMARELO_AVISO, tema.TEXTO_AVISO


def _formatar_valor(valor):
    """Formata um Decimal para pré-preencher um campo de edição —
    sem símbolo de moeda, sempre com ponto (a leitura, em
    `_ler_decimal`, aceita ponto ou vírgula na escrita).
    """
    return f"{valor:.2f}"


def _ler_decimal(texto, nome_campo):
    """Converte o texto de um campo monetário em Decimal, aceitando
    vírgula ou ponto (mesma tolerância de gui/contratos.py). Levanta
    ValueError com mensagem pronta para popup, em vez de deixar
    escapar decimal.InvalidOperation.
    """
    try:
        return Decimal(texto.strip().replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"{nome_campo} tem um valor inválido.")


def _colocar_no_topo(janela):
    """Traz um popup (CTkToplevel) para a frente da janela principal.

    Sem isto, o Windows (e alguns outros gestores de janelas) por
    vezes abre o popup por baixo da janela principal, escondido —
    bug reportado pelo aluno, 06/09/2026 (tarde), em todos os
    popups deste ecrã. `after(10, ...)` dá tempo ao Tk para mapear
    a janela antes de `grab_set()` — chamado já a seguir a
    `super().__init__(...)`, `grab_set()` falha com "grab failed:
    window not viewable" em alguns sistemas.
    """
    janela.after(
        10, lambda: (janela.lift(), janela.focus_force(), janela.grab_set())
    )


class _ConfirmarForcarModal(ctk.CTkToplevel):
    """Modal de duas opções — "Cancelar" ou "Forçar desativação" —
    mostrado quando desativar uma propriedade/unidade encontra
    dependências ativas (mesma decisão do CLI:
    `_desativar_propriedade`/`_desativar_unidade` em cli.py também
    contam as dependências antes e só chamam
    `propriedades.desativar`/`unidades.desativar` com forcar=True
    depois de confirmado — nunca deixam a exceção da camada de
    negócio ser a primeira coisa que o utilizador vê).

    O dropdown de Responsável (mesmo padrão de "Responsável do
    desconto" em gui/contratos.py) é obrigatório para forçar —
    `propriedades.desativar`/`unidades.desativar` exigem
    `responsavel_id` sempre que forcar=True encontra dependências
    ativas, para saber quem autorizou (decisão do aluno,
    06/09/2026). `ao_forcar(responsavel_id)` só é chamado se
    "Forçar desativação" for escolhido com um responsável
    selecionado; ao cancelar, o modal fecha-se sem fazer nada.
    """

    def __init__(self, master, mensagem, ao_forcar):
        super().__init__(master)
        self.ao_forcar = ao_forcar

        self.title("Confirmar desativação")
        self.geometry("380x300")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        _colocar_no_topo(self)

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
            text="Forçar desativação",
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._forcar,
        ).pack(side="right")

    def _responsavel_escolhido_id(self):
        indice = self.combo_responsavel.cget("values").index(
            self.combo_responsavel.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _forcar(self):
        responsavel_id = self._responsavel_escolhido_id()

        if not responsavel_id:
            componentes.mostrar_erro(
                "Escolhe o responsável que autoriza a desativação " "forçada."
            )
            return

        self.destroy()
        self.ao_forcar(responsavel_id)


class ListaPropriedades(ctk.CTkFrame):
    """Ecrã principal: lista as propriedades e as suas unidades —
    mensais e Airbnb —, com ações de criar/editar/desativar/
    reativar.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Propriedades e Unidades").pack(
            fill="x"
        )

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
        ).pack(side="right")

        self.area_lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.area_lista.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        rodape = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO, height=48)
        rodape.pack(fill="x", padx=24, pady=(0, 16))
        ctk.CTkButton(
            rodape,
            text="+ Nova Propriedade",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=lambda: NovaPropriedadeModal(self),
        ).pack(side="left")

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _recarregar(self):
        """Limpa e volta a desenhar a lista inteira — chamada na
        abertura do ecrã, ao mexer em "Mostrar inativos", e depois
        de qualquer criação/edição/desativação/reativação, para
        refletir logo o resultado (mesmo princípio de
        `PlantaLugares._recarregar_unidades`).
        """
        for widget in self.area_lista.winfo_children():
            widget.destroy()

        incluir_inativas = self.mostrar_inativos.get()
        lista = propriedades.listar(incluir_inativas=incluir_inativas)

        if not lista:
            ctk.CTkLabel(
                self.area_lista,
                text="Ainda não há propriedades cadastradas.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        for prop in lista:
            self._desenhar_propriedade(prop, incluir_inativas)

    # -- desenho -------------------------------------------------------

    def _desenhar_propriedade(self, prop, incluir_inativas):
        inativa = not prop["ativo"]

        cartao = ctk.CTkFrame(
            self.area_lista,
            corner_radius=tema.RAIO_CARTAO,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
        )
        cartao.pack(fill="x", pady=8)

        cabecalho = ctk.CTkFrame(cartao, fg_color="transparent")
        cabecalho.pack(fill="x", padx=16, pady=(14, 6))

        bloco_texto = ctk.CTkFrame(cabecalho, fg_color="transparent")
        bloco_texto.pack(side="left", anchor="w")

        nome = prop["nome"] + ("  (inativa)" if inativa else "")
        cor_nome = tema.COR_TEXTO_SECUNDARIO if inativa else tema.COR_TEXTO
        ctk.CTkLabel(
            bloco_texto,
            text=nome,
            text_color=cor_nome,
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            bloco_texto,
            text=prop["morada"] or "sem morada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(anchor="w")

        botoes = ctk.CTkFrame(cabecalho, fg_color="transparent")
        botoes.pack(side="right")

        if inativa:
            ctk.CTkButton(
                botoes,
                text="Reativar",
                width=80,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color=tema.VERDE,
                hover_color=tema.VERDE,
                command=lambda: self._reativar_propriedade(prop),
            ).pack(side="left")
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
                command=lambda: self._desativar_propriedade(prop),
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
                command=lambda: EditarPropriedadeModal(self, prop),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                botoes,
                text="+ Unidade",
                width=90,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.AZUL_CLARO,
                command=lambda: NovaUnidadeModal(self, prop),
            ).pack(side="left")

        unidades_prop = unidades.listar(
            incluir_inativas=incluir_inativas,
            propriedade_id=prop["id"],
        )
        # Ativas primeiro, inativas sempre no final (pedido do aluno,
        # 06/09/2026) — sort() é estável, por isso dentro de cada
        # grupo mantém a ordem devolvida por unidades.listar().
        unidades_prop.sort(key=lambda u: not u["ativo"])

        if not unidades_prop:
            ctk.CTkLabel(
                cartao,
                text="Sem unidades.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=16, pady=(0, 14))
            return

        for uni in unidades_prop:
            self._desenhar_unidade(cartao, uni, prop)

        ctk.CTkFrame(cartao, fg_color="transparent", height=6).pack()

    def _desenhar_unidade(self, master, uni, prop):
        inativa = not uni["ativo"]

        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=3)

        # Etiqueta de tipo só aparece na Airbnb — as unidades mensais
        # continuam sem sufixo nenhum, exatamente como antes de este
        # ecrã passar a mostrar também as Airbnb (06/09/2026).
        etiqueta_tipo = "" if uni["tipo"] == "mensal" else "  · Airbnb"
        nome = uni["nome"] + etiqueta_tipo + ("  (inativa)" if inativa else "")
        cor_nome = tema.COR_TEXTO_SECUNDARIO if inativa else tema.COR_TEXTO
        ctk.CTkLabel(
            linha,
            text=nome,
            text_color=cor_nome,
            font=ctk.CTkFont(size=13),
            anchor="w",
            width=160,
        ).pack(side="left")

        if inativa:
            botoes = ctk.CTkFrame(linha, fg_color="transparent")
            botoes.pack(side="right")
            ctk.CTkButton(
                botoes,
                text="Reativar",
                width=80,
                height=24,
                corner_radius=tema.RAIO_BOTAO,
                fg_color=tema.VERDE,
                hover_color=tema.VERDE,
                command=lambda: self._reativar_unidade(uni),
            ).pack(side="left")
            return

        estado_texto = unidades.estado(uni["id"], datetime.date.today())
        fundo, texto = _cor_estado(estado_texto)

        ctk.CTkLabel(
            linha,
            text=estado_texto,
            text_color=texto,
            fg_color=fundo,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=90,
            height=22,
        ).pack(side="left", padx=8)

        botoes = ctk.CTkFrame(linha, fg_color="transparent")
        botoes.pack(side="right")
        ctk.CTkButton(
            botoes,
            text="Desativar",
            width=72,
            height=24,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=lambda: self._desativar_unidade(uni),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            botoes,
            text="Editar",
            width=60,
            height=24,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=lambda: EditarUnidadeModal(self, uni, prop),
        ).pack(side="left", padx=(0, 6))

        # "Ver planta" só faz sentido no regime mensal — a Airbnb não
        # usa quarto/lugar (decisão 5), não tem planta nenhuma para
        # mostrar (06/09/2026, ao juntar a Airbnb a este ecrã).
        if uni["tipo"] == "mensal":
            ctk.CTkButton(
                botoes,
                text="Ver planta →",
                width=100,
                height=24,
                corner_radius=tema.RAIO_BOTAO,
                fg_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.AZUL_CLARO,
                command=lambda: self._abrir_planta(uni["id"]),
            ).pack(side="left")

    # -- ações -----------------------------------------------------------

    def _abrir_planta(self, unidade_id):
        self.controlador.mostrar_frame(PlantaLugares, unidade_id=unidade_id)

    def _desativar_propriedade(self, prop):
        ativas = unidades.listar(propriedade_id=prop["id"])

        if ativas:
            mensagem = (
                f"A propriedade {prop['nome']} tem {len(ativas)} "
                f"unidade(s) ativa(s) — deseja mesmo desativá-la?"
            )
            _ConfirmarForcarModal(
                self,
                mensagem,
                lambda responsavel_id: self._forcar_desativar_propriedade(
                    prop, responsavel_id
                ),
            )
            return

        pergunta = f"Desativar a propriedade {prop['nome']} ({prop['id']})?"
        if not componentes.confirmar(pergunta):
            return

        try:
            propriedades.desativar(prop["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Propriedade {prop['nome']} desativada.")
        self._recarregar()

    def _forcar_desativar_propriedade(self, prop, responsavel_id):
        try:
            propriedades.desativar(
                prop["id"], forcar=True, responsavel_id=responsavel_id
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Propriedade {prop['nome']} desativada.")
        self._recarregar()

    def _reativar_propriedade(self, prop):
        try:
            propriedades.reativar(prop["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Propriedade {prop['nome']} reativada.")
        self._recarregar()

    def _desativar_unidade(self, uni):
        ativas = contratos.listar(unidade_id=uni["id"])

        if ativas:
            mensagem = (
                f"A unidade {uni['nome']} tem {len(ativas)} "
                f"ocupação(ões) ativa(s) — deseja mesmo desativá-la?"
            )
            _ConfirmarForcarModal(
                self,
                mensagem,
                lambda responsavel_id: self._forcar_desativar_unidade(
                    uni, responsavel_id
                ),
            )
            return

        pergunta = f"Desativar a unidade {uni['nome']} ({uni['id']})?"
        if not componentes.confirmar(pergunta):
            return

        try:
            unidades.desativar(uni["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Unidade {uni['nome']} desativada.")
        self._recarregar()

    def _forcar_desativar_unidade(self, uni, responsavel_id):
        try:
            unidades.desativar(
                uni["id"], forcar=True, responsavel_id=responsavel_id
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Unidade {uni['nome']} desativada.")
        self._recarregar()

    def _reativar_unidade(self, uni):
        try:
            unidades.reativar(uni["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Unidade {uni['nome']} reativada.")
        self._recarregar()


class NovaPropriedadeModal(ctk.CTkToplevel):
    """Modal de criação de uma propriedade — só nome e morada
    (`propriedades.criar` não pede mais nada).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title("Nova Propriedade")
        self.geometry("380x260")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Nova Propriedade",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 14))

        ctk.CTkLabel(
            self,
            text="Nome",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.pack(fill="x", padx=20, pady=(2, 10))

        ctk.CTkLabel(
            self,
            text="Morada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_morada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_morada.pack(fill="x", padx=20, pady=(2, 10))

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
            text="Criar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._criar,
        ).pack(side="right")

    def _criar(self):
        try:
            propriedade = propriedades.criar(
                self.campo_nome.get(), self.campo_morada.get()
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Propriedade criada com sucesso: {propriedade['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class EditarPropriedadeModal(ctk.CTkToplevel):
    """Modal de edição de uma propriedade existente — mesmos campos
    de NovaPropriedadeModal, pré-preenchidos.
    """

    def __init__(self, tela_lista, prop):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.prop = prop

        self.title(f"Editar Propriedade — {prop['nome']}")
        self.geometry("380x260")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {prop['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 14))

        ctk.CTkLabel(
            self,
            text="Nome",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.insert(0, prop["nome"])
        self.campo_nome.pack(fill="x", padx=20, pady=(2, 10))

        ctk.CTkLabel(
            self,
            text="Morada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_morada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_morada.insert(0, prop["morada"])
        self.campo_morada.pack(fill="x", padx=20, pady=(2, 10))

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
            text="Guardar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):
        try:
            propriedades.atualizar(
                self.prop["id"],
                nome=self.campo_nome.get(),
                morada=self.campo_morada.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Propriedade {self.prop['id']} atualizada."
        )
        self.destroy()
        self.tela_lista._recarregar()


class NovaUnidadeModal(ctk.CTkToplevel):
    """Modal de criação de uma unidade dentro de uma propriedade já
    escolhida (o cartão onde "+ Unidade" foi premido) — a
    propriedade vem fixa, mas o tipo (Mensal/Airbnb) já se escolhe
    aqui (06/09/2026, ao juntar a Airbnb a este ecrã — antes só
    criava "mensal", fixo).

    "Época alta ativa" só tem efeito real na Airbnb —
    `contratos.criar_mensal` usa sempre `preco_base`, nunca
    `epoca_alta_ativa`/`preco_epoca_alta` (só
    `contratos._preco_calculado_airbnb` os lê). Por isso, com
    "Mensal" escolhido, marcar essa caixa mostra um aviso e
    desmarca-se sozinha — decisão do aluno, 06/09/2026: validado só
    aqui na GUI, por agora (unidades.criar/atualizar continuam a
    aceitar qualquer combinação, para o cli.py não mudar).
    """

    def __init__(self, tela_lista, prop):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.prop = prop

        self.title(f"Nova Unidade — {prop['nome']}")
        self.geometry("380x560")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Nova Unidade",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text=f"Propriedade: {prop['nome']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Tipo",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.combo_tipo = ctk.CTkOptionMenu(
            self, values=["Mensal", "Airbnb"], command=self._ao_mudar_tipo
        )
        self.combo_tipo.set("Mensal")
        self.combo_tipo.pack(fill="x", padx=20, pady=(2, 10))

        self.campo_nome = self._campo("Nome")
        self.campo_preco_base = self._campo("Preço base (€)")
        self.campo_preco_epoca_alta = self._campo("Preço época alta (€)")
        self.campo_multa = self._campo("Multa check-in tardio (€)")

        self.epoca_alta_ativa = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="Época alta ativa",
            variable=self.epoca_alta_ativa,
            command=self._ao_marcar_epoca_alta,
        ).pack(anchor="w", padx=20, pady=(14, 0))

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
            text="Criar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._criar,
        ).pack(side="right")

    def _campo(self, rotulo):
        ctk.CTkLabel(
            self,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(6, 2))
        entrada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        entrada.pack(fill="x", padx=20)
        return entrada

    def _tipo_selecionado(self):
        return "mensal" if self.combo_tipo.get() == "Mensal" else "airbnb"

    def _ao_mudar_tipo(self, _valor_escolhido):
        """Ao trocar para "Mensal" com "Época alta ativa" já
        marcada, desmarca e avisa — mesma regra de
        `_ao_marcar_epoca_alta`, só que disparada pelo lado do
        tipo em vez do lado da caixa (cobre trocar o tipo DEPOIS de
        já ter marcado a caixa, não só o caminho inverso).
        """
        tipo_mensal = self._tipo_selecionado() == "mensal"
        if tipo_mensal and self.epoca_alta_ativa.get():
            self.epoca_alta_ativa.set(False)
            componentes.mostrar_erro(
                "Unidade do tipo mensal não existe época alta."
            )

    def _ao_marcar_epoca_alta(self):
        tipo_mensal = self._tipo_selecionado() == "mensal"
        if self.epoca_alta_ativa.get() and tipo_mensal:
            self.epoca_alta_ativa.set(False)
            componentes.mostrar_erro(
                "Unidade do tipo mensal não existe época alta."
            )

    def _criar(self):
        try:
            preco_base = _ler_decimal(
                self.campo_preco_base.get(), "Preço base"
            )
            preco_epoca_alta = _ler_decimal(
                self.campo_preco_epoca_alta.get(), "Preço época alta"
            )
            multa = _ler_decimal(
                self.campo_multa.get(), "Multa de check-in tardio"
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            unidade = unidades.criar(
                self.prop["id"],
                self.campo_nome.get(),
                self._tipo_selecionado(),
                preco_base,
                preco_epoca_alta,
                multa,
                epoca_alta_ativa=self.epoca_alta_ativa.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Unidade criada com sucesso: {unidade['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class EditarUnidadeModal(ctk.CTkToplevel):
    """Modal de edição de uma unidade existente — mesmos campos de
    NovaUnidadeModal, pré-preenchidos; propriedade e tipo não se
    alteram (mesma regra de `unidades.atualizar`), por isso não há
    seletor de tipo aqui — só o rótulo, com o tipo real da unidade
    (06/09/2026: passou a poder ser "mensal" OU "airbnb", em vez de
    sempre "mensal" fixo no texto).
    """

    def __init__(self, tela_lista, uni, prop):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.uni = uni

        self.title(f"Editar Unidade — {uni['nome']}")
        self.geometry("380x520")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {uni['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text=f"Propriedade: {prop['nome']} · tipo: {uni['tipo']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        self.campo_nome = self._campo("Nome", uni["nome"])
        self.campo_preco_base = self._campo(
            "Preço base (€)", _formatar_valor(uni["preco_base"])
        )
        self.campo_preco_epoca_alta = self._campo(
            "Preço época alta (€)", _formatar_valor(uni["preco_epoca_alta"])
        )
        self.campo_multa = self._campo(
            "Multa check-in tardio (€)",
            _formatar_valor(uni["multa_check_in_tardio"]),
        )

        self.epoca_alta_ativa = ctk.BooleanVar(value=uni["epoca_alta_ativa"])
        ctk.CTkCheckBox(
            self,
            text="Época alta ativa",
            variable=self.epoca_alta_ativa,
            command=self._ao_marcar_epoca_alta,
        ).pack(anchor="w", padx=20, pady=(14, 0))

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
            text="Guardar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _campo(self, rotulo, valor_inicial):
        ctk.CTkLabel(
            self,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(6, 2))
        entrada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        entrada.insert(0, valor_inicial)
        entrada.pack(fill="x", padx=20)
        return entrada

    def _ao_marcar_epoca_alta(self):
        # Tipo é fixo aqui (não muda ao editar — regra de
        # unidades.atualizar), por isso só valida contra
        # self.uni["tipo"], sem seletor nenhum para reler.
        if self.epoca_alta_ativa.get() and self.uni["tipo"] == "mensal":
            self.epoca_alta_ativa.set(False)
            componentes.mostrar_erro(
                "Unidade do tipo mensal não existe época alta."
            )

    def _guardar(self):
        try:
            preco_base = _ler_decimal(
                self.campo_preco_base.get(), "Preço base"
            )
            preco_epoca_alta = _ler_decimal(
                self.campo_preco_epoca_alta.get(), "Preço época alta"
            )
            multa = _ler_decimal(
                self.campo_multa.get(), "Multa de check-in tardio"
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            unidades.atualizar(
                self.uni["id"],
                nome=self.campo_nome.get(),
                preco_base=preco_base,
                preco_epoca_alta=preco_epoca_alta,
                multa_check_in_tardio=multa,
                epoca_alta_ativa=self.epoca_alta_ativa.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Unidade {self.uni['id']} atualizada.")
        self.destroy()
        self.tela_lista._recarregar()
