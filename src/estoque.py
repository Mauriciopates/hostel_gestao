"""Gestão do stock — o armazém central que serve os responsáveis.

Seis entidades neste módulo: Produto (catálogo), Requisicao (pedido
do responsável, cabeçalho com quatro estados) e ItemRequisicao (um
produto e uma quantidade dentro dela), Devolucao (sobra devolvida
ao armazém, cabeçalho, entidade própria desde a decisão 19) e
ItemDevolucao (um produto e uma quantidade dentro dela), e
Movimento (registo imutável de entrada ou saída) — decisão 9. A
divisão cabeçalho/itens em Requisicao e Devolucao é da decisão 20:
uma requisição ou devolução pode juntar vários produtos de uma vez,
mas envia-se, recebe-se ou aceita-se sempre de uma só vez — nunca
item a item. Armazém central único, não distribuído: não há stock
por unidade.

Não acede a ficheiros nem à interface: devolve resultado e sinaliza
erro com `raise ValueError`.

MIGRAÇÃO MySQL (Fase 2): tal como `propriedades.py`, `unidades.py`,
`clientes.py`, `responsaveis.py` e `contratos.py`, este módulo já
não recebe nem devolve `dados` — fala diretamente com o MySQL
através do `repositorio.py` (inserir_produto, procurar_produto,
listar_produtos, atualizar_produto; inserir_movimento,
listar_movimentos; inserir_requisicao, procurar_requisicao,
listar_requisicoes, atualizar_requisicao; inserir_item_requisicao,
procurar_item_requisicao, listar_itens_requisicao,
atualizar_item_requisicao; inserir_devolucao, procurar_devolucao,
listar_devolucoes, atualizar_devolucao; inserir_item_devolucao,
procurar_item_devolucao, listar_itens_devolucao). O saldo de um
produto (`saldo_produto`) passa a somar
`repositorio.listar_movimentos(produto_id=...)` em vez de percorrer
`dados["movimentos"]` à mão — mesma lógica, fonte diferente.
"""

import repositorio
import responsaveis

PREFIXO = "PRD"
PREFIXO_MOVIMENTO = "MOV"
PREFIXO_REQUISICAO = "REQ"
PREFIXO_ITEM_REQUISICAO = "ITR"
PREFIXO_DEVOLUCAO = "DEV"
PREFIXO_ITEM_DEVOLUCAO = "ITD"


def criar_produto(nome, unidade_medida, stock_minimo=0):
    """Cria um produto no catálogo e grava-o imediatamente na base de
    dados.

    'stock_minimo' é o limiar de alerta de reposição — não bloqueia
    nada aqui, só fica guardado para quem, mais à frente, o for
    consultar. Não tem campo de quantidade: o saldo de um produto é
    sempre a soma dos seus movimentos, nunca um valor guardado
    (decisão 9) — é a mesma razão pela qual `Movimento` não vai ter
    `atualizar` nem `desativar` neste módulo.

    Devolve o registo criado. Grava de imediato via repositório —
    mesma convenção de propriedades.criar, unidades.criar,
    clientes.criar e responsaveis.criar, agora todos em MySQL.
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

    repositorio.inserir_produto(produto)
    return produto


def procurar_produto(produto_id):
    """Devolve o produto com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra inativos — procura, não decide (mesma
    convenção de propriedades.procurar, unidades.procurar,
    clientes.procurar e contratos.procurar).
    """
    return repositorio.procurar_produto(produto_id)


def listar_produtos(incluir_inativos=False):
    """Devolve os produtos, ativos ou todos se pedido.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção de propriedades.listar,
    unidades.listar, clientes.listar e contratos.listar).
    """
    return repositorio.listar_produtos(incluir_inativos=incluir_inativos)


def atualizar_produto(
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
    produto = procurar_produto(produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    campos = {}

    if nome is not None:
        nome = nome.strip()

        if not nome:
            raise ValueError("O nome do produto é obrigatório.")

        campos["nome"] = nome

    if unidade_medida is not None:
        unidade_medida = unidade_medida.strip()

        if not unidade_medida:
            raise ValueError("A unidade de medida é obrigatória.")

        campos["unidade_medida"] = unidade_medida

    if stock_minimo is not None:
        if not isinstance(stock_minimo, int) or isinstance(stock_minimo, bool):
            raise ValueError(
            f"O stock mínimo tem de ser um número inteiro: " f"{stock_minimo}"
            )

        if stock_minimo < 0:
            raise ValueError(
                f"O stock mínimo não pode ser negativo: " f"{stock_minimo}."
            )

        campos["stock_minimo"] = stock_minimo

    if campos:
        repositorio.atualizar_produto(produto_id, campos)
        produto.update(campos)

    return produto


def desativar_produto(produto_id):
    """Marca o produto como inativo, sem o eliminar.

    Um produto com movimentos ou requisições associadas não pode
    desaparecer: o histórico de stock refere-se a ele (decisão 8).
    Desativar mantém o registo e tira-o das listagens de escolha,
    sem apagar o histórico.
    """

    produto = procurar_produto(produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    if not produto["ativo"]:
        raise ValueError(f"O produto {produto_id} já está inativo.")

    repositorio.atualizar_produto(produto_id, {"ativo": False})
    produto["ativo"] = False
    return produto


def reativar_produto(produto_id):
    """Repõe um produto desativado como ativo.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar_produto`.
    """

    produto = procurar_produto(produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    if produto["ativo"]:
        raise ValueError(f"O produto {produto_id} já está ativo.")

    repositorio.atualizar_produto(produto_id, {"ativo": True})
    produto["ativo"] = True
    return produto


TIPOS_MOVIMENTO = ("entrada", "saida", "ajuste")


def registar_movimento(
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

    Grava de imediato via repositório — mesma convenção dos outros
    módulos de negócio, agora todos em MySQL.
    """
    produto = procurar_produto(produto_id)

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
        responsavel = responsaveis.validar_autoria(responsavel_id)
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

    repositorio.inserir_movimento(movimento)
    return movimento


def saldo_produto(produto_id):
    """Calcula o saldo atual de um produto, a partir dos movimentos.

    Nunca é um valor guardado (decisão 9): soma "entrada" e
    "ajuste" (já vem com o sinal certo), subtrai "saida". Percorre
    sempre todo o histórico do produto — não há atalho com um total
    intermédio guardado, porque isso seria voltar a ter um campo
    de quantidade fora dos movimentos.
    """
    produto = procurar_produto(produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    total = 0

    for m in repositorio.listar_movimentos(produto_id=produto_id):
        if m["tipo"] == "saida":
            total -= m["quantidade"]
        else:
            total += m["quantidade"]

    return total

def abaixo_do_minimo(produto_id):
    """Indica se o saldo do produto está abaixo do limiar de reposição.

    Dá uso ao 'stock_minimo' que criar_produto já guarda: até
    agora o campo era gravado e validado, mas nunca comparado com
    nada — a comparação vivia no cli.py, fora da camada de
    negócio (decisão 7).

    A comparação é estrita: um saldo igual ao mínimo ainda chega,
    só abaixo dele é que alerta. Um produto com 'stock_minimo' a
    zero nunca dispara, exceto com saldo negativo — que é sempre
    um problema, haja limiar ou não.

    Não filtra inativos: calcula, não decide. É a
    listar_alertas_stock que os exclui, porque um produto
    desativado não é para repor.

    Levanta ValueError se o produto não existir, com a mesma
    mensagem da saldo_produto.
    """
    produto = procurar_produto(produto_id)

    if produto is None:
        raise ValueError(f"O produto {produto_id} não existe.")

    return saldo_produto(produto_id) < produto["stock_minimo"]


def listar_alertas_stock():
    """Devolve os produtos ativos que estão abaixo do stock mínimo.

    Cada elemento é um dicionário novo com o registo do produto, o
    saldo e quanto falta para chegar ao mínimo. Nem 'saldo' nem
    'em_falta' existem na base de dados: são calculados a cada
    chamada, como manda a decisão 9 — nunca se guarda um total.

    Ordenada pelo que falta mais, do maior para o menor. A ordem é
    decisão de negócio, não de apresentação: o que falta mais é o
    que se repõe primeiro, e qualquer interface deve herdá-la sem
    a repetir.

    Só produtos ativos. Devolve lista vazia quando não há nada a
    repor.
    """
    alertas = []

    for produto in listar_produtos():
        saldo = saldo_produto(produto["id"])

        if saldo >= produto["stock_minimo"]:
            continue

        alertas.append(
            {
                "produto": produto,
                "saldo": saldo,
                "em_falta": produto["stock_minimo"] - saldo,
            }
        )

    alertas.sort(key=lambda a: a["em_falta"], reverse=True)

    return alertas


def _validar_inteiro(valor, nome):
    """Valida que 'valor' é um número inteiro (não bool) não nulo.

    Repete-se sempre que uma quantidade é lida de um item de
    requisição ou de devolução — 'nome' entra na frase do erro
    ("pedida", "enviada", "devolvida") para a mensagem continuar
    específica apesar de a verificação estar centralizada (decisão
    20). Não valida o sinal: cada ponto de chamada decide se aceita
    zero ou exige positivo.
    """
    if valor is None:
        raise ValueError(f"A quantidade {nome} é obrigatória.")

    if not isinstance(valor, int) or isinstance(valor, bool):
        raise ValueError(
            f"A quantidade {nome} tem de ser um número inteiro: "
            f"{valor}"
        )

    return valor


def criar_requisicao(
    responsavel_id,
    itens,
    data_pedido,
    observacoes="",
):
    """Cria uma requisição de material, no estado inicial "pendente".

    Primeiro dos quatro estados do fluxo (decisão 9, revista nas
    decisões 19 e 20): pendente → enviada → fechada, com "rejeitada"
    como saída alternativa a partir de pendente. Nada sai do
    armazém ainda — só quando `enviar_requisicao` aprovar o pedido
    é que se gera o primeiro movimento.

    'itens' é uma lista de dicionários no formato
    {"produto_id": ..., "quantidade_pedida": ...} — uma requisição
    pode pedir vários produtos de uma vez (decisão 20). Não pode
    vir vazia nem repetir o mesmo produto duas vezes: pedir mais
    desse produto é aumentar a quantidade no item existente, não
    criar um segundo.

    'responsavel_id' passa por `responsaveis.validar_autoria`: tem
    de existir e estar ativo, porque é ele quem assume a autoria do
    pedido (decisão 10) — mesma verificação que a anonimização de
    um cliente já exige a quem a regista.

    Não valida se há saldo suficiente dos produtos: o envio parcial
    é permitido (decisão 9), por isso pedir mais do que o stock
    atual não é, por si só, um erro nesta fase — só se torna
    relevante quando a requisição for enviada.

    Grava de imediato via repositório (cabeçalho e todos os itens)
    — mesma convenção dos outros módulos de negócio, agora todos em
    MySQL.
    """
    responsavel = responsaveis.validar_autoria(responsavel_id)

    if not itens:
        raise ValueError("A requisição tem de ter pelo menos um item.")

    produtos_vistos = set()

    for item in itens:
        produto_id = item.get("produto_id")
        produto = procurar_produto(produto_id)

        if produto is None:
            raise ValueError(f"O produto {produto_id} não existe.")

        if not produto["ativo"]:
            raise ValueError(f"O produto {produto_id} não está ativo.")

        if produto_id in produtos_vistos:
            raise ValueError(
                f"O produto {produto_id} está repetido na "
                f"requisição — some as quantidades num único item."
            )

        produtos_vistos.add(produto_id)

        quantidade_pedida = _validar_inteiro(
            item.get("quantidade_pedida"), "pedida"
        )

        if quantidade_pedida <= 0:
            raise ValueError("A quantidade pedida tem de ser positiva.")

    if data_pedido is None:
        raise ValueError("A data do pedido é obrigatória.")

    requisicao = {
        "id": repositorio.proximo_id(PREFIXO_REQUISICAO),
        "responsavel_id": responsavel["id"],
        "estado": "pendente",
        "data_pedido": data_pedido,
        "data_envio": None,
        "data_fecho": None,
        "responsavel_rejeicao_id": "",
        "motivo_rejeicao": "",
        "observacoes": observacoes.strip(),
    }

    repositorio.inserir_requisicao(requisicao)

    for item in itens:
        item_requisicao = {
            "id": repositorio.proximo_id(PREFIXO_ITEM_REQUISICAO),
            "requisicao_id": requisicao["id"],
            "produto_id": item["produto_id"],
            "quantidade_pedida": item["quantidade_pedida"],
            "quantidade_enviada": 0,
        }
        repositorio.inserir_item_requisicao(item_requisicao)

    return requisicao


def listar_itens_requisicao(requisicao_id=None, produto_id=None):
    """Devolve os itens de requisição, filtráveis por requisição e
    produto.

    'requisicao_id' e 'produto_id' filtram por um valor exato
    quando indicados; None (omisso) não filtra nesse campo — os
    filtros aplicam-se na própria consulta SQL, em
    `repositorio.listar_itens_requisicao`.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção dos `listar` dos outros
    módulos).
    """
    return repositorio.listar_itens_requisicao(
        requisicao_id=requisicao_id, produto_id=produto_id
    )


def procurar_item_requisicao(item_id):
    """Devolve o item de requisição com o identificador indicado, ou
    None.

    A ausência não é erro: quem chama decide se ela impede a
    operação (mesma convenção de procurar_requisicao).
    """
    return repositorio.procurar_item_requisicao(item_id)


def procurar_requisicao(requisicao_id):
    """Devolve a requisição com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra por estado — procura, não decide (mesma
    convenção de procurar_produto e dos `procurar` dos outros
    módulos).
    """
    return repositorio.procurar_requisicao(requisicao_id)


def enviar_requisicao(
    requisicao_id,
    enviado_por_id,
    data_envio,
    quantidades_enviadas=None,
):
    """Aprova e envia uma requisição pendente — pendente → enviada.

    Gera um movimento de saída por item (decisão 9), cada um a dar
    baixa no saldo do respetivo produto. 'enviado_por_id' é quem
    aprova e envia — não é necessariamente o mesmo responsável que
    pediu (esse é o 'responsavel_id' guardado em
    `criar_requisicao`); a Fase 1 não distingue papéis (decisão
    10), por isso os dois passam por `responsaveis.validar_autoria`,
    mas são parâmetros distintos.

    Envia-se a requisição toda de uma só vez — não há aprovação
    item a item (decisão 20). 'quantidades_enviadas', quando
    indicado, é um dicionário {produto_id: quantidade} para envio
    parcial de itens específicos; os produtos omissos nele são
    enviados na totalidade pedida. Omisso por completo, envia-se
    tudo na totalidade — o mesmo comportamento por omissão que já
    existia por item antes da decisão 20.

    Valida o saldo de todos os itens antes de gerar qualquer
    movimento: uma requisição não fica enviada a meio — ou há saldo
    para todos os itens nas quantidades pedidas para este envio, ou
    nenhum movimento é gerado e a requisição continua pendente.

    Grava de imediato via repositório — mesma convenção dos outros
    módulos de negócio, agora todos em MySQL.
    """
    requisicao = procurar_requisicao(requisicao_id)

    if requisicao is None:
        raise ValueError(f"A requisição {requisicao_id} não existe.")

    if requisicao["estado"] != "pendente":
        raise ValueError(
            f"A requisição {requisicao_id} não está pendente "
            f"(estado atual: {requisicao['estado']})."
        )

    quem_envia = responsaveis.validar_autoria(enviado_por_id)

    itens = listar_itens_requisicao(requisicao_id=requisicao_id)

    if quantidades_enviadas is not None:
        produtos_da_requisicao = {i["produto_id"] for i in itens}

        for produto_id in quantidades_enviadas:
            if produto_id not in produtos_da_requisicao:
                raise ValueError(
                    f"O produto {produto_id} não faz parte desta "
                    f"requisição."
                )

    a_enviar = []

    for item in itens:
        if quantidades_enviadas is not None:
            quantidade = quantidades_enviadas.get(
                item["produto_id"], item["quantidade_pedida"]
            )
        else:
            quantidade = item["quantidade_pedida"]

        _validar_inteiro(quantidade, "enviada")

        if quantidade <= 0:
            raise ValueError(
                "A quantidade enviada tem de ser positiva."
            )

        if quantidade > item["quantidade_pedida"]:
            raise ValueError(
                f"A quantidade enviada do produto "
                f"{item['produto_id']} não pode exceder a "
                f"quantidade pedida."
            )

        saldo = saldo_produto(item["produto_id"])

        if quantidade > saldo:
            raise ValueError(
                f"Saldo insuficiente do produto {item['produto_id']}: "
                f"{saldo} disponível, {quantidade} pedido para envio."
            )

        a_enviar.append((item, quantidade))

    if data_envio is None:
        raise ValueError("A data de envio é obrigatória.")

    for item, quantidade in a_enviar:
        registar_movimento(
            produto_id=item["produto_id"],
            tipo="saida",
            quantidade=quantidade,
            data=data_envio,
            responsavel_id=quem_envia["id"],
            requisicao_id=requisicao["id"],
        )
        repositorio.atualizar_item_requisicao(
            item["id"], {"quantidade_enviada": quantidade}
        )
        item["quantidade_enviada"] = quantidade

    campos = {"data_envio": data_envio, "estado": "enviada"}
    repositorio.atualizar_requisicao(requisicao_id, campos)
    requisicao.update(campos)

    return requisicao

def rejeitar_requisicao(requisicao_id, responsavel_id, motivo):
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

    Grava de imediato via repositório — mesma convenção dos outros
    módulos de negócio, agora todos em MySQL.
    """
    requisicao = procurar_requisicao(requisicao_id)

    if requisicao is None:
        raise ValueError(f"A requisição {requisicao_id} não existe.")

    if requisicao["estado"] != "pendente":
        raise ValueError(
            f"A requisição {requisicao_id} não está pendente "
            f"(estado atual: {requisicao['estado']})."
        )

    responsavel = responsaveis.validar_autoria(responsavel_id)

    motivo = motivo.strip()

    if not motivo:
        raise ValueError(
            "O motivo é obrigatório para rejeitar uma requisição."
        )

    campos = {
        "estado": "rejeitada",
        "motivo_rejeicao": motivo,
        "responsavel_rejeicao_id": responsavel["id"],
    }
    repositorio.atualizar_requisicao(requisicao_id, campos)
    requisicao.update(campos)

    return requisicao

def confirmar_rececao_requisicao(requisicao_id, responsavel_id, data_fecho):
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

    Grava de imediato via repositório — mesma convenção dos outros
    módulos de negócio, agora todos em MySQL.
    """
    requisicao = procurar_requisicao(requisicao_id)

    if requisicao is None:
        raise ValueError(f"A requisição {requisicao_id} não existe.")

    if requisicao["estado"] != "enviada":
        raise ValueError(
            f"A requisição {requisicao_id} não está enviada "
            f"(estado atual: {requisicao['estado']})."
        )

    responsavel = responsaveis.validar_autoria(responsavel_id)

    if responsavel["id"] != requisicao["responsavel_id"]:
        raise ValueError(
            f"Só o responsável que pediu "
            f"({requisicao['responsavel_id']}) pode confirmar a "
            f"receção desta requisição."
        )

    if data_fecho is None:
        raise ValueError("A data de receção é obrigatória.")

    campos = {"estado": "fechada", "data_fecho": data_fecho}
    repositorio.atualizar_requisicao(requisicao_id, campos)
    requisicao.update(campos)

    return requisicao

def reportar_devolucao(
    requisicao_id,
    responsavel_id,
    itens,
    data_reportada,
):
    """Reporta sobra de material de uma requisição já fechada.

    Entidade própria desde a decisão 19 — não é mais um passo da
    requisição, é um evento à parte que só existe quando sobra
    material por usar. Pode juntar vários produtos devolvidos de
    uma vez, cada um com a sua quantidade (decisão 20), simétrico a
    `criar_requisicao`.

    'itens' é uma lista de dicionários no formato
    {"produto_id": ..., "quantidade": ...}. Não pode vir vazia nem
    repetir o mesmo produto duas vezes. Cada quantidade tem de ser
    positiva: não sobrou nada não é uma devolução, é simplesmente
    não haver linha nenhuma a reportar para esse produto (era isto
    que aceitar zero, antes da decisão 19, obrigava a fingir que
    era).

    Mesma regra de identidade da versão anterior: só o responsável
    que pediu (e recebeu) pode reportar a sobra — é ele quem sabe o
    que sobrou.

    Cada produto devolvido tem de fazer parte da requisição
    original, e a sua quantidade não pode exceder o que ainda falta
    devolver dele — a quantidade enviada desse item, descontadas as
    devoluções já reportadas antes (pendentes ou fechadas), para
    impedir reportar sobra a mais do que o que foi mesmo enviado.

    O material devolvido ainda não conta no saldo (decisão 9): é
    trânsito real — saiu das mãos do responsável mas ainda não
    voltou fisicamente ao armazém. O movimento de entrada só é
    gerado em `fechar_devolucao`, quando o admin aceitar.

    Grava de imediato via repositório (cabeçalho e todos os itens)
    — mesma convenção dos outros módulos de negócio, agora todos em
    MySQL.
    """
    requisicao = procurar_requisicao(requisicao_id)

    if requisicao is None:
        raise ValueError(f"A requisição {requisicao_id} não existe.")

    if requisicao["estado"] != "fechada":
        raise ValueError(
            f"A requisição {requisicao_id} não está fechada "
            f"(estado atual: {requisicao['estado']})."
        )

    responsavel = responsaveis.validar_autoria(responsavel_id)

    if responsavel["id"] != requisicao["responsavel_id"]:
        raise ValueError(
            f"Só o responsável que pediu "
            f"({requisicao['responsavel_id']}) pode reportar "
            f"sobra desta requisição."
        )

    if not itens:
        raise ValueError("A devolução tem de ter pelo menos um item.")

    itens_requisicao = listar_itens_requisicao(requisicao_id=requisicao_id)
    itens_por_produto = {i["produto_id"]: i for i in itens_requisicao}

    devolucao_ids_existentes = {
        d["id"] for d in listar_devolucoes(requisicao_id=requisicao_id)
    }

    ja_reportado_por_produto = {}

    for devolucao_id in devolucao_ids_existentes:
        for item_dev in listar_itens_devolucao(devolucao_id=devolucao_id):
            ja_reportado_por_produto[item_dev["produto_id"]] = (
                ja_reportado_por_produto.get(item_dev["produto_id"], 0)
                + item_dev["quantidade"]
            )

    produtos_vistos = set()

    for item in itens:
        produto_id = item.get("produto_id")

        if produto_id not in itens_por_produto:
            raise ValueError(
                f"O produto {produto_id} não faz parte da "
                f"requisição {requisicao_id}."
            )

        if produto_id in produtos_vistos:
            raise ValueError(
                f"O produto {produto_id} está repetido na "
                f"devolução — some as quantidades num único item."
            )

        produtos_vistos.add(produto_id)

        quantidade = _validar_inteiro(item.get("quantidade"), "devolvida")

        if quantidade <= 0:
            raise ValueError(
                "A quantidade devolvida tem de ser positiva — sem "
                "sobra não há devolução a reportar."
            )

        ja_reportado = ja_reportado_por_produto.get(produto_id, 0)
        quantidade_enviada = itens_por_produto[produto_id][
            "quantidade_enviada"
        ]

        if ja_reportado + quantidade > quantidade_enviada:
            raise ValueError(
                f"A quantidade devolvida do produto {produto_id} "
                f"não pode exceder a quantidade enviada."
            )

    if data_reportada is None:
        raise ValueError("A data de devolução é obrigatória.")

    devolucao = {
        "id": repositorio.proximo_id(PREFIXO_DEVOLUCAO),
        "requisicao_id": requisicao_id,
        "responsavel_id": responsavel["id"],
        "estado": "pendente",
        "data_reportada": data_reportada,
        "data_fecho": None,
    }

    repositorio.inserir_devolucao(devolucao)

    for item in itens:
        item_devolucao = {
            "id": repositorio.proximo_id(PREFIXO_ITEM_DEVOLUCAO),
            "devolucao_id": devolucao["id"],
            "produto_id": item["produto_id"],
            "quantidade": item["quantidade"],
        }
        repositorio.inserir_item_devolucao(item_devolucao)

    return devolucao


def listar_itens_devolucao(devolucao_id=None, produto_id=None):
    """Devolve os itens de devolução, filtráveis por devolução e
    produto.

    'devolucao_id' e 'produto_id' filtram por um valor exato quando
    indicados; None (omisso) não filtra nesse campo — os filtros
    aplicam-se na própria consulta SQL, em
    `repositorio.listar_itens_devolucao`.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção dos `listar` dos outros
    módulos).
    """
    return repositorio.listar_itens_devolucao(
        devolucao_id=devolucao_id, produto_id=produto_id
    )


def procurar_item_devolucao(item_id):
    """Devolve o item de devolução com o identificador indicado, ou
    None.

    A ausência não é erro: quem chama decide se ela impede a
    operação (mesma convenção de procurar_devolucao).
    """
    return repositorio.procurar_item_devolucao(item_id)


def procurar_devolucao(devolucao_id):
    """Devolve a devolução com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra por estado — procura, não decide (mesma
    convenção de procurar_requisicao e dos `procurar` dos outros
    módulos).
    """
    return repositorio.procurar_devolucao(devolucao_id)

def listar_devolucoes(estado=None, requisicao_id=None, responsavel_id=None):
    """Devolve as devoluções, filtráveis por estado, requisição e
    responsável.

    'estado' filtra por um valor exato quando indicado; None
    (omisso) não filtra — mesma convenção de listar_requisicoes. Os
    filtros aplicam-se na própria consulta SQL, em
    `repositorio.listar_devolucoes`.

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção dos `listar` dos outros
    módulos).
    """
    return repositorio.listar_devolucoes(
        estado=estado,
        requisicao_id=requisicao_id,
        responsavel_id=responsavel_id,
    )

def fechar_devolucao(devolucao_id, aceite_por_id, data_fecho):
    """Aceita uma devolução — pendente → fechada.

    Gera um movimento de entrada por item (decisão 9, decisão 20) —
    só agora se repõe o saldo de cada produto: enquanto a devolução
    estava pendente, o material estava em trânsito, fora do armazém
    e fora do saldo (ver `reportar_devolucao`).

    Aceita-se a devolução toda de uma só vez — não há aceitação
    item a item (decisão 20), simétrico ao envio da requisição.

    'aceite_por_id' é quem aceita a devolução no armazém — como em
    `enviar_requisicao`, não tem de ser o mesmo responsável que
    pediu ou que devolveu, só precisa de estar ativo.

    Grava de imediato via repositório — mesma convenção dos outros
    módulos de negócio, agora todos em MySQL.
    """
    devolucao = procurar_devolucao(devolucao_id)

    if devolucao is None:
        raise ValueError(f"A devolução {devolucao_id} não existe.")

    if devolucao["estado"] != "pendente":
        raise ValueError(
            f"A devolução {devolucao_id} não está pendente "
            f"(estado atual: {devolucao['estado']})."
        )

    aceite = responsaveis.validar_autoria(aceite_por_id)

    if data_fecho is None:
        raise ValueError("A data de fecho é obrigatória.")

    itens = listar_itens_devolucao(devolucao_id=devolucao_id)

    for item in itens:
        registar_movimento(
            produto_id=item["produto_id"],
            tipo="entrada",
            quantidade=item["quantidade"],
            data=data_fecho,
            responsavel_id=aceite["id"],
            requisicao_id=devolucao["requisicao_id"],
        )

    campos = {"estado": "fechada", "data_fecho": data_fecho}
    repositorio.atualizar_devolucao(devolucao_id, campos)
    devolucao.update(campos)

    return devolucao

def listar_requisicoes(estado=None, responsavel_id=None, produto_id=None):
    """Devolve as requisições, filtráveis por estado, responsável e
    produto.

    Não tem filtro de "incluir_inativos" — Requisicao não tem campo
    'ativo' (decisão 8 não se aplica aqui): o ciclo de vida é o
    estado, um dos quatro valores do fluxo, nunca uma requisição
    "desativada". 'estado' e 'responsavel_id' filtram por um valor
    exato quando indicados; None (omisso) não filtra — mesma
    convenção do 'incompleto' em clientes.listar e do 'tipo' em
    contratos.listar. Estes dois filtros aplicam-se na própria
    consulta SQL, em `repositorio.listar_requisicoes`.

    'produto_id', desde a decisão 20, já não é um campo da
    requisição — filtra pelas requisições que têm pelo menos um
    item desse produto, através de `listar_itens_requisicao`. Este
    cruzamento continua a ser feito aqui, não em `repositorio.py`
    (mesmo princípio de `contratos._nif_tem_contrato_mensal_ativo`,
    que cruza com `clientes` em vez de virar SQL na camada de
    persistência).

    Devolve lista nova, para que alterá-la depois não afete a
    estrutura de dados (mesma convenção de listar_produtos e dos
    `listar` dos outros módulos).
    """
    requisicoes_com_produto = None

    if produto_id is not None:
        requisicoes_com_produto = {
            item["requisicao_id"]
            for item in listar_itens_requisicao(produto_id=produto_id)
        }

    resultado = repositorio.listar_requisicoes(
        estado=estado, responsavel_id=responsavel_id
    )

    if requisicoes_com_produto is not None:
        resultado = [
            r for r in resultado if r["id"] in requisicoes_com_produto
        ]

    return resultado