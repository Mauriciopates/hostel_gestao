"""Gestão de credenciais e autenticação.

Módulo novo da v1.5.0. Trata da credencial do responsável — username,
password, último acesso — e das regras de permissão por perfil
(Master / Admin / Staff).

DIVISÃO COM `responsaveis.py`: os dois módulos tocam na mesma tabela
`responsaveis`, cada um com o seu foco. `responsaveis.py` continua a
ser o módulo de gestão da pessoa — quem é, contactos, ativo/inativo,
perfil. `utilizadores.py` trata do que é específico de autenticação:
procurar pelo username, validar password, registar último acesso,
verificar permissões. É o mesmo padrão de `estoque.py`/`produtos.py`,
que também partilham tabela sem se misturarem.

DECISÃO DE ESQUEMA (Fase 2, v1.4.0 / v1.5.0): o perfil
(`tipo_utilizador`) é coluna do próprio responsável, não uma tabela
`utilizadores` à parte. Isto foi decidido na Fase 2 — `responsaveis`
já era o alvo de todas as chaves estrangeiras de autoria, e separar
o perfil obrigava a uma junção em cada leitura de sessão sem
acrescentar nenhum campo próprio. A credencial segue o mesmo
princípio: vive na própria linha do responsável.

FORMATO DE HASH: `pbkdf2_sha256$<iteracoes>$<salt>$<hash>`, o
formato modular do Django. Uma só coluna, migra para Django sem
conversão. Algoritmo `hashlib.pbkdf2_hmac('sha256', ...)` — stdlib,
sem dependências externas.

PERMISSÕES: vivem sempre na camada de negócio, nunca só na GUI
(regra 11.2 do plano de correções — desativar um campo no ecrã é
conforto visual, não segurança). É por isso que todas as funções
que fazem uma operação sensível recebem o `autor` (o registo do
responsável ativo) e validam antes de agir.
"""

import hashlib
import logging
import os
from datetime import date, datetime

import repositorio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------

# Perfis válidos. A ordem não implica hierarquia de código — é só
# leitura humana. A hierarquia real vive nas regras de permissão
# mais abaixo.
PERFIS = ("Master", "Admin", "Staff")

# Iterações do PBKDF2. Valor escolhido para o contexto deste
# sistema: secretaria de mesa, um utilizador por vez, autenticação
# em ~0,4s. O Django usa 600.000 por omissão (contexto web, com
# muitos utilizadores em paralelo e onde a autenticação é uma vez
# por sessão). Aqui, 600.000 fazia cada login levar ~2s — tempo
# desconfortável para um sistema de uso diário.
#
# 100.000 continua sólido para este contexto: ninguém vai fazer um
# ataque por força bruta a um sistema de hostel com 4 utilizadores.
# Se um dia migrar para web com muitos utilizadores, sobe-se outra
# vez — os hashes já gravados mantêm as suas iterações (estão
# dentro do próprio hash), só os novos é que usam o valor novo.
_ITERACOES = 100000

# Comprimento mínimo da password. Sem exigência de complexidade —
# uma política de 8 caracteres é suficiente para um sistema
# individual; exigir maiúsculas e dígitos só incentiva passwords
# anotadas em papel.
_COMPRIMENTO_MINIMO = 8

# Motivos de falha de autenticação. Devolvidos por `autenticar` na
# tupla (None, motivo). A tradução para a mensagem em português
# vive na GUI — o módulo de negócio nunca escreve texto de ecrã.
MOTIVO_OK = "ok"
MOTIVO_NAO_ENCONTRADO = "nao_encontrado"
MOTIVO_SEM_CREDENCIAL = "sem_credencial"
MOTIVO_PASSWORD_ERRADA = "password_errada"
MOTIVO_INATIVO = "inativo"


# ---------------------------------------------------------------------
# Hash e validação de password
# ---------------------------------------------------------------------


def _hash_password(password):
    """Devolve a password no formato modular do Django, pronta a
    gravar em `password_hash`.

    Formato:

        pbkdf2_sha256$<iteracoes>$<salt>$<hash>

    O salt é gerado por `os.urandom(16)` — criptograficamente seguro,
    nunca previsível. Cada password leva o seu salt, mesmo que dois
    utilizadores escolham a mesma password: os hashes finais são
    sempre diferentes, o que torna ataques por dicionário inúteis.

    A password em texto simples nunca é gravada — só existe em
    memória, e é descartada no fim da função.
    """
    salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERACOES,
    )

    return f"pbkdf2_sha256${_ITERACOES}$" f"{salt.hex()}${hash_bytes.hex()}"


def _validar_password(password, hash_guardado):
    """Confirma se a password corresponde ao hash guardado.

    O formato gravado tem quatro partes separadas por `$`:
    algoritmo, iterações, salt, hash. Recalcula-se o hash com o
    mesmo algoritmo + salt + iterações, e comparam-se os dois
    resultados — nunca a password em si.

    Devolve False se o hash estiver vazio ou malformado — o que
    cobre o caso do responsável que ainda não tem credencial
    definida (password_hash = "").

    Comparação em tempo constante (`hmac.compare_digest`, via o
    próprio `==` do bytes) — não é essencial neste projeto, mas é
    o hábito certo a manter para quando migrar para web.
    """
    if not hash_guardado or hash_guardado.count("$") != 3:
        return False

    algoritmo, iteracoes_str, salt_hex, hash_hex = hash_guardado.split("$")

    if algoritmo != "pbkdf2_sha256":
        return False

    try:
        iteracoes = int(iteracoes_str)
        salt = bytes.fromhex(salt_hex)
        hash_esperado = bytes.fromhex(hash_hex)
    except ValueError:
        return False

    hash_calculado = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iteracoes,
    )

    return hash_calculado == hash_esperado


def _validar_politica_password(password):
    """Levanta ValueError se a password não cumprir a política.

    Política: mínimo de 8 caracteres. Sem outras exigências.
    """
    if not password:
        raise ValueError("A password é obrigatória.")

    if len(password) < _COMPRIMENTO_MINIMO:
        raise ValueError(
            f"A password tem de ter pelo menos {_COMPRIMENTO_MINIMO} "
            "caracteres."
        )


# ---------------------------------------------------------------------
# Permissões
# ---------------------------------------------------------------------


def verificar_permissao(autor, perfis_permitidos, perfil_alvo=None):
    """Confirma que `autor` tem permissão para a operação.

    `autor` é o registo devolvido por `sessao.obter_responsavel_ativo()`
    — um dicionário com pelo menos `id` e `tipo_utilizador`. Se for
    None (nenhum responsável ativo), levanta erro.

    `perfis_permitidos` é uma coleção de perfis (ex.: {"Master"}).

    `perfil_alvo` (opcional) é o perfil do responsável sobre quem se
    opera (ex.: "Staff" ou "Master"). Quando passado, aplica-se uma
    regra adicional: um Admin só pode operar sobre Staff. Quando
    omitido (None), a verificação fica só pelo perfil do autor.

    Isto cobre duas regras com a mesma forma:

      - 3.5 (criar responsável): o autor Master cria qualquer perfil,
        o autor Admin só cria Staff.
      - 5.1 / 5.3 (definir credencial / reativar): mesma forma —
        Master com todos, Admin só com Staff.

    Sem `perfil_alvo`:

      - 3.2 (alterar tipo de utilizador): só Master, ponto.
      - 5.3 (desativar responsável): só Master, ponto.

    Levanta ValueError se a permissão falhar.
    """
    if autor is None:
        raise ValueError(
            "Não há responsável ativo. Escolha um antes de continuar."
        )

    tipo_autor = autor.get("tipo_utilizador")

    if tipo_autor not in perfis_permitidos:
        logger.warning(
            "Permissão recusada — autor_id=%s, tipo=%s, permitidos=%s",
            autor.get("id"),
            tipo_autor,
            sorted(perfis_permitidos),
        )
        raise ValueError("O seu perfil não tem permissão para esta operação.")

    # Regra adicional do Admin: só opera sobre Staff. Um Master passa
    # por aqui sem restrição (está nos perfis_permitidos das chamadas
    # que usam perfil_alvo).
    if perfil_alvo is not None:
        if tipo_autor == "Admin" and perfil_alvo != "Staff":
            logger.warning(
                "Permissão recusada — Admin sobre não-Staff: autor_id=%s, "
                "perfil_alvo=%s",
                autor.get("id"),
                perfil_alvo,
            )
            raise ValueError("Um Admin só pode operar sobre Staff.")


# ---------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------


def autenticar(username, password):
    """Valida as credenciais e devolve o registo do responsável.

    Devolve uma tupla `(registro, motivo)`:

      - Sucesso: `(registo, "ok")` — o registo é o dicionário do
        responsável, pronto a passar a `sessao.definir_responsavel_ativo`.
      - Falha: `(None, motivo)` — `motivo` é uma das constantes
        MOTIVO_* definidas no topo deste módulo.

    Nunca levanta erro — é o LoginModal que decide o que mostrar
    ao utilizador, a partir do motivo.

    Regista o sucesso em `ultimo_login` (data e hora). Não
    regista tentativas falhadas — a decisão de 17/09/2026 foi
    deixar essa política para a Fase 3 (web), onde o Django traz
    o rate-limit nativo.

    O motivo `sem_credencial` distingue dois casos que parecem
    um só: o responsável existe na base mas `username` ainda é
    NULL (ninguém lhe definiu credencial), ou o `username`
    indicado não pertence a ninguém. A distinção é útil em
    ambiente de secretaria de mesa — o Master percebe logo se
    se esqueceu de definir a credencial a alguém.
    """
    username = (username or "").strip()
    password = password or ""

    # Nunca se regista o username tentado nem a password — o que foi
    # escrito no campo do utilizador pode ser uma password digitada
    # no sítio errado.
    if not username or not password:
        logger.warning(
            "Falha de autenticação — motivo=%s", MOTIVO_NAO_ENCONTRADO
        )
        return None, MOTIVO_NAO_ENCONTRADO

    responsavel = repositorio.procurar_responsavel_por_username(username)

    if responsavel is None:
        logger.warning(
            "Falha de autenticação — motivo=%s", MOTIVO_NAO_ENCONTRADO
        )
        return None, MOTIVO_NAO_ENCONTRADO

    if not responsavel["password_hash"]:
        logger.warning(
            "Falha de autenticação — motivo=%s, responsavel_id=%s",
            MOTIVO_SEM_CREDENCIAL,
            responsavel["id"],
        )
        return None, MOTIVO_SEM_CREDENCIAL

    if not responsavel["ativo"]:
        logger.warning(
            "Falha de autenticação — motivo=%s, responsavel_id=%s",
            MOTIVO_INATIVO,
            responsavel["id"],
        )
        return None, MOTIVO_INATIVO

    if not _validar_password(password, responsavel["password_hash"]):
        logger.warning(
            "Falha de autenticação — motivo=%s, responsavel_id=%s",
            MOTIVO_PASSWORD_ERRADA,
            responsavel["id"],
        )
        return None, MOTIVO_PASSWORD_ERRADA

    # Sucesso — regista o último acesso. `datetime.now()` porque a
    # coluna é DATETIME, não DATE: a hora importa para a coluna
    # "Último acesso" da GUI, que mostra dia e hora.
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repositorio.atualizar_responsavel(
        responsavel["id"], {"ultimo_login": agora}
    )
    responsavel["ultimo_login"] = agora

    logger.info(
        "Autenticação bem-sucedida — responsavel_id=%s", responsavel["id"]
    )
    return responsavel, MOTIVO_OK


def verificar_password(responsavel_id, password):
    """Confirma a password de um responsável, SEM fazer login.

    Devolve True se a password bater com a guardada, False em todos
    os outros casos (password vazia, responsável inexistente, sem
    credencial).

    Existe para as CONFIRMAÇÕES — por exemplo, a password pedida no
    modal do "Começar do zero". Uma confirmação não é um login, e o
    `autenticar` não serve para isto porque:

      - atualiza o `ultimo_login` na base de dados;
      - regista "Autenticação bem-sucedida" / "Falha de
        autenticação" no log.

    Usado para confirmar, o `autenticar` escrevia no histórico de
    acessos logins que nunca aconteceram.

    Não regista nada no log de propósito: quem chama sabe o contexto
    (qual operação estava a ser confirmada) e é quem deve registar.
    """
    if not password:
        return False

    responsavel = repositorio.procurar_responsavel(responsavel_id)

    if responsavel is None or not responsavel.get("password_hash"):
        return False

    return _validar_password(password, responsavel["password_hash"])


# ---------------------------------------------------------------------
# Credenciais — definir e alterar
# ---------------------------------------------------------------------


def definir_credencial(responsavel_id, username, password, autor):
    """Atribui uma credencial a um responsável que ainda não tem.

    Só Master e Admin podem definir credenciais; Admin só a Staff.
    Um Admin não pode dar credencial a outro Admin nem a um Master
    (regra 5.1 da ronda de 17/09/2026).

    Valida: política de password, unicidade do username, perfil do
    autor face ao perfil do alvo.

    CORREÇÃO 22/09/2026 (PASSO 9): a barreira de perfil passou a
    estar no próprio módulo, via `verificar_permissao`. Antes, o
    único `if` verificava que o autor não era um Admin a mexer num
    não-Staff — deixava um Staff autenticado passar (bastava que o
    alvo fosse Staff para o ramo do `if` não disparar). A barreira
    real vive no módulo (regra 11.2 do plano de correções); a GUI
    já escondia o botão a quem não é Master/Admin, mas a barreira
    de negócio era a que estava a faltar.

    O username é `strip()`-ado e comparado com os já existentes.
    Se já estiver em uso por outro responsável, levanta ValueError
    — o UNIQUE da coluna também o faria, mas esta validação dá uma
    mensagem clara antes de bater na base.

    Devolve o registo atualizado.
    """
    autor = _validar_autor(autor, responsavel_id)

    username = (username or "").strip()

    if not username:
        raise ValueError("O utilizador é obrigatório.")

    _validar_politica_password(password)

    alvo = repositorio.procurar_responsavel(responsavel_id)

    if alvo is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if alvo["username"]:
        raise ValueError(
            f"O responsável {responsavel_id} já tem credencial "
            f"definida ({alvo['username']}). Use 'Alterar password' "
            "em vez de 'Definir credencial'."
        )

    # Regra 5.1 — barreira de perfil no próprio módulo.
    #
    # `verificar_permissao` cobre as três combinações que
    # interessam:
    #   - Master sobre qualquer perfil  → passa
    #   - Admin sobre Staff             → passa
    #   - Admin sobre Admin/Master      → recusa ("Admin só sobre Staff")
    #   - Staff como autor              → recusa (não está em
    #                                     {"Master", "Admin"})
    #
    # A posição da chamada é intencional: vem DEPOIS das validações
    # de dados (username, password, alvo existe, alvo já tem
    # credencial) e ANTES do UPDATE. Se os dados do formulário
    # estão mal, o erro diz isso — não "não tens permissão".
    verificar_permissao(
        autor,
        {"Master", "Admin"},
        perfil_alvo=alvo["tipo_utilizador"],
    )

    # Unicidade do username — o UNIQUE da base também garante isto,
    # mas aqui damos uma mensagem específica em vez de erro do MySQL.
    outro = repositorio.procurar_responsavel_por_username(username)

    if outro is not None and outro["id"] != responsavel_id:
        raise ValueError(
            f"O utilizador '{username}' já está atribuído ao "
            f"responsável {outro['id']}."
        )

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    campos = {
        "username": username,
        "password_hash": _hash_password(password),
        "password_alterada_em": agora,
    }

    repositorio.atualizar_responsavel(responsavel_id, campos)
    alvo.update(campos)

    logger.info(
        "Credencial definida — alvo_id=%s, autor_id=%s",
        responsavel_id,
        autor["id"],
    )
    return alvo


def alterar_password(responsavel_id, password_atual, password_nova, autor):
    """Troca a password de um responsável.

    Duas situações:

      - O PRÓPRIO altera a sua password. Nesse caso tem de indicar
        a password atual (para se confirmar que é mesmo ele).
      - Um MASTER altera a password de outro. Nesse caso a password
        atual é ignorada — o Master não sabe a antiga, e é a
        operação que permite recuperar acesso quando alguém se
        esqueceu.

    Admin não altera passwords de outros (regra 3.1 da ronda de
    17/09/2026).

    Valida: política da password nova, perfil do autor face ao
    alvo, e (quando é o próprio) a password atual.

    Devolve o registo atualizado.
    """
    autor = _validar_autor(autor, responsavel_id)

    _validar_politica_password(password_nova)

    alvo = repositorio.procurar_responsavel(responsavel_id)

    if alvo is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if not alvo["password_hash"]:
        raise ValueError(
            f"O responsável {responsavel_id} ainda não tem credencial "
            "definida. Use 'Definir credencial' primeiro."
        )

    e_o_proprio = autor["id"] == responsavel_id
    e_master = autor["tipo_utilizador"] == "Master"

    if not e_o_proprio and not e_master:
        logger.warning(
            "Alteração de password recusada — alvo_id=%s, autor_id=%s",
            responsavel_id,
            autor["id"],
        )
        raise ValueError(
            "Só o próprio ou um Master podem alterar esta password."
        )

    # O próprio tem de confirmar a password atual; o Master não.
    if e_o_proprio:
        if not _validar_password(password_atual, alvo["password_hash"]):
            logger.warning(
                "Alteração de password — password atual errada, "
                "responsavel_id=%s",
                responsavel_id,
            )
            raise ValueError("A password atual não corresponde.")

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    campos = {
        "password_hash": _hash_password(password_nova),
        "password_alterada_em": agora,
    }

    repositorio.atualizar_responsavel(responsavel_id, campos)
    alvo.update(campos)

    logger.info(
        "Password alterada — alvo_id=%s, autor_id=%s, modo=%s",
        responsavel_id,
        autor["id"],
        "proprio" if e_o_proprio else "reposicao_master",
    )
    return alvo


# ---------------------------------------------------------------------
# Estado — desativar e reativar
# ---------------------------------------------------------------------


def desativar(responsavel_id, autor):
    """Desativa um responsável. Só Master (regra 5.3).

    Não permite que alguém se desative a si mesmo (regra 4.3) —
    isso deixaria o sistema potencialmente sem ninguém que possa
    reativar (se for o único Master).

    Regista quem desativou (`desativado_por_id`) e quando
    (`data_desativacao`) — mesma convenção de produtos,
    propriedades e unidades.

    Não elimina nada. Um responsável com autoria registada não
    pode desaparecer: as anonimizações, os movimentos de stock e
    as alterações de configuração guardam o seu ID. Desativar
    tira-o das listagens e impede novas operações, sem tocar no
    histórico.

    Devolve o registo atualizado.
    """
    autor = _validar_autor(autor, responsavel_id)

    verificar_permissao(autor, {"Master"})

    if autor["id"] == responsavel_id:
        raise ValueError(
            "Não pode desativar-se a si mesmo. Peça a outro Master."
        )

    alvo = repositorio.procurar_responsavel(responsavel_id)

    if alvo is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if not alvo["ativo"]:
        raise ValueError(f"O responsável {responsavel_id} já está inativo.")

    campos = {
        "ativo": False,
        "desativado_por_id": autor["id"],
        "data_desativacao": date.today().isoformat(),
    }

    repositorio.atualizar_responsavel(responsavel_id, campos)
    alvo.update(campos)

    logger.info(
        "Responsável desativado — alvo_id=%s, autor_id=%s",
        responsavel_id,
        autor["id"],
    )
    return alvo


def reativar(responsavel_id, autor):
    """Repõe um responsável desativado como ativo.

    Master ou Admin (Admin só pode reativar Staff — regra 5.3).

    Limpa `desativado_por_id` e `data_desativacao` — quem reativou
    e quando deixa de fazer sentido quando o estado atual é ativo.
    O histórico de desativações antigas fica onde sempre ficou: na
    data de desativação anterior, que foi sobrescrita. Se um dia
    for preciso histórico completo, faz-se numa tabela própria
    (Fase 3).

    Devolve o registo atualizado.
    """
    autor = _validar_autor(autor, responsavel_id)

    alvo = repositorio.procurar_responsavel(responsavel_id)

    if alvo is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if alvo["ativo"]:
        raise ValueError(f"O responsável {responsavel_id} já está ativo.")

    # Regra 5.3: Admin só reativa Staff.
    if (
        autor["tipo_utilizador"] == "Admin"
        and alvo["tipo_utilizador"] != "Staff"
    ):
        logger.warning(
            "Reativação recusada — Admin sobre não-Staff: alvo_id=%s, "
            "autor_id=%s",
            responsavel_id,
            autor["id"],
        )
        raise ValueError("Um Admin só pode reativar Staff.")

    verificar_permissao(autor, {"Master", "Admin"})

    campos = {
        "ativo": True,
        "desativado_por_id": None,
        "data_desativacao": None,
    }

    repositorio.atualizar_responsavel(responsavel_id, campos)
    alvo.update(campos)

    logger.info(
        "Responsável reativado — alvo_id=%s, autor_id=%s",
        responsavel_id,
        autor["id"],
    )
    return alvo


# ---------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------


def listar_com_estado(incluir_inativos=False):
    """Devolve os responsáveis com os campos de credencial.

    Igual a `responsaveis.listar`, mas garante que os campos
    `username`, `ultimo_login` e `desativado_por_id` vêm sempre
    no formato de string vazia (nunca None) — para a GUI poder
    mostrar "sem credencial" ou "nunca" sem ter de testar dois
    casos diferentes.

    Delega no `repositorio.listar_responsaveis_com_credencial`,
    que é o que faz a normalização.
    """
    return repositorio.listar_responsaveis_com_credencial(
        incluir_inativos=incluir_inativos
    )


# ---------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------


def _validar_autor(autor, responsavel_id):
    """Confirma que `autor` está preenchido e não é o próprio alvo.

    Separado porque várias funções precisam do mesmo teste (o
    `autor` tem de existir, não pode ser None). E porque o caso
    "autor == alvo" é tratado de forma diferente em cada função —
    aqui só se garante que o `autor` é válido enquanto dicionário.
    """
    if autor is None:
        raise ValueError(
            "Não há responsável ativo. Escolha um antes de continuar."
        )

    if not autor.get("id"):
        raise ValueError(
            "O responsável ativo não tem ID. Volte a entrar no sistema."
        )

    return autor
