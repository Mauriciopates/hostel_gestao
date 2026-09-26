"""Ecrã de gestão de fornecedores e os seus modais."""

import customtkinter as ctk

import despesas

from .. import componentes
from .. import tema
from . import gui_desp_comum

# Helpers partilhados — alias local, mesmo padrão do
# gui_est_aprovacao.py (nomes públicos em gui_desp_comum).
_autor_atual = gui_desp_comum.autor_atual


# =====================================================================
# ECRÃ FORNECEDORES
# =====================================================================


class Fornecedores(ctk.CTkFrame):
    """Ecrã de gestão de fornecedores.

    Mesmo padrão do `Categorias`, com uma coluna extra (CONTACTO).
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Fornecedores").pack(fill="x")

        self._montar_barra()

        self.tabela = componentes.Tabela(
            self,
            colunas=(
                componentes.Coluna("ID", minimo=114, espaco=8),
                componentes.Coluna("NOME", peso=3, minimo=220),
                componentes.Coluna("CONTACTO", peso=2, minimo=170),
                componentes.Coluna(
                    "ESTADO",
                    peso=1,
                    minimo=110,
                    alinhamento="centro",
                ),
                componentes.Coluna("AÇÕES", minimo=100, alinhamento="centro"),
            ),
            altura_linha=44,
            mensagem_vazia="Ainda não há fornecedores.",
            tom_alternado=True,
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    def _montar_barra(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20, pady=(4, 8))

        ctk.CTkButton(
            barra,
            text="+ Novo Fornecedor",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: _NovoFornecedorModal(self),
        ).pack(side="left")

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome… (Enter)",
            width=220,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="right")
        self.campo_busca.bind("<Return>", lambda _e: self._recarregar())

        self.mostrar_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativos",
            variable=self.mostrar_inativos,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=(12, 0))

    def _recarregar(self):
        self.tabela.limpar()
        incluir = self.mostrar_inativos.get()
        busca = self.campo_busca.get().strip().lower()

        lista = despesas.listar_fornecedores(incluir_inativos=incluir)

        if busca:
            lista = [f for f in lista if busca in f["nome"].lower()]

        if not lista:
            self.tabela.mostrar_vazio(
                "Nenhum fornecedor encontrado." if busca else None
            )
            return

        for f in lista:
            self._desenhar_fornecedor(f)

    def _desenhar_fornecedor(self, f):
        ativo = f["ativo"]
        linha = self.tabela.nova_linha()

        self.tabela.colocar(
            linha,
            0,
            ctk.CTkLabel(
                linha,
                text=f["id"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL
                    if not ativo
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
                text=f["nome"],
                text_color=(
                    tema.TEXTO_INDISPONIVEL if not ativo else tema.COR_TEXTO
                ),
                font=ctk.CTkFont(size=13),
                anchor="w",
            ),
        )

        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=f["contacto"] or "—",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ),
        )

        chip_texto = "ativo" if ativo else "inativo"
        chip_fundo = tema.VERDE_LIVRE if ativo else tema.CINZA_INDISPONIVEL
        chip_cor = tema.TEXTO_LIVRE if ativo else tema.TEXTO_INDISPONIVEL

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
                width=100,
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
                command=lambda f=f: _GerirFornecedorModal(self, f),
            )
        )

    def _desativar(self, f):
        if not componentes.confirmar(
            f"Desativar o fornecedor '{f['nome']}'?\n\n"
            "As despesas antigas continuam a apontar para ele."
        ):
            return

        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.desativar_fornecedor(f["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Fornecedor '{f['nome']}' desativado.")
        self._recarregar()

    def _reativar(self, f):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.reativar_fornecedor(f["id"], autor)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Fornecedor '{f['nome']}' reativado.")
        self._recarregar()


class _NovoFornecedorModal(ctk.CTkToplevel):
    """Modal de criação de fornecedor — nome, contacto, nif."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        largura, altura = 420, 380
        self.title("Novo fornecedor")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Novo fornecedor",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 14))

        self.campo_nome = self._campo("Nome *")
        self.campo_contacto = self._campo("Contacto")
        self.campo_nif = self._campo("NIF")

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

    def _campo(self, rotulo, placeholder=""):
        ctk.CTkLabel(
            self,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(6, 2))
        entrada = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text=placeholder,
        )
        entrada.pack(fill="x", padx=24)
        return entrada

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.criar_fornecedor(
                self.campo_nome.get(),
                autor,
                contacto=self.campo_contacto.get(),
                nif=self.campo_nif.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso("Fornecedor criado.")
        self.destroy()
        self.tela_lista._recarregar()


class _GerirFornecedorModal(ctk.CTkToplevel):
    """Popup de ações — Editar + Desativar ou Reativar."""

    def __init__(self, tela_lista, fornecedor):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.fornecedor = fornecedor

        ativo = fornecedor["ativo"]
        altura = 240 if ativo else 200

        largura = 340
        self.title(f"Gerir — {fornecedor['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=fornecedor["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=280,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=(
                f"{fornecedor['id']} · " + ("ativo" if ativo else "inativo")
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if ativo:
            self._botao(
                "Editar",
                cor=tema.COR_TEXTO,
                acao=lambda: _EditarFornecedorModal(tela_lista, fornecedor),
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
        self.tela_lista._desativar(self.fornecedor)

    def _reativar(self):
        self.tela_lista._reativar(self.fornecedor)


class _EditarFornecedorModal(ctk.CTkToplevel):
    """Edição dos campos de um fornecedor existente."""

    def __init__(self, tela_lista, fornecedor):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.fornecedor = fornecedor

        largura, altura = 420, 380
        self.title(f"Editar — {fornecedor['id']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        componentes.centrar_sobre(self, tela_lista, largura, altura)
        componentes.colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {fornecedor['id']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(18, 14))

        self.campo_nome = self._campo("Nome *", fornecedor["nome"])
        self.campo_contacto = self._campo("Contacto", fornecedor["contacto"])
        self.campo_nif = self._campo("NIF", fornecedor["nif"])

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

    def _campo(self, rotulo, valor_inicial=""):
        ctk.CTkLabel(
            self,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=24, pady=(6, 2))
        entrada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        entrada.insert(0, valor_inicial)
        entrada.pack(fill="x", padx=24)
        return entrada

    def _guardar(self):
        autor = _autor_atual()
        if autor is None:
            componentes.mostrar_erro(
                "Defina um responsável ativo antes de continuar."
            )
            return

        try:
            despesas.atualizar_fornecedor(
                self.fornecedor["id"],
                autor,
                nome=self.campo_nome.get(),
                contacto=self.campo_contacto.get(),
                nif=self.campo_nif.get(),
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Fornecedor {self.fornecedor['id']} atualizado."
        )
        self.destroy()
        self.tela_lista._recarregar()
