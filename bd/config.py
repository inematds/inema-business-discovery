"""Parâmetros da análise. Tudo pode ser trocado por um config.json na pasta de dados.

Os valores marcados como PREMISSA não vêm dos dados: são suposições do gestor,
aparecem no relatório e precisam ser confirmadas por teste.
"""
from __future__ import annotations

import json
from pathlib import Path

PADRAO = {
    "data_referencia": None,            # None = maior data encontrada em vendas.csv
    "margem_contribuicao": 0.30,        # PREMISSA quando não há custo por produto
    "conversao_reativacao": 0.20,       # PREMISSA: taxa de retorno esperada da campanha
    "conversao_proposta": 0.25,         # PREMISSA: chance de fechar proposta esquecida
    "prob_churn_em_risco": 0.35,        # PREMISSA: chance de perder um cliente em risco
    "dias_inativo": 90,                 # sem comprar há mais de N dias = inativo
    "compras_ano_alta_frequencia": 6,   # >= N compras/ano antes de parar = alta frequência
    "dias_proposta_esquecida": 30,
    "fator_intervalo_risco": 1.8,       # intervalo atual > fator × intervalo típico
    "aumento_despesa_alerta": 0.10,     # despesa recorrente subiu mais de 10%
    "dias_contrato_renovacao": 60,
    "custo_hora": 45.0,                 # PREMISSA: custo da hora de trabalho
    "lift_minimo_par": 1.5,             # produtos comprados juntos acima do acaso
    "custo_contato_cliente": 25.0,      # PREMISSA: custo por cliente abordado
    "alfa_validacao": 0.05,
    # Portão de governança: tipos de ação que só andam com aprovação humana
    "acoes_com_aprovacao": ["contato_comercial", "desconto", "preco", "contrato", "processo"],
    "llm": {"provedor": "nenhum", "modelo": "qwen3:30b"},
}


def sem_comentarios(texto: str) -> str:
    """Tira comentários `# ...` (fora de aspas), para o gestor anotar o próprio config.json."""
    linhas = []
    for linha in texto.splitlines():
        dentro, saida = False, []
        for i, ch in enumerate(linha):
            if ch == '"' and (i == 0 or linha[i - 1] != "\\"):
                dentro = not dentro
            if ch == "#" and not dentro:
                break
            saida.append(ch)
        linhas.append("".join(saida))
    return "\n".join(linhas)


def carregar(pasta_dados: str | Path | None = None, arquivo: str | Path | None = None) -> dict:
    cfg = json.loads(json.dumps(PADRAO))
    candidatos = []
    if arquivo:
        candidatos.append(Path(arquivo))
    if pasta_dados:
        candidatos.append(Path(pasta_dados) / "config.json")
    for c in candidatos:
        if c.exists():
            try:
                extra = json.loads(sem_comentarios(c.read_text(encoding="utf-8")))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{c}: config.json inválido na linha {e.lineno} ({e.msg}). "
                                 "Confira aspas, vírgulas entre os itens e nenhuma vírgula depois do último.")
            cfg["_informado"] = sorted(extra)
            for k, v in extra.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
            break
    return cfg
