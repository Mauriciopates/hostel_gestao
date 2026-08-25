"""Gestão das unidades, quartos e lugares — a estrutura física do
alojamento.

Unidade é o que se contrata (tem preço e regime); quarto é a
divisão; lugar é a cama ou posição contratável dentro dele
(decisão 17). Só `em_manutencao` persiste como estado — livre,
ocupado e reservado calculam-se a partir dos contratos, para uma
data (decisão 3).

Não acede a ficheiros nem à interface: recebe a estrutura de dados,
devolve resultado e sinaliza erro com `raise ValueError`. Quem
carrega e grava é o `main.py`, através do repositório.
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
    dados,
    propriedade_id,
    tipo,
    preco_base,
    preco_epoca_alta,
    multa_check_in_tardio,
    epoca_alta_ativa=False,
):
    """Criação das unidades, faz a validações de existencia
    antes de criar a unidade"""

    propriedade = propriedades.procurar(dados, propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    if tipo not in validacoes.TIPOS_UNIDADE:
        raise ValueError(f"Tipo de unidade desconhecido: {tipo}")

    precos = (
        ("preço base", preco_base),
        ("preço de época alta", preco_epoca_alta),
        ("multa de check-in tardio", multa_check_in_tardio),
    )

    for nome, valor in precos:
        if valor is None:
            raise ValueError(f"{nome} é obrigatório.")

        if not isinstance(valor, Decimal):
            raise ValueError(
                f"{nome} tem de ser Decimal, não" f" {type(valor).__name__}."
            )

        if valor < 0:
            raise ValueError(f"{nome} não pode ser negativo: {valor}.")

    unidade = {
        "id": repositorio.proximo_id(PREFIXO),
        "propriedade_id": propriedade_id,
        "tipo": tipo,
        "preco_base": preco_base,
        "preco_epoca_alta": preco_epoca_alta,
        "multa_check_in_tardio": multa_check_in_tardio,
        "epoca_alta_ativa": epoca_alta_ativa,
        "em_manutencao": False,
        "ativo": True,
    }

    dados["unidades"].append(unidade)
    return unidade


def procurar(dados, unidade_id):
    """Devolve a unidade com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação — é o que a `criar` faz com a propriedade, ao
    transformar o None num ValueError.

    Não filtra inativas: uma unidade desativada continua a ser
    encontrada, senão a `reativar` não teria como lhe chegar.
    """

    for u in dados["unidades"]:
        if u["id"] == unidade_id:
            return u

    return None


def listar(dados, incluir_inativas=False, propriedade_id=None, tipo=None):
    """Devolve as unidades, filtráveis por propriedade e por tipo.

    Devolve lista nova: alterá-la depois não afeta a estrutura de
    dados (mesma convenção de `propriedades.listar`).
    """

    resultado = []

    for u in dados["unidades"]:
        if not incluir_inativas and not u["ativo"]:
            continue

        if propriedade_id is not None:
            if u["propriedade_id"] != propriedade_id:
                continue

        if tipo is not None and u["tipo"] != tipo:
            continue

        resultado.append(u)

    return resultado


def atualizar(
    dados,
    unidade_id,
    preco_base=None,
    preco_epoca_alta=None,
    multa_check_in_tardio=None,
    epoca_alta_ativa=None,
):
    """Altera os preços e o indicador de época alta de uma unidade.

    Um parâmetro a None significa não alterar (mesma convenção de
    `propriedades.atualizar`). Os três preços não podem ficar vazios
    nem negativos: são obrigatórios no cadastro (decisão 6) e essa
    obrigatoriedade mantém-se na alteração.

    O tipo e a propriedade não se alteram aqui: o tipo é restrição
    rígida sobre as ocupações e mudar de propriedade não corresponde
    a nenhuma operação real do negócio. O estado de manutenção tem
    funções próprias.
    """

    unidade = procurar(dados, unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    precos = (
        ("preço base", preco_base),
        ("preço de época alta", preco_epoca_alta),
        ("multa de check-in tardio", multa_check_in_tardio),
    )

    for nome, valor in precos:
        if valor is None:
            continue

        if not isinstance(valor, Decimal):
            raise ValueError(
                f"{nome} tem de ser Decimal, não" f" {type(valor).__name__}."
            )

        if valor < 0:
            raise ValueError(f"{nome} não pode ser negativo: {valor}.")

    if preco_base is not None:
        unidade["preco_base"] = preco_base

    if preco_epoca_alta is not None:
        unidade["preco_epoca_alta"] = preco_epoca_alta

    if multa_check_in_tardio is not None:
        unidade["multa_check_in_tardio"] = multa_check_in_tardio

    if epoca_alta_ativa is not None:
        unidade["epoca_alta_ativa"] = epoca_alta_ativa

    return unidade


def desativar(dados, unidade_id):
    """Marca a unidade como inativa, sem a eliminar.

    Uma unidade com ocupações associadas não pode desaparecer: os
    contratos históricos referem-se a ela (decisão 8). Desativar
    mantém o registo e tira-o das listagens de escolha, sem apagar
    o histórico.
    """

    unidade = procurar(dados, unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if not unidade["ativo"]:
        raise ValueError(f"A unidade {unidade_id} já está inativa.")

    unidade["ativo"] = False
    return unidade


def reativar(dados, unidade_id):
    """Repõe uma unidade desativada como ativa.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar`.
    """

    unidade = procurar(dados, unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["ativo"]:
        raise ValueError(f"A unidade {unidade_id} já está ativa.")

    unidade["ativo"] = True
    return unidade


def marcar_manutencao(dados, unidade_id):
    """Coloca a unidade em manutenção, tirando-a da oferta.

    'em_manutencao' é a única forma de estado que persiste na
    unidade — livre, ocupado e reservado calculam-se a partir dos
    contratos para uma data (decisão 3). Colocar em manutenção é
    decisão da gestão, não algo que se infira dos contratos.
    """

    unidade = procurar(dados, unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["em_manutencao"]:
        raise ValueError(f"A unidade {unidade_id} já está em manutenção.")

    unidade["em_manutencao"] = True
    return unidade


def desmarcar_manutencao(dados, unidade_id):
    """Repõe a unidade na oferta, saindo da manutenção.

    Inversa exata da `marcar_manutencao`.
    """

    unidade = procurar(dados, unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if not unidade["em_manutencao"]:
        raise ValueError(f"A unidade {unidade_id} não está em manutenção.")

    unidade["em_manutencao"] = False
    return unidade


# Inicio do código para Quartos


def criar_quarto(dados, unidade_id, nome, privativo=False,
                limpeza_incluida=False):
    """Cria um quarto dentro de uma unidade existente.

    Devolve o registo criado. Não grava: a gravação é decidida pelo
    `main.py` (mesma convenção da `criar` da unidade).
    """

    unidade = procurar(dados, unidade_id)

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

    dados["quartos"].append(quarto)
    return quarto


def procurar_quarto(dados, quarto_id):
    """Devolve o quarto com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos — procura, não decide (mesma
    convenção de `procurar`, unidade acima).
    """

    for q in dados["quartos"]:
        if q["id"] == quarto_id:
            return q

    return None


def listar_quartos(dados, incluir_inativas=False, unidade_id=None):
    """Devolve os quartos, filtráveis por unidade.

    Devolve lista nova: alterá-la depois não afeta a estrutura de
    dados (mesma convenção de `listar`, unidade acima).
    """

    resultado = []

    for q in dados["quartos"]:
        if not incluir_inativas and not q["ativo"]:
            continue

        if unidade_id is not None and q["unidade_id"] != unidade_id:
            continue

        resultado.append(q)

    return resultado


def atualizar_quarto(
    dados, quarto_id, nome=None, privativo=None, limpeza_incluida=None
):
    """Altera o nome ou os indicadores de um quarto existente.

    Um parâmetro a None significa não alterar (mesma convenção de
    `atualizar`, unidade acima). O nome não pode ficar vazio; os
    dois indicadores são independentes entre si (decisão 17).
    """

    quarto = procurar_quarto(dados, quarto_id)

    if quarto is None:
        raise ValueError(f"O quarto {quarto_id} não existe.")

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome do quarto é obrigatório.")

        quarto["nome"] = nome

    if privativo is not None:
        quarto["privativo"] = privativo

    if limpeza_incluida is not None:
        quarto["limpeza_incluida"] = limpeza_incluida

    return quarto


def desativar_quarto(dados, quarto_id):
    """Marca o quarto como inativo, sem o eliminar.

    Um quarto com lugares associados não pode desaparecer: mantém
    o registo e tira-o das listagens de escolha, sem apagar o
    histórico (decisão 8).
    """

    quarto = procurar_quarto(dados, quarto_id)

    if quarto is None:
        raise ValueError(f"O quarto {quarto_id} não existe.")

    if not quarto["ativo"]:
        raise ValueError(f"O quarto {quarto_id} já está inativo.")

    quarto["ativo"] = False
    return quarto


def reativar_quarto(dados, quarto_id):
    """Repõe um quarto desativado como ativo.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar_quarto`.
    """

    quarto = procurar_quarto(dados, quarto_id)

    if quarto is None:
        raise ValueError(f"O quarto {quarto_id} não existe.")

    if quarto["ativo"]:
        raise ValueError(f"O quarto {quarto_id} já está ativo.")

    quarto["ativo"] = True
    return quarto


def criar_lugar(dados, quarto_id, nome, capacidade=1):
    """Cria um lugar dentro de um quarto existente.

    Devolve o registo criado. Não grava: a gravação é decidida pelo
    `main.py` (mesma convenção da `criar` da unidade e do quarto).
    """

    quarto = procurar_quarto(dados, quarto_id)

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

    dados["lugares"].append(lugar)
    return lugar

def procurar_lugar(dados, lugar_id):
    """Devolve o lugar com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos — procura, não decide (mesma
    convenção de `procurar` e `procurar_quarto`, acima).
    """

    for lg in dados["lugares"]:
        if lg["id"] == lugar_id:
            return lg

    return None


def listar_lugares(dados, incluir_inativas=False, quarto_id=None):
    """Devolve os lugares, filtráveis por quarto.

    Devolve lista nova: alterá-la depois não afeta a estrutura de
    dados (mesma convenção de `listar` e `listar_quartos`, acima).
    """

    resultado = []

    for lg in dados["lugares"]:
        if not incluir_inativas and not lg["ativo"]:
            continue

        if quarto_id is not None and lg["quarto_id"] != quarto_id:
            continue

        resultado.append(lg)

    return resultado


def atualizar_lugar(dados, lugar_id, nome=None, capacidade=None):
    """Altera o nome ou a capacidade de um lugar existente.

    Um parâmetro a None significa não alterar (mesma convenção de
    `atualizar` e `atualizar_quarto`, acima). A capacidade passa
    pela mesma validação usada na criação.
    """

    lugar = procurar_lugar(dados, lugar_id)

    if lugar is None:
        raise ValueError(f"O lugar {lugar_id} não existe.")

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome do lugar é obrigatório.")

        lugar["nome"] = nome

    if capacidade is not None:
        validacoes.validar_capacidade_lugar(capacidade)
        lugar["capacidade"] = capacidade

    return lugar


def desativar_lugar(dados, lugar_id):
    """Marca o lugar como inativo, sem o eliminar.

    Um lugar com ocupações associadas não pode desaparecer: mantém
    o registo e tira-o das listagens de escolha, sem apagar o
    histórico (decisão 8).
    """

    lugar = procurar_lugar(dados, lugar_id)

    if lugar is None:
        raise ValueError(f"O lugar {lugar_id} não existe.")

    if not lugar["ativo"]:
        raise ValueError(f"O lugar {lugar_id} já está inativo.")

    lugar["ativo"] = False
    return lugar

def reativar_lugar(dados, lugar_id):
    """Repõe um lugar desativado como ativo.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar_lugar`.
    """

    lugar = procurar_lugar(dados, lugar_id)

    if lugar is None:
        raise ValueError(f"O lugar {lugar_id} não existe.")

    if lugar["ativo"]:
        raise ValueError(f"O lugar {lugar_id} já está ativo.")

    lugar["ativo"] = True
    return lugar



def estado(dados, unidade_id, data):
    """Calcula o estado da unidade numa data: Livre, Ocupado,
    Reservado ou, no regime mensal, a proporção ocupada.

    'em_manutencao' sobrepõe-se ao cálculo (decisão 3): uma unidade
    em manutenção nunca está livre, independentemente das ocupações.
    """
    unidade = procurar(dados, unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["em_manutencao"]:
        return "Em manutenção"

    if unidade["tipo"] == "mensal":
        return _estado_mensal(dados, unidade_id, data)

    return _estado_airbnb(dados, unidade_id, data)


def _estado_mensal(dados, unidade_id, data):
    """Proporção "ocupados/capacidade" de uma unidade mensal numa
    data (decisão 17: capacidade é a soma dos lugares dos quartos
    ativos; um contrato sem lugar_id conta na mesma, ver secção 4).

    Conta as ocupações mensais ativas cuja vigência cobre 'data':
    data_inicio <= data e (data_fim nulo ou data_fim > data).
    """
    capacidade = 0

    for quarto in listar_quartos(dados, unidade_id=unidade_id):
        for lugar in listar_lugares(dados, quarto_id=quarto["id"]):
            capacidade += lugar["capacidade"]

    ocupados = 0

    for ocupacao in dados["ocupacoes"]:
        if ocupacao["unidade_id"] != unidade_id:
            continue

        if ocupacao["tipo"] != "mensal":
            continue

        if not ocupacao["ativo"]:
            continue

        if ocupacao["data_inicio"] > data:
            continue

        if ocupacao["data_fim"] is not None and ocupacao["data_fim"] <= data:
            continue

        ocupados += 1

    return f"{ocupados}/{capacidade}"


def _estado_airbnb(dados, unidade_id, data):
    """Livre, Ocupado ou Reservado de uma unidade Airbnb numa data.

    Fórmula de sobreposição da secção 4 — inicio_A < fim_B E
    inicio_B < fim_A — tratando 'data' como a noite [data, data + 1
    dia). Reservado é uma ocupação futura ainda não iniciada
    (início > data), quando a noite pedida está livre.
    """
    fim_janela = data + timedelta(days=1)
    tem_futura = False

    for ocupacao in dados["ocupacoes"]:
        if ocupacao["unidade_id"] != unidade_id:
            continue

        if ocupacao["tipo"] != "airbnb":
            continue

        if not ocupacao["ativo"]:
            continue

        if ocupacao["data_inicio"] < fim_janela and data < ocupacao["data_fim"]:
            return "Ocupado"

        if ocupacao["data_inicio"] > data:
            tem_futura = True

    return "Reservado" if tem_futura else "Livre"