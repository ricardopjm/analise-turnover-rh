"""So para TESTE do pipeline. Uso: python3 -I src/utilitarios/simular_corte.py DADOS /pasta/teste/DADOS
Corta os dados brutos em CUT (30/09/2025), simulando um trimestre anterior. Depois rode com DIAG_RAIZ=/pasta/teste."""
import csv, io, sys
from datetime import date
src, dst = sys.argv[1], sys.argv[2]; CUT = date(2025, 9, 30)
PT = {"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}
def d(s):
    s = s.strip()
    if not s: return None
    if s[4:5] == "-": y, m, dd = s[:10].split("-")
    else: dd, m, y = s.split("/")
    return date(int(y), int(m), int(dd))
def mes(s):
    if s[4:5] == "-": return (int(s[:4]), int(s[5:7]))
    a, b = s.split("/"); return (2000+int(b), PT[a.lower()])
def ler(f, enc):
    return list(csv.reader(io.StringIO(open(f"{src}/{f}", "rb").read().decode(enc), newline=""), delimiter=";"))
def gravar(f, rows, enc):
    out = io.StringIO(newline=""); csv.writer(out, delimiter=";", lineterminator="\r\n").writerows(rows); open(f"{dst}/{f}", "wb").write(out.getvalue().encode(enc))
r = ler("colaboradores.csv", "utf-8-sig"); h, b = r[0], r[1:]; I = {c: i for i, c in enumerate(h)}
out = []; apos = set()
for x in b:
    if d(x[I["data_admissao"]]) > CUT: apos.add(x[0]); continue
    if x[I["data_desligamento"]] and d(x[I["data_desligamento"]]) > CUT: x[I["data_desligamento"]] = ""
    out.append(x)
gravar("colaboradores.csv", [h]+out, "utf-8")
r = ler("desligamentos.csv", "latin1"); gravar("desligamentos.csv", [r[0]]+[x for x in r[1:] if d(x[1]) <= CUT], "latin1")
r = ler("historico_mensal.csv", "utf-8-sig"); gravar("historico_mensal.csv", [r[0]]+[x for x in r[1:] if mes(x[0]) <= (2025, 9)], "utf-8")
r = ler("pesquisa_clima.csv", "utf-8-sig"); gravar("pesquisa_clima.csv", [r[0]]+[x for x in r[1:] if d(x[0]) <= CUT], "utf-8")
import shutil; shutil.copy(f"{src}/faixas_salariais.csv", f"{dst}/faixas_salariais.csv")
print("truncado em", CUT)
