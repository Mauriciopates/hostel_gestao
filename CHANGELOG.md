# Registo de alterações

Todas as alterações relevantes deste projeto são registadas neste ficheiro.
Numeração segundo maior.menor.correção (decisão de arquitetura, secção 7).

## [Não publicado] — v1.5.0 (em curso)

Módulo `utilizadores.py` — login, credenciais e permissões.
Primeiro dos três módulos da v1.5.0 (faltam `financeiro.py` e
`relatorios.py`). Esta entrada será consolidada com os outros dois
e datada quando a tag v1.5.0 for criada.

### Adicionado

- `src/utilizadores.py` — módulo novo. Login, gestão de credenciais
  e regras de permissão por perfil. Separado do `responsaveis.py`:
  os dois tocam na tabela `responsaveis`, cada um com o seu foco —
  `responsaveis.py` continua a ser o módulo da pessoa (nome,
  contacto, perfil, ativo/inativo); `utilizadores.py` trata do que
  é específico de autenticação (procurar pelo username, validar
  password, registar último acesso, verificar permissões). Mesmo
  padrão de `estoque.py`/`produtos.py`.

  Funções públicas: `autenticar`, `definir_credencial`,
  `alterar_password`, `desativar`, `reativar`, `listar_com_estado`,
  `verificar_permissao`.

  Hash de password no formato modular do Django
  (`pbkdf2_sha256$<iteracoes>$<salt>$<hash>`), com
  `hashlib.pbkdf2_hmac`. Escolhido o formato modular porque migra
  para Django na Fase 3 sem conversão — algoritmo, iterações e salt
  vivem dentro da própria string, portanto mudar de algoritmo no
  futuro é só gravar com outro prefixo, sem tocar no esquema.

- Colunas novas em `responsaveis` (aplicadas por `ALTER TABLE` em
  17/09/2026): `username` (VARCHAR(50) UNIQUE), `password_hash`
  (VARCHAR(255)), `password_alterada_em` (DATETIME),
  `ultimo_login` (DATETIME), `desativado_por_id` (VARCHAR(10),
  FK auto-referente) e `data_desativacao` (DATE).

  O `username` nasce `NULL` — a coluna é `UNIQUE` mas o MySQL não
  conta nulos como duplicados, portanto vários responsáveis podem
  coexistir sem credencial. O Master define cada um pela GUI. O
  `password_hash` acompanha: `NULL` enquanto não há credencial.

  `desativado_por_id` e `data_desativacao` seguem o mesmo padrão já
  usado em `produtos`, `propriedades` e `unidades` — consistência
  interna, não preparação especulativa para a Fase 3.

- `repositorio.procurar_responsavel_por_username()` — procura pelo
  username em vez do id. É o que o `autenticar` usa.

- `repositorio.listar_responsaveis_com_credencial()` — variante de
  `listar_responsaveis` que devolve também as colunas de credencial
  já normalizadas. Existe para o ecrã de Gestão de Responsáveis
  poder mostrar "sem credencial" ou "último acesso" sem segunda
  consulta.

- Modal "Definir credencial" (gui_responsaveis.py) — atribui
  username e password a um responsável que ainda não tem. Campos:
  utilizador, password, confirmar password. Aviso visível de que a
  password é gravada com hash e não pode ser consultada depois.

- Modal "Alterar password" (gui_responsaveis.py) — troca a password
  de um responsável. Adapta-se ao contexto: se for o próprio a
  alterar, pede a password atual (para confirmar identidade); se for
  um Master a alterar de outro, não pede — o Master não sabe a
  antiga, e é a operação que permite recuperar acesso quando alguém
  se esquece.

- Bloco de credencial no popup "Gerir" (gui_responsaveis.py) — no
  topo do popup, antes das ações habituais. Dois estados: sem
  credencial mostra um aviso e o botão "Definir credencial"; com
  credencial mostra o username, o último acesso e o botão "Alterar
  password". O bloco encolhe quando já há credencial.

- `LoginModal` (app.py) — substitui o antigo
  `SelecionarUtilizadorModal`. Pede utilizador e password, e valida
  contra `utilizadores.autenticar`. Bloqueante: sem login válido, a
  GUI principal não abre. Tem quatro mensagens de erro específicas
  (utilizador não encontrado, sem credencial definida, password
  incorreta, conta inativa) e um botão "Sair" discreto que fecha a
  aplicação inteira.

- Feedback visual no `LoginModal` durante a autenticação: o botão
  muda para "A validar credenciais" com pontos animados, e os
  campos/botões ficam desativados. O `update_idletasks()` antes da
  chamada a `autenticar` força o redesenho — sem ele, a GUI só
  atualizava quando a validação já tinha terminado (e a espera
  parecia um bloqueio).

- Logoff verdadeiro: "Trocar utilizador" fecha a janela toda (com
  confirmação prévia) e a aplicação reabre do zero. O `main_gui.py`
  ficou com um `while` que deteta `self.reabrir` e cria uma nova
  `Aplicacao`. Antes, o popup do login abria por cima do Dashboard,
  deixando os dados do utilizador anterior à vista.

- `utilizadores.verificar_permissao(autor, perfis_permitidos,
  perfil_alvo=None)` — helper central de permissões. Cobre duas
  regras com a mesma forma: a regra geral "só Master/Admin" e a
  regra do Admin "só opera sobre Staff". O `perfil_alvo` opcional
  ativa a segunda.

### Alterado

- `responsaveis.criar()` ganha `autor` (opcional). Fecha a
  pendência 11.4 — só Master cria Admin/Master, Admin cria Staff,
  Staff não cria ninguém. Aceita `None` para não quebrar o CLI
  (que ainda não passa o autor); quando `autor` é passado, a
  validação é feita.

- `responsaveis.desativar()` e `responsaveis.reativar()` ganham
  `autor` e delegam a lógica em `utilizadores.desativar` /
  `utilizadores.reativar`. Sem duplicação de regras — a validação
  de permissão vive num sítio só.

- `responsaveis.alterar_tipo_utilizador()` passa a receber `autor`
  (o dict do responsável ativo) em vez de `tipo_utilizador_autor`
  (só o tipo em texto). Isto é o que permite implementar a regra
  3.4 — Masters imunes a rebaixamento por outros. Uniformiza também
  com o `utilizadores.py`: todas as funções que validam permissão
  recebem o autor como dict.

- `repositorio.inserir_responsavel()` passa a gravar as 11 colunas
  (antes 5). Os campos de credencial usam `.get()` com default
  `None`: na criação de um responsável sem credencial (o caso
  normal), todos vêm vazios.

- `repositorio._normalizar_responsavel()` trata os `NULL` das
  colunas novas — `None` vira `""` (convenção do sistema para "sem
  valor"). Mesmo padrão já aplicado a `data_desativacao` em
  produtos, propriedades e unidades.

- `modelos.Responsavel` ganha os 6 campos novos. Dataclass é
  documental — não é instanciada em runtime pelo `repositorio`,
  que trabalha sempre com dicionários.

- `gui_responsaveis._AcoesResponsavelModal()` — calcula a altura
  dinamicamente com `update_idletasks()` + `winfo_reqheight()` em
  vez de fixar em pixels. O bloco de credencial pode ter 2 ou 4
  linhas conforme o estado, portanto a altura fixa cortava conteúdo
  num dos casos (regra 11.2 do plano de correções).

- `_FormularioResponsavel` (gui_responsaveis.py) — o combo "Tipo
  de utilizador" adapta-se ao autor em três estados: sem sessão
  fica desativado; Master vê todos os perfis; Admin vê só Staff.

- `Aplicacao.__init__` (app.py) e `Aplicacao.trocar_utilizador`
  passam ambos a mostrar o Dashboard depois do login. Antes, o
  `__init__` mostrava o Dashboard mas o `trocar_utilizador` voltava
  à Gestão de Propriedades — inconsistência corrigida.

- `main_gui.py` — passa a ter um `while` que cria a `Aplicacao`,
  corre o `mainloop()`, e decide se deve reabrir (logoff) ou
  terminar (fecho normal). Necessário para o logoff verdadeiro.

- `config.VERSAO`: 1.4.0 → 1.5.0.

### Corrigido

- `responsaveis.criar()` não validava quem podia criar um Master
  ou Admin — qualquer chamada podia criar já com esse tipo. Era a
  pendência 11.4 do plano de correções, fechada nesta versão.

- `alterar_tipo_utilizador()` não impedia que um Master rebaixasse
  outro Master — a regra 3.4 ficou explicitamente implementada
  nesta versão.

### Notas

- Decisão de hash: `pbkdf2_hmac('sha256', ...)` com 100.000
  iterações. O Django usa 600.000 por omissão (contexto web, muitos
  utilizadores em paralelo). Aqui, 600.000 fazia cada login levar
  ~2 segundos — desconfortável para um sistema de secretaria de
  mesa com uso diário. 100.000 continua sólido para este contexto
  (4 utilizadores, sem exposição pública) e a autenticação fica em
  ~0,4 segundos. Se um dia migrar para web com muitos utilizadores,
  sobem-se as iterações outra vez — os hashes já gravados mantêm as
  suas iterações (estão dentro do próprio hash), só os novos usam o
  valor novo.

- Decisão de bootstrap: não há ecrã de "primeiro arranque" no
  `LoginModal`. Se a base estiver vazia ou nenhum responsável tiver
  credencial, o login recusa com a mensagem específica. O primeiro
  Master com credencial é criado por SQL direto na instalação —
  mesmo padrão do `manage.py createsuperuser` do Django.

- Decisão de permissão: `responsavel_unidade` é INFORMATIVA, não
  restritiva. Permissões são só por perfil (Master/Admin/Staff). A
  ligação responsável ↔ unidade serve para mostrar quem gere o quê
  (o balão sobre o crachá na Gestão de Responsáveis), não para
  limitar operações.

- Decisão parqueada para a Fase 3 (web): deslogar utilizador à
  distância (Master, a partir das Configurações). Em secretaria de
  mesa exigiria polling à BD ou ficheiro de sinal — mais caro do
  que o problema. O Django resolve com a tabela de sessões nativa
  (`Session.objects.filter(user_id=X).delete()`).

- Decisão parqueada para a Fase 3 (web): recuperação de password
  por email. Exige SMTP configurado, coluna `email` em
  `responsaveis` (que não existe — só há `contacto`, livre) e um
  servidor HTTP onde o link aterre. Em secretaria de mesa o reset
  por Master cobre 100% do caso real. O Django traz
  `password_reset` nativo.

- Decisão parqueada para a Fase 3 (web): tabela de auditoria de
  sessões (`sessoes_auditoria` com `ip`, `origem`, tentativas
  falhadas). Não entra na v1.5.0 — em secretaria de mesa não há
  conceito de IP nem de origem, e o Django traz rate-limit próprio.

- `esquema.sql` da raiz foi substituído pelo
  `docs/Modelo_de_dados_esquema_v.1.5.3.sql` (export `mysqldump
  -d` do Workbench). O `v.1.5.2` foi arquivado no drive pessoal do
  aluno. O ficheiro de v1.5.3 é o que serve de instalação — quem
  instalar o sistema corre este e fica com a base criada.

- Backup etiquetado da migração: `docs/dump_pre_migracao_utilizadores.sql`
  (estrutura + dados, com os 4 responsáveis e os seus valores
  originais antes das colunas de credencial). Serve de rede de
  segurança — se algo correr mal na migração, restaura-se com este
  ficheiro.


## [1.4.0] - 2026-09-17 

Estabilização da interface. As correções foram organizadas por ordem
de dependência do código, não por ecrã: primeiro a infraestrutura de
pastas, depois a base de dados e as permissões, e só então os ecrãs
que assentam em cima delas.

As pastas de trabalho do sistema saem de dentro do repositório e
passam a viver num sítio fixo fora da pasta de instalação, criado
automaticamente no arranque. É o que permite correr o sistema como
executável (PyInstaller) sem erros de permissão de escrita — um
executável pode ficar instalado numa pasta onde o utilizador não pode
escrever, e até aqui o código assumia sempre que a raiz do projeto era
escrevível.

## Adicionado

- config.DIR_BASE, config.DIR_DADOS, config.DIR_BACKUPS,
config.DIR_CONTRATOS e config.DIR_LOGS — os cinco caminhos que o
sistema usa em disco, todos derivados de um só sítio. Em Windows tenta
C:\Hostel_gestao; se não houver permissão de escrita, cai para
Path.home()/"Hostel_gestao". Deixa de haver caminhos calculados a
partir da raiz do repositório espalhados por vários módulos.

- config.garantir_diretorios() — cria a árvore de pastas se não
existir, idempotente. Chamada só nos pontos de entrada (main.py e
main_gui.py), nunca à importação do módulo: se corresse à importação,
correr os testes criava pastas reais no disco da máquina de quem os
corre.

- repositorio._ficheiro_contadores() — substitui a constante de módulo
FICHEIRO_CONTADORES. O caminho passa a ser calculado a cada chamada, a
partir de config.DIR_DADOS. Uma constante calculada uma vez à
importação ficava presa ao caminho inicial e não acompanhava o
fallback do garantir_diretorios(), se este fosse acionado. Mesmo
cuidado vale para qualquer código futuro que precise destas pastas:
ler sempre o atributo, nunca fixar o valor num nome de módulo.

- Perfis de utilizador. `responsaveis` ganhou a coluna
`tipo_utilizador` ('Master'/'Admin'/'Staff'), e com ela
`responsaveis.alterar_tipo_utilizador()` e
`sessao.tipo_utilizador_ativo()`. O perfil ficou como coluna do
próprio responsável em vez de numa tabela `utilizadores` à parte:
`responsaveis` já era o alvo de todas as chaves estrangeiras de
autoria, e separar obrigava a uma junção em cada leitura de sessão sem
acrescentar nenhum campo próprio. Continua sem credenciais —
palavra-passe e login chegam com `utilizadores.py` (v1.5.0).

- Beliches como estrutura, não como duas camas soltas. `lugares`
ganhou `posicao_beliche` e `beliche_grupo_id`, e `unidades` ganhou
`criar_beliche()` (cria o par de uma vez) e `agrupar_beliches()`
(função pura que separa uma lista de lugares em pares e avulsos). Um
beliche continua a ser dois lugares de capacidade 1 — os campos novos
só dizem qual é a cama de cima e quais duas camas são a mesma
estrutura. A Planta de Lugares desenha-os empilhados.

- Cama extra nas unidades Airbnb: `permite_cama_extra`,
`qtd_cama_extra` e `tipo_cama_extra` em `unidades`, validados por
`unidades._validar_cama_extra()`. A validação vive na camada de
negócio, não num CHECK da base — a regra depende da coluna `tipo` da
mesma linha, que um CHECK não consegue ler de forma fiável.

- Formulários de cliente por regime. "+ Novo Cliente" passa por
`_SeletorRegimeClienteModal`, dois cartões que abrem modais dedicados:
`NovoClienteMensalModal` (12 campos, só email e contacto de emergência
opcionais) e `NovoClienteAirbnbModal` (7 campos, todos obrigatórios —
só o que o boletim de alojamento exige). `clientes` ganhou
`pais_emissor_documento` e `pais_residencia`, usados apenas no regime
Airbnb.

- Rol de Lavanderia automático. Ao criar uma reserva Airbnb,
`estoque.gerar_rol_lavanderia_automatico()` calcula a roupa de cama e
banho a partir dos lugares da unidade e da cama extra, e grava a
requisição já como 'enviada' com o distintivo "Rol Lavanderia".
Bloqueado para o perfil Staff.

- `estoque.cancelar_requisicao()` — saída alternativa a partir de
"pendente", distinta de `rejeitar_requisicao` pela autoria: aqui é o
próprio autor que desiste do pedido antes de o admin o ver. Não toca
no stock, porque de uma pendente ainda não saiu nada.

- `unidades.listar_com_propriedade()` e
`unidades.rotulo_com_propriedade()` — o formato "Propriedade - Unidade
(UNI-XXX)", que várias listas repetiam à mão. Usado nas caixas de
seleção de contratos e, agora, na barra lateral do calendário.

## Alterado

- main.py e main_gui.py: garantir_diretorios() passa a ser a primeira
instrução dos dois pontos de entrada, antes de qualquer leitura ou
escrita. Na prática é o único sítio do sistema que decide que as
pastas têm de existir.

- repositorio.py: criar_backup(), limpar_backups_antigos(),
_carregar_contadores() e _gravar_contadores() passam a usar
config.DIR_BACKUPS e config.DIR_DADOS. RAIZ_PROJETO, PASTA_DADOS e
PASTA_BACKUPS removidos. _garantir_pastas() deixa de criar pastas e
delega em config.garantir_diretorios() — uma só função a decidir onde
estas pastas vivem.

- impressao.py: _caminho_do_ficheiro() grava o PDF do contrato em
config.DIR_CONTRATOS em vez de RAIZ_PROJETO/PASTA_CONTRATOS
(removida).

- As pastas backups/, contratos_gerados/, dados/ e logs/ na raiz do
repositório ficam obsoletas para o sistema em execução. Continuam fora
do controlo de versões (decisão 13), mas nada volta a escrever nelas;
os dados reais foram copiados para a localização nova antes desta
alteração entrar.

- Aceitar uma devolução passou a ser exclusivo de 'Admin' e 'Master'.
O perfil Staff vê a devolução mas não a fecha, e o ecrã diz-lhe porquê
em vez de esconder o botão. A restrição é verificada na camada de
negócio: desativar um campo na interface é conforto visual, não
segurança.

- Ecrã de Aprovação: os dois caminhos de uma requisição pendente
passaram a estar no rodapé, com o nome do que fazem — "Aprovar e
enviar" (abate stock) e "Rejeitar" (exige motivo, não toca no stock).

- O conceito de registo "incompleto" foi descartado.
`validacoes.validar_cliente()` deixou de devolver uma lista de campos
em falta: o que é obrigatório bloqueia com ValueError, e o que não
pertence ao regime nem chega a ser pedido. Com dois formulários, um
por regime, deixou de existir o estado "a meio" que a ideia original
servia. O filtro "Todos/Incompletos/Completos" saiu da lista de
clientes e do CLI. A coluna `incompleto` continua na base com outro
uso — `clientes.anonimizar` marca-a para sinalizar dados apagados por
RGPD.

- Nacionalidade passou a obrigatória nos dois regimes (antes só era
exigida fora do regime mensal). No regime mensal, telefone também.

- cli.py alinhado com os formulários por regime: `_criar_cliente()`
pergunta o regime primeiro e pede só os campos desse regime. Corrige
um erro que impedia criar qualquer cliente Airbnb pelo CLI — o ecrã
nunca pedia os dois campos de país que a validação passou a exigir.
`_atualizar_cliente()` pergunta o regime explicitamente em vez de o
deduzir, e é hoje o único sítio onde se preenchem esses dois campos
num cliente Airbnb criado antes desta versão.

- Calendário: navegar entre semanas passou de cerca de 1,5s para cerca
de 0,2s. Quatro alterações, todas medidas antes e depois. As leituras
à base passaram a uma por unidade em vez de uma por dia
(`unidades.estados_da_semana`), o que reduziu de 183 ligações ao MySQL
por semana navegada para 27. As linhas da grelha são criadas uma vez e
reutilizadas (`_criar_linha_pool`) em vez de destruídas e recriadas.
Só se reconfigura o que mudou (`_atualizar_linha`): no CustomTkinter
um `configure` redesenha o widget e os filhos, e custava o mesmo que
criar tudo de raiz. Os filtros escolhidos sobrevivem ao fecho da
janela, por regime.

- Reservas Airbnb: clicar duas vezes numa linha da lista abre o mesmo
detalhe do botão "Gerir", que passou a mostrar cliente, estadia,
check-in tardio e motivo de cancelamento. O duplo clique liga-se às
células, não à linha — em `componentes.Tabela` não existe um widget
por linha, a grelha é partilhada.

- modelos.py acompanha as colunas novas de `responsaveis`, `lugares`,
`unidades` e `clientes`.

- config.VERSAO: 1.3.0 -> 1.4.0.

## Notas

- Registo de ocorrências (logging): deliberadamente fora do âmbito
desta versão. Nada no sistema gera logs neste momento, e a intenção é
que o registo nasça integrado na regra de negócio e pensado para a
migração da Fase 3, não como captura técnica de exceções na fronteira.
A pasta config.DIR_LOGS já existe e fica reservada até essa decisão
ser retomada.

- Pendências conhecidas e aceites: `EditarClienteModal` não foi
repartido por regime e não mostra os dois campos de país (usar o CLI
para os preencher em clientes antigos); `responsaveis.criar` ainda não
valida quem pode criar um Master ou Admin; em `NovoContratoMensal` o
botão "+ Novo cliente" só fica bem posicionado depois de uma primeira
interação na caixa de seleção.

## [1.3.0] - 2026-09-13

Fase 2 — interface gráfica funcional e fecho do fluxo de stock. Com esta
versão, o sistema deixa de ser só CLI: entra a GUI completa (CustomTkinter),
com Dashboard, Calendário, Gestão de Propriedades, Clientes, Contratos e
Reservas, Responsáveis e Stock. O fluxo de stock revisto (Aprovação de
Requisições, cancelamento pelo autor, observação de receção, Rol de
Lavanderia) fica fechado. Acrescentado o IBAN da propriedade, que destranca
a impressão do contrato mensal em PDF — minuta completa com senhorio,
inquilino, renda e IBAN.

## Adicionado

- gui/ — pacote novo da interface gráfica (CustomTkinter), com o tema
em tema.py (paleta extraída do logo, preparada para modo claro e
escuro) e app.py/main_gui.py como ponto de entrada. A decisão 7
mantém-se: só a camada de apresentação fala com quem usa o sistema;
os módulos de negócio continuam sem saber que existe ecrã.

- componentes.py — tabela genérica (Tabela/Coluna) com cabeçalho e
corpo na mesma grelha (evita o desalinhamento que se arrastou por
várias tentativas em 08/09/2026, quando cabeçalho e linhas viviam em
grelhas separadas), barra lateral com secções, cabeçalho comum,
popups nativos (mostrar_erro/mostrar_sucesso/confirmar) e
helpers visuais partilhados (colocar_no_topo, centrar_sobre,
tornar_cliclavel, truncar_texto, formatar_valor).

- componentes_graficos.py — gráficos com matplotlib embutidos em
CustomTkinter. Base Grafico (Figure + canvas + tema aplicado num
sítio só) e duas subclasses: GraficoOcupacao (linhas, ocupação dos
últimos 7 dias) e GraficoRequisicoes (barras horizontais por
estado). Ficheiro próprio por causa do custo de importar o matplotlib
— quem só precisa de tabelas não o paga.

- gui_dashboard.py — ecrã de arranque. KPIs do dia, gráficos de
ocupação e requisições, alertas clicáveis (navegam para o ecrã certo)
e três ações rápidas (nova reserva, novo contrato, novo cliente).
Substitui a Gestão de Propriedades como ecrã inicial.

- gui_calendario.py — calendário em dois passos: cartões clicáveis
(Mensal/Airbnb) e popup da semana. Cada regime mede-se na sua
unidade natural (mensal em "ocupados/capacidade", Airbnb em
livre/reservado/ocupado) — uma grelha só, com as duas leituras
misturadas, obrigava a legenda a mentir num dos casos.

- gui_propriedades.py, gui_clientes.py, gui_contratos.py,
gui_unidades.py, gui_responsaveis.py, gui_est_*.py — os ecrãs
de cada módulo de negócio, todos com o mesmo padrão de lista
(tabela + botão "Gerir" por linha + popup de ações).

- gui_est_hub.py, gui_est_produtos.py, gui_est_movimentos.py,
gui_est_requisicoes.py, gui_est_devolucoes.py,
gui_est_aprovacao.py, gui_est_comum.py — o antigo gui_estoque.py
(1200 linhas, 7 classes, no limite do que dá para navegar) partido
em sete ficheiros focados. gui_est_comum.py guarda constantes e
helpers partilhados, para evitar imports cruzados entre irmãos.

- gui_relatorios.py e gui_configuracoes.py — placeholders. Existem
na barra lateral (secção "Sistema") para a estrutura do menu estar
completa desde já; o que vão fazer está no docstring de cada um.

- impressao.py — módulo puro de formatação, gera o PDF do contrato
mensal a partir de dicionários já lidos pelos módulos de negócio.
Não fala com a base de dados, não importa nenhum módulo de negócio —
fica testável com dicionários falsos. A pasta contratos_gerados/
fica na raiz, fora do controlo de versões (mesma convenção de
dados/ e backups/, decisão 13).

- sessao.py — sessão em memória: mantém o responsável ativo durante
a execução da GUI, sem login nem palavra-passe (decisão 10).
Substitui o que era pedido ecrã a ecrã no cli.py.

estoque.cancelar_requisicao(requisicao_id, responsavel_id) e o
estado novo cancelada — o autor desiste de uma requisição pendente
antes de o admin a ver, sem gerar movimento de stock (nada saiu do
armazém ainda). Só o autor, só pendentes.

estoque.confirmar_rececao_requisicao(..., observacao_rececao="") —
texto livre que o responsável escreve ao confirmar, para informar
faltas. Não mexe no stock: o admin lê depois e decide se corrige com
um movimento de ajuste.

estoque.criar_requisicao(..., origem="pedido") — distingue as
requisições normais ('pedido') das criadas pelo Rol de Lavanderia
('rol'). As duas vivem no mesmo fluxo a partir do momento em que são
enviadas; a origem só serve para o responsável perceber, na lista
dele, porque apareceu ali uma requisição que ele não pediu.

estoque.listar_movimentos(produto_id=None, tipo=None) — o ecrã de
Movimentos da GUI precisava de listar por produto e por tipo, e não
havia função pública para isso.

estoque.contar_dependencias_produto(produto_id) — a GUI precisa de
saber se o produto tem dependências antes de decidir se pede forçar,
sem falar com repositorio diretamente (decisão 7).

estoque.desativar_produto(..., forcar=False, responsavel_id=None) —
mesma proteção de propriedades.desativar e unidades.desativar,
agora aplicada aos produtos. Forçar com dependências exige
responsável validado, gravado em desativado_por_id/
data_desativacao.

contratos.avisos_encerramento(ocupacao, data_fim) — os dois sinais
de encerramento (duração abaixo do mínimo, aviso prévio
insuficiente) ficam acessíveis à interface ANTES de encerrar, sem
duplicar a regra fora do módulo de negócio.

contratos.calcular_preco_airbnb(unidade, data_inicio, data_fim) —
versão pública do cálculo, para a GUI mostrar "Preço calculado: ..."
antes de pedir o praticado e decidir se há desconto a confirmar.

contratos.detalhes_mensal/detalhes_airbnb (públicas) — antes
viviam como auxiliares privadas (_dados_mensais/_dados_airbnb) e
o cli.py mantinha réplicas funcionais suas; agora é a forma
correta de a GUI ler os dados específicos de um contrato/reserva.

unidades.taxa_ocupacao(data, tipo=None) — ocupação agregada de
todas as unidades ativas num dia, medida na unidade natural de cada
regime (Airbnb em unidades, mensal em lugares). Alimenta os KPIs do
Dashboard.

unidades.proxima_disponibilidade(unidade_id, data) — próxima
janela livre de uma unidade Airbnb, ou None se não houver ocupações
futuras. Alimenta a faixa amarela do "Detalhe do dia" no calendário.

unidades.atribuir_responsavel, unidades.remover_atribuicao e
unidades.unidades_geridas_por (tabela responsavel_unidade) — a
ligação responsável ↔ unidade não existia no modelo até esta versão;
antes, responsavel_id só aparecia em requisições, devoluções e
movimentos. Um balão sobre o crachá do ID, na Gestão de
Responsáveis, mostra as unidades geridas.

propriedades.criar(nome, morada="", iban="") e
propriedades.atualizar(..., iban=None) — o IBAN do senhorio, para
a Cláusula 3ª do contrato mensal. Opcional, guardado cru sem espaços
(formato canónico), a formatação com espaços de 4 em 4 fica na
apresentação.

validacoes.validar_iban(iban) — algoritmo do módulo 97 (ISO 13616),
o mecanismo oficial de controlo do IBAN. Confirma que o número não
tem erros de digitação; não confirma que a conta existe (mesmo tipo
de validação do nif_valido).

## Alterado

config.VERSAO: 1.2.0 → 1.3.0.

- cli.py, main.py: já não têm consumidor do dados único (a
migração MySQL ficou completa na v1.1.0, mas a estrutura em memória
ainda era usada como referência em comentários). Removido o
cli.mostrar_erro_arranque (só servia para o erro de versão que o
carregar() levantava) e, em repositorio.py,
carregar()/gravar()/_estrutura_vazia()/_migrar() e os
auxiliares de serialização (_reconstituir_tipos, _serializar,
_desserializar) — sem consumidores (grep confirmado em todo o
projeto antes da remoção).

_FormularioCliente (gui_clientes.py) — o botão "+ Novo cliente"
existe em três sítios (ListaClientes e cartões "Cliente" de
Novo Contrato Mensal e Nova Reserva Airbnb). O modal chamava sempre
self.tela_lista._recarregar() no fim; quando a tela_lista era o
contrato ou a reserva, esse método não existia e rebentava. Agora
tolera os dois casos com _recarregar_tela_lista.

NovaReservaAirbnb (gui_contratos.py) — formulário reformulado:
cartões "Unidade e cliente", "Estadia", "Check-in tardio" e resumo
final, todos dentro da área de scroll. Antes o resumo e o rodapé
ficavam presos ao fundo da janela e saíam da vista quando o
conteúdo era maior do que o espaço disponível.

_AlterarValorCalculadoModal (gui_contratos.py) — sub-confirmação
nova, aparece só quando o preço praticado fica abaixo do calculado.
Distinta do "Editar reserva" (que corrige uma reserva já criada) —
esta vive dentro do fluxo de criação.

_AcoesRequisicaoModal (gui_est_requisicoes.py) — substituído por
três modais específicos, cada um com a sua única ação:
_AcoesRequisicaoPendenteModal (só cancelar),
_ConfirmarRececaoModal (ficha do que foi enviado + observação) e
_AcoesRequisicaoFechadaModal (só reportar sobra). As ações do admin
(aprovar, rejeitar) saíram daqui e passaram para o ecrã de Aprovação.

ListaRequisicoes (gui_est_requisicoes.py) — a coluna
"Responsável e produtos" foi desdobrada em "Responsável" e
"Observações"; a lista de produtos resumida era ruído — quem quer
ver produtos abre o Gerir. Duas marcas visuais novas na coluna de
estado: chip "rol lavanderia" (quando origem == "rol") e chip
"obs. receção" (quando fechada e há observação de receção).

produtos — o desativar_produto passa a registar quem autorizou
a desativação forçada (desativado_por_id/data_desativacao), e o
reativar_produto limpa esses dois campos ao reativar.

propriedades.desativar e unidades.desativar — já existiam com
forcar/responsavel_id; sem alterações de assinatura nesta versão.

_dados_mensais/_dados_airbnb (contratos.py) — renomeadas para
detalhes_mensal/detalhes_airbnb, agora públicas.

Corrigido
clientes.anonimizar(): as colunas data_nascimento/
validade_documento continuam NOT NULL no esquema físico — o
aviso sobre o ALTER TABLE fica registado, sem correção do esquema
nesta versão (ver Notas).

impressao.py: as fontes core do fpdf2 (Times, Helvetica,
Courier) usam Latin-1 e não incluem travessão longo (—), aspas
curvas, nem reticências (…) — todos os travessões do documento
foram substituídos por hífen simples (ASCII puro), resolvendo o
ValueError: Character ... is outside the range of characters supported by the font used. Preferida esta correção mínima a
carregar um .ttf Unicode.

componentes_graficos._cor_para_matplotlib: o CORES_ESTADO
mistura pares do tema com cores de marca simples; tirar o elemento
claro com um [0] cru dava "#" para as strings, e o matplotlib
rebentava com "not a valid value for color". A função normaliza os
dois casos.

Margens e nomes cortados nos gráficos do Dashboard:
set_layout_engine("tight") do matplotlib entrava em conflito com
o tight_layout(pad=1.5) explícito — os rótulos do eixo X
("seg 7") e os nomes dos estados ("rejeitada") apareciam cortados.
Removido o set_layout_engine; o tight_layout explícito, com
pad subido de 1.2 para 1.5, é agora o único sítio a mexer nas
margens.

ListaRequisicoes._desenhar_linha (gui_est_requisicoes.py): o
bloco_estado (chip + marcas) tinha pack_propagate(False) sem
height explícita — um CTkFrame sem altura assume 200px por
omissão, e o pack_propagate(False) impede-o de encolher até ao
tamanho dos chips lá dentro. A linha inteira esticava até aos 200px,
com espaçamento vertical enorme entre requisições. Corrigido com
height=26.

ListaRequisicoes._e_o_autor e _pode_reportar_devolucao
(gui_est_requisicoes.py): os dois métodos eram chamados pelos modais
desde o primeiro dia, mas nunca tinham sido escritos. Abrir o Gerir
de uma pendente ou de uma fechada rebentava com AttributeError.

gui_est_requisicoes.py: linha 90 tinha
_tornar_clicavel = componentes.tornar_cliclavel (com um "l" a
menos). Rebentava com AttributeError no import, e isso quebrava
toda a cadeia de imports da GUI.

gui_est_aprovacao._COLUNAS_APROVACAO: a coluna ESTADO tinha
alinhamento="center" (em inglês); o _ALINHAMENTOS do
componentes.py só conhece "centro" (em português). O
componentes.Tabela rebentava com KeyError: 'center'.

Gestão de Propriedades: espaçador transparente entre a última
coluna de texto e os botões, com fill="x", expand=True e
height=1. A primeira versão, sem height, esticou cada linha
para ~200px (mesma família do bug do pack_propagate acima, mas
ao contrário: não era faltar propagate(False), era faltar
height).

"← Voltar" → "< Voltar" (gui_propriedades.py) e "Ver planta →"
→ "Abrir Mapa": o glifo Unicode da seta aparecia como um quadrado
(tofu) no Windows. < e > são ASCII puro, sem depender da fonte
ter o glifo.

gui_relatorios.py/gui_configuracoes.py na barra lateral: existe
um cartão por implementar em cada ecrã, para o utilizador perceber
que a página está vazia por decisão e não por engano.

## [1.2.0] - 2026-09-05

Fase 2 — MySQL estabilizado. Fecha os passos de estabilização definidos
depois da migração completa da v1.1.0: backups adaptados ao MySQL, decisão
formal de arquitetura (sem SQLite em paralelo), limpeza de avisos pyflakes
(com um bug real corrigido), confirmação em produção do bug de
TIPOS_DOCUMENTO, atualização dos documentos formais do projeto, e
confirmação das 5 condições de "módulo concluído" para os 8 módulos
tocados na Fase 2.

### Adicionado

- `repositorio.criar_backup()`/`limpar_backups_antigos()`: cópias de
  segurança passam a ser feitas com `mysqldump` (substituindo a cópia de
  `dados.json`, que já não existe) — `dump_AAAA-MM-DD.sql` por dia, sem
  sobrescrever a do próprio dia, password passada por variável de ambiente
  (`MYSQL_PWD`), nunca como argumento da linha de comandos.
- `repositorio.py`: docstrings adicionadas às 27 funções públicas que
  ainda não tinham (sobretudo procurar_X/listar_X/atualizar_X de quartos,
  lugares, ocupações, produtos, requisições e devoluções) — módulo passa
  a cumprir a condição 4 do checklist de módulo concluído.

### Alterado

- `Regras_versionamento.txt`: descrições das versões 1.1.0/1.2.0
  corrigidas de "SQLite" para "MySQL", refletindo a decisão de saltar a
  fase SQLite e migrar diretamente para MySQL.
- `Modelo_de_Dados_v1.5.docx`: tabela de fases sem a antiga Fase 3
  ("MySQL, evolução para PostgreSQL"); Fase 2 passa a descrever MySQL como
  decisão implementada; DDL da secção 8 substituído pelo esquema MySQL
  real (17 tabelas); PostgreSQL mantido como evolução futura possível,
  sem fase atribuída.
- Ficheiro `esquema.sql` (protótipo SQLite) removido do repositório —
  MySQL é a decisão definitiva de persistência, sem SQLite em paralelo.

### Corrigido

- `clientes.anonimizar()`: gravava o texto cru recebido como
  `responsavel_id` em `responsavel_anonimizado_id`, em vez do id canónico
  devolvido por `responsaveis.validar_autoria()` — corrigido para gravar
  sempre a forma canónica (ex.: `RES-001`, mesmo indicando `res-001`).
- `testes/apoio_BD.py`: `BaseMySQLTest.setUp`/`tearDown` ainda guardava e
  restaurava `repositorio.FICHEIRO_DADOS`, atributo já removido de
  `repositorio.py` — quebrava com `AttributeError` todos os testes que
  herdam desta classe base.
- Avisos pyflakes cosméticos: imports/constantes sem uso removidos em
  `validacoes.py`, `modelos.py`, `config.py` e `repositorio.py`
  (`VERSAO_DADOS`, `FICHEIRO_DADOS`, entre outros).

### Testes

- Confirmado em produção que o bug do TIPOS_DOCUMENTO (corrigido na
  v1.1.0) está resolvido: cliente de teste criado com "Cartão de
  Cidadão" via CLI, sem erro, confirmado por SELECT no Workbench.
- Suite completa: 521 testes, todos ok, depois de corrigido o bug em
  `apoio_BD.py`.
- Confirmadas as 5 condições de módulo concluído (importa sem erro,
  testes, PEP 8 — sem dependências externas, documentação, separação de
  camadas) para os 8 módulos da Fase 2: propriedades, unidades, clientes,
  responsaveis, contratos, estoque, validacoes, repositorio.

### Notas

O bug em `apoio_BD.py` só foi detetado ao correr a suite completa depois
de a limpeza de pyflakes anterior ter removido `FICHEIRO_DADOS` de
`repositorio.py` sem atualizar o ficheiro de apoio dos testes que ainda o
referenciava — lição para futuras limpezas: fazer grep também em
`testes/` antes de remover um atributo público de um módulo.

## [1.1.0] - 2026-09-05

Fase 2 — persistência em MySQL (substitui o SQLite previsto no plano de
versões original; decisão de pivot já registada anteriormente). Com esta
versão, todas as entidades do sistema falam diretamente com o MySQL, sem
passar por `dados`/JSON em nenhum ponto: propriedades, unidades/quartos/
lugares, clientes, responsáveis, ocupações (contratos.py) e stock
(estoque.py).

### Adicionado

- `repositorio.py`: bloco de funções por entidade para clientes,
  responsáveis, ocupações/ocupações_mensal/ocupações_airbnb e
  produtos/movimentos/requisições/itens_requisicao/devoluções/
  itens_devolucao — inserir_X/procurar_X/listar_X/atualizar_X, ligação
  nova por operação via `obter_conexao()`, `cursor(dictionary=True)`,
  commit explícito.
- `testes/apoio_bd.py` (novo): `BaseMySQLTest`, base de testes que
  provisiona automaticamente uma base de dados MySQL dedicada e separada
  da base real (`hostel_gestao_teste`), aplica o esquema completo, e
  esvazia todas as tabelas antes de cada teste — nunca toca em dados
  reais.
  - .gitignore foi incluido a regra de não subir o .env com as credenciais para acessar a BD. 

### Alterado

- `clientes.py`, `responsaveis.py`, `contratos.py`, `estoque.py`:
  reescritos sem `dados` em nenhuma função, falando só com
  `repositorio.py`.
- `cli.py`: perde o `dados` nas chamadas a estes quatro módulos e os
  `repositorio.gravar(dados)` redundantes a seguir.
- Suite de testes automáticos (`teste_clientes.py`, `teste_responsaveis.py`,
  `teste_contratos.py`, `teste_estoque.py`, `teste_propriedades.py`,
  `teste_unidades.py`) reescrita para a API sem `dados`, correndo agora
  contra MySQL real via `apoio_bd.py`. Mudança de semântica: `procurar_X`/
  `listar_X` deixam de devolver o mesmo objeto Python que `criar()`
  devolvera — `assertIs` substituído por `assertEqual` em todo o lado.

### Corrigido

- `clientes.py`: colunas `data_nascimento`/`validade_documento` estavam
  `NOT NULL` no esquema físico, impedindo `clientes.anonimizar()` de as
  limpar (RGPD, decisão 8).
- `repositorio.inserir_cliente`: gravava `""` em vez de `None` em
  `responsavel_anonimizado_id` (FK), causando `IntegrityError` 1452 ao
  criar cliente novo.
- `repositorio._normalizar_cliente`: `responsavel_anonimizado_id` nunca
  era reposto a `""` na leitura depois de gravado como `None` — todo
  cliente não anonimizado, relido do MySQL, aparecia com `None` em vez de
  `""`.
- `repositorio.inserir_propriedade`: `morada` era convertida para `None`
  quando vazia, sem normalização de volta na leitura.
- `validacoes.TIPOS_DOCUMENTO`: "Cartão Cidadão" não coincidia com o ENUM
  do esquema MySQL nem com a documentação do projeto ("Cartão de
  Cidadão") — bloqueava a criação de qualquer cliente com esse tipo de
  documento contra o MySQL real (erro 1265). Bug de maior gravidade desta
  versão.
- `estoque.criar_requisicao`: dicionário devolvido não incluía a chave
  `responsavel_rejeicao_id`, presente em `procurar_requisicao`/
  `listar_requisicoes`.

### Testes

- Suite completa: 526 testes, todos verdes, contra uma instância MySQL de
  teste dedicada. `teste_repositorio.py` e `teste_manual_cli.md` sem
  alterações.

### Notas

Os 5 bugs de persistência acima só foram detetados durante a atualização
da suite de testes para correr contra MySQL real — nenhum tinha sido
apanhado pelos testes manuais anteriores (que validavam comportamento,
não o round-trip completo de cada campo pela base de dados).

## [1.0.2] - 2026-09-02

### Corrigido

- Envio de requisições não era gravado: o `repositorio.gravar` estava
  indentado dentro do bloco `except`, a seguir a um `return`, e nunca
  chegava a correr. A baixa no stock só persistia se outra operação
  gravasse a seguir (`cli.py`, `_enviar_requisicao`).
- Baixar a renda de um contrato mensal pela interface falhava sempre
  com "O responsável é obrigatório": o ecrã de atualização não pedia o
  responsável do desconto, ao contrário do equivalente Airbnb, mas
  `contratos.atualizar_mensal` já o exigia.

### Alterado

- A validação de autoria da anonimização passou do `cli.py` para dentro
  de `clientes.anonimizar`, através de `responsaveis.validar_autoria`.
  Antes, qualquer texto não vazio era aceite como responsável se a
  função fosse chamada fora da interface. O identificador gravado passa
  a ser o devolvido pela validação, não o texto recebido.
- O alerta de stock mínimo saiu do `cli.py` para o `estoque.py`, nas
  funções `abaixo_do_minimo` e `listar_alertas_stock`. Até aqui, o
  campo `stock_minimo` era gravado e validado mas só comparado numa
  linha de listagem.
- A verificação de segundo ocupante em quarto privativo passou do
  `cli.py` para `unidades.quarto_privativo_ocupado`. Eram 55 linhas de
  lógica de domínio na camada de interação, contra a decisão 7.

### Notas

Nenhuma alteração à estrutura de dados: sem campos novos, sem migração.
As três regras movidas mantêm o comportamento exato que tinham — muda
o módulo onde vivem, para que a interface gráfica da Fase 2 as herde em
vez de as repetir.

Suite: 552 testes, com 19 novos (10 do stock mínimo, 9 do quarto
privativo).

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