"""Ponto de entrada do sistema — arranque, cópia de segurança e
entrega do controlo à interface (decisão 7: só o cli.py interage
com quem usa o sistema; este módulo não tem input() nem print()
próprio).
"""

import logging

import sys

import cli
import config
import configuracoes
import registo_logs
import repositorio
import servidores

logger = logging.getLogger(__name__)


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
    registo_logs.configurar("cli")

    # SERVIDOR (27/09/2026) — o mesmo passo que o main_gui faz em
    # `gui_servidores.garantir_ligacao()`, sem janelas: abre o túnel
    # SSH da VM (se o servidor ativo o usar) e confirma que o MySQL
    # responde ANTES do backup, que já usa a base. Sem isto, com a VM
    # ativa, o CLI nunca abria o túnel e rebentava na primeira
    # consulta. Escolher ou corrigir um servidor continua a ser no GUI
    # (Configurações → Sistema); aqui só se informa e termina.
    id_servidor, servidor = servidores.servidor_ativo()

    if id_servidor is None:
        sys.exit(
            "Ainda não há servidor de base de dados configurado. "
            "Abre o GUI (python src/main_gui.py) para o configurar."
        )

    ok, texto = servidores.testar_id(id_servidor)

    if not ok:
        logger.warning("Servidor '%s' indisponível: %s", id_servidor, texto)
        sys.exit(
            f"Sem ligação ao servidor '{(servidor or {}).get('nome')}':\n"
            f"{texto}\n"
            "Muda ou corrige o servidor no GUI (Configurações → Sistema)."
        )

    logger.info("Servidor '%s': %s", id_servidor, texto)

    repositorio.criar_backup()
    repositorio.limpar_backups_antigos()

    # Valores por omissão das Configurações — o GUI faz o mesmo no
    # arranque; sem eles, uma base nova não tem as chaves que o
    # negócio lê.
    configuracoes.garantir_seed()

    cli.menu_principal()

    logger.info("Aplicação terminada")


if __name__ == "__main__":
    main()