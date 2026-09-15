"""Ponto de entrada do sistema — arranque, cópia de segurança e
entrega do controlo à interface (decisão 7: só o cli.py interage
com quem usa o sistema; este módulo não tem input() nem print()
próprio).
"""

import cli
import config
import repositorio


def main():
    """Arranca o sistema: pastas persistentes, cópia de segurança,
    limpeza de cópias antigas e entrega ao menu principal.

    A ordem importa: `config.garantir_diretorios()` corre primeiro
    de tudo (Fase 1, v1.4.0) — sem isto, `criar_backup()` podia
    falhar por a pasta de destino ainda não existir. A cópia de hoje
    faz-se ANTES da limpeza, para que um erro na limpeza nunca deixe
    passar um arranque sem cópia do dia. `criar_backup` e
    `limpar_backups_antigos` não recebem argumentos: o primeiro
    decide sozinho se a cópia de hoje já existe, o segundo usa
    `config.DIAS_BACKUP` por omissão.

    Não há mais nenhuma estrutura de dados a carregar aqui: desde a
    migração completa da Fase 2 para MySQL (v1.1.0), cada módulo de
    negócio fala diretamente com a base de dados através de
    `repositorio.py` — não existe um `dados` único carregado no
    arranque e devolvido no fecho. `repositorio.carregar()` /
    `gravar()` / `_estrutura_vazia()` (o mecanismo antigo, ligado a
    `dados/dados.json`) e `cli.mostrar_erro_arranque` (só usada para
    o erro de versão que `carregar()` levantava) foram removidos por
    já não terem nenhum consumidor.
    """
    config.garantir_diretorios()

    repositorio.criar_backup()
    repositorio.limpar_backups_antigos()

    cli.menu_principal()


if __name__ == "__main__":
    main()