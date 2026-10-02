# Hostel_Cleaning — Sistema de Gestão de Alojamento

Sistema de gestão administrativa e comercial de alojamento local no Portugal,
em regime misto: arrendamento mensal partilhado e estadias curtas (Airbnb).

Projeto individual da UFCD 26.0462 — Desenvolvimento de projeto de tecnologias
e programação de sistemas de informação.

**Autor:** Mauricio Pates
**Entrega:** outubro de 2026

---

## Estado

**Fase 2 — em desenvolvimento.** 

| Fase | Âmbito | Estado |
|------|--------|--------|
| 1.0 | CLI + JSON | Finalizado |
| 2.0 | GUI CustomTkinter + MySQL + financeiro, relatórios, utilizadores | Em andamento |
| 3.0 | Django + Nginx | Fora da entrega de outubro — tentativa em novembro, na apresentação final |

---

## Âmbito

Gestão de fluxo geral:

- **Mensal** — contrato por pessoa, vários ativos em simultâneo na mesma
  unidade; ocupação apresentada como proporção dos lugares
- **Airbnb** — reserva exclusiva do apartamento; qualquer sobreposição de
  datas é recusada

**Consultar manual para a instalação.

---

## Ambiente 
# Instalação - Windows 

- Python 3.11
- Apenas biblioteca padrão na Fase 1
- Testes com `unittest`

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows (Git Bash)
pip install -r requirements.txt
```

## Ambiente
# Instalação — Linux

- **Python 3.11**
- **MySQL 8.0+**
- Ubuntu 22.04+ / Debian equivalente

# 1. Preparar o Python

```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

sudo apt install -y python3.11 python3.11-venv python3.11-dev python3.11-tk
```
Recomendado a criação de ambiente virtual para a instalação

```bash
python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

---

## Comando para correr os testes

Os testes correm contra uma base **separada**, `hostel_gestao_teste`
(ou a indicada em `DB_NAME_TESTE` no `.env`) — nunca contra a base de
trabalho. Ver `testes/apoio_BD.py`. É preciso o MySQL a correr e o
`.venv` ativo.

Correr **sempre a partir da raiz do repositório**:

```bash
# Todos os testes
python -m unittest discover -s testes -p "teste_*.py" -t . -v

# Um só ficheiro
python -m unittest testes.teste_clientes -v

# Uma só classe / um só teste
python -m unittest testes.teste_clientes.TesteCriar -v
python -m unittest testes.teste_clientes.TesteCriar.test_id_com_prefixo_cli -v
```

O `-t .` é obrigatório: os testes importam `from testes.apoio_BD import ...`,
e sem ele o `unittest` não encontra o pacote `testes`.

O registo de cada execução fica em `testes/teste_logs/testes.log`
(fora do controlo de versões).

Verificações estáticas antes de cada commit:

```bash
python -m compileall -q src testes
python -m pyflakes src testes
pyright src
```

## Estrutura 

src/ módulos da aplicação
src/repositorio/ camada de persistência (única que fala com o MySQL),
  um ficheiro por domínio: _base.py (ligação, contadores, backups)
  e rep_<módulo>.py (ex.: rep_clientes.py). O código faz sempre
  `import repositorio` — o __init__.py reexporta tudo
src/gui/ interface gráfica (CustomTkinter), um ficheiro por ecrã;
  os módulos grandes têm subpasta própria: gui/contratos/ (gui_cnt_*),
  gui/despesas/ (gui_desp_*), gui/estoque/ (gui_est_*),
  gui/relatorios/ (gui_relat_*)
src/impressao/ exportação PDF, CSV e Excel
testes/ testes unitários (prefixo teste_)
docs/ análise, desenho, testes e manual
img/ imagem do logo de sistema 

Disco Local C:/ (Criado automaticamente no arranque)

dados/ ficheiros de dados — fora do controlo de versões
contratos/ ficheiro de armazenamento dos contratos emitidos 
backups/ cópias de segurança — fora do controlo de versões
logs/ registos — fora do controlo de versões
relatorios/ ficheiros de armazenamento dos relatórios emitidos 


---

## Criação do Pacote de instalação

Onde esta o projeto — Git Bash, na raiz do projeto (~/hostel_gestao)

1. Confirmar que estás na versão certa (branch main, já com a tag v1.8.0):

git status
git log --oneline -1

2. Gerar o executável (demora uns minutos):

source .venv/Scripts/activate
pyinstaller HostelGestao.spec --clean --noconfirm

3. Montar o pacote:

bash montar_pacote.sh

No fim aparece "Pacote pronto." e ficam criados:

C:\HostelGestao_instalacao\, com HostelGestao\, vm\, docs\ e LEIA-ME.txt
C:\HostelGestao_instalacao_v1.8.0.zip, que é o ficheiro a levar para o sin-11-teste



## Decisões de arquitetura

As 17 decisões que sustentam o desenho estão documentadas em
`docs/1_analise/Arquitetura_Sistema_v1.8.docx`.

Princípio estruturante: os módulos de lógica não conhecem a interface. Não
contêm `input()` nem `print()`; comunicam por `return` e sinalizam erro com
`raise ValueError`. É o que permite substituir a CLI por interface gráfica na
Fase 2 e por camada web na Fase 3 sem reescrever lógica de negócio.

---

## Proteção de dados

Os dados operacionais não são versionados. O sistema prevê anonimização
irreversível a pedido do titular (RGPD), dados de Airbnb conforme
necessidade de envio ao portal SIBA (Aima)
conservando os registos contratuais e financeiros exigidos por lei.