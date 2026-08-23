"""Interface de linha de comando — a única camada de interação com quem
usa o sistema (decisão 7).

É aqui, e só aqui, que existem `input()` e `print()`. Os módulos de
negócio (`propriedades.py`, `unidades.py`, `clientes.py`,
`responsaveis.py`, `contratos.py`, `estoque.py`) recebem e devolvem
dados por `return` e sinalizam erro com `raise ValueError` — não sabem
que existe um ecrã. É este módulo que faz a ponte: lê texto do
teclado, converte para os tipos internos (`Decimal`, `date`, `int`,
`bool`), chama a função de negócio, e mostra o resultado ou o erro.

Quem carrega e grava os dados é o `main.py`, através do repositório —
este módulo recebe a estrutura de dados já carregada, tal como os
módulos de negócio (secção 5.1 das orientações).
"""

from datetime import date
from decimal import Decimal, InvalidOperation

import clientes
import config
import contratos
import estoque
import propriedades
import repositorio
import responsaveis
import unidades
import validacoes


def mostrar_erro_arranque(mensagem):
    """Mostra um erro fatal de arranque, antes de o sistema chegar
    ao menu principal.
    """
    print(f"\nErro fatal: {mensagem}")
    print("O sistema não pode continuar.")


def ler_texto(mensagem, obrigatorio=True):
    """Lê uma linha de texto do teclado, validando obrigatoriedade.

    Repete o pedido enquanto o campo for obrigatório e vier vazio —
    nunca deixa passar um obrigatório em branco para o módulo de
    negócio, que rejeitaria com `raise ValueError` só depois de já
    ter gasto a leitura. Um campo opcional aceita "" (cadeia vazia)
    e devolve-a sem insistir, mesma convenção de "campo em branco"
    usada em `clientes.criar` para email, telefone, morada e
    nacionalidade (decisão 11).

    `strip()` aqui evita que espaços em branco à volta do texto
    cheguem ao módulo de negócio como se fossem conteúdo — os
    módulos de negócio já fazem `strip()` outra vez internamente,
    mas isso protege-os de quem os chame diretamente (testes, por
    exemplo); esta função protege quem escreve espaços sem querer
    no teclado.
    """
    while True:
        valor = input(mensagem).strip()

        if valor or not obrigatorio:
            return valor

        print("Este campo é obrigatório.")

def ler_inteiro(mensagem, obrigatorio=True, minimo=None):
    """Lê um número inteiro do teclado, convertendo e validando.

    Reaproveita `ler_texto` para a obrigatoriedade — não repete aqui
    o ciclo "pede, valida vazio, repete", só acrescenta a conversão
    para `int` e, se indicado, um valor mínimo aceite.

    Um campo opcional deixado em branco devolve `None`, nunca `0` —
    são coisas diferentes (mesma distinção que `atualizar_lugar`,
    `criar_produto` etc. fazem entre "não alterar" e "valor zero").
    Cabe a quem chamar decidir se, perante `None`, omite o argumento
    para a função de negócio usar o valor por omissão, ou trata
    `None` doutra forma.

    `minimo` é genérico de propósito — serve tanto para "capacidade
    ≥ 1" (`validacoes.validar_capacidade_lugar`) como para
    "quantidade > 0" em vários pontos de `estoque.py`; a validação
    de limite superior ou de regras mais finas (ex.: dia de
    vencimento entre 1 e 28) fica para os módulos de negócio, que já
    a fazem — esta função só evita reenviar lixo óbvio.
    """
    while True:
        texto = ler_texto(mensagem, obrigatorio)

        if not texto and not obrigatorio:
            return None

        try:
            valor = int(texto)
        except ValueError:
            print("Introduz um número inteiro válido.")
            continue

        if minimo is not None and valor < minimo:
            print(f"O valor tem de ser pelo menos {minimo}.")
            continue

        return valor

def ler_decimal(mensagem, obrigatorio=True, minimo=None):
    """Lê um valor monetário do teclado, convertendo para Decimal.

    Decimal é o tipo usado para dinheiro em todo o sistema (decisão
    4) — nunca float, para não deixar entrar erro de arredondamento
    binário em rendas, preços e cauções. Reaproveita `ler_texto`
    para a obrigatoriedade, mesmo padrão de `ler_inteiro`.

    Aceita vírgula como separador decimal, além do ponto — é o que
    se escreve por hábito em PT-PT — e troca-a por ponto antes de
    entregar a `Decimal`, que só reconhece ponto.

    Recusa `NaN` e infinito: `Decimal("NaN")` e `Decimal("Infinity")`
    não levantam exceção na conversão (são literais válidos do
    tipo), mas não fazem sentido nenhum como preço ou renda — sem
    este `is_finite()`, um utilizador que escrevesse "nan" por
    engano passaria incólume por esta função e só rebentaria mais
    tarde, dentro de `validacoes.validar_caucao` ou algures em
    `contratos.py`, com um erro bem mais difícil de ligar à origem.

    Um campo opcional deixado em branco devolve `None`, nunca
    `Decimal("0")` — mesma distinção de `ler_inteiro`.
    """
    while True:
        texto = ler_texto(mensagem, obrigatorio)

        if not texto and not obrigatorio:
            return None

        texto = texto.replace(",", ".")

        try:
            valor = Decimal(texto)
        except InvalidOperation:
            print("Introduz um valor monetário válido.")
            continue

        if not valor.is_finite():
            print("Introduz um valor monetário válido.")
            continue

        if minimo is not None and valor < minimo:
            print(f"O valor tem de ser pelo menos {minimo}.")
            continue

        return valor


def ler_data(mensagem, obrigatorio=True):
    """Lê uma data do teclado, no formato DD/MM/AAAA.

    Decisão 4: ISO no armazenamento, DD/MM/AAAA na apresentação — é
    este segundo formato que o utilizador escreve e lê aqui; a
    conversão para/de ISO fica só dentro de `repositorio.py`, ao
    gravar e ao carregar. Este módulo nunca vê nem produz texto ISO.

    Reaproveita `ler_texto` para a obrigatoriedade, mesmo padrão de
    `ler_inteiro` e `ler_decimal`. Um campo opcional deixado em
    branco devolve `None` — coerente com `data_fim` de um contrato
    mensal em vigor (decisão da secção 4: fica nulo, nunca uma data
    qualquer nem uma cadeia vazia).

    Não valida aqui se a data faz sentido no contexto (passado,
    futuro, dentro de um intervalo) — só que é uma data real do
    calendário. Essa validação de contexto já existe em
    `validacoes.validar_intervalo` e é feita depois, com as duas
    datas em mãos.
    """
    while True:
        texto = ler_texto(mensagem, obrigatorio)

        if not texto and not obrigatorio:
            return None

        try:
            dia, mes, ano = texto.split("/")
            valor = date(int(ano), int(mes), int(dia))
        except (ValueError, TypeError):
            print("Introduz uma data válida, no formato DD/MM/AAAA.")
            continue

        return valor


def confirmar(mensagem):
    """Pede confirmação explícita (sim/não) para uma operação.

    Usada nos pontos em que as decisões da arquitetura exigem
    confirmação explícita antes de prosseguir: caução nula ou
    acima da renda sugerida (decisão 14), anonimização de um
    cliente — operação irreversível (decisão 8) —, atribuir um
    segundo lugar num quarto privativo já ocupado (decisão 17).

    Reaproveita `ler_texto` para garantir que a resposta não vem
    vazia (obrigatório por omissão) — não é preciso reescrever esse
    ciclo aqui, só validar que o que veio é uma de duas respostas
    reconhecidas.

    Não tem valor por omissão: perante um "enter" em branco ou uma
    resposta não reconhecida, insiste. Decidir sozinho por quem usa
    o sistema, numa operação que a arquitetura marcou como exigindo
    confirmação explícita, seria o oposto do que essa exigência
    existe para garantir.
    """
    while True:
        resposta = ler_texto(f"{mensagem} (s/n): ").lower()

        if resposta in ("s", "sim"):
            return True

        if resposta in ("n", "não", "nao"):
            return False

        print("Responde 's' ou 'n'.")

def mostrar_menu(titulo, opcoes, texto_saida="Sair"):
    """Mostra um menu numerado com saída/voltar embutida em "0",
    aceitando tanto o número como o texto da opção.

    A opção de saída/voltar fica sempre no número 0 e na última
    linha mostrada, seja qual for o menu — convenção fixa em todo o
    sistema, para nunca haver de adivinhar onde está. `texto_saida`
    troca o rótulo consoante o contexto: "Sair" no menu principal,
    "Voltar" nos submenus de cada módulo (propriedades, unidades,
    clientes...).

    Aceita tanto o número como o texto exato da opção, sem
    distinguir maiúsculas de minúsculas nem espaços à volta — para
    quem prefere escrever o nome da ação a contar linhas. As duas
    formas são equivalentes: dão sempre o mesmo resultado.

    Devolve o índice da opção escolhida (base 0, dentro de
    'opcoes' — nunca conta a opção de saída), ou None quando a
    escolha foi sair/voltar. É o None que quem chama usa para
    terminar o ciclo do menu.

    Deixa de reaproveitar `ler_inteiro`: a entrada aqui pode ser
    número ou texto, e `ler_inteiro` só sabe recusar o que não é
    número — continua a reaproveitar `ler_texto`, para a
    obrigatoriedade da resposta.
    """
    print(f"\n{titulo}")

    for posicao, opcao in enumerate(opcoes, start=1):
        print(f"{posicao}. {opcao}")

    print(f"0. {texto_saida}")


    rotulos: dict[str, int | None] = {
        opcao.strip().lower(): indice
        for indice, opcao in enumerate(opcoes)
    }
    rotulos[texto_saida.strip().lower()] = None

    while True:
        escolha = ler_texto("Escolha uma opção: ").strip().lower()

        if escolha.isdigit():
            numero = int(escolha)

            if numero == 0:
                return None

            if 1 <= numero <= len(opcoes):
                return numero - 1

            print(f"Escolhe um número entre 0 e {len(opcoes)}.")
            continue

        if escolha in rotulos:
            return rotulos[escolha]

        print("Opção não reconhecida — escreve o número ou o nome exato.")

def formatar_data(data):
    """Converte uma data para o formato DD/MM/AAAA usado na
    apresentação.

    Inversa de `ler_data`: por dentro do sistema uma data é sempre
    um objeto `date` (decisão 4); só na fronteira com quem usa o
    sistema é que se escreve como texto — e é sempre neste formato,
    nunca ISO, que fica reservado ao ficheiro de dados
    (`repositorio.py` converte para ISO só na gravação/leitura).

    Uma data ausente (`None`) devolve um texto neutro, nunca uma
    cadeia vazia nem um erro — é o caso de `data_fim` de um
    contrato mensal em vigor (decisão da secção 4: fica nulo
    enquanto vigora), ou de `data_nascimento`/`validade_documento`
    de um cliente ainda por preencher.
    """
    if data is None:
        return "—"

    return data.strftime("%d/%m/%Y")

def formatar_valor(valor):
    """Converte um Decimal monetário para texto em PT-PT, com euro.

    Inversa de `ler_decimal`: por dentro do sistema um valor
    monetário é sempre `Decimal` (decisão 4); só na fronteira com
    quem usa o sistema se escreve como texto — sempre com vírgula
    decimal, ponto de milhar e símbolo de euro, nunca em notação de
    programação.

    Um valor ausente (`None`) devolve o mesmo texto neutro que
    `formatar_data` usa para datas ausentes — mesma convenção nos
    dois, para não obrigar quem lê o ecrã a aprender dois símbolos
    diferentes para "não há valor aqui". Não há hoje nenhum campo
    monetário opcional na estrutura de dados (`multa_praticada`,
    por exemplo, chega sempre como `Decimal("0.00")`, nunca `None`)
    — incluído por simetria e por precaução, caso surja um no
    futuro.

    Formata sempre com duas casas decimais, independentemente de
    quantas o Decimal guarde internamente: dinheiro apresenta-se
    sempre com duas casas em PT-PT, mesmo quando o valor é exato
    (45 mostra-se "45,00 €", nunca "45 €"). O ponto de milhar troca
    de posição com a vírgula decimal face ao formato de origem
    (`1,234.56` em notação de programação vira `1.234,56` em
    PT-PT) — por isso a troca é feita em dois passos com um
    marcador temporário, para as duas trocas não se atropelarem
    uma à outra.
    """
    if valor is None:
        return "—"

    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{texto} €"

def _criar_propriedade(dados):
    """Ecrã de criação de uma propriedade.

    Lê nome (obrigatório) e morada (opcional), chama
    propriedades.criar e mostra o resultado ou o erro. Grava logo
    a seguir a um sucesso — decisão tomada nesta sessão: cada ecrã
    do cli.py grava de imediato, para minimizar o que se perde se o
    programa fechar a meio (main.py só grava a cópia de segurança
    diária, não substitui esta gravação por operação).
    """
    print("\n--- Nova propriedade ---")

    nome = ler_texto("Nome: ")
    morada = ler_texto("Morada: ", obrigatorio=False)

    try:
        propriedade = propriedades.criar(dados, nome, morada)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Propriedade criada: {propriedade['id']} — "
        f"{propriedade['nome']}"
    )

def _listar_propriedades(dados):
    """Ecrã de listagem de propriedades.

    Pergunta se deve incluir as inativas — normalmente não interessam
    para o dia a dia, mas são precisas nalguns momentos (ex.: antes
    de reativar uma). Não há valor por omissão que sirva sempre, por
    isso pergunta em vez de escolher por conta própria.

    Só lê — não altera nada em 'dados', por isso não grava no fim
    (ao contrário de `_criar_propriedade`).
    """
    incluir_inativas = confirmar("Incluir propriedades inativas?")

    lista = propriedades.listar(dados, incluir_inativas=incluir_inativas)

    if not lista:
        print("\nNenhuma propriedade encontrada.")
        return

    print(f"\n--- Propriedades ({len(lista)}) ---")

    for p in lista:
        estado = "ativa" if p["ativo"] else "inativa"
        print(f"{p['id']} — {p['nome']} ({estado})")

        if p["morada"]:
            print(f"    morada: {p['morada']}")

def ler_atualizacao(mensagem, atual, permite_limpar=False):
    """Lê um campo de texto para uma atualização, distinguindo "não
    alterar" de "apagar o conteúdo".

    Traduz para o teclado a convenção que já usas em todos os
    'atualizar' dos módulos de negócio (secção 5.3 das orientações):
    None significa não alterar, "" significa apagar. Sem esta
    função, quem usa o sistema teria de reescrever o valor atual só
    para o manter — aqui, deixar em branco (Enter) já significa
    "fica como está".

    Um campo que não pode ficar vazio (ex.: nome de uma
    propriedade) usa `permite_limpar=False`: um hífen sozinho não
    tem significado especial, é tratado como texto normal. Um campo
    que pode ficar vazio (ex.: morada) usa `permite_limpar=True`: só
    aí um hífen sozinho apaga o conteúdo — fora desse caso, seria
    fácil apagar um campo sem querer ao escrever um texto que começa
    por hífen.

    Mostra o valor atual na própria mensagem, para quem responde
    decidir sem ter de consultar a listagem primeiro.
    """
    texto = input(f"{mensagem} [atual: {atual or '(vazio)'}]: ").strip()

    if not texto:
        return None

    if permite_limpar and texto == "-":
        return ""

    return texto

def _atualizar_propriedade(dados):
    """Ecrã de atualização de uma propriedade existente.

    Pede o ID, mostra os valores atuais através de `ler_atualizacao`
    para cada campo — Enter em branco mantém, hífen sozinho apaga
    onde é permitido (só a morada; o nome nunca pode ficar vazio,
    por isso não permite limpar).
    """
    print("\n--- Atualizar propriedade ---")

    propriedade_id = ler_texto("ID da propriedade: ")
    propriedade = propriedades.procurar(dados, propriedade_id)

    if propriedade is None:
        print(f"Erro: A propriedade {propriedade_id} não existe.")
        return

    nome = ler_atualizacao("Nome", propriedade["nome"])
    morada = ler_atualizacao(
        "Morada", propriedade["morada"], permite_limpar=True
    )

    try:
        propriedade = propriedades.atualizar(
            dados, propriedade_id, nome=nome, morada=morada
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Propriedade atualizada: {propriedade['id']} — "
        f"{propriedade['nome']}"
    )


def _desativar_propriedade(dados):
    """Ecrã de desativação de uma propriedade.

    Pede o ID e chama propriedades.desativar. Sem confirmação extra
    antes de desativar — decisão 8 já prevê o `reativar` para
    corrigir um engano, e o próprio `desativar` recusa se a
    propriedade já estiver inativa, o que já expõe o erro em vez de
    o aceitar em silêncio. Uma confirmação aqui duplicaria essa
    proteção sem necessidade.
    """
    print("\n--- Desativar propriedade ---")

    propriedade_id = ler_texto("ID da propriedade: ")

    try:
        propriedade = propriedades.desativar(dados, propriedade_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Propriedade desativada: {propriedade['id']} — "
        f"{propriedade['nome']}"
    )

def _reativar_propriedade(dados):
    """Ecrã de reativação de uma propriedade desativada.

    Inversa exata de `_desativar_propriedade` — mesma estrutura,
    chamando `propriedades.reativar` em vez de `propriedades.
    desativar`. Sem confirmação, pela mesma razão: é a própria
    correção de um engano, não faria sentido pedir confirmação
    para corrigir uma confirmação que nem sequer existiu.
    """
    print("\n--- Reativar propriedade ---")

    propriedade_id = ler_texto("ID da propriedade: ")

    try:
        propriedade = propriedades.reativar(dados, propriedade_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Propriedade reativada: {propriedade['id']} — "
        f"{propriedade['nome']}"
    )

def menu_propriedades(dados):
    """Submenu de gestão de propriedades — o primeiro módulo de
    negócio ligado à interface.

    Amarra as cinco funções de ecrã (`_criar_propriedade`,
    `_listar_propriedades`, `_atualizar_propriedade`,
    `_desativar_propriedade`, `_reativar_propriedade`) através de
    `mostrar_menu`, num ciclo que só termina quando se escolhe
    "Voltar" (0) — devolvido por `mostrar_menu` como `None`.

    É a única função deste bloco chamada de fora (por
    `menu_principal`, ainda por escrever); as cinco que amarra
    ficam privadas (prefixo `_`) porque não fazem sentido chamadas
    diretamente de outro sítio — é exatamente para isto que serve o
    índice base 0 que `mostrar_menu` devolve: indexar `acoes`
    diretamente, sem cadeia de `if/elif`.
    """
    acoes = (
        _criar_propriedade,
        _listar_propriedades,
        _atualizar_propriedade,
        _desativar_propriedade,
        _reativar_propriedade,
    )

    rotulos = ["Criar", "Listar", "Atualizar", "Desativar", "Reativar"]

    while True:
        escolha = mostrar_menu(
            "Gestão de Propriedades", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)

def ler_escolha(mensagem, opcoes, obrigatorio=True):
    """Lê texto do teclado, aceitando só um valor de um conjunto
    fixo (comparação sem distinguir maiúsculas/minúsculas),
    devolvendo o valor exato tal como está em 'opcoes'.

    Serve campos de texto restritos a um conjunto pequeno e fixo —
    aqui o tipo da unidade (validacoes.TIPOS_UNIDADE); mais à frente
    servirá o tipo de documento de um cliente ou o tipo de um
    movimento de stock. Diferente de mostrar_menu: não numera nem
    tem opção de saída embutida — não é navegação, é um campo de
    formulário.

    obrigatorio=False permite usá-la também como filtro opcional
    numa listagem (Enter em branco devolve None, "não filtrar").
    """
    texto_opcoes = "/".join(opcoes)

    while True:
        resposta = ler_texto(
            f"{mensagem} ({texto_opcoes}): ", obrigatorio=obrigatorio
        )

        if not resposta and not obrigatorio:
            return None

        resposta_normalizada = resposta.lower()

        for opcao in opcoes:
            if resposta_normalizada == opcao.lower():
                return opcao

        print(f"Valor inválido. Escolhe um de: {texto_opcoes}.")


def ler_booleano_atualizacao(mensagem, atual):
    """Lê uma alteração para um campo booleano, permitindo manter o
    valor atual — a versão para bool de `ler_atualizacao`.

    Um booleano nunca tem "apagar" (não há conteúdo para limpar,
    só dois estados), por isso não existe aqui equivalente ao
    hífen de `ler_atualizacao`: Enter em branco mantém, "s"/"n"
    altera, qualquer outra coisa mantém e avisa.
    """
    atual_texto = "sim" if atual else "não"
    resposta = ler_texto(
        f"{mensagem} [atual: {atual_texto}] (s/n, Enter mantém): ",
        obrigatorio=False,
    ).lower()

    if not resposta:
        return None

    if resposta in ("s", "sim"):
        return True

    if resposta in ("n", "não", "nao"):
        return False

    print("Resposta não reconhecida — valor mantido.")
    return None

def _criar_unidade(dados):
    """Ecrã de criação de uma unidade.

    Os três preços são obrigatórios (decisão 6, revista: nenhum é
    anulável com recurso ao valor global) e o tipo é restrito a
    'mensal'/'airbnb' (validacoes.TIPOS_UNIDADE).
    """
    print("\n--- Nova unidade ---")

    propriedade_id = ler_texto("ID da propriedade: ")
    tipo = ler_escolha("Tipo", validacoes.TIPOS_UNIDADE)
    preco_base = ler_decimal("Preço base: ", minimo=Decimal("0"))
    preco_epoca_alta = ler_decimal(
        "Preço em época alta: ", minimo=Decimal("0")
    )
    multa_check_in_tardio = ler_decimal(
        "Multa de check-in tardio: ", minimo=Decimal("0")
    )
    epoca_alta_ativa = confirmar("Época alta ativa nesta unidade?")

    try:
        unidade = unidades.criar(
            dados,
            propriedade_id,
            tipo,
            preco_base,
            preco_epoca_alta,
            multa_check_in_tardio,
            epoca_alta_ativa=epoca_alta_ativa,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Unidade criada: {unidade['id']} ({unidade['tipo']})")


def _listar_unidades(dados):
    """Ecrã de listagem de unidades, filtrável por propriedade e tipo."""
    incluir_inativas = confirmar("Incluir unidades inativas?")

    propriedade_id = ler_texto(
        "Filtrar por propriedade (ID, Enter para todas): ",
        obrigatorio=False,
    ) or None

    tipo = ler_escolha(
        "Filtrar por tipo", validacoes.TIPOS_UNIDADE, obrigatorio=False
    )

    lista = unidades.listar(
        dados,
        incluir_inativas=incluir_inativas,
        propriedade_id=propriedade_id,
        tipo=tipo,
    )

    if not lista:
        print("\nNenhuma unidade encontrada.")
        return

    print(f"\n--- Unidades ({len(lista)}) ---")

    for u in lista:
        estado = "ativa" if u["ativo"] else "inativa"
        manutencao = " [em manutenção]" if u["em_manutencao"] else ""
        print(
            f"{u['id']} — {u['tipo']}, propriedade "
            f"{u['propriedade_id']} ({estado}){manutencao}"
        )
        print(
            f"    base: {formatar_valor(u['preco_base'])}  "
            f"época alta: {formatar_valor(u['preco_epoca_alta'])}  "
            f"multa: {formatar_valor(u['multa_check_in_tardio'])}"
        )


def _atualizar_unidade(dados):
    """Ecrã de atualização de uma unidade.

    Tipo e propriedade não se alteram (unidades.atualizar não os
    aceita — mudar de tipo ou de propriedade não corresponde a
    nenhuma operação real do negócio). Só os preços e a época alta.
    """
    print("\n--- Atualizar unidade ---")

    unidade_id = ler_texto("ID da unidade: ")
    unidade = unidades.procurar(dados, unidade_id)

    if unidade is None:
        print(f"Erro: A unidade {unidade_id} não existe.")
        return

    preco_base = ler_decimal(
        f"Preço base [atual: {formatar_valor(unidade['preco_base'])}, "
        f"Enter mantém]: ",
        obrigatorio=False,
        minimo=Decimal("0"),
    )
    preco_epoca_alta = ler_decimal(
        "Preço em época alta [atual: "
        f"{formatar_valor(unidade['preco_epoca_alta'])}, Enter mantém]: ",
        obrigatorio=False,
        minimo=Decimal("0"),
    )
    multa_check_in_tardio = ler_decimal(
        "Multa de check-in tardio [atual: "
        f"{formatar_valor(unidade['multa_check_in_tardio'])}, "
        f"Enter mantém]: ",
        obrigatorio=False,
        minimo=Decimal("0"),
    )
    epoca_alta_ativa = ler_booleano_atualizacao(
        "Época alta ativa", unidade["epoca_alta_ativa"]
    )

    try:
        unidade = unidades.atualizar(
            dados,
            unidade_id,
            preco_base=preco_base,
            preco_epoca_alta=preco_epoca_alta,
            multa_check_in_tardio=multa_check_in_tardio,
            epoca_alta_ativa=epoca_alta_ativa,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Unidade atualizada: {unidade['id']}")


def _desativar_unidade(dados):
    print("\n--- Desativar unidade ---")

    unidade_id = ler_texto("ID da unidade: ")

    try:
        unidade = unidades.desativar(dados, unidade_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Unidade desativada: {unidade['id']}")


def _reativar_unidade(dados):
    print("\n--- Reativar unidade ---")

    unidade_id = ler_texto("ID da unidade: ")

    try:
        unidade = unidades.reativar(dados, unidade_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Unidade reativada: {unidade['id']}")


def _marcar_manutencao(dados):
    """'em_manutencao' é o único estado que persiste na unidade
    (decisão 3) — livre/ocupado/reservado calculam-se dos contratos.
    """
    print("\n--- Marcar unidade em manutenção ---")

    unidade_id = ler_texto("ID da unidade: ")

    try:
        unidade = unidades.marcar_manutencao(dados, unidade_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Unidade {unidade['id']} marcada em manutenção.")


def _desmarcar_manutencao(dados):
    print("\n--- Desmarcar manutenção ---")

    unidade_id = ler_texto("ID da unidade: ")

    try:
        unidade = unidades.desmarcar_manutencao(dados, unidade_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Unidade {unidade['id']} fora de manutenção.")


def _gerir_quartos(dados):
    """Pede a unidade e, se existir, abre o submenu dos seus
    quartos — quartos e lugares vivem sempre dentro de uma unidade
    (decisão 17), por isso este passo de contexto vem antes.
    """
    unidade_id = ler_texto("ID da unidade: ")
    unidade = unidades.procurar(dados, unidade_id)

    if unidade is None:
        print(f"Erro: A unidade {unidade_id} não existe.")
        return

    _menu_quartos(dados, unidade_id)


def menu_unidades(dados):
    """Submenu de gestão de unidades. Chamada por menu_principal."""
    acoes = (
        _criar_unidade,
        _listar_unidades,
        _atualizar_unidade,
        _desativar_unidade,
        _reativar_unidade,
        _marcar_manutencao,
        _desmarcar_manutencao,
        _gerir_quartos,
    )

    rotulos = [
        "Criar",
        "Listar",
        "Atualizar",
        "Desativar",
        "Reativar",
        "Marcar em manutenção",
        "Desmarcar manutenção",
        "Gerir quartos de uma unidade",
    ]

    while True:
        escolha = mostrar_menu(
            "Gestão de Unidades", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)

def _criar_quarto(dados, unidade_id):
    """'privativo' e 'limpeza_incluida' são independentes entre si
    (decisão 17) — perguntados em separado, nunca inferido um do
    outro.
    """
    print(f"\n--- Novo quarto em {unidade_id} ---")

    nome = ler_texto("Nome do quarto: ")
    privativo = confirmar("Quarto privativo?")
    limpeza_incluida = confirmar("Limpeza incluída no cálculo de roupa?")

    try:
        quarto = unidades.criar_quarto(
            dados,
            unidade_id,
            nome,
            privativo=privativo,
            limpeza_incluida=limpeza_incluida,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Quarto criado: {quarto['id']} — {quarto['nome']}")


def _listar_quartos(dados, unidade_id):
    incluir_inativos = confirmar("Incluir quartos inativos?")

    lista = unidades.listar_quartos(
        dados, incluir_inativas=incluir_inativos, unidade_id=unidade_id
    )

    if not lista:
        print("\nNenhum quarto encontrado nesta unidade.")
        return

    print(f"\n--- Quartos de {unidade_id} ({len(lista)}) ---")

    for q in lista:
        estado = "ativo" if q["ativo"] else "inativo"
        privativo = "privativo" if q["privativo"] else "partilhado"
        limpeza = "com limpeza" if q["limpeza_incluida"] else "sem limpeza"
        print(
            f"{q['id']} — {q['nome']} ({estado}, {privativo}, {limpeza})"
        )


def _atualizar_quarto(dados, unidade_id):
    print("\n--- Atualizar quarto ---")

    quarto_id = ler_texto("ID do quarto: ")
    quarto = unidades.procurar_quarto(dados, quarto_id)

    if quarto is None:
        print(f"Erro: O quarto {quarto_id} não existe.")
        return

    if quarto["unidade_id"] != unidade_id:
        print(
            f"Erro: O quarto {quarto_id} não pertence à unidade "
            f"{unidade_id}."
        )
        return

    nome = ler_atualizacao("Nome", quarto["nome"])
    privativo = ler_booleano_atualizacao("Privativo", quarto["privativo"])
    limpeza_incluida = ler_booleano_atualizacao(
        "Limpeza incluída", quarto["limpeza_incluida"]
    )

    try:
        quarto = unidades.atualizar_quarto(
            dados,
            quarto_id,
            nome=nome,
            privativo=privativo,
            limpeza_incluida=limpeza_incluida,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Quarto atualizado: {quarto['id']} — {quarto['nome']}")


def _desativar_quarto(dados, unidade_id):
    print("\n--- Desativar quarto ---")

    quarto_id = ler_texto("ID do quarto: ")
    quarto = unidades.procurar_quarto(dados, quarto_id)

    if quarto is not None and quarto["unidade_id"] != unidade_id:
        print(
            f"Erro: O quarto {quarto_id} não pertence à unidade "
            f"{unidade_id}."
        )
        return

    try:
        quarto = unidades.desativar_quarto(dados, quarto_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Quarto desativado: {quarto['id']} — {quarto['nome']}")


def _reativar_quarto(dados, unidade_id):
    print("\n--- Reativar quarto ---")

    quarto_id = ler_texto("ID do quarto: ")
    quarto = unidades.procurar_quarto(dados, quarto_id)

    if quarto is not None and quarto["unidade_id"] != unidade_id:
        print(
            f"Erro: O quarto {quarto_id} não pertence à unidade "
            f"{unidade_id}."
        )
        return

    try:
        quarto = unidades.reativar_quarto(dados, quarto_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Quarto reativado: {quarto['id']} — {quarto['nome']}")


def _gerir_lugares(dados, unidade_id):
    """Pede o quarto (validando que pertence à unidade em curso) e
    abre o submenu dos seus lugares.
    """
    quarto_id = ler_texto("ID do quarto: ")
    quarto = unidades.procurar_quarto(dados, quarto_id)

    if quarto is None:
        print(f"Erro: O quarto {quarto_id} não existe.")
        return

    if quarto["unidade_id"] != unidade_id:
        print(
            f"Erro: O quarto {quarto_id} não pertence à unidade "
            f"{unidade_id}."
        )
        return

    _menu_lugares(dados, quarto_id)


def _menu_quartos(dados, unidade_id):
    """Submenu dos quartos de uma unidade. Só se chega aqui a
    partir de _gerir_quartos, que já validou a unidade.
    """
    acoes = (
        _criar_quarto,
        _listar_quartos,
        _atualizar_quarto,
        _desativar_quarto,
        _reativar_quarto,
        _gerir_lugares,
    )

    rotulos = [
        "Criar quarto",
        "Listar quartos",
        "Atualizar quarto",
        "Desativar quarto",
        "Reativar quarto",
        "Gerir lugares de um quarto",
    ]

    while True:
        escolha = mostrar_menu(
            f"Quartos da unidade {unidade_id}",
            rotulos,
            texto_saida="Voltar",
        )

        if escolha is None:
            return

        acoes[escolha](dados, unidade_id)

def _criar_lugar(dados, quarto_id):
    """Capacidade por omissão 1 (decisão 17 — um beliche são dois
    lugares de capacidade 1, nunca um de capacidade 2).
    """
    print(f"\n--- Novo lugar em {quarto_id} ---")

    nome = ler_texto("Nome do lugar: ")
    capacidade = ler_inteiro(
        "Capacidade [Enter para 1]: ", obrigatorio=False, minimo=1
    )

    if capacidade is None:
        capacidade = 1

    try:
        lugar = unidades.criar_lugar(
            dados, quarto_id, nome, capacidade=capacidade
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Lugar criado: {lugar['id']} — {lugar['nome']}")


def _listar_lugares(dados, quarto_id):
    incluir_inativos = confirmar("Incluir lugares inativos?")

    lista = unidades.listar_lugares(
        dados, incluir_inativas=incluir_inativos, quarto_id=quarto_id
    )

    if not lista:
        print("\nNenhum lugar encontrado neste quarto.")
        return

    print(f"\n--- Lugares de {quarto_id} ({len(lista)}) ---")

    for lg in lista:
        estado = "ativo" if lg["ativo"] else "inativo"
        print(
            f"{lg['id']} — {lg['nome']} "
            f"(capacidade {lg['capacidade']}, {estado})"
        )


def _atualizar_lugar(dados, quarto_id):
    print("\n--- Atualizar lugar ---")

    lugar_id = ler_texto("ID do lugar: ")
    lugar = unidades.procurar_lugar(dados, lugar_id)

    if lugar is None:
        print(f"Erro: O lugar {lugar_id} não existe.")
        return

    if lugar["quarto_id"] != quarto_id:
        print(
            f"Erro: O lugar {lugar_id} não pertence ao quarto "
            f"{quarto_id}."
        )
        return

    nome = ler_atualizacao("Nome", lugar["nome"])
    capacidade = ler_inteiro(
        f"Capacidade [atual: {lugar['capacidade']}, Enter mantém]: ",
        obrigatorio=False,
        minimo=1,
    )

    try:
        lugar = unidades.atualizar_lugar(
            dados, lugar_id, nome=nome, capacidade=capacidade
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Lugar atualizado: {lugar['id']} — {lugar['nome']}")


def _desativar_lugar(dados, quarto_id):
    print("\n--- Desativar lugar ---")

    lugar_id = ler_texto("ID do lugar: ")
    lugar = unidades.procurar_lugar(dados, lugar_id)

    if lugar is not None and lugar["quarto_id"] != quarto_id:
        print(
            f"Erro: O lugar {lugar_id} não pertence ao quarto "
            f"{quarto_id}."
        )
        return

    try:
        lugar = unidades.desativar_lugar(dados, lugar_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Lugar desativado: {lugar['id']} — {lugar['nome']}")


def _reativar_lugar(dados, quarto_id):
    print("\n--- Reativar lugar ---")

    lugar_id = ler_texto("ID do lugar: ")
    lugar = unidades.procurar_lugar(dados, lugar_id)

    if lugar is not None and lugar["quarto_id"] != quarto_id:
        print(
            f"Erro: O lugar {lugar_id} não pertence ao quarto "
            f"{quarto_id}."
        )
        return

    try:
        lugar = unidades.reativar_lugar(dados, lugar_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Lugar reativado: {lugar['id']} — {lugar['nome']}")


def _menu_lugares(dados, quarto_id):
    """Submenu dos lugares de um quarto — último nível da
    hierarquia física (decisão 17). Só se chega aqui a partir de
    _gerir_lugares, que já validou o quarto.
    """
    acoes = (
        _criar_lugar,
        _listar_lugares,
        _atualizar_lugar,
        _desativar_lugar,
        _reativar_lugar,
    )

    rotulos = [
        "Criar lugar",
        "Listar lugares",
        "Atualizar lugar",
        "Desativar lugar",
        "Reativar lugar",
    ]

    while True:
        escolha = mostrar_menu(
            f"Lugares do quarto {quarto_id}",
            rotulos,
            texto_saida="Voltar",
        )

        if escolha is None:
            return

        acoes[escolha](dados, quarto_id)

def _criar_responsavel(dados):
    print("\n--- Novo responsável ---")

    nome = ler_texto("Nome: ")
    contacto = ler_texto("Contacto: ", obrigatorio=False)

    try:
        responsavel = responsaveis.criar(dados, nome, contacto)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Responsável criado: {responsavel['id']} — "
        f"{responsavel['nome']}"
    )


def _listar_responsaveis(dados):
    incluir_inativos = confirmar("Incluir responsáveis inativos?")

    lista = responsaveis.listar(dados, incluir_inativos=incluir_inativos)

    if not lista:
        print("\nNenhum responsável encontrado.")
        return

    print(f"\n--- Responsáveis ({len(lista)}) ---")

    for r in lista:
        estado = "ativo" if r["ativo"] else "inativo"
        print(f"{r['id']} — {r['nome']} ({estado})")

        if r["contacto"]:
            print(f"    contacto: {r['contacto']}")


def _atualizar_responsavel(dados):
    print("\n--- Atualizar responsável ---")

    responsavel_id = ler_texto("ID do responsável: ")
    responsavel = responsaveis.procurar(dados, responsavel_id)

    if responsavel is None:
        print(f"Erro: O responsável {responsavel_id} não existe.")
        return

    nome = ler_atualizacao("Nome", responsavel["nome"])
    contacto = ler_atualizacao(
        "Contacto", responsavel["contacto"], permite_limpar=True
    )

    try:
        responsavel = responsaveis.atualizar(
            dados, responsavel_id, nome=nome, contacto=contacto
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Responsável atualizado: {responsavel['id']} — "
        f"{responsavel['nome']}"
    )


def _desativar_responsavel(dados):
    print("\n--- Desativar responsável ---")

    responsavel_id = ler_texto("ID do responsável: ")

    try:
        responsavel = responsaveis.desativar(dados, responsavel_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Responsável desativado: {responsavel['id']}")


def _reativar_responsavel(dados):
    print("\n--- Reativar responsável ---")

    responsavel_id = ler_texto("ID do responsável: ")

    try:
        responsavel = responsaveis.reativar(dados, responsavel_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Responsável reativado: {responsavel['id']}")


def _criar_cliente(dados):
    """Ecrã de criação de um cliente.

    'regime' não fica gravado (não é campo do cliente — ver
    clientes.criar) e serve só para saber se o NIF é obrigatório
    (decisão 11: bloqueia só no mensal). Peço-o antes do NIF
    precisamente para poder tornar o NIF obrigatório já no ecrã,
    em vez de deixar a rejeição só acontecer dentro de
    validacoes.validar_cliente depois de já teres preenchido tudo
    o resto.
    """
    print("\n--- Novo cliente ---")

    nome = ler_texto("Nome: ")
    tipo_documento = ler_escolha("Tipo de documento", 
                                 validacoes.TIPOS_DOCUMENTO
                                )
    
    numero_documento = ler_texto("Número de documento: ")
    regime = ler_escolha("Regime", validacoes.TIPOS_UNIDADE)

    nif = ler_texto("NIF: ", obrigatorio=(regime == "mensal"))
    email = ler_texto("Email: ", obrigatorio=False)
    telefone = ler_texto("Telefone: ", obrigatorio=False)
    morada = ler_texto("Morada: ", obrigatorio=False)
    nacionalidade = ler_texto("Nacionalidade: ", obrigatorio=False)
    data_nascimento = ler_data(
        "Data de nascimento (Enter se desconhecida): ", obrigatorio=False
    )
    validade_documento = ler_data(
        "Validade do documento (Enter se não aplicável): ",
        obrigatorio=False,
    )
    contacto_emergencia = ler_texto("Contacto de emergência: ", 
                                    obrigatorio=False
                                    )

    try:
        cliente = clientes.criar(
            dados,
            nome,
            tipo_documento,
            numero_documento,
            regime,
            nif=nif,
            email=email,
            telefone=telefone,
            morada=morada,
            nacionalidade=nacionalidade,
            data_nascimento=data_nascimento,
            validade_documento=validade_documento,
            contacto_emergencia=contacto_emergencia,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    aviso = (" [incompleto — verifica os campos em falta]"
            if cliente["incompleto"] else ""
    )
    print(f"Cliente criado: {cliente['id']} — {cliente['nome']}{aviso}")


def _listar_clientes(dados):
    """Inclui o filtro por 'incompleto' — decisão 11 exige que essa
    listagem exista, senão o aviso de campos em falta não produz
    efeito nenhum.
    """
    incluir_inativos = confirmar("Incluir clientes inativos?")

    filtro = ler_escolha(
        "Filtrar por completude", ("Todos", "Incompletos", "Completos")
    )
    assert filtro is not None  # obrigatorio=True (omisso): nunca é None

    incompleto = {"Todos": None, "Incompletos": True, 
                  "Completos": False}[filtro]

    lista = clientes.listar(
        dados, incluir_inativos=incluir_inativos, incompleto=incompleto
    )

    if not lista:
        print("\nNenhum cliente encontrado.")
        return

    print(f"\n--- Clientes ({len(lista)}) ---")

    for c in lista:
        estado = "ativo" if c["ativo"] else "inativo"
        marcas = ""
        if c["incompleto"]:
            marcas += " [incompleto]"
        if c["anonimizado"]:
            marcas += " [anonimizado]"

        print(f"{c['id']} — {c['nome']} ({estado}){marcas}")
        print(f"    {c['tipo_documento']} {c['numero_documento']}")


def _atualizar_cliente(dados):
    """Ecrã de atualização de um cliente.

    Recusa atualizar um cliente anonimizado — clientes.atualizar,
    tal como está, não faz essa verificação sozinho (registado em
    Pendencias_Correcoes_pos_0.7.0); esta guarda evita que se
    reintroduzam dados pessoais já apagados, o que contrariaria a
    irreversibilidade da decisão 8.
    """
    print("\n--- Atualizar cliente ---")

    cliente_id = ler_texto("ID do cliente: ")
    cliente = clientes.procurar(dados, cliente_id)

    if cliente is None:
        print(f"Erro: O cliente {cliente_id} não existe.")
        return

    if cliente["anonimizado"]:
        print(
            f"Erro: O cliente {cliente_id} está anonimizado; os "
            f"dados pessoais foram apagados e não podem ser "
            f"reintroduzidos."
        )
        return

    nome = ler_atualizacao("Nome", cliente["nome"])
    tipo_documento = ler_escolha_atualizacao(
        "Tipo de documento",
        validacoes.TIPOS_DOCUMENTO,
        cliente["tipo_documento"],
    )
    numero_documento = ler_atualizacao(
        "Número de documento", cliente["numero_documento"]
    )
    nif = ler_atualizacao("NIF", cliente["nif"], permite_limpar=True)
    email = ler_atualizacao("Email", cliente["email"], permite_limpar=True)
    telefone = ler_atualizacao(
        "Telefone", cliente["telefone"], permite_limpar=True
    )
    morada = ler_atualizacao("Morada", cliente["morada"], permite_limpar=True)
    nacionalidade = ler_atualizacao(
        "Nacionalidade", cliente["nacionalidade"], permite_limpar=True
    )

    exige_nif = confirmar(
        "Cliente em regime mensal (torna o NIF obrigatório)?"
    )
    regime = "mensal" if exige_nif else None

    data_nascimento = ler_data(
        "Data de nascimento [atual: "
        f"{formatar_data(cliente['data_nascimento'])}, Enter mantém]: ",
        obrigatorio=False,
    )
    validade_documento = ler_data(
        "Validade do documento [atual: "
        f"{formatar_data(cliente['validade_documento'])}, Enter mantém]: ",
        obrigatorio=False,
    )
    contacto_emergencia = ler_atualizacao(
        "Contacto de emergência",
        cliente["contacto_emergencia"],
        permite_limpar=True,
    )

    try:
        cliente = clientes.atualizar(
            dados,
            cliente_id,
            regime=regime,
            nome=nome,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            nif=nif,
            email=email,
            telefone=telefone,
            morada=morada,
            nacionalidade=nacionalidade,
            data_nascimento=data_nascimento,
            validade_documento=validade_documento,
            contacto_emergencia=contacto_emergencia,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    aviso = " [incompleto]" if cliente["incompleto"] else ""
    print(f"Cliente atualizado: {cliente['id']} — {cliente['nome']}{aviso}")


def _desativar_cliente(dados):
    print("\n--- Desativar cliente ---")

    cliente_id = ler_texto("ID do cliente: ")

    try:
        cliente = clientes.desativar(dados, cliente_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Cliente desativado: {cliente['id']} — {cliente['nome']}")


def _reativar_cliente(dados):
    print("\n--- Reativar cliente ---")

    cliente_id = ler_texto("ID do cliente: ")

    try:
        cliente = clientes.reativar(dados, cliente_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Cliente reativado: {cliente['id']} — {cliente['nome']}")


def _anonimizar_cliente(dados):
    """Ecrã de anonimização — operação IRREVERSÍVEL (decisão 8,
    RGPD secção 6). Valida o responsável com
    responsaveis.validar_autoria antes de anonimizar: é exatamente
    o passo que o docstring de clientes.anonimizar deixou marcado
    como pendente para quando responsaveis.py existisse — já
    existe, por isso a verificação faz-se aqui.
    """
    print("\n--- Anonimizar cliente ---")
    print("ATENÇÃO: operação irreversível. Apaga os dados pessoais")
    print("do cliente e não pode ser desfeita.")

    cliente_id = ler_texto("ID do cliente: ")
    cliente = clientes.procurar(dados, cliente_id)

    if cliente is None:
        print(f"Erro: O cliente {cliente_id} não existe.")
        return

    if cliente["anonimizado"]:
        print(f"Erro: O cliente {cliente_id} já está anonimizado.")
        return

    print(
        f"Cliente: {cliente['nome']} "
        f"({cliente['tipo_documento']} {cliente['numero_documento']})"
    )

    if not confirmar(
        f"Confirmas a anonimização IRREVERSÍVEL de {cliente['id']}?"
    ):
        print("Anonimização cancelada.")
        return

    responsavel_id = ler_texto("ID do responsável que autoriza: ")

    try:
        responsaveis.validar_autoria(dados, responsavel_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    data = ler_data(
        "Data da anonimização (Enter para hoje): ", obrigatorio=False
    )

    if data is None:
        data = date.today()

    try:
        cliente = clientes.anonimizar(dados, cliente_id, responsavel_id, data)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Cliente {cliente['id']} anonimizado.")


def menu_clientes(dados):
    """Submenu de gestão de clientes. Chamada por menu_principal.

    Inclui a anonimização (decisão 8, RGPD, irreversível) como
    sexta opção, ao lado das cinco ações habituais — é a única
    entidade do sistema com esta operação extra.
    """
    
    acoes = (
        _criar_cliente,
        _listar_clientes,
        _atualizar_cliente,
        _desativar_cliente,
        _reativar_cliente,
        _anonimizar_cliente,
    )

    rotulos = [
        "Criar",
        "Listar",
        "Atualizar",
        "Desativar",
        "Reativar",
        "Anonimizar (irreversível)",
    ]

    while True:
        escolha = mostrar_menu(
            "Gestão de Clientes", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)

        

def menu_responsaveis(dados):
    """Submenu de gestão de responsáveis. Chamada por menu_principal."""

    acoes = (
        _criar_responsavel,
        _listar_responsaveis,
        _atualizar_responsavel,
        _desativar_responsavel,
        _reativar_responsavel,
    )

    rotulos = ["Criar", "Listar", "Atualizar", "Desativar", "Reativar"]

    while True:
        escolha = mostrar_menu(
            "Gestão de Responsáveis", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)

def ler_escolha_atualizacao(mensagem, opcoes, atual):
    """Lê uma alteração para um campo de escolha restrita, permitindo
    manter o valor atual — versão de `ler_atualizacao` para um
    conjunto fixo de valores (ex.: tipo de documento) em vez de
    texto livre.
    """
    texto_opcoes = "/".join(opcoes)
    resposta = ler_texto(
        f"{mensagem} [atual: {atual}] ({texto_opcoes}, Enter mantém): ",
        obrigatorio=False,
    )

    if not resposta:
        return None

    resposta_normalizada = resposta.lower()

    for opcao in opcoes:
        if resposta_normalizada == opcao.lower():
            return opcao

    print(f"Valor inválido — mantido '{atual}'.")
    return None

def _detalhes_mensal(dados, ocupacao_id):
    """Devolve o registo específico de um contrato mensal, ou None.

    Réplica funcional de contratos._dados_mensais — essa é privada
    (prefixo _) e só deveria ser usada dentro de contratos.py; esta
    existe só para o cli.py poder mostrar valores atuais (renda,
    caução, dia de vencimento) antes de pedir uma atualização. Só
    lê, nunca decide nada — ver nota na explicação sobre a
    alternativa mais limpa (expor isto como função pública em
    contratos.py).
    """
    for registo in dados["ocupacoes_mensal"]:
        if registo["ocupacao_id"] == ocupacao_id:
            return registo

    return None


def _detalhes_airbnb(dados, ocupacao_id):
    """Mesma ideia de `_detalhes_mensal`, para reservas Airbnb."""
    for registo in dados["ocupacoes_airbnb"]:
        if registo["ocupacao_id"] == ocupacao_id:
            return registo

    return None

def _criar_contrato_mensal(dados):
    """Ecrã de criação de um contrato mensal.

    Mostra a renda calculada (preço base da unidade) antes de pedir
    a praticada, e pede motivo se forem diferentes — decisão 14: o
    calculado e o praticado ficam sempre visíveis lado a lado.
    Chama validacoes.validar_caucao diretamente, ANTES de chamar
    contratos.criar_mensal, para poder agir sobre o resultado
    (True = exige confirmação explícita) — ver explicação, é a
    lacuna mais importante encontrada nesta sessão.
    """
    print("\n--- Novo contrato mensal ---")

    unidade_id = ler_texto("ID da unidade: ")
    unidade = unidades.procurar(dados, unidade_id)

    if unidade is None:
        print(f"Erro: A unidade {unidade_id} não existe.")
        return

    cliente_id = ler_texto("ID do cliente: ")
    data_inicio = ler_data("Data de início: ")
    lugar_id = ler_texto(
        "ID do lugar (Enter se não aplicável): ", obrigatorio=False
    )
    dia_vencimento = ler_inteiro(
        f"Dia de vencimento [Enter para {config.DIA_VENCIMENTO}]: ",
        obrigatorio=False,
        minimo=1,
    )

    if dia_vencimento is not None and dia_vencimento > 28:
        print("Erro: O dia de vencimento tem de estar entre 1 e 28.")
        return

    print(
        "Renda calculada (preço base da unidade): "
        f"{formatar_valor(unidade['preco_base'])}"
    )

    renda_praticada = ler_decimal("Renda praticada: ")

    motivo_alteracao_renda = ""
    if renda_praticada != unidade["preco_base"]:
        motivo_alteracao_renda = ler_texto(
            "Motivo da diferença face à renda calculada (opcional): ",
            obrigatorio=False,
        )

    caucao = ler_decimal("Caução: ", minimo=Decimal("0"))

    try:
        exige_confirmacao = validacoes.validar_caucao(
            caucao, renda_praticada, config.MULTIPLICADOR_MAXIMO_CAUCAO
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    motivo_alteracao_caucao = ""
    if exige_confirmacao:
        if not confirmar(
            f"A caução ({formatar_valor(caucao)}) é nula ou superior à "
            f"renda praticada — confirmas?"
        ):
            print("Criação cancelada.")
            return

        motivo_alteracao_caucao = ler_texto(
            "Motivo (opcional): ", obrigatorio=False
        )

    try:
        ocupacao, mensal = contratos.criar_mensal(
            dados,
            unidade_id,
            cliente_id,
            data_inicio,
            renda_praticada,
            caucao,
            lugar_id=lugar_id,
            dia_vencimento=dia_vencimento,
            motivo_alteracao_renda=motivo_alteracao_renda,
            motivo_alteracao_caucao=motivo_alteracao_caucao,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    aviso = (
        " [aviso: documento expira durante a estadia]"
        if ocupacao["aviso_documento"]
        else ""
    )
    print(f"Contrato criado: {ocupacao['id']}{aviso}")


def _criar_reserva_airbnb(dados):
    """Ecrã de registo de uma reserva Airbnb.

    Mostra o preço calculado ANTES de pedir o praticado, através de
    contratos.calcular_preco_airbnb — a função pública que resolve
    a pendência que existia aqui (antes, só dava para saber o
    calculado depois de a reserva já estar registada).

    Quando o praticado (preço ou multa) fica abaixo do calculado, é
    um desconto: pede confirmação e o ID de um responsável que o
    autorize (decisão 18), antes de chamar contratos.registar_airbnb.
    """
    print("\n--- Nova reserva Airbnb ---")

    unidade_id = ler_texto("ID da unidade: ")
    unidade = unidades.procurar(dados, unidade_id)

    if unidade is None:
        print(f"Erro: A unidade {unidade_id} não existe.")
        return

    cliente_id = ler_texto("ID do cliente: ")
    data_inicio = ler_data("Data de check-in: ")
    data_fim = ler_data("Data de check-out: ")

    preco_calculado = contratos.calcular_preco_airbnb(
        unidade, data_inicio, data_fim
    )
    print(f"Preço calculado: {formatar_valor(preco_calculado)}")

    check_in_tardio = confirmar("Check-in tardio?")
    hora_chegada = ""
    multa_praticada = None
    responsavel_desconto_multa_id = ""

    if check_in_tardio:
        hora_chegada = ler_texto("Hora de chegada (HH:MM): ")
        multa_calculada = unidade["multa_check_in_tardio"]
        print(
            "Multa calculada (configuração da unidade): "
            f"{formatar_valor(multa_calculada)}"
        )
        multa_praticada = ler_decimal(
            "Multa praticada [Enter para "
            f"{formatar_valor(multa_calculada)}]: ",
            obrigatorio=False,
            minimo=Decimal("0"),
        )

        if multa_praticada is None:
            multa_praticada = multa_calculada

        if multa_praticada < multa_calculada:
            if not confirmar(
                f"A multa praticada ({formatar_valor(multa_praticada)}) "
                f"é inferior à calculada "
                f"({formatar_valor(multa_calculada)}) — confirmas o "
                f"perdão?"
            ):
                print("Criação cancelada.")
                return

            responsavel_desconto_multa_id = ler_texto(
                "ID do responsável que autoriza este perdão: "
            )

    preco_praticado = ler_decimal("Preço praticado (total da estadia): ")
    responsavel_desconto_preco_id = ""

    if preco_praticado is not None and preco_praticado < preco_calculado:
        if not confirmar(
            f"O preço praticado ({formatar_valor(preco_praticado)}) é "
            f"inferior ao calculado ({formatar_valor(preco_calculado)}) "
            f"— confirmas o desconto?"
        ):
            print("Criação cancelada.")
            return

        responsavel_desconto_preco_id = ler_texto(
            "ID do responsável que autoriza este desconto: "
        )

    try:
        ocupacao, airbnb = contratos.registar_airbnb(
            dados,
            unidade_id,
            cliente_id,
            data_inicio,
            data_fim,
            preco_praticado,
            responsavel_desconto_preco_id=responsavel_desconto_preco_id,
            check_in_tardio=check_in_tardio,
            hora_chegada=hora_chegada,
            multa_praticada=multa_praticada,
            responsavel_desconto_multa_id=responsavel_desconto_multa_id,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    aviso = (
        " [aviso: documento expira durante a estadia]"
        if ocupacao["aviso_documento"]
        else ""
    )
    desconto_preco = (
        f"  [desconto autorizado por "
        f"{airbnb['responsavel_desconto_preco_id']}]"
        if airbnb["responsavel_desconto_preco_id"]
        else ""
    )
    print(f"Reserva registada: {ocupacao['id']}{aviso}")
    print(
        f"    calculado: {formatar_valor(airbnb['preco_calculado'])}  "
        f"praticado: {formatar_valor(airbnb['preco_praticado'])}"
        f"{desconto_preco}"
    )


def _listar_ocupacoes(dados):
    incluir_inativas = confirmar("Incluir ocupações inativas/encerradas?")

    unidade_id = ler_texto(
        "Filtrar por unidade (ID, Enter para todas): ", obrigatorio=False
    ) or None
    cliente_id = ler_texto(
        "Filtrar por cliente (ID, Enter para todos): ", obrigatorio=False
    ) or None
    tipo = ler_escolha(
        "Filtrar por tipo", validacoes.TIPOS_UNIDADE, obrigatorio=False
    )
    filtro_aviso = ler_escolha(
        "Filtrar por aviso de documento", ("Todos", "Com aviso", "Sem aviso")
    )
    assert filtro_aviso is not None  # obrigatorio=True (omisso): nunca é None

    aviso_documento = {
        "Todos": None, "Com aviso": True, "Sem aviso": False
    }[filtro_aviso]

    lista = contratos.listar(
        dados,
        incluir_inativas=incluir_inativas,
        unidade_id=unidade_id,
        cliente_id=cliente_id,
        tipo=tipo,
        aviso_documento=aviso_documento,
    )

    if not lista:
        print("\nNenhuma ocupação encontrada.")
        return

    print(f"\n--- Ocupações ({len(lista)}) ---")

    for o in lista:
        estado = "ativa" if o["ativo"] else "encerrada/cancelada"
        aviso = " [aviso: documento]" if o["aviso_documento"] else ""
        print(
            f"{o['id']} — {o['tipo']}, unidade {o['unidade_id']}, "
            f"cliente {o['cliente_id']} ({estado}){aviso}"
        )
        print(
            f"    {formatar_data(o['data_inicio'])} → "
            f"{formatar_data(o['data_fim'])}"
        )


def _atualizar_contrato_mensal(dados):
    print("\n--- Atualizar contrato mensal ---")

    ocupacao_id = ler_texto("ID do contrato: ")
    ocupacao = contratos.procurar(dados, ocupacao_id)

    if ocupacao is None:
        print(f"Erro: A ocupação {ocupacao_id} não existe.")
        return

    if ocupacao["tipo"] != "mensal":
        print(f"Erro: A ocupação {ocupacao_id} não é um contrato mensal.")
        return

    mensal = _detalhes_mensal(dados, ocupacao_id)

    if mensal is None:
        print(
            f"Erro: Faltam os dados mensais da ocupação {ocupacao_id} "
            f"(inconsistência nos dados)."
        )
        return

    renda_praticada = ler_decimal(
        "Renda praticada [atual: "
        f"{formatar_valor(mensal['renda_praticada'])}, Enter mantém]: ",
        obrigatorio=False,
    )
    caucao = ler_decimal(
        f"Caução [atual: {formatar_valor(mensal['caucao'])}, "
        f"Enter mantém]: ",
        obrigatorio=False,
        minimo=Decimal("0"),
    )

    motivo_alteracao_renda = None
    if renda_praticada is not None:
        motivo_alteracao_renda = ler_texto(
            "Motivo da alteração da renda (opcional): ", obrigatorio=False
        )

    motivo_alteracao_caucao = None
    if caucao is not None:
        renda_para_validar = (
            renda_praticada
            if renda_praticada is not None
            else mensal["renda_praticada"]
        )

        try:
            exige_confirmacao = validacoes.validar_caucao(
                caucao,
                renda_para_validar,
                config.MULTIPLICADOR_MAXIMO_CAUCAO,
            )
        except ValueError as erro:
            print(f"Erro: {erro}")
            return

        if exige_confirmacao and not confirmar(
            f"A caução ({formatar_valor(caucao)}) é nula ou superior à "
            f"renda — confirmas?"
        ):
            print("Atualização cancelada.")
            return

        motivo_alteracao_caucao = ler_texto(
            "Motivo da alteração da caução (opcional): ", obrigatorio=False
        )

    dia_vencimento = ler_inteiro(
        f"Dia de vencimento [atual: {mensal['dia_vencimento']}, "
        f"Enter mantém]: ",
        obrigatorio=False,
        minimo=1,
    )

    try:
        ocupacao, mensal = contratos.atualizar_mensal(
            dados,
            ocupacao_id,
            renda_praticada=renda_praticada,
            caucao=caucao,
            motivo_alteracao_renda=motivo_alteracao_renda,
            motivo_alteracao_caucao=motivo_alteracao_caucao,
            dia_vencimento=dia_vencimento,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Contrato atualizado: {ocupacao['id']}")


def _atualizar_reserva_airbnb(dados):
    """Ecrã de atualização de uma reserva Airbnb.

    'preco_calculado' e 'multa_calculada' já vêm gravados na
    reserva desde a criação (não recalcula nada) — por isso, ao
    contrário do ecrã de criação, não precisa de chamar
    contratos.calcular_preco_airbnb.

    Mesma regra de desconto do ecrã de criação (decisão 18): pede
    confirmação e um responsável sempre que o novo valor fique
    abaixo do calculado.
    """
    print("\n--- Atualizar reserva Airbnb ---")

    ocupacao_id = ler_texto("ID da reserva: ")
    ocupacao = contratos.procurar(dados, ocupacao_id)

    if ocupacao is None:
        print(f"Erro: A ocupação {ocupacao_id} não existe.")
        return

    if ocupacao["tipo"] != "airbnb":
        print(f"Erro: A ocupação {ocupacao_id} não é uma reserva Airbnb.")
        return

    airbnb = _detalhes_airbnb(dados, ocupacao_id)

    if airbnb is None:
        print(
            f"Erro: Faltam os dados Airbnb da ocupação {ocupacao_id} "
            f"(inconsistência nos dados)."
        )
        return

    preco_praticado = ler_decimal(
        "Preço praticado [atual: "
        f"{formatar_valor(airbnb['preco_praticado'])}, Enter mantém]: ",
        obrigatorio=False,
    )

    responsavel_desconto_preco_id = ""
    if preco_praticado is not None:
        if preco_praticado < airbnb["preco_calculado"]:
            if not confirmar(
                f"O preço praticado ({formatar_valor(preco_praticado)}) "
                f"é inferior ao calculado "
                f"({formatar_valor(airbnb['preco_calculado'])}) — "
                f"confirmas o desconto?"
            ):
                print("Atualização cancelada.")
                return

            responsavel_desconto_preco_id = ler_texto(
                "ID do responsável que autoriza este desconto: "
            )

    multa_praticada = None
    responsavel_desconto_multa_id = ""

    if airbnb["check_in_tardio"]:
        multa_praticada = ler_decimal(
            "Multa praticada [atual: "
            f"{formatar_valor(airbnb['multa_praticada'])}, "
            f"Enter mantém]: ",
            obrigatorio=False,
            minimo=Decimal("0"),
        )

        if (
            multa_praticada is not None
            and multa_praticada < airbnb["multa_calculada"]
        ):
            if not confirmar(
                f"A multa praticada ({formatar_valor(multa_praticada)}) "
                f"é inferior à calculada "
                f"({formatar_valor(airbnb['multa_calculada'])}) — "
                f"confirmas o perdão?"
            ):
                print("Atualização cancelada.")
                return

            responsavel_desconto_multa_id = ler_texto(
                "ID do responsável que autoriza este perdão: "
            )
    else:
        print(
            "(Esta reserva não teve check-in tardio — sem multa a "
            "alterar.)"
        )

    try:
        ocupacao, airbnb = contratos.atualizar_airbnb(
            dados,
            ocupacao_id,
            preco_praticado=preco_praticado,
            responsavel_desconto_preco_id=responsavel_desconto_preco_id,
            multa_praticada=multa_praticada,
            responsavel_desconto_multa_id=responsavel_desconto_multa_id,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Reserva atualizada: {ocupacao['id']}")


def _encerrar_contrato_mensal(dados):
    print("\n--- Encerrar contrato mensal ---")

    ocupacao_id = ler_texto("ID do contrato: ")
    data_fim = ler_data("Data de fim: ")
    motivo = ler_texto("Motivo (opcional): ", obrigatorio=False)

    try:
        ocupacao, mensal = contratos.encerrar_mensal(
            dados, ocupacao_id, data_fim, motivo=motivo
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    avisos = []
    if mensal["duracao_abaixo_minima"]:
        avisos.append("duração abaixo do mínimo")
    if mensal["aviso_previo_insuficiente"]:
        avisos.append("aviso prévio insuficiente")

    texto_avisos = f" [{', '.join(avisos)}]" if avisos else ""

    print(f"Contrato encerrado: {ocupacao['id']}{texto_avisos}")


def _cancelar_reserva_airbnb(dados):
    print("\n--- Cancelar reserva Airbnb ---")

    ocupacao_id = ler_texto("ID da reserva: ")
    motivo = ler_texto("Motivo (opcional): ", obrigatorio=False)

    try:
        ocupacao, airbnb = contratos.cancelar_airbnb(
            dados, ocupacao_id, motivo=motivo
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Reserva cancelada: {ocupacao['id']}")


def _reativar_ocupacao(dados):
    print("\n--- Reativar ocupação ---")

    ocupacao_id = ler_texto("ID da ocupação: ")

    try:
        ocupacao = contratos.reativar(dados, ocupacao_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Ocupação reativada: {ocupacao['id']}")


def menu_contratos(dados):
    """Submenu de gestão de contratos mensais e reservas Airbnb.

    Chamada por menu_principal. Junta as ações dos dois regimes num
    só menu, em vez de separar em dois submenus — decisão 5: os
    dois regimes partilham a base comum ('ocupacoes') e a mesma
    listagem e reativação, só divergem em criar/atualizar/encerrar
    ou cancelar.
    """

    acoes = (
        _criar_contrato_mensal,
        _criar_reserva_airbnb,
        _listar_ocupacoes,
        _atualizar_contrato_mensal,
        _atualizar_reserva_airbnb,
        _encerrar_contrato_mensal,
        _cancelar_reserva_airbnb,
        _reativar_ocupacao,
    )

    rotulos = [
        "Criar contrato mensal",
        "Registar reserva Airbnb",
        "Listar",
        "Atualizar contrato mensal",
        "Atualizar reserva Airbnb",
        "Encerrar contrato mensal",
        "Cancelar reserva Airbnb",
        "Reativar",
    ]

    while True:
        escolha = mostrar_menu(
            "Gestão de Contratos e Reservas", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)

def _criar_produto(dados):
    print("\n--- Novo produto ---")

    nome = ler_texto("Nome: ")
    unidade_medida = ler_texto(
        "Unidade de medida (ex: un, kg, L, cx, par): "
    )
    stock_minimo = ler_inteiro(
        "Stock mínimo [Enter para 0]: ", obrigatorio=False, minimo=0
    )

    if stock_minimo is None:
        stock_minimo = 0

    try:
        produto = estoque.criar_produto(
            dados, nome, unidade_medida, stock_minimo=stock_minimo
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Produto criado: {produto['id']} — {produto['nome']}")


def _listar_produtos(dados):
    """Mostra o saldo de cada produto e assinala quando está abaixo
    do stock mínimo — dá uso real ao 'stock_minimo' que
    estoque.criar_produto já guarda como limiar de alerta.
    """
    incluir_inativos = confirmar("Incluir produtos inativos?")

    lista = estoque.listar_produtos(dados, incluir_inativos=incluir_inativos)

    if not lista:
        print("\nNenhum produto encontrado.")
        return

    print(f"\n--- Produtos ({len(lista)}) ---")

    for p in lista:
        estado = "ativo" if p["ativo"] else "inativo"
        saldo = estoque.saldo_produto(dados, p["id"])
        alerta = " [abaixo do mínimo]" if saldo < p["stock_minimo"] else ""

        print(
            f"{p['id']} — {p['nome']} ({p['unidade_medida']}, "
            f"{estado}){alerta}"
        )
        print(f"    saldo: {saldo}  mínimo: {p['stock_minimo']}")


def _atualizar_produto(dados):
    print("\n--- Atualizar produto ---")

    produto_id = ler_texto("ID do produto: ")
    produto = estoque.procurar_produto(dados, produto_id)

    if produto is None:
        print(f"Erro: O produto {produto_id} não existe.")
        return

    nome = ler_atualizacao("Nome", produto["nome"])
    unidade_medida = ler_atualizacao(
        "Unidade de medida (ex: un, kg, L, cx, par)", 
        produto["unidade_medida"]
    )
    stock_minimo = ler_inteiro(
        f"Stock mínimo [atual: {produto['stock_minimo']}, "
        f"Enter mantém]: ",
        obrigatorio=False,
        minimo=0,
    )

    try:
        produto = estoque.atualizar_produto(
            dados,
            produto_id,
            nome=nome,
            unidade_medida=unidade_medida,
            stock_minimo=stock_minimo,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Produto atualizado: {produto['id']} — {produto['nome']}")


def _desativar_produto(dados):
    print("\n--- Desativar produto ---")

    produto_id = ler_texto("ID do produto: ")

    try:
        produto = estoque.desativar_produto(dados, produto_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Produto desativado: {produto['id']} — {produto['nome']}")


def _reativar_produto(dados):
    print("\n--- Reativar produto ---")

    produto_id = ler_texto("ID do produto: ")

    try:
        produto = estoque.reativar_produto(dados, produto_id)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Produto reativado: {produto['id']} — {produto['nome']}")


def _menu_produtos(dados):
    acoes = (
        _criar_produto,
        _listar_produtos,
        _atualizar_produto,
        _desativar_produto,
        _reativar_produto,
    )

    rotulos = ["Criar", "Listar", "Atualizar", "Desativar", "Reativar"]

    while True:
        escolha = mostrar_menu(
            "Gestão de Produtos", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)

def _registar_movimento(dados):
    """Movimentos são imutáveis (decisão 9) — não há ecrã de
    'atualizar' nem 'desativar' movimento. Uma correção é sempre um
    novo movimento de ajuste, com motivo obrigatório.
    """
    print("\n--- Registar movimento de stock ---")

    produto_id = ler_texto("ID do produto: ")
    tipo = ler_escolha("Tipo de movimento", estoque.TIPOS_MOVIMENTO)

    if tipo == "ajuste":
        quantidade = ler_inteiro("Quantidade (pode ser negativa): ")
        motivo = ler_texto("Motivo do ajuste: ")
    else:
        quantidade = ler_inteiro(f"Quantidade ({tipo}): ", minimo=1)
        motivo = ler_texto("Motivo (opcional): ", obrigatorio=False)

    data = ler_data("Data do movimento: ")
    responsavel_id = ler_texto(
        "ID do responsável (Enter se não aplicável): ", obrigatorio=False
    )

    try:
        movimento = estoque.registar_movimento(
            dados,
            produto_id,
            tipo,
            quantidade,
            data,
            responsavel_id=responsavel_id,
            motivo=motivo,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Movimento registado: {movimento['id']} "
        f"({movimento['tipo']}, {movimento['quantidade']})"
    )


def _ver_saldo_produto(dados):
    """Ecrã só de leitura — mostra o saldo atual (soma dos
    movimentos, nunca um campo guardado — decisão 9).
    """
    print("\n--- Saldo de um produto ---")

    produto_id = ler_texto("ID do produto: ")
    produto = estoque.procurar_produto(dados, produto_id)

    if produto is None:
        print(f"Erro: O produto {produto_id} não existe.")
        return

    saldo = estoque.saldo_produto(dados, produto_id)

    print(
        f"Saldo de {produto['nome']} ({produto_id}): "
        f"{saldo} {produto['unidade_medida']}"
    )


def _menu_movimentos(dados):
    acoes = (_registar_movimento, _ver_saldo_produto)
    rotulos = ["Registar movimento", "Ver saldo de um produto"]

    while True:
        escolha = mostrar_menu(
            "Movimentos de Stock", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)

def _ler_itens_requisicao(dados):
    """Lê a lista de itens (produto + quantidade pedida) de uma
    requisição, um de cada vez, até o utilizador dizer que não quer
    pedir mais nenhum produto — uma requisição pode juntar vários
    produtos numa só vez (decisão 20).

    Devolve sempre pelo menos um item: o primeiro é sempre pedido,
    só os seguintes são opcionais.
    """
    itens = []

    while True:
        produto_id = ler_texto(
            f"ID do produto (item {len(itens) + 1}): "
        )
        quantidade_pedida = ler_inteiro("Quantidade pedida: ", minimo=1)

        itens.append(
            {
                "produto_id": produto_id,
                "quantidade_pedida": quantidade_pedida,
            }
        )

        if not confirmar("Adicionar outro produto a esta requisição?"):
            break

    return itens


def _imprimir_itens_requisicao(dados, requisicao_id):
    """Mostra cada item de uma requisição, uma linha por produto —
    reutilizado por todos os ecrãs que apresentam o resultado de
    uma operação sobre a requisição (decisão 20: os itens deixaram
    de estar no cabeçalho, por isso já não aparecem sozinhos no
    print da requisição).
    """
    for item in estoque.listar_itens_requisicao(
        dados, requisicao_id=requisicao_id
    ):
        produto = estoque.procurar_produto(dados, item["produto_id"])
        nome = produto["nome"] if produto else item["produto_id"]
        print(
            f"    {nome} ({item['produto_id']}) — pedida: "
            f"{item['quantidade_pedida']}  enviada: "
            f"{item['quantidade_enviada']}"
        )


def _criar_requisicao(dados):
    print("\n--- Nova requisição ---")

    responsavel_id = ler_texto("ID do responsável: ")
    itens = _ler_itens_requisicao(dados)
    data_pedido = ler_data(
        "Data do pedido [Enter para hoje]: ", obrigatorio=False
    )

    if data_pedido is None:
        data_pedido = date.today()

    observacoes = ler_texto("Observações (opcional): ", obrigatorio=False)

    try:
        requisicao = estoque.criar_requisicao(
            dados,
            responsavel_id,
            itens,
            data_pedido,
            observacoes=observacoes,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Requisição criada: {requisicao['id']} (pendente)")
    _imprimir_itens_requisicao(dados, requisicao["id"])


def _listar_requisicoes(dados):
    estado = ler_escolha(
        "Filtrar por estado (Enter para todos)",
        (
            "pendente",
            "enviada",
            "fechada",
            "rejeitada",
        ),
        obrigatorio=False,
    )
    responsavel_id = ler_texto(
        "Filtrar por responsável (ID, Enter para todos): ",
        obrigatorio=False,
    ) or None
    produto_id = ler_texto(
        "Filtrar por produto (ID, Enter para todos): ", obrigatorio=False
    ) or None

    lista = estoque.listar_requisicoes(
        dados, estado=estado, responsavel_id=responsavel_id,
        produto_id=produto_id
    )

    if not lista:
        print("\nNenhuma requisição encontrada.")
        return

    print(f"\n--- Requisições ({len(lista)}) ---")

    for r in lista:
        print(
            f"{r['id']} — responsável {r['responsavel_id']} "
            f"({r['estado']})"
        )
        _imprimir_itens_requisicao(dados, r["id"])


def _enviar_requisicao(dados):
    """Envia a requisição toda de uma só vez — não há aprovação
    item a item (decisão 20). Por omissão envia-se cada item na
    quantidade pedida; o ajuste por item só aparece se for pedido
    explicitamente, para não obrigar quem envia a confirmar produto
    a produto no caso comum, que é enviar tudo.
    """
    print("\n--- Enviar requisição ---")

    requisicao_id = ler_texto("ID da requisição: ")
    enviado_por_id = ler_texto("ID de quem envia: ")
    data_envio = ler_data(
        "Data de envio [Enter para hoje]: ", obrigatorio=False
    )

    if data_envio is None:
        data_envio = date.today()

    itens_pedidos = estoque.listar_itens_requisicao(
        dados, requisicao_id=requisicao_id
    )

    quantidades_enviadas = None

    if itens_pedidos and confirmar(
        "Ajustar a quantidade enviada de algum item (envio parcial)?"
    ):
        quantidades_enviadas = {}

        for item in itens_pedidos:
            produto = estoque.procurar_produto(
                dados, item["produto_id"]
            )
            nome = produto["nome"] if produto else item["produto_id"]
            quantidade = ler_inteiro(
                f"Quantidade enviada de {nome} "
                f"[pedida: {item['quantidade_pedida']}, "
                f"Enter mantém]: ",
                obrigatorio=False,
                minimo=1,
            )

            if quantidade is not None:
                quantidades_enviadas[item["produto_id"]] = quantidade

    try:
        requisicao = estoque.enviar_requisicao(
            dados,
            requisicao_id,
            enviado_por_id,
            data_envio,
            quantidades_enviadas=quantidades_enviadas,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Requisição enviada: {requisicao['id']}")
    _imprimir_itens_requisicao(dados, requisicao["id"])


def _rejeitar_requisicao(dados):
    print("\n--- Rejeitar requisição ---")

    requisicao_id = ler_texto("ID da requisição: ")
    responsavel_id = ler_texto("ID de quem rejeita: ")
    motivo = ler_texto("Motivo da rejeição: ")

    try:
        requisicao = estoque.rejeitar_requisicao(
            dados, requisicao_id, responsavel_id, motivo
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Requisição rejeitada: {requisicao['id']}")


def _confirmar_rececao(dados):
    print("\n--- Confirmar receção ---")

    requisicao_id = ler_texto("ID da requisição: ")
    responsavel_id = ler_texto("ID do responsável que confirma: ")
    data_rececao = ler_data(
        "Data de receção [Enter para hoje]: ", obrigatorio=False
    )

    if data_rececao is None:
        data_rececao = date.today()

    try:
        requisicao = estoque.confirmar_rececao_requisicao(
            dados, requisicao_id, responsavel_id, data_rececao
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Receção confirmada — requisição fechada: {requisicao['id']}"
    )
    _imprimir_itens_requisicao(dados, requisicao["id"])


def _ler_itens_devolucao(dados):
    """Lê a lista de itens (produto + quantidade) de uma devolução,
    um de cada vez, até o utilizador dizer que não sobrou mais
    nenhum produto — simétrico a `_ler_itens_requisicao` (decisão
    20: uma devolução pode juntar vários produtos de uma vez).

    Devolve sempre pelo menos um item: o primeiro é sempre pedido,
    só os seguintes são opcionais.
    """
    itens = []

    while True:
        produto_id = ler_texto(
            f"ID do produto que sobrou (item {len(itens) + 1}): "
        )
        quantidade = ler_inteiro(
            "Quantidade que sobrou (não usada): ", minimo=1
        )

        itens.append(
            {"produto_id": produto_id, "quantidade": quantidade}
        )

        if not confirmar("Sobrou mais algum produto?"):
            break

    return itens


def _imprimir_itens_devolucao(dados, devolucao_id):
    """Mostra cada item de uma devolução, uma linha por produto —
    reutilizado pelos ecrãs que apresentam o resultado de uma
    operação sobre a devolução (decisão 20: os itens deixaram de
    estar no cabeçalho).
    """
    for item in estoque.listar_itens_devolucao(
        dados, devolucao_id=devolucao_id
    ):
        produto = estoque.procurar_produto(dados, item["produto_id"])
        nome = produto["nome"] if produto else item["produto_id"]
        print(f"    {nome} ({item['produto_id']}) — {item['quantidade']}")


def _reportar_devolucao(dados):
    print("\n--- Reportar sobra (devolução) ---")

    requisicao_id = ler_texto("ID da requisição (já fechada): ")
    responsavel_id = ler_texto("ID do responsável que devolve: ")
    itens = _ler_itens_devolucao(dados)
    data_reportada = ler_data(
        "Data de devolução [Enter para hoje]: ", obrigatorio=False
    )

    if data_reportada is None:
        data_reportada = date.today()

    try:
        devolucao = estoque.reportar_devolucao(
            dados,
            requisicao_id,
            responsavel_id,
            itens,
            data_reportada,
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(
        f"Devolução registada: {devolucao['id']} "
        f"(requisição {devolucao['requisicao_id']})"
    )
    _imprimir_itens_devolucao(dados, devolucao["id"])


def _fechar_devolucao(dados):
    print("\n--- Aceitar devolução ---")

    devolucao_id = ler_texto("ID da devolução: ")
    aceite_por_id = ler_texto("ID de quem aceita a devolução: ")
    data_fecho = ler_data(
        "Data de fecho [Enter para hoje]: ", obrigatorio=False
    )

    if data_fecho is None:
        data_fecho = date.today()

    try:
        devolucao = estoque.fechar_devolucao(
            dados, devolucao_id, aceite_por_id, data_fecho
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    repositorio.gravar(dados)

    print(f"Devolução aceite: {devolucao['id']}")
    _imprimir_itens_devolucao(dados, devolucao["id"])


def _enviar_rol_lavanderia(dados):
    """Envia stock a um responsável sem que ele o tenha pedido antes
    — o caso típico de reposição do rol de lavanderia (decisão 20):
    o admin decide o que enviar, sem depender de uma requisição
    prévia do responsável.

    Por baixo não é uma funcionalidade nova: encadeia
    `criar_requisicao` e `enviar_requisicao`, as mesmas duas funções
    do fluxo normal — cria a requisição já em nome de quem vai
    receber e envia-a de imediato, na mesma operação. O responsável
    só entra depois, a confirmar a receção pelo ecrã normal (decisão
    9: quem recebe é quem confirma, nunca o admin em nome dele).
    """
    print("\n--- Enviar rol de lavanderia ---")

    responsavel_id = ler_texto("ID do responsável que vai receber: ")
    enviado_por_id = ler_texto("ID de quem envia (admin): ")
    data = ler_data("Data de envio [Enter para hoje]: ", obrigatorio=False)

    if data is None:
        data = date.today()

    itens = _ler_itens_requisicao(dados)

    try:
        requisicao = estoque.criar_requisicao(
            dados,
            responsavel_id,
            itens,
            data,
            observacoes=(
                "Enviado sem requisição prévia (rol de lavanderia)."
            ),
        )
    except ValueError as erro:
        print(f"Erro: {erro}")
        return

    try:
        requisicao = estoque.enviar_requisicao(
            dados, requisicao["id"], enviado_por_id, data
        )
    except ValueError as erro:
        repositorio.gravar(dados)
        print(
            f"Requisição {requisicao['id']} criada, mas não foi "
            f"possível enviar: {erro}"
        )
        print(
            "Fica pendente — usa 'Enviar requisição' no menu para "
            "tentar de novo."
        )
        return

    repositorio.gravar(dados)

    print(
        f"Rol enviado: {requisicao['id']} "
        f"(estado: {requisicao['estado']})"
    )
    _imprimir_itens_requisicao(dados, requisicao["id"])


def _menu_requisicoes(dados):
    acoes = (
        _criar_requisicao,
        _listar_requisicoes,
        _enviar_requisicao,
        _rejeitar_requisicao,
        _confirmar_rececao,
        _reportar_devolucao,
        _fechar_devolucao,
        _enviar_rol_lavanderia,
    )

    rotulos = [
        "Criar requisição",
        "Listar requisições",
        "Enviar requisição",
        "Rejeitar requisição",
        "Confirmar receção",
        "Reportar sobra (devolução)",
        "Aceitar devolução",
        "Enviar rol de lavanderia",
    ]

    while True:
        escolha = mostrar_menu(
            "Requisições de Material", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)


def menu_estoque(dados):
    """Submenu de gestão de stock — chamada por menu_principal.

    Três entidades paralelas (Produto, Movimento, Requisição, não
    aninhadas como unidade→quarto→lugar), por isso o primeiro nível
    escolhe o grupo em vez de já pedir um ID.
    """
    acoes = (_menu_produtos, _menu_movimentos, _menu_requisicoes)
    rotulos = ["Produtos", "Movimentos", "Requisições"]

    while True:
        escolha = mostrar_menu(
            "Gestão de Stock", rotulos, texto_saida="Voltar"
        )

        if escolha is None:
            return

        acoes[escolha](dados)

def menu_principal(dados):
    """Menu principal — ponto de entrada do cli.py, chamado por
    main.py depois de repositorio.carregar() e da cópia de
    segurança diária.

    Amarra os seis submenus de módulo através de mostrar_menu, com
    texto_saida="Sair" — é o único menu onde "sair" significa
    terminar o programa; em todos os submenus, o mesmo mecanismo
    (0, mostrar_menu) significa "voltar a este menu", não sair do
    cli.py.

    Não grava nada diretamente: cada ecrã já grava a seguir à sua
    própria operação (decisão tomada nesta sessão — logo após cada
    sucesso). main.py só precisa de chamar isto uma vez, depois de
    carregar os dados.
    """
    acoes = (
        menu_propriedades,
        menu_unidades,
        menu_clientes,
        menu_responsaveis,
        menu_contratos,
        menu_estoque,
    )

    rotulos = [
        "Propriedades",
        "Unidades",
        "Clientes",
        "Responsáveis",
        "Contratos e Reservas",
        "Stock",
    ]

    while True:
        escolha = mostrar_menu(
            "Hostel Cleaning — Menu Principal", rotulos, texto_saida="Sair"
        )

        if escolha is None:
            print("\nAté à próxima.")
            return

        acoes[escolha](dados)