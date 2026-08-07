# Hostel_Cleaning — Sistema de Gestão de Alojamento

Sistema de gestão administrativa e comercial de alojamento local no Porto,
em regime misto: arrendamento mensal partilhado e estadias curtas (Airbnb).

Projeto individual da UFCD 26.0462 — Desenvolvimento de projeto de tecnologias
e programação de sistemas de informação.

**Autor:** Mauricio Pates
**Formador:** Alberto Crista
**Entrega:** outubro de 2026

---

## Estado

**Fase 1 — em desenvolvimento.** Análise e desenho concluídos.

| Fase | Âmbito | Estado |
|------|--------|--------|
| 1.0 | CLI + JSON | Em curso |
| 2.0 | GUI CustomTkinter + SQLite + financeiro, relatórios, utilizadores | Planeada |
| 3.0 | Django + MySQL + Nginx | Fora da entrega de outubro |

---

## Âmbito

Gestão de 22 unidades distribuídas por 7 propriedades, em dois regimes de
ocupação com regras distintas:

- **Mensal** — contrato por pessoa, vários ativos em simultâneo na mesma
  unidade; ocupação apresentada como proporção dos lugares
- **Airbnb** — reserva exclusiva do apartamento; qualquer sobreposição de
  datas é recusada

Módulos: propriedades, unidades (com quartos e lugares), clientes, contratos,
stock e responsáveis.

---

## Ambiente

- Python 3.11
- Apenas biblioteca padrão na Fase 1
- Testes com `unittest`

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows (Git Bash)
pip install -r requirements.txt
```

---

## Estrutura

src/ módulos da aplicação
testes/ testes unitários (prefixo teste_)
docs/ análise, desenho, testes e manual
dados/ ficheiros de dados — fora do controlo de versões
backups/ cópias de segurança — fora do controlo de versões
logs/ registos — fora do controlo de versões

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
irreversível a pedido do titular (RGPD), conservando os registos contratuais
e financeiros exigidos por lei.