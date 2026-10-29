"""Empresa FICTÍCIA para demonstração e testes.

Todos os nomes e números são inventados. O cenário de reativação reproduz o
exemplo ilustrativo do documento de visão (120 clientes inativos, 40 de alta
frequência, ticket médio R$ 3.500, margem 30%) — não é resultado observado.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

REF = date(2026, 9, 30)
INICIO = date(2025, 10, 1)

PRODUTOS = [
    # id, nome, categoria, preco, custo
    ("P01", "Pacote de serviços", "Serviço", 3500, 2450),
    ("P02", "Licença anual", "Software", 1800, 1080),
    ("P03", "Instalação", "Serviço", 1200, 780),
    ("P04", "Manutenção anual", "Serviço", 2200, 1320),
    ("P05", "Treinamento", "Serviço", 900, 540),
    ("P06", "Sensor industrial", "Hardware", 650, 600),
    ("P07", "Cabo e conectores", "Hardware", 120, 110),
    ("P08", "Consultoria", "Serviço", 2600, 1300),
]
SEGMENTOS = ["Indústria", "Varejo", "Serviços", "Saúde"]


def _w(caminho: Path, cab: list[str], linhas: list[list]):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cab)
        w.writerows(linhas)


def gerar(pasta: str | Path, semente: int = 2026) -> Path:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(semente)
    preco = {p[0]: p[3] for p in PRODUTOS}
    clientes, vendas = [], []
    vid = 0

    def venda(cid, d, pid):
        nonlocal vid
        vid += 1
        vendas.append([f"V{vid:05d}", d.isoformat(), cid, pid, 1, f"{preco[pid]:.2f}"])

    # 120 inativos: 40 de alta frequência, 80 de baixa; só compravam o pacote (ticket R$ 3.500)
    for i in range(120):
        cid = f"C{i + 1:04d}"
        clientes.append([cid, f"Cliente Fictício {i + 1}", SEGMENTOS[i % 4], "Cidade Exemplo", "2024-01-15"])
        ultima = date(2026, 3, 1) + timedelta(days=(i * 7) % 115)   # mar–jun/2026, espalhado
        if i < 40:
            for k in range(8):                                       # a cada ~20 dias
                venda(cid, ultima - timedelta(days=20 * k), "P01")
        else:
            venda(cid, ultima - timedelta(days=150 + (i % 60)), "P01")
            venda(cid, ultima, "P01")

    # 280 ativos; 30 deles demorando mais que o normal (risco de abandono)
    for i in range(120, 400):
        cid = f"C{i + 1:04d}"
        clientes.append([cid, f"Cliente Fictício {i + 1}", SEGMENTOS[i % 4], "Cidade Exemplo", "2023-06-01"])
        em_risco = i < 150
        intervalo = 18 + (i % 8)
        ultima = REF - timedelta(days=(intervalo * 2 + 12 + i % 20) if em_risco else (i % 12))
        d = ultima
        n = 0
        tem_instalacao = rnd.random() < 0.4
        while d >= INICIO and n < 14:
            if tem_instalacao and n % 3 == 0:
                pid = "P03"
            elif n % 3 == 1 and tem_instalacao and rnd.random() < 0.75:
                pid = "P04"
            elif n % 3 == 1 and not tem_instalacao and rnd.random() < 0.08:
                pid = "P04"
            else:
                pid = rnd.choice(["P02", "P05", "P06", "P07", "P08", "P06", "P02"])
            venda(cid, d, pid)
            d -= timedelta(days=intervalo + rnd.randint(-2, 2))
            n += 1

    vendas.sort(key=lambda v: v[1])
    _w(pasta / "clientes.csv", ["cliente_id", "nome", "segmento", "cidade", "desde"], clientes)
    _w(pasta / "vendas.csv", ["venda_id", "data", "cliente_id", "produto_id", "quantidade", "valor"], vendas)
    _w(pasta / "produtos.csv", ["produto_id", "nome", "categoria", "preco", "custo"],
       [[a, b, c, f"{d:.2f}", f"{e:.2f}"] for a, b, c, d, e in PRODUTOS])

    # propostas: 18 esquecidas, outras recentes ou fechadas
    props = []
    for i in range(60):
        cid = f"C{rnd.randint(121, 400):04d}"
        d = REF - timedelta(days=rnd.randint(20, 200))
        if i < 18:
            status, contato = "aberta", REF - timedelta(days=35 + i * 3)
        elif i < 30:
            status, contato = "aberta", REF - timedelta(days=rnd.randint(1, 20))
        else:
            status, contato = rnd.choice(["ganha", "perdida"]), d + timedelta(days=10)
        props.append([f"PR{i + 1:03d}", cid, d.isoformat(), f"{rnd.choice([4200, 6800, 9500, 12000, 15800]):.2f}",
                      status, contato.isoformat()])
    _w(pasta / "propostas.csv", ["proposta_id", "cliente_id", "data", "valor", "status", "ultimo_contato"], props)

    # despesas mensais
    desp = []
    for m in range(12):
        d = date(2025 + (9 + m) // 12, (9 + m) % 12 + 1, 5)
        fixos = [
            ("Nuvem Alfa", "TI", 2400 if m < 7 else 3000),
            ("Contabilidade Exemplo", "Serviços contábeis", 2800 if m < 6 else 3200),
            ("Energia Local", "Energia", 5200 * (1 + 0.03 * ((m % 4) - 1.5) / 1.5)),
            ("Imóveis Exemplo", "Aluguel", 12000),
            ("CRM Um", "CRM", 900),
            ("CRM Dois", "CRM", 650),
            ("Limpeza Exemplo", "Limpeza", 1500),
        ]
        for forn, cat, v in fixos:
            desp.append([d.isoformat(), forn, cat, f"{v:.2f}", "sim", "2026-11-30" if forn == "Nuvem Alfa" else ""])
        desp.append([(d + timedelta(days=12)).isoformat(), "Diversos", "Material", f"{rnd.randint(200, 900):.2f}", "nao", ""])
    _w(pasta / "despesas.csv", ["data", "fornecedor", "categoria", "valor", "recorrente", "contrato_fim"], desp)

    # operação: a separação concentra o retrabalho
    ops = []
    etapas = [("Orçamento", 1.5, 0.05), ("Separação", 2.0, 0.22), ("Instalação", 4.0, 0.06), ("Faturamento", 0.8, 0.03)]
    for i in range(150):
        d = REF - timedelta(days=rnd.randint(0, 180))
        for etapa, h, prob in etapas:
            re = 1 if rnd.random() < prob else 0
            ops.append([f"OP{i + 1:04d}", d.isoformat(), etapa, f"{h * rnd.uniform(0.8, 1.3) * (1.6 if re else 1):.2f}", re])
    _w(pasta / "operacao.csv", ["pedido_id", "data", "etapa", "horas", "retrabalho"], ops)

    (pasta / "config.json").write_text(json.dumps({
        "_leia": "Empresa FICTÍCIA. Margem e conversões são premissas do exemplo do documento de visão.",
        "data_referencia": REF.isoformat(),
        "margem_contribuicao": 0.30,
        "conversao_reativacao": 0.20,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    (pasta / "LEIA-ME.txt").write_text(
        "DADOS FICTÍCIOS gerados por `python3 -m bd exemplo`. Nenhum cliente, fornecedor ou valor é real.\n",
        encoding="utf-8")
    return pasta


def simular_resultados(grupos_csv: str | Path, saida: str | Path, conv_teste=0.22, conv_controle=0.05,
                       ticket=3500.0, semente: int = 11) -> Path:
    """Resultado SIMULADO de um teste, para demonstrar o Validador. Não é dado real."""
    rnd = random.Random(semente)
    linhas = list(csv.DictReader(open(grupos_csv, encoding="utf-8")))
    out = []
    for grupo, conv in (("teste", conv_teste), ("controle", conv_controle)):
        ids = [r["alvo_id"] for r in linhas if r["grupo"] == grupo]
        k = round(len(ids) * conv)
        sim = set(rnd.sample(ids, k))
        out += [[a, grupo, int(a in sim), f"{ticket if a in sim else 0:.2f}"] for a in ids]
    _w(Path(saida), ["alvo_id", "grupo", "converteu", "receita"], out)
    return Path(saida)
