"""Ponto de entrada da interface gráfica.

Separado do `teste_gui.py` por uma questão simples: aquele é um
script de desenvolvimento, que pode ser apagado a qualquer momento
sem afetar o projeto. Este é o ficheiro oficial — quem corre a
aplicação a partir do executável, do atalho, ou com
`python src/main_gui.py`, é este que arranca.

A lógica toda vive no `app.py` (a classe `Aplicacao`); este
ficheiro é só o casquilho que a instancia e arranca o loop de
eventos do Tkinter. A única coisa que faz antes disso é garantir a
árvore de diretorias persistentes (dados/backups/contratos/logs),
criada em `config.garantir_diretorios()` — Fase 1, v1.4.0.
"""

import config
from gui.app import Aplicacao


if __name__ == "__main__":
    config.garantir_diretorios()
    app = Aplicacao()
    app.mainloop()