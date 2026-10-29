import json
import re
from pathlib import Path

import pytest

from bd.auditor import Auditor, avaliar
from bd.ciclo import analisar
from bd.config import carregar as cfg_de
from bd.dados import ErroDados, carregar
from bd.exemplo import gerar, simular_resultados
from bd.governanca import aprovar, rejeitar
from bd.investigador import Investigador
from bd.llm import narrar
from bd.memoria import Memoria
from bd.modelos import Calculo, Descoberta
from bd.validador import ErroGovernanca, validar

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def empresa(tmp_path_factory):
    return gerar(tmp_path_factory.mktemp("dados"))


@pytest.fixture()
def rodada(empresa, tmp_path):
    analisar(empresa, tmp_path, cfg_de(empresa), log=lambda *_: None)
    return tmp_path


def _mem(saida):
    return Memoria(Path(saida) / "memoria.sqlite")


# ---------- dados ----------
def test_le_csv_brasileiro(tmp_path):
    (tmp_path / "vendas.csv").write_text(
        "venda_id;data;cliente_id;produto_id;valor\nV1;05/03/2026;C1;P1;1.234,56\n", encoding="utf-8")
    b = carregar(tmp_path)
    assert b["vendas"][0]["valor"] == 1234.56
    assert b["vendas"][0]["data"].isoformat() == "2026-03-05"


def test_vendas_obrigatorio(tmp_path):
    with pytest.raises(ErroDados):
        carregar(tmp_path)


def test_coluna_faltando(tmp_path):
    (tmp_path / "vendas.csv").write_text("venda_id,data\nV1,2026-01-01\n", encoding="utf-8")
    with pytest.raises(ErroDados, match="faltam colunas"):
        carregar(tmp_path)


# ---------- números do documento ----------
def test_exemplo_do_documento(empresa):
    inv = Investigador(carregar(empresa), cfg_de(empresa))
    d = inv.reativacao()
    e = d.calculo.entradas
    assert e["clientes"] == 120
    assert e["ticket"] == 3500
    assert e["conversao"] == 0.20 and e["margem"] == 0.30
    assert e["clientes"] * e["conversao"] * e["ticket"] == pytest.approx(84000)
    assert d.impacto == pytest.approx(25200)
    assert "40 eram de alta frequência" in d.titulo


def test_cinco_frentes(rodada):
    dados = json.loads((rodada / "descobertas.json").read_text())
    frentes = {d["frente"] for d in dados["descobertas"]}
    assert frentes == {"receita_perdida", "despesas_evitaveis", "risco_abandono",
                       "ineficiencia_operacional", "oportunidade_comercial"}


def test_margem_calculada_sem_config(empresa, tmp_path):
    cfg = cfg_de(None)
    inv = Investigador(carregar(empresa), cfg)
    assert "produtos.csv" in inv.margem_origem
    assert 0 < inv.margem < 1


# ---------- auditor ----------
def test_auditor_refaz_e_aprova(rodada):
    m = _mem(rodada)
    assert all(d.auditoria["aprovada"] for d in m.listar())


def test_auditor_pega_conta_errada(empresa):
    d = Investigador(carregar(empresa), cfg_de(empresa)).reativacao()
    d.calculo.resultado += 1000
    Auditor(carregar(empresa)).auditar(d)
    assert d.estado == "reprovada_auditoria"
    assert "conta não fecha" in d.auditoria["falhas"][0]


def test_auditor_pega_alvo_inexistente(empresa):
    d = Investigador(carregar(empresa), cfg_de(empresa)).reativacao()
    d.alvo_ids.append("C9999")
    Auditor(carregar(empresa)).auditar(d)
    assert any("não existem" in f for f in d.auditoria["falhas"])


def test_expressao_insegura_bloqueada():
    with pytest.raises(ValueError):
        avaliar("__import__('os').system('true')", {})
    assert avaliar("a * b - c / 2", {"a": 2, "b": 3, "c": 4}) == 4


# ---------- cientista: competição às cegas ----------
def test_avaliacao_cega_sem_autoria(rodada):
    d = _mem(rodada).obter("RP-REATIVACAO")
    cegas = json.dumps(d.competicao["avaliacao_cega"], ensure_ascii=False)
    assert "Agente" not in cegas and "Recuperação" not in cegas
    assert len(d.competicao["propostas"]) == 3
    assert d.competicao["vencedora"] in d.competicao["revelacao"].values()


# ---------- experimentador ----------
def test_grupos_disjuntos_e_completos(rodada):
    d = _mem(rodada).obter("RP-REATIVACAO")
    t, c = set(d.plano_teste["grupo_teste"]), set(d.plano_teste["grupo_controle"])
    assert not t & c and t | c == set(d.alvo_ids)
    assert (rodada / "planos" / "RP-REATIVACAO-grupos.csv").exists()


# ---------- crítico ----------
def test_critico_baixa_confianca_amostra_pequena(rodada):
    d = _mem(rodada).obter("RP-PROPOSTAS")
    assert any("amostra pequena" in r for r in d.riscos)
    assert d.confianca < 0.55


# ---------- governança ----------
def test_nao_valida_sem_aprovacao(rodada, tmp_path):
    m = _mem(rodada)
    res = simular_resultados(rodada / "planos" / "RP-REATIVACAO-grupos.csv", tmp_path / "r.csv")
    with pytest.raises(ErroGovernanca):
        validar(m, "RP-REATIVACAO", res, cfg_de(None))


def test_agente_nao_aprova(rodada):
    m = _mem(rodada)
    for nome in ("", "agente", "ciclo"):
        with pytest.raises(ErroGovernanca):
            aprovar(m, "RP-REATIVACAO", nome)


def test_trilha_registra_quem_aprovou(rodada):
    m = _mem(rodada)
    aprovar(m, "RP-REATIVACAO", "Maria Gestora")
    ev = [e for e in m.eventos("RP-REATIVACAO") if "aprovada" in e["tipo"]]
    assert ev and ev[0]["autor"] == "Maria Gestora"


def test_decisao_humana_sobrevive_nova_analise(empresa, rodada):
    m = _mem(rodada)
    rejeitar(m, "DE-SOBREPOSICAO", "João")
    m.fechar()
    analisar(empresa, rodada, cfg_de(empresa), log=lambda *_: None)
    assert _mem(rodada).obter("DE-SOBREPOSICAO").estado == "rejeitada"


# ---------- validador + memória ----------
def test_validacao_promove_e_reforca(empresa, rodada, tmp_path):
    m = _mem(rodada)
    aprovar(m, "RP-REATIVACAO", "Maria")
    res = simular_resultados(rodada / "planos" / "RP-REATIVACAO-grupos.csv", tmp_path / "r.csv")
    r = validar(m, "RP-REATIVACAO", res, cfg_de(empresa))
    assert r["promovida"] and r["p_valor"] < 0.05
    assert r["contribuicao_incremental"] == pytest.approx(9000)
    assert m.metricas()["oportunidades_validadas"] == 1
    vencedora = m.obter("RP-REATIVACAO").competicao["vencedora"].split("—")[-1].strip()
    assert vencedora in m.estrategias_validadas("receita_perdida")
    m.fechar()
    # próximo ciclo: a estratégia validada ganha bônus na competição
    analisar(empresa, rodada, cfg_de(empresa), log=lambda *_: None)
    d = _mem(rodada).obter("RP-PROPOSTAS")  # mesma frente
    assert any(c["bonus"] for c in d.competicao["avaliacao_cega"])


def test_sem_efeito_descarta(empresa, rodada, tmp_path):
    m = _mem(rodada)
    aprovar(m, "RP-REATIVACAO", "Maria")
    res = simular_resultados(rodada / "planos" / "RP-REATIVACAO-grupos.csv", tmp_path / "r.csv",
                             conv_teste=0.05, conv_controle=0.05)
    r = validar(m, "RP-REATIVACAO", res, cfg_de(empresa))
    assert not r["promovida"]
    assert m.obter("RP-REATIVACAO").estado == "descartada"
    assert m.estrategias_validadas("receita_perdida") == set()


# ---------- relatório, LLM e limites ----------
def test_relatorio_escapa_html(empresa, tmp_path):
    from bd.relatorio import gerar_html
    d = Investigador(carregar(empresa), cfg_de(empresa)).reativacao()
    d.titulo = "<script>alert(1)</script>"
    html = gerar_html({"versao": "x", "descobertas": [d.to_dict()], "metricas": {
        "oportunidades_validadas": 0, "impacto_incremental": 0, "precisao_media_hipoteses": None},
        "aviso": "a"})
    assert "<script>alert(1)" not in html


def test_llm_padrao_nao_chama_nada():
    d = Descoberta(id="X", frente="receita_perdida", titulo="t", resumo="r", evidencias=["e"],
                   origem_dados=["vendas.csv"], periodo="p", hipotese="h",
                   calculo=Calculo("f", "a", {"a": 1}, 1), premissas=[], confianca=0.5,
                   custo_estimado=0, risco="baixo", acao_tipo="contato_comercial", proximos_passos=[])
    assert narrar(d, cfg_de(None)) == ""


def test_nenhuma_chave_de_api_no_codigo():
    fonte = "".join(p.read_text() for p in (RAIZ / "bd").glob("*.py"))
    assert not re.search(r"API_KEY|api\.anthropic|api\.openai|openrouter", fonte, re.I)


def test_config_aceita_comentarios(tmp_path):
    (tmp_path / "config.json").write_text(
        '{\n  "margem_contribuicao": 0.25,   # minha margem\n  "custo_hora": 50,  # R$ por hora\n'
        '  "llm": {"provedor": "nenhum"}  # sem modelo\n}\n', encoding="utf-8")
    c = cfg_de(tmp_path)
    assert c["margem_contribuicao"] == 0.25 and c["custo_hora"] == 50
    assert "margem_contribuicao" in c["_informado"]


def test_config_invalido_mensagem_clara(tmp_path):
    (tmp_path / "config.json").write_text('{"margem_contribuicao": 0.3,}', encoding="utf-8")
    with pytest.raises(SystemExit, match="config.json inválido"):
        cfg_de(tmp_path)
