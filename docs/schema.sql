-- Esquema OPCIONAL para PostgreSQL / Supabase.
-- V2: esta tabela segue a estrutura do CSV de DEMONSTRAÇÃO (fictício, formato largo). Os dados reais do
-- MonitorAr são lidos do arquivo em data/reais e não usam este banco.
-- O app funciona sem banco; use este arquivo apenas se for ler os dados de uma tabela.
-- Baseado nas tabelas apresentadas nas aulas (fontes e registros), adaptado às colunas do dataset
-- (poluentes, temperatura e umidade; o dataset não possui precipitação). A tabela "analises"
-- das aulas não foi implementada nesta versão.
--
-- Como usar: cole no SQL Editor do Supabase ou rode scripts/carregar_csv_no_banco.py (que executa este arquivo).

CREATE TABLE IF NOT EXISTS fontes (
    id    BIGSERIAL PRIMARY KEY,
    nome  TEXT NOT NULL UNIQUE,
    tipo  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS registros_ambientais (
    id        BIGSERIAL PRIMARY KEY,
    fonte_id  BIGINT NOT NULL REFERENCES fontes (id),
    data_hora TIMESTAMP NOT NULL,
    mp10      DOUBLE PRECISION,
    mp2_5     DOUBLE PRECISION,
    o3        DOUBLE PRECISION,
    co        DOUBLE PRECISION,
    co2       DOUBLE PRECISION,
    no2       DOUBLE PRECISION,
    temp      DOUBLE PRECISION,
    umidade   DOUBLE PRECISION,
    UNIQUE (fonte_id, data_hora)
);

CREATE INDEX IF NOT EXISTS idx_registros_data_hora ON registros_ambientais (data_hora);

-- Exemplos de consultas (SELECT, WHERE) equivalentes aos filtros do dashboard:
-- SELECT * FROM registros_ambientais WHERE data_hora >= '2024-03-01' AND data_hora < '2024-04-01' ORDER BY data_hora;
-- SELECT AVG(mp2_5) FROM registros_ambientais;
