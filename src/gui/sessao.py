"""Sessão em memória: mantém o responsável ativo durante a execução da
aplicação gráfica, sem login nem palavra-passe (decisão 10). Substitui
o que hoje é pedido ecrã a ecrã em cli.py.
"""

import responsaveis

_responsavel_ativo = None


def definir_responsavel_ativo(responsavel_id):
    """Define o responsável ativo desta sessão.

    Valida o id contra responsaveis.validar_autoria (confirma que o
    responsável existe e está ativo) e guarda o REGISTO devolvido —
    nunca o texto cru recebido — para que o id fique sempre na forma
    canónica, o mesmo padrão já usado em estoque.py e corrigido em
    clientes.anonimizar(). Propaga o erro de validar_autoria se o id
    for inválido ou o responsável estiver inativo.
    """
    global _responsavel_ativo
    _responsavel_ativo = responsaveis.validar_autoria(responsavel_id)
    return _responsavel_ativo

def obter_responsavel_ativo():
    """Devolve o responsável ativo desta sessão, ou None se ainda
    não tiver sido definido (nenhuma chamada bem-sucedida a
    definir_responsavel_ativo desde o arranque da aplicação).
    """
    return _responsavel_ativo

def limpar_responsavel_ativo():
    """Repõe a sessão para nenhum responsável ativo — por exemplo,
    para trocar de utilizador sem fechar a aplicação, sem precisar
    de reiniciar o processo."""
    global _responsavel_ativo
    _responsavel_ativo = None