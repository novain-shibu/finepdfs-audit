"""FINDINGS sec 26 scorer: AGREEMENT between FinePDFs' production text and free Tesseract on the same PDF (first 10 pages).
FinePDFs text is cut to roughly the same pages (share of its length = OCR'd pages / total pages, min 1).
Validation against labels26.json (written before scores), then the pre-registered rule: < 0.25 fabricated, >= 0.50 faithful."""
import collections, json, math, re, statistics, unicodedata
from pathlib import Path
from common import swords, BLOCK

meta = {m["id"]: m for m in json.loads(Path("ocrpath_meta.json").read_text(encoding="utf-8"))}
T = json.loads(Path("kaggle_out5/tess5.json").read_text(encoding="utf-8"))
pages = {r["id"]: r["pages"] for r in json.loads(Path("audit25_results.json").read_text(encoding="utf-8"))}
labels = json.loads(Path("labels26.json").read_text(encoding="utf-8"))["labels"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - h) / d, 3), round((c + h) / d, 3)


rows = []
for doc_id, t in T.items():
    if "pages" not in t:
        continue
    m = meta[doc_id]; base = BLOCK[m["cfg"].split("_")[1]]
    tess = collections.Counter(swords("\n".join(t["pages"]), base))
    if sum(tess.values()) < 30:
        rows.append({"id": doc_id, "cfg": m["cfg"], "excluded": "tesseract < 30 script words"}); continue
    total = pages.get(re.sub(r"[^A-Za-z0-9-]", "_", doc_id).strip("_"), len(t["pages"])) or len(t["pages"])
    frac = min(1.0, len(t["pages"]) / max(1, total))
    fin = swords(m["text"][: max(1, int(len(m["text"]) * frac))], base)
    if len(fin) < 30:
        rows.append({"id": doc_id, "cfg": m["cfg"], "excluded": "finepdfs < 30 script words"}); continue
    agree = sum(min(n, tess[w]) for w, n in collections.Counter(fin).items()) / len(fin)
    rows.append({"id": doc_id, "cfg": m["cfg"], "agreement": round(agree, 3), "fin_words": len(fin), "tess_words": sum(tess.values())})

print("VALIDATION (labels written before scores):")
ok = n = 0
for L in labels:
    r = next((r for r in rows if L["id_part"] in r["id"] and r["cfg"] == L["cfg"] and "agreement" in r), None)
    a = r["agreement"] if r else None
    pred = None if a is None else ("fabricated" if a < 0.25 else ("faithful" if a >= 0.50 else "unclear"))
    truth = "fabricated" if L["label"] in ("fabricated", "unfaithful") else "faithful"
    hit = pred == truth
    if a is not None:
        n += 1; ok += hit
    print(f"  {L['cfg']} {L['id_part']:9s} label={L['label']:15s} agreement={a} pred={pred} {'OK' if hit else ''}")
print(f"  correct {ok}/{n} -> rule {'VALID' if n >= 10 and ok / max(1, n) >= 0.8 else 'NOT VALID (n<10 or <80%)'}")
print("\nRATE per config (share of scored docs with agreement < 0.25), Wilson 95% CI; median agreement:")
for cfg in ["tam_Taml", "mal_Mlym", "tel_Telu", "kan_Knda", "hin_Deva", "ben_Beng"]:
    v = [r["agreement"] for r in rows if r["cfg"] == cfg and "agreement" in r]
    ex = sum(1 for r in rows if r["cfg"] == cfg and "excluded" in r)
    k = sum(1 for a in v if a < 0.25)
    med = round(statistics.median(v), 3) if v else None
    print(f"  {cfg}: scored {len(v)}, excluded {ex}, fabricated {k}/{len(v)} {wilson(k, len(v))}, median agreement {med}")
Path("score26_results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
