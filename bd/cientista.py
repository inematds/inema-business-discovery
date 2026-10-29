"""Agente Cientista — LOOP-R: Propor.

Para cada descoberta formula intervenções possíveis e coloca três agentes para
competir com estratégias independentes (A Recuperação, B Oferta, C Relacionamento).
Um avaliador recebe as propostas embaralhadas e sem a autoria, escolhe uma, e só
depois a autoria é revelada. Se a memória já tem uma estratégia validada para a
mesma frente, ela entra no placar como bônus (Reforçar).
"""
from __future__ import annotations

import random

from .modelos import Descoberta

# efeito = multiplicador sobre o impacto estimado da descoberta (PREMISSAS explícitas)
ESTRATEGIAS = {
    "receita": [
        ("A", "Recuperação", "Contato personalizado do vendedor, com histórico do cliente na mão.",
         1.00, 0.0, "baixo", "conversão base; custo só do contato"),
        ("B", "Oferta", "Desconto segmentado de 10% para quem voltar a comprar.",
         0.93, 0.0, "alto", "converte ~40% mais, mas o desconto come 1/3 da margem; cria precedente de preço"),
        ("C", "Relacionamento", "Benefício de serviço (revisão, frete, suporte) sem mexer no preço.",
         1.10, 0.08, "baixo", "converte ~20% mais; o benefício custa ~8% do impacto"),
    ],
    "despesa": [
        ("A", "Renegociar", "Renegociar com o fornecedor atual usando cotações.",
         0.70, 0.0, "baixo", "recupera ~70% do aumento sem trocar"),
        ("B", "Trocar", "Trocar de fornecedor pelo melhor preço.",
         1.00, 0.15, "medio", "recupera tudo, mas a troca custa ~15% e tem risco de transição"),
        ("C", "Consolidar", "Juntar compras em um contrato anual com desconto.",
         0.85, 0.05, "baixo", "~85% do ganho com pouco atrito"),
    ],
    "processo": [
        ("A", "Checklist", "Checklist obrigatória antes da etapa.",
         0.60, 0.0, "baixo", "reduz parte do retrabalho, custo quase zero"),
        ("B", "Automação", "Automatizar a conferência com um agente/script.",
         1.00, 0.30, "medio", "corta mais, mas custa implantar"),
        ("C", "Treinamento", "Treinar a equipe nas 5 causas principais.",
         0.70, 0.10, "baixo", "efeito médio, depende de manter"),
    ],
    "preco": [
        ("A", "Reajuste direto", "Reajustar o preço de tabela.",
         1.00, 0.0, "alto", "ganho total se o volume segurar"),
        ("B", "Pacote", "Vender o item em pacote com outro de margem alta.",
         0.80, 0.05, "medio", "ganho menor, menos rejeição"),
        ("C", "Versão premium", "Criar versão premium e manter a básica.",
         0.60, 0.10, "baixo", "ganho menor e mais seguro"),
    ],
}

FAMILIA = {
    "receita_perdida": "receita",
    "risco_abandono": "receita",
    "oportunidade_comercial": "receita",
    "despesas_evitaveis": "despesa",
    "ineficiencia_operacional": "processo",
}

PENALIDADE_RISCO = {"baixo": 0.0, "medio": 0.07, "alto": 0.15}


class Cientista:
    nome = "Cientista"

    def __init__(self, memoria=None, semente: int = 7):
        self.memoria = memoria
        self.semente = semente

    def familia(self, d: Descoberta) -> str:
        return "preco" if d.acao_tipo == "preco" else FAMILIA[d.frente]

    def propor(self, d: Descoberta) -> None:
        estrategias = ESTRATEGIAS[self.familia(d)]
        d.intervencoes = [f"{nome}: {desc}" for _, nome, desc, *_ in estrategias]
        d.competicao = self.competir(d)

    def competir(self, d: Descoberta) -> dict:
        estrategias = ESTRATEGIAS[self.familia(d)]
        promovidas = set()
        if self.memoria is not None:
            promovidas = self.memoria.estrategias_validadas(d.frente)
        propostas = []
        for agente, nome, desc, efeito, custo_rel, risco, nota in estrategias:
            bruto = d.impacto * efeito
            custo = d.custo_estimado + d.impacto * custo_rel
            propostas.append({
                "agente": f"Agente {agente} — {nome}",
                "estrategia": nome,
                "descricao": desc,
                "premissa": nota,
                "impacto_bruto": round(bruto, 2),
                "custo": round(custo, 2),
                "risco": risco,
            })
        # avaliação às cegas: embaralha e tira a autoria antes de pontuar
        rnd = random.Random(f"{self.semente}-{d.id}")
        ordem = list(range(len(propostas)))
        rnd.shuffle(ordem)
        cegas = []
        for i, idx in enumerate(ordem, start=1):
            p = propostas[idx]
            liquido = p["impacto_bruto"] - p["custo"]
            nota = liquido * (1 - PENALIDADE_RISCO[p["risco"]])
            motivo = []
            if p["estrategia"] in promovidas:
                nota *= 1.10
                motivo.append("já validada antes nesta frente (+10%)")
            cegas.append({"rotulo": f"Proposta {i}", "_idx": idx, "liquido": round(liquido, 2),
                          "nota": round(nota, 2), "risco": p["risco"], "bonus": motivo})
        vencedora = max(cegas, key=lambda c: c["nota"])
        revelado = {c["rotulo"]: propostas[c["_idx"]]["agente"] for c in cegas}
        for c in cegas:
            c.pop("_idx")
        return {
            "propostas": propostas,
            "avaliacao_cega": cegas,
            "vencedora_rotulo": vencedora["rotulo"],
            "vencedora": revelado[vencedora["rotulo"]],
            "revelacao": revelado,
            "criterio": "contribuição líquida (impacto − custo) com desconto de risco: médio −7%, alto −15%",
        }
