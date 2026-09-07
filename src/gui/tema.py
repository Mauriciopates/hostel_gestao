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
NAVY_ESCURO = "#0C2F48"          # fundo da sidebar — já escuro nos dois

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

# Indisponibilidade (ex.: um lugar já reservado para uma data futura,
# sem estar ocupado agora) — cinzento, para não se confundir nem com
# aviso/parcial (amarelo) nem com erro/ocupado (vermelho). Acrescentado
# em 06/09/2026, a pedido, ao chegar a planta de lugares.
CINZA_INDISPONIVEL = ("#E4E6E8", "#2A2E33")     # fundo da caixa
TEXTO_INDISPONIVEL = ("#6B7280", "#9AA3AD")

# Par "livre", em falta até agora: a Planta de Lugares mostra "Livre"
# sem fundo (só texto em VERDE, sobre COR_FUNDO), mas o ecrã de
# Propriedades e Unidades (06/09/2026) mostra o estado de cada
# unidade como uma etiqueta/pílula, igual às de parcial/ocupado/
# manutenção — precisa do mesmo par (fundo, texto) que as outras,
# em vez de destoar sendo a única sem fundo.
VERDE_LIVRE = ("#E1F5EA", "#1C3A2A")            # fundo da etiqueta
TEXTO_LIVRE = ("#2E8B57", "#8FD9AE")

# Chip de ID (propriedade/unidade) — acrescentado em 07/09/2026,
# aprovado por mockup, para mostrar o ID ao lado do nome em
# Propriedades e Unidades sem competir visualmente com as etiquetas
# de estado (fundo bem mais claro, sem apelo de "aviso"). Só a
# propriedade usa este par — o chip de ID da unidade reaproveita
# CINZA_INDISPONIVEL/TEXTO_INDISPONIVEL, já existentes.
ID_CHIP_FUNDO = ("#EAF3F8", "#16323F")          # fundo do chip de ID

# Zebra striping das tabelas de Gestão de Propriedades (07/09/2026,
# 4ª ronda, ao passar para uma "tabela a sério") — tom muito
# ligeiramente diferente de COR_FUNDO, só para o olho seguir a linha
# sem precisar de bordas pesadas por todo o lado. Só as linhas
# ativas alternam; as inativas ficam sempre no fundo normal.
LINHA_ALTERNADA = ("#F7F9FB", "#20262E")

# Fundo do cabeçalho das mesmas tabelas (07/09/2026, 5ª ronda — o
# aluno achou que, mesmo com colunas alinhadas, "não parecia uma
# tabela"): uma faixa com fundo próprio por trás do cabeçalho,
# dentro de um cartão com borda à volta de toda a tabela, é o que
# faz ler como tabela a sério, não só texto alinhado em colunas.
CABECALHO_TABELA_FUNDO = ("#F5F6F9", "#1E242B")

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