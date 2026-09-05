"""Validação de dados de entrada.

Bloqueia o essencial e avisa no resto (decisão 11): campos obrigatórios
impedem a gravação; campos em falta que não sejam essenciais marcam o
registo como incompleto, para aparecer na listagem própria.

Não conhece a interface: recebe valores, devolve resultado, sinaliza erro
com `raise ValueError`. A conversão de texto para Decimal ou date é
responsabilidade de quem chama.
"""

# O que muda aqui mudar o modelo de negício
# Não altera as configurações de validação.

from datetime import date

TIPOS_DOCUMENTO = (
    "Cartão de Cidadão",
    "Passaporte",
    "Título de Residência",
    "Outro",
)

TIPOS_ESTADO_CIVIL = (
    "Solteiro(a)",
    "Casado(a)",
    "Divorciado(a)",
    "Viúvo(a)",
    "União de facto",
)

TIPOS_UNIDADE = ("mensal", "airbnb")


def nif_valido(nif):
    """Verifica um NIF português pelo dígito de controlo.

    Aceita apenas nove dígitos. O último resulta dos oito primeiros
    através do algoritmo módulo 11, o que deteta erros de digitação sem
    consultar qualquer serviço externo.
    """
    if not nif or not nif.isdigit() or len(nif) != 9:
        return False

    soma = 0
    for posicao in range(8):
        soma += int(nif[posicao]) * (9 - posicao)

    resto = soma % 11
    controlo = 0 if resto < 2 else 11 - resto

    return controlo == int(nif[8])


# isto valida o formato, não a existência
# nesta fase não temos como consultar as informações
# nas finanças.
""" Regra para saber se é um NIF Multiplica-se
cada um dos 8 primeiros dígitos por pesos de 9 a 2
soma-se tudo, e o resto da divisão por 11 tem de 
coincidir com o 9.º dígito (11 menos o resto,
ou 0 se o resto for 0 ou 1).
"""


def validar_cliente(dados, regime):
    """Valida os dados de um cliente para o regime indicado.

    Aplica a decisão 11 (o essencial bloqueia, o resto avisa), mas
    desde a decisão de 26/08 (ponto 2) o que conta como essencial
    passa a depender do regime:

    - Airbnb: nome, tipo de documento, número de documento,
      validade do documento, data de nascimento e nacionalidade são
      obrigatórios. NIF, email, telefone, morada e contacto de
      emergência ficam opcionais (nunca marcam incompleto, exceto
      email/telefone/morada).
    - Mensal: nome, tipo de documento, número de documento,
      validade do documento, data de nascimento, NIF, morada e
      estado civil são obrigatórios. Email, telefone e
      nacionalidade ficam opcionais.

    Devolve a lista de campos em falta que não impedem a gravação —
    se não estiver vazia, o registo é marcado como incompleto.

    Lança ValueError no primeiro campo obrigatório em falta.
    """
    if regime not in TIPOS_UNIDADE:
        raise ValueError(f"Regime desconhecido: {regime}")

    if not dados.get("nome", "").strip():
        raise ValueError("O nome é obrigatório.")

    if not dados.get("tipo_documento", "").strip():
        raise ValueError("O tipo de documento é obrigatório.")

    if dados["tipo_documento"] not in TIPOS_DOCUMENTO:
        raise ValueError(
                f"Tipo de documento inválido: {dados['tipo_documento']}"
        )

    if not dados.get("numero_documento", "").strip():
        raise ValueError("O número do documento é obrigatório.")

    if dados.get("validade_documento") is None:
        raise ValueError("A validade do documento é obrigatória.")

    if dados.get("data_nascimento") is None:
        raise ValueError("A data de nascimento é obrigatória.")

    if regime == "mensal":
        nif = dados.get("nif", "").strip()
        if not nif:
            raise ValueError("O NIF é obrigatório no regime mensal.")
        if not nif_valido(nif):
            raise ValueError(f"NIF inválido: {nif}")

        if not dados.get("morada", "").strip():
            raise ValueError(
                "A morada de residência é obrigatória no regime "
                "mensal."
            )

        estado_civil = dados.get("estado_civil", "").strip()

        if not estado_civil:
            raise ValueError(
                "O estado civil é obrigatório no regime mensal."
            )

        if estado_civil not in TIPOS_ESTADO_CIVIL:
            raise ValueError(f"Estado civil inválido: {estado_civil}")

        em_falta = []
        for campo in ("email", "telefone", "nacionalidade"):
            if not dados.get(campo, "").strip():
                em_falta.append(campo)
    else:
        if not dados.get("nacionalidade", "").strip():
            raise ValueError(
                "A nacionalidade é obrigatória no regime Airbnb."
            )

        em_falta = []
        for campo in ("email", "telefone", "morada"):
            if not dados.get(campo, "").strip():
                em_falta.append(campo)

    return em_falta

def documento_expira_durante_estadia(validade, data_inicio, data_fim):
    """Verifica se o documento caduca durante a permanência.

    Não bloqueia: é aviso (decisão 11). Um documento que expira a meio da
    estadia continua a identificar o hóspede à entrada, mas o sistema
    assinala-o porque o boletim de alojamento é comunicado às autoridades.

    Um contrato mensal sem termo (data_fim nula) considera-se em curso: a
    validade é comparada apenas com o início.
    """
    if validade is None:
        return False

    if data_fim is None:
        return validade < data_inicio

    return data_inicio <= validade < data_fim


def validar_caucao(caucao, renda_praticada, multiplicador_maximo):
    """Verifica se a caução está dentro do teto permitido.

    A caução é calculada a partir da renda praticada, não é montante fixo
    (decisão 14). O sistema sugere uma renda e aceita até duas; acima
    disso recusa. Valor nulo é admitido, com confirmação de quem regista.

    Devolve True quando a caução exige confirmação explícita: valor nulo
    ou acima do sugerido. Lança ValueError acima do teto.
    """
    if caucao is None:
        raise ValueError("A caução não pode ser omitida.")

    if caucao < 0:
        raise ValueError("A caução não pode ser negativa.")

    if renda_praticada is None or renda_praticada <= 0:
        raise ValueError(
            "A renda praticada tem de ser positiva para calcular a " "caução."
        )

    teto = renda_praticada * multiplicador_maximo

    if caucao > teto:
        raise ValueError(
            f"A caução de {caucao} excede o máximo de {teto}, "
            f"correspondente a {multiplicador_maximo} rendas."
        )

    return caucao == 0 or caucao > renda_praticada


def validar_intervalo(data_inicio, data_fim, minimo=None, maximo=None):
    """Verifica a coerência de um intervalo de datas.

    O fim tem de ser posterior ao início: a unidade de contagem é a
    noite, e um intervalo com o mesmo dia de entrada e saída não contém
    nenhuma.

    Os limites de duração são opcionais, porque só se aplicam ao regime
    Airbnb — um contrato mensal não tem termo previsto.
    """
    if data_inicio is None:
        raise ValueError("A data de início é obrigatória.")

    if data_fim is None:
        return

    if data_fim <= data_inicio:
        raise ValueError(
            "A data de fim tem de ser posterior à data de início."
        )

    noites = (data_fim - data_inicio).days

    if minimo is not None and noites < minimo:
        raise ValueError(
        f"A estadia de {noites} noites é inferior ao mínimo de " f"{minimo}."
        )

    if maximo is not None and noites > maximo:
        raise ValueError(
            f"A estadia de {noites} noites excede o máximo de {maximo}."
        )


def validar_capacidade_lugar(capacidade):
    """Verifica a capacidade declarada de um lugar.

    A capacidade é guardada no lugar e não derivada do tipo de cama, o
    que permite configurações fora do par solteiro/casal (decisão 17).

    Um beliche são dois lugares de capacidade 1, nunca um de capacidade
    2: os ocupantes de um beliche não têm relação entre si, ao contrário
    dos de uma cama de casal.
    """
    if capacidade is None:
        raise ValueError("A capacidade do lugar é obrigatória.")

    if not isinstance(capacidade, int) or isinstance(capacidade, bool):
        raise ValueError(
            f"A capacidade tem de ser um número inteiro: {capacidade}"
        )

    if capacidade < 1:
        raise ValueError(f"A capacidade tem de ser pelo menos 1: {capacidade}")

    return capacidade > 2


def validar_tipo_unidade(tipo_unidade, tipo_ocupacao):
    """Verifica se o tipo da ocupação corresponde ao tipo da unidade.

    A restrição é rígida: uma unidade mensal nunca aceita reserva Airbnb
    e uma unidade Airbnb nunca aceita contrato mensal. Não há confirmação
    que a contorne.
    """
    if tipo_unidade not in TIPOS_UNIDADE:
        raise ValueError(f"Tipo de unidade desconhecido: {tipo_unidade}")

    if tipo_ocupacao not in TIPOS_UNIDADE:
        raise ValueError(f"Tipo de ocupação desconhecido: {tipo_ocupacao}")

    if tipo_unidade != tipo_ocupacao:
        raise ValueError(
            f"Uma unidade do tipo {tipo_unidade} não aceita ocupações "
            f"do tipo {tipo_ocupacao}."
        )


def em_epoca_alta(data, epoca_alta_ativa, inicio, fim):
    """Verifica se uma data está em época alta para a unidade.

    Exige as duas condições: o indicador manual da unidade tem de estar
    ativo E a data tem de cair no período configurado. A época alta nunca
    é automática.

    O período é indicado como pares (mês, dia), independentes do ano, e o
    dia final está incluído.
    """
    if data is None:
        raise ValueError("A data é obrigatória.")

    if not epoca_alta_ativa:
        return False

    return inicio <= (data.month, data.day) <= fim