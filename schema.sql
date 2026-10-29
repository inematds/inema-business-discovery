-- INEMA Business Discovery — esquema para Postgres/Supabase (fase 2)
-- Espelha a memória SQLite local (bd/memoria.py). Ative RLS antes de expor ao navegador.

create table if not exists bd_execucoes (
  id bigserial primary key,
  empresa_id uuid not null,
  quando timestamptz not null default now(),
  pasta text not null,
  hashes jsonb not null,           -- sha256 de cada CSV analisado (rastreabilidade)
  versao text not null
);

create table if not exists bd_descobertas (
  id text not null,
  empresa_id uuid not null,
  execucao_id bigint references bd_execucoes(id),
  frente text not null check (frente in ('receita_perdida','despesas_evitaveis','risco_abandono',
                                         'ineficiencia_operacional','oportunidade_comercial')),
  estado text not null,
  prioridade numeric, impacto numeric, confianca numeric,
  dados jsonb not null,            -- descoberta completa: evidências, cálculo, auditoria, competição, plano
  atualizado timestamptz not null default now(),
  primary key (empresa_id, id)
);

create table if not exists bd_eventos (       -- trilha de decisões: quem, quando, o quê
  id bigserial primary key,
  empresa_id uuid not null,
  descoberta_id text not null,
  quando timestamptz not null default now(),
  tipo text not null, autor text not null, detalhe text
);

create table if not exists bd_licoes (
  id bigserial primary key,
  empresa_id uuid not null,
  quando timestamptz not null default now(),
  descoberta_id text, frente text, estrategia text,
  estimado numeric, observado numeric, precisao numeric, p_valor numeric,
  promovida boolean not null, texto text
);

alter table bd_execucoes enable row level security;
alter table bd_descobertas enable row level security;
alter table bd_eventos enable row level security;
alter table bd_licoes enable row level security;
-- Políticas: cada usuário só vê linhas da própria empresa (ajuste ao seu modelo de auth).
