"""Testes de `sistema.py` — o reset "Começar do zero".

MIGRAÇÃO MySQL: `sistema.py` fala diretamente com o `repositorio.py`
(o mesmo que todos os outros módulos de negócio desde a Fase 2). Estes
testes correm contra a base de dados de teste dedicada (ver
`apoio_BD.py`) — NUNCA contra a base de dados real. Cada teste começa
com as tabelas vazias e os contadores reiniciados.

ÂMBITO: só a função pública `sistema.comecar_do_zero(autor)`. As três
funções privadas (`_validar_autor_master`, `_reiniciar_contadores`,
`_definir_credencial_inicial`) NÃO são testadas isoladamente — os seus
efeitos são observáveis pela própria `comecar_do_zero`:

  - `_validar_autor_master`     → comportamento dos testes de autor.
  - `_reiniciar_contadores`     → primeira propriedade depois do reset
                                  é PRO-001.
  - `_definir_credencial_inicial` → autenticar com as credenciais
                                    padrão devolve MOTIVO_OK.

Testá-las diretamente obrigaria a importar símbolos privados, o que
não se faz em nenhum outro ficheiro da suite.

CUSTO: cada chamada a `comecar_do_zero` corre `_definir_credencial_
inicial`, que faz um PBKDF2 de 100.000 iterações (~0,4s por hash, tal
como `utilizadores.definir_credencial`). Os testes que correm o
`comecar_do_zero` todo pagam esse custo — é o preço de testar isto a
sério, e o volume do ficheiro é pequeno.

MOCK DO MYSQLDUMP: `comecar_do_zero` chama
`repositorio.criar_backup_com_nome("pre_reset")`, que por baixo corre
`subprocess.run(["mysqldump", ...])`. Nos testes que verificam a falha
do backup, o `subprocess.run` é substituído por `unittest.mock.patch`
— mesmo padrão já consolidado em `teste_repositorio.py`.

NUNCA toca na base de dados real: `BaseMySQLTest.setUp` substitui
`config.DB_NAME` por `DB_NAME_TESTE` antes de qualquer operação, e
`tearDown` repõe. Confirmado pelo utilizador em 22/09/2026.
"""

import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest

import clientes
import config
import configuracoes
import estoque
import propriedades
import repositorio
import responsaveis
import sistema
import unidades
import utilizadores


# ---------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------


def _criar_master(nome="Master Existente"):
    """Master ativo, pronto a servir de autor para `comecar_do_zero`.

    Cria-se SEMPRE um Master novo dentro de cada teste, nunca em
    `setUp` partilhado — cada teste é auto-suficiente, mesma
    convenção já consolidada no PASSO 9.
    """
    return responsaveis.criar(nome, tipo_utilizador="Master")


def _criar_admin(nome="Admin de Teste"):
    return responsaveis.criar(nome, tipo_utilizador="Admin")


def _criar_staff(nome="Staff de Teste"):
    return responsaveis.criar(nome, tipo_utilizador="Staff")


def _criar_propriedade(nome="Foz Velha"):
    return propriedades.criar(nome, "Rua de Exemplo, 1")


def _criar_cliente_mensal(nome="Ana Silva", nif="501442600"):
    """Cliente completo para o regime mensal — todos os obrigatórios
    que `validacoes.validar_cliente` exige (26/08 + 16/09/2026)."""
    return clientes.criar(
        nome,
        "Cartão de Cidadão",
        "12345678",
        "mensal",
        nif=nif,
        morada="Rua do Porto, 12",
        nacionalidade="Portuguesa",
        estado_civil="Solteiro(a)",
        telefone="912345678",
        data_nascimento=date(1990, 5, 20),
        validade_documento=date(2030, 1, 1),
    )


def _criar_produto(nome="Lixívia"):
    return estoque.criar_produto(nome, "L")


# =====================================================================
# 1. Validação do autor
# =====================================================================


class TesteAutor(BaseMySQLTest):
    """`comecar_do_zero` recusa qualquer autor que não seja Master."""

    def test_autor_none_falha(self):
        with self.assertRaises(ValueError):
            sistema.comecar_do_zero(None)

    def test_autor_sem_id_falha(self):
        with self.assertRaises(ValueError):
            sistema.comecar_do_zero({"nome": "sem id"})

    def test_autor_admin_falha(self):
        admin = _criar_admin()
        with self.assertRaises(ValueError):
            sistema.comecar_do_zero(admin)

    def test_autor_staff_falha(self):
        staff = _criar_staff()
        with self.assertRaises(ValueError):
            sistema.comecar_do_zero(staff)

    def test_autor_master_passa(self):
        """Um Master válido não é travado na validação — o
        `comecar_do_zero` corre até ao fim.

        Este é o teste que prova que a barreira de permissão não é
        demasiado restritiva."""
        master = _criar_master()

        resultado = sistema.comecar_do_zero(master)

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo_utilizador"], "Master")

    def test_validacao_do_autor_corre_antes_do_backup(self):
        """Um autor inválido é recusado ANTES de haver backup.

        Se a validação do autor viesse depois do backup, um Admin
        que tentasse o reset deixava um `pre_reset_*.sql` pendurado
        em disco — lixo que a operação nunca devia ter produzido.
        """
        admin = _criar_admin()

        with self.assertRaises(ValueError):
            sistema.comecar_do_zero(admin)

        # Nenhum ficheiro `pre_reset_*.sql` foi criado.
        ficheiros = list(config.DIR_BACKUPS.glob("pre_reset_*.sql"))
        self.assertEqual(ficheiros, [])


# =====================================================================
# 2. Backup antes do reset
# =====================================================================


class TesteBackup(BaseMySQLTest):
    """`comecar_do_zero` faz um backup automático com prefixo
    `pre_reset` antes de apagar."""

    def test_backup_com_prefixo_pre_reset_e_criado(self):
        master = _criar_master()

        sistema.comecar_do_zero(master)

        ficheiros = list(config.DIR_BACKUPS.glob("pre_reset_*.sql"))
        self.assertEqual(len(ficheiros), 1)

    def test_backup_vai_para_a_pasta_correta(self):
        """O ficheiro fica em `config.DIR_BACKUPS`, não noutro sítio."""
        master = _criar_master()

        sistema.comecar_do_zero(master)

        for ficheiro in config.DIR_BACKUPS.glob("pre_reset_*.sql"):
            self.assertEqual(ficheiro.parent, config.DIR_BACKUPS)

    def test_backup_criado_antes_de_apagar(self):
        """O backup é criado DEPOIS de validar o autor, mas ANTES
        de apagar.

        Prova-se pela ordem dos efeitos observáveis: se o backup
        corresse depois do `apagar_tudo`, o dump conteria uma BD
        já vazia. O que se verifica aqui não é o conteúdo (é binário
        do mysqldump), é apenas que o ficheiro existe quando o
        `comecar_do_zero` termina — combinado com o teste seguinte
        (falha do mysqldump bloqueia o reset antes de apagar),
        garante que o backup correu antes.
        """
        _criar_propriedade("Vai desaparecer")
        master = _criar_master()

        sistema.comecar_do_zero(master)

        # O backup existe; a propriedade desapareceu.
        self.assertTrue(
            list(config.DIR_BACKUPS.glob("pre_reset_*.sql"))
        )
        self.assertEqual(propriedades.listar(incluir_inativas=True), [])


# =====================================================================
# 3. Falha do backup
# =====================================================================


class TesteFalhaDoBackup(BaseMySQLTest):
    """Quando o `mysqldump` falha, o `comecar_do_zero` recusa ANTES
    de apagar nada — a BD fica intacta e nenhum ficheiro fica
    pendurado."""

    def test_falha_do_mysqldump_levanta_valueerror(self):
        master = _criar_master()

        with patch(
            "repositorio.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with self.assertRaises(ValueError):
                sistema.comecar_do_zero(master)

    def test_bd_fica_intacta_quando_backup_falha(self):
        """Os dados criados antes do reset continuam lá depois de o
        backup falhar."""
        propriedade = _criar_propriedade("Não pode desaparecer")
        cliente = _criar_cliente_mensal()
        produto = _criar_produto()
        master = _criar_master()

        with patch(
            "repositorio.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with self.assertRaises(ValueError):
                sistema.comecar_do_zero(master)

        # Tudo continua na base de dados.
        self.assertIsNotNone(propriedades.procurar(propriedade["id"]))
        self.assertIsNotNone(clientes.procurar(cliente["id"]))
        self.assertIsNotNone(estoque.procurar_produto(produto["id"]))

    def test_nenhum_pre_reset_pendurado_quando_backup_falha(self):
        """O `criar_backup_com_nome` já apaga o ficheiro a meio se o
        mysqldump falhar — não fica nenhum `pre_reset_*.sql` a zero
        bytes em disco."""
        master = _criar_master()

        with patch(
            "repositorio.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with self.assertRaises(ValueError):
                sistema.comecar_do_zero(master)

        ficheiros = list(config.DIR_BACKUPS.glob("pre_reset_*.sql"))
        self.assertEqual(ficheiros, [])

    def test_master_nao_e_criado_quando_backup_falha(self):
        """O reset não chegou à fase de criar o Master padrão — o
        Master que existia antes continua a ser o único."""
        master_original = _criar_master("O único Master")

        with patch(
            "repositorio.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with self.assertRaises(ValueError):
                sistema.comecar_do_zero(master_original)

        lista = responsaveis.listar(incluir_inativos=True)
        ids = [r["id"] for r in lista]
        self.assertIn(master_original["id"], ids)
        # Não apareceu um segundo Master criado pelo reset.
        self.assertEqual(len([r for r in lista if r["tipo_utilizador"] == "Master"]), 1)


# =====================================================================
# 4. Estado final depois do reset
# =====================================================================


class TesteEstadoFinal(BaseMySQLTest):
    """Depois de um reset bem-sucedido, a BD tem exatamente um
    responsável: o Master padrão."""

    def test_so_fica_um_responsavel(self):
        _criar_admin("Vai desaparecer 1")
        _criar_staff("Vai desaparecer 2")
        master_autor = _criar_master("Autor do reset")

        sistema.comecar_do_zero(master_autor)

        lista = responsaveis.listar(incluir_inativos=True)
        self.assertEqual(len(lista), 1)

    def test_o_unico_responsavel_e_master(self):
        master_autor = _criar_master("Autor do reset")

        sistema.comecar_do_zero(master_autor)

        lista = responsaveis.listar(incluir_inativos=True)
        self.assertEqual(lista[0]["tipo_utilizador"], "Master")

    def test_nome_do_master_padrao_vem_do_config(self):
        master_autor = _criar_master("Autor do reset")

        criado = sistema.comecar_do_zero(master_autor)

        self.assertEqual(criado["nome"], config.NOME_MASTER_PADRAO)

    def test_master_criado_tem_username_do_config(self):
        master_autor = _criar_master("Autor do reset")

        sistema.comecar_do_zero(master_autor)

        # Reler via repositório para apanhar a normalização.
        lista = utilizadores.listar_com_estado(incluir_inativos=True)
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["username"], config.UTILIZADOR_PADRAO)

    def test_o_master_do_reset_fica_ativo(self):
        master_autor = _criar_master("Autor do reset")

        criado = sistema.comecar_do_zero(master_autor)

        self.assertTrue(criado["ativo"])


# =====================================================================
# 5. Credencial inicial funcional
# =====================================================================


class TesteCredencialInicial(BaseMySQLTest):
    """A credencial definida pelo reset é autenticável — e é a única
    credencial que existe depois do reset."""

    def test_autenticar_com_credenciais_padrao(self):
        master_autor = _criar_master("Autor do reset")
        sistema.comecar_do_zero(master_autor)

        registo, motivo = utilizadores.autenticar(
            config.UTILIZADOR_PADRAO, config.PASSWORD_PADRAO
        )

        self.assertEqual(motivo, utilizadores.MOTIVO_OK)
        self.assertIsNotNone(registo)
        assert registo is not None
        self.assertEqual(registo["tipo_utilizador"], "Master")

    def test_password_padrao_errada_devolve_erro(self):
        master_autor = _criar_master("Autor do reset")
        sistema.comecar_do_zero(master_autor)

        registo, motivo = utilizadores.autenticar(
            config.UTILIZADOR_PADRAO, "password_errada"
        )

        self.assertIsNone(registo)
        self.assertEqual(motivo, utilizadores.MOTIVO_PASSWORD_ERRADA)

    def test_username_padrao_mas_sem_password_hash_daria_sem_credencial(self):
        """Controlo negativo: ANTES do reset, se alguém criar um
        responsável com o username padrão mas sem hash, o
        `autenticar` devolve `MOTIVO_SEM_CREDENCIAL`. Depois do
        reset, com a credencial definida, devolve `MOTIVO_OK`.

        Este teste cobre os dois lados, para provar que o
        `comecar_do_zero` realmente definiu a credencial (não se
        limitou a gravar o username)."""
        # Estado "antes": username definido mas sem hash.
        responsaveis.criar(
            "Sem credencial", tipo_utilizador="Master"
        )
        repositorio.atualizar_responsavel(
            responsaveis.listar()[0]["id"],
            {"username": config.UTILIZADOR_PADRAO},
        )

        registo, motivo = utilizadores.autenticar(
            config.UTILIZADOR_PADRAO, config.PASSWORD_PADRAO
        )
        self.assertIsNone(registo)
        self.assertEqual(motivo, utilizadores.MOTIVO_SEM_CREDENCIAL)

        # Reset (o autor tem de ser Master, e o anterior está lá).
        master_autor = responsaveis.criar(
            "Master Autor", tipo_utilizador="Master"
        )
        sistema.comecar_do_zero(master_autor)

        # Estado "depois": credencial funcional.
        registo, motivo = utilizadores.autenticar(
            config.UTILIZADOR_PADRAO, config.PASSWORD_PADRAO
        )
        self.assertEqual(motivo, utilizadores.MOTIVO_OK)


# =====================================================================
# 6. Contadores a zero
# =====================================================================


class TesteContadores(BaseMySQLTest):
    """Depois do reset, o próximo ID de cada prefixo é o 001 — os
    contadores voltaram a zero."""

    def test_proxima_propriedade_e_pro_001(self):
        # Criar uma propriedade ANTES, para o contador avançar.
        _criar_propriedade("Antes do reset")

        master_autor = _criar_master()
        sistema.comecar_do_zero(master_autor)

        nova = _criar_propriedade("Depois do reset")

        self.assertEqual(nova["id"], "PRO-001")

    def test_proximo_responsavel_e_res_001(self):
        """Depois do reset, o Master padrão já ocupou RES-001 — o
        próximo responsável criado é RES-002 (não RES-001), porque
        o próprio `comecar_do_zero` chamou `responsaveis.criar(...)`
        para o Master padrão."""
        # Criar vários responsáveis antes, para o contador avançar.
        _criar_admin("Antes 1")
        _criar_staff("Antes 2")

        master_autor = _criar_master("Autor do reset")
        sistema.comecar_do_zero(master_autor)

        # O Master padrão do reset é RES-001.
        lista = responsaveis.listar(incluir_inativos=True)
        self.assertEqual(lista[0]["id"], "RES-001")

        # O próximo a ser criado é RES-002.
        novo = _criar_staff("Depois do reset")
        self.assertEqual(novo["id"], "RES-002")

    def test_produto_e_prd_001_depois_do_reset(self):
        _criar_produto("Antes do reset")

        master_autor = _criar_master()
        sistema.comecar_do_zero(master_autor)

        novo = _criar_produto("Depois do reset")

        self.assertEqual(novo["id"], "PRD-001")


# =====================================================================
# 7. Dados anteriores desapareceram
# =====================================================================


class TesteDadosApagados(BaseMySQLTest):
    """Tudo o que existia antes do reset desaparece — clientes,
    propriedades, unidades, produtos, configurações."""

    def setUp(self):
        super().setUp()

        # Fixture comum: criar um pouco de tudo, para depois
        # verificar que nada sobrevive ao reset.
        self.propriedade = _criar_propriedade("Vai desaparecer")
        self.unidade = unidades.criar(
            self.propriedade["id"],
            "Unidade Vai Desaparecer",
            "mensal",
            Decimal("250.00"),
            Decimal("250.00"),
            Decimal("20.00"),
        )
        self.cliente = _criar_cliente_mensal()
        self.produto = _criar_produto()
        configuracoes.garantir_seed()
        configuracoes.definir(
            "operacao.dia_vencimento",
            10,
            autor=_criar_master("Autor pré-reset"),
        )

        # Autor do reset — criado por último, para o teste de
        # responsáveis ainda ver todos os outros.
        self.master_autor = _criar_master("Autor do reset")

    def test_clientes_apagados(self):
        sistema.comecar_do_zero(self.master_autor)

        self.assertEqual(
            clientes.listar(incluir_inativos=True), []
        )

    def test_propriedades_apagadas(self):
        sistema.comecar_do_zero(self.master_autor)

        self.assertEqual(
            propriedades.listar(incluir_inativas=True), []
        )

    def test_unidades_apagadas(self):
        sistema.comecar_do_zero(self.master_autor)

        self.assertEqual(
            unidades.listar(incluir_inativas=True), []
        )

    def test_produtos_apagados(self):
        sistema.comecar_do_zero(self.master_autor)

        self.assertEqual(
            estoque.listar_produtos(incluir_inativos=True), []
        )

    def test_configuracoes_apagadas(self):
        """As chaves de configuração desaparecem — a seed tem de
        correr outra vez depois do reset para as recriar."""
        sistema.comecar_do_zero(self.master_autor)

        # Nenhuma chave da seed sobreviveu.
        for chave in configuracoes._CHAVES:
            registo = repositorio.procurar_configuracao(chave)
            self.assertIsNone(
                registo,
                f"chave {chave!r} sobreviveu ao reset",
            )

    def test_historico_de_configuracoes_apagado(self):
        """O `configuracoes_historico` também é esvaziado — não se
        guarda o histórico de uma alteração a uma chave que já não
        existe."""
        sistema.comecar_do_zero(self.master_autor)

        self.assertEqual(configuracoes.listar_historico(), [])

    def test_todos_os_dados_desaparecem_em_conjunto(self):
        """Confirmação em bloco — uma só chamada ao reset apaga
        tudo de uma vez."""
        sistema.comecar_do_zero(self.master_autor)

        self.assertEqual(clientes.listar(incluir_inativos=True), [])
        self.assertEqual(propriedades.listar(incluir_inativas=True), [])
        self.assertEqual(unidades.listar(incluir_inativas=True), [])
        self.assertEqual(
            estoque.listar_produtos(incluir_inativos=True), []
        )
        self.assertEqual(configuracoes.listar_historico(), [])

        # E sobra só o Master padrão.
        lista = responsaveis.listar(incluir_inativos=True)
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["tipo_utilizador"], "Master")


if __name__ == "__main__":
    unittest.main(verbosity=2)