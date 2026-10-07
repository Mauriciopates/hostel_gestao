"""Ecrã "Regras do Rol" do Stock (v1.9.0 — mockup aprovado pelo aluno
a 05/10/2026).

Diz que roupa vai para cada tipo de cama quando se regista uma
reserva Airbnb (o Rol de lavandaria). Um separador por tipo de cama
(solteiro, casal, beliche por par, extra casal, extra solteiro); à
esquerda a tabela da regra, à direita a pré-visualização do que uma
cama desse tipo envia em cada limpeza.

Avisos por cima dos separadores:
- unidades com cama extra ainda sem tamanho (as criadas antes da
  v1.9.0) — a cama extra delas não envia roupa;
- base sem produtos nenhum: botão para criar o kit de roupa de base
  (o mesmo que o 1.º arranque oferece).

Só Admin/Master chegam aqui (o cartão do hub é `so_admin`); as
funções de `estoque` voltam a validar o perfil (regra 11.2).

Mudar uma regra só vale para reservas NOVAS — o Rol é calculado no
momento em que a reserva é registada.
"""

import customtkinter as ctk

import estoque
import unidades
from .. import componentes
from .. import sessao
from .. import tema

# Rótulo do separador e frase da pré-visualização, por tipo de cama.
_ROTULOS = {
    "solteiro": "Solteiro",
    "casal": "Casal",
    "beliche": "Beliche (par)",
    "extra_casal": "Extra casal",
    "extra_solteiro": "Extra solteiro",
}
_FRASES = {
    "solteiro": "1 cama de solteiro",
    "casal": "1 cama de casal",
    "beliche": "1 beliche (2 camas)",
    "extra_casal": "1 cama extra de casal",
    "extra_solteiro": "1 cama extra de solteiro",
}
_TIPOS_PRODUTO = {
    "roupa_cama": "roupa de cama",
    "roupa_banho": "roupa de banho",
}

_COLUNAS = (
    componentes.Coluna("ID", minimo=94, espaco=8),
    componentes.Coluna("PRODUTO", peso=1, minimo=150),
    componentes.Coluna(
        "QTD. POR CAMA", minimo=100, alinhamento="centro"
    ),
    componentes.Coluna("AÇÕES", minimo=84, alinhamento="centro"),
)

_ALTURA_LINHA = 48


def _autor_id():
    ativo = sessao.obter_responsavel_ativo()
    return ativo["id"] if ativo else None


class RegrasRol(ctk.CTkFrame):
    """Ecrã das regras do Rol de lavandaria."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador
        self.tipo_atual = "casal"
        self._regras = []

        componentes.Cabecalho(self, titulo="Regras do Rol").pack(fill="x")

        topo = componentes.Contentor(self)
        topo.pack(fill="x", padx=20)
        componentes.Botao(
            topo, "< Voltar ao Stock", self._voltar, estilo="contorno"
        ).pack(side="left", pady=(0, 8))

        self._faixa(
            "Quando se regista uma reserva Airbnb, o sistema conta as "
            "camas da unidade e envia, para cada cama, os produtos "
            "definidos aqui. Só entram produtos de roupa (cama ou "
            "banho) ativos. Mudar uma regra só vale para reservas "
            "novas.",
            tema.ID_CHIP_FUNDO,
            tema.AZUL_PRINCIPAL,
        )

        # Avisos variáveis (cama extra sem tamanho, base sem produtos)
        # — redesenhados a cada `_recarregar`.
        # Só é empacotada quando há avisos (`_desenhar_avisos`). Um
        # CTkFrame VAZIO ocupa 200x200 (lição 13 do ficheiro 11), e um
        # frame que perde os filhos não volta a encolher — sem avisos
        # deixava um buraco antes dos separadores.
        self.zona_avisos = componentes.Contentor(self)

        self.barra_tabs = componentes.Contentor(self)
        self.barra_tabs.pack(fill="x", padx=20, pady=(4, 0))
        self.botoes_tabs = {}
        for tipo in estoque.TIPOS_CAMA_ROL:
            botao = componentes.Botao(
                self.barra_tabs,
                _ROTULOS[tipo],
                lambda t=tipo: self._mudar_tab(t),
                estilo="discreto",
                corner_radius=0,
                width=130,
            )
            botao.pack(side="left")
            self.botoes_tabs[tipo] = botao
        componentes.Separador(self).pack(fill="x", padx=20)

        corpo = componentes.Contentor(self)
        corpo.pack(fill="both", expand=True, padx=20, pady=(10, 16))
        # 2/3 para a tabela, 1/3 para a pré-visualização: com a janela
        # no tamanho mínimo, a tabela (~430 px de colunas) ainda cabe.
        corpo.grid_columnconfigure(0, weight=2, uniform="corpo")
        corpo.grid_columnconfigure(1, weight=1, uniform="corpo")
        corpo.grid_rowconfigure(0, weight=1)

        esquerda = componentes.Contentor(corpo)
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        componentes.Botao(
            esquerda,
            "+ Adicionar produto",
            self._abrir_adicionar,
            estilo="sucesso",
        ).pack(anchor="w", pady=(0, 8))
        self.tabela = componentes.Tabela(
            esquerda,
            colunas=_COLUNAS,
            altura_linha=_ALTURA_LINHA,
            mensagem_vazia=(
                "Ainda não há produtos nesta regra.\n"
                "Sem regra, esta cama não envia roupa no Rol."
            ),
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True)

        self.cartao_previa = componentes.Cartao(
            corpo, titulo="Pré-visualização"
        )
        self.cartao_previa.grid(row=0, column=1, sticky="nsew")

        self._recarregar()

    # -- construção ----------------------------------------------------

    def _faixa(self, texto, fundo, cor, master=None, botao=None):
        """Faixa colorida de uma linha (informação ou aviso)."""
        faixa = ctk.CTkFrame(
            master or self, fg_color=fundo, corner_radius=tema.RAIO_CAMPO
        )
        faixa.pack(fill="x", padx=20, pady=(0, 8))
        # Quebra pensada para a janela no tamanho mínimo (950 px).
        componentes.Rotulo(
            faixa, texto, "texto", cor=cor,
            wraplength=560 if botao else 680,
            justify="left", height=0,
        ).pack(side="left", fill="x", expand=True, padx=12, pady=8)

        if botao is not None:
            texto_botao, comando = botao
            componentes.Botao(
                faixa, texto_botao, comando, estilo="primario"
            ).pack(side="right", padx=10, pady=6)

        return faixa

    def _desenhar_avisos(self):
        for filho in self.zona_avisos.winfo_children():
            filho.destroy()
        self.zona_avisos.pack_forget()

        sem_tamanho = unidades.com_cama_extra_sem_tamanho()
        if sem_tamanho:
            nomes = ", ".join(u["nome"] for u in sem_tamanho[:4])
            if len(sem_tamanho) > 4:
                nomes += ", …"
            n = len(sem_tamanho)
            frase = (
                "1 unidade com cama extra sem tamanho definido"
                if n == 1
                else f"{n} unidades com cama extra sem tamanho definido"
            )
            self._faixa(
                f"{frase} ({nomes}): a cama extra não envia roupa. "
                "Defina o tamanho em Gestão de Propriedades → Editar "
                "unidade → Cama extra.",
                tema.AMARELO_AVISO,
                tema.TEXTO_AVISO,
                master=self.zona_avisos,
            )

        if estoque.pode_criar_kit_roupa():
            self._faixa(
                "Ainda não há produtos no Stock. Pode começar com o kit "
                "de roupa de base (7 produtos e as regras de cada cama) "
                "e ajustar depois.",
                tema.AMARELO_AVISO,
                tema.TEXTO_AVISO,
                master=self.zona_avisos,
                botao=("Criar kit de roupa", self._criar_kit),
            )

    def _mostrar_zona_avisos(self):
        """Empacota a zona dos avisos por cima dos separadores, só se
        tiver algum aviso lá dentro."""
        if self.zona_avisos.winfo_children():
            self.zona_avisos.pack(fill="x", before=self.barra_tabs)

    # -- dados -----------------------------------------------------------

    def _recarregar(self):
        self._regras = estoque.listar_regras_rol()
        self._desenhar_avisos()
        self._mostrar_zona_avisos()
        self._desenhar_tabs()
        self._desenhar_tabela()
        self._desenhar_previa()

    def _regras_do_tipo(self, tipo):
        return [r for r in self._regras if r["tipo_cama"] == tipo]

    def _mudar_tab(self, tipo):
        self.tipo_atual = tipo
        self._desenhar_tabs()
        self._desenhar_tabela()
        self._desenhar_previa()

    def _desenhar_tabs(self):
        for tipo, botao in self.botoes_tabs.items():
            n = len(self._regras_do_tipo(tipo))
            ativo = tipo == self.tipo_atual
            botao.configure(
                text=f"{_ROTULOS[tipo]}  ({n})",
                fg_color=tema.AZUL_PRINCIPAL if ativo else "transparent",
                text_color="#FFFFFF" if ativo else tema.AZUL_PRINCIPAL,
                hover_color=(
                    tema.AZUL_CLARO if ativo else tema.LINHA_ALTERNADA
                ),
                font=ctk.CTkFont(
                    size=12, weight="bold" if ativo else "normal"
                ),
            )

    def _desenhar_tabela(self):
        self.tabela.limpar()
        regras = self._regras_do_tipo(self.tipo_atual)

        if not regras:
            self.tabela.mostrar_vazio()
            return

        for regra in regras:
            self._desenhar_linha(regra)

    def _desenhar_linha(self, regra):
        linha = self.tabela.nova_linha()
        ativo = regra["produto_ativo"]
        cor = tema.COR_TEXTO if ativo else tema.TEXTO_INDISPONIVEL

        self.tabela.colocar(
            linha,
            0,
            componentes.ChipId(
                linha, regra["produto_id"], inativo=not ativo, largura=84
            ),
            esticar="w",
        )

        celula = componentes.Contentor(linha)
        componentes.Rotulo(
            celula, regra["produto_nome"], "texto", cor=cor
        ).pack(anchor="w")
        detalhe = _TIPOS_PRODUTO.get(regra["tipo_produto"], "")
        if not ativo:
            detalhe = "desativado (não é enviado)"
        componentes.Rotulo(celula, detalhe, "secundario").pack(anchor="w")
        self.tabela.colocar(linha, 1, celula, esticar="w")

        self.tabela.colocar(
            linha,
            2,
            componentes.Rotulo(
                linha, str(regra["quantidade"]), "forte", cor=cor,
                anchor="center",
            ),
        )

        acoes = self.tabela.celula_acoes(linha, 3)
        acoes.adicionar(
            componentes.Botao(
                acoes,
                "Gerir",
                lambda r=regra: GerirRegraModal(self, r),
                estilo="contorno",
                width=64,
                height=26,
            )
        )

    def _desenhar_previa(self):
        corpo = self.cartao_previa.corpo
        for filho in corpo.winfo_children():
            filho.destroy()

        regras = [
            r for r in self._regras_do_tipo(self.tipo_atual)
            if r["produto_ativo"]
        ]

        componentes.Rotulo(
            corpo,
            f"{_FRASES[self.tipo_atual]} envia, em cada limpeza:",
            "secundario",
        ).pack(anchor="w", pady=(0, 8))

        if not regras:
            componentes.Etiqueta(
                corpo, "Nada, esta cama não recebe roupa", estilo="aviso"
            ).pack(anchor="w")
            return

        for regra in regras:
            fila = componentes.Contentor(corpo)
            fila.pack(fill="x", pady=2)
            componentes.Rotulo(fila, regra["produto_nome"], "texto").pack(
                side="left"
            )
            componentes.Rotulo(
                fila, f"× {regra['quantidade']}", "forte",
                cor=tema.AZUL_PRINCIPAL,
            ).pack(side="right")

        total = sum(r["quantidade"] for r in regras)
        componentes.Separador(corpo).pack(fill="x", pady=(8, 4))
        componentes.Rotulo(
            corpo, f"Total: {total} peças por cama", "forte"
        ).pack(anchor="e")

    # -- ações -----------------------------------------------------------

    def _voltar(self):
        from .gui_est_hub import EcraStock

        self.controlador.mostrar_frame(EcraStock)

    def _abrir_adicionar(self):
        candidatos = estoque.produtos_para_regra_rol(self.tipo_atual)

        if not candidatos:
            componentes.mostrar_erro(
                "Não há produtos de roupa ativos que ainda não estejam "
                "nesta regra. Crie-os em Stock → Produtos (tipo roupa "
                "de cama ou roupa de banho).",
                titulo="Sem produtos",
            )
            return

        AdicionarRegraModal(self, self.tipo_atual, candidatos)

    def _criar_kit(self):
        if not componentes.confirmar(
            "Criar os 7 produtos de roupa de base (com stock 0) e as "
            "regras de cada tipo de cama?\n\nPode mudar tudo depois.",
            titulo="Kit de roupa",
        ):
            return

        try:
            resultado = estoque.criar_kit_roupa_base(_autor_id())
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Kit criado: {len(resultado['produtos'])} produtos e "
            f"{resultado['regras']} regras.\n\nAs entradas de stock "
            "fazem-se em Stock → Movimentos.",
            titulo="Kit de roupa",
        )
        self._recarregar()


def _ler_quantidade(texto):
    try:
        return int(texto.strip())
    except ValueError:
        raise ValueError(
            "A quantidade tem de ser um número inteiro."
        ) from None


class _ModalRegra(ctk.CTkToplevel):
    """Base dos dois popups: título, subtítulo e campo de quantidade."""

    def __init__(self, tela, titulo_janela, titulo, subtitulo, altura):
        super().__init__(tela)
        self.tela = tela
        self.title(titulo_janela)
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela.winfo_toplevel())

        self.corpo = componentes.Contentor(self)
        self.corpo.pack(fill="both", expand=True, padx=20, pady=16)
        componentes.Rotulo(self.corpo, titulo, "titulo").pack(anchor="w")
        componentes.Rotulo(self.corpo, subtitulo, "secundario").pack(
            anchor="w", pady=(0, 12)
        )

        componentes.centrar_sobre(self, tela.winfo_toplevel(), 440, altura)
        componentes.colocar_no_topo(self)

    def _campo_quantidade(self, inicial):
        componentes.Rotulo(
            self.corpo, "Quantidade por cama *", "secundario"
        ).pack(anchor="w")
        campo = componentes.CampoTexto(self.corpo, width=100)
        campo.insert(0, str(inicial))
        campo.pack(anchor="w", pady=(2, 10))
        return campo


class AdicionarRegraModal(_ModalRegra):
    """Popup "+ Adicionar produto" de uma regra."""

    def __init__(self, tela, tipo_cama, candidatos):
        super().__init__(
            tela,
            "Adicionar produto à regra",
            "Adicionar produto",
            f"Regra: {_FRASES[tipo_cama][2:]}",
            300,
        )
        self.tipo_cama = tipo_cama
        self.id_por_rotulo = {
            f"{p['nome']} · {p['id']}": p["id"] for p in candidatos
        }

        componentes.Rotulo(self.corpo, "Produto *", "secundario").pack(
            anchor="w"
        )
        self.seletor = componentes.Seletor(
            self.corpo,
            values=list(self.id_por_rotulo),
            width=300,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.seletor.set(next(iter(self.id_por_rotulo)))
        self.seletor.pack(anchor="w", pady=(2, 10))

        self.campo_qtd = self._campo_quantidade(1)

        rodape = componentes.Contentor(self.corpo)
        rodape.pack(fill="x", side="bottom")
        componentes.Botao(rodape, "Cancelar", self.destroy).pack(
            side="left"
        )
        componentes.Botao(
            rodape, "Adicionar", self._adicionar, estilo="primario"
        ).pack(side="right")

    def _adicionar(self):
        try:
            estoque.adicionar_regra_rol(
                self.tipo_cama,
                self.id_por_rotulo[self.seletor.get()],
                _ler_quantidade(self.campo_qtd.get()),
                _autor_id(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.destroy()
        self.tela._recarregar()


class GerirRegraModal(_ModalRegra):
    """Popup "Gerir" de uma linha: mudar a quantidade ou retirar o
    produto da regra."""

    def __init__(self, tela, regra):
        super().__init__(
            tela,
            "Gerir regra",
            regra["produto_nome"],
            f"{regra['produto_id']} · regra: "
            f"{_FRASES[regra['tipo_cama']][2:]}",
            240,
        )
        self.regra = regra
        self.campo_qtd = self._campo_quantidade(regra["quantidade"])

        rodape = componentes.Contentor(self.corpo)
        rodape.pack(fill="x", side="bottom")
        retirar = componentes.Botao(
            rodape, "Retirar desta regra", self._retirar, estilo="discreto"
        )
        # O estilo "discreto" fixa o texto escuro; aqui é uma ação de
        # remoção, por isso vai a vermelho.
        retirar.configure(text_color=tema.TEXTO_ERRO)
        retirar.pack(side="left")
        componentes.Botao(
            rodape, "Guardar", self._guardar, estilo="primario"
        ).pack(side="right")
        componentes.Botao(rodape, "Cancelar", self.destroy).pack(
            side="right", padx=(0, 8)
        )

    def _guardar(self):
        try:
            estoque.alterar_quantidade_regra_rol(
                self.regra["id"],
                _ler_quantidade(self.campo_qtd.get()),
                _autor_id(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.destroy()
        self.tela._recarregar()

    def _retirar(self):
        if not componentes.confirmar(
            f"Retirar {self.regra['produto_nome']} desta regra?",
            titulo="Retirar produto",
        ):
            return

        try:
            estoque.retirar_regra_rol(self.regra["id"], _autor_id())
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.destroy()
        self.tela._recarregar()
