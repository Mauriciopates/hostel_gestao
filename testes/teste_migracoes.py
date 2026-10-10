"""Testes do sistema de migrações (v1.8.0, passo C).

Correm contra a base de teste dedicada (`apoio_BD.BaseMySQLTest`),
com listas de migrações PRÓPRIAS — nunca a lista oficial, que tem
seeds (decisão 4 do passo C: a base de testes precisa das tabelas
vazias). As migrações de teste só mexem numa tabela `migracao_teste`,
criada e apagada aqui.

A tabela `migracoes_aplicadas` não está na lista do TRUNCATE do
`apoio_BD` (é criada pelo próprio sistema de migrações), por isso
cada teste apaga-a no início — cada teste começa como uma base que
nunca correu migrações.
"""

import sys
import threading
import unittest
from datetime import date
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest  # noqa: E402

import clientes  # noqa: E402
import migracoes  # noqa: E402
import repositorio  # noqa: E402

_CRIAR_TABELA_TESTE = (
    "CREATE TABLE IF NOT EXISTS migracao_teste ("
    "id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
    "nome VARCHAR(50) NOT NULL)"
)
_INSERIR_A = (
    "INSERT INTO migracao_teste (nome) SELECT 'A' FROM DUAL "
    "WHERE NOT EXISTS (SELECT 1 FROM migracao_teste WHERE nome = 'A')"
)
_INSERIR_B = (
    "INSERT INTO migracao_teste (nome) SELECT 'B' FROM DUAL "
    "WHERE NOT EXISTS (SELECT 1 FROM migracao_teste WHERE nome = 'B')"
)


def _executar(sql):
    """Corre uma instrução avulsa na base de teste (preparação)."""
    conexao = repositorio.obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(sql)
        conexao.commit()
    finally:
        conexao.close()


def _nomes_em_teste():
    """Devolve a lista ordenada dos nomes gravados em migracao_teste."""
    conexao = repositorio.obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT nome FROM migracao_teste ORDER BY nome")
        linhas = cast(list[tuple], cursor.fetchall())
        return [str(linha[0]) for linha in linhas]
    finally:
        conexao.close()


class BaseMigracoesTest(BaseMySQLTest):
    """Cada teste começa sem `migracoes_aplicadas` nem
    `migracao_teste`."""

    def setUp(self):
        super().setUp()
        _executar("DROP TABLE IF EXISTS migracoes_aplicadas")
        _executar("DROP TABLE IF EXISTS migracao_teste")

    def tearDown(self):
        _executar("DROP TABLE IF EXISTS migracao_teste")
        super().tearDown()


class TesteAplicarPendentes(BaseMigracoesTest):
    """O ciclo normal: criar a tabela, aplicar, não repetir."""

    def teste_cria_a_tabela_de_controlo(self):
        """Numa base sem `migracoes_aplicadas`, a tabela é criada e
        uma lista vazia não aplica nada."""
        self.assertEqual([], migracoes.aplicar_pendentes([]))
        self.assertEqual(set(), repositorio.listar_migracoes_aplicadas())

    def teste_aplica_por_ordem_e_regista(self):
        lista = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_inserir_a", [_INSERIR_A]),
        ]

        feitas = migracoes.aplicar_pendentes(lista)

        self.assertEqual(["0001_criar_tabela", "0002_inserir_a"], feitas)
        self.assertEqual(
            {"0001_criar_tabela", "0002_inserir_a"},
            repositorio.listar_migracoes_aplicadas(),
        )
        self.assertEqual(["A"], _nomes_em_teste())

    def teste_segunda_vez_nao_repete(self):
        """Num segundo arranque não há nada a aplicar."""
        lista = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_inserir_a", [_INSERIR_A]),
        ]
        migracoes.aplicar_pendentes(lista)

        self.assertEqual([], migracoes.aplicar_pendentes(lista))
        self.assertEqual(["A"], _nomes_em_teste())

    def teste_so_aplica_as_novas(self):
        """Uma migração acrescentada no fim é a única a correr."""
        lista = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_inserir_a", [_INSERIR_A]),
        ]
        migracoes.aplicar_pendentes(lista)

        lista.append(("0003_inserir_b", [_INSERIR_B]))

        self.assertEqual(
            ["0003_inserir_b"], migracoes.aplicar_pendentes(lista)
        )
        self.assertEqual(["A", "B"], _nomes_em_teste())

    def teste_varias_instrucoes_numa_migracao(self):
        lista = [
            ("0001_tudo", [_CRIAR_TABELA_TESTE, _INSERIR_A, _INSERIR_B]),
        ]

        migracoes.aplicar_pendentes(lista)

        self.assertEqual(["A", "B"], _nomes_em_teste())


class TesteFalha(BaseMigracoesTest):
    """Uma migração que falha não fica registada e trava as seguintes."""

    def _lista_com_falha(self):
        return [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            (
                "0002_partida",
                [_INSERIR_A, "INSERT INTO nao_existe VALUES (1)"],
            ),
            ("0003_inserir_b", [_INSERIR_B]),
        ]

    def teste_falha_levanta_value_error_com_o_nome(self):
        with self.assertRaises(ValueError) as contexto:
            migracoes.aplicar_pendentes(self._lista_com_falha())

        self.assertIn("0002_partida", str(contexto.exception))

    def teste_falha_nao_regista_e_nao_continua(self):
        with self.assertRaises(ValueError):
            migracoes.aplicar_pendentes(self._lista_com_falha())

        self.assertEqual(
            {"0001_criar_tabela"}, repositorio.listar_migracoes_aplicadas()
        )
        # O INSERT de 'A' da migração partida foi desfeito (rollback) e
        # a 0003 não correu.
        self.assertEqual([], _nomes_em_teste())

    def teste_depois_de_corrigida_volta_a_tentar(self):
        """No arranque seguinte, a migração em falta é tentada outra
        vez (aqui já corrigida)."""
        with self.assertRaises(ValueError):
            migracoes.aplicar_pendentes(self._lista_com_falha())

        corrigida = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_partida", [_INSERIR_A]),
            ("0003_inserir_b", [_INSERIR_B]),
        ]

        self.assertEqual(
            ["0002_partida", "0003_inserir_b"],
            migracoes.aplicar_pendentes(corrigida),
        )
        self.assertEqual(["A", "B"], _nomes_em_teste())


def _categorias():
    """Devolve [(id, nome), ...] das categorias, por id."""
    conexao = repositorio.obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT id, nome FROM categorias_despesa ORDER BY id")
        linhas = cast(list[tuple], cursor.fetchall())
        return [(str(a), str(b)) for a, b in linhas]
    finally:
        conexao.close()


class TesteBloqueio(BaseMigracoesTest):
    """v1.8.1 — dois arranques ao mesmo tempo não aplicam a mesma
    migração duas vezes (teste de instalação de 02/10/2026: o segundo
    rebentava com "Duplicate entry ... uq_migracoes_nome")."""

    def teste_dois_arranques_ao_mesmo_tempo(self):
        # A 0002 demora 1 s (DO SLEEP): sem o bloqueio, os dois
        # arranques liam "falta a 0002" e o segundo falhava no registo.
        lista = [
            ("0001_criar_tabela", [_CRIAR_TABELA_TESTE]),
            ("0002_lenta", ["DO SLEEP(1)", _INSERIR_A]),
        ]
        resultados, erros = [], []

        def arrancar():
            try:
                resultados.append(migracoes.aplicar_pendentes(lista))
            except Exception as erro:  # o teste mostra qual foi
                erros.append(erro)

        fios = [threading.Thread(target=arrancar) for _ in range(2)]
        for fio in fios:
            fio.start()
        for fio in fios:
            fio.join(timeout=30)

        self.assertEqual([], erros)
        # Um aplicou as duas; o outro esperou e já não tinha nada.
        self.assertCountEqual(
            [["0001_criar_tabela", "0002_lenta"], []], resultados
        )
        self.assertEqual(["A"], _nomes_em_teste())

    def teste_bloqueio_ocupado_demasiado_tempo_recusa(self):
        # Outra "cópia" segura o bloqueio; esta desiste ao fim de 1 s.
        with repositorio.bloqueio_migracoes():
            erro = []

            def tentar():
                try:
                    with repositorio.bloqueio_migracoes(espera_s=1):
                        pass
                except ValueError as e:
                    erro.append(e)

            fio = threading.Thread(target=tentar)
            fio.start()
            fio.join(timeout=10)

        self.assertEqual(1, len(erro))
        self.assertIn("Outro arranque", str(erro[0]))

    def teste_bloqueio_largado_no_fim(self):
        migracoes.aplicar_pendentes([])
        # Se tivesse ficado preso, esta espera de 1 s falhava.
        with repositorio.bloqueio_migracoes(espera_s=1):
            pass

    def teste_bloqueio_largado_mesmo_se_a_migracao_falha(self):
        with self.assertRaises(ValueError):
            migracoes.aplicar_pendentes(
                [("0001_partida", ["ISTO NAO E SQL"])]
            )
        with repositorio.bloqueio_migracoes(espera_s=1):
            pass


class TesteSeedCompraDeStock(BaseMigracoesTest):
    """Migração 0001 — a categoria "Compra de Stock" (passo D).

    Corre só essa migração da lista oficial, numa base de teste com as
    tabelas vazias (TRUNCATE do apoio_BD) — cada teste prepara o caso
    que quer à mão.
    """

    _NOME = "0001_categoria_compra_de_stock"

    def _aplicar(self):
        lista = [m for m in migracoes.MIGRACOES if m[0] == self._NOME]
        return migracoes.aplicar_pendentes(lista)

    def teste_base_nova_cria_cat_001(self):
        self.assertEqual([self._NOME], self._aplicar())
        self.assertEqual([("CAT-001", "Compra de Stock")], _categorias())

    def teste_base_antiga_ja_com_a_categoria_nao_duplica(self):
        """Caso do Localhost: a categoria já existe (aqui CAT-005)."""
        _executar(
            "INSERT INTO categorias_despesa (id, nome, ativo) "
            "VALUES ('CAT-005', 'Compra de Stock', 1)"
        )

        self._aplicar()

        self.assertEqual([("CAT-005", "Compra de Stock")], _categorias())

    def teste_id_ocupado_usa_o_seguinte(self):
        """Se o CAT-001 já é outra categoria, a nova fica com o
        seguinte — nunca um ID fixo."""
        _executar(
            "INSERT INTO categorias_despesa (id, nome, ativo) "
            "VALUES ('CAT-001', 'Consumos Mensais', 1)"
        )

        self._aplicar()

        self.assertEqual(
            [("CAT-001", "Consumos Mensais"), ("CAT-002", "Compra de Stock")],
            _categorias(),
        )

    def teste_proximo_id_continua_depois_do_seed(self):
        """O `proximo_id` conta a categoria semeada (era o bug)."""
        self._aplicar()

        self.assertEqual("CAT-002", repositorio.proximo_id("CAT"))

    def teste_segunda_vez_nao_faz_nada(self):
        self._aplicar()

        self.assertEqual([], self._aplicar())
        self.assertEqual(1, len(_categorias()))


class TesteTextosLegaisDemo(BaseMigracoesTest):
    """Migração 0002 — versão 0.1 fictícia dos três documentos."""

    _NOME = "0002_textos_legais_demo"
    _TIPOS = ("confidencialidade", "privacidade_colaborador",
              "privacidade_hospede")

    def _aplicar(self):
        lista = [m for m in migracoes.MIGRACOES if m[0] == self._NOME]
        return migracoes.aplicar_pendentes(lista)

    def teste_base_nova_publica_os_tres_em_vigor(self):
        self._aplicar()

        for tipo in self._TIPOS:
            with self.subTest(tipo=tipo):
                texto = repositorio.obter_texto_em_vigor(tipo)
                self.assertIsNotNone(texto)
                self.assertEqual("0.1", texto["versao"])
                self.assertIn("DEMONSTRAÇÃO", texto["texto"])
                self.assertIn("Gato Tripeiro", texto["texto"])

    def teste_texto_gravado_igual_ao_do_codigo(self):
        """Acentos, «», — e quebras de linha chegam intactos."""
        import migracoes_textos

        self._aplicar()

        texto = repositorio.obter_texto_em_vigor("confidencialidade")
        self.assertEqual(
            migracoes_textos.CONFIDENCIALIDADE, texto["texto"]
        )

    def teste_tipo_que_ja_tem_versao_nao_e_tocado(self):
        """Base antiga: a confidencialidade já tem a 1.0 — fica igual;
        os outros dois documentos recebem a 0.1."""
        _executar(
            "INSERT INTO textos_legais "
            "(tipo, versao, texto, publicado_em, em_vigor) VALUES "
            "('confidencialidade', '1.0', 'Texto real', CURDATE(), 1)"
        )

        self._aplicar()

        conf = repositorio.obter_texto_em_vigor("confidencialidade")
        self.assertEqual("1.0", conf["versao"])
        self.assertEqual("Texto real", conf["texto"])
        self.assertEqual(
            "0.1",
            repositorio.obter_texto_em_vigor("privacidade_hospede")["versao"],
        )

    def teste_segunda_vez_nao_faz_nada(self):
        self._aplicar()

        self.assertEqual([], self._aplicar())


_FORMA_ANTIGA_AVISOS = [
    # Desfaz a 0003 na base de TESTE, para a migração ter o que fazer.
    "ALTER TABLE avisos_privacidade DROP CONSTRAINT ck_aviso_um_titular",
    "ALTER TABLE avisos_privacidade DROP FOREIGN KEY fk_aviso_cliente",
    "ALTER TABLE avisos_privacidade DROP FOREIGN KEY fk_aviso_responsavel",
    "ALTER TABLE avisos_privacidade DROP FOREIGN KEY fk_aviso_registado_por",
    "ALTER TABLE avisos_privacidade DROP INDEX fk_aviso_registado_por",
    "ALTER TABLE avisos_privacidade DROP COLUMN cliente_id, "
    "DROP COLUMN responsavel_id",
    "ALTER TABLE avisos_privacidade "
    "ADD COLUMN titular_tipo ENUM('cliente','responsavel') NOT NULL "
    "AFTER id, "
    "ADD COLUMN titular_id VARCHAR(10) NOT NULL AFTER titular_tipo, "
    "ADD KEY idx_aviso_titular (titular_tipo, titular_id)",
]


def _colunas_avisos():
    conexao = repositorio.obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'avisos_privacidade'"
        )
        return {str(linha[0]) for linha in cast(list, cursor.fetchall())}
    finally:
        conexao.close()


def _restricoes_avisos():
    conexao = repositorio.obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT constraint_name FROM information_schema."
            "table_constraints WHERE constraint_schema = DATABASE() "
            "AND table_name = 'avisos_privacidade'"
        )
        return {str(linha[0]) for linha in cast(list, cursor.fetchall())}
    finally:
        conexao.close()


class TesteAvisosComFks(BaseMigracoesTest):
    """Migração 0003 — titular_tipo/titular_id → cliente_id +
    responsavel_id com FKs e CHECK.

    Cada teste põe a tabela na FORMA ANTIGA, corre a migração e, no
    fim, garante a forma nova (os outros testes precisam dela).
    """

    _NOME = "0003_avisos_privacidade_fks"

    def setUp(self):
        super().setUp()
        for instrucao in _FORMA_ANTIGA_AVISOS:
            _executar(instrucao)
        # Pessoas e texto reais, para as FKs terem a que apontar.
        _executar(
            "INSERT INTO responsaveis (id, nome, tipo_utilizador, ativo) "
            "VALUES ('RES-001', 'Master Teste', 'Master', 1)"
        )
        self.cliente = clientes.criar(
            "Hóspede de Teste", "Passaporte", "X1234567", "airbnb",
            nacionalidade="Brasileira", pais_emissor_documento="Brasil",
            pais_residencia="Brasil",
            data_nascimento=date(1990, 1, 1),
            validade_documento=date(2035, 1, 1),
        )
        _executar(
            "INSERT INTO textos_legais "
            "(tipo, versao, texto, publicado_em, em_vigor) VALUES "
            "('confidencialidade', '1.0', 'T', CURDATE(), 1), "
            "('privacidade_hospede', '1.0', 'T', CURDATE(), 1)"
        )

    def tearDown(self):
        _executar("DELETE FROM avisos_privacidade")
        self._correr_instrucoes()     # deixa sempre a forma nova
        super().tearDown()

    def _instrucoes(self):
        return [m for m in migracoes.MIGRACOES if m[0] == self._NOME][0][1]

    def _correr_instrucoes(self):
        """As instruções da 0003 numa ligação, SEM registar — como uma
        nova tentativa depois de uma falha a meio."""
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            for instrucao in self._instrucoes():
                cursor.execute(instrucao)
            conexao.commit()
        finally:
            conexao.close()

    def _aplicar(self):
        lista = [m for m in migracoes.MIGRACOES if m[0] == self._NOME]
        return migracoes.aplicar_pendentes(lista)

    def _aviso_antigo(self, tipo, titular_id, documento, registado=None):
        registado_sql = f"'{registado}'" if registado else "NULL"
        _executar(
            "INSERT INTO avisos_privacidade (titular_tipo, titular_id, "
            "documento, versao_texto, data_entrega, registado_por_id, "
            f"suporte) VALUES ('{tipo}', '{titular_id}', '{documento}', "
            f"'1.0', NOW(), {registado_sql}, 'sistema')"
        )

    def teste_copia_os_dados_e_cria_as_restricoes(self):
        self._aviso_antigo("cliente", self.cliente["id"],
                           "privacidade_hospede", "RES-001")
        self._aviso_antigo("responsavel", "RES-001", "confidencialidade",
                           "RES-001")

        self.assertEqual([self._NOME], self._aplicar())

        colunas = _colunas_avisos()
        self.assertIn("cliente_id", colunas)
        self.assertIn("responsavel_id", colunas)
        self.assertNotIn("titular_tipo", colunas)
        self.assertNotIn("titular_id", colunas)
        self.assertTrue(
            {"fk_aviso_cliente", "fk_aviso_responsavel",
             "fk_aviso_registado_por", "ck_aviso_um_titular",
             "fk_aviso_texto"} <= _restricoes_avisos()
        )

        historico_cliente = repositorio.listar_avisos(
            "cliente", self.cliente["id"])
        historico_master = repositorio.listar_avisos("responsavel",
                                                     "RES-001")
        self.assertEqual(1, len(historico_cliente))
        self.assertEqual("privacidade_hospede",
                         historico_cliente[0]["documento"])
        self.assertEqual(1, len(historico_master))
        self.assertEqual("confidencialidade",
                         historico_master[0]["documento"])

    def teste_tabela_vazia_tambem_migra(self):
        self._aplicar()
        self.assertIn("cliente_id", _colunas_avisos())

    def teste_segunda_vez_nao_faz_nada(self):
        self._aplicar()
        self.assertEqual([], self._aplicar())

    def teste_correr_outra_vez_as_instrucoes_nao_falha(self):
        """Idempotente: depois de aplicada, repetir as instruções (o
        que acontece se uma falha a meio obrigar a nova tentativa) não
        rebenta nem duplica nada."""
        self._aviso_antigo("responsavel", "RES-001", "confidencialidade")
        self._correr_instrucoes()
        self._correr_instrucoes()

        self.assertEqual(
            1, len(repositorio.listar_avisos("responsavel", "RES-001")))

    def teste_titular_orfao_faz_falhar_e_nao_regista(self):
        """Um aviso de um cliente que não existe impede a FK: a
        migração falha com o nome dela e fica por aplicar (a
        aplicação não abre — decisão 2 do passo C)."""
        self._aviso_antigo("cliente", "CLI-999", "privacidade_hospede")

        with self.assertRaises(ValueError) as contexto:
            self._aplicar()

        self.assertIn(self._NOME, str(contexto.exception))
        self.assertNotIn(self._NOME,
                         repositorio.listar_migracoes_aplicadas())


class TesteConsentimentoComunicacoes(BaseMigracoesTest):
    """Migração 0004 — coluna clientes.consente_comunicacoes_em."""

    _NOME = "0004_consentimento_comunicacoes"

    def setUp(self):
        super().setUp()
        _executar(
            "ALTER TABLE clientes DROP COLUMN consente_comunicacoes_em")

    def tearDown(self):
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            for instrucao in self._instrucoes():
                cursor.execute(instrucao)
            conexao.commit()
        finally:
            conexao.close()
        super().tearDown()

    def _instrucoes(self):
        return [m for m in migracoes.MIGRACOES if m[0] == self._NOME][0][1]

    def _colunas(self):
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'clientes'"
            )
            return {str(c[0]) for c in cast(list, cursor.fetchall())}
        finally:
            conexao.close()

    def teste_cria_a_coluna(self):
        lista = [m for m in migracoes.MIGRACOES if m[0] == self._NOME]
        self.assertEqual([self._NOME], migracoes.aplicar_pendentes(lista))
        self.assertIn("consente_comunicacoes_em", self._colunas())
        self.assertEqual([], migracoes.aplicar_pendentes(lista))


class TesteDespesaUnidadeAtribuida(BaseMigracoesTest):
    """Migração 0005 — auditoria da atribuição de unidade."""

    _NOME = "0005_despesa_unidade_atribuida"

    def setUp(self):
        super().setUp()
        _executar("ALTER TABLE despesas DROP FOREIGN KEY "
                  "fk_despesas_unidade_atribuida")
        _executar("ALTER TABLE despesas DROP COLUMN "
                  "unidade_atribuida_por_id")
        _executar("ALTER TABLE despesas DROP COLUMN unidade_atribuida_em")

    def tearDown(self):
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            for instrucao in self._instrucoes():
                cursor.execute(instrucao)
            conexao.commit()
        finally:
            conexao.close()
        super().tearDown()

    def _instrucoes(self):
        return [m for m in migracoes.MIGRACOES if m[0] == self._NOME][0][1]

    def _colunas(self):
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'despesas'"
            )
            return {str(c[0]) for c in cast(list, cursor.fetchall())}
        finally:
            conexao.close()

    def teste_cria_as_colunas_e_e_idempotente(self):
        lista = [m for m in migracoes.MIGRACOES if m[0] == self._NOME]
        self.assertEqual([self._NOME], migracoes.aplicar_pendentes(lista))
        colunas = self._colunas()
        self.assertIn("unidade_atribuida_por_id", colunas)
        self.assertIn("unidade_atribuida_em", colunas)
        self.assertEqual([], migracoes.aplicar_pendentes(lista))

    def teste_corre_duas_vezes_sem_erro(self):
        for _ in range(2):
            conexao = repositorio.obter_conexao()
            try:
                cursor = conexao.cursor()
                for instrucao in self._instrucoes():
                    cursor.execute(instrucao)
                conexao.commit()
            finally:
                conexao.close()
        self.assertIn("unidade_atribuida_em", self._colunas())


class TestePropriedadeSenhorio(BaseMigracoesTest):
    """Migração 0006 — coluna propriedades.senhorio_nome."""

    _NOME = "0006_propriedade_senhorio"

    def setUp(self):
        super().setUp()
        _executar("ALTER TABLE propriedades DROP COLUMN senhorio_nome")

    def tearDown(self):
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            for instrucao in self._instrucoes():
                cursor.execute(instrucao)
            conexao.commit()
        finally:
            conexao.close()
        super().tearDown()

    def _instrucoes(self):
        return [m for m in migracoes.MIGRACOES if m[0] == self._NOME][0][1]

    def _colunas(self):
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'propriedades'"
            )
            return {str(c[0]) for c in cast(list, cursor.fetchall())}
        finally:
            conexao.close()

    def teste_cria_a_coluna_e_e_idempotente(self):
        lista = [m for m in migracoes.MIGRACOES if m[0] == self._NOME]
        self.assertEqual([self._NOME], migracoes.aplicar_pendentes(lista))
        self.assertIn("senhorio_nome", self._colunas())
        self.assertEqual([], migracoes.aplicar_pendentes(lista))


class TesteValidarLista(unittest.TestCase):
    """Validação da lista — não precisa de base de dados."""

    def teste_lista_oficial_e_valida(self):
        migracoes.validar_lista(migracoes.MIGRACOES)

    def teste_nome_fora_do_formato_recusa(self):
        for nome in ("1_curto", "0001-hifen", "0001_Maiusculas", "abcd_x"):
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    migracoes.validar_lista([(nome, ["SELECT 1"])])

    def teste_nome_repetido_recusa(self):
        with self.assertRaises(ValueError):
            migracoes.validar_lista(
                [("0001_a", ["SELECT 1"]), ("0001_a", ["SELECT 1"])]
            )

    def teste_fora_de_ordem_recusa(self):
        with self.assertRaises(ValueError):
            migracoes.validar_lista(
                [("0002_b", ["SELECT 1"]), ("0001_a", ["SELECT 1"])]
            )

    def teste_sem_instrucoes_recusa(self):
        with self.assertRaises(ValueError):
            migracoes.validar_lista([("0001_vazia", [])])


if __name__ == "__main__":
    unittest.main()
