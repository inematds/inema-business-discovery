"""Raciocínio em linguagem natural — opcional e sem API paga.

O motor da plataforma (contas, auditoria, validação) não usa modelo nenhum.
O modelo só escreve um parágrafo explicando a descoberta para o gestor.

Provedores:
  nenhum      (padrão) — não chama nada
  ollama      — modelo local em http://localhost:11434 (ex.: qwen3:30b)
  claude-cli  — `claude -p` pela sua assinatura do Claude Code
  codex-cli   — `codex exec` pela sua assinatura do ChatGPT

Nenhum provedor lê chave de API. O texto enviado leva só números agregados:
nenhum nome de cliente sai da máquina (LGPD).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request

from .modelos import Descoberta


def prompt(d: Descoberta) -> str:
    return (
        "Você é o Cientista de uma equipe de análise de negócios. Explique em até 4 frases, em português "
        "simples, para o dono da empresa: o que foi encontrado, por que pode estar acontecendo, o que testar "
        "e o que pode dar errado. Não invente números além destes.\n\n"
        f"Frente: {d.frente}\nAchado: {d.titulo}\nResumo: {d.resumo}\n"
        f"Conta: {d.calculo.formula} = {d.calculo.resultado}\n"
        f"Premissas: {'; '.join(d.premissas)}\nRiscos: {'; '.join(d.riscos)}\n"
        f"Explicações alternativas: {'; '.join(d.explicacoes_alternativas)}\n"
    )


def narrar(d: Descoberta, cfg: dict, timeout: int = 120) -> str:
    prov = (cfg.get("llm") or {}).get("provedor", "nenhum")
    modelo = (cfg.get("llm") or {}).get("modelo", "qwen3:30b")
    texto = prompt(d)
    try:
        if prov == "ollama":
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps({"model": modelo, "prompt": texto, "stream": False,
                                 "options": {"temperature": 0.2}}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.load(r).get("response", "")
        elif prov == "claude-cli" and shutil.which("claude"):
            out = subprocess.run(["claude", "-p", texto], capture_output=True, text=True, timeout=timeout).stdout
        elif prov == "codex-cli" and shutil.which("codex"):
            out = subprocess.run(["codex", "exec", "-s", "read-only", "--skip-git-repo-check", "-"],
                                 input=texto, capture_output=True, text=True, timeout=timeout).stdout
        else:
            return ""
    except Exception as e:  # o relatório sai mesmo sem o texto
        return f"(narrativa indisponível: {e.__class__.__name__})"
    # remove raciocínio interno de modelos que o expõem
    if "</think>" in out:
        out = out.split("</think>", 1)[1]
    return out.strip()
