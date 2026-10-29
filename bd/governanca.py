"""Portão humano: ações comerciais, de preço, contrato e processo só andam com aprovação.

Toda decisão fica na trilha (quem, quando, o quê). Nenhum agente aprova sozinho.
"""
from __future__ import annotations

from .memoria import Memoria
from .validador import ErroGovernanca


def _exigir_nome(por: str):
    if not por or not por.strip() or por.strip().lower() in ("ciclo", "agente", "validador", "auto"):
        raise ErroGovernanca("aprovação precisa do nome de uma pessoa")


def aprovar(mem: Memoria, did: str, por: str, nota: str = ""):
    _exigir_nome(por)
    d = mem.obter(did)
    if d is None:
        raise KeyError(did)
    if d.estado != "aguardando_aprovacao":
        raise ErroGovernanca(f"{did} está '{d.estado}', não aguarda aprovação")
    return mem.mudar_estado(did, "aprovada", por.strip(), nota or "teste aprovado")


def rejeitar(mem: Memoria, did: str, por: str, nota: str = ""):
    _exigir_nome(por)
    d = mem.obter(did)
    if d is None:
        raise KeyError(did)
    if d.estado not in ("aguardando_aprovacao", "aprovada"):
        raise ErroGovernanca(f"{did} está '{d.estado}', não pode ser rejeitada agora")
    return mem.mudar_estado(did, "rejeitada", por.strip(), nota or "rejeitada pelo gestor")
