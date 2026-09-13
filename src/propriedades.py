"""Gestão das propriedades — os edifícios que agrupam unidades.

Existe como entidade própria (decisão 12) para o nome e a morada
viverem num único sítio: repetidos em cada unidade, uma correção
obrigaria a alterar treze registos e um ficaria por corrigir.

MIGRADO para MySQL (Fase 2, pivot): já não recebe nem devolve a
estrutura `dados` em memória — fala diretamente com o `repositorio`,
que faz o INSERT/SELECT/UPDATE na base de dados. Continua a não
aceder a ficheiros nem à base de dados diretamente (só através do
repositorio), e continua a sinalizar erro com `raise ValueError`.

ALTERAÇÕES 13/09/2026 (IBAN da propriedade, para a impressão do
contrato mensal):

- `criar` passa a aceitar `iban=""` — opcional, como o `morada`
  (a propriedade pode não ter IBAN conhecido no momento do
  cadastro). O valor é guardado cru, sem espaços (formato
  canónico), e a interface é que formata na apresentação.
- `atualizar` passa a aceitar `iban=None`. Um None significa não
  alterar; uma string vazia significa apagar o conteúdo (mesma
  convenção do `morada`).
- A validação do formato do IBAN (módulo 97) NÃO vive aqui — vive
  em `validacoes.py`, tal como o NIF e as datas. Este módulo só
  guarda o que lhe chega.
"""

from datetime import date

import repositorio
import responsaveis

# prefixo antes da numeração da propriedade
PREFIXO = "PRO"


def criar(nome, morada="", iban=""):
    """Cria uma propriedade e grava-a imediatamente na base de dados.

    Devolve o registo criado. Ao contrário da versão antiga (em
    memória), aqui já não há gravação separada: cada função grava a
    sua própria operação assim que a validação passa.

    'iban' é opcional (por omissão, ""), mesma convenção do 'morada'
    — uma propriedade pode não ter IBAN conhecido no momento do
    cadastro. O valor é guardado cru, sem espaços, porque é o
    formato canónico que o módulo de negócio aceita; a formatação
    com espaços de 4 em 4 fica para quem apresenta (a GUI, o PDF do
    contrato).
    """
    nome = nome.strip()

    if not nome:
        raise ValueError("O nome da propriedade é obrigatório.")

    propriedade = {
        "id": repositorio.proximo_id(PREFIXO),
        "nome": nome,
        "morada": morada.strip(),
        "iban": iban.strip(),
        "ativo": True,
    }

    repositorio.inserir_propriedade(propriedade)
    return propriedade


def procurar(propriedade_id):
    """Devolve a propriedade com o identificador indicado, ou None.

    A ausência não é erro: quem chama é que decide se a falta de
    resultado impede a operação.

    Não filtra inativas — procura, não decide.
    """
    return repositorio.procurar_propriedade(propriedade_id)


def listar(incluir_inativas=False):
    """Devolve as propriedades ativas, ou todas se pedido."""
    return repositorio.listar_propriedades(incluir_inativas=incluir_inativas)


def atualizar(propriedade_id, nome=None, morada=None, iban=None):
    """Altera o nome, a morada ou o IBAN de uma propriedade existente.

    Um parâmetro a None significa não alterar; uma cadeia vazia
    significa apagar o conteúdo. A morada e o IBAN podem ficar
    vazios, o nome não.

    O IBAN é guardado cru, sem espaços — mesma convenção do 'criar'.
    Um utilizador que escreva "PT50 0002 0123 1234 5678 9015 4" com
    espaços deve ter isso limpo antes de chegar aqui (é trabalho da
    GUI, que já trata da formatação na apresentação — o módulo de
    negócio só aceita o formato canónico).
    """
    propriedade = procurar(propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    campos = {}

    if nome is not None:
        nome = nome.strip()
        if not nome:
            raise ValueError("O nome da propriedade é obrigatório.")
        campos["nome"] = nome

    if morada is not None:
        campos["morada"] = morada.strip()

    if iban is not None:
        campos["iban"] = iban.strip()

    if campos:
        repositorio.atualizar_propriedade(propriedade_id, campos)
        propriedade.update(campos)

    return propriedade


def desativar(propriedade_id, forcar=False, responsavel_id=None):
    """Marca a propriedade como inativa, sem a eliminar.

    Uma propriedade com unidades associadas não pode desaparecer: os
    contratos históricos referem essas unidades (decisão 8). Desativar
    mantém o registo e tira-o das listagens de escolha.

    Recusa por omissão se existirem unidades ativas dependentes
    (decisão de 27/08, item 9) — passa forcar=True para desativar
    mesmo assim, conscientemente. A verificação vive aqui, não só no
    cli.py, para que qualquer interface futura (a GUI da Fase 2, por
    exemplo) herde esta proteção sem ter de a repetir.

    Forçar com dependências ativas exige `responsavel_id` (decisão do
    aluno, 06/09/2026, ao testar a desativação forçada na GUI): quem
    contorna o aviso fica registado em `desativado_por_id`/
    `data_desativacao`, validado por
    `responsaveis.validar_autoria` (mesma autorização já usada nos
    movimentos de stock e na anonimização de clientes). Sem
    dependências ativas, forcar=True não tem efeito nenhum além de
    ignorar uma verificação que já ia passar — não exige responsável
    nem grava nada nesses dois campos.
    """
    propriedade = procurar(propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    if not propriedade["ativo"]:
        raise ValueError(f"A propriedade {propriedade_id} já está inativa.")

    total_ativas = repositorio.contar_unidades_ativas(propriedade_id)
    campos: dict = {"ativo": False}

    if total_ativas:
        if not forcar:
            raise ValueError(
                f"A propriedade {propriedade_id} tem "
                f"{total_ativas} unidade(s) ativa(s) — "
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

    repositorio.atualizar_propriedade(propriedade_id, campos)
    propriedade.update(campos)
    return propriedade


def reativar(propriedade_id):
    """Repõe uma propriedade desativada como ativa.

    Existe porque a desativação por engano seria irreversível sem ela.
    É a inversa exata da `desativar` — inclui limpar
    `desativado_por_id`/`data_desativacao`, quando a desativação
    tinha sido forçada, para não deixar rasto de uma desativação que
    já não está em vigor.
    """
    propriedade = procurar(propriedade_id)

    if propriedade is None:
        raise ValueError(f"A propriedade {propriedade_id} não existe.")

    if propriedade["ativo"]:
        raise ValueError(f"A propriedade {propriedade_id} já está ativa.")

    campos = {
        "ativo": True,
        "desativado_por_id": None,
        "data_desativacao": None,
    }
    repositorio.atualizar_propriedade(propriedade_id, campos)
    propriedade.update(campos)
    return propriedade