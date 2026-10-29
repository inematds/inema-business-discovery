"""Agente Experimentador — LOOP-R: Operar (planejado).

Simula cenários e monta o teste controlado: sorteia grupo de teste e grupo de
controle, calcula o tamanho de amostra necessário e avisa quando o teste será
só indicativo.
"""
from __future__ import annotations

import random

from .estat import amostra_por_grupo
from .modelos import Descoberta

RETORNO_NATURAL = 0.05  # PREMISSA: parte dos inativos voltaria sozinha, sem campanha


class Experimentador:
    nome = "Experimentador"

    def __init__(self, cfg: dict, semente: int = 42):
        self.cfg = cfg
        self.semente = semente

    def planejar(self, d: Descoberta) -> None:
        cenarios = {
            "pessimista": round(d.impacto * 0.5, 2),
            "base": round(d.impacto, 2),
            "otimista": round(d.impacto * 1.5, 2),
        }
        plano = {"cenarios": cenarios, "duracao_dias": 30}
        conv = d.calculo.entradas.get("conversao")
        if d.alvo_ids and conv and d.acao_tipo == "contato_comercial":
            alvos = list(d.alvo_ids)
            random.Random(f"{self.semente}-{d.id}").shuffle(alvos)
            meio = len(alvos) // 2
            teste, controle = sorted(alvos[:meio]), sorted(alvos[meio:])
            precisa = amostra_por_grupo(RETORNO_NATURAL, conv, self.cfg["alfa_validacao"])
            plano.update({
                "tipo": "teste controlado (A/B com grupo de controle)",
                "grupo_teste": teste,
                "grupo_controle": controle,
                "metrica": "contribuição incremental por cliente (teste − controle) em 30 dias",
                "conversao_esperada": conv,
                "retorno_natural_premissa": RETORNO_NATURAL,
                "amostra_necessaria_por_grupo": precisa,
                "suficiente": min(len(teste), len(controle)) >= precisa,
            })
            if not plano["suficiente"]:
                plano["aviso"] = (f"cada grupo tem {min(len(teste), len(controle))} clientes; para separar "
                                  f"{conv:.0%} de {RETORNO_NATURAL:.0%} com 80% de poder seriam {precisa}. "
                                  "O resultado será indicativo, não prova.")
        else:
            plano.update({
                "tipo": "antes e depois com período de comparação",
                "metrica": "valor mensal antes × depois, mesmo mês do ano anterior como referência",
            })
        d.plano_teste = plano
