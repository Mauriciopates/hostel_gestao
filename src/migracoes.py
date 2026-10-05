"""Sistema de migrações da base de dados (v1.8.0, decisões D1 e D3).

Cada migração é um par (nome, lista de instruções SQL). A lista
`MIGRACOES` está por ordem e só cresce: uma migração já publicada
NUNCA se altera nem se apaga — uma correção é sempre uma migração
nova, no fim da lista.

No arranque (`main_gui.py` e `main.py`), `aplicar_pendentes()`:
  1. garante a tabela `migracoes_aplicadas` (CREATE IF NOT EXISTS);
  2. lê o que já foi aplicado NESTA base (1 SELECT);
  3. corre, por ordem, só as que faltam, registando cada uma.
Assim o Localhost e a VM atualizam-se cada um no seu arranque, sem
SQL à mão.

REGRAS DE ESCRITA DE UMA MIGRAÇÃO
- Nome: 4 dígitos + "_" + descrição em minúsculas
  (ex.: "0001_categoria_compra_de_stock"), sempre crescente.
- Idempotente: CREATE ... IF NOT EXISTS, INSERT ... WHERE NOT
  EXISTS. No MySQL, CREATE/ALTER fazem commit sozinhos, por isso uma
  migração que falhe a meio tem de poder ser corrida outra vez.
- Seeds procuram pelo NOME (ou outra chave natural), nunca contam
  com um ID livre: numa base antiga o registo pode já existir.

O `configuracoes.garantir_seed()` NÃO é uma migração (decisão 3 do
passo C): já é idempotente e segue o mapa `_CHAVES`.
"""

import logging
import re

import migracoes_textos
import repositorio

logger = logging.getLogger(__name__)


# --- 0001: categoria "Compra de Stock" -------------------------------
# Obrigatória para a VIA 2 das despesas (o `despesas.py` procura-a pelo
# NOME). Só é criada se ainda não existir nenhuma categoria com esse
# nome — numa base antiga (Localhost: CAT-001) não faz nada.
# O ID não é fixo: é o seguinte ao maior CAT-NNN da tabela, pela mesma
# regra do `repositorio.proximo_id` (MAX numérico, três dígitos no
# mínimo). A tabela derivada `t` calcula tudo numa só leitura:
#   n      → próximo número livre
#   existe → quantas categorias já se chamam "Compra de Stock"
_SQL_CATEGORIA_COMPRA_DE_STOCK = (
    "INSERT INTO categorias_despesa (id, nome, ativo) "
    "SELECT CONCAT('CAT-', LPAD(t.n, GREATEST(3, CHAR_LENGTH(t.n)), '0')), "
    "'Compra de Stock', 1 "
    "FROM ("
    "SELECT COALESCE(MAX(CASE WHEN id LIKE 'CAT-%' "
    "THEN CAST(SUBSTRING(id, 5) AS UNSIGNED) END), 0) + 1 AS n, "
    "COALESCE(SUM(nome = 'Compra de Stock'), 0) AS existe "
    "FROM categorias_despesa"
    ") AS t "
    "WHERE t.existe = 0"
)


# --- 0002: textos legais de demonstração (versão 0.1) -----------------
# Sem uma versão em vigor da confidencialidade, ninguém entra numa base
# nova (`termos.bloqueia`). Publica a versão 0.1 — fictícia, ver
# `migracoes_textos.py` — de cada documento que ainda NÃO tenha
# nenhuma versão. Numa base que já tem textos (Localhost, VM) não faz
# nada: aí os textos mudam-se em Configurações → "Publicar versão nova".


def _literal_sql(texto):
    """Escreve um texto como literal SQL entre plicas.

    Só para textos fixos do código (nunca dados de utilizadores): as
    migrações correm sem parâmetros. Duplica as plicas e as barras.
    """
    return "'" + texto.replace("\\", "\\\\").replace("'", "''") + "'"


def _sql_publicar_texto_demo(tipo, texto):
    """INSERT da versão 0.1 do documento, só se não houver nenhuma."""
    return (
        "INSERT INTO textos_legais "
        "(tipo, versao, texto, publicado_em, em_vigor) "
        f"SELECT '{tipo}', '0.1', {_literal_sql(texto)}, CURDATE(), 1 "
        "FROM DUAL WHERE NOT EXISTS "
        f"(SELECT 1 FROM textos_legais WHERE tipo = '{tipo}')"
    )


# --- 0003: avisos_privacidade com chaves estrangeiras -----------------
# Antes: `titular_tipo` + `titular_id` (associação polimórfica — o id
# podia ser de `clientes` OU de `responsaveis`, por isso nenhuma FK o
# protegia). Agora: duas colunas, `cliente_id` e `responsavel_id`,
# cada uma com a sua FK, e um CHECK que obriga a preencher EXATAMENTE
# uma. O `registado_por_id` (quem registou) ganha também FK para
# `responsaveis` — continua opcional (NULL = veio do site).
#
# IDEMPOTÊNCIA: o MySQL 8.4 não tem "ADD COLUMN IF NOT EXISTS" (só o
# MariaDB). Cada passo pergunta primeiro ao `information_schema` se
# ainda é preciso e só então corre o ALTER (ver `_se`). Se a migração
# falhar a meio, voltar a corrê-la continua do ponto onde parou.


def _se(condicao, instrucao):
    """Corre `instrucao` só se `condicao` (SQL que devolve 0/1) for 1.

    O MySQL não tem IF fora de procedimentos, por isso monta-se a
    instrução numa variável e corre-se como "prepared statement"; quando
    a condição é falsa corre-se `DO 0` (não faz nada). Devolve as 4
    instruções, a juntar à lista da migração.
    """
    return [
        f"SET @sql_migracao = IF(({condicao}) = 1, "
        f"{_literal_sql(instrucao)}, 'DO 0')",
        "PREPARE passo_migracao FROM @sql_migracao",
        "EXECUTE passo_migracao",
        "DEALLOCATE PREPARE passo_migracao",
    ]


def _existe_coluna(tabela, coluna):
    return (
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() "
        f"AND table_name = '{tabela}' AND column_name = '{coluna}'"
    )


def _existe_indice(tabela, indice):
    return (
        "SELECT COUNT(*) > 0 FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() "
        f"AND table_name = '{tabela}' AND index_name = '{indice}'"
    )


def _existe_restricao(tabela, restricao):
    """FK ou CHECK com este nome (os dois estão na table_constraints)."""
    return (
        "SELECT COUNT(*) FROM information_schema.table_constraints "
        "WHERE constraint_schema = DATABASE() "
        f"AND table_name = '{tabela}' AND constraint_name = '{restricao}'"
    )


def _nao(condicao):
    return f"SELECT NOT ({condicao})"


_AVISOS = "avisos_privacidade"

_MIGRACAO_0003 = (
    # 1. As duas colunas novas, logo a seguir ao id.
    _se(_nao(_existe_coluna(_AVISOS, "cliente_id")),
        f"ALTER TABLE {_AVISOS} ADD COLUMN cliente_id VARCHAR(10) "
        "NULL AFTER id")
    + _se(_nao(_existe_coluna(_AVISOS, "responsavel_id")),
          f"ALTER TABLE {_AVISOS} ADD COLUMN responsavel_id VARCHAR(10) "
          "NULL AFTER cliente_id")
    # 2. Copiar os dados antigos (só enquanto as colunas antigas
    #    existem — numa segunda corrida já foram apagadas).
    + _se(_existe_coluna(_AVISOS, "titular_tipo"),
          f"UPDATE {_AVISOS} SET cliente_id = titular_id "
          "WHERE titular_tipo = 'cliente' AND cliente_id IS NULL")
    + _se(_existe_coluna(_AVISOS, "titular_tipo"),
          f"UPDATE {_AVISOS} SET responsavel_id = titular_id "
          "WHERE titular_tipo = 'responsavel' "
          "AND responsavel_id IS NULL")
    # 3. Tirar o índice e as colunas antigas.
    + _se(_existe_indice(_AVISOS, "idx_aviso_titular"),
          f"ALTER TABLE {_AVISOS} DROP INDEX idx_aviso_titular")
    + _se(_existe_coluna(_AVISOS, "titular_tipo"),
          f"ALTER TABLE {_AVISOS} DROP COLUMN titular_tipo")
    + _se(_existe_coluna(_AVISOS, "titular_id"),
          f"ALTER TABLE {_AVISOS} DROP COLUMN titular_id")
    # 4. As chaves estrangeiras (RESTRICT, como as outras do sistema:
    #    um cliente ou colaborador com avisos registados não se apaga —
    #    anonimiza-se ou desativa-se).
    + _se(_nao(_existe_restricao(_AVISOS, "fk_aviso_cliente")),
          f"ALTER TABLE {_AVISOS} ADD CONSTRAINT fk_aviso_cliente "
          "FOREIGN KEY (cliente_id) REFERENCES clientes (id) "
          "ON DELETE RESTRICT ON UPDATE RESTRICT")
    + _se(_nao(_existe_restricao(_AVISOS, "fk_aviso_responsavel")),
          f"ALTER TABLE {_AVISOS} ADD CONSTRAINT fk_aviso_responsavel "
          "FOREIGN KEY (responsavel_id) REFERENCES responsaveis (id) "
          "ON DELETE RESTRICT ON UPDATE RESTRICT")
    + _se(_nao(_existe_restricao(_AVISOS, "fk_aviso_registado_por")),
          f"ALTER TABLE {_AVISOS} ADD CONSTRAINT fk_aviso_registado_por "
          "FOREIGN KEY (registado_por_id) REFERENCES responsaveis (id) "
          "ON DELETE RESTRICT ON UPDATE RESTRICT")
    # 5. Exatamente um titular por linha.
    + _se(_nao(_existe_restricao(_AVISOS, "ck_aviso_um_titular")),
          f"ALTER TABLE {_AVISOS} ADD CONSTRAINT ck_aviso_um_titular "
          "CHECK ((cliente_id IS NULL) <> (responsavel_id IS NULL))")
)


# Lista oficial, por ordem. Só cresce — nunca alterar uma já publicada.
MIGRACOES = [
    ("0001_categoria_compra_de_stock", [_SQL_CATEGORIA_COMPRA_DE_STOCK]),
    (
        "0002_textos_legais_demo",
        [
            _sql_publicar_texto_demo(
                "confidencialidade", migracoes_textos.CONFIDENCIALIDADE
            ),
            _sql_publicar_texto_demo(
                "privacidade_colaborador",
                migracoes_textos.PRIVACIDADE_COLABORADOR,
            ),
            _sql_publicar_texto_demo(
                "privacidade_hospede", migracoes_textos.PRIVACIDADE_HOSPEDE
            ),
        ],
    ),
    ("0003_avisos_privacidade_fks", _MIGRACAO_0003),
]

_FORMATO_NOME = re.compile(r"^\d{4}_[a-z0-9_]+$")


def validar_lista(migracoes):
    """Confirma que a lista de migrações está bem escrita.

    Levanta ValueError se um nome não seguir o formato
    "NNNN_descricao", se houver nomes repetidos, se a ordem não for
    crescente, ou se uma migração não tiver instruções.
    """
    anterior = ""
    vistos = set()

    for nome, instrucoes in migracoes:
        if not _FORMATO_NOME.match(nome):
            raise ValueError(
                f"Nome de migração inválido: {nome!r} "
                f"(formato esperado: 0001_descricao)."
            )

        if nome in vistos:
            raise ValueError(f"Migração repetida: {nome!r}.")

        if nome < anterior:
            raise ValueError(
                f"Migração fora de ordem: {nome!r} vem depois de "
                f"{anterior!r}."
            )

        if not instrucoes:
            raise ValueError(f"A migração {nome!r} não tem instruções.")

        vistos.add(nome)
        anterior = nome


def aplicar_pendentes(migracoes=None):
    """Aplica, por ordem, as migrações que ainda faltam nesta base.

    'migracoes' existe para os testes passarem uma lista própria;
    por omissão usa a lista oficial `MIGRACOES`.

    Devolve a lista dos nomes aplicados agora (vazia num arranque
    normal, com a base já em dia).

    Se uma migração falhar, pára aí (as seguintes não correm) e
    levanta ValueError com o nome da migração e o erro original —
    quem chama decide não abrir a aplicação (decisão 2 do passo C).

    CONCORRÊNCIA (v1.8.1): tudo corre dentro do bloqueio de migrações
    da base (`repositorio.bloqueio_migracoes`). Um segundo arranque ao
    mesmo tempo espera pelo primeiro e só depois lê o que já foi
    aplicado — nunca corre a mesma migração duas vezes.
    """
    lista = MIGRACOES if migracoes is None else migracoes
    validar_lista(lista)

    with repositorio.bloqueio_migracoes():
        return _aplicar_em_falta(lista)


def _aplicar_em_falta(lista):
    """Corre as migrações da lista que ainda não estão registadas.
    Chamada só com o bloqueio de migrações na mão."""
    repositorio.garantir_tabela_migracoes()
    aplicadas = repositorio.listar_migracoes_aplicadas()

    feitas = []
    for nome, instrucoes in lista:
        if nome in aplicadas:
            continue

        try:
            repositorio.aplicar_migracao(nome, instrucoes)
        except Exception as erro:
            logger.exception("Migração %s falhou", nome)
            raise ValueError(
                f"A atualização da base de dados falhou na migração "
                f"{nome}: {erro}"
            ) from erro

        logger.info("Migração aplicada: %s", nome)
        feitas.append(nome)

    return feitas
