"""Fair (OCR-favouring) rescoring, added after seeing that Tesseract appends ZWNJ after viramas: ZWNJ/ZWJ removed from
truth, OCR and v4 alike; reported overall and by style (a 12pt Regular, b 16pt Bold, c 10pt Italic)."""
import collections, json, random
from pathlib import Path
from common import words
D = Path("word_test"); rnd = random.Random(0)
R = json.loads(Path("kaggle_out3/ocr_results.json").read_text(encoding="utf-8"))
zw = lambda t: t.replace("‌", "").replace("‍", "")
res = {}
for styles in ("ab", "c", "abc"):
    allp, per = [], {}
    for lang in "hi bn ta ml te kn gu pa or si".split():
        pairs = []
        for v in styles:
            name = f"fresh2_{lang}_{v}.pdf"
            g = collections.Counter(words(zw((D/f"fresh2_{lang}_{v}.txt").read_text(encoding="utf-8"))))
            if not g or name not in R["files"]: continue
            f = R["files"][name]
            co = collections.Counter(words(zw("\n".join(f["pages"][k] for k in sorted(f["pages"], key=int)))))
            c4 = collections.Counter(words(zw((D/f"fresh2_{lang}_{v}.unshaped4.txt").read_text(encoding="utf-8"))))
            for w, n in g.items():
                pairs += [(int(k < co[w]), int(k < c4[w])) for k in range(n)]
        if pairs:
            N = len(pairs); per[lang] = (N, round(100*sum(p[0] for p in pairs)/N, 1), round(100*sum(p[1] for p in pairs)/N, 1))
        allp += pairs
    N = len(allp); bs = sorted(sum(p[1]-p[0] for p in rnd.choices(allp, k=N))/N for _ in range(2000))
    res[styles] = dict(per_script=per, words=N, ocr=round(100*sum(p[0] for p in allp)/N, 2), v4=round(100*sum(p[1] for p in allp)/N, 2), v4_minus_ocr_ci=[round(100*bs[50], 2), round(100*bs[1949], 2)])
    print(styles, {k: v for k, v in res[styles].items() if k != "per_script"}); print("   (words, OCR, v4):", per)
Path("word_test/ocr3_fair_scored_20261017.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
