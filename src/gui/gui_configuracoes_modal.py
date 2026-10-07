"""Modais de confirmação do ecrã de Configurações.

Este módulo tem dois modais:

  - `GerirConfiguracaoModal` (v1.11.2) — o botão "Gerir" de cada
    linha. Campo do valor, resumo antes → depois enquanto se
    escreve, e "Confirmar alteração", que grava pelo
    `configuracoes.definir`. Substituiu o `confirmar_alteracao`.

  - `confirmar_reset_sistema(...)` — aparece quando o Master clica
    em "Começar do zero". Exige confirmação dupla (escrever
    "APAGAR TUDO" + password do Master ativo). Devolve a password
    se confirmar, `None` se cancelar. NÃO executa o reset — só
    recolhe a confirmação; quem executa é o `sistema.py` (Ficheiro 6).

Os dois modais seguem o mesmo estilo dos outros da aplicação:
`CTkToplevel`, `transient` do parent, `colocar_no_topo` para
trazer à frente, cores do `tema.py`.
"""

import logging

import customtkinter as ctk

import configuracoes
import utilizadores
from . import componentes
from . import sessao
from . import tema

logger = logging.getLogger(__name__)

# =====================================================================
# MODAL 1 — GERIR UMA CONFIGURAÇÃO (v1.11.2, mockup aprovado 07/10)
# =====================================================================
#
# Substitui o `confirmar_alteracao`. Antes, cada linha do ecrã tinha
# o controlo à vista (campo + Guardar, interruptor, seletores) e um
# segundo modal pedia a confirmação. Agora a linha só mostra o valor
# e o botão "Gerir"; o modal junta o campo, o resumo "antes → depois"
# (atualizado enquanto se escreve) e a confirmação, num passo só.

_MESES = (
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
)

# Unidade mostrada a seguir aos números (linha do ecrã e resumo).
_UNIDADES = {
    "operacao.dia_vencimento": "do mês",
    "operacao.aviso_previo_dias": "dias",
    "operacao.duracao_minima_meses": "meses",
    "financeiro.multiplicador_caucao": "× renda",
    "financeiro.multiplicador_maximo_caucao": "× renda",
}

_LARGURA_GERIR = 460


def formatar_valor(chave, valor, tipo):
    """Texto de um valor de configuração para o ecrã.

    - bool → "Sim" / "Não"
    - tupla (mês, dia) → "15 de jun"
    - número → "30 dias" (com a unidade da chave, vírgula decimal)
    - texto → tal e qual
    """
    if tipo == "bool":
        return "Sim" if valor else "Não"

    if tipo == "tupla_mes_dia":
        mes, dia = valor
        return f"{dia} de {_MESES[mes - 1]}"

    if tipo in ("int", "decimal"):
        texto = str(valor).replace(".", ",")
        unidade = _UNIDADES.get(chave, "")
        return f"{texto} {unidade}".strip()

    return str(valor)


def _texto_limites(definicao):
    """"Novo valor (1 a 28)", "(número inteiro, mínimo 0)"…"""
    minimo = definicao.get("minimo")
    maximo = definicao.get("maximo")
    tipo = "número inteiro" if definicao["tipo"] == "int" else "número"

    if minimo is not None and maximo is not None:
        return f"Novo valor ({minimo} a {maximo})"
    if minimo is not None:
        return f"Novo valor ({tipo}, mínimo {minimo})"
    return f"Novo valor ({tipo})"


class GerirConfiguracaoModal(ctk.CTkToplevel):
    """Modal "Gerir" de uma linha das Configurações.

    `definicao` vem do `configuracoes.listar_definicoes`; `valor_atual`
    do `configuracoes.obter`. `ao_gravar(novo)` é chamado depois de o
    `configuracoes.definir` gravar — o ecrã atualiza a linha.

    O botão "Confirmar alteração" só fica ativo quando o valor mudou e
    é válido (a validação é a do negócio, `configuracoes.ler_numero` /
    `validar_valor`). Enter confirma; Escape cancela.
    """

    def __init__(self, pai, titulo, definicao, valor_atual, ao_gravar):
        super().__init__(pai)
        self.pai = pai
        self.chave = definicao["chave"]
        self.tipo = definicao["tipo"]
        self.definicao = definicao
        self.valor_atual = valor_atual
        self.ao_gravar = ao_gravar
        self.titulo = titulo
        self.novo = valor_atual
        self._valido = True

        self.title("Gerir configuração")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(pai)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.corpo = componentes.Contentor(self)
        self.corpo.pack(fill="both", expand=True, padx=22, pady=(18, 16))

        componentes.Rotulo(
            self.corpo, f"Gerir: {titulo}", "cartao"
        ).pack(fill="x")
        componentes.Rotulo(
            self.corpo, definicao["descricao"], "secundario",
            wraplength=_LARGURA_GERIR - 50, justify="left", height=0,
        ).pack(fill="x", pady=(2, 12))

        self._montar_controlo()

        self.rotulo_erro = componentes.Rotulo(
            self.corpo, "", "secundario", cor=tema.TEXTO_ERRO
        )
        self.rotulo_erro.pack(fill="x", pady=(4, 0))

        self.caixa_resumo = componentes.Contentor(
            self.corpo, corner_radius=tema.RAIO_CAMPO,
            fg_color=tema.LINHA_ALTERNADA,
        )
        self.caixa_resumo.pack(fill="x", pady=(8, 0))
        self.rotulo_resumo = componentes.Rotulo(
            self.caixa_resumo, "", "texto",
            wraplength=_LARGURA_GERIR - 80, justify="left", height=0,
        )
        self.rotulo_resumo.pack(fill="x", padx=12, pady=(10, 2))
        self.rotulo_nota = componentes.Rotulo(
            self.caixa_resumo, "", "secundario",
            wraplength=_LARGURA_GERIR - 80, justify="left", height=0,
        )
        self.rotulo_nota.pack(fill="x", padx=12, pady=(0, 10))

        rodape = componentes.Contentor(self.corpo)
        rodape.pack(fill="x", pady=(14, 0))
        self.botao_confirmar = componentes.Botao(
            rodape, "Confirmar alteração", self._confirmar, "primario",
            width=170, height=34,
        )
        self.botao_confirmar.pack(side="right")
        componentes.Botao(
            rodape, "Cancelar", self.destroy, width=110, height=34
        ).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _e: self._confirmar(), add="+")
        self.bind("<Escape>", lambda _e: self.destroy(), add="+")

        self._atualizar()
        self._ajustar_tamanho()
        componentes.colocar_no_topo(self)

    # -- controlo, conforme o tipo ------------------------------------

    def _montar_controlo(self):
        if self.tipo == "bool":
            componentes.Rotulo(self.corpo, "Ativo?", "secundario").pack(
                fill="x", pady=(0, 4)
            )
            self.seletor_bool = componentes.SeletorVistas(
                self.corpo, ("Sim", "Não"), self._ao_mudar_bool,
                inicial="Sim" if self.valor_atual else "Não",
            )
            self.seletor_bool.pack(anchor="w")
            return

        if self.tipo == "tupla_mes_dia":
            componentes.Rotulo(
                self.corpo, "Novo valor (mês e dia)", "secundario"
            ).pack(fill="x", pady=(0, 4))
            linha = componentes.Contentor(self.corpo)
            linha.pack(anchor="w")
            mes, dia = self.valor_atual
            self.combo_mes = componentes.Seletor(
                linha, values=list(_MESES), width=90,
                command=lambda _v: self._ao_mudar_tupla(),
            )
            self.combo_mes.set(_MESES[mes - 1])
            self.combo_mes.pack(side="left")
            self.combo_dia = componentes.Seletor(
                linha, values=[str(d) for d in range(1, 32)], width=80,
                command=lambda _v: self._ao_mudar_tupla(),
            )
            self.combo_dia.set(str(dia))
            self.combo_dia.pack(side="left", padx=(8, 0))
            return

        if self.tipo == "texto":
            componentes.Rotulo(
                self.corpo, "Nova pasta", "secundario"
            ).pack(fill="x", pady=(0, 4))
            linha = componentes.Contentor(self.corpo)
            linha.pack(fill="x")
            self.campo = componentes.CampoTexto(linha)
            self.campo.insert(0, str(self.valor_atual))
            self.campo.pack(side="left", fill="x", expand=True)
            self.campo.bind("<KeyRelease>", self._ao_escrever, add=True)
            componentes.Botao(
                linha, "Escolher", self._escolher_pasta, width=90
            ).pack(side="left", padx=(8, 0))
            return

        # int / decimal
        componentes.Rotulo(
            self.corpo, _texto_limites(self.definicao), "secundario"
        ).pack(fill="x", pady=(0, 4))
        self.campo = componentes.CampoTexto(
            self.corpo, width=120, justify="center"
        )
        self.campo.insert(0, str(self.valor_atual).replace(".", ","))
        self.campo.pack(anchor="w")
        self.campo.bind("<KeyRelease>", self._ao_escrever, add=True)
        self.after(50, self._focar_campo)

    def _focar_campo(self):
        try:
            self.campo.focus_set()
            self.campo.select_range(0, "end")
        except Exception:  # janela fechada entretanto
            pass

    # -- leitura do valor ---------------------------------------------

    def _ao_mudar_bool(self, texto):
        self.novo = texto == "Sim"
        self._valido = True
        self._atualizar()

    def _ao_mudar_tupla(self):
        novo = (
            _MESES.index(self.combo_mes.get()) + 1,
            int(self.combo_dia.get()),
        )
        self._validar(novo)
        self._atualizar()

    def _ao_escrever(self, _evento=None):
        texto = self.campo.get()
        if self.tipo == "texto":
            self._validar(texto.strip())
        else:
            try:
                self.novo = configuracoes.ler_numero(self.chave, texto)
                self._valido = True
                self.rotulo_erro.configure(text="")
            except ValueError as erro:
                self._valido = False
                self.rotulo_erro.configure(text=str(erro))
        self._atualizar()

    def _validar(self, valor):
        try:
            configuracoes.validar_valor(self.chave, valor)
        except ValueError as erro:
            self._valido = False
            self.rotulo_erro.configure(text=str(erro))
            return
        self.novo = valor
        self._valido = True
        self.rotulo_erro.configure(text="")

    def _escolher_pasta(self):
        from tkinter import filedialog

        pasta = filedialog.askdirectory(
            parent=self, title="Escolher pasta",
            initialdir=str(self.valor_atual),
        )
        if not pasta:
            return
        self.campo.delete(0, "end")
        self.campo.insert(0, pasta)
        self._ao_escrever()

    # -- resumo e confirmação -----------------------------------------

    def _mudou(self):
        return self._valido and self.novo != self.valor_atual

    def _atualizar(self):
        if self._mudou():
            antes = formatar_valor(self.chave, self.valor_atual, self.tipo)
            depois = formatar_valor(self.chave, self.novo, self.tipo)
            self.caixa_resumo.configure(fg_color=tema.AMARELO_AVISO)
            self.rotulo_resumo.configure(
                text=f"{antes}  →  {depois}", text_color=tema.TEXTO_AVISO,
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            self.rotulo_nota.configure(
                text=(
                    "Vale para os registos novos; os que já existem não "
                    "mudam. Fica registado com o seu nome."
                )
            )
            self.botao_confirmar.configure(state="normal")
        else:
            self.caixa_resumo.configure(fg_color=tema.LINHA_ALTERNADA)
            self.rotulo_resumo.configure(
                text=(
                    "Sem alterações: o valor é igual ao atual."
                    if self._valido
                    else "Corrige o valor para ver a alteração."
                ),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            )
            self.rotulo_nota.configure(text="")
            self.botao_confirmar.configure(state="disabled")

    def _confirmar(self):
        if not self._mudou():
            return

        autor = sessao.obter_responsavel_ativo()
        try:
            configuracoes.definir(self.chave, self.novo, autor)
        except ValueError as erro:
            self.rotulo_erro.configure(text=str(erro))
            return

        logger.info(
            "Configuração alterada pelo Gerir — chave=%s", self.chave
        )
        novo = self.novo
        self.destroy()
        self.ao_gravar(novo)

    def _ajustar_tamanho(self):
        """Mede o conteúdo e centra sobre a janela que abriu (regra da
        geometria dos modais: medir e converter para lógico)."""
        self.update_idletasks()
        fator = componentes.escala(self)
        altura = int(self.corpo.winfo_reqheight() / fator) + 40
        componentes.centrar_sobre(
            self, self.pai.winfo_toplevel(), _LARGURA_GERIR, altura
        )


# =====================================================================
# MODAL 2 — CONFIRMAR RESET DO SISTEMA
# =====================================================================


def confirmar_reset_sistema(pai):
    """Abre o modal de confirmação dupla do "Começar do zero".

    Exige:
      - Escrever literalmente "APAGAR TUDO" (case-sensitive).
      - A password do Master ativo.

    Devolve:
      - A PASSWORD introduzida, se as duas confirmações passarem e
        o utilizador clicar em "Começar do zero".
      - `None` em todos os outros casos (cancelar, X).

    Devolve a password, e não só True/False, porque quem executa o
    reset — o `sistema.comecar_do_zero(autor, password)` — volta a
    verificá-la (alteração de 23/09/2026: a confirmação com password
    passou a ser regra do módulo, não só deste ecrã). A verificação
    feita aqui fica só pelo conforto: com a password errada o modal
    não fecha e a pessoa tenta outra vez.

    NÃO executa o reset — só recolhe a confirmação.
    """
    resultado: dict = {"password": None}

    janela = ctk.CTkToplevel(pai)
    janela.title("Começar do zero")
    janela.resizable(False, False)
    janela.configure(fg_color=tema.COR_FUNDO)
    janela.transient(pai)
    componentes.colocar_no_topo(janela)

    def fechar(password):
        resultado["password"] = password
        janela.destroy()

    janela.protocol("WM_DELETE_WINDOW", lambda: fechar(None))

    # ---------------------------------------------------------------
    # Cabeçalho vermelho
    # ---------------------------------------------------------------
    cabecalho = ctk.CTkFrame(
        janela,
        fg_color=tema.VERMELHO_ERRO,
        corner_radius=tema.RAIO_CARTAO,
    )
    cabecalho.pack(fill="x", padx=24, pady=(20, 12))

    ctk.CTkLabel(
        cabecalho,
        text="⚠  Esta operação é IRREVERSÍVEL",
        text_color=tema.TEXTO_ERRO,
        font=ctk.CTkFont(size=15, weight="bold"),
        anchor="w",
    ).pack(fill="x", padx=16, pady=(14, 4))

    ctk.CTkLabel(
        cabecalho,
        text=(
            "Apaga TODOS os dados: propriedades, unidades, clientes, "
            "contratos, stock, despesas, configurações e utilizadores. "
            "Só ficará um utilizador Master padrão."
        ),
        text_color=tema.TEXTO_ERRO,
        font=ctk.CTkFont(size=11),
        anchor="w",
        justify="left",
        wraplength=440,
    ).pack(fill="x", padx=16, pady=(0, 4))

    ctk.CTkLabel(
        cabecalho,
        text=(
            "É criado um backup automático antes do reset, para o "
            "caso de precisares de recuperar algo."
        ),
        text_color=tema.TEXTO_ERRO,
        font=ctk.CTkFont(size=11, weight="bold"),
        anchor="w",
        justify="left",
        wraplength=440,
    ).pack(fill="x", padx=16, pady=(0, 14))

    # ---------------------------------------------------------------
    # Campo 1 — escrever "APAGAR TUDO"
    # ---------------------------------------------------------------
    ctk.CTkLabel(
        janela,
        text='Para continuar, escreve "APAGAR TUDO":',
        text_color=tema.COR_TEXTO,
        font=ctk.CTkFont(size=12),
        anchor="w",
    ).pack(fill="x", padx=24)

    campo_texto = ctk.CTkEntry(
        janela,
        corner_radius=tema.RAIO_CAMPO,
        placeholder_text="APAGAR TUDO",
    )
    campo_texto.pack(fill="x", padx=24, pady=(4, 14))

    # ---------------------------------------------------------------
    # Campo 2 — password do Master ativo
    # ---------------------------------------------------------------
    ctk.CTkLabel(
        janela,
        text="Confirma com a tua password:",
        text_color=tema.COR_TEXTO,
        font=ctk.CTkFont(size=12),
        anchor="w",
    ).pack(fill="x", padx=24)

    campo_password = ctk.CTkEntry(
        janela,
        corner_radius=tema.RAIO_CAMPO,
        show="•",
        placeholder_text="Password do Master ativo",
    )
    campo_password.pack(fill="x", padx=24, pady=(4, 14))

    # ---------------------------------------------------------------
    # Rodapé — Cancelar + Começar do zero (vermelho)
    # ---------------------------------------------------------------
    rodape = ctk.CTkFrame(janela, fg_color="transparent")
    rodape.pack(fill="x", padx=24, pady=(0, 20))

    ctk.CTkButton(
        rodape,
        text="Cancelar",
        width=130,
        height=36,
        corner_radius=tema.RAIO_BOTAO,
        fg_color="transparent",
        border_width=1,
        border_color=tema.COR_BORDA,
        text_color=tema.COR_TEXTO,
        hover_color=tema.COR_BORDA,
        command=lambda: fechar(None),
    ).pack(side="left")

    def tentar_confirmar():
        """Verifica a password UMA vez, só ao clicar.

        Antes (até 23/09/2026) a password era verificada a cada tecla,
        com o `utilizadores.autenticar`: enchia o log de falsas
        "falhas de autenticação" (uma por letra), registava um login
        que não aconteceu e atualizava o `ultimo_login` do Master.
        """
        password = campo_password.get()

        if _password_do_master_valida(password):
            fechar(password)
            return

        ativo = sessao.obter_responsavel_ativo()
        logger.warning(
            "Password errada na confirmação do reset — autor_id=%s",
            ativo["id"] if ativo else None,
        )
        componentes.mostrar_erro(
            "A password não corresponde ao utilizador ativo."
        )
        campo_password.delete(0, "end")
        campo_password.focus_set()
        validar()

    botao_confirmar = ctk.CTkButton(
        rodape,
        text="Começar do zero",
        width=170,
        height=36,
        corner_radius=tema.RAIO_BOTAO,
        fg_color=tema.TEXTO_ERRO,
        hover_color="#A02D22",
        state="disabled",
        command=tentar_confirmar,
    )
    botao_confirmar.pack(side="right")

    # ---------------------------------------------------------------
    # Validação em tempo real dos dois campos
    # ---------------------------------------------------------------
    def validar(*_args):
        # Só liga o botão. A password é verificada ao clicar, em
        # `tentar_confirmar` — nunca a cada tecla.
        texto_ok = campo_texto.get().strip() == "APAGAR TUDO"
        password_ok = bool(campo_password.get())

        if texto_ok and password_ok:
            botao_confirmar.configure(state="normal")
        else:
            botao_confirmar.configure(state="disabled")

    campo_texto.bind("<KeyRelease>", validar)
    campo_password.bind("<KeyRelease>", validar)

    # Ajusta a janela ao conteúdo e centra
    janela.update_idletasks()
    largura = 520
    altura = janela.winfo_reqheight()
    janela.geometry(f"{largura}x{altura}")

    _centrar_no_parent(janela, pai, largura, altura)

    janela.wait_window()

    return resultado["password"]


# =====================================================================
# HELPERS
# =====================================================================


def _password_do_master_valida(password):
    """Confirma se a password bate com o Master ativo.

    Usa o `utilizadores.verificar_password`, e NÃO o `autenticar`:
    isto é uma confirmação, não um login — não deve atualizar o
    `ultimo_login` nem registar acessos no log.
    """
    if not password:
        return False

    ativo = sessao.obter_responsavel_ativo()

    if ativo is None:
        return False

    return utilizadores.verificar_password(ativo["id"], password)


def _centrar_no_parent(janela, pai, largura, altura):
    """Centra um Toplevel sobre a janela que o abriu.

    Reaproveita a lógica do `componentes.centrar_sobre`, mas
    aceita uma geometria já calculada (o modal ajusta-se ao
    conteúdo, por isso a altura só é conhecida no fim).
    """
    pai.update_idletasks()
    x = pai.winfo_rootx() + (pai.winfo_width() - largura) // 2
    y = pai.winfo_rooty() + (pai.winfo_height() - altura) // 2
    janela.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")
