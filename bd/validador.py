"""Validador de resultados — LOOP-R: Observar.

Compara o que foi previsto com o que aconteceu, usando o grupo de controle.
Só conta o efeito INCREMENTAL: o que o grupo de teste fez a mais que o controle.

Arquivo de resultados (CSV): alvo_id, grupo (teste|controle), converteu (0|1), receita
"""
from __future__ import annotations

import csv
from pathlib import Path

from .estat import z_duas_proporcoes
from .memoria import Memoria
from .relatorio import brl


class ErroGovernanca(RuntimeError):
    pass


def ler_resultados(caminho: str | Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))
    for c in ("alvo_id", "grupo", "converteu", "receita"):
        if not linhas or c not in linhas[0]:
            raise ValueError(f"resultados: falta a coluna {c}")
    return [{"alvo_id": r["alvo_id"], "grupo": r["grupo"].strip().lower(),
             "converteu": int(float(r["converteu"])), "receita": float(r["receita"] or 0)} for r in linhas]


def validar(mem: Memoria, did: str, caminho: str | Path, cfg: dict, autor: str = "validador") -> dict:
    d = mem.obter(did)
    if d is None:
        raise KeyError(did)
    if d.estado not in ("aprovada", "em_teste"):
        raise ErroGovernanca(f"{did} está '{d.estado}': só se valida teste aprovado por um humano")
    linhas = ler_resultados(caminho)
    t = [r for r in linhas if r["grupo"] == "teste"]
    c = [r for r in linhas if r["grupo"] == "controle"]
    if not t or not c:
        raise ValueError("precisa de linhas nos dois grupos: teste e controle")
    margem = d.calculo.entradas.get("margem", cfg["margem_contribuicao"])
    conv_t = sum(r["converteu"] for r in t) / len(t)
    conv_c = sum(r["converteu"] for r in c) / len(c)
    rec_t = sum(r["receita"] for r in t) / len(t)
    rec_c = sum(r["receita"] for r in c) / len(c)
    incremental_receita = (rec_t - rec_c) * len(t)
    custo = cfg["custo_contato_cliente"] * len(t)
    contrib_incremental = round(incremental_receita * margem - custo, 2)
    _, p = z_duas_proporcoes(sum(r["converteu"] for r in t), len(t), sum(r["converteu"] for r in c), len(c))
    n_total = max(len(d.alvo_ids), 1)
    estimado = round(d.impacto * len(t) / n_total, 2)  # previsão proporcional ao grupo de teste
    precisao = round(max(0.0, 1 - abs(estimado - contrib_incremental) / estimado), 3) if estimado else None
    promovida = p < cfg["alfa_validacao"] and contrib_incremental > 0
    vencedora = (d.competicao or {}).get("vencedora", "")
    estrategia = vencedora.split("—")[-1].strip() if vencedora else "não informada"
    texto = (f"{estrategia}: conversão {conv_t:.0%} no teste contra {conv_c:.0%} no controle; "
             f"contribuição incremental {brl(contrib_incremental)} (prevista {brl(estimado)}); p = {p:.3f}. "
             + ("PROMOVIDA: entra como estratégia validada." if promovida
                else "NÃO PROMOVIDA: o efeito não se separou do acaso ou não pagou o custo."))
    mem.registrar_licao(descoberta_id=did, frente=d.frente, estrategia=estrategia, estimado=estimado,
                        observado=contrib_incremental, precisao=precisao, p_valor=round(p, 4),
                        promovida=promovida, texto=texto)
    mem.mudar_estado(did, "validada" if promovida else "descartada", autor, texto)
    return {
        "descoberta": did, "n_teste": len(t), "n_controle": len(c),
        "conversao_teste": round(conv_t, 4), "conversao_controle": round(conv_c, 4),
        "receita_media_teste": round(rec_t, 2), "receita_media_controle": round(rec_c, 2),
        "custo_campanha": round(custo, 2), "contribuicao_incremental": contrib_incremental,
        "previsto_para_o_grupo": estimado, "precisao": precisao, "p_valor": round(p, 4),
        "promovida": promovida, "licao": texto,
    }
