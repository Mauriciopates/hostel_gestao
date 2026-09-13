"""Ecrã de Gestão de Responsáveis.

Ciclo completo do módulo `responsaveis`: listar, criar, editar,
desativar e reativar. Mesma estrutura da Gestão de Propriedades —
barra de busca, "Mostrar inativos", tabela em `componentes.Tabela`
e botão "Gerir" por linha, que abre um popup com as ações.

Decisões desta entrega (09/09/2026):

1. Colunas: ID, NOME, CONTACTO, AÇÕES. Chegou a estar prevista uma
   coluna "unidade do responsável", mas as unidades geridas são
   várias por pessoa — não cabem numa célula. Passaram para um
   balão que aparece ao passar o rato sobre o crachá do ID, sem
   ser preciso clicar (`_BalaoUnidades`).

2. A ligação responsável-unidade não existia no modelo até esta
   entrega. Foi criada agora: tabela `responsavel_unidade` no
   MySQL e as funções `unidades.atribuir_responsavel`,
   `unidades.remover_atribuicao` e `unidades.unidades_geridas_por`.
   Antes disto, `responsavel_id` só aparecia em requisições,
   devoluções e movimentos — o responsável ligava-se ao que FAZ,
   nunca a um sítio onde está colocado.

3. "Definir como responsável ativo" entra nas ações. Até aqui, o
   `sessao.definir_responsavel_ativo` existia e não era chamado em
   lado nenhum da aplicação: o cabeçalho de todos os ecrãs mostrava
   "sem responsável" e o "Confirmar receção" das requisições nunca
   podia aparecer, porque compara o responsável ativo com quem fez
   o pedido. Este ecrã é o sítio natural para o resolver.

4. Definir o responsável ativo reconstrói o ecrã em vez de só
   recarregar a tabela. O `componentes.Cabecalho` lê a sessão uma
   única vez, quando é criado — recarregar a tabela deixava o canto
   superior direito a dizer "sem responsável" logo a seguir a
   escolher um.

5. Não há anonimização aqui, ao contrário de Clientes. O
   responsável não é hóspede: o prazo de conservação do RGPD não se
   lhe aplica, e desativar é a saída de quem deixa a operação, não
   um apagamento.

CONSOLIDAÇÃO DE HELPERS EM componentes.py (13/09/2026) — o helper
visual que estava duplicado localmente passou a viver só no
`componentes.py`:

- `_colocar_no_topo` local → `componentes.colocar_no_topo`
  (alias no topo, mesmo nome antigo, para o corpo do ficheiro não
  ter de ser reescrito). O resto do ficheiro não mudou.
"""
import customtkinter as ctk

import responsaveis
import unidades
from . import componentes
from . import sessao
from . import tema


# Aliases locais para os helpers que viviam neste ficheiro e passaram
# a viver em componentes.py. Mantêm-se os nomes antigos com "_" para
# o corpo do ficheiro não ter de ser reescrito — mesma técnica já
# usada no gui_propriedades.py, gui_contratos.py, gui_calendario.py,
# gui_unidades.py e gui_est_requisicoes.py.
_colocar_no_topo = componentes.colocar_no_topo


_LARGURA_ID = 70
_LARGURA_NOME = 190
_LARGURA_CONTACTO = 170
_LARGURA_ESTADO = 110
_LARGURA_ACOES = 100

# Crachá de estado: os mesmos pares de cor da Planta de Lugares e do
# calendário, para a leitura ser a mesma em todo o sistema.
_CORES_ESTADO = {
    True: (tema.VERDE_LIVRE, tema.TEXTO_LIVRE, "ativo"),
    False: (tema.VERMELHO_ERRO, tema.TEXTO_ERRO, "desativado"),
}

# Mesma disciplina da tabela de propriedades: NOME e CONTACTO
# repartem o espaço que sobra, ID e AÇÕES não crescem.
_COLUNAS_RESPONSAVEL = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("NOME", peso=3, minimo=_LARGURA_NOME),
    componentes.Coluna("CONTACTO", peso=3, minimo=_LARGURA_CONTACTO),
    componentes.Coluna(
        "ESTADO", peso=1, minimo=_LARGURA_ESTADO, alinhamento="centro"
    ),
    componentes.Coluna(
        "AÇÕES", minimo=_LARGURA_ACOES, alinhamento="centro"
    ),
)

_ALTURA_LINHA = 44

# Quantas unidades o balão mostra antes de resumir o resto.
_MAX_UNIDADES_BALAO = 6


class _BalaoUnidades:
    """Balão com as unidades geridas, ao passar o rato sobre o ID.

    Não é um widget: é o objeto que liga os eventos de entrada e
    saída do rato a um `CTkToplevel` sem decoração, criado só
    quando aparece e destruído quando o rato sai.

    Três detalhes que não são óbvios:

    - `overrideredirect(True)` tira a barra de título e as bordas,
      que é o que faz isto parecer um balão e não uma janela.
    - A lista é lida no momento em que o balão aparece, não quando
      a linha é desenhada: assim reflete o que está na base de
      dados agora, mesmo que se tenha atribuído uma unidade noutra
      janela entretanto.
    - Há um atraso antes de aparecer. Sem ele, arrastar o rato pela
      tabela abria e fechava um balão por cada linha atravessada.
    """

    ATRASO_MS = 350

    def __init__(self, alvo, responsavel_id):
        self.alvo = alvo
        self.responsavel_id = responsavel_id
        self.janela = None
        self.agendado = None

        alvo.bind("<Enter>", self._agendar, add="+")
        alvo.bind("<Leave>", self._esconder, add="+")
        # Sem isto, clicar no crachá deixava o balão pendurado.
        alvo.bind("<Button-1>", self._esconder, add="+")

    def _agendar(self, evento=None):
        self._cancelar()
        self.agendado = self.alvo.after(self.ATRASO_MS, self._mostrar)

    def _cancelar(self):
        if self.agendado is not None:
            self.alvo.after_cancel(self.agendado)
            self.agendado = None

    def _mostrar(self):
        self.agendado = None

        if self.janela is not None:
            return

        try:
            geridas = unidades.unidades_geridas_por(self.responsavel_id)
        except ValueError:
            return

        # Construída numa variável local e só guardada em
        # self.janela no fim. Além de ser mais claro, evita que o
        # verificador de tipos do editor conclua que o atributo é
        # sempre None (é assim que arranca no __init__) e marque
        # cada uso a vermelho.
        janela = ctk.CTkToplevel(self.alvo)
        janela.overrideredirect(True)
        janela.configure(fg_color=tema.COR_FUNDO)
        janela.attributes("-topmost", True)

        moldura = ctk.CTkFrame(
            janela,
            corner_radius=8,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        moldura.pack(fill="both", expand=True)

        ctk.CTkLabel(
            moldura,
            text="UNIDADES GERIDAS",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 4))

        if not geridas:
            ctk.CTkLabel(
                moldura,
                text="Nenhuma unidade atribuída.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).pack(fill="x", padx=12, pady=(0, 10))
        else:
            for unidade in geridas[:_MAX_UNIDADES_BALAO]:
                ctk.CTkLabel(
                    moldura,
                    text=f"{unidade['id']} · {unidade['nome']}",
                    text_color=tema.COR_TEXTO,
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                ).pack(fill="x", padx=12, pady=1)

            se_faltam = len(geridas) - _MAX_UNIDADES_BALAO

            if se_faltam > 0:
                ctk.CTkLabel(
                    moldura,
                    text=f"e mais {se_faltam}…",
                    text_color=tema.COR_TEXTO_SECUNDARIO,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                ).pack(fill="x", padx=12, pady=(2, 0))

            ctk.CTkFrame(moldura, height=1, fg_color="transparent").pack(
                pady=(0, 8)
            )

        self._posicionar(janela)
        self.janela = janela

    def _posicionar(self, janela):
        """Encosta o balão ao canto inferior esquerdo do crachá.

        Recebe a janela em vez de a ir buscar a self.janela: quando
        isto corre, o atributo ainda não foi atribuído.

        Usa coordenadas de ecrã (`winfo_rootx`), não relativas ao
        pai: o crachá está dentro de uma célula, dentro de uma
        linha, dentro de uma grelha com scroll, e as coordenadas
        relativas não sobreviveriam a essa profundidade toda.
        """
        janela.update_idletasks()

        x = self.alvo.winfo_rootx()
        y = self.alvo.winfo_rooty() + self.alvo.winfo_height() + 4

        largura = janela.winfo_reqwidth()
        altura = janela.winfo_reqheight()
        ecra_largura = janela.winfo_screenwidth()
        ecra_altura = janela.winfo_screenheight()

        # Se não couber para baixo ou à direita, vira ao contrário —
        # senão o balão saía do ecrã nas últimas linhas da tabela.
        if y + altura > ecra_altura:
            y = self.alvo.winfo_rooty() - altura - 4

        if x + largura > ecra_largura:
            x = ecra_largura - largura - 8

        janela.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _esconder(self, evento=None):
        self._cancelar()

        if self.janela is not None:
            self.janela.destroy()
            self.janela = None


class ListaResponsaveis(ctk.CTkFrame):
    """Lista de responsáveis, com busca e filtro de inativos."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(
            self, titulo="Gestão de Responsáveis"
        ).pack(fill="x")

        # Botão de criação numa barra própria, logo abaixo do
        # cabeçalho e a verde — mesmo padrão de Contrato Mensal e
        # Reservas Airbnb (09/09/2026). Estava em baixo e a azul,
        # o que o deixava fora do campo de visão em listas longas
        # e sem se distinguir dos botões de ação das linhas.
        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Novo Responsável",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovoResponsavelModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome ou ID… (Enter)",
            width=220,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="left")
        # Só filtra ao premir Enter, como nos outros ecrãs: filtrar
        # a cada tecla redesenhava a lista inteira a cada letra.
        self.campo_busca.bind("<Return>", lambda evento: self._recarregar())

        self.mostrar_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativos",
            variable=self.mostrar_inativos,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right")

        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_RESPONSAVEL,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia="Ainda não há responsáveis cadastrados.",
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 4))

        ctk.CTkLabel(
            self,
            text="Passe o rato sobre o ID para ver as unidades geridas.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=24, pady=(0, 6))

        # Os balões vivem enquanto as linhas viverem: guardados para
        # não serem recolhidos pelo Python enquanto a tabela existe.
        self._baloes = []

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela.

        Chamada na abertura do ecrã, ao mexer em "Mostrar inativos",
        ao confirmar uma busca, e depois de qualquer criação,
        edição, desativação, reativação ou mudança de unidades.
        """
        self.tabela.limpar()
        self._baloes = []

        incluir_inativos = self.mostrar_inativos.get()
        texto_busca = self.campo_busca.get().strip().lower()
        lista = responsaveis.listar(incluir_inativos=incluir_inativos)

        if texto_busca:
            lista = [
                registo
                for registo in lista
                if texto_busca
                in f"{registo['nome']} {registo['id']}".lower()
            ]

        if not lista:
            self.tabela.mostrar_vazio(
                "Nenhum responsável encontrado para a busca."
                if texto_busca
                else None
            )
            return

        for registo in lista:
            self._desenhar_responsavel(registo)

    def _desenhar_responsavel(self, registo):
        """Desenha uma linha da tabela.

        Cada célula é criada com a linha como master e colocada com
        `self.tabela.colocar`, que trata do grid, do alinhamento e
        das folgas a partir de `_COLUNAS_RESPONSAVEL`.
        """
        inativo = not registo["ativo"]
        ativo_na_sessao = self._e_o_ativo(registo)

        linha = self.tabela.nova_linha()

        cracha = ctk.CTkLabel(
            linha,
            text=registo["id"],
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=_LARGURA_ID,
            anchor="w",
        )
        self.tabela.colocar(linha, 0, cracha, esticar="w")
        self._baloes.append(_BalaoUnidades(cracha, registo["id"]))

        # Ativo/desativado passou para a coluna ESTADO, com crachá,
        # igual à tabela de unidades. Por baixo do nome fica só o
        # marcador da sessão — e diz "(em sessão)", não
        # "(responsável ativo)": com o crachá a dizer "ativo" ao
        # lado, a mesma palavra estaria a significar duas coisas
        # diferentes na mesma linha (09/09/2026).
        texto_nome = registo["nome"]

        if ativo_na_sessao:
            texto_nome += "\n(em sessão)"

        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=texto_nome,
                text_color=(
                    tema.TEXTO_INDISPONIVEL if inativo else tema.COR_TEXTO
                ),
                font=ctk.CTkFont(size=13),
                width=_LARGURA_NOME,
                anchor="w",
                justify="left",
            ),
        )

        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=registo["contacto"] or "—",
                text_color=(
                    tema.TEXTO_INDISPONIVEL
                    if inativo
                    else tema.COR_TEXTO_SECUNDARIO
                ),
                font=ctk.CTkFont(size=12),
                width=_LARGURA_CONTACTO,
                anchor="w",
            ),
        )

        fundo, cor_texto, rotulo = _CORES_ESTADO[registo["ativo"]]
        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=rotulo,
                text_color=cor_texto,
                fg_color=fundo,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ESTADO,
                height=22,
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
                command=lambda: _AcoesResponsavelModal(self, registo),
            )
        )

    def _e_o_ativo(self, registo):
        """Diz se este é o responsável ativo da sessão."""
        ativo = sessao.obter_responsavel_ativo()

        return ativo is not None and ativo["id"] == registo["id"]

    # -- ações -------------------------------------------------------

    def _definir_ativo(self, registo):
        """Passa este responsável a ser o da sessão.

        Reconstrói o ecrã em vez de só recarregar a tabela: o
        `Cabecalho` lê a sessão quando é criado, e recarregar
        deixava o canto superior direito a dizer "sem responsável"
        logo a seguir a escolher um.
        """
        try:
            sessao.definir_responsavel_ativo(registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"{registo['nome']} passou a ser o responsável ativo."
        )
        self.controlador.mostrar_frame(ListaResponsaveis)

    def _desativar(self, registo):
        if not componentes.confirmar(
            f"Desativar o responsável {registo['nome']}?\n\n"
            "Deixa de poder registar novas operações em seu nome. O "
            "histórico já gravado mantém-se intacto.",
            titulo="Desativar responsável",
        ):
            return

        try:
            responsaveis.desativar(registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        # Se era o responsável ativo, a sessão fica sem ninguém: um
        # inativo não passa na validação de autoria, e deixá-lo lá
        # dava erro na primeira operação que o usasse.
        if self._e_o_ativo(registo):
            sessao.limpar_responsavel_ativo()
            componentes.mostrar_sucesso(
                f"{registo['nome']} foi desativado. A sessão ficou sem "
                "responsável ativo."
            )
            self.controlador.mostrar_frame(ListaResponsaveis)
            return

        componentes.mostrar_sucesso(
            f"Responsável {registo['nome']} desativado."
        )
        self._recarregar()

    def _reativar(self, registo):
        try:
            responsaveis.reativar(registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Responsável {registo['nome']} reativado."
        )
        self._recarregar()


class _AcoesResponsavelModal(ctk.CTkToplevel):
    """Popup pequeno com as ações de um responsável.

    Mesmo padrão dos popups de propriedade e de unidade: todos os
    botões com a mesma forma, altura e contorno, só a cor do texto a
    distinguir a intenção, e um risco antes da ação destrutiva.
    """

    def __init__(self, tela_lista, registo):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.registo = registo

        self.title(f"Ações — {registo['id']}")
        self.geometry("320x300")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        self._centrar_sobre(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=registo["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=registo["id"],
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if registo["ativo"]:
            # Cinzento em vez de escondido quando já é o ativo: o
            # popup mantém a mesma forma e mostra porque não se pode
            # clicar, em vez de a opção desaparecer sem explicação.
            self._botao(
                "Definir como responsável ativo",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: self.tela_lista._definir_ativo(registo),
                ativo=not tela_lista._e_o_ativo(registo),
            )
            self._botao(
                "Gerir Unidades",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: UnidadesDoResponsavelModal(
                    self.tela_lista, registo
                ),
            )
            self._botao(
                "Editar",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EditarResponsavelModal(
                    self.tela_lista, registo
                ),
            )
            self._separador()
            self._botao(
                "Desativar",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: self.tela_lista._desativar(registo),
            )
        else:
            self._botao(
                "Reativar",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self.tela_lista._reativar(registo),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(10, 16))

    def _centrar_sobre(self, janela):
        """Abre por cima da janela que o chamou.

        Sem isto o Tk coloca o popup no canto superior esquerdo do
        ecrã, longe do botão que acabou de ser clicado.
        """
        janela.update_idletasks()
        x = janela.winfo_rootx() + (janela.winfo_width() - 320) // 2
        y = janela.winfo_rooty() + (janela.winfo_height() - 300) // 2
        self.geometry(f"320x300+{max(x, 0)}+{max(y, 0)}")

    def _separador(self):
        """Risco fino antes da ação destrutiva."""
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, text_color, hover_color, acao, ativo=True):
        """Botão de ação: fecha este popup antes de agir.

        A ordem importa. As ações recarregam ou reconstroem o ecrã
        por trás — deixar este popup aberto por cima deixava-o
        pendurado sobre coisas que entretanto mudaram.
        """

        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=32,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color if ativo else tema.TEXTO_INDISPONIVEL,
            border_width=1,
            border_color=tema.COR_BORDA,
            state="normal" if ativo else "disabled",
            command=executar,
        ).pack(fill="x", padx=20, pady=3)


class UnidadesDoResponsavelModal(ctk.CTkToplevel):
    """Popup para atribuir e remover as unidades que um responsável
    gere.

    É o único sítio que alimenta o balão da tabela — sem este
    ecrã, o balão estaria sempre vazio.

    O seletor mostra apenas as unidades que ainda NÃO estão
    atribuídas a esta pessoa. Mostrar todas e recusar as repetidas
    no momento de gravar seria dar a escolher algo que já se sabe
    que vai falhar.
    """

    def __init__(self, tela_lista, registo):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.registo = registo

        self.title(f"Gerir Unidades — {registo['id']}")
        self.geometry("520x520")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=registo["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 0))

        ctk.CTkLabel(
            self,
            text="Unidades que este responsável gere",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20)

        self.combo_unidade = ctk.CTkOptionMenu(
            barra,
            values=["—"],
            width=300,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_unidade.pack(side="left")

        ctk.CTkButton(
            barra,
            text="+ Adicionar",
            width=110,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._adicionar,
        ).pack(side="left", padx=(8, 0))

        cartao = ctk.CTkFrame(
            self,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="both", expand=True, padx=20, pady=(14, 8))

        self.area_geridas = ctk.CTkScrollableFrame(
            cartao, fg_color="transparent"
        )
        self.area_geridas.pack(fill="both", expand=True)

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self._fechar,
        ).pack(fill="x", padx=20, pady=(0, 16))

        self._recarregar()

    def _fechar(self):
        """Fecha e recarrega a tabela por trás.

        A tabela mostra o balão com as unidades geridas — se não
        recarregasse, o balão continuaria a mostrar a lista antiga
        até a próxima ida ao ecrã.
        """
        self.destroy()
        self.tela_lista._recarregar()

    # -- carregamento ------------------------------------------------

    def _recarregar(self):
        for widget in self.area_geridas.winfo_children():
            widget.destroy()

        try:
            geridas = unidades.unidades_geridas_por(self.registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        geridas.sort(key=lambda unidade: unidade["nome"])
        self._preencher_seletor(geridas)

        if not geridas:
            ctk.CTkLabel(
                self.area_geridas,
                text="Nenhuma unidade atribuída.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=13),
            ).pack(pady=30)
            return

        for indice, unidade in enumerate(geridas):
            self._desenhar_gerida(unidade, indice % 2 == 1)

    def _preencher_seletor(self, geridas):
        """Só as unidades ainda não atribuídas a esta pessoa."""
        ja_geridas = {unidade["id"] for unidade in geridas}

        disponiveis = [
            unidade
            for unidade in unidades.listar()
            if unidade["id"] not in ja_geridas
        ]
        disponiveis.sort(key=lambda unidade: unidade["nome"])

        self.id_por_rotulo = {
            f"{unidade['id']} · {unidade['nome']}": unidade["id"]
            for unidade in disponiveis
        }

        if self.id_por_rotulo:
            rotulos = sorted(self.id_por_rotulo)
            self.combo_unidade.configure(values=rotulos, state="normal")
            self.combo_unidade.set(rotulos[0])
        else:
            # Todas as unidades ativas já estão atribuídas.
            self.combo_unidade.configure(
                values=["— Sem unidades disponíveis —"], state="disabled"
            )
            self.combo_unidade.set("— Sem unidades disponíveis —")

    def _desenhar_gerida(self, unidade, tingida):
        linha = ctk.CTkFrame(
            self.area_geridas,
            height=38,
            corner_radius=0,
            fg_color=tema.LINHA_ALTERNADA if tingida else "transparent",
        )
        linha.pack(fill="x")
        # `height` sem isto não é respeitado: um CTkFrame cresce até
        # ao tamanho dos filhos e assume 200px quando não tem
        # nenhum.
        linha.pack_propagate(False)

        ctk.CTkLabel(
            linha,
            text=f"{unidade['id']} · {unidade['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left", padx=(14, 0))

        ctk.CTkButton(
            linha,
            text="Remover",
            width=80,
            height=24,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=lambda: self._remover(unidade),
        ).pack(side="right", padx=(0, 14))

    # -- ações -------------------------------------------------------

    def _adicionar(self):
        unidade_id = self.id_por_rotulo.get(self.combo_unidade.get())

        if unidade_id is None:
            componentes.mostrar_erro("Escolha uma unidade a acrescentar.")
            return

        try:
            unidades.atribuir_responsavel(unidade_id, self.registo["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self._recarregar()

    def _remover(self, unidade):
        if not componentes.confirmar(
            f"Deixar de atribuir {unidade['nome']} a "
            f"{self.registo['nome']}?",
            titulo="Remover unidade",
        ):
            return

        try:
            unidades.remover_atribuicao(
                unidade["id"], self.registo["id"]
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self._recarregar()


class _FormularioResponsavel(ctk.CTkToplevel):
    """Base dos formulários de criar e editar.

    Os dois têm exatamente os mesmos dois campos e a mesma
    disposição; só muda o título, o texto do botão e o que acontece
    ao gravar. Duplicar o formulário era duplicar também cada
    correção futura de layout.
    """

    def __init__(self, tela_lista, titulo, texto_botao, nome="",
                 contacto=""):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title(titulo)
        self.geometry("440x310")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=titulo,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 16))

        ctk.CTkLabel(
            self,
            text="Nome",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_nome = ctk.CTkEntry(
            self, corner_radius=tema.RAIO_CAMPO
        )
        self.campo_nome.pack(fill="x", padx=20, pady=(2, 12))
        self.campo_nome.insert(0, nome)

        ctk.CTkLabel(
            self,
            text="Contacto (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.campo_contacto = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="Telefone, email ou extensão interna",
        )
        self.campo_contacto.pack(fill="x", padx=20, pady=(2, 6))
        self.campo_contacto.insert(0, contacto)

        ctk.CTkLabel(
            self,
            text="O formato do contacto é livre e não é validado.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=20)

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=16)

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
            text=texto_botao,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._gravar,
        ).pack(side="right")

        self.campo_nome.focus_set()

    def _valores(self):
        return (
            self.campo_nome.get().strip(),
            self.campo_contacto.get().strip(),
        )

    def _gravar(self):
        raise NotImplementedError


class NovoResponsavelModal(_FormularioResponsavel):
    """Formulário de criação de um responsável."""

    def __init__(self, tela_lista):
        super().__init__(
            tela_lista,
            titulo="Novo Responsável",
            texto_botao="Criar",
        )

    def _gravar(self):
        nome, contacto = self._valores()

        try:
            registo = responsaveis.criar(nome, contacto)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Responsável criado com sucesso: {registo['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class EditarResponsavelModal(_FormularioResponsavel):
    """Formulário de edição do nome e do contacto."""

    def __init__(self, tela_lista, registo):
        self.registo = registo
        super().__init__(
            tela_lista,
            titulo=f"Editar Responsável — {registo['id']}",
            texto_botao="Guardar",
            nome=registo["nome"],
            contacto=registo["contacto"],
        )

    def _gravar(self):
        nome, contacto = self._valores()

        try:
            responsaveis.atualizar(
                self.registo["id"], nome=nome, contacto=contacto
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso("Responsável atualizado.")
        self.destroy()
        self.tela_lista._recarregar()