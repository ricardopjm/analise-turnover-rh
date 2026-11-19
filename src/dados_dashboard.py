"""Calcula tudo que o dashboard mostra e grava RESULTADOS/dashboard_dados.json (dados reais de DADOS_TRATADOS)."""
import sys, json, csv, statistics as st
from datetime import date, timedelta
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parent))
import turnover as tv                       # reaproveita funcoes de headcount (turnover.json ja foi gerado pelo passo anterior)
from base_analitica import painel, taxa
from periodo import TRAT, RES, periodo
PER = periodo(); REF = PER["ref"]; ANOS = PER["anos"]
rd = lambda f: list(csv.DictReader(open(TRAT/f, encoding="utf-8"), delimiter=";"))
P, rows = painel(); T = json.load(open(RES/"turnover.json", encoding="utf-8")); TOP = T["top_area"]
col = tv.col
out = dict(periodo=dict(ini=PER["ini"], fim=PER["fim"], ref=REF.isoformat(), n=PER["n"], anos=ANOS), top_area=TOP)
# ---- KPIs
ativos = [r for r in col if r["dl"] is None]
tot = T["total"]["resumo"]; per = tot["periodo"]
out["kpi"] = dict(headcount=len(ativos), hc_inicio=T["total"]["serie"][0]["hc_ini"], taxa=per["taxa_anual"], taxa_vol=per["taxa_vol_anual"], taxa_inv=per["taxa_inv_anual"],
    saidas=per["tot"], vol=per["vol"], inv=per["inv"], anos={str(a): dict(taxa=tot[str(a)]["taxa"], taxa_vol=tot[str(a)]["taxa_vol"], tot=tot[str(a)]["tot"], meses=tot[str(a)]["meses"]) for a in ANOS},
    tend=(lambda S: dict(ult12=sum(i["vol"]+i["inv"] for i in S[-12:])/(sum(i["hc_med"] for i in S[-12:])/12), ant12=sum(i["vol"]+i["inv"] for i in S[-24:-12])/(sum(i["hc_med"] for i in S[-24:-12])/12)) if len(S) >= 24 else None)(T["total"]["serie"]),
    custo=sum(3*r["sal"] for r in [dict(sal=float(x["salario"]), dl=x["dl"]) for x in col] if r["dl"]),
    custo_ano={str(a): sum(3*float(x["salario"]) for x in col if x["dl"] and x["dl"].year == a) for a in ANOS})
# ---- serie mensal
out["serie"] = T["total"]["serie"]
# ---- area x periodo
def pr(res, k):
    if k == "periodo": p = res["periodo"]; return dict(hc=p["hc_medio"], tot=p["tot"], vol=p["vol"], inv=p["inv"], taxa=p["taxa_anual"], av=p["taxa_vol_anual"], ai=p["taxa_inv_anual"])
    p = res[k]; return dict(hc=p["hc_medio"], tot=p["tot"], vol=p["vol"], inv=p["inv"], taxa=p["taxa"], av=p["taxa_vol"], ai=p["taxa_inv"])
out["area"] = [dict(nome=k, **{pk: pr(v["resumo"], pk) for pk in ["periodo"] + [str(a) for a in ANOS]}) for k, v in T["area"].items()]
out["area"].sort(key=lambda a: -a["periodo"]["taxa"])
# ---- modalidade x grupo
grp = {"Todas as áreas": col, TOP: [r for r in col if r["area"] == TOP], "Demais áreas": [r for r in col if r["area"] != TOP]}
out["modal"] = {g: [dict(nome=m, **pr(tv.resumo([r for r in rs if r["modalidade"] == m]), "periodo")) for m in ("Presencial", "Hibrido", "Remoto")] for g, rs in grp.items()}
# ---- gestores
G = defaultdict(list)
for r in rows: G[r["gestor"]].append(r)
atv = defaultdict(int)
for r in ativos: atv[r["gestor"]] += 1
out["gestores"] = [dict(nome=g, area=rs[0]["area"], py=len(rs)/12, vol=sum(r["vol"] for r in rs), inv=sum(r["inv"] for r in rs), ativos=atv[g]) for g, rs in G.items() if g != "Nao informado"]
# ---- salarios x faixas (somente ativos)
fx = rd("faixas_salariais.csv"); out["faixas"] = []
for f in sorted(fx, key=lambda f: float(f["faixa_media"])):
    mn, md, mx = float(f["faixa_min"]), float(f["faixa_media"]), float(f["faixa_max"])
    pes = [dict(s=float(r["salario"]), a=round(((REF - r["adm"]).days)/365.25, 1)) for r in ativos if r["cargo"] == f["cargo"] and r["nivel"] == f["nivel"]]
    out["faixas"].append(dict(cargo=f["cargo"], nivel=f["nivel"], mn=mn, md=md, mx=mx, pessoas=pes))
# ---- eNPS
pes = rd("pesquisa_clima.csv"); dl = {r["colaborador_id"]: r["dl"] for r in col}; tipo = {r["colaborador_id"]: r["tipo"] for r in col}
des = {r["colaborador_id"]: r["tipo"] for r in rd("desligamentos.csv")}
rod = defaultdict(lambda: [0, 0, 0])
seg = {"Detrator": [0, 0, 0], "Neutro": [0, 0, 0], "Promotor": [0, 0, 0]}   # n, saiu total, saiu voluntario
for r in pes:
    e = int(r["enps"]); g = "Detrator" if e <= 6 else "Neutro" if e <= 8 else "Promotor"
    rod[r["data_pesquisa"]][("Detrator", "Neutro", "Promotor").index(g)] += 1
    d = date.fromisoformat(r["data_pesquisa"])
    if d + timedelta(days=183) <= REF:      # so respostas com 6 meses completos de acompanhamento
        s = seg[g]; s[0] += 1; x = dl[r["colaborador_id"]]
        if x and d < x <= d + timedelta(days=183):
            s[1] += 1; s[2] += des[r["colaborador_id"]] == "Voluntario"
out["enps_rodadas"] = [dict(data=k, det=v[0], neu=v[1], pro=v[2], n=sum(v), enps=(v[2]-v[0])/sum(v)*100) for k, v in sorted(rod.items())]
out["enps_seg"] = [dict(nome=k, n=v[0], saiu=v[1], vol=v[2]) for k, v in seg.items()]
usadas = [k for k in sorted(rod) if date.fromisoformat(k) + timedelta(days=183) <= REF]
out["enps_janela"] = dict(ini=usadas[0] if usadas else None, fim=usadas[-1] if usadas else None)
json.dump(out, open(RES/"dashboard_dados.json", "w", encoding="utf-8"), ensure_ascii=False)
print(json.dumps({k: out[k] for k in ("kpi", "enps_rodadas", "enps_seg")}, ensure_ascii=False, default=float)[:2500])
print("area", [(a["nome"], round(a["periodo"]["taxa"], 3)) for a in out["area"]]); print("gestores", len(out["gestores"]), "faixas", [(f["cargo"], len(f["pessoas"])) for f in out["faixas"]])
