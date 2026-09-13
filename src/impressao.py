"""Geração de documentos PDF do sistema.

Módulo puro de formatação: recebe dicionários já lidos pelos
módulos de negócio, escreve um PDF, devolve o caminho do ficheiro.
NÃO fala com base de dados, NÃO chama `procurar` nenhum, NÃO
importa nenhum módulo de negócio. O contrato que recebe chega
pronto — esta camada só o desenha.

Mantém-se assim de propósito (decisão do aluno, 13/09/2026): quando
o módulo de Relatórios chegar, vai fazer as suas próprias leituras
e passar objetos a este módulo, tal como o gui_contratos.py fará.
Ficando puro, o impressao.py não cresce em dependências e pode ser
testado com dicionários falsos, sem MySQL nenhum a correr.

Neste momento só tem o contrato mensal (`gerar_contrato_pdf`). O
resto dos relatórios do sistema, quando aparecerem, seguem o mesmo
padrão — uma função pública por documento, todas com a mesma
assinatura "recebe dicts, devolve caminho".

O texto da minuta é transcrito literalmente do ficheiro
`Minuta-Contrato-de-Arrendamento-de-Quarto.pdf`, com duas exceções
documentadas na conversa com o aluno (13/09/2026):

1. As gralhas tipográficas óbvias da minuta estão corrigidas
   (letras trocadas, palavras faltantes, falta de espaço). Estilo,
   pontuação peculiar e estrutura das cláusulas mantêm-se
   exatamente como estão na minuta — só se corrigiu o que era
   claramente erro de transcrição.
2. Um parágrafo de abertura identifica as partes antes da
   Cláusula 1ª (a minuta original começa direto na Cláusula 1ª e
   nunca nomeia as partes), e uma zona de assinaturas fecha o
   documento (a minuta original termina na linha "local, data"
   sem espaço para assinar). Ambos foram acrescentados a pedido do
   aluno — sem eles, o senhorio e o inquilino nunca apareceriam
   com nome no PDF.

Formato dos números: só algarismos ("350,00 euros"), como o resto
do sistema. Datas com espaços à volta das barras ("13 / 09 / 2026"),
fiel à minuta original. Nomes de pessoas e unidades sempre só com
o nome — nunca com o ID à frente (só o ID do contrato aparece, e é
"CNT-XXX").

A pasta `contratos_gerados/` fica na raiz do projeto (ao lado de
`dados/` e `backups/`), fora do controlo de versões — mesma
convenção da decisão 13. O nome do ficheiro leva a hora, para nunca
sobrescrever um contrato já gerado no mesmo dia (decisão do aluno,
13/09/2026).

ALTERAÇÕES 13/09/2026 (mesmo dia, ao testar no PC do aluno):

- As fontes core do PDF (`Times`, `Helvetica`, `Courier`) usam
  Latin-1 e NÃO incluem símbolos tipográficos: travessão longo
  "—" (U+2014), en-dash "–" (U+2013), aspas curvas (U+2018/2019/
  201C/201D), reticências "…" (U+2026), etc. Quando o `fpdf2`
  encontra um destes caracteres, rebenta com "Character 'X' is
  outside the range of characters supported by the font used".

  Isto aconteceu em duas rondas, ambas apanhadas pelo aluno ao
  imprimir contratos reais:

  1. Primeira ronda: `_formatar_iban` e `_formatar_valor_para_pdf`
     usavam "—" no caso vazio. Corrigido para "-" (hífen, ASCII).
  2. Segunda ronda: os TÍTULOS das cláusulas ("Cláusula 1ª —
     Prazo", etc.) ainda usavam "—". Foram os últimos a sobrar
     porque o meu primeiro "grep" ao ficheiro não os apanhou.

  Nesta versão, TODOS os travessões do documento estão substituídos
  por hífen simples ("-", U+002D, ASCII puro). Revi o ficheiro de
  ponta a ponta à procura de qualquer símbolo não-ASCII que ainda
  fosse para dentro de uma chamada `pdf.cell` ou `pdf.multi_cell`.

  Preferida esta correção mínima em vez de carregar um `.ttf`
  Unicode (a outra opção, mais pesada) — não vale a pena meter um
  ficheiro de fontes no projeto só por causa de um carácter.
  Quando aparecer um caso que precise de símbolos a sério
  (gráficos, ícones, moeda), aí passa-se para o Unicode.

Nota para quem mexer neste ficheiro no futuro: o texto que vai
para o PDF (dentro de `pdf.cell` e `pdf.multi_cell`) NUNCA pode
ter símbolos fora de Latin-1. Se alguém escrever travessões ou
aspas curvas no corpo do contrato no futuro, a correção é sempre
a mesma: trocar por equivalente ASCII. Se for impossível (raro em
contratos), aí sim, considerar a alternativa de carregar um TTF.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from fpdf import FPDF

# Raiz do projeto = pasta que contém `src/` e `dados/` como irmãs;
# ancora-se na localização deste ficheiro, não na pasta corrente —
# mesma convenção do `repositorio.py`.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_CONTRATOS = RAIZ_PROJETO / "contratos_gerados"


def _formatar_valor_para_pdf(valor):
    """Converte um Decimal para texto no formato PT-PT usado nos
    contratos: vírgula decimal, duas casas, ponto de milhar. Sem
    símbolo de euro (a minuta escreve "euros" depois).

    Uma versão da `formatar_valor` do cli.py, sem o "EUR" — porque
    o contrato diz "350,00 euros", não "350,00 EUR euros".

    Um valor None devolve "-" (hífen simples, ASCII), NÃO o
    travessão — as fontes core do PDF usam Latin-1 e não incluem o
    travessão. Mesma razão da `_formatar_iban` (ver docstring do
    módulo).
    """
    if valor is None:
        return "-"

    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")

    return texto


def _formatar_data_barra(data):
    """Formata uma date como "13 / 09 / 2026" — com espaços à volta
    das barras, fiel à minuta original (decisão do aluno, 13/09/2026).
    """
    return f"{data.day:02d} / {data.month:02d} / {data.year}"


def _formatar_iban(iban):
    """Formata um IBAN cru (sem espaços) com espaços de 4 em 4,
    só para apresentação. Igual à `_formatar_iban` do
    gui_propriedades.py — duplicada aqui porque o `impressao.py` é
    um módulo puro e não deve importar nada da GUI.

    Um IBAN vazio devolve "-" (hífen simples, ASCII), NÃO o
    travessão — ver docstring do módulo para a explicação
    detalhada.
    """
    if not iban:
        return "-"

    return " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))


def _garantir_pasta():
    """Cria a pasta `contratos_gerados/` se não existir.

    Está fora do controlo de versões (mesma decisão dos backups),
    por isso tem de ser criada na primeira geração.
    """
    PASTA_CONTRATOS.mkdir(exist_ok=True)


def _caminho_do_ficheiro(ocupacao_id):
    """Constrói o nome e o caminho do PDF para este contrato.

    Formato: `contratos_gerados/CNT-003_2026-09-13_15h42.pdf` — o ID
    do contrato, a data e a hora a que foi gerado. A hora resolve o
    problema de gerar o mesmo contrato duas vezes no mesmo dia, sem
    sobrescrever o primeiro (decisão do aluno, 13/09/2026).
    """
    from datetime import datetime

    _garantir_pasta()

    agora = date.today()
    hora_minuto = datetime.now().strftime("%Hh%M")

    nome = f"{ocupacao_id}_{agora.isoformat()}_{hora_minuto}.pdf"

    return PASTA_CONTRATOS / nome


def gerar_contrato_pdf(
    ocupacao,
    mensal,
    cliente,
    unidade,
    propriedade,
    senhorio,
    local,
):
    """Gera o PDF do contrato mensal e devolve o caminho do ficheiro.

    Parâmetros — todos dicionários já lidos pelos módulos de
    negócio (o `gui_contratos.py` faz as leituras com
    `contratos.procurar`, `contratos.detalhes_mensal`,
    `clientes.procurar`, `unidades.procurar`,
    `propriedades.procurar`, `responsaveis.procurar`):

    - `ocupacao`: linha base da ocupação (traz id, data_inicio, tipo)
    - `mensal`: dados específicos do contrato mensal (renda_praticada,
      caucao, dia_vencimento)
    - `cliente`: registo do cliente (nome)
    - `unidade`: registo da unidade (nome)
    - `propriedade`: registo da propriedade (iban)
    - `senhorio`: registo do responsável escolhido no popup (nome)
    - `local`: string escrita no popup (cidade da assinatura)

    Devolve o `Path` do ficheiro gerado (não só o nome — quem
    chama pode precisar do caminho todo para o mostrar).

    Não valida nada: assume que o `gui_contratos.py` já validou
    (cliente não anonimizado, senhorio escolhido, local preenchido).

    ATENÇÃO — regra crítica: qualquer texto passado a `pdf.cell` ou
    `pdf.multi_cell` tem de ser Latin-1. Se adicionares parágrafos
    novos, NUNCA uses travessões longos, aspas curvas, nem
    reticências tipográficas — só o equivalente ASCII. Ver
    docstring do módulo.
    """
    caminho = _caminho_do_ficheiro(ocupacao["id"])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ---- margens e fonte base -----------------------------------
    pdf.set_margins(left=20, top=20, right=20)

    largura_util = pdf.w - pdf.l_margin - pdf.r_margin

    # ---- título --------------------------------------------------
    pdf.set_font("Times", "B", 13)
    pdf.cell(
        largura_util,
        10,
        "CONTRATO DE ARRENDAMENTO DE QUARTO",
        align="C",
    )
    pdf.ln(16)

    # ---- parágrafo de abertura -----------------------------------
    # Acrescentado a pedido do aluno (não está na minuta original,
    # ver docstring do módulo): identifica as partes antes da
    # Cláusula 1ª. Sem isto, os nomes do senhorio e do inquilino
    # nunca apareceriam no PDF.
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            f"Entre {senhorio['nome']}, na qualidade de Primeiro "
            f"Contraente (senhorio), e {cliente['nome']}, na "
            f"qualidade de Segundo Contraente (inquilino), e "
            f"celebrado o presente contrato de arrendamento do "
            f"quarto sito na unidade {unidade['nome']}, "
            f"correspondente ao contrato n.o {ocupacao['id']}, que "
            f"se rege pelas clausulas seguintes."
        ),
        align="J",
    )
    pdf.ln(6)

    # ---- Cláusula 1 - Prazo -------------------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 1 - Prazo", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            f"1. O presente contrato de arrendamento e feito pelo "
            f"prazo de 3 meses, tendo o seu inicio a "
            f"{_formatar_data_barra(ocupacao['data_inicio'])}."
        ),
        align="J",
    )
    pdf.ln(4)

    # ---- Cláusula 2 - Renovação ---------------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 2 - Renovacao", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "2. No seu termo, o presente contrato de arrendamento "
            "renovar-se-a automaticamente por igual e sucessivos "
            "periodos de 3 meses, nos termos do art. 1096 do CC, "
            "com as alteracoes introduzidas pela Lei n. 31/2012, "
            "de 14 de Agosto."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "3. A Segunda Contraente, nao pode ceder a terceiros o "
            "gozo do locado, total ou parcialmente, gratuita ou "
            "onerosamente, seja a que titulo for e independentemente "
            "da natureza juridica do titulo pelo qual se opera essa "
            "cedencia."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "4. Fica impedida, igualmente, a hospedagem e o "
            "subarrendamento, ou a permanencia de outras pessoas "
            "para pernoitar com o(a) inquilino(a)."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "5. Caso se verifique a hospedagem, o subarrendamento, "
            "ou a permanencia de outras pessoas para pernoitar com "
            "o(a) inquilino(a), concede este(a) a faculdade ao "
            "Primeiro Contraente, de cessar imediatamente o contrato "
            "de arrendamento, sem direito a devolucao da caucao na "
            "totalidade."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "6. E igualmente proibida a permanencia de animais, "
            "quer no quarto, quer na fraccao, assim como o consumo "
            "de tabaco dentro da fraccao (incluindo as janelas dos "
            "quarto, casa de banho, sala e cozinha), sendo que no "
            "caso de ser fumador(a) devera deslocar-se a varanda e "
            "utilizar um dos cinzeiros disponiveis para o efeito, "
            "sendo que sempre que o utilize devera despejar as "
            "cinzas e as beatas e higieniza-lo."
        ),
        align="J",
    )
    pdf.ln(4)

    # ---- Cláusula 3 - Valor da renda ----------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 3 - Valor da renda", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            f"1. A renda mensal pelo presente arrendamento e de "
            f"{_formatar_valor_para_pdf(mensal['renda_praticada'])} "
            f"euros, que devera ser paga entre o 1. e o "
            f"{mensal['dia_vencimento']}. dia do mes a que disser "
            f"respeito, atraves de deposito ou transferencia para o "
            f"IBAN {_formatar_iban(propriedade['iban'])}."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "2. Com a assinatura do presente Contrato, o Segundo "
            "Contraente paga as seguintes quantias:"
        ),
        align="J",
    )
    pdf.ln(1)
    pdf.multi_cell(
        largura_util,
        6,
        (
            f"a) {_formatar_valor_para_pdf(mensal['renda_praticada'])} "
            f"euros, a titulo de pagamento da renda correspondente "
            f"a cada mes;"
        ),
        align="J",
    )
    pdf.ln(1)
    pdf.multi_cell(
        largura_util,
        6,
        (
            f"b) {_formatar_valor_para_pdf(mensal['caucao'])} euros, "
            f"correspondentes a antecipacao de um mes de renda, "
            f"designada por caucao."
        ),
        align="J",
    )
    pdf.ln(4)

    # ---- Cláusula 4 - Denúncia ----------------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 4 - Denuncia", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "1. A Segunda Contraente podera denunciar o presente "
            "contrato de arrendamento no termo do prazo "
            "contratualizado, impedindo a sua renovacao, com uma "
            "antecedencia minima de 30 dias, mediante comunicacao "
            "escrita, ao Primeiro Contraente, nos termos do art. "
            "1098, n. 3 do CC."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "2. O incumprimento do aviso previo de 30 dias quanto a "
            "denuncia do contrato por parte da Segunda Contraente, "
            "ou no decurso das suas renovacoes, nao obsta a "
            "cessacao do contrato, mas obriga esta ao pagamento das "
            "rendas correspondentes ao periodo de pre-aviso em "
            "falta, segundo o disposto no art. 1098, n. 6 do CC."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "3. O Primeiro Contraente podera denunciar o contrato "
            "de arrendamento, ao termino do prazo contratual de um "
            "ano, impedindo assim a sua renovacao, mediante "
            "comunicacao ao Segundo Contraente, com uma "
            "antecedencia nao inferior a 30 dias."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "4. O Primeiro Contraente, podera no decurso do "
            "arrendamento, ainda que durante o prazo inicial "
            "estipulado de 3 meses, denunciar a qualquer tempo o "
            "contrato de arrendamento, no caso de se verificar que "
            "o segundo Contraente, por algum motivo, nao cumpra "
            "escrupulosamente com o estipulado no contrato."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "5. O Primeiro Contraente. No decurso das suas "
            "renovacoes, podera denunciar antes do termino das suas "
            "renovacoes, mediante comunicacao escrita. Ao Segundo "
            "Contraente, com uma antecedencia nao inferior a 30 "
            "dias."
        ),
        align="J",
    )
    pdf.ln(4)

    # ---- Cláusula 5 - Fim ---------------------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 5 - Fim", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "O local arrendado destina-se exclusivamente a "
            "habitacao da Segunda Contraente, reconhecendo este que "
            "o mesmo cumpre cabalmente o fim a que se destina, nao "
            "podendo dar-lhe outro uso, nem subarrenda-lo ou ceder "
            "por qualquer outra forma, no todo ou em parte, sem a "
            "previa autorizacao, por escrito, do Primeiro "
            "Contraente."
        ),
        align="J",
    )
    pdf.ln(4)

    # ---- Cláusula 6 - Manutenção --------------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 6 - Manutencao", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "1. O Segundo Contraente obriga-se a manter o quarto "
            "que ocupa individualmente no estado de conservacao e "
            "limpeza em que se encontra, e as partes comuns da "
            "fraccao, conjuntamente com os restantes inquilinos que "
            "a habitam, no estado de conservacao e limpeza em que "
            "actualmente se encontram as instalacoes e canalizacoes "
            "de agua, luz, esgotos, moveis, utensilios, pagando a "
            "sua custa todas as reparacoes decorrentes de culpa ou "
            "negligencia sua, bem como, manter em bom estado os "
            "respectivos soalhos, portas, janelas, pinturas vidros, "
            "ressalvando o desgaste de sua normal e prudente "
            "utilizacao."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "2. O Segundo Contraente obriga-se a custear todas as "
            "reparacoes decorrentes de culpa ou negligencia sua no "
            "quarto e respectivo equipamento e solidariamente nas "
            "partes comuns da fraccao e respectivo equipamento, no "
            "caso de se vir a verificar algum dano e negligencia "
            "nos referidos e que nao se venha a apurar a quem cabe "
            "a responsabilidade."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "3. E importante que todos os inquilinos zelem pelo bom "
            "funcionamento e manutencao da fraccao, mobilia e demais "
            "equipamentos, a fim de se evitarem problemas futuros "
            "para todos os interessados."
        ),
        align="J",
    )
    pdf.ln(4)

    # ---- Cláusula 7 - Obras -------------------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 7 - Obras", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "O Segundo Contraente nao podera fazer quaisquer obras "
            "no local arrendado sem a previa autorizacao, nem "
            "levantar quaisquer benfeitorias por si realizadas, nem "
            "por elas pedir indemnizacao ou alegar qualquer direito "
            "de retencao."
        ),
        align="J",
    )
    pdf.ln(4)

    # ---- Cláusula 8 - Despesas ----------------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 8 - Despesas", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "Com a assinatura do presente contrato, o Segundo "
            "Contraente declara que as despesas de agua, luz e "
            "internet ficarao a seu cargo e as mesmas serao "
            "liquidadas equitativamente pelo Segundo Contraente e "
            "pelos restantes inquilinos que habitarem a fraccao."
        ),
        align="J",
    )
    pdf.ln(4)

    # ---- Cláusula 9 - Estado do locado --------------------------
    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_util, 6, "Clausula 9 - Estado do locado", ln=1)
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "1. Ao presente contrato sao anexadas fotografias do "
            "locado, demonstrativas do estado em que o mesmo se "
            "encontra, assim como a listagem de bens comuns e "
            "individuais do quarto, e memorando de co-habitacao da "
            "fraccao, contendo as regras e boa conduta, manutencao "
            "e funcionamento, sendo que as referidas ficam a fazer "
            "parte integrante do presente contrato."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        (
            "2. No momento de restituicao do imovel, havera lugar "
            "a uma vistoria a realizar pelo Primeiro Contraente ou "
            "por seus representantes, na presenca do segundo "
            "Contraente, que se obriga a entregar o quarto equipado "
            "e no mesmo estado de conservacao e limpeza que o "
            "recebeu aquando do inicio do contrato."
        ),
        align="J",
    )
    pdf.ln(6)

    # ---- parágrafo final -----------------------------------------
    pdf.multi_cell(
        largura_util,
        6,
        (
            "Este contrato foi celebrado em dois documentos "
            "originais, declarando as partes contratantes dispensar "
            "o reconhecimento notarial, nao podendo tal facto ser "
            "invocado por qualquer das partes como vicio, nulidade "
            "ou anulabilidade do mesmo."
        ),
        align="J",
    )
    pdf.ln(8)

    # ---- local e data de assinatura ------------------------------
    # Fiel à minuta: "... (local), ... / ... / ..." — com espaços
    # à volta das barras. A data é a de hoje (dia da assinatura).
    hoje = date.today()
    pdf.multi_cell(
        largura_util,
        6,
        (f"{local}, {hoje.day:02d} / {hoje.month:02d} / " f"{hoje.year}"),
    )
    pdf.ln(20)

    # ---- zona de assinaturas -------------------------------------
    # Acrescentada (não está na minuta original, ver docstring do
    # módulo): sem isto, o contrato não tinha sítio para assinar.
    largura_coluna = largura_util / 2 - 5

    pdf.cell(largura_coluna, 6, "_" * 40, align="C")
    pdf.cell(largura_util - largura_coluna, 6, "_" * 40, align="C", ln=1)
    pdf.ln(1)

    pdf.set_font("Times", "B", 11)
    pdf.cell(largura_coluna, 6, "Primeiro Contraente", align="C")
    pdf.cell(
        largura_util - largura_coluna,
        6,
        "Segundo Contraente",
        align="C",
        ln=1,
    )

    pdf.set_font("Times", "", 11)
    pdf.cell(largura_coluna, 6, senhorio["nome"], align="C")
    pdf.cell(
        largura_util - largura_coluna,
        6,
        cliente["nome"],
        align="C",
        ln=1,
    )

    # ---- gravar --------------------------------------------------
    pdf.output(str(caminho))

    return caminho
