"""Agente Auditor — confere dados, contas e fundamentação.

Quem fez a conta (Investigador) nunca é quem confere. O Auditor refaz cada
cálculo a partir das entradas, verifica se os alvos existem nos dados e se a
descoberta tem evidência e período. Reprova o que não fecha.
"""
from __future__ import annotations

import ast
import operator

from .dados import Base
from .modelos import Descoberta

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def avaliar(expressao: str, entradas: dict[str, float]) -> float:
    """Avalia só aritmética simples com as variáveis dadas (sem eval)."""

    def ev(no):
        if isinstance(no, ast.Expression):
            return ev(no.body)
        if isinstance(no, ast.BinOp) and type(no.op) in _OPS:
            return _OPS[type(no.op)](ev(no.left), ev(no.right))
        if isinstance(no, ast.Name):
            if no.id not in entradas:
                raise ValueError(f"variável sem entrada: {no.id}")
            return float(entradas[no.id])
        if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
            return float(no.value)
        raise ValueError(f"expressão não permitida: {ast.dump(no)}")

    return ev(ast.parse(expressao, mode="eval"))


class Auditor:
    nome = "Auditor"

    def __init__(self, base: Base, tolerancia: float = 0.01):
        self.base = base
        self.tol = tolerancia
        self.ids_validos = {
            "clientes": {c["cliente_id"] for c in base["clientes"]} | {v["cliente_id"] for v in base["vendas"]},
            "propostas": {p["proposta_id"] for p in base["propostas"]},
        }

    def auditar(self, d: Descoberta) -> None:
        falhas, avisos = [], []
        try:
            refeito = round(avaliar(d.calculo.expressao, d.calculo.entradas), 2)
            if abs(refeito - d.calculo.resultado) > max(self.tol, abs(d.calculo.resultado) * 1e-6):
                falhas.append(f"conta não fecha: refeita = {refeito}, declarada = {d.calculo.resultado}")
        except (ValueError, ZeroDivisionError) as e:
            refeito = None
            falhas.append(f"conta não reproduzível: {e}")
        for k, v in d.calculo.entradas.items():
            if v is None or v < 0:
                falhas.append(f"entrada inválida: {k} = {v}")
        if not d.evidencias:
            falhas.append("sem evidência")
        if not d.periodo:
            falhas.append("sem período analisado")
        if not d.origem_dados:
            falhas.append("sem origem dos dados")
        for arq in d.origem_dados:
            if arq not in self.base.hashes:
                avisos.append(f"{arq} não estava na pasta: parte da conta usa premissa")
        if d.acao_tipo == "contato_comercial" and d.alvo_ids:
            universo = self.ids_validos["propostas"] if d.id == "RP-PROPOSTAS" else self.ids_validos["clientes"]
            fantasmas = [a for a in d.alvo_ids if a not in universo]
            if fantasmas:
                falhas.append(f"{len(fantasmas)} alvos não existem nos dados (ex.: {fantasmas[:3]})")
        if self.base.problemas:
            avisos.append(f"{len(self.base.problemas)} linhas com problema na leitura dos CSVs")
        d.auditoria = {
            "auditor": self.nome,
            "conta_refeita": refeito,
            "falhas": falhas,
            "avisos": avisos,
            "aprovada": not falhas,
            "hashes": {a: self.base.hashes.get(a) for a in d.origem_dados},
        }
        d.estado = "auditada" if not falhas else "reprovada_auditoria"
