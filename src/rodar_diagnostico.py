"""Roda o diagnostico completo: confere os dados brutos, trata, calcula, gera os dois HTML e arquiva a entrega em ENTREGAS/<periodo>/.
Uso:  python3 src/rodar_diagnostico.py          (usa a pasta DADOS/ do projeto)
Para testar sem tocar nos dados reais: DIAG_RAIZ=/outra/pasta python3 src/rodar_diagnostico.py"""
import csv, json, os, shutil, subprocess, sys, io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodo import SRC, RAIZ, ENT, TRAT, RES, ENTREGAS, periodo, rotulo, nome_mes

ESPERADO = {
    "colaboradores.csv": "colaborador_id;nome;area;cargo;nivel;gestor_id;gestor;data_admissao;data_desligamento;salario;modalidade;cidade;uf;data_nascimento;data_ultima_promocao",
    "historico_mensal.csv": "mes;colaborador_id;horas_extras;faltas_dias",
    "pesquisa_clima.csv": "data_pesquisa;colaborador_id;enps;satisfacao_gestor;satisfacao_salario;satisfacao_carreira",
    "desligamentos.csv": "colaborador_id;data_desligamento;tipo;motivo;aviso_previo",
    "faixas_salariais.csv": "cargo;nivel;faixa_min;faixa_media;faixa_max"}
AREAS = {"Atendimento", "Operacoes", "Comercial", "Tecnologia", "Logistica", "Financeiro", "Marketing", "RH"}
PASSOS = ["limpeza_rh.py", "turnover.py", "salario_faixa.py", "dados_relatorio.py", "gerar_relatorio.py", "dados_dashboard.py", "gerar_dashboard.py"]
avisos, erros, log = [], [], []
def say(msg): print(msg); log.append(msg)
def le(p, enc=None):
    b = p.read_bytes()
    for e in ([enc] if enc else ["utf-8-sig", "latin1"]):
        try: return list(csv.DictReader(io.StringIO(b.decode(e), newline=""), delimiter=";")), b.decode(e).splitlines()[0]
        except UnicodeDecodeError: pass
    raise SystemExit(f"nao consegui ler {p.name}")
def rd(p): return list(csv.DictReader(open(p, encoding="utf-8", newline=""), delimiter=";"))

# ---------- 1. conferencia dos brutos ----------
say(f"== 1. Conferindo os dados brutos em {ENT.relative_to(RAIZ)}/")
for nome, cab in ESPERADO.items():
    p = ENT / nome
    if not p.exists(): erros.append(f"arquivo ausente: {nome}"); continue
    linhas, cab_lido = le(p)
    if cab_lido.strip().lstrip("﻿") != cab: erros.append(f"{nome}: colunas diferentes do esperado.\n   esperado: {cab}\n   recebido: {cab_lido}")
    say(f"   {nome}: {len(linhas)} linhas")
if erros:
    for e in erros: print("ERRO:", e)
    raise SystemExit("Parei: corrija os arquivos e rode de novo. Nada foi alterado.")

def passo(script, n, total):
    say(f"== {n}/{total}. {script}")
    r = subprocess.run([sys.executable, "-I", str(SRC / script)], capture_output=True, text=True, env={**os.environ, "DIAG_RAIZ": str(RAIZ)})
    saida = (r.stdout + r.stderr).strip()
    for l in saida.splitlines()[-6:]: say("   " + l[:200])
    if r.returncode: raise SystemExit(f"Parei em {script} (codigo {r.returncode}). Veja a mensagem acima; nada foi arquivado.")
    for l in saida.splitlines():
        if l.startswith("AVISO"): avisos.append(l)

passo(PASSOS[0], 1, 7)
# ---------- 2. conferencia dos tratados ----------
say("== 2. Conferindo a consistencia dos dados tratados")
col, des, hist, fx = rd(TRAT/"colaboradores.csv"), rd(TRAT/"desligamentos.csv"), rd(TRAT/"historico_mensal.csv"), rd(TRAT/"faixas_salariais.csv")
P = periodo()
if not P["contiguo"]: erros.append("o historico mensal tem meses faltando entre o primeiro e o ultimo")
ids = [r["colaborador_id"] for r in col]
if len(ids) != len(set(ids)): erros.append("ha colaborador_id repetido no cadastro tratado")
deslig_cad = {r["colaborador_id"] for r in col if r["data_desligamento"]}; deslig_arq = {r["colaborador_id"] for r in des}
if deslig_cad != deslig_arq: erros.append(f"cadastro e desligamentos nao batem: {len(deslig_cad - deslig_arq)} so no cadastro, {len(deslig_arq - deslig_cad)} so no arquivo de desligamentos")
ultimo = {}
for r in hist: ultimo[r["colaborador_id"]] = max(ultimo.get(r["colaborador_id"], ""), r["mes"])
div = sum(1 for r in col if r["data_desligamento"] and ultimo.get(r["colaborador_id"]) not in (None, r["data_desligamento"][:7]))
if div: avisos.append(f"{div} pessoas desligadas cujo ultimo mes no historico nao e o mes do desligamento")
novas = {r["area"] for r in col} - AREAS
if novas: avisos.append(f"areas novas no cadastro: {sorted(novas)} (revisar regras de tratamento)")
faixas = {(r["cargo"], r["nivel"]) for r in fx}; sem = {(r["cargo"], r["nivel"]) for r in col} - faixas
if sem: erros.append(f"cargo/nivel sem faixa salarial: {sorted(sem)}")
rej = rd(TRAT/"rejeitados.csv"); pct_rej = len(rej)/max(1, len(hist)+len(rej))
if pct_rej > 0.02: avisos.append(f"{len(rej)} linhas de historico rejeitadas ({pct_rej:.1%} do total), acima do usual (0,1%)")
say(f"   periodo: {nome_mes(P['ini'])} a {nome_mes(P['fim'])} ({P['n']} meses) | {len(col)} pessoas | {len(deslig_arq)} desligamentos | {len(rej)} linhas rejeitadas")
if erros:
    for e in erros: print("ERRO:", e)
    raise SystemExit("Parei: inconsistencia nos dados. Nada foi arquivado.")

for i, s in enumerate(PASSOS[1:], 2): passo(s, i, 7)
T = json.load(open(RES/"turnover.json", encoding="utf-8"))
hc_cad = sum(1 for r in col if not r["data_desligamento"]); hc_fim = T["total"]["serie"][-1]["hc_fim"]
if hc_cad != hc_fim: erros.append(f"headcount do cadastro ({hc_cad}) difere do headcount do ultimo mes ({hc_fim})")

# ---------- 3. resumo e comparativo ----------
K = json.load(open(RES/"dashboard_dados.json", encoding="utf-8")); Rl = json.load(open(RES/"relatorio_dados.json", encoding="utf-8"))
ER = K["enps_rodadas"]; kk = K["kpi"]; E = Rl["excesso"]; H = Rl["hoje"]
resumo = dict(rotulo=rotulo(P), ini=P["ini"], fim=P["fim"], meses=P["n"], headcount=kk["headcount"], taxa_anual=kk["taxa"], taxa_vol_anual=kk["taxa_vol"], saidas=kk["saidas"], voluntarias=kk["vol"],
    custo_estimado=kk["custo"], enps=round(ER[-1]["enps"], 1), enps_rodada=ER[-1]["data"], abaixo_do_piso=H["piso"], piso_e_detrator=H["piso_detr"], detratores_ativos=H["detr"], pessoas_com_2_sinais=H["dois"],
    area_critica=Rl["top_area"], taxa_area_critica=Rl["taxa_top"], gestores_criticos=Rl["alvo"], explicado_pelos_fatores=E["todos"]/E["total_vol"],
    tendencia=K["kpi"]["tend"], fatores={o["nome"]: dict(orr=round(o["orr"], 2), nivel=o["nivel"]) for o in Rl["or"]},
    excesso={i["nome"]: round(i["e"], 1) for i in E["itens"]}, avisos=avisos)
pasta = ENTREGAS / resumo["rotulo"]
anteriores = []
if ENTREGAS.exists():
    for d in ENTREGAS.iterdir():
        f = d / "resumo.json"
        if d.is_dir() and not d.name.startswith("._") and f.exists() and d.name != pasta.name:
            r0 = json.load(open(f, encoding="utf-8"))
            if r0["fim"] < resumo["fim"]: anteriores.append(r0)
ant = max(anteriores, key=lambda r: r["fim"]) if anteriores else None
if ant is None and ENTREGAS.exists(): pass
f1 = lambda x: f"{x*100:.1f}%".replace(".", ",")
def lin(nome, a, b, fmt=lambda x: f"{x}", pp=False):
    if ant is None: return f"| {nome} | {fmt(a)} | — | — |"
    d = a - b
    if pp: var = f"{'+' if d > 0 else ''}{str(round(d*100, 1)).replace('.', ',')} pp"
    else: var = f"{'+' if d > 0 else ''}{fmt(round(d, 1) if isinstance(d, float) and d != int(d) else int(d))}"
    return f"| {nome} | {fmt(a)} | {fmt(b)} | {var} |"
md = [f"# Comparativo do diagnostico: {resumo['rotulo']}" + (f" contra {ant['rotulo']}" if ant else ""), "",
      f"Periodo: {nome_mes(P['ini'])} a {nome_mes(P['fim'])} ({P['n']} meses)." + ("" if ant else " Primeira entrega arquivada, sem trimestre anterior para comparar."), "",
      "| Indicador | Agora | Anterior | Variacao |", "|---|---|---|---|"]
g = (lambda k: ant[k]) if ant else (lambda k: resumo[k])
md += [lin("Headcount atual", resumo["headcount"], g("headcount")), lin("Turnover anual do periodo", resumo["taxa_anual"], g("taxa_anual"), f1, True), lin("Turnover voluntario anual", resumo["taxa_vol_anual"], g("taxa_vol_anual"), f1, True),
       lin("Saidas acumuladas", resumo["saidas"], g("saidas")), lin("Custo estimado (3x salario), R$", round(resumo["custo_estimado"]), round(g("custo_estimado")), lambda x: f"{x:,}".replace(",", ".")),
       lin("eNPS (ultima rodada)", resumo["enps"], g("enps"), lambda x: str(x).replace(".", ",")), lin("Pessoas abaixo do piso", resumo["abaixo_do_piso"], g("abaixo_do_piso")), lin("Detratores ativos", resumo["detratores_ativos"], g("detratores_ativos")),
       lin("Explicado pelos fatores", resumo["explicado_pelos_fatores"], g("explicado_pelos_fatores"), lambda x: f"{x*100:.0f}%", True), ""]
if ant:
    mudou = []
    if ant["area_critica"] != resumo["area_critica"]: mudou.append(f"Area com maior turnover mudou: {ant['area_critica']} -> {resumo['area_critica']}.")
    ent = sorted(set(resumo["gestores_criticos"]) - set(ant["gestores_criticos"])); sai = sorted(set(ant["gestores_criticos"]) - set(resumo["gestores_criticos"]))
    if ent: mudou.append("Gestores que passaram a ser criticos: " + ", ".join(ent) + ".")
    if sai: mudou.append("Gestores que deixaram de ser criticos: " + ", ".join(sai) + ".")
    for nm, v in resumo["fatores"].items():
        v0 = ant["fatores"].get(nm)
        if v0 and v0["nivel"] != v["nivel"]: mudou.append(f"Fator '{nm}' mudou de classificacao: {v0['nivel']} -> {v['nivel']} (razao de chances {v0['orr']} -> {v['orr']}).")
    md += ["## O que mudou de qualitativo", ""] + (["- " + m for m in mudou] or ["- Nenhuma mudanca de area critica, gestores criticos ou classificacao de fatores."]) + [""]
if avisos: md += ["## Avisos da execucao", ""] + ["- " + a for a in avisos] + [""]
if erros:
    for e in erros: print("ERRO:", e)
    raise SystemExit("Parei: " + erros[0])

# ---------- 4. arquivar ----------
say(f"== Arquivando em {pasta.relative_to(RAIZ)}/")
if pasta.exists(): avisos.append(f"a entrega {pasta.name} ja existia e foi substituida"); shutil.rmtree(pasta)
(pasta / "dados_brutos").mkdir(parents=True)
for f in ("dashboard_turnover.html", "relatorio_turnover.html", "abaixo_do_piso.csv"): shutil.copy2(RES/f, pasta/f)
for f in ("log_limpeza.csv", "rejeitados.csv"): shutil.copy2(TRAT/f, pasta/f)
for f in ENT.glob("*.csv"):   # so os CSVs: o dicionario fica de fora
    if not f.name.startswith("._"): shutil.copy2(f, pasta/"dados_brutos"/f.name)
# copia mais recente dos dois HTMLs para docs/ (e a pagina publicada no GitHub Pages)
DOCS = RAIZ/"docs"; DOCS.mkdir(exist_ok=True)
for f in ("dashboard_turnover.html", "relatorio_turnover.html"): shutil.copy2(RES/f, DOCS/f)
json.dump(resumo, open(pasta/"resumo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
(pasta/"comparativo.md").write_text("\n".join(md), encoding="utf-8")
(pasta/"log_execucao.txt").write_text("\n".join(log + ["AVISOS:"] + avisos), encoding="utf-8")
say("\n" + "\n".join(md[:14]))
say(f"\nPRONTO. Entrega: {pasta.relative_to(RAIZ)}/ (copia dos HTMLs em docs/)" + (f"\n{len(avisos)} aviso(s): " + " | ".join(avisos) if avisos else ""))
