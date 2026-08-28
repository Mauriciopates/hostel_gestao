"""Gestão dos clientes — as pessoas que contratam alojamento.

Concentra os dados pessoais do sistema (decisão 11) e é o alvo da
anonimização prevista pelo RGPD (decisão 8). Não acede a ficheiros
nem à interface: recebe a estrutura de dados, devolve resultado e
sinaliza erro com `raise ValueError`. Quem carrega e grava é o
`main.py`, através do repositório.
"""

import repositorio
import validacoes

PREFIXO = "CLI"


def _nif_pertence_a_outro_cliente(dados, nif, ignorar_id=None):
    """Verifica se o NIF já pertence a outro cliente ativo.

    Só compara NIFs não vazios — um cliente Airbnb sem NIF nunca
    colide com outro sem NIF (o NIF só é obrigatório no mensal,
    decisão de 26/08). 'ignorar_id' exclui o próprio cliente da
    comparação, para 'atualizar' não se recusar a si mesmo ao manter
    o NIF que já tinha.

    Só considera clientes ativos — um cliente inativo não bloqueia
    a reutilização do NIF (decisão de 26/08, item 5).
    """
    if not nif:
        return False

    for c in dados["clientes"]:
        if ignorar_id is not None and c["id"] == ignorar_id:
            continue
        if not c["ativo"]:
            continue
        if c["nif"] == nif:
            return True

    return False


def criar(
    dados,
    nome,
    tipo_documento,
    numero_documento,
    regime,
    nif="",
    email="",
    telefone="",
    morada="",
    nacionalidade="",
    estado_civil="",
    data_nascimento=None,
    validade_documento=None,
    contacto_emergencia="",
):
    """Cria um cliente e acrescenta-o à estrutura de dados.

    'regime' ("mensal" ou "airbnb") não fica guardado no registo:
    serve só para validacoes.validar_cliente() saber quais campos
    são obrigatórios nesse regime (decisão 11, revista na decisão
    de 26/08 — cada regime passou a ter o seu próprio conjunto de
    obrigatórios, ver validar_cliente). O regime pertence ao
    contrato, não ao cliente.

    Devolve o registo criado, com 'incompleto' a True se algum
    campo não essencial (por regime) ficou por preencher.

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção de propriedades.criar e unidades.criar).
    """
    candidato = {
        "nome": nome.strip(),
        "tipo_documento": tipo_documento.strip(),
        "numero_documento": numero_documento.strip(),
        "nif": nif.strip(),
        "email": email.strip(),
        "telefone": telefone.strip(),
        "morada": morada.strip(),
        "nacionalidade": nacionalidade.strip(),
        "estado_civil": estado_civil.strip(),
        "data_nascimento": data_nascimento,
        "validade_documento": validade_documento,
    }

    em_falta = validacoes.validar_cliente(candidato, regime)

    if _nif_pertence_a_outro_cliente(dados, candidato["nif"]):
        raise ValueError(
            f"Já existe um cliente ativo com o NIF {candidato['nif']}."
        )

    cliente = {
        "id": repositorio.proximo_id(PREFIXO),
        "nome": candidato["nome"],
        "tipo_documento": candidato["tipo_documento"],
        "numero_documento": candidato["numero_documento"],
        "nif": candidato["nif"],
        "email": candidato["email"],
        "telefone": candidato["telefone"],
        "morada": candidato["morada"],
        "nacionalidade": candidato["nacionalidade"],
        "estado_civil": candidato["estado_civil"],
        "data_nascimento": data_nascimento,
        "validade_documento": validade_documento,
        "contacto_emergencia": contacto_emergencia.strip(),
        "incompleto": bool(em_falta),
        "anonimizado": False,
        "data_anonimizado": None,
        "responsavel_anonimizado_id": "",
        "ativo": True,
    }

    dados["clientes"].append(cliente)
    return cliente


def procurar(dados, cliente_id):
    """Devolve o cliente com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos nem anonimizados — procura, não
    decide (mesma convenção de propriedades.procurar e
    unidades.procurar).
    """

    for c in dados["clientes"]:
        if c["id"] == cliente_id:
            return c

    return None


def listar(dados, incluir_inativos=False, incompleto=None):
    """Devolve os clientes, filtráveis por estado e por incompletos.

    'incompleto' filtra por True ou False quando indicado; None
    (omisso) não filtra. Decisão 11 exige que exista uma listagem
    dos registos incompletos, senão o aviso de campos em falta não
    produz efeito nenhum — é o que este parâmetro serve.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção de propriedades.listar e
    unidades.listar).
    """

    resultado = []

    for c in dados["clientes"]:
        if not incluir_inativos and not c["ativo"]:
            continue

        if incompleto is not None and c["incompleto"] != incompleto:
            continue

        resultado.append(c)

    return resultado


def atualizar(
    dados,
    cliente_id,
    regime=None,
    nome=None,
    tipo_documento=None,
    numero_documento=None,
    nif=None,
    email=None,
    telefone=None,
    morada=None,
    nacionalidade=None,
    estado_civil=None,
    data_nascimento=None,
    validade_documento=None,
    contacto_emergencia=None,
):
    """Altera os dados de um cliente existente.

    Um parâmetro a None significa não alterar; "" significa limpar
    o conteúdo de um campo opcional (mesma convenção de
    propriedades.atualizar e unidades.atualizar). 'nome',
    'tipo_documento' e 'numero_documento' não podem ficar vazios —
    são obrigatórios em qualquer regime, tal como em criar(). Os
    restantes obrigatórios dependem do regime (ver validar_cliente)
    — tentar limpar um deles quando o regime exige preenchido é
    recusado por validar_cliente, antes de qualquer campo ser
    gravado.

    Recusa atualizar um cliente já anonimizado — a anonimização
    (decisão 8, RGPD, secção 6) é irreversível e apaga dados
    pessoais; sem esta guarda, esta função reintroduziria dados que
    a decisão 8 exige apagados. Mesma proteção que `reativar` já
    tem para o mesmo caso.

    'regime' não é guardado (não é campo do cliente, ver criar()).
    Serve só, nesta chamada, para reforçar quais campos são
    obrigatórios (decisão de 26/08). Omisso, assume-se "airbnb" —
    mesma convenção já usada abaixo para o NIF, agora estendida aos
    outros campos que dependem do regime.

    'data_nascimento' e 'validade_documento' só mudam quando um
    valor novo é fornecido; não há, nesta versão, forma de os voltar
    a limpar depois de preenchidos (limitação documentada) — e como
    os dois passaram a obrigatórios (decisão de 26/08), um cliente
    antigo que ainda não os tenha preenchido só volta a poder ser
    atualizado depois de os fornecer nesta mesma chamada.

    Devolve o registo atualizado.
    """
    cliente = procurar(dados, cliente_id)

    if cliente is None:
        raise ValueError(f"O cliente {cliente_id} não existe.")

    if cliente["anonimizado"]:
        raise ValueError(
            f"O cliente {cliente_id} está anonimizado e não pode "
            f"ser atualizado."
        )

    candidato = {
        "nome": (nome.strip() if nome is not None else cliente["nome"]),
        "tipo_documento": (
            tipo_documento.strip()
            if tipo_documento is not None
            else cliente["tipo_documento"]
        ),
        "numero_documento": (
            numero_documento.strip()
            if numero_documento is not None
            else cliente["numero_documento"]
        ),
        "nif": nif.strip() if nif is not None else cliente["nif"],
        "email": (email.strip() if email is not None else cliente["email"]),
        "telefone": (
            telefone.strip() if telefone is not None else cliente["telefone"]
        ),
        "morada": (
            morada.strip() if morada is not None else cliente["morada"]
        ),
        "nacionalidade": (
            nacionalidade.strip()
            if nacionalidade is not None
            else cliente["nacionalidade"]
        ),
        "estado_civil": (
            estado_civil.strip()
            if estado_civil is not None
            else cliente["estado_civil"]
        ),
        "data_nascimento": (
            data_nascimento
            if data_nascimento is not None
            else cliente["data_nascimento"]
        ),
        "validade_documento": (
            validade_documento
            if validade_documento is not None
            else cliente["validade_documento"]
        ),
    }

    regime_para_validar = regime if regime is not None else "airbnb"
    em_falta = validacoes.validar_cliente(candidato, regime_para_validar)

    if (
        regime_para_validar != "mensal"
        and candidato["nif"]
        and not validacoes.nif_valido(candidato["nif"])
    ):
        raise ValueError(f"NIF inválido: {candidato['nif']}")

    if _nif_pertence_a_outro_cliente(
        dados, candidato["nif"], ignorar_id=cliente_id
    ):
        raise ValueError(
            f"Já existe um cliente ativo com o NIF {candidato['nif']}."
        )

    cliente["nome"] = candidato["nome"]

    cliente["nome"] = candidato["nome"]
    cliente["tipo_documento"] = candidato["tipo_documento"]
    cliente["numero_documento"] = candidato["numero_documento"]
    cliente["nif"] = candidato["nif"]
    cliente["email"] = candidato["email"]
    cliente["telefone"] = candidato["telefone"]
    cliente["morada"] = candidato["morada"]
    cliente["nacionalidade"] = candidato["nacionalidade"]
    cliente["estado_civil"] = candidato["estado_civil"]
    cliente["incompleto"] = bool(em_falta)

    if data_nascimento is not None:
        cliente["data_nascimento"] = data_nascimento

    if validade_documento is not None:
        cliente["validade_documento"] = validade_documento

    if contacto_emergencia is not None:
        cliente["contacto_emergencia"] = contacto_emergencia.strip()

    return cliente


def desativar(dados, cliente_id):
    """Marca o cliente como inativo, sem o eliminar.

    Um cliente com ocupações associadas não pode desaparecer: os
    contratos históricos referem-se a ele (decisão 8). Desativar
    mantém o registo e tira-o das listagens de escolha, sem apagar
    nenhum dado pessoal — isso é o que distingue de `anonimizar`
    (ainda por escrever), que é irreversível e apaga dados.
    """

    cliente = procurar(dados, cliente_id)

    if cliente is None:
        raise ValueError(f"O cliente {cliente_id} não existe.")

    if not cliente["ativo"]:
        raise ValueError(f"O cliente {cliente_id} já está inativo.")

    cliente["ativo"] = False
    return cliente


def reativar(dados, cliente_id):
    """Repõe um cliente desativado como ativo.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar` — mas só da desativação
    simples: um cliente anonimizado (decisão 8, operação
    irreversível) não pode ser reativado por esta função, porque os
    dados pessoais já foram apagados e não há para onde voltar.

        Recusa também reativar se o NIF do cliente já pertencer, agora,
    a outro cliente ativo (item 6, 27/08) — sem esta verificação,
    dois clientes ativos podiam acabar com o mesmo NIF: um
    desativado, um novo criado entretanto com o mesmo NIF (permitido,
    porque o primeiro estava inativo — item 5), e o primeiro depois
    reativado sem que nada voltasse a cruzar os dois.
    """

    cliente = procurar(dados, cliente_id)

    if cliente is None:
        raise ValueError(f"O cliente {cliente_id} não existe.")

    if cliente["anonimizado"]:
        raise ValueError(
            f"O cliente {cliente_id} foi anonimizado e não pode ser "
            f"reativado."
        )

    if cliente["ativo"]:
        raise ValueError(f"O cliente {cliente_id} já está ativo.")

    if _nif_pertence_a_outro_cliente(
        dados, cliente["nif"], ignorar_id=cliente_id
    ):
        raise ValueError(
            f"Já existe um cliente ativo com o NIF {cliente['nif']} — "
            f"não é possível reativar."
        )

    cliente["ativo"] = True
    return cliente


def anonimizar(dados, cliente_id, responsavel_id, data):
    """Anonimiza um cliente, a pedido do titular ou por prazo excedido.

    Operação irreversível (decisão 8, RGPD, secção 6). Substitui o
    nome por "Titular anonimizado {ID}" e apaga email, telefone,
    morada, NIF, número de documento, validade do documento, data
    de nascimento e contacto de emergência. Conserva
    'nacionalidade' — não identifica o titular e tem valor
    estatístico. Conserva também 'tipo_documento' pela mesma razão
    (Cartão de Cidadão/Passaporte/etc. é categoria, não
    identificador). Contratos, datas e valores associados ao
    cliente nunca são alterados por esta função.

    Marca 'ativo' a False — a anonimização é uma das formas de um
    cliente deixar de estar ativo (ver comentário do campo em
    modelos.py). Um cliente anonimizado não pode ser reposto por
    'reativar()'.

    'responsavel_id' não é verificado contra responsaveis.py — esse
    módulo ainda não existe nesta fase do projeto. Fica a cargo de
    quem chamar (cli.py) confirmar que o responsável existe, quando
    esse módulo estiver escrito.
    """

    cliente = procurar(dados, cliente_id)

    if cliente is None:
        raise ValueError(f"O cliente {cliente_id} não existe.")

    if cliente["anonimizado"]:
        raise ValueError(f"O cliente {cliente_id} já está anonimizado.")

    responsavel_id = responsavel_id.strip()

    if not responsavel_id:
        raise ValueError("O responsável pela anonimização é obrigatório.")

    if data is None:
        raise ValueError("A data da anonimização é obrigatória.")

    cliente["nome"] = f"Titular anonimizado {cliente['id']}"
    cliente["email"] = ""
    cliente["telefone"] = ""
    cliente["morada"] = ""
    cliente["nif"] = ""
    cliente["numero_documento"] = ""
    cliente["validade_documento"] = None
    cliente["data_nascimento"] = None
    cliente["contacto_emergencia"] = ""

    cliente["incompleto"] = True
    cliente["anonimizado"] = True
    cliente["data_anonimizado"] = data
    cliente["responsavel_anonimizado_id"] = responsavel_id
    cliente["ativo"] = False

    return cliente
