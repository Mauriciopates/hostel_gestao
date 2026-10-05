"""Peças partilhadas pelas vistas do Dashboard.

`VistaBase` é o contrato de todas as vistas:

- `__init__(master, controlador)` — constrói logo o conteúdo.
- `atualizar()` — deita fora o conteúdo e volta a construí-lo com
  dados frescos. É o que o botão "↻ Atualizar" chama.
- `_recarregar()` — o MESMO que `atualizar()`, com o nome que os
  modais existentes esperam do ecrã que os abriu
  (`tela_lista._recarregar()` depois de gravar). É isto que deixa o
  Dashboard abrir `NovaReservaAirbnbModal`, `NovaRequisicaoModal`,
  `_ConfirmarRececaoModal`, etc., sem mexer nesses modais.

Reconstruir tudo é deliberado (a mesma decisão do Dashboard antigo,
`_recarregar`): são poucas dezenas de widgets, e uma versão "trocar
só os números" obrigava a guardar referências a cada rótulo sem
ganho que se note.
"""

import datetime

import customtkinter as ctk

from .. import componentes
from .. import tema

NOMES_DIAS_LONGOS = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)

NOMES_MESES_LONGOS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

# Largura das pílulas de estado nas listas — igual em todas as
# linhas, para o texto à esquerda ficar alinhado.
LARGURA_ETIQUETA = 96

# Espaço entre cartões lado a lado e entre filas de cartões.
ESPACO = 12


def data_curta(dia):
    """"seg 28/09" — dia da semana abreviado e data sem ano."""
    nomes = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")

    return f"{nomes[dia.weekday()]} {dia.strftime('%d/%m')}"


def data_longa(dia):
    """"domingo, 27/09/2026"."""
    return f"{NOMES_DIAS_LONGOS[dia.weekday()]}, {dia.strftime('%d/%m/%Y')}"


def plural(n, singular, plural_):
    """Escolhe a forma certa da palavra para `n`."""
    return singular if n == 1 else plural_


class VistaBase(ctk.CTkFrame):
    """Base das vistas: área com scroll + ciclo construir/atualizar.

    As subclasses só implementam `_construir()`, a desenhar dentro
    de `self.area`.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color="transparent")
        self.controlador = controlador
        self.hoje = datetime.date.today()

        self.area = componentes.AreaRolavel(self)
        self.area.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self._construir()

    def atualizar(self):
        """Volta a construir o conteúdo com dados frescos."""
        self.hoje = datetime.date.today()

        for filho in self.area.winfo_children():
            filho.destroy()

        self._construir()

    def _recarregar(self):
        """Nome que os modais existentes chamam depois de gravar."""
        self.atualizar()

    def _construir(self):
        raise NotImplementedError(
            "Cada vista do Dashboard tem de redefinir _construir."
        )


def titulo_secao(master, texto, primeira=False):
    """Título pequeno em maiúsculas dentro de um cartão ("ENTRADAS")."""
    componentes.Rotulo(master, texto.upper(), "secao").pack(
        fill="x", pady=(0 if primeira else 12, 2)
    )


def texto_vazio(master, texto):
    """Linha cinzenta para uma secção sem nada ("Sem entradas hoje.")."""
    componentes.Rotulo(master, texto, "secundario").pack(
        fill="x", pady=(4, 4)
    )


def linha_lista(master, titulo, detalhe="", etiqueta=None,
                estilo_etiqueta="info", ao_clicar=None, separador=True):
    """Uma linha de lista: título, detalhe por baixo, pílula à direita.

    Devolve o contentor da direita (`direita`), onde quem chama pode
    pôr um botão em vez de (ou além de) uma etiqueta. Com
    `ao_clicar`, a linha inteira fica clicável — mas o clique NÃO se
    liga aos botões da direita (conflituaria com o clique do botão;
    mesma lição do duplo clique nas tabelas, ficheiro 11).
    """
    if separador:
        componentes.Separador(master).pack(fill="x")

    linha = componentes.Contentor(master)
    linha.pack(fill="x", pady=6)

    # width/height=1: um CTkFrame vazio ocupa 200x200 por omissão, e
    # uma linha sem etiqueta nem botão ficava com 200px de altura.
    direita = componentes.Contentor(linha, width=1, height=1)
    direita.pack(side="right", padx=(8, 0))

    texto = componentes.Contentor(linha)
    texto.pack(side="left", fill="x", expand=True)

    componentes.Rotulo(texto, titulo, "forte").pack(fill="x")

    if detalhe:
        componentes.Rotulo(
            texto, detalhe, "secundario", wraplength=420, justify="left"
        ).pack(fill="x")

    if etiqueta:
        componentes.Etiqueta(
            direita, etiqueta, estilo_etiqueta, largura=LARGURA_ETIQUETA
        ).pack(side="right")

    if ao_clicar is not None:
        componentes.tornar_cliclavel(texto, ao_clicar)

    return direita


def caixa_alerta(master, titulo, detalhe, peso, ao_clicar):
    """Caixa colorida de um alerta, com "Ver ›" à direita.

    `peso` ("erro" | "aviso" | "info") escolhe a cor, pelos mesmos
    pares do tema que as etiquetas usam.
    """
    fundos = {
        "erro": tema.VERMELHO_ERRO,
        "aviso": tema.AMARELO_AVISO,
        "info": tema.ID_CHIP_FUNDO,
    }

    caixa = componentes.Contentor(
        master, fg_color=fundos.get(peso, tema.ID_CHIP_FUNDO),
        corner_radius=8,
    )
    caixa.pack(fill="x", pady=(0, 8))

    componentes.Botao(caixa, "Ver ›", ao_clicar, width=64).pack(
        side="right", padx=10, pady=8
    )

    textos = componentes.Contentor(caixa)
    textos.pack(side="left", fill="x", expand=True, padx=12, pady=8)

    componentes.Rotulo(textos, titulo, "forte").pack(fill="x")
    componentes.Rotulo(
        textos, detalhe, "secundario", wraplength=300, justify="left"
    ).pack(fill="x")

    componentes.tornar_cliclavel(textos, ao_clicar)


def abrir_ecra(controlador, nome):
    """Navega para um ecrã pelo nome.

    Importa tarde, dentro da função: importar estes ecrãs no topo
    criava um ciclo com o `app.py` (a mesma razão do
    `_resolver_ecra` do Dashboard antigo). Um nome desconhecido não
    faz nada — mais vale não navegar do que rebentar num clique.
    """
    classe = None

    if nome == "ListaAprovacao":
        from ..estoque.gui_est_aprovacao import ListaAprovacao

        classe = ListaAprovacao
    elif nome == "ListaProdutos":
        from ..estoque.gui_est_produtos import ListaProdutos

        classe = ListaProdutos
    elif nome == "ListaRequisicoes":
        from ..estoque.gui_est_requisicoes import ListaRequisicoes

        classe = ListaRequisicoes
    elif nome == "ListaContratosMensais":
        from ..contratos.gui_cnt_mensal_lista import ListaContratosMensais

        classe = ListaContratosMensais
    elif nome == "ListaClientes":
        from ..gui_clientes import ListaClientes

        classe = ListaClientes
    elif nome == "ListaPreCheckins":
        from ..gui_prechecking import ListaPreCheckins

        classe = ListaPreCheckins

    if classe is not None:
        controlador.mostrar_frame(classe)
