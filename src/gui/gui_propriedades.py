"""Ecrã "Propriedades e Unidades": lista as propriedades (edifícios)
e, dentro de cada uma, as suas unidades — mensais e Airbnb — com o
estado de ocupação de cada unidade (calculado por unidades.estado(),
nunca guardado) e ações de criar/editar/desativar/reativar.

Escolhido pelo aluno como o ecrã seguinte à Planta de Lugares e ao
Novo Contrato Mensal, 06/09/2026. Decisões tomadas na validação por
mockup (Xvfb + CustomTkinter real, dados falsos, sem tocar no MySQL
do aluno), antes deste ficheiro:

1. Unidades mensais E Airbnb aparecem aqui (06/09/2026, ronda 4 —
   antes só mensais; Airbnb era só pelo CLI). A Airbnb não usa
   quarto/lugar (decisão 5), por isso não tem "Ver planta →" nem
   entra na Planta de Lugares — só as duas ações comuns
   (Desativar/Editar). Cada unidade Airbnb mostra "· Airbnb" a
   seguir ao nome, para se distinguir das mensais (que não ganham
   sufixo nenhum, continuam iguais a antes).

2. Além de listar, o ecrã cria e edita Propriedades e Unidades
   (mensais) diretamente aqui, em modais (CTkToplevel) — "+ Nova
   Propriedade" no rodapé, "+ Unidade"/"Editar" em cada cartão de
   propriedade, "Editar" em cada unidade. A propriedade e o tipo
   ("mensal") de uma unidade vêm sempre fixos do modal onde foram
   abertos — não se alteram depois (mesma regra de
   `unidades.atualizar`, que não deixa mudar tipo nem propriedade).

3. "Ver planta →" em cada unidade mensal chama
   `controlador.mostrar_frame(PlantaLugares, unidade_id=...)` —
   liga este ecrã à Planta de Lugares já construída. Ao contrário
   da ligação planta → Novo Contrato Mensal (que ainda não tem
   controlador/menu à volta e fica para mais à frente), este ecrã
   já nasce com um controlador, como todos os ecrãs — por isso a
   ligação já é feita.

4. Cada unidade mostra o resultado de `unidades.estado()` como uma
   etiqueta colorida: verde quando não há nenhum ocupante, amarelo
   quando parcial, vermelho quando cheia, cinza (indisponível) para
   "Em manutenção" — mesma paleta de avisos/erros já usada na
   Planta de Lugares (ver ponto 6 sobre o par verde, novo).

5. Desativar/reativar: pedido do aluno, ao ver o mockup sem forma
   de esconder um quarto fechado para obras. Cada cartão/linha
   ativa tem um botão "Desativar" discreto (texto vermelho, sem
   fundo — para não competir com "Editar"/"+ Unidade"/"Ver planta").

   Primeira versão (06/09/2026, manhã) pedia confirmação simples e
   nunca passava forcar=True — se houvesse dependências ativas, só
   mostrava o erro exato da camada de negócio e parava. O aluno
   testou no MySQL real, viu esse erro para uma unidade com 2
   ocupações ativas, e pediu para mudar: em vez de só bloquear,
   contar as dependências ativas ANTES (mesma lógica de
   `_desativar_propriedade`/`_desativar_unidade` em cli.py:
   `unidades.listar(propriedade_id=...)` e
   `contratos.listar(unidade_id=...)`) e perguntar "tem N
   dependência(s) ativa(s) — deseja mesmo desativar?" com duas
   opções — "Cancelar" ou "Forçar desativação" — em vez do popup de
   erro simples. Só quando o aluno escolhe forçar é que
   `propriedades.desativar`/`unidades.desativar` é chamado com
   forcar=True (ver `_ConfirmarForcarModal`, `_forcar_desativar_*`).
   Sem dependências ativas, continua a simples confirmação por
   popup (componentes.confirmar — terceira convenção de popup da
   GUI) antes de desativar sem forçar.

   Ainda no mesmo pedido: "para saber quem desativou forçadamente",
   `_ConfirmarForcarModal` ganhou um dropdown de Responsável
   (mesmo padrão de "Responsável do desconto" em
   gui/gui_contratos.py) — obrigatório para "Forçar desativação"
   avançar. `propriedades.desativar`/`unidades.desativar` passaram
   a aceitar `responsavel_id` e a gravá-lo (com a data) em
   `desativado_por_id`/`data_desativacao`, só quando a desativação
   é mesmo forçada com dependências ativas — nova coluna em
   propriedades/unidades (ver claude/esquema_mysql.sql, ALTER
   TABLE). cli.py também passou a pedir o responsável ao forçar,
   para as duas interfaces ficarem consistentes.

   Uma caixa "Mostrar inativos" no topo revela as propriedades/
   unidades desativadas, cada uma só com "Reativar".

6. Cor nova em gui/tema.py: VERDE_LIVRE/TEXTO_LIVRE. A Planta de
   Lugares mostra "Livre" só com texto verde sobre o fundo normal;
   aqui as quatro etiquetas de estado precisam de se parecer (são
   todas uma "pílula" colorida), por isso "livre" ganhou o mesmo
   tipo de par (fundo, texto) que amarelo/vermelho/cinza já tinham.

7. BUG reportado pelo aluno, 06/09/2026 (tarde), testando no
   Windows real dele: todos os popups deste ecrã (os 5 CTkToplevel
   — os 4 modais de criar/editar e o `_ConfirmarForcarModal`) às
   vezes abriam ESCONDIDOS atrás da janela principal, exigindo um
   clique extra para os ver. Faltava dizer ao Tk que o popup é uma
   janela "transiente" da principal e trazê-lo para a frente — o
   Xvfb usado para validar por imagem não tem gestor de janelas
   nenhum, por isso este bug nunca apareceu nos mockups. Corrigido
   com `_colocar_no_topo` (função nova, logo antes de
   `_ConfirmarForcarModal`): cada modal chama `self.transient(...)`
   e agenda
   lift()/focus_force()/grab_set() com `after(10, ...)` — o atraso
   dá tempo ao Tk para mapear a janela antes de grab_set(), que
   falha com "not viewable" se chamado logo de seguida.

8. RONDA 4 (mesmo dia, ao juntar a Airbnb a este ecrã): três pedidos
   do aluno.

   Unidades desativadas sempre no final: `_desenhar_propriedade`
   ordena a lista de unidades de cada propriedade (`sort`, estável)
   por "está inativa" — as ativas ficam pela ordem que já vinha de
   `unidades.listar`, as inativas vão sempre a seguir, nunca
   misturadas no meio.

   Criar uma unidade Airbnb aqui: `NovaUnidadeModal` ganhou um
   seletor "Tipo" (Mensal/Airbnb) antes do Nome, a substituir o
   "mensal" antes fixo — passa a escolha diretamente a
   `unidades.criar`. `EditarUnidadeModal` não ganhou seletor (tipo
   não muda ao editar — regra de `unidades.atualizar`), só corrigiu
   o rótulo para mostrar o tipo real da unidade em vez de "mensal"
   escrito à mão.

   "Época alta ativa" só faz sentido na Airbnb: fui conferir
   `contratos.py` antes de mexer e `criar_mensal` usa sempre
   `preco_base` — nunca olha para `epoca_alta_ativa`/`preco_epoca_alta`;
   quem lê os dois é só
   `contratos._preco_calculado_airbnb` (usado nas reservas
   Airbnb). Por isso marcar essa caixa com "Mensal" escolhido (ou
   trocar para "Mensal" com a caixa já marcada) desmarca-a sozinha
   e mostra "Unidade do tipo mensal não existe época alta." —
   `_ao_marcar_epoca_alta`/`_ao_mudar_tipo`, nos dois modais.
   Decisão do aluno, 06/09/2026: validado só aqui na GUI, por
   agora — `unidades.criar`/`atualizar` continuam a aceitar
   qualquer combinação (o cli.py, que já pergunta "Época alta
   ativa?" para os dois tipos, fica exatamente como estava).

9. BUSCA + FILTRO POR ESTADO + BOTÃO MANUTENÇÃO (07/09/2026) —
   itens 2/3/5 do checklist de wireframes, aprovados por mockup
   (imagem, sem código) antes de codar. O wireframe original previa
   um ecrã de escolha de regime e uma lista Airbnb à parte; decisão
   do aluno foi manter a fusão já existente neste ecrã, só
   acrescentando o que faltava dentro dele:

   - Campo de busca (nome ou ID, live enquanto se escreve) e
     dropdown "Estado" (Todos/Livre/Parcial/Ocupado/Reservado/Em
     manutenção) na barra do topo, ao lado de "Mostrar inativos".
     Filtram as UNIDADES; uma propriedade sem nenhuma unidade que
     bata certo com os filtros não é desenhada (evita mostrar
     cartões vazios de propriedade só porque o filtro escondeu
     todas as unidades lá dentro). `_cor_estado` foi desmembrada em
     `_categoria_estado` (classificação) + `_cor_estado` (cores),
     para o filtro reutilizar exatamente a mesma classificação que
     já pinta a etiqueta — nunca duas fontes de verdade para a
     mesma regra.
   - Botão "Manutenção"/"Retirar manutenção" por unidade ATIVA
     (mesmo critério de Desativar/Editar — inativa não tem estado
     calculado para alternar), ligado a
     `unidades.marcar_manutencao`/`desmarcar_manutencao` (já
     existiam no módulo de negócio, só não tinham ecrã — módulo B
     do checklist). "Manutenção" pede confirmação simples
     (`componentes.confirmar`, tira da oferta); "Retirar
     manutenção" não pede (mesma convenção de "Reativar" — repor
     não é destrutivo).

   O item 5 do checklist ("Confirmar alteração de preço") não entra
   aqui: já fechou em 06/09/2026 por decisão própria (dropdown do
   responsável vale como confirmação, sem popup à parte) — sem
   nenhuma alteração de código.

9b. 2ª RONDA DO PONTO 9 (07/09/2026, mesmo dia) — aprovado por
    mockup, a pedido do aluno depois de testar a 1ª entrega no
    PC/MySQL real dele:

    - Busca deixou de filtrar a cada tecla (ficava feio, a
      redesenhar a lista inteira a cada letra) — passa a filtrar só
      ao premir Enter dentro do campo.
    - O botão "Manutenção"/"Retirar manutenção" saiu da linha da
      lista (desalinhava "Ver planta →") e passou para dentro de
      `EditarUnidadeModal`, agindo na hora e fechando o modal a
      seguir. Uma unidade em manutenção mostra só texto simples a
      seguir ao nome ("— em manutenção", cor secundária, mesmo
      padrão do "(inativa)") — sem pílula de estado nem botão
      nenhum na linha.
    - Chip de ID a seguir ao nome, tanto da propriedade
      (`prop["id"]`) quanto de cada unidade (`uni["id"]`) — a busca
      já aceitava procurar por ID, mas o ID não aparecia em lado
      nenhum da tela. Cor nova em `gui/tema.py`: `ID_CHIP_FUNDO`
      (chip da propriedade); o chip da unidade reaproveita
      `CINZA_INDISPONIVEL`/`TEXTO_INDISPONIVEL`, já existentes.
    - Duplo clique numa linha de unidade (nome ou chip de ID) abre
      `EditarUnidadeModal` dessa unidade — atalho, sem botão novo.

10. REESTRUTURAÇÃO — "GESTÃO DE PROPRIEDADES" (07/09/2026, mesmo
    dia) — aprovado por mockup (imagem, sem código, em duas rondas),
    a pedido do aluno depois de ver o layout do ponto 9b quebrado no
    PC real dele: em vez de mais um ajuste ao ecrã fundido, decidiu
    separar propriedades e unidades em dois níveis.

    - Ecrã renomeado para "Gestão de Propriedades" (título do
      Cabecalho e item da barra lateral, ver `gui/app.py`) e passa a
      listar SÓ propriedades, em tabela simples
      (ID/Nome/Morada/ações) — as unidades deixam de aparecer aqui.
    - Ganhou busca própria (nome ou ID, mesmo padrão Enter das
      unidades) — faltava, reparado pelo aluno ao validar a 1ª
      versão do mockup. O filtro por estado sai daqui (não fazia
      sentido nas propriedades, só nas unidades) e "Mostrar
      inativos" passa a valer só para propriedades.
    - Clicar no ID da propriedade (rótulo azul-claro, cursor de
      mão) abre `UnidadesDaPropriedadeModal`: popup com cabeçalho
      "UNIDADES DA PROPRIEDADE" + nome da propriedade, e lá dentro a
      tabela de unidades (ID/Nome/Estado/Preço/ações) — no formato
      que o aluno gostou desde o primeiro mockup deste ecrã (ver
      wireframe original do checklist). Busca, filtro de estado,
      "Mostrar inativas" e "+ Nova Unidade" mudam-se todos para
      dentro deste popup (antes viviam no ecrã principal) — cada um
      age só sobre as unidades da propriedade aberta.
    - Cada linha de unidade no popup tem Desativar/Editar/Abrir — a
      1ª versão do mockup só tinha "Abrir" e o aluno pediu para
      repor os outros dois, que continuavam a fazer falta. "Abrir"
      continua a levar à Planta de Lugares e só aparece nas
      unidades mensais (Airbnb não tem planta, decisão 5); duplo
      clique no nome/ID continua a abrir Editar Unidade, mesmo
      atalho do ponto 9b. O que "Abrir" deve fazer numa unidade
      Airbnb (o aluno quer ligar isto ao cálculo de roupa de cama a
      enviar) fica para decisão futura — depende de stock, ainda por
      desenhar.
    - As duas tabelas (propriedades e unidades) passaram a desenhar
      cada coluna como um único widget com largura fixa (`width=`),
      lado a lado com `.pack(side="left")` — sem `CTkFrame`
      aninhada nenhuma a combinar nome+chip de ID como no ponto 9b.
      Resolve por construção o bug relatado pelo aluno (aquele
      `pack_propagate(False)` sem altura que criava espaços vazios
      enormes entre as linhas): sem frame nenhuma a "prender"
      altura, não há altura nenhuma para prender mal. O chip de ID
      passa a ser a própria coluna "ID" (já não fica colado ao
      nome) — por isso `ID_CHIP_FUNDO`, criado no ponto 9b, continua
      a ser usado, só que agora numa coluna própria.
    - "Planta de Lugares" sai da barra lateral (`gui/app.py`) — só
      se chega lá pelo botão "Abrir" de uma unidade mensal dentro
      do popup. O ecrã continua a existir e a funcionar exatamente
      igual (`PlantaLugares`, `gui/gui_unidades.py`); só deixou de
      ter entrada própria no menu.

11. AJUSTES DO PONTO 10, TESTADOS NO PC REAL (07/09/2026, 3ª ronda):

    - Chip de ID (propriedade e unidade) e pílula de estado
      ganharam `anchor="w"` — sem isso, o texto ficava centrado
      dentro da largura fixa da coluna, desalinhado com o
      cabeçalho da tabela (que já usava `anchor="w"`). Nome/Morada/
      Preço já estavam corretos, só o chip/pílula é que faltava.
    - Larguras das colunas Nome/Morada da tabela de propriedades
      reduzidas (200→190, 220→170) — o botão "Editar" ficava fora
      da janela (900x700, menos os 150px da barra lateral), a soma
      das larguras ficava demasiado perto do limite.
    - "Abrir" (unidade mensal, dentro do popup) renomeado para
      "Abrir Mapa" — mais claro que é a planta de lugares que abre.

12. "TABELA A SÉRIO" (07/09/2026, 4ª ronda) — aprovado por mockup,
    a pedido do aluno ("como tu farias, sendo um dev sénior"): as
    duas tabelas (propriedades e unidades) ganham disciplina de
    tabela profissional, em vez de larguras fixas escolhidas por
    tentativa e erro (o que já ia na 3ª ronda de acertos).

    - `_LARGURA_*`: uma constante por coluna, no topo do módulo —
      cabeçalho e linhas leem sempre a MESMA constante. Antes, o
      número vinha escrito duas vezes (uma no cabeçalho, outra em
      cada linha) — bastava mudar um sítio e esquecer o outro para
      desalinhar tudo outra vez.
    - `_truncar_texto`: um nome (ou morada) mais largo do que a
      coluna corta com reticências ("…"), medido a sério com
      `tkinter.font.Font.measure` — não é um número "adivinhado",
      é a largura real do texto nessa fonte. Resolve de vez o bug
      relatado ("MYSQL AIRBNB · Airbnb (inativa)—" colado à coluna
      seguinte): um nome comprido já não empurra as colunas
      seguintes, corta e para. Nota honesta: a fonte usada para
      medir (`tkinter.font.Font`) não é pixel-a-pixel idêntica à
      que o CustomTkinter usa para desenhar (`CTkFont`) — a
      diferença é cosmética (corta um caráter a mais ou a menos no
      limite), nunca causa colisão nenhuma.
    - "(inativa)" sai do texto do nome e passa para uma segunda
      linha, dentro do mesmo `CTkLabel` (`text="nome\ninativa"`,
      `justify="left"`) — sem frame nenhuma a envolver, sem
      `pack_propagate` nenhum, por isso não reintroduz o bug do
      ponto 10. Deixa de competir com "· Airbnb" na mesma linha.
    - Zebra striping subtil (`tema.LINHA_ALTERNADA`, cor nova, só
      um tom muito ligeiramente diferente do fundo) nas linhas
      ativas, alternada — as inativas ficam sempre no fundo normal,
      para não juntar dois sinais visuais de "diferente" ao mesmo
      tempo. Uma linha fina (`tema.COR_BORDA`, altura 1px) separa
      cada linha da tabela.
    - Preço alinhado à direita (`anchor="e"`, como o cabeçalho
      "PREÇO") — convenção normal para comparar valores numéricos.

13. AINDA "TABELA A SÉRIO" + "ABRIR MAPA" EM POPUP (07/09/2026, 5ª
    ronda) — aprovado por mockup: o ponto 12 ainda não "lia" como
    tabela aos olhos do aluno (colunas alinhadas, mas sem cara de
    tabela), e "Abrir Mapa" ficou aprovado para deixar de trocar o
    ecrã principal.

    - As duas tabelas (propriedades e unidades) ganham um cartão
      com borda à volta (`corner_radius=tema.RAIO_CARTAO,
      border_width=1`) e uma faixa de fundo própria no cabeçalho
      (`tema.CABECALHO_TABELA_FUNDO`, cor nova) — é isto, mais do
      que só colunas alinhadas, que faz ler como tabela a sério.
    - BUG corrigido de caminho: o `return` do ramo "unidade
      inativa" em `_desenhar_unidade` saltava a linha divisória
      dessa linha — virou `if`/`else`, os dois ramos convergem na
      mesma linha divisória no final.
    - "Abrir Mapa" passa a abrir `PlantaLugaresModal` — um popup
      novo que embrulha a `PlantaLugares` já existente
      (`gui/gui_unidades.py`, sem lhe tocar nada) e acrescenta
      "← Voltar" junto ao título, que fecha o popup e reabre
      `UnidadesDaPropriedadeModal` da mesma propriedade. Fecha
      primeiro o popup de unidades, para nunca haver dois popups
      abertos ao mesmo tempo sobre o mesmo assunto.
    - `_ControladorPontePlanta`: `PlantaLugares._abrir_contrato`
      navega para `NovoContratoMensal` chamando
      `self.controlador.mostrar_frame(...)` (clique numa cama
      livre/reservada) — sem esta ponte, isso trocaria o ecrã
      principal por trás com o popup do mapa ainda aberto por
      cima, flutuando sem sentido. A ponte fecha o popup primeiro e
      só depois repassa a chamada ao controlador verdadeiro.

14. ESPAÇO MAL DISTRIBUÍDO NAS TABELAS + "< VOLTAR" (07/09/2026, 6ª
    ronda) — depois de `app.py` passar a `resizable(True, True)`
    com 1100x700 por omissão (pedido do aluno, ver comentário em
    `Aplicacao.__init__`), as colunas de largura fixa das duas
    tabelas deixavam sobrar espaço em branco entre a Morada/Preço e
    os botões — nunca esticavam com a janela.

    - Cada linha ganha um espaçador transparente entre a última
      coluna de texto (Morada, ou Preço na tabela de unidades) e o
      frame de botões, com `.pack(side="left", fill="x",
      expand=True)`: absorve toda a folga da linha e empurra
      Desativar/Editar/Abrir Mapa para a margem direita, tal como
      "justify-content:flex-end" no mockup `tabela_moderna.html`
      (5ª ronda) já mostrava — só não estava implementado ainda.
    - BUG corrigido na mesma ronda: a primeira versão deste
      espaçador (`ctk.CTkFrame(linha, fg_color="transparent")`, sem
      `height`) esticou cada linha para ~200px de altura — um
      CTkFrame sem altura explícita assume 200px por omissão, e
      `fill="x"` só estica a largura, nunca a altura (mesma família
      do bug do `pack_propagate` do ponto 10, mas ao contrário: não
      era faltar `propagate(False)`, era faltar `height`). Corrigido
      passando
      `height=1` ao espaçador — invisível (`fg_color="transparent"`)
      e não interfere no `fill="x"`.
    - As larguras `_LARGURA_NOME_PROPRIEDADE`/`_LARGURA_MORADA`/
      `_LARGURA_NOME_UNIDADE` e a geometria dos popups NÃO mudam
      nesta ronda — uma tentativa de as aumentar (240/210/230)
      chegou a ser feita, mas cortava os botões pela margem direita
      nalgumas larguras de janela (o texto de um CTkButton também só
      respeita `width=` como mínimo, tal como o CTkLabel do ponto
      11); revertido para não arriscar isso — o espaçador sozinho já
      resolve a distribuição do espaço.
    - "< Voltar" (era "← Voltar"): o glifo Unicode da seta aparecia
      como um quadrado (tofu) no Windows do aluno — mesma família de
      bug do antigo "Ver planta →" (por isso "Abrir Mapa" já não usa
      seta nenhuma). "<" é ASCII puro, sem depender da fonte ter
      esse glifo.

15. IBAN DA PROPRIEDADE (13/09/2026) — alteração pedida para a
    impressão do contrato mensal: a Cláusula 3ª da minuta mostra o
    IBAN para onde o inquilino paga a renda. Decisão do aluno (em
    conversa): o IBAN é do SENHORIO, não do cliente — por isso vive
    na propriedade (é a propriedade que tem conta bancária própria,
    não o inquilino que lá mora).

    - `propriedades.py` ganhou `criar(nome, morada="", iban="")` e
      `atualizar(..., iban=None)`. É opcional (o aluno decidiu, para
      não rebentar com as propriedades que já existem na base sem
      IBAN) — o PDF do contrato mostra "—" quando não existir.
    - `validacoes.validar_iban` (nova) faz o algoritmo do módulo 97
      (ISO 13616) — apanha erros de digitação, não confirma que a
      conta existe (mesmo tipo de validação do `nif_valido`).
    - Guardado cru, sem espaços ("PT50000201231234567890154") — o
      formato canónico, mesma convenção das datas em ISO no
      repositório (decisão 4). A formatação com espaços de 4 em 4
      ("PT50 0002 0123 1234 5678 9015 4") é feita na apresentação
      (`_formatar_iban`, abaixo), tanto no `EditarPropriedadeModal`
      quanto — mais tarde — no PDF do contrato mensal.
    - `NovaPropriedadeModal` e `EditarPropriedadeModal` ganharam o
      campo "IBAN (opcional)", com a mesma ajuda por baixo que os
      outros campos opcionais já têm. O Editar mostra formatado (com
      espaços) para facilitar a leitura a olho, mas limpa os espaços
      antes de gravar — a base recebe sempre o cru.
    - `ALTER TABLE propriedades ADD COLUMN iban VARCHAR(34)` fica
      documentado para correr na base (ver claude/esquema_mysql.sql),
      mas o aluno combinou só o correr quando todos os ficheiros
      desta ronda estiverem entregues — para a aplicação não
      rebentar a meio.

16. CONSOLIDAÇÃO DE HELPERS EM componentes.py (13/09/2026) — os
    helpers visuais que estavam duplicados localmente passaram a
    viver só no `componentes.py`:

    - `_truncar_texto` local → `componentes.truncar_texto`. O
      parâmetro `fonte` mantém-se (a fonte é criada uma vez por
      recarregamento, não a cada linha — é a mesma otimização que
      já estava em prática).
    - `_colocar_no_topo` local → `componentes.colocar_no_topo`.
    - O resto do ficheiro não mudou.

Segue a mesma disciplina de camadas do resto da GUI (decisão 7): só
fala com `propriedades` e `unidades` — nunca com `repositorio`
diretamente.
"""

import datetime
import tkinter
import tkinter.font as tkfont
from decimal import Decimal, InvalidOperation

import customtkinter as ctk

import contratos
import propriedades
import responsaveis
import unidades
import validacoes
from . import componentes
from . import tema
from .gui_unidades import PlantaLugares

# Aliases locais para os helpers que viviam neste ficheiro e passaram
# a viver em componentes.py. Mantêm-se os nomes antigos com "_" para
# o corpo do ficheiro não ter de ser reescrito — mesma técnica já
# usada no gui_est_requisicoes.py para os helpers do gui_est_comum.
_truncar_texto = componentes.truncar_texto
_colocar_no_topo = componentes.colocar_no_topo


def _ajustar_tamanho(janela, largura=None):
    """Redimensiona `janela` ao tamanho que o seu próprio conteúdo
    já pede (`winfo_reqheight`), em vez de um "WxH" fixo escolhido
    à mão.

    Existe porque o modal de Unidade (e depois o pop-up de cama
    extra) passou por três rondas de "está a cortar/sobrepor
    conteúdo" com valores fixos (560→680→820, depois 290) — a fonte
    "Segoe UI" e a escala de ecrã do aluno rendem mais alto do que
    o que qualquer conta em pixels à mão previa, e adivinhar de novo
    só adiava o mesmo bug para o próximo campo (15/09/2026). Chamar
    sempre por último, já com todos os widgets fixos "packed" — e
    de novo sempre que um bloco de conteúdo variável (como o resumo
    da cama extra) aparece ou desaparece, porque `resizable(False,
    False)` só impede o REDIMENSIONAMENTO PELO RATO, nunca uma
    chamada a `.geometry()` feita pelo código.

    `largura` fica fixa (não pedida ao conteúdo) porque os campos
    desta aplicação usam sempre `fill="x"` — a largura não é o que
    quebra, é sempre a altura.

    Usa `tkinter.Toplevel.geometry` (a versão de base), não
    `janela.geometry`: o `CTkToplevel.geometry()` do customtkinter
    volta a multiplicar o valor recebido pela escala da janela (o
    "widget scaling"), pensado para quem escreve um tamanho à mão
    em pixels lógicos — mas `winfo_reqwidth`/`winfo_reqheight` já
    devolvem pixels reais, depois dessa escala. Passar um valor já
    escalado pela versão do customtkinter escalava-o outra vez,
    fazendo o modal crescer com espaço vazio a cada chamada em vez
    de encolher (bug visto pelo aluno em 15/09/2026, ao marcar
    "Permite cama extra" uma 2ª vez com o resumo já visível).
    """
    janela.update_idletasks()
    if largura is None:
        largura = janela.winfo_reqwidth()
    altura = janela.winfo_reqheight()
    tkinter.Toplevel.geometry(janela, f"{largura}x{altura}")


def _categoria_estado(texto_estado):
    """Classifica o texto de `unidades.estado()` numa categoria —
    "manutencao", "livre", "parcial", "ocupado" ou "reservado".

    Extraída de `_cor_estado` em 07/09/2026 para o filtro por estado
    (`ListaPropriedades`) reutilizar exatamente a mesma classificação
    que já pinta a etiqueta de cada unidade — uma só fonte de
    verdade para "o que é livre/parcial/ocupado", em vez de repetir
    a lógica no filtro.
    """
    if texto_estado == "Em manutenção":
        return "manutencao"

    if texto_estado == "Livre":
        return "livre"

    if texto_estado == "Ocupado":
        return "ocupado"

    if texto_estado == "Reservado":
        return "reservado"

    ocupados, capacidade = texto_estado.split("/")
    ocupados, capacidade = int(ocupados), int(capacidade)

    if ocupados == 0:
        return "livre"

    if ocupados >= capacidade:
        return "ocupado"

    return "parcial"


_CORES_POR_CATEGORIA = {
    "manutencao": (tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL),
    "livre": (tema.VERDE_LIVRE, tema.TEXTO_LIVRE),
    "parcial": (tema.AMARELO_AVISO, tema.TEXTO_AVISO),
    "ocupado": (tema.VERMELHO_ERRO, tema.TEXTO_ERRO),
    "reservado": (tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL),
}


def _cor_estado(texto_estado):
    """Devolve (cor_fundo, cor_texto) da etiqueta de estado de uma
    unidade, a partir do texto de `unidades.estado()`. Duas formas
    possíveis, consoante o tipo da unidade:

    - Mensal (ou "Em manutenção", comum aos dois tipos):
      "ocupados/capacidade" (ex.: "2/4").
    - Airbnb (acrescentado 06/09/2026, ao juntar as unidades Airbnb
      a este ecrã): "Livre", "Ocupado" ou "Reservado" — mesma
      paleta de "Livre"/"Ocupado"/"Reservado" já usada na Planta de
      Lugares (`gui/gui_unidades.py`, `_cores_estado`), sem o estado
      "parcial" (não existe capacidade parcial numa reserva Airbnb —
      ocupa a unidade inteira ou não ocupa nada).
    """
    return _CORES_POR_CATEGORIA[_categoria_estado(texto_estado)]


# Rótulos do dropdown "Estado" -> categoria de _categoria_estado.
# "Todos" fica de fora de propósito: ausência de chave == sem
# filtro, ver `ListaPropriedades._estado_filtro_selecionado`.
_ESTADOS_FILTRO = {
    "Livre": "livre",
    "Parcial": "parcial",
    "Ocupado": "ocupado",
    "Reservado": "reservado",
    "Em manutenção": "manutencao",
}


# Larguras fixas das colunas das duas tabelas deste ecrã (07/09/2026,
# 4ª ronda, ponto 12) — uma constante por coluna, lida tanto pelo
# cabeçalho como pelas linhas, para os dois nunca poderem desalinhar
# por um número esquecido num dos dois sítios.
_LARGURA_ID = 70
_LARGURA_NOME_PROPRIEDADE = 190
_LARGURA_MORADA = 170
_LARGURA_NOME_UNIDADE = 190
_LARGURA_ESTADO = 90
_LARGURA_PRECO = 80
# As três ações passaram para dentro de um popup, aberto por um
# único botão "Ações" (08/09/2026). A coluna encolheu de 240 para
# 100px, e esse espaço foi para o nome e para o estado. A vantagem
# maior não é o espaço: é que acrescentar uma quarta ação a uma
# unidade deixa de ser um problema de largura de coluna.
_LARGURA_ACOES = 100


# Colunas da tabela de unidades do popup. A grelha manual que aqui
# estava (uma tupla de pesos mais uma função que a aplicava ao
# cabeçalho e a cada linha) passou para `componentes.Tabela`, que faz
# o mesmo para todas as tabelas da aplicação — ver o docstring dessa
# classe para o porquê. Aqui fica só a definição, que é a parte
# específica deste ecrã.
#
# O peso distribui o espaço que sobra: NOME leva a maior fatia, ID e
# AÇÕES não crescem.
_COLUNAS_UNIDADE = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("NOME", peso=3, minimo=_LARGURA_NOME_UNIDADE),
    componentes.Coluna(
        "ESTADO", peso=1, minimo=_LARGURA_ESTADO, alinhamento="centro"
    ),
    componentes.Coluna(
        "PREÇO", peso=1, minimo=_LARGURA_PRECO, alinhamento="w", espaco=8
    ),
    componentes.Coluna("AÇÕES", minimo=_LARGURA_ACOES, alinhamento="centro"),
)

# Altura da linha. 44px chegam para as duas linhas da célula do
# nome, que é o caso mais alto (nome + "inativa"). O mesmo valor
# serve as duas tabelas, para as linhas terem o mesmo peso visual
# quando se passa de um ecrã para o outro.
_ALTURA_LINHA_UNIDADE = 44
_ALTURA_LINHA_PROPRIEDADE = 44

# Colunas da tabela de propriedades. Mesma disciplina da tabela de
# unidades: NOME e MORADA repartem o espaço que sobra, ID e AÇÕES
# não crescem.
_COLUNAS_PROPRIEDADE = (
    componentes.Coluna("ID", minimo=_LARGURA_ID + 24, espaco=8),
    componentes.Coluna("NOME", peso=3, minimo=_LARGURA_NOME_PROPRIEDADE),
    componentes.Coluna("MORADA", peso=3, minimo=_LARGURA_MORADA),
    componentes.Coluna("AÇÕES", minimo=_LARGURA_ACOES, alinhamento="centro"),
)

# Margem interna subtraída à largura da coluna antes de decidir se
# um texto precisa de reticências (`_truncar_texto`) — folga
# pequena para não cortar um texto que já cabe "à justa".
_MARGEM_TRUNCAGEM = 10


def _formatar_valor(valor):
    """Formata um Decimal para pré-preencher um campo de edição —
    sem símbolo de moeda, sempre com ponto (a leitura, em
    `_ler_decimal`, aceita ponto ou vírgula na escrita).
    """
    return f"{valor:.2f}"


def _ler_decimal(texto, nome_campo):
    """Converte o texto de um campo monetário em Decimal, aceitando
    vírgula ou ponto (mesma tolerância de gui/gui_contratos.py). Levanta
    ValueError com mensagem pronta para popup, em vez de deixar
    escapar decimal.InvalidOperation.
    """
    try:
        return Decimal(texto.strip().replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"{nome_campo} tem um valor inválido.")


def _ler_inteiro_cama_extra(texto):
    """Converte o texto do campo "Quantidade de camas extra" em int.
    Levanta ValueError com mensagem pronta para popup — a regra de
    "maior que zero" fica por conta de
    `unidades._validar_cama_extra`, aqui só se garante que é um
    número inteiro (Fase 2, v1.4.0, item (d)).
    """
    try:
        return int(texto.strip())
    except ValueError:
        raise ValueError(
            "A quantidade de cama extra tem de ser um número inteiro."
        )


def _formatar_iban(iban):
    """Formata um IBAN cru (sem espaços) com espaços de 4 em 4,
    só para apresentação — o valor gravado é sempre o cru (decisão
    do aluno, 13/09/2026).

    Exemplo: "PT50000201231234567890154" →
             "PT50 0002 0123 1234 5678 9015 4"

    Um IBAN vazio devolve "—" (mesmo texto neutro de `formatar_data`
    e `formatar_valor` para valores ausentes — mesma convenção em
    toda a aplicação).
    """
    if not iban:
        return "—"

    return " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))


class _ConfirmarForcarModal(ctk.CTkToplevel):
    """Modal de duas opções — "Cancelar" ou "Forçar desativação" —
    mostrado quando desativar uma propriedade/unidade encontra
    dependências ativas (mesma decisão do CLI:
    `_desativar_propriedade`/`_desativar_unidade` em cli.py também
    contam as dependências antes e só chamam
    `propriedades.desativar`/`unidades.desativar` com forcar=True
    depois de confirmado — nunca deixam a exceção da camada de
    negócio ser a primeira coisa que o utilizador vê).

    O dropdown de Responsável (mesmo padrão de "Responsável do
    desconto" em gui/gui_contratos.py) é obrigatório para forçar —
    `propriedades.desativar`/`unidades.desativar` exigem
    `responsavel_id` sempre que forcar=True encontra dependências
    ativas, para saber quem autorizou (decisão do aluno,
    06/09/2026). `ao_forcar(responsavel_id)` só é chamado se
    "Forçar desativação" for escolhido com um responsável
    selecionado; ao cancelar, o modal fecha-se sem fazer nada.
    """

    def __init__(self, master, mensagem, ao_forcar):
        super().__init__(master)
        self.ao_forcar = ao_forcar

        self.title("Confirmar desativação")
        self.geometry("380x300")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(master)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=mensagem,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            wraplength=330,
            justify="left",
        ).pack(padx=20, pady=(24, 14), fill="x")

        ctk.CTkLabel(
            self,
            text="Responsável que autoriza *",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)

        self.responsaveis_disponiveis = responsaveis.listar()
        nomes = ["— Nenhum —"] + [
            f"{r['id']} · {r['nome']}" for r in self.responsaveis_disponiveis
        ]
        self.combo_responsavel = componentes.Seletor(self, values=nomes)
        self.combo_responsavel.set(nomes[0])
        self.combo_responsavel.pack(fill="x", padx=20, pady=(2, 10))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Forçar desativação",
            fg_color=tema.TEXTO_ERRO,
            hover_color=tema.VERMELHO_ERRO,
            command=self._forcar,
        ).pack(side="right")

    def _responsavel_escolhido_id(self):
        indice = self.combo_responsavel.cget("values").index(
            self.combo_responsavel.get()
        )
        if indice == 0:
            return ""
        return self.responsaveis_disponiveis[indice - 1]["id"]

    def _forcar(self):
        responsavel_id = self._responsavel_escolhido_id()

        if not responsavel_id:
            componentes.mostrar_erro(
                "Escolhe o responsável que autoriza a desativação " "forçada."
            )
            return

        self.destroy()
        self.ao_forcar(responsavel_id)


class ListaPropriedades(ctk.CTkFrame):
    """Ecrã principal: lista as propriedades, em tabela simples —
    ID, nome, morada e ações (desativar/reativar, editar). As
    unidades de cada propriedade deixaram de aparecer aqui
    (07/09/2026, ver ponto 10 do docstring do módulo): clicar no ID
    de uma propriedade abre-as num popup próprio
    (`UnidadesDaPropriedadeModal`).
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Gestão de Propriedades").pack(
            fill="x"
        )

        # Botão de criação numa barra própria, logo abaixo do
        # cabeçalho e a verde — mesmo padrão de Contrato Mensal e
        # Reservas Airbnb (09/09/2026). Estava em baixo e a azul,
        # o que o deixava fora do campo de visão em listas longas
        # e sem se distinguir dos botões de ação das linhas.
        barra_criar = ctk.CTkFrame(self, fg_color="transparent")
        barra_criar.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkButton(
            barra_criar,
            text="+ Nova Propriedade",
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovaPropriedadeModal(self),
        ).pack(side="left")

        barra = ctk.CTkFrame(self, fg_color=tema.COR_FUNDO)
        barra.pack(fill="x", padx=20, pady=(0, 4))

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome ou ID… (Enter)",
            width=220,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="left")
        # Só filtra ao premir Enter (mesmo padrão do popup de
        # unidades, ponto 9b) — filtrar a cada tecla ficava feio, a
        # redesenhar a lista inteira a cada letra escrita.
        self.campo_busca.bind("<Return>", lambda evento: self._recarregar())

        self.mostrar_inativos = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativos",
            variable=self.mostrar_inativos,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="right")

        # Cartão, faixa de cabeçalho, divisórias e área com scroll
        # vinham daqui escritos à mão, em dois blocos que tinham de
        # concordar um com o outro. Agora é `componentes.Tabela`,
        # como no popup de unidades (08/09/2026).
        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_PROPRIEDADE,
            altura_linha=_ALTURA_LINHA_PROPRIEDADE,
            mensagem_vazia="Ainda não há propriedades cadastradas.",
        )
        self.tabela.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela de propriedades —
        chamada na abertura do ecrã, ao mexer em "Mostrar inativos"
        ou confirmar uma busca (Enter), e depois de qualquer
        criação/edição/desativação/reativação de propriedade.
        """
        self.tabela.limpar()

        incluir_inativas = self.mostrar_inativos.get()
        texto_busca = self.campo_busca.get().strip().lower()
        lista = propriedades.listar(incluir_inativas=incluir_inativas)

        if texto_busca:
            lista = [
                prop
                for prop in lista
                if texto_busca in f"{prop['nome']} {prop['id']}".lower()
            ]

        if not lista:
            self.tabela.mostrar_vazio(
                "Nenhuma propriedade encontrada para a busca."
                if texto_busca
                else None
            )
            return

        # Fontes reais para medir texto (`_truncar_texto`) — criadas
        # uma única vez por recarregamento, não por linha (ponto 12).
        fonte_nome = tkfont.Font(size=13)
        fonte_morada = tkfont.Font(size=12)

        for prop in lista:
            self._desenhar_propriedade(prop, fonte_nome, fonte_morada)

    # -- desenho -------------------------------------------------------

    def _desenhar_propriedade(self, prop, fonte_nome, fonte_morada):
        """Desenha uma linha da tabela para uma propriedade.

        Cada célula é um widget criado com a linha como master e
        colocado com `self.tabela.colocar`, que trata do grid, do
        alinhamento e das folgas a partir de `_COLUNAS_PROPRIEDADE`.
        A altura, as divisórias e o tom das linhas são da tabela.
        """
        inativa = not prop["ativo"]

        linha = self.tabela.nova_linha()

        rotulo_id = ctk.CTkLabel(
            linha,
            text=prop["id"],
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=_LARGURA_ID,
            anchor="w",
            cursor="hand2",
        )
        self.tabela.colocar(linha, 0, rotulo_id, esticar="w")
        # Único sítio que abre as unidades da propriedade — decisão
        # do aluno, 07/09/2026 (ponto 10): nome e morada ficam só de
        # leitura aqui, editar continua no botão "Editar" de sempre.
        rotulo_id.bind(
            "<Button-1>",
            lambda evento: UnidadesDaPropriedadeModal(self, prop),
        )

        cor_nome = tema.COR_TEXTO_SECUNDARIO if inativa else tema.COR_TEXTO
        largura_texto_nome = _LARGURA_NOME_PROPRIEDADE - _MARGEM_TRUNCAGEM
        nome = _truncar_texto(fonte_nome, prop["nome"], largura_texto_nome)
        texto_nome = f"{nome}\ninativa" if inativa else nome
        self.tabela.colocar(
            linha,
            1,
            ctk.CTkLabel(
                linha,
                text=texto_nome,
                text_color=cor_nome,
                font=ctk.CTkFont(size=13),
                width=_LARGURA_NOME_PROPRIEDADE,
                anchor="w",
                justify="left",
            ),
        )

        largura_texto_morada = _LARGURA_MORADA - _MARGEM_TRUNCAGEM
        morada = _truncar_texto(
            fonte_morada, prop["morada"] or "sem morada", largura_texto_morada
        )
        self.tabela.colocar(
            linha,
            2,
            ctk.CTkLabel(
                linha,
                text=morada,
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_MORADA,
                anchor="w",
            ),
        )

        # Um botão só, que abre o popup com as ações da
        # propriedade. Chegou a ser testado um menu de contexto com
        # a biblioteca CTkMenuBar (08/09/2026) — cantos redondos e
        # submenu "Mais" —, mas dava problemas no ecrã do aluno e foi
        # revertido. O popup fica.
        acoes = self.tabela.celula_acoes(linha, 3)
        acoes.adicionar(
            ctk.CTkButton(
                acoes,
                text="Gerir",
                width=76,
                height=26,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda: _AcoesPropriedadeModal(self, prop),
            )
        )

    # -- ações -----------------------------------------------------------

    def _desativar_propriedade(self, prop):
        ativas = unidades.listar(propriedade_id=prop["id"])

        if ativas:
            mensagem = (
                f"A propriedade {prop['nome']} tem {len(ativas)} "
                f"unidade(s) ativa(s) — deseja mesmo desativá-la?"
            )
            _ConfirmarForcarModal(
                self,
                mensagem,
                lambda responsavel_id: self._forcar_desativar_propriedade(
                    prop, responsavel_id
                ),
            )
            return

        pergunta = f"Desativar a propriedade {prop['nome']} ({prop['id']})?"
        if not componentes.confirmar(pergunta):
            return

        try:
            propriedades.desativar(prop["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Propriedade {prop['nome']} desativada.")
        self._recarregar()

    def _forcar_desativar_propriedade(self, prop, responsavel_id):
        try:
            propriedades.desativar(
                prop["id"], forcar=True, responsavel_id=responsavel_id
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Propriedade {prop['nome']} desativada.")
        self._recarregar()

    def _reativar_propriedade(self, prop):
        try:
            propriedades.reativar(prop["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Propriedade {prop['nome']} reativada.")
        self._recarregar()


class _AcoesPropriedadeModal(ctk.CTkToplevel):
    """Popup pequeno com as ações de uma propriedade.

    Gémeo do `_AcoesUnidadeModal`: o mesmo padrão nos dois ecrãs,
    para quem usa a aplicação não ter de aprender duas maneiras de
    chegar às mesmas coisas. "Ver unidades" fica aqui como ação
    principal porque, até agora, o único sítio que abria as unidades
    era o clique no crachá do ID — que continua a funcionar, mas
    ninguém adivinha que é clicável.
    """

    def __init__(self, tela_lista, prop):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.prop = prop

        self.title(f"Ações — {prop['id']}")
        self.geometry("300x230")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        self._centrar_sobre(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=prop["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=260,
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=prop["id"],
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if not prop["ativo"]:
            self._botao(
                "Reativar",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self.tela_lista._reativar_propriedade(prop),
            )
        else:
            self._botao(
                "Ver unidades",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: UnidadesDaPropriedadeModal(self.tela_lista, prop),
            )
            self._botao(
                "Editar",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EditarPropriedadeModal(self.tela_lista, prop),
            )
            self._separador()
            self._botao(
                "Desativar",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: self.tela_lista._desativar_propriedade(prop),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(10, 16))

    def _centrar_sobre(self, janela):
        """Abre por cima da janela que o chamou.

        Sem isto o Tk coloca o popup no canto superior esquerdo do
        ecrã, longe do botão que acabou de ser clicado.
        """
        janela.update_idletasks()
        x = janela.winfo_rootx() + (janela.winfo_width() - 300) // 2
        y = janela.winfo_rooty() + (janela.winfo_height() - 230) // 2
        self.geometry(f"300x230+{max(x, 0)}+{max(y, 0)}")

    def _separador(self):
        """Risco fino antes da ação destrutiva.

        Não é decoração: separa o que se pode desfazer do que não se
        desfaz, e dá uma pausa antes do último botão.
        """
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, text_color, hover_color, acao):
        """Botão de ação: fecha este popup antes de agir.

        A ordem importa. `_desativar_propriedade` faz `_recarregar`
        na tabela por trás, e "Ver unidades" abre outro popup —
        deixar este aberto por cima deixava-o pendurado sobre coisas
        que entretanto mudaram.
        """

        def executar():
            self.destroy()
            acao()

        # Os três botões partilham forma, altura e contorno; só a
        # cor do texto muda. Num menu de opções nenhuma delas é mais
        # importante do que as outras — antes havia um azul cheio,
        # um com contorno e um solto sem nada, e a diferença de peso
        # visual dizia uma coisa que não era verdade (08/09/2026).
        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)


class UnidadesDaPropriedadeModal(ctk.CTkToplevel):
    """Popup com as unidades de UMA propriedade — mensais e Airbnb —,
    aberto ao clicar no ID da propriedade na tabela de
    `ListaPropriedades` (07/09/2026, ver ponto 10 do docstring do
    módulo: as unidades deixaram de aparecer no ecrã principal,
    passam a viver só aqui dentro, no formato de tabela que o aluno
    gostou desde o primeiro mockup deste ecrã).

    Busca, filtro de estado, "Mostrar inativas" e "+ Nova Unidade"
    (antes no ecrã principal) mudaram-se todos para aqui — agem só
    sobre as unidades desta propriedade. `NovaUnidadeModal` e
    `EditarUnidadeModal` não mudaram nada: já recebiam `tela_lista` e
    só chamam `tela_lista._recarregar()` no final, por isso aceitam
    este popup como `tela_lista` sem precisar de saber que já não é
    `ListaPropriedades`.
    """

    def __init__(self, tela_lista, prop):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.controlador = tela_lista.controlador
        self.prop = prop

        self.title(f"Unidades da Propriedade — {prop['nome']}")
        # 780x580 -> 900x620 (08/09/2026): a linha de uma unidade
        # mensal ativa precisa de 718px e a largura útil andava nos
        # 715. Com escala de 125% no Windows, "Editar" e "Abrir
        # Mapa" ficavam fora da janela e parecia que o mapa tinha
        # desaparecido.
        self.geometry("900x620")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="UNIDADES DA PROPRIEDADE",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 0))
        ctk.CTkLabel(
            self,
            text=prop["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=20)

        self.campo_busca = ctk.CTkEntry(
            barra,
            placeholder_text="Procurar por nome ou ID… (Enter)",
            width=200,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.campo_busca.pack(side="left")
        self.campo_busca.bind("<Return>", lambda evento: self._recarregar())

        self.combo_estado = componentes.Seletor(
            barra,
            values=["Todos"] + list(_ESTADOS_FILTRO),
            command=lambda _valor: self._recarregar(),
            width=140,
        )
        self.combo_estado.set("Todos")
        self.combo_estado.pack(side="left", padx=(8, 0))

        self.mostrar_inativas = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            barra,
            text="Mostrar inativas",
            variable=self.mostrar_inativas,
            command=self._recarregar,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            barra,
            text="+ Nova Unidade",
            width=120,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.VERDE,
            hover_color=tema.VERDE,
            command=lambda: NovaUnidadeModal(self, self.prop),
        ).pack(side="right")

        # Cartão, faixa de cabeçalho, divisória e área com scroll
        # vinham daqui escritos à mão, em dois blocos que tinham de
        # concordar um com o outro. Agora é `componentes.Tabela`, com
        # a definição das colunas num sítio só (08/09/2026).
        self.tabela = componentes.Tabela(
            self,
            colunas=_COLUNAS_UNIDADE,
            altura_linha=_ALTURA_LINHA_UNIDADE,
            mensagem_vazia="Sem unidades.",
        )
        self.tabela.pack(fill="both", expand=True, padx=16, pady=(10, 16))

        self._recarregar()

    # -- carregamento / atualização ----------------------------------

    def _estado_filtro_selecionado(self):
        """Categoria escolhida no dropdown "Estado", ou None quando
        é "Todos" (ausência de filtro — ver `_ESTADOS_FILTRO`).
        """
        return _ESTADOS_FILTRO.get(self.combo_estado.get())

    def _recarregar(self):
        """Limpa e volta a desenhar a tabela de unidades desta
        propriedade — chamada na abertura do popup, ao mexer em
        "Mostrar inativas"/busca/filtro de estado, e depois de
        qualquer criação/edição/desativação/reativação/manutenção.
        """
        self.tabela.limpar()

        incluir_inativas = self.mostrar_inativas.get()
        texto_busca = self.campo_busca.get().strip().lower()
        estado_filtro = self._estado_filtro_selecionado()

        lista = unidades.listar(
            incluir_inativas=incluir_inativas,
            propriedade_id=self.prop["id"],
        )
        # Ativas primeiro, inativas sempre no final (pedido do aluno,
        # 06/09/2026) — sort() é estável, mantém a ordem devolvida
        # por unidades.listar() dentro de cada grupo.
        lista.sort(key=lambda u: not u["ativo"])

        # Estado calculado uma única vez por unidade ativa — serve
        # tanto para o filtro quanto para a etiqueta desenhada em
        # `_desenhar_unidade`.
        estados_por_unidade = {
            uni["id"]: unidades.estado(uni["id"], datetime.date.today())
            for uni in lista
            if uni["ativo"]
        }

        visiveis = [
            uni
            for uni in lista
            if self._unidade_passa_filtros(
                uni,
                texto_busca,
                estado_filtro,
                estados_por_unidade.get(uni["id"]),
            )
        ]

        if not visiveis:
            self.tabela.mostrar_vazio(
                None
                if not lista
                else "Nenhuma unidade encontrada para os filtros aplicados."
            )
            return

        # Fonte real para medir texto (`_truncar_texto`) — criada uma
        # única vez por recarregamento, não por linha (ponto 12).
        fonte_nome = tkfont.Font(size=13)

        # O tom alternado deixou de ser contado aqui: é a própria
        # `componentes.Tabela` que o faz. Muda um pormenor — antes só
        # as unidades ativas entravam na contagem e as inativas
        # ficavam sempre sem tom; agora alternam como as outras.
        for uni in visiveis:
            self._desenhar_unidade(
                uni, estados_por_unidade.get(uni["id"]), fonte_nome
            )

    def _unidade_passa_filtros(
        self, uni, texto_busca, estado_filtro, estado_texto
    ):
        """True quando a unidade sobrevive à busca de texto e ao
        filtro de estado atuais. Unidades inativas não têm estado
        calculado (`estado_texto` vem None para elas) — por isso um
        filtro de estado escolhido as exclui sempre; a busca de
        texto continua a aplicar-se-lhes na mesma.
        """
        if texto_busca:
            alvo = f"{uni['nome']} {uni['id']}".lower()
            if texto_busca not in alvo:
                return False

        if estado_filtro is not None:
            if estado_texto is None:
                return False

            if _categoria_estado(estado_texto) != estado_filtro:
                return False

        return True

    # -- desenho -------------------------------------------------------

    def _desenhar_unidade(self, uni, estado_texto, fonte_nome):
        """Desenha uma linha da tabela.

        Cada célula é um widget criado com a linha como master e
        colocado com `self.tabela.colocar`, que trata do grid, do
        alinhamento e das folgas a partir de `_COLUNAS_UNIDADE`. O
        zebra striping, a altura e a divisória são da tabela.
        """
        inativa = not uni["ativo"]
        em_manutencao = uni["em_manutencao"]

        linha = self.tabela.nova_linha()

        rotulo_id = ctk.CTkLabel(
            linha,
            text=uni["id"],
            text_color=tema.TEXTO_INDISPONIVEL,
            fg_color=tema.CINZA_INDISPONIVEL,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=_LARGURA_ID,
            anchor="w",
        )
        self.tabela.colocar(linha, 0, rotulo_id, esticar="w")

        # Etiqueta de tipo só aparece na Airbnb — as unidades mensais
        # continuam sem sufixo nenhum (06/09/2026). "— em manutenção"
        # continua a seguir ao nome, na mesma linha (mesmo padrão do
        # ponto 9b); "(inativa)" passa a 2ª linha da célula, sem
        # competir com "· Airbnb" no mesmo texto (ponto 12).
        etiqueta_tipo = "" if uni["tipo"] == "mensal" else "  · Airbnb"
        sufixo = "  — em manutenção" if (em_manutencao and not inativa) else ""
        largura_texto_nome = _LARGURA_NOME_UNIDADE - _MARGEM_TRUNCAGEM
        texto_bruto = uni["nome"] + etiqueta_tipo + sufixo
        nome_base = _truncar_texto(fonte_nome, texto_bruto, largura_texto_nome)
        texto_nome = f"{nome_base}\ninativa" if inativa else nome_base
        cor_nome = (
            tema.COR_TEXTO
            if not (inativa or em_manutencao)
            else tema.COR_TEXTO_SECUNDARIO
        )
        rotulo_nome = ctk.CTkLabel(
            linha,
            text=texto_nome,
            text_color=cor_nome,
            font=ctk.CTkFont(size=13),
            width=_LARGURA_NOME_UNIDADE,
            anchor="w",
            justify="left",
        )
        self.tabela.colocar(linha, 1, rotulo_nome)

        # Duplo clique no nome/ID abre "Editar Unidade" — mesmo
        # atalho do ponto 9b, agora dentro do popup. Cada widget tem
        # de ser ligado à parte: um clique num widget-filho não
        # chega ao binding do pai, no Tkinter.
        for widget in (rotulo_id, rotulo_nome):
            widget.bind(
                "<Double-Button-1>",
                lambda evento: EditarUnidadeModal(self, uni, self.prop),
            )

        # Sem pílula quando inativa/em manutenção — "—" no lugar,
        # mesma largura para a coluna Preço continuar alinhada.
        if inativa or em_manutencao or estado_texto is None:
            etiqueta_estado = ctk.CTkLabel(
                linha,
                text="—",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=11),
                width=_LARGURA_ESTADO,
                anchor="w",
            )
        else:
            fundo, texto = _cor_estado(estado_texto)
            etiqueta_estado = ctk.CTkLabel(
                linha,
                text=estado_texto,
                text_color=texto,
                fg_color=fundo,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=_LARGURA_ESTADO,
                height=22,
                anchor="w",
            )

        self.tabela.colocar(linha, 2, etiqueta_estado)

        self.tabela.colocar(
            linha,
            3,
            ctk.CTkLabel(
                linha,
                text=f"{uni['preco_base']:.2f} €",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
                width=_LARGURA_PRECO,
                anchor="w",
            ),
        )

        # Um botão só, que abre o popup com as ações da unidade. As
        # três que aqui estavam lado a lado obrigavam a coluna a ter
        # 240px e voltavam a rebentar sempre que se juntava mais uma.
        #
        # "Gerir" e não "Ações": o título da coluna já diz o que a
        # coluna é, o botão deve dizer o que faz. Com a mesma
        # palavra nos dois, lia-se "AÇÕES / Ações" na vertical.
        acoes = self.tabela.celula_acoes(linha, 4)
        acoes.adicionar(
            ctk.CTkButton(
                acoes,
                text="Gerir",
                width=76,
                height=24,
                corner_radius=tema.RAIO_BOTAO,
                fg_color="transparent",
                border_width=1,
                border_color=tema.COR_BORDA,
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                command=lambda: _AcoesUnidadeModal(self, uni),
            )
        )

        # A divisória entre linhas passou a ser desenhada pela
        # própria `componentes.Tabela`, em `nova_linha`.

    # -- ações -----------------------------------------------------------

    def _abrir_planta(self, unidade_id):
        # Fecha o popup de unidades e abre a Planta de Lugares como
        # popup próprio (07/09/2026, 5ª ronda, ver ponto 13 do
        # docstring do módulo) — antes trocava o ecrã principal por
        # trás da barra lateral, escondendo de vez as unidades da
        # propriedade. Guarda as referências ANTES de destruir: o
        # próprio widget continua acessível depois do destroy() (só
        # o Tk é desfeito, os atributos Python ficam), mas é mais
        # claro assim.
        tela_lista = self.tela_lista
        prop = self.prop
        self.destroy()
        PlantaLugaresModal(tela_lista, prop, unidade_id)

    def _desativar_unidade(self, uni):
        ativas = contratos.listar(unidade_id=uni["id"])

        if ativas:
            mensagem = (
                f"A unidade {uni['nome']} tem {len(ativas)} "
                f"ocupação(ões) ativa(s) — deseja mesmo desativá-la?"
            )
            _ConfirmarForcarModal(
                self,
                mensagem,
                lambda responsavel_id: self._forcar_desativar_unidade(
                    uni, responsavel_id
                ),
            )
            return

        pergunta = f"Desativar a unidade {uni['nome']} ({uni['id']})?"
        if not componentes.confirmar(pergunta):
            return

        try:
            unidades.desativar(uni["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Unidade {uni['nome']} desativada.")
        self._recarregar()

    def _forcar_desativar_unidade(self, uni, responsavel_id):
        try:
            unidades.desativar(
                uni["id"], forcar=True, responsavel_id=responsavel_id
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Unidade {uni['nome']} desativada.")
        self._recarregar()

    def _reativar_unidade(self, uni):
        try:
            unidades.reativar(uni["id"])
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Unidade {uni['nome']} reativada.")
        self._recarregar()


class _AcoesUnidadeModal(ctk.CTkToplevel):
    """Popup pequeno com as ações de uma unidade.

    Substitui os três botões que estavam lado a lado na linha da
    tabela (08/09/2026). Motivo: a coluna precisava de 240px fixos
    para os acomodar, e cada ação nova era outra vez uma discussão
    de largura de coluna — o "Abrir Mapa" chegou a ficar espremido
    num círculo de 24px por causa disso. Com o popup, a linha fica
    com um botão de 76px e as ações deixam de competir com o resto
    da tabela pelo espaço.

    As ações disponíveis dependem do estado da unidade, tal como
    antes: uma unidade inativa só oferece "Reativar", e "Abrir Mapa"
    aparece nos dois regimes — desde a Fase 4 (16/09/2026), a Airbnb
    também tem quartos e lugares, que representam as camas físicas
    da unidade; é essa estrutura que o Rol de Lavanderia usa para
    contar a roupa."
    """

    def __init__(self, tela_unidades, uni):
        super().__init__(tela_unidades)
        self.tela_unidades = tela_unidades
        self.uni = uni

        self.title(f"Ações — {uni['id']}")
        self.geometry("300x230")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_unidades)
        self._centrar_sobre(tela_unidades)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=uni["nome"],
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=uni["id"],
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 14))

        if not uni["ativo"]:
            self._botao(
                "Reativar",
                text_color=tema.TEXTO_LIVRE,
                hover_color=tema.VERDE_LIVRE,
                acao=lambda: self.tela_unidades._reativar_unidade(uni),
            )
        else:
            # FASE 4 (16/09/2026) — "Abrir Mapa" passa a aparecer nos
            # dois tipos. Antes só aparecia em unidades mensais
            # (as Airbnb não tinham lugares). Agora as Airbnb também
            # têm quartos e lugares (que representam as camas
            # físicas), porque o Rol de Lavanderia precisa dessa
            # estrutura para contar a roupa.
            self._botao(
                "Abrir Mapa",
                text_color=tema.AZUL_PRINCIPAL,
                hover_color=tema.ID_CHIP_FUNDO,
                acao=lambda: self.tela_unidades._abrir_planta(uni["id"]),
            )

            self._botao(
                "Editar",
                text_color=tema.COR_TEXTO,
                hover_color=tema.COR_BORDA,
                acao=lambda: EditarUnidadeModal(
                    self.tela_unidades, uni, self.tela_unidades.prop
                ),
            )
            self._separador()
            self._botao(
                "Desativar",
                text_color=tema.TEXTO_ERRO,
                hover_color=tema.VERMELHO_ERRO,
                acao=lambda: self.tela_unidades._desativar_unidade(uni),
            )

        ctk.CTkButton(
            self,
            text="Fechar",
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(fill="x", padx=20, pady=(10, 16))

    def _centrar_sobre(self, janela):
        """Abre por cima da janela que o chamou.

        Sem isto o Tk coloca o popup no canto superior esquerdo do
        ecrã, longe do botão que acabou de ser clicado.
        """
        janela.update_idletasks()
        x = janela.winfo_rootx() + (janela.winfo_width() - 300) // 2
        y = janela.winfo_rooty() + (janela.winfo_height() - 230) // 2
        self.geometry(f"300x230+{max(x, 0)}+{max(y, 0)}")

    def _separador(self):
        """Risco fino antes da ação destrutiva.

        Não é decoração: separa o que se pode desfazer do que não se
        desfaz, e dá uma pausa antes do último botão.
        """
        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(8, 5)
        )

    def _botao(self, texto, text_color, hover_color, acao):
        """Botão de ação: fecha este popup antes de agir.

        A ordem importa. `_abrir_planta` destrói a janela das
        unidades para abrir a planta, e `_desativar_unidade` faz
        `_recarregar` na tabela por trás — em qualquer dos casos,
        deixar este popup aberto por cima deixava-o órfão, agarrado
        a uma janela que já não existe.
        """

        def executar():
            self.destroy()
            acao()

        # Os três botões partilham forma, altura e contorno; só a
        # cor do texto muda. Num menu de opções nenhuma delas é mais
        # importante do que as outras — antes havia um azul cheio,
        # um com contorno e um solto sem nada, e a diferença de peso
        # visual dizia uma coisa que não era verdade (08/09/2026).
        ctk.CTkButton(
            self,
            text=texto,
            height=34,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=tema.COR_BORDA,
            command=executar,
        ).pack(fill="x", padx=20, pady=3)


class _ControladorPontePlanta:
    """Usada só dentro de `PlantaLugaresModal`, passada como
    `controlador` à `PlantaLugares` embrulhada (ver ponto 13 do
    docstring do módulo).

    `PlantaLugares._abrir_contrato` navega para `NovoContratoMensal`
    chamando `self.controlador.mostrar_frame(...)` — ao clicar numa
    cama livre/reservada. Se `PlantaLugares` estiver dentro deste
    popup e essa chamada for direta ao controlador verdadeiro, o
    popup ficava aberto, flutuando por cima da janela principal, que
    trocava de ecrã lá atrás — esta ponte fecha primeiro o popup e
    só depois repassa a chamada. Não muda nada em `gui_unidades.py`:
    `PlantaLugares` continua a falar só com "o controlador", seja
    lá que objeto for.
    """

    def __init__(self, popup, controlador_real):
        self._popup = popup
        self._controlador_real = controlador_real

    def mostrar_frame(self, classe_frame, **kwargs):
        self._popup.destroy()
        self._controlador_real.mostrar_frame(classe_frame, **kwargs)


class PlantaLugaresModal(ctk.CTkToplevel):
    """Popup com a Planta de Lugares de uma unidade — aberto pelo
    botão "Abrir Mapa" dentro de `UnidadesDaPropriedadeModal`
    (07/09/2026, 5ª ronda, aprovado por mockup, ver ponto 13 do
    docstring do módulo).

    Reaproveita a `PlantaLugares` já existente (`gui/gui_unidades.
    py`) sem lhe tocar — só a embrulha aqui dentro e acrescenta
    "← Voltar", junto ao título, que fecha este popup e reabre
    `UnidadesDaPropriedadeModal` da mesma propriedade. Antes, "Abrir
    Mapa" trocava o ecrã principal por trás da barra lateral,
    escondendo de vez as unidades da propriedade — agora fica na
    mesma família de popups (propriedade → unidades → mapa).
    """

    def __init__(self, tela_lista, prop, unidade_id):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.prop = prop

        self.title("Planta de Lugares")
        self.geometry("900x640")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", padx=20, pady=(14, 0))
        ctk.CTkButton(
            cabecalho,
            # "<" simples em vez de "←": o glifo Unicode da seta
            # aparecia como um quadrado (tofu) no Windows do aluno —
            # mesma família de bug do "Ver planta →" antigo (por
            # isso "Abrir Mapa" já não usa seta nenhuma). "<" é ASCII
            # puro, sem depender da fonte ter esse glifo.
            text="< Voltar",
            width=90,
            height=26,
            corner_radius=tema.RAIO_BOTAO,
            fg_color=tema.ID_CHIP_FUNDO,
            text_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.COR_BORDA,
            command=self._voltar,
        ).pack(side="left")

        controlador_ponte = _ControladorPontePlanta(
            self, tela_lista.controlador
        )
        planta = PlantaLugares(
            self, controlador=controlador_ponte, unidade_id=unidade_id
        )
        planta.pack(fill="both", expand=True)

        # Fechar pela X nativa da janela volta às unidades da
        # propriedade, mesmo comportamento do botão "← Voltar" — só
        # que disparado pelo gestor de janelas, não pelo Tkinter.
        self.protocol("WM_DELETE_WINDOW", self._voltar)

    def _voltar(self):
        self.destroy()
        UnidadesDaPropriedadeModal(self.tela_lista, self.prop)


class NovaPropriedadeModal(ctk.CTkToplevel):
    """Modal de criação de uma propriedade — nome, morada e IBAN
    (opcional). O IBAN foi acrescentado em 13/09/2026 para a
    impressão do contrato mensal: a Cláusula 3ª mostra o IBAN para
    onde o inquilino paga a renda, e é a propriedade que o guarda
    (não o cliente — decisão do aluno, ver conversa).
    """

    def __init__(self, tela_lista):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista

        self.title("Nova Propriedade")
        self.geometry("380x360")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Nova Propriedade",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 14))

        ctk.CTkLabel(
            self,
            text="Nome",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.pack(fill="x", padx=20, pady=(2, 10))

        ctk.CTkLabel(
            self,
            text="Morada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_morada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_morada.pack(fill="x", padx=20, pady=(2, 10))

        ctk.CTkLabel(
            self,
            text="IBAN (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_iban = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: PT50000201231234567890154",
        )
        self.campo_iban.pack(fill="x", padx=20, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text=(
                "Sem espaços. Aparece formatado no contrato mensal, "
                "para o inquilino saber para onde pagar."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=340,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Criar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._criar,
        ).pack(side="right")

    def _criar(self):
        iban = self.campo_iban.get().strip()

        if iban and not validacoes.validar_iban(iban):
            componentes.mostrar_erro(
                "IBAN inválido — confirma o número. Se tiveres "
                "espaços, tira-os antes de gravar."
            )
            return

        try:
            propriedade = propriedades.criar(
                self.campo_nome.get(), self.campo_morada.get(), iban=iban
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Propriedade criada com sucesso: {propriedade['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class EditarPropriedadeModal(ctk.CTkToplevel):
    """Modal de edição de uma propriedade existente — mesmos campos
    de `NovaPropriedadeModal`, pré-preenchidos.

    O IBAN aparece formatado com espaços de 4 em 4 (mais fácil de
    conferir a olho nu do que a string crua de 25 caracteres), mas
    ao gravar é sempre mandado cru, sem espaços — o formato
    canónico que a base de dados guarda (decisão do aluno,
    13/09/2026). O utilizador pode escrever com ou sem espaços; a
    limpeza acontece aqui, antes de chamar `propriedades.atualizar`.
    """

    def __init__(self, tela_lista, prop):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.prop = prop

        self.title(f"Editar Propriedade — {prop['nome']}")
        self.geometry("380x360")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {prop['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 14))

        ctk.CTkLabel(
            self,
            text="Nome",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_nome = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_nome.insert(0, prop["nome"])
        self.campo_nome.pack(fill="x", padx=20, pady=(2, 10))

        ctk.CTkLabel(
            self,
            text="Morada",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_morada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_morada.insert(0, prop["morada"])
        self.campo_morada.pack(fill="x", padx=20, pady=(2, 10))

        ctk.CTkLabel(
            self,
            text="IBAN (opcional)",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_iban = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: PT50000201231234567890154",
        )
        # Mostra formatado com espaços, para leitura — mas o que se
        # grava é o cru, limpo no `_guardar`.
        self.campo_iban.insert(0, _formatar_iban(prop["iban"]))
        self.campo_iban.pack(fill="x", padx=20, pady=(2, 2))

        ctk.CTkLabel(
            self,
            text=(
                "Podes escrever com ou sem espaços. Guardado sempre "
                "sem espaços (formato canónico)."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=10),
            wraplength=340,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Guardar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

    def _guardar(self):
        # Limpa espaços antes de validar/gravar. O utilizador pode
        # ter escrito o IBAN com espaços de 4 em 4 (o que se vê na
        # caixa ao abrir), e a base de dados guarda sempre o cru.
        iban = self.campo_iban.get().strip().replace(" ", "")

        if iban and not validacoes.validar_iban(iban):
            componentes.mostrar_erro("IBAN inválido — confirma o número.")
            return

        try:
            propriedades.atualizar(
                self.prop["id"],
                nome=self.campo_nome.get(),
                morada=self.campo_morada.get(),
                iban=iban,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Propriedade {self.prop['id']} atualizada."
        )
        self.destroy()
        self.tela_lista._recarregar()


class _PopupCamaExtra(ctk.CTkToplevel):
    """Pop-up para "Quantidade de camas extra" e "Tipo de cama
    extra", aberto ao marcar "Permite cama extra" em
    NovaUnidadeModal/EditarUnidadeModal (Fase 2, v1.4.0, item (d),
    2ª ronda — mockup validado pelo aluno em 15/09/2026: a 1ª
    versão mostrava estes dois campos dentro do próprio modal da
    unidade, mas o corpo ficou demasiado alto e o rodapé chegou a
    sobrepor-se à secção; separar num pop-up devolveu o modal
    principal ao tamanho de antes).

    "Voltar" e "Confirmar" fazem os dois a mesma ação de fecho —
    guardam o texto escrito e fecham o pop-up, mantendo "Permite
    cama extra" marcada — só muda QUANDO validam: "Confirmar" exige
    já aqui quantidade (inteiro > 0) e tipo preenchidos, recusando
    fechar enquanto faltar algo; "Voltar" aceita o texto tal como
    está, válido ou não, e deixa a validação para o "Criar"/
    "Guardar" do modal principal, tal como qualquer outro campo do
    formulário.
    """

    def __init__(
        self, pai, nome_unidade, qtd_inicial, tipo_inicial, ao_fechar
    ):
        super().__init__(pai)
        self.ao_fechar = ao_fechar

        self.title("Cama extra")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(pai)
        _colocar_no_topo(self)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text="CAMA EXTRA",
            text_color=tema.AZUL_PRINCIPAL,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=5,
            font=ctk.CTkFont(size=9, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            self,
            text="Cama extra",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20)
        ctk.CTkLabel(
            self,
            text=nome_unidade,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Quantidade de camas extra",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_qtd = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        self.campo_qtd.insert(0, qtd_inicial)
        self.campo_qtd.pack(fill="x", padx=20, pady=(2, 10))

        ctk.CTkLabel(
            self,
            text="Tipo de cama extra",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.campo_tipo = ctk.CTkEntry(
            self,
            corner_radius=tema.RAIO_CAMPO,
            placeholder_text="ex.: colchão insuflável, sofá-cama",
        )
        self.campo_tipo.insert(0, tipo_inicial)
        self.campo_tipo.pack(fill="x", padx=20, pady=(2, 6))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Voltar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self._voltar,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Confirmar",
            fg_color=tema.VERDE,
            hover_color=tema.AZUL_CLARO,
            command=self._confirmar,
        ).pack(side="right")

        # Por último, e não no início: só depois de todos os
        # widgets (incluindo o rodapé) estarem "packed" é que
        # `winfo_reqheight` sabe a altura real que isto precisa.
        _ajustar_tamanho(self, largura=300)

        self.campo_qtd.focus_set()

    def _voltar(self):
        self.ao_fechar(self.campo_qtd.get(), self.campo_tipo.get())
        self.destroy()

    def _confirmar(self):
        texto_qtd = self.campo_qtd.get().strip()
        texto_tipo = self.campo_tipo.get().strip()

        try:
            _ler_inteiro_cama_extra(texto_qtd)
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        if not texto_tipo:
            componentes.mostrar_erro("O tipo de cama extra é obrigatório.")
            return

        self.ao_fechar(texto_qtd, texto_tipo)
        self.destroy()


class NovaUnidadeModal(ctk.CTkToplevel):
    """Modal de criação de uma unidade dentro de uma propriedade já
    escolhida (o cartão onde "+ Unidade" foi premido) — a
    propriedade vem fixa, mas o tipo (Mensal/Airbnb) já se escolhe
    aqui (06/09/2026, ao juntar a Airbnb a este ecrã — antes só
    criava "mensal", fixo).

    "Época alta ativa" só tem efeito real na Airbnb —
    `contratos.criar_mensal` usa sempre `preco_base`, nunca
    `epoca_alta_ativa`/`preco_epoca_alta` (só
    `contratos._preco_calculado_airbnb` os lê). Por isso, com
    "Mensal" escolhido, marcar essa caixa mostra um aviso e
    desmarca-se sozinha — decisão do aluno, 06/09/2026: validado só
    aqui na GUI, por agora (unidades.criar/atualizar continuam a
    aceitar qualquer combinação, para o cli.py não mudar).

    Cama extra do Airbnb (Fase 2, v1.4.0, item (d), 2ª ronda,
    mockup validado pelo aluno em 15/09/2026): só faz sentido na
    Airbnb, "Permite cama extra" desmarca-se sozinha com aviso ao
    trocar para Mensal (`_ao_mudar_tipo`) ou ao tentar marcá-la já
    em Mensal (`_ao_marcar_cama_extra`). Marcá-la abre
    `_PopupCamaExtra` por cima deste modal — "Quantidade" e "Tipo
    de cama extra" não vivem aqui dentro (a 1ª versão tentou isso e
    o modal ficou demasiado alto, com o rodapé a sobrepor-se à
    secção); o que fica aqui é só um resumo de uma linha
    (`self.frame_resumo_cama_extra`) com um link "editar" que
    reabre o pop-up.
    """

    def __init__(self, tela_lista, prop):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.prop = prop
        self._cama_extra_qtd_texto = ""
        self._cama_extra_tipo_texto = ""

        self.title(f"Nova Unidade — {prop['nome']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text="Nova Unidade",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text=f"Propriedade: {prop['nome']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Tipo",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20)
        self.combo_tipo = componentes.Seletor(
            self, values=["Mensal", "Airbnb"], command=self._ao_mudar_tipo
        )
        self.combo_tipo.set("Mensal")
        self.combo_tipo.pack(fill="x", padx=20, pady=(2, 10))

        self.campo_nome = self._campo("Nome")
        self.campo_preco_base = self._campo("Preço base (€)")
        self.campo_preco_epoca_alta = self._campo("Preço época alta (€)")
        self.campo_multa = self._campo("Multa check-in tardio (€)")

        self.epoca_alta_ativa = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="Época alta ativa",
            variable=self.epoca_alta_ativa,
            command=self._ao_marcar_epoca_alta,
        ).pack(anchor="w", padx=20, pady=(14, 0))

        self.permite_cama_extra = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="Permite cama extra",
            variable=self.permite_cama_extra,
            command=self._ao_marcar_cama_extra,
        ).pack(anchor="w", padx=20, pady=(10, 0))

        self.frame_resumo_cama_extra = ctk.CTkFrame(
            self,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.rotulo_resumo_cama_extra = ctk.CTkLabel(
            self.frame_resumo_cama_extra,
            text="",
            text_color=tema.NAVY_ESCURO,
            font=ctk.CTkFont(size=11),
        )
        self.rotulo_resumo_cama_extra.pack(side="left", padx=10, pady=6)
        ctk.CTkButton(
            self.frame_resumo_cama_extra,
            text="editar",
            fg_color="transparent",
            hover=False,
            text_color=tema.AZUL_PRINCIPAL,
            font=ctk.CTkFont(size=11, underline=True),
            command=self._abrir_popup_cama_extra,
        ).pack(side="right", padx=10, pady=6)
        # Começa escondido (self.permite_cama_extra nasce False) —
        # só `_atualizar_resumo_cama_extra` decide quando aparece.

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Criar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._criar,
        ).pack(side="right")

        _ajustar_tamanho(self, largura=380)

    def _campo(self, rotulo):
        ctk.CTkLabel(
            self,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(6, 2))
        entrada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        entrada.pack(fill="x", padx=20)
        return entrada

    def _tipo_selecionado(self):
        return "mensal" if self.combo_tipo.get() == "Mensal" else "airbnb"

    def _ao_mudar_tipo(self, _valor_escolhido):
        """Ao trocar para "Mensal" com "Época alta ativa" e/ou
        "Permite cama extra" já marcadas, desmarca e avisa — mesma
        regra de `_ao_marcar_epoca_alta`/`_ao_marcar_cama_extra`, só
        que disparada pelo lado do tipo em vez do lado da caixa
        (cobre trocar o tipo DEPOIS de já ter marcado a caixa, não
        só o caminho inverso).
        """
        tipo_mensal = self._tipo_selecionado() == "mensal"
        if tipo_mensal and self.epoca_alta_ativa.get():
            self.epoca_alta_ativa.set(False)
            componentes.mostrar_erro(
                "Unidade do tipo mensal não existe época alta."
            )
        if tipo_mensal and self.permite_cama_extra.get():
            self._desmarcar_cama_extra_com_aviso()

    def _ao_marcar_epoca_alta(self):
        tipo_mensal = self._tipo_selecionado() == "mensal"
        if self.epoca_alta_ativa.get() and tipo_mensal:
            self.epoca_alta_ativa.set(False)
            componentes.mostrar_erro(
                "Unidade do tipo mensal não existe época alta."
            )

    def _ao_marcar_cama_extra(self):
        if not self.permite_cama_extra.get():
            self._cama_extra_qtd_texto = ""
            self._cama_extra_tipo_texto = ""
            self._atualizar_resumo_cama_extra()
            return

        if self._tipo_selecionado() == "mensal":
            self._desmarcar_cama_extra_com_aviso()
            return

        self._abrir_popup_cama_extra()

    def _desmarcar_cama_extra_com_aviso(self):
        self.permite_cama_extra.set(False)
        self._cama_extra_qtd_texto = ""
        self._cama_extra_tipo_texto = ""
        self._atualizar_resumo_cama_extra()
        componentes.mostrar_erro(
            "Cama extra só se aplica a unidades do tipo Airbnb."
        )

    def _abrir_popup_cama_extra(self):
        _PopupCamaExtra(
            self,
            self.campo_nome.get().strip() or "Nova unidade",
            self._cama_extra_qtd_texto,
            self._cama_extra_tipo_texto,
            self._ao_fechar_popup_cama_extra,
        )

    def _ao_fechar_popup_cama_extra(self, qtd_texto, tipo_texto):
        self._cama_extra_qtd_texto = qtd_texto.strip()
        self._cama_extra_tipo_texto = tipo_texto.strip()
        self._atualizar_resumo_cama_extra()

    def _atualizar_resumo_cama_extra(self):
        if not self.permite_cama_extra.get():
            self.frame_resumo_cama_extra.pack_forget()
            _ajustar_tamanho(self, largura=380)
            return

        if self._cama_extra_qtd_texto and self._cama_extra_tipo_texto:
            texto = (
                f"{self._cama_extra_qtd_texto} × "
                f"{self._cama_extra_tipo_texto}"
            )
        else:
            texto = "Por preencher"

        self.rotulo_resumo_cama_extra.configure(text=texto)
        self.frame_resumo_cama_extra.pack(fill="x", padx=20, pady=(6, 0))
        _ajustar_tamanho(self, largura=380)

    def _criar(self):
        try:
            preco_base = _ler_decimal(
                self.campo_preco_base.get(), "Preço base"
            )
            preco_epoca_alta = _ler_decimal(
                self.campo_preco_epoca_alta.get(), "Preço época alta"
            )
            multa = _ler_decimal(
                self.campo_multa.get(), "Multa de check-in tardio"
            )
            qtd_cama_extra = None
            if self.permite_cama_extra.get():
                qtd_cama_extra = _ler_inteiro_cama_extra(
                    self._cama_extra_qtd_texto
                )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            unidade = unidades.criar(
                self.prop["id"],
                self.campo_nome.get(),
                self._tipo_selecionado(),
                preco_base,
                preco_epoca_alta,
                multa,
                epoca_alta_ativa=self.epoca_alta_ativa.get(),
                permite_cama_extra=self.permite_cama_extra.get(),
                qtd_cama_extra=qtd_cama_extra,
                tipo_cama_extra=self._cama_extra_tipo_texto,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(
            f"Unidade criada com sucesso: {unidade['id']}"
        )
        self.destroy()
        self.tela_lista._recarregar()


class EditarUnidadeModal(ctk.CTkToplevel):
    """Modal de edição de uma unidade existente — mesmos campos de
    NovaUnidadeModal, pré-preenchidos; propriedade e tipo não se
    alteram (mesma regra de `unidades.atualizar`), por isso não há
    seletor de tipo aqui — só o rótulo, com o tipo real da unidade
    (06/09/2026: passou a poder ser "mensal" OU "airbnb", em vez de
    sempre "mensal" fixo no texto).

    Ganhou o botão "Colocar em manutenção"/"Retirar manutenção"
    (07/09/2026, 2ª ronda) — antes vivia como botão próprio na linha
    da lista (`ListaPropriedades`), mas desalinhava "Ver planta →" e
    competia com Desativar/Editar; o aluno pediu para mudar para
    aqui dentro, agindo na hora (mesma confirmação de sempre para
    "Colocar", sem confirmação para "Retirar" — mesma convenção de
    `_reativar_unidade`) e fechando o modal a seguir, sem misturar
    com o "Guardar" dos preços.

    Cama extra do Airbnb (Fase 2, v1.4.0, item (d), 2ª ronda,
    mockup validado pelo aluno em 15/09/2026): como o tipo não muda
    ao editar, aqui não há a lógica de "desmarcar sozinho ao trocar
    de tipo" de `NovaUnidadeModal` — "Época alta ativa" e "Permite
    cama extra" ficam as duas permanentemente desativadas
    (`state="disabled"`) quando `uni["tipo"] == "mensal"`, com uma
    nota a explicar porquê. Em Airbnb, se a unidade já tiver cama
    extra gravada, aparece logo o resumo de uma linha (sem abrir o
    pop-up sozinho) com um link "editar" — `_PopupCamaExtra` só
    abre se o aluno clicar em "editar" ou desmarcar e voltar a
    marcar a caixa.
    """

    def __init__(self, tela_lista, uni, prop):
        super().__init__(tela_lista)
        self.tela_lista = tela_lista
        self.uni = uni
        self._cama_extra_qtd_texto = (
            str(uni["qtd_cama_extra"])
            if uni["qtd_cama_extra"] is not None
            else ""
        )
        self._cama_extra_tipo_texto = uni["tipo_cama_extra"]

        self.title(f"Editar Unidade — {uni['nome']}")
        self.resizable(False, False)
        self.configure(fg_color=tema.COR_FUNDO)
        self.transient(tela_lista)
        _colocar_no_topo(self)

        ctk.CTkLabel(
            self,
            text=f"Editar {uni['nome']}",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text=f"Propriedade: {prop['nome']} · tipo: {uni['tipo']}",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        self.campo_nome = self._campo("Nome", uni["nome"])
        self.campo_preco_base = self._campo(
            "Preço base (€)", _formatar_valor(uni["preco_base"])
        )
        self.campo_preco_epoca_alta = self._campo(
            "Preço época alta (€)", _formatar_valor(uni["preco_epoca_alta"])
        )
        self.campo_multa = self._campo(
            "Multa check-in tardio (€)",
            _formatar_valor(uni["multa_check_in_tardio"]),
        )

        airbnb = uni["tipo"] == "airbnb"

        self.epoca_alta_ativa = ctk.BooleanVar(value=uni["epoca_alta_ativa"])
        ctk.CTkCheckBox(
            self,
            text="Época alta ativa",
            variable=self.epoca_alta_ativa,
            command=self._ao_marcar_epoca_alta,
            state="normal" if airbnb else "disabled",
        ).pack(anchor="w", padx=20, pady=(14, 0))

        self.permite_cama_extra = ctk.BooleanVar(
            value=uni["permite_cama_extra"]
        )
        ctk.CTkCheckBox(
            self,
            text="Permite cama extra",
            variable=self.permite_cama_extra,
            command=self._ao_marcar_cama_extra,
            state="normal" if airbnb else "disabled",
        ).pack(anchor="w", padx=20, pady=(10, 0))

        self.frame_resumo_cama_extra = ctk.CTkFrame(
            self,
            fg_color=tema.ID_CHIP_FUNDO,
            corner_radius=tema.RAIO_CAMPO,
        )
        self.rotulo_resumo_cama_extra = ctk.CTkLabel(
            self.frame_resumo_cama_extra,
            text="",
            text_color=tema.NAVY_ESCURO,
            font=ctk.CTkFont(size=11),
        )
        self.rotulo_resumo_cama_extra.pack(side="left", padx=10, pady=6)
        ctk.CTkButton(
            self.frame_resumo_cama_extra,
            text="editar",
            fg_color="transparent",
            hover=False,
            text_color=tema.AZUL_PRINCIPAL,
            font=ctk.CTkFont(size=11, underline=True),
            command=self._abrir_popup_cama_extra,
        ).pack(side="right", padx=10, pady=6)

        if airbnb:
            self._atualizar_resumo_cama_extra()
        else:
            ctk.CTkLabel(
                self,
                text=(
                    "Época alta e cama extra só se aplicam a "
                    "unidades do tipo Airbnb."
                ),
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=10),
                wraplength=320,
                justify="left",
            ).pack(anchor="w", padx=20, pady=(8, 0))

        ctk.CTkFrame(self, height=1, fg_color=tema.COR_BORDA).pack(
            fill="x", padx=20, pady=(16, 12)
        )

        em_manutencao = uni["em_manutencao"]
        cor_manutencao = (
            tema.VERDE if em_manutencao else tema.TEXTO_INDISPONIVEL
        )
        fundo_hover = (
            tema.VERDE_LIVRE if em_manutencao else tema.CINZA_INDISPONIVEL
        )
        ctk.CTkButton(
            self,
            text=(
                "Retirar manutenção"
                if em_manutencao
                else "Colocar em manutenção"
            ),
            fg_color="transparent",
            border_width=1,
            border_color=cor_manutencao,
            text_color=cor_manutencao,
            hover_color=fundo_hover,
            command=self._alternar_manutencao,
        ).pack(anchor="w", padx=20)

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=20, pady=20, side="bottom")
        ctk.CTkButton(
            rodape,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            rodape,
            text="Guardar",
            fg_color=tema.AZUL_PRINCIPAL,
            hover_color=tema.AZUL_CLARO,
            command=self._guardar,
        ).pack(side="right")

        _ajustar_tamanho(self, largura=380)

    def _alternar_manutencao(self):
        if self.uni["em_manutencao"]:
            try:
                unidades.desmarcar_manutencao(self.uni["id"])
            except ValueError as erro:
                componentes.mostrar_erro(str(erro))
                return

            componentes.mostrar_sucesso(
                f"Unidade {self.uni['nome']} retirada da manutenção."
            )
        else:
            pergunta = (
                f"Colocar a unidade {self.uni['nome']} "
                f"({self.uni['id']}) em manutenção? Sai da oferta "
                "até a retirares."
            )
            if not componentes.confirmar(pergunta):
                return

            try:
                unidades.marcar_manutencao(self.uni["id"])
            except ValueError as erro:
                componentes.mostrar_erro(str(erro))
                return

            componentes.mostrar_sucesso(
                f"Unidade {self.uni['nome']} em manutenção."
            )

        self.destroy()
        self.tela_lista._recarregar()

    def _campo(self, rotulo, valor_inicial):
        ctk.CTkLabel(
            self,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=20, pady=(6, 2))
        entrada = ctk.CTkEntry(self, corner_radius=tema.RAIO_CAMPO)
        entrada.insert(0, valor_inicial)
        entrada.pack(fill="x", padx=20)
        return entrada

    def _ao_marcar_epoca_alta(self):
        # Tipo é fixo aqui (não muda ao editar — regra de
        # unidades.atualizar), por isso só valida contra
        # self.uni["tipo"], sem seletor nenhum para reler.
        if self.epoca_alta_ativa.get() and self.uni["tipo"] == "mensal":
            self.epoca_alta_ativa.set(False)
            componentes.mostrar_erro(
                "Unidade do tipo mensal não existe época alta."
            )

    def _ao_marcar_cama_extra(self):
        # Tipo é fixo aqui e a caixa já nasce desativada quando
        # mensal — este ramo só é alcançável em Airbnb.
        if not self.permite_cama_extra.get():
            self._cama_extra_qtd_texto = ""
            self._cama_extra_tipo_texto = ""
            self._atualizar_resumo_cama_extra()
            return

        self._abrir_popup_cama_extra()

    def _abrir_popup_cama_extra(self):
        _PopupCamaExtra(
            self,
            self.uni["nome"],
            self._cama_extra_qtd_texto,
            self._cama_extra_tipo_texto,
            self._ao_fechar_popup_cama_extra,
        )

    def _ao_fechar_popup_cama_extra(self, qtd_texto, tipo_texto):
        self._cama_extra_qtd_texto = qtd_texto.strip()
        self._cama_extra_tipo_texto = tipo_texto.strip()
        self._atualizar_resumo_cama_extra()

    def _atualizar_resumo_cama_extra(self):
        if not self.permite_cama_extra.get():
            self.frame_resumo_cama_extra.pack_forget()
            _ajustar_tamanho(self, largura=380)
            return

        if self._cama_extra_qtd_texto and self._cama_extra_tipo_texto:
            texto = (
                f"{self._cama_extra_qtd_texto} × "
                f"{self._cama_extra_tipo_texto}"
            )
        else:
            texto = "Por preencher"

        self.rotulo_resumo_cama_extra.configure(text=texto)
        self.frame_resumo_cama_extra.pack(fill="x", padx=20, pady=(6, 0))
        _ajustar_tamanho(self, largura=380)

    def _guardar(self):
        try:
            preco_base = _ler_decimal(
                self.campo_preco_base.get(), "Preço base"
            )
            preco_epoca_alta = _ler_decimal(
                self.campo_preco_epoca_alta.get(), "Preço época alta"
            )
            multa = _ler_decimal(
                self.campo_multa.get(), "Multa de check-in tardio"
            )
            qtd_cama_extra = None
            if self.permite_cama_extra.get():
                qtd_cama_extra = _ler_inteiro_cama_extra(
                    self._cama_extra_qtd_texto
                )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        try:
            unidades.atualizar(
                self.uni["id"],
                nome=self.campo_nome.get(),
                preco_base=preco_base,
                preco_epoca_alta=preco_epoca_alta,
                multa_check_in_tardio=multa,
                epoca_alta_ativa=self.epoca_alta_ativa.get(),
                permite_cama_extra=self.permite_cama_extra.get(),
                qtd_cama_extra=qtd_cama_extra,
                tipo_cama_extra=self._cama_extra_tipo_texto,
            )
        except ValueError as erro:
            componentes.mostrar_erro(str(erro))
            return

        componentes.mostrar_sucesso(f"Unidade {self.uni['id']} atualizada.")
        self.destroy()
        self.tela_lista._recarregar()