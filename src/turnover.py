"""Turnover mensal/anual por tipo, area e modalidade. Le DADOS_TRATADOS, grava RESULTADOS/turnover.json.
Periodo e anos derivados dos dados (periodo.py). Anos parciais sao anualizados pelo numero de meses."""
import csv, json, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodo import TRAT, RES, periodo
PER = periodo()
rd = lambda f: list(csv.DictReader(open(TRAT/f, encoding="utf-8"), delimiter=";"))
col = rd("colaboradores.csv"); des = {r["colaborador_id"]: r for r in rd("desligamentos.csv")}
for r in col:
    r["adm"] = date.fromisoformat(r["data_admissao"])
    r["dl"] = date.fromisoformat(r["data_desligamento"]) if r["data_desligamento"] else None
    r["tipo"] = des[r["colaborador_id"]]["tipo"] if r["dl"] else None
meses = [(int(m[:4]), int(m[5:])) for m in PER["meses"]]
def ini(y, m): return date(y, m, 1)
def fim(y, m): return date(y + (m == 12), m % 12 + 1, 1)   # 1o dia do mes seguinte
def ativo_em(r, d): return r["adm"] < d and (r["dl"] is None or r["dl"] >= d)   # ativo antes do dia d
def hc(rows, d): return sum(ativo_em(r, d) for r in rows)
def serie(rows):
    out = []
    for y, m in meses:
        a, b = hc(rows, ini(y, m)), hc(rows, fim(y, m))
        s = [r for r in rows if r["dl"] and (r["dl"].year, r["dl"].month) == (y, m)]
        out.append(dict(mes=f"{y}-{m:02d}", hc_ini=a, hc_fim=b, hc_med=(a+b)/2,
                        vol=sum(r["tipo"] == "Voluntario" for r in s), inv=sum(r["tipo"] == "Involuntario" for r in s)))
    return out
def agg(x):
    k = len(x); hcm = sum(i["hc_med"] for i in x) / k; v = sum(i["vol"] for i in x); iv = sum(i["inv"] for i in x); f = 12 / k
    return dict(meses=k, hc_medio=round(hcm, 1), vol=v, inv=iv, tot=v+iv, taxa=(v+iv)/hcm*f, taxa_vol=v/hcm*f, taxa_inv=iv/hcm*f)
def resumo(rows):
    s = serie(rows); res = {str(a): agg([i for i in s if i["mes"].startswith(str(a))]) for a in PER["anos"]}
    p = agg(s); res["periodo"] = dict(meses=p["meses"], hc_medio=p["hc_medio"], vol=p["vol"], inv=p["inv"], tot=p["tot"],
        taxa_acum=p["tot"]/(sum(i["hc_med"] for i in s)/len(s)), taxa_anual=p["taxa"], taxa_vol_anual=p["taxa_vol"], taxa_inv_anual=p["taxa_inv"])
    return res

if __name__ == "__main__":
    out = dict(periodo=dict(ini=PER["ini"], fim=PER["fim"], n=PER["n"], anos=PER["anos"]), total=dict(serie=serie(col), resumo=resumo(col)), area={}, modalidade={})
    for campo, chave in (("area", "area"), ("modalidade", "modalidade")):
        for v in sorted({r[campo] for r in col}):
            rows = [r for r in col if r[campo] == v]
            out[chave][v] = dict(resumo=resumo(rows), serie=serie(rows))
    top = max(out["area"], key=lambda a: out["area"][a]["resumo"]["periodo"]["taxa_anual"]); out["top_area"] = top
    out["cruzado"] = {}   # modalidade dentro e fora da area com maior turnover
    for grupo, rows in ((top, [r for r in col if r["area"] == top]), ("Demais areas", [r for r in col if r["area"] != top])):
        out["cruzado"][grupo] = {m: resumo([r for r in rows if r["modalidade"] == m])["periodo"] for m in ("Presencial", "Hibrido", "Remoto")}
        out["cruzado"][grupo]["Total"] = resumo(rows)["periodo"]
    RES.mkdir(exist_ok=True)
    json.dump(out, open(RES/"turnover.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("turnover.json ok:", PER["ini"], "a", PER["fim"], "| area com maior turnover:", top)
