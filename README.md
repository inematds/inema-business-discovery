# INEMA Business Discovery

[![INEMA Business Discovery](guia/assets/banner.jpg)](https://inematds.github.io/inema-business-discovery/guia/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## O que é

O INEMA Business Discovery é um programa aberto que lê as planilhas da sua empresa (vendas, clientes, propostas, despesas e operação) e aponta oportunidades: clientes que pararam de comprar, despesas que subiram demais, retrabalho, vendas que poderiam acontecer. Serve para o dono ou gestor de uma pequena ou média empresa que quer decidir com prova, não com palpite. Cada achado vem com a conta, o grau de confiança e um teste para confirmar. Para usar, basta Python 3 e as planilhas exportadas em CSV.

## 📖 Guia de uso

Guia completo (landing + passo a passo): **https://inematds.github.io/inema-business-discovery/guia/**

**Laboratório de descobertas para gestão de negócios.** Seis agentes investigam os dados da empresa, encontram oportunidades que o gestor ainda não viu, propõem hipóteses, planejam testes com grupo de controle, conferem as contas, tentam derrubar as próprias conclusões e guardam o que foi aprendido.

> E se uma empresa tivesse uma equipe de pesquisadores de IA trabalhando 24 horas por dia, não para responder perguntas do gestor, mas para descobrir continuamente como ela pode ganhar mais, gastar menos e operar melhor?

- Curso explicativo: https://inematds.github.io/business-discovery-v72/

## Em 1 minuto

```bash
git clone https://github.com/inematds/inema-business-discovery
cd inema-business-discovery
python3 -m bd demo                       # empresa FICTÍCIA, ciclo completo
python3 -m bd servir --saida saida-demo  # painel em http://127.0.0.1:8765
```

Só precisa de Python 3.10+. Nenhuma dependência externa, nenhuma chave de API.

A demo reproduz o exemplo do documento de visão: **120 clientes inativos × 20% de conversão × ticket de R$ 3.500 = R$ 84.000 de receita potencial; × margem de 30% = R$ 25.200 de contribuição potencial.** É um cenário ilustrativo, com dados inventados — não é resultado observado. O teste da demo também é **simulado**.

## A equipe de agentes

| Agente | O que faz | No LOOP-R |
|---|---|---|
| **Investigador** | Varre as 5 frentes e acha padrões, anomalias e oportunidades. Só cálculo, sem modelo de linguagem. | Localizar |
| **Cientista** | Formula hipótese e intervenções; põe 3 agentes para competir com estratégias diferentes. | Propor |
| **Experimentador** | Simula cenários (pessimista, base, otimista) e sorteia grupo de teste e grupo de controle. | Operar |
| **Auditor** | Refaz cada conta a partir das entradas, confere se os alvos existem e se há evidência. Reprova o que não fecha. | (verificação) |
| **Crítico** | Procura explicações alternativas e sinais de número inflado; baixa a confiança. | (verificação) |
| **Memória** | Guarda descobertas, decisões (quem, quando) e lições. Só estratégia validada é promovida. | Reforçar |

O **Validador** compara previsto × medido usando o grupo de controle — LOOP-R: Observar.
Regra do LOOP-R: **quem faz nunca é quem avalia.**

## As cinco frentes

| Frente | O que procura (nesta versão) |
|---|---|
| Receita perdida | clientes que pararam de comprar; propostas esquecidas no CRM |
| Despesas evitáveis | despesas recorrentes que subiram mais de 10%; dois fornecedores para a mesma coisa |
| Risco de abandono | clientes ativos demorando mais que o normal para voltar |
| Ineficiências operacionais | etapa que concentra o retrabalho; gargalo de tempo |
| Oportunidades comerciais | produtos comprados juntos (venda casada); itens com margem muito baixa |

Cada descoberta sai com: origem dos dados, período, hipótese, evidências, conta reproduzível, premissas, riscos, grau de confiança, custo, prioridade e próximo passo.

## Agentes competindo, avaliador às cegas

Para cada descoberta, três agentes propõem caminhos (ex.: **A Recuperação** — contato personalizado; **B Oferta** — desconto segmentado; **C Relacionamento** — benefício sem mexer no preço). O avaliador recebe as propostas embaralhadas como "Proposta 1, 2, 3", sem saber quem fez cada uma, e pontua pela contribuição líquida com desconto de risco. A autoria só é revelada depois. Uma estratégia já validada nos testes ganha bônus nas próximas rodadas.

## Governança: o humano aprova

Contato comercial, desconto, preço, contrato e mudança de processo **só andam com aprovação de uma pessoa** (`python3 -m bd aprovar ID --por "Nome"` ou o botão do painel). Agente não aprova: nomes como "agente" ou "ciclo" são recusados. Sem aprovação, o Validador se recusa a validar. Tudo fica na trilha de decisões.

## Usar com os seus dados

Exporte planilhas do CRM, do financeiro e da operação para uma pasta (`;` ou `,`, datas `aaaa-mm-dd` ou `dd/mm/aaaa`, valores `1.234,56` aceitos):

| Arquivo | Colunas |
|---|---|
| `vendas.csv` (obrigatório) | venda_id, data, cliente_id, produto_id, quantidade, valor |
| `clientes.csv` | cliente_id, nome, segmento, cidade, desde |
| `produtos.csv` | produto_id, nome, categoria, preco, custo |
| `propostas.csv` | proposta_id, cliente_id, data, valor, status, ultimo_contato |
| `despesas.csv` | data, fornecedor, categoria, valor, recorrente, contrato_fim |
| `operacao.csv` | pedido_id, data, etapa, horas, retrabalho |

Arquivo que falta só desliga a frente correspondente. Premissas (margem, conversões, custo da hora) ficam num `config.json` na mesma pasta — veja `exemplos/empresa-ficticia/config.json` e `bd/config.py`.

## O processo, do início ao fim

🧠 sessão com o gestor · ⚙️ script · 🤖 agente/modelo

1. 🧠 **Exportar os dados** do CRM, financeiro e operação para uma pasta (CSV). Sem integração no primeiro piloto.
2. 🧠 **Escrever as premissas** no `config.json`: margem de contribuição, conversões esperadas, custo da hora.
3. ⚙️ **Rodar o ciclo**: `python3 -m bd analisar --dados minha-pasta --saida saida` — Investigador, Cientista, Experimentador, Auditor e Crítico rodam em sequência.
4. 🤖 *(opcional)* **Narrativa**: com `--llm` e `"llm": {"provedor": "ollama"}` no config, um modelo local explica cada descoberta em português simples.
5. 🧠 **Ler o relatório** (`saida/relatorio.html`) ou abrir o painel: `python3 -m bd servir --saida saida`.
6. 🧠 **Aprovar ou rejeitar** cada teste: `python3 -m bd aprovar RP-REATIVACAO --por "Seu Nome"`.
7. 🧠 **Executar o teste** com os grupos sorteados em `saida/planos/<ID>-grupos.csv` (só o grupo "teste" recebe a ação).
8. 🧠 **Registrar o resultado** em CSV: `alvo_id, grupo, converteu, receita`.
9. ⚙️ **Validar**: `python3 -m bd validar RP-REATIVACAO --resultados resultado.csv --saida saida` — calcula a contribuição incremental, o p-valor e a precisão da previsão.
10. ⚙️ **Reforçar**: estratégia que passou (p < 0,05 e lucro incremental) vira lição promovida e ganha peso no próximo ciclo; o resto fica registrado como descartado.
11. ⚙️ **Repetir** toda semana com dados novos (cron, systemd ou n8n — `n8n/business-discovery.json`). Decisões humanas anteriores são preservadas.

## Métricas para provar resultado

`python3 -m bd memoria --saida saida` mostra: oportunidades validadas, impacto incremental medido, precisão das hipóteses (previsto × realizado), testes concluídos e descobertas por estado.

## Modelo de linguagem: opcional e local

O motor (contas, auditoria, estatística) **não usa modelo nenhum**. O modelo só escreve a explicação para o gestor. Provedores: `nenhum` (padrão), `ollama` (local), `claude-cli` (`claude -p` pela sua assinatura) e `codex-cli` (`codex exec` pela sua assinatura). Nenhum lê chave de API, e o texto enviado leva só números agregados — nenhum nome de cliente sai da máquina.

## Arquitetura e próximos passos

Hoje: Python puro + SQLite + HTML. Caminho previsto no documento de visão (detalhes em [docs/ARQUITETURA.md](docs/ARQUITETURA.md)):

- **Supabase**: `schema.sql` já traz as tabelas para guardar histórico em Postgres.
- **n8n**: fluxo de exemplo em `n8n/` roda o ciclo toda semana e avisa quem precisa aprovar.
- **Next.js**: painel web multiusuário sobre o mesmo `descobertas.json`.
- **Fase 2**: custos, margens e operações com conectores diretos.
- **Fase 3**: aprendizado entre empresas, só com dados agregados e anonimizados, base legal, contrato e LGPD.

## Testes

```bash
python3 -m pytest -q   # 22 testes: contas do documento, auditoria, portão humano, avaliação às cegas, validação
```

## Licença

MIT. Dados de exemplo inteiramente fictícios.
