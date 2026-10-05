"""Janela de arranque — "o Hostel Gestão está a abrir" (v1.10.0).

PORQUÊ: no teste do Sin-Windows11 de 05/10/2026 o arranque demorou
vários segundos sem mostrar nada (túnel SSH até à VM e, no primeiro
arranque do dia, a cópia de segurança pelo túnel). Quem não vê nada
volta a clicar no ícone. A cópia única (v1.8.1, `instancia.py`) já
impedia a segunda cópia de arrancar; faltava mostrar que a primeira
estava a trabalhar. Mockup aprovado pelo aluno a 05/10/2026.

COMO: a janela aparece logo a seguir ao trinco de cópia única, antes
de qualquer ligação. O `main_gui` corre cada passo do arranque com
`correr(...)`: o trabalho vai para uma thread e a janela continua
viva (barra a correr, segundos a contar) até ele acabar. Os widgets
só são tocados na thread principal — o Tk não aceita outra.

A janela não tem botão de fechar: cancelar a meio da cópia de
segurança ou das migrações deixava a base a meio do caminho. Quem a
fecha é o `main_gui`, antes de qualquer popup (erro, Master criado)
e antes de criar a `Aplicacao` — o CustomTkinter só aguenta uma
janela-raiz de cada vez.
"""

import threading
import time
import tkinter

import customtkinter as ctk

import config
from . import componentes
from . import tema

# O título serve também para a segunda cópia encontrar esta janela e
# a trazer para a frente (`instancia.trazer_para_frente`).
TITULO = "Hostel Gestão — a iniciar"

PASSOS = (
    "A preparar",
    "A ligar ao servidor",
    "Cópia de segurança do dia",
    "A atualizar a base de dados",
    "A abrir o início de sessão",
)
PREPARAR, LIGAR, COPIA, MIGRAR, ABRIR = range(len(PASSOS))

# A cópia de segurança só demora no primeiro arranque do dia (nos
# outros a cópia já existe e o passo é imediato). O aviso amarelo só
# aparece se o passo passar deste tempo.
AVISO_COPIA_APOS_S = 2.0
AVISO_COPIA = (
    "O primeiro arranque do dia guarda uma cópia da base de dados e "
    "pode demorar até um minuto."
)

_INTERVALO_S = 0.05  # de quanto em quanto tempo a janela é redesenhada
_LARGURA = 400
_ALTURA = 372

# Marcas de cada passo: (símbolo, cor do símbolo, cor do texto)
_PENDENTE = ("○", tema.COR_TEXTO_SIDEBAR_SECAO, tema.COR_TEXTO_SECUNDARIO)
_ATUAL = ("●", tema.AZUL_PRINCIPAL, tema.COR_TEXTO)
_FEITO = ("✓", tema.VERDE, tema.COR_TEXTO)


def texto_tempo(segundos):
    """Segundos inteiros para o ecrã: 3.7 -> "3 s"."""
    return f"{max(0, int(segundos))} s"


def mostrar_aviso_copia(indice, segundos):
    """O aviso amarelo só aparece na cópia de segurança, e só quando
    ela já demora (= primeiro arranque do dia)."""
    return indice == COPIA and segundos >= AVISO_COPIA_APOS_S


class JanelaArranque(ctk.CTk):
    """Janela-raiz do arranque, antes do login.

    `ja_feitos` marca os primeiros passos como feitos — usado quando
    a janela reabre depois do plano B da ligação (o servidor estava
    em baixo e o utilizador carregou "Tentar de novo").
    """

    def __init__(self, ja_feitos=0):
        super().__init__()
        self.title(TITULO)
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        # Sem fechar: cancelar a meio deixava a base a meio do caminho.
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self._linhas = []
        self._aviso = None
        self._fonte = {
            False: ctk.CTkFont(size=12),
            True: ctk.CTkFont(size=12, weight="bold"),
        }
        self._desenhar()
        for indice in range(ja_feitos):
            self._marcar(indice, _FEITO)

        componentes.centrar_no_ecra(self, _LARGURA, _ALTURA)
        self.lift()
        self.focus_force()
        self.update()

    # -- desenho -------------------------------------------------------

    def _desenhar(self):
        topo = componentes.Contentor(self, fg_color=tema.NAVY_ESCURO)
        topo.pack(fill="x")
        componentes.Rotulo(
            topo, "HOSTEL CLEAN", estilo="secao",
            cor=tema.COR_TEXTO_SIDEBAR_SECAO,
        ).pack(fill="x", padx=24, pady=(20, 0))
        componentes.Rotulo(
            topo, "Hostel Gestão", estilo="titulo",
            cor=tema.COR_TEXTO_SIDEBAR,
        ).pack(fill="x", padx=24)
        componentes.Rotulo(
            topo, f"versão {config.VERSAO}", estilo="secundario",
            cor=tema.COR_TEXTO_SIDEBAR_SECAO,
        ).pack(fill="x", padx=24, pady=(0, 16))

        corpo = componentes.Contentor(self)
        corpo.pack(fill="both", expand=True, padx=24, pady=(14, 18))

        componentes.Etiqueta(
            corpo, f"● {config.SERVIDOR_NOME}", estilo="azul"
        ).pack(anchor="w", pady=(0, 10))

        for texto in PASSOS:
            linha = componentes.Contentor(corpo)
            linha.pack(fill="x", pady=1)
            marca = componentes.Rotulo(linha, _PENDENTE[0], estilo="forte",
                                       cor=_PENDENTE[1], width=22)
            marca.pack(side="left")
            nome = componentes.Rotulo(linha, texto, estilo="texto",
                                      cor=_PENDENTE[2])
            nome.pack(side="left", padx=(6, 0))
            tempo = componentes.Rotulo(linha, "", estilo="secundario",
                                       anchor="e")
            tempo.pack(side="right")
            self._linhas.append((marca, nome, tempo))

        self._barra = componentes.BarraCorrer(corpo)
        self._barra.pack(fill="x", pady=(12, 0))
        self._barra.start()

        self._rodape = componentes.Contentor(corpo)
        self._rodape.pack(fill="x", pady=(10, 0))
        componentes.Rotulo(
            self._rodape, "Aguarde, não é preciso clicar de novo.",
            estilo="secundario",
        ).pack(fill="x")

    def _marcar(self, indice, estado, segundos=None):
        simbolo, cor_marca, cor_texto = estado
        marca, nome, tempo = self._linhas[indice]
        marca.configure(text=simbolo, text_color=cor_marca)
        nome.configure(text_color=cor_texto,
                       font=self._fonte[estado is _ATUAL])
        if segundos is not None:
            tempo.configure(text=texto_tempo(segundos))

    def _mostrar_aviso(self):
        if self._aviso is not None:
            return
        self._aviso = componentes.Rotulo(
            self._rodape, AVISO_COPIA, estilo="texto",
            cor=tema.TEXTO_AVISO, fg_color=tema.AMARELO_AVISO,
            corner_radius=8, wraplength=320, justify="left", height=44,
        )
        self._aviso.pack(fill="x", pady=(8, 0))

    # -- passos --------------------------------------------------------

    def correr(self, indice, trabalho):
        """Corre `trabalho()` numa thread com o passo `indice` marcado
        como atual, mantendo a janela viva. Devolve o resultado; se o
        trabalho levantar uma exceção, ela é lançada de novo aqui, na
        thread principal (quem chama decide o que mostrar).

        `trabalho` não pode criar nem tocar em widgets.
        """
        self._marcar(indice, _ATUAL, 0)
        inicio = time.monotonic()
        resultado = {}

        def alvo():
            try:
                resultado["valor"] = trabalho()
            except BaseException as erro:  # entregue à thread principal
                resultado["erro"] = erro

        fio = threading.Thread(target=alvo, daemon=True)
        fio.start()
        tempo = self._linhas[indice][2]
        while fio.is_alive():
            decorrido = time.monotonic() - inicio
            tempo.configure(text=texto_tempo(decorrido))
            if mostrar_aviso_copia(indice, decorrido):
                self._mostrar_aviso()
            self.update()
            fio.join(_INTERVALO_S)

        self._marcar(indice, _FEITO, time.monotonic() - inicio)
        self.update()

        if "erro" in resultado:
            raise resultado["erro"]
        return resultado.get("valor")

    def correr_aqui(self, indice, trabalho):
        """Como `correr`, mas na thread principal — para o que não
        pode ir para outra thread (importar os ecrãs, que tocam no
        Tk). A barra fica parada enquanto corre."""
        self._marcar(indice, _ATUAL, 0)
        self.update()
        inicio = time.monotonic()
        valor = trabalho()
        self._marcar(indice, _FEITO, time.monotonic() - inicio)
        self.update()
        return valor

    def fechar(self):
        """Fecha a janela. Cancela antes os `after` que o CustomTkinter
        deixa agendados (barra, escala do ecrã): sem isto, ao fechar uma
        janela-raiz fora do `mainloop`, aparecem erros "invalid command
        name" na consola. Fechar duas vezes não faz mal."""
        try:
            self._barra.stop()
            for pendente in self.tk.call("after", "info"):
                self.after_cancel(pendente)
            self.destroy()
        except tkinter.TclError:
            pass
