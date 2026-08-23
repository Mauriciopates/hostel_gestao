# Registo de alterações

Todas as alterações relevantes deste projeto são registadas neste ficheiro.
Numeração segundo maior.menor.correção (decisão de arquitetura, secção 7).

### [0.7.0] — 2026-08-23

### Adicionado
- `cli.py`: interface de linha de comando, único módulo autorizado a
  usar `input()`/`print()` (decisão 7). 84 funções:
  - Leitoras de base: `ler_texto`, `ler_inteiro`, `ler_decimal`,
    `ler_data`, `confirmar`.
  - `mostrar_menu`: menu numerado com saída/voltar sempre em "0",
    sempre na última linha, aceitando tanto o número como o texto
    exato da opção.
  - Formatadoras: `formatar_data`, `formatar_valor` — inversas de
    `ler_data`/`ler_decimal`, formato de apresentação PT-PT.
  - Leitoras de atualização: `ler_atualizacao`,
    `ler_booleano_atualizacao`, `ler_escolha_atualizacao` — Enter em
    branco mantém, hífen sozinho apaga (só onde `permite_limpar` é
    verdadeiro).
  - Ecrãs de propriedades, unidades/quartos/lugares, responsáveis,
    clientes (incluindo anonimização, decisão 8), contratos mensais
    e reservas Airbnb, e estoque (produtos, movimentos e
    requisições) — cada um com `menu_X` a amarrar as suas ações.
  - `mostrar_erro_arranque`: mostra um erro fatal de arranque, antes
    de o sistema chegar ao menu principal — chamada pelo `main.py`
    quando `repositorio.carregar()` levanta `ValueError`; é o único
    ponto do sistema em que uma exceção é apanhada fora de um ecrã
    propriamente dito, mas continua a preservar a decisão 7 (nunca
    um `print()` direto no `main.py`).
  - `menu_principal`: liga os seis submenus de módulo.
- `main.py`: ponto de entrada do sistema — cria a cópia de
  segurança, limpa cópias antigas (`config.DIAS_BACKUP`), carrega os
  dados e entrega ao `cli.menu_principal`. Não tem `input()`/
  `print()` próprio: até o erro de arranque é delegado a
  `cli.mostrar_erro_arranque` (decisão 7).
- `teste_manual_cli.md`: roteiro de teste manual de `cli.py` e
  `main.py`, 9 grupos — substitui `unittest` para estes dois módulos
  (ver decisão registada abaixo).
- `Pseudocodigo_Modulos.docx`: capítulos 18 (Módulo cli.py) e 19
  (Testes do módulo cli.py) — documento sobe para a versão 1.7.
- Entidade `Devolucao` em `modelos.py` (decisão 19) — sobra de material
  devolvida ao armazém passa a ser um registo próprio (`DEV-0xx`),
  associado a uma requisição já fechada, com fluxo próprio de dois
  estados (pendente → fechada).
- `estoque.py`: `reportar_devolucao`, `procurar_devolucao`,
  `listar_devolucoes`, `fechar_devolucao` — substituem
  `devolver_requisicao`/`fechar_requisicao`.
- `cli.py`: ecrãs "Reportar sobra (devolução)" e "Aceitar devolução"
  no menu de Requisições, no lugar de "Devolver material"/"Fechar
  requisição".


### Alterado
- `repositorio.py` (v0.2.0, fechado) — `carregar()` nunca chamava
  `_desserializar()` depois do `json.load()`: campos `Decimal` e
  `date` voltavam do disco como texto, e só rebentava num
  `formatar_valor` já dentro do `cli.py`, sem relação aparente com a
  causa. Corrigido com uma função nova, `_reconstituir_tipos(dados)`,
  chamada logo a seguir ao `json.load()`. Invisível aos testes
  automáticos existentes, porque nenhum deles grava e volta a
  carregar de um ficheiro real — só apareceu no primeiro arranque
  real via `main.py`.
- `contratos.py` (v0.5.0, fechado):
  - Prefixo de ID único `PREFIXO = "OCU"` desmembrado em
    `PREFIXO_MENSAL = "CNT"` e `PREFIXO_AIRBNB = "RSV"` — um
    contrato mensal gera documento, uma reserva é só controlo
    interno; o prefixo partilhado confundia os dois.
  - Nova função pública `calcular_preco_airbnb(unidade,
    data_inicio, data_fim)` — resolve a lacuna nº4 da lista de
    pendências (sem forma de pré-visualizar o preço calculado antes
    de registar a reserva).
  - `registar_airbnb`/`atualizar_airbnb`: os campos de texto livre
    `motivo_alteracao_preco`/`motivo_alteracao_multa` foram
    substituídos por `responsavel_desconto_preco_id`/
    `responsavel_desconto_multa_id` (decisão 18, nova — ver abaixo).
  - `reativar()`: reservas Airbnb passam a verificar sobreposição
    antes de reativar, com a mesma `_existe_sobreposicao` já usada
    em `registar_airbnb` — sem isto, dava para reativar uma reserva
    cancelada mesmo já existindo outra reserva ativa a cobrir as
    mesmas datas na mesma unidade (bug encontrado durante o Grupo 6
    do roteiro manual).
- `modelos.py` — dataclass `OcupacaoAirbnb`: mesma troca de campos
  de `contratos.py` acima.
- `teste_contratos.py`: testes atualizados para os novos prefixos
  (`test_id_gerado_com_prefixo_cnt`, `test_id_gerado_com_prefixo_rsv`
  novo) e os três placeholders `"OCU-999"` trocados por
  `"CNT-999"`; 69 testes, todos verdes.
- `Requisicao` (modelos.py) simplificada de cinco para quatro
  estados: pendente → enviada → fechada, com rejeitada a partir de
  pendente. Removidos os campos `quantidade_devolvida`,
  `data_rececao` e `data_devolucao` — a sobra devolvida deixou de
  ser um passo da requisição.
- `estoque.confirmar_rececao_requisicao` fecha a requisição
  automaticamente no momento da confirmação (antes só passava a
  "recebida", à espera de devolução).
- `repositorio.py`: `_estrutura_vazia` e `_reconstituir_tipos`
  ajustados para a nova coleção `dados["devolucoes"]` e para os
  campos de data revistos em `requisicoes`.
- `teste_estoque.py`: `TestDevolverRequisicao`/`TestFecharRequisicao`
  substituídos por `TestReportarDevolucao`/
  `TestProcurarListarDevolucao`/`TestFecharDevolucao` (108 testes,
  todos verdes).

### Decisões registadas
- Gravação imediata: cada ecrã que altera `dados` chama
  `repositorio.gravar(dados)` logo a seguir a um sucesso, nunca em
  lote nem só no fim do programa.
- Testes de `cli.py`/`main.py`: decisão de teste MANUAL via
  `main.py`, não `unittest` com mock de `input()` — única exceção às
  suites automáticas dos restantes módulos, por serem os únicos com
  interação direta (decisão 7).
- Tratamento do erro de arranque: `main.py` apanha o `ValueError` de
  `repositorio.carregar()` e delega a mensagem a
  `cli.mostrar_erro_arranque`, preservando a decisão 7. Infraestrutura
  de `logging` a sério fica deliberadamente fora da Fase 1.
- **Decisão 18 (nova):** quando o preço ou a multa praticados de uma
  reserva Airbnb ficam abaixo do calculado, é um desconto — exige
  confirmação explícita e o ID de um responsável que o autorize
  (`responsaveis.validar_autoria`, tem de existir e estar ativo),
  tanto na criação como na atualização. Substitui o antigo campo de
  motivo em texto livre, que nunca era obrigatório.
- Três lacunas de arquitetura continuam identificadas e documentadas
  para correção em ramos `fix/` após o fecho da v0.7.0 (ver
  `claude/Pendencias_Correcoes_pos_0.7.0.txt`): `clientes.atualizar`
  não recusa clientes anonimizados (severidade alta, RGPD);
  `contratos.criar_mensal`/`atualizar_mensal` descartam o booleano
  de `validacoes.validar_caucao`; `dia_vencimento` só é validado em
  `atualizar_mensal`, não em `criar_mensal`. (A quarta lacuna original
  — pré-visualização do preço Airbnb — foi resolvida nesta sessão,
  ver `contratos.calcular_preco_airbnb` acima.)
- **Decisão 19** — a devolução de sobra de material deixou de ser um
  passo obrigatório da requisição, o que antes obrigava a aceitar
  `quantidade_devolvida = 0` como valor válido sem sentido de
  negócio real ("0" não é uma devolução, é a ausência de uma).
  Passa a ser uma entidade própria (`Devolucao`), associada a uma
  requisição já fechada, só existindo quando há mesmo sobra
  (`quantidade > 0`, validado). A confirmação de receção passa a
  fechar a requisição automaticamente, por analogia com o mundo
  real: "confirmo receção já fecha automaticamente, reportar sobra
  é um evento à parte, só quando existir sobra".

## [0.6.0] — 2026-08-20

### Adicionado
- `estoque.py`: módulo de gestão de stock, com três entidades —
  Produto, Movimento e Requisição — implementando a decisão 9
  (armazém único e central).
  - Produto: `criar_produto`, `procurar_produto`, `listar_produtos`,
    `atualizar_produto`, `desativar_produto`, `reativar_produto`.
  - Movimento: `registar_movimento`, `saldo_produto`. Movimentos são
    imutáveis — correções fazem-se sempre com um novo movimento de
    tipo `"ajuste"` e motivo obrigatório, nunca por alteração de um
    movimento existente.
  - Requisição: `criar_requisicao`, `procurar_requisicao`,
    `listar_requisicoes`, `enviar_requisicao`, `rejeitar_requisicao`,
    `confirmar_rececao_requisicao`, `devolver_requisicao`,
    `fechar_requisicao` — implementam o fluxo de cinco estados
    pendente → enviada → recebida → devolução pendente → fechada,
    com `rejeitada` como saída alternativa a partir de pendente.
  - Prefixos de identificador: `PRD` (produto), `MOV` (movimento),
    `REQ` (requisição) — decisão 2.
- `testes/teste_estoque.py`: 99 casos, 14 classes de teste,
  cobrindo as 16 funções do módulo.
- `Pseudocodigo_Modulos.docx`: capítulos 16 (Módulo estoque.py) e
  17 (Testes do módulo estoque.py) — documento sobe para a versão
  1.6.

### Alterado
- `modelos.py`: dataclass `Requisicao` — acrescentados os campos
  `produto_id` (obrigatório), `responsavel_rejeicao_id` (por
  omissão `""`) e `data_devolucao` (por omissão `None`),
  identificados como necessários durante o desenvolvimento de
  `estoque.py`.

### Decisões registadas
- Validação de saldo em `enviar_requisicao` (a quantidade enviada
  não pode exceder `saldo_produto`) — regra acrescentada durante o
  desenvolvimento, fora das 17 decisões originais do projeto.
- `registar_movimento` valida `responsavel_id` por
  `responsaveis.validar_autoria` apenas quando o campo é indicado,
  para permitir o registo inicial de stock antes de existirem
  responsáveis identificados.



### [0.5.0] - 2026-08-19


### Adicionado 

- `contratos.py`: gestão das ocupações de uma unidade — contratos de
  arrendamento mensal e reservas Airbnb, com uma base comum
  (`Ocupacao`) e tabelas específicas por regime (`OcupacaoMensal`,
  `OcupacaoAirbnb`). 16 funções: 7 auxiliares privadas,
  `procurar`/`listar`/`reativar` unificadas para os dois regimes, e
  `criar_mensal`/`atualizar_mensal`/`encerrar_mensal` (contrato) +
  `registar_airbnb`/`atualizar_airbnb`/`cancelar_airbnb` (reserva)
  divididas por regime.
- `testes/teste_contratos.py`: 68 testes unitários (336 no total do
  projeto).
- Pseudocódigo de `contratos.py` e dos seus testes — capítulos 14 e
  15 do `Pseudocodigo_Modulos` (agora na v1.5).

### Alterado 

- `modelos.py`: `Ocupacao` ganha o campo `aviso_documento`;
  `OcupacaoMensal` ganha `motivo_encerramento`,
  `duracao_abaixo_minima` e `aviso_previo_insuficiente`;
  `OcupacaoAirbnb` ganha `motivo_cancelamento`.



### [0.4.0] — 2026-08-18

Grupo "Pessoas". Versão par: quem contrata alojamento e quem opera o sistema.

### Adicionado

- `clientes.py`: registo de clientes, listagem de registos incompletos (decisão 11) e anonimização RGPD (decisão 8) — criar, procurar, listar, atualizar, desativar/reativar e anonimizar, com 51 testes e pseudocódigo documentado
- `responsaveis.py`: autoria de operações sem credenciais (decisão 10) — criar, procurar, listar, atualizar, desativar/reativar e validar_autoria, que exige responsável existente e ativo, com 60 testes e pseudocódigo documentado
Alterado
- `modelos.py`: acrescentado o campo morada à dataclass Cliente, para corresponder ao que validacoes.validar_cliente já verificava (módulo reaberto pontualmente; as restantes entidades não foram tocadas)
- `Pseudocodigo_Modulos v1.3 → v1.4`: capítulo 12 (módulo responsaveis.py) e capítulo 13 (os seus testes); secção 11.8 reescrita, por a limitação "não há validação cruzada com responsaveis.py" ter deixado de se aplicar
Campos obrigatórios do cliente: o nome passa a constar como campo que bloqueia a criação, a par do tipo e do número de documento. Corrige a decisão inicial ao confrontá-la com validacoes.py já fechado

### [0.3.0] — 2026-08-17

Grupo "Estrutura física". Versão ímpar: os edifícios e o que neles se contrata.

### Adicionado

- `propriedades.py` com criação, procura, listagem, atualização, desativação e reposição
28 testes da gestão de propriedades
-`unidades.py`: unidades, quartos e lugares — criar, procurar, listar, atualizar, desativar/reativar e marcar/desmarcar manutenção, com 74 testes e pseudocódigo documentado


### [0.2.0] — 2026-08-11

- Estrutura do repositório: `src/`, `testes/`, `docs/`, `dados/`, `backups/`, `logs/`
- Ambiente virtual com Python 3.11 e `requirements.txt` (Fase 1 sem dependências externas)
- `.gitignore` a excluir dados operacionais, cópias de segurança e registos (decisão 13)
- `config.py` com os valores de configuração da análise
- `modelos.py` com as 14 estruturas de dados do sistema
- `repositorio.py` com persistência em JSON, cópias de segurança diárias e contadores de identificadores
- 15 testes da camada de persistência em `testes/teste_repositorio.py`
- `validacoes.py` com verificação de NIF, campos obrigatórios por regime e regras de negócio
- 40 testes das validações em `testes/teste_validacoes.py`

### [0.1.0] — 2026-08-07

Fase de análise e desenho. Sem código.

### Adicionado
- `Arquitetura_Sistema_v1.8.docx` — 17 decisões de arquitetura, ciclo de vida,
  metodologia, divergências face à especificação e correspondência com a grelha
  de avaliação
- Fluxogramas da Fase 1 (4 páginas)
- Pseudocódigo dos processos principais
- Wireframes da Fase 2 (9 ecrãs)
- `Modelo_de_Dados_v1.3` com diagrama ER e lista de relações
- `Plano_de_Testes_v1.0.docx` — 101 casos em 12 grupos

### Alterado
- Protótipo em CLI (~7500 linhas) descartado. O valor retido está nos requisitos
  que revelou, não no código: contadores de ID a reiniciar, ausência de gravação
  automática, ausência de validação de sobreposição de datas e stock por unidade
  desalinhado da operação real
- Especificação corrigida de 20 para 22 unidades (omissão do Santa Catarina AP1)

### Segurança
- Histórico do Git limpo com `git-filter-repo` após deteção de dados pessoais
  reais em repositório público. Repositório recriado, dados de exemplo
  anonimizados