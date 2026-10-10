"""Testes do rótulo do seletor de lugar do contrato mensal
(`gui.contratos.gui_cnt_comum.rotulo_lugar`) — 10/10/2026: passou a
mostrar o quarto e o tipo de cama. Função pura, sem base de dados.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gui.contratos import gui_cnt_comum  # noqa: E402


def _lugar(nome="Cama 1", tipo="solteiro", posicao=None):
    return {"nome": nome, "tipo_cama": tipo, "posicao_beliche": posicao}


class TesteRotuloLugar(unittest.TestCase):

    def test_quarto_cama_tipo_e_estado(self):
        self.assertEqual(
            gui_cnt_comum.rotulo_lugar(_lugar(), 0, 1, "Quarto 2"),
            "Quarto 2 · Cama 1 · Solteiro · livre (0/1)",
        )

    def test_casal_parcial(self):
        self.assertEqual(
            gui_cnt_comum.rotulo_lugar(
                _lugar("Cama de Casal", "casal"), 1, 2, "Quarto 1"
            ),
            "Quarto 1 · Cama de Casal · Casal · parcial (1/2)",
        )

    def test_beliche_com_posicao_ocupado(self):
        self.assertEqual(
            gui_cnt_comum.rotulo_lugar(
                _lugar("Cama 2", "beliche", "superior"), 1, 1, "Quarto 3"
            ),
            "Quarto 3 · Cama 2 · Beliche superior · ocupado (1/1)",
        )

    def test_sem_quarto_nem_tipo_mantem_o_formato_antigo(self):
        self.assertEqual(
            gui_cnt_comum.rotulo_lugar({"nome": "Cama 1"}, 0, 1),
            "Cama 1 · livre (0/1)",
        )


if __name__ == "__main__":
    unittest.main()
