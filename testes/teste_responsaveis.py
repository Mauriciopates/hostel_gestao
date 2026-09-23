"""Testes da gestão de responsáveis.

MIGRAÇÃO MySQL (Fase 2): `responsaveis.py` já não recebe nem devolve
`dados` — fala diretamente com a base de dados. Estes testes correm
contra a base de dados de teste dedicada (ver `apoio_bd.py`); cada
teste começa com a tabela vazia e os contadores reiniciados.

NOTA sobre identidade: `procurar()` faz sempre um SELECT novo — já
não devolve o MESMO objeto Python que `criar()` devolveu. Por isso
comparamos com `assertEqual`, nunca com `assertIs`, e "está na base
de dados" verifica-se com `assertIn(id, [r["id"] for r in listar()])`
em vez de `assertIn(r, dados["responsaveis"])`.

NOTA sobre chaves dos dicionários (v1.6.0): `criar()` devolve o
dicionário que construiu (id, nome, contacto, ativo, tipo_utilizador);
`procurar()`/`listar()` devolvem o que está gravado no MySQL, com
`SELECT *` — trazem também `username`, `password_hash`,
`password_alterada_em`, `ultimo_login`, `desativado_por_id` e
`data_desativacao`. Comparar o dicionário devolvido por `criar()` com
o devolvido por `procurar()` por igualdade literal NÃO funciona: os
testes comparam por ID (ou pelo campo específico que estão a
verificar), nunca o dicionário todo — mesma convenção já aplicada em
teste_unidades.py, teste_clientes.py e teste_contratos.py.

NOTA sobre `responsaveis.desativar`/`reativar` (v1.5.0): ambos exigem
`autor` — o dict do responsável ativo que executa a operação.
`desativar` é só Master, e recusa a auto-desativação
(`utilizadores.desativar`); `reativar` é Master ou Admin (Admin só
sobre Staff). Por isso cada teste que desativa/reativa cria o seu
próprio `_criar_master()` ALÉM do responsável visado — o autor tem de
ser outra pessoa. Os testes que só verificam o comportamento do
`validar_autoria` sobre um inativo também precisam do Master, para o
passo de desativar chegar ao fim.

NOTA sobre a asserção de `TesteListar.teste_lista_so_ativos_por_omissao`:
o Master criado como autor fica ativo e aparece em `listar()`. A
asserção filtra por não-Master, para continuar a verificar exatamente
o que o teste original verificava (que o responsável desativado
desaparece da listagem), sem depender do número de Masters que cada
teste cria como fixture.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest

import responsaveis


def _criar_master(nome="Master de Teste"):
    """Cria um Master, para servir de `autor` nas chamadas a
    `responsaveis.desativar`/`reativar` — desde a v1.5.0, ambos exigem
    autor, e só um Master desativa (utilizadores.desativar)."""
    return responsaveis.criar(nome, tipo_utilizador="Master")


class TesteCriar(BaseMySQLTest):

    def teste_cria_responsavel_valido(self):
        r = responsaveis.criar("Ana Ferreira", "912345678")

        self.assertEqual("Ana Ferreira", r["nome"])
        self.assertEqual("912345678", r["contacto"])
        self.assertTrue(r["ativo"])

    def teste_id_com_prefixo_res(self):
        r = responsaveis.criar("Ana Ferreira")

        self.assertTrue(r["id"].startswith("RES-"))

    def teste_contacto_omisso_fica_vazio(self):
        r = responsaveis.criar("Ana Ferreira")

        self.assertEqual("", r["contacto"])

    def teste_limpa_espacos_do_nome_e_contacto(self):
        r = responsaveis.criar("  Ana Ferreira  ", "  912345678  ")

        self.assertEqual("Ana Ferreira", r["nome"])
        self.assertEqual("912345678", r["contacto"])

    def teste_recusa_nome_vazio(self):
        for nome in ("", "   "):
            with self.assertRaises(ValueError):
                responsaveis.criar(nome)

    def teste_fica_registado_na_base_de_dados(self):
        r = responsaveis.criar("Ana Ferreira")

        ids = [x["id"] for x in responsaveis.listar()]
        self.assertIn(r["id"], ids)


class TesteProcurar(BaseMySQLTest):

    def teste_encontra_responsavel_existente(self):
        """Comparação por ID — `criar()` devolve só as chaves que
        construiu; `procurar()` traz também as de credencial
        (`username`, `password_hash`, ..., `data_desativacao`).
        O que interessa é que é a MESMA linha na base de dados.
        """
        criado = responsaveis.criar("Ana Ferreira")

        encontrado = responsaveis.procurar(criado["id"])

        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado["id"], criado["id"])  # type: ignore

    def teste_devolve_none_para_id_inexistente(self):
        self.assertIsNone(responsaveis.procurar("RES-999"))

    def teste_encontra_responsavel_inativo(self):
        criado = responsaveis.criar("Ana Ferreira")
        responsaveis.desativar(criado["id"], autor=_criar_master())

        self.assertIsNotNone(responsaveis.procurar(criado["id"]))


class TesteListar(BaseMySQLTest):

    def teste_lista_vazia_sem_responsaveis(self):
        self.assertEqual([], responsaveis.listar())

    def teste_lista_so_ativos_por_omissao(self):
        """O Master usado como autor fica ativo e aparece na
        listagem — a asserção filtra por não-Master, para continuar
        a verificar só o que o teste original verificava: que o
        responsável desativado desaparece da listagem."""
        master = _criar_master()
        ativo = responsaveis.criar("Ana Ferreira")
        inativo = responsaveis.criar("Bruno Alves")
        responsaveis.desativar(inativo["id"], autor=master)

        resultado = responsaveis.listar()

        ids_nao_master = [
            r["id"] for r in resultado if r["tipo_utilizador"] != "Master"
        ]
        self.assertEqual(ids_nao_master, [ativo["id"]])

    def teste_lista_incluir_inativos(self):
        master = _criar_master()
        ativo = responsaveis.criar("Ana Ferreira")
        inativo = responsaveis.criar("Bruno Alves")
        responsaveis.desativar(inativo["id"], autor=master)

        resultado = responsaveis.listar(incluir_inativos=True)

        ids = [r["id"] for r in resultado]
        self.assertIn(ativo["id"], ids)
        self.assertIn(inativo["id"], ids)

    def teste_devolve_lista_nova(self):
        responsaveis.criar("Ana Ferreira")

        resultado = responsaveis.listar()
        resultado.append("intruso")

        self.assertEqual(1, len(responsaveis.listar()))


class TesteAtualizar(BaseMySQLTest):

    def teste_recusa_id_inexistente(self):
        with self.assertRaises(ValueError):
            responsaveis.atualizar("RES-999", nome="Teste")

    def teste_none_nao_altera(self):
        r = responsaveis.criar("Ana Ferreira", "912345678")

        atualizado = responsaveis.atualizar(r["id"])

        self.assertEqual("Ana Ferreira", atualizado["nome"])
        self.assertEqual("912345678", atualizado["contacto"])

    def teste_altera_nome(self):
        r = responsaveis.criar("Ana Ferreira")

        atualizado = responsaveis.atualizar(r["id"], nome="Ana Sofia Ferreira")

        self.assertEqual("Ana Sofia Ferreira", atualizado["nome"])

    def teste_altera_contacto(self):
        r = responsaveis.criar("Ana Ferreira", "912345678")

        atualizado = responsaveis.atualizar(r["id"], contacto="913456789")

        self.assertEqual("913456789", atualizado["contacto"])

    def teste_limpa_contacto_com_vazio(self):
        r = responsaveis.criar("Ana Ferreira", "912345678")

        atualizado = responsaveis.atualizar(r["id"], contacto="")

        self.assertEqual("", atualizado["contacto"])

    def teste_recusa_apagar_nome(self):
        r = responsaveis.criar("Ana Ferreira")

        with self.assertRaises(ValueError):
            responsaveis.atualizar(r["id"], nome="")

    def teste_limpa_espacos(self):
        r = responsaveis.criar("Ana Ferreira")

        atualizado = responsaveis.atualizar(r["id"], nome="  Ana Sofia  ")

        self.assertEqual("Ana Sofia", atualizado["nome"])

    def teste_nao_altera_ativo(self):
        """atualizar() não mexe em 'ativo' — só desativar/reativar."""
        r = responsaveis.criar("Ana Ferreira")

        atualizado = responsaveis.atualizar(r["id"], nome="Ana Sofia")

        self.assertTrue(atualizado["ativo"])


class TesteDesativar(BaseMySQLTest):

    def teste_desativa_responsavel_ativo(self):
        """O autor é outro Master — `utilizadores.desativar` recusa
        auto-desativação ("Não pode desativar-se a si mesmo")."""
        master = _criar_master()
        r = responsaveis.criar("Ana Ferreira")

        desativado = responsaveis.desativar(r["id"], autor=master)

        self.assertFalse(desativado["ativo"])

    def teste_recusa_desativar_duas_vezes(self):
        master = _criar_master()
        r = responsaveis.criar("Ana Ferreira")
        responsaveis.desativar(r["id"], autor=master)

        with self.assertRaises(ValueError):
            responsaveis.desativar(r["id"], autor=master)

    def teste_recusa_desativar_inexistente(self):
        master = _criar_master()

        with self.assertRaises(ValueError):
            responsaveis.desativar("RES-999", autor=master)


class TesteReativar(BaseMySQLTest):

    def teste_reativa_responsavel_inativo(self):
        master = _criar_master()
        r = responsaveis.criar("Ana Ferreira")
        responsaveis.desativar(r["id"], autor=master)

        reativado = responsaveis.reativar(r["id"], autor=master)

        self.assertTrue(reativado["ativo"])

    def teste_recusa_reativar_ja_ativo(self):
        master = _criar_master()
        r = responsaveis.criar("Ana Ferreira")

        with self.assertRaises(ValueError):
            responsaveis.reativar(r["id"], autor=master)

    def teste_recusa_reativar_inexistente(self):
        master = _criar_master()

        with self.assertRaises(ValueError):
            responsaveis.reativar("RES-999", autor=master)


class TesteValidarAutoria(BaseMySQLTest):
    """`validar_autoria` é chamada por quem regista uma operação com
    autoria — anonimizações, requisições, movimentos de stock,
    alterações de configuração (ver docstring do módulo)."""

    def teste_aceita_responsavel_ativo(self):
        r = responsaveis.criar("Ana Ferreira")

        validado = responsaveis.validar_autoria(r["id"])

        self.assertEqual(r["id"], validado["id"])

    def teste_recusa_none(self):
        with self.assertRaises(ValueError):
            responsaveis.validar_autoria(None)

    def teste_recusa_vazio_ou_so_espacos(self):
        for valor in ("", "   "):
            with self.assertRaises(ValueError):
                responsaveis.validar_autoria(valor)

    def teste_recusa_inexistente(self):
        with self.assertRaises(ValueError):
            responsaveis.validar_autoria("RES-999")

    def teste_recusa_inativo(self):
        master = _criar_master()
        r = responsaveis.criar("Ana Ferreira")
        responsaveis.desativar(r["id"], autor=master)

        with self.assertRaises(ValueError):
            responsaveis.validar_autoria(r["id"])

    def teste_aceita_id_com_espacos_a_volta(self):
        r = responsaveis.criar("Ana Ferreira")

        validado = responsaveis.validar_autoria(f"  {r['id']}  ")

        self.assertEqual(r["id"], validado["id"])


if __name__ == "__main__":
    unittest.main()
