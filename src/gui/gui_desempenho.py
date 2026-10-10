"""Modo `--desempenho` — a parte que se vê (v2.2.0).

Depois do login, se a aplicação arrancou com `--desempenho`, o
`main_gui` chama `iniciar(app)`. Só um Master pode medir (decisão de
10/10/2026: o executável vai para o cliente, não pode haver uma porta
para entrar sem login). A aplicação abre sozinha cada ecrã do menu e
dos hubs, `desempenho.REPETICOES` vezes, com uma janelinha de
progresso por cima ("A medir… Calendário (2/3)") e um botão "Parar".
No fim grava o relatório na pasta de relatórios, abre o HTML e volta
ao Dashboard — a aplicação continua aberta para uso normal.

Os ecrãs que gravam na base só por abrir (`desempenho.ECRAS_QUE_GRAVAM`)
não são abertos; o relatório diz quais foram e porquê.
"""

import importlib
import logging
import time

import customtkinter as ctk

import config
import desempenho
import impressao.desempenho as relatorio
from impressao.base import abrir_no_sistema
from . import componentes, sessao, tema

logger = logging.getLogger(__name__)

# Pausa entre aberturas: deixa a janela de progresso redesenhar-se e
# o Tk tratar dos eventos pendentes, para a medição seguinte começar
# "limpa".
_PAUSA_MS = 60


def iniciar(app):
    """Ponto de entrada (chamado pelo `main_gui` depois do login)."""
    if sessao.tipo_utilizador_ativo() != "Master":
        componentes.mostrar_erro(
            "A medição de desempenho só pode ser feita por um Master.\n\n"
            "A aplicação continua aberta normalmente.",
            titulo="Medição de desempenho",
        )
        return

    ecras = _lista_de_ecras(app)
    a_medir = sum(1 for e in ecras if e["saltar"] is None)
    if not componentes.confirmar(
        f"Vai medir {a_medir} ecrãs, {desempenho.REPETICOES} vezes cada, "
        f"no servidor «{config.SERVIDOR_NOME}».\n\n"
        "A aplicação vai abrir os ecrãs sozinha durante alguns minutos. "
        "Não é preciso clicar em nada. No fim abre-se o relatório.\n\n"
        "Começar?",
        titulo="Medição de desempenho",
    ):
        return

    _Medicao(app, ecras).comecar()


def _lista_de_ecras(app):
    """[{nome, preparar, abrir, saltar}] — o que medir e como.

    `saltar` é o motivo para NÃO abrir o ecrã (grava na base), ou
    None.
    """
    from gui import app as modulo_app
    from gui.dashboard.gui_dash_hub import Dashboard

    ecras = []
    for item in modulo_app._itens_visiveis():
        if item["tipo"] != "item":
            continue
        classe = item["ecra"]
        ecras.append({
            "nome": item["texto"],
            "preparar": None,
            "abrir": (lambda c=classe: app.mostrar_frame(c)),
            "saltar": desempenho.ECRAS_QUE_GRAVAM.get(classe.__name__),
        })

    # A vista "Financeiro" do Dashboard só se constrói quando é
    # escolhida: mede-se à parte, a partir de um Dashboard aberto.
    def preparar_dashboard():
        app.mostrar_frame(Dashboard)

    def abrir_financeiro():
        dashboard = app.frame_atual
        vistas = getattr(dashboard, "vistas", {})
        if "Financeiro" in vistas:
            vistas["Financeiro"].destroy()
            del vistas["Financeiro"]
        dashboard.mostrar_vista("Financeiro")

    ecras.append({
        "nome": "Dashboard › Financeiro",
        "preparar": preparar_dashboard,
        "abrir": abrir_financeiro,
        "saltar": None,
    })

    for nome, modulo, nome_classe in desempenho.SUB_ECRAS:
        try:
            classe = getattr(importlib.import_module(modulo), nome_classe)
        except (ImportError, AttributeError) as erro:
            logger.warning("Desempenho: ecrã %s ignorado (%s)", nome, erro)
            continue
        ecras.append({
            "nome": nome,
            "preparar": None,
            "abrir": (lambda c=classe: app.mostrar_frame(c)),
            "saltar": desempenho.ECRAS_QUE_GRAVAM.get(nome_classe),
        })

    return ecras


def _contar_widgets(widget):
    total = 1
    for filho in widget.winfo_children():
        total += _contar_widgets(filho)
    return total


def medir_abertura(app, abrir):
    """Abre um ecrã uma vez e devolve as fases medidas (ms).

    Depois de `abrir()` força o layout e o desenho
    (`update_idletasks` + `update`) — é aí que o Tk trabalha de facto.
    """
    marca_inicio = desempenho.ESTADO.marca()
    inicio = time.perf_counter()
    abrir()
    fim_construcao = time.perf_counter()
    marca_construcao = desempenho.ESTADO.marca()
    app.update_idletasks()
    app.update()
    fim = time.perf_counter()

    consultas, ligacoes = desempenho.ESTADO.desde(marca_inicio)
    n_consultas = marca_construcao[0] - marca_inicio[0]
    n_ligacoes = marca_construcao[1] - marca_inicio[1]
    atual = getattr(app, "frame_atual", None)

    return desempenho.medicao(
        total=(fim - inicio) * 1000,
        construcao_bruta=(fim_construcao - inicio) * 1000,
        consultas=consultas,
        ligacoes=ligacoes,
        consultas_construcao=consultas[:n_consultas],
        ligacoes_construcao=ligacoes[:n_ligacoes],
        widgets=_contar_widgets(atual) if atual is not None else 0,
    )


class _Medicao:
    """Corre a medição passo a passo (um `after` por abertura), para a
    janela de progresso e o botão "Parar" continuarem vivos."""

    def __init__(self, app, ecras):
        self.app = app
        self.ecras = ecras
        self.linhas = []
        self.indice = 0
        self.repeticoes = []
        self.parar_pedido = False
        self.originais = {}
        self.janela = None

    # -- arranque e fim -------------------------------------------------

    def comecar(self):
        logger.info("Desempenho: medição iniciada (%s ecrãs)",
                    len(self.ecras))
        self._silenciar_popups()
        self.janela = _JanelaProgresso(self.app, self._pedir_paragem)
        self.app.after(300, self._passo)

    def _pedir_paragem(self):
        self.parar_pedido = True
        self._mostrar("A parar depois deste ecrã…", None)

    def _mostrar(self, texto, progresso):
        if self.janela is not None:
            self.janela.mostrar(texto, progresso)

    def _silenciar_popups(self):
        """Um aviso a meio (erro, sucesso, confirmar) parava a medição
        à espera de um clique: troca-os por versões que só registam."""
        for nome, valor in (("mostrar_erro", None),
                            ("mostrar_sucesso", None),
                            ("confirmar", False)):
            self.originais[nome] = getattr(componentes, nome)
            setattr(componentes, nome,
                    lambda *a, _n=nome, _v=valor, **k: self._aviso(_n, _v))

    def _aviso(self, nome, valor):
        logger.info("Desempenho: aviso ignorado durante a medição (%s)",
                    nome)
        return valor

    def _repor_popups(self):
        for nome, funcao in self.originais.items():
            setattr(componentes, nome, funcao)

    def _terminar(self):
        self._repor_popups()
        if self.janela is not None:
            self.janela.fechar()

        try:
            caminho = relatorio.gravar(
                self.linhas, config.SERVIDOR_NOME, desempenho.REPETICOES
            )
        except OSError as erro:
            componentes.mostrar_erro(
                f"Não foi possível gravar o relatório: {erro}",
                titulo="Medição de desempenho",
            )
            return

        logger.info("Desempenho: relatório em %s", caminho)
        from gui.dashboard.gui_dash_hub import Dashboard

        self.app.mostrar_frame(Dashboard)
        abrir_no_sistema(caminho)
        componentes.mostrar_sucesso(
            f"Medição concluída.\n\nRelatório:\n{caminho}",
            titulo="Medição de desempenho",
        )

    # -- ciclo -------------------------------------------------------------

    def _passo(self):
        if not self.app.winfo_exists():
            return

        if self.parar_pedido or self.indice >= len(self.ecras):
            self._terminar()
            return

        ecra = self.ecras[self.indice]

        if ecra["saltar"] is not None:
            self.linhas.append(
                desempenho.linha_saltada(ecra["nome"], ecra["saltar"])
            )
            self._seguinte()
            return

        n = len(self.repeticoes) + 1
        self._mostrar(
            f"A medir… {ecra['nome']} ({n}/{desempenho.REPETICOES})",
            self.indice / len(self.ecras),
        )

        try:
            if ecra["preparar"] is not None:
                ecra["preparar"]()
                self.app.update()
            self.repeticoes.append(medir_abertura(self.app, ecra["abrir"]))
        except Exception as erro:  # um ecrã que falha não para tudo
            logger.exception("Desempenho: %s falhou", ecra["nome"])
            self.linhas.append(desempenho.linha_com_erro(ecra["nome"], erro))
            self._seguinte()
            return

        if len(self.repeticoes) >= desempenho.REPETICOES:
            self.linhas.append(
                desempenho.juntar_repeticoes(ecra["nome"], self.repeticoes)
            )
            self._seguinte()
            return

        self.app.after(_PAUSA_MS, self._passo)

    def _seguinte(self):
        self.indice += 1
        self.repeticoes = []
        self.app.after(_PAUSA_MS, self._passo)


class _JanelaProgresso(ctk.CTkToplevel):
    """"A medir… Calendário (2/3)", barra de progresso e "Parar"."""

    def __init__(self, app, ao_parar):
        super().__init__(app)
        self.title("Medição de desempenho")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(app)
        # O X faz o mesmo que "Parar" (fecha no fim do ecrã atual).
        self.protocol("WM_DELETE_WINDOW", ao_parar)

        self.rotulo = componentes.Rotulo(self, "A preparar…", "cartao")
        self.rotulo.pack(fill="x", padx=20, pady=(18, 8))

        self.barra = componentes.BarraNivel(self, 0, largura=300)
        self.barra.pack(padx=20)

        componentes.Rotulo(
            self,
            "Não é preciso clicar em nada. No fim abre-se o relatório.",
            "secundario",
        ).pack(fill="x", padx=20, pady=(8, 0))

        self.botao = componentes.Botao(self, "Parar", ao_parar)
        self.botao.pack(anchor="e", padx=20, pady=(10, 16))

        componentes.centrar_sobre(self, app, 360, 150)
        componentes.colocar_no_topo(self)

    def mostrar(self, texto, progresso):
        if not self.winfo_exists():
            return
        self.rotulo.configure(text=texto)
        if progresso is not None:
            self.barra.set(max(0.0, min(1.0, progresso)))
        else:
            self.botao.configure(state="disabled")
        self.update_idletasks()

    def fechar(self):
        try:
            self.grab_release()
            self.destroy()
        except Exception:  # noqa: BLE001 — já pode ter sido destruída
            pass
