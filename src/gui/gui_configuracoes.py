"""Ecrã de Configurações — placeholder.

Decisão do aluno, 13/09/2026: fica por implementar. Mesmo raciocínio
de `gui_relatorios.py`: o item existe na secção "SISTEMA" da barra
lateral para a estrutura do menu estar completa, e o ecrã que ele
abre diz claramente que ainda não faz nada.

O que vai lá viver (ideias, por ordem de utilidade):

1. Modo de aparência (Claro / Escuro / Sistema). Já tem
   infraestrutura pronta: `ctk.set_appearance_mode(...)` existe
   desde o arranque, e os pares do `tema.py` já estão preparados
   para os dois modos. Falta o ecrã com o seletor, e uma chamada
   a `grafico.aplicar_tema()` quando o modo mudar (para os
   gráficos do Dashboard acompanharem — o gancho já existe em
   `componentes_graficos.py`).

2. Valores por omissão do sistema — a decisão do dia de
   vencimento (hoje é `config.DIA_VENCIMENTO`), o multiplicador
   máximo de caução (`config.MULTIPLICADOR_MAXIMO_CAUCAO`), a
   duração mínima de contrato (`config.DURACAO_MINIMA_MESES`), o
   aviso prévio (`config.AVISO_PREVIO_DIAS`). Estes valores vivem
   hoje em `config.py` como constantes — a ideia seria passarem a
   poder ser editados pela UI e guardados (uma tabela de
   configurações na base, ou um ficheiro JSON ao lado do
   executável).

3. Caminho de destino dos PDFs gerados (impressão de contratos) —
   hoje vai sempre para a pasta por omissão do sistema.

4. Gestão de utilizadores (quando existir o módulo
   `utilizadores.py` com conta e palavra-passe próprios) — o
   `SelecionarUtilizadorModal` do `app.py` fica obsoleto nesse dia,
   e o login a sério vive aqui.

Nota: nada disto é bloqueante para o resto do sistema. O
`config.py` continua a funcionar como está; este ecrã é só a
camada de edição que ainda não existe.
"""

import customtkinter as ctk

from . import componentes
from . import tema


class Configuracoes(ctk.CTkFrame):
    """Ecrã placeholder — cabeçalho + cartão "por implementar"."""

    def __init__(self, master, controlador):
        super().__init__(master, fg_color=tema.COR_FUNDO)
        self.controlador = controlador

        componentes.Cabecalho(self, titulo="Configurações").pack(fill="x")

        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.pack(expand=True, fill="both")

        cartao = ctk.CTkFrame(
            centro,
            corner_radius=tema.RAIO_CARTAO,
            border_width=1,
            border_color=tema.COR_BORDA,
            fg_color=tema.COR_FUNDO,
        )
        cartao.pack(expand=True, padx=40, pady=40)

        ctk.CTkLabel(
            cartao,
            text="Configurações",
            text_color=tema.COR_TEXTO,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(padx=40, pady=(30, 8))

        ctk.CTkLabel(
            cartao,
            text="Por implementar.",
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=13),
        ).pack(padx=40, pady=(0, 6))

        ctk.CTkLabel(
            cartao,
            text=(
                "Esta área vai permitir alterar o modo de aparência\n"
                "(claro/escuro), os valores por omissão do sistema\n"
                "(dia de vencimento, caução, avisos) e a pasta de\n"
                "destino dos PDFs gerados."
            ),
            text_color=tema.COR_TEXTO_SECUNDARIO,
            font=ctk.CTkFont(size=11),
            justify="center",
        ).pack(padx=40, pady=(0, 30))