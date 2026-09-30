"""Camada de persistência. Único módulo que toca em ficheiros e na
base de dados.

Os módulos de negócio nunca leem nem gravam — pedem aqui. Foi isto
que permitiu migrar módulo a módulo de JSON para MySQL (decisão 1)
sem tocar nos módulos de negócio.

MIGRAÇÃO CONCLUÍDA (v1.1.0): todas as entidades falam diretamente
com o MySQL através de `obter_conexao()`, nas funções específicas
por entidade mais abaixo neste ficheiro. As antigas `carregar()` /
`gravar()` / `_estrutura_vazia()` / `_migrar()` e os auxiliares de
serialização (`_reconstituir_tipos`, `_serializar`, `_desserializar`)
que liam e escreviam `dados/dados.json` foram removidos por já não
terem nenhum consumidor — nem `main.py`/`cli.py` nem nenhum módulo
de negócio (grep confirmado em todo o projeto antes da remoção).

Módulos já migrados: propriedades, unidades (unidades, quartos,
lugares), responsaveis, clientes, contratos (ocupacoes,
ocupacoes_mensal, ocupacoes_airbnb), estoque (produtos, movimentos,
requisicoes, itens_requisicao, devolucoes, itens_devolucao).

v1.8.0 (decisão D4): o `dados/contadores.json` deixou de existir —
`proximo_id()` calcula o próximo número a partir do MAX(id) da
tabela de cada prefixo (ver `_base._TABELA_POR_PREFIXO`).

`criar_backup()`/`limpar_backups_antigos()` passaram a fazer dump
da base MySQL via `mysqldump` (antes copiavam `dados.json`, que já
não existe) — ver docstring de `criar_backup()` para o porquê da
escolha e os requisitos (binário `mysqldump` no PATH).

ALTERAÇÕES 15/09/2026 (Fase 1, v1.4.0 — pastas persistentes):

- `dados/` e `backups/` deixam de viver dentro do repositório
  (`RAIZ_PROJETO / "dados"` / `"backups"`, decisão 13 antiga).
  Passam a viver em `config.DIR_DADOS` / `config.DIR_BACKUPS` —
  fora da pasta de instalação, para não dar erro de permissão de
  escrita quando o sistema corre como executável PyInstaller (ver
  `config.garantir_diretorios()`).
- `_garantir_pastas()` passa a delegar em
  `config.garantir_diretorios()`, em vez de criar as pastas aqui —
  uma só função decide onde estas pastas vivem no disco.
- `FICHEIRO_CONTADORES` deixa de ser uma constante de módulo:
  calcula-se a cada chamada a partir de `config.DIR_DADOS`, para
  acompanhar corretamente o caminho de recurso (fallback) de
  `config.garantir_diretorios()`, se algum dia for acionado.

ALTERAÇÕES 10/09/2026 (ecrãs Produtos e Movimentos da GUI):

- `inserir_produto`/`_normalizar_produto`/`atualizar_produto`
  passam a lidar com `desativado_por_id`/`data_desativacao` —
  duas colunas novas em `produtos`, para registar quem autorizou
  uma desativação forçada (mesma convenção de `propriedades` e
  `unidades`).
- `contar_movimentos_produto`, `contar_itens_requisicao_produto` e
  `contar_itens_devolucao_produto` são novas — usadas por
  `estoque.desativar_produto` para decidir se a desativação tem
  de ser forçada.
- `listar_movimentos` ganhou filtro por `tipo` e passou a ordenar
  em SQL (data decrescente) — o ecrã de Movimentos da GUI precisa
  das duas coisas.

ALTERAÇÕES 13/09/2026 (IBAN da propriedade, para a impressão do
contrato mensal):

- `propriedades` ganha uma coluna `iban` (VARCHAR) — o IBAN do
  senhorio, para onde o inquilino paga a renda. É o campo que a
  Cláusula 3ª do contrato mensal imprime.
- `inserir_propriedade` grava-o; `_normalizar_propriedade` (nova)
  repõe "" quando vier NULL, mesma convenção de string vazia usada
  em todo o sistema; `procurar_propriedade` e `listar_propriedades`
  passam a chamar a normalização.
- `atualizar_propriedade` não muda: já aceita qualquer campo, e o
  `iban` é apenas mais um.

ALTERAÇÕES 13/09/2026 (Aprovação de Requisições + cancelamento):

- `requisicoes` ganha duas colunas novas: `observacao_rececao`
  (TEXT) e `origem` (VARCHAR com DEFAULT 'pedido').
- `inserir_requisicao` passa a gravá-las explicitamente (ambas
  vêm sempre preenchidas do `estoque.criar_requisicao`).
- `_normalizar_requisicao` repõe "" em `observacao_rececao` e
  `origem` quando vierem NULL — por simetria com as outras
  colunas de texto (na prática `origem` nunca vem NULL, porque a
  coluna tem DEFAULT e o negócio preenche-a sempre).
- `atualizar_requisicao` não muda: já aceita qualquer campo, e
  os dois novos são apenas mais dois.

ALTERAÇÕES 26/09/2026 (divisão em pacote):

- O antigo `src/repositorio.py` (3 557 linhas) passou a ser o
  pacote `src/repositorio/`, um ficheiro por domínio. O código foi
  movido sem alterações. Este `__init__.py` reexporta tudo, por isso
  quem faz `import repositorio` não precisa de mudar nada.
- ATENÇÃO para testes futuros: substituir uma função com
  `repositorio.x = falso` ou `mock.patch("repositorio.x")` já NÃO
  chega aos outros ficheiros do pacote — é preciso fazer o patch no
  submódulo onde ela vive (ex.: `repositorio._base.obter_conexao`).
"""

from ._base import (
    _garantir_pastas,
    config,
    criar_backup,
    limpar_backups_antigos,
    obter_conexao,
    proximo_id,
    subprocess,
)
from .rep_propriedades import (
    atualizar_lugar,
    atualizar_propriedade,
    atualizar_quarto,
    atualizar_unidade,
    contar_unidades_ativas,
    inserir_lugar,
    inserir_propriedade,
    inserir_quarto,
    inserir_unidade,
    listar_lugares,
    listar_propriedades,
    listar_quartos,
    listar_unidades,
    listar_unidades_com_propriedade,
    procurar_lugar,
    procurar_propriedade,
    procurar_quarto,
    procurar_unidade,
)
from .rep_responsaveis import (
    atualizar_atribuicao,
    atualizar_responsavel,
    inserir_atribuicao,
    inserir_responsavel,
    listar_atribuicoes,
    listar_responsaveis,
    listar_responsaveis_com_credencial,
    procurar_atribuicao,
    procurar_responsavel,
    procurar_responsavel_por_username,
)
from .rep_clientes import (
    atualizar_cliente,
    cliente_com_nif_existe,
    inserir_cliente,
    listar_clientes,
    procurar_cliente,
)
from .rep_contratos import (
    atualizar_ocupacao,
    atualizar_ocupacao_airbnb,
    atualizar_ocupacao_mensal,
    inserir_ocupacao,
    inserir_ocupacao_airbnb,
    inserir_ocupacao_mensal,
    listar_ocupacoes,
    procurar_ocupacao,
    procurar_ocupacao_airbnb,
    procurar_ocupacao_mensal,
)
from .rep_estoque import (
    atualizar_devolucao,
    atualizar_item_requisicao,
    atualizar_produto,
    atualizar_requisicao,
    contar_itens_devolucao_produto,
    contar_itens_requisicao_produto,
    contar_movimentos_produto,
    inserir_devolucao,
    inserir_item_devolucao,
    inserir_item_requisicao,
    inserir_movimento,
    inserir_produto,
    inserir_requisicao,
    listar_devolucoes,
    listar_itens_devolucao,
    listar_itens_requisicao,
    listar_movimentos,
    listar_produtos,
    listar_regras_rol_lavanderia,
    listar_requisicoes,
    procurar_devolucao,
    procurar_item_devolucao,
    procurar_item_requisicao,
    procurar_produto,
    procurar_requisicao,
)
from .rep_despesas import (
    atualizar_categoria_despesa,
    atualizar_despesa,
    atualizar_fornecedor,
    atualizar_item_despesa,
    inserir_categoria_despesa,
    inserir_despesa,
    inserir_fornecedor,
    inserir_item_despesa,
    listar_categorias_despesa,
    listar_despesas,
    listar_fornecedores,
    listar_itens_despesa,
    procurar_categoria_despesa,
    procurar_despesa,
    procurar_fornecedor,
)
from .rep_sistema import (
    apagar_tudo,
    criar_backup_com_nome,
)
from .rep_configuracoes import (
    gravar_configuracao,
    inserir_configuracao_historico,
    listar_configuracao_historico,
    listar_configuracoes,
    procurar_configuracao,
)
from .rep_esquema import (
    criar_tabelas,
    estado_base,
    instrucoes_esquema,
    preparar_base,
    tabelas_do_esquema,
)
from .rep_migracoes import (
    aplicar_migracao,
    garantir_tabela_migracoes,
    listar_migracoes_aplicadas,
)
from .rep_termos import (
    contar_avisos_por_versao,
    listar_avisos,
    listar_textos,
    obter_texto,
    obter_texto_em_vigor,
    obter_ultimo_aviso,
    publicar_texto,
    registar_aviso,
)

# Lista explícita do que o pacote exporta. Também diz ao
# pyflakes que os imports acima são usados.
__all__ = [
    "_garantir_pastas",
    "config",
    "criar_backup",
    "limpar_backups_antigos",
    "obter_conexao",
    "proximo_id",
    "subprocess",
    "criar_tabelas",
    "estado_base",
    "preparar_base",
    "instrucoes_esquema",
    "tabelas_do_esquema",
    "aplicar_migracao",
    "garantir_tabela_migracoes",
    "listar_migracoes_aplicadas",
    "atualizar_lugar",
    "atualizar_propriedade",
    "atualizar_quarto",
    "atualizar_unidade",
    "contar_unidades_ativas",
    "inserir_lugar",
    "inserir_propriedade",
    "inserir_quarto",
    "inserir_unidade",
    "listar_lugares",
    "listar_propriedades",
    "listar_quartos",
    "listar_unidades",
    "listar_unidades_com_propriedade",
    "procurar_lugar",
    "procurar_propriedade",
    "procurar_quarto",
    "procurar_unidade",
    "atualizar_atribuicao",
    "atualizar_responsavel",
    "inserir_atribuicao",
    "inserir_responsavel",
    "listar_atribuicoes",
    "listar_responsaveis",
    "listar_responsaveis_com_credencial",
    "procurar_atribuicao",
    "procurar_responsavel",
    "procurar_responsavel_por_username",
    "atualizar_cliente",
    "cliente_com_nif_existe",
    "inserir_cliente",
    "listar_clientes",
    "procurar_cliente",
    "atualizar_ocupacao",
    "atualizar_ocupacao_airbnb",
    "atualizar_ocupacao_mensal",
    "inserir_ocupacao",
    "inserir_ocupacao_airbnb",
    "inserir_ocupacao_mensal",
    "listar_ocupacoes",
    "procurar_ocupacao",
    "procurar_ocupacao_airbnb",
    "procurar_ocupacao_mensal",
    "atualizar_devolucao",
    "atualizar_item_requisicao",
    "atualizar_produto",
    "atualizar_requisicao",
    "contar_itens_devolucao_produto",
    "contar_itens_requisicao_produto",
    "contar_movimentos_produto",
    "inserir_devolucao",
    "inserir_item_devolucao",
    "inserir_item_requisicao",
    "inserir_movimento",
    "inserir_produto",
    "inserir_requisicao",
    "listar_devolucoes",
    "listar_itens_devolucao",
    "listar_itens_requisicao",
    "listar_movimentos",
    "listar_produtos",
    "listar_regras_rol_lavanderia",
    "listar_requisicoes",
    "procurar_devolucao",
    "procurar_item_devolucao",
    "procurar_item_requisicao",
    "procurar_produto",
    "procurar_requisicao",
    "atualizar_categoria_despesa",
    "atualizar_despesa",
    "atualizar_fornecedor",
    "atualizar_item_despesa",
    "inserir_categoria_despesa",
    "inserir_despesa",
    "inserir_fornecedor",
    "inserir_item_despesa",
    "listar_categorias_despesa",
    "listar_despesas",
    "listar_fornecedores",
    "listar_itens_despesa",
    "procurar_categoria_despesa",
    "procurar_despesa",
    "procurar_fornecedor",
    "apagar_tudo",
    "criar_backup_com_nome",
    "gravar_configuracao",
    "inserir_configuracao_historico",
    "listar_configuracao_historico",
    "listar_configuracoes",
    "procurar_configuracao",
    "contar_avisos_por_versao",
    "listar_avisos",
    "listar_textos",
    "obter_texto",
    "obter_texto_em_vigor",
    "obter_ultimo_aviso",
    "publicar_texto",
    "registar_aviso",
]
