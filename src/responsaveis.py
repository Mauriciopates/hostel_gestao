"""Gestão dos responsáveis — as pessoas que operam o sistema.

Antecipado para a Fase 1 sem credenciais (decisão 10): existe para
atribuir autoria a operações — anonimizações (decisão 8),
requisições de material (decisão 9) e alterações de configuração.
Login, palavra-passe e permissões chegam na Fase 2, no
`utilizadores.py`; este módulo não os prepara nem os antecipa.

Entidade independente do `clientes.py`: um responsável não é um
cliente com outro papel. Não partilham campos nem estrutura.

Não acede a ficheiros nem à interface: recebe a estrutura de dados,
devolve resultado e sinaliza erro com `raise ValueError`. Quem
carrega e grava é o `main.py`, através do repositório.
"""

import repositorio

PREFIXO = "RES"


def criar(dados, nome, contacto=""):
    """Cria um responsável e acrescenta-o à estrutura de dados.

    O nome é obrigatório: sem ele, a autoria que este módulo
    existe para registar não identificaria ninguém. O contacto é
    opcional e não tem validação de formato — pode ser telefone,
    email ou extensão interna, e a decisão 11 já dispensa a
    validação de formato de telefone.

    Não marca o registo como incompleto: `Responsavel` não tem
    esse campo (ver modelos.py). A listagem de incompletos da
    decisão 11 é dos dados de hóspedes, comunicados às
    autoridades — não se estende a quem opera o sistema.

    Devolve o registo criado. Não grava: a gravação é decidida
    pelo `main.py` (mesma convenção de propriedades.criar,
    unidades.criar e clientes.criar).
    """
    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do responsável é obrigatório.")

    responsavel = {
        "id": repositorio.proximo_id(PREFIXO),
        "nome": nome,
        "contacto": contacto.strip(),
        "ativo": True,
    }

    dados["responsaveis"].append(responsavel)
    return responsavel

def procurar(dados, responsavel_id):
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

    for r in dados["responsaveis"]:
        if r["id"] == responsavel_id:
            return r

    return None

def listar(dados, incluir_inativos=False):
    """Devolve os responsáveis, ativos ou todos se pedido.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção de propriedades.listar,
    unidades.listar e clientes.listar).

    Não tem filtros de conteúdo: o responsável só tem nome e
    contacto, e nenhum deles é categoria por onde valha a pena
    filtrar. O parâmetro de estado chega para as duas listagens
    que a interface precisa — quem se escolhe hoje e quem já
    passou pela operação.
    """

    resultado = []

    for r in dados["responsaveis"]:
        if incluir_inativos or r["ativo"]:
            resultado.append(r)

    return resultado

def atualizar(dados, responsavel_id, nome=None, contacto=None):
    """Altera o nome ou o contacto de um responsável existente.

    Um parâmetro a None significa não alterar; "" significa
    limpar o conteúdo (mesma convenção de propriedades.atualizar,
    unidades.atualizar e clientes.atualizar). O contacto pode
    ficar vazio, o nome não — é obrigatório, tal como em criar().

    Não altera 'ativo': a desativação e a reativação têm funções
    próprias, com as suas verificações. Deixar mudar o estado por
    aqui abriria um segundo caminho sem essas verificações.

    Devolve o registo atualizado.
    """

    responsavel = procurar(dados, responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome do responsável é obrigatório.")

        responsavel["nome"] = nome

    if contacto is not None:
        responsavel["contacto"] = contacto.strip()

    return responsavel

def desativar(dados, responsavel_id):
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

    responsavel = procurar(dados, responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if not responsavel["ativo"]:
        raise ValueError(
            f"O responsável {responsavel_id} já está inativo."
        )

    responsavel["ativo"] = False
    return responsavel

def reativar(dados, responsavel_id):
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

    responsavel = procurar(dados, responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if responsavel["ativo"]:
        raise ValueError(
            f"O responsável {responsavel_id} já está ativo."
        )

    responsavel["ativo"] = True
    return responsavel

def validar_autoria(dados, responsavel_id):
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

    responsavel = procurar(dados, responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    if not responsavel["ativo"]:
        raise ValueError(
            f"O responsável {responsavel_id} está inativo e não pode "
            f"assumir a autoria da operação."
        )

    return responsavel