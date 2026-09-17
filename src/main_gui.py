"""Ponto de entrada da interface gráfica.

Separado do `teste_gui.py` por uma questão simples: aquele é um
script de desenvolvimento, que pode ser apagado a qualquer momento
sem afetar o projeto. Este é o ficheiro oficial — quem corre a
aplicação a partir do executável, do atalho, ou com
`python src/main_gui.py`, é este que arranca.

A lógica toda vive no `app.py` (a classe `Aplicacao`); este
ficheiro é o casquilho que a instancia e arranca o loop de eventos
do Tkinter.

LOGOFF (v1.5.0, 17/09/2026): o `Aplicacao.trocar_utilizador` faz
logoff verdadeiro — marca `self.reabrir = True` e destrói a
janela. Este ficheiro deteta isso num `while` e cria uma nova
`Aplicacao`, que volta a pedir credenciais no `LoginModal`. Se
`self.reabrir` ficar False (o normal ao fechar a janela), o
`while` termina e a aplicação fecha de vez.
"""

import config
from gui.app import Aplicacao


def main():
    """Arranca a aplicação, com suporte a logoff.

    O `while` é o mecanismo do logoff: cada iteração cria uma
    `Aplicacao` nova, corre o `mainloop()`, e — quando este
    devolve — decide se deve continuar (porque o utilizador pediu
    para trocar) ou terminar.

    `config.garantir_diretorios()` corre uma só vez, antes do
    primeiro arranque. Não faz sentido repetir em cada reabertura
    (a árvore já existe), mas também não faz mal se acontecer.
    """
    config.garantir_diretorios()

    while True:
        app = Aplicacao()

        # Se o utilizador clicou "Sair" no LoginModal, a app já
        # foi destruída DENTRO do `__init__` — não há mainloop
        # para arrancar (rebentaria). Sai já.
        if app.terminar_pedido:
            break

        app.mainloop()

        # Se `reabrir` ficou False, o utilizador fechou a janela
        # normalmente. Termina.
        if not app.reabrir:
            break

        # Se chegou aqui, foi pedido logoff — o `while` recomeça
        # e cria uma nova `Aplicacao`.
        del app


if __name__ == "__main__":
    main()