"""Guia de entrega — modal do botão "Guia de entrega" em
Stock · Rota de Envio (27/09/2026, v1.6.0 — mockup aprovado pelo
aluno; 10/10/2026: o botão passou de Requisições para a Rota de
Envio e a guia passou a ser por unidade, com o Rol de Lavandaria).

Escolhe-se a data de envio, vê-se o resumo por unidade (o Rol e os
pedidos que vão para cada uma) e só depois se gera o PDF — um bloco
por unidade, depois um bloco por staff com os pedidos dele.

A lógica toda vive em `estoque.guia_entrega` (agrupamento, totais,
validação de perfil) e o PDF em `impressao.gerar_guia_entrega_pdf`;
este ficheiro só desenha e chama.
"""

import datetime

import customtkinter as ctk

import estoque
import impressao
from impressao.base import abrir_no_sistema
from .. import componentes
from .. import sessao
from .. import tema

_LARGURA = 640
_ALTURA = 640
_FORMATO_DATA = "%d/%m/%Y"


class GuiaEntregaModal(ctk.CTkToplevel):
    """Data de envio → resumo por staff → "Gerar PDF"."""

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.blocos = []
        self.data_envio = datetime.date.today()

        self.title("Guia de entrega")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista.winfo_toplevel())

        ctk.CTkLabel(
            self,
            text="Guia de entrega",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=22, pady=(18, 0))
        ctk.CTkLabel(
            self,
            text=(
                "Tudo o que foi enviado do armazém no dia escolhido, "
                "separado pela unidade de destino."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=22, pady=(0, 12))

        self._montar_linha_data()

        self.faixa_resumo = ctk.CTkFrame(self, fg_color="transparent")
        self.faixa_resumo.pack(fill="x", padx=22, pady=(0, 10))

        # Rodapé primeiro (side="bottom"), para a lista ficar com o
        # espaço que sobra no meio.
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=22, pady=(8, 16))
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
        self.botao_gerar = ctk.CTkButton(
            rodape,
            text="Gerar PDF",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._gerar_pdf,
        )
        self.botao_gerar.pack(side="right")

        ctk.CTkLabel(
            self,
            text=(
                "Entram as requisições com data de envio = dia "
                "escolhido, estejam \"enviada\" ou já \"fechada\"."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="bottom", anchor="w", padx=22)

        self.lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.lista.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        componentes.centrar_sobre(
            self, tela_lista.winfo_toplevel(), _LARGURA, _ALTURA
        )
        componentes.colocar_no_topo(self)

        self._carregar()

    # -- construção ------------------------------------------------------

    def _montar_linha_data(self):
        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=22, pady=(0, 12))

        ctk.CTkLabel(
            linha,
            text="Data de envio",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w")

        self.campo_data = componentes.CampoData(linha, width=140)
        self.campo_data.insert(0, self.data_envio.strftime(_FORMATO_DATA))
        self.campo_data.pack(side="left")
        # Enter no campo (nunca <FocusOut> — lição da v1.5.0).
        self.campo_data.bind("<Return>", lambda evento: self._carregar())

        for texto, dias in (("Hoje", 0), ("Ontem", 1)):
            ctk.CTkButton(
                linha,
                text=texto,
                width=70,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda d=dias: self._escolher_dia(d),
            ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            linha,
            text="Atualizar",
            width=90,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=self._carregar,
        ).pack(side="left", padx=(8, 0))

    def _escolher_dia(self, dias_atras):
        data = datetime.date.today() - datetime.timedelta(days=dias_atras)
        self.campo_data.delete(0, "end")
        self.campo_data.insert(0, data.strftime(_FORMATO_DATA))
        self._carregar()

    # -- dados -----------------------------------------------------------

    def _carregar(self):
        texto = self.campo_data.get().strip()
        try:
            data = datetime.datetime.strptime(texto, _FORMATO_DATA).date()
        except ValueError:
            componentes.mostrar_erro(
                "Data de envio inválida — use o formato dd/mm/aaaa."
            )
            return

        try:
            blocos = estoque.guia_entrega(
                data, sessao.tipo_utilizador_ativo()
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        self.data_envio = data
        self.blocos = blocos
        self._desenhar_resumo()
        self._desenhar_blocos()

    def _desenhar_resumo(self):
        for filho in self.faixa_resumo.winfo_children():
            filho.destroy()

        n_unidades = sum(1 for b in self.blocos if not b["sem_unidade"])
        n_rol = sum(len(b["rol"]) for b in self.blocos)
        n_req = sum(len(b["requisicoes"]) for b in self.blocos)
        # Rol sem unidade reconhecível (nota antiga ou editada à mão).
        rol_sem_unidade = sum(
            len(b["rol"])
            for b in self.blocos
            if b["sem_unidade"] and not b.get("staff")
        )

        for valor, rotulo, aviso in (
            (n_unidades, "unidades", False),
            (n_rol, "rol lavandaria", False),
            (n_req, "pedidos de staff", False),
            (rol_sem_unidade, "rol sem unidade", rol_sem_unidade > 0),
        ):
            cartao = ctk.CTkFrame(
                self.faixa_resumo,
                corner_radius=tema.RAIO_CAMPO,
                fg_color=(
                    tema.AMARELO_AVISO if aviso
                    else tema.CABECALHO_TABELA_FUNDO
                ),
            )
            cartao.pack(side="left", fill="x", expand=True, padx=(0, 8))
            cor = tema.TEXTO_AVISO if aviso else tema.COR_TEXTO
            ctk.CTkLabel(
                cartao,
                text=str(valor),
                text_color=cor,
                font=ctk.CTkFont(size=18, weight="bold"),
            ).pack(anchor="w", padx=10, pady=(6, 0))
            ctk.CTkLabel(
                cartao,
                text=rotulo,
                text_color=(
                    tema.TEXTO_AVISO if aviso
                    else tema.COR_TEXTO_SECUNDARIO
                ),
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=10, pady=(0, 6))

        self.botao_gerar.configure(
            state="normal" if self.blocos else "disabled"
        )

    def _desenhar_blocos(self):
        for filho in self.lista.winfo_children():
            filho.destroy()

        if not self.blocos:
            ctk.CTkLabel(
                self.lista,
                text=(
                    "Sem envios em "
                    f"{self.data_envio.strftime(_FORMATO_DATA)}."
                ),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=13),
            ).pack(pady=40)
            return

        for bloco in self.blocos:
            self._cartao_bloco(bloco)

    def _cartao_bloco(self, bloco):
        # Amarelo só no Rol sem unidade (é um aviso); os pedidos de
        # staff são normais.
        aviso = bloco["sem_unidade"] and not bloco.get("staff")
        cartao = ctk.CTkFrame(
            self.lista,
            corner_radius=tema.RAIO_CAMPO,
            border_width=1,
            border_color=tema.TEXTO_AVISO if aviso else tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(fill="x", padx=6, pady=(0, 8))

        cabecalho = ctk.CTkFrame(
            cartao,
            corner_radius=tema.RAIO_CAMPO,
            fg_color=(
                tema.AMARELO_AVISO if aviso
                else tema.CABECALHO_TABELA_FUNDO
            ),
        )
        cabecalho.pack(fill="x", padx=1, pady=(1, 0))

        if bloco.get("staff"):
            nome = f"Pedidos de staff · {bloco['staff']['nome']}"
        elif aviso:
            nome = "Rol sem unidade"
        else:
            unidade = bloco["unidade"]
            propriedade = unidade.get("propriedade_nome") or ""
            prefixo = f"{propriedade} · " if propriedade else ""
            nome = f"{prefixo}{unidade['nome']} ({unidade['id']})"
        cor = tema.TEXTO_AVISO if aviso else tema.COR_TEXTO
        ctk.CTkLabel(
            cabecalho,
            text=nome,
            text_color=cor,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=12, pady=6)

        partes = []
        if bloco["rol"]:
            partes.append(f"{len(bloco['rol'])} rol")
        if bloco["requisicoes"]:
            n = len(bloco["requisicoes"])
            partes.append(f"{n} pedido{'' if n == 1 else 's'}")
        ctk.CTkLabel(
            cabecalho,
            text=" · ".join(partes),
            text_color=cor,
            font=ctk.CTkFont(size=12),
        ).pack(side="right", padx=12)

        ids = [f"{e['id']} rol" for e in bloco["rol"]] + [
            f"{e['id']} ({e['estado']})" for e in bloco["requisicoes"]
        ]
        n_produtos = len(bloco["totais"])
        ctk.CTkLabel(
            cartao,
            text=(
                f"{' · '.join(ids)} — {n_produtos} "
                f"produto{'' if n_produtos == 1 else 's'}, "
                f"{bloco['total_itens']} itens"
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            wraplength=_LARGURA - 80,
            justify="left",
        ).pack(anchor="w", padx=12, pady=8)

    # -- ação ------------------------------------------------------------

    def _gerar_pdf(self):
        if not self.blocos:
            return

        ativo = sessao.obter_responsavel_ativo()
        gerado_por = ativo["nome"] if ativo else "—"

        try:
            caminho = impressao.gerar_guia_entrega_pdf(
                self.data_envio, self.blocos, gerado_por
            )
        except OSError as erro:
            componentes.mostrar_erro(
                f"Não foi possível gravar o PDF: {erro}"
            )
            return

        componentes.mostrar_sucesso(f"Guia de entrega gerada:\n{caminho}")
        abrir_no_sistema(caminho)
        self.destroy()
