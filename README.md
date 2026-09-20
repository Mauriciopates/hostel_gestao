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
| 3.0 | Django + Nginx | Fora da entrega de outubro | Tentativa de entrega em Novembro na apresentação final

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

```
bash
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

```
bash

sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

sudo apt install -y python3.11 python3.11-venv python3.11-dev python3.11-tk
```
Recomendado a criação de ambiente virtual para a instalação

```
bash

python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

---

## Estrutura 

src/ módulos da aplicação
testes/ testes unitários (prefixo teste_)
docs/ análise, desenho, testes e manual
img/ imagem do logo de sistema 

Disco Local C:/ (Criado automaticamente no arranque)

dados/ ficheiros de dados — fora do controlo de versões
contratos/ ficheiro de armazenamento dos contratos emitidos 
backups/ cópias de segurança — fora do controlo de versões
logs/ registos — fora do controlo de versões
relatorios/ fihceiros de armazenamento dos relatorios emitidos 


---

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