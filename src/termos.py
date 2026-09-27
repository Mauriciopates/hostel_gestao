"""Textos legais e registo de avisos de privacidade.

Módulo de negócio criado na v1.6.0. Responde a duas perguntas, e
só a essas:

  1. Qual é o texto em vigor deste documento, e o que é que este
     titular já recebeu/aceitou?
  2. Registar que o recebeu/aceitou agora.

DUAS NATUREZAS, UMA TABELA
--------------------------
A `avisos_privacidade` guarda coisas juridicamente diferentes,
distinguidas pelo `documento`:

  - `privacidade_hospede` / `privacidade_colaborador` —
    INFORMAÇÃO prestada ao abrigo do artigo 13.º do RGPD. O
    titular não consente nem assina: é informado. Nunca bloqueia
    nada. O fundamento do tratamento é a execução do contrato e a
    obrigação legal (Lei 23/2007), não o consentimento.

  - `confidencialidade` — COMPROMISSO do colaborador. É uma
    condição de acesso ao sistema, e por isso pode bloquear sem
    problema legal.

É por isso que a função de escrita se chama `registar` e não
`aceitar`: só num dos casos há aceitação. Dar-lhe o nome "aceitar"
trazia de volta exatamente a confusão que corrigimos no ficheiro
07 do projeto.

CAMADAS
-------
Não toca na base de dados: tudo passa pelo `repositorio`. Não
imprime nem lê do teclado. Erros de utilização saem como
`ValueError`, para a GUI apanhar no `try/except` habitual.
"""

import datetime
import logging

import repositorio

logger = logging.getLogger(__name__)


# --- tipos de documento -----------------------------------------------

CONFIDENCIALIDADE = "confidencialidade"
PRIVACIDADE_HOSPEDE = "privacidade_hospede"
PRIVACIDADE_COLABORADOR = "privacidade_colaborador"

TIPOS = (
    CONFIDENCIALIDADE,
    PRIVACIDADE_HOSPEDE,
    PRIVACIDADE_COLABORADOR,
)

# --- titulares --------------------------------------------------------

TITULAR_CLIENTE = "cliente"
TITULAR_RESPONSAVEL = "responsavel"

TITULARES = (TITULAR_CLIENTE, TITULAR_RESPONSAVEL)

# --- por onde foi prestado --------------------------------------------

SUPORTES = ("papel", "contrato", "web", "sistema")

# --- o que impede a utilização ----------------------------------------
# Só o compromisso do colaborador é condição de acesso. A informação
# de privacidade informa; nunca trava ninguém.

DOCUMENTOS_QUE_BLOQUEIAM = (CONFIDENCIALIDADE,)


def bloqueia(tipo):
    """True se este documento for condição de acesso ao sistema."""
    return tipo in DOCUMENTOS_QUE_BLOQUEIAM


def _validar(titular_tipo, titular_id, tipo):
    """Valida os três identificadores contra os ENUM da tabela.

    Vale a pena falhar aqui em vez de deixar o MySQL recusar:
    a mensagem fica em português e a GUI já a sabe mostrar.
    """
    if tipo not in TIPOS:
        raise ValueError(f"Documento desconhecido: {tipo}")

    if titular_tipo not in TITULARES:
        raise ValueError(f"Tipo de titular desconhecido: {titular_tipo}")

    if not titular_id:
        raise ValueError("O titular é obrigatório.")


def texto_em_vigor(tipo):
    """Devolve o texto em vigor desse documento.

    Levanta `ValueError` se não houver nenhum. Isso é erro de
    configuração do sistema, não um caso normal a tratar com um
    `if` em cada ecrã.
    """
    if tipo not in TIPOS:
        raise ValueError(f"Documento desconhecido: {tipo}")

    texto = repositorio.obter_texto_em_vigor(tipo)

    if texto is None:
        logger.error(
            "Nenhuma versão em vigor do documento '%s' — erro de "
            "configuração",
            tipo,
        )
        raise ValueError(
            f"Não há nenhuma versão em vigor do documento "
            f"'{tipo}'. Publique uma versão antes de a usar."
        )

    return texto


def verificar(titular_tipo, titular_id, tipo):
    """Devolve tudo o que um ecrã precisa de saber, numa chamada.

    Dicionário com:

      texto           - o registo completo da versão em vigor
                        (id, tipo, versao, texto, publicado_em)
      versao_aceite   - a última versão registada a este titular,
                        ou None se nunca houve nenhuma
      data_aceite     - a data dessa última, ou None
      precisa_aceitar - True quando o documento bloqueia E a
                        versão registada é diferente da que está
                        em vigor

    Quem nunca aceitou entra no `precisa_aceitar` pela mesma
    comparação (None != "1.0"), sem precisar de ramo próprio.
    """
    _validar(titular_tipo, titular_id, tipo)

    texto = texto_em_vigor(tipo)
    ultimo = repositorio.obter_ultimo_aviso(titular_tipo, titular_id, tipo)

    versao_aceite = ultimo["versao_texto"] if ultimo else None
    data_aceite = ultimo["data_entrega"] if ultimo else None

    return {
        "texto": texto,
        "versao_aceite": versao_aceite,
        "data_aceite": data_aceite,
        "precisa_aceitar": (
            bloqueia(tipo) and versao_aceite != texto["versao"]
        ),
    }


def registar(
    titular_tipo,
    titular_id,
    tipo,
    registado_por_id=None,
    suporte="sistema",
):
    """Regista que este titular recebeu/aceitou o documento.

    Devolve a versão que ficou registada.

    A VERSÃO NÃO É PARÂMETRO, e é a decisão mais importante deste
    módulo. A função vai ela própria buscar a versão em vigor no
    momento de gravar. Se viesse do ecrã, bastava o ecrã estar
    aberto desde ontem e ter sido publicada uma versão nova
    entretanto: a pessoa carregava em "Aceitar" e ficava
    registada a aceitar uma versão que já não estava em vigor. O
    registo passava a dizer uma coisa falsa, sem erro nenhum.
    Quem grava a prova tem de ler o estado atual.

    Se já existir registo desta mesma versão, devolve-a sem
    inserir segunda linha — é o que protege do duplo clique sem
    sujar o histórico.
    """
    _validar(titular_tipo, titular_id, tipo)

    if suporte not in SUPORTES:
        raise ValueError(f"Suporte desconhecido: {suporte}")

    texto = texto_em_vigor(tipo)
    versao = texto["versao"]

    ultimo = repositorio.obter_ultimo_aviso(titular_tipo, titular_id, tipo)

    if ultimo is not None and ultimo["versao_texto"] == versao:
        return versao

    repositorio.registar_aviso(
        titular_tipo,
        titular_id,
        tipo,
        versao,
        registado_por_id or None,
        suporte,
    )

    return versao


def historico(titular_tipo, titular_id):
    """Tudo o que já foi entregue a este titular, do mais recente
    para o mais antigo. Para o dia em que alguém perguntar.
    """
    if titular_tipo not in TITULARES:
        raise ValueError(f"Tipo de titular desconhecido: {titular_tipo}")

    if not titular_id:
        raise ValueError("O titular é obrigatório.")

    return repositorio.listar_avisos(titular_tipo, titular_id)


# --- publicação e estado (v1.6.0) -------------------------------------
#
# O nome de cada documento vive aqui e não no ecrã: é o mesmo que
# aparece nas Configurações, no cabeçalho do quadro de aceitação e,
# mais tarde, no documento impresso. Três cópias da mesma frase em
# sítios diferentes acabam sempre com uma delas desatualizada.

ROTULOS = {
    CONFIDENCIALIDADE: "Termo de confidencialidade e uso do sistema",
    PRIVACIDADE_HOSPEDE: "Informação de privacidade — hóspedes",
    PRIVACIDADE_COLABORADOR: ("Informação de privacidade — colaboradores"),
}

_MAX_VERSAO = 20


def rotulo(tipo):
    """O nome por extenso de um documento."""
    if tipo not in TIPOS:
        raise ValueError(f"Documento desconhecido: {tipo}")

    return ROTULOS[tipo]


def publicar(tipo, versao, texto, autor, publicado_em=None):
    """Publica uma versão nova. Devolve a versão publicada.

    Valida antes de escrever, para a mensagem sair em português em
    vez de um erro do MySQL:

      - o autor tem de ser Master
      - o documento tem de ser um dos três
      - a versão não pode ir vazia nem passar dos 20 caracteres
      - o texto não pode ir vazio
      - a versão não pode já existir nesse documento

    Essa última é a que mais interessa: a tabela tem `UNIQUE (tipo,
    versao)` e recusava na mesma, mas com um erro de driver que não
    diz nada a quem está à frente do ecrã. Aqui diz.

    A permissão é validada AQUI e não só no ecrã, pela mesma
    disciplina do `configuracoes._validar_permissao`: a barreira
    real vive na camada de negócio. Publicar um documento legal é
    pelo menos tão sério como mudar uma chave `sistema.*`, e essas
    já são só de Master.

    NÃO existe função para editar nem para apagar uma versão, e a
    ausência é a funcionalidade: é o que garante que o texto que
    alguém aceitou continua a poder ser mostrado tal como estava.
    """
    if autor is None:
        raise ValueError(
            "Não há responsável ativo. Entre novamente no sistema."
        )

    if autor.get("tipo_utilizador") != "Master":
        logger.warning(
            "Publicação de texto legal recusada — autor_id=%s, "
            "tipo_utilizador=%s, documento=%s",
            autor.get("id"),
            autor.get("tipo_utilizador"),
            tipo,
        )
        raise ValueError(
            "Só um Master pode publicar uma versão de um documento " "legal."
        )

    if tipo not in TIPOS:
        raise ValueError(f"Documento desconhecido: {tipo}")

    versao = (versao or "").strip()
    texto = (texto or "").strip()

    if not versao:
        raise ValueError("A versão é obrigatória.")

    if len(versao) > _MAX_VERSAO:
        raise ValueError(
            f"A versão não pode ter mais de {_MAX_VERSAO} caracteres."
        )

    if not texto:
        raise ValueError("O texto do documento é obrigatório.")

    if repositorio.obter_texto(tipo, versao) is not None:
        raise ValueError(
            f"Já existe a versão {versao} deste documento. "
            "As versões não se reescrevem — use um número novo."
        )

    if publicado_em is None:
        publicado_em = datetime.date.today()

    repositorio.publicar_texto(tipo, versao, texto, publicado_em)

    logger.info(
        "Publicação de texto legal — tipo=%s, versao=%s, autor_id=%s",
        tipo,
        versao,
        autor.get("id"),
    )

    return versao


def estado_documentos():
    """Uma linha por documento, para o ecrã de Configurações.

    Cada dicionário traz:

      tipo        - a chave interna
      rotulo      - o nome por extenso
      texto       - o registo da versão em vigor, ou None se ainda
                    não houver nenhuma publicada
      aceitacoes  - quantas pessoas já registaram essa versão (0
                    quando não há versão)
      bloqueia    - se o documento é condição de acesso

    O total contra o qual comparar as `aceitacoes` — quantos
    colaboradores existem — não vem daqui de propósito. Esse número
    é de `responsaveis`, e não vale a pena este módulo passar a
    saber quem são as pessoas só para preencher um rodapé.
    """
    return [_estado_documento(tipo) for tipo in TIPOS]


def _estado_documento(tipo):
    texto = repositorio.obter_texto_em_vigor(tipo)

    if texto is None:
        return {
            "tipo": tipo,
            "rotulo": ROTULOS[tipo],
            "texto": None,
            "aceitacoes": 0,
            "bloqueia": bloqueia(tipo),
        }

    return {
        "tipo": tipo,
        "rotulo": ROTULOS[tipo],
        "texto": texto,
        "aceitacoes": repositorio.contar_avisos_por_versao(
            tipo, texto["versao"]
        ),
        "bloqueia": bloqueia(tipo),
    }


def historico_documento(tipo):
    """Todas as versões de um documento, da mais recente para trás."""
    if tipo not in TIPOS:
        raise ValueError(f"Documento desconhecido: {tipo}")

    return repositorio.listar_textos(tipo)
