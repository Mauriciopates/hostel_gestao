"""Gestão das unidades, quartos e lugares — a estrutura física do
alojamento.

Unidade é o que se contrata (tem preço e regime); quarto é a
divisão; lugar é a cama ou posição contratável dentro dele
(decisão 17). Só `em_manutencao` persiste como estado — livre,
ocupado e reservado calculam-se a partir dos contratos, para uma
data (decisão 3).

MIGRAÇÃO MySQL (Fase 2): as três entidades deste módulo falam
diretamente com o MySQL através do `repositorio` (unidades, quartos,
lugares). Desde a migração de `contratos.py`, nenhuma função deste
módulo recebe `dados` — `desativar`, `estado`, `_estado_mensal`,
`_estado_airbnb` e `quarto_privativo_ocupado` já não precisam de ler
`dados["ocupacoes"]` diretamente: leem `repositorio.listar_ocupacoes`
(mesmo módulo que `contratos.py` usa), o que continua a evitar o
import circular (`contratos.py` já importa `unidades.py`).
"""

from decimal import Decimal
from datetime import timedelta

import repositorio
import validacoes
import propriedades

PREFIXO = "UNI"
PREFIXO_QUARTO = "QRT"
PREFIXO_LUGAR = "LUG"


def criar(
    propriedade_id,
    nome,
    tipo,
    preco_base,
    preco_epoca_alta,
    multa_check_in_tardio,
    epoca_alta_ativa=False,
):
    """Criação das unidades, faz a validações de existencia
    antes de criar a unidade"""

    propriedade = propriedades.procurar(propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome da unidade é obrigatório.")

    if tipo not in validacoes.TIPOS_UNIDADE:
        raise ValueError(f"Tipo de unidade desconhecido: {tipo}")

    precos = (
        ("preço base", preco_base),
        ("preço de época alta", preco_epoca_alta),
        ("multa de check-in tardio", multa_check_in_tardio),
    )

    for nome_preco, valor in precos:
        if valor is None:
            raise ValueError(f"{nome_preco} é obrigatório.")

        if not isinstance(valor, Decimal):
            raise ValueError(
                f"{nome_preco} tem de ser Decimal, não"
                f" {type(valor).__name__}."
            )

        if valor < 0:
            raise ValueError(f"{nome_preco} não pode ser negativo: {valor}.")

    unidade = {
        "id": repositorio.proximo_id(PREFIXO),
        "propriedade_id": propriedade_id,
        "nome": nome,
        "tipo": tipo,
        "preco_base": preco_base,
        "preco_epoca_alta": preco_epoca_alta,
        "multa_check_in_tardio": multa_check_in_tardio,
        "epoca_alta_ativa": epoca_alta_ativa,
        "em_manutencao": False,
        "ativo": True,
    }

    repositorio.inserir_unidade(unidade)
    return unidade


def procurar(unidade_id):
    """Devolve a unidade com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação — é o que a `criar` faz com a propriedade, ao
    transformar o None num ValueError.

    Não filtra inativas: uma unidade desativada continua a ser
    encontrada, senão a `reativar` não teria como lhe chegar.
    """
    return repositorio.procurar_unidade(unidade_id)


def listar(incluir_inativas=False, propriedade_id=None, tipo=None):
    """Devolve as unidades, filtráveis por propriedade e por tipo."""
    return repositorio.listar_unidades(
        incluir_inativas=incluir_inativas,
        propriedade_id=propriedade_id,
        tipo=tipo,
    )


def atualizar(
    unidade_id,
    nome=None,
    preco_base=None,
    preco_epoca_alta=None,
    multa_check_in_tardio=None,
    epoca_alta_ativa=None,
):
    """Altera o nome, os preços e o indicador de época alta de uma
    unidade.

    Um parâmetro a None significa não alterar (mesma convenção de
    `propriedades.atualizar`). O nome não pode ficar vazio, mesma regra
    de `atualizar_quarto`. Os três preços não podem ficar vazios
    nem negativos: são obrigatórios no cadastro (decisão 6) e essa
    obrigatoriedade mantém-se na alteração.

    O tipo e a propriedade não se alteram aqui: o tipo é restrição
    rígida sobre as ocupações e mudar de propriedade não corresponde
    a nenhuma operação real do negócio. O estado de manutenção tem
    funções próprias.
    """

    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    campos = {}

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome da unidade é obrigatório.")

        campos["nome"] = nome

    precos = (
        ("preço base", "preco_base", preco_base),
        ("preço de época alta", "preco_epoca_alta", preco_epoca_alta),
        (
            "multa de check-in tardio",
            "multa_check_in_tardio",
            multa_check_in_tardio,
        ),
    )

    for nome_preco, campo, valor in precos:
        if valor is None:
            continue

        if not isinstance(valor, Decimal):
            raise ValueError(
                f"{nome_preco} tem de ser Decimal, não"
                f" {type(valor).__name__}."
            )

        if valor < 0:
            raise ValueError(f"{nome_preco} não pode ser negativo: {valor}.")

        campos[campo] = valor

    if epoca_alta_ativa is not None:
        campos["epoca_alta_ativa"] = epoca_alta_ativa

    if campos:
        repositorio.atualizar_unidade(unidade_id, campos)
        unidade.update(campos)

    return unidade


def desativar(unidade_id, forcar=False):
    """Marca a unidade como inativa, sem a eliminar.

    Uma unidade com ocupações associadas não pode desaparecer: os
    contratos históricos referem-se a ela (decisão 8). Desativar
    mantém o registo e tira-o das listagens de escolha, sem apagar
    o histórico.

    Recusa por omissão se existirem ocupações ativas dependentes
    (decisão de 27/08, item 9) — passa forcar=True para desativar
    mesmo assim, conscientemente. Consulta
    `repositorio.listar_ocupacoes` em vez de chamar `contratos.py`,
    para evitar import circular (`contratos.py` já importa
    `unidades.py`) — mesmo padrão usado em `_estado_mensal`/
    `_estado_airbnb`, abaixo.
    """

    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if not unidade["ativo"]:
        raise ValueError(f"A unidade {unidade_id} já está inativa.")

    if not forcar:
        ocupacoes_ativas = repositorio.listar_ocupacoes(unidade_id=unidade_id)

        if ocupacoes_ativas:
            raise ValueError(
                f"A unidade {unidade_id} tem "
                f"{len(ocupacoes_ativas)} ocupação(ões) ativa(s) — "
                f"forcar=True para desativar mesmo assim."
            )

    repositorio.atualizar_unidade(unidade_id, {"ativo": False})
    unidade["ativo"] = False
    return unidade


def reativar(unidade_id):
    """Repõe uma unidade desativada como ativa.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar`.
    """

    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["ativo"]:
        raise ValueError(f"A unidade {unidade_id} já está ativa.")

    repositorio.atualizar_unidade(unidade_id, {"ativo": True})
    unidade["ativo"] = True
    return unidade


def marcar_manutencao(unidade_id):
    """Coloca a unidade em manutenção, tirando-a da oferta.

    'em_manutencao' é a única forma de estado que persiste na
    unidade — livre, ocupado e reservado calculam-se a partir dos
    contratos para uma data (decisão 3). Colocar em manutenção é
    decisão da gestão, não algo que se infira dos contratos.
    """

    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["em_manutencao"]:
        raise ValueError(f"A unidade {unidade_id} já está em manutenção.")

    repositorio.atualizar_unidade(unidade_id, {"em_manutencao": True})
    unidade["em_manutencao"] = True
    return unidade


def desmarcar_manutencao(unidade_id):
    """Repõe a unidade na oferta, saindo da manutenção.

    Inversa exata da `marcar_manutencao`.
    """

    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if not unidade["em_manutencao"]:
        raise ValueError(f"A unidade {unidade_id} não está em manutenção.")

    repositorio.atualizar_unidade(unidade_id, {"em_manutencao": False})
    unidade["em_manutencao"] = False
    return unidade


# Inicio do código para Quartos


def criar_quarto(unidade_id, nome, privativo=False, limpeza_incluida=False):
    """Cria um quarto dentro de uma unidade existente.

    Devolve o registo criado.
    """

    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do quarto é obrigatório.")

    quarto = {
        "id": repositorio.proximo_id(PREFIXO_QUARTO),
        "unidade_id": unidade_id,
        "nome": nome,
        "privativo": privativo,
        "limpeza_incluida": limpeza_incluida,
        "ativo": True,
    }

    repositorio.inserir_quarto(quarto)
    return quarto


def procurar_quarto(quarto_id):
    """Devolve o quarto com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos — procura, não decide (mesma
    convenção de `procurar`, unidade acima).
    """
    return repositorio.procurar_quarto(quarto_id)


def listar_quartos(incluir_inativas=False, unidade_id=None):
    """Devolve os quartos, filtráveis por unidade."""
    return repositorio.listar_quartos(
        incluir_inativas=incluir_inativas, unidade_id=unidade_id
    )


def atualizar_quarto(quarto_id, nome=None, privativo=None, limpeza_incluida=None):
    """Altera o nome ou os indicadores de um quarto existente.

    Um parâmetro a None significa não alterar (mesma convenção de
    `atualizar`, unidade acima). O nome não pode ficar vazio; os
    dois indicadores são independentes entre si (decisão 17).
    """

    quarto = procurar_quarto(quarto_id)

    if quarto is None:
        raise ValueError(f"O quarto {quarto_id} não existe.")

    campos = {}

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome do quarto é obrigatório.")

        campos["nome"] = nome

    if privativo is not None:
        campos["privativo"] = privativo

    if limpeza_incluida is not None:
        campos["limpeza_incluida"] = limpeza_incluida

    if campos:
        repositorio.atualizar_quarto(quarto_id, campos)
        quarto.update(campos)

    return quarto


def desativar_quarto(quarto_id):
    """Marca o quarto como inativo, sem o eliminar.

    Um quarto com lugares associados não pode desaparecer: mantém
    o registo e tira-o das listagens de escolha, sem apagar o
    histórico (decisão 8).
    """

    quarto = procurar_quarto(quarto_id)

    if quarto is None:
        raise ValueError(f"O quarto {quarto_id} não existe.")

    if not quarto["ativo"]:
        raise ValueError(f"O quarto {quarto_id} já está inativo.")

    repositorio.atualizar_quarto(quarto_id, {"ativo": False})
    quarto["ativo"] = False
    return quarto


def reativar_quarto(quarto_id):
    """Repõe um quarto desativado como ativo.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar_quarto`.
    """

    quarto = procurar_quarto(quarto_id)

    if quarto is None:
        raise ValueError(f"O quarto {quarto_id} não existe.")

    if quarto["ativo"]:
        raise ValueError(f"O quarto {quarto_id} já está ativo.")

    repositorio.atualizar_quarto(quarto_id, {"ativo": True})
    quarto["ativo"] = True
    return quarto


def criar_lugar(quarto_id, nome, capacidade=1):
    """Cria um lugar dentro de um quarto existente.

    Devolve o registo criado.
    """

    quarto = procurar_quarto(quarto_id)

    if quarto is None:
        raise ValueError(f"O quarto {quarto_id} não existe.")

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do lugar é obrigatório.")

    validacoes.validar_capacidade_lugar(capacidade)

    lugar = {
        "id": repositorio.proximo_id(PREFIXO_LUGAR),
        "quarto_id": quarto_id,
        "nome": nome,
        "capacidade": capacidade,
        "ativo": True,
    }

    repositorio.inserir_lugar(lugar)
    return lugar


def procurar_lugar(lugar_id):
    """Devolve o lugar com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos — procura, não decide (mesma
    convenção de `procurar` e `procurar_quarto`, acima).
    """
    return repositorio.procurar_lugar(lugar_id)


def listar_lugares(incluir_inativas=False, quarto_id=None):
    """Devolve os lugares, filtráveis por quarto."""
    return repositorio.listar_lugares(
        incluir_inativas=incluir_inativas, quarto_id=quarto_id
    )


def atualizar_lugar(lugar_id, nome=None, capacidade=None):
    """Altera o nome ou a capacidade de um lugar existente.

    Um parâmetro a None significa não alterar (mesma convenção de
    `atualizar` e `atualizar_quarto`, acima). A capacidade passa
    pela mesma validação usada na criação.
    """

    lugar = procurar_lugar(lugar_id)

    if lugar is None:
        raise ValueError(f"O lugar {lugar_id} não existe.")

    campos = {}

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome do lugar é obrigatório.")

        campos["nome"] = nome

    if capacidade is not None:
        validacoes.validar_capacidade_lugar(capacidade)
        campos["capacidade"] = capacidade

    if campos:
        repositorio.atualizar_lugar(lugar_id, campos)
        lugar.update(campos)

    return lugar


def desativar_lugar(lugar_id):
    """Marca o lugar como inativo, sem o eliminar.

    Um lugar com ocupações associadas não pode desaparecer: mantém
    o registo e tira-o das listagens de escolha, sem apagar o
    histórico (decisão 8).
    """

    lugar = procurar_lugar(lugar_id)

    if lugar is None:
        raise ValueError(f"O lugar {lugar_id} não existe.")

    if not lugar["ativo"]:
        raise ValueError(f"O lugar {lugar_id} já está inativo.")

    repositorio.atualizar_lugar(lugar_id, {"ativo": False})
    lugar["ativo"] = False
    return lugar


def reativar_lugar(lugar_id):
    """Repõe um lugar desativado como ativo.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar_lugar`.
    """

    lugar = procurar_lugar(lugar_id)

    if lugar is None:
        raise ValueError(f"O lugar {lugar_id} não existe.")

    if lugar["ativo"]:
        raise ValueError(f"O lugar {lugar_id} já está ativo.")

    repositorio.atualizar_lugar(lugar_id, {"ativo": True})
    lugar["ativo"] = True
    return lugar


def quarto_privativo_ocupado(lugar_id):
    """Verifica se o lugar indicado pertence a um quarto privativo
    que já tem algum ocupante mensal ativo — em qualquer um dos
    seus lugares, não só no lugar indicado (decisão 17: "privativo
    restringe quem ocupar" é uma regra do QUARTO, não do lugar
    isolado — atribuir um segundo ocupante a um quarto privativo já
    ocupado exige confirmação explícita, mesmo que seja noutro
    lugar do mesmo quarto).

    Devolve False sempre que o lugar não existir, não pertencer a
    um quarto privativo, ou o quarto não tiver ocupante ativo em
    nenhum dos seus lugares — nesses casos não há nada a confirmar
    aqui; a existência do próprio lugar continua a ser validada por
    contratos.criar_mensal, como até agora.

    Consulta `repositorio.listar_ocupacoes` em vez de chamar
    `contratos.py`, para evitar import circular (mesma razão de
    `desativar`, acima) — lugar, quarto e a lista de lugares do
    quarto vêm do MySQL através de `procurar_lugar`,
    `procurar_quarto` e `listar_lugares`.

    Vive aqui, e não em contratos.py, porque "privativo" é um
    atributo do quarto e é este módulo que trata de unidades,
    quartos e lugares; contratos.py continua sem saber que o
    conceito existe (separação de camadas, decisão 7). Responde à
    pergunta, não decide o que fazer com a resposta: a confirmação
    de um segundo ocupante continua a ser da interface.
    """
    lugar = procurar_lugar(lugar_id)

    if lugar is None:
        return False

    quarto = procurar_quarto(lugar["quarto_id"])

    if quarto is None or not quarto["privativo"]:
        return False

    lugares_do_quarto = {
        lg["id"]
        for lg in listar_lugares(incluir_inativas=True, quarto_id=quarto["id"])
    }

    for ocupacao in repositorio.listar_ocupacoes(tipo="mensal"):
        if ocupacao.get("lugar_id") in lugares_do_quarto:
            return True

    return False


def estado(unidade_id, data):
    """Calcula o estado da unidade numa data: Livre, Ocupado,
    Reservado ou, no regime mensal, a proporção ocupada.

    'em_manutencao' sobrepõe-se ao cálculo (decisão 3): uma unidade
    em manutenção nunca está livre, independentemente das ocupações.
    """
    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["em_manutencao"]:
        return "Em manutenção"

    if unidade["tipo"] == "mensal":
        return _estado_mensal(unidade_id, data)

    return _estado_airbnb(unidade_id, data)


def _estado_mensal(unidade_id, data):
    """Proporção "ocupados/capacidade" de uma unidade mensal numa
    data (decisão 17: capacidade é a soma dos lugares dos quartos
    ativos; um contrato sem lugar_id conta na mesma, ver secção 4).

    Conta as ocupações mensais ativas cuja vigência cobre 'data':
    data_inicio <= data e (data_fim nulo ou data_fim > data).
    """
    capacidade = 0

    for quarto in listar_quartos(unidade_id=unidade_id):
        for lugar in listar_lugares(quarto_id=quarto["id"]):
            capacidade += lugar["capacidade"]

    ocupados = 0

    for ocupacao in repositorio.listar_ocupacoes(
        unidade_id=unidade_id, tipo="mensal"
    ):
        if ocupacao["data_inicio"] > data:
            continue

        if ocupacao["data_fim"] is not None and ocupacao["data_fim"] <= data:
            continue

        ocupados += 1

    return f"{ocupados}/{capacidade}"


def _estado_airbnb(unidade_id, data):
    """Livre, Ocupado ou Reservado de uma unidade Airbnb numa data.

    Fórmula de sobreposição da secção 4 — inicio_A < fim_B E
    inicio_B < fim_A — tratando 'data' como a noite [data, data + 1
    dia). Reservado é uma ocupação futura ainda não iniciada
    (início > data), quando a noite pedida está livre.
    """
    fim_janela = data + timedelta(days=1)
    tem_futura = False

    for ocupacao in repositorio.listar_ocupacoes(
        unidade_id=unidade_id, tipo="airbnb"
    ):
        if (
            ocupacao["data_inicio"] < fim_janela
            and data < ocupacao["data_fim"]
        ):
            return "Ocupado"

        if ocupacao["data_inicio"] > data:
            tem_futura = True

    return "Reservado" if tem_futura else "Livre"