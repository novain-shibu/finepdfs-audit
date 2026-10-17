"""FINDINGS sec 28 scorer (rules pre-registered). Compares FinePDFs' stored text (first N pages via page_ends) with free
Tesseract on the same PDF pages (N = pages OCR'd, max 10).
- guj ory pan sin mar npi: word agreement, FABRICATED if < 0.25
- tha khm mya: character 3-gram agreement, FABRICATED if < 0.558
Secondary: 3-gram agreement for all, number agreement (alignment). Scale: config rows x token share x flagged rate."""
import collections, json, math, re, statistics, unicodedata
from pathlib import Path
from calib_cgram import BLOCKS, cagree

NOSPACE = {"tha_Thai", "khm_Khmr", "mya_Mymr"}
ROWS = {"guj_Gujr": 84057, "ory_Orya": 5745, "pan_Guru": 14727, "sin_Sinh": 20112, "mar_Deva": 185544,
        "npi_Deva": 181691, "tha_Thai": 2516013, "khm_Khmr": 23142, "mya_Mymr": 29171}
CARD_TOKENS = {"tha_Thai": 17.56e9}


def swords(t, script):
    lo, hi = BLOCKS[script]
    t = unicodedata.normalize("NFC", t).replace("‌", "").replace("‍", "")
    return [w for w in re.findall(f"[\\u{lo:04x}-\\u{hi:04x}]+", t) if len(w) >= 2]


def nums(t):
    t = "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in t)
    return re.findall(r"\d{2,}", t)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - h) / d), min(1.0, (c + h) / d)


def main():
    M = json.loads(Path("census_meta.json").read_text(encoding="utf-8"))
    T = json.loads(Path("kaggle_out6/tess6.json").read_text(encoding="utf-8"))
    res = collections.defaultdict(list); excl = collections.Counter(); rows = []
    for d in M["docs"]:
        t = T.get(d["id"])
        if not t or "pages" not in t:
            excl[(d["cfg"], "no ocr")] += 1; continue
        cfg = d["cfg"]; script = cfg.split("_")[1]; n = len(t["pages"])
        pe = d.get("page_ends") or []
        cut = pe[min(n, len(pe)) - 1] if pe else len(d["text"])
        fin = d["text"][:cut]; tess = "\n".join(t["pages"])
        cg = cagree(fin, tess, script)
        fw, tw = swords(fin, script), collections.Counter(swords(tess, script))
        wa = (sum(min(k, tw[w]) for w, k in collections.Counter(fw).items()) / len(fw)) if len(fw) >= 30 and sum(tw.values()) >= 30 else None
        fn, tn = nums(fin), collections.Counter(nums(tess))
        na = (sum(min(k, tn[x]) for x, k in collections.Counter(fn).items()) / len(fn)) if len(fn) >= 5 and sum(tn.values()) >= 5 else None
        primary = cg if cfg in NOSPACE else wa
        if primary is None:
            excl[(cfg, "too little text")] += 1; continue
        flag = primary < (0.558 if cfg in NOSPACE else 0.25)
        res[cfg].append((flag, primary, cg, na, d["tokens"]))
        rows.append({"id": d["id"], "cfg": cfg, "primary": round(primary, 3), "cgram": cg and round(cg, 3), "numbers": na and round(na, 3), "flag": flag})
    print("config   | scored | flagged (95% CI)     | median primary | median 3-gram | median numbers | excluded")
    tot_tok = flag_tok = lo_tok = hi_tok = 0
    for cfg in ROWS:
        v = res.get(cfg, [])
        k = sum(f for f, *_ in v); a, b = wilson(k, len(v))
        med = lambda xs: round(statistics.median(xs), 3) if xs else None
        ex = sum(c for (cf, _), c in excl.items() if cf == cfg)
        print(f"{cfg} | {len(v):6d} | {k:2d}/{len(v):<2d} ({a:.0%}-{b:.0%})       | {med([p for _, p, *_ in v])} | "
              f"{med([c for _, _, c, *_ in v if c is not None])} | {med([x for *_, x, _ in v if x is not None])} | {ex}")
        pages = M["pages"][cfg]; tt = sum(r["tokens"] for r in pages); rt = sum(r["tokens"] for r in pages if r["extractor"] == "rolmOCR")
        total = CARD_TOKENS.get(cfg, ROWS[cfg] * tt / max(1, len(pages)))
        ocr_tok = total * rt / max(1, tt)
        if v:
            flag_tok += ocr_tok * k / len(v); lo_tok += ocr_tok * a; hi_tok += ocr_tok * b
        tot_tok += ocr_tok
        print(f"           tokens: total ~{total/1e9:.2f}B, rolmOCR share {rt/max(1,tt):.0%} -> {ocr_tok/1e9:.2f}B; flagged-weighted ~{(ocr_tok*k/len(v) if v else 0)/1e9:.2f}B")
    print(f"CENSUS TOTAL rolmOCR-path tokens ~{tot_tok/1e9:.1f}B; flagged-weighted ~{flag_tok/1e9:.1f}B (CI {lo_tok/1e9:.1f}-{hi_tok/1e9:.1f}B)")
    Path("census_results.json").write_text(json.dumps({"rows": rows, "excluded": {f"{a}|{b}": c for (a, b), c in excl.items()}}, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
