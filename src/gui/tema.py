"""Paleta de cores e valores de estilo comuns à interface gráfica,
extraídos do logo do sistema. Preparada para alternância entre modo
claro e escuro: cada cor é um valor único (quando já tem contraste
suficiente nos dois modos) ou um par (claro, escuro) — a mesma
convenção que o CustomTkinter espera em fg_color/text_color, por
isso não há lógica extra a escrever aqui.
"""
import customtkinter as ctk

# Cores de marca (extraídas do logo) — iguais nos dois modos, já têm
# contraste suficiente tanto sobre fundo claro como escuro
AZUL_PRINCIPAL = "#0E6291"       # botões primários, item ativo da navegação
AZUL_CLARO = "#2B99BF"           # hover, destaques
VERDE = "#4FBE7C"                # ações positivas (aprovar, sucesso)
NAVY_ESCURO = "#0C2F48"          # fundo da sidebar — já escuro, serve nos dois modos

# Cores que mudam consoante o modo: (claro, escuro)
COR_FUNDO = ("#FFFFFF", "#1A1F26")              # fundo principal da janela
COR_TEXTO = ("#0C2F48", "#E8EEF3")              # texto sobre COR_FUNDO
COR_TEXTO_SECUNDARIO = ("#5A6B7A", "#94A3AD")   # legendas, rótulos pequenos
COR_BORDA = ("#D0D0D0", "#3A4048")              # bordas de tabelas/campos

# Texto da barra lateral — fundo fixo (navy nos dois modos), por
# isso o texto também tem de ser fixo, não pode vir de COR_TEXTO*
COR_TEXTO_SIDEBAR = "#FFFFFF"
COR_TEXTO_SIDEBAR_SECAO = "#7C93A6"

# Avisos e erros — sem relação com a marca (decisão já tomada)
AMARELO_AVISO = ("#FFF3D6", "#4A3B14")          # fundo da caixa de aviso
TEXTO_AVISO = ("#9A7B12", "#F0D888")
VERMELHO_ERRO = ("#FBE4E1", "#4A1E19")
TEXTO_ERRO = ("#C0392B", "#F0A79C")

# Raios de canto por omissão — arredondado em toda a interface
RAIO_BOTAO = 10
RAIO_CARTAO = 14
RAIO_CAMPO = 8

def aplicar_tema():
    """Configura o modo de aparência inicial da aplicação. Chamar
    uma única vez, no arranque de app.py, antes de criar a janela
    principal. O modo pode depois ser trocado em runtime com
    ctk.set_appearance_mode("Light"/"Dark") — por exemplo, a partir
    de um botão em Configurações — sem reiniciar o programa.
    """
    ctk.set_appearance_mode("System")