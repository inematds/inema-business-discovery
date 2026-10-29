"""Estruturas de dados compartilhadas pelos agentes."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

FRENTES = {
    "receita_perdida": "Receita perdida",
    "despesas_evitaveis": "Despesas evitáveis",
    "risco_abandono": "Risco de abandono",
    "ineficiencia_operacional": "Ineficiências operacionais",
    "oportunidade_comercial": "Oportunidades comerciais",
}

# Estados de uma descoberta ao longo do LOOP-R
ESTADOS = (
    "localizada",            # Investigador encontrou
    "auditada",              # Auditor conferiu dados e contas
    "reprovada_auditoria",   # Auditor achou erro: não segue
    "aguardando_aprovacao",  # ação sensível: precisa de um humano
    "aprovada",              # humano aprovou o teste
    "rejeitada",             # humano recusou
    "em_teste",              # experimento rodando
    "validada",              # resultado incremental confirmado
    "descartada",            # teste não confirmou: volta, sem promover
)


@dataclass
class Calculo:
    """Conta reproduzível: fórmula em texto + entradas + resultado.

    O Auditor refaz a conta a partir de `entradas` usando `expressao` e compara.
    """

    formula: str
    expressao: str
    entradas: dict[str, float]
    resultado: float
    unidade: str = "R$"


@dataclass
class Descoberta:
    id: str
    frente: str
    titulo: str
    resumo: str
    evidencias: list[str]
    origem_dados: list[str]
    periodo: str
    hipotese: str
    calculo: Calculo
    premissas: list[str]
    confianca: float              # 0 a 1
    custo_estimado: float         # R$ para executar a intervenção
    risco: str                    # baixo | medio | alto
    acao_tipo: str                # tipo de ação, para o portão de aprovação
    proximos_passos: list[str]
    alvo_ids: list[str] = field(default_factory=list)  # clientes/itens envolvidos
    intervencoes: list[str] = field(default_factory=list)
    explicacoes_alternativas: list[str] = field(default_factory=list)
    riscos: list[str] = field(default_factory=list)
    auditoria: dict[str, Any] = field(default_factory=dict)
    plano_teste: dict[str, Any] = field(default_factory=dict)
    competicao: dict[str, Any] = field(default_factory=dict)
    requer_aprovacao: bool = False
    estado: str = "localizada"
    prioridade: float = 0.0
    narrativa: str = ""           # texto opcional do LLM local

    @property
    def impacto(self) -> float:
        return self.calculo.resultado

    @property
    def nivel_confianca(self) -> str:
        if self.confianca >= 0.7:
            return "alta"
        if self.confianca >= 0.45:
            return "média"
        return "baixa"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["impacto"] = self.impacto
        d["nivel_confianca"] = self.nivel_confianca
        d["frente_nome"] = FRENTES[self.frente]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Descoberta":
        d = dict(d)
        for k in ("impacto", "nivel_confianca", "frente_nome"):
            d.pop(k, None)
        d["calculo"] = Calculo(**d["calculo"])
        return cls(**d)
