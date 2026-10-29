"""Agente Memória — LOOP-R: Reforçar.

Guarda execuções, descobertas, cada mudança de estado (quem, quando, por quê) e
as lições. Só uma estratégia que passou na validação vira "promovida" e ganha
peso nas próximas competições. O resto fica registrado como descartado.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .modelos import Descoberta

ESQUEMA = """
create table if not exists execucoes (
  id integer primary key autoincrement,
  quando text not null, pasta text not null, hashes text not null, versao text not null
);
create table if not exists descobertas (
  id text primary key, execucao_id integer, frente text, estado text,
  prioridade real, impacto real, confianca real, dados text not null, atualizado text
);
create table if not exists eventos (
  id integer primary key autoincrement, descoberta_id text, quando text,
  tipo text, autor text, detalhe text
);
create table if not exists licoes (
  id integer primary key autoincrement, quando text, descoberta_id text, frente text,
  estrategia text, estimado real, observado real, precisao real, p_valor real,
  promovida integer, texto text
);
"""


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Memoria:
    nome = "Memória"

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.caminho)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(ESQUEMA)

    def fechar(self):
        self.db.close()

    def nova_execucao(self, pasta: str, hashes: dict, versao: str) -> int:
        cur = self.db.execute("insert into execucoes (quando, pasta, hashes, versao) values (?,?,?,?)",
                              (agora(), str(pasta), json.dumps(hashes), versao))
        self.db.commit()
        return cur.lastrowid

    def registrar_evento(self, did: str, tipo: str, autor: str, detalhe: str = ""):
        self.db.execute("insert into eventos (descoberta_id, quando, tipo, autor, detalhe) values (?,?,?,?,?)",
                        (did, agora(), tipo, autor, detalhe))
        self.db.commit()

    def salvar(self, d: Descoberta, execucao_id: int | None = None):
        anterior = self.obter(d.id)
        # estado decidido por humano (aprovada, rejeitada, validada...) sobrevive a uma nova análise
        if anterior and anterior.estado in ("aprovada", "rejeitada", "em_teste", "validada", "descartada") \
                and d.estado in ("auditada", "aguardando_aprovacao", "localizada"):
            d.estado = anterior.estado
        self.db.execute(
            "insert into descobertas (id, execucao_id, frente, estado, prioridade, impacto, confianca, dados, atualizado)"
            " values (?,?,?,?,?,?,?,?,?) on conflict(id) do update set execucao_id=coalesce(excluded.execucao_id, execucao_id),"
            " frente=excluded.frente, estado=excluded.estado, prioridade=excluded.prioridade, impacto=excluded.impacto,"
            " confianca=excluded.confianca, dados=excluded.dados, atualizado=excluded.atualizado",
            (d.id, execucao_id, d.frente, d.estado, d.prioridade, d.impacto, d.confianca,
             json.dumps(d.to_dict(), ensure_ascii=False, default=str), agora()))
        self.db.commit()

    def obter(self, did: str) -> Descoberta | None:
        r = self.db.execute("select dados from descobertas where id=?", (did,)).fetchone()
        return Descoberta.from_dict(json.loads(r["dados"])) if r else None

    def listar(self) -> list[Descoberta]:
        rows = self.db.execute("select dados from descobertas order by prioridade desc").fetchall()
        return [Descoberta.from_dict(json.loads(r["dados"])) for r in rows]

    def mudar_estado(self, did: str, estado: str, autor: str, detalhe: str = "") -> Descoberta:
        d = self.obter(did)
        if d is None:
            raise KeyError(f"descoberta não encontrada: {did}")
        de = d.estado
        d.estado = estado
        self.salvar(d)
        self.registrar_evento(did, f"{de} → {estado}", autor, detalhe)
        return d

    def eventos(self, did: str | None = None) -> list[dict]:
        q = "select * from eventos" + (" where descoberta_id=?" if did else "") + " order by id"
        return [dict(r) for r in self.db.execute(q, (did,) if did else ())]

    def registrar_licao(self, **k):
        self.db.execute(
            "insert into licoes (quando, descoberta_id, frente, estrategia, estimado, observado, precisao, p_valor, promovida, texto)"
            " values (?,?,?,?,?,?,?,?,?,?)",
            (agora(), k["descoberta_id"], k["frente"], k["estrategia"], k["estimado"], k["observado"],
             k["precisao"], k["p_valor"], int(k["promovida"]), k["texto"]))
        self.db.commit()

    def licoes(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("select * from licoes order by id")]

    def estrategias_validadas(self, frente: str) -> set[str]:
        rows = self.db.execute("select estrategia from licoes where frente=? and promovida=1", (frente,))
        return {r["estrategia"] for r in rows}

    def metricas(self) -> dict:
        lic = self.licoes()
        validadas = [x for x in lic if x["promovida"]]
        precs = [x["precisao"] for x in lic if x["precisao"] is not None]
        estados = {r["estado"]: r["n"] for r in
                   self.db.execute("select estado, count(*) n from descobertas group by estado")}
        return {
            "oportunidades_validadas": len(validadas),
            "impacto_incremental": round(sum(x["observado"] for x in validadas), 2),
            "precisao_media_hipoteses": round(sum(precs) / len(precs), 3) if precs else None,
            "testes_concluidos": len(lic),
            "descobertas_por_estado": estados,
        }
