"""Gestão das propriedades — os edifícios que agrupam unidades.

Existe como entidade própria (decisão 12) para o nome e a morada
viverem num único sítio: repetidos em cada unidade, uma correção
obrigaria a alterar treze registos e um ficaria por corrigir.

MIGRADO para MySQL (Fase 2, pivot): já não recebe nem devolve a
estrutura `dados` em memória — fala diretamente com o `repositorio`,
que faz o INSERT/SELECT/UPDATE na base de dados. Continua a não
aceder a ficheiros nem à base de dados diretamente (só através do
repositorio), e continua a sinalizar erro com `raise ValueError`.
"""

import repositorio

# prefixo antes da numeração da propriedade
PREFIXO = "PRO"


def criar(nome, morada=""):
    """Cria uma propriedade e grava-a imediatamente na base de dados.

    Devolve o registo criado. Ao contrário da versão antiga (em
    memória), aqui já não há gravação separada: cada função grava a
    sua própria operação assim que a validação passa.
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

    repositorio.inserir_propriedade(propriedade)
    return propriedade


def procurar(propriedade_id):
    """Devolve a propriedade com o identificador indicado, ou None.

    A ausência não é erro: quem chama é que decide se a falta de
    resultado impede a operação.

    Não filtra inativas — procura, não decide.
    """
    return repositorio.procurar_propriedade(propriedade_id)


def listar(incluir_inativas=False):
    """Devolve as propriedades ativas, ou todas se pedido."""
    return repositorio.listar_propriedades(incluir_inativas=incluir_inativas)


def atualizar(propriedade_id, nome=None, morada=None):
    """Altera o nome ou a morada de uma propriedade existente.

    Um parâmetro a None significa não alterar; uma cadeia vazia
    significa apagar o conteúdo. A morada pode ficar vazia, o nome não.
    """
    propriedade = procurar(propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    campos = {}

    if nome is not None:
        nome = nome.strip()
        if not nome:
            raise ValueError("O nome da propriedade é obrigatório.")
        campos["nome"] = nome

    if morada is not None:
        campos["morada"] = morada.strip()

    if campos:
        repositorio.atualizar_propriedade(propriedade_id, campos)
        propriedade.update(campos)

    return propriedade


def desativar(propriedade_id, forcar=False):
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
    propriedade = procurar(propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    if not propriedade["ativo"]:
        raise ValueError(f"A propriedade {propriedade_id} já está inativa.")

    if not forcar:
        total_ativas = repositorio.contar_unidades_ativas(propriedade_id)

        if total_ativas:
            raise ValueError(
                f"A propriedade {propriedade_id} tem "
                f"{total_ativas} unidade(s) ativa(s) — "
                f"forcar=True para desativar mesmo assim."
            )

    repositorio.atualizar_propriedade(propriedade_id, {"ativo": False})
    propriedade["ativo"] = False
    return propriedade


def reativar(propriedade_id):
    """Repõe uma propriedade desativada como ativa.

    Existe porque a desativação por engano seria irreversível sem ela.
    É a inversa exata da `desativar`.
    """
    propriedade = procurar(propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    if propriedade["ativo"]:
        raise ValueError(f"A propriedade {propriedade_id} já está ativa.")

    repositorio.atualizar_propriedade(propriedade_id, {"ativo": True})
    propriedade["ativo"] = True
    return propriedade
