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

import repositorio

logger = logging.getLogger(__name__)


# Lista oficial, por ordem. Os seeds de sistema entram no passo D.
MIGRACOES = []

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
