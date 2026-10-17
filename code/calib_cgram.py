"""Census v2 calibration (run BEFORE any census data exists): character 3-gram agreement on the EXISTING sec-26 data.
CGRAM agreement = share of FinePDFs' script 3-grams (script characters only, whitespace and other characters removed)
found in Tesseract's 3-grams of the same pages (multiset). Compared with the word-agreement labels of sec 26."""
import collections, json, re, statistics, unicodedata
from pathlib import Path

BLOCKS = {"Taml": (0x0B80, 0x0BFF), "Mlym": (0x0D00, 0x0D7F), "Telu": (0x0C00, 0x0C7F), "Knda": (0x0C80, 0x0CFF),
          "Deva": (0x0900, 0x097F), "Beng": (0x0980, 0x09FF), "Gujr": (0x0A80, 0x0AFF), "Orya": (0x0B00, 0x0B7F),
          "Guru": (0x0A00, 0x0A7F), "Sinh": (0x0D80, 0x0DFF), "Thai": (0x0E00, 0x0E7F), "Khmr": (0x1780, 0x17FF),
          "Mymr": (0x1000, 0x109F)}


def cgrams(t, script, n=3):
    lo, hi = BLOCKS[script]
    t = unicodedata.normalize("NFC", t)
    s = "".join(c for c in t if lo <= ord(c) <= hi)
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def cagree(fin_text, tess_text, script):
    f = collections.Counter(cgrams(fin_text, script)); t = collections.Counter(cgrams(tess_text, script))
    tot = sum(f.values())
    return (sum(min(n, t[g]) for g, n in f.items()) / tot) if tot >= 100 else None


if __name__ == "__main__":
    meta = {m["id"]: m for m in json.loads(Path("ocrpath_meta.json").read_text(encoding="utf-8"))}
    T = json.loads(Path("kaggle_out5/tess5.json").read_text(encoding="utf-8"))
    pages = {r["id"]: r["pages"] for r in json.loads(Path("audit25_results.json").read_text(encoding="utf-8"))}
    S = {r["id"]: r for r in json.loads(Path("score26_results.json").read_text()) if "agreement" in r}
    by = collections.defaultdict(list)
    pairs = []
    for doc_id, r in S.items():
        m = meta[doc_id]; script = m["cfg"].split("_")[1]
        total = pages.get(re.sub(r"[^A-Za-z0-9-]", "_", doc_id).strip("_"), 1) or 1
        frac = min(1.0, len(T[doc_id]["pages"]) / total)
        a = cagree(m["text"][: max(1, int(len(m["text"]) * frac))], "\n".join(T[doc_id]["pages"]), script)
        if a is None:
            continue
        by[m["cfg"]].append(a); pairs.append((r["agreement"] < 0.25, a))
    for cfg, v in by.items():
        print(f"{cfg}: n {len(v)} median 3-gram agreement {statistics.median(v):.3f} range {min(v):.2f}-{max(v):.2f}")
    fab = [a for f, a in pairs if f]; ok = [a for f, a in pairs if not f]
    print(f"word-flagged docs: median {statistics.median(fab):.3f} max {max(fab):.3f} | not flagged: median {statistics.median(ok):.3f} min {min(ok):.3f}")
    cut = (statistics.median(fab) + statistics.median(ok)) / 2
    acc = sum((a < cut) == f for f, a in pairs) / len(pairs)
    print(f"midpoint cut-off = {cut:.3f}; agreement with word-based labels on these {len(pairs)} docs: {acc:.1%}")
