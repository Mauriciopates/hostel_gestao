# Registo de alterações

Todas as alterações relevantes deste projeto são registadas neste ficheiro.
Numeração segundo maior.menor.correção (decisão de arquitetura, secção 7).

### [1.0.1] — 2026/08/29


### Adicionado
- Confirmação explícita ao atribuir um segundo ocupante a um quarto
  privativo já ocupado (decisão 17) — fecha uma regra de negócio
  documentada desde a Fase 1 mas nunca codificada (identificado no
  roteiro de teste manual, secção de Unidades). Nova função
  `_quarto_privativo_ja_ocupado` em `cli.py`, chamada dentro de
  `_criar_contrato_mensal`, mesmo padrão já usado na confirmação da
  caução. A regra é do quarto, não do lugar isolado: um segundo
  ocupante em qualquer lugar do mesmo quarto privativo, mesmo que
  diferente do primeiro, exige confirmação. Fica em `cli.py` e não em
  `contratos.py` — confirmação de interface, não bloqueio de regra de
  negócio (decisão 7).

### Testes
- `teste_manual_cli.md`: novo Grupo 6A (7 passos), a seguir ao Grupo 6
  — cobre a ausência de confirmação quando o quarto ainda não tem
  ocupante, a confirmação recusada e aceite num lugar diferente do
  mesmo quarto privativo, e o controlo negativo de um quarto
  partilhado (nunca pede confirmação). Validado em execução real
  contra o repositório.

### [1.0.0] — 2026/08/28

Fase 1 completa — CLI + persistência em JSON. Todos os módulos integrados
e verificados pelas cinco condições, projeto inteiro (funciona, tem
testes, PEP 8, documentado, separação de camadas).

### Corrigido
- PEP 8: linhas acima de 79 caracteres corrigidas em `cli.py`,
  `clientes.py` e `contratos.py`, identificadas na verificação final da
  Fase 1 (condição 3 do script de verificação, aplicado ao projeto
  inteiro). Sem alteração de comportamento — suite completa confirmou.

### Documentação
- `Arquitetura_Sistema_v1.10.docx` → `v1.11.docx`: decisões 19 e 20
  (revisão do fluxo de stock e separação cabeçalho/itens — já
  implementadas e testadas desde a 0.7.0, ver `estoque.py`) documentadas
  pela primeira vez, fechando uma lacuna entre o código e o documento de
  referência identificada a 28/08/2026. Secção de estrutura de dados do
  stock corrigida (exemplo desatualizado dos estados da Requisição;
  acrescentadas as linhas `ItemRequisicao`, `Devolucao`,
  `ItemDevolucao`).
- `docs/4_Manual/Manual_Fase1_v1.0.0.docx`: manual da Fase 1 —
  instalação, utilização por menu (uma secção por módulo, com tabela de
  opções: Propriedades, Unidades, Clientes, Responsáveis, Contratos e
  Reservas, Stock) e normas e regulamentos aplicáveis (RGPD — anonimização,
  prazos de conservação, alerta automático; alojamento local — SIBA/AIMA,
  a confirmar em fonte oficial antes da entrega de outubro). Ainda sem
  capturas de ecrã — versão só de texto, a completar depois.

### Testes
- Verificação final da Fase 1 sobre os 12 módulos (as cinco condições
  do script de verificação): todos os módulos carregam sem erro; suite
  completa — **532 testes, todos verdes** (confirma o número esperado
  registado em 0.7.7); zero linhas acima de 79 caracteres depois da
  correção acima; módulos e funções públicas documentados; nenhuma
  chamada real a `input()`/`print()` fora de `cli.py` (as únicas
  ocorrências fora dele são menções em texto no docstring do
  `main.py`, não chamadas).

### [0.7.7] — 2026/08/27

Fase 1 completa. Fecha as pendências finais levantadas pelo roteiro
de teste da rotina diária (itens 5 a 10 de
Pendencias_Antes_v1.0.0.txt — o item 7 foi dispensado, ver
Documentação), mais um bug encontrado fora da lista original.
Sistema funcional em linha de comando, com persistência em JSON.

### Corrigido
- `clientes.py`: `criar` e `atualizar` passam a recusar um NIF já
  usado por outro cliente ativo (`_nif_pertence_a_outro_cliente`).
  `reativar` ganhou a mesma verificação, fechando a mesma brecha por
  outro caminho (evita dois clientes ativos com o mesmo NIF, um
  reativado depois de o outro já ter sido criado com esse NIF).
- `contratos.py`: `criar_mensal` passa a exigir NIF preenchido no
  cliente e a recusar um segundo contrato mensal ativo para o
  mesmo NIF (`_nif_tem_contrato_mensal_ativo`) — o cruzamento é só
  mensal-com-mensal, não considera reservas Airbnb do mesmo NIF.
- `repositorio.py`: `PASTA_DADOS` e `PASTA_BACKUPS` passam a ser
  ancoradas na raiz do projeto
  (`Path(__file__).resolve().parent.parent`), em vez de relativas
  à pasta a partir de onde o programa é executado — antes, correr
  a partir de `src/` fazia o sistema ler/gravar num `dados/` novo e
  vazio, ignorando o `dados/` real na raiz.
- `propriedades.py`: `desativar` ganhou o parâmetro `forcar=False`
  e passa a recusar desativar uma propriedade com unidades ativas
  associadas, salvo confirmação explícita (`forcar=True`).
- `unidades.py`: `desativar` ganhou o mesmo parâmetro e a mesma
  recusa, para ocupações ativas associadas à unidade.
- `cli.py`: `_desativar_propriedade`/`_desativar_unidade` passam a
  contar as dependências ativas e a pedir confirmação (s/n) antes
  de chamar `desativar(..., forcar=True)`.
- `contratos.py`: `criar_mensal` e `registar_airbnb` passam a
  recusar criar um contrato ou reserva numa unidade que não esteja
  ativa.

### Adicionado
- `cli.py`: listagens e ecrãs de contratos/reservas passam a
  mostrar sempre "nome (código)" da unidade e do cliente, em vez de
  só o nome — dois helpers novos, `_identificar_unidade` e
  `_identificar_cliente`, usados nos 8 pontos onde essa informação
  aparece.
- Criação de dois docs novos Pseudocodigo_Modulos e _Testes, sendo dois 
documentos distintos melhores de ser tratados. 

### Documentação
- Item 7 das pendências (corrigir "OCU-[ID]" para CNT-/RSV- no
  roteiro de teste da rotina diária) foi dispensado por decisão do
  aluno — o roteiro já tinha cumprido o papel de levantar esta
  lista de pendências e não ia ser reutilizado como está.
- Inclusão do arquivo Roteiro_testes_rotina_v1.0 em Docs/3_testes
- Exclusão do Documento Pseudocodigo_Modulos_v1.7, existe uma cópia no drive,
mas foi gerado um desmembrando Modulos e Testes. 


### Testes
- `teste_clientes.py`: +8 (6 do item 5, NIF duplicado; 2 do item 6,
  reativação cruzada).
- `teste_contratos.py`: +6 (4 do item 6; 2 do item 10, unidade
  inativa).
- `teste_propriedades.py` / `teste_unidades.py`: +3 cada (item 9,
  dependências ativas ao desativar).
- Marcos confirmados: 504 testes (fecho da 0.7.7) → 524 (depois do
  fix do caminho de dados) → 530 (depois do item 9). O item 10
  acrescentou mais 2, confirmados verdes em `teste_contratos.py`
  (90 testes nesse ficheiro) — falta só correr a suite completa
  uma última vez (esperado: 532) antes de fechar a tag.


### [0.7.6] — 2026/08/26

Nome próprio nas unidades — identificação visual em toda a interface,
sem depender só do prefixo/ID.

### Adicionado
- Campo `nome` em `Unidade` (`modelos.py`), obrigatório — mesma
  convenção que `Quarto` e `Lugar` já tinham. Passou a ser o 3.º
  argumento de `unidades.criar()` (a seguir a `propriedade_id`,
  antes de `tipo`) e um argumento opcional em `unidades.atualizar()`,
  com a mesma validação de "não pode ficar vazio" já usada em
  `criar_quarto`/`criar_lugar`.
- `cli.py`: os ecrãs de unidades (criar, listar, atualizar,
  desativar, reativar, marcar/desmarcar manutenção) passam a
  mostrar o nome da unidade — formato `UNI-XXX — Nome (tipo)` — em
  vez de só o ID e o tipo. A listagem de unidades passou também a
  mostrar o nome da propriedade em vez do ID cru.
- `cli.py`: ecrãs de Contratos e Reservas (criar, atualizar,
  encerrar, cancelar, reativar) e de Stock (movimento, requisições,
  devoluções) passam a mostrar o nome do cliente/unidade/produto/
  responsável relacionado, em vez de só o ID — mesma regra aplicada
  a toda a interface.

### Testes
- `teste_unidades.py` e `teste_contratos.py`: chamadas a
  `unidades.criar()` atualizadas com o novo argumento `nome`
  (8 pontos em `teste_unidades.py`, 3 em `teste_contratos.py`).
  Suite completa (N testes) confirmou.


### [0.7.5] — 2026-08-25

### Corrigido
- Em `modelos.py`, removida a definição duplicada da classe
  `Ocupacao` (existiam duas: uma incompleta, sem o atributo
  `aviso_documento`, e uma completa mais abaixo). A versão
  incompleta era ofuscada em runtime pela segunda definição (Python
  mantém apenas a última), mas o código morto criava risco de
  edição errada no futuro. Sem impacto funcional — suite completa
  confirmou.

### Adicionado
- Implementada `unidades.estado(dados, unidade_id, data=None)`,
  pendente desde a Fase 2 (aguardava `contratos.py`). Calcula o
  estado de uma unidade numa data:
  - Unidades em manutenção (`em_manutencao=True`) devolvem sempre
    "Em manutenção", independentemente de ocupações.
  - Unidades com regime mensal devolvem a proporção de lugares
    ocupados face à capacidade total (`X/Y`), considerando apenas
    ocupações mensais ativas cuja `data_inicio` já decorreu e sem
    `data_fim` anterior à data pedida.
  - Unidades Airbnb devolvem "Livre", "Ocupado" ou "Reservado"
    consoante a sobreposição de reservas ativas com a data pedida
    (fórmula da secção 4: `inicio_A < fim_B E inicio_B < fim_A`,
    contagem por noites — dia de check-out não conflita com
    check-in do mesmo dia).
  - Ligado o cálculo à listagem de unidades em `cli.py`
    (`_listar_unidades`): novo prompt "Data para calcular o estado"
    (Enter = hoje) e nova linha de saída por unidade.

### Testes
- Novos testes em `teste_unidades.py`, classe `TesteEstado`: 19
  testes (recusa de ID inexistente; 7 cenários de regime mensal —
  proporção, encerramento, ocupações futuras/inativas, isolamento
  entre unidades; 8 cenários de regime Airbnb — Livre/Ocupado/
  Reservado, sobreposição na fronteira, cancelamentos; 3 cenários
  de manutenção). Antes só existia `test_nao_implementada`, a
  testar o `NotImplementedError` do placeholder.
- `dados_base()` passou a incluir a chave `"ocupacoes": []`;
  adicionados os helpers `criar_ocupacao(...)` e
  `dar_lugares(...)` para montar cenários de teste sem depender de
  `contratos.py`.

Testes: `teste_unidades.py` completo, 92 testes, todos verdes.
Suite completa do projeto (490 testes) confirmou não haver efeitos
colaterais — à parte de 4 erros conhecidos e sem relação (falso
positivo do Windows em `repositorio._gravar_contadores`, já
documentado, não reprodutível).


### [0.7.4] — 2026-08-25

### Corrigido
- No módulo `repositorio.py` em `repositorio.carregar` verifica agora a versão dos dados gravados
  antes de reconstituir os tipos (Decimal e date) dos registos —
  antes fazia o inverso, e dados gravados por uma versão mais
  recente do formato rebentavam com um `KeyError` confuso em vez do
  `ValueError` claro já previsto para esse caso (severidade média)

### Testes
- `teste_gravar_e_carregar_preserva_data` deixou de chamar
  `_desserializar` uma segunda vez sobre um valor que
  `repositorio.carregar` já reconstitui internamente — o `date`
  devolvido não passa por `date.fromisoformat` outra vez, que não
  aceita receber um `date` já convertido (ponto 6a; não havia bug,
  só um teste com uma conversão a mais, mascarada até agora por
  `Decimal()` tolerar o mesmo padrão no teste irmão).

Testes: `teste_repositorio.py` completo, 15 testes, todos verdes.
Suite completa do projeto (472 testes) confirmou não haver efeitos
colaterais no resto do código.


### [0.7.3] — 2026-08-25

### Testes
- Investigado o ponto 5 das pendências pós-0.7.0 (27 erros + 1
  falha em testes de reservas Airbnb): A correção
  ficou toda em `teste_contratos.py`:
  - `ESTADIA_MINIMA_NOITES` foi alterado intencionalmente para 1
    (aceitar reservas de 1 noite, dado o regime de check-in às
    15h / check-out às 11h). O teste
    `test_estadia_abaixo_do_minimo_gera_erro` testava um cenário
    que deixou de ser inválido — substituído por
    `test_estadia_de_uma_noite_aceite`.
  - `preco_praticado` estava desatualizado em 17 testes (6
    classes), com um valor fixo (50.00) que caía sempre abaixo do
    `preco_calculado` real da estadia completa (soma de
    `preco_base` por noite), acionando sem intenção o ramo de
    desconto da decisão 18 e a exigência de responsável. Valores
    corrigidos para refletirem preços sem desconto.
  - Decisão tomada com o aluno: perdão total da multa
    (`multa_praticada=0.00`) continua a exigir responsável
    validado, tal como um desconto parcial — sem exceção. Os dois
    testes que exercitam esse caso
    (`test_check_in_tardio_multa_praticada_editavel`,
    `test_multa_zero_admitida_como_perdao`) passam agora um
    responsável criado com `responsaveis.criar`.

Testes: `teste_contratos.py` completo, 76 testes, todos verdes.
Suite completa do projeto (472 testes) confirmou não haver efeitos
colaterais no resto do código — à parte de 2 erros novos e sem
relação, em `teste_repositorio.py` (persistência), registados como
pendência separada; não bloqueiam este fix.


### [0.7.2] — 2026-08-24

### Corrigido
- `contratos.criar_mensal` recusa agora `dia_vencimento` fora do
  intervalo 1–28 ou não inteiro, tal como `atualizar_mensal` já
  fazia — a validação foi extraída para `_validar_dia_vencimento`,
  chamada pelas duas funções (severidade baixa — ver
  `claude/Pendencias_Correcoes_pos_0.7.0.txt`, ponto 3).
- `contratos.criar_mensal` e `atualizar_mensal` passam a devolver
  o resultado de `validacoes.validar_caucao` no novo campo
  `caucao_exige_confirmacao`, em vez de o descartar — a decisão 14
  (confirmação explícita quando a caução é nula ou acima da renda)
  fica agora representada nos dados, não só no remendo do cli.py
  (severidade média — ver mesmo ficheiro, ponto 2).

Testes: `teste_contratos.py`, classes `TesteCriarMensal` e
`TesteAtualizarMensal` — todos verdes (7 testes novos + os já
existentes). A corrida completa do ficheiro revelou, em paralelo,
27 erros e 1 falha em testes de reservas Airbnb — sem relação com
este fix (não tocam em contratos mensais, caução ou
dia_vencimento). Ficam registados como nova pendência para investigação em fix/ separado.


### [0.7.1] — 2026-08-24

### Corrigido
- `clientes.atualizar` recusa agora clientes já anonimizados
  (severidade ALTA, RGPD — decisão 8) — antes só o `cli.py` tinha
  essa guarda; uma chamada direta à função de negócio (testes, ou
  um futuro `gui.py`) conseguia reintroduzir dados pessoais já
  apagados. 


### [0.7.0] — 2026-08-23

### Adicionado
- `cli.py`: interface de linha de comando, único módulo autorizado a
  usar `input()`/`print()` (decisão 7). 89 funções:
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
  `main.py`, 9 grupos (90 passos) — substitui `unittest` para estes
  dois módulos (ver decisão registada abaixo). Todos os 90 passos
  correram manualmente e bateram com o resultado esperado antes do
  fecho desta versão.
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

  - `ItemRequisicao` e `ItemDevolucao` (modelos.py) — linha de produto
  + quantidade dentro de uma requisição/devolução (decisão 20).
- `estoque.listar_itens_requisicao`, `estoque.procurar_item_requisicao`,
  `estoque.listar_itens_devolucao`, `estoque.procurar_item_devolucao`.
- Ecrã "Enviar rol de lavanderia" no cli.py — o admin envia stock a
  um responsável sem requisição prévia (encadeia criar_requisicao +
  enviar_requisicao).
- Coleções `itens_requisicao` e `itens_devolucao` em repositorio.py,
  retrocompatíveis com ficheiros antigos (`.get(..., [])`).


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

- `Requisicao` e `Devolucao` (modelos.py) passam a ser cabeçalhos —
  perderam `produto_id`/`quantidade_pedida`/`quantidade_enviada` e
  `quantidade`, respetivamente; os produtos ficam em
  `ItemRequisicao`/`ItemDevolucao`.
- `estoque.criar_requisicao` e `estoque.reportar_devolucao` passam a
  receber uma lista de itens em vez de um único produto/quantidade.
- `estoque.enviar_requisicao` envia todos os itens de uma requisição
  numa só chamada (`quantidades_enviadas`, opcional, substitui
  `quantidade_enviada`); valida o saldo de todos os itens antes de
  gerar qualquer movimento — tudo ou nada.
- `estoque.fechar_devolucao` gera um movimento de entrada por item,
  numa só aceitação.
- cli.py: ecrãs de criar requisição e reportar devolução passam a
  fazer um loop "adicionar mais um produto?"; ecrã de enviar
  requisição só pergunta por ajuste de quantidade por item quando
  pedido — por omissão envia tudo na totalidade pedida.

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

  - Decisão 20: requisições e devoluções passam de um único produto
  por registo para cabeçalho + lista de itens, para suportar pedidos
  com vários produtos de uma vez. Envio, receção e aceitação de
  devolução continuam a ser uma ação única sobre o registo inteiro —
  nunca item a item. Sem funções de edição de requisição/devolução:
  qualquer correção a um registo já fechado passa por
  `registar_movimento(tipo="ajuste")` (decisão 9).

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