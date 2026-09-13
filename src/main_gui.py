"""Ponto de entrada da interface gráfica.

Separado do `teste_gui.py` por uma questão simples: aquele é um
script de desenvolvimento, que pode ser apagado a qualquer momento
sem afetar o projeto. Este é o ficheiro oficial — quem corre a
aplicação a partir do executável, do atalho, ou com
`python src/main_gui.py`, é este que arranca.

A lógica toda vive no `app.py` (a classe `Aplicacao`); este
ficheiro é só o casquilho que a instancia e arranca o loop de
eventos do Tkinter.
"""

from gui.app import Aplicacao


if __name__ == "__main__":
    app = Aplicacao()
    app.mainloop()