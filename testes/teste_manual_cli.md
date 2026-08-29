# Testes Manuais — cli.py e main.py

## Sobre este ficheiro

Descreve, passo a passo, o que deve ser executado para validar `cli.py`
e `main.py`. A justificação de usar testes manuais em vez de `unittest`
para estes dois módulos fica no `Pseudocodigo_Modulos.docx`, secção
19.1 (decisão 7: só `cli.py`/`main.py` interagem com quem usa o
sistema) — aqui fica só o que deve ser executado.

Os grupos correm por ordem, numa única sessão contínua: cada um usa
registos criados nos grupos anteriores (uma propriedade do Grupo 2,
uma unidade do Grupo 3, um responsável do Grupo 4, um cliente do
Grupo 5, etc.). Não são casos independentes.

## Preparação

Corre isto contra uma cópia de trabalho do repositório (clone à
parte, ou com `dados/` e `backups/` esvaziados/renomeados antes de
começar) — o roteiro cria dezenas de registos reais através de
`repositorio.proximo_id()`, que grava sempre em
`dados/contadores.json`. Correr isto contra os teus dados reais deixa
esse rasto lá para sempre.

Sempre que um passo pedir uma data relativa a "hoje", usa a data do
dia em que estás a correr o teste — os resultados esperados dos
Grupos 6 e 9 dependem disso.

---

## Grupo 1 — Leitoras de base e menu genérico (10 passos)

```
ROTEIRO leitoras_e_menu_generico

PASSO 1 — arranque_mostra_menu_principal
    Caminho: cli.menu_principal(dados), com dados vindo de
    repositorio.carregar()
    RESULTADO ESPERADO: mostra "Hostel Cleaning — Menu Principal" com
    as seis opções (Propriedades, Unidades, Clientes, Responsáveis,
    Contratos e Reservas, Stock) e, na última linha, "0. Sair"
FIM PASSO

PASSO 2 — numero_fora_do_intervalo
    Entrada: "9"
    RESULTADO ESPERADO: "Escolhe um número entre 0 e 6."; o menu não
    avança
FIM PASSO

PASSO 3 — texto_nao_reconhecido
    Entrada: "abc"
    RESULTADO ESPERADO: "Opção não reconhecida — escreve o número ou
    o nome exato."; o menu não avança
FIM PASSO

PASSO 4 — escolha_por_nome_em_vez_de_numero
    Entrada: "propriedades" (minúsculas, sem acento no rótulo)
    RESULTADO ESPERADO: entra em "Gestão de Propriedades" — confirma
    que mostrar_menu aceita o rótulo por texto, sem distinguir
    maiúsculas
FIM PASSO

PASSO 5 — voltar_do_submenu
    Caminho: dentro de "Gestão de Propriedades" → "0"
    RESULTADO ESPERADO: volta a "Hostel Cleaning — Menu Principal" em
    silêncio, sem qualquer mensagem de despedida
FIM PASSO

PASSO 6 — campo_obrigatorio_em_branco
    Caminho: Propriedades → Criar → deixar "Nome" em branco (Enter)
    RESULTADO ESPERADO: "Este campo é obrigatório."; volta a pedir o
    mesmo campo, sem avançar para a morada
FIM PASSO

PASSO 7 — decimal_invalido
    Caminho: completar o passo anterior com um nome válido; Unidades
    → Criar → no preço base, escrever "abc"
    RESULTADO ESPERADO: "Introduz um valor monetário válido."; insiste
    no mesmo campo
FIM PASSO

PASSO 8 — confirmacao_nao_reconhecida
    Caminho: em qualquer ecrã com confirmar() (ex.: "Incluir
    inativas?"), responder "talvez"
    RESULTADO ESPERADO: "Responde 's' ou 'n'."; insiste na mesma
    pergunta
FIM PASSO

PASSO 9 — data_invalida
    Caminho: em qualquer ecrã com ler_data (ex.: criar contrato
    mensal), escrever "31/02/2025"
    RESULTADO ESPERADO: "Introduz uma data válida, no formato
    DD/MM/AAAA."; insiste no mesmo campo
FIM PASSO

PASSO 10 — sair_do_menu_principal
    Caminho: no Menu Principal → "0" (ou "sair", por texto)
    RESULTADO ESPERADO: "Até à próxima."; a função menu_principal
    termina
FIM PASSO

FIM ROTEIRO
```

---

## Grupo 2 — Propriedades (8 passos)

```
ROTEIRO propriedades

PASSO 1 — criar_propriedade_valida
    Caminho: Menu Principal → Propriedades → Criar
    Entrada: nome "Foz Velha", morada "Rua da Ribeira, 12"
    RESULTADO ESPERADO: "Propriedade criada: PRO-0xx — Foz Velha"
FIM PASSO

PASSO 2 — listar_mostra_a_criada
    Caminho: Propriedades → Listar → "n" (não incluir inativas)
    RESULTADO ESPERADO: mostra a propriedade do passo 1, com a morada
    numa segunda linha
FIM PASSO

PASSO 3 — atualizar_mantendo_nome_e_apagando_morada
    Caminho: Propriedades → Atualizar → ID do passo 1
    Entrada: nome em branco (Enter, mantém), morada "-" (apaga)
    RESULTADO ESPERADO: "Propriedade atualizada: PRO-0xx — Foz Velha";
    uma nova listagem já não mostra linha de morada
FIM PASSO

PASSO 4 — atualizar_id_inexistente
    Caminho: Propriedades → Atualizar
    Entrada: "PRO-999"
    RESULTADO ESPERADO: "Erro: A propriedade PRO-999 não existe."
FIM PASSO

PASSO 5 — desativar_propriedade
    Caminho: Propriedades → Desativar → ID do passo 1
    RESULTADO ESPERADO: "Propriedade desativada: PRO-0xx — Foz Velha"
FIM PASSO

PASSO 6 — desativar_ja_inativa
    Caminho: Propriedades → Desativar → mesmo ID
    RESULTADO ESPERADO: "Erro: A propriedade PRO-0xx já está inativa."
FIM PASSO

PASSO 7 — reativar_propriedade
    Caminho: Propriedades → Reativar → mesmo ID
    RESULTADO ESPERADO: "Propriedade reativada: PRO-0xx — Foz Velha"
FIM PASSO

PASSO 8 — voltar_ao_menu_principal
    Caminho: Propriedades → "0"
    RESULTADO ESPERADO: volta ao Menu Principal
FIM PASSO

FIM ROTEIRO
```

---

## Grupo 3 — Unidades, quartos e lugares (13 passos)

```
ROTEIRO unidades_quartos_lugares

PASSO 1 — criar_unidade_mensal
    Caminho: Unidades → Criar
    Entrada: ID de uma propriedade existente, tipo "mensal", preço
    base "250", preço época alta "250", multa "20", época alta ativa
    "n"
    RESULTADO ESPERADO: "Unidade criada: UNI-0xx (mensal)"
FIM PASSO

PASSO 2 — criar_com_tipo_desconhecido
    Caminho: Unidades → Criar → no campo Tipo, escrever "semanal"
    RESULTADO ESPERADO: "Valor inválido. Escolhe um de:
    mensal/airbnb."; insiste no mesmo campo
FIM PASSO

PASSO 3 — listar_filtrando_por_tipo
    Caminho: Unidades → Listar → incluir inativas "n", propriedade
    Enter (todas), tipo "airbnb"
    RESULTADO ESPERADO: mostra só unidades airbnb, mesmo que existam
    unidades mensais na estrutura de dados
FIM PASSO

PASSO 4 — atualizar_so_um_campo
    Caminho: Unidades → Atualizar → ID do passo 1
    Entrada: novo preço base "260", Enter em época alta ativa e nos
    restantes dois preços
    RESULTADO ESPERADO: "Unidade atualizada: UNI-0xx"; uma nova
    listagem mostra preço base 260,00 € e os restantes valores por
    alterar
FIM PASSO

PASSO 5 — marcar_e_remarcar_manutencao
    Caminho: Unidades → Marcar em manutenção → mesmo ID; repetir a
    mesma ação uma segunda vez
    RESULTADO ESPERADO: "Unidade UNI-0xx marcada em manutenção." na
    primeira vez; "Erro: A unidade UNI-0xx já está em manutenção." na
    segunda
FIM PASSO

PASSO 6 — desmarcar_manutencao
    Caminho: Unidades → Desmarcar manutenção → mesmo ID
    RESULTADO ESPERADO: "Unidade UNI-0xx fora de manutenção."
FIM PASSO

PASSO 7 — entrar_em_gerir_quartos
    Caminho: Unidades → Gerir quartos de uma unidade → ID do passo 1
    RESULTADO ESPERADO: entra em "Quartos da unidade UNI-0xx" com seis
    opções e "0. Voltar"
FIM PASSO

PASSO 8 — criar_quarto
    Caminho: (dentro do submenu do passo 7) → Criar quarto
    Entrada: nome "Quarto 1", privativo "s", limpeza incluída "n"
    RESULTADO ESPERADO: "Quarto criado: QRT-0xx — Quarto 1"
FIM PASSO

PASSO 9 — guarda_de_hierarquia_no_quarto
    Caminho: sair para Unidades → Criar uma SEGUNDA unidade (qualquer
    tipo, é só para este teste) → entrar em Gerir quartos dessa
    segunda unidade → tentar Atualizar quarto com o ID do quarto
    criado no passo 8 (que pertence à primeira unidade)
    RESULTADO ESPERADO: "Erro: O quarto QRT-0xx não pertence à unidade
    UNI-0yy." — confirma a guarda de hierarquia que existe só em
    cli.py, porque unidades.py por si só não a impõe
FIM PASSO

PASSO 10 — entrar_em_gerir_lugares
    Caminho: (de volta ao submenu correto, unidade do passo 1) →
    Gerir lugares de um quarto → ID do quarto do passo 8
    RESULTADO ESPERADO: entra em "Lugares do quarto QRT-0xx"
FIM PASSO

PASSO 11 — criar_lugar_com_capacidade_omissa
    Caminho: (dentro do submenu do passo 10) → Criar lugar
    Entrada: nome "Cama 1", capacidade em branco (Enter)
    RESULTADO ESPERADO: "Lugar criado: LUG-0xx — Cama 1"; uma listagem
    seguinte mostra capacidade 1
FIM PASSO

PASSO 12 — desativar_e_reativar_lugar
    Caminho: Desativar lugar → mesmo ID; Reativar lugar → mesmo ID
    RESULTADO ESPERADO: "Lugar desativado: ..." seguido de "Lugar
    reativado: ..."
FIM PASSO

PASSO 13 — voltar_tres_niveis
    Caminho: "0", "0", "0" sucessivos, a partir do submenu de lugares
    RESULTADO ESPERADO: volta a Lugares → Quartos → Unidades → Menu
    Principal, um nível de cada vez
FIM PASSO

FIM ROTEIRO
```

O passo 9 é o mais importante do grupo: verifica em execução real a
guarda de hierarquia — uma proteção que existe só em `cli.py`, porque
`unidades.procurar_quarto` não sabe em que unidade o utilizador está a
navegar.

---

## Grupo 4 — Responsáveis (7 passos)

```
ROTEIRO responsaveis

PASSO 1 — criar_responsavel
    Caminho: Responsáveis → Criar
    Entrada: nome "Ana Ferreira", contacto "912345678"
    RESULTADO ESPERADO: "Responsável criado: RES-0xx — Ana Ferreira"
FIM PASSO

PASSO 2 — listar_responsaveis
    Caminho: Responsáveis → Listar → "n"
    RESULTADO ESPERADO: mostra o responsável do passo 1, com contacto
    numa segunda linha
FIM PASSO

PASSO 3 — atualizar_id_inexistente
    Caminho: Responsáveis → Atualizar → "RES-999"
    RESULTADO ESPERADO: "Erro: O responsável RES-999 não existe."
FIM PASSO

PASSO 4 — atualizar_apagando_contacto
    Caminho: Responsáveis → Atualizar → ID do passo 1
    Entrada: nome em branco (mantém), contacto "-" (apaga)
    RESULTADO ESPERADO: "Responsável atualizado: RES-0xx — Ana
    Ferreira"
FIM PASSO

PASSO 5 — desativar_e_repetir
    Caminho: Desativar → mesmo ID; Desativar de novo o mesmo ID
    RESULTADO ESPERADO: "Responsável desativado: RES-0xx" na primeira
    vez; "Erro: O responsável RES-0xx já está inativo." na segunda
FIM PASSO

PASSO 6 — reativar
    Caminho: Reativar → mesmo ID
    RESULTADO ESPERADO: "Responsável reativado: RES-0xx"
FIM PASSO

PASSO 7 — criar_segundo_responsavel
    Caminho: Responsáveis → Criar
    Entrada: nome "Bruno Costa", contacto "913000000"
    RESULTADO ESPERADO: "Responsável criado: RES-0yy — Bruno Costa" —
    este segundo responsável é usado no Grupo 7, passo 10, para testar
    a rejeição de quem não pediu a requisição
FIM PASSO

FIM ROTEIRO
```

---

## Grupo 5 — Clientes, incluindo anonimização (10 passos)

```
ROTEIRO clientes

PASSO 1 — criar_cliente_mensal_sem_nif
    Caminho: Clientes → Criar
    Entrada: nome "João Silva", tipo de documento "Cartão de
    Cidadão", número "12345678", regime "mensal", NIF em branco
    (Enter) para ver o aviso, depois um NIF válido para completar;
    preenche TAMBÉM email, telefone, morada e nacionalidade (não
    deixes em branco — este cliente tem de ficar "completo" para os
    passos 3 e 4 funcionarem como esperado)
    RESULTADO ESPERADO: "Este campo é obrigatório." no primeiro NIF em
    branco — o regime mensal torna-o obrigatório (decisão 11);
    insiste até vir preenchido; no fim, "Cliente criado: CLI-0xx —
    João Silva" SEM a marca "[incompleto]"
FIM PASSO

PASSO 2 — criar_cliente_airbnb_incompleto
    Caminho: Clientes → Criar
    Entrada: nome, tipo de documento, número, regime "airbnb", NIF em
    branco (aceite, regime não é mensal), email/telefone/morada/
    nacionalidade/data de nascimento todos em branco; validade do
    documento = hoje + 7 dias (propositado — garante a existência de
    uma ocupação com aviso de documento, usada no Grupo 6, passo 7)
    RESULTADO ESPERADO: "Cliente criado: CLI-0yy — ... [incompleto —
    verifica os campos em falta]" — a validade do documento não entra
    no cálculo de "incompleto" (só email/telefone/morada/
    nacionalidade contam), por isso continua incompleto apesar de
    teres preenchido esse campo
FIM PASSO

PASSO 3 — listar_filtrando_incompletos
    Caminho: Clientes → Listar → incluir inativos "n", filtrar por
    completude "Incompletos"
    RESULTADO ESPERADO: mostra só o cliente do passo 2, com a marca
    "[incompleto]"
FIM PASSO

PASSO 4 — atualizar_cliente_normal
    Caminho: Clientes → Atualizar → ID do cliente do passo 1
    Entrada: alterar só o telefone, Enter nos restantes
    RESULTADO ESPERADO: "Cliente atualizado: CLI-0xx — João Silva" sem
    marca "[incompleto]"
FIM PASSO

PASSO 5 — anonimizar_cancelada
    Caminho: Clientes → Anonimizar (irreversível) → ID do cliente do
    passo 1
    Entrada: na confirmação "Confirmas a anonimização IRREVERSÍVEL...",
    responder "n"
    RESULTADO ESPERADO: mostra o aviso inicial e os dados do cliente,
    depois "Anonimização cancelada."; o cliente permanece com os
    dados intactos
FIM PASSO

PASSO 6 — anonimizar_confirmada
    Caminho: Clientes → Anonimizar (irreversível) → mesmo ID
    Entrada: confirmar "s"; ID de um responsável ativo (RES-0xx); data
    em branco (Enter, usa hoje)
    RESULTADO ESPERADO: "Cliente CLI-0xx anonimizado."
FIM PASSO

PASSO 7 — anonimizar_ja_anonimizado
    Caminho: Clientes → Anonimizar (irreversível) → mesmo ID
    RESULTADO ESPERADO: "Erro: O cliente CLI-0xx já está anonimizado."
    — sai antes de pedir confirmação ou responsável
FIM PASSO

PASSO 8 — atualizar_cliente_anonimizado
    Caminho: Clientes → Atualizar → mesmo ID
    RESULTADO ESPERADO: "Erro: O cliente CLI-0xx está anonimizado; os
    dados pessoais foram apagados e não podem ser reintroduzidos." —
    sai antes de pedir qualquer campo
FIM PASSO

PASSO 9 — desativar_e_reativar_cliente_normal
    Caminho: Desativar → ID do cliente do passo 2; Reativar → mesmo ID
    RESULTADO ESPERADO: "Cliente desativado: ..." seguido de "Cliente
    reativado: ..."
FIM PASSO

PASSO 10 — anonimizar_id_inexistente
    Caminho: Clientes → Anonimizar (irreversível) → "CLI-999"
    RESULTADO ESPERADO: "Erro: O cliente CLI-999 não existe." — sai
    antes de mostrar qualquer dado do cliente ou pedir confirmação
FIM PASSO

FIM ROTEIRO
```

Os passos 5 a 8 são o núcleo deste grupo: verificam, em execução
real, a irreversibilidade da anonimização (decisão 8, RGPD secção 6)
e a guarda contra reintroduzir dados pessoais num cliente já
anonimizado.

---

## Grupo 6 — Contratos mensais e reservas Airbnb (13 passos)

```

PASSO 1 — preparar_segundo_lugar
    Caminho: Unidades → Gerir quartos → ID do quarto do Grupo 3
    (QRT-0xx) → Gerir lugares de um quarto → Criar lugar
    Entrada: nome "Cama 2", capacidade em branco (Enter)
    RESULTADO ESPERADO: "Lugar criado: LUG-0yy — Cama 2"; a unidade
    mensal do Grupo 3 fica com 2 lugares de capacidade 1 cada
    (capacidade total 2) — sem isto, os passos 4 e 5 deste grupo
    esbarram na guarda de capacidade ao tentar um segundo contrato
    mensal na mesma unidade, porque o único lugar criado no Grupo 3
    (Passo 11) já fica ocupado pelo contrato do passo 2 abaixo
FIM PASSO

PASSO 2 — criar_contrato_mensal_valido
    Caminho: Contratos e Reservas → Criar contrato mensal
    Entrada: unidade mensal do Grupo 3 (UNI-0xx), cliente CLI-0xx
    (João Silva), data de início = HOJE, lugar em branco (usa o
    primeiro disponível — LUG-0xx, "Cama 1"), dia de vencimento em
    branco (usa o de config.py); renda praticada igual ao preço base
    mostrado; caução igual a uma renda
    RESULTADO ESPERADO: mostra "Renda calculada (preço base da
    unidade): ..." antes de pedir a renda; não pede confirmação de
    caução (dentro do teto); termina com "Contrato criado: CNT-0xx"
FIM PASSO

PASSO 3 — dia_vencimento_fora_do_intervalo
    Caminho: Criar contrato mensal → mesma unidade, cliente CLI-0xx,
    no dia de vencimento escrever "99"
    RESULTADO ESPERADO: "Erro: O dia de vencimento tem de estar entre
    1 e 28."; nenhum contrato é criado — o segundo lugar (LUG-0yy)
    continua disponível para o passo seguinte
FIM PASSO

PASSO 4 — caucao_zero_cancelada
    Caminho: Criar contrato mensal → mesma unidade, cliente CLI-0xx,
    dia de vencimento válido, caução "0"
    Entrada: na confirmação da caução, responder "n"
    RESULTADO ESPERADO: "A caução (0,00 €) é nula ou superior à renda
    praticada — confirmas?" seguido de "Criação cancelada."; nenhum
    contrato é criado — o segundo lugar continua disponível para o
    passo seguinte
FIM PASSO

PASSO 5 — caucao_zero_confirmada
    Caminho: repetir o passo 4, respondendo "s" e indicando um motivo
    RESULTADO ESPERADO: "Contrato criado: CNT-0yy" — confirma que a
    confirmação da decisão 14 chega mesmo a ser pedida; a unidade
    fica agora com os 2 lugares ocupados (capacidade esgotada)
FIM PASSO

PASSO 6 — reserva_airbnb_sem_check_in_tardio
    Caminho: Contratos e Reservas → Registar reserva Airbnb
    Entrada: unidade airbnb, cliente CLI-0yy (o do passo 2 do Grupo
    5, com validade do documento em hoje+7 dias); data de check-in =
    HOJE, data de check-out = hoje + 14 dias; check-in tardio "n";
    preço praticado
    RESULTADO ESPERADO: não pede hora de chegada nem multa; "Reserva
    registada: RSV-0xx [aviso: documento expira durante a estadia]"
    seguido de "calculado: ... praticado: ..." — o aviso só aparece
    depois de gravada, nunca antes
FIM PASSO

PASSO 7 — reserva_airbnb_com_check_in_tardio
    Caminho: Registar reserva Airbnb → check-in tardio "s"
    Entrada: hora "18:30"; multa praticada em branco (aceita a
    calculada)
    RESULTADO ESPERADO: mostra "Multa calculada (configuração da
    unidade): ..." antes de pedir a praticada; não pede motivo, por
    teres deixado o campo em branco (fica igual à calculada); termina
    com "Reserva registada: RSV-0yy"
FIM PASSO

PASSO 8 — listar_ocupacoes_com_aviso
    Caminho: Contratos e Reservas → Listar → incluir inativas "n",
    filtros de unidade/cliente/tipo em branco, aviso de documento
    "Com aviso"
    RESULTADO ESPERADO: mostra só a reserva do passo 6, com "[aviso:
    documento]" — se este passo vier vazio, confirma que o cliente do
    passo 2 do Grupo 5 ficou mesmo com validade do documento = hoje+7
    dias
FIM PASSO

PASSO 9 — atualizar_com_tipo_errado
    Caminho: Contratos e Reservas → Atualizar contrato mensal → ID de
    uma reserva Airbnb (RSV-0xx ou RSV-0yy, não mensal)
    RESULTADO ESPERADO: "Erro: A ocupação RSV-0xx não é um contrato
    mensal."
FIM PASSO

PASSO 10 — atualizar_reserva_sem_multa_a_alterar
    Caminho: Atualizar reserva Airbnb → ID da reserva do passo 6 (sem
    check-in tardio)
    RESULTADO ESPERADO: "(Esta reserva não teve check-in tardio — sem
    multa a alterar.)" — não pede multa praticada
FIM PASSO

PASSO 11 — encerrar_contrato_com_aviso
    Caminho: Encerrar contrato mensal → ID do contrato do passo 2
    Entrada: data de fim = hoje + 20 dias (pelo menos 15 dias no
    futuro, para NÃO acionar também o aviso de prévio insuficiente —
    ver nota abaixo)
    RESULTADO ESPERADO: "Contrato encerrado: CNT-0xx [duração abaixo
    do mínimo]" — só este aviso, não o de aviso prévio
FIM PASSO

PASSO 12 — cancelar_reserva
    Caminho: Cancelar reserva Airbnb → ID da reserva do passo 7
    RESULTADO ESPERADO: "Reserva cancelada: RSV-0yy"
FIM PASSO

PASSO 13 — reativar_ocupacao
    Caminho: Reativar → mesmo ID da reserva cancelada no passo 12
    RESULTADO ESPERADO: "Ocupação reativada: RSV-0yy"
FIM PASSO

FIM ROTEIRO

```

Nota sobre o passo 1: esta preparação existe por causa de um caso descoberto durante os testes — a unidade mensal do Grupo 3 nasceu com um único lugar de capacidade 1 (Grupo 3, Passo 11), e este grupo precisa de ter dois contratos mensais ativos ao mesmo tempo na mesma unidade (passos 2 e 5) para testar caução corretamente. Sem um segundo lugar, o passo 5 esbarraria na guarda de capacidade antes de chegar à confirmação da caução — um erro de planeamento do roteiro, não do código.

Nota sobre o passo 11: aviso_previo_insuficiente fica True sempre que a data de fim ficar a menos de 15 dias de hoje (config. AVISO_PREVIO_DIAS) — incluindo se a data de fim já estiver no passado. Usar hoje+20 dias garante que só a duração abaixo do mínimo (menos de config.DURACAO_MINIMA_MESES = 3 meses desde o início) aparece isolada.

---

## Grupo 6A — Confirmação de segundo ocupante em quarto privativo (7 passos)

Corre depois do Grupo 6 — reaproveita a unidade mensal UNI-0xx do
Grupo 3. Cria o seu próprio cliente, para não depender do estado de
anonimização do Grupo 5 (CLI-0xx já foi anonimizado nesse grupo).

Testa a pendência registada em `claude/Pendencias_Pos_v1.0.0.txt`:
a confirmação explícita ao atribuir um segundo ocupante a um quarto
privativo já ocupado — mesmo quando é um LUGAR DIFERENTE dentro do
mesmo quarto (decisão 17: a restrição é do quarto, não do lugar
isolado). Função testada: `_quarto_privativo_ja_ocupado` (cli.py).

```
ROTEIRO confirmacao_privativo

PASSO 1 — criar_cliente_para_este_teste
    Caminho: Clientes → Criar
    Entrada: nome "Marta Sousa", tipo de documento "Cartão de
    Cidadão", número "87654321", regime "mensal", e todos os campos
    que o regime mensal torna obrigatórios (NIF, morada, estado
    civil) — evita ficar "incompleto", sem interferir no resultado
    deste teste
    RESULTADO ESPERADO: "Cliente criado: CLI-0zz — Marta Sousa"
FIM PASSO

PASSO 2 — criar_quarto_privativo_para_este_teste
    Caminho: Unidades → Gerir quartos de uma unidade → ID da unidade
    mensal do Grupo 3 (UNI-0xx) → Criar quarto
    Entrada: nome "Quarto Confirmação", privativo "s", limpeza
    incluída "n"
    RESULTADO ESPERADO: "Quarto criado: QRT-0zz — Quarto Confirmação"
FIM PASSO

PASSO 3 — criar_dois_lugares_no_quarto
    Caminho: Gerir lugares de um quarto → ID do quarto do passo 2 →
    Criar lugar (duas vezes)
    Entrada: "Cama A", capacidade em branco; depois "Cama B",
    capacidade em branco
    RESULTADO ESPERADO: "Lugar criado: LUG-0zz — Cama A" seguido de
    "Lugar criado: LUG-0ww — Cama B"
FIM PASSO

PASSO 4 — primeiro_contrato_sem_confirmacao
    Caminho: Contratos e Reservas → Criar contrato mensal
    Entrada: unidade UNI-0xx, cliente CLI-0zz, data de início =
    HOJE, lugar = LUG-0zz (Cama A), dia de vencimento em branco,
    renda praticada = preço base mostrado, caução = uma renda
    RESULTADO ESPERADO: NÃO aparece nenhuma pergunta sobre o quarto
    ser privativo — o quarto ainda não tinha ocupante nenhum;
    termina com "Contrato criado: CNT-0zz"
FIM PASSO

PASSO 5 — segundo_contrato_lugar_diferente_recusado
    Caminho: Criar contrato mensal → mesma unidade, cliente CLI-0zz
    outra vez (tanto faz), data de início = HOJE, lugar = LUG-0ww
    (Cama B — lugar DIFERENTE do passo 4, mas no MESMO quarto
    privativo)
    Entrada: na confirmação, responder "n"
    RESULTADO ESPERADO: "O quarto deste lugar (LUG-0ww) é privativo
    e já tem um ocupante mensal ativo — confirmas um segundo
    ocupante?" seguido de "Criação cancelada."; nenhum contrato
    novo é criado — confirma que a pergunta aparece mesmo sendo um
    LUGAR diferente, porque a restrição é do quarto (decisão 17),
    não do lugar isolado
FIM PASSO

PASSO 6 — segundo_contrato_lugar_diferente_confirmado
    Caminho: repetir o passo 5, respondendo "s" desta vez
    RESULTADO ESPERADO: "Contrato criado: CNT-0ww" — o contrato é
    criado normalmente depois da confirmação; o quarto fica agora
    com os dois lugares ocupados
FIM PASSO

PASSO 7 — quarto_partilhado_nao_pede_confirmacao
    Caminho: Gerir quartos → Criar quarto na mesma unidade, com
    privativo "n"; Gerir lugares desse quarto → Criar lugar "Cama C"
    (capacidade em branco); voltar a Contratos e Reservas → Criar
    contrato mensal → mesma unidade, outro cliente, lugar = o novo
    "Cama C"
    RESULTADO ESPERADO: NÃO aparece pergunta nenhuma sobre segundo
    ocupante — o quarto não é privativo; termina normalmente com
    "Contrato criado: CNT-0vv" — confirma que a pergunta só dispara
    para quartos privativos, nunca para os partilhados
FIM PASSO

FIM ROTEIRO
```

O passo 5 é o mais importante do grupo: é o que prova que a regra é
do quarto, não do lugar — sem ele, um teste que só usasse o mesmo
lugar duas vezes deixaria passar despercebida a diferença entre as
duas leituras possíveis da decisão 17. O passo 7 é o controlo
negativo: garante que a confirmação não passou a aparecer também
para quartos partilhados, por engano.

---

## Grupo 7 — Estoque: produtos, movimentos, requisições e devoluções (18 passos)

```
ROTEIRO estoque

PASSO 1 — criar_produto_com_minimo
    Caminho: Stock → Produtos → Criar
    Entrada: nome "Toalhas", unidade de medida "unidade", stock
    mínimo "10"
    RESULTADO ESPERADO: "Produto criado: PRD-0xx — Toalhas"
FIM PASSO

PASSO 2 — criar_segundo_produto
    Caminho: Stock → Produtos → Criar
    Entrada: nome "Sabonetes", unidade de medida "unidade", stock
    mínimo "5"
    RESULTADO ESPERADO: "Produto criado: PRD-0yy — Sabonetes"
FIM PASSO

PASSO 3 — listar_produtos_sem_movimentos
    Caminho: Stock → Produtos → Listar → "n"
    RESULTADO ESPERADO: as duas linhas, ambas marcadas
    "[abaixo do mínimo]" (saldo 0 nas duas)
FIM PASSO

PASSO 4 — registar_entrada_toalhas
    Caminho: Stock → Movimentos → Registar movimento
    Entrada: produto do passo 1, tipo "entrada", quantidade "5", data
    de hoje, responsável em branco
    RESULTADO ESPERADO: "Movimento registado: MOV-0xx (entrada, 5)"
FIM PASSO

PASSO 5 — registar_entrada_sabonetes
    Caminho: Stock → Movimentos → Registar movimento
    Entrada: produto do passo 2, tipo "entrada", quantidade "20",
    data de hoje, responsável em branco
    RESULTADO ESPERADO: "Movimento registado: MOV-0yy (entrada, 20)"
FIM PASSO

PASSO 6 — ver_saldo_ainda_abaixo_do_minimo
    Caminho: Stock → Movimentos → Ver saldo de um produto → ID do
    passo 1
    RESULTADO ESPERADO: "Saldo de Toalhas (PRD-0xx): 5 unidade" —
    ainda abaixo do mínimo (10)
FIM PASSO

PASSO 7 — saldo_de_produto_inexistente
    Caminho: Ver saldo de um produto → "PRD-999"
    RESULTADO ESPERADO: "Erro: O produto PRD-999 não existe."
FIM PASSO

PASSO 8 — ajuste_sem_motivo_insiste
    Caminho: Registar movimento → tipo "ajuste" → deixar "Motivo do
    ajuste" em branco
    RESULTADO ESPERADO: "Este campo é obrigatório."; insiste no
    motivo antes de aceitar o ajuste
FIM PASSO

PASSO 9 — criar_requisicao_com_dois_itens
    Caminho: Stock → Requisições → Criar requisição
    Entrada: responsável RES-0xx (Ana Ferreira); item 1 = produto do
    passo 1, quantidade "1000" (acima do saldo, de propósito);
    responder "s" a "Adicionar outro produto?"; item 2 = produto do
    passo 2, quantidade "5"; responder "n"; data em branco
    RESULTADO ESPERADO: "Requisição criada: REQ-0xx (pendente)",
    mostrando as DUAS linhas de item (Toalhas — pedida: 1000
    enviada: 0 / Sabonetes — pedida: 5 enviada: 0) — criar_requisicao
    não valida saldo, só o envio valida (decisão 20)
FIM PASSO

PASSO 10 — enviar_tudo_falha_por_saldo_insuficiente_num_item
    Caminho: Requisições → Enviar requisição → ID do passo 9
    Entrada: enviado por RES-0yy, data em branco, responder "n" a
    "Ajustar a quantidade enviada de algum item?" (envio total)
    RESULTADO ESPERADO: "Erro: Saldo insuficiente do produto
    PRD-0xx: 5 disponível, 1000 pedido para envio." A requisição
    continua pendente — inclusive o item de Sabonetes, que tinha
    saldo de sobra, também não é enviado: é tudo ou nada (decisão
    20, sem envio parcial "automático" por item)
FIM PASSO

PASSO 11 — enviar_com_ajuste_parcial_bem_sucedido
    Caminho: Enviar requisição → mesma requisição do passo 9
    Entrada: enviado por RES-0yy, data em branco, responder "s" a
    "Ajustar a quantidade enviada de algum item?"; para Toalhas
    informar "5"; para Sabonetes deixar em branco (mantém a
    quantidade pedida, 5)
    RESULTADO ESPERADO: "Requisição enviada: REQ-0xx" com as duas
    linhas (Toalhas — pedida: 1000 enviada: 5 / Sabonetes — pedida: 5
    enviada: 5); dois movimentos de saída gerados, um por produto
FIM PASSO

PASSO 12 — confirmar_rececao_com_responsavel_errado
    Caminho: Requisições → Confirmar receção → mesma requisição,
    indicando RES-0yy (Bruno Costa) em vez de quem pediu
    RESULTADO ESPERADO: "Erro: Só o responsável que pediu
    (RES-0xx) pode confirmar a receção desta requisição."
FIM PASSO

PASSO 13 — confirmar_rececao_correta
    Caminho: Confirmar receção → mesma requisição, com RES-0xx
    RESULTADO ESPERADO: "Receção confirmada — requisição fechada:
    REQ-0xx". O fecho é automático nesta confirmação (decisão 19) —
    já não existe um passo separado de "Fechar requisição" como
    havia antes
FIM PASSO

PASSO 14 — reportar_devolucao_quantidade_zero_e_bloqueada_no_ecra
    Caminho: Requisições → Reportar sobra (devolução) → mesma
    requisição, RES-0xx, produto Toalhas, quantidade "0"
    RESULTADO ESPERADO: "O valor tem de ser pelo menos 1." — o ecrã
    insiste e nem chega a submeter ao estoque.py. Isto fecha em
    definitivo o antigo Passo 12 (o do quantidade_devolvida = 0):
    zero deixou de ser um valor aceite em qualquer camada, começando
    já no próprio ler_inteiro(minimo=1) do ecrã (decisão 19)
FIM PASSO

PASSO 15 — reportar_devolucao_com_dois_itens
    Caminho: Reportar sobra (devolução) → mesma requisição, RES-0xx;
    item 1 = Toalhas, quantidade "3", responder "s" a "Sobrou mais
    algum produto?"; item 2 = Sabonetes, quantidade "1"; responder
    "n"; data em branco
    RESULTADO ESPERADO: "Devolução registada: DEV-0xx (requisição
    REQ-0xx)" com as duas linhas de item — uma devolução só, não
    duas
FIM PASSO

PASSO 16 — devolver_produto_fora_da_requisicao_e_erro
    Caminho: Reportar sobra (devolução) → mesma requisição, RES-0xx,
    indicando um produto que não fazia parte dela (ex.: um terceiro
    produto criado à parte), quantidade "1"
    RESULTADO ESPERADO: "Erro: O produto PRD-0zz não faz parte da
    requisição REQ-0xx." Nenhuma devolução é gravada
FIM PASSO

PASSO 17 — aceitar_devolucao
    Caminho: Requisições → Aceitar devolução → DEV-0xx do passo 15,
    aceite por RES-0yy, data em branco
    RESULTADO ESPERADO: "Devolução aceite: DEV-0xx" com as duas
    linhas; saldo de Toalhas sobe 3 (0 → 3), saldo de Sabonetes sobe
    1 (15 → 16) — dois movimentos de entrada, um por produto
FIM PASSO

PASSO 18 — rejeitar_requisicao_ja_fechada
    Caminho: Requisições → Rejeitar requisição → mesma REQ-0xx (já
    fechada)
    RESULTADO ESPERADO: "Erro: A requisição REQ-0xx não está
    pendente (estado atual: fechada)."
FIM PASSO

FIM ROTEIRO

```
O passo 10 é o mais importante do grupo novo: prova que o envio é
tudo-ou-nada por requisição, mesmo tendo vários produtos — um item
sem saldo trava a requisição inteira, não só o item problemático. O
passo 14 é o que fecha definitivamente a razão de ser desta sessão
inteira: o zero, que antes só era rejeitado dentro de
devolver_requisicao, agora nem sai do ecrã.

(Deixei de fora, de propósito, o "Enviar rol de lavanderia" — é
funcionalidade nova da decisão 20 mas fica melhor como um roteiro à
parte, já que ele testa uma combinação de duas funções em vez de uma
função isolada, como todos os passos acima. Se quiser, escrevo esse
roteiro à parte também, aqui na tela.)

---

## Grupo 8 — Menu principal (5 passos)

```
ROTEIRO menu_principal

PASSO 1 — arrancar_e_ver_seis_opcoes
    Caminho: cli.menu_principal(dados)
    RESULTADO ESPERADO: mostra as seis entradas (Propriedades,
    Unidades, Clientes, Responsáveis, Contratos e Reservas, Stock) e
    "0. Sair", nesta ordem
FIM PASSO

PASSO 2 — entrar_e_voltar_de_cada_submodulo
    Caminho: para cada uma das seis opções, entrar e imediatamente
    escrever "0" (Voltar)
    RESULTADO ESPERADO: em todos os seis casos, volta ao Menu
    Principal sem qualquer mensagem
FIM PASSO

PASSO 3 — persistencia_entre_operacoes
    Caminho: criar um registo em qualquer submódulo (ex.: uma
    propriedade), voltar ao Menu Principal, entrar noutro submódulo e
    voltar de novo
    RESULTADO ESPERADO: uma nova listagem no submódulo onde o registo
    foi criado continua a mostrá-lo
FIM PASSO

PASSO 4 — sair_do_programa
    Caminho: Menu Principal → "0" (ou "sair")
    RESULTADO ESPERADO: "Até à próxima."; a função menu_principal
    devolve o controlo a quem a chamou
FIM PASSO

PASSO 5 — reabrir_e_confirmar_persistencia_em_disco
    Caminho: reiniciar o main.py (ver Grupo 9 para o roteiro completo
    de arranque) e voltar a Listar no mesmo submódulo do passo 3
    RESULTADO ESPERADO: o registo criado no passo 3 continua presente
    — confirma que a gravação já tinha acontecido em disco durante a
    sessão anterior
FIM PASSO

FIM ROTEIRO
```

---

## Grupo 9 — Arranque do sistema (main.py) (6 passos)

```
ROTEIRO arranque_main

PASSO 1 — primeira_execucao_sem_dados
    Caminho: com dados/ renomeada ou ausente (num clone limpo, por
    exemplo), correr "python src/main.py"
    RESULTADO ESPERADO: dados/ e backups/ são criadas sozinhas; sem
    erro; aparece logo o Menu Principal. Não é criada cópia de
    segurança — repositorio.criar_backup() devolve None quando ainda
    não há dados.json
FIM PASSO

PASSO 2 — arranque_normal_com_dados_existentes
    Caminho: com dados/dados.json já a existir, correr
    "python src/main.py"
    RESULTADO ESPERADO: aparece um ficheiro novo em backups/,
    dados_<data de hoje>.json; o Menu Principal aparece; os dados
    mostrados batem certo com o que lá estava gravado
FIM PASSO

PASSO 3 — segunda_execucao_no_mesmo_dia
    Caminho: correr main.py outra vez, no mesmo dia
    RESULTADO ESPERADO: não aparece uma segunda cópia — confirma em
    backups/ que continua a existir só um ficheiro com a data de hoje
FIM PASSO

PASSO 4 — limpeza_de_copias_antigas
    Caminho: criar (ou renomear) manualmente um ficheiro em backups/
    com data anterior a config.DIAS_BACKUP (30) dias antes de hoje;
    correr main.py
    RESULTADO ESPERADO: esse ficheiro desaparece depois do arranque;
    os ficheiros com menos de 30 dias continuam lá
FIM PASSO

PASSO 5 — erro_de_arranque_versao_incompativel
    Caminho: fazer uma cópia manual do dados/dados.json real; editar
    o ficheiro e mudar "versao_dados": 1 para um número maior (ex.:
    99); correr main.py
    RESULTADO ESPERADO: "Erro fatal: ..." seguido de "O sistema não
    pode continuar."; o programa termina sozinho (sys.exit(1)); o
    Menu Principal nunca aparece. Repor o ficheiro original a seguir
FIM PASSO

PASSO 6 — saida_normal
    Caminho: no Menu Principal, escolher "0" ou escrever "Sair"
    RESULTADO ESPERADO: "Até à próxima."; o programa termina sem erro
FIM PASSO

FIM ROTEIRO
```

O passo 5 é o mais importante do grupo: é o único ponto de todo o
sistema em que uma exceção é apanhada fora de um ecrã de `cli.py`
propriamente dito — testa `cli.mostrar_erro_arranque` e o `except
ValueError` de `main()`.

---

## Limitações documentadas

O teste manual não tem garantia de regressão nenhuma: nada volta a
correr automaticamente depois de uma alteração futura, ao contrário
da suite `unittest` dos outros seis módulos de negócio. Uma alteração
a uma mensagem de erro num módulo de negócio pode, em teoria, quebrar
um ecrã de `cli.py` que dependa dela, e nada apanha essa quebra
automaticamente — só se descobre repetindo o roteiro correspondente.

Não há também nenhum mecanismo que assinale quando um destes grupos
(nove numerados, mais o 6A) fica desatualizado por uma alteração ao
`cli.py` ou ao `main.py` — cabe a quem altera um ecrã notar isso e
atualizar o roteiro correspondente, como qualquer outra parte deste
documento.