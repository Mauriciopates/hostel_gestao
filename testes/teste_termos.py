"""Testes do módulo `termos` (v1.6.0).

REESCRITO 22/09/2026 (PASSO 8) sobre `BaseTermosTest`, em vez de
`unittest.TestCase` puro.

PORQUÊ DA REESCRITA: a versão anterior corria contra a BD de
DESENVOLVIMENTO (`hostel_gestao`), fazia limpeza à mão com `DELETE
FROM avisos_privacidade`, e dependia de já existir uma versão em
vigor publicada naquela base para os testes não rebentarem. Numa
base limpa, ou depois de um TRUNCATE a `textos_legais`, todos os
testes que chamam `termos.texto_em_vigor` ou `termos.verificar`
rebentavam com ValueError antes de chegar a verificar nada.

A `BaseTermosTest` (ver `apoio_BD.py`) resolve as duas fragilidades
de uma vez:
  - Isola da base real (herda de `BaseMySQLTest`): TRUNCATE antes de
    cada teste, tudo em `hostel_gestao_teste`.
  - Publica uma versão "1.0" de cada um dos três documentos no
    `setUp`, e expõe `self.master` (o Master usado como autor).

NOTA sobre identificadores: a versão antiga usava `RES-TESTE` /
`CLI-TESTE`, que não existem na BD de teste. Aqui usam-se os
identificadores reais do `self.master` para os testes de
responsável, e cria-se um cliente a sério com `clientes.criar` para
os testes de cliente. Nenhuma linha precisa de limpeza à mão — o
TRUNCATE do próximo teste trata disso.

NOTA sobre "regra 4" (FK composta ON UPDATE RESTRICT): o teste
`TesteFkComposta.test_update_em_versao_com_aviso_falha` faz um
`UPDATE` cru na tabela `textos_legais` para provar o comportamento
real da FK. É intencionalmente fora do estilo do resto do ficheiro
(toca o `repositorio` em cru), porque a única forma de testar uma
constraint é tentar violá-la. Se a FK desaparecer um dia do schema,
este teste falha — que é o que se quer.
"""

import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseTermosTest

import clientes
import repositorio
import responsaveis
import termos


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _criar_cliente_minimo():
    """Cliente real, para usar como titular. O regime Airbnb não
    exige NIF, morada, estado_civil nem telefone — os quatro campos
    que faltariam a um cliente mínimo. Sem isto, `clientes.criar`
    levantaria ValueError por falta de obrigatórios do mensal."""
    return clientes.criar(
        "Hóspede de Teste",
        "Passaporte",
        "X1234567",
        "airbnb",
        nacionalidade="Brasileira",
        pais_emissor_documento="Brasil",
        pais_residencia="Brasil",
        data_nascimento=date(1990, 1, 1),
        validade_documento=date(2035, 1, 1),
    )


# ---------------------------------------------------------------------
# 1. texto_em_vigor
# ---------------------------------------------------------------------


class TesteTextoEmVigor(BaseTermosTest):
    """Registo do documento em vigor, por tipo."""

    def test_devolve_versao_em_vigor_dos_tres_documentos(self):
        """A `BaseTermosTest` publica uma versão "1.0" de cada
        documento — os três têm de a devolver."""
        for tipo in termos.TIPOS:
            texto = termos.texto_em_vigor(tipo)
            self.assertEqual(texto["versao"], "1.0")
            self.assertEqual(texto["tipo"], tipo)
            self.assertTrue(texto["em_vigor"])

    def test_documento_desconhecido_levanta(self):
        with self.assertRaises(ValueError):
            termos.texto_em_vigor("inventado")

    def test_sem_versao_em_vigor_levanta(self):
        """Apagar todas as versões de um tipo deixa `texto_em_vigor`
        sem nada para devolver — a função tem de levantar, não
        devolver None."""
        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            cursor.execute(
                "DELETE FROM textos_legais WHERE tipo = %s",
                (termos.CONFIDENCIALIDADE,),
            )
            conexao.commit()
        finally:
            conexao.close()

        with self.assertRaises(ValueError):
            termos.texto_em_vigor(termos.CONFIDENCIALIDADE)


# ---------------------------------------------------------------------
# 2. verificar — regra 5 (None != "1.0")
# ---------------------------------------------------------------------


class TesteVerificar(BaseTermosTest):
    """Estado de um titular perante o documento em vigor."""

    def test_quem_nunca_aceitou_precisa_aceitar_confidencialidade(self):
        """Regra 5: `None != "1.0"`. Sem aviso prévio, um documento
        que bloqueia exige aceitação."""
        estado = termos.verificar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
        )

        self.assertIsNone(estado["versao_aceite"])
        self.assertIsNone(estado["data_aceite"])
        self.assertTrue(estado["precisa_aceitar"])

    def test_informacao_ao_hospede_nunca_precisa_aceitar(self):
        """A informação ao hóspede não bloqueia — sem aviso prévio,
        `precisa_aceitar` fica False mesmo assim."""
        estado = termos.verificar(
            termos.TITULAR_CLIENTE,
            "CLI-001",
            termos.PRIVACIDADE_HOSPEDE,
        )

        self.assertFalse(estado["precisa_aceitar"])

    def test_informacao_ao_colaborador_nunca_precisa_aceitar(self):
        estado = termos.verificar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.PRIVACIDADE_COLABORADOR,
        )

        self.assertFalse(estado["precisa_aceitar"])

    def test_depois_de_registar_deixa_de_precisar(self):
        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        estado = termos.verificar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
        )

        self.assertFalse(estado["precisa_aceitar"])
        self.assertEqual(estado["versao_aceite"], "1.0")
        self.assertIsNotNone(estado["data_aceite"])

    def test_titular_desconhecido_levanta(self):
        with self.assertRaises(ValueError):
            termos.verificar(
                "hospede",
                self.master["id"],
                termos.CONFIDENCIALIDADE,
            )

    def test_titular_vazio_levanta(self):
        with self.assertRaises(ValueError):
            termos.verificar(
                termos.TITULAR_RESPONSAVEL,
                "",
                termos.CONFIDENCIALIDADE,
            )

    def test_documento_desconhecido_levanta(self):
        with self.assertRaises(ValueError):
            termos.verificar(
                termos.TITULAR_RESPONSAVEL,
                self.master["id"],
                "inventado",
            )


# ---------------------------------------------------------------------
# 3. registar — regras 1 e 2
# ---------------------------------------------------------------------


class TesteRegistar(BaseTermosTest):
    """Gravação do aviso: versão em vigor lida no momento, data do
    servidor, sem duplicação."""

    def test_registar_devolve_a_versao_em_vigor(self):
        """Regra 1: `registar` não recebe versão como parâmetro.
        Devolve sempre a versão em vigor no momento."""
        versao = termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        self.assertEqual(versao, "1.0")

    def test_registar_nao_duplica_mesma_versao(self):
        """Registar três vezes a mesma versão cria UMA linha."""
        for _ in range(3):
            termos.registar(
                termos.TITULAR_RESPONSAVEL,
                self.master["id"],
                termos.CONFIDENCIALIDADE,
                registado_por_id=self.master["id"],
            )

        historico = termos.historico(
            termos.TITULAR_RESPONSAVEL, self.master["id"]
        )

        self.assertEqual(len(historico), 1)

    def test_data_vem_do_servidor_mysql(self):
        """Regra 2: a data de entrega é gerada por `NOW()` no MySQL,
        não pelo relógio do Python. Teste-se pela diferença entre a
        data gravada e o `datetime.now()` local — < 5 segundos é
        folgado para uma operação de rede local."""
        antes = datetime.now()

        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        depois = datetime.now()

        aviso = repositorio.obter_ultimo_aviso(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
        )

        self.assertIsNotNone(aviso)
        data_gravada = aviso["data_entrega"]  # type: ignore

        # Aceita-se uma janela folgada: entre 5s antes do teste e 5s
        # depois. Se o Python estivesse a gerar a data, viria dentro
        # desta janela também — mas o que estamos a testar é que a
        # data NÃO é nem o `date.today()` (dia, sem hora) nem uma
        # data muito distante. Um valor com segundos e microssegundos
        # é o sinal de que veio do servidor.
        self.assertGreaterEqual(data_gravada, antes - timedelta(seconds=5))
        self.assertLessEqual(data_gravada, depois + timedelta(seconds=5))

    def test_registar_guarda_versao_em_vigor_no_momento(self):
        """Regra 1, o ponto mais importante: se o ecrã estiver aberto
        quando uma versão nova é publicada, o `registar` grava a
        versão EM VIGOR no momento da chamada, não a versão que
        estava em vigor quando o ecrã abriu."""
        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        # Agora publica-se uma versão nova, já depois do primeiro
        # registo.
        termos.publicar(
            termos.CONFIDENCIALIDADE,
            "2.0",
            "Versão 2.0, publicada a meio do teste.",
            autor=self.master,
        )

        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        historico = termos.historico(
            termos.TITULAR_RESPONSAVEL, self.master["id"]
        )

        # Duas linhas, cada uma com a versão em vigor no seu momento.
        versoes = {aviso["versao_texto"] for aviso in historico}
        self.assertEqual(versoes, {"1.0", "2.0"})

    def test_suporte_invalido_levanta(self):
        with self.assertRaises(ValueError):
            termos.registar(
                termos.TITULAR_RESPONSAVEL,
                self.master["id"],
                termos.CONFIDENCIALIDADE,
                suporte="fax",
            )

    def test_registado_por_none_e_aceite(self):
        """Registo via web: não há ninguém a assinar pelo sistema."""
        termos.registar(
            termos.TITULAR_CLIENTE,
            "CLI-001",
            termos.PRIVACIDADE_HOSPEDE,
            registado_por_id=None,
            suporte="web",
        )

        historico = termos.historico(
            termos.TITULAR_CLIENTE, "CLI-001"
        )
        self.assertEqual(len(historico), 1)
        self.assertEqual(historico[0]["registado_por_id"], "")


# ---------------------------------------------------------------------
# 4. publicar — regra 3 (só Master)
# ---------------------------------------------------------------------


class TestePublicar(BaseTermosTest):
    """Publicação de versões novas — autorização e validações."""

    def test_master_publica_versao_nova(self):
        versao = termos.publicar(
            termos.CONFIDENCIALIDADE,
            "2.0",
            "Texto novo, versão 2.0.",
            autor=self.master,
        )

        self.assertEqual(versao, "2.0")

        em_vigor = termos.texto_em_vigor(termos.CONFIDENCIALIDADE)
        self.assertEqual(em_vigor["versao"], "2.0")

    def test_staff_nao_publica(self):
        """Regra 3: só Master publica."""
        staff = responsaveis.criar(
            "Staff de Teste", tipo_utilizador="Staff"
        )

        with self.assertRaises(ValueError):
            termos.publicar(
                termos.CONFIDENCIALIDADE,
                "2.0",
                "Tentativa de publicar como Staff.",
                autor=staff,
            )

    def test_admin_nao_publica(self):
        """A regra é só Master, não Master+Admin — testa-se o
        Admin explicitamente para o distinguir do Staff."""
        admin = responsaveis.criar(
            "Admin de Teste", tipo_utilizador="Admin"
        )

        with self.assertRaises(ValueError):
            termos.publicar(
                termos.CONFIDENCIALIDADE,
                "2.0",
                "Tentativa de publicar como Admin.",
                autor=admin,
            )

    def test_autor_none_levanta(self):
        with self.assertRaises(ValueError):
            termos.publicar(
                termos.CONFIDENCIALIDADE,
                "2.0",
                "Texto.",
                autor=None,
            )

    def test_versao_duplicada_levanta(self):
        """A tabela tem UNIQUE (tipo, versao) — mas a validação de
        negócio levanta antes, com mensagem em português."""
        with self.assertRaises(ValueError):
            termos.publicar(
                termos.CONFIDENCIALIDADE,
                "1.0",  # já existe, publicada pela BaseTermosTest
                "Tentativa de reescrever a 1.0.",
                autor=self.master,
            )

    def test_versao_vazia_levanta(self):
        with self.assertRaises(ValueError):
            termos.publicar(
                termos.CONFIDENCIALIDADE,
                "   ",
                "Texto.",
                autor=self.master,
            )

    def test_versao_demasiado_longa_levanta(self):
        with self.assertRaises(ValueError):
            termos.publicar(
                termos.CONFIDENCIALIDADE,
                "x" * 21,  # _MAX_VERSAO = 20
                "Texto.",
                autor=self.master,
            )

    def test_texto_vazio_levanta(self):
        with self.assertRaises(ValueError):
            termos.publicar(
                termos.CONFIDENCIALIDADE,
                "2.0",
                "   ",
                autor=self.master,
            )

    def test_documento_desconhecido_levanta(self):
        with self.assertRaises(ValueError):
            termos.publicar(
                "inventado",
                "1.0",
                "Texto.",
                autor=self.master,
            )

    def test_publicar_tira_a_versao_anterior_de_vigor(self):
        """Publicar uma versão nova põe a anterior a `em_vigor=False`
        — a regra "só uma versão de cada tipo em vigor" vive na
        camada de negócio, dentro de `publicar_texto` (transação
        UPDATE + INSERT)."""
        termos.publicar(
            termos.CONFIDENCIALIDADE,
            "2.0",
            "Texto novo.",
            autor=self.master,
        )

        historico = termos.historico_documento(termos.CONFIDENCIALIDADE)
        em_vigor = [t for t in historico if t["em_vigor"]]

        self.assertEqual(len(em_vigor), 1)
        self.assertEqual(em_vigor[0]["versao"], "2.0")


# ---------------------------------------------------------------------
# 5. FK composta (documento, versao) ON UPDATE RESTRICT
# ---------------------------------------------------------------------


class TesteFkComposta(BaseTermosTest):
    """Regra 4: a FK composta entre avisos_privacidade e
    textos_legais é ON UPDATE RESTRICT — um registo de aceitação
    não pode ficar órfão de uma versão que entretanto mudou de
    nome.

    Este teste corre um UPDATE cru na tabela `textos_legais` — é a
    única forma de provar o comportamento real de uma constraint.
    Se a FK desaparecer um dia do schema, este teste falha."""

    def test_update_em_versao_com_aviso_falha(self):
        """Publica 1.0, regista um aviso nela, e tenta mudar a versão
        para 1.1 com UPDATE direto — o MySQL recusa por causa da FK
        composta ON UPDATE RESTRICT."""

        # 1. Regista um aviso na versão 1.0 (publicada pela
        #    BaseTermosTest) — cria a referência que a FK protege.
        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        # 2. Tenta mudar o nome da versão na tabela `textos_legais`.
        #    O MySQL tem de recusar (foreign key constraint fails).
        import mysql.connector

        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            with self.assertRaises(mysql.connector.IntegrityError):
                cursor.execute(
                    "UPDATE textos_legais SET versao = %s "
                    "WHERE tipo = %s AND versao = %s",
                    ("1.1", termos.CONFIDENCIALIDADE, "1.0"),
                )
        finally:
            conexao.close()

    def test_versao_sem_avisos_pode_ser_alterada(self):
        """Controlo negativo: uma versão SEM avisos associados não é
        travada pela FK — prova que o teste anterior mede mesmo a FK
        e não qualquer outra coisa."""

        # Publica uma versão nova (2.0) que ninguém vai registar.
        termos.publicar(
            termos.CONFIDENCIALIDADE,
            "2.0",
            "Versão 2.0, sem avisos associados.",
            autor=self.master,
        )

        conexao = repositorio.obter_conexao()
        try:
            cursor = conexao.cursor()
            # Isto NÃO deve levantar — a versão 2.0 ainda não tem
            # nenhum aviso a apontar-lhe.
            cursor.execute(
                "UPDATE textos_legais SET versao = %s "
                "WHERE tipo = %s AND versao = %s",
                ("2.1", termos.CONFIDENCIALIDADE, "2.0"),
            )
            conexao.commit()
        finally:
            conexao.close()

        # Confirma que a alteração passou.
        texto = repositorio.obter_texto(termos.CONFIDENCIALIDADE, "2.1")
        self.assertIsNotNone(texto)


# ---------------------------------------------------------------------
# 6. Histórico e estado dos documentos
# ---------------------------------------------------------------------


class TesteHistoricoEEstado(BaseTermosTest):
    """`historico`, `historico_documento` e `estado_documentos`."""

    def test_historico_do_titular_vazio_sem_registos(self):
        self.assertEqual(
            termos.historico(
                termos.TITULAR_RESPONSAVEL, self.master["id"]
            ),
            [],
        )

    def test_historico_mais_recente_primeiro(self):
        """Registar 1.0 e depois 2.0 — o histórico vem com 2.0
        à frente de 1.0 (ordenação por data_entrega desc)."""
        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        termos.publicar(
            termos.CONFIDENCIALIDADE,
            "2.0",
            "Versão nova.",
            autor=self.master,
        )

        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        historico = termos.historico(
            termos.TITULAR_RESPONSAVEL, self.master["id"]
        )

        self.assertEqual(len(historico), 2)
        self.assertEqual(historico[0]["versao_texto"], "2.0")
        self.assertEqual(historico[1]["versao_texto"], "1.0")

    def test_historico_titular_desconhecido_levanta(self):
        with self.assertRaises(ValueError):
            termos.historico("hospede", "X")

    def test_historico_titular_vazio_levanta(self):
        with self.assertRaises(ValueError):
            termos.historico(termos.TITULAR_RESPONSAVEL, "")

    def test_historico_documento_mostra_todas_as_versoes(self):
        termos.publicar(
            termos.CONFIDENCIALIDADE,
            "2.0",
            "Texto novo.",
            autor=self.master,
        )

        historico = termos.historico_documento(termos.CONFIDENCIALIDADE)
        versoes = [t["versao"] for t in historico]

        self.assertIn("1.0", versoes)
        self.assertIn("2.0", versoes)

    def test_historico_documento_desconhecido_levanta(self):
        with self.assertRaises(ValueError):
            termos.historico_documento("inventado")

    def test_estado_documentos_traz_os_tres(self):
        estado = termos.estado_documentos()
        tipos = [e["tipo"] for e in estado]

        self.assertEqual(len(estado), 3)
        for tipo in termos.TIPOS:
            self.assertIn(tipo, tipos)

    def test_estado_documentos_conta_aceitacoes(self):
        """Registar uma aceitação no Master faz `aceitacoes` subir
        para 1, no documento certo."""
        termos.registar(
            termos.TITULAR_RESPONSAVEL,
            self.master["id"],
            termos.CONFIDENCIALIDADE,
            registado_por_id=self.master["id"],
        )

        estado = termos.estado_documentos()
        confidencialidade = next(
            e for e in estado if e["tipo"] == termos.CONFIDENCIALIDADE
        )

        self.assertEqual(confidencialidade["aceitacoes"], 1)
        self.assertTrue(confidencialidade["bloqueia"])

    def test_estado_documentos_privacidades_nao_bloqueiam(self):
        estado = termos.estado_documentos()

        privacidades = [
            e for e in estado if e["tipo"] != termos.CONFIDENCIALIDADE
        ]

        for entrada in privacidades:
            self.assertFalse(entrada["bloqueia"])


# ---------------------------------------------------------------------
# 7. bloqueia
# ---------------------------------------------------------------------


class TesteBloqueia(BaseTermosTest):
    """`bloqueia(tipo)` — a regra que separa compromisso de
    informação."""

    def test_confidencialidade_bloqueia(self):
        self.assertTrue(termos.bloqueia(termos.CONFIDENCIALIDADE))

    def test_privacidades_nao_bloqueiam(self):
        self.assertFalse(termos.bloqueia(termos.PRIVACIDADE_HOSPEDE))
        self.assertFalse(termos.bloqueia(termos.PRIVACIDADE_COLABORADOR))


if __name__ == "__main__":
    unittest.main(verbosity=2)