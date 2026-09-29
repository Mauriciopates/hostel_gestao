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
    """
    lista = MIGRACOES if migracoes is None else migracoes
    validar_lista(lista)

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
