"""POST-HOC (not pre-registered) second judge for sec 25: where the PDF's OWN text layer is clean Unicode
(>= 100 script words, < 2% invalid by validity.py), measure how much of FinePDFs' rolmOCR text it supports.
COVERAGE = share of FinePDFs' script words (>= 2 chars, NFC, ZWNJ/ZWJ stripped) present in the text layer (multiset)."""
import collections, json, re, statistics, unicodedata
from pathlib import Path
import pymupdf
from validity import scan_text
from common import swords, BLOCK

meta = {re.sub(r"[^A-Za-z0-9-]", "_", m["id"]).strip("_"): m for m in json.loads(Path("ocrpath_meta.json").read_text(encoding="utf-8"))}
R = json.loads(Path("audit25_results.json").read_text(encoding="utf-8"))
groups, rows = collections.defaultdict(list), []
for r in R:
    if not r["text_layer"]:
        continue
    m = meta[r["id"]]; s = m["cfg"].split("_")[1]; b = BLOCK[s]
    raw = "".join(p.get_text() for p in pymupdf.open(f"ocrpath_pdfs/{r['id']}.pdf"))
    w, bad = scan_text(raw, s)
    if w < 100 or bad / w > 0.02:
        continue
    tl = collections.Counter(swords(raw, b)); th = swords(m["text"], b)
    if len(th) < 50:
        continue
    cov = sum(min(n, tl[x]) for x, n in collections.Counter(th).items()) / len(th)
    rev = sum(min(n, collections.Counter(th)[x]) for x, n in tl.items()) / max(1, sum(tl.values()))
    groups[m["cfg"]].append(cov)
    rows.append({"id": r["id"], "cfg": m["cfg"], "tl_words": w, "tl_invalid": round(bad / w, 4), "finepdfs_words": len(th),
                 "coverage": round(cov, 4), "reverse": round(rev, 4)})
for cfg in ["tam_Taml", "mal_Mlym", "tel_Telu", "kan_Knda", "hin_Deva", "ben_Beng"]:
    v = groups.get(cfg, [])
    print(cfg, "n", len(v), "median coverage", round(statistics.median(v), 3) if v else None, sorted(round(x, 2) for x in v))
Path("audit25b_results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
