"""Estatística básica sem dependências externas."""
from __future__ import annotations

import math


def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def z_duas_proporcoes(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """Teste z para diferença de proporções. Devolve (z, p-valor unilateral p1 > p2)."""
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (p1 - p2) / se
    return z, 1 - _phi(z)


def amostra_por_grupo(p0: float, p1: float, alfa: float = 0.05, poder: float = 0.8) -> int:
    """Tamanho por grupo para detectar p1 contra p0 (teste unilateral)."""
    if p1 <= p0:
        return 10**9
    za = _inv_phi(1 - alfa)
    zb = _inv_phi(poder)
    pm = (p0 + p1) / 2
    num = (za * math.sqrt(2 * pm * (1 - pm)) + zb * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2
    return math.ceil(num / (p1 - p0) ** 2)


def _inv_phi(q: float) -> float:
    # bisseção: suficiente para tamanho de amostra
    lo, hi = -10.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _phi(mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
