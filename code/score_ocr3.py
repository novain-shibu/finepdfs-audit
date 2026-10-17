"""Score Tesseract (kaggle_out3/ocr_results.json) vs v4 on FRESH2, pre-registered FINDINGS sec 18.
Same words() (NFC) and exact-word recall as the decoder runs (common.words); paired word bootstrap (2000, seed 0)."""
import collections, json, random, sys
from pathlib import Path
import pymupdf
from common import words
D = Path("word_test"); rnd = random.Random(0)
R = json.loads(Path("kaggle_out3/ocr_results.json").read_text(encoding="utf-8"))
print("\n".join(R["log"][:8]))
out, allp, secs = {}, [], []
for lang in "hi bn ta ml te kn gu pa or si".split():
    pairs = []
    for v in "abc":
        name = f"fresh2_{lang}_{v}.pdf"; g = collections.Counter(words((D/f"fresh2_{lang}_{v}.txt").read_text(encoding="utf-8")))
        if not g: continue
        f = R["files"].get(name)
        ocr = "\n".join(f["pages"][k] for k in sorted(f["pages"], key=int)) if f else ""
        if f: secs += list(f["page_sec"].values())
        co = collections.Counter(words(ocr)); c4 = collections.Counter(words((D/f"fresh2_{lang}_{v}.unshaped4.txt").read_text(encoding="utf-8")))
        for w, n in g.items():
            pairs += [(int(k < co[w]), int(k < c4[w])) for k in range(n)]
    N = len(pairs); o = sum(p[0] for p in pairs)/N; u = sum(p[1] for p in pairs)/N
    bs = sorted(sum(p[1]-p[0] for p in rnd.choices(pairs, k=N))/N for _ in range(2000))
    out[lang] = dict(words=N, ocr=round(100*o, 1), v4=round(100*u, 1), v4_minus_ocr=round(100*(u-o), 2), ci=[round(100*bs[50], 2), round(100*bs[1949], 2)])
    print(lang, out[lang]); allp += pairs
N = len(allp); bs = sorted(sum(p[1]-p[0] for p in rnd.choices(allp, k=N))/N for _ in range(2000))
s = dict(words=N, ocr=round(100*sum(p[0] for p in allp)/N, 2), v4=round(100*sum(p[1] for p in allp)/N, 2), ci=[round(100*bs[50], 2), round(100*bs[1949], 2)],
         ocr_sec_per_page=round(sum(secs)/max(1, len(secs)), 2), pages=len(secs))
print("ALL", s)
Path("word_test/ocr3_scored_20261017.json").write_text(json.dumps({"per_script": out, "pooled": s}, indent=1), encoding="utf-8")
