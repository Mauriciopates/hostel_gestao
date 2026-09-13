-- ============================================================
-- alteracao_responsavel_unidade.sql
-- Hostel_Cleaning — acrescenta a ligação responsável <-> unidade
--
-- Criado em 09/09/2026, para o ecrã de Gestão de Responsáveis:
-- o balão que aparece ao passar o rato sobre o ID de um
-- responsável mostra as unidades que ele gere, e essa ligação
-- não existia no modelo até aqui. Até esta data, responsavel_id
-- só aparecia em requisições, devoluções e movimentos — ou seja,
-- o responsável ligava-se ao que FAZ, nunca a um sítio onde está
-- colocado.
--
-- Corre este ficheiro contra a base já existente (hostel_gestao).
-- É um CREATE TABLE novo, não uma alteração a uma tabela com
-- dados — não apaga nem toca em nada do que já lá está.
--
-- Depois de correr, acrescenta este mesmo bloco ao teu
-- esquema_mysql.sql principal, a seguir à tabela `responsaveis`,
-- para o ficheiro continuar a refletir a estrutura real da base.
-- ============================================================

USE hostel_gestao;

-- ------------------------------------------------------------
-- responsavel_unidade
--
-- Um responsável pode gerir várias unidades, e uma unidade pode
-- ter vários responsáveis — é a relação mais simples que cobre
-- prédios onde a limpeza é feita por mais do que uma pessoa.
--
-- O par (responsavel_id, unidade_id) é UNIQUE: não pode haver
-- duas linhas para a mesma ligação. É isso que permite ao
-- unidades.atribuir_responsavel() reativar uma ligação removida
-- em vez de inserir uma segunda linha para o mesmo par.
--
-- Como no resto do sistema, uma ligação nunca é apagada, só
-- desativada (ativo = 0), para não perder o histórico de quem
-- geriu o quê.
-- ------------------------------------------------------------
CREATE TABLE responsavel_unidade (
    id              VARCHAR(10)  PRIMARY KEY,
    responsavel_id  VARCHAR(10)  NOT NULL,
    unidade_id      VARCHAR(10)  NOT NULL,
    ativo           BOOLEAN      NOT NULL DEFAULT 1,
    UNIQUE KEY uk_responsavel_unidade (responsavel_id, unidade_id),
    FOREIGN KEY (responsavel_id) REFERENCES responsaveis(id),
    FOREIGN KEY (unidade_id) REFERENCES unidades(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
