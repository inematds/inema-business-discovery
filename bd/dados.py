"""Leitura dos CSVs exportados do CRM, do financeiro e da operação.

Primeiro piloto sem integração: o gestor exporta planilhas e aponta a pasta.
Arquivos esperados (os que faltarem só desligam a frente correspondente):

  clientes.csv   cliente_id, nome, segmento, cidade, desde
  vendas.csv     venda_id, data, cliente_id, produto_id, quantidade, valor
  produtos.csv   produto_id, nome, categoria, preco, custo
  propostas.csv  proposta_id, cliente_id, data, valor, status, ultimo_contato
  despesas.csv   data, fornecedor, categoria, valor, recorrente, contrato_fim
  operacao.csv   pedido_id, data, etapa, horas, retrabalho
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ESQUEMA = {
    "clientes": ["cliente_id", "nome", "segmento"],
    "vendas": ["venda_id", "data", "cliente_id", "produto_id", "valor"],
    "produtos": ["produto_id", "nome", "categoria", "preco"],
    "propostas": ["proposta_id", "cliente_id", "data", "valor", "status", "ultimo_contato"],
    "despesas": ["data", "fornecedor", "categoria", "valor", "recorrente"],
    "operacao": ["pedido_id", "data", "etapa", "horas", "retrabalho"],
}

CAMPOS_DATA = {"data", "desde", "ultimo_contato", "contrato_fim"}
CAMPOS_NUM = {"valor", "quantidade", "preco", "custo", "horas", "retrabalho"}


class ErroDados(ValueError):
    pass


def _data(txt: str) -> date | None:
    txt = (txt or "").strip()
    if not txt:
        return None
    for sep in ("-", "/"):
        partes = txt.split(sep)
        if len(partes) == 3:
            a, b, c = partes
            if len(a) == 4:
                return date(int(a), int(b), int(c))
            return date(int(c), int(b), int(a))  # dd/mm/aaaa
    raise ErroDados(f"data inválida: {txt!r}")


def _num(txt: str) -> float:
    txt = (txt or "").strip()
    if not txt:
        return 0.0
    if "," in txt and "." in txt:      # 1.234,56
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:                    # 1234,56
        txt = txt.replace(",", ".")
    return float(txt)


@dataclass
class Base:
    pasta: Path
    tabelas: dict[str, list[dict]] = field(default_factory=dict)
    hashes: dict[str, str] = field(default_factory=dict)
    problemas: list[str] = field(default_factory=list)

    def tem(self, nome: str) -> bool:
        return bool(self.tabelas.get(nome))

    def __getitem__(self, nome: str) -> list[dict]:
        return self.tabelas.get(nome, [])

    def periodo(self) -> tuple[date, date] | None:
        datas = [v["data"] for v in self["vendas"] if v.get("data")]
        return (min(datas), max(datas)) if datas else None


def carregar(pasta: str | Path) -> Base:
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise ErroDados(f"pasta não encontrada: {pasta}")
    base = Base(pasta=pasta)
    for nome, obrig in ESQUEMA.items():
        arq = pasta / f"{nome}.csv"
        if not arq.exists():
            continue
        bruto = arq.read_bytes()
        base.hashes[arq.name] = hashlib.sha256(bruto).hexdigest()[:16]
        texto = bruto.decode("utf-8-sig")
        sep = ";" if texto.splitlines()[0].count(";") > texto.splitlines()[0].count(",") else ","
        leitor = csv.DictReader(texto.splitlines(), delimiter=sep)
        faltam = [c for c in obrig if c not in (leitor.fieldnames or [])]
        if faltam:
            raise ErroDados(f"{arq.name}: faltam colunas {faltam}")
        linhas = []
        for i, lin in enumerate(leitor, start=2):
            reg = {}
            for k, v in lin.items():
                if k is None:
                    continue
                k = k.strip()
                try:
                    if k in CAMPOS_DATA:
                        reg[k] = _data(v)
                    elif k in CAMPOS_NUM:
                        reg[k] = _num(v)
                    else:
                        reg[k] = (v or "").strip()
                except (ValueError, ErroDados) as e:
                    base.problemas.append(f"{arq.name} linha {i}: {e}")
                    reg[k] = None
            linhas.append(reg)
        base.tabelas[nome] = linhas
    if not base.tem("vendas"):
        raise ErroDados("vendas.csv é obrigatório (é dele que saem clientes, frequência e ticket)")
    return base
