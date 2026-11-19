"""Inversao salarial (novos x veteranos) e posicao na faixa. Le DADOS_TRATADOS, grava RESULTADOS/abaixo_do_piso.csv"""
import csv, statistics as st
from datetime import date
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodo import TRAT, RES, periodo
PER = periodo()
rd = lambda f: list(csv.DictReader(open(TRAT/f, encoding="utf-8"), delimiter=";"))
col, fx, des = rd("colaboradores.csv"), rd("faixas_salariais.csv"), {r["colaborador_id"]: r for r in rd("desligamentos.csv")}
F = {(r["cargo"], r["nivel"]): {k: float(r[k]) for k in ("faixa_min", "faixa_media", "faixa_max")} for r in fx}
REF = PER["ref"]   # ultimo dia do periodo
for r in col:
    r["adm"] = date.fromisoformat(r["data_admissao"]); r["sal"] = float(r["salario"])
    r["dl"] = date.fromisoformat(r["data_desligamento"]) if r["data_desligamento"] else None
    r["ativo"] = r["dl"] is None
    r["f"] = F[(r["cargo"], r["nivel"])]
    r["anos"] = ((r["dl"] or REF) - r["adm"]).days / 365.25
    r["abaixo"] = r["sal"] < r["f"]["faixa_min"]
    r["vol"] = r["ativo"] is False and des[r["colaborador_id"]]["tipo"] == "Voluntario"
    r["motivo"] = des[r["colaborador_id"]]["motivo"] if r["dl"] else ""
import json
TOP = json.load(open(RES/"turnover.json", encoding="utf-8"))["top_area"]
ativos = [r for r in col if r["ativo"]]
print("ATIVOS", len(ativos))
# --- inversao
print("\n== INVERSAO (ativos): <1,5 ano vs >4 anos, mesmo cargo/nivel")
g = defaultdict(lambda: ([], []))
for r in ativos:
    if r["anos"] < 1.5: g[(r["cargo"], r["nivel"])][0].append(r["sal"])
    elif r["anos"] > 4: g[(r["cargo"], r["nivel"])][1].append(r["sal"])
tn = tv = 0
for k, (n, v) in sorted(g.items(), key=lambda kv: F[kv[0]]["faixa_media"]):
    if n and v:
        mn, mv = st.median(n), st.median(v)
        print(f"{k[0]:13}{k[1]:7} novos n={len(n):3} med={mn:9.0f} | veteranos n={len(v):3} med={mv:9.0f} | dif={mn/mv-1:+.1%}  media dif={st.mean(n)/st.mean(v)-1:+.1%}  faixa_media={F[k]['faixa_media']:.0f}")
    tn += len(n); tv += len(v)
print("totais novos/vet", tn, tv)
# medida agregada: salario relativo a faixa_media
nov = [r["sal"]/r["f"]["faixa_media"] for r in ativos if r["anos"] < 1.5]
vet = [r["sal"]/r["f"]["faixa_media"] for r in ativos if r["anos"] > 4]
print(f"salario / faixa_media: novos {st.mean(nov):.3f} (n={len(nov)}) | veteranos {st.mean(vet):.3f} (n={len(vet)})")
for lo, hi in ((0,1.5),(1.5,2.5),(2.5,4),(4,7),(7,99)):
    x=[r["sal"]/r["f"]["faixa_media"] for r in ativos if lo<=r["anos"]<hi]; print(f" tempo {lo}-{hi}: n={len(x)} sal/faixa_media={st.mean(x):.3f}")
# --- abaixo do piso
ab = [r for r in ativos if r["abaixo"]]
print("\n== ABAIXO DO PISO (ativos):", len(ab), f"({len(ab)/len(ativos):.1%})")
from collections import Counter
print(Counter(r["area"] for r in ab).most_common()); print(Counter((r["cargo"],r["nivel"]) for r in ab).most_common())
gap=[(r["f"]["faixa_min"]-r["sal"]) for r in ab]; print("gap R$ mediana/media/max", st.median(gap), st.mean(gap), max(gap), "gap% medio", st.mean((r["f"]["faixa_min"]-r["sal"])/r["f"]["faixa_min"] for r in ab))
print("tempo de casa abaixo (mediana anos)", st.median(r["anos"] for r in ab), "vs nao abaixo ativos", st.median(r["anos"] for r in ativos if not r["abaixo"]))
print("custo p/ levar ao piso (R$/mes):", sum(gap))
print("por faixa de tempo:", Counter(("<1.5" if r["anos"]<1.5 else "1.5-4" if r["anos"]<4 else ">4") for r in ab), Counter(("<1.5" if r["anos"]<1.5 else "1.5-4" if r["anos"]<4 else ">4") for r in ativos))
with open(RES/"abaixo_do_piso.csv","w",encoding="utf-8",newline="") as f:
    w=csv.writer(f,delimiter=";",lineterminator="\n"); w.writerow(["colaborador_id","nome","area","cargo","nivel","gestor","admissao","anos_de_casa","salario","faixa_min","falta_para_piso","pct_abaixo"])
    for r in sorted(ab,key=lambda r:-(r["f"]["faixa_min"]-r["sal"])/r["f"]["faixa_min"]):
        w.writerow([r["colaborador_id"],r["nome"],r["area"],r["cargo"],r["nivel"],r["gestor"],r["data_admissao"],f'{r["anos"]:.1f}',f'{r["sal"]:.2f}',f'{r["f"]["faixa_min"]:.0f}',f'{r["f"]["faixa_min"]-r["sal"]:.2f}',f'{(r["f"]["faixa_min"]-r["sal"])/r["f"]["faixa_min"]:.3f}'])
# --- relacao com pedido de demissao (todas as pessoas, exposicao 2023-2025)
print("\n== RELACAO COM PEDIDO DE DEMISSAO (exposicao em pessoa-ano,", PER["ini"], "a", PER["fim"], ")")
J0 = date(int(PER["ini"][:4]), int(PER["ini"][5:]), 1)
def expo(r):
    a=max(r["adm"],J0); b=r["dl"] or REF; return max(0,(b-a).days)/365.25
def tabela(rows, rot):
    for lab, f in (("abaixo do piso", True), ("dentro/acima", False)):
        x=[r for r in rows if r["abaixo"]==f]; pa=sum(expo(r) for r in x); v=sum(r["vol"] for r in x); t=sum(r["dl"] is not None for r in x)
        print(f"{rot:14}{lab:15} pessoas={len(x):4} pessoa-ano={pa:7.1f} saidas={t:3} vol={v:3} taxa_vol_anual={v/pa:.1%} taxa_total={t/pa:.1%}")
tabela(col,"TODOS"); tabela([r for r in col if r["area"]==TOP],TOP); tabela([r for r in col if r["area"]!=TOP],"Demais areas")
# motivos Salario
for lab,f in (("abaixo",True),("dentro",False)):
    x=[r for r in col if r["abaixo"]==f and r["dl"]]; m=Counter(r["motivo"] for r in x)
    print(lab,"saidas",len(x),"motivo Salario",m["Salário"], f'{m["Salário"]/len(x):.0%}', "| Proposta outra empresa", m["Proposta de outra empresa"])
# quantas pessoas ja estavam abaixo e sairam
print("pessoas desligadas abaixo do piso (salario final):",sum(1 for r in col if r["dl"] and r["abaixo"]),"de",sum(1 for r in col if r["dl"]))
# risco estratificado por cargo/nivel
print("\nRisco por cargo/nivel (taxa vol anual abaixo vs dentro):")
for k in sorted({(r["cargo"],r["nivel"]) for r in col}, key=lambda k:F[k]["faixa_media"]):
    out=[]
    for f in (True,False):
        x=[r for r in col if (r["cargo"],r["nivel"])==k and r["abaixo"]==f]; pa=sum(expo(r) for r in x)
        out.append((len(x), sum(r["vol"] for r in x)/pa if pa else 0))
    print(f"{k[0]:13}{k[1]:7} abaixo n={out[0][0]:3} {out[0][1]:.1%} | dentro n={out[1][0]:3} {out[1][1]:.1%}")
