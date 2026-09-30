# -*- mode: python ; coding: utf-8 -*-
"""Receita do executável Windows do Hostel Clean (v1.8.0, INST-04).

Como usar (Git Bash, na raiz do repositório, com o .venv ativo):

    pip install pyinstaller
    pyinstaller HostelGestao.spec --clean --noconfirm

Resultado: dist/HostelGestao/HostelGestao.exe + dist/HostelGestao/_internal/
(modo --onedir). O `build/` e o `dist/` não vão para o Git — reconstroem-se
sempre a partir deste ficheiro e do commit.

Este ficheiro é código Python, mas quem o corre é o PyInstaller: os nomes
Analysis, PYZ, EXE e COLLECT são injetados por ele (por isso não têm
import aqui).
"""

import sys

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

# Os módulos da aplicação vivem em src/ e importam-se uns aos outros como
# `import config`, `from gui import ...` — o src/ tem de estar no sys.path,
# tanto aqui (para o collect_submodules("gui") funcionar) como na análise
# (pathex, mais abaixo).
sys.path.insert(0, "src")

# ---------------------------------------------------------------------------
# DATAS — ficheiros que NÃO são código e que a análise de imports não vê.
# Cada par é (origem no repositório, pasta de destino dentro do _internal).
# No executável, sys._MEIPASS aponta para esse _internal.
# ---------------------------------------------------------------------------
datas = [
    # Esquema oficial da base (INST-03). config.FICHEIRO_ESQUEMA procura-o
    # em sys._MEIPASS / "bd" / "esquema.sql".
    ("src/bd/esquema.sql", "bd"),
    # Logótipo e ícone. config.PASTA_IMG → sys._MEIPASS / "img".
    ("img", "img"),
]
# O customtkinter traz temas (.json) e fontes que carrega por caminho.
datas += collect_data_files("customtkinter")
# O keyring escolhe o backend (Windows → Gestor de Credenciais) pelos
# "entry points", que vivem nos metadados do pacote instalado.
datas += copy_metadata("keyring")

# ---------------------------------------------------------------------------
# HIDDEN IMPORTS — módulos carregados sem um `import` que a análise veja.
# ---------------------------------------------------------------------------
hiddenimports = []
# Há __import__("gui....") em gui_est_* e gui_unidades; por segurança entram
# todos os ecrãs.
hiddenimports += collect_submodules("gui")
# O conector MySQL carrega os plugins de autenticação (caching_sha2_password
# do MySQL 8) e as mensagens de erro por nome, em tempo de execução.
hiddenimports += collect_submodules("mysql.connector")
# Backend do cofre do Windows (servidores.obter_password).
hiddenimports += ["keyring.backends.Windows"]
# O tkcalendar formata datas com o babel, importado de forma indireta.
hiddenimports += ["babel.numbers"]


a = Analysis(
    # Ponto de entrada: a interface gráfica. A CLI continua a correr do
    # código (python src/main.py) — não vai no executável.
    ["src/main_gui.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # Ferramentas de desenvolvimento que nunca devem ir para o cliente.
    # O `unittest` NÃO pode sair: o matplotlib (via numpy/pyparsing)
    # importa-o ao arrancar — excluí-lo parte o executável.
    excludes=["pyright", "pyflakes", "pycodestyle"],
    noarchive=False,
)

# PYZ: o arquivo comprimido com todos os .pyc (o teu código + bibliotecas).
pyz = PYZ(a.pure)

# EXE: o pequeno executável que arranca o Python embutido e o main_gui.
exe = EXE(
    pyz,
    a.scripts,
    [],
    # exclude_binaries=True → modo --onedir: as DLL e os datas ficam na
    # pasta (COLLECT), não enfiados dentro do .exe.
    exclude_binaries=True,
    name="HostelGestao",
    icon="img/ico_hostel.ico",
    # False = aplicação de janela: sem a consola preta atrás. Os erros vão
    # para o log em C:\Hostel_gestao\logs (registo_logs).
    console=False,
    # UPX comprime DLL mas faz disparar antivírus — desligado.
    upx=False,
    debug=False,
    strip=False,
)

# COLLECT: monta a pasta final dist/HostelGestao/ (o .exe + _internal/).
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="HostelGestao",
)
