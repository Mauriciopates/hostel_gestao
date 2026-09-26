"""Ecrã de gestão de categorias de despesa e os seus modais."""

import customtkinter as ctk

import despesas

from .. import componentes
from .. import tema
from . import gui_desp_comum

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_desp_comum).
_autor_atual = gui_desp_comum.autor_atual


# =====================================================================
# ECRÃ CATEGORIAS
# =====================================================================


class Categorias(ctk.CTkFrame):
    """Ecrã de gestão de categorias de despesa.

    Segue o padrão dos outros ecrãs (botão "+ Nova", busca,
    "Mostrar inativas", tabela, botão "Gerir" por linha). O modal
    Gerir permite Editar, Desativar ou Reativar — a ação
    Desativar/Reativar depende do estado atual.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Categorias").pack(fill="x")

        self._montar_barra()

        self.tabela = componentes.Tabela(
            self,
            colunas=(
                componentes.Coluna("ID", minimo=114, espaco=8),
                componentes.Coluna("NOME", peso=3, minimo=260),
                componentes.Coluna(
                    "ESTADO",
                    peso=1,
                    minimo=110,
                    alinhamento="centro",
                ),
                componentes.Coluna("AÇÕES", minimo=100, alinhamento="centro"),
            ),
            altura_linha=44,
            mensagem_vazia="Ainda não há categorias.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    def _montar_barra(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 8))

        ctk.CTkButton(
            barra,
            text="+ Nova Categoria",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _NovaCategoriaModal(self),
        ).pack(side="left")

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome… (Enter)",
            width=220,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="right")
        self.campo_busca.bind("<Return>", lambda _e: self._recarregar())

        self.mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativas",
            variable=self.mostrar_inativas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

    def _recarregar(self):
        self.tabela.limpar()
        incluir = self.mostrar_inativas.get()
        busca = self.campo_busca.get().strip().lower()

        lista = despesas.listar_categorias(incluir_inativas=incluir)

        if busca:
            lista = [c for c in lista if busca in c["nome"].lower()]

        if not lista:
            self.tabela.mostrar_vazio(
                "Nenhuma categoria encontrada." if busca else None
            )
            return

        for c in lista:
            self._desenhar_categoria(c)

    def _desenhar_categoria(self, c):
        ativa = c["ativo"]
        linha = self.tabela.nova_linha()

        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=c["id"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL
                    if not ativa
                    else tema.AZUL_PRINCIPAL
                ),
                fg_color=tema.ID_CHIP_FUNDO,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=90,
                anchor="w",
            ),
            esticar="w",
        )

        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=c["nome"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL if not ativa else tema.COR_TEXTO
                ),
                font=ctk.CTkFont(size=13),
                anchor="w",
            ),
        )

        chip_texto = "ativa" if ativa else "inativa"
        chip_fundo = tema.VERDE_LIVRE if ativa else tema.CINZA_INDISPONIVEL
        chip_cor = tema.TEXTO_LIVRE if ativa else tema.TEXTO_INDISPONIVEL

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
                width=100,
                height=22,
            ),
        )

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
                command=lambda c=c: _GerirCategoriaModal(self, c),
            )
        )

    def _desativar(self, c):
        if not componentes.confirmar(
            f"Desativar a categoria '{c['nome']}'?\n\n"
            "As despesas antigas continuam a apontar para ela."
        ):
            return

        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.desativar_categoria(c["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Categoria '{c['nome']}' desativada.")
        self._recarregar()

    def _reativar(self, c):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.reativar_categoria(c["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Categoria '{c['nome']}' reativada.")
        self._recarregar()


class _NovaCategoriaModal(ctk.CTkToplevel):
    """Modal simples: só nome."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 400, 280
        self.title("Nova categoria")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Nova categoria",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 14))

        ctk.CTkLabel(
            self,
            text="Nome *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_nome = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: Limpeza, Manutenção, …",
        )
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 6))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=34,
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
            text="Criar",
            width=130,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        nome = self.campo_nome.get().strip()
        try:
            despesas.criar_categoria(nome, autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Categoria '{nome}' criada.")
        self.destroy()
        self.tela_lista._recarregar()


class _GerirCategoriaModal(ctk.CTkToplevel):
    """Popup de ações de uma categoria — Editar + Desativar ou
    Reativar."""

    def __init__(self, tela_lista, categoria):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.categoria = categoria

        ativa = categoria["ativo"]
        altura = 240 if ativa else 200

        largura = 320
        self.title(f"Gerir — {categoria['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=categoria["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=f"{categoria['id']} · " + ("ativa" if ativa else "inativa"),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if ativa:
            self._botao(
                "Editar",
                cor=tema.COR_TEXTO,
                acao=lambda: _EditarCategoriaModal(tela_lista, categoria),
            )
            self._separador()
            self._botao(
                "Desativar",
                cor=tema.TEXTO_ERRO,
                acao=lambda: self._desativar(),
            )
        else:
            self._botao(
                "Reativar",
                cor=tema.TEXTO_LIVRE,
                acao=lambda: self._reativar(),
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

    def _separador(self):
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, cor, acao):
        def executar():
            self.destroy()
            acao()

        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=cor,
            hover_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)

    def _desativar(self):
        self.tela_lista._desativar(self.categoria)

    def _reativar(self):
        self.tela_lista._reativar(self.categoria)


class _EditarCategoriaModal(ctk.CTkToplevel):
    """Edição do nome de uma categoria existente."""

    def __init__(self, tela_lista, categoria):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.categoria = categoria

        largura, altura = 400, 280
        self.title(f"Editar — {categoria['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {categoria['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 14))

        ctk.CTkLabel(
            self,
            text="Nome *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24)
        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.insert(0, categoria["nome"])
        self.campo_nome.pack(fill="x", padx=24, pady=(2, 6))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(14, 18), side="bottom")

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            width=130,
            height=34,
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
            width=130,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        nome = self.campo_nome.get().strip()
        try:
            despesas.atualizar_categoria(self.categoria["id"], nome, autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Categoria {self.categoria['id']} atualizada."
        )
        self.destroy()
        self.tela_lista._recarregar()
