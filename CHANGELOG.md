# Registo de alterações

Todas as alterações relevantes deste projeto são registadas neste ficheiro.
Numeração segundo maior.menor.correção (decisão de arquitetura, secção 7).



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