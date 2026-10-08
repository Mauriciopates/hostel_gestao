"""Testes da v1.12.0 — estado "Finalizada" das reservas Airbnb
(`contratos.esta_finalizada`). Cálculo puro, sem base de dados."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import contratos  # noqa: E402

HOJE = date(2026, 10, 8)


def _reserva(fim, ativo=True, tipo="airbnb"):
    return {"tipo": tipo, "ativo": ativo, "data_fim": fim}


class TesteEstaFinalizada(unittest.TestCase):

    def test_saida_ja_passou_esta_finalizada(self):
        self.assertTrue(
            contratos.esta_finalizada(_reserva(date(2026, 10, 6)), HOJE)
        )

    def test_no_dia_da_saida_ainda_esta_ativa(self):
        self.assertFalse(
            contratos.esta_finalizada(_reserva(date(2026, 10, 8)), HOJE)
        )

    def test_saida_futura_esta_ativa(self):
        self.assertFalse(
            contratos.esta_finalizada(_reserva(date(2026, 10, 9)), HOJE)
        )

    def test_cancelada_nao_e_finalizada(self):
        self.assertFalse(
            contratos.esta_finalizada(
                _reserva(date(2026, 10, 6), ativo=False), HOJE
            )
        )

    def test_contrato_mensal_nunca_e_finalizado(self):
        self.assertFalse(
            contratos.esta_finalizada(
                _reserva(date(2026, 10, 6), tipo="mensal"), HOJE
            )
        )

    def test_sem_data_de_fim_nao_e_finalizada(self):
        self.assertFalse(contratos.esta_finalizada(_reserva(None), HOJE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
