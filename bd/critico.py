"""Agente Crítico — tenta refutar a hipótese.

Procura explicações alternativas e sinais de que o número está inflado. Cada
problema encontrado baixa a confiança da descoberta. O Crítico não decide nada:
ele só deixa o caso mais difícil de passar.
"""
from __future__ import annotations

from collections import Counter

from .dados import Base
from .modelos import Descoberta

ALTERNATIVAS = {
    "receita_perdida": [
        "Os clientes podem ter fechado ou mudado de ramo (não há o que reativar).",
        "Sazonalidade: a parada pode ser do calendário, não do relacionamento.",
        "Um concorrente pode ter oferecido preço que não vale a pena cobrir.",
    ],
    "despesas_evitaveis": [
        "O aumento pode ser reajuste contratual legítimo (índice de inflação).",
        "Pode ter havido aumento de volume contratado, não de preço.",
    ],
    "risco_abandono": [
        "O cliente pode estar comprando em lote maior e com menos frequência.",
        "A demora pode ser sazonal e repetir todo ano.",
    ],
    "ineficiencia_operacional": [
        "O retrabalho pode vir de pedido mal especificado pelo cliente, não da etapa.",
        "Registro de horas pode estar inconsistente entre equipes.",
    ],
    "oportunidade_comercial": [
        "Comprar junto não prova que um produto puxa o outro (correlação ≠ causa).",
        "Clientes que não compram o complemento podem já comprar de outro fornecedor.",
    ],
}


class Critico:
    nome = "Crítico"

    def __init__(self, base: Base):
        self.base = base
        self.receita_cli = Counter()
        self.ultima = {}
        for v in base["vendas"]:
            self.receita_cli[v["cliente_id"]] += v["valor"]
            if v["cliente_id"] not in self.ultima or v["data"] > self.ultima[v["cliente_id"]]:
                self.ultima[v["cliente_id"]] = v["data"]

    def criticar(self, d: Descoberta) -> None:
        riscos = []
        ajuste = 0.0
        alvos_cli = [a for a in d.alvo_ids if a in self.receita_cli]
        if len(alvos_cli) >= 3:
            total = sum(self.receita_cli[a] for a in alvos_cli)
            top3 = sum(sorted((self.receita_cli[a] for a in alvos_cli), reverse=True)[:3])
            if total and top3 / total > 0.5:
                riscos.append(f"concentração: 3 alvos respondem por {top3 / total:.0%} do valor — o resultado depende deles")
                ajuste -= 0.1
        if d.alvo_ids and len(d.alvo_ids) < 30 and d.acao_tipo == "contato_comercial":
            riscos.append(f"amostra pequena ({len(d.alvo_ids)} alvos): variação alta no resultado")
            ajuste -= 0.1
        premissas = sum("PREMISSA" in p for p in d.premissas)
        if premissas >= 2:
            riscos.append(f"{premissas} premissas sem dado observado sustentam o número")
            ajuste -= 0.05
        if d.id == "RP-REATIVACAO" and alvos_cli:
            meses = Counter(self.ultima[a].strftime("%Y-%m") for a in alvos_cli)
            mes, qtd = meses.most_common(1)[0]
            if qtd / len(alvos_cli) > 0.5:
                riscos.append(f"{qtd} das paradas aconteceram em {mes}: pode ser corte de dados ou evento pontual")
                ajuste -= 0.1
        if d.risco == "alto":
            riscos.append("ação de risco alto: exige aprovação e teste pequeno antes de escalar")
        d.explicacoes_alternativas = list(ALTERNATIVAS.get(d.frente, []))
        d.riscos = riscos
        d.confianca = round(max(0.1, min(0.95, d.confianca + ajuste)), 2)
