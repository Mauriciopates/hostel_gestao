# Registo de alterações

Todas as alterações relevantes deste projeto são registadas neste ficheiro.
Numeração segundo maior.menor.correção (decisão de arquitetura, secção 7).

## [Não lançado]



### [0.2.0] — 2026-08-11

- Estrutura do repositório: `src/`, `testes/`, `docs/`, `dados/`, `backups/`, `logs/`
- Ambiente virtual com Python 3.11 e `requirements.txt` (Fase 1 sem dependências externas)
- `.gitignore` a excluir dados operacionais, cópias de segurança e registos (decisão 13)
- `config.py` com os valores de configuração da análise
- `modelos.py` com as 14 estruturas de dados do sistema
- `repositorio.py` com persistência em JSON, cópias de segurança diárias e contadores de identificadores
- 15 testes da camada de persistência em `testes/teste_repositorio.py`
- `validacoes.py` com verificação de NIF, campos obrigatórios por regime e regras de negócio
- 40 testes das validações em `testes/teste_validacoes.py`

## [0.1.0] — 2026-08-07

Fase de análise e desenho. Sem código.

### Adicionado
- `Arquitetura_Sistema_v1.8.docx` — 17 decisões de arquitetura, ciclo de vida,
  metodologia, divergências face à especificação e correspondência com a grelha
  de avaliação
- Fluxogramas da Fase 1 (4 páginas)
- Pseudocódigo dos processos principais
- Wireframes da Fase 2 (9 ecrãs)
- `Modelo_de_Dados_v1.3` com diagrama ER e lista de relações
- `Plano_de_Testes_v1.0.docx` — 101 casos em 12 grupos

### Alterado
- Protótipo em CLI (~7500 linhas) descartado. O valor retido está nos requisitos
  que revelou, não no código: contadores de ID a reiniciar, ausência de gravação
  automática, ausência de validação de sobreposição de datas e stock por unidade
  desalinhado da operação real
- Especificação corrigida de 20 para 22 unidades (omissão do Santa Catarina AP1)

### Segurança
- Histórico do Git limpo com `git-filter-repo` após deteção de dados pessoais
  reais em repositório público. Repositório recriado, dados de exemplo
  anonimizados