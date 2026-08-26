"""Estruturas de dados do sistema.

Classes de dados sem lógica de negócio: guardam os campos, não decidem nada.
As regras vivem nos módulos correspondentes (`unidades.py`, `clientes.py`,
`contratos.py`), o que mantém a separação de camadas da decisão 7.

Montantes em Decimal e datas em `date` (decisão 4). A conversão de e para
texto ISO é responsabilidade do `repositorio.py`.
"""

from dataclasses import dataclass, field
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

    """

    id: str
    quarto_id: str
    nome: str
    capacidade: int = 1
    ativo: bool = True


@dataclass
class Cliente:
    """Pessoa que contrata alojamento.
    Concentra os dados pessoais do sistema e é alvo da 
    anonimização prevista no RGPD (decisão 8). A nacionalidade
    é conservada na anonimização por não identificar e 
    ter valor estatistico.

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
    data_nascimento: date | None = None
    validade_documento: date | None = None
    contacto_emergencia: str = ""
    incompleto: bool = False
    anonimizado: bool = False
    data_anonimizado: date | None = None
    responsavel_anonimizado_id: str = ""
    ativo: bool = (
        True  
        # bool = True se o cliente está ativo no sistema, 
        #False se foi desativado (ex: por pedido de anonimização).
    )


@dataclass
class Responsavel:
    """PEssoa que opera o sistema.

    Antecipado para a Fase 1 sem credenciais  (decisão 10): 
    serve para atribuir autoria a operações - requisições de stock,
    anonimizações, alterações de configuração. Login e permissões
    chegam na Fase 2.

    """

    id: str
    nome: str
    contacto: str = ""
    ativo: bool = True


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
    """ Catalogo de material do armazem central.
    
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

    Percorre quatro estados: pendente -> enviada -> fechada, com
    'rejeitada' como saida alternativa a partir de pendente
    (decisão 9, revista na decisão 19). Os estados são sempre da
    requisição inteira, nunca de um item isolado: não há aprovação
    nem receção item a item — envia-se e recebe-se a requisição
    toda de uma vez (decisão 20).

    pendente — o responsável registou o pedido. Nada saiu do armazém
    ainda.

    enviada — o admin aprovou e enviou. Gera um movimento de saída
    por item, dá baixa no saldo de cada produto.

    fechada — o responsável confirma que o material chegou. Esta
    confirmação é dele, não do admin: quem pede é quem sabe se
    recebeu. O fecho é automático nesse momento — não espera por
    nenhuma devolução (decisão 19).

    rejeitada — saída alternativa a partir de pendente. O admin
    recusou o pedido, com motivo.

    Sobra de material devolvida ao armazém é tratada à parte, pela
    entidade 'Devolucao' — nem toda requisição gera sobra, por isso
    deixou de ser um passo obrigatório desta.

    Uma requisição fechada ou rejeitada nunca se edita: um erro
    detetado depois corrige-se com um movimento de ajuste, não com
    uma alteração a este registo (decisão 20, por analogia com a
    imutabilidade dos movimentos da decisão 9).
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