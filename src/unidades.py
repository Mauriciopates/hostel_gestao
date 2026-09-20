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

ACRESCENTADO 13/09/2026 — `taxa_ocupacao(data, tipo=None)`, para o
Dashboard. Agrega a ocupação de todas as unidades ativas num dia,
medindo cada regime na sua unidade natural: Airbnb em unidades
ocupadas/total, mensal em lugares ocupados/total. Não substitui
`estado`/`estado_detalhe` (que classificam UMA unidade); responde
a uma pergunta diferente — "de tudo o que está em oferta, quanto
é que está ocupado".
"""

from decimal import Decimal
from datetime import date, timedelta

import repositorio
import validacoes
import propriedades
import responsaveis

PREFIXO = "UNI"
PREFIXO_QUARTO = "QRT"
PREFIXO_LUGAR = "LUG"
PREFIXO_ATRIBUICAO = "ATR"

# Fase 2, v1.4.0 — beliches. Não é um prefixo novo: um beliche é só
# duas linhas de `lugares` (tipo_cama='beliche') ligadas por
# beliche_grupo_id, que reaproveita o próprio LUG-XXX de uma delas
# (ver criar_beliche, mais abaixo) — sem contador próprio.
POSICOES_BELICHE = ("superior", "inferior")


def _validar_cama_extra(tipo, permite_cama_extra, qtd_cama_extra,
                         tipo_cama_extra):
    """Valida os três campos de cama extra do Airbnb em conjunto
    (Fase 2, v1.4.0, item (d) do plano de correções).

    Decisão do aluno (15/09/2026): só fazem sentido em unidades
    tipo='airbnb' — uma unidade mensal nem chega a mostrar isto na
    GUI, e aqui a mesma regra é aplicada como segunda barreira, não
    só confiança na interface. Quando `permite_cama_extra` é True,
    `qtd_cama_extra` (inteiro > 0) e `tipo_cama_extra` (não vazio)
    passam a obrigatórios — mesma relação que o CHECK já aplicado
    à tabela `unidades` via ALTER TABLE numa entrega anterior; esta
    validação replica-a do lado da aplicação, não a substitui.
    Quando `permite_cama_extra` é False, os outros dois nem chegam
    a ser olhados aqui — quem chama é que já os reduz a None nesse
    caso (ver `criar`/`atualizar`).
    """
    if not permite_cama_extra:
        return

    if tipo != "airbnb":
        raise ValueError(
            "Cama extra só se aplica a unidades do tipo 'airbnb'."
        )

    if not isinstance(qtd_cama_extra, int) or qtd_cama_extra <= 0:
        raise ValueError(
            "A quantidade de cama extra tem de ser um número "
            "inteiro maior que zero."
        )

    if not tipo_cama_extra or not tipo_cama_extra.strip():
        raise ValueError(
            "O tipo de cama extra é obrigatório quando a unidade "
            "permite cama extra."
        )


def criar(
    propriedade_id,
    nome,
    tipo,
    preco_base,
    preco_epoca_alta,
    multa_check_in_tardio,
    epoca_alta_ativa=False,
    permite_cama_extra=False,
    qtd_cama_extra=None,
    tipo_cama_extra=None,
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

    _validar_cama_extra(
        tipo, permite_cama_extra, qtd_cama_extra, tipo_cama_extra
    )

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
        "permite_cama_extra": permite_cama_extra,
        "qtd_cama_extra": qtd_cama_extra if permite_cama_extra else 0,
        "tipo_cama_extra": (
            tipo_cama_extra.strip()
            if permite_cama_extra and tipo_cama_extra
            else None
        ),
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


def listar_com_propriedade(incluir_inativas=False, tipo=None):
    """Devolve as unidades com o nome da propriedade a que
    pertencem (campo `propriedade_nome`), para popular ComboBoxes
    que têm de distinguir unidades com o mesmo nome em propriedades
    diferentes (Fase 2, v1.4.0). Ver `rotulo_com_propriedade` para
    formatar cada linha como texto de ComboBox.

    Sem filtro por propriedade_id — não faria sentido aqui: se já
    se sabe a propriedade, `listar()` chega e é mais direto.
    """
    return repositorio.listar_unidades_com_propriedade(
        incluir_inativas=incluir_inativas, tipo=tipo,
    )


def rotulo_com_propriedade(unidade):
    """Formata o rótulo "[PROPRIEDADE] - [UNIDADE] (ID)" usado nos
    ComboBoxes de unidade, a partir de uma linha devolvida por
    `listar_com_propriedade` (tem de incluir `propriedade_nome`) —
    mesma convenção de ID entre parênteses já usada nos outros
    seletores do sistema.
    """
    return (
        f"{unidade['propriedade_nome']} - {unidade['nome']} "
        f"({unidade['id']})"
    )


def atualizar(
    unidade_id,
    nome=None,
    preco_base=None,
    preco_epoca_alta=None,
    multa_check_in_tardio=None,
    epoca_alta_ativa=None,
    permite_cama_extra=None,
    qtd_cama_extra=None,
    tipo_cama_extra=None,
):
    """Altera o nome, os preços, o indicador de época alta e a cama
    extra do Airbnb de uma unidade.

    Um parâmetro a None significa não alterar (mesma convenção de
    `propriedades.atualizar`). O nome não pode ficar vazio, mesma regra
    de `atualizar_quarto`. Os três preços não podem ficar vazios
    nem negativos: são obrigatórios no cadastro (decisão 6) e essa
    obrigatoriedade mantém-se na alteração.

    O tipo e a propriedade não se alteram aqui: o tipo é restrição
    rígida sobre as ocupações e mudar de propriedade não corresponde
    a nenhuma operação real do negócio. O estado de manutenção tem
    funções próprias.

    Cama extra (Fase 2, v1.4.0, item (d)): os três campos
    (`permite_cama_extra`, `qtd_cama_extra`, `tipo_cama_extra`) são
    tratados em conjunto, não um a um — mudar só a quantidade sem
    tocar em `permite_cama_extra` tem de continuar válido contra o
    valor JÁ gravado, não contra None. Por isso, sempre que UM dos
    três vier diferente de None, os outros dois completam-se com o
    valor atual da unidade antes de validar com
    `_validar_cama_extra`. Desligar `permite_cama_extra` limpa
    sempre `qtd_cama_extra`/`tipo_cama_extra` para None, mesmo que
    tenham sido passados — a flag é que manda, nunca fica um par
    quantidade/tipo "orfão" de uma cama extra desligada.
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

    algum_cama_extra_mudou = (
        permite_cama_extra is not None
        or qtd_cama_extra is not None
        or tipo_cama_extra is not None
    )

    if algum_cama_extra_mudou:
        novo_permite = (
            permite_cama_extra
            if permite_cama_extra is not None
            else unidade["permite_cama_extra"]
        )
        novo_qtd = (
            qtd_cama_extra
            if qtd_cama_extra is not None
            else unidade["qtd_cama_extra"]
        )
        novo_tipo = (
            tipo_cama_extra
            if tipo_cama_extra is not None
            else unidade["tipo_cama_extra"]
        )

        _validar_cama_extra(unidade["tipo"], novo_permite, novo_qtd,
                             novo_tipo)

        campos["permite_cama_extra"] = novo_permite
        campos["qtd_cama_extra"] = novo_qtd if novo_permite else None
        campos["tipo_cama_extra"] = (
            novo_tipo.strip() if novo_permite and novo_tipo else None
        )

    if campos:
        repositorio.atualizar_unidade(unidade_id, campos)
        unidade.update(campos)

    return unidade


def desativar(unidade_id, forcar=False, responsavel_id=None):
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

    Forçar com ocupações ativas exige `responsavel_id` (decisão do
    aluno, 06/09/2026, ao testar a desativação forçada na GUI): quem
    contorna o aviso fica registado em `desativado_por_id`/
    `data_desativacao`, validado por
    `responsaveis.validar_autoria` (mesma autorização já usada nos
    movimentos de stock e na anonimização de clientes). Sem
    ocupações ativas, forcar=True não tem efeito nenhum além de
    ignorar uma verificação que já ia passar — não exige responsável
    nem grava nada nesses dois campos.
    """

    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if not unidade["ativo"]:
        raise ValueError(f"A unidade {unidade_id} já está inativa.")

    ocupacoes_ativas = repositorio.listar_ocupacoes(unidade_id=unidade_id)
    campos: dict = {"ativo": False}

    if ocupacoes_ativas:
        if not forcar:
            raise ValueError(
                f"A unidade {unidade_id} tem "
                f"{len(ocupacoes_ativas)} ocupação(ões) ativa(s) — "
                f"forcar=True para desativar mesmo assim."
            )

        if not responsavel_id:
            raise ValueError(
                "É obrigatório indicar o responsável para forçar a "
                "desativação com dependências ativas."
            )

        responsavel = responsaveis.validar_autoria(responsavel_id)
        campos["desativado_por_id"] = responsavel["id"]
        campos["data_desativacao"] = date.today()

    repositorio.atualizar_unidade(unidade_id, campos)
    unidade.update(campos)
    return unidade


def reativar(unidade_id):
    """Repõe uma unidade desativada como ativa.

    Existe porque a desativação por engano seria irreversível sem
    ela. É a inversa exata da `desativar` — inclui limpar
    `desativado_por_id`/`data_desativacao`, quando a desativação
    tinha sido forçada, para não deixar rasto de uma desativação
    que já não está em vigor.
    """

    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["ativo"]:
        raise ValueError(f"A unidade {unidade_id} já está ativa.")

    campos = {
        "ativo": True,
        "desativado_por_id": None,
        "data_desativacao": None,
    }
    repositorio.atualizar_unidade(unidade_id, campos)
    unidade.update(campos)
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


def atualizar_quarto(
    quarto_id, nome=None, privativo=None, limpeza_incluida=None
):
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


def _criar_lugar(
    quarto_id,
    nome,
    tipo_cama,
    capacidade,
    posicao_beliche=None,
    beliche_grupo_id=None,
    id_lugar=None,
):
    """Validações e persistência comuns a `criar_lugar` e a
    `criar_beliche` (Fase 2, v1.4.0).

    'posicao_beliche'/'beliche_grupo_id' só se aplicam a
    tipo_cama='beliche' — nos restantes têm de vir None, e num
    beliche são obrigatórios (raise ValueError se não bater certo).

    'id_lugar' existe só para `criar_beliche`: a cama "inferior" do
    par usa o seu próprio id como beliche_grupo_id (decisão de
    15/09/2026, para não criar um prefixo novo — ver
    POSICOES_BELICHE, acima), e para isso o id tem de ser conhecido
    ANTES de gravar a linha, em vez de vir de
    `repositorio.proximo_id` só depois. Quando não indicado (uso
    normal, via `criar_lugar`), gera-se um novo, como sempre.
    """
    quarto = procurar_quarto(quarto_id)

    if quarto is None:
        raise ValueError(f"O quarto {quarto_id} não existe.")

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do lugar é obrigatório.")

    validacoes.validar_tipo_cama(tipo_cama)
    validacoes.validar_capacidade_lugar(capacidade)

    if tipo_cama == "beliche":
        if posicao_beliche not in POSICOES_BELICHE:
            raise ValueError(
                "Uma cama de beliche exige posicao_beliche "
                f"{POSICOES_BELICHE[0]!r} ou {POSICOES_BELICHE[1]!r}."
            )

        if not beliche_grupo_id:
            raise ValueError(
                "Uma cama de beliche exige beliche_grupo_id."
            )
    elif posicao_beliche is not None or beliche_grupo_id is not None:
        raise ValueError(
            "posicao_beliche/beliche_grupo_id só se aplicam a "
            "tipo_cama='beliche'."
        )

    lugar = {
        "id": id_lugar or repositorio.proximo_id(PREFIXO_LUGAR),
        "quarto_id": quarto_id,
        "nome": nome,
        "tipo_cama": tipo_cama,
        "capacidade": capacidade,
        "ativo": True,
        "posicao_beliche": posicao_beliche,
        "beliche_grupo_id": beliche_grupo_id,
    }

    repositorio.inserir_lugar(lugar)
    return lugar


def criar_lugar(quarto_id, nome, tipo_cama, capacidade=1):
    """Cria um lugar dentro de um quarto existente.

    'tipo_cama' é obrigatório e só decide a aparência do lugar na
    planta de lugares (GUI) — não deriva nem substitui a
    capacidade, que continua um campo à parte (decisão 17).

    Para camas de beliche (agrupadas duas a duas), usar
    `criar_beliche` — esta função cria sempre um lugar avulso, sem
    posicao_beliche/beliche_grupo_id.

    Devolve o registo criado.
    """
    return _criar_lugar(quarto_id, nome, tipo_cama, capacidade)


# Fase 2, v1.4.0 — decisão do aluno (15/09/2026): não existe beliche
# com um lugar só. Cada nível aloja sempre 1 pessoa; o par soma 2 ao
# todo do quarto/unidade (`_contagem_mensal` soma a capacidade de
# cada lugar). Não é um valor à escolha de quem cria — é uma
# propriedade física do móvel, por isso `criar_beliche` nem recebe
# capacidade como parâmetro.
CAPACIDADE_CAMA_BELICHE = 1


def criar_beliche(quarto_id, nome_superior, nome_inferior):
    """Cria um par de beliche — duas camas ligadas — num quarto
    existente (Fase 2, v1.4.0).

    Não introduz nenhum prefixo/contador novo (decisão de
    15/09/2026): 'beliche' é só `tipo_cama='beliche'` em duas linhas
    de `lugares`, e o agrupamento faz-se reaproveitando o próprio
    LUG-XXX da cama "inferior" como beliche_grupo_id das duas —
    por isso a cama inferior é sempre criada primeiro.

    Sem parâmetro de capacidade (ver CAPACIDADE_CAMA_BELICHE, acima)
    — cada cama do par fica sempre com capacidade 1, o par soma
    sempre 2 ao total do quarto.

    Levanta ValueError nos mesmos casos de `criar_lugar` (quarto
    inexistente, nome vazio), mais se os dois nomes vierem iguais
    depois de retirados os espaços.

    Devolve o par de lugares criados, (inferior, superior).
    """
    nome_superior_normalizado = nome_superior.strip()
    nome_inferior_normalizado = nome_inferior.strip()

    if (
        nome_superior_normalizado
        and nome_inferior_normalizado
        and nome_superior_normalizado == nome_inferior_normalizado
    ):
        raise ValueError(
            "As duas camas do beliche não podem ter o mesmo nome."
        )

    inferior = _criar_lugar(
        quarto_id,
        nome_inferior,
        "beliche",
        CAPACIDADE_CAMA_BELICHE,
        posicao_beliche="inferior",
        beliche_grupo_id=repositorio.proximo_id(PREFIXO_LUGAR),
    )

    superior = _criar_lugar(
        quarto_id,
        nome_superior,
        "beliche",
        CAPACIDADE_CAMA_BELICHE,
        posicao_beliche="superior",
        beliche_grupo_id=inferior["beliche_grupo_id"],
    )

    return inferior, superior


def agrupar_beliches(lugares):
    """Agrupa os lugares de UM quarto em pares de beliche mais
    avulsos, para a Planta de Beliches (Fase 2/3, v1.4.0).

    Recebe a lista tal como `listar_lugares(quarto_id=...)` a
    devolve. Função pura — não acede à base de dados, fácil de
    testar sem MySQL.

    Devolve uma lista de itens:
    - {"tipo": "beliche", "grupo_id": ..., "superior": lugar,
      "inferior": lugar} — par completo, decidido sempre por
      'posicao_beliche', nunca pela ordem de chegada da lista (MySQL
      não promete ordem sem ORDER BY).
    - {"tipo": "beliche_incompleto", "grupo_id": ..., "lugares":
      [...]} — só uma das duas camas do grupo veio na lista (ex.: a
      outra está inativa e a chamada não incluiu inativas). Não
      esconde o problema, devolve o que há para a GUI decidir o que
      mostrar.
    - {"tipo": "avulso", "lugar": lugar} — sem beliche_grupo_id
      (solteiro, casal, ou beliche sem par ainda).
    """
    grupos = {}
    avulsos = []

    for lugar in lugares:
        grupo_id = lugar.get("beliche_grupo_id")

        if grupo_id:
            grupos.setdefault(grupo_id, []).append(lugar)
        else:
            avulsos.append(lugar)

    resultado = []

    for grupo_id, membros in grupos.items():
        por_posicao = {m.get("posicao_beliche"): m for m in membros}
        superior = por_posicao.get("superior")
        inferior = por_posicao.get("inferior")

        if superior is not None and inferior is not None:
            resultado.append(
                {
                    "tipo": "beliche",
                    "grupo_id": grupo_id,
                    "superior": superior,
                    "inferior": inferior,
                }
            )
        else:
            resultado.append(
                {
                    "tipo": "beliche_incompleto",
                    "grupo_id": grupo_id,
                    "lugares": membros,
                }
            )

    for lugar in avulsos:
        resultado.append({"tipo": "avulso", "lugar": lugar})

    return resultado


def atualizar_lugar(lugar_id, nome=None, tipo_cama=None, capacidade=None):
    """Altera o nome, o tipo de cama ou a capacidade de um lugar
    existente.

    Um parâmetro a None significa não alterar (mesma convenção de
    `atualizar` e `atualizar_quarto`, acima). 'tipo_cama', quando
    indicado, passa pela mesma validação da criação.
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

    if tipo_cama is not None:
        validacoes.validar_tipo_cama(tipo_cama)
        campos["tipo_cama"] = tipo_cama

    if capacidade is not None:
        validacoes.validar_capacidade_lugar(capacidade)
        campos["capacidade"] = capacidade

    if campos:
        repositorio.atualizar_lugar(lugar_id, campos)
        lugar.update(campos)

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


def _capacidade_mensal(unidade_id):
    """Soma a capacidade dos lugares ativos de uma unidade mensal.

    Extraída de `_contagem_mensal` na Fase 5 (v1.4.0), ao separar a
    LEITURA da CLASSIFICAÇÃO: a capacidade de uma unidade não depende
    da data, por isso numa semana de calendário basta lê-la uma vez
    em vez de sete (ver `estados_da_semana`, mais abaixo).

    Custa 1 + N queries — uma para os quartos, mais uma por cada
    quarto para os seus lugares. É a leitura mais cara deste módulo.
    """
    capacidade = 0

    for quarto in listar_quartos(unidade_id=unidade_id):
        for lugar in listar_lugares(quarto_id=quarto["id"]):
            capacidade += lugar["capacidade"]

    return capacidade


def _classificar_mensal(ocupacoes, data):
    """Conta as ocupações mensais que cobrem 'data'.

    Função pura — recebe as ocupações já lidas e não toca na base de
    dados, como `agrupar_beliches`. Vigência: data_inicio <= data e
    (data_fim nulo ou data_fim > data). É a mesma regra que vivia
    dentro de `_contagem_mensal` antes da Fase 5 — mudou de sítio,
    não de conteúdo.

    Separada da leitura para o calendário poder classificar os sete
    dias de uma semana a partir de UMA leitura (ver
    `estados_da_semana`), e para a regra de vigência poder ser
    testada em `unittest` sem MySQL.
    """
    ocupados = 0

    for ocupacao in ocupacoes:
        if ocupacao["data_inicio"] > data:
            continue

        if ocupacao["data_fim"] is not None and ocupacao["data_fim"] <= data:
            continue

        ocupados += 1

    return ocupados


def _classificar_proporcao(ocupados, capacidade):
    """Classifica uma unidade mensal em "livre", "parcial" ou
    "cheia" a partir da contagem. Função pura.

    Capacidade zero é uma unidade mensal ainda sem quartos ou sem
    lugares ativos: não está cheia, está por preencher. Sem este
    caso, `ocupados >= capacidade` daria "cheia" para 0/0.

    Vive numa função própria (Fase 5, v1.4.0) porque passou a ter
    dois chamadores — `estado_detalhe` e `estados_da_semana`. Com a
    regra escrita duas vezes, bastava corrigir uma delas um dia para
    o calendário e a Gestão de Propriedades passarem a discordar
    sobre a mesma unidade.
    """
    if capacidade == 0 or ocupados == 0:
        return "livre"

    if ocupados >= capacidade:
        return "cheia"

    return "parcial"


def _contagem_mensal(unidade_id, data):
    """Devolve o par (ocupados, capacidade) de uma unidade mensal
    numa data (decisão 17: capacidade é a soma dos lugares dos
    quartos ativos; um contrato sem lugar_id conta na mesma, ver
    secção 4).

    Extraída de `_estado_mensal` em 08/09/2026, ao chegar o ecrã de
    Calendário: `estado()` devolve a proporção como texto ("6/8"), e
    o calendário precisa dos dois números separados para escolher a
    cor da célula. Partir a string na interface seria pôr regra de
    negócio na camada errada.

    Fase 5 (v1.4.0): passou a casca fina sobre `_capacidade_mensal`
    (leitura) e `_classificar_mensal` (regra). Por fora não mudou
    nada — `_estado_mensal`, `estado_detalhe` e `taxa_ocupacao`
    continuam a chamá-la exatamente como antes.
    """
    capacidade = _capacidade_mensal(unidade_id)
    ocupados = _classificar_mensal(
        repositorio.listar_ocupacoes(unidade_id=unidade_id, tipo="mensal"),
        data,
    )

    return ocupados, capacidade


def _estado_mensal(unidade_id, data):
    """Proporção "ocupados/capacidade" de uma unidade mensal numa
    data, em texto — o formato que `estado()` sempre devolveu e
    que o CLI e a Gestão de Propriedades já mostram tal e qual.
    """
    ocupados, capacidade = _contagem_mensal(unidade_id, data)

    return f"{ocupados}/{capacidade}"


def _classificar_airbnb(ocupacoes, data):
    """Livre, Ocupado ou Reservado a partir das ocupações já lidas.

    Função pura — não toca na base de dados. Fórmula de sobreposição
    da secção 4 — inicio_A < fim_B E inicio_B < fim_A — tratando
    'data' como a noite [data, data + 1 dia). Reservado é uma
    ocupação futura ainda não iniciada (início > data), quando a
    noite pedida está livre.

    Separada de `_estado_airbnb` na Fase 5 (v1.4.0) pela mesma razão
    de `_classificar_mensal`: o calendário lê uma vez e classifica
    sete dias.
    """
    fim_janela = data + timedelta(days=1)
    tem_futura = False

    for ocupacao in ocupacoes:
        if (
            ocupacao["data_inicio"] < fim_janela
            and data < ocupacao["data_fim"]
        ):
            return "Ocupado"

        if ocupacao["data_inicio"] > data:
            tem_futura = True

    return "Reservado" if tem_futura else "Livre"


def _estado_airbnb(unidade_id, data):
    """Livre, Ocupado ou Reservado de uma unidade Airbnb numa data.

    Casca fina sobre `_classificar_airbnb` desde a Fase 5 (v1.4.0) —
    faz a leitura e delega a regra. Por fora não mudou nada:
    `estado()` e `taxa_ocupacao` continuam a chamá-la como antes.
    """
    return _classificar_airbnb(
        repositorio.listar_ocupacoes(unidade_id=unidade_id, tipo="airbnb"),
        data,
    )


# Tradução dos estados textuais de `_estado_airbnb` para as chaves
# minúsculas que `estado_detalhe` devolve. Existe para o texto que a
# interface antiga já mostra ("Ocupado", com maiúscula) continuar
# intacto, sem obrigar quem consome o dicionário a comparar strings
# com maiúsculas e acentos.
_ESTADOS_AIRBNB = {
    "Ocupado": "ocupado",
    "Reservado": "reservado",
    "Livre": "livre",
}


def estado_detalhe(unidade_id, data):
    """Estado da unidade numa data, já classificado e com os números
    separados — versão estruturada de `estado()`.

    Devolve um dicionário com três chaves:

    - 'estado': "livre", "parcial", "cheia", "reservado", "ocupado"
      ou "manutencao". As três primeiras só aparecem no regime
      mensal; "reservado" e "ocupado" só no Airbnb.
    - 'ocupados' e 'capacidade': inteiros no regime mensal, None no
      Airbnb — uma unidade Airbnb é indivisível, não tem proporção
      nenhuma a mostrar (decisão 5), e None diz isso melhor do que
      um zero que se confundiria com "vazia".

    Acrescentada em 08/09/2026 para o ecrã de Calendário. `estado()`
    continua a existir sem alterações, para o CLI e a Gestão de
    Propriedades — as duas leem a mesma contagem, em
    `_contagem_mensal`.

    Em manutenção sobrepõe-se ao cálculo, tal como em `estado()`
    (decisão 3): uma unidade em manutenção nunca está livre,
    independentemente das ocupações.

    Para SETE dias seguidos da mesma unidade, usar
    `estados_da_semana` — chamar esta função sete vezes relê as
    mesmas linhas sete vezes (ver o porquê nessa docstring).
    """
    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["em_manutencao"]:
        return {
            "estado": "manutencao",
            "ocupados": None,
            "capacidade": None,
        }

    if unidade["tipo"] != "mensal":
        return {
            "estado": _ESTADOS_AIRBNB[_estado_airbnb(unidade_id, data)],
            "ocupados": None,
            "capacidade": None,
        }

    ocupados, capacidade = _contagem_mensal(unidade_id, data)

    return {
        "estado": _classificar_proporcao(ocupados, capacidade),
        "ocupados": ocupados,
        "capacidade": capacidade,
    }


def estados_da_semana(unidade_id, inicio):
    """Os sete estados de uma unidade, a começar no dia 'inicio' — o
    mesmo que sete chamadas a `estado_detalhe`, mas lendo a base de
    dados uma vez só.

    Devolve uma lista de sete dicionários com as MESMAS chaves de
    `estado_detalhe` ('estado', 'ocupados', 'capacidade'), por ordem
    de dia: o índice 0 é 'inicio', o índice 6 é 'inicio' + 6 dias.
    Levanta ValueError se a unidade não existir, com a mesma
    mensagem de `estado_detalhe` — quem chama continua a poder
    apanhá-la e saltar a linha.

    Não exige que 'inicio' seja segunda-feira: devolve sete dias a
    contar de onde lhe disserem. Quem decide que a semana vai de
    segunda a domingo é o calendário, não este módulo.

    PORQUÊ (Fase 5, v1.4.0): nenhuma das leituras de que o estado
    depende recebe a data — `listar_ocupacoes` devolve todas as
    ocupações da unidade, `listar_quartos`/`listar_lugares` devolvem
    a estrutura física inteira, e o filtro por data acontece todo em
    Python, depois. Sete chamadas a `estado_detalhe` para a mesma
    unidade traziam por isso exatamente as mesmas linhas sete vezes.
    Medido no calendário a 16/09/2026: 183 ligações ao MySQL por
    mudança de semana, a ~9ms cada (o `repositorio` abre uma ligação
    nova por operação, por decisão documentada). Com esta função
    passam a 27.

    Custo por unidade: 1 query em manutenção, 2 no Airbnb, 3 + N
    quartos no mensal — em vez de 7, 14 e 7 x (3 + N).
    """
    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    dias = [inicio + timedelta(days=indice) for indice in range(7)]

    if unidade["em_manutencao"]:
        return [
            {
                "estado": "manutencao",
                "ocupados": None,
                "capacidade": None,
            }
            for _dia in dias
        ]

    if unidade["tipo"] != "mensal":
        ocupacoes = repositorio.listar_ocupacoes(
            unidade_id=unidade_id, tipo="airbnb"
        )
        estados = []

        for dia in dias:
            texto = _classificar_airbnb(ocupacoes, dia)
            estados.append(
                {
                    "estado": _ESTADOS_AIRBNB[texto],
                    "ocupados": None,
                    "capacidade": None,
                }
            )

        return estados

    capacidade = _capacidade_mensal(unidade_id)
    ocupacoes = repositorio.listar_ocupacoes(
        unidade_id=unidade_id, tipo="mensal"
    )
    estados = []

    for dia in dias:
        ocupados = _classificar_mensal(ocupacoes, dia)
        estados.append(
            {
                "estado": _classificar_proporcao(ocupados, capacidade),
                "ocupados": ocupados,
                "capacidade": capacidade,
            }
        )

    return estados


def taxa_ocupacao(data, tipo=None):
    """Taxa de ocupação agregada de todas as unidades ativas, numa
    data — devolve o par (ocupados, total).

    Cada regime mede-se na sua unidade natural (decisão tomada com
    o aluno, 13/09/2026, ao planear o dashboard):

    - tipo="airbnb" → (unidades ocupadas, unidades ativas). Uma
      unidade Airbnb é indivisível (decisão 5), por isso a unidade
      natural de medida é a própria unidade: ou está ocupada, ou
      não está.
    - tipo="mensal" → (lugares ocupados, lugares totais). Uma
      unidade mensal tem vários lugares (decisão 17), e a pergunta
      "quanto está ocupado" só faz sentido ao nível do lugar.
    - tipo=None → soma os dois regimes (unidades Airbnb ocupadas +
      lugares mensais ocupados, unidades Airbnb + lugares mensais).
      Só serve para um número de topo; qualquer leitura em detalhe
      deve passar um tipo concreto.

    Unidades inativas e unidades em manutenção ficam de fora da
    contagem nos dois lados (numerador e denominador): uma unidade
    desativada não faz parte da oferta, e uma em manutenção também
    não (decisão 3 — manutenção sobrepõe-se ao cálculo). Isto é o
    que distingue esta função de `estado_detalhe`, que classifica
    uma unidade isolada; aqui a pergunta é "de tudo o que está em
    oferta, quanto é que está ocupado".

    Uma unidade mensal ainda sem quartos ou sem lugares ativos
    contribui com 0 lugares para o total — está por preencher, não
    está ocupada. `estado_detalhe` trata este caso como "livre"
    (via capacidade==0), e é coerente com o que aqui se faz.
    """
    if tipo is not None and tipo not in ("mensal", "airbnb"):
        raise ValueError(f"Tipo de unidade desconhecido: {tipo}")

    ocupados = 0
    total = 0

    for unidade in listar(tipo=tipo):
        if unidade["em_manutencao"]:
            continue

        if unidade["tipo"] == "airbnb":
            total += 1

            if _estado_airbnb(unidade["id"], data) == "Ocupado":
                ocupados += 1

        else:  # mensal
            ocupados_unidade, capacidade = _contagem_mensal(
                unidade["id"], data
            )
            ocupados += ocupados_unidade
            total += capacidade

    return ocupados, total


def proxima_disponibilidade(unidade_id, data):
    """Devolve (data_inicio, data_fim) da próxima janela livre da
    unidade a partir de 'data', ou None se não houver nenhuma
    ocupação futura registada.

    Só faz sentido para unidades Airbnb — uma unidade mensal tem
    ocupações sem termo previsto, e "próxima janela livre" não é
    uma pergunta que se responda com o modelo atual. Levanta
    ValueError se a unidade for mensal.

    A janela começa no dia seguinte à última ocupação ativa que
    ainda vai começar (ou que já começou mas ainda não terminou —
    a partir de hoje, é a mesma coisa). Termina na data de início
    da ocupação seguinte, ou fica em aberto (None) se não houver
    nenhuma.

    Devolve None quando não há nenhuma ocupação futura — a unidade
    está livre a partir de 'data' e não há nada a anunciar a seguir.

    Não é uma função de apresentação: devolve dates, quem chama
    formata. Vive aqui e não em contratos.py porque é uma pergunta
    sobre o estado físico da unidade, e é este módulo que trata de
    unidades (mesma lógica que levou `quarto_privativo_ocupado`
    para aqui, em vez de para contratos.py).
    """
    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    if unidade["tipo"] != "airbnb":
        raise ValueError(
            "A próxima disponibilidade só se calcula para unidades "
            "Airbnb."
        )

    # Ocupações ativas cujo data_fim ainda não passou — as que
    # interessam para "quando é que isto volta a estar livre".
    ocupacoes = [
        o
        for o in repositorio.listar_ocupacoes(
            unidade_id=unidade_id, tipo="airbnb"
        )
        if o["data_fim"] is not None and o["data_fim"] > data
    ]

    if not ocupacoes:
        return None

    ocupacoes.sort(key=lambda o: o["data_fim"])

    inicio = ocupacoes[-1]["data_fim"]

    # Fim: a próxima ocupação cujo início já seja depois da janela
    # que estamos a anunciar. Se não houver, a janela fica aberta
    # (None), e quem chama mostra "sem fim previsto".
    seguintes = [
        o["data_inicio"] for o in ocupacoes if o["data_inicio"] > inicio
    ]

    if not seguintes:
        return (inicio, None)

    return (inicio, min(seguintes))

# --- atribuição de responsáveis a unidades ---------------------------
#
# Liga um responsável à gestão de uma ou mais unidades — quem faz a
# limpeza, quem acompanha a manutenção, etc. Acrescentado em
# 09/09/2026, a pedido do ecrã de Gestão de Responsáveis: o balão
# que aparece ao passar o rato sobre o ID de um responsável mostra
# as unidades que ele gere, e precisava de vir de algum lado.
#
# Não existia nenhuma ligação entre responsável e unidade até aqui —
# confirmado antes de começar: `responsavel_id` só aparecia em
# requisições, devoluções e movimentos, ou seja, o responsável
# liga-se ao que FAZ, nunca a um sítio onde está colocado. Esta é a
# primeira vez que essa ligação existe.
#
# Um responsável pode gerir várias unidades, e uma unidade pode ter
# vários responsáveis — é a relação mais simples que cobre prédios
# onde a limpeza é feita por mais do que uma pessoa. Uma ligação
# nunca é apagada, só desativada (mesma convenção do resto do
# sistema): perder o histórico de quem geriu o quê não seria
# aceitável só porque a pessoa deixou de gerir aquela unidade hoje.


def atribuir_responsavel(unidade_id, responsavel_id):
    """Liga um responsável à gestão de uma unidade.

    Se a ligação já tiver existido e tiver sido removida, reativa-a
    em vez de inserir uma segunda linha — o par (responsavel_id,
    unidade_id) é único na base de dados, e inserir o mesmo par
    outra vez chocaria com essa restrição.

    Levanta ValueError se a unidade ou o responsável não existirem,
    ou se a ligação já estiver ativa.
    """
    unidade = procurar(unidade_id)

    if unidade is None:
        raise ValueError(f"A unidade {unidade_id} não existe.")

    responsavel = responsaveis.procurar(responsavel_id)

    if responsavel is None:
        raise ValueError(f"O responsável {responsavel_id} não existe.")

    existente = repositorio.procurar_atribuicao(responsavel_id, unidade_id)

    if existente is not None:
        if existente["ativo"]:
            raise ValueError(
                f"{responsavel['nome']} já gere a unidade "
                f"{unidade['nome']}."
            )

        repositorio.atualizar_atribuicao(existente["id"], {"ativo": True})
        existente["ativo"] = True

        return existente

    atribuicao = {
        "id": repositorio.proximo_id(PREFIXO_ATRIBUICAO),
        "responsavel_id": responsavel_id,
        "unidade_id": unidade_id,
        "ativo": True,
    }
    repositorio.inserir_atribuicao(atribuicao)

    return atribuicao


def remover_atribuicao(unidade_id, responsavel_id):
    """Desliga um responsável da gestão de uma unidade.

    Desativa a ligação em vez de a apagar, pela mesma razão que
    nenhum outro registo do sistema é apagado a sério: o histórico
    de quem geriu o quê fica gravado.

    Levanta ValueError se a ligação não existir ou já estiver
    inativa.
    """
    atribuicao = repositorio.procurar_atribuicao(responsavel_id, unidade_id)

    if atribuicao is None or not atribuicao["ativo"]:
        raise ValueError(
            f"O responsável {responsavel_id} não gere atualmente a "
            f"unidade {unidade_id}."
        )

    repositorio.atualizar_atribuicao(atribuicao["id"], {"ativo": False})


def unidades_geridas_por(responsavel_id):
    """Devolve as unidades (registos completos) que este responsável
    gere atualmente.

    Lista vazia significa que não gere nenhuma — não é erro nenhum,
    é o estado normal de um responsável recém-criado.
    """
    atribuicoes = repositorio.listar_atribuicoes(
        responsavel_id=responsavel_id
    )

    geridas = []

    for atribuicao in atribuicoes:
        unidade = procurar(atribuicao["unidade_id"])

        # Uma unidade referenciada por uma atribuição nunca devia
        # deixar de existir (não há apagamento a sério no sistema),
        # mas salta-se em vez de rebentar caso aconteça.
        if unidade is not None:
            geridas.append(unidade)

    return geridas