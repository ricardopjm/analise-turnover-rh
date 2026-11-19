import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodo import SRC, RES
d = json.load(open(RES/"relatorio_dados.json", encoding="utf-8"))
html = (SRC/"relatorio_template.html").read_text(encoding="utf-8").replace("__DADOS__", json.dumps(d, ensure_ascii=False))
(RES/"relatorio_turnover.html").write_text(html, encoding="utf-8"); print("relatorio_turnover.html ok", len(html)//1024, "KB")
