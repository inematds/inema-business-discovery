# CLAUDE.md — inema-business-discovery

Plataforma INEMA Business Discovery: 6 agentes (Investigador, Cientista, Experimentador, Auditor, Crítico, Memória) + Validador, ciclo LOOP-R, sobre CSVs. Python puro, sem dependências.

- Conta GitHub: `inematds`; autor e committer `inematds <inematds@gmail.com>`.
- Testes: `python3 -m pytest -q` (todos devem passar antes de commit). Demo: `python3 -m bd demo`.
- Guia em `guia/` (PT) + `guia/en/` + `guia/es/`; Pages serve da raiz da main.
- Curso irmão (a criar): `~/projetos/business-discovery-v72`.
- Regras: o motor nunca chama modelo; LLM só em `bd/llm.py`, sem chave de API. Ação sensível sempre passa pelo portão humano. Dados de exemplo sempre marcados como FICTÍCIOS.
- Ao mudar o fluxo, atualizar "O processo, do início ao fim" no README no mesmo commit.

## Self-learning

When I correct you, or you catch yourself making a mistake: before continuing, add the lesson as a one-line rule at the TOP of the Lessons section below.

## Lessons
- Toda conta guardada em `Calculo` deve ser feita com as MESMAS entradas arredondadas que ficam gravadas; senão o Auditor reprova (28/10/2026).
