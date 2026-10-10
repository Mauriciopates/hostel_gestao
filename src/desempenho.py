"""Medição de desempenho dos ecrãs — modo `--desempenho` (v2.2.0).

Corre-se com `HostelGestao.exe --desempenho` (ou
`python src/main_gui.py --desempenho`): depois do login normal, um
Master vê a aplicação abrir sozinha cada ecrã do menu (e os ecrãs dos
hubs) três vezes, e no fim abre um relatório HTML com o tempo de cada
um, quanto desse tempo foi base de dados, construção de widgets e
desenho, e quantas consultas fez.

Nasceu da ferramenta `ferramentas/perfil/medir_ecras.py` (09/10/2026),
que só corria no PC de desenvolvimento. O aluno precisava dos números
DENTRO do Sin-11 (o cliente de teste em VMware), onde a app é o
executável — decisão de 10/10/2026: o mesmo executável com uma opção
de arranque, em vez de um segundo .exe.

Este módulo não desenha nada (isso é o `gui/gui_desempenho.py`) nem
grava ficheiros (isso é o `impressao/desempenho.py`). Tem:

- o "embrulho" do `mysql.connector.connect` que cronometra cada
  consulta (`instrumentar_mysql`) — ativado só neste modo, logo no
  arranque, antes de abrir qualquer ligação;
- as contas que transformam N aberturas de um ecrã numa linha do
  relatório (`juntar_repeticoes`, `sugerir`, `estado_de`).
"""

import re
import statistics
import time

# Opção de arranque que liga este modo.
OPCAO_ARRANQUE = "--desempenho"

# Quantas vezes cada ecrã é aberto (decisão de 10/10/2026).
REPETICOES = 3

# Limites do estado de cada ecrã, em milissegundos.
LIMITE_OK_MS = 300
LIMITE_LENTO_MS = 800

# Ecrãs que GRAVAM na base só por serem abertos — ficam de fora da
# medição (decisão de 10/10/2026). O hub de Despesas lança as despesas
# recorrentes do mês ao abrir (`EcraDespesas._gerar_recorrencias`).
# Chave = nome da classe do ecrã.
ECRAS_QUE_GRAVAM = {
    "EcraDespesas": "lança as despesas recorrentes do mês ao abrir",
}

# Ecrãs abertos a partir dos hubs (não estão no menu lateral):
# (nome a mostrar, módulo, classe).
SUB_ECRAS = (
    ("Despesas › Lista", "gui.despesas.gui_desp_lista", "ListaDespesas"),
    ("Despesas › Aprovações", "gui.despesas.gui_desp_aprovacao",
     "Aprovacoes"),
    ("Despesas › Categorias", "gui.despesas.gui_desp_categorias",
     "Categorias"),
    ("Despesas › Fornecedores", "gui.despesas.gui_desp_fornecedores",
     "Fornecedores"),
    ("Stock › Requisições", "gui.estoque.gui_est_requisicoes",
     "ListaRequisicoes"),
    ("Stock › Rota de Envio", "gui.estoque.gui_est_aprovacao",
     "ListaAprovacao"),
    ("Stock › Devoluções", "gui.estoque.gui_est_devolucoes",
     "ListaDevolucoes"),
    ("Stock › Produtos", "gui.estoque.gui_est_produtos", "ListaProdutos"),
    ("Stock › Movimentos", "gui.estoque.gui_est_movimentos",
     "ListaMovimentos"),
    ("Stock › Regras do rol", "gui.estoque.gui_est_regras_rol",
     "RegrasRol"),
)

_ESCRITA = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|REPLACE|TRUNCATE|ALTER|CREATE|DROP)\b",
    re.I,
)


# =====================================================================
# Recolha (base de dados)
# =====================================================================


class _Estado:
    """Tudo o que o embrulho da base de dados vai vendo."""

    def __init__(self):
        self.consultas = []  # dicts: sql, ms, escrita
        self.ligacoes = []  # ms de cada connect()

    def marca(self):
        """Posição atual — para depois saber o que veio a seguir."""
        return len(self.consultas), len(self.ligacoes)

    def desde(self, marca):
        """(consultas, ligações) feitas desde `marca`."""
        return self.consultas[marca[0]:], self.ligacoes[marca[1]:]


ESTADO = _Estado()


def e_escrita(sql):
    """True se o SQL grava (INSERT, UPDATE, DELETE, ...)."""
    return bool(_ESCRITA.match(str(sql)))


class _Cursor:
    """Embrulho de um cursor: cronometra execute e fetch."""

    def __init__(self, real):
        self._real = real
        self._ultimo = None

    def _correr(self, nome, operacao, *args, **kwargs):
        inicio = time.perf_counter()
        try:
            return getattr(self._real, nome)(operacao, *args, **kwargs)
        finally:
            registo = {
                "sql": " ".join(str(operacao).split()),
                "ms": (time.perf_counter() - inicio) * 1000,
                "escrita": e_escrita(operacao),
            }
            ESTADO.consultas.append(registo)
            self._ultimo = registo

    def execute(self, operacao, *args, **kwargs):
        return self._correr("execute", operacao, *args, **kwargs)

    def executemany(self, operacao, *args, **kwargs):
        return self._correr("executemany", operacao, *args, **kwargs)

    def _buscar(self, nome, *args, **kwargs):
        inicio = time.perf_counter()
        try:
            return getattr(self._real, nome)(*args, **kwargs)
        finally:
            if self._ultimo is not None:
                self._ultimo["ms"] += (time.perf_counter() - inicio) * 1000

    def fetchone(self, *args, **kwargs):
        return self._buscar("fetchone", *args, **kwargs)

    def fetchall(self, *args, **kwargs):
        return self._buscar("fetchall", *args, **kwargs)

    def fetchmany(self, *args, **kwargs):
        return self._buscar("fetchmany", *args, **kwargs)

    def __iter__(self):
        return iter(self._real)

    def __enter__(self):
        return self

    def __exit__(self, *excecao):
        self._real.close()
        return False

    def __getattr__(self, nome):
        return getattr(self._real, nome)


class _Ligacao:
    """Embrulho de uma ligação: só troca o cursor por um que mede."""

    def __init__(self, real):
        self._real = real

    def cursor(self, *args, **kwargs):
        return _Cursor(self._real.cursor(*args, **kwargs))

    def __enter__(self):
        return self

    def __exit__(self, *excecao):
        self._real.close()
        return False

    def __getattr__(self, nome):
        return getattr(self._real, nome)


def instrumentar_mysql(modulo=None):
    """Troca o `connect` do mysql.connector por uma versão que mede.

    Chamar UMA vez, no arranque, antes de qualquer ligação (o pool do
    `repositorio` guarda as ligações que abrir — se já existissem, as
    consultas delas não eram contadas). `modulo` existe para os
    testes passarem um falso; por omissão é o `mysql.connector`.
    Devolve o `connect` original.
    """
    if modulo is None:
        import mysql.connector as modulo

    original = modulo.connect

    def connect(*args, **kwargs):
        inicio = time.perf_counter()
        real = original(*args, **kwargs)
        ESTADO.ligacoes.append((time.perf_counter() - inicio) * 1000)
        return _Ligacao(real)

    modulo.connect = connect
    return original


# =====================================================================
# Contas
# =====================================================================


def medicao(total, construcao_bruta, consultas, ligacoes,
            consultas_construcao, ligacoes_construcao, widgets):
    """Uma abertura de um ecrã, partida em fases (em ms).

    - `total`: do clique até o ecrã estar desenhado;
    - `construcao_bruta`: até o construtor do ecrã acabar (inclui as
      consultas feitas lá dentro — descontam-se aqui);
    - `consultas`/`ligacoes`: tudo o que foi à base nesta abertura;
    - `*_construcao`: só o que aconteceu durante a construção.
    """
    dados = sum(c["ms"] for c in consultas) + sum(ligacoes)
    dados_construcao = (
        sum(c["ms"] for c in consultas_construcao)
        + sum(ligacoes_construcao)
    )
    construcao = max(0.0, construcao_bruta - dados_construcao)
    desenho = max(0.0, total - dados - construcao)
    return {
        "total": total,
        "dados": dados,
        "construcao": construcao,
        "desenho": desenho,
        "consultas": list(consultas),
        "ligacoes": list(ligacoes),
        "widgets": widgets,
    }


def linha_saltada(nome, motivo):
    """Linha do relatório de um ecrã que não foi medido."""
    return {"nome": nome, "saltado": motivo, "erro": None}


def linha_com_erro(nome, erro):
    """Linha do relatório de um ecrã que rebentou ao abrir."""
    return {"nome": nome, "saltado": None, "erro": str(erro)}


def juntar_repeticoes(nome, repeticoes):
    """Resume as N aberturas do mesmo ecrã numa linha do relatório.

    Os tempos são a média; as consultas mais pesadas vêm da abertura
    mais lenta (é a que interessa investigar).
    """
    def media(chave):
        return statistics.fmean(r[chave] for r in repeticoes)

    pior = max(repeticoes, key=lambda r: r["total"])
    agrupadas = {}
    for consulta in pior["consultas"]:
        chave = consulta["sql"][:200]
        soma = agrupadas.setdefault(
            chave, {"sql": consulta["sql"], "ms": 0.0, "n": 0}
        )
        soma["ms"] += consulta["ms"]
        soma["n"] += 1
    lentas = sorted(agrupadas.values(), key=lambda x: x["ms"],
                    reverse=True)[:4]

    linha = {
        "nome": nome,
        "total": media("total"),
        "primeira": repeticoes[0]["total"],
        "maximo": max(r["total"] for r in repeticoes),
        "dados": media("dados"),
        "construcao": media("construcao"),
        "desenho": media("desenho"),
        "n_consultas": round(
            statistics.fmean(len(r["consultas"]) for r in repeticoes)
        ),
        "n_ligacoes": round(
            statistics.fmean(len(r["ligacoes"]) for r in repeticoes)
        ),
        "ms_ligacoes": statistics.fmean(
            sum(r["ligacoes"]) for r in repeticoes
        ),
        "widgets": round(media("widgets")),
        "escritas": sum(1 for c in pior["consultas"] if c["escrita"]),
        "lentas": [
            {"sql": x["sql"][:160], "ms": x["ms"], "n": x["n"]}
            for x in lentas
        ],
        "saltado": None,
        "erro": None,
    }
    linha["dicas"] = sugerir(linha)
    linha["estado"] = estado_de(linha["total"])
    return linha


def estado_de(ms):
    """"OK", "Atenção" ou "Lento"."""
    if ms < LIMITE_OK_MS:
        return "OK"
    if ms <= LIMITE_LENTO_MS:
        return "Atenção"
    return "Lento"


def sugerir(linha):
    """Regras simples que transformam os números em pistas."""
    dicas = []
    total = max(linha["total"], 1)

    if linha["n_consultas"] >= 15:
        dicas.append(
            f"{linha['n_consultas']} consultas ao abrir: procurar um ciclo "
            "que faz uma consulta por linha e trocar por uma só."
        )
    if linha["n_ligacoes"] >= 5 and linha["ms_ligacoes"] / total > 0.25:
        dicas.append(
            f"Abrir {linha['n_ligacoes']} ligações custa "
            f"{linha['ms_ligacoes']:.0f} ms "
            f"({linha['ms_ligacoes'] / total:.0%} do total)."
        )
    if linha["dados"] / total > 0.5 and linha["n_consultas"] < 15:
        dicas.append(
            "O tempo é sobretudo base de dados: ver as consultas mais "
            "pesadas abaixo."
        )
    if linha["construcao"] / total > 0.5 and linha["widgets"] > 400:
        dicas.append(
            f"{linha['widgets']} widgets criados: limitar as linhas "
            "visíveis ou paginar."
        )
    if linha["desenho"] / total > 0.4:
        dicas.append(
            "Muito tempo em layout/desenho: evitar reconstruções "
            "completas e update() dentro de ciclos."
        )
    if linha["escritas"] > 0:
        dicas.append(
            f"Grava {linha['escritas']}x na base só por abrir o ecrã."
        )
    if not dicas:
        dicas.append("Sem problema evidente nesta medição.")
    return dicas


def resumo(linhas):
    """Números do topo do relatório (só os ecrãs medidos)."""
    medidas = [
        linha for linha in linhas
        if not linha.get("erro") and not linha.get("saltado")
    ]
    if not medidas:
        return {"medidos": 0, "media": 0.0, "lentos": 0, "consultas": 0,
                "mais_lento": None}
    mais_lento = max(medidas, key=lambda x: x["total"])
    return {
        "medidos": len(medidas),
        "media": statistics.fmean(x["total"] for x in medidas),
        "lentos": sum(1 for x in medidas if x["total"] > LIMITE_LENTO_MS),
        "consultas": sum(x["n_consultas"] for x in medidas),
        "mais_lento": {"nome": mais_lento["nome"],
                       "total": mais_lento["total"]},
    }
