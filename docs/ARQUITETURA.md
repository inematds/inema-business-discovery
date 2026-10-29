# Arquitetura

## O ciclo (LOOP-R)

```
CSV (CRM, vendas, financeiro, operação)
   │
   ▼
Investigador ── Localizar ── 5 frentes, contas reproduzíveis
   │
   ▼
Cientista ───── Propor ───── hipótese + 3 agentes competindo (A/B/C) → avaliador às cegas
   │
   ▼
Experimentador ─ Operar ──── cenários + sorteio teste/controle + tamanho de amostra
   │
   ▼
Auditor ─────── refaz as contas, confere alvos, evidência, período  → reprova o que não fecha
   │
   ▼
Crítico ─────── explicações alternativas, concentração, amostra pequena → baixa a confiança
   │
   ▼
Portão humano ─ ações comerciais, preço, contrato, processo: só com nome de quem aprova
   │
   ▼
Teste real (grupo de teste recebe a ação, controle não)
   │
   ▼
Validador ───── Observar ─── incremental (teste − controle), p-valor, precisão da previsão
   │
   ▼
Memória ─────── Reforçar ─── promove só o que o número confirmou; volta para o Cientista
```

## Arquivos

| Módulo | Papel |
|---|---|
| `bd/dados.py` | leitura e normalização dos CSVs, hash de cada arquivo |
| `bd/investigador.py` | as 8 buscas das 5 frentes |
| `bd/cientista.py` | intervenções, competição, avaliação às cegas |
| `bd/experimentador.py` | cenários e plano de teste |
| `bd/auditor.py` | reavaliação segura das contas (sem `eval`) |
| `bd/critico.py` | tentativa de refutação |
| `bd/governanca.py` | portão humano |
| `bd/validador.py` | teste z de duas proporções, contribuição incremental |
| `bd/memoria.py` | SQLite: execuções, descobertas, eventos, lições |
| `bd/relatorio.py`, `bd/servidor.py` | relatório HTML e painel local (127.0.0.1) |
| `bd/llm.py` | narrativa opcional (Ollama local ou CLI pela assinatura) |

## Para a fase 2

- **Supabase**: `schema.sql` (mesmas tabelas, com `empresa_id` e RLS). Trocar `Memoria` por um adaptador Postgres mantendo a interface (`salvar`, `obter`, `listar`, `mudar_estado`, `registrar_licao`).
- **n8n**: `n8n/business-discovery.json` agenda o ciclo e avisa quem aprova.
- **Next.js**: ler `descobertas.json` (ou as tabelas) e chamar `/api/aprovar` com login real.
- **Conectores**: só depois de o piloto com CSV provar valor.

## Limites conhecidos

- As conversões e a margem são premissas até o primeiro teste medir.
- O teste z assume amostras independentes e conversão binária; para receita com cauda longa, usar bootstrap.
- Correlação de compra (venda casada) não prova causa — por isso toda ação passa por teste com controle.
