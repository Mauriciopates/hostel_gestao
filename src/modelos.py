"""Estruturas de dados do sistema.

Classes de dados sem lógica de negócio: guardam os campos, não decidem nada.
As regras vivem nos módulos correspondentes (`unidades.py`, `clientes.py`,
`contratos.py`), o que mantém a separação de camadas da decisão 7.

Montantes em Decimal e datas em `date` (decisão 4). A conversão de e para
texto ISO é responsabilidade do `repositorio.py`.

ALTERAÇÕES 13/09/2026 (fluxo de Stock com Aprovação de Requisições):

- `Requisicao` ganha dois campos novos — `observacao_rececao` e
  `origem` — e um estado novo, `cancelada`, a acrescentar aos quatro
  que já existiam (pendente/enviada/fechada/rejeitada). Os dois
  campos vieram de duas decisões do fluxo de Stock, tomadas na
  mesma ronda:

  * `observacao_rececao` — texto livre que o responsável que pediu
    escreve ao confirmar a receção, para informar faltas. Não mexe
    no stock (decisão de 13/09/2026: "o Maurício só informa a falta
    em observação, o Tiago é que decide se corrige o stock"). Fica
    gravado na própria requisição.

  * `origem` — distingue requisições normais ('pedido') das criadas
    por Rol de Lavanderia ('rol'). O Rol cria e envia numa só
    operação (não passa por Aprovação, porque o admin é quem decide
    e quem envia — não há nada a aprovar), mas precisa de se
    distinguir na lista, senão o responsável vê uma requisição que
    não pediu, sem explicação.

  * `cancelada` — estado novo, no mesmo espírito de `rejeitada`, mas
    com autor diferente: `rejeitada` é o admin a recusar uma
    pendente; `cancelada` é o próprio autor a desistir de uma
    pendente (antes de o admin a ver). Só existe enquanto a
    requisição está pendente — uma vez enviada, já saiu stock, e a
    correção faz-se com movimento de ajuste, não com cancelamento.

ALTERAÇÕES 16/09/2026 (v1.4.0 — Fases 2 e 3 do plano de correções):

- `Responsavel` ganha `tipo_utilizador` ('Master'/'Admin'/'Staff').
  O perfil ficou como coluna do próprio responsável, e não numa
  tabela `utilizadores` à parte: `responsaveis` já era o alvo de
  todas as chaves estrangeiras de autoria do sistema, e separar o
  perfil obrigava a uma junção em cada leitura de sessão sem
  acrescentar nenhum campo próprio. Continua sem credenciais —
  palavra-passe e login chegam com `utilizadores.py` (v1.5.0).

- `Lugar` ganha `posicao_beliche` e `beliche_grupo_id`. Um beliche
  continua a ser dois lugares de capacidade 1 (decisão 17): estes
  dois campos apenas dizem qual é a cama de cima e qual a de baixo,
  e quais duas camas formam a mesma estrutura. Só os lugares com
  `tipo_cama='beliche'` os preenchem; nos outros ficam a "".

- `Unidade` ganha `permite_cama_extra`, `qtd_cama_extra` e
  `tipo_cama_extra`. Só fazem sentido em unidades de tipo 'airbnb' —
  a regra vive em `unidades._validar_cama_extra`, não aqui nem na
  base de dados (um CHECK teria de ler a coluna `tipo` da mesma
  linha).

- `Cliente` ganha `pais_emissor_documento` e `pais_residencia`, os
  dois campos que o boletim de alojamento exige e que só o regime
  Airbnb preenche. O significado de `incompleto` mudou: ver a
  docstring da classe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# bool é um tipo com apenas dois valores possíveis: True ou False.
# Sim ou não. Ligado ou desligado. Não há meio-termo.
# Todas as classes do modelos.py são do mesmo tipo: guardam campos,
# não decidem nada. É por isso do uso de dataclass


@dataclass
class Propriedade:
    """Edificio ou fração que agrupa unidades de alojamento."""

    id: str
    nome: str
    morada: str = ""
    ativo: bool = True


@dataclass
class Unidade:
    """Alojamento contratável. Pertence a uma propriedade.
    O tipo é restrição rígida: mensal não aceita reserva Airbnb e vice-versa.
    Livre, ocupado e Reservado não são guardados - calculam-se a partir dos
    contratos para uma data(decisão 3). Só 'em_manutencao' persiste,
    pois é uma decisão da gestão da unidade.

    Os três campos de cama extra (v1.4.0) descrevem a cama
    suplementar que a unidade aceita receber: se permite, quantas e
    de que tipo. Só fazem sentido em unidades de tipo "airbnb" e só
    são validados quando 'permite_cama_extra' é True — a regra está
    em `unidades._validar_cama_extra`, não aqui. 'qtd_cama_extra'
    fica None quando não há cama extra: um "0" seria um número a
    fingir que existe, e quando existe é sempre positivo.
    """

    id: str
    propriedade_id: str
    nome: str
    tipo: str  # "mensal" ou "airbnb"
    preco_base: Decimal
    preco_epoca_alta: Decimal
    multa_check_in_tardio: Decimal
    epoca_alta_ativa: bool = False
    em_manutencao: bool = False
    permite_cama_extra: bool = False
    qtd_cama_extra: int | None = None
    tipo_cama_extra: str = ""
    ativo: bool = True


@dataclass
class Quarto:
    """Divisão de uma unidade que agrupa lugares.
    Os dois indicadores são independentes: 'privativo'
    restringe quem ocupar, 'limpeza_incluida' deterrmina
    se o quarto entra no calculo da roupa de cama e enviar
    (decisão 17).

    """

    id: str
    unidade_id: str
    nome: str
    privativo: bool = False
    limpeza_incluida: bool = False
    ativo: bool = True


@dataclass
class Lugar:
    """Cama ou posição contratável dentro de um quarto.

    É a unidade minima de ocupação. A capacidade é guardada aqui,
    não derivada do tipo de cama - permite configurações fora do par
    solteiro/casal. Um beliche são dois lugares de capacidade 1,
    nunca um lugar de capacidade 2 (decisão 17).

    'tipo_cama' ("solteiro"/"casal"/"beliche") só decide a aparência
    do lugar na planta de lugares (GUI) — não deriva nem substitui
    'capacidade' (decisão de 06/09/2026, ao chegar este ecrã).

    'posicao_beliche' ("superior"/"inferior") e 'beliche_grupo_id'
    (v1.4.0) só se aplicam quando 'tipo_cama' é "beliche": dizem qual
    é a cama de cima e qual a de baixo, e ligam as duas camas da
    mesma estrutura pelo mesmo identificador de grupo (BEL-001,
    BEL-002...). Nos restantes lugares ficam a "". O grupo não é uma
    entidade própria — não há tabela de beliches, porque uma
    estrutura de beliche não tem nenhum atributo além do par.
    """

    id: str
    quarto_id: str
    nome: str
    tipo_cama: str
    capacidade: int = 1
    posicao_beliche: str = ""
    beliche_grupo_id: str = ""
    ativo: bool = True


@dataclass
class Cliente:
    """Pessoa que contrata alojamento.
    Concentra os dados pessoais do sistema e é alvo da
    anonimização prevista no RGPD (decisão 8). A nacionalidade
    é conservada na anonimização por não identificar e
    ter valor estatistico.

    Nem todos os campos se aplicam aos dois regimes. Um cliente
    Mensal preenche quase tudo; um cliente Airbnb preenche só o que
    o boletim de alojamento exige — nome, nacionalidade, data de
    nascimento, tipo e número de documento, 'pais_emissor_documento'
    e 'pais_residencia' (os dois últimos acrescentados em 16/09/2026
    e usados apenas neste regime). NIF, morada, estado civil,
    validade do documento, telefone, email e contacto de emergência
    não fazem parte do regime Airbnb. Quem manda nisto é
    `validacoes.validar_cliente`, não esta classe.

    ATENÇÃO ao significado de 'incompleto' (16/09/2026): já NÃO quer
    dizer "faltam campos por preencher". Esse conceito foi
    descartado quando cada regime passou a ter o seu próprio
    formulário, que só pede o que precisa — o que é obrigatório
    bloqueia a gravação, e o resto nem chega a ser pedido. A coluna
    sobrevive com outro uso: `clientes.anonimizar` marca-a True para
    sinalizar um registo cujos dados foram apagados por RGPD. Quem
    ler este campo tem de o ler assim.
    """

    id: str
    nome: str
    tipo_documento: str
    numero_documento: str
    nif: str = ""
    email: str = ""
    telefone: str = ""
    morada: str = ""
    nacionalidade: str = ""
    estado_civil: str = ""
    data_nascimento: date | None = None
    validade_documento: date | None = None
    contacto_emergencia: str = ""
    pais_emissor_documento: str = ""
    pais_residencia: str = ""
    incompleto: bool = False
    anonimizado: bool = False
    data_anonimizado: date | None = None
    responsavel_anonimizado_id: str = ""
    ativo: bool = (
        True
        # bool = True se o cliente está ativo no sistema,
        # False se foi desativado (ex: por pedido de anonimização).
    )


@dataclass
class Responsavel:
    """Pessoa que opera o sistema.

    Antecipado para a Fase 1 sem credenciais (decisão 10): serve
    para atribuir autoria a operações — requisições de stock,
    anonimizações, alterações de configuração.

    'tipo_utilizador' (v1.4.0) é o perfil de permissões: 'Master',
    'Admin' ou 'Staff'. Decide o que cada pessoa pode fazer — enviar
    um Rol de Lavanderia, aceitar uma devolução, alterar o perfil de
    outra pessoa. A validação de quem pode alterar o quê vive na
    camada de negócio (`utilizadores.verificar_permissao`), nunca só
    na interface.

    CREDENCIAL (v1.5.0): a partir desta versão, o responsável tem
    login e palavra-passe. A credencial vive na própria linha do
    responsável — não há tabela `utilizadores` à parte (decisão da
    Fase 2, mantida). O módulo `utilizadores.py` é que a gere.

    Os seis campos novos:

      - 'username': o nome de login. NULL na base para responsáveis
        que ainda não têm credencial; no dicionário, "" (string
        vazia) — a convenção de "sem valor" usada em todo o sistema.
        UNIQUE na base: dois responsáveis não podem ter o mesmo.

      - 'password_hash': hash da password no formato modular do
        Django (`pbkdf2_sha256$<iteracoes>$<salt>$<hash>`). A
        password em texto simples nunca é guardada.

      - 'password_alterada_em': quando a password foi alterada pela
        última vez. "" enquanto nunca foi definida ou alterada.

      - 'ultimo_login': data e hora do último login bem-sucedido.
        "" enquanto o responsável nunca entrou desde que ganhou
        credencial.

      - 'desativado_por_id': quem autorizou a desativação. FK
        auto-referente. "" enquanto o responsável está ativo.

      - 'data_desativacao': quando foi desativado. "" enquanto
        ativo. Mesma convenção de `data_desativacao` em produtos,
        propriedades e unidades.

    ATENÇÃO: os três últimos campos (desativado_por_id,
    data_desativacao) seguem o mesmo padrão já usado em produtos,
    propriedades e unidades — é consistência interna, não preparação
    para a Fase 3. E os três primeiros (username, password_hash,
    password_alterada_em, ultimo_login) são o mínimo que qualquer
    login exige, mesmo antes de haver web.
    """

    id: str
    nome: str
    contacto: str = ""
    tipo_utilizador: str = "Staff"
    ativo: bool = True
    username: str = ""
    password_hash: str = ""
    password_alterada_em: str = ""
    ultimo_login: str = ""
    desativado_por_id: str = ""
    data_desativacao: str = ""


@dataclass
class OcupacaoMensal:
    """Dados especificos de um contrato de arrendamento mensal.
    Liga-se a 'Ocupacao' pelo mesmo ID. A caução é calculada a partir
    da renda praticda, não é montante fixo (decisão 14).:
    O sistema sugere uma renda, aceita até duas, recusa acima.

    Conserva 'renda_calculada' e 'renda_praticada' para que a
    diferença fique visivel - nunca se guarda um total.

    """

    ocupacao_id: str
    renda_calculada: Decimal
    renda_praticada: Decimal
    caucao: Decimal
    responsavel_desconto_renda_id: str = ""
    caucao_exige_confirmacao: bool = False
    motivo_alteracao_renda: str = ""
    motivo_alteracao_caucao: str = ""
    dia_vencimento: int = 5
    motivo_encerramento: str = ""
    duracao_abaixo_minima: bool = False
    aviso_previo_insuficiente: bool = False


@dataclass
class OcupacaoAirbnb:
    """Dados especificos de uma reserva de estadia curtam.

    Liga-se á 'Ocupacao' pelo mesmo ID. O preço é por noite, calculado
    a partir da unidade: 'preco_epoca_alta' só se aplica quando o
    indicador manual da unidade esta ativo E a data cai no periodo
    da época alta.
    A multa de check-in tardio só existe quando 'check_in_tardio'
    é True(decisão 15).

    Quando 'preco_praticado' fica abaixo de 'preco_calculado' (ou
    'multa_praticada' abaixo de 'multa_calculada'), é um desconto —
    exige um responsável que o autorize (decisão 18, por analogia
    com a decisão 8: quem assume a exceção fica identificado, não
    só descrito em texto livre). 'responsavel_desconto_preco_id' e
    'responsavel_desconto_multa_id' ficam em branco quando não há
    desconto nesse valor.
    """

    ocupacao_id: str
    preco_calculado: Decimal
    preco_praticado: Decimal
    responsavel_desconto_preco_id: str = ""
    check_in_tardio: bool = False
    hora_chegada: str = ""
    multa_calculada: Decimal = Decimal("0.00")
    multa_praticada: Decimal = Decimal("0.00")
    responsavel_desconto_multa_id: str = ""
    motivo_cancelamento: str = ""


@dataclass
class Produto:
    """Catalogo de material do armazem central.

    Definifo uma unica vez: o nome, a unidade de medida e stock minimo
    vivem aqui, não se repetem em cada movimento (decisão 9).

    Não tem campo de quantidade. O saldo é a soma de movimentos,
    nunca um valor guardado.

    """

    id: str
    nome: str
    unidade_medida: str
    stock_minimo: int = 0
    ativo: bool = True


@dataclass
class Requisicao:
    """Pedido de material do responsavel ao armazém central.

    É um cabeçalho — não carrega produto nem quantidade. Uma
    requisição pode pedir vários produtos de uma vez, cada um numa
    linha própria em 'ItemRequisicao', ligada por este ID (decisão
    20, que separou o que era um único registo em cabeçalho +
    itens, tal como 'Ocupacao' já separava dados comuns dos
    especificos de cada regime).

    Percorre cinco estados: pendente -> enviada -> fechada, com
    'rejeitada' e 'cancelada' como saídas alternativas a partir de
    pendente (decisão 9, revista na decisão 19; 'cancelada' chegou
    em 13/09/2026, ao separar a Aprovação de Requisições num ecrã
    próprio). Os estados são sempre da requisição inteira, nunca de
    um item isolado: não há aprovação nem receção item a item —
    envia-se e recebe-se a requisição toda de uma vez (decisão 20).

    pendente — o responsável registou o pedido. Nada saiu do armazém
    ainda. É aqui que o autor pode 'cancelar' (desistir antes de o
    admin ver), se se enganou em algum item — mais simples do que
    editar a requisição depois de criada.

    enviada — o admin aprovou e enviou. Gera um movimento de saída
    por item, dá baixa no saldo de cada produto. Já não se cancela:
    para corrigir, o admin faz um movimento de ajuste. É este o
    momento em que o responsável que pediu vê o que foi enviado e
    pode confirmar a receção.

    fechada — o responsável confirma que o material chegou. Esta
    confirmação é dele, não do admin: quem pede é quem sabe se
    recebeu. Pode deixar uma 'observacao_rececao' (texto livre) a
    informar faltas — não mexe no stock, é só informação para o
    admin tratar depois, no ecrã de Movimentos ou de Devoluções.

    rejeitada — saída alternativa a partir de pendente. O admin
    recusou o pedido, com motivo. Distinta de 'cancelada' pela
    autoria: 'rejeitada' é o admin a recusar; 'cancelada' é o
    autor a desistir.

    cancelada — saída alternativa a partir de pendente. O próprio
    autor desistiu do pedido antes de o admin o ver. Só existe
    enquanto pendente (nada saiu ainda; cancelar não gera nenhum
    movimento de stock).

    Sobra de material devolvida ao armazém é tratada à parte, pela
    entidade 'Devolucao' — nem toda requisição gera sobra, por isso
    deixou de ser um passo obrigatório desta.

    Uma requisição fechada ou rejeitada nunca se edita: um erro
    detetado depois corrige-se com um movimento de ajuste, não com
    uma alteração a este registo (decisão 20, por analogia com a
    imutabilidade dos movimentos da decisão 9).

    'origem' distingue as requisições pedidas pelo staff ('pedido',
    por omissão) das criadas pelo admin no fluxo de Rol de
    Lavanderia ('rol'). As duas vivem na mesma tabela e no mesmo
    fluxo a partir do momento em que são enviadas; só se distinguem
    pela origem, para o responsável perceber, na lista dele, porque
    apareceu ali uma requisição que ele não pediu.
    """

    id: str
    responsavel_id: str
    estado: str = "pendente"
    data_pedido: date | None = None
    data_envio: date | None = None
    data_fecho: date | None = None
    responsavel_rejeicao_id: str = ""
    motivo_rejeicao: str = ""
    observacoes: str = ""
    observacao_rececao: str = ""
    origem: str = "pedido"


@dataclass
class ItemRequisicao:
    """Uma linha de uma requisição: um produto e uma quantidade.

    Ligado a 'Requisicao' por 'requisicao_id'. Não tem estado
    próprio — o estado é sempre o da requisição a que pertence
    (decisão 20). Não pode haver dois itens do mesmo produto na
    mesma requisição; pedir mais desse produto é aumentar a
    quantidade do item existente, não duplicar a linha.

    'quantidade_enviada' fica a 0 até a requisição ser enviada.
    Regra geral vai ser igual a 'quantidade_pedida', mas pode ficar
    abaixo dela num envio parcial — o saldo do armazém manda no que
    é possível enviar, não o que foi pedido.
    """

    id: str
    requisicao_id: str
    produto_id: str
    quantidade_pedida: int
    quantidade_enviada: int = 0


@dataclass
class Devolucao:
    """Sobra de material devolvida ao armazém central.

    É um cabeçalho — não carrega produto nem quantidade. Associada
    a uma requisição já fechada — não é um passo dela, é um evento
    à parte que só existe quando sobra material por usar (decisão
    19). Pode juntar vários produtos devolvidos de uma vez, cada um
    numa linha própria em 'ItemDevolucao', ligada por este ID —
    simétrico à separação cabeçalho/itens da requisição (decisão
    20).

    Segue um mini-fluxo de dois estados: pendente (o responsável
    reportou a sobra) -> fechada (o admin aceitou e o material
    voltou a contar no saldo, gerando um movimento de entrada por
    item). Só depois de fechada é que as quantidades entram no
    saldo dos produtos — o mesmo princípio de dupla confirmação que
    já existia na requisição. Tal como na requisição, aceita-se ou
    fecha-se a devolução toda de uma vez, nunca item a item.

    Uma devolução fechada nunca se edita: um erro detetado depois
    corrige-se com um movimento de ajuste, não com uma alteração a
    este registo (decisão 20).
    """

    id: str
    requisicao_id: str
    responsavel_id: str
    estado: str = "pendente"
    data_reportada: date | None = None
    data_fecho: date | None = None


@dataclass
class ItemDevolucao:
    """Uma linha de uma devolução: um produto e uma quantidade.

    Ligado a 'Devolucao' por 'devolucao_id'. Não tem estado próprio
    — o estado é sempre o da devolução a que pertence (decisão 20).
    A quantidade nunca pode ser zero ou negativa: se não sobrou
    nada desse produto, não há linha nenhuma a criar para ele — o
    mesmo raciocínio que já existia na 'Devolucao' da decisão 19,
    agora aplicado a cada item.
    """

    id: str
    devolucao_id: str
    produto_id: str
    quantidade: int


@dataclass
class Movimento:
    """Entrada ou saída de material do armazém central.

    Imutável: um movimento registado nunca se altera nem se apaga. As
    correções fazem-se com movimentos de ajuste, com motivo obrigatório
    (decisão 9).

    O saldo de um produto é a soma dos seus movimentos, nunca um campo
    guardado.
    """

    id: str
    produto_id: str
    tipo: str
    quantidade: int
    data: date
    responsavel_id: str = ""
    requisicao_id: str = ""
    motivo: str = ""


@dataclass
class Configuracao:
    """Valor de configuração global, guardado como par chave/valor.

    O valor é sempre texto: a conversão para Decimal, int ou tuplo é
    responsabilidade de quem lê, conforme a chave. Carregado uma vez ao
    arranque para um dicionário em memória.

    Os valores iniciais estão em `config.py`; esta classe é o que fica
    gravado depois de alguém os alterar.
    É a única classe do modelo sem id. Uma chave de configuração é um
    identificador técnico, escolhido por quem programa,
    não um nome de negócio.
    """

    chave: str
    valor: str
    descricao: str = ""


@dataclass
class ConfiguracaoHistorico:
    """Registo imutável de uma alteração a uma configuração.

    Guarda o valor anterior e o novo, com data e responsável. Nunca se
    altera nem se apaga — corrigir um valor gera um novo registo, não a
    edição deste.

    É o que permite responder a "quando é que o preço mudou e quem o mudou".
    """

    id: str
    chave: str
    valor_anterior: str
    valor_novo: str
    data: date
    responsavel_id: str
    motivo: str = ""


@dataclass
class Ocupacao:
    """Base comum a contratos mensais e reservas Airbnb.
    ...
    """

    id: str
    unidade_id: str
    cliente_id: str
    tipo: str
    data_inicio: date
    data_fim: date | None = None
    lugar_id: str = ""
    aviso_documento: bool = False
    ativo: bool = True