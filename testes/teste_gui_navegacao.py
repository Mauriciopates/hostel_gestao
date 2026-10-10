"""Testes da reação ao clique no menu (v2.3.0, mockup aprovado a
10/10/2026): "A abrir …" logo ao clicar, cliques repetidos
ignorados, pílulas do menu relidas só de tempos a tempos e a
janelinha "A calcular…" do `com_janela_carregar`. Sem base de dados:
ecrãs e contadores falsos.
"""

import sys
import time
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import customtkinter as ctk  # noqa: E402

from gui import app as modulo_app  # noqa: E402
from gui import componentes  # noqa: E402


class _EcraLento(ctk.CTkFrame):
    construidos = 0

    def __init__(self, master, controlador):
        super().__init__(master)
        _EcraLento.construidos += 1
        time.sleep(0.2)


class _EcraRapido(ctk.CTkFrame):
    def __init__(self, master, controlador):
        super().__init__(master)


class _Base(unittest.TestCase):

    def setUp(self):
        self.raiz = ctk.CTk()
        self.raiz.withdraw()
        self.contagens = 0

    def tearDown(self):
        self.raiz.destroy()

    def _contar(self):
        self.contagens += 1
        return 1

    def _esperar(self, segundos):
        fim = time.time() + segundos
        while time.time() < fim:
            self.raiz.update()
            time.sleep(0.01)


class TesteNavegar(_Base):

    def setUp(self):
        super().setUp()
        app = self.raiz
        for nome in ("navegar", "_concluir_navegacao",
                     "_libertar_navegacao", "_tirar_tela_abrir",
                     "mostrar_frame"):
            setattr(app, nome, types.MethodType(
                getattr(modulo_app.Aplicacao, nome), app))
        app.trocar_utilizador = lambda: None
        app.frame_atual = None
        app.area_conteudo = ctk.CTkFrame(app)
        app.area_conteudo.pack(fill="both", expand=True)
        app.barra_lateral = componentes.BarraLateral(app, app, [
            {"tipo": "item", "texto": "Rápido", "ecra": _EcraRapido},
            {"tipo": "item", "texto": "Lento", "ecra": _EcraLento,
             "contador": self._contar},
        ])
        _EcraLento.construidos = 0

    def test_mostra_a_abrir_logo_ao_clicar(self):
        self.raiz.navegar(_EcraLento, "Lento")
        self.assertIsInstance(self.raiz._tela_abrir, componentes.TelaAbrir)
        self._esperar(0.6)
        self.assertIsInstance(self.raiz.frame_atual, _EcraLento)
        self.assertIsNone(self.raiz._tela_abrir)

    def test_cliques_repetidos_sao_ignorados(self):
        for _ in range(3):
            self.raiz.navegar(_EcraLento, "Lento")
        self._esperar(0.8)
        self.assertEqual(_EcraLento.construidos, 1)

    def test_volta_a_aceitar_cliques_depois_de_abrir(self):
        self.raiz.navegar(_EcraLento, "Lento")
        self._esperar(0.8)
        self.raiz.navegar(_EcraRapido, "Rápido")
        self._esperar(0.3)
        self.assertIsInstance(self.raiz.frame_atual, _EcraRapido)

    def test_contadores_nao_sao_relidos_em_cada_troca(self):
        lidas = self.contagens
        self.raiz.mostrar_frame(_EcraRapido)
        self.raiz.mostrar_frame(_EcraRapido)
        self.assertEqual(self.contagens, lidas)

        self.raiz.barra_lateral._contadores_lidos_em -= 60
        self.raiz.mostrar_frame(_EcraRapido)
        self.assertEqual(self.contagens, lidas + 1)

    def test_atualizar_contadores_le_sempre(self):
        lidas = self.contagens
        self.raiz.barra_lateral.atualizar_contadores()
        self.assertEqual(self.contagens, lidas + 1)


class TesteComJanelaCarregar(_Base):

    def _camadas(self):
        return [w for w in self.raiz.winfo_children()
                if isinstance(w, componentes.CamadaCarregar)]

    def test_mostra_a_camada_durante_o_trabalho_e_tira_no_fim(self):
        self.raiz.deiconify()
        self.raiz.update()
        vistas = []

        def trabalho():
            vistas.append(len(self._camadas()))
            return 42

        resultado = componentes.com_janela_carregar(
            self.raiz, "A calcular…", trabalho
        )
        self.assertEqual(resultado, 42)
        self.assertEqual(vistas, [1])
        self.assertEqual(self._camadas(), [])

    def test_tira_a_camada_mesmo_com_erro(self):
        self.raiz.deiconify()
        self.raiz.update()

        def trabalho():
            raise ValueError("falhou")

        with self.assertRaises(ValueError):
            componentes.com_janela_carregar(
                self.raiz, "A calcular…", trabalho
            )
        self.assertEqual(self._camadas(), [])

    def test_sem_janela_visivel_so_corre_o_trabalho(self):
        resultado = componentes.com_janela_carregar(
            self.raiz, "A calcular…", lambda: "ok"
        )
        self.assertEqual(resultado, "ok")


if __name__ == "__main__":
    unittest.main()
