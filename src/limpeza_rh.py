"""Limpeza das bases de RH. Le ../DADOS (originais, intocados) e grava em ../DADOS_TRATADOS."""
import csv, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodo import ENT, TRAT as SAI
SAI.mkdir(exist_ok=True)
log = []          # (arquivo, problema, qtd, acao)
rejeitados = []   # (arquivo, motivo, linha original)

ENC = {}   # encoding efetivamente usado em cada arquivo
def ler(nome, enc=None):
    """Le o CSV tentando UTF-8 e, se falhar, ISO-8859-1 (arquivo de desligamentos veio assim)."""
    bruto = (ENT / nome).read_bytes()
    for e in ([enc] if enc else ["utf-8-sig", "latin1"]):
        try: texto = bruto.decode(e); ENC[nome] = e; break
        except UnicodeDecodeError: continue
    import io
    return list(csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"))

def gravar(nome, linhas, cols):
    with open(SAI / nome, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=";", lineterminator="\n")
        w.writeheader(); w.writerows(linhas)

def reg(arq, prob, qtd, acao):
    log.append((arq, prob, qtd, acao))

def data(s):
    s = s.strip()
    if not s: return None
    if re.match(r"\d{4}-\d{2}-\d{2}", s): y, m, d = s[:10].split("-")
    else: d, m, y = s.split("/")
    return date(int(y), int(m), int(d))

def iso(d): return d.isoformat() if d else ""

# ---------------- colaboradores ----------------
AREA = {"ti": "Tecnologia", "t.i.": "Tecnologia", "tecnologia": "Tecnologia", "operações": "Operacoes", "operacoes": "Operacoes"}
MODAL = {"presencial": "Presencial", "hibrido": "Hibrido", "híbrido": "Hibrido", "remoto": "Remoto", "home office": "Remoto"}

col = ler("colaboradores.csv")
vistos, unicos = set(), []
for r in col:
    k = tuple(r.values())
    if k in vistos: continue
    vistos.add(k); unicos.append(r)
reg("colaboradores", "linhas duplicadas exatas", len(col) - len(unicos), "removidas")
col = unicos

desl = ler("desligamentos.csv")
if ENC["desligamentos.csv"] == "latin1": reg("desligamentos", "arquivo em ISO-8859-1 (acentos quebrados)", len(desl), "convertido para UTF-8")
data_desl = {r["colaborador_id"]: data(r["data_desligamento"]) for r in desl}

n = dict(sal=0, area=0, cargo=0, modal=0, gest=0, deslig=0, nome=0)
for r in col:
    s = r["salario"].strip()
    if "R$" in s:
        s = s.replace("R$", "").replace(".", "").replace(",", ".").strip(); n["sal"] += 1
    r["salario"] = f"{float(s):.2f}"
    a = AREA.get(r["area"].strip().lower(), r["area"].strip())
    n["area"] += a != r["area"]; r["area"] = a
    c = r["cargo"].strip().title()
    n["cargo"] += c != r["cargo"]; r["cargo"] = c
    m = MODAL[r["modalidade"].strip().lower()]
    n["modal"] += m != r["modalidade"]; r["modalidade"] = m
    if not r["gestor_id"]:
        r["gestor_id"], r["gestor"] = "NI", "Nao informado"; n["gest"] += 1
    adm, dl = data(r["data_admissao"]), data(r["data_desligamento"])
    ref = data_desl.get(r["colaborador_id"])
    if dl and ref and dl != ref:   # fonte de verdade: arquivo de desligamentos
        n["deslig"] += 1; dl = ref
    for k in ("data_admissao", "data_nascimento", "data_ultima_promocao"):
        r[k] = iso(data(r[k]))
    r["data_admissao"], r["data_desligamento"] = iso(adm), iso(dl)
    for k in ("nome", "gestor"):
        r[k] = r[k].strip()
reg("colaboradores", "salario em texto 'R$ 4.500,00'", n["sal"], "convertido para numero")
reg("colaboradores", "area com grafias diferentes (TI, T.I., Operações)", n["area"], "padronizado: Tecnologia / Operacoes")
reg("colaboradores", "cargo em CAIXA ALTA ou com espaco sobrando", n["cargo"], "padronizado (Title Case, sem espacos)")
reg("colaboradores", "modalidade com grafias diferentes (Híbrido, HIBRIDO, Home Office...)", n["modal"], "padronizado: Presencial / Hibrido / Remoto (Home Office = Remoto)")
reg("colaboradores", "gestor em branco", n["gest"], "preenchido com gestor_id 'NI' / 'Nao informado'")
reg("colaboradores", "desligamento anterior a admissao (data diferente do arquivo desligamentos)", n["deslig"], "corrigido com a data de desligamentos.csv")
reg("colaboradores", "datas em DD/MM/AAAA", len(col), "convertidas para AAAA-MM-DD")

ids = {r["colaborador_id"]: r for r in col}
# validacoes pos-correcao
ruim = [i for i, r in ids.items() if r["data_desligamento"] and r["data_desligamento"] < r["data_admissao"]]
assert not ruim, ruim
promo = [i for i, r in ids.items() if r["data_desligamento"] and r["data_ultima_promocao"] > r["data_desligamento"]]
reg("colaboradores", "promocao posterior ao desligamento (apos correcao)", len(promo), "mantido; sem ocorrencias" if not promo else f"mantido, revisar: {promo}")
gravar("colaboradores.csv", col, list(col[0].keys()))

# ---------------- desligamentos ----------------
n_tipo = 0
for r in desl:
    t = r["tipo"].strip().title()
    n_tipo += t != r["tipo"]; r["tipo"] = t
    r["data_desligamento"] = iso(data(r["data_desligamento"]))
reg("desligamentos", "tipo com caixa inconsistente (voluntario/Voluntario)", n_tipo, "padronizado (Voluntario / Involuntario)")
reg("desligamentos", "datas em formato misto", len(desl), "convertidas para AAAA-MM-DD")
assert all(r["colaborador_id"] in ids for r in desl)
gravar("desligamentos.csv", desl, list(desl[0].keys()))

# ---------------- historico_mensal ----------------
PT = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
def mes(s):
    s = s.strip()
    if re.match(r"\d{4}-\d{2}$", s): return s, False
    a, b = s.split("/"); return f"20{b}-{PT[a.lower()]:02d}", True

hist = ler("historico_mensal.csv")
out, chaves = [], set()
c = dict(mes=0, falta=0, neg=0, dup=0, orf=0)
for r in hist:
    if r["colaborador_id"] not in ids:
        c["orf"] += 1; rejeitados.append(("historico_mensal", "colaborador inexistente no cadastro", ";".join(r.values()))); continue
    m, mudou = mes(r["mes"]); c["mes"] += mudou
    if not r["faltas_dias"].strip().isdigit(): c["falta"] += 1
    faltas = int(re.sub(r"\D", "", r["faltas_dias"]))
    he = float(r["horas_extras"])
    if he < 0:
        c["neg"] += 1; he = None
    k = (m, r["colaborador_id"], he, faltas)
    if k in chaves: c["dup"] += 1; continue
    chaves.add(k)
    out.append({"mes": m, "colaborador_id": r["colaborador_id"], "horas_extras": "" if he is None else f"{he:.1f}", "faltas_dias": faltas})
reg("historico_mensal", "mes em formato misto (abr/24)", c["mes"], "convertido para AAAA-MM")
reg("historico_mensal", "faltas_dias como texto ('2 dias')", c["falta"], "convertido para inteiro")
reg("historico_mensal", "horas extras negativas (valor impossivel)", c["neg"], "valor esvaziado (nulo), linha mantida para nao perder as faltas")
reg("historico_mensal", "linhas duplicadas", c["dup"], "removidas")
reg("historico_mensal", "linhas orfas (colaborador fora do cadastro)", c["orf"], "removidas e listadas em rejeitados.csv")
gravar("historico_mensal.csv", out, ["mes", "colaborador_id", "horas_extras", "faltas_dias"])

# ---------------- pesquisa_clima ----------------
LIK = {"discordo totalmente": 1, "discordo": 2, "neutro": 3, "concordo": 4, "concordo totalmente": 5}
pes = ler("pesquisa_clima.csv")
c = dict(enps=0, gest=0, carr=0)
for r in pes:
    e = r["enps"].strip()
    if not e.isdigit(): c["enps"] += 1
    r["enps"] = int(e.split(" ")[0])
    g = r["satisfacao_gestor"].strip()
    if not g.isdigit(): c["gest"] += 1; g = LIK[g.lower()]
    r["satisfacao_gestor"] = int(g)
    c["carr"] += r["satisfacao_carreira"] == ""
    r["data_pesquisa"] = iso(data(r["data_pesquisa"]))
    assert r["colaborador_id"] in ids and 0 <= r["enps"] <= 10
reg("pesquisa_clima", "enps como texto ('8 - nota 8')", c["enps"], "convertido para inteiro")
reg("pesquisa_clima", "satisfacao_gestor como rotulo ('Concordo')", c["gest"], "convertido para 1-5 (Discordo totalmente=1 ... Concordo totalmente=5)")
reg("pesquisa_clima", "satisfacao_carreira em branco", c["carr"], "mantido em branco (nao imputado)")
reg("pesquisa_clima", "datas DD/MM/AAAA", len(pes), "convertidas para AAAA-MM-DD")
gravar("pesquisa_clima.csv", pes, list(pes[0].keys()))

# ---------------- faixas ----------------
fx = ler("faixas_salariais.csv")
gravar("faixas_salariais.csv", fx, list(fx[0].keys()))
reg("faixas_salariais", "sem problemas", 0, "copiada sem alteracao")

# ---------------- relatorios ----------------
with open(SAI / "log_limpeza.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter=";", lineterminator="\n"); w.writerow(["arquivo", "problema", "linhas_afetadas", "acao"]); w.writerows(log)
with open(SAI / "rejeitados.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter=";", lineterminator="\n"); w.writerow(["arquivo", "motivo", "linha_original"]); w.writerows(rejeitados)
for l in log: print(l)
