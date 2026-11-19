"""Calcula todos os numeros do relatorio de diagnostico e grava RESULTADOS/relatorio_dados.json.
Tudo derivado dos dados: periodo, area critica e gestores criticos sao detectados por regra, nunca digitados."""
import sys, json, math, csv, statistics as st
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodo import TRAT, RES, periodo
from base_analitica import *
from modelo import logit
PER = periodo(); REF = PER["ref"]; ANOS = PER["anos"]
PES, rows = painel()
T = json.load(open(RES/"turnover.json", encoding="utf-8")); TOP = T["top_area"]
# ---- REGRA DE GESTOR CRITICO: >= 1,5x as saidas voluntarias esperadas para a area E chance de acaso < 5% (Poisson)
OE_MIN, P_MAX = 1.5, 0.05
out = dict(periodo=dict(ini=PER["ini"], fim=PER["fim"], n=PER["n"], anos=ANOS), top_area=TOP, regra_gestor=dict(oe_min=OE_MIN, p_max=P_MAX))
# ---- turnover
blk = lambda tab: sorted([dict(nome=k, hc=v["resumo"]["periodo"]["hc_medio"], tot=v["resumo"]["periodo"]["tot"], vol=v["resumo"]["periodo"]["vol"], inv=v["resumo"]["periodo"]["inv"],
    anual=v["resumo"]["periodo"]["taxa_anual"], av=v["resumo"]["periodo"]["taxa_vol_anual"], ai=v["resumo"]["periodo"]["taxa_inv_anual"]) for k, v in tab.items()], key=lambda x: -x["anual"])
S = T["total"]["serie"]
def taxa_meses(x): return sum(i["vol"]+i["inv"] for i in x)/(sum(i["hc_med"] for i in x)/len(x))*12/len(x)
tend = dict(ult12=taxa_meses(S[-12:]), ant12=taxa_meses(S[-24:-12])) if len(S) >= 24 else None
out["turnover"] = dict(serie=S, anos=T["total"]["resumo"], area=blk(T["area"]), modal=blk(T["modalidade"]), tend=tend)
tot_area_hc = sum(a["hc"] for a in out["turnover"]["area"])
# ---- gestores
ref = defaultdict(lambda: [0, 0])
for r in rows: ref[r["area"]][0] += r["vol"]; ref[r["area"]][1] += 1
G = defaultdict(list)
for r in rows: G[r["gestor"]].append(r)
ges = []
for g, rs in G.items():
    if g == "Nao informado": continue
    obs = sum(r["vol"] for r in rs); esp = sum(ref[r["area"]][0]/ref[r["area"]][1] for r in rs)
    p = poisson_p_maior(obs, esp)
    ges.append(dict(nome=g, area=rs[0]["area"], py=len(rs)/12, obs=obs, esp=esp, oe=obs/esp if esp else 0, p=p, taxa=taxa(rs)[2],
                    ativos=sum(1 for x in PES.values() if not x["dl"] and x["gestor"] == g)))
ges.sort(key=lambda x: -x["oe"])
ALVO = [g["nome"] for g in ges if g["oe"] >= OE_MIN and g["p"] < P_MAX]
for g in ges: g["alvo"] = g["nome"] in ALVO; g["bonf"] = g["p"] < P_MAX/len(ges)
out["gestores"] = ges[:max(12, len(ALVO))]; out["n_gestores"] = len(ges); out["alvo"] = ALVO
def perfil(rs):
    f = lambda k: [r[k] for r in rs if r[k] is not None]; enps = f("enps")
    return dict(s_gest=st.mean(f("s_gest")) if f("s_gest") else None, detr=(sum(e <= 6 for e in enps)/len(enps)) if enps else None)
mot = lambda rs: Counter(r["motivo"] for r in rs if r["motivo"])
a_rows = [r for r in rows if r["gestor"] in ALVO]; o_rows = [r for r in rows if r["gestor"] not in ALVO]
ma, mo = mot(a_rows), mot(o_rows)
if ALVO:
    out["equipes"] = dict(alvo=dict(py=len(a_rows)/12, vol=sum(r["vol"] for r in a_rows), taxa=taxa(a_rows)[2], saidas=sum(ma.values()), **perfil(a_rows)),
                          resto=dict(py=len(o_rows)/12, vol=sum(r["vol"] for r in o_rows), taxa=taxa(o_rows)[2], saidas=sum(mo.values()), **perfil(o_rows)))
else: out["equipes"] = None
out["rel_gestao"] = dict(total=ma["Relação com a gestão"]+mo["Relação com a gestão"], nas_equipes=ma["Relação com a gestão"])
out["pessoapa_alvo"] = len(a_rows)/len(rows)
# ---- area critica: taxa por gestor
at = defaultdict(list)
for r in rows:
    if r["area"] == TOP and r["gestor"] != "Nao informado": at[r["gestor"]].append(r)
out["top_gestores"] = sorted([dict(nome=g, taxa=taxa(v)[2], py=len(v)/12, alvo=g in ALVO) for g, v in at.items() if len(v) >= 120], key=lambda x: -x["taxa"])
fora_top = [r for r in rows if r["area"] != TOP and r["gestor"] not in ALVO]
out["ref_fora_top"] = taxa(fora_top)[2]; out["taxa_top"] = taxa([r for r in rows if r["area"] == TOP])[2]
mhe = lambda rs: st.mean(r["he3"] for r in rs if r["he3"] is not None)
out["he_top"] = dict(top=mhe([r for r in rows if r["area"] == TOP and r["gestor"] not in ALVO]), resto=mhe(fora_top + [r for r in rows if r["area"] == TOP and r["gestor"] not in ALVO][:0]))
out["he_top"]["resto"] = mhe([r for r in rows if r["gestor"] not in ALVO])
# ---- modelo completo (todos os fatores juntos)
CAND = [("gestor", "Gestor crítico", lambda r: r["gestor"] in ALVO), ("area", TOP, lambda r: r["area"] == TOP), ("piso", "Abaixo do piso", lambda r: r["abaixo"]),
    ("detr", "Detrator (eNPS ≤ 6)", lambda r: r["enps"] is not None and r["enps"] <= 6), ("carr", "Satisfação carreira ≤ 2", lambda r: r["s_carr"] is not None and r["s_carr"] <= 2),
    ("he", "Horas extras ≥ 25h/mês", lambda r: r["he3"] is not None and r["he3"] >= 25), ("jr", "Assistente Júnior", lambda r: r["cargo"] == "Assistente" and r["nivel"] == "Junior"),
    ("remoto", "Remoto", lambda r: r["modal"] == "Remoto"), ("hibrido", "Híbrido", lambda r: r["modal"] == "Hibrido"), ("falta", "Faltas ≥ 3 em 3 meses", lambda r: r["fal3"] is not None and r["fal3"] >= 3),
    ("idade", "Idade < 30", lambda r: r["idade"] < 30), ("ten", "Menos de 12 meses de casa", lambda r: r["ten"] < 12), ("promo", "Nunca promovido", lambda r: not r["promovido"]),
    ("ssal", "Satisfação salário ≤ 2", lambda r: r["s_sal"] is not None and r["s_sal"] <= 2), ("sem", "Sem pesquisa recente", lambda r: r["enps"] is None)]
FAT = []
for k, lab, f in CAND:
    n = sum(1 for r in rows if f(r))
    if 0 < n < len(rows) and sum(1 for r in rows if f(r) and r["vol"]) > 0: FAT.append((k, lab, f))
    else: print("AVISO: fator sem variacao no periodo, fora do modelo:", lab)
y = [1.0 if r["vol"] else 0.0 for r in rows]
X = [[1.0] + [1.0 if f(r) else 0.0 for _, _, f in FAT] for r in rows]
res = logit(X, y, ["i"] + [k for k, _, _ in FAT])[1:]
def pval(z): return math.erfc(abs(z)/math.sqrt(2))
def nivel(lo, hi): return "forte" if lo >= 1.4 else "moderado" if lo > 1 else "protetor" if hi < 1 else "nenhum"   # regra de classificacao
def por_ano(f):
    o = []
    for a in ANOS:
        e = [r for r in rows if r["t"].year == a and f(r)]; n = [r for r in rows if r["t"].year == a and not f(r)]
        o.append(dict(ano=a, exp=taxa(e)[2], e=taxa(e)[0], ref=taxa(n)[2], meses=len({r["mes"] for r in e+n})))
    return o
orl = []
for (k, lab, f), (nm, b, se, o, lo, hi, z) in zip(FAT, res):
    ex = [r for r in rows if f(r)]; nx = [r for r in rows if not f(r)]
    orl.append(dict(key=k, nome=lab, orr=o, lo=lo, hi=hi, z=z, p=pval(z), nivel=nivel(lo, hi), bruto=taxa(ex)[2]/taxa(nx)[2], taxa_exp=taxa(ex)[2], eventos=taxa(ex)[0], por_ano=por_ano(f)))
out["or"] = orl
# ---- excesso atribuivel (modelo enxuto: gestor critico, area critica, piso, horas extras)
CORE = [(k, lab, f) for k, lab, f in FAT if k in ("gestor", "area", "piso", "he")]
X4 = [[1.0] + [1.0 if f(r) else 0.0 for _, _, f in CORE] for r in rows]; b4 = [x[1] for x in logit(X4, y, ["i"] + [k for k, _, _ in CORE])]
sig = lambda z: 1/(1+math.exp(-z))
def exc(ix):
    e = 0
    for xi in X4:
        if any(xi[j] for j in ix):
            z = sum(b*x for b, x in zip(b4, xi)); z0 = sum(b*(0 if j in ix else x) for j, (b, x) in enumerate(zip(b4, xi))); e += sig(z)-sig(z0)
    return e
sal_v = st.mean(p["sal"] for p in PES.values() if p["tipo"] == "Voluntario")
ordem = {"area": 0, "piso": 1, "gestor": 2, "he": 3}
out["excesso"] = dict(total_vol=int(sum(y)), sal_vol=sal_v, todos=exc(list(range(1, len(CORE)+1))),
    itens=sorted([dict(key=k, nome=lab if k != "he" else "Horas extras ≥ 25h", e=exc([i+1]), custo=exc([i+1])*3*sal_v) for i, (k, lab, _) in enumerate(CORE)], key=lambda d: -d["e"]))
out["custo_total"] = sum(3*p["sal"] for p in PES.values() if p["dl"])
# ---- piso e eNPS
def rt(rs): e, n, t = taxa(rs); lo, hi = wilson(e, n); return dict(taxa=t, e=e, py=n/12, lo=lo*12, hi=hi*12)
out["piso_ano"] = [dict(ano=a, abaixo=rt([r for r in rows if r["t"].year == a and r["abaixo"]]), dentro=rt([r for r in rows if r["t"].year == a and not r["abaixo"]])) for a in ANOS]
out["piso_total"] = dict(abaixo=rt([r for r in rows if r["abaixo"]]), dentro=rt([r for r in rows if not r["abaixo"]]))
sub = [r for r in rows if r["area"] != TOP and r["gestor"] not in ALVO]
out["piso_fora"] = dict(abaixo=rt([r for r in sub if r["abaixo"]]), dentro=rt([r for r in sub if not r["abaixo"]]))
com = [r for r in rows if r["enps"] is not None]
out["piso_detr"] = [dict(nome=f"{'Abaixo do piso' if a else 'Dentro da faixa'} · {'detrator' if d else 'não detrator'}", **rt([r for r in com if r["abaixo"] == a and (r["enps"] <= 6) == d])) for a in (True, False) for d in (True, False)]
out["enps"] = [dict(nome=n, **rt([r for r in com if f(r["enps"])])) for n, f in (("Detrator (0 a 6)", lambda e: e <= 6), ("Neutro (7 e 8)", lambda e: 7 <= e <= 8), ("Promotor (9 e 10)", lambda e: e >= 9))]
sai = lambda r: r["vol"] or r["inv"]
out["motivo_sal"] = dict(abaixo=sum(1 for r in rows if r["motivo"] == "Salário" and r["abaixo"] and sai(r)), n_abaixo=sum(1 for r in rows if r["abaixo"] and sai(r)),
    dentro=sum(1 for r in rows if r["motivo"] == "Salário" and not r["abaixo"] and sai(r)), n_dentro=sum(1 for r in rows if not r["abaixo"] and sai(r)))
# ---- quadro ativo hoje
ativos = [p for p in PES.values() if not p["dl"]]
pesq = list(csv.DictReader(open(TRAT/"pesquisa_clima.csv", encoding="utf-8"), delimiter=";")); ult_data = max(r["data_pesquisa"] for r in pesq)
ult = {r["colaborador_id"]: int(r["enps"]) for r in pesq if r["data_pesquisa"] == ult_data}
fl = {p["colaborador_id"]: (p["gestor"] in ALVO, p["abaixo"], ult.get(p["colaborador_id"], 99) <= 6) for p in ativos}
fx_min = {(r["cargo"], r["nivel"]): float(r["faixa_min"]) for r in csv.DictReader(open(TRAT/"faixas_salariais.csv", encoding="utf-8"), delimiter=";")}
falta = sum(fx_min[(p["cargo"], p["nivel"])]-p["sal"] for p in ativos if p["abaixo"])
nab = sum(v[1] for v in fl.values()); sal_ab = st.mean(p["sal"] for p in ativos if p["abaixo"]) if nab else 0
dif = out["piso_total"]["abaixo"]["taxa"] - out["piso_total"]["dentro"]["taxa"]
compa = lambda p: p["compa"]; anos_casa = lambda p: (REF - p["adm"]).days/365.25
nov = [compa(p) for p in ativos if anos_casa(p) < 1.5]; vet = [compa(p) for p in ativos if anos_casa(p) > 4]
out["hoje"] = dict(ativos=len(ativos), equipe=sum(v[0] for v in fl.values()), piso=nab, detr=sum(v[2] for v in fl.values()), ult_data=ult_data, resp=len(ult),
    dois=sum(1 for v in fl.values() if sum(v) >= 2), piso_detr=sum(1 for v in fl.values() if v[1] and v[2]), custo_piso_ano=falta*12, sal_ab=sal_ab,
    evit_ano=max(0.0, dif*nab), detr_top=sum(1 for p in ativos if p["area"] == TOP and fl[p["colaborador_id"]][2]),
    ativos_alvo={g: sum(1 for p in ativos if p["gestor"] == g) for g in ALVO},
    compa_novos=st.median(nov) if nov else None, compa_vets=st.median(vet) if vet else None)
json.dump(out, open(RES/"relatorio_dados.json", "w", encoding="utf-8"), ensure_ascii=False)
print("relatorio_dados.json ok | area critica:", TOP, "| gestores criticos:", ALVO or "nenhum", "| fatores no modelo:", len(FAT))
print({o["nome"]: (round(o["orr"], 2), o["nivel"]) for o in orl})
