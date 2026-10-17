import sys, collections, random, json
from pathlib import Path
sys.path.insert(0, r".")
from common import words
import pymupdf
D = Path(r"word_test")
res = json.loads(sorted(D.glob("unshape_multi3_2026101*.json"))[-1].read_text())
rnd = random.Random(0); out = {}; npass = 0
for lang in "hi bn ta ml te kn gu pa or si".split():
    ind = []; mu_ind = []; fonts = set()
    for v in "abc":
        g = collections.Counter(words((D/f"fresh_{lang}_{v}.txt").read_text(encoding="utf-8")))
        c = collections.Counter(words((D/f"fresh_{lang}_{v}.unshaped3.txt").read_text(encoding="utf-8")))
        doc = pymupdf.open(D/f"fresh_{lang}_{v}.pdf")
        m = collections.Counter(words("".join(p.get_text() for p in doc)))
        for p in doc:
            for f in p.get_fonts(): fonts.add((v, f[3]))
        for w, n in g.items():
            k = min(n, c[w]); ind += [1]*k + [0]*(n-k)
            k = min(n, m[w]); mu_ind += [1]*k + [0]*(n-k)
    N = len(ind); p = sum(ind)/N
    bs = sorted(sum(rnd.choices(ind, k=N))/N for _ in range(2000))
    rows = [r for r in res if r["lang"] == lang]
    rv = sum(r["stretches"].get("render_verified", 0) for r in rows); uv = sum(r["stretches"].get("unverified", 0) for r in rows)
    am = sum(r["stretches"].get("render_ambiguous", 0) for r in rows)
    ok = p >= 0.90; npass += ok
    out[lang] = dict(words=N, pymupdf=round(sum(mu_ind)/N*100, 1), unshape=round(p*100, 1), ci=[round(bs[50]*100, 1), round(bs[1949]*100, 1)],
                     render_verified=round(rv/(rv+uv)*100, 1), render_ambiguous=round(am/max(1, rv)*100, 1), pass90=ok,
                     fonts=sorted({f"{v}:{n}" for v, n in fonts}))
    print(lang, json.dumps(out[lang], ensure_ascii=False))
verdict = "PASS" if npass >= 7 else ("FAIL" if npass < 5 else "IN-BETWEEN")
print("scripts >= 90%:", npass, "/10 ->", verdict)
(D/"fresh_scored_20261017.json").write_text(json.dumps({"per_script": out, "n_pass": npass, "verdict": verdict}, indent=1, ensure_ascii=False), encoding="utf-8")
