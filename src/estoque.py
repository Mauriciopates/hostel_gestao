"""Gestão do stock — o armazém central que serve os responsáveis.

Quatro entidades neste módulo: Produto (catálogo), Requisicao
(pedido do responsável, com quatro estados), Devolucao (sobra
devolvida ao armazém, entidade própria desde a decisão 19) e
Movimento (registo imutável de entrada ou saída) — decisão 9.
Armazém central único, não distribuído: não há stock por unidade.

Não acede a ficheiros nem à interface: recebe a estrutura de dados,
devolve resultado e sinaliza erro com `raise ValueError`. Quem
carrega e grava é o `main.py`, através do repositório.
"""

import repositorio
import responsaveis

PREFIXO = "PRD"
PREFIXO_MOVIMENTO = "MOV"
PREFIXO_REQUISICAO = "REQ"
PREFIXO_DEVOLUCAO = "DEV"


def criar_produto(dados, nome, unidade_medida, stock_minimo=0):
    """Cria um produto no catálogo e acrescenta-o à estrutura de dados.

    'stock_minimo' é o limiar de alerta de reposição — não bloqueia
    nada aqui, só fica guardado para quem, mais à frente, o for
    consultar. Não tem campo de quantidade: o saldo de um produto é
    sempre a soma dos seus movimentos, nunca um valor guardado
    (decisão 9) — é a mesma razão pela qual `Movimento` não vai ter
    `atualizar` nem `desativar` neste módulo.

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção de propriedades.criar, unidades.criar e
    clientes.criar).
    """
    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do produto é obrigatório.")

    unidade_medida = unidade_medida.strip()

    if not unidade_medida:
        raise ValueError("A unidade de medida é obrigatória.")

    if not isinstance(stock_minimo, int) or isinstance(stock_minimo, bool):
        raise ValueError(
            f"O stock mínimo tem de ser um número inteiro: " f"{stock_minimo}"
        )

    if stock_minimo < 0:
        raise ValueError(
            f"O stock mínimo não pode ser negativo: {stock_minimo}."
            )

    produto = {
        "id": repositorio.proximo_id(PREFIXO),
        "nome": nome,
        "unidade_medida": unidade_medida,
        "stock_minimo": stock_minimo,
        "ativo": True,
    }

    dados["produtos"].append(produto)
    return produto


def procurar_produto(dados, produto_id):
    """Devolve o produto com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos — procura, não decide (mesma
    convenção de propriedades.procurar, unidades.procurar,
    clientes.procurar e contratos.procurar).
    """

    for p in dados["produtos"]:
        if p["id"] == produto_id:
            return p

    return None


def listar_produtos(dados, incluir_inativos=False):
    """Devolve os produtos, ativos ou todos se pedido.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção de propriedades.listar,
    unidades.listar, clientes.listar e contratos.listar).
    """

    resultado = []

    for p in dados["produtos"]:
        if incluir_inativos or p["ativo"]:
            resultado.append(p)

    return resultado


def atualizar_produto(
    dados,
    produto_id,
    nome=None,
    unidade_medida=None,
    stock_minimo=None,
):
    """Altera o nome, a unidade de medida ou o stock mínimo de um
    produto existente.

    Um parâmetro a None significa não alterar (mesma convenção de
    propriedades.atualizar, unidades.atualizar e
    clientes.atualizar). 'nome' e 'unidade_medida' não podem ficar
    vazios — são obrigatórios, tal como em criar_produto().
    """
    produto = procurar_produto(dados, produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome do produto é obrigatório.")

        produto["nome"] = nome

    if unidade_medida is not None:
        unidade_medida = unidade_medida.strip()

        if not unidade_medida:
            raise ValueError("A unidade de medida é obrigatória.")

        produto["unidade_medida"] = unidade_medida

    if stock_minimo is not None:
        if not isinstance(stock_minimo, int) or isinstance(stock_minimo, bool):
            raise ValueError(
            f"O stock mínimo tem de ser um número inteiro: " f"{stock_minimo}"
            )

        if stock_minimo < 0:
            raise ValueError(
                f"O stock mínimo não pode ser negativo: " f"{stock_minimo}."
            )

        produto["stock_minimo"] = stock_minimo

    return produto


def desativar_produto(dados, produto_id):
    """Marca o produto como inativo, sem o eliminar.

    Um produto com movimentos ou requisições associadas não pode
    desaparecer: o histórico de stock refere-se a ele (decisão 8).
    Desativar mantém o registo e tira-o das listagens de escolha,
    sem apagar o histórico.
    """

    produto = procurar_produto(dados, produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    if not produto["ativo"]:
        raise ValueError(f"O produto {produto_id} já está inativo.")

    produto["ativo"] = False
    return produto


def reativar_produto(dados, produto_id):
    """Repõe um produto desativado como ativo.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar_produto`.
    """

    produto = procurar_produto(dados, produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    if produto["ativo"]:
        raise ValueError(f"O produto {produto_id} já está ativo.")

    produto["ativo"] = True
    return produto


TIPOS_MOVIMENTO = ("entrada", "saida", "ajuste")


def registar_movimento(
    dados,
    produto_id,
    tipo,
    quantidade,
    data,
    responsavel_id="",
    requisicao_id="",
    motivo="",
):
    """Regista um movimento de stock — entrada, saída ou ajuste.

    Movimentos são imutáveis (decisão 9): não há `atualizar` nem
    `desativar` nesta função — uma correção a um movimento já
    registado faz-se com um novo movimento de ajuste, nunca
    alterando o antigo.

    'quantidade' é sempre positiva para "entrada" e "saida" — o
    sinal do movimento vem do 'tipo', não do valor. Para "ajuste"
    pode ser negativa, porque um ajuste tanto corrige um excesso
    registado a mais como uma falta; por isso o motivo é
    obrigatório só neste caso (decisão 9).

    'responsavel_id' é opcional (ex.: carregamento inicial de
    stock, sem uma pessoa concreta a apontar) — mas quando vem
    preenchido, passa por `responsaveis.validar_autoria`: tem de
    existir e estar ativo, mesma verificação que `criar_requisicao`
    já exige, para que o histórico de stock nunca fique associado a
    um responsável inexistente ou desativado.

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção dos outros módulos de negócio).
    """
    produto = procurar_produto(dados, produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    if tipo not in TIPOS_MOVIMENTO:
        raise ValueError(f"Tipo de movimento desconhecido: {tipo}")

    if quantidade is None:
        raise ValueError("A quantidade é obrigatória.")

    if not isinstance(quantidade, int) or isinstance(quantidade, bool):
        raise ValueError(
            f"A quantidade tem de ser um número inteiro: " f"{quantidade}"
        )

    if quantidade == 0:
        raise ValueError("A quantidade não pode ser zero.")

    if tipo in ("entrada", "saida") and quantidade < 0:
        raise ValueError(
            f"A quantidade tem de ser positiva num movimento de " f"{tipo}."
        )

    if data is None:
        raise ValueError("A data do movimento é obrigatória.")

    motivo = motivo.strip()

    if tipo == "ajuste" and not motivo:
        raise ValueError("O motivo é obrigatório num movimento de ajuste.")

    responsavel_id = responsavel_id.strip()

    if responsavel_id:
        responsavel = responsaveis.validar_autoria(dados, responsavel_id)
        responsavel_id = responsavel["id"]

    movimento = {
        "id": repositorio.proximo_id(PREFIXO_MOVIMENTO),
        "produto_id": produto_id,
        "tipo": tipo,
        "quantidade": quantidade,
        "data": data,
        "responsavel_id": responsavel_id,
        "requisicao_id": requisicao_id.strip(),
        "motivo": motivo,
    }

    dados["movimentos"].append(movimento)
    return movimento


def saldo_produto(dados, produto_id):
    """Calcula o saldo atual de um produto, a partir dos movimentos.

    Nunca é um valor guardado (decisão 9): soma "entrada" e
    "ajuste" (já vem com o sinal certo), subtrai "saida". Percorre
    sempre todo o histórico — não há atalho com um total
    intermédio guardado, porque isso seria voltar a ter um campo
    de quantidade fora dos movimentos.
    """
    produto = procurar_produto(dados, produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    total = 0

    for m in dados["movimentos"]:
        if m["produto_id"] != produto_id:
            continue

        if m["tipo"] == "saida":
            total -= m["quantidade"]
        else:
            total += m["quantidade"]

    return total


def criar_requisicao(
    dados,
    responsavel_id,
    produto_id,
    quantidade_pedida,
    data_pedido,
    observacoes="",
):
    """Cria uma requisição de material, no estado inicial "pendente".

    Primeiro dos quatro estados do fluxo (decisão 9, revista na
    decisão 19): pendente → enviada → fechada, com "rejeitada" como
    saída alternativa a partir de pendente. Nada sai do armazém
    ainda — só quando `enviar_requisicao` aprovar o pedido é que se
    gera o primeiro movimento.

    'responsavel_id' passa por `responsaveis.validar_autoria`: tem
    de existir e estar ativo, porque é ele quem assume a autoria do
    pedido (decisão 10) — mesma verificação que a anonimização de
    um cliente já exige a quem a regista.

    Não valida se há saldo suficiente do produto: o envio parcial é
    permitido (decisão 9), por isso pedir mais do que o stock atual
    não é, por si só, um erro nesta fase — só se torna relevante
    quando a requisição for enviada.

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção dos outros módulos de negócio).
    """
    responsavel = responsaveis.validar_autoria(dados, responsavel_id)

    produto = procurar_produto(dados, produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    if not produto["ativo"]:
        raise ValueError(f"O produto {produto_id} não está ativo.")

    if quantidade_pedida is None:
        raise ValueError("A quantidade pedida é obrigatória.")

    if (
        not isinstance(quantidade_pedida, int) 
        or isinstance(quantidade_pedida, bool)
    ):
        
        raise ValueError(
            f"A quantidade pedida tem de ser um número inteiro: "
            f"{quantidade_pedida}"
        )

    if quantidade_pedida <= 0:
        raise ValueError("A quantidade pedida tem de ser positiva.")

    if data_pedido is None:
        raise ValueError("A data do pedido é obrigatória.")

    requisicao = {
        "id": repositorio.proximo_id(PREFIXO_REQUISICAO),
        "responsavel_id": responsavel["id"],
        "produto_id": produto_id,
        "quantidade_pedida": quantidade_pedida,
        "estado": "pendente",
        "quantidade_enviada": 0,
        "data_pedido": data_pedido,
        "data_envio": None,
        "data_fecho": None,
        "motivo_rejeicao": "",
        "observacoes": observacoes.strip(),
    }

    dados["requisicoes"].append(requisicao)
    return requisicao

def procurar_requisicao(dados, requisicao_id):
    """Devolve a requisição com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra por estado — procura, não decide (mesma
    convenção de procurar_produto e dos `procurar` dos outros
    módulos).
    """

    for r in dados["requisicoes"]:
        if r["id"] == requisicao_id:
            return r

    return None


def enviar_requisicao(
    dados,
    requisicao_id,
    enviado_por_id,
    data_envio,
    quantidade_enviada=None,
):
    """Aprova e envia uma requisição pendente — pendente → enviada.

    Gera o primeiro movimento de stock do fluxo: uma saída, que dá
    baixa no saldo do produto (decisão 9). 'enviado_por_id' é quem
    aprova e envia — não é necessariamente o mesmo responsável que
    pediu (esse é o 'responsavel_id' guardado em
    `criar_requisicao`); a Fase 1 não distingue papéis (decisão
    10), por isso os dois passam por `responsaveis.validar_autoria`,
    mas são parâmetros distintos.

    'quantidade_enviada' pode ser menor do que a quantidade pedida
    — envio parcial é permitido (decisão 9) e fecha logo neste
    estado com a quantidade que foi mesmo enviada, sem deixar
    pendência aberta para o resto. Omissa, envia-se a quantidade
    pedida na totalidade.

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção dos outros módulos de negócio).
    """
    requisicao = procurar_requisicao(dados, requisicao_id)

    if requisicao is None:
        raise ValueError(f"A requisição {requisicao_id} não existe.")

    if requisicao["estado"] != "pendente":
        raise ValueError(
            f"A requisição {requisicao_id} não está pendente "
            f"(estado atual: {requisicao['estado']})."
        )

    quem_envia = responsaveis.validar_autoria(dados, enviado_por_id)

    if quantidade_enviada is None:
        quantidade_enviada = requisicao["quantidade_pedida"]

    if (
        not isinstance(quantidade_enviada, int)
        or isinstance(quantidade_enviada, bool)
    ):
        raise ValueError(
            f"A quantidade enviada tem de ser um número inteiro: "
            f"{quantidade_enviada}"
        )

    if quantidade_enviada <= 0:
        raise ValueError("A quantidade enviada tem de ser positiva.")

    if quantidade_enviada > requisicao["quantidade_pedida"]:
        raise ValueError(
            "A quantidade enviada não pode exceder a quantidade "
            "pedida."
        )

    saldo = saldo_produto(dados, requisicao["produto_id"])

    if quantidade_enviada > saldo:
        raise ValueError(
            f"Saldo insuficiente do produto "
            f"{requisicao['produto_id']}: {saldo} disponível, "
            f"{quantidade_enviada} pedido para envio."
        )

    if data_envio is None:
        raise ValueError("A data de envio é obrigatória.")

    registar_movimento(
        dados,
        produto_id=requisicao["produto_id"],
        tipo="saida",
        quantidade=quantidade_enviada,
        data=data_envio,
        responsavel_id=quem_envia["id"],
        requisicao_id=requisicao["id"],
    )

    requisicao["quantidade_enviada"] = quantidade_enviada
    requisicao["data_envio"] = data_envio
    requisicao["estado"] = "enviada"

    return requisicao

def rejeitar_requisicao(dados, requisicao_id, responsavel_id, motivo):
    """Rejeita uma requisição pendente — pendente → rejeitada.

    Saída alternativa a partir de "pendente" (decisão 9), distinta
    do fluxo normal de envio: não gera nenhum movimento de stock,
    porque nada chegou a sair do armazém.

    O motivo é obrigatório — sem ele, "rejeitada" fica
    indistinguível de um estado sem explicação, e a decisão 9 é
    explícita: "o admin recusou o pedido, com motivo".

    'responsavel_id' passa por `responsaveis.validar_autoria` e
    fica gravado em 'responsavel_rejeicao_id' — pela mesma razão de
    auditoria já usada em `responsavel_anonimizado_id`
    (clientes.anonimizar): sem guardar quem rejeitou, não há como
    responder depois "quem recusou este pedido".

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção dos outros módulos de negócio).
    """
    requisicao = procurar_requisicao(dados, requisicao_id)

    if requisicao is None:
        raise ValueError(f"A requisição {requisicao_id} não existe.")

    if requisicao["estado"] != "pendente":
        raise ValueError(
            f"A requisição {requisicao_id} não está pendente "
            f"(estado atual: {requisicao['estado']})."
        )

    responsavel = responsaveis.validar_autoria(dados, responsavel_id)

    motivo = motivo.strip()

    if not motivo:
        raise ValueError(
            "O motivo é obrigatório para rejeitar uma requisição."
        )

    requisicao["estado"] = "rejeitada"
    requisicao["motivo_rejeicao"] = motivo
    requisicao["responsavel_rejeicao_id"] = responsavel["id"]

    return requisicao

def confirmar_rececao_requisicao(
    dados, requisicao_id, responsavel_id, data_fecho
):
    """Confirma a receção de uma requisição — enviada → fechada.

    Só o responsável que pediu confirma a receção (decisão 9,
    reforçada no docstring de `Requisicao` em modelos.py): "esta
    confirmação é dele, não do admin — quem pede é quem sabe se
    recebeu". Por isso 'responsavel_id' tem de corresponder ao
    'responsavel_id' gravado em `criar_requisicao`, não a qualquer
    responsável ativo — ao contrário de `enviar_requisicao`, em que
    'enviado_por_id' podia ser qualquer um.

    O fecho é automático nesse momento (decisão 19): a requisição
    deixa de ficar à espera de devolução. Se sobrar material, isso
    passa a ser reportado à parte, com `reportar_devolucao`, sem
    bloquear o fecho desta.

    Não gera movimento: a saída já foi registada em
    `enviar_requisicao`. Confirmar a receção não altera o saldo, só
    o estado da requisição.

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção dos outros módulos de negócio).
    """
    requisicao = procurar_requisicao(dados, requisicao_id)

    if requisicao is None:
        raise ValueError(f"A requisição {requisicao_id} não existe.")

    if requisicao["estado"] != "enviada":
        raise ValueError(
            f"A requisição {requisicao_id} não está enviada "
            f"(estado atual: {requisicao['estado']})."
        )

    responsavel = responsaveis.validar_autoria(dados, responsavel_id)

    if responsavel["id"] != requisicao["responsavel_id"]:
        raise ValueError(
            f"Só o responsável que pediu "
            f"({requisicao['responsavel_id']}) pode confirmar a "
            f"receção desta requisição."
        )

    if data_fecho is None:
        raise ValueError("A data de receção é obrigatória.")

    requisicao["estado"] = "fechada"
    requisicao["data_fecho"] = data_fecho

    return requisicao

def reportar_devolucao(
    dados,
    requisicao_id,
    responsavel_id,
    quantidade,
    data_reportada,
):
    """Reporta sobra de material de uma requisição já fechada.

    Entidade própria desde a decisão 19 — não é mais um passo da
    requisição, é um evento à parte que só existe quando sobra
    material por usar. Por isso 'quantidade' tem de ser positiva:
    não sobrou nada não é uma devolução, é simplesmente não haver
    devolução nenhuma a reportar (era isto que aceitar zero, na
    versão anterior, obrigava a fingir que era).

    Mesma regra de identidade da versão anterior: só o responsável
    que pediu (e recebeu) pode reportar a sobra — é ele quem sabe o
    que sobrou.

    'quantidade' não pode exceder o que ainda falta devolver desta
    requisição — a quantidade enviada, descontadas as devoluções já
    reportadas antes (pendentes ou fechadas), para impedir reportar
    sobra a mais do que o que foi mesmo enviado.

    O material devolvido ainda não conta no saldo (decisão 9): é
    trânsito real — saiu das mãos do responsável mas ainda não
    voltou fisicamente ao armazém. O movimento de entrada só é
    gerado em `fechar_devolucao`, quando o admin aceitar.

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção dos outros módulos de negócio).
    """
    requisicao = procurar_requisicao(dados, requisicao_id)

    if requisicao is None:
        raise ValueError(f"A requisição {requisicao_id} não existe.")

    if requisicao["estado"] != "fechada":
        raise ValueError(
            f"A requisição {requisicao_id} não está fechada "
            f"(estado atual: {requisicao['estado']})."
        )

    responsavel = responsaveis.validar_autoria(dados, responsavel_id)

    if responsavel["id"] != requisicao["responsavel_id"]:
        raise ValueError(
            f"Só o responsável que pediu "
            f"({requisicao['responsavel_id']}) pode reportar "
            f"sobra desta requisição."
        )

    if not isinstance(quantidade, int) or isinstance(quantidade, bool):
        raise ValueError(
            f"A quantidade devolvida tem de ser um número inteiro: "
            f"{quantidade}"
        )

    if quantidade <= 0:
        raise ValueError(
            "A quantidade devolvida tem de ser positiva — sem "
            "sobra não há devolução a reportar."
        )

    ja_reportado = sum(
        d["quantidade"]
        for d in dados["devolucoes"]
        if d["requisicao_id"] == requisicao_id
    )

    if ja_reportado + quantidade > requisicao["quantidade_enviada"]:
        raise ValueError(
            "A quantidade devolvida não pode exceder a quantidade "
            "enviada."
        )

    if data_reportada is None:
        raise ValueError("A data de devolução é obrigatória.")

    devolucao = {
        "id": repositorio.proximo_id(PREFIXO_DEVOLUCAO),
        "requisicao_id": requisicao_id,
        "responsavel_id": responsavel["id"],
        "quantidade": quantidade,
        "estado": "pendente",
        "data_reportada": data_reportada,
        "data_fecho": None,
    }

    dados["devolucoes"].append(devolucao)
    return devolucao

def procurar_devolucao(dados, devolucao_id):
    """Devolve a devolução com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra por estado — procura, não decide (mesma
    convenção de procurar_requisicao e dos `procurar` dos outros
    módulos).
    """

    for d in dados["devolucoes"]:
        if d["id"] == devolucao_id:
            return d

    return None

def listar_devolucoes(
    dados, estado=None, requisicao_id=None, responsavel_id=None
):
    """Devolve as devoluções, filtráveis por estado, requisição e
    responsável.

    'estado' filtra por um valor exato quando indicado; None
    (omisso) não filtra — mesma convenção de listar_requisicoes.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção dos `listar` dos outros
    módulos).
    """

    resultado = []

    for d in dados["devolucoes"]:
        if estado is not None and d["estado"] != estado:
            continue

        if (
            requisicao_id is not None
            and d["requisicao_id"] != requisicao_id
        ):
            continue

        if (
            responsavel_id is not None
            and d["responsavel_id"] != responsavel_id
        ):
            continue

        resultado.append(d)

    return resultado

def fechar_devolucao(dados, devolucao_id, aceite_por_id, data_fecho):
    """Aceita uma devolução — pendente → fechada.

    Só agora se gera o movimento de entrada que repõe o saldo —
    enquanto a devolução estava pendente, o material estava em
    trânsito, fora do armazém e fora do saldo (ver
    `reportar_devolucao`).

    'aceite_por_id' é quem aceita a devolução no armazém — como em
    `enviar_requisicao`, não tem de ser o mesmo responsável que
    pediu ou que devolveu, só precisa de estar ativo.

    Não grava: a gravação é decidida pelo `main.py` (mesma
    convenção dos outros módulos de negócio).
    """
    devolucao = procurar_devolucao(dados, devolucao_id)

    if devolucao is None:
        raise ValueError(f"A devolução {devolucao_id} não existe.")

    if devolucao["estado"] != "pendente":
        raise ValueError(
            f"A devolução {devolucao_id} não está pendente "
            f"(estado atual: {devolucao['estado']})."
        )

    aceite = responsaveis.validar_autoria(dados, aceite_por_id)

    if data_fecho is None:
        raise ValueError("A data de fecho é obrigatória.")

    requisicao = procurar_requisicao(dados, devolucao["requisicao_id"])

    if requisicao is None:
        raise ValueError(
            f"A requisição {devolucao['requisicao_id']} associada a "
            f"esta devolução não existe."
        )

    registar_movimento(
        dados,
        produto_id=requisicao["produto_id"],
        tipo="entrada",
        quantidade=devolucao["quantidade"],
        data=data_fecho,
        responsavel_id=aceite["id"],
        requisicao_id=requisicao["id"],
    )

    devolucao["estado"] = "fechada"
    devolucao["data_fecho"] = data_fecho

    return devolucao

def listar_requisicoes(
    dados, estado=None, responsavel_id=None, produto_id=None
):
    """Devolve as requisições, filtráveis por estado, responsável e
    produto.

    Não tem filtro de "incluir_inativos" — Requisicao não tem campo
    'ativo' (decisão 8 não se aplica aqui): o ciclo de vida é o
    estado, um dos quatro valores do fluxo, nunca uma requisição
    "desativada". 'estado' filtra por um valor exato quando
    indicado; None (omisso) não filtra — mesma convenção do
    'incompleto' em clientes.listar e do 'tipo' em contratos.listar.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção de listar_produtos e dos
    `listar` dos outros módulos).
    """

    resultado = []

    for r in dados["requisicoes"]:
        if estado is not None and r["estado"] != estado:
            continue

        if (
            responsavel_id is not None
            and r["responsavel_id"] != responsavel_id
        ):
            continue

        if produto_id is not None and r["produto_id"] != produto_id:
            continue

        resultado.append(r)

    return resultado