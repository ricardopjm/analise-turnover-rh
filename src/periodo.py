"""Caminhos e periodo analisado, derivados dos dados. Nenhum script deve ter data ou ano fixo.
DIAG_RAIZ (variavel de ambiente) troca a pasta raiz; serve para testar sem tocar nos dados reais."""
import os, csv
from datetime import date, timedelta
from pathlib import Path
SRC = Path(__file__).resolve().parent
RAIZ = Path(os.environ.get("DIAG_RAIZ", SRC.parent))
ENT, TRAT, RES, ENTREGAS = RAIZ/"DADOS", RAIZ/"DADOS_TRATADOS", RAIZ/"RESULTADOS", RAIZ/"ENTREGAS"
MES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

def indice(m):  # 'AAAA-MM' -> numero sequencial de mes
    return int(m[:4])*12 + int(m[5:7])

def periodo():
    """Periodo = do primeiro ao ultimo mes do historico mensal tratado."""
    with open(TRAT/"historico_mensal.csv", encoding="utf-8", newline="") as f:
        meses = sorted({r["mes"] for r in csv.DictReader(f, delimiter=";")})
    y, m = int(meses[-1][:4]), int(meses[-1][5:7])
    ref = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
    return dict(meses=meses, ini=meses[0], fim=meses[-1], ref=ref, anos=sorted({int(x[:4]) for x in meses}), n=len(meses),
                contiguo=all(indice(b) - indice(a) == 1 for a, b in zip(meses, meses[1:])))

def rotulo(p):
    """Nome da pasta de entrega: AAAA-T1..T4 quando o periodo fecha num trimestre; senao AAAA-MM."""
    y, m = int(p["fim"][:4]), int(p["fim"][5:7])
    return f"{y}-T{(m-1)//3+1}" if m % 3 == 0 else f"{y}-{m:02d}"

def nome_mes(m):  # 'AAAA-MM' -> 'dez/2025'
    return f"{MES_PT[int(m[5:7])-1]}/{m[:4]}"
