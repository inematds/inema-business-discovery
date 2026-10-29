"""Linha de comando: python3 -m bd <comando>

  demo                         empresa fictícia → ciclo completo (análise, aprovação, teste simulado, validação)
  exemplo PASTA                gera os CSVs fictícios em PASTA
  analisar --dados D --saida S roda o ciclo LOOP-R sobre os seus CSVs
  listar --saida S             mostra as descobertas e o estado de cada uma
  aprovar ID --por NOME        portão humano: libera o teste
  rejeitar ID --por NOME
  validar ID --resultados CSV  compara previsto × medido (teste vs controle) e atualiza a memória
  memoria --saida S            métricas, lições e trilha de decisões
  servir --saida S             painel local em http://127.0.0.1:8765 com botões de aprovar
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .ciclo import analisar, exportar
from .config import carregar as carregar_cfg
from .governanca import aprovar, rejeitar
from .memoria import Memoria
from .relatorio import brl
from .validador import validar


def _mem(saida) -> Memoria:
    p = Path(saida) / "memoria.sqlite"
    if not p.exists():
        sys.exit(f"sem memória em {saida}: rode `analisar` antes")
    return Memoria(p)


def cmd_demo(a):
    from .exemplo import gerar, simular_resultados

    dados = Path(a.dados)
    if not (dados / "vendas.csv").exists():
        gerar(dados)
    saida = Path(a.saida)
    if (saida / "memoria.sqlite").exists():
        (saida / "memoria.sqlite").unlink()
    print("== INEMA Business Discovery — DEMONSTRAÇÃO com empresa FICTÍCIA ==\n")
    cfg = carregar_cfg(dados)
    analisar(dados, saida, cfg, usar_llm=a.llm)
    mem = Memoria(saida / "memoria.sqlite")
    d = mem.obter("RP-REATIVACAO")
    e = d.calculo.entradas
    print("\nExemplo do documento (recuperação de clientes):")
    print(f"  {e['clientes']:.0f} clientes × {e['conversao']:.0%} × {brl(e['ticket'])} = receita potencial "
          f"{brl(e['clientes'] * e['conversao'] * e['ticket'])}")
    print(f"  × margem {e['margem']:.0%} = contribuição potencial {brl(d.impacto)}")
    print(f"  Competição: {d.competicao['vencedora']} venceu a avaliação às cegas")
    print(f"\nPortão humano: {d.id} está '{d.estado}'. Na demo, o 'Gestor (demo)' aprova o teste.")
    aprovar(mem, d.id, "Gestor (demo)", "aprovado na demonstração")
    res = simular_resultados(saida / "planos" / f"{d.id}-grupos.csv", saida / "resultados-SIMULADOS.csv")
    print(f"Teste SIMULADO (não é dado real) gravado em {res}")
    r = validar(mem, d.id, res, cfg, autor="Validador")
    print(f"\nValidador: conversão teste {r['conversao_teste']:.0%} × controle {r['conversao_controle']:.0%}, "
          f"p = {r['p_valor']}")
    print(f"  contribuição incremental {brl(r['contribuicao_incremental'])} "
          f"(previsto p/ o grupo {brl(r['previsto_para_o_grupo'])}, precisão {r['precisao']:.0%})")
    print(f"  {r['licao']}")
    exportar(mem, saida, cfg)
    print(f"\nMétricas: {json.dumps(mem.metricas(), ensure_ascii=False)}")
    mem.fechar()
    print(f"\nRelatório: {saida / 'relatorio.html'}\nPainel:    python3 -m bd servir --saida {saida}")


def cmd_analisar(a):
    analisar(a.dados, a.saida, carregar_cfg(a.dados, a.config), usar_llm=a.llm)
    print(f"\nRelatório: {Path(a.saida) / 'relatorio.html'}")


def cmd_listar(a):
    mem = _mem(a.saida)
    for d in mem.listar():
        print(f"{d.id:<16} {d.estado:<22} {brl(d.impacto):>16}  conf {d.confianca:.2f}  {d.titulo}")
    mem.fechar()


def _decidir(a, fn):
    mem = _mem(a.saida)
    d = fn(mem, a.id, a.por, a.nota or "")
    exportar(mem, Path(a.saida), carregar_cfg(a.dados) if a.dados else carregar_cfg())
    mem.fechar()
    print(f"{d.id}: {d.estado} (por {a.por})")


def cmd_validar(a):
    mem = _mem(a.saida)
    cfg = carregar_cfg(a.dados) if a.dados else carregar_cfg()
    r = validar(mem, a.id, a.resultados, cfg, autor=a.por)
    exportar(mem, Path(a.saida), cfg)
    mem.fechar()
    print(json.dumps(r, ensure_ascii=False, indent=1))


def cmd_memoria(a):
    mem = _mem(a.saida)
    print(json.dumps({"metricas": mem.metricas(), "licoes": mem.licoes(), "trilha": mem.eventos()},
                     ensure_ascii=False, indent=1, default=str))
    mem.fechar()


def cmd_servir(a):
    from .servidor import servir

    servir(a.saida, carregar_cfg(a.dados) if a.dados else carregar_cfg(), a.porta)


def cmd_exemplo(a):
    from .exemplo import gerar

    print(f"dados fictícios em {gerar(a.pasta)}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bd", description="INEMA Business Discovery " + __version__)
    p.add_argument("--version", action="version", version=__version__)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("demo")
    x.add_argument("--dados", default="exemplos/empresa-ficticia")
    x.add_argument("--saida", default="saida-demo")
    x.add_argument("--llm", action="store_true", help="narrativa pelo provedor do config (padrão: nenhum)")
    x.set_defaults(f=cmd_demo)
    x = s.add_parser("exemplo")
    x.add_argument("pasta")
    x.set_defaults(f=cmd_exemplo)
    x = s.add_parser("analisar")
    x.add_argument("--dados", required=True)
    x.add_argument("--saida", required=True)
    x.add_argument("--config")
    x.add_argument("--llm", action="store_true")
    x.set_defaults(f=cmd_analisar)
    for nome, fn in (("aprovar", aprovar), ("rejeitar", rejeitar)):
        x = s.add_parser(nome)
        x.add_argument("id")
        x.add_argument("--por", required=True, help="nome de quem decide (fica na trilha)")
        x.add_argument("--nota")
        x.add_argument("--saida", default="saida")
        x.add_argument("--dados")
        x.set_defaults(f=lambda a, fn=fn: _decidir(a, fn))
    x = s.add_parser("validar")
    x.add_argument("id")
    x.add_argument("--resultados", required=True)
    x.add_argument("--por", default="Validador")
    x.add_argument("--saida", default="saida")
    x.add_argument("--dados")
    x.set_defaults(f=cmd_validar)
    for nome, fn in (("listar", cmd_listar), ("memoria", cmd_memoria)):
        x = s.add_parser(nome)
        x.add_argument("--saida", default="saida")
        x.set_defaults(f=fn)
    x = s.add_parser("servir")
    x.add_argument("--saida", default="saida")
    x.add_argument("--dados")
    x.add_argument("--porta", type=int, default=8765)
    x.set_defaults(f=cmd_servir)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
