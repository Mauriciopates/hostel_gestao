"""Testes de configuracoes.py — leitura, escrita, permissões e histórico.

MIGRAÇÃO MySQL (Fase 2): `configuracoes.py` fala diretamente com a
base de dados através do `repositorio.py`, tal como os outros módulos
de negócio. Estes testes correm contra a base de dados de teste
dedicada (ver `apoio_BD.py`); cada teste começa com as tabelas vazias
e os contadores de identificadores reiniciados.

NOTA sobre o mapa `_CHAVES`: o módulo tem um mapa com todas as chaves
conhecidas (chave, tipo, perfil, default, descrição). Qualquer chave
fora do mapa é recusada pelo `obter` e pelo `definir`. Isto é
intencional — evita gravar chaves inventadas. Os testes cobrem os dois
lados: o que está no mapa passa, o que não está é recusado.

NOTA sobre a seed: `garantir_seed()` insere no `_CHAVES` os valores
por omissão. Como cada teste parte de uma BD vazia, a seed é
obrigatória antes de `obter` — sem ela, o `obter` cai no default do
mapa (que vem do `config.py`) e isso é válido, mas os testes que
querem verificar a ESCRITA e LEITURA na BD precisam de garantir a
seed primeiro.

NOTA sobre identidade dos autores: os testes criam autores via
`responsaveis.criar(...)` com o perfil certo para cada chave. Perfis
exigidos pelo módulo:
  - `operacao.*`     → Master ou Admin
  - `financeiro.*`   → depende da chave
      `financeiro.multiplicador_*` → só Master
      restantes                    → Master ou Admin
  - `stock.*`        → só Master
  - `sistema.*`      → só Master
  - `empresa.*`      → Master ou Admin

Os testes que verificam o "perfil errado" criam o autor do perfil
errado e verificam que o `definir` recusa com ValueError.
"""

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest

import configuracoes
import repositorio
import responsaveis


# ---------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------


def _criar_master(nome="Master de Teste"):
    return responsaveis.criar(nome, tipo_utilizador="Master")


def _criar_admin(nome="Admin de Teste"):
    return responsaveis.criar(nome, tipo_utilizador="Admin")


def _criar_staff(nome="Staff de Teste"):
    return responsaveis.criar(nome, tipo_utilizador="Staff")


def _seed_e_master():
    """Aplica a seed e devolve um Master — o par mais usado nos
    testes que só querem ler ou escrever uma chave qualquer."""
    configuracoes.garantir_seed()
    return _criar_master()


# =====================================================================
# 1. Conversão de tipos — `_para_texto` / `_do_texto`
# =====================================================================
#
# Estas duas funções são o coração do módulo: tudo o que entra ou sai
# da BD passa por elas. Um erro aqui contamina todas as leituras.
# Testam-se diretamente, porque são funções puras — não precisam de
# BD e apanham bugs antes de eles aparecerem nos testes de integração.


class TesteConversaoTipos(unittest.TestCase):
    """Conversão entre valor Python e texto na BD — funções puras,
    sem MySQL."""

    def test_para_texto_bool_true(self):
        self.assertEqual(configuracoes._para_texto(True), "true")

    def test_para_texto_bool_false(self):
        self.assertEqual(configuracoes._para_texto(False), "false")

    def test_para_texto_int(self):
        self.assertEqual(configuracoes._para_texto(5), "5")

    def test_para_texto_decimal(self):
        self.assertEqual(configuracoes._para_texto(Decimal("2.5")), "2.5")

    def test_para_texto_tupla_mes_dia(self):
        self.assertEqual(configuracoes._para_texto((7, 1)), "7,1")

    def test_para_texto_texto(self):
        self.assertEqual(configuracoes._para_texto("15:00"), "15:00")

    def test_do_texto_int(self):
        self.assertEqual(configuracoes._do_texto("5", "int"), 5)

    def test_do_texto_int_invalido_falha(self):
        with self.assertRaises(ValueError):
            configuracoes._do_texto("abc", "int")

    def test_do_texto_decimal(self):
        self.assertEqual(
            configuracoes._do_texto("2.5", "decimal"), Decimal("2.5")
        )

    def test_do_texto_decimal_invalido_falha(self):
        with self.assertRaises(ValueError):
            configuracoes._do_texto("nao_e_decimal", "decimal")

    def test_do_texto_bool_true(self):
        self.assertIs(configuracoes._do_texto("true", "bool"), True)

    def test_do_texto_bool_false(self):
        self.assertIs(configuracoes._do_texto("false", "bool"), False)

    def test_do_texto_bool_invalido_falha(self):
        with self.assertRaises(ValueError):
            configuracoes._do_texto("sim", "bool")

    def test_do_texto_tupla(self):
        self.assertEqual(
            configuracoes._do_texto("7,1", "tupla_mes_dia"), (7, 1)
        )

    def test_do_texto_tupla_com_mes_invalido_falha(self):
        with self.assertRaises(ValueError):
            configuracoes._do_texto("13,1", "tupla_mes_dia")

    def test_do_texto_tupla_com_dia_invalido_falha(self):
        with self.assertRaises(ValueError):
            configuracoes._do_texto("7,32", "tupla_mes_dia")

    def test_do_texto_tupla_com_formato_errado_falha(self):
        with self.assertRaises(ValueError):
            configuracoes._do_texto("sem_virgula", "tupla_mes_dia")

    def test_do_texto_none_falha(self):
        with self.assertRaises(ValueError):
            configuracoes._do_texto(None, "int")

    def test_do_texto_texto_simples(self):
        self.assertEqual(configuracoes._do_texto("15:00", "texto"), "15:00")


# =====================================================================
# 2. Obter e definir — integração com a BD
# =====================================================================


class TesteObter(BaseMySQLTest):
    """Leitura de configurações com e sem seed."""

    def test_obter_devolve_default_quando_nao_esta_na_bd(self):
        """Sem seed, o `obter` cai no default do mapa `_CHAVES` (que
        veio do `config.py`). É o comportamento correto: uma chave
        que ainda não foi tocada tem de devolver o valor inicial do
        sistema, não rebentar.
        """
        valor = configuracoes.obter("operacao.dia_vencimento")

        self.assertEqual(valor, 5)  # config.DIA_VENCIMENTO

    def test_obter_apos_seed_devolve_o_mesmo_default(self):
        configuracoes.garantir_seed()

        valor = configuracoes.obter("operacao.dia_vencimento")

        self.assertEqual(valor, 5)

    def test_obter_chave_desconhecida_falha(self):
        """Uma chave fora do mapa é recusada — evita devolver None
        silenciosamente."""
        with self.assertRaises(ValueError):
            configuracoes.obter("inventado.chave")

    def test_obter_int_devolve_int(self):
        configuracoes.garantir_seed()
        valor = configuracoes.obter_int("operacao.dia_vencimento")

        self.assertIsInstance(valor, int)

    def test_obter_decimal_devolve_decimal(self):
        configuracoes.garantir_seed()
        valor = configuracoes.obter_decimal(
            "financeiro.multiplicador_caucao"
        )

        self.assertIsInstance(valor, Decimal)

    def test_obter_bool_devolve_bool(self):
        configuracoes.garantir_seed()
        valor = configuracoes.obter_bool("stock.permitir_envio_parcial")

        self.assertIsInstance(valor, bool)

    def test_obter_tupla_devolve_tupla(self):
        configuracoes.garantir_seed()
        valor = configuracoes.obter_tupla("financeiro.epoca_alta_inicio")

        self.assertIsInstance(valor, tuple)
        self.assertEqual(valor, (7, 1))

    def test_obter_aceita_default_explicito(self):
        """Quando o chamador passa `default`, ele é usado se a chave
        não estiver na BD — antes do fallback do mapa."""
        valor = configuracoes.obter("operacao.dia_vencimento", default=99)

        self.assertEqual(valor, 99)


class TesteDefinir(BaseMySQLTest):
    """Escrita de configurações — gravação + histórico."""

    def test_definir_altera_valor_e_le_de_volta(self):
        master = _seed_e_master()

        configuracoes.definir(
            "operacao.dia_vencimento", 10, autor=master
        )

        self.assertEqual(
            configuracoes.obter("operacao.dia_vencimento"), 10
        )

    def test_definir_guarda_no_historico(self):
        master = _seed_e_master()

        configuracoes.definir(
            "operacao.dia_vencimento", 10, autor=master, motivo="teste"
        )

        historico = configuracoes.listar_historico(
            "operacao.dia_vencimento"
        )

        self.assertEqual(len(historico), 1)
        self.assertEqual(historico[0]["valor_anterior"], "5")
        self.assertEqual(historico[0]["valor_novo"], "10")
        self.assertEqual(historico[0]["responsavel_id"], master["id"])
        self.assertEqual(historico[0]["motivo"], "teste")

    def test_definir_guarda_historico_com_motivo_vazio(self):
        """Um motivo em branco fica gravado como string vazia na
        leitura — não como None.

        A escrita passa `""` por `motivo or None`, por isso a coluna
        fica NULL na BD (é nullable por desenho). A leitura, via
        `repositorio._normalizar_configuracao_historico`, repõe o
        `""` antes de devolver. É a convenção de string vazia usada
        em todo o sistema.

        CORREÇÃO 22/09/2026 (PASSO 9): antes desta data, o
        `listar_configuracao_historico` não normalizava nada, e o
        `motivo` vazio chegava ao consumidor como `None`. Foi o
        último sítio do projeto onde a convenção "NULL vira string
        vazia" ainda não estava aplicada.
        """
        master = _seed_e_master()

        configuracoes.definir(
            "operacao.dia_vencimento", 10, autor=master
        )

        historico = configuracoes.listar_historico(
            "operacao.dia_vencimento"
        )

        self.assertEqual(historico[0]["motivo"], "")

    def test_definir_duas_vezes_gera_dois_registos_historico(self):
        master = _seed_e_master()

        configuracoes.definir("operacao.dia_vencimento", 10, autor=master)
        configuracoes.definir("operacao.dia_vencimento", 20, autor=master)

        historico = configuracoes.listar_historico(
            "operacao.dia_vencimento"
        )

        self.assertEqual(len(historico), 2)
        # O mais recente primeiro.
        self.assertEqual(historico[0]["valor_anterior"], "10")
        self.assertEqual(historico[0]["valor_novo"], "20")

    def test_definir_chave_desconhecida_falha(self):
        master = _seed_e_master()

        with self.assertRaises(ValueError):
            configuracoes.definir("inventado.chave", 1, autor=master)

    def test_definir_autor_none_falha(self):
        with self.assertRaises(ValueError):
            configuracoes.definir(
                "operacao.dia_vencimento", 10, autor=None
            )

    def test_definir_bool_true(self):
        master = _seed_e_master()

        configuracoes.definir(
            "stock.permitir_envio_parcial", False, autor=master
        )

        self.assertFalse(
            configuracoes.obter_bool("stock.permitir_envio_parcial")
        )

    def test_definir_tupla(self):
        master = _seed_e_master()

        configuracoes.definir(
            "financeiro.epoca_alta_inicio", (6, 15), autor=master
        )

        self.assertEqual(
            configuracoes.obter_tupla("financeiro.epoca_alta_inicio"),
            (6, 15),
        )

    def test_definir_decimal(self):
        master = _seed_e_master()

        configuracoes.definir(
            "financeiro.multiplicador_caucao",
            Decimal("1.5"),
            autor=master,
        )

        self.assertEqual(
            configuracoes.obter_decimal("financeiro.multiplicador_caucao"),
            Decimal("1.5"),
        )

    def test_definir_texto(self):
        master = _seed_e_master()

        configuracoes.definir(
            "empresa.pasta_relatorios", "/tmp/relatorios", autor=master
        )

        self.assertEqual(
            configuracoes.obter("empresa.pasta_relatorios"),
            "/tmp/relatorios",
        )


# =====================================================================
# 3. Permissões
# =====================================================================


class TestePermissoes(BaseMySQLTest):
    """Regras de perfil por prefixo de chave.

    As chaves `stock.*`, `sistema.*` e `financeiro.multiplicador_*`
    são só para Master. `operacao.*`, `empresa.*` e o resto de
    `financeiro.*` são Master + Admin.
    """

    def setUp(self):
        super().setUp()
        configuracoes.garantir_seed()

    # -- chaves Master+Admin ------------------------------------------

    def test_master_altera_chave_operacao(self):
        master = _criar_master()
        configuracoes.definir("operacao.dia_vencimento", 10, autor=master)

    def test_admin_altera_chave_operacao(self):
        admin = _criar_admin()
        configuracoes.definir("operacao.dia_vencimento", 10, autor=admin)

    def test_staff_nao_altera_chave_operacao(self):
        staff = _criar_staff()
        with self.assertRaises(ValueError):
            configuracoes.definir(
                "operacao.dia_vencimento", 10, autor=staff
            )

    # -- chaves só Master ---------------------------------------------

    def test_master_altera_chave_stock(self):
        master = _criar_master()
        configuracoes.definir(
            "stock.permitir_envio_parcial", False, autor=master
        )

    def test_admin_nao_altera_chave_stock(self):
        admin = _criar_admin()
        with self.assertRaises(ValueError):
            configuracoes.definir(
                "stock.permitir_envio_parcial", False, autor=admin
            )

    def test_staff_nao_altera_chave_stock(self):
        staff = _criar_staff()
        with self.assertRaises(ValueError):
            configuracoes.definir(
                "stock.permitir_envio_parcial", False, autor=staff
            )

    def test_master_altera_chave_multiplicador_caucao(self):
        master = _criar_master()
        configuracoes.definir(
            "financeiro.multiplicador_caucao",
            Decimal("1.5"),
            autor=master,
        )

    def test_admin_nao_altera_chave_multiplicador_caucao(self):
        admin = _criar_admin()
        with self.assertRaises(ValueError):
            configuracoes.definir(
                "financeiro.multiplicador_caucao",
                Decimal("1.5"),
                autor=admin,
            )

    def test_admin_nao_altera_chave_multiplicador_maximo_caucao(self):
        admin = _criar_admin()
        with self.assertRaises(ValueError):
            configuracoes.definir(
                "financeiro.multiplicador_maximo_caucao",
                Decimal("3"),
                autor=admin,
            )

    # -- chaves operacao e financeiro restantes -----------------------

    def test_admin_altera_chave_epoca_alta(self):
        admin = _criar_admin()
        configuracoes.definir(
            "financeiro.epoca_alta_inicio", (6, 1), autor=admin
        )

    def test_admin_altera_pasta_relatorios(self):
        admin = _criar_admin()
        configuracoes.definir(
            "empresa.pasta_relatorios", "/tmp/x", autor=admin
        )

    # -- pode_alterar -------------------------------------------------

    def test_pode_alterar_master_true(self):
        master = _criar_master()
        self.assertTrue(
            configuracoes.pode_alterar(
                "stock.permitir_envio_parcial", master
            )
        )

    def test_pode_alterar_admin_chave_master_false(self):
        admin = _criar_admin()
        self.assertFalse(
            configuracoes.pode_alterar(
                "stock.permitir_envio_parcial", admin
            )
        )

    def test_pode_alterar_admin_chave_operacao_true(self):
        admin = _criar_admin()
        self.assertTrue(
            configuracoes.pode_alterar("operacao.dia_vencimento", admin)
        )

    def test_pode_alterar_staff_false(self):
        staff = _criar_staff()
        self.assertFalse(
            configuracoes.pode_alterar("operacao.dia_vencimento", staff)
        )

    def test_pode_alterar_autor_none_false(self):
        self.assertFalse(
            configuracoes.pode_alterar(
                "operacao.dia_vencimento", None
            )
        )

    def test_pode_alterar_chave_desconhecida_false(self):
        master = _criar_master()
        self.assertFalse(
            configuracoes.pode_alterar("inventado.chave", master)
        )


# =====================================================================
# 4. Seed
# =====================================================================


class TesteGarantirSeed(BaseMySQLTest):
    """Seed inicial — cria as chaves que faltam, idempotente."""

    def test_seed_cria_todas_as_chaves(self):
        criadas = configuracoes.garantir_seed()

        self.assertEqual(criadas, len(configuracoes._CHAVES))

    def test_seed_idempotente(self):
        configuracoes.garantir_seed()
        criadas_na_segunda = configuracoes.garantir_seed()

        self.assertEqual(criadas_na_segunda, 0)

    def test_seed_nao_sobrescreve_valores_alterados(self):
        master = _criar_master()
        configuracoes.garantir_seed()
        configuracoes.definir(
            "operacao.dia_vencimento", 10, autor=master
        )

        configuracoes.garantir_seed()

        self.assertEqual(
            configuracoes.obter("operacao.dia_vencimento"), 10
        )


# =====================================================================
# 5. Listagens e metadados
# =====================================================================


class TesteListar(BaseMySQLTest):
    """`listar_por_prefixo`, `listar_definicoes`, `listar_historico`."""

    def test_listar_por_prefixo_operacao(self):
        configuracoes.garantir_seed()

        resultado = configuracoes.listar_por_prefixo("operacao.")

        # Há 3 chaves operacao.* no mapa.
        self.assertEqual(len(resultado), 3)
        self.assertIn("operacao.dia_vencimento", resultado)
        self.assertIn("operacao.aviso_previo_dias", resultado)
        self.assertIn("operacao.duracao_minima_meses", resultado)

    def test_listar_por_prefixo_devolve_defaults_sem_seed(self):
        """Sem seed, o `listar_por_prefixo` cai nos defaults do
        mapa — devolve os mesmos valores que a seed gravaria.
        """
        resultado = configuracoes.listar_por_prefixo("operacao.")

        self.assertEqual(resultado["operacao.dia_vencimento"], 5)

    def test_listar_por_prefixo_com_valor_alterado(self):
        master = _seed_e_master()
        configuracoes.definir(
            "operacao.dia_vencimento", 10, autor=master
        )

        resultado = configuracoes.listar_por_prefixo("operacao.")

        self.assertEqual(resultado["operacao.dia_vencimento"], 10)

    def test_listar_por_prefixo_sem_resultados(self):
        resultado = configuracoes.listar_por_prefixo("inexistente.")

        self.assertEqual(resultado, {})

    def test_listar_definicoes_traz_todas(self):
        definicoes = configuracoes.listar_definicoes()

        self.assertEqual(len(definicoes), len(configuracoes._CHAVES))

    def test_listar_definicoes_filtra_por_prefixo(self):
        definicoes = configuracoes.listar_definicoes("operacao.")

        self.assertEqual(len(definicoes), 3)
        for d in definicoes:
            self.assertTrue(d["chave"].startswith("operacao."))

    def test_listar_definicoes_tem_os_campos_esperados(self):
        definicoes = configuracoes.listar_definicoes("operacao.")

        primeira = definicoes[0]
        for campo in ("chave", "tipo", "perfil", "default", "descricao"):
            self.assertIn(campo, primeira)

    def test_listar_historico_sem_registos(self):
        configuracoes.garantir_seed()
        resultado = configuracoes.listar_historico()

        self.assertEqual(resultado, [])

    def test_listar_historico_ordena_mais_recente_primeiro(self):
        master = _seed_e_master()
        configuracoes.definir("operacao.dia_vencimento", 10, autor=master)
        configuracoes.definir("operacao.dia_vencimento", 20, autor=master)

        historico = configuracoes.listar_historico()

        self.assertEqual(len(historico), 2)
        # O mais recente é o que tem valor_novo=20.
        self.assertEqual(historico[0]["valor_novo"], "20")
        self.assertEqual(historico[1]["valor_novo"], "10")

    def test_listar_historico_filtra_por_chave(self):
        master = _seed_e_master()
        configuracoes.definir("operacao.dia_vencimento", 10, autor=master)
        configuracoes.definir(
            "operacao.aviso_previo_dias", 20, autor=master
        )

        historico = configuracoes.listar_historico(
            "operacao.dia_vencimento"
        )

        self.assertEqual(len(historico), 1)
        self.assertEqual(historico[0]["chave"], "operacao.dia_vencimento")


if __name__ == "__main__":
    unittest.main(verbosity=2)