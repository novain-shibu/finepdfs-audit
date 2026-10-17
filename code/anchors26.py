"""POST-HOC language-free check for sec 26: do the NUMBERS in FinePDFs' stored text match the numbers free Tesseract
reads on the same PDF pages? Digits are script-independent and read reliably by Tesseract. Token = digit run >= 2 digits
(ASCII digits plus each script's own digits mapped to ASCII). Agreement = share of FinePDFs number tokens also present in
Tesseract's output (multiset), on the same first-N-pages slice as score26. Docs with < 5 FinePDFs number tokens skipped."""
import collections, json, re, statistics, unicodedata
from pathlib import Path
meta = {m["id"]: m for m in json.loads(Path("ocrpath_meta.json").read_text(encoding="utf-8"))}
T = json.loads(Path("kaggle_out5/tess5.json").read_text(encoding="utf-8"))
pages = {r["id"]: r["pages"] for r in json.loads(Path("audit25_results.json").read_text(encoding="utf-8"))}
def nums(t):
    t = "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t)
    return re.findall(r"\d{2,}", t)
out = collections.defaultdict(list)
for doc_id, t in T.items():
    if "pages" not in t: continue
    m = meta[doc_id]
    total = pages.get(re.sub(r"[^A-Za-z0-9-]", "_", doc_id).strip("_"), len(t["pages"])) or len(t["pages"])
    frac = min(1.0, len(t["pages"]) / max(1, total))
    fin = nums(m["text"][: max(1, int(len(m["text"]) * frac))]); tes = collections.Counter(nums("\n".join(t["pages"])))
    if len(fin) < 5 or sum(tes.values()) < 5: continue
    out[m["cfg"]].append(sum(min(n, tes[w]) for w, n in collections.Counter(fin).items()) / len(fin))
for cfg in ["mal_Mlym", "tam_Taml", "tel_Telu", "kan_Knda", "hin_Deva", "ben_Beng"]:
    v = out[cfg]
    print(f"{cfg}: docs {len(v)}, median number agreement {statistics.median(v):.2f}" if v else f"{cfg}: docs 0",
          sorted(round(x, 2) for x in v))
