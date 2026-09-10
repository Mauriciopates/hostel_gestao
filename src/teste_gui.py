# teste_gui.py — script temporário, só para testar ecrãs da GUI
# antes de estarem ligados ao menu lateral (app.py). Apaga depois.
#
# Atualizado a cada ecrã novo entregue (convenção pedida pelo aluno,
# 06/09/2026): aponta sempre para o ecrã mais recente. Versões
# anteriores desta linha, para voltar a testar um ecrã já fechado:
#   from gui.gui_unidades import PlantaLugares
#   app.mostrar_frame(PlantaLugares, unidade_id="UNI-001")
#
#   from gui.gui_contratos import NovoContratoMensal
#   app.mostrar_frame(
#       NovoContratoMensal, unidade_id="UNI-001", lugar_id="LUG-004"
#   )
#
#   from gui.gui_propriedades import ListaPropriedades
#   app.mostrar_frame(ListaPropriedades)
#
# 07/09/2026: ficheiros dentro de gui/ renomeados com prefixo gui_
# (gui_unidades.py, gui_propriedades.py, gui_contratos.py,
# gui_clientes.py) para deixarem de colidir de nome com os módulos
# de negócio homónimos na raiz de src/ — ver claude/
# Decisoes_Pendentes_Fase2.txt, secção 10.

from gui.app import Aplicacao
from gui.gui_clientes import ListaClientes

app = Aplicacao()
app.mostrar_frame(ListaClientes)
app.mainloop()
