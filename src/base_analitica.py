"""Painel pessoa-mes para investigar saidas. Cada linha = uma pessoa em um mes; evento = saiu NESSE mes.
Fatores dinamicos (hora extra, falta, eNPS) usam apenas informacao de meses ANTERIORES ao mes da linha."""
import csv, math
from datetime import date
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodo import TRAT
rd = lambda f: list(csv.DictReader(open(TRAT/f, encoding="utf-8"), delimiter=";"))
def idx(m): y, mm = m.split("-"); return int(y)*12 + int(mm)
def mstart(m): y, mm = m.split("-"); return date(int(y), int(mm), 1)

def carregar():
    col, hist, pes, des, fx = rd("colaboradores.csv"), rd("historico_mensal.csv"), rd("pesquisa_clima.csv"), rd("desligamentos.csv"), rd("faixas_salariais.csv")
    F = {(r["cargo"], r["nivel"]): float(r["faixa_media"]) for r in fx}
    FM = {(r["cargo"], r["nivel"]): float(r["faixa_min"]) for r in fx}
    D = {r["colaborador_id"]: r for r in des}
    P = {}
    for r in col:
        i = r["colaborador_id"]; k = (r["cargo"], r["nivel"])
        r["sal"] = float(r["salario"]); r["adm"] = date.fromisoformat(r["data_admissao"])
        r["nasc"] = date.fromisoformat(r["data_nascimento"]); r["promo"] = date.fromisoformat(r["data_ultima_promocao"])
        r["dl"] = date.fromisoformat(r["data_desligamento"]) if r["data_desligamento"] else None
        r["compa"] = r["sal"] / F[k]; r["abaixo"] = r["sal"] < FM[k]
        r["tipo"] = D[i]["tipo"] if i in D else None; r["motivo"] = D[i]["motivo"] if i in D else None
        r["promovido"] = r["promo"] > r["adm"]
        P[i] = r
    H = defaultdict(dict)
    for r in hist:
        if r["colaborador_id"] in P:
            H[r["colaborador_id"]][r["mes"]] = (float(r["horas_extras"]) if r["horas_extras"] else None, int(r["faltas_dias"]))
    S = defaultdict(list)
    for r in pes:
        S[r["colaborador_id"]].append((date.fromisoformat(r["data_pesquisa"]), int(r["enps"]), int(r["satisfacao_gestor"]), int(r["satisfacao_salario"]),
                                        int(r["satisfacao_carreira"]) if r["satisfacao_carreira"] else None))
    for v in S.values(): v.sort()
    return P, H, S

def painel():
    P, H, S = carregar(); rows = []
    for i, r in P.items():
        meses = sorted(H[i])
        for m in meses:
            t = mstart(m); n = idx(m)
            ant = [H[i][mm] for mm in (f"{(n-k-1)//12}-{(n-k-1)%12+1:02d}" for k in range(1, 4)) if mm in H[i]]
            he = [a[0] for a in ant if a[0] is not None]
            sv = [x for x in S[i] if x[0] <= t]
            ult = sv[-1] if sv and (t - sv[-1][0]).days <= 200 else None
            saiu = r["dl"] is not None and (r["dl"].year, r["dl"].month) == (t.year, t.month)
            rows.append(dict(id=i, mes=m, t=t, area=r["area"], modal=r["modalidade"], gestor=r["gestor"], gid=r["gestor_id"], cargo=r["cargo"], nivel=r["nivel"],
                uf=r["uf"], compa=r["compa"], abaixo=r["abaixo"], idade=(t - r["nasc"]).days/365.25, ten=(t - r["adm"]).days/30.44,
                he3=(sum(he)/len(he) if he else None), fal3=(sum(a[1] for a in ant) if ant else None),
                promo_ok=r["promo"] <= t, m_promo=((t - r["promo"]).days/30.44 if r["promo"] <= t else None), promovido=r["promovido"],
                enps=(ult[1] if ult else None), s_gest=(ult[2] if ult else None), s_sal=(ult[3] if ult else None), s_carr=(ult[4] if ult else None),
                sal=r["sal"], vol=bool(saiu and r["tipo"] == "Voluntario"), inv=bool(saiu and r["tipo"] == "Involuntario"), motivo=(r["motivo"] if saiu else None)))
    return P, rows

def taxa(rows, key=lambda r: r["vol"]):
    n = len(rows); e = sum(1 for r in rows if key(r))
    return e, n, (e / n * 12 if n else 0)   # taxa anualizada: eventos por pessoa-ano
def poisson_p_maior(obs, esp):
    """P(X >= obs) para Poisson(esp)"""
    if esp <= 0: return 1.0
    s, term = 0.0, math.exp(-esp)
    for k in range(obs):
        s += term; term *= esp / (k + 1)
    return max(0.0, 1 - s)
def wilson(e, n, z=1.96):
    if n == 0: return (0, 0)
    p = e / n; d = 1 + z*z/n; c = p + z*z/(2*n); a = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c - a)/d, (c + a)/d)
