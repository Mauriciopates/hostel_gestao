"""Camada de persistência. Único módulo que toca em ficheiros.

Os módulos de negócio nunca leem nem gravam — pedem aqui. É isto que
permite trocar JSON por SQLite na Fase 2 alterando só este ficheiro
(decisão 1).

Converte Decimal e date de e para texto na gravação e na leitura: em
memória é sempre Decimal e date, no ficheiro é sempre texto (decisão 4).
"""

import json
import shutil
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import config

"""
É por isso que os testes têm aquele sys.path.insert(0, 'src')
— sem ele, o unittest corre a partir da raiz do projeto e 
não encontraria nada.

"""


## Funções de leitura e escrita de ficheiros

PASTA_DADOS = Path(
    "dados"
)  

# o path possibilita a leitura e escrita de ficheiros 
# mesmo em sistemas operativos diferentes

PASTA_BACKUPS = Path("backups")
FICHEIRO_DADOS = PASTA_DADOS / "dados.json"
FICHEIRO_CONTADORES = PASTA_DADOS / "contadores.json"


def _reconstituir_tipos(dados):
    """Converte para Decimal e date os campos de cada coleção,
    logo a seguir ao json.load() os trazer como texto — inversa de
    _serializar, aplicada registo a registo através de
    _desserializar (que já existia, mas nunca era chamada).
    """


    dados["unidades"] = [
        _desserializar(
            u,
            campos_decimal=(
                "preco_base", "preco_epoca_alta",
                "multa_check_in_tardio",
            ),
        )
        for u in dados["unidades"]
    ]
    dados["clientes"] = [
        _desserializar(
            c,
            campos_data=(
                "data_nascimento", "validade_documento",
                "data_anonimizado",
            ),
        )
        for c in dados["clientes"]
    ]
    dados["ocupacoes"] = [
        _desserializar(o, campos_data=("data_inicio", "data_fim"))
        for o in dados["ocupacoes"]
    ]
    dados["ocupacoes_mensal"] = [
        _desserializar(
            m,
            campos_decimal=(
                "renda_calculada", "renda_praticada", "caucao",
            ),
        )
        for m in dados["ocupacoes_mensal"]
    ]
    dados["ocupacoes_airbnb"] = [
        _desserializar(
            a,
            campos_decimal=(
                "preco_calculado", "preco_praticado",
                "multa_calculada", "multa_praticada",
            ),
        )
        for a in dados["ocupacoes_airbnb"]
    ]
    dados["requisicoes"] = [
        _desserializar(
            r,
            campos_data=(
                "data_pedido", "data_envio", "data_rececao",
                "data_fecho", "data_devolucao",
            ),
        )
        for r in dados["requisicoes"]
    ]
    dados["movimentos"] = [
        _desserializar(m, campos_data=("data",))
        for m in dados["movimentos"]
    ]
    dados["configuracoes_historico"] = [
        _desserializar(c, campos_data=("data",))
        for c in dados["configuracoes_historico"]
    ]
    return dados


def _serializar(valor):
    """Converte tipos Python para tipos aceites pelo JSON.

    Decimal e date tornam-se texto; None e os tipos simples passam
    intactos. Chamada pelo `json.dump` para cada valor que não saiba
    gravar sozinho.
    """
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    raise TypeError(f"Tipo não serializável: {type(valor).__name__}")


"""Def é definição de uma função, que pode ser chamada em qualquer
parte do código, desde que seja importada.
"""


def _desserializar(dicionario, campos_decimal=(), campos_data=()):
    """Converte texto do JSON de volta para Decimal e date.

    Recebe os nomes dos campos a converter porque o JSON não guarda o tipo
    original: "250.00" e "2026-03-15" são ambos texto no ficheiro. Campos
    vazios ou nulos ficam a None.
    """
    resultado = dict(dicionario)

    for campo in campos_decimal:
        valor = resultado.get(campo)
        if valor is not None and valor != "":
            resultado[campo] = Decimal(valor)

    for campo in campos_data:
        valor = resultado.get(campo)
        if valor is not None and valor != "":
            resultado[campo] = date.fromisoformat(valor)

    return resultado


def _garantir_pastas():
    """Cria as pastas de dados e de cópias de segurança se não existirem.

    Estas pastas estão fora do controlo de versões (decisão 13), pelo que
    não vêm com o repositório: têm de ser criadas na primeira execução.
    """
    PASTA_DADOS.mkdir(exist_ok=True)
    PASTA_BACKUPS.mkdir(exist_ok=True)


def criar_backup():
    """Copia o ficheiro de dados para a pasta de cópias de segurança.

    Uma cópia por dia, criada ao arrancar antes de qualquer operação. Se
    já existir a cópia de hoje, não faz nada — a proteção é do estado com
    que o dia começou.

    Devolve o caminho da cópia, ou None se não houver dados para copiar.
    """
    _garantir_pastas()

    if not FICHEIRO_DADOS.exists():
        return None

    destino = (
        PASTA_BACKUPS / f"dados_{date.today().isoformat()}.json"
    )  
    #Formato de data ISO 8601, que é o formato de data mais
    #utilizado e recomendado para intercâmbio de dados entre sistemas.

    if destino.exists():
        return destino

    shutil.copy2(FICHEIRO_DADOS, destino)
    return destino


def limpar_backups_antigos(dias=None):
    """Elimina as cópias de segurança com mais dias do que o configurado.

    O prazo vem da configuração (30 dias por omissão), justificado pelo
    ciclo mensal do negócio: um erro de lançamento pode só ser detetado no
    fecho do mês seguinte.

    Devolve o número de cópias eliminadas.
    """
    if dias is None:
        dias = config.DIAS_BACKUP

    _garantir_pastas()
    limite = date.today() - timedelta(days=dias)
    eliminadas = 0

    for ficheiro in PASTA_BACKUPS.glob("dados_*.json"):
        texto = ficheiro.stem.replace("dados_", "")
        try:
            data_copia = date.fromisoformat(texto)
        except ValueError:
            continue

        if (
            data_copia < limite
        ):  
            ficheiro.unlink()
            eliminadas += 1

    return eliminadas
#não pode ser menor que o limite, o sistema ignora e não trava a execução

def carregar():
    """Lê o ficheiro de dados e devolve o seu conteúdo.

    Verifica a versão do formato antes de devolver: versão anterior é
    migrada, igual é aceite, posterior é recusada para não corromper
    dados gravados por uma versão mais recente do programa.

    Na primeira execução devolve uma estrutura vazia.
    """
    _garantir_pastas()

    if not FICHEIRO_DADOS.exists():
        return _estrutura_vazia()

    with open(FICHEIRO_DADOS, encoding="utf-8") as f:
        dados = json.load(f)
        dados = _reconstituir_tipos(dados)
        versao = dados.get("versao_dados", 1)

    if versao > config.VERSAO_DADOS:
        raise ValueError(
            f"Os dados foram gravados pela versão {versao} do formato, "
            f"posterior à versão {config.VERSAO_DADOS} deste programa. "
            f"Atualize o programa antes de continuar."
        )

    if versao < config.VERSAO_DADOS:
        dados = _migrar(dados, versao)
        gravar(dados)

    return dados


def _estrutura_vazia():
    """Devolve a estrutura inicial de dados, sem registos."""
    return {
        "versao_dados": config.VERSAO_DADOS,
        "propriedades": [],
        "unidades": [],
        "quartos": [],
        "lugares": [],
        "clientes": [],
        "responsaveis": [],
        "ocupacoes": [],
        "ocupacoes_mensal": [],
        "ocupacoes_airbnb": [],
        "produtos": [],
        "requisicoes": [],
        "movimentos": [],
        "configuracoes": [],
        "configuracoes_historico": [],
    }


def gravar(dados):
    """Escreve os dados no ficheiro, convertendo Decimal e date em texto.

    Grava primeiro num ficheiro temporário e só depois o substitui pelo
    definitivo: uma interrupção a meio da escrita deixaria o ficheiro
    truncado e os dados perdidos.
    """
    _garantir_pastas()
    dados["versao_dados"] = config.VERSAO_DADOS

    temporario = FICHEIRO_DADOS.with_suffix(".tmp")

    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(dados, f, default=_serializar, ensure_ascii=False, indent=2)

    temporario.replace(
        FICHEIRO_DADOS
    )  

    """replease substitui o ficheiro original pelo temporário, 
    garantindo que a operação é atómica e não deixa o ficheiro 
    em estado inconsistente. tem de estar com o mesmo nome do 
    ficheiro original, mas com a extensão .tmp para não sobrescrever
    o ficheiro original antes de ter terminado de escrever o temporário.
    """


def _migrar(dados, versao_origem):
    """Converte dados de um formato anterior para o formato atual.

    Aplica as migrações em cadeia, uma por versão: da 1 para a 2, da 2
    para a 3, e assim sucessivamente. Não há migrações definidas enquanto
    a versão do formato for 1.
    """
    migracoes = {}

    while versao_origem < config.VERSAO_DADOS:
        migracao = migracoes.get(versao_origem)
        if migracao is None:
            raise ValueError(
                f"Não existe migração da versão {versao_origem} para a "
                f"versão {versao_origem + 1} do formato de dados."
            )
        dados = migracao(dados)
        versao_origem += 1

    dados["versao_dados"] = config.VERSAO_DADOS
    return dados


def _carregar_contadores():
    """Lê o ficheiro dos contadores de identificadores.

    Devolve um dicionário de prefixo para último número atribuído. Se o
    ficheiro não existir, devolve um dicionário vazio.
    """
    _garantir_pastas()

    if not FICHEIRO_CONTADORES.exists():
        return {}

    with open(FICHEIRO_CONTADORES, encoding="utf-8") as f:
        return json.load(f)


def _gravar_contadores(contadores):
    """Escreve o ficheiro dos contadores, com a mesma proteção do gravar.

      Exemplo de conteúdo do ficheiro:Json

      {
    "UNI": 22,
    "CLI": 14,
    "PRO": 7
      }

    Pelo que entendi esse arquivo é usado para manter o controle dos últimos
    identificadores usados para diferentes entidades, como unidades, 
    clientes e produtos. Isso ajuda a garantir que cada nova entidade
    receba um identificador único e sequencial.

    """
    _garantir_pastas()
    temporario = FICHEIRO_CONTADORES.with_suffix(".tmp")

    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(contadores, f, ensure_ascii=False, indent=2)

    temporario.replace(FICHEIRO_CONTADORES)


def proximo_id(prefixo):
    """Devolve o próximo identificador para o prefixo indicado.

    Formato prefixo-sequencial com três dígitos: UNI-001, CLI-014
    (decisão 2).
    O contador é gravado antes de o identificador ser devolvido.

    Aqui ele busca o que foi gravado anteriormente exemplo: UNI-22
    CLI-14, PRO-7 e incrementa o número para o próximo id. mesmo que
    excluida se ja existiu UNI-22, o próximo id será UNI-23, garantindo que não
    há duplicidade de identificadores. Isso é importante para manter a
    integridade dos dados e evitar conflitos de identificação.


    """

    contadores = _carregar_contadores()
    numero = contadores.get(prefixo, 0) + 1
    contadores[prefixo] = numero
    _gravar_contadores(contadores)

    return f"{prefixo}-{numero:03d}"
