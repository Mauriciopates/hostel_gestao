"""Modal de confirmação antes de gravar uma reserva Airbnb
(`_ConfirmacaoAirbnb`): desconto + Rol de Lavanderia."""

import customtkinter as ctk

import estoque
import responsaveis
import unidades

from gui import componentes, tema

# Aliases locais para helpers que vivem em componentes.py (nomes
# antigos com "_", para o corpo não ter de ser reescrito).
_formatar_valor = componentes.formatar_valor
_colocar_no_topo = componentes.colocar_no_topo


# =====================================================================
# CONFIRMAÇÃO AIRBNB — Fase 4, v1.4.0
# =====================================================================
#
# Modal único de confirmação antes de gravar uma reserva Airbnb:
#
# - Zona 1 (condicional): só aparece quando o preço praticado é
#   inferior ao calculado. Reaproveita o desenho do antigo
#   `_AlterarValorCalculadoModal` (calculado / praticado / diferença
#   + responsável obrigatório). O campo "Motivo" saiu a 28/09/2026:
#   era pedido mas nunca gravado — a decisão 18 identifica o
#   desconto pelo responsável que o autoriza, não por texto livre.
#
# - Zona 2 (sempre): Rol de Lavanderia pré-preenchido, só de leitura,
#   com os produtos e quantidades calculados a partir dos lugares
#   ativos da unidade + cama extra. Aviso verde (stock suficiente) ou
#   amarelo (stock insuficiente) por baixo.
#
# O botão "Confirmar" grava a reserva E cria o Rol; "Cancelar" não
# grava nada. Substitui o `_AlterarValorCalculadoModal`, que é
# apagado no fim do bloco 5a.


class _ConfirmacaoAirbnb(ctk.CTkToplevel):
    """Confirmação da reserva Airbnb — modal único, com as duas
    zonas descritas acima."""

    def __init__(
        self,
        master,
        unidade,
        cliente,
        data_inicio,
        data_fim,
        preco_calculado,
        preco_praticado,
        check_in_tardio,
        hora_chegada,
        multa_praticada,
        responsavel_multa_id,
        ao_confirmar,
    ):
        super().__init__(master)

        self.unidade = unidade
        self.cliente = cliente
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.preco_calculado = preco_calculado
        self.preco_praticado = preco_praticado
        self.check_in_tardio = check_in_tardio
        self.hora_chegada = hora_chegada
        self.multa_praticada = multa_praticada
        self.responsavel_multa_id = responsavel_multa_id
        self.ao_confirmar = ao_confirmar

        # FASE 4 — o Rol de Lavanderia é calculado já aqui, no
        # __init__, para o ecrã abrir já preenchido. A reserva ainda
        # não existe, mas o cálculo só precisa da unidade.
        try:
            self.produtos_rol, self.produtos_desativados = (
                estoque.calcular_rol_lavanderia(unidade["id"])
            )
        except ValueError:
            # Se a unidade por algum motivo já não existir, abre o
            # modal na mesma (o cliente ainda pode querer ver a
            # reserva); a Zona 2 aparece vazia.
            self.produtos_rol = []
            self.produtos_desativados = []

        tem_desconto = (
            preco_calculado is not None and preco_praticado < preco_calculado
        )

        # Altura variável — sem Zona 1, o modal é mais baixo. O
        # ajuste real de altura faz-se no fim do `__init__` (ver
        # `_ajustar_altura`), depois de todos os widgets estarem
        # construídos.
        largura, altura = 560, 600

        self.title(f"Confirmar Reserva — {unidade['nome']}")
        self.geometry(f"{largura}x{altura}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        _colocar_no_topo(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # ---- Cabeçalho (título + cliente + unidade + estadia) ----
        self._construir_cabecalho()

        # ---- Corpo (Zona 1 condicional + Zona 2 sempre) ----
        corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=20, pady=(0, 4))
        self.corpo = corpo

        if tem_desconto:
            self._construir_zona_1(corpo)

        self._construir_zona_2(corpo)

        # ---- Rodapé ----
        self._construir_rodape()

        # Ajusta a altura ao conteúdo real. Sem isto, o modal com
        # Zona 1 ficava com scroll desnecessário (o conteúdo cabia
        # em 600) e o modal sem Zona 1 ficava com espaço vazio em
        # baixo. `update_idletasks()` primeiro para o Tk calcular as
        # alturas dos filhos; só depois `winfo_reqheight()`.
        self.after(20, self._ajustar_altura)

    def _ajustar_altura(self):
        """Redimensiona o modal à altura que o conteúdo já pede.

        Usa `tkinter.Toplevel.geometry` (a versão de base, não a do
        customtkinter) porque `CTkToplevel.geometry` volta a
        multiplicar o valor pela escala da janela — e o
        `winfo_reqheight()` já vem em pixéis reais, escalados.
        Mesma técnica de `_ajustar_tamanho` em `gui_propriedades.py`
        (ver lição sobre geometria, ficheiro 11).
        """
        import tkinter

        self.update_idletasks()
        largura = 560
        altura = self.winfo_reqheight()

        # Uma folga mínima para o rodapé não colar ao bordo.
        altura = max(altura, 300)

        tkinter.Toplevel.geometry(self, f"{largura}x{altura}")

    # -- cabeçalho ----------------------------------------------------

    def _construir_cabecalho(self):
        """Cabeçalho: título + cliente + unidade + estadia."""
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            cabecalho,
            text=f"Confirmar Reserva — {self.unidade['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x")

        noites = (self.data_fim - self.data_inicio).days
        meta = (
            f"Cliente: {self.cliente['nome']} "
            f"({self.cliente['id']}) · "
            f"Unidade: {self.unidade['nome']} "
            f"({self.unidade['id']})\n"
            f"Estadia: {self.data_inicio.strftime('%d/%m/%Y')} → "
            f"{self.data_fim.strftime('%d/%m/%Y')} · "
            f"{noites} noites"
        )

        ctk.CTkLabel(
            cabecalho,
            text=meta,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(4, 0))

    # -- zona 1 (desconto, condicional) ------------------------------

    def _construir_zona_1(self, master):
        """Zona 1 — só quando há desconto (preço praticado inferior
        ao calculado).

        Reaproveita o desenho do antigo `_AlterarValorCalculadoModal`:
        cartão com calculado / praticado / diferença, mais o
        responsável do desconto (obrigatório).
        """
        ctk.CTkLabel(
            master,
            text="PREÇO PRATICADO DIVERGENTE DO CALCULADO",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(4, 6))

        cartao = ctk.CTkFrame(
            master,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x")

        corpo = ctk.CTkFrame(cartao, fg_color="transparent")
        corpo.pack(fill="x", padx=16, pady=12)

        diferenca = self.preco_praticado - self.preco_calculado

        self._linha_cartao(
            corpo, "Preço calculado", _formatar_valor(self.preco_calculado)
        )
        self._linha_cartao(
            corpo, "Preço praticado", _formatar_valor(self.preco_praticado)
        )

        ctk.CTkFrame(corpo, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", pady=(6, 4)
        )

        self._linha_cartao(
            corpo,
            "Diferença",
            _formatar_valor(diferenca),
            cor_valor=tema.TEXTO_ERRO,
        )

        # ---- Responsável do desconto (obrigatório) ----
        ctk.CTkLabel(
            corpo,
            text="Responsável do desconto *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(12, 2))

        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Escolher —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]

        self.combo_responsavel = componentes.Seletor(
            corpo,
            values=nomes,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.combo_responsavel.set(nomes[0])
        self.combo_responsavel.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(
            corpo,
            text=(
                "Obrigatório quando o preço praticado é inferior ao "
                "calculado."
            ),
            text_color=tema.TEXTO_AVISO,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x")

    # -- helper da zona 1 --------------------------------------------

    def _linha_cartao(self, master, rotulo, valor, cor_valor=None):
        """Uma linha rótulo → valor dentro do cartão da Zona 1."""
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", pady=2)

        ctk.CTkLabel(
            linha,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=valor,
            text_color=cor_valor or tema.COR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="e",
        ).pack(side="right")

    def _responsavel_escolhido_id(self):
        """ID do responsável do desconto escolhido no dropdown da
        Zona 1, ou "" se nenhum."""
        if not hasattr(self, "combo_responsavel"):
            return ""

        indice = self.combo_responsavel.cget("values").index(
            self.combo_responsavel.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    # -- zona 2 (Rol, sempre) ----------------------------------------

    def _construir_zona_2(self, master):
        """Zona 2 — Rol de Lavanderia. Sempre presente, só leitura.

        Mostra o chip "ROL LAVANDERIA", a nota "Calculado a partir
        de: ..." (que ajuda a perceber os números) e a tabela
        produto / pedido / em armazém. Se houver stock insuficiente
        ou produtos desativados ignorados, aparece a faixa amarela
        por baixo; caso contrário, faixa verde.
        """
        ctk.CTkLabel(
            master,
            text="ROL DE LAVANDERIA",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(6, 4))

        cartao = ctk.CTkFrame(
            master,
            fg_color=tema.COR_FUNDO,
            border_width=1,
            border_color=tema.COR_BORDA,
            corner_radius=tema.RAIO_CARTAO,
        )
        cartao.pack(fill="x")

        # ---- Cabeçalho do cartão (título + chip + nota) ----
        cabecalho = ctk.CTkFrame(
            cartao,
            corner_radius=0,
            fg_color=tema.CABECALHO_TABELA_FUNDO,
        )
        cabecalho.pack(fill="x")

        linha_titulo = ctk.CTkFrame(cabecalho, fg_color="transparent")
        linha_titulo.pack(fill="x", padx=16, pady=(12, 2))

        ctk.CTkLabel(
            linha_titulo,
            text="Roupa de cama e banho",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            linha_titulo,
            text="ROL LAVANDERIA",
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            padx=8,
            pady=2,
        ).pack(side="right")

        nota = self._texto_nota_rol()
        ctk.CTkLabel(
            cabecalho,
            text=nota,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=16, pady=(0, 10))

        # ---- Tabela de produtos ----
        if not self.produtos_rol:
            ctk.CTkLabel(
                cartao,
                text="Sem produtos a enviar para esta unidade.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).pack(fill="x", padx=16, pady=(12, 16))
            return

        # Cabeçalho da tabela
        linha_cabecalho = ctk.CTkFrame(cartao, fg_color="transparent")
        linha_cabecalho.pack(fill="x", padx=16, pady=(10, 2))

        for texto, largura, alinhamento in (
            ("PRODUTO", 280, "w"),
            ("PEDIDO", 90, "center"),
            ("EM ARMAZÉM", 110, "center"),
        ):
            ctk.CTkLabel(
                linha_cabecalho,
                text=texto,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=largura,
                anchor=alinhamento,
            ).pack(side="left")

        ctk.CTkFrame(cartao, height=1, fg_color=tema.COR_BORDA).pack(fill="x")

        # Linhas
        for p in self.produtos_rol:
            linha = ctk.CTkFrame(cartao, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=6)

            ctk.CTkLabel(
                linha,
                text=p["nome"],
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12),
                width=280,
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                linha,
                text=str(p["quantidade"]),
                text_color=tema.COR_TEXTO,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=90,
                anchor="center",
            ).pack(side="left")

            try:
                saldo = estoque.saldo_produto(p["produto_id"])
            except ValueError:
                saldo = 0

            falta = saldo < p["quantidade"]

            ctk.CTkLabel(
                linha,
                text=str(saldo),
                text_color=(
                    tema.TEXTO_ERRO if falta else tema.COR_TEXTO_SECUNDARIO
                ),
                font=ctk.CTkFont(
                    size=12, weight="bold" if falta else "normal"
                ),
                width=110,
                anchor="center",
            ).pack(side="left")

        # ---- Faixa de stock (verde / amarela) ----
        ctk.CTkFrame(cartao, height=6, fg_color="transparent").pack()
        self._construir_faixa_stock(cartao)

    # -- helpers da zona 2 -------------------------------------------

    def _texto_nota_rol(self):
        """Monta a nota "Calculado a partir de: X + Y + Z" que
        aparece por baixo do título da Zona 2. Conta os lugares por
        tipo de cama da unidade."""
        try:
            quartos = unidades.listar_quartos(unidade_id=self.unidade["id"])
        except ValueError:
            return "Calculado a partir dos lugares da unidade."

        contagem = {"casal": 0, "solteiro": 0, "beliche": 0}

        for quarto in quartos:
            for lugar in unidades.listar_lugares(quarto_id=quarto["id"]):
                tipo = lugar["tipo_cama"]
                if tipo in contagem:
                    contagem[tipo] += 1

        partes = []

        if contagem["casal"]:
            partes.append(
                f"{contagem['casal']} cama"
                + ("s" if contagem["casal"] > 1 else "")
                + " de casal"
            )

        if contagem["solteiro"]:
            partes.append(
                f"{contagem['solteiro']} cama"
                + ("s" if contagem["solteiro"] > 1 else "")
                + " de solteiro"
            )

        if contagem["beliche"]:
            pares = contagem["beliche"] // 2
            partes.append(f"{pares} beliche" + ("s" if pares > 1 else ""))

        extra = ""
        if (
            self.unidade.get("permite_cama_extra")
            and self.unidade.get("categoria_cama_extra")
            and (self.unidade.get("qtd_cama_extra") or 0) > 0
        ):
            qtd = self.unidade["qtd_cama_extra"]
            cat = self.unidade["categoria_cama_extra"]
            extra = (
                f" + {qtd} cama"
                + ("s" if qtd > 1 else "")
                + f" extra de {cat}"
            )

        if not partes and not extra:
            return "Sem lugares ativos — Rol vazio."

        return "Calculado a partir de: " + " + ".join(partes) + extra + "."

    def _construir_faixa_stock(self, master):
        """Faixa verde (stock suficiente) ou amarela (stock
        insuficiente). Verde se não faltar nada; amarela se algum
        produto estiver abaixo do pedido."""
        produtos_em_falta = []
        for p in self.produtos_rol:
            try:
                saldo = estoque.saldo_produto(p["produto_id"])
            except ValueError:
                saldo = 0
            if saldo < p["quantidade"]:
                produtos_em_falta.append((p, saldo))

        tem_desativados = bool(self.produtos_desativados)

        # ---- Nada a avisar: faixa verde ----
        if not produtos_em_falta and not tem_desativados:
            ctk.CTkLabel(
                master,
                text="Stock suficiente — o Rol será criado como enviada.",
                text_color=tema.TEXTO_LIVRE,
                fg_color=tema.VERDE_LIVRE,
                corner_radius=tema.RAIO_CAMPO,
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=16, pady=(0, 14))
            return

        # ---- Com avisos: faixa amarela ----
        partes = []

        if produtos_em_falta:
            itens = ", ".join(
                f"{p['nome']} (faltam "
                f"{p['quantidade'] - saldo}, {saldo} em armazém)"
                for p, saldo in produtos_em_falta
            )
            partes.append(
                f"Stock insuficiente — {itens}. O Rol será criado "
                f"como pendente e fica a aguardar reposição."
            )

        if tem_desativados:
            nomes = ", ".join(p["nome"] for p in self.produtos_desativados)
            partes.append(f"Produtos desativados ignorados: {nomes}.")

        ctk.CTkLabel(
            master,
            text=" ".join(partes),
            text_color=tema.TEXTO_AVISO,
            fg_color=tema.AMARELO_AVISO,
            corner_radius=tema.RAIO_CAMPO,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=480,
        ).pack(fill="x", padx=16, pady=(0, 14))

    # -- rodapé -------------------------------------------------------

    def _construir_rodape(self):
        """Rodapé com Cancelar/Confirmar."""
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(4, 20), side="bottom")

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
            text="Confirmar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._confirmar,
        ).pack(side="right")

    def _confirmar(self):
        """Fecha o modal e chama o `ao_confirmar` (que é o `_gravar`
        do `NovaReservaAirbnb`) com os dados que ele precisa.

        Se a Zona 1 existir (houve desconto), valida primeiro que
        um responsável foi escolhido — sem isto o `contratos.
        registar_airbnb` ia recusar mais tarde, com uma mensagem
        menos clara.
        """
        # Se há desconto, o responsável é obrigatório.
        if hasattr(self, "combo_responsavel"):
            responsavel_id = self._responsavel_escolhido_id()

            if not responsavel_id:
                componentes.mostrar_erro(
                    "Escolhe o responsável que autoriza o desconto."
                )
                return
        else:
            responsavel_id = ""

        # Guarda referências antes de fechar — o `ao_confirmar` corre
        # já depois do `destroy()`, e o `self` continua válido em
        # Python, mas é mais claro assim.
        ao_confirmar = self.ao_confirmar
        dados = {
            "data_inicio": self.data_inicio,
            "data_fim": self.data_fim,
            "preco_praticado": self.preco_praticado,
            "responsavel_desconto_preco_id": responsavel_id,
            "check_in_tardio": self.check_in_tardio,
            "hora_chegada": self.hora_chegada,
            "multa_praticada": self.multa_praticada,
        }

        self.destroy()
        ao_confirmar(**dados)
