"""Dashboard — o ecrã inicial da aplicação.

Responde à pergunta "como é que está o alojamento hoje?" num
relance, sem obrigar a navegar por cinco ecrãs. Quatro blocos:

1. KPIs (4 cartões) — os números de hoje.
2. Gráficos (2 lado a lado) — ocupação dos últimos 7 dias, e
   requisições por estado.
3. Alertas (lista) — o que exige atenção, cada linha clicável
   para o ecrã certo.
4. Ações rápidas (3 botões) — os atalhos mais usados no dia a dia.

Cada bloco tem um método `_construir_*` que só desenha e um método
`_*` (sem o prefixo) que só calcula. A separação não é decorativa:
permite testar os cálculos sem abrir a GUI, e permite uma futura
versão "refresh sem recriar" só troque os dados.

O `_recarregar()` existe desde já, mesmo sem botão "Atualizar" na
UI — os números ficam obsoletos se alguém criar um contrato noutro
ecrã e voltar ao Dashboard, e a infraestrutura está pronta para o
dia em que isso se resolver com um botão.

Camadas: só fala com os módulos de negócio (`unidades`,
`estoque`, `contratos`, `clientes`, `responsaveis`), nunca com
`repositorio` diretamente. Mesma disciplina do resto da GUI.

Sobre os alertas clicáveis: cada linha navega para o ecrã certo,
já com o filtro aplicado quando é possível. Isto é o que dá vida
ao painel — sem isto, "3 produtos abaixo do mínimo" obrigava a ir
a Stock → Produtos → procurar. Com isto, é um clique.

Sobre cores de alertas: cada alerta tem um chip com a cor do seu
peso. Amarelo = ação necessária (requisições pendentes, produtos
abaixo do mínimo, documentos a expirar). Cinza = não urgente
(clientes incompletos). Esta distinção evita que 4 alertas
diferentes pareçam todos igualmente urgentes.

ALTERAÇÕES 13/09/2026:

- `_ALTURA_GRAFICO` de 220 para 260 — com as margens corretas
  que o `componentes_graficos.py` passou a forçar, 220px deixava
  os rótulos do eixo X com pouca folga.
- `weight` dos gráficos de `14:10` para `12:12` — o gráfico de
  barras precisa de mais espaço horizontal para os nomes dos
  estados ("rejeitada", "pendente") caberem sem cortar. O de
  linhas tem 7 pontos, cabe bem em menos espaço.
"""

import datetime

import customtkinter as ctk

import clientes
import contratos
import estoque
import responsaveis
import unidades
from . import componentes
from . import componentes_graficos
from . import gui_est_comum
from . import tema

# Largura mínima dos cartões KPI. Com 4 cartões lado a lado a
# 1100px de janela útil, cada um fica com ~200px. O `uniform` do
# `grid_columnconfigure` força todos ao mesmo tamanho, mesmo que
# um conteúdo seja mais comprido — sem isto, o cartão "12/19" e o
# cartão "3" tinham larguras diferentes, e lia-se mal.
_LARGURA_MINIMA_KPI = 180


# Altura dos gráficos. Igual para os dois painéis, para ficarem à
# mesma altura lado a lado (é a única razão de ser uma constante e
# não um valor por gráfico).
#
# 260px (era 220px até 13/09/2026): com as margens corretas que o
# `tight_layout(pad=1.5)` do `componentes_graficos.py` agora força,
# 220 deixava os rótulos do eixo X com pouca folga e o conteúdo do
# gráfico comprimido entre os eixos. 260 dá o mínimo confortável.
_ALTURA_GRAFICO = 260


class Dashboard(ctk.CTkFrame):
    """Ecrã principal: KPIs, gráficos, alertas, ações rápidas.

    Recebe só `controlador` — sem argumentos específicos. Se algum
    dia precisar (ex.: abrir com um filtro pré-aplicado), é só
    acrescentar `**kwargs` ao `__init__` e passá-lo ao
    `mostrar_frame`; a assinatura do `Aplicacao.mostrar_frame` já
    aceita.
    """

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Dashboard").pack(fill="x")

        # Área com scroll — o Dashboard tem muito conteúdo (KPIs +
        # 2 gráficos + alertas + ações) e em janelas pequenas não
        # cabe tudo. Scroll vertical, sem scroll horizontal (o
        # `_construir_graficos` já garante que dois painéis cabem
        # lado a lado na largura mínima).
        self.area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.area.pack(fill="both", expand=True, padx=20, pady=(8, 16))

        self._construir_kpis()
        self._construir_graficos()
        self._construir_alertas()
        self._construir_acoes()

    # -----------------------------------------------------------------
    # Recarregamento
    # -----------------------------------------------------------------

    def _recarregar(self):
        """Reconstrói tudo do zero.

        Simples e correto: o Dashboard tem poucos widgets (4 KPIs,
        2 gráficos, no máximo 4 alertas, 3 botões), e reconstruir
        2 Figures de 7 pontos cada é instantâneo. Uma versão
        "refresh sem recriar" só compensaria se o ecrã tivesse
        dezenas de widgets — não é o caso.

        Hoje não é chamado por nenhum botão da UI, mas fica aqui
        porque a próxima iteração (botão "Atualizar" no cabeçalho,
        ou auto-refresh a cada X minutos) liga-se a este método.
        """
        for widget in self.area.winfo_children():
            widget.destroy()

        self._construir_kpis()
        self._construir_graficos()
        self._construir_alertas()
        self._construir_acoes()

    # -----------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------

    def _kpis(self):
        """Devolve os quatro números do topo, prontos a mostrar.

        Cada entrada é `(rotulo, valor, subtexto)`. Valores
        ausentes (denominador zero, por exemplo) ficam como "—" em
        vez de rebentar — o Dashboard tem de abrir sempre, mesmo
        numa base vazia.

        Os dois primeiros números vêm de `unidades.taxa_ocupacao`,
        a função agregada acrescentada hoje. Os dois últimos
        (entradas e saídas) contam ocupações cujo `data_inicio` ou
        `data_fim` é hoje — para os dois regimes (mensal e
        airbnb), porque um check-out de mensal é tão relevante
        como um check-out de Airbnb para quem está a gerir.
        """
        hoje = datetime.date.today()

        # Ocupação Airbnb
        airbnb_ocupados, airbnb_total = unidades.taxa_ocupacao(
            hoje, tipo="airbnb"
        )
        texto_airbnb = (
            f"{airbnb_ocupados}/{airbnb_total}" if airbnb_total else "—"
        )

        # Ocupação Mensal
        mensal_ocupados, mensal_total = unidades.taxa_ocupacao(
            hoje, tipo="mensal"
        )
        texto_mensal = (
            f"{mensal_ocupados}/{mensal_total}" if mensal_total else "—"
        )

        # Entradas e saídas de hoje — contam os dois regimes.
        # `listar` já devolve só as ativas por omissão, o que é o
        # que interessa: uma ocupação inativa não gera check-in
        # nenhum.
        entradas = 0
        saidas = 0

        for ocupacao in contratos.listar():
            if ocupacao["data_inicio"] == hoje:
                entradas += 1

            if ocupacao["data_fim"] == hoje:
                saidas += 1

        return [
            ("ocupação airbnb hoje", texto_airbnb, "unidades ocupadas"),
            ("lugares mensais", texto_mensal, "ocupados hoje"),
            ("entradas hoje", str(entradas), "check-ins"),
            ("saídas hoje", str(saidas), "check-outs"),
        ]

    def _construir_kpis(self):
        """Desenha a fila de quatro cartões.

        Os quatro cartões são `grid` com pesos iguais e `uniform`
        — força todos ao mesmo tamanho, mesmo com conteúdos de
        larguras diferentes ("12/19" vs "3"). Sem o `uniform`, o
        grid respeitava o tamanho natural de cada cartão e a fila
        ficava desalinhada.
        """
        contentor = ctk.CTkFrame(self.area, fg_color="transparent")
        contentor.pack(fill="x", pady=(0, 16))

        for coluna in range(4):
            contentor.grid_columnconfigure(coluna, weight=1, uniform="kpi")

        for indice, (rotulo, valor, subtexto) in enumerate(self._kpis()):
            self._desenhar_kpi(contentor, indice, rotulo, valor, subtexto)

    def _desenhar_kpi(self, master, coluna, rotulo, valor, subtexto):
        """Desenha um cartão de KPI.

        Cartão com borda tracejada — o único sítio da aplicação
        que usa `border_*` a tracejar (os outros usam linha
        contínua). É intencional: os KPIs não são "coisas onde se
        clica", são "coisas onde se olha". O tracejado diz isso.
        """
        cartao = ctk.CTkFrame(
            master,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.grid(row=0, column=coluna, sticky="nsew", padx=6)

        ctk.CTkLabel(
            cartao,
            text=rotulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            cartao,
            text=valor,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=26, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=16)

        ctk.CTkLabel(
            cartao,
            text=subtexto,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 14))

    # -----------------------------------------------------------------
    # Gráficos
    # -----------------------------------------------------------------

    def _series_ocupacao(self):
        """Séries para o gráfico de ocupação dos últimos 7 dias.

        Devolve `(rotulos, airbnb, mensal)` — três listas paralelas:

        - `rotulos`: strings tipo "seg 8" (dia da semana + dia do
          mês).
        - `airbnb` e `mensal`: floats entre 0 e 1, ou 0 se o
          regime não tiver nenhuma unidade ativa nesse dia.

        "0" quando o denominador é zero é melhor do que `None`:
        uma linha que desaparece porque falta um ponto confunde
        mais do que uma linha que desce a 0% (e o utilizador vê
        logo que não há unidades, o que é uma informação útil).

        O nome do dia da semana vem da mesma tabela do
        `gui_calendario.py` (não uso `strftime("%a")` porque sem
        locale dá inglês) — a consistência com o Calendário vale
        mais do que uma linha de código a menos.
        """
        nomes_dias = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
        rotulos = []
        airbnb = []
        mensal = []

        hoje = datetime.date.today()

        # Do mais antigo para o mais recente — os 7 dias incluem
        # hoje, e é o último ponto do gráfico que é o "agora".
        for deslocamento in range(6, -1, -1):
            dia = hoje - datetime.timedelta(days=deslocamento)
            rotulos.append(f"{nomes_dias[dia.weekday()]} {dia.day}")

            ocupados, total = unidades.taxa_ocupacao(dia, tipo="airbnb")
            airbnb.append(ocupados / total if total else 0)

            ocupados, total = unidades.taxa_ocupacao(dia, tipo="mensal")
            mensal.append(ocupados / total if total else 0)

        return rotulos, airbnb, mensal

    def _contagem_requisicoes(self):
        """Devolve `(estados, contagens)` para o gráfico de barras.

        `estados` é a ordem em que as barras aparecem, do que
        exige ação para o que não exige. É esta a ordem que faz
        sentido olhar de manhã: pendentes primeiro (há algo para
        fazer), fechadas por último (já resolvido).
        """
        estados = ("pendente", "enviada", "fechada", "rejeitada")
        contagens = []

        for estado in estados:
            contagens.append(len(estoque.listar_requisicoes(estado=estado)))

        return list(estados), contagens

    def _construir_graficos(self):
        """Desenha os dois gráficos lado a lado.

        Proporção 12 : 12 (era 14 : 10 até 13/09/2026) — o gráfico
        de barras precisava de mais espaço horizontal para os nomes
        dos estados ("rejeitada", "pendente") caberem sem cortar à
        esquerda. O de linhas tem 7 pontos e cabe bem em metade da
        largura, por isso não perde nada em ficar mais estreito.

        Cada gráfico é embrulhado num painel com borda e título,
        para ler como "bloco de informação" e não como "linhas
        soltas no meio do ecrã". É a mesma convenção do resto da
        aplicação (os cartões do hub de Stock também são painéis
        com borda e título).
        """
        contentor = ctk.CTkFrame(self.area, fg_color="transparent")
        contentor.pack(fill="x", pady=(0, 16))

        contentor.grid_columnconfigure(0, weight=12, uniform="grafico")
        contentor.grid_columnconfigure(1, weight=12, uniform="grafico")

        self._construir_grafico_ocupacao(contentor)
        self._construir_grafico_requisicoes(contentor)

    def _construir_grafico_ocupacao(self, master):
        """Painel do gráfico de ocupação (linhas)."""
        painel = self._criar_painel_grafico(
            master, "ocupação · últimos 7 dias"
        )
        painel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        rotulos, airbnb, mensal = self._series_ocupacao()

        grafico = componentes_graficos.GraficoOcupacao(
            painel, altura=_ALTURA_GRAFICO
        )
        grafico.pack(fill="both", expand=True)
        grafico.atualizar(rotulos=rotulos, airbnb=airbnb, mensal=mensal)

    def _construir_grafico_requisicoes(self, master):
        """Painel do gráfico de requisições (barras).

        Se todas as contagens forem 0, o gráfico não teria nada
        para mostrar — e o `ax.barh` com todas as barras a 0
        desenhava 4 linhas minúsculas, o que é feio. Mostro uma
        mensagem em vez do gráfico. É uma decisão de apresentação,
        por isso vive aqui e não no `GraficoRequisicoes`.
        """
        painel = self._criar_painel_grafico(master, "requisições por estado")
        painel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        estados, contagens = self._contagem_requisicoes()

        if not any(contagens):
            ctk.CTkLabel(
                painel,
                text="Sem requisições registadas.",
                text_color=tema.COR_TEXTO_SECUNDARIO,
                font=ctk.CTkFont(size=12),
            ).pack(expand=True, pady=60)
            return

        grafico = componentes_graficos.GraficoRequisicoes(
            painel, altura=_ALTURA_GRAFICO
        )
        grafico.pack(fill="both", expand=True)
        grafico.atualizar(
            estados=estados,
            contagens=contagens,
            cores=gui_est_comum.CORES_ESTADO,
        )

    def _criar_painel_grafico(self, master, titulo):
        """Cria e devolve um painel vazio com título — a moldura
        comum dos dois gráficos. O gráfico em si é acrescentado
        por quem chama, depois de receber o painel de volta.
        """
        painel = ctk.CTkFrame(
            master,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )

        ctk.CTkLabel(
            painel,
            text=titulo,
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 6))

        return painel

    # -----------------------------------------------------------------
    # Alertas
    # -----------------------------------------------------------------

    def _alertas(self):
        """Devolve a lista de alertas a mostrar.

        Cada alerta é um dicionário com quatro campos:

        - 'texto': a frase completa (ex.: "3 produtos abaixo do mínimo").
        - 'peso': "aviso" (amarelo) ou "info" (cinza) — a cor do chip.
        - 'ecra': a classe do ecrã a abrir no clique, ou None se
          não houver destino.
        - 'kwargs': argumentos extra a passar a `mostrar_frame`
          (ex.: um filtro pré-aplicado). Vazio por omissão.

        Os quatro alertas possíveis (nesta ordem, do mais urgente
        para o menos):

        1. Requisições pendentes — se houver alguma.
        2. Produtos abaixo do stock mínimo — se houver algum.
        3. Contratos com documento a expirar — se houver algum.
        4. Clientes incompletos — se houver algum.

        Os que não têm nada a dizer não aparecem — um alerta a
        dizer "0 requisições pendentes" é ruído, não é informação.
        """
        alertas = []

        # 1. Requisições pendentes
        pendentes = estoque.listar_requisicoes(estado="pendente")

        if pendentes:
            alertas.append(
                {
                    "texto": (
                        f"{len(pendentes)} "
                        f"{'requisição' if len(pendentes) == 1 else 'requisições'} "
                        f"de stock "
                        f"{'pendente' if len(pendentes) == 1 else 'pendentes'}"
                    ),
                    "peso": "aviso",
                    "ecra": "ListaAprovacao",
                    "kwargs": {},
                }
            )

        # 2. Produtos abaixo do mínimo
        abaixo = estoque.listar_alertas_stock()

        if abaixo:
            alertas.append(
                {
                    "texto": (
                        f"{len(abaixo)} "
                        f"{'produto' if len(abaixo) == 1 else 'produtos'} "
                        f"abaixo do mínimo"
                    ),
                    "peso": "aviso",
                    "ecra": "ListaProdutos",
                    "kwargs": {},
                }
            )

        # 3. Contratos com documento a expirar — os dois regimes.
        # Uso `aviso_documento=True` (filtro que já existe) em vez
        # de comparar datas aqui: a regra de "o que é um documento
        # a expirar" já vive em `contratos.py`, e duplicá-la aqui
        # era pedir para divergirem.
        avisos = contratos.listar(aviso_documento=True)
        # Exclui inativas — o `listar` por omissão devolve as
        # ativas; se um dia a assinatura mudar, este filtro
        # defensivo evita contar contratos encerrados.
        avisos = [o for o in avisos if o.get("ativo", True)]

        if avisos:
            alertas.append(
                {
                    "texto": (
                        f"{len(avisos)} "
                        f"{'contrato' if len(avisos) == 1 else 'contratos'} "
                        f"com documento a expirar"
                    ),
                    "peso": "aviso",
                    "ecra": "ListaContratosMensais",
                    "kwargs": {},
                }
            )

        # 4. Clientes incompletos
        incompletos = clientes.listar(incompleto=True)

        if incompletos:
            alertas.append(
                {
                    "texto": (
                        f"{len(incompletos)} "
                        f"{'cliente' if len(incompletos) == 1 else 'clientes'} "
                        f"com dados incompletos"
                    ),
                    "peso": "info",
                    "ecra": "ListaClientes",
                    "kwargs": {},
                }
            )

        return alertas

    def _construir_alertas(self):
        """Desenha o painel de alertas.

        Se não houver alertas nenhuns, mostra "Tudo em ordem." em
        vez de esconder o painel: um painel que desaparece quando
        está tudo bem faz o utilizador pensar que a app se
        esqueceu dele.
        """
        painel = ctk.CTkFrame(
            self.area,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        painel.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            painel,
            text="alertas",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 6))

        alertas = self._alertas()

        if not alertas:
            ctk.CTkLabel(
                painel,
                text="✓  Tudo em ordem. Sem alertas.",
                text_color=tema.TEXTO_LIVRE,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).pack(fill="x", padx=16, pady=(4, 14))
            return

        for alerta in alertas:
            self._desenhar_alerta(painel, alerta)

        # Pequeno respiro em baixo do último alerta
        ctk.CTkFrame(painel, height=6, fg_color="transparent").pack()

    def _desenhar_alerta(self, master, alerta):
        """Desenha uma linha de alerta — clique navega para o ecrã.

        Cada alerta é uma linha horizontal com: um chip colorido
        (o "peso"), o texto, e uma seta "›" à direita. A linha
        inteira é clicável, não só o texto — o utilizador não
        devia ter de apontar ao pixel certo.

        A resolução do "ecra" (que é uma string, não uma classe)
        para a classe real é feita por `_resolver_ecra`, porque
        importar aqui no topo criaria imports circulares: o
        `gui_est_aprovacao.py` importa `gui_est_requisicoes.py`,
        que importa `gui_contratos.py`, que importa
        `gui_propriedades.py`, que importa este ficheiro. O
        caminho seguro é importar tarde, dentro da função de
        clique.
        """
        cor_chip = (
            (tema.AMARELO_AVISO, tema.TEXTO_AVISO)
            if alerta["peso"] == "aviso"
            else (tema.CINZA_INDISPONIVEL, tema.TEXTO_INDISPONIVEL)
        )

        linha = ctk.CTkFrame(
            master,
            fg_color="transparent",
            cursor="hand2",
            height=32,
        )
        linha.pack(fill="x", padx=16, pady=2)
        linha.pack_propagate(False)

        # Extrai o primeiro número do texto para o chip — o texto
        # é "N coisas...", e o chip mostra só "N". Isto poupa uma
        # estrutura de dados extra: o alerta já tem o número
        # embutido no texto, e extraí-lo aqui é mais simples do
        # que obrigar todos os `_alertas` a devolver o número
        # separado.
        numero = alerta["texto"].split(" ", 1)[0]

        ctk.CTkLabel(
            linha,
            text=numero,
            text_color=cor_chip[1],
            fg_color=cor_chip[0],
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=30,
            height=22,
        ).pack(side="left", padx=(0, 10))

        # O texto completo, sem o número (já está no chip)
        texto_restante = alerta["texto"].split(" ", 1)[1]

        ctk.CTkLabel(
            linha,
            text=texto_restante,
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            linha,
            text="›",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=14),
        ).pack(side="right", padx=(10, 0))

        # Clique na linha inteira navega — o `_navegar_alerta`
        # resolve o nome do ecrã (string) para a classe real e
        # chama `mostrar_frame`.
        linha.bind(
            "<Button-1>",
            lambda _e, a=alerta: self._navegar_alerta(a),
        )

        # Em Tkinter, o clique num widget-filho não propaga para o
        # pai — ligar o binding da linha não chega. É preciso
        # ligá-lo a cada filho também.
        for filho in linha.winfo_children():
            filho.bind(
                "<Button-1>",
                lambda _e, a=alerta: self._navegar_alerta(a),
            )
            filho.configure(cursor="hand2")

    def _navegar_alerta(self, alerta):
        """Resolve o nome do ecrã e navega — chamado ao clicar
        numa linha de alerta."""
        if not alerta["ecra"]:
            return

        classe = self._resolver_ecra(alerta["ecra"])

        if classe is not None:
            self.controlador.mostrar_frame(classe, **alerta["kwargs"])

    def _resolver_ecra(self, nome):
        """Converte um nome de ecrã (string) para a classe real.

        Existe para evitar imports circulares no topo do ficheiro:
        este Dashboard é importado pelo `app.py`, que também
        importa os ecrãs todos. Se este ficheiro importasse
        `ListaAprovacao` no topo, criava um ciclo com o
        `gui_est_aprovacao.py` → `gui_est_requisicoes.py` →
        `gui_est_hub.py` → `app.py`.

        Importar dentro desta função, só quando é mesmo preciso,
        evita o ciclo sem custo nenhum (o Python guarda os
        módulos importados em cache, por isso importar duas vezes
        não lê o ficheiro duas vezes).

        Devolve None se o nome não corresponder a nenhum ecrã —
        mais vale não navegar do que rebentar num clique.
        """
        if nome == "ListaAprovacao":
            from .gui_est_aprovacao import ListaAprovacao

            return ListaAprovacao

        if nome == "ListaProdutos":
            from .gui_est_produtos import ListaProdutos

            return ListaProdutos

        if nome == "ListaContratosMensais":
            from .gui_contratos import ListaContratosMensais

            return ListaContratosMensais

        if nome == "ListaClientes":
            from .gui_clientes import ListaClientes

            return ListaClientes

        return None

    # -----------------------------------------------------------------
    # Ações rápidas
    # -----------------------------------------------------------------

    def _construir_acoes(self):
        """Desenha os três botões de ação rápida.

        São os três modais de criação mais usados no dia a dia.
        Os modais em si já existem nos ecrãs respetivos — este
        painel só os abre aqui, sem duplicar código.
        """
        painel = ctk.CTkFrame(
            self.area,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        painel.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            painel,
            text="ações rápidas",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 6))

        linha = ctk.CTkFrame(painel, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=(0, 14))

        for coluna in range(3):
            linha.grid_columnconfigure(coluna, weight=1, uniform="acao")

        self._botao_acao(linha, 0, "Nova reserva", self._nova_reserva)
        self._botao_acao(linha, 1, "Novo contrato", self._novo_contrato)
        self._botao_acao(linha, 2, "Novo cliente", self._novo_cliente)

    def _botao_acao(self, master, coluna, texto, comando):
        """Botão de ação rápida — mesma forma em todos.

        Contorno simples em vez de fundo colorido: são atalhos,
        não ações primárias (essas têm o azul da marca, dentro dos
        ecrãs). Um fundo azul aqui, três vezes seguido, roubava o
        foco aos KPIs logo acima.
        """
        ctk.CTkButton(
            master,
            text=texto,
            height=40,
            corner_radius=tema.RAIO_BOTAO,
            fg_color="transparent",
            border_width=1,
            border_color=tema.COR_BORDA,
            text_color=tema.COR_TEXTO,
            hover_color=tema.COR_BORDA,
            command=comando,
        ).grid(row=0, column=coluna, sticky="ew", padx=4)

    def _nova_reserva(self):
        """Abre o modal de Nova Reserva Airbnb, importado tarde
        para evitar ciclo (ver `_resolver_ecra`)."""
        from .gui_contratos import NovaReservaAirbnbModal

        NovaReservaAirbnbModal(self)

    def _novo_contrato(self):
        """Abre o modal de Novo Contrato Mensal."""
        from .gui_contratos import NovoContratoModal

        NovoContratoModal(self)

    def _novo_cliente(self):
        """Abre o modal de Novo Cliente."""
        from .gui_clientes import NovoClienteModal

        NovoClienteModal(self)
