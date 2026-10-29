"""Relatório HTML (abre direto no navegador; com `bd servir` ganha botões de aprovação)."""
from __future__ import annotations

import html
import json

from .modelos import FRENTES

E = lambda s: html.escape(str(s))  # noqa: E731

ESTADO_ROTULO = {
    "localizada": "Localizada", "auditada": "Auditada", "reprovada_auditoria": "Reprovada na auditoria",
    "aguardando_aprovacao": "Aguarda aprovação humana", "aprovada": "Aprovada para teste",
    "rejeitada": "Rejeitada pelo gestor", "em_teste": "Em teste", "validada": "Validada (promovida)",
    "descartada": "Descartada pelo teste",
}


def brl(v) -> str:
    try:
        s = f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"
    return f"R$ {s}"


def _barras(descobertas) -> str:
    por = {k: 0.0 for k in FRENTES}
    for d in descobertas:
        if d["estado"] != "reprovada_auditoria":
            por[d["frente"]] += max(d["impacto"], 0)
    mx = max(por.values()) or 1
    linhas = []
    for i, (k, v) in enumerate(por.items()):
        y = 8 + i * 46
        w = 4 + 560 * v / mx
        linhas.append(
            f'<text x="0" y="{y + 15}" class="lb">{E(FRENTES[k])}</text>'
            f'<rect x="0" y="{y + 22}" width="{w:.0f}" height="14" rx="4" class="bar"/>'
            f'<text x="{w + 8:.0f}" y="{y + 34}" class="vl">{E(brl(v))}</text>')
    return (f'<svg viewBox="0 0 760 {8 + 46 * len(por)}" role="img" aria-label="Impacto estimado por frente">'
            + "".join(linhas) + "</svg>")


def _card(d) -> str:
    aud = d.get("auditoria") or {}
    comp = d.get("competicao") or {}
    pt = d.get("plano_teste") or {}
    est = d["estado"]
    li = lambda xs: "".join(f"<li>{E(x)}</li>" for x in xs)  # noqa: E731
    cegas = "".join(
        f"<tr><td>{E(c['rotulo'])}</td><td>{E(brl(c['liquido']))}</td><td>{E(c['risco'])}</td>"
        f"<td>{E(brl(c['nota']))}</td><td>{E(comp['revelacao'][c['rotulo']])}</td></tr>"
        for c in comp.get("avaliacao_cega", []))
    teste = ""
    if pt.get("grupo_teste"):
        teste = (f"<p><b>{E(pt['tipo'])}</b>: {len(pt['grupo_teste'])} no teste, {len(pt['grupo_controle'])} no "
                 f"controle. Métrica: {E(pt['metrica'])}. Amostra necessária por grupo: "
                 f"{E(pt['amostra_necessaria_por_grupo'])}.</p>")
        if pt.get("aviso"):
            teste += f'<p class="warn">Aviso: {E(pt["aviso"])}</p>'
    else:
        teste = f"<p><b>{E(pt.get('tipo', ''))}</b>. Métrica: {E(pt.get('metrica', ''))}</p>"
    cen = pt.get("cenarios", {})
    botoes = ""
    if est == "aguardando_aprovacao":
        botoes = (f'<div class="gate"><span>Ação do tipo <b>{E(d["acao_tipo"])}</b>: só anda com aprovação.</span>'
                  f'<button class="ok" data-acao="aprovar" data-id="{E(d["id"])}">Aprovar teste</button>'
                  f'<button class="no" data-acao="rejeitar" data-id="{E(d["id"])}">Rejeitar</button>'
                  f'<code class="cli">python3 -m bd aprovar {E(d["id"])} --por "seu nome"</code></div>')
    narr = f'<p class="narr"><b>Cientista (modelo local):</b> {E(d["narrativa"])}</p>' if d.get("narrativa") else ""
    falhas = li(aud.get("falhas", [])) or "<li>conta refeita e conferida</li>"
    return f"""
<article class="card" id="{E(d['id'])}">
  <div class="top"><span class="chip">{E(d['frente_nome'])}</span><span class="st st-{E(est)}">{E(ESTADO_ROTULO.get(est, est))}</span>
  <span class="id">{E(d['id'])}</span></div>
  <h3>{E(d['titulo'])}</h3>
  <p>{E(d['resumo'])}</p>
  <div class="nums">
    <div><small>Impacto estimado</small><b>{E(brl(d['impacto']))}</b></div>
    <div><small>Confiança</small><b>{E(d['nivel_confianca'])} ({d['confianca']:.2f})</b></div>
    <div><small>Custo</small><b>{E(brl(d['custo_estimado']))}</b></div>
    <div><small>Risco</small><b>{E(d['risco'])}</b></div>
    <div><small>Prioridade</small><b>{E(brl(d['prioridade']))}</b></div>
  </div>
  {narr}
  <details><summary>Evidências, conta e premissas</summary>
    <ul>{li(d['evidencias'])}</ul>
    <p class="formula">{E(d['calculo']['formula'])}<br><code>{E(d['calculo']['expressao'])}</code> com
    <code>{E(json.dumps(d['calculo']['entradas'], ensure_ascii=False))}</code> = <b>{E(brl(d['calculo']['resultado']))}</b></p>
    <ul class="prem">{li(d['premissas'])}</ul>
    <p class="meta">Dados: {E(', '.join(d['origem_dados']))} · período {E(d['periodo'])}</p>
  </details>
  <details><summary>Auditor e Crítico</summary>
    <p><b>Auditor</b> refez a conta: {E(brl(aud.get('conta_refeita')))}</p><ul>{falhas}{li(aud.get('avisos', []))}</ul>
    <p><b>Crítico</b> — riscos:</p><ul>{li(d['riscos']) or '<li>nenhum sinal quantitativo</li>'}</ul>
    <p>Explicações alternativas a descartar:</p><ul>{li(d['explicacoes_alternativas'])}</ul>
  </details>
  <details><summary>Agentes competindo: {E(comp.get('vencedora', ''))} venceu</summary>
    <p class="meta">Avaliação às cegas — {E(comp.get('criterio', ''))}. A autoria só aparece depois da nota.</p>
    <table><tr><th>Proposta</th><th>Líquido</th><th>Risco</th><th>Nota</th><th>Autor revelado</th></tr>{cegas}</table>
  </details>
  <details><summary>Experimentador: cenários e teste</summary>
    <p>Pessimista {E(brl(cen.get('pessimista')))} · base {E(brl(cen.get('base')))} · otimista {E(brl(cen.get('otimista')))}</p>
    {teste}<ul>{li(d['proximos_passos'])}</ul>
  </details>
  {botoes}
</article>"""


def gerar_html(dados: dict) -> str:
    ds = dados["descobertas"]
    m = dados["metricas"]
    total = sum(d["impacto"] for d in ds if d["estado"] != "reprovada_auditoria")
    licoes = "".join(
        f"<tr><td>{E(x['descoberta_id'])}</td><td>{E(x['estrategia'])}</td><td>{E(brl(x['estimado']))}</td>"
        f"<td>{E(brl(x['observado']))}</td><td>{E(x['p_valor'])}</td><td>{'sim' if x['promovida'] else 'não'}</td></tr>"
        for x in dados.get("licoes", [])) or '<tr><td colspan="6">Nenhum teste validado ainda.</td></tr>'
    eventos = "".join(f"<li><code>{E(e['quando'])}</code> {E(e['descoberta_id'])} — {E(e['tipo'])} por {E(e['autor'])}"
                      f"{(': ' + E(e['detalhe'])) if e['detalhe'] and e['tipo'] != 'analise' else ''}</li>"
                      for e in dados.get("eventos", []) if e["tipo"] != "analise")
    prec = m.get("precisao_media_hipoteses")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Business Discovery — relatório</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0c0c10;--bg2:#14141b;--card:#16161e;--line:#272730;--txt:#e9e9ee;--mut:#9a9aa6;--amb:#FACC15;--ok:#4ade80;--bad:#f87171}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:16px/1.6 Inter,system-ui,sans-serif}}
main{{max-width:1160px;margin:0 auto;padding:32px 16px 80px}}h1,h2,h3{{font-family:Sora,Inter,sans-serif;line-height:1.25}}
h1{{font-size:2rem;margin:.2em 0}}h1 span{{color:var(--amb)}}h2{{margin-top:2.4em;font-size:1.35rem}}
.aviso{{border:1px solid var(--line);border-left:4px solid var(--amb);background:var(--bg2);padding:12px 16px;border-radius:10px;color:var(--mut)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}}
.kpis div,.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}}
.kpis small,.nums small{{display:block;color:var(--mut);font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}}
.kpis b{{font-size:1.4rem;font-family:Sora}}svg{{width:100%;height:auto}}.lb{{fill:var(--txt);font-size:14px}}
.vl{{fill:var(--mut);font-size:13px}}.bar{{fill:var(--amb)}}.card{{margin:16px 0}}.top{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.chip{{border:1px solid var(--amb);color:var(--amb);border-radius:999px;padding:2px 10px;font-size:.75rem;text-transform:uppercase;letter-spacing:.06em}}
.st{{font-size:.85rem;color:var(--mut)}}.st-validada{{color:var(--ok)}}.st-validada::before{{content:"✓ "}}
.st-reprovada_auditoria,.st-descartada,.st-rejeitada{{color:var(--bad)}}.st-reprovada_auditoria::before,.st-descartada::before{{content:"✕ "}}
.st-aguardando_aprovacao{{color:var(--amb)}}.st-aguardando_aprovacao::before{{content:"⏸ "}}
.id{{margin-left:auto;font:12px JetBrains Mono,monospace;color:var(--mut)}}
.nums{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:12px 0}}
details{{border-top:1px solid var(--line);padding:8px 0}}summary{{cursor:pointer;font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:.92rem}}td,th{{border-bottom:1px solid var(--line);padding:6px;text-align:left}}
.overflow{{overflow-x:auto}}code{{font-family:JetBrains Mono,monospace;font-size:.85em;color:var(--amb)}}
.formula{{background:var(--bg2);padding:10px;border-radius:12px}}.meta,.prem{{color:var(--mut);font-size:.9rem}}
.warn{{color:var(--amb)}}.narr{{border-left:3px solid var(--line);padding-left:12px;color:var(--mut)}}
.gate{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:10px;padding:12px;border:1px dashed var(--amb);border-radius:10px}}
.gate button{{border:0;border-radius:10px;padding:8px 14px;font-weight:600;cursor:pointer;display:none}}
.ok{{background:var(--amb);color:#1a1206}}.no{{background:var(--line);color:var(--txt)}}.servido .gate button{{display:inline-block}}
.servido .cli{{display:none}}
</style></head><body><main>
<p class="chip">INEMA Business Discovery · v{E(dados['versao'])}</p>
<h1>Descobertas da semana: <span>{len(ds)}</span> oportunidades auditadas</h1>
<p class="aviso">{E(dados['aviso'])} Período dos dados: {E(dados.get('periodo') or '—')}.</p>
<div class="kpis">
 <div><small>Impacto estimado total</small><b>{E(brl(total))}</b></div>
 <div><small>Aguardando aprovação</small><b>{sum(d['estado'] == 'aguardando_aprovacao' for d in ds)}</b></div>
 <div><small>Oportunidades validadas</small><b>{m['oportunidades_validadas']}</b></div>
 <div><small>Impacto incremental medido</small><b>{E(brl(m['impacto_incremental']))}</b></div>
 <div><small>Precisão das hipóteses</small><b>{E(f"{prec:.0%}" if prec is not None else "—")}</b></div>
</div>
<h2>Impacto estimado por frente</h2>{_barras(ds)}
<h2>Descobertas por prioridade</h2>
{''.join(_card(d) for d in ds)}
<h2>Memória: o que os testes ensinaram</h2>
<div class="overflow"><table><tr><th>Descoberta</th><th>Estratégia</th><th>Previsto</th><th>Medido (incremental)</th><th>p</th><th>Promovida</th></tr>{licoes}</table></div>
<h2>Trilha de decisões</h2><ul>{eventos or '<li>Nenhuma decisão humana registrada.</li>'}</ul>
</main>
<script>
fetch('/api/ping').then(r=>{{if(r.ok)document.body.classList.add('servido')}}).catch(()=>{{}});
document.addEventListener('click',async e=>{{const b=e.target.closest('button[data-acao]');if(!b)return;
const por=prompt('Seu nome (fica registrado na trilha):');if(!por)return;
const r=await fetch('/api/'+b.dataset.acao,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:b.dataset.id,por}})}});
if(r.ok)location.reload();else alert(await r.text());}});
</script></body></html>"""
