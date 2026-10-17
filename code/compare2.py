import sys, collections, random, json
from pathlib import Path
sys.path.insert(0, r".")
from common import words
import pymupdf
D = Path(r"word_test"); rnd = random.Random(0)
def logrows(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.startswith("{")]
R = {3: logrows(D.parent/"fresh2_v3.log"), 4: logrows(D.parent/"fresh2_v4.log")}
allpairs, out = [], {}
for lang in "hi bn ta ml te kn gu pa or si".split():
    pairs = []; mu = []
    for v in "abc":
        t = D/f"fresh2_{lang}_{v}.txt"; g = collections.Counter(words(t.read_text(encoding="utf-8")))
        if not g: continue
        c3 = collections.Counter(words((D/f"fresh2_{lang}_{v}.unshaped3.txt").read_text(encoding="utf-8")))
        c4 = collections.Counter(words((D/f"fresh2_{lang}_{v}.unshaped4.txt").read_text(encoding="utf-8")))
        m = collections.Counter(words("".join(p.get_text() for p in pymupdf.open(D/f"fresh2_{lang}_{v}.pdf"))))
        for w, n in g.items():
            for k in range(n):
                pairs.append((int(k < c3[w]), int(k < c4[w]))); mu.append(int(k < m[w]))
    N = len(pairs); a = sum(p[0] for p in pairs)/N; b = sum(p[1] for p in pairs)/N
    bs = sorted(sum(p[1]-p[0] for p in rnd.choices(pairs, k=N))/N for _ in range(2000))
    b4 = sorted(sum(p[1] for p in rnd.choices(pairs, k=N))/N for _ in range(2000))
    rows = {k: [r for r in R[k] if r["lang"] == lang] for k in R}
    def share(k, key):
        rv = sum(r["stretches"].get("render_verified", 0) for r in rows[k]); uv = sum(r["stretches"].get("unverified", 0) for r in rows[k]); am = sum(r["stretches"].get("render_ambiguous", 0) for r in rows[k])
        return round(100*rv/(rv+uv), 1) if key == "rv" else round(100*am/max(1, rv), 1)
    out[lang] = dict(words=N, pymupdf=round(100*sum(mu)/N, 1), v3=round(100*a, 1), v4=round(100*b, 1), v4_ci=[round(100*b4[50], 1), round(100*b4[1949], 1)],
                     diff=round(100*(b-a), 2), diff_ci=[round(100*bs[50], 2), round(100*bs[1949], 2)], rv3=share(3, "rv"), rv4=share(4, "rv"), amb4=share(4, "am"))
    print(lang, out[lang]); allpairs += pairs
N = len(allpairs); d = sum(p[1]-p[0] for p in allpairs)/N
bs = sorted(sum(p[1]-p[0] for p in rnd.choices(allpairs, k=N))/N for _ in range(2000))
drop = [l for l, o in out.items() if o["diff"] < -1.0]
v = "PASS" if bs[50] > 0 and not drop else ("KILL" if bs[50] <= 0 <= bs[1949] else "FAIL(drop)")
summary = dict(words=N, v3=round(100*sum(p[0] for p in allpairs)/N, 2), v4=round(100*sum(p[1] for p in allpairs)/N, 2), diff=round(100*d, 2), diff_ci=[round(100*bs[50], 2), round(100*bs[1949], 2)], drops=drop, verdict=v)
print("ALL", summary)
(D/"fresh2_scored_20261017.json").write_text(json.dumps({"per_script": out, "pooled": summary}, indent=1), encoding="utf-8")
