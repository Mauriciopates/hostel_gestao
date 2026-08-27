"""Gestão dos contratos mensais e das reservas Airbnb — as duas
formas de ocupação de uma unidade (decisão 5).

Base comum em `dados["ocupacoes"]`; os dados específicos de cada
regime vivem em `dados["ocupacoes_mensal"]` e
`dados["ocupacoes_airbnb"]`, ligados pelo mesmo id (`ocupacao_id`).

Não acede a ficheiros nem à interface: recebe a estrutura de dados,
devolve resultado e sinaliza erro com `raise ValueError`. Quem
carrega e grava é o `main.py`, através do repositório.
"""

from datetime import date, timedelta
from decimal import Decimal

import config
import clientes
import repositorio
import responsaveis
import unidades
import validacoes

PREFIXO_MENSAL = "CNT"
PREFIXO_AIRBNB = "RSV"


def _capacidade_unidade(dados, unidade_id):
    """Soma a capacidade de todos os lugares ativos da unidade.

    Percorre os quartos ativos e, dentro deles, os lugares ativos —
    a capacidade nunca é um campo solto (decisão 17). Serve para
    saber quantas pessoas cabem numa unidade mensal.
    """
    total = 0

    for quarto in unidades.listar_quartos(dados, unidade_id=unidade_id):
        for lugar in unidades.listar_lugares(dados, quarto_id=quarto["id"]):
            total += lugar["capacidade"]

    return total


def _ocupantes_mensal(dados, unidade_id, lugar_id=None):
    """Conta as ocupações mensais ativas de uma unidade (ou lugar).

    Sem 'lugar_id', conta o total da unidade — usada no bloqueio de
    capacidade. Com 'lugar_id', conta só as desse lugar — usada na
    regra "lugar de casal admite dois contratos; solteiro admite
    um" (decisão 4).
    """
    total = 0

    for ocupacao in dados["ocupacoes"]:
        if not ocupacao["ativo"]:
            continue
        if ocupacao["tipo"] != "mensal":
            continue
        if ocupacao["unidade_id"] != unidade_id:
            continue
        if lugar_id is not None and ocupacao["lugar_id"] != lugar_id:
            continue
        total += 1

    return total


def _validar_dia_vencimento(dia_vencimento):
    """Valida que 'dia_vencimento' é um inteiro entre 1 e 28.

    Extraída de atualizar_mensal (correção pós-0.7.0, ponto 3): só
    ela validava; criar_mensal aceitava qualquer inteiro sem erro, e
    um dia_vencimento fora do intervalo só rebentava mais tarde,
    numa atualização. Chamada agora pelas duas, para nunca mais
    divergirem.
    """
    if not isinstance(dia_vencimento, int) or isinstance(dia_vencimento, bool):
        raise ValueError("O dia de vencimento tem de ser um número inteiro.")

    if not 1 <= dia_vencimento <= 28:
        raise ValueError("O dia de vencimento tem de estar entre 1 e 28.")


def _nif_tem_contrato_mensal_ativo(dados, nif):
    """Verifica se o NIF já tem um contrato mensal ativo, em
    qualquer unidade.

    Cruza pelo NIF do cliente, não pelo cliente_id — duas fichas de
    cliente com o mesmo NIF (por exemplo, uma reativada depois de
    ter estado inativa) contam da mesma forma, porque é a mesma
    pessoa que teria dois contratos mensais em vigor ao mesmo tempo.
    Decisão de 26/08 (item 6): cruza só entre contratos mensais,
    nunca com reservas Airbnb.
    """
    for ocupacao in dados["ocupacoes"]:
        if not ocupacao["ativo"]:
            continue
        if ocupacao["tipo"] != "mensal":
            continue

        outro_cliente = clientes.procurar(dados, ocupacao["cliente_id"])

        if outro_cliente is not None and outro_cliente["nif"] == nif:
            return True

    return False


def criar_mensal(
    dados,
    unidade_id,
    cliente_id,
    data_inicio,
    renda_praticada,
    caucao,
    responsavel_desconto_renda_id="",
    lugar_id="",
    dia_vencimento=None,
    motivo_alteracao_renda="",
    motivo_alteracao_caucao="",
):
    """Cria um contrato de arrendamento mensal.

    Acrescenta um registo a 'ocupacoes' (base) e outro a
    'ocupacoes_mensal' (específico), ligados pelo mesmo id.
    Devolve os dois, em tuplo — não são juntados num só dicionário
    porque não existe, em lado nenhum da estrutura de dados, uma
    forma combinada dos dois (e as chaves colidiriam: a base usa
    "id", o específico usa "ocupacao_id" para o mesmo valor).

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção dos outros módulos de negócio).
    """
    unidade = unidades.procurar(dados, unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    validacoes.validar_tipo_unidade(unidade["tipo"], "mensal")

    cliente = clientes.procurar(dados, cliente_id)

    if cliente is None:
        raise ValueError(f"O cliente {cliente_id} não existe.")

    if not cliente["ativo"]:
        raise ValueError(f"O cliente {cliente_id} não está ativo.")

    if not cliente["nif"]:
        raise ValueError(
            f"O cliente {cliente_id} não tem NIF preenchido — "
            f"obrigatório para um contrato mensal."
        )

    if _nif_tem_contrato_mensal_ativo(dados, cliente["nif"]):
        raise ValueError(f"O NIF {cliente['nif']} já tem um contrato mensal ativo.")

    aviso_documento = validacoes.documento_expira_durante_estadia(
        cliente["validade_documento"], data_inicio, None
    )

    validacoes.validar_intervalo(data_inicio, None)

    capacidade = _capacidade_unidade(dados, unidade_id)
    ocupantes = _ocupantes_mensal(dados, unidade_id)

    if ocupantes >= capacidade:
        raise ValueError(
            f"A unidade {unidade_id} já está na capacidade máxima " f"({capacidade})."
        )

    lugar_id = lugar_id.strip()

    if lugar_id:
        lugar = unidades.procurar_lugar(dados, lugar_id)

        if lugar is None:
            raise ValueError(f"O lugar {lugar_id} não existe.")

        quarto = unidades.procurar_quarto(dados, lugar["quarto_id"])

        if quarto is None or quarto["unidade_id"] != unidade_id:
            raise ValueError(
                f"O lugar {lugar_id} não pertence à unidade " f"{unidade_id}."
            )

        ocupantes_lugar = _ocupantes_mensal(dados, unidade_id, lugar_id=lugar_id)

        if ocupantes_lugar >= lugar["capacidade"]:
            raise ValueError(
                f"O lugar {lugar_id} já está ocupado ao limite da "
                f"capacidade ({lugar['capacidade']})."
            )

    if renda_praticada is None or renda_praticada <= 0:
        raise ValueError("A renda praticada tem de ser positiva.")

    renda_calculada = unidade["preco_base"]

    if renda_praticada < renda_calculada:
        responsaveis.validar_autoria(dados, responsavel_desconto_renda_id)
        responsavel_desconto_renda_id = responsavel_desconto_renda_id.strip()
    else:
        responsavel_desconto_renda_id = ""

    caucao_exige_confirmacao = validacoes.validar_caucao(
        caucao, renda_praticada, config.MULTIPLICADOR_MAXIMO_CAUCAO
    )

    if dia_vencimento is None:
        dia_vencimento = config.DIA_VENCIMENTO
    else:
        _validar_dia_vencimento(dia_vencimento)

    ocupacao_id = repositorio.proximo_id(PREFIXO_MENSAL)

    ocupacao = {
        "id": ocupacao_id,
        "unidade_id": unidade_id,
        "cliente_id": cliente_id,
        "tipo": "mensal",
        "data_inicio": data_inicio,
        "data_fim": None,
        "lugar_id": lugar_id,
        "aviso_documento": aviso_documento,
        "ativo": True,
    }

    ocupacao_mensal = {
        "ocupacao_id": ocupacao_id,
        "renda_calculada": renda_calculada,
        "renda_praticada": renda_praticada,
        "responsavel_desconto_renda_id": responsavel_desconto_renda_id,
        "caucao": caucao,
        "caucao_exige_confirmacao": caucao_exige_confirmacao,
        "motivo_alteracao_renda": motivo_alteracao_renda.strip(),
        "motivo_alteracao_caucao": motivo_alteracao_caucao.strip(),
        "dia_vencimento": dia_vencimento,
    }

    dados["ocupacoes"].append(ocupacao)
    dados["ocupacoes_mensal"].append(ocupacao_mensal)

    return ocupacao, ocupacao_mensal


def procurar(dados, ocupacao_id):
    """Devolve a ocupação com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativas — procura, não decide (mesma
    convenção de propriedades.procurar, unidades.procurar e
    clientes.procurar).

    Serve tanto para contratos mensais como para reservas Airbnb —
    os dois vivem na mesma base ('ocupacoes'); os dados específicos
    de cada regime só se vão buscar depois, se precisos, a
    'ocupacoes_mensal' ou 'ocupacoes_airbnb' pelo mesmo id.
    """

    for ocupacao in dados["ocupacoes"]:
        if ocupacao["id"] == ocupacao_id:
            return ocupacao

    return None


def listar(
    dados,
    incluir_inativas=False,
    unidade_id=None,
    cliente_id=None,
    tipo=None,
    aviso_documento=None,
):
    """Devolve as ocupações, filtráveis por unidade, cliente, tipo
    e aviso de documento.

    Serve os dois regimes ao mesmo tempo — filtrar por
    tipo="mensal" ou tipo="airbnb" é o que separa um do outro
    quando precisas só de um. Sem 'tipo', devolve os dois
    misturados.

    'aviso_documento' filtra por True ou False quando indicado;
    None (omisso) não filtra — é o que dá efeito real ao aviso da
    decisão 11 (senão o aviso nunca mais seria encontrado depois
    de criado o contrato).

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção de propriedades.listar,
    unidades.listar e clientes.listar).
    """

    resultado = []

    for ocupacao in dados["ocupacoes"]:
        if not incluir_inativas and not ocupacao["ativo"]:
            continue

        if unidade_id is not None and ocupacao["unidade_id"] != unidade_id:
            continue

        if cliente_id is not None and ocupacao["cliente_id"] != cliente_id:
            continue

        if tipo is not None and ocupacao["tipo"] != tipo:
            continue

        if (
            aviso_documento is not None
            and ocupacao["aviso_documento"] != aviso_documento
        ):
            continue

        resultado.append(ocupacao)

    return resultado


def encerrar_mensal(dados, ocupacao_id, data_fim, motivo=""):
    """Encerra um contrato de arrendamento mensal, preenchendo a
    data de fim.

    A duração abaixo do mínimo (config.DURACAO_MINIMA_MESES) e o
    aviso prévio insuficiente (config.AVISO_PREVIO_DIAS, contado a
    partir de hoje) ficam sinalizados no registo específico
    ('ocupacoes_mensal') — nunca bloqueiam o encerramento (mesmo
    princípio da decisão 14: regra da casa, não imposição legal).

    Devolve os dois registos (base e específico), em tuplo — mesma
    convenção da criar_mensal.
    """
    ocupacao = procurar(dados, ocupacao_id)

    if ocupacao is None:
        raise ValueError(f"A ocupação {ocupacao_id} não existe.")

    if ocupacao["tipo"] != "mensal":
        raise ValueError(f"A ocupação {ocupacao_id} não é um contrato mensal.")

    if not ocupacao["ativo"]:
        raise ValueError(f"O contrato {ocupacao_id} já está encerrado.")

    if data_fim is None:
        raise ValueError("A data de fim é obrigatória para encerrar um contrato.")

    validacoes.validar_intervalo(ocupacao["data_inicio"], data_fim)

    mensal = _dados_mensais(dados, ocupacao_id)

    if mensal is None:
        raise ValueError(f"Faltam os dados mensais da ocupação {ocupacao_id}.")

    meses = (data_fim.year - ocupacao["data_inicio"].year) * 12 + (
        data_fim.month - ocupacao["data_inicio"].month
    )

    mensal["duracao_abaixo_minima"] = meses < config.DURACAO_MINIMA_MESES
    mensal["aviso_previo_insuficiente"] = (
        data_fim - date.today()
    ).days < config.AVISO_PREVIO_DIAS
    mensal["motivo_encerramento"] = motivo.strip()

    ocupacao["data_fim"] = data_fim
    ocupacao["ativo"] = False

    return ocupacao, mensal


def _dados_mensais(dados, ocupacao_id):
    """Devolve o registo específico de um contrato mensal, ou None.

    Auxiliar interna — o mesmo papel que `procurar()` tem para a
    base, mas para `dados["ocupacoes_mensal"]`. Não é pensada para
    o `cli.py` chamar diretamente (por isso o `_` no nome); serve
    só para funções deste módulo que precisem de alterar os campos
    específicos do regime mensal, como a `encerrar_mensal`.
    """

    for registo in dados["ocupacoes_mensal"]:
        if registo["ocupacao_id"] == ocupacao_id:
            return registo

    return None


def _dados_airbnb(dados, ocupacao_id):
    """Devolve o registo específico de uma reserva Airbnb, ou None.

    Mesmo papel que `_dados_mensais` tem para o regime mensal, mas
    a percorrer `dados["ocupacoes_airbnb"]`.
    """

    for registo in dados["ocupacoes_airbnb"]:
        if registo["ocupacao_id"] == ocupacao_id:
            return registo

    return None


def cancelar_airbnb(dados, ocupacao_id, motivo=""):
    """Cancela uma reserva Airbnb.

    Ao contrário da 'encerrar_mensal', não pede nem altera nenhuma
    data — a reserva já tem 'data_fim' desde a criação (ocupação
    exclusiva, com termo definido à partida). Só marca a reserva
    como inativa e regista o motivo, se indicado.

    Devolve os dois registos (base e específico), em tuplo — mesma
    convenção da criar_mensal e da encerrar_mensal.
    """
    ocupacao = procurar(dados, ocupacao_id)

    if ocupacao is None:
        raise ValueError(f"A ocupação {ocupacao_id} não existe.")

    if ocupacao["tipo"] != "airbnb":
        raise ValueError(f"A ocupação {ocupacao_id} não é uma reserva Airbnb.")

    if not ocupacao["ativo"]:
        raise ValueError(f"A reserva {ocupacao_id} já está cancelada.")

    airbnb = _dados_airbnb(dados, ocupacao_id)

    if airbnb is None:
        raise ValueError(f"Faltam os dados Airbnb da ocupação {ocupacao_id}.")

    airbnb["motivo_cancelamento"] = motivo.strip()
    ocupacao["ativo"] = False

    return ocupacao, airbnb


def reativar(dados, ocupacao_id):
    """Repõe uma ocupação encerrada ou cancelada como ativa.

    Existe porque um encerramento ou cancelamento por engano seria
    irreversível sem ela — é a inversa exata da 'encerrar_mensal' e
    da 'cancelar_airbnb', mas só da desativação simples (mesma
    ressalva que já existe em clientes.reativar para o cliente
    anonimizado: aqui não há caso irreversível nenhum a impedir).

    Fica unificada porque não precisa de nenhum parâmetro extra —
    só se comporta de forma diferente por dentro, consoante o
    tipo: um contrato mensal tem 'data_fim' reposto a None
    (inverte exatamente o que 'encerrar_mensal' fez); uma reserva
    Airbnb não mexe em 'data_fim', porque o cancelamento nunca lhe
    tocou.

    Numa reserva Airbnb, verifica sobreposição antes de reativar —
    sem isto, reativar contornaria a regra de exclusividade que a
    própria criação impõe (registar_airbnb já recusa duas reservas
    Airbnb sobrepostas na mesma unidade; reativar tinha ficado de
    fora dessa regra por descuido).
    """
    ocupacao = procurar(dados, ocupacao_id)

    if ocupacao is None:
        raise ValueError(f"A ocupação {ocupacao_id} não existe.")

    if ocupacao["ativo"]:
        raise ValueError(f"A ocupação {ocupacao_id} já está ativa.")

    if ocupacao["tipo"] == "airbnb":
        if _existe_sobreposicao(
            dados,
            ocupacao["unidade_id"],
            ocupacao["data_inicio"],
            ocupacao["data_fim"],
        ):
            raise ValueError(
                f"A unidade {ocupacao['unidade_id']} já tem uma "
                f"reserva ativa nesse período — não é possível "
                f"reativar {ocupacao_id}."
            )

    if ocupacao["tipo"] == "mensal":
        ocupacao["data_fim"] = None

    ocupacao["ativo"] = True

    return ocupacao


def _sobrepoe(inicio_a, fim_a, inicio_b, fim_b):
    """Verifica se dois intervalos de datas se sobrepõem.

    Fórmula da secção 4 das orientações: inicio_A < fim_B E
    inicio_B < fim_A. Nunca "data dentro do intervalo" — essa
    forma falha nos casos de fronteira que interessam aqui.

    A unidade de contagem é a noite: dois intervalos que só se
    tocam no mesmo dia (a saída de um coincide com a entrada do
    outro) não contam como sobreposição — 'fim' é sempre o dia de
    saída, não uma noite ocupada.
    """
    return inicio_a < fim_b and inicio_b < fim_a


def _existe_sobreposicao(dados, unidade_id, data_inicio, data_fim, ignorar_id=None):
    """Verifica se alguma reserva Airbnb ativa da unidade se
    sobrepõe ao intervalo indicado.

    'ignorar_id' permite excluir uma ocupação da comparação — sem
    uso nenhum por agora (só 'registar_airbnb' chama esta função,
    e uma reserva nova nunca precisa de se ignorar a si própria),
    mas fica pronta para quando houver uma função de alterar datas
    de uma reserva existente, que vai precisar de se comparar
    contra as outras sem se comparar contra si mesma.
    """
    for ocupacao in dados["ocupacoes"]:
        if not ocupacao["ativo"]:
            continue

        if ocupacao["tipo"] != "airbnb":
            continue

        if ocupacao["unidade_id"] != unidade_id:
            continue

        if ignorar_id is not None and ocupacao["id"] == ignorar_id:
            continue

        if _sobrepoe(
            data_inicio, data_fim, ocupacao["data_inicio"], ocupacao["data_fim"]
        ):

            return True

    return False


def _preco_calculado_airbnb(unidade, data_inicio, data_fim):
    """Soma o preço de cada noite da estadia, aplicando o preço de
    época alta noite a noite.

    Uma reserva pode atravessar a fronteira da época alta a meio
    da estadia (ex.: entra a 28 de junho, sai a 3 de julho) — por
    isso não pode ser um preço único para a reserva toda; percorre
    cada noite e decide, noite a noite, se o preço de época alta
    se aplica (exige o indicador manual ativo na unidade E a data
    dentro do período configurado — validacoes.em_epoca_alta, já
    escrita).
    """
    total = Decimal("0.00")
    noite = data_inicio

    while noite < data_fim:
        if validacoes.em_epoca_alta(
            noite,
            unidade["epoca_alta_ativa"],
            config.EPOCA_ALTA_INICIO,
            config.EPOCA_ALTA_FIM,
        ):
            total += unidade["preco_epoca_alta"]
        else:
            total += unidade["preco_base"]

        noite += timedelta(days=1)

    return total


def calcular_preco_airbnb(unidade, data_inicio, data_fim):
    """Calcula o preço total de uma estadia Airbnb, sem registar
    nada — versão pública de '_preco_calculado_airbnb' (mesma
    lógica, chamada por ela).

    Existe para o cli.py poder mostrar "Preço calculado: ..." ANTES
    de pedir o preço praticado, e assim decidir se há desconto a
    confirmar (decisão 18) antes mesmo de a pessoa escrever um
    valor — sem esta função pública, isso só era possível depois de
    a reserva já estar registada, porque a única forma de calcular
    o preço era a função privada '_preco_calculado_airbnb', que o
    cli.py não devia chamar diretamente.
    """
    return _preco_calculado_airbnb(unidade, data_inicio, data_fim)


def registar_airbnb(
    dados,
    unidade_id,
    cliente_id,
    data_inicio,
    data_fim,
    preco_praticado,
    responsavel_desconto_preco_id="",
    check_in_tardio=False,
    hora_chegada="",
    multa_praticada=None,
    responsavel_desconto_multa_id="",
):
    """Regista uma reserva Airbnb.

    Não é um "contrato" (ver secção 5.4 das orientações) — é uma
    marcação de estadia curta, com data de fim definida à partida.

    Acrescenta um registo a 'ocupacoes' (base) e outro a
    'ocupacoes_airbnb' (específico), ligados pelo mesmo id.
    Devolve os dois, em tuplo — mesma convenção da criar_mensal.

    Quando 'preco_praticado' fica abaixo do calculado, ou
    'multa_praticada' abaixo da calculada, exige um responsável que
    autorize o desconto (decisão 18) — validado com
    responsaveis.validar_autoria (tem de existir e estar ativo).
    Sem desconto, os dois campos de responsável ficam sempre em
    branco, mesmo que algo tenha sido passado neles.
    """
    unidade = unidades.procurar(dados, unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    validacoes.validar_tipo_unidade(unidade["tipo"], "airbnb")

    cliente = clientes.procurar(dados, cliente_id)

    if cliente is None:
        raise ValueError(f"O cliente {cliente_id} não existe.")

    if not cliente["ativo"]:
        raise ValueError(f"O cliente {cliente_id} não está ativo.")

    validacoes.validar_intervalo(
        data_inicio,
        data_fim,
        config.ESTADIA_MINIMA_NOITES,
        config.ESTADIA_MAXIMA_NOITES,
    )

    if _existe_sobreposicao(dados, unidade_id, data_inicio, data_fim):
        raise ValueError(f"A unidade {unidade_id} já tem uma reserva nesse período.")

    aviso_documento = validacoes.documento_expira_durante_estadia(
        cliente["validade_documento"], data_inicio, data_fim
    )

    if preco_praticado is None or preco_praticado <= 0:
        raise ValueError("O preço praticado tem de ser positivo.")

    preco_calculado = _preco_calculado_airbnb(unidade, data_inicio, data_fim)

    if preco_praticado < preco_calculado:
        responsaveis.validar_autoria(dados, responsavel_desconto_preco_id)
        responsavel_desconto_preco_id = responsavel_desconto_preco_id.strip()
    else:
        responsavel_desconto_preco_id = ""

    if check_in_tardio:
        hora_chegada = hora_chegada.strip()

        if not hora_chegada:
            raise ValueError(
                "A hora de chegada é obrigatória quando o check-in " "é tardio."
            )

        multa_calculada = unidade["multa_check_in_tardio"]

        if multa_praticada is None:
            multa_praticada = multa_calculada
    else:
        hora_chegada = ""
        multa_calculada = Decimal("0.00")
        multa_praticada = Decimal("0.00")

    if multa_praticada < multa_calculada:
        responsaveis.validar_autoria(dados, responsavel_desconto_multa_id)
        responsavel_desconto_multa_id = responsavel_desconto_multa_id.strip()
    else:
        responsavel_desconto_multa_id = ""

    ocupacao_id = repositorio.proximo_id(PREFIXO_AIRBNB)

    ocupacao = {
        "id": ocupacao_id,
        "unidade_id": unidade_id,
        "cliente_id": cliente_id,
        "tipo": "airbnb",
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "lugar_id": "",
        "aviso_documento": aviso_documento,
        "ativo": True,
    }

    ocupacao_airbnb = {
        "ocupacao_id": ocupacao_id,
        "preco_calculado": preco_calculado,
        "preco_praticado": preco_praticado,
        "responsavel_desconto_preco_id": responsavel_desconto_preco_id,
        "check_in_tardio": check_in_tardio,
        "hora_chegada": hora_chegada,
        "multa_calculada": multa_calculada,
        "multa_praticada": multa_praticada,
        "responsavel_desconto_multa_id": responsavel_desconto_multa_id,
        "motivo_cancelamento": "",
    }

    dados["ocupacoes"].append(ocupacao)
    dados["ocupacoes_airbnb"].append(ocupacao_airbnb)

    return ocupacao, ocupacao_airbnb


def atualizar_mensal(
    dados,
    ocupacao_id,
    renda_praticada=None,
    responsavel_desconto_renda_id="",
    caucao=None,
    motivo_alteracao_renda=None,
    motivo_alteracao_caucao=None,
    dia_vencimento=None,
):
    """Altera a renda praticada, a caução ou o dia de vencimento
    de um contrato mensal já existente.

    'renda_calculada' nunca muda aqui — fica fixa desde a criação
    (decisão 14: o calculado e o praticado ficam sempre visíveis
    lado a lado, nunca se sobrepõem um ao outro).
    """
    ocupacao = procurar(dados, ocupacao_id)

    if ocupacao is None:
        raise ValueError(f"A ocupação {ocupacao_id} não existe.")

    if ocupacao["tipo"] != "mensal":
        raise ValueError(f"A ocupação {ocupacao_id} não é um contrato mensal.")

    if not ocupacao["ativo"]:
        raise ValueError(
            f"O contrato {ocupacao_id} está encerrado e não pode " f"ser alterado."
        )

    mensal = _dados_mensais(dados, ocupacao_id)

    if mensal is None:
        raise ValueError(f"Faltam os dados mensais da ocupação {ocupacao_id}.")

    nova_renda = (
        renda_praticada if renda_praticada is not None else mensal["renda_praticada"]
    )

    if nova_renda <= 0:
        raise ValueError("A renda praticada tem de ser positiva.")

    if renda_praticada is not None:
        if renda_praticada < mensal["renda_calculada"]:
            responsaveis.validar_autoria(dados, responsavel_desconto_renda_id)
            mensal["responsavel_desconto_renda_id"] = (
                responsavel_desconto_renda_id.strip()
            )
        else:
            mensal["responsavel_desconto_renda_id"] = ""

    nova_caucao = caucao if caucao is not None else mensal["caucao"]

    caucao_exige_confirmacao = validacoes.validar_caucao(
        nova_caucao, nova_renda, config.MULTIPLICADOR_MAXIMO_CAUCAO
    )

    mensal["renda_praticada"] = nova_renda
    mensal["caucao"] = nova_caucao
    mensal["caucao_exige_confirmacao"] = caucao_exige_confirmacao

    if motivo_alteracao_renda is not None:
        mensal["motivo_alteracao_renda"] = motivo_alteracao_renda.strip()

    if motivo_alteracao_caucao is not None:
        mensal["motivo_alteracao_caucao"] = motivo_alteracao_caucao.strip()

    if dia_vencimento is not None:
        _validar_dia_vencimento(dia_vencimento)
        mensal["dia_vencimento"] = dia_vencimento

    return ocupacao, mensal


def atualizar_airbnb(
    dados,
    ocupacao_id,
    preco_praticado=None,
    responsavel_desconto_preco_id="",
    multa_praticada=None,
    responsavel_desconto_multa_id="",
):
    """Altera o preço praticado ou a multa de check-in tardio de
    uma reserva Airbnb já existente.

    Não altera 'check_in_tardio' nem 'hora_chegada' — esses só se
    definem na criação (registar_airbnb). Mudar se houve ou não
    check-in tardio depois de a reserva já estar registada é uma
    decisão diferente de uma simples edição de valor, e fica fora
    do âmbito desta função.

    Mesma regra de desconto de registar_airbnb (decisão 18):
    quando o novo valor fica abaixo do calculado gravado na
    criação, exige responsável validado; quando não fica, limpa
    qualquer autorização anterior — deixar de haver desconto
    também deixa de precisar de responsável associado.
    """
    ocupacao = procurar(dados, ocupacao_id)

    if ocupacao is None:
        raise ValueError(f"A ocupação {ocupacao_id} não existe.")

    if ocupacao["tipo"] != "airbnb":
        raise ValueError(f"A ocupação {ocupacao_id} não é uma reserva Airbnb.")

    if not ocupacao["ativo"]:
        raise ValueError(
            f"A reserva {ocupacao_id} está cancelada e não pode " f"ser alterada."
        )

    airbnb = _dados_airbnb(dados, ocupacao_id)

    if airbnb is None:
        raise ValueError(f"Faltam os dados Airbnb da ocupação {ocupacao_id}.")

    if preco_praticado is not None:
        if preco_praticado <= 0:
            raise ValueError("O preço praticado tem de ser positivo.")

        if preco_praticado < airbnb["preco_calculado"]:
            responsaveis.validar_autoria(dados, responsavel_desconto_preco_id)
            airbnb["responsavel_desconto_preco_id"] = (
                responsavel_desconto_preco_id.strip()
            )
        else:
            airbnb["responsavel_desconto_preco_id"] = ""

        airbnb["preco_praticado"] = preco_praticado

    if multa_praticada is not None:
        if not airbnb["check_in_tardio"]:
            raise ValueError(
                f"A reserva {ocupacao_id} não teve check-in "
                f"tardio; não há multa a alterar."
            )

        if multa_praticada < 0:
            raise ValueError("A multa praticada não pode ser negativa.")

        if multa_praticada < airbnb["multa_calculada"]:
            responsaveis.validar_autoria(dados, responsavel_desconto_multa_id)
            airbnb["responsavel_desconto_multa_id"] = (
                responsavel_desconto_multa_id.strip()
            )
        else:
            airbnb["responsavel_desconto_multa_id"] = ""

        airbnb["multa_praticada"] = multa_praticada

    return ocupacao, airbnb
