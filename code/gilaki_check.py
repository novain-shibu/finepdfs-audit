"""Report section 5: is FinePDFs' glk_Arab ("Gilaki") config real Gilaki, or broken Persian/Arabic PDF text?

Two pre-registered runs, both reproduced by this script (datasets-server rows API, 5 s between calls):
  v1  rules PF / REV / LEG, glk sample seed 31; FAILED its control: LEG fired on 27% of real Gilaki Wikipedia
      articles, because Gilaki writes U+065A (ARABIC VOWEL SIGN SMALL V ABOVE). Kept for the record.
  v2  LEG without U+065A (derived from the Wikipedia control only), FRESH glk sample seed 3131. Reported result.
Rules per document, on Arabic-script characters only (documents with < 200 such characters are skipped):
  PF   Arabic presentation forms (U+FB50-FDFF, U+FE70-FEFF) > 5%      -> shaped glyphs copied as text
  REV  reversed function words outnumber the forward ones, >= 5 hits  -> visual-order (reversed) lines
  LEG  legacy marks/letters (U+0655-065F, U+063B-063F) > 1%           -> legacy Iranian-font mojibake
  corrupted = any rule. PASS: glk corrupted >= 50% AND both Wikipedia controls <= 5%; KILL: any control > 10%.
Output: results/gilaki_<v1|v2>_results.json (document IDs, row offsets, flags and numbers only; no text).
Usage: python gilaki_check.py v2
"""
import collections, json, math, random, sys, time, urllib.request
from pathlib import Path

UA = {"User-Agent": "finepdfs-audit/1.2 (research; github.com/novain-shibu/finepdfs-audit)"}
REV = ["رد", "زا", "هب", "ار", "اب", "هک", "نیا", "نيا", "یاه", "ياه", "تسا"]
FWD = ["در", "از", "به", "را", "با", "که", "این", "اين", "های", "هاي", "است"]
GLK_DOCS, FAS_DOCS = 312000, 1300000


def rows(ds, cfg, off, n=20):
    u = f"https://datasets-server.huggingface.co/rows?dataset={ds}&config={cfg}&split=train&offset={off}&length={n}"
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120))
    time.sleep(5)
    return [(r["row_idx"], r["row"]) for r in d["rows"]]


def arab(c):
    o = ord(c)
    return 0x0600 <= o <= 0x06FF or 0xFB50 <= o <= 0xFDFF or 0xFE70 <= o <= 0xFEFF


def rules(t, version):
    a = [c for c in t if arab(c)]
    n = max(1, len(a))
    pf = sum(1 for c in a if ord(c) >= 0xFB50) / n
    skip = {0x065A} if version == "v2" else set()
    leg = sum(1 for c in a if (0x0655 <= ord(c) <= 0x065F and ord(c) not in skip) or 0x063B <= ord(c) <= 0x063F) / n
    w = t.split()
    r, f = sum(w.count(x) for x in REV), sum(w.count(x) for x in FWD)
    return {"PF": pf > 0.05, "REV": r > f and r >= 5, "LEG": leg > 0.01}, len(a)


def wilson(k, n, z=1.96):
    if not n:
        return [0.0, 0.0]
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def score(rs, version, weight):
    k = n = tk = tt = 0
    per = collections.Counter()
    docs = []
    for idx, r in rs:
        ru, na = rules(r["text"], version)
        if na < 200:
            continue
        bad = any(ru.values())
        n += 1; k += bad; per.update(x for x, v in ru.items() if v)
        w = r.get("token_count", 1) if weight else 1
        tt += w; tk += w * bad
        docs.append({"row": idx, "id": r.get("id"), "extractor": r.get("extractor"), "lid": r.get("full_doc_lid"),
                     "lid_score": r.get("full_doc_lid_score"), "token_count": r.get("token_count"),
                     "arabic_chars": na, **ru})
    return {"n": n, "corrupted": k, "share": round(k / max(1, n), 3), "ci95": wilson(k, n),
            "token_share": round(tk / max(1, tt), 3), "per_rule": dict(per)}, docs


def main(version):
    rnd = random.Random(31 if version == "v1" else 3131)
    glk = []
    for off in sorted(rnd.sample(range(GLK_DOCS), 5)):
        glk += rows("HuggingFaceFW/finepdfs", "glk_Arab", off)
    res, out = {}, {}
    res["glk_Arab"], out["glk_Arab"] = score(glk, version, True)
    res["glk_Arab"]["extractor"] = dict(collections.Counter(r["extractor"] for _, r in glk))
    res["glk_Arab"]["doc_lid"] = dict(collections.Counter(r["full_doc_lid"] for _, r in glk).most_common(6))
    if version == "v1":
        fas = []
        for off in sorted(rnd.sample(range(FAS_DOCS), 2)):
            fas += rows("HuggingFaceFW/finepdfs", "fas_Arab", off)
        res["fas_Arab"], out["fas_Arab"] = score(fas, version, True)  # reported, not a control
    # Gilaki Wikipedia control: 5 x 100 articles (most are stubs < 200 Arabic chars and are skipped)
    wglk = []
    for off in (0, 2000, 4000, 6000, 8000):
        wglk += rows("wikimedia/wikipedia", "20231101.glk", off, 100)
    wfa = rows("wikimedia/wikipedia", "20231101.fa", 1000 if version == "v1" else 3000, 20 if version == "v1" else 40)
    res["wiki_glk"], _ = score(wglk, version, False)
    res["wiki_fa"], _ = score(wfa, version, False)
    ctl = max(res["wiki_glk"]["share"], res["wiki_fa"]["share"])
    res["verdict"] = ("KILL (control > 10%)" if ctl > 0.10 else
                      "PASS" if res["glk_Arab"]["share"] >= 0.5 and ctl <= 0.05 else "PARTIAL")
    print(json.dumps(res, indent=1, ensure_ascii=False))
    p = Path(__file__).resolve().parent.parent / "results" / f"gilaki_{version}_results.json"
    p.write_text(json.dumps({"version": version, "results": res, "docs": out}, indent=1, ensure_ascii=False),
                 encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "v2")
