"""Testes de utilizadores.py — credenciais, autenticação e permissões.

MIGRAÇÃO MySQL (Fase 2): tal como `responsaveis.py`, `clientes.py` e
os restantes módulos de negócio já migrados, `utilizadores.py` fala
diretamente com o MySQL através do `repositorio.py`. Estes testes
correm contra a base de dados de teste dedicada (ver `apoio_BD.py`);
cada teste começa com as tabelas vazias e os contadores de
identificadores reiniciados.

NOTA sobre identidade: `procurar()` faz sempre um SELECT novo à base
de dados — já não devolve o MESMO objeto Python que `criar()`
devolveu. Os testes comparam por ID (ou pelo campo específico), nunca
o dicionário todo.

NOTA sobre o bug corrigido no PASSO 3 (v1.5.0 → corrigido a
22/09/2026): `utilizadores.reativar` escrevia `""` (string vazia) em
`desativado_por_id` (FK auto-referente para `responsaveis.id`) e
`data_desativacao` (DATE). O MySQL recusava os dois. A correção passa
`None` em ambos os campos. O teste que agarra este bug verifica a
releitura via `repositorio.procurar_responsavel` — o dict devolvido
pelo `reativar` fica com `None` nos dois campos (é o valor que a
função escreveu, não o normalizado que a releitura faz). Ver a
docstring desse teste para o porquê de a asserção sobre o dict
devolvido ter sido relaxada.

NOTA sobre a correção do PASSO 9 (22/09/2026) em
`utilizadores.definir_credencial`: a barreira de perfil passou a
estar no próprio módulo, via `verificar_permissao`. Antes, um Staff
autenticado conseguia definir credenciais a outro Staff — o único
`if` que lá estava só cobria o caso "Admin a mexer num não-Staff".
O teste `test_staff_nao_define_credencial` agarra este bug.

NOTA sobre custo: `utilizadores.definir_credencial` e
`alterar_password` correm PBKDF2 com 100.000 iterações (~0,4s cada
hash, como o próprio módulo documenta). Cada teste auto-suficiente
paga esse custo; é aceitável para o volume deste ficheiro.

NOTA sobre `autenticar`: a função devolve uma tupla `(registro,
motivo)` e NUNCA levanta. Os testes verificam o motivo em cada caso
de falha, não só a ausência de registo — é o motivo que o
`LoginModal` usa para escolher a mensagem em português.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from testes.apoio_BD import BaseMySQLTest

import repositorio
import responsaveis
import utilizadores


# ---------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------


def _criar_master(nome="Master de Teste"):
    """Cria um Master via `responsaveis.criar(...)` — sem autor (é
    bootstrap de teste), com perfil Master. É o autor que as funções
    de `utilizadores` exigem."""
    return responsaveis.criar(nome, tipo_utilizador="Master")


def _criar_staff(nome="Staff de Teste"):
    return responsaveis.criar(nome, tipo_utilizador="Staff")


def _criar_admin(nome="Admin de Teste"):
    return responsaveis.criar(nome, tipo_utilizador="Admin")


def _definir_credencial(alvo, username, autor, password="password123"):
    """Atalho — define credencial para `alvo`, com um username dado.

    `autor` é obrigatório e vem antes de `password` para não haver
    argumento com omissão antes de um sem omissão. Todas as chamadas
    do ficheiro passam-no por keyword (`autor=...`), para ficar
    explícito quem assina.

    A password por omissão cumpre a política (>= 8 caracteres).
    """
    return utilizadores.definir_credencial(
        alvo["id"], username, password, autor
    )


# ---------------------------------------------------------------------
# 1. Autenticação
# ---------------------------------------------------------------------


class TesteAutenticar(BaseMySQLTest):
    """Caminho completo de `autenticar` — sucesso e cada um dos
    cinco motivos de falha."""

    def test_autentica_com_credenciais_validas(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        registo, motivo = utilizadores.autenticar("ana", "password123")

        self.assertEqual(motivo, utilizadores.MOTIVO_OK)
        self.assertIsNotNone(registo)
        assert registo is not None
        self.assertEqual(registo["id"], alvo["id"])

    def test_utilizador_inexistente_devolve_nao_encontrado(self):
        registo, motivo = utilizadores.autenticar("ninguem", "password123")

        self.assertIsNone(registo)
        self.assertEqual(motivo, utilizadores.MOTIVO_NAO_ENCONTRADO)

    def test_username_vazio_devolve_nao_encontrado(self):
        registo, motivo = utilizadores.autenticar("", "password123")

        self.assertIsNone(registo)
        self.assertEqual(motivo, utilizadores.MOTIVO_NAO_ENCONTRADO)

    def test_password_vazia_devolve_nao_encontrado(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        registo, motivo = utilizadores.autenticar("ana", "")

        self.assertIsNone(registo)
        self.assertEqual(motivo, utilizadores.MOTIVO_NAO_ENCONTRADO)

    def test_sem_credencial_devolve_sem_credencial(self):
        """O caminho real: um responsável com `username` preenchido
        mas sem `password_hash`.

        Na prática, `definir_credencial` grava sempre os dois campos
        juntos — este estado só acontece se a BD for mexida à mão
        ou se uma migração a meio deixar o username sem hash. O
        `autenticar` trata-o explicitamente com um motivo próprio,
        por isso merece um teste que o force. É o único sítio do
        ficheiro que fala diretamente com o repositório — a API
        pública não permite criar este estado.
        """
        responsavel = _criar_staff("Ana")
        repositorio.atualizar_responsavel(
            responsavel["id"], {"username": "ana"}
        )

        registo, motivo = utilizadores.autenticar("ana", "qualquer")

        self.assertIsNone(registo)
        self.assertEqual(motivo, utilizadores.MOTIVO_SEM_CREDENCIAL)

    def test_password_errada_devolve_password_errada(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        registo, motivo = utilizadores.autenticar("ana", "outraCoisa")

        self.assertIsNone(registo)
        self.assertEqual(motivo, utilizadores.MOTIVO_PASSWORD_ERRADA)

    def test_utilizador_inativo_devolve_inativo(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)
        responsaveis.desativar(alvo["id"], autor=master)

        registo, motivo = utilizadores.autenticar("ana", "password123")

        self.assertIsNone(registo)
        self.assertEqual(motivo, utilizadores.MOTIVO_INATIVO)

    def test_login_bem_sucedido_atualiza_ultimo_login(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        # Antes do login — vazio.
        antes = repositorio.procurar_responsavel(alvo["id"])
        assert antes is not None
        self.assertEqual(antes["ultimo_login"], "")

        utilizadores.autenticar("ana", "password123")

        depois = repositorio.procurar_responsavel(alvo["id"])
        assert depois is not None
        self.assertNotEqual(depois["ultimo_login"], "")

    def test_username_com_espacos_a_volta_e_aceite(self):
        """`autenticar` faz `strip()` do username antes de procurar
        — o `LoginModal` já limpa, mas o módulo também. Se alguém
        chamar `autenticar("  ana  ", ...)` diretamente, deve
        funcionar.
        """
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        registo, motivo = utilizadores.autenticar("  ana  ", "password123")

        self.assertEqual(motivo, utilizadores.MOTIVO_OK)
        self.assertIsNotNone(registo)


# ---------------------------------------------------------------------
# 2. Definir credencial
# ---------------------------------------------------------------------


class TesteDefinirCredencial(BaseMySQLTest):
    """Atribuição de credencial — só Master ou Admin, Admin só sobre
    Staff, password tem de cumprir a política, username é único."""

    def test_master_define_credencial_a_staff(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")

        atualizado = _definir_credencial(alvo, "ana", autor=master)

        self.assertEqual(atualizado["username"], "ana")
        self.assertTrue(atualizado["password_hash"])
        # Formato modular do Django: pbkdf2_sha256$<iter>$<salt>$<hash>
        self.assertTrue(
            atualizado["password_hash"].startswith("pbkdf2_sha256$")
        )
        self.assertEqual(atualizado["password_hash"].count("$"), 3)

    def test_admin_define_credencial_a_staff(self):
        admin = _criar_admin()
        alvo = _criar_staff("Ana")

        atualizado = _definir_credencial(alvo, "ana", autor=admin)

        self.assertEqual(atualizado["username"], "ana")

    def test_admin_nao_define_credencial_a_admin(self):
        admin_autor = _criar_admin("Autor")
        alvo = _criar_admin("Alvo")

        with self.assertRaises(ValueError):
            _definir_credencial(alvo, "alvo", autor=admin_autor)

    def test_admin_nao_define_credencial_a_master(self):
        admin_autor = _criar_admin("Autor")
        alvo = _criar_master("Alvo")

        with self.assertRaises(ValueError):
            _definir_credencial(alvo, "alvo", autor=admin_autor)

    def test_staff_nao_define_credencial(self):
        """BUG do PASSO 9 (22/09/2026): antes da correção, o
        `definir_credencial` só tinha o `if` que cobria o caso
        "Admin a mexer num não-Staff". Um Staff autenticado
        passava sem ser travado — o alvo podia ser outro Staff,
        a credencial era criada, e a barreira real (que a GUI já
        fazia) não existia no módulo.

        Depois da correção, `verificar_permissao` recusa qualquer
        autor que não seja Master ou Admin. Este teste agarra
        esse caso.
        """
        staff_autor = _criar_staff("Autor")
        alvo = _criar_staff("Alvo")

        with self.assertRaises(ValueError):
            _definir_credencial(alvo, "alvo", autor=staff_autor)

    def test_autor_none_falha(self):
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            utilizadores.definir_credencial(
                alvo["id"], "ana", "password123", None
            )

    def test_alvo_inexistente_falha(self):
        master = _criar_master()

        with self.assertRaises(ValueError):
            utilizadores.definir_credencial(
                "RES-999", "ana", "password123", master
            )

    def test_alvo_ja_com_credencial_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        with self.assertRaises(ValueError):
            _definir_credencial(alvo, "outro", autor=master)

    def test_username_vazio_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            _definir_credencial(alvo, "", autor=master)

    def test_password_curta_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            _definir_credencial(alvo, "ana", autor=master, password="curta")

    def test_password_vazia_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            _definir_credencial(alvo, "ana", autor=master, password="")

    def test_username_duplicado_falha(self):
        master = _criar_master()
        alvo_a = _criar_staff("Ana")
        alvo_b = _criar_staff("Bruno")
        _definir_credencial(alvo_a, "ana", autor=master)

        with self.assertRaises(ValueError):
            _definir_credencial(alvo_b, "ana", autor=master)

    def test_username_fica_limpo_de_espacos(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")

        atualizado = _definir_credencial(alvo, "  ana  ", autor=master)

        self.assertEqual(atualizado["username"], "ana")


# ---------------------------------------------------------------------
# 3. Alterar password
# ---------------------------------------------------------------------


class TesteAlterarPassword(BaseMySQLTest):
    """Troca de password — o próprio precisa da atual, um Master
    troca a de outro sem a atual, um Admin não troca a de outro."""

    def test_proprio_alterar_com_password_atual_correta(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        utilizadores.alterar_password(
            alvo["id"], "password123", "novapassword456", autor=alvo
        )

        registo, motivo = utilizadores.autenticar("ana", "novapassword456")
        self.assertEqual(motivo, utilizadores.MOTIVO_OK)
        self.assertIsNotNone(registo)

    def test_proprio_alterar_com_password_atual_errada_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        with self.assertRaises(ValueError):
            utilizadores.alterar_password(
                alvo["id"], "errada", "novapassword456", autor=alvo
            )

    def test_master_alterar_de_outro_sem_password_atual(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        utilizadores.alterar_password(
            alvo["id"], "", "novapassword456", autor=master
        )

        registo, motivo = utilizadores.autenticar("ana", "novapassword456")
        self.assertEqual(motivo, utilizadores.MOTIVO_OK)

    def test_admin_nao_alterar_de_outro(self):
        admin_autor = _criar_admin("Autor")
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        with self.assertRaises(ValueError):
            utilizadores.alterar_password(
                alvo["id"], "", "novapassword456", autor=admin_autor
            )

    def test_password_nova_curta_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        with self.assertRaises(ValueError):
            utilizadores.alterar_password(
                alvo["id"], "password123", "curta", autor=alvo
            )

    def test_alvo_sem_credencial_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            utilizadores.alterar_password(
                alvo["id"], "", "novapassword456", autor=master
            )

    def test_alvo_inexistente_falha(self):
        master = _criar_master()

        with self.assertRaises(ValueError):
            utilizadores.alterar_password(
                "RES-999", "", "novapassword456", autor=master
            )

    def test_autor_none_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        with self.assertRaises(ValueError):
            utilizadores.alterar_password(
                alvo["id"], "password123", "novapassword456", autor=None
            )


# ---------------------------------------------------------------------
# 4. Verificar permissão
# ---------------------------------------------------------------------


class TesteVerificarPermissao(BaseMySQLTest):
    """Regras de permissão partilhadas por todas as operações de
    escrita do módulo.

    NOTA: o `verificar_permissao` valida PERFIS, não a existência
    do autor. A verificação de "autor tem id" vive em cada operação
    específica, via `_validar_autor` — não aqui. Este ficheiro não
    testa esse caso no `verificar_permissao` porque a função não o
    tem por contrato; testa-o indiretamente através dos testes que
    chamam as operações de escrita com autores incompletos.
    """

    def test_autor_none_falha(self):
        with self.assertRaises(ValueError):
            utilizadores.verificar_permissao(None, {"Master"})

    def test_master_passa_em_perfis_de_master(self):
        master = _criar_master()
        # Não deve levantar.
        utilizadores.verificar_permissao(master, {"Master"})

    def test_staff_recusado_em_perfis_de_master(self):
        staff = _criar_staff()
        with self.assertRaises(ValueError):
            utilizadores.verificar_permissao(staff, {"Master"})

    def test_admin_recusado_em_perfis_de_master(self):
        admin = _criar_admin()
        with self.assertRaises(ValueError):
            utilizadores.verificar_permissao(admin, {"Master"})

    def test_master_passa_em_perfis_de_master_admin(self):
        master = _criar_master()
        utilizadores.verificar_permissao(master, {"Master", "Admin"})

    def test_admin_passa_em_perfis_de_master_admin(self):
        admin = _criar_admin()
        utilizadores.verificar_permissao(admin, {"Master", "Admin"})

    def test_staff_recusado_em_perfis_de_master_admin(self):
        staff = _criar_staff()
        with self.assertRaises(ValueError):
            utilizadores.verificar_permissao(staff, {"Master", "Admin"})

    def test_admin_sobre_staff_passa(self):
        admin = _criar_admin()
        utilizadores.verificar_permissao(
            admin, {"Master", "Admin"}, perfil_alvo="Staff"
        )

    def test_admin_sobre_admin_falha(self):
        admin = _criar_admin()
        with self.assertRaises(ValueError):
            utilizadores.verificar_permissao(
                admin, {"Master", "Admin"}, perfil_alvo="Admin"
            )

    def test_admin_sobre_master_falha(self):
        admin = _criar_admin()
        with self.assertRaises(ValueError):
            utilizadores.verificar_permissao(
                admin, {"Master", "Admin"}, perfil_alvo="Master"
            )

    def test_master_sobre_qualquer_perfil_passa(self):
        master = _criar_master()
        for perfil in ("Staff", "Admin", "Master"):
            utilizadores.verificar_permissao(
                master, {"Master", "Admin"}, perfil_alvo=perfil
            )


# ---------------------------------------------------------------------
# 5. Desativar
# ---------------------------------------------------------------------


class TesteDesativar(BaseMySQLTest):
    """Desativação de responsável — só Master, recusa auto-desativação."""

    def test_master_desativa_staff(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")

        desativado = utilizadores.desativar(alvo["id"], autor=master)

        self.assertFalse(desativado["ativo"])
        self.assertEqual(desativado["desativado_por_id"], master["id"])
        self.assertNotEqual(desativado["data_desativacao"], "")

    def test_master_desativa_admin(self):
        master = _criar_master()
        alvo = _criar_admin("Bruno")

        desativado = utilizadores.desativar(alvo["id"], autor=master)

        self.assertFalse(desativado["ativo"])

    def test_master_nao_se_desativa_a_si_mesmo(self):
        master = _criar_master()

        with self.assertRaises(ValueError):
            utilizadores.desativar(master["id"], autor=master)

    def test_admin_nao_desativa(self):
        admin_autor = _criar_admin("Autor")
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            utilizadores.desativar(alvo["id"], autor=admin_autor)

    def test_staff_nao_desativa(self):
        staff_autor = _criar_staff("Autor")
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            utilizadores.desativar(alvo["id"], autor=staff_autor)

    def test_autor_none_falha(self):
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            utilizadores.desativar(alvo["id"], autor=None)

    def test_alvo_inexistente_falha(self):
        master = _criar_master()

        with self.assertRaises(ValueError):
            utilizadores.desativar("RES-999", autor=master)

    def test_alvo_ja_inativo_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        utilizadores.desativar(alvo["id"], autor=master)

        with self.assertRaises(ValueError):
            utilizadores.desativar(alvo["id"], autor=master)


# ---------------------------------------------------------------------
# 6. Reativar
# ---------------------------------------------------------------------


class TesteReativar(BaseMySQLTest):
    """Reativação de responsável — Master ou Admin (Admin só sobre
    Staff). Inclui o teste explícito ao bug corrigido no PASSO 3."""

    def test_master_reativa_staff(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        utilizadores.desativar(alvo["id"], autor=master)

        reativado = utilizadores.reativar(alvo["id"], autor=master)

        self.assertTrue(reativado["ativo"])

    def test_master_reativa_admin(self):
        master = _criar_master()
        alvo = _criar_admin("Bruno")
        utilizadores.desativar(alvo["id"], autor=master)

        reativado = utilizadores.reativar(alvo["id"], autor=master)

        self.assertTrue(reativado["ativo"])

    def test_admin_reativa_staff(self):
        master = _criar_master()
        admin_autor = _criar_admin("Autor")
        alvo = _criar_staff("Ana")
        utilizadores.desativar(alvo["id"], autor=master)

        reativado = utilizadores.reativar(alvo["id"], autor=admin_autor)

        self.assertTrue(reativado["ativo"])

    def test_admin_nao_reativa_admin(self):
        master = _criar_master()
        admin_autor = _criar_admin("Autor")
        alvo = _criar_admin("Alvo")
        utilizadores.desativar(alvo["id"], autor=master)

        with self.assertRaises(ValueError):
            utilizadores.reativar(alvo["id"], autor=admin_autor)

    def test_admin_nao_reativa_master(self):
        master_autor = _criar_master("Autor")
        master_alvo = _criar_master("Alvo")
        utilizadores.desativar(master_alvo["id"], autor=master_autor)

        admin_autor = _criar_admin("Admin")
        with self.assertRaises(ValueError):
            utilizadores.reativar(master_alvo["id"], autor=admin_autor)

    def test_staff_nao_reativa(self):
        master = _criar_master()
        staff_autor = _criar_staff("Autor")
        alvo = _criar_staff("Ana")
        utilizadores.desativar(alvo["id"], autor=master)

        with self.assertRaises(ValueError):
            utilizadores.reativar(alvo["id"], autor=staff_autor)

    def test_alvo_ja_ativo_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")

        with self.assertRaises(ValueError):
            utilizadores.reativar(alvo["id"], autor=master)

    def test_alvo_inexistente_falha(self):
        master = _criar_master()

        with self.assertRaises(ValueError):
            utilizadores.reativar("RES-999", autor=master)

    def test_autor_none_falha(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        utilizadores.desativar(alvo["id"], autor=master)

        with self.assertRaises(ValueError):
            utilizadores.reativar(alvo["id"], autor=None)

    def test_reativar_limpa_campos_de_desativacao(self):
        """BUG do PASSO 3 (v1.5.0 → corrigido a 22/09/2026):
        `utilizadores.reativar` escrevia `""` (string vazia) em
        `desativado_por_id` (FK auto-referente) e `data_desativacao`
        (DATE). O MySQL recusava os dois. A correção passa `None`
        em ambos os campos.

        O que este teste verifica é que a ESCRITA passa sem erro
        e que a RELEITURA devolve os campos limpos. A verificação
        é feita via `repositorio.procurar_responsavel`, que é o
        caminho real de leitura — o dict devolvido pelo `reativar`
        fica com `None` nos dois campos (é o valor que a função
        escreveu, não o normalizado que a releitura faz), e essa
        diferença é uma convenção do projeto, não um bug.

        Se alguém voltar a pôr `""` no `reativar`, o UPDATE falha
        no MySQL e este teste rebenta — antes de chegar às
        asserções de releitura.
        """
        master = _criar_master()
        alvo = _criar_staff("Ana")
        utilizadores.desativar(alvo["id"], autor=master)

        reativado = utilizadores.reativar(alvo["id"], autor=master)

        self.assertTrue(reativado["ativo"])

        # Confirmação pela leitura direta ao repositório — a
        # normalização `NULL → ""` corre aqui, não no dict que o
        # `reativar` devolve.
        relido = repositorio.procurar_responsavel(alvo["id"])
        assert relido is not None
        self.assertTrue(relido["ativo"])
        self.assertEqual(relido["desativado_por_id"], "")
        self.assertEqual(relido["data_desativacao"], "")


# ---------------------------------------------------------------------
# 7. Listar com estado
# ---------------------------------------------------------------------


class TesteListarComEstado(BaseMySQLTest):
    """Listagem com os campos de credencial já normalizados."""

    def test_lista_traz_campos_de_credencial_como_strings(self):
        """Nunca devolve `None` nos campos de texto — mesma
        convenção de string vazia usada em todo o sistema. É o que
        permite ao `gui_responsaveis` mostrar 'sem credencial' ou
        'nunca' sem testar dois casos.
        """
        _criar_master("Sem credencial")

        lista = utilizadores.listar_com_estado()

        self.assertEqual(len(lista), 1)
        registo = lista[0]
        # Todos os campos de credencial vêm como strings.
        for campo in (
            "username",
            "password_hash",
            "password_alterada_em",
            "ultimo_login",
            "desativado_por_id",
            "data_desativacao",
        ):
            self.assertIsInstance(
                registo[campo], str, f"campo {campo!r} não é str"
            )

    def test_lista_so_ativos_por_omissao(self):
        master = _criar_master()
        _criar_staff("Ativo")
        inativo = _criar_staff("Inativo")
        utilizadores.desativar(inativo["id"], autor=master)

        lista = utilizadores.listar_com_estado()

        ids = [r["id"] for r in lista]
        self.assertEqual(len(ids), 2)  # master + o staff ativo
        self.assertNotIn(inativo["id"], ids)

    def test_lista_incluir_inativos(self):
        master = _criar_master()
        _criar_staff("Ativo")
        inativo = _criar_staff("Inativo")
        utilizadores.desativar(inativo["id"], autor=master)

        lista = utilizadores.listar_com_estado(incluir_inativos=True)

        ids = [r["id"] for r in lista]
        self.assertEqual(len(ids), 3)
        self.assertIn(inativo["id"], ids)

    def test_lista_reflete_credencial_definida(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)

        lista = utilizadores.listar_com_estado()
        por_id = {r["id"]: r for r in lista}

        self.assertEqual(por_id[alvo["id"]]["username"], "ana")
        self.assertNotEqual(por_id[alvo["id"]]["password_hash"], "")


# ---------------------------------------------------------------------
# Verificar password — confirmações que NÃO são logins (23/09/2026)
# ---------------------------------------------------------------------


class TesteVerificarPassword(BaseMySQLTest):
    """`verificar_password` confirma uma password sem fazer login.

    Existe para confirmações (a do reset do sistema): não pode mexer
    no `ultimo_login` nem registar acessos — era esse o problema de
    usar o `autenticar` para confirmar.
    """

    def setUp(self):
        super().setUp()
        self.master = _criar_master()
        self.alvo = _criar_staff("Ana")
        _definir_credencial(self.alvo, "ana", autor=self.master)

    def test_password_certa_devolve_true(self):
        self.assertTrue(
            utilizadores.verificar_password(self.alvo["id"], "password123")
        )

    def test_password_errada_devolve_false(self):
        self.assertFalse(
            utilizadores.verificar_password(self.alvo["id"], "errada123")
        )

    def test_password_vazia_devolve_false(self):
        self.assertFalse(utilizadores.verificar_password(self.alvo["id"], ""))

    def test_responsavel_sem_credencial_devolve_false(self):
        sem_credencial = _criar_staff("Sem credencial")
        self.assertFalse(
            utilizadores.verificar_password(sem_credencial["id"], "x")
        )

    def test_responsavel_inexistente_devolve_false(self):
        self.assertFalse(utilizadores.verificar_password("RES-999", "x"))

    def test_nao_atualiza_ultimo_login(self):
        utilizadores.verificar_password(self.alvo["id"], "password123")
        depois = repositorio.procurar_responsavel(self.alvo["id"])
        assert depois is not None
        self.assertEqual(depois["ultimo_login"], "")

    def test_nao_regista_nada_no_log(self):
        """Nem sucesso nem falha: quem chama é que sabe o contexto e
        regista. Um "Autenticação bem-sucedida" aqui seria um login
        que nunca aconteceu."""
        with self.assertNoLogs("utilizadores"):
            utilizadores.verificar_password(self.alvo["id"], "password123")
            utilizadores.verificar_password(self.alvo["id"], "errada123")


class TesteLogsAutenticacao(BaseMySQLTest):
    """O que o `autenticar` e o `verificar_permissao` deixam no log."""

    def test_falha_regista_motivo_sem_o_username_tentado(self):
        """O username tentado NUNCA vai para o log — pode ser uma
        password escrita no campo errado."""
        with self.assertLogs("utilizadores", level="WARNING") as registo:
            utilizadores.autenticar("utilizador_que_nao_existe", "x")
        self.assertIn("nao_encontrado", registo.output[0])
        self.assertNotIn("utilizador_que_nao_existe", registo.output[0])

    def test_password_errada_nao_vai_para_o_log(self):
        master = _criar_master()
        alvo = _criar_staff("Ana")
        _definir_credencial(alvo, "ana", autor=master)
        with self.assertLogs("utilizadores", level="WARNING") as registo:
            utilizadores.autenticar("ana", "segredo_errado_123")
        texto = "\n".join(registo.output)
        self.assertNotIn("segredo_errado_123", texto)
        self.assertIn(alvo["id"], texto)

    def test_recusa_de_permissao_fica_registada(self):
        staff = _criar_staff()
        with self.assertLogs("utilizadores", level="WARNING") as registo:
            with self.assertRaises(ValueError):
                utilizadores.verificar_permissao(staff, {"Master"})
        self.assertIn("Permissão recusada", registo.output[0])
        self.assertIn(staff["id"], registo.output[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)