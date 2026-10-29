"""Ciclo LOOP-R completo sobre uma pasta de dados.

Localizar (Investigador) → Propor (Cientista + competição) → Operar/planejar
(Experimentador) → conferir (Auditor) → refutar (Crítico) → priorizar →
portão humano → [teste real] → Observar (Validador) → Reforçar (Memória).

Quem faz nunca é quem avalia: o Investigador calcula, o Auditor refaz a conta,
o Crítico ataca, e um humano aprova toda ação sensível.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .auditor import Auditor
from .cientista import Cientista
from .config import carregar as carregar_cfg
from .critico import Critico
from .dados import carregar as carregar_dados
from .experimentador import Experimentador
from .investigador import Investigador
from .llm import narrar
from .memoria import Memoria
from .relatorio import brl

FATOR_RISCO = {"baixo": 1.0, "medio": 0.8, "alto": 0.6}


def prioridade(d) -> float:
    esperado = d.impacto * d.confianca - d.custo_estimado
    return round(esperado * FATOR_RISCO[d.risco], 2)


def analisar(pasta_dados, saida, cfg=None, usar_llm: bool = False, log=print) -> dict:
    pasta_dados, saida = Path(pasta_dados), Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    cfg = cfg or carregar_cfg(pasta_dados)
    base = carregar_dados(pasta_dados)
    mem = Memoria(saida / "memoria.sqlite")
    exec_id = mem.nova_execucao(str(pasta_dados), base.hashes, __version__)

    inv = Investigador(base, cfg)
    log(f"[L] Investigador: dados de {inv.periodo_txt}, margem {inv.margem:.0%} ({inv.margem_origem})")
    achados = inv.localizar()
    log(f"[L] {len(achados)} descobertas localizadas nas frentes")

    cientista, exp, aud, crit = Cientista(mem), Experimentador(cfg), Auditor(base), Critico(base)
    for d in achados:
        cientista.propor(d)        # P: hipóteses + competição A/B/C às cegas
        exp.planejar(d)            # O: cenários e teste controlado
        aud.auditar(d)             # conferência independente
        crit.criticar(d)           # tentativa de refutação
        d.prioridade = prioridade(d)
        if d.estado == "auditada" and d.acao_tipo in cfg["acoes_com_aprovacao"]:
            d.requer_aprovacao = True
            d.estado = "aguardando_aprovacao"
        if usar_llm:
            d.narrativa = narrar(d, cfg)
        mem.salvar(d, exec_id)
        mem.registrar_evento(d.id, "analise", "ciclo", f"execução {exec_id}")
        log(f"    {d.id:<16} {d.estado:<22} impacto {brl(d.impacto):>16}  confiança {d.confianca:.2f}")

    resultado = exportar(mem, saida, cfg, inv.periodo_txt)
    mem.fechar()
    return resultado


def exportar(mem: Memoria, saida: Path, cfg: dict, periodo: str = "") -> dict:
    from .relatorio import gerar_html

    descobertas = [d.to_dict() for d in mem.listar()]
    if not periodo and descobertas:
        periodo = max((d["periodo"] for d in descobertas), key=len)
    dados = {
        "versao": __version__,
        "periodo": periodo,
        "descobertas": descobertas,
        "metricas": mem.metricas(),
        "licoes": mem.licoes(),
        "eventos": mem.eventos(),
        "aviso": "Estimativas não são resultados. Só o teste com grupo de controle mede o efeito incremental.",
    }
    (saida / "descobertas.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1, default=str),
                                            encoding="utf-8")
    (saida / "relatorio.html").write_text(gerar_html(dados), encoding="utf-8")
    planos = saida / "planos"
    planos.mkdir(exist_ok=True)
    for d in descobertas:
        pt = d.get("plano_teste") or {}
        if pt.get("grupo_teste"):
            linhas = ["alvo_id,grupo"] + [f"{a},teste" for a in pt["grupo_teste"]] + \
                     [f"{a},controle" for a in pt["grupo_controle"]]
            (planos / f"{d['id']}-grupos.csv").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return dados
