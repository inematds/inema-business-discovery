"""Agente Investigador — LOOP-R: Localizar.

Varre as cinco frentes de descoberta e devolve descobertas com evidência e conta
reproduzível. Não usa modelo de linguagem: tudo aqui é cálculo sobre os dados,
para que o Auditor possa refazer cada número.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from itertools import combinations
from statistics import mean, median

from .dados import Base
from .modelos import Calculo, Descoberta


def _brl(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _pct(v: float) -> str:
    return f"{v * 100:.0f}%".replace(".", ",")


class Investigador:
    nome = "Investigador"

    def __init__(self, base: Base, cfg: dict):
        self.base = base
        self.cfg = cfg
        per = base.periodo()
        self.inicio, self.fim = per
        ref = cfg.get("data_referencia")
        self.ref = date.fromisoformat(ref) if ref else self.fim
        self.periodo_txt = f"{self.inicio.isoformat()} a {self.fim.isoformat()}"
        self.dias_periodo = max((self.fim - self.inicio).days, 1)
        self._compras = defaultdict(list)
        for v in base["vendas"]:
            if v.get("data") and v.get("cliente_id"):
                self._compras[v["cliente_id"]].append(v)
        for lst in self._compras.values():
            lst.sort(key=lambda x: x["data"])
        self.margem, self.margem_origem = self._margem()

    # ---------- apoio ----------
    def _margem(self) -> tuple[float, str]:
        if "margem_contribuicao" in self.cfg.get("_informado", []):
            return float(self.cfg["margem_contribuicao"]), "informada pelo gestor no config.json"
        prods = {p["produto_id"]: p for p in self.base["produtos"]}
        receita = custo = 0.0
        for v in self.base["vendas"]:
            p = prods.get(v.get("produto_id"))
            if not p or not p.get("custo"):
                continue
            qtd = v.get("quantidade") or 1
            receita += v["valor"]
            custo += p["custo"] * qtd
        if receita > 0 and custo > 0:
            return round(1 - custo / receita, 4), "calculada de produtos.csv (custo × quantidade)"
        return float(self.cfg["margem_contribuicao"]), "PREMISSA do config (sem custo por produto)"

    def _nome_cliente(self, cid: str) -> str:
        for c in self.base["clientes"]:
            if c["cliente_id"] == cid:
                return c.get("nome") or cid
        return cid

    def localizar(self) -> list[Descoberta]:
        achados: list[Descoberta] = []
        for f in (
            self.reativacao,
            self.propostas_esquecidas,
            self.despesas_subindo,
            self.fornecedores_sobrepostos,
            self.risco_abandono,
            self.retrabalho,
            self.venda_casada,
            self.margem_baixa,
        ):
            d = f()
            if d:
                achados.append(d)
        return achados

    # ---------- 1. Receita perdida ----------
    def reativacao(self) -> Descoberta | None:
        limite = self.ref - timedelta(days=self.cfg["dias_inativo"])
        inativos, alta = [], []
        tickets = []
        for cid, compras in self._compras.items():
            if len(compras) < 2 or compras[-1]["data"] >= limite:
                continue
            inativos.append(cid)
            tickets.extend(c["valor"] for c in compras)
            span = max((compras[-1]["data"] - compras[0]["data"]).days, 30)
            if len(compras) / span * 365 >= self.cfg["compras_ano_alta_frequencia"]:
                alta.append(cid)
        if not inativos:
            return None
        n = len(inativos)
        ticket = round(mean(tickets), 2)
        conv = self.cfg["conversao_reativacao"]
        receita = round(n * conv * ticket, 2)
        contrib = round(receita * self.margem, 2)
        return Descoberta(
            id="RP-REATIVACAO",
            frente="receita_perdida",
            titulo=f"{n} clientes pararam de comprar — {len(alta)} eram de alta frequência",
            resumo=(f"{n} clientes com 2 ou mais compras não compram há mais de {self.cfg['dias_inativo']} dias. "
                    f"Uma campanha de reativação pode trazer de volta {_brl(receita)} em receita "
                    f"e {_brl(contrib)} de contribuição, se a premissa de {_pct(conv)} de retorno se confirmar."),
            evidencias=[
                f"{n} clientes inativos (última compra antes de {limite.isoformat()})",
                f"{len(alta)} deles compravam {self.cfg['compras_ano_alta_frequencia']} ou mais vezes por ano",
                f"ticket médio histórico desses clientes: {_brl(ticket)}",
                f"margem de contribuição: {_pct(self.margem)} ({self.margem_origem})",
            ],
            origem_dados=["vendas.csv", "produtos.csv", "clientes.csv"],
            periodo=self.periodo_txt,
            hipotese="Uma campanha de reativação personalizada recupera parte da receita desses clientes.",
            calculo=Calculo(
                formula="contribuição = clientes abordados × conversão × ticket médio × margem",
                expressao="clientes * conversao * ticket * margem",
                entradas={"clientes": n, "conversao": conv, "ticket": ticket, "margem": self.margem},
                resultado=contrib,
            ),
            premissas=[f"conversão de {_pct(conv)} é PREMISSA (não observada)",
                       "não inclui custo de campanha nem impostos adicionais"],
            confianca=0.6,
            custo_estimado=round(n * self.cfg["custo_contato_cliente"], 2),
            risco="baixo",
            acao_tipo="contato_comercial",
            proximos_passos=["Separar grupo de controle (metade não recebe contato)",
                             "Aprovar o roteiro de contato",
                             "Medir a contribuição incremental em 30 dias"],
            alvo_ids=sorted(inativos),
        )

    def propostas_esquecidas(self) -> Descoberta | None:
        limite = self.ref - timedelta(days=self.cfg["dias_proposta_esquecida"])
        abertas = [p for p in self.base["propostas"]
                   if (p.get("status") or "").lower() == "aberta" and p.get("ultimo_contato")
                   and p["ultimo_contato"] < limite]
        if not abertas:
            return None
        total = round(sum(p["valor"] for p in abertas), 2)
        conv = self.cfg["conversao_proposta"]
        contrib = round(total * conv * self.margem, 2)
        return Descoberta(
            id="RP-PROPOSTAS",
            frente="receita_perdida",
            titulo=f"{len(abertas)} propostas abertas sem contato há mais de {self.cfg['dias_proposta_esquecida']} dias",
            resumo=f"{_brl(total)} em propostas paradas no CRM. Retomar o contato pode render {_brl(contrib)} de contribuição.",
            evidencias=[f"{len(abertas)} propostas com status 'aberta' e último contato antes de {limite.isoformat()}",
                        f"valor somado: {_brl(total)}",
                        f"maior proposta: {_brl(max(p['valor'] for p in abertas))}"],
            origem_dados=["propostas.csv"],
            periodo=self.periodo_txt,
            hipotese="Parte das propostas esquecidas ainda fecha se o vendedor retomar o contato.",
            calculo=Calculo(
                formula="contribuição = valor em aberto × chance de fechar × margem",
                expressao="valor_aberto * conversao * margem",
                entradas={"valor_aberto": total, "conversao": conv, "margem": self.margem},
                resultado=contrib,
            ),
            premissas=[f"chance de fechar de {_pct(conv)} é PREMISSA"],
            confianca=0.55,
            custo_estimado=round(len(abertas) * self.cfg["custo_contato_cliente"], 2),
            risco="baixo",
            acao_tipo="contato_comercial",
            proximos_passos=["Distribuir as propostas entre os vendedores", "Registrar o resultado de cada uma no CRM"],
            alvo_ids=sorted(p["proposta_id"] for p in abertas),
        )

    # ---------- 2. Despesas evitáveis ----------
    def _recorrentes(self) -> dict[tuple[str, str], list[dict]]:
        g = defaultdict(list)
        for d in self.base["despesas"]:
            if (d.get("recorrente") or "").lower() in ("sim", "s", "1", "true") and d.get("data"):
                g[(d["fornecedor"], d["categoria"])].append(d)
        for v in g.values():
            v.sort(key=lambda x: x["data"])
        return g

    def despesas_subindo(self) -> Descoberta | None:
        lim = self.cfg["aumento_despesa_alerta"]
        achados = []
        for (forn, cat), lst in self._recorrentes().items():
            if len(lst) < 6:
                continue
            antes = mean(x["valor"] for x in lst[:3])
            agora = mean(x["valor"] for x in lst[-3:])
            if antes > 0 and agora / antes - 1 > lim:
                achados.append((forn, cat, antes, agora))
        if not achados:
            return None
        diferenca_mensal = round(sum(a - b for _, _, b, a in achados), 2)
        anual = round(diferenca_mensal * 12, 2)
        return Descoberta(
            id="DE-REAJUSTES",
            frente="despesas_evitaveis",
            titulo=f"{len(achados)} despesas recorrentes subiram mais de {_pct(lim)}",
            resumo=f"Os reajustes somam {_brl(diferenca_mensal)} por mês. Renegociar ou trocar devolve até {_brl(anual)} por ano.",
            evidencias=[f"{f} ({c}): de {_brl(b)} para {_brl(a)} por mês (+{_pct(a / b - 1)})" for f, c, b, a in achados],
            origem_dados=["despesas.csv"],
            periodo=self.periodo_txt,
            hipotese="Os aumentos não acompanham o mercado e podem ser renegociados.",
            calculo=Calculo(
                formula="economia anual = aumento mensal somado × 12",
                expressao="aumento_mensal * meses",
                entradas={"aumento_mensal": diferenca_mensal, "meses": 12},
                resultado=anual,
            ),
            premissas=["supõe recuperar o valor anterior; parte do aumento pode ser inflação legítima"],
            confianca=0.75,
            custo_estimado=round(len(achados) * 2 * self.cfg["custo_hora"], 2),
            risco="baixo",
            acao_tipo="contrato",
            proximos_passos=["Pedir três cotações para cada item", "Renegociar com o fornecedor atual usando as cotações"],
            alvo_ids=sorted(f for f, _, _, _ in achados),
        )

    def fornecedores_sobrepostos(self) -> Descoberta | None:
        por_cat = defaultdict(dict)
        for (forn, cat), lst in self._recorrentes().items():
            por_cat[cat][forn] = mean(x["valor"] for x in lst[-3:])
        duplos = {c: f for c, f in por_cat.items() if len(f) >= 2}
        if not duplos:
            return None
        economia_mensal = round(sum(min(f.values()) for f in duplos.values()), 2)
        anual = round(economia_mensal * 12, 2)
        return Descoberta(
            id="DE-SOBREPOSICAO",
            frente="despesas_evitaveis",
            titulo=f"{len(duplos)} categorias pagam dois ou mais fornecedores pela mesma coisa",
            resumo=f"Consolidar em um fornecedor por categoria pode cortar {_brl(anual)} por ano.",
            evidencias=[f"{c}: " + ", ".join(f"{n} ({_brl(v)}/mês)" for n, v in f.items()) for c, f in duplos.items()],
            origem_dados=["despesas.csv"],
            periodo=self.periodo_txt,
            hipotese="Os serviços se sobrepõem e um deles pode ser cancelado sem perda.",
            calculo=Calculo(
                formula="economia anual = soma do menor contrato de cada categoria × 12",
                expressao="menor_mensal * meses",
                entradas={"menor_mensal": economia_mensal, "meses": 12},
                resultado=anual,
            ),
            premissas=["supõe que os fornecedores da mesma categoria entregam a mesma coisa — confirmar com a área"],
            confianca=0.5,
            custo_estimado=round(len(duplos) * 4 * self.cfg["custo_hora"], 2),
            risco="medio",
            acao_tipo="contrato",
            proximos_passos=["Perguntar à área usuária o que cada fornecedor entrega", "Cancelar o redundante ao fim do contrato"],
            alvo_ids=sorted(duplos),
        )

    # ---------- 3. Risco de abandono ----------
    def risco_abandono(self) -> Descoberta | None:
        limite_inativo = self.ref - timedelta(days=self.cfg["dias_inativo"])
        fator = self.cfg["fator_intervalo_risco"]
        em_risco, receita_anual = [], 0.0
        ano = self.ref - timedelta(days=365)
        for cid, compras in self._compras.items():
            if len(compras) < 4 or compras[-1]["data"] < limite_inativo:
                continue
            intervalos = [(b["data"] - a["data"]).days for a, b in zip(compras, compras[1:])]
            tipico = median(intervalos)
            atual = (self.ref - compras[-1]["data"]).days
            if tipico > 0 and atual >= 30 and atual > fator * tipico:
                em_risco.append(cid)
                receita_anual += sum(c["valor"] for c in compras if c["data"] >= ano)
        if not em_risco:
            return None
        receita_anual = round(receita_anual, 2)
        prob = self.cfg["prob_churn_em_risco"]
        contrib = round(receita_anual * prob * self.margem, 2)
        return Descoberta(
            id="RA-INTERVALO",
            frente="risco_abandono",
            titulo=f"{len(em_risco)} clientes ativos estão demorando mais que o normal para voltar",
            resumo=(f"Esses clientes ainda compram, mas o intervalo atual passou de {fator}× o intervalo típico deles. "
                    f"Juntos faturaram {_brl(receita_anual)} nos últimos 12 meses."),
            evidencias=[f"{len(em_risco)} clientes com intervalo atual > {fator}× o intervalo mediano",
                        f"receita deles nos últimos 12 meses: {_brl(receita_anual)}"],
            origem_dados=["vendas.csv"],
            periodo=self.periodo_txt,
            hipotese="Um contato preventivo agora evita que esses clientes virem inativos.",
            calculo=Calculo(
                formula="contribuição em risco = receita 12 meses × chance de perder × margem",
                expressao="receita_anual * prob_perda * margem",
                entradas={"receita_anual": receita_anual, "prob_perda": prob, "margem": self.margem},
                resultado=contrib,
            ),
            premissas=[f"chance de perda de {_pct(prob)} é PREMISSA"],
            confianca=0.5,
            custo_estimado=round(len(em_risco) * self.cfg["custo_contato_cliente"], 2),
            risco="baixo",
            acao_tipo="contato_comercial",
            proximos_passos=["Ligar para perguntar como está o atendimento", "Comparar com grupo de controle"],
            alvo_ids=sorted(em_risco),
        )

    # ---------- 4. Ineficiências operacionais ----------
    def retrabalho(self) -> Descoberta | None:
        ops = self.base["operacao"]
        if not ops:
            return None
        por = defaultdict(lambda: {"n": 0, "horas": 0.0, "re_n": 0, "re_horas": 0.0})
        for o in ops:
            e = por[o["etapa"]]
            e["n"] += 1
            e["horas"] += o["horas"] or 0
            if (o.get("retrabalho") or 0) >= 1:
                e["re_n"] += 1
                e["re_horas"] += o["horas"] or 0
        etapa, st = max(por.items(), key=lambda kv: kv[1]["re_horas"])
        if st["re_horas"] <= 0:
            return None
        datas = [o["data"] for o in ops if o.get("data")]
        dias = max((max(datas) - min(datas)).days, 1)
        horas_ano = round(st["re_horas"] * 365 / dias, 1)
        reducao = self.cfg.get("reducao_retrabalho", 0.5)
        economia = round(horas_ano * self.cfg["custo_hora"] * reducao, 2)
        gargalo = max(por.items(), key=lambda kv: kv[1]["horas"] / kv[1]["n"])
        return Descoberta(
            id="OP-RETRABALHO",
            frente="ineficiencia_operacional",
            titulo=f"A etapa '{etapa}' concentra o retrabalho: {_pct(st['re_n'] / st['n'])} dos pedidos voltam",
            resumo=f"São {horas_ano:.0f} horas por ano refazendo trabalho em '{etapa}'. Cortar metade economiza {_brl(economia)}.",
            evidencias=[f"'{etapa}': {st['re_n']} de {st['n']} registros com retrabalho ({st['re_horas']:.0f} h no período)",
                        f"gargalo de tempo: '{gargalo[0]}' com {gargalo[1]['horas'] / gargalo[1]['n']:.1f} h por pedido"],
            origem_dados=["operacao.csv"],
            periodo=f"{min(datas).isoformat()} a {max(datas).isoformat()}",
            hipotese=f"Uma checagem padronizada (ou automação) antes de '{etapa}' reduz o retrabalho pela metade.",
            calculo=Calculo(
                formula="economia anual = horas de retrabalho/ano × custo da hora × redução esperada",
                expressao="horas_ano * custo_hora * reducao",
                entradas={"horas_ano": horas_ano, "custo_hora": self.cfg["custo_hora"], "reducao": reducao},
                resultado=economia,
            ),
            premissas=[f"redução de {_pct(reducao)} e custo de {_brl(self.cfg['custo_hora'])}/h são PREMISSAS"],
            confianca=0.55,
            custo_estimado=round(16 * self.cfg["custo_hora"], 2),
            risco="medio",
            acao_tipo="processo",
            proximos_passos=["Listar as 5 causas mais comuns do retrabalho", "Testar uma checklist por 4 semanas"],
            alvo_ids=[etapa],
        )

    # ---------- 5. Oportunidades comerciais ----------
    def venda_casada(self) -> Descoberta | None:
        por_cli = defaultdict(set)
        for v in self.base["vendas"]:
            por_cli[v["cliente_id"]].add(v["produto_id"])
        n = len(por_cli)
        if n < 20:
            return None
        cont = defaultdict(int)
        par = defaultdict(int)
        for prods in por_cli.values():
            for p in prods:
                cont[p] += 1
            for a, b in combinations(sorted(prods), 2):
                par[(a, b)] += 1
        melhor = None
        for (a, b), ab in par.items():
            if ab < 5:
                continue
            lift = (ab / n) / ((cont[a] / n) * (cont[b] / n))
            if lift >= self.cfg["lift_minimo_par"] and (melhor is None or lift > melhor[2]):
                melhor = (a, b, lift, ab)
        if not melhor:
            return None
        a, b, lift, ab = melhor
        prods = {p["produto_id"]: p for p in self.base["produtos"]}
        # quem compra o mais popular dos dois e ainda não compra o outro
        ancora, alvo = (a, b) if cont[a] >= cont[b] else (b, a)
        alvos = sorted(c for c, ps in por_cli.items() if ancora in ps and alvo not in ps)
        preco = prods.get(alvo, {}).get("preco") or mean(v["valor"] for v in self.base["vendas"] if v["produto_id"] == alvo)
        conv = self.cfg.get("conversao_venda_casada", 0.15)
        contrib = round(len(alvos) * conv * preco * self.margem, 2)
        nome = lambda p: prods.get(p, {}).get("nome", p)  # noqa: E731
        return Descoberta(
            id="OC-VENDA-CASADA",
            frente="oportunidade_comercial",
            titulo=f"Quem compra '{nome(ancora)}' tende a levar '{nome(alvo)}' — {len(alvos)} clientes ainda não levaram",
            resumo=f"Os dois aparecem juntos {lift:.1f}× mais que o acaso. Oferecer o complemento pode render {_brl(contrib)}.",
            evidencias=[f"{ab} clientes compram os dois (lift {lift:.2f})",
                        f"{len(alvos)} clientes compram '{nome(ancora)}' e nunca compraram '{nome(alvo)}'",
                        f"preço de '{nome(alvo)}': {_brl(preco)}"],
            origem_dados=["vendas.csv", "produtos.csv"],
            periodo=self.periodo_txt,
            hipotese=f"Oferecer '{nome(alvo)}' a quem já compra '{nome(ancora)}' converte melhor que oferta genérica.",
            calculo=Calculo(
                formula="contribuição = clientes-alvo × conversão × preço × margem",
                expressao="clientes * conversao * preco * margem",
                entradas={"clientes": len(alvos), "conversao": conv, "preco": round(preco, 2), "margem": self.margem},
                resultado=contrib,
            ),
            premissas=[f"conversão de {_pct(conv)} é PREMISSA", "correlação de compra não prova causa"],
            confianca=0.45,
            custo_estimado=round(len(alvos) * self.cfg["custo_contato_cliente"] * 0.4, 2),
            risco="baixo",
            acao_tipo="contato_comercial",
            proximos_passos=["Montar a oferta do complemento", "Testar com metade dos clientes-alvo"],
            alvo_ids=alvos,
        )

    def margem_baixa(self) -> Descoberta | None:
        prods = [p for p in self.base["produtos"] if p.get("custo") and p.get("preco")]
        if len(prods) < 3:
            return None
        vend = defaultdict(float)
        qtd = defaultdict(float)
        for v in self.base["vendas"]:
            vend[v["produto_id"]] += v["valor"]
            qtd[v["produto_id"]] += v.get("quantidade") or 1
        margens = {p["produto_id"]: 1 - p["custo"] / p["preco"] for p in prods}
        media = mean(margens.values())
        baixos = [p for p in prods if margens[p["produto_id"]] < media * 0.6 and vend[p["produto_id"]] > 0]
        if not baixos:
            return None
        ajuste = self.cfg.get("ajuste_preco", 0.05)
        volume = round(sum(vend[p["produto_id"]] for p in baixos) * 365 / self.dias_periodo, 2)
        perda_volume = self.cfg.get("perda_volume_preco", 0.03)
        vend_baixos = sum(vend[p["produto_id"]] for p in baixos)
        margem_baixa = round(sum(margens[p["produto_id"]] * vend[p["produto_id"]] for p in baixos) / vend_baixos, 4)
        ganho = round(volume * ajuste - volume * perda_volume * margem_baixa, 2)
        return Descoberta(
            id="OC-PRECO",
            frente="oportunidade_comercial",
            titulo=f"{len(baixos)} produtos vendem bem com margem muito abaixo da média",
            resumo=f"Um reajuste de {_pct(ajuste)} nesses itens pode somar {_brl(ganho)} por ano, já descontando alguma perda de volume.",
            evidencias=[f"{p['nome']}: margem {_pct(margens[p['produto_id']])} (média {_pct(media)})" for p in baixos],
            origem_dados=["produtos.csv", "vendas.csv"],
            periodo=self.periodo_txt,
            hipotese="O cliente desses itens é pouco sensível a um reajuste pequeno.",
            calculo=Calculo(
                formula="ganho anual = vendas/ano × reajuste − vendas/ano × perda de volume × margem desses itens",
                expressao="volume * ajuste - volume * perda * margem_baixa",
                entradas={"volume": volume, "ajuste": ajuste, "perda": perda_volume, "margem_baixa": margem_baixa},
                resultado=ganho,
            ),
            premissas=[f"reajuste de {_pct(ajuste)} e perda de volume de {_pct(perda_volume)} são PREMISSAS"],
            confianca=0.4,
            custo_estimado=round(8 * self.cfg["custo_hora"], 2),
            risco="alto",
            acao_tipo="preco",
            proximos_passos=["Testar o novo preço em uma região ou canal", "Acompanhar volume semanal"],
            alvo_ids=sorted(p["produto_id"] for p in baixos),
        )
