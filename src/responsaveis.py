"""Gestão dos responsáveis — as pessoas que operam o sistema.

Entidade independente do `clientes.py`: um responsável não é um
cliente com outro papel. Não partilham campos nem estrutura.

A credencial (login, palavra-passe) vive no `utilizadores.py`, não
aqui. Este módulo continua a ser o da gestão da PESSOA — nome,
contacto, perfil, ativa/inativa. O `utilizadores.py` trata do que
é específico de autenticação. Os dois tocam na mesma tabela, cada
um com o seu foco — mesmo padrão de `estoque.py`/`produtos.py`.

MIGRAÇÃO MySQL (Fase 2): tal como `propriedades.py` e `unidades.py`,
este módulo já não recebe nem devolve `dados` — fala diretamente com
o MySQL através do `repositorio.py`. Não acede a ficheiros nem à
interface: devolve resultado e sinaliza erro com `raise ValueError`.

ALTERAÇÕES v1.5.0 (ronda de 17/09/2026):

  - `criar` ganha `autor` (opcional). Fecha a pendência 11.4 — só
    Master cria Admin/Master, Admin cria Staff, Staff não cria
    ninguém. Se `autor` for None, a validação é ignorada (para o
    CLI continuar a funcionar até ser adaptado).
  - `desativar` e `reativar` ganham `autor`. Delegam a lógica ao
    `utilizadores.py`, que tem as regras.
  - `alterar_tipo_utilizador` passa a receber `autor` (o dict do
    responsável ativo) em vez de `tipo_utilizador_autor` (só o
    tipo em texto). Acrescenta a regra 3.4 — Masters imunes a
    rebaixamento por outros.
"""

import logging

import repositorio

logger = logging.getLogger(__name__)

PREFIXO = "RES"

# Perfis de acesso (Fase 2, v1.4.0). A ordem aqui não implica
# hierarquia de código nenhuma — é só a ordem "do mais para o
# menos amplo" para leitura humana.
TIPOS_UTILIZADOR = ("Master", "Admin", "Staff")


def criar(nome, contacto="", tipo_utilizador="Staff", autor=None):
    """Cria um responsável e grava-o imediatamente na base de dados.

    Regras de permissão (pendência 11.4, fechada na v1.5.0):

      - Só Master cria Admin ou Master.
      - Admin cria Staff.
      - Staff não cria ninguém.

    O `autor` é o dict do responsável ativo — o mesmo que
    `sessao.obter_responsavel_ativo()` devolve. Aceita None para
    não quebrar chamadas antigas (por exemplo, do CLI em testes
    ainda não adaptados) — nesse caso a permissão não é validada.
    Quando o chamador passa o autor, a validação é feita.

    O nome é obrigatório. O contacto é opcional e não tem
    validação de formato. `tipo_utilizador` por omissão é "Staff",
    o mesmo valor por omissão da coluna na base.

    Não marca o registo como incompleto — `Responsavel` não tem
    esse campo. A listagem de incompletos é dos dados de hóspedes.

    Devolve o registo criado. Grava de imediato via repositório —
    mesma convenção de propriedades.criar, unidades.criar e
    clientes.criar.
    """
    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do responsável é obrigatório.")

    if tipo_utilizador not in TIPOS_UTILIZADOR:
        raise ValueError(
            "Tipo de utilizador inválido. Tem de ser um de: "
            + ", ".join(TIPOS_UTILIZADOR)
        )

    if autor is not None:
        import utilizadores

        utilizadores.verificar_permissao(
            autor,
            {"Master", "Admin"},
            perfil_alvo=tipo_utilizador,
        )

    responsavel = {
        "id": repositorio.proximo_id(PREFIXO),
        "nome": nome,
        "contacto": contacto.strip(),
        "ativo": True,
        "tipo_utilizador": tipo_utilizador,
    }

    repositorio.inserir_responsavel(responsavel)
    logger.info(
        "Responsável criado — id=%s, tipo=%s, autor_id=%s",
        responsavel["id"],
        tipo_utilizador,
        autor.get("id") if autor is not None else None,
    )
    return responsavel


def procurar(responsavel_id):
    """Devolve o responsável com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos — procura, não decide.

    É por não filtrar que a `reativar` consegue chegar a um
    responsável desativado, e que uma anonimização antiga
    continua a poder mostrar o nome de quem a fez mesmo depois de
    essa pessoa sair da operação.
    """
    return repositorio.procurar_responsavel(responsavel_id)


def listar(incluir_inativos=False):
    """Devolve os responsáveis, ativos ou todos se pedido."""
    return repositorio.listar_responsaveis(incluir_inativos=incluir_inativos)


def atualizar(responsavel_id, nome=None, contacto=None):
    """Altera o nome ou o contacto de um responsável existente.

    Um parâmetro a None significa não alterar; "" significa
    limpar o conteúdo. O contacto pode ficar vazio, o nome não.

    Não altera 'ativo': a desativação e a reativação têm funções
    próprias, com as suas verificações. Deixar mudar o estado por
    aqui abriria um segundo caminho sem essas verificações.

    Não altera `tipo_utilizador` também — isso é a
    `alterar_tipo_utilizador`, com as suas próprias regras.

    Devolve o registo atualizado.
    """
    responsavel = procurar(responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    campos = {}

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome do responsável é obrigatório.")

        campos["nome"] = nome

    if contacto is not None:
        campos["contacto"] = contacto.strip()

    if campos:
        repositorio.atualizar_responsavel(responsavel_id, campos)
        responsavel.update(campos)

    return responsavel


def desativar(responsavel_id, autor):
    """Marca o responsável como inativo, sem o eliminar.

    Só Master (regra 5.3). A lógica vive em
    `utilizadores.desativar`; esta função é uma porta de entrada
    com a mesma assinatura de antes, mais o `autor`.

    Devolve o registo atualizado.
    """
    import utilizadores

    return utilizadores.desativar(responsavel_id, autor)


def reativar(responsavel_id, autor):
    """Repõe um responsável desativado como ativo.

    Master ou Admin (Admin só sobre Staff) — regra 5.3. A lógica
    vive em `utilizadores.reativar`; esta função é uma porta de
    entrada com a mesma assinatura de antes, mais o `autor`.

    Devolve o registo atualizado.
    """
    import utilizadores

    return utilizadores.reativar(responsavel_id, autor)


def alterar_tipo_utilizador(responsavel_id, tipo_utilizador, autor):
    """Muda o perfil de acesso de um responsável existente.

    Regras (ronda de 17/09/2026, v1.5.0):

      - Só um Master pode alterar o tipo de utilizador de outro
        (regra 3.2).
      - Um Master NÃO pode rebaixar outro Master (regra 3.4). Um
        Master só se desce a si mesmo, se quiser.

    O `autor` é o dict do responsável ativo — o mesmo que
    `sessao.obter_responsavel_ativo()` devolve. Aceitar o dict em
    vez de dois argumentos separados uniformiza com o
    `utilizadores.py`: todas as funções que validam permissão
    recebem o autor como dict.

    Devolve o registo atualizado.
    """
    import utilizadores

    utilizadores.verificar_permissao(autor, {"Master"})

    if tipo_utilizador not in TIPOS_UTILIZADOR:
        raise ValueError(
            "Tipo de utilizador inválido. Tem de ser um de: "
            + ", ".join(TIPOS_UTILIZADOR)
        )

    responsavel = procurar(responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if responsavel["tipo_utilizador"] == tipo_utilizador:
        raise ValueError(
            f"O responsável {responsavel_id} já tem o tipo "
            f"'{tipo_utilizador}'."
        )

    # Regra 3.4: Masters imunes a rebaixamento por outros.
    if (
        responsavel["tipo_utilizador"] == "Master"
        and autor["id"] != responsavel_id
    ):
        logger.warning(
            "Tentativa de rebaixar outro Master recusada — alvo_id=%s, "
            "autor_id=%s",
            responsavel_id,
            autor["id"],
        )
        raise ValueError(
            "Um Master não pode rebaixar outro Master. Só o próprio "
            "pode descer-se a si mesmo."
        )

    tipo_anterior = responsavel["tipo_utilizador"]

    repositorio.atualizar_responsavel(
        responsavel_id, {"tipo_utilizador": tipo_utilizador}
    )
    responsavel["tipo_utilizador"] = tipo_utilizador
    logger.info(
        "Tipo de utilizador alterado — alvo_id=%s, %s → %s, autor_id=%s",
        responsavel_id,
        tipo_anterior,
        tipo_utilizador,
        autor["id"],
    )
    return responsavel


def validar_autoria(responsavel_id):
    """Confirma que o responsável indicado pode assumir autoria.

    Exige mais do que a `procurar`: o responsável tem de existir
    E estar ativo. É a função que autoriza o presente, enquanto a
    `procurar` serve para ler o passado — um responsável inativo
    continua a ser encontrado pela `procurar`, para que o
    histórico permaneça legível, mas deixa de poder assinar
    operações novas.

    Chamada por quem regista uma operação com autoria: a
    anonimização de um cliente, as requisições e os movimentos de
    material, as alterações de configuração. Recusa antes de o
    registo ser criado, nunca depois.

    Devolve o registo do responsável, para que quem chama possa
    usar o nome sem repetir a procura.
    """

    if responsavel_id is None:
        raise ValueError("O responsável é obrigatório.")

    responsavel_id = responsavel_id.strip()

    if not responsavel_id:
        raise ValueError("O responsável é obrigatório.")

    responsavel = procurar(responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if not responsavel["ativo"]:
        raise ValueError(
            f"O responsável {responsavel_id} está inativo e não pode "
            f"assumir a autoria da operação."
        )

    return responsavel
