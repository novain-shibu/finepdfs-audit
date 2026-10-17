"""W1: random cluster sample of FinePDFs complex-script configs (8 random offsets x 25 rows per config, seed 20261016),
scored on the fly with validity.py. Stores per-doc stats only; keeps text of up to 15 flagged docling docs per config
(truncated) for the skeptic review. Paced: 3 s between datasets-server calls. Also fetches Wikipedia baselines.
"""
import json, random, sys, time, urllib.parse, urllib.request
sys.path.insert(0, ".")
from validity import scan_text

CONFIGS_ALL = {"hin_Deva": 850570, "mar_Deva": 185544, "npi_Deva": 181691, "ben_Beng": 539857, "asm_Beng": 1551,
           "tam_Taml": 100576, "mal_Mlym": 54104, "tel_Telu": 31411, "kan_Knda": 35407, "guj_Gujr": 84057,
           "pan_Guru": 14727, "ory_Orya": 5745}
WIKI_ALL = {"hi": "Deva", "mr": "Deva", "ne": "Deva", "bn": "Beng", "as": "Beng", "ta": "Taml", "ml": "Mlym",
        "te": "Telu", "kn": "Knda", "gu": "Gujr", "pa": "Guru", "or": "Orya"}
import os
_sel = os.environ.get("CFGS")
CONFIGS_ALL.update({"tha_Thai": 2516013, "khm_Khmr": 23142, "sin_Sinh": 20112, "mya_Mymr": 29171})
WIKI_ALL.update({"th": "Thai", "km": "Khmr", "si": "Sinh", "my": "Mymr"})
CONFIGS = {k: v for k, v in CONFIGS_ALL.items() if not _sel or k in _sel.split(",")}
WIKI = {k: v for k, v in WIKI_ALL.items() if not _sel or v in {c.split("_")[1] for c in CONFIGS}}
OUT = os.environ.get("OUT", "random_sample.json")
UA = {"User-Agent": "invent7-validity-check/0.1 (research; github.com/novain-shibu)"}

def get(url):
    for a in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120))
        except Exception as e:
            print("  retry", e, flush=True); time.sleep(15)
    return None

def main():
    rng = random.Random(20261016)
    out = {"docs": {}, "flagged_text": {}, "wiki": {}}
    for cfg, n in CONFIGS.items():
        script = cfg.split("_")[1]
        offs = sorted(rng.sample(range(0, max(1, n - 25)), 8)) if n > 225 else [0, 25, 50, 75, 100, 125, 150, 175]
        docs, kept = [], []
        for off in offs:
            d = get(f"https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config={cfg}&split=train&offset={off}&length=25")
            time.sleep(3)
            for r in (d or {}).get("rows", []):
                row = r["row"]; bw = []; w, b = scan_text(row["text"], script, bw)
                docs.append({"id": row["id"], "url": row.get("url"), "extractor": row.get("extractor"), "words": w, "invalid": b,
                             "offset": off, "chars": len(row["text"]), "bad_words": bw[:60]})
                if row.get("extractor") == "docling" and w >= 50 and b / w > 0.05 and len(kept) < 15:
                    kept.append({"id": row["id"], "url": row.get("url"), "text": row["text"][:20000]})
        out["docs"][cfg] = docs; out["flagged_text"][cfg] = kept
        print(cfg, len(docs), "docs", flush=True)
    for lang, script in ({} if os.environ.get("NOWIKI") else WIKI).items():
        q = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "random", "grnnamespace": 0,
                                    "grnlimit": 20, "prop": "extracts", "explaintext": 1, "exlimit": 20})
        d = get(f"https://{lang}.wikipedia.org/w/api.php?{q}"); time.sleep(2)
        W = B = 0
        for p in (d or {}).get("query", {}).get("pages", {}).values():
            w, b = scan_text(p.get("extract", ""), script); W += w; B += b
        out["wiki"][lang] = {"script": script, "words": W, "invalid": B}
        print("wiki", lang, W, B, flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

if __name__ == "__main__":
    main()
