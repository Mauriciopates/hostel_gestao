"""Ponto de entrada do sistema — arranque, cópia de segurança e
entrega da estrutura de dados à interface (decisão 7: só o cli.py
interage com quem usa o sistema; este módulo não tem input() nem
print() próprio — até o erro de arranque é mostrado através de
cli.mostrar_erro_arranque, nunca de um print() aqui).
"""

import sys

import cli
import repositorio


def main():
    """Arranca o sistema: cópia de segurança, limpeza de cópias
    antigas, carregamento dos dados e entrega ao menu principal.

    A ordem importa: a cópia de hoje faz-se ANTES da limpeza, para
    que um erro na limpeza nunca deixe passar um arranque sem
    cópia do dia. `criar_backup` e `limpar_backups_antigos` não
    recebem argumentos: o primeiro decide sozinho se a cópia de
    hoje já existe, o segundo usa `config.DIAS_BACKUP` por
    omissão.

    `repositorio.carregar()` só levanta `ValueError` num caso: o
    ficheiro de dados foi gravado por uma versão posterior à deste
    programa (ver repositorio.py). É o único ponto do sistema em
    que uma exceção é apanhada fora de um ecrã do cli.py — porque
    acontece ANTES de o menu principal, e portanto qualquer ecrã,
    existirem. Termina com sys.exit(1): um erro de arranque não
    tem por onde continuar.
    """
    repositorio.criar_backup()
    repositorio.limpar_backups_antigos()

    try:
        dados = repositorio.carregar()
    except ValueError as erro:
        cli.mostrar_erro_arranque(str(erro))
        sys.exit(1)

    cli.menu_principal(dados)


if __name__ == "__main__":
    main()
