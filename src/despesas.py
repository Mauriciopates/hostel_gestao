"""Gestão de despesas — saídas reais de dinheiro do sistema.

Este é o módulo financeiro de escrita. Cobre despesas manuais (EDP,
água, internet, obras), despesas via stock (compra de produtos para
o armazém), divisão automática por propriedade (caso da internet
contratada uma vez por prédio), recorrência mensal (a despesa gera
sozinha a do mês seguinte), e a gestão das tabelas de apoio
(categorias_despesa e fornecedores).

CONCEITO CENTRAL — as DUAS VIAS de lançar uma despesa:

  VIA 1 — Despesa manual. Sem itens de produto. Nasce `pendente`.
          Exemplos: EDP, água, internet, obras. `itens_confirmados`
          nasce True (nada a confirmar). O Master/Admin marca como
          `paga` quando a pagar de facto.

  VIA 2 — Despesa via stock. Lançada pelo financeiro (não pelo
          módulo Stock), com um ou mais produtos e quantidades.
          Categoria fixada automaticamente a "Compra de Stock".
          Nasce `paga` (assume-se pago na hora), unidade_id=NULL
          (armazém, "por imputar"). `itens_confirmados` nasce False
          — só passa a True quando um Master/Admin confirmar que a
          mercadoria chegou certa, momento em que se geram os
          movimentos de entrada no stock, um por item.

Isto NÃO substitui o stock. A entrada direta pelo Stock (reposições
rápidas, sem fatura a registar) continua a existir em paralelo. São
duas portas para a mesma coisa, com propósitos diferentes.

DISTINÇÃO COGS vs DESPESA OPERACIONAL: o consumo de stock por uma
unidade (via `movimentos` + `requisicoes`) é COGS — não passa por
este módulo. As `despesas` são despesas operacionais. O financeiro
(próximo módulo) vai somar os dois no mesmo número final, mas as
origens ficam distintas na base de dados.

RECORRÊNCIA: uma despesa manual pode ser marcada `recorrente=True`.
A função `gerar_recorrencias_pendentes(autor)` corre ao abrir o
módulo financeiro e cria a do mês seguinte (mesma unidade,
categoria, fornecedor e descrição; valor em branco para o
utilizador preencher; `despesa_origem_id` a apontar para a anterior).
Gera mesmo que a anterior ainda esteja `pendente` — não espera pelo
pagamento.

VENCIMENTO: `data_vencimento` é diferente de `data_lancamento`
(quando registaste) e `data_pagamento` (quando pagaste). Uma
despesa `pendente` com `data_vencimento` no passado é "vencida" —
calculado na hora por `esta_vencida(despesa)`, SEM nenhum estado
novo na tabela.

DIVISÃO POR PROPRIEDADE (caso da internet): uma despesa de valor
TOTAL associada a uma propriedade pode ser dividida igualmente
pelas unidades ATIVAS dessa propriedade. Gera N despesas
independentes, uma por unidade, cada uma com `unidade_id`
preenchido. Arredondamento simples por linha (2 casas decimais); se
a soma ficar com 1 cêntimo de diferença face ao valor original,
isso é aceite — não há ajuste na última unidade. Não existe, nesta
versão, nenhum campo a ligar as N despesas entre si como "vindas
da mesma fatura" — cada uma é autónoma.

PERMISSÕES: só Master e Admin acedem a este módulo. Categorias são
só Master (criar/editar/desativar). Fornecedores são Master+Admin.
Todas as funções de escrita recebem o `autor` (dict do responsável
ativo) e validam permissão via `utilizadores.verificar_permissao`.
A barreira vive aqui, não só na GUI (regra 11.2 do projeto).

Este módulo NÃO acede a ficheiros nem à interface. Fala com o
`repositorio` (BD), com o `responsaveis.validar_autoria`, com o
`estoque.registar_movimento`/`criar_produto` (só na VIA 2) e com o
`utilizadores.verificar_permissao`. Devolve dicionários/lista e
sinaliza erro com `raise ValueError`.
"""

from datetime import date, timedelta
from decimal import Decimal

import estoque
import repositorio
import responsaveis
import utilizadores

# Prefixos dos IDs — mesma convenção dos outros módulos (PRD, MOV,
# REQ, DEV, CNT, RSV, RES...). DSP = despesa, IDP = item de despesa,
# CAT = categoria de despesa, FOR = fornecedor.
PREFIXO_DESPESA = "DSP"
PREFIXO_ITEM_DESPESA = "IDP"
PREFIXO_CATEGORIA = "CAT"
PREFIXO_FORNECEDOR = "FOR"

# Perfis que podem fazer operações de despesas. Master e Admin, no
# mesmo pé — mesma convenção de `estoque._TIPOS_ADMINISTRATIVOS`.
_TIPOS_ADMINISTRATIVOS = ("Admin", "Master")

# Perfis que podem gerir categorias de despesa. Decisão do handoff
# (Parte E): só Master. Fornecedores são Master+Admin, ficam com a
# constante de cima.
_TIPOS_GESTAO_CATEGORIAS = ("Master",)

# Estados possíveis de uma despesa. Os três do ENUM na base de dados.
_ESTADOS_DESPESA = ("pendente", "paga", "cancelada")

# Nome da categoria obrigatória, semeada na migração SQL (Parte C.3
# do handoff). É usada automaticamente pela VIA 2. Procurada pelo
# nome, nunca pelo ID — o ID (CAT000001) é só o valor do seed, não é
# contrato.
_NOME_CATEGORIA_COMPRA_STOCK = "Compra de Stock"


# =====================================================================
# HELPERS INTERNOS
# =====================================================================


def _validar_autor(autor):
    """Confirma que `autor` é um responsável ativo com perfil válido
    para este módulo (Master ou Admin).

    Chamada por TODAS as funções de escrita. É a barreira de
    permissão do módulo — a GUI também verifica, mas a barreira real
    vive aqui (regra 11.2).

    Devolve o próprio dict `autor` (para encadear `.get("id")` sem
    repetir a verificação). Levanta ValueError se `autor` for None,
    se não tiver `id` ou se o perfil não for Master/Admin.
    """
    if autor is None:
        raise ValueError(
            "Não há responsável ativo. Escolha um antes de continuar."
        )

    if not autor.get("id"):
        raise ValueError(
            "O responsável ativo não tem ID. Volte a entrar no sistema."
        )

    utilizadores.verificar_permissao(autor, set(_TIPOS_ADMINISTRATIVOS))

    return autor


def _validar_valor(valor):
    """Confirma que `valor` é um Decimal não-negativo (pode ser 0)."""
    if valor is None:
        raise ValueError("O valor é obrigatório.")

    if not isinstance(valor, Decimal):
        raise ValueError(
            f"O valor tem de ser Decimal, não {type(valor).__name__}."
        )

    if not valor.is_finite():
        raise ValueError("O valor tem de ser um número finito.")

    if valor < 0:
        raise ValueError(f"O valor não pode ser negativo: {valor}.")

    return valor


def _validar_quantidade_item(quantidade):
    """Confirma que a quantidade de um item é um inteiro > 0."""
    if quantidade is None:
        raise ValueError("A quantidade é obrigatória.")

    if not isinstance(quantidade, int) or isinstance(quantidade, bool):
        raise ValueError(
            f"A quantidade tem de ser um número inteiro: {quantidade}"
        )

    if quantidade <= 0:
        raise ValueError(f"A quantidade tem de ser positiva: {quantidade}")

    return quantidade


def _procurar_categoria_compra_stock():
    """Devolve a categoria 'Compra de Stock' ATIVA, ou levanta erro.

    Usada pela VIA 2 para fixar a categoria. Se o Master tiver
    desativado esta categoria, o lançamento por VIA 2 fica bloqueado
    com uma mensagem que explica o que fazer (reativar, ou usar
    outra categoria). Decisão do handoff (C.3): não se impede o
    Master de a desativar — apenas se valida no momento do uso.
    """
    for categoria in repositorio.listar_categorias_despesa():
        if categoria["nome"] == _NOME_CATEGORIA_COMPRA_STOCK:
            return categoria

    raise ValueError(
        f"A categoria '{_NOME_CATEGORIA_COMPRA_STOCK}' não existe ou "
        f"está desativada. Peça ao Master para a reativar antes de "
        f"lançar compras de stock pelo financeiro."
    )


def _agrupar_despesas_por_cadeia(despesas):
    """Agrupa despesas recorrentes pela sua cadeia de origem.

    Uma 'cadeia recorrente' é o conjunto de despesas ligadas por
    `despesa_origem_id`. A despesa original (a que não tem
    `despesa_origem_id`) é a raiz; as seguintes apontam para a
    anterior, formando uma lista ligada.

    Devolve `{id_raiz: [despesa_mais_recente, ..., despesa_raiz]}`,
    com cada lista ordenada por `data_lancamento` descendente (a
    mais recente primeiro). Usado por `gerar_recorrencias_pendentes`
    para decidir se cada cadeia já tem lançamento do mês atual.
    """
    por_id = {d["id"]: d for d in despesas}
    cadeias = {}

    for despesa in despesas:
        # Encontra a raiz seguindo despesa_origem_id até chegar a
        # uma que não tenha.
        atual = despesa
        visitados = set()

        while atual.get("despesa_origem_id"):
            if atual["id"] in visitados:
                # Ciclo (não devia acontecer, mas protege-se para
                # não entrar em loop infinito).
                break
            visitados.add(atual["id"])
            anterior = por_id.get(atual["despesa_origem_id"])
            if anterior is None:
                break
            atual = anterior

        cadeias.setdefault(atual["id"], []).append(despesa)

    for lista in cadeias.values():
        lista.sort(key=lambda d: d["data_lancamento"], reverse=True)

    return cadeias


def _mes_de(data):
    """Devolve o par (ano, mês) de uma data — usado para comparar
    'é do mês atual?' sem precisar de somar/subtrair meses."""
    return (data.year, data.month)


# =====================================================================
# LEITURA — despesas, itens, categorias, fornecedores
# =====================================================================


def procurar_despesa(despesa_id):
    """Devolve a despesa com o identificador indicado, ou None.

    A ausência não é erro: quem chama decide se ela impede a
    operação. Não filtra por estado — procura, não decide (mesma
    convenção de `estoque.procurar_produto` e dos outros módulos).
    """
    return repositorio.procurar_despesa(despesa_id)


def listar_despesas(
    estado=None,
    unidade_id=None,
    categoria_id=None,
    fornecedor_id=None,
    incluir_vencidas=None,
):
    """Devolve as despesas, com filtros opcionais.

    Cada filtro é um valor exato quando indicado; None (omisso) não
    filtra nesse campo. Os filtros SQL (estado, unidade, categoria,
    fornecedor) vão diretamente para o `repositorio`. O filtro
    `incluir_vencidas` é aplicado em Python depois de ler — porque
    'vencida' não é um estado guardado na base (é calculado em
    tempo de leitura, ver `esta_vencida`).

    'incluir_vencidas':
      - None  → sem filtro (devolve pendentes vencidas e não vencidas)
      - True  → só as vencidas
      - False → só as NÃO vencidas

    Devolve lista nova, ordenada por `data_lancamento` descendente.
    """
    despesas = repositorio.listar_despesas(
        estado=estado,
        unidade_id=unidade_id,
        categoria_id=categoria_id,
        fornecedor_id=fornecedor_id,
    )

    if incluir_vencidas is not None:
        despesas = [d for d in despesas if esta_vencida(d) == incluir_vencidas]

    despesas.sort(key=lambda d: d["data_lancamento"], reverse=True)

    return despesas


def listar_itens_despesa(despesa_id):
    """Devolve os itens de uma despesa VIA 2.

    Para despesas VIA 1 (manuais, sem itens) devolve lista vazia —
    é o comportamento correto, não é erro.
    """
    return repositorio.listar_itens_despesa(despesa_id=despesa_id)


def procurar_categoria(categoria_id):
    """Devolve a categoria com o identificador indicado, ou None."""
    return repositorio.procurar_categoria_despesa(categoria_id)


def listar_categorias(incluir_inativas=False):
    """Devolve as categorias de despesa.

    Ativas por omissão; todas se `incluir_inativas=True`. Ordenada
    por nome.
    """
    categorias = repositorio.listar_categorias_despesa(
        incluir_inativas=incluir_inativas
    )
    categorias.sort(key=lambda c: c["nome"])
    return categorias


def procurar_fornecedor(fornecedor_id):
    """Devolve o fornecedor com o identificador indicado, ou None."""
    return repositorio.procurar_fornecedor(fornecedor_id)


def listar_fornecedores(incluir_inativos=False):
    """Devolve os fornecedores. Ativos por omissão; todos se
    `incluir_inativos=True`. Ordenada por nome.
    """
    fornecedores = repositorio.listar_fornecedores(
        incluir_inativos=incluir_inativos
    )
    fornecedores.sort(key=lambda f: f["nome"])
    return fornecedores


def esta_vencida(despesa):
    """Diz se uma despesa está vencida — calculado NA HORA, não
    guardado em estado nenhum (decisão do handoff, B.7).

    Uma despesa está vencida quando:
      - Está `pendente` (as `paga` já não têm prazo em falta, as
        `cancelada` saíram do fluxo), E
      - Tem `data_vencimento` preenchida (é opcional), E
      - Essa data é anterior a hoje.

    Uma despesa `pendente` sem `data_vencimento` nunca é vencida —
    não tem prazo definido, não há nada a comparar.

    Devolve sempre bool.
    """
    if despesa["estado"] != "pendente":
        return False

    if despesa["data_vencimento"] is None:
        return False

    return despesa["data_vencimento"] < date.today()


# =====================================================================
# CATEGORIAS DE DESPESA — gestão (só Master)
# =====================================================================


def criar_categoria(nome, autor):
    """Cria uma categoria de despesa. Só Master.

    O nome é obrigatório e tem de ser único entre as categorias
    ATIVAS (o MySQL tem UNIQUE na coluna, mas esta validação dá uma
    mensagem clara antes de bater na base). Categorias desativadas
    não bloqueiam a criação de uma nova com o mesmo nome — a
    desativação tira-as do uso, não as apaga.

    Devolve o registo criado.
    """
    _validar_autor(autor)

    # A verificação de perfil de categoria (só Master) é mais fina do
    # que a de _validar_autor (que aceita Master+Admin). Faz-se aqui
    # depois, com o dict já validado.
    utilizadores.verificar_permissao(autor, set(_TIPOS_GESTAO_CATEGORIAS))

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome da categoria é obrigatório.")

    for categoria in repositorio.listar_categorias_despesa():
        if categoria["nome"].lower() == nome.lower():
            raise ValueError(
                f"Já existe uma categoria ativa chamada '{nome}'."
            )

    categoria = {
        "id": repositorio.proximo_id(PREFIXO_CATEGORIA),
        "nome": nome,
        "ativo": True,
    }

    repositorio.inserir_categoria_despesa(categoria)
    return categoria


def atualizar_categoria(categoria_id, nome, autor):
    """Altera o nome de uma categoria existente. Só Master.

    Recusa se a categoria não existir, se já estiver desativada (uma
    categoria desativada não é editável — reativa-se primeiro, para
    não haver nomes a mudar em registos que estão fora do uso), ou
    se o novo nome já pertencer a outra categoria ativa.

    Devolve o registo atualizado.
    """
    _validar_autor(autor)
    utilizadores.verificar_permissao(autor, set(_TIPOS_GESTAO_CATEGORIAS))

    categoria = repositorio.procurar_categoria_despesa(categoria_id)

    if categoria is None:
        raise ValueError(f"A categoria {categoria_id} não existe.")

    if not categoria["ativo"]:
        raise ValueError(
            f"A categoria {categoria_id} está desativada. Reativa-a "
            f"antes de a editar."
        )

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome da categoria é obrigatório.")

    for outra in repositorio.listar_categorias_despesa():
        if (
            outra["id"] != categoria_id
            and outra["nome"].lower() == nome.lower()
        ):
            raise ValueError(
                f"Já existe uma categoria ativa chamada '{nome}'."
            )

    repositorio.atualizar_categoria_despesa(categoria_id, {"nome": nome})
    categoria["nome"] = nome
    return categoria


def desativar_categoria(categoria_id, autor):
    """Marca uma categoria como inativa. Só Master.

    Não apaga nada — despesas antigas continuam a apontar para ela
    sem problema (mesmo padrão de produtos, propriedades, unidades).
    A categoria 'Compra de Stock' NÃO é protegida — o Master pode
    desativá-la; a VIA 2 é que valida no momento do uso (ver
    `_procurar_categoria_compra_stock`).

    Devolve o registo atualizado.
    """
    _validar_autor(autor)
    utilizadores.verificar_permissao(autor, set(_TIPOS_GESTAO_CATEGORIAS))

    categoria = repositorio.procurar_categoria_despesa(categoria_id)

    if categoria is None:
        raise ValueError(f"A categoria {categoria_id} não existe.")

    if not categoria["ativo"]:
        raise ValueError(f"A categoria {categoria_id} já está inativa.")

    campos = {
        "ativo": False,
        "desativado_por_id": autor["id"],
        "data_desativacao": date.today(),
    }
    repositorio.atualizar_categoria_despesa(categoria_id, campos)
    categoria.update(campos)
    return categoria


def reativar_categoria(categoria_id, autor):
    """Repõe uma categoria desativada como ativa. Só Master.

    Limpa `desativado_por_id` e `data_desativacao` — mesma convenção
    de `propriedades.reativar`, `unidades.reativar`,
    `estoque.reativar_produto`.

    Devolve o registo atualizado.
    """
    _validar_autor(autor)
    utilizadores.verificar_permissao(autor, set(_TIPOS_GESTAO_CATEGORIAS))

    categoria = repositorio.procurar_categoria_despesa(categoria_id)

    if categoria is None:
        raise ValueError(f"A categoria {categoria_id} não existe.")

    if categoria["ativo"]:
        raise ValueError(f"A categoria {categoria_id} já está ativa.")

    campos = {
        "ativo": True,
        "desativado_por_id": None,
        "data_desativacao": None,
    }
    repositorio.atualizar_categoria_despesa(categoria_id, campos)
    categoria.update(campos)
    return categoria


# =====================================================================
# FORNECEDORES — gestão (Master + Admin)
# =====================================================================


def criar_fornecedor(nome, autor, contacto="", nif=""):
    """Cria um fornecedor. Master ou Admin.

    O nome é obrigatório. `contacto` (telefone/email) e `nif` são
    opcionais — nem todos os fornecedores têm NIF conhecido no
    momento do cadastro (mesma lógica de `propriedades.criar` com
    o IBAN).

    Devolve o registo criado.
    """
    _validar_autor(autor)

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do fornecedor é obrigatório.")

    fornecedor = {
        "id": repositorio.proximo_id(PREFIXO_FORNECEDOR),
        "nome": nome,
        "contacto": contacto.strip(),
        "nif": nif.strip(),
        "ativo": True,
    }

    repositorio.inserir_fornecedor(fornecedor)
    return fornecedor


def atualizar_fornecedor(
    fornecedor_id, autor, nome=None, contacto=None, nif=None
):
    """Altera os dados de um fornecedor existente. Master ou Admin.

    Um parâmetro a None significa não alterar; "" significa limpar o
    conteúdo (mesma convenção de `clientes.atualizar`,
    `propriedades.atualizar`). O nome não pode ficar vazio.

    Devolve o registo atualizado.
    """
    _validar_autor(autor)

    fornecedor = repositorio.procurar_fornecedor(fornecedor_id)

    if fornecedor is None:
        raise ValueError(f"O fornecedor {fornecedor_id} não existe.")

    campos = {}

    if nome is not None:
        nome = nome.strip()
        if not nome:
            raise ValueError("O nome do fornecedor é obrigatório.")
        campos["nome"] = nome

    if contacto is not None:
        campos["contacto"] = contacto.strip()

    if nif is not None:
        campos["nif"] = nif.strip()

    if campos:
        repositorio.atualizar_fornecedor(fornecedor_id, campos)
        fornecedor.update(campos)

    return fornecedor


def desativar_fornecedor(fornecedor_id, autor):
    """Marca um fornecedor como inativo. Master ou Admin.

    Mesmo padrão dos outros módulos — desativação sem apagar,
    histórico preservado. Despesas antigas continuam a apontar para
    ele sem problema.

    Devolve o registo atualizado.
    """
    _validar_autor(autor)

    fornecedor = repositorio.procurar_fornecedor(fornecedor_id)

    if fornecedor is None:
        raise ValueError(f"O fornecedor {fornecedor_id} não existe.")

    if not fornecedor["ativo"]:
        raise ValueError(f"O fornecedor {fornecedor_id} já está inativo.")

    campos = {
        "ativo": False,
        "desativado_por_id": autor["id"],
        "data_desativacao": date.today(),
    }
    repositorio.atualizar_fornecedor(fornecedor_id, campos)
    fornecedor.update(campos)
    return fornecedor


def reativar_fornecedor(fornecedor_id, autor):
    """Repõe um fornecedor desativado como ativo. Master ou Admin.

    Devolve o registo atualizado.
    """
    _validar_autor(autor)

    fornecedor = repositorio.procurar_fornecedor(fornecedor_id)

    if fornecedor is None:
        raise ValueError(f"O fornecedor {fornecedor_id} não existe.")

    if fornecedor["ativo"]:
        raise ValueError(f"O fornecedor {fornecedor_id} já está ativo.")

    campos = {
        "ativo": True,
        "desativado_por_id": None,
        "data_desativacao": None,
    }
    repositorio.atualizar_fornecedor(fornecedor_id, campos)
    fornecedor.update(campos)
    return fornecedor


# =====================================================================
# DESPESAS — VIA 1 (manual)
# =====================================================================


def criar_despesa_manual(
    categoria_id,
    valor,
    data_lancamento,
    responsavel_id,
    autor,
    unidade_id=None,
    fornecedor_id=None,
    data_vencimento=None,
    descricao="",
    comprovativo_caminho="",
    recorrente=False,
):
    """VIA 1 — cria uma despesa manual (EDP, água, internet, obras).

    Sem itens de produto: `itens_confirmados` nasce True (nada a
    confirmar). Nasce `pendente` — só passa a `paga` quando o
    Master/Admin a marcar como tal, e só a partir daí é que conta
    para o financeiro.

    'categoria_id' é obrigatório — nunca fica sem categoria. A
    categoria tem de estar ativa no momento do uso.

    'unidade_id' é opcional — uma despesa de unidade preenche-o; uma
    despesa de propriedade (ou sem imputação) fica com None. A
    divisão automática por propriedade (ver
    `dividir_despesa_por_propriedade`) cria N despesas desta via,
    cada uma com unidade_id preenchido.

    'valor' tem de ser Decimal não-negativo — digitado à mão, nunca
    calculado a partir de itens.

    'responsavel_id' passa por `responsaveis.validar_autoria` — tem
    de existir e estar ativo.

    'autor' é o dict do responsável ativo — para validação de
    permissão. Não confundir com `responsavel_id`: o autor é quem
    executa a operação agora; o responsavel_lancamento é a quem a
    despesa fica atribuída (podem ser a mesma pessoa, mas não têm
    de ser).

    Devolve o registo criado.
    """
    _validar_autor(autor)

    categoria = repositorio.procurar_categoria_despesa(categoria_id)

    if categoria is None:
        raise ValueError(f"A categoria {categoria_id} não existe.")

    if not categoria["ativo"]:
        raise ValueError(
            f"A categoria {categoria_id} está desativada. Escolha " f"outra."
        )

    if unidade_id is not None:
        # Só valida existência; a unidade pode estar inativa — uma
        # despesa histórica pode referir-se a ela na mesma.
        unidade = repositorio.procurar_unidade(unidade_id)
        if unidade is None:
            raise ValueError(f"A unidade {unidade_id} não existe.")

    if fornecedor_id is not None:
        fornecedor = repositorio.procurar_fornecedor(fornecedor_id)
        if fornecedor is None:
            raise ValueError(f"O fornecedor {fornecedor_id} não existe.")

    _validar_valor(valor)

    if data_lancamento is None:
        raise ValueError("A data de lançamento é obrigatória.")

    if data_vencimento is not None and data_vencimento < data_lancamento:
        raise ValueError(
            "A data de vencimento não pode ser anterior à data de "
            "lançamento."
        )

    responsavel = responsaveis.validar_autoria(responsavel_id)

    despesa = {
        "id": repositorio.proximo_id(PREFIXO_DESPESA),
        "unidade_id": unidade_id,
        "categoria_id": categoria_id,
        "fornecedor_id": fornecedor_id,
        "valor": valor,
        "data_lancamento": data_lancamento,
        "data_pagamento": None,
        "data_vencimento": data_vencimento,
        "estado": "pendente",
        "recorrente": bool(recorrente),
        "despesa_origem_id": None,
        "itens_confirmados": True,
        "itens_confirmados_por_id": None,
        "itens_confirmados_em": None,
        "responsavel_lancamento_id": responsavel["id"],
        "responsavel_cancelamento_id": None,
        "motivo_cancelamento": None,
        "descricao": descricao.strip(),
        "comprovativo_caminho": comprovativo_caminho.strip(),
    }

    repositorio.inserir_despesa(despesa)
    return despesa


def dividir_despesa_por_propriedade(
    propriedade_id,
    valor_total,
    categoria_id,
    data_lancamento,
    responsavel_id,
    autor,
    fornecedor_id=None,
    data_vencimento=None,
    descricao="",
    comprovativo_caminho="",
    recorrente=False,
):
    """Divide uma despesa de valor TOTAL pelas unidades ATIVAS de
    uma propriedade. Devolve lista de despesas criadas (uma por
    unidade).

    Caso típico: internet contratada uma vez por prédio, que se
    divide igualmente pelas unidades. Água e luz NÃO precisam disto
    — cada unidade tem contador próprio.

    Divisão SEMPRE em partes iguais — nunca por peso, nunca por
    critério. Arredondamento simples por linha (2 casas decimais):
    se a soma das N linhas ficar 1 cêntimo acima ou abaixo do
    `valor_total`, isso é ACEITE — não há ajuste de cêntimo na
    última unidade (decisão do handoff, B.5).

    Cria N despesas VIA 1 (via `criar_despesa_manual`), cada uma já
    com `unidade_id` preenchido. Não existe, nesta versão, nenhum
    campo a ligar as N despesas entre si como 'vindas da mesma
    fatura' — cada uma é autónoma (registado na Parte G do handoff
    como decisão adiada).

    Levanta ValueError se a propriedade não existir, se não tiver
    nenhuma unidade ativa, ou se o valor total não for divisível por
    um número > 0.

    Devolve lista de dicts (pode ser vazia? Não — se a propriedade
    não tiver unidades ativas, levanta erro em vez de devolver
    vazio. Uma divisão por zero unidades não é um resultado válido,
    é um erro de utilização).
    """
    _validar_autor(autor)

    propriedade = repositorio.procurar_propriedade(propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    unidades_ativas = repositorio.listar_unidades(
        propriedade_id=propriedade_id
    )

    if not unidades_ativas:
        raise ValueError(
            f"A propriedade {propriedade_id} não tem unidades ativas "
            f"— não há por quem dividir."
        )

    _validar_valor(valor_total)

    if valor_total <= 0:
        raise ValueError(
            "O valor a dividir tem de ser positivo. Uma despesa a "
            "dividir por várias unidades não pode ser zero."
        )

    # Arredonda o valor por unidade a 2 casas. Aceita a diferença de
    # cêntimo resultante — não se ajusta a última unidade.
    valor_por_unidade = (valor_total / len(unidades_ativas)).quantize(
        Decimal("0.01")
    )

    despesas_criadas = []

    for unidade in unidades_ativas:
        despesa = criar_despesa_manual(
            categoria_id=categoria_id,
            valor=valor_por_unidade,
            data_lancamento=data_lancamento,
            responsavel_id=responsavel_id,
            autor=autor,
            unidade_id=unidade["id"],
            fornecedor_id=fornecedor_id,
            data_vencimento=data_vencimento,
            descricao=descricao,
            comprovativo_caminho=comprovativo_caminho,
            recorrente=recorrente,
        )
        despesas_criadas.append(despesa)

    return despesas_criadas


# =====================================================================
# DESPESAS — VIA 2 (via stock)
# =====================================================================


def criar_despesa_stock(
    itens,
    valor_total,
    data_lancamento,
    responsavel_id,
    autor,
    fornecedor_id=None,
    descricao="",
    comprovativo_caminho="",
):
    """VIA 2 — cria uma despesa de compra de stock.

    Recebe uma lista de produtos e quantidades (ex.: "5 lixívias + 3
    detergentes"), cria:
      - 1 linha em `despesas` (categoria fixada a "Compra de
        Stock", `unidade_id=None` — armazém, "por imputar",
        `estado="paga"`, `data_pagamento = data_lancamento`,
        `itens_confirmados=False`)
      - N linhas em `itens_despesa` (uma por item, com
        `movimento_id=None` — os movimentos só nascem na
        confirmação)

    Não substitui a entrada direta pelo Stock — as duas portas
    continuam a existir em paralelo. Esta via é para quando há
    fatura a registar.

    'itens' é uma lista de dicionários no formato
      {"produto_id": "PRD-001", "quantidade": 5}.
    Não pode vir vazia, nem repetir o mesmo produto duas vezes
    (pedir mais desse produto é aumentar a quantidade num único
    item).

    'valor_total' é digitado à mão — não é a soma dos itens. O
    handoff rejeitou explicitamente "valor = soma dos itens"
    (Parte B.4).

    Se um produto não existir no catálogo, é criado aqui mesmo —
    mas com os 4 campos completos (`nome`, `unidade_medida`,
    `stock_minimo`, `tipo_produto`), não uma criação rápida só com
    nome. O item correspondente nessa lista tem de trazer essas 4
    chaves a mais, e o `produto_id` fica None — o produto é criado
    primeiro e o ID devolvido pelo `estoque.criar_produto` é usado.
    Isto é a única forma de criar produtos por esta via; não se
    aceita um `produto_id` fictício.

    Devolve tuplo `(despesa, itens_criados)` — coerente com
    `contratos.criar_mensal`, que também devolve dois registos
    quando grava em duas tabelas.
    """
    _validar_autor(autor)

    if not itens:
        raise ValueError("A despesa via stock tem de ter pelo menos um item.")

    categoria = _procurar_categoria_compra_stock()

    _validar_valor(valor_total)

    if data_lancamento is None:
        raise ValueError("A data de lançamento é obrigatória.")

    if fornecedor_id is not None:
        fornecedor = repositorio.procurar_fornecedor(fornecedor_id)
        if fornecedor is None:
            raise ValueError(f"O fornecedor {fornecedor_id} não existe.")

    responsavel = responsaveis.validar_autoria(responsavel_id)

    # Primeiro passo — resolver todos os itens (criar produtos que
    # ainda não existam). Feito antes de gravar a despesa, para não
    # deixar nada a meio se algum item falhar.
    itens_resolvidos = []
    produtos_vistos = set()

    for item in itens:
        produto_id = item.get("produto_id")

        if produto_id is None:
            # Criar produto novo — o item traz os 4 campos completos
            # (nome, unidade_medida, stock_minimo, tipo_produto).
            nome = (item.get("nome") or "").strip()
            unidade_medida = (item.get("unidade_medida") or "").strip()

            if not nome or not unidade_medida:
                raise ValueError(
                    "Um item sem produto_id tem de trazer 'nome' e "
                    "'unidade_medida' para o produto ser criado."
                )

            produto = estoque.criar_produto(
                nome=nome,
                unidade_medida=unidade_medida,
                stock_minimo=item.get("stock_minimo", 0),
                tipo_produto=item.get("tipo_produto", "consumivel"),
            )
            produto_id = produto["id"]
        else:
            produto = repositorio.procurar_produto(produto_id)

            if produto is None:
                raise ValueError(
                    f"O produto {produto_id} não existe. Para criar "
                    f"um produto novo, deixe 'produto_id' em None e "
                    f"traga os campos completos do produto."
                )

        if produto_id in produtos_vistos:
            raise ValueError(
                f"O produto {produto_id} está repetido na despesa — "
                f"some as quantidades num único item."
            )

        produtos_vistos.add(produto_id)

        quantidade = _validar_quantidade_item(item.get("quantidade"))

        itens_resolvidos.append(
            {"produto_id": produto_id, "quantidade": quantidade}
        )

    # Segundo passo — gravar a despesa VIA 2.
    despesa = {
        "id": repositorio.proximo_id(PREFIXO_DESPESA),
        "unidade_id": None,
        "categoria_id": categoria["id"],
        "fornecedor_id": fornecedor_id,
        "valor": valor_total,
        "data_lancamento": data_lancamento,
        "data_pagamento": data_lancamento,  # nasce paga
        "data_vencimento": None,
        "estado": "paga",
        "recorrente": False,  # VIA 2 não é recorrente
        "despesa_origem_id": None,
        "itens_confirmados": False,
        "itens_confirmados_por_id": None,
        "itens_confirmados_em": None,
        "responsavel_lancamento_id": responsavel["id"],
        "responsavel_cancelamento_id": None,
        "motivo_cancelamento": None,
        "descricao": descricao.strip(),
        "comprovativo_caminho": comprovativo_caminho.strip(),
    }

    repositorio.inserir_despesa(despesa)

    # Terceiro passo — gravar os itens.
    itens_criados = []

    for item in itens_resolvidos:
        item_despesa = {
            "id": repositorio.proximo_id(PREFIXO_ITEM_DESPESA),
            "despesa_id": despesa["id"],
            "produto_id": item["produto_id"],
            "quantidade": item["quantidade"],
            "movimento_id": None,
        }
        repositorio.inserir_item_despesa(item_despesa)
        itens_criados.append(item_despesa)

    return despesa, itens_criados


def confirmar_itens_despesa(despesa_id, autor):
    """Confirma que os itens de uma despesa VIA 2 chegaram certos.

    Ações (todas na mesma chamada):
      1. Por cada linha de `itens_despesa` dessa despesa, gera UM
         movimento de ENTRADA no stock (`estoque.registar_movimento`,
         tipo="entrada", motivo="Entrada via despesa DSP-XXX").
      2. Grava o `movimento_id` devolvido em cada item.
      3. Marca a despesa: `itens_confirmados=True`,
         `itens_confirmados_por_id=autor["id"]`,
         `itens_confirmados_em=datetime.now()`.

    Só se aplica a despesas VIA 2 ainda por confirmar
    (`itens_confirmados=False`). Se já estiver confirmada, recusa
    com erro — sem isto, um segundo clique gerava movimentos de
    stock duplicados.

    Se a despesa não tiver itens (VIA 1, por exemplo), também
    recusa — não há nada a confirmar.

    Devolve a despesa atualizada (com os campos de confirmação já
    preenchidos). Os itens ficam acessíveis via
    `listar_itens_despesa`, com os `movimento_id` já gravados.
    """
    from datetime import datetime

    _validar_autor(autor)

    despesa = repositorio.procurar_despesa(despesa_id)

    if despesa is None:
        raise ValueError(f"A despesa {despesa_id} não existe.")

    if despesa["estado"] == "cancelada":
        raise ValueError(
            f"A despesa {despesa_id} está cancelada — não há nada a "
            f"confirmar."
        )

    if despesa["itens_confirmados"]:
        raise ValueError(
            f"Os itens da despesa {despesa_id} já foram confirmados. "
            f"Não é possível confirmar duas vezes — os movimentos de "
            f"stock já foram gerados na primeira confirmação."
        )

    itens = repositorio.listar_itens_despesa(despesa_id=despesa_id)

    if not itens:
        raise ValueError(
            f"A despesa {despesa_id} não tem itens. Só despesas "
            f"criadas via stock (VIA 2) é que se confirmam."
        )

    # Gera um movimento por item. Motivo combinado com o utilizador —
    # ver a 3ª pergunta desta ronda de decisões. Fica rastreável no
    # histórico de stock, sem obrigar quem olha a saltar para a
    # tabela de despesas só para perceber de onde veio a entrada.
    motivo = f"Entrada via despesa {despesa_id}"

    for item in itens:
        movimento = estoque.registar_movimento(
            produto_id=item["produto_id"],
            tipo="entrada",
            quantidade=item["quantidade"],
            data=date.today(),
            responsavel_id=autor["id"],
            motivo=motivo,
        )

        repositorio.atualizar_item_despesa(
            item["id"], {"movimento_id": movimento["id"]}
        )

    # Marca a despesa como confirmada.
    agora = datetime.now()
    campos = {
        "itens_confirmados": True,
        "itens_confirmados_por_id": autor["id"],
        "itens_confirmados_em": agora,
    }
    repositorio.atualizar_despesa(despesa_id, campos)
    despesa.update(campos)

    return despesa


# =====================================================================
# DESPESAS — pagamento, cancelamento, edição
# =====================================================================


def marcar_paga(despesa_id, data_pagamento, autor):
    """Marca uma despesa VIA 1 como paga.

    Só faz sentido para despesas VIA 1 ainda `pendente` — as VIA 2 já
    nascem `paga`, e as `cancelada` saíram do fluxo.

    'data_pagamento' é a data em que o pagamento aconteceu (pode ser
    hoje ou uma data retroativa). Se for None, usa-se hoje.

    Devolve a despesa atualizada.
    """
    _validar_autor(autor)

    despesa = repositorio.procurar_despesa(despesa_id)

    if despesa is None:
        raise ValueError(f"A despesa {despesa_id} não existe.")

    if despesa["estado"] == "paga":
        raise ValueError(f"A despesa {despesa_id} já está paga.")

    if despesa["estado"] == "cancelada":
        raise ValueError(
            f"A despesa {despesa_id} está cancelada — não pode ser "
            f"marcada como paga."
        )

    if data_pagamento is None:
        data_pagamento = date.today()

    campos = {
        "estado": "paga",
        "data_pagamento": data_pagamento,
    }
    repositorio.atualizar_despesa(despesa_id, campos)
    despesa.update(campos)
    return despesa


def cancelar_despesa(despesa_id, motivo, autor):
    """Cancela uma despesa — estado passa a `cancelada`, sem apagar
    nada.

    Exige SEMPRE motivo (texto obrigatório) — o handoff é explícito
    nisto (B.8). O responsável que cancelou fica gravado em
    `responsavel_cancelamento_id`.

    Uma despesa cancelada continua visível no histórico e nos
    relatórios, com o estado `cancelada`. Não desaparece.

    Uma despesa já cancelada não se recancela — mesma proteção do
    `estoque.rejeitar_requisicao`, que recusa rejeitar duas vezes.

    Devolve a despesa atualizada.
    """
    _validar_autor(autor)

    despesa = repositorio.procurar_despesa(despesa_id)

    if despesa is None:
        raise ValueError(f"A despesa {despesa_id} não existe.")

    if despesa["estado"] == "cancelada":
        raise ValueError(f"A despesa {despesa_id} já está cancelada.")

    motivo = (motivo or "").strip()

    if not motivo:
        raise ValueError("O motivo é obrigatório para cancelar uma despesa.")

    campos = {
        "estado": "cancelada",
        "motivo_cancelamento": motivo,
        "responsavel_cancelamento_id": autor["id"],
    }
    repositorio.atualizar_despesa(despesa_id, campos)
    despesa.update(campos)
    return despesa


def editar_valor_despesa(despesa_id, novo_valor, autor):
    """Altera o valor de uma despesa, só se ela ainda estiver
    `pendente`.

    O handoff é explícito (B.8): depois de `paga`, o valor fica
    bloqueado — só resta cancelar e lançar de novo se houver erro.
    O mesmo se aplica a `cancelada` (não faz sentido editar uma
    despesa fora do fluxo).

    Devolve a despesa atualizada.
    """
    _validar_autor(autor)

    despesa = repositorio.procurar_despesa(despesa_id)

    if despesa is None:
        raise ValueError(f"A despesa {despesa_id} não existe.")

    if despesa["estado"] == "paga":
        raise ValueError(
            f"A despesa {despesa_id} está paga — o valor está "
            f"bloqueado. Se houver erro, cancele-a e lance outra."
        )

    if despesa["estado"] == "cancelada":
        raise ValueError(
            f"A despesa {despesa_id} está cancelada — o valor não é "
            f"editável."
        )

    _validar_valor(novo_valor)

    repositorio.atualizar_despesa(despesa_id, {"valor": novo_valor})
    despesa["valor"] = novo_valor
    return despesa


def editar_despesa_pendente(
    despesa_id,
    autor,
    valor=None,
    descricao=None,
    categoria_id=None,
    fornecedor_id=None,
    data_lancamento=None,
    data_vencimento=None,
):
    """Edita os dados de uma despesa pendente.

    Só se aplica a despesas com `estado == "pendente"`. Depois de
    `paga`, os dados ficam bloqueados — se houver erro, o caminho é
    cancelar e relançar. Depois de `cancelada`, também não é editável.

    Campos editáveis (todos opcionais — um campo a None não é
    alterado):
      - valor (Decimal não-negativo)
      - descricao (texto — pode ficar vazio? não: obrigatória, se
        for fornecida vazia levanta erro para não deixar a despesa
        sem descrição no ecrã)
      - categoria_id (FK — tem de existir e estar ativa)
      - fornecedor_id (FK — se for None, não altera; se for "",
        limpa o fornecedor; se for um id, valida que existe)
      - data_lancamento (date)
      - data_vencimento (date ou None para limpar)

    O que NÃO é editável aqui (decisão tomada com o aluno):
      - unidade_id — é estrutural, define-se no lançamento
      - recorrente — ligar/desligar tem implicações na próxima
        geração, e é raro; se enganou, cancela e relança
      - estado — o estado é gerido pelas funções próprias
        (marcar_paga, cancelar_despesa)

    Devolve a despesa atualizada.
    """
    _validar_autor(autor)

    despesa = repositorio.procurar_despesa(despesa_id)

    if despesa is None:
        raise ValueError(f"A despesa {despesa_id} não existe.")

    if despesa["estado"] == "paga":
        raise ValueError(
            f"A despesa {despesa_id} está paga — os dados estão "
            f"bloqueados. Se houver erro, cancele-a e lance outra."
        )

    if despesa["estado"] == "cancelada":
        raise ValueError(
            f"A despesa {despesa_id} está cancelada — não é editável."
        )

    campos = {}

    # ---- valor ----
    if valor is not None:
        _validar_valor(valor)
        campos["valor"] = valor

    # ---- descrição ----
    if descricao is not None:
        descricao = descricao.strip()
        if not descricao:
            raise ValueError(
                "A descrição é obrigatória — não pode ficar vazia."
            )
        campos["descricao"] = descricao

    # ---- categoria ----
    if categoria_id is not None:
        categoria = repositorio.procurar_categoria_despesa(categoria_id)
        if categoria is None:
            raise ValueError(f"A categoria {categoria_id} não existe.")
        if not categoria["ativo"]:
            raise ValueError(
                f"A categoria {categoria_id} está desativada. "
                f"Escolha outra."
            )
        campos["categoria_id"] = categoria_id

    # ---- fornecedor ----
    # Convenção: None = não alterar, "" = limpar, id = trocar.
    # Isto distingue-se da maioria dos outros campos onde None = não
    # alterar e "" é ambíguo — aqui o "" tem significado explícito
    # (limpar o fornecedor), porque a coluna é nullable.
    if fornecedor_id is not None:
        if fornecedor_id == "":
            campos["fornecedor_id"] = None
        else:
            fornecedor = repositorio.procurar_fornecedor(fornecedor_id)
            if fornecedor is None:
                raise ValueError(f"O fornecedor {fornecedor_id} não existe.")
            campos["fornecedor_id"] = fornecedor_id

    # ---- data_lancamento ----
    if data_lancamento is not None:
        campos["data_lancamento"] = data_lancamento

    # ---- data_vencimento ----
    # Aceita None como valor explícito para "limpar o vencimento".
    # Como `None` também significa "não alterar" por convenção, uso
    # um sentinela separado — mas como não estou a distinguir, trato
    # este caso concreto com uma pequena regra: se a data de
    # lançamento for alterada e a de vencimento não, valida que a de
    # vencimento (a atual) continua coerente. Caso contrário, aceita
    # a data nova.
    if data_vencimento is not None:
        campos["data_vencimento"] = data_vencimento

    # Coerência final: vencimento >= lançamento (com os valores que
    # ficam depois de aplicar todas as alterações).
    lancamento_final = campos.get(
        "data_lancamento", despesa["data_lancamento"]
    )
    vencimento_final = campos.get(
        "data_vencimento", despesa["data_vencimento"]
    )
    if vencimento_final is not None and vencimento_final < lancamento_final:
        raise ValueError(
            "A data de vencimento não pode ser anterior à data de "
            "lançamento."
        )

    if not campos:
        # Nada a alterar — devolve o registo tal como está.
        return despesa

    repositorio.atualizar_despesa(despesa_id, campos)
    despesa.update(campos)
    return despesa


# =====================================================================
# RECORRÊNCIAS
# =====================================================================


def gerar_recorrencias_pendentes(autor):
    """Gera os lançamentos do mês atual das despesas recorrentes
    que ainda não os têm.

    Chamada ao abrir o ecrã de despesas (verificação leve — mesmo
    espírito do `garantir_diretorios()` que corre nos pontos de
    entrada). NÃO gera logo que a aplicação arranca; só quando o
    utilizador entra no módulo financeiro.

    Funcionamento:
      1. Lê todas as despesas com `recorrente=True`.
      2. Agrupa por cadeia (via `despesa_origem_id`, ver
         `_agrupar_despesas_por_cadeia`).
      3. Para cada cadeia cujo lançamento MAIS RECENTE não é do mês
         atual, cria a do mês atual, copiando:
           - unidade_id, categoria_id, fornecedor_id, descricao,
             comprovativo_caminho, responsavel_lancamento_id
           - `valor` fica `0` — o utilizador preenche (o valor muda
             mês a mês, não se copia o antigo)
           - `data_lancamento` = hoje
           - `data_vencimento` = hoje + 30 dias (provisório — o
             utilizador ajusta se quiser; não há regra de negócio
             que defina isto a priori)
           - `despesa_origem_id` = a despesa mais recente da cadeia
           - `estado` = "pendente"
           - `itens_confirmados` = True (VIA 1)
      4. GERA MESMO que a anterior ainda esteja `pendente`. A
         decisão final do handoff (B.6) foi: não esperar pelo
         pagamento. Pode haver várias em aberto da mesma cadeia.

    Devolve a lista das despesas geradas nesta chamada (pode ser
    vazia — é o caso normal fora do início do mês).
    """
    _validar_autor(autor)

    hoje = date.today()
    mes_atual = _mes_de(hoje)

    todas = repositorio.listar_despesas()
    recorrentes = [d for d in todas if d["recorrente"]]

    if not recorrentes:
        return []

    cadeias = _agrupar_despesas_por_cadeia(recorrentes)

    geradas = []

    for raiz_id, membros in cadeias.items():
        # `membros` vem ordenado por data_lancamento descendente —
        # o primeiro é o mais recente.
        mais_recente = membros[0]

        if _mes_de(mais_recente["data_lancamento"]) == mes_atual:
            # Esta cadeia já tem lançamento do mês atual — não
            # duplica.
            continue

        # Cadeia precisa de um novo lançamento para o mês atual.
        nova = {
            "id": repositorio.proximo_id(PREFIXO_DESPESA),
            "unidade_id": mais_recente["unidade_id"],
            "categoria_id": mais_recente["categoria_id"],
            "fornecedor_id": mais_recente["fornecedor_id"],
            "valor": Decimal("0.00"),
            "data_lancamento": hoje,
            "data_pagamento": None,
            "data_vencimento": hoje + timedelta(days=30),
            "estado": "pendente",
            "recorrente": True,
            "despesa_origem_id": mais_recente["id"],
            "itens_confirmados": True,
            "itens_confirmados_por_id": None,
            "itens_confirmados_em": None,
            "responsavel_lancamento_id": autor["id"],
            "responsavel_cancelamento_id": None,
            "motivo_cancelamento": None,
            "descricao": mais_recente["descricao"],
            "comprovativo_caminho": "",
        }

        repositorio.inserir_despesa(nova)
        geradas.append(nova)

    return geradas
