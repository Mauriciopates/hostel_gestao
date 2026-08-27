"""Gestão das propriedades — os edifícios que agrupam unidades.

Existe como entidade própria (decisão 12) para o nome e a morada
viverem num único sítio: repetidos em cada unidade, uma correção
obrigaria a alterar treze registos e um ficaria por corrigir.

Não acede a ficheiros nem à interface: recebe a estrutura de dados,
devolve resultado e sinaliza erro com `raise ValueError`. Quem carrega e
grava é o `main.py`, através do repositório.
"""

import repositorio

# prefixo antes da numeração da propriedade
PREFIXO = "PRO"


def criar(dados, nome, morada=""):
    """Cria uma propriedade e acrescenta-a à estrutura de dados.

    Devolve o registo criado. Não grava: a gravação é decidida pelo
    `main.py`, o que permite reunir várias operações numa só escrita e
    não deixar dados inconsistentes quando uma delas falha.
    """
    nome = nome.strip()

    if not nome:
        raise ValueError("O nome da propriedade é obrigatório.")

    propriedade = {
        "id": repositorio.proximo_id(PREFIXO),
        "nome": nome,
        "morada": morada.strip(),
        "ativo": True,
    }

    dados["propriedades"].append(propriedade)
    return propriedade


def procurar(dados, propriedade_id):
    """Devolve a propriedade com o identificador indicado, ou None.

    A ausência não é erro: quem chama é que decide se a falta de
    resultado impede a operação.

    Não filtra inativas — procura, não decide.
    """

    for p in dados["propriedades"]:
        if p["id"] == propriedade_id:
            return p

    return None


def listar(dados, incluir_inativas=False):
    """Devolve as propriedades ativas, ou todas se pedido.

    Devolve uma lista nova para que alterações a essa lista não afetem
    a estrutura de dados.
    """

    resultado = []

    for p in dados["propriedades"]:
        if incluir_inativas or p["ativo"]:
            resultado.append(p)

    return resultado


def atualizar(dados, propriedade_id, nome=None, morada=None):
    """Altera o nome ou a morada de uma propriedade existente.

    Um parâmetro a None significa não alterar; uma cadeia vazia
    significa apagar o conteúdo. A morada pode ficar vazia, o nome não.
    """

    p = procurar(dados, propriedade_id)

    if p is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    if nome is not None:
        nome = nome.strip()
        if not nome:
            raise ValueError("O nome da propriedade é obrigatório.")
        p["nome"] = nome

    if morada is not None:
        morada = morada.strip()
        p["morada"] = morada

    return p


def desativar(dados, propriedade_id, forcar=False):
    """Marca a propriedade como inativa, sem a eliminar.

    Uma propriedade com unidades associadas não pode desaparecer: os
    contratos históricos referem essas unidades (decisão 8). Desativar
    mantém o registo e tira-o das listagens de escolha.

    Recusa por omissão se existirem unidades ativas dependentes
    (decisão de 27/08, item 9) — passa forcar=True para desativar
    mesmo assim, conscientemente. A verificação vive aqui, não só no
    cli.py, para que qualquer interface futura (a GUI da Fase 2, por
    exemplo) herde esta proteção sem ter de a repetir.
    """

    p = procurar(dados, propriedade_id)

    if p is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    if not p["ativo"]:
        raise ValueError(f"A propriedade {propriedade_id} já está inativa.")

    if not forcar:
        unidades_ativas = [
            u for u in dados["unidades"]
            if u["propriedade_id"] == propriedade_id and u["ativo"]
        ]

        if unidades_ativas:
            raise ValueError(
                f"A propriedade {propriedade_id} tem "
                f"{len(unidades_ativas)} unidade(s) ativa(s) — "
                f"forcar=True para desativar mesmo assim."
            )

    p["ativo"] = False
    return p


def reativar(dados, propriedade_id):
    """Repõe uma propriedade desativada como ativa.

    Existe porque a desativação por engano seria irreversível sem ela.
    É a inversa exata da `desativar`.

    """

    p = procurar(dados, propriedade_id)

    if p is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    if p["ativo"]:
        raise ValueError(f"A propriedade {propriedade_id} já está ativa.")

    p["ativo"] = True 
    return p
