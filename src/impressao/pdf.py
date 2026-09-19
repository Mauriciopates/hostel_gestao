"""Geração de PDFs — contratos e relatórios.

Este módulo é o único sítio do projeto que desenha PDFs. Tem duas
funções públicas:

  - `gerar_contrato_pdf(...)` — o contrato mensal, transcrito da
    minuta original.
  - `gerar_relatorio_pdf(...)` — um relatório tabular (os 12 do
    `gui_relatorios.py`).

REGRA CRÍTICA herdada do `impressao.py` original: qualquer texto
que vá para dentro do PDF tem de ser Latin-1. As fontes core do
fpdf (`Times`, `Helvetica`, `Courier`) não incluem `€`,
travessões longos, aspas curvas, nem reticências tipográficas.
Se aparecerem, o fpdf rebenta com "Character 'X' is outside the
range of characters supported by the font used".

Para o programador não ter de se lembrar disto, existe uma função
`base.sanitizar_texto_pdf` que troca esses caracteres por
equivalentes ASCII. TODOS os textos que entram em `pdf.cell` ou
`pdf.multi_cell` neste ficheiro passam por ela. É a rede de
segurança — e resolve o bug do `€` que o aluno apanhou em
19/09/2026 (o PDF do relatório "Receita por unidade" rebentava
porque o valor `50,00 €` tinha o símbolo de euro).
"""

from datetime import date
from pathlib import Path

from fpdf import FPDF

import config
from . import base

# =====================================================================
# CAMINHO DAS IMAGENS
# =====================================================================
#
# Mesma técnica do `componentes.py`: o caminho calcula-se a partir
# do `__file__` deste módulo, para funcionar independentemente do
# sítio de onde a aplicação é corrida. O `resolve()` normaliza o
# caminho antes de o usar.
#
# Este `pdf.py` está em `src/impressao/`. O `img/` está na raiz do
# projeto. Logo: `../../img/`.

_PASTA_IMG = Path(__file__).resolve().parent.parent.parent / "img"
_LOGO_PDF = _PASTA_IMG / "ico_hostel_transparente.png"


# =====================================================================
# CABEÇALHO E RODAPÉ COMUNS AOS RELATÓRIOS
# =====================================================================


def _desenhar_cabecalho(pdf, titulo, data_inicio, data_fim):
    """Desenha o cabeçalho comum a todos os relatórios.

    Título à esquerda, meta (período + data de geração) por baixo,
    logo no canto superior direito. Não devolve nada — desenha
    diretamente no `pdf` que recebe.

    Este cabeçalho repete-se igual em todos os relatórios, e só
    muda o título e o período. Ter a função separada evita
    duplicar as coordenadas do logo e as fontes sempre que um
    relatório novo aparecer.

    Usa `base.sanitizar_texto_pdf` nos textos — os relatórios que
    a chamam devem continuar a fazê-lo por dentro, mas aqui
    protegemos também o título e a meta, por segurança.

    O `x` e o `y` do logo são calculados a partir das margens
    atuais do PDF (`pdf.l_margin`/`pdf.r_margin`/`pdf.t_margin`),
    não valores fixos — se um dia as margens mudarem, o logo
    acompanha.
    """
    largura_util = pdf.w - pdf.l_margin - pdf.r_margin

    # ---- Logo à direita -----------------------------------------
    # 25mm de largura, altura proporcional (o fpdf calcula-a).
    largura_logo = 25
    x_logo = pdf.w - pdf.r_margin - largura_logo
    y_logo = pdf.t_margin

    try:
        pdf.image(str(_LOGO_PDF), x=x_logo, y=y_logo, w=largura_logo)
    except (FileNotFoundError, OSError):
        # Sem logo, o cabeçalho fica só com texto — não rebenta
        # por causa de uma imagem em falta.
        pass

    # ---- Título à esquerda --------------------------------------
    # Limitamos a largura do texto do título à largura útil menos
    # o espaço do logo, para nunca se sobreporem visualmente.
    largura_texto = largura_util - largura_logo - 5

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(
        largura_texto,
        8,
        base.sanitizar_texto_pdf(titulo),
        ln=1,
    )

    # ---- Meta (período + data) ----------------------------------
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 107, 122)
    pdf.cell(
        largura_texto,
        5,
        base.sanitizar_texto_pdf(
            f"Periodo: {data_inicio.strftime('%d/%m/%Y')} a "
            f"{data_fim.strftime('%d/%m/%Y')} "
            f"| Gerado em {date.today().strftime('%d/%m/%Y')}"
        ),
        ln=1,
    )
    pdf.set_text_color(0, 0, 0)


def _desenhar_rodape(pdf):
    """Desenha o rodapé comum a todos os relatórios.

    Copyright à esquerda, número de página à direita. Sem cor
    forte: cinza secundário e itálico, para o rodapé não competir
    visualmente com o conteúdo.

    Chamado uma vez por página, pelo `gerar_relatorio_pdf`, no
    fim de desenhar os dados. Se um dia os relatórios passarem de
    uma página, o sítio certo para o repetir é depois de cada
    `pdf.add_page()`.
    """
    largura_util = pdf.w - pdf.l_margin - pdf.r_margin

    # Vai para o fundo da página. `pdf.h` é a altura total do
    # papel; 15mm acima do fim deixa o rodapé na zona do "canto
    # inferior" sem encostar à margem.
    y_rodape = pdf.h - 15
    pdf.set_y(y_rodape)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(90, 107, 122)

    # Copyright à esquerda — usa metade da largura útil e alinha
    # à esquerda.
    pdf.cell(
        largura_util / 2,
        5,
        base.sanitizar_texto_pdf("© 2026 Hostel Clean"),
        align="L",
    )

    # Número de página à direita — a outra metade da largura, com
    # `ln=1` para fechar a linha.
    pdf.cell(
        largura_util / 2,
        5,
        base.sanitizar_texto_pdf(f"Página {pdf.page_no()}"),
        align="R",
        ln=1,
    )

    # Repõe a cor do texto para preto, para não afetar quem venha
    # a desenhar depois.
    pdf.set_text_color(0, 0, 0)


# =====================================================================
# CONTRATO MENSAL
# =====================================================================


def _caminho_contrato(ocupacao_id):
    """Constrói o caminho completo do PDF do contrato.

    Formato: `CNT-003_2026-09-13_15h42.pdf`, dentro de
    `config.DIR_CONTRATOS` — o ID do contrato, a data e a hora a
    que foi gerado. A hora resolve o problema de gerar o mesmo
    contrato duas vezes no mesmo dia, sem sobrescrever o primeiro.
    """
    config.garantir_diretorios()

    agora = date.today()
    from datetime import datetime

    hora_minuto = datetime.now().strftime("%Hh%M")

    nome = f"{ocupacao_id}_{agora.isoformat()}_{hora_minuto}.pdf"

    return config.DIR_CONTRATOS / nome


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
    """
    caminho = _caminho_contrato(ocupacao["id"])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

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
    pdf.set_font("Times", "", 11)
    pdf.multi_cell(
        largura_util,
        6,
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
            f"1. O presente contrato de arrendamento e feito pelo "
            f"prazo de 3 meses, tendo o seu inicio a "
            f"{base.formatar_data_pt(ocupacao['data_inicio'])}."
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
            f"1. A renda mensal pelo presente arrendamento e de "
            f"{base.formatar_valor_pt(mensal['renda_praticada'])} "
            f"euros, que devera ser paga entre o 1. e o "
            f"{mensal['dia_vencimento']}. dia do mes a que disser "
            f"respeito, atraves de deposito ou transferencia para o "
            f"IBAN {propriedade.get('iban') or '-'}."
        ),
        align="J",
    )
    pdf.ln(2)
    pdf.multi_cell(
        largura_util,
        6,
        base.sanitizar_texto_pdf(
            "2. Com a assinatura do presente Contrato, o Segundo "
            "Contraente paga as seguintes quantias:"
        ),
        align="J",
    )
    pdf.ln(1)
    pdf.multi_cell(
        largura_util,
        6,
        base.sanitizar_texto_pdf(
            f"a) {base.formatar_valor_pt(mensal['renda_praticada'])} "
            f"euros, a titulo de pagamento da renda correspondente "
            f"a cada mes;"
        ),
        align="J",
    )
    pdf.ln(1)
    pdf.multi_cell(
        largura_util,
        6,
        base.sanitizar_texto_pdf(
            f"b) {base.formatar_valor_pt(mensal['caucao'])} euros, "
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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
        base.sanitizar_texto_pdf(
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

    # ---- parágrafo final ----------------------------------------
    pdf.multi_cell(
        largura_util,
        6,
        base.sanitizar_texto_pdf(
            "Este contrato foi celebrado em dois documentos "
            "originais, declarando as partes contratantes dispensar "
            "o reconhecimento notarial, nao podendo tal facto ser "
            "invocado por qualquer das partes como vicio, nulidade "
            "ou anulabilidade do mesmo."
        ),
        align="J",
    )
    pdf.ln(8)

    # ---- local e data de assinatura -----------------------------
    hoje = date.today()
    pdf.multi_cell(
        largura_util,
        6,
        base.sanitizar_texto_pdf(
            f"{local}, {hoje.day:02d} / {hoje.month:02d} / {hoje.year}"
        ),
    )
    pdf.ln(20)

    # ---- zona de assinaturas ------------------------------------
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
    pdf.cell(
        largura_coluna,
        6,
        base.sanitizar_texto_pdf(senhorio["nome"]),
        align="C",
    )
    pdf.cell(
        largura_util - largura_coluna,
        6,
        base.sanitizar_texto_pdf(cliente["nome"]),
        align="C",
        ln=1,
    )

    pdf.output(str(caminho))
    return caminho


# =====================================================================
# RELATÓRIO TABULAR
# =====================================================================


def _caminho_relatorio(area, relatorio_id, data_inicio, data_fim):
    """Constrói o caminho completo do PDF de um relatório.

    Usa o `base.nome_base_relatorio` (que já inclui a hora no fim)
    e acrescenta a extensão `.pdf`. Grava dentro de
    `config.DIR_RELATORIOS`.
    """
    prefixo = base.nome_base_relatorio(
        area, relatorio_id, data_inicio, data_fim
    )
    return base.pasta_relatorios() / f"{prefixo}.pdf"


def gerar_relatorio_pdf(
    titulo,
    colunas,
    linhas,
    area,
    relatorio_id,
    data_inicio,
    data_fim,
):
    """Gera um PDF com o conteúdo de um relatório.

    Parâmetros:
      - `titulo`:     o título do relatório (usado no cabeçalho).
      - `colunas`:    tuplo de strings, os nomes das colunas.
      - `linhas`:     lista de listas; cada lista interna é uma linha,
                      com o mesmo número de elementos de `colunas`.
                      Cada célula pode ser `str`, `Decimal` ou
                      `date` — este módulo trata da conversão para
                      texto formatado em PT-PT.
      - `area`:       chave da área ('financeiro', 'contratos',
                      'stock').
      - `relatorio_id`: id do relatório ('resultado', etc.).
      - `data_inicio`: `date` — primeira data do período.
      - `data_fim`:   `date` — última data do período (inclusiva).

    Devolve o `Path` do ficheiro gerado.

    Estrutura do PDF:
      - Cabeçalho: título a bold, período + data de geração.
      - Tabela: cabeçalho das colunas em faixa cinza, uma linha
        por registo, com zebra para leitura.
      - Rodapé: número de registos + nota "Hostel Gestao".

    TODOS os textos passam por `base.sanitizar_texto_pdf` — o
    símbolo de euro é substituído por "EUR" antes de entrar no
    PDF, e valores são pré-formatados com `base.formatar_valor_pt`.
    Ver a docstring do módulo para o porquê.
    """
    caminho = _caminho_relatorio(area, relatorio_id, data_inicio, data_fim)

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(left=15, top=15, right=15)

    largura_util = pdf.w - pdf.l_margin - pdf.r_margin

    # ---- Cabeçalho (com logo) -----------------------------------
    _desenhar_cabecalho(pdf, titulo, data_inicio, data_fim)
    pdf.ln(6)

    # ---- Larguras das colunas -----------------------------------
    n_colunas = len(colunas)
    if n_colunas == 0:
        # Sem colunas — só o cabeçalho. Não devia acontecer, mas
        # protege-se.
        _desenhar_rodape(pdf)
        pdf.output(str(caminho))
        return caminho

    largura_primeira = largura_util * 0.40
    largura_outras = (
        (largura_util - largura_primeira) / (n_colunas - 1)
        if n_colunas > 1
        else 0
    )
    larguras = [largura_primeira] + [largura_outras] * (n_colunas - 1)

    altura_linha = 7
    cor_cabecalho = (245, 246, 249)  # #F5F6F9
    cor_zebra = (247, 249, 251)  # #F7F9FB
    cor_branca = (255, 255, 255)
    cor_linha = (208, 208, 208)  # #D0D0D0

    # ---- Cabeçalho da tabela (com fundo cinza) ------------------
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*cor_cabecalho)
    pdf.set_text_color(90, 107, 122)

    # Guardamos o y onde o cabeçalho começa — vamos precisar dele
    # no fim, para desenhar as linhas verticais da grelha.
    y_inicio_tabela = pdf.get_y()

    for i, coluna in enumerate(colunas):
        pdf.cell(
            larguras[i],
            altura_linha,
            base.sanitizar_texto_pdf(str(coluna).upper()),
            border=0,
            align="L",
            fill=True,
        )
    pdf.ln()

    y_fim_cabecalho = pdf.get_y()

    # ---- Linha horizontal no fundo do cabeçalho -----------------
    pdf.set_draw_color(*cor_linha)
    pdf.set_line_width(0.2)
    pdf.line(
        pdf.l_margin,
        y_fim_cabecalho,
        pdf.w - pdf.r_margin,
        y_fim_cabecalho,
    )

    # ---- Linhas de dados ----------------------------------------
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)

    zebra = False
    for linha in linhas:
        if zebra:
            pdf.set_fill_color(*cor_zebra)
        else:
            pdf.set_fill_color(*cor_branca)

        for i, celula in enumerate(linha):
            texto = _celula_para_pdf(celula)

            pdf.cell(
                larguras[i],
                altura_linha,
                base.sanitizar_texto_pdf(texto),
                border=0,
                align="L",
                fill=True,
            )
        pdf.ln()

        # Linha horizontal no fundo de cada linha de dados.
        y_atual = pdf.get_y()
        pdf.line(
            pdf.l_margin,
            y_atual,
            pdf.w - pdf.r_margin,
            y_atual,
        )

        zebra = not zebra

    y_fim_tabela = pdf.get_y()

    # ---- Linhas verticais (grelha) ------------------------------
    # Desenhadas no fim, para não interferirem com o `cell`.
    # A primeira vai no `l_margin`, a última no `r_margin`, e as
    # intermédias nas fronteiras entre colunas.
    x_coluna = pdf.l_margin
    for i in range(len(larguras) - 1):
        x_coluna += larguras[i]
        pdf.line(x_coluna, y_inicio_tabela, x_coluna, y_fim_tabela)

    # Borda exterior da tabela — esquerda e direita.
    pdf.line(
        pdf.l_margin,
        y_inicio_tabela,
        pdf.l_margin,
        y_fim_tabela,
    )
    pdf.line(
        pdf.w - pdf.r_margin,
        y_inicio_tabela,
        pdf.w - pdf.r_margin,
        y_fim_tabela,
    )

    # ---- Rodapé -------------------------------------------------
    # Desligar a quebra automática antes de desenhar o rodapé.
    # Sem isto, o `set_y(pdf.h - 15)` que o rodapé usa fica
    # dentro da margem de quebra (20mm) e o fpdf salta para
    # uma página nova a meio do rodapé.
    pdf.set_auto_page_break(auto=False)
    _desenhar_rodape(pdf)

    pdf.output(str(caminho))
    return caminho


def _celula_para_pdf(celula):
    """Converte uma célula para texto pronto a entrar no PDF.

    Aceita `str`, `Decimal`, `int` ou `date` — a origem é a lista
    `linhas` de cada relatório. Devolve sempre uma string.

    Valores monetários (Decimal) saem formatados em PT-PT
    (`4.200,00 €`), datas em ISO com barras (`01/09/2026`). O
    `€` é depois substituído por `EUR` na sanitização — por isso
    este método não se preocupa com isso.
    """
    from decimal import Decimal

    if celula is None:
        return "-"

    if isinstance(celula, Decimal):
        return base.formatar_valor_pt(celula)

    if isinstance(celula, date):
        return base.formatar_data_pt(celula)

    return str(celula)
