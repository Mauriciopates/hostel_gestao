"""Gestão dos responsáveis — as pessoas que operam o sistema.

Antecipado para a Fase 1 sem credenciais (decisão 10): existe para
atribuir autoria a operações — anonimizações (decisão 8),
requisições de material (decisão 9) e alterações de configuração.
Login, palavra-passe e permissões chegam na Fase 2, no
`utilizadores.py`; este módulo não os prepara nem os antecipa.

Entidade independente do `clientes.py`: um responsável não é um
cliente com outro papel. Não partilham campos nem estrutura.

MIGRAÇÃO MySQL (Fase 2): tal como `propriedades.py` e `unidades.py`,
este módulo já não recebe nem devolve `dados` — fala diretamente com
o MySQL através do `repositorio.py` (inserir_responsavel,
procurar_responsavel, listar_responsaveis, atualizar_responsavel).
Não acede a ficheiros nem à interface: devolve resultado e sinaliza
erro com `raise ValueError`.
"""

import repositorio

PREFIXO = "RES"

# Perfis de acesso (Fase 2, v1.4.0). A coluna `tipo_utilizador` já
# existia na tabela (ALTER TABLE de uma entrega anterior); esta é a
# primeira vez que o próprio módulo passa a conhecer e a validar os
# valores permitidos, em vez de deixar o ENUM da base ser a única
# barreira. A ordem aqui não implica hierarquia de código nenhuma —
# é só a ordem "do mais para o menos amplo" para leitura humana; a
# lógica de permissões por perfil (próximo passo do plano) é que vai
# dar significado real a cada um.
TIPOS_UTILIZADOR = ("Master", "Admin", "Staff")


def criar(nome, contacto="", tipo_utilizador="Staff"):
    """Cria um responsável e grava-o imediatamente na base de dados.

    O nome é obrigatório: sem ele, a autoria que este módulo
    existe para registar não identificaria ninguém. O contacto é
    opcional e não tem validação de formato — pode ser telefone,
    email ou extensão interna, e a decisão 11 já dispensa a
    validação de formato de telefone.

    `tipo_utilizador` por omissão é "Staff", o mesmo valor por
    omissão da coluna na base — criar um responsável sem indicar o
    perfil continua a dar o resultado mais restrito, não o mais
    permissivo. Tem de ser um de TIPOS_UTILIZADOR; qualquer outro
    valor é erro. Não há bootstrap automático do primeiro "Master"
    aqui — combinado que o primeiro Master de cada instalação é
    promovido com um UPDATE manual na base, feito uma única vez.

    Não marca o registo como incompleto: `Responsavel` não tem
    esse campo (ver modelos.py). A listagem de incompletos da
    decisão 11 é dos dados de hóspedes, comunicados às
    autoridades — não se estende a quem opera o sistema.

    Devolve o registo criado. Grava de imediato via repositório —
    mesma convenção de propriedades.criar, unidades.criar e
    clientes.criar, agora todos em MySQL.
    """
    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do responsável é obrigatório.")

    if tipo_utilizador not in TIPOS_UTILIZADOR:
        raise ValueError(
            "Tipo de utilizador inválido. Tem de ser um de: "
            + ", ".join(TIPOS_UTILIZADOR)
        )

    responsavel = {
        "id": repositorio.proximo_id(PREFIXO),
        "nome": nome,
        "contacto": contacto.strip(),
        "ativo": True,
        "tipo_utilizador": tipo_utilizador,
    }

    repositorio.inserir_responsavel(responsavel)
    return responsavel


def procurar(responsavel_id):
    """Devolve o responsável com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos — procura, não decide (mesma
    convenção de propriedades.procurar, unidades.procurar e
    clientes.procurar).

    É por não filtrar que a `reativar` consegue chegar a um
    responsável desativado, e que uma anonimização antiga
    continua a poder mostrar o nome de quem a fez mesmo depois de
    essa pessoa sair da operação.
    """
    return repositorio.procurar_responsavel(responsavel_id)


def listar(incluir_inativos=False):
    """Devolve os responsáveis, ativos ou todos se pedido.

    Não tem filtros de conteúdo: o responsável só tem nome e
    contacto, e nenhum deles é categoria por onde valha a pena
    filtrar. O parâmetro de estado chega para as duas listagens
    que a interface precisa — quem se escolhe hoje e quem já
    passou pela operação.
    """
    return repositorio.listar_responsaveis(incluir_inativos=incluir_inativos)


def atualizar(responsavel_id, nome=None, contacto=None):
    """Altera o nome ou o contacto de um responsável existente.

    Um parâmetro a None significa não alterar; "" significa
    limpar o conteúdo (mesma convenção de propriedades.atualizar,
    unidades.atualizar e clientes.atualizar). O contacto pode
    ficar vazio, o nome não — é obrigatório, tal como em criar().

    Não altera 'ativo': a desativação e a reativação têm funções
    próprias, com as suas verificações. Deixar mudar o estado por
    aqui abriria um segundo caminho sem essas verificações.

    Devolve o registo atualizado, já com os campos novos aplicados
    localmente (evita um SELECT extra a seguir ao UPDATE).
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


def desativar(responsavel_id):
    """Marca o responsável como inativo, sem o eliminar.

    Um responsável com autoria registada não pode desaparecer: as
    anonimizações, os movimentos de stock e as alterações de
    configuração guardam o seu identificador (decisão 8, decisão
    9). Eliminar o registo deixaria esses IDs sem tradução — o
    histórico ficaria a apontar para ninguém.

    Desativar tira-o das listagens de escolha e impede novas
    operações em seu nome (ver validar_autoria), sem tocar nas
    que já estão gravadas. É a saída de quem deixa a operação,
    não um apagamento.

    Não é anonimização: os dados do responsável mantêm-se
    intactos, ao contrário do que a clientes.anonimizar faz ao
    titular. O responsável não é hóspede — a decisão 8 e o prazo
    de conservação de hóspedes não se lhe aplicam.
    """

    responsavel = procurar(responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if not responsavel["ativo"]:
        raise ValueError(
            f"O responsável {responsavel_id} já está inativo."
        )

    repositorio.atualizar_responsavel(responsavel_id, {"ativo": False})
    responsavel["ativo"] = False
    return responsavel


def reativar(responsavel_id):
    """Repõe um responsável desativado como ativo.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar` — e, ao contrário da
    clientes.reativar, não tem exceção nenhuma a tratar: não há
    operação irreversível neste módulo que a impeça.

    Reativar devolve ao responsável a possibilidade de novas
    operações em seu nome (ver validar_autoria). Não altera nada
    do que ficou gravado enquanto esteve inativo — nunca houve
    nada para alterar, porque a validação de autoria recusa antes
    de qualquer registo ser criado.
    """

    responsavel = procurar(responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if responsavel["ativo"]:
        raise ValueError(
            f"O responsável {responsavel_id} já está ativo."
        )

    repositorio.atualizar_responsavel(responsavel_id, {"ativo": True})
    responsavel["ativo"] = True
    return responsavel


def alterar_tipo_utilizador(responsavel_id, tipo_utilizador,
                             tipo_utilizador_autor):
    """Muda o perfil de acesso de um responsável existente.

    Função própria, à parte de `atualizar`, pela mesma razão que
    `desativar`/`reativar` têm as suas: mudar o perfil de acesso não
    é como corrigir um nome ou um contacto, tem a sua própria
    verificação (o valor tem de ser um de TIPOS_UTILIZADOR) e um
    segundo caminho sem ela seria uma porta lateral.

    `tipo_utilizador_autor` é o tipo_utilizador de quem está a pedir
    esta alteração — normalmente `sessao.tipo_utilizador_ativo()`,
    lido por quem chama. Este módulo não importa `sessao` (seria
    import circular: `sessao.py` já importa `responsaveis`), por
    isso a verificação de "quem" fica aqui, mas o valor tem de vir
    de fora (item (c) da Fase 2, 15/09/2026, corrigido no mesmo
    dia depois de um teste do aluno mostrar que só desativar o
    combo na GUI não chegava — um responsável sem ser Master
    conseguiu gravar a alteração à mesma). Só um "Master" pode
    mudar o tipo de outro responsável; qualquer outro valor
    (incluindo None, sem sessão ativa) é recusado.

    Devolve o registo atualizado, já com o novo tipo aplicado
    localmente — mesma convenção de `atualizar`, `desativar` e
    `reativar`.
    """

    if tipo_utilizador_autor != "Master":
        raise ValueError(
            "Só um responsável do tipo 'Master' pode alterar o tipo "
            "de utilizador de outro responsável."
        )

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

    repositorio.atualizar_responsavel(
        responsavel_id, {"tipo_utilizador": tipo_utilizador}
    )
    responsavel["tipo_utilizador"] = tipo_utilizador
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
    anonimização de um cliente (decisão 8), as requisições e os
    movimentos de material (decisão 9) e as alterações de
    configuração. Recusa antes de o registo ser criado, nunca
    depois — é isso que garante que um responsável inativo nunca
    fica associado a nada de novo.

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