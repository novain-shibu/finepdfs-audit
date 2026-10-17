"""Score RolmOCR (kaggle_out4/vlm_results.json) vs v4 and Tesseract on FRESH2, pre-registered FINDINGS sec 19.
Only docs with ALL pages done; OCR-favouring (ZWNJ/ZWJ stripped everywhere); paired bootstrap 2000, seed 0."""
import collections, json, random
from pathlib import Path
import pymupdf
from common import words
D = Path("word_test"); rnd = random.Random(0); zw = lambda t: t.replace("‌", "").replace("‍", "")
V = json.loads(Path("kaggle_out4/vlm_results.json").read_text(encoding="utf-8"))
T = json.loads(Path("kaggle_out3/ocr_results.json").read_text(encoding="utf-8"))
print("\n".join(V["log"]))
per, allp, done = {}, [], []
for lang in "hi bn ta ml te kn gu pa or si".split():
    trip = []
    for v in "abc":
        name = f"fresh2_{lang}_{v}.pdf"; p = D/name
        if not p.exists() or name not in T["files"]: continue
        n = len(pymupdf.open(p)); keys = [f"{name}|{i}" for i in range(n)]
        if not all(k in V["pages"] for k in keys): continue
        done.append(name)
        g = collections.Counter(words(zw((D/f"fresh2_{lang}_{v}.txt").read_text(encoding="utf-8"))))
        cv = collections.Counter(words(zw("\n".join(V["pages"][k] for k in keys))))
        f = T["files"][name]; ct = collections.Counter(words(zw("\n".join(f["pages"][k] for k in sorted(f["pages"], key=int)))))
        c4 = collections.Counter(words(zw((D/f"fresh2_{lang}_{v}.unshaped4.txt").read_text(encoding="utf-8"))))
        for w, m in g.items():
            trip += [(int(k < cv[w]), int(k < ct[w]), int(k < c4[w]), v) for k in range(m)]
    if trip:
        N = len(trip); per[lang] = dict(words=N, rolm=round(100*sum(t[0] for t in trip)/N, 1), tess=round(100*sum(t[1] for t in trip)/N, 1), v4=round(100*sum(t[2] for t in trip)/N, 1))
        print(lang, per[lang])
    allp += trip
def summ(P, tag):
    N = len(P); bs = sorted(sum(t[2]-t[0] for t in rnd.choices(P, k=N))/N for _ in range(2000))
    s = dict(words=N, rolm=round(100*sum(t[0] for t in P)/N, 2), tess=round(100*sum(t[1] for t in P)/N, 2), v4=round(100*sum(t[2] for t in P)/N, 2), v4_minus_rolm_ci=[round(100*bs[50], 2), round(100*bs[1949], 2)])
    print(tag, s); return s
S = {"all": summ(allp, "ALL"), "regular_bold": summ([t for t in allp if t[3] in "ab"], "a+b"), "italic": summ([t for t in allp if t[3] == "c"], "c") if any(t[3] == "c" for t in allp) else None}
sec = list(V["sec"].values()); tok = list(V["tokens"].values())
print("docs scored", len(done), "| rolm s/page (2xT4, batch 6 amortised)", round(sum(sec)/max(1, len(sec)), 1), "| tokens/page", round(sum(tok)/max(1, len(tok))))
Path("word_test/vlm4_scored_20261017.json").write_text(json.dumps({"per_script": per, "summary": S, "docs": done}, indent=1), encoding="utf-8")
