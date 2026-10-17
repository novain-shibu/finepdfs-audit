"""Report section 6: broken text of big languages is filed under small-language configs ("exile"), and some small-language
configs are mostly broken text in their own language. Both runs are reproduced by this script (datasets-server rows API,
5 s between calls; no text is saved, only document IDs, row offsets, flags and numbers).

  screen   all 82 non-Latin configs with >= 1,000 docs, 20 rows each at one random offset (seed 3232); anp_Deva 5 x 20.
  retest   the screen hits on FRESH samples, 5 x 20 rows each (seed 3333), with clean Wikipedia controls. Reported result.

Per document (>= 200 letters): MISMATCH = < 50% of letters in the config's own script. CORRUPT = for Arabic script:
presentation forms (U+FB50-FDFF, U+FE70-FEFF) > 5%, or reversed function words outnumber forward ones (>= 5 hits), or
legacy-font letters U+063B-063F > 0.5% (they occur 0 times in 2.1M characters of Wikipedia in Kashmiri, Uyghur, Gilaki,
Persian, Arabic, Urdu, Sorani, Sindhi and Pashto); for Brahmic scripts: > 5% orthographically impossible words
(validity.py, >= 50 words). BAD = mismatch or corrupt.
CONFIRMED config: BAD >= 50%, 95% CI lower bound >= 30%, and its script's Wikipedia controls <= 5%.
Usage: python exile_check.py retest   (or: screen)
"""
import collections, json, random, statistics, sys, time, unicodedata, urllib.request
from pathlib import Path

from validity import scan_text
from gilaki_check import REV, FWD, arab, wilson

UA = {"User-Agent": "finepdfs-audit/1.3 (research; github.com/novain-shibu/finepdfs-audit)"}
SC = {"Arab": ("ARABIC",), "Deva": ("DEVANAGARI",), "Beng": ("BENGALI",), "Cyrl": ("CYRILLIC",), "Ethi": ("ETHIOPIC",),
      "Tibt": ("TIBETAN",), "Hani": ("CJK",), "Thaa": ("THAANA",), "Grek": ("GREEK",), "Gujr": ("GUJARATI",),
      "Hebr": ("HEBREW",), "Armn": ("ARMENIAN",), "Cans": ("CANADIAN",), "Jpan": ("CJK", "HIRAGANA", "KATAKANA"),
      "Knda": ("KANNADA",), "Geor": ("GEORGIAN",), "Khmr": ("KHMER",), "Hang": ("HANGUL", "CJK"), "Laoo": ("LAO",),
      "Mlym": ("MALAYALAM",), "Mymr": ("MYANMAR",), "Orya": ("ORIYA",), "Guru": ("GURMUKHI",), "Sinh": ("SINHALA",),
      "Taml": ("TAMIL",), "Telu": ("TELUGU",), "Thai": ("THAI",)}
BRAHMIC = {"Deva", "Beng", "Guru", "Gujr", "Orya", "Taml", "Telu", "Knda", "Mlym", "Sinh"}
RETEST = {"bcc_Arab": 111724, "glk_Arab": 313867, "kas_Arab": 21699, "acm_Arab": 8597, "uig_Arab": 2889,
          "asm_Beng": 1551, "pan_Guru": 14727, "kas_Deva": 4309, "anp_Deva": 129557}
WIKI = [("ks", "Arab", 5000), ("ug", "Arab", 5000), ("ar", "Arab", 5000), ("fa", "Arab", 5000), ("glk", "Arab", 5000),
        ("as", "Beng", 5000), ("pa", "Guru", 9000), ("hi", "Deva", 5000),
        ("ks", "Arab", 0), ("ks", "Arab", 3000), ("ks", "Arab", 4000)]  # ks has 4,307 articles: offsets 0/3000/4000 are the
                                                                        # independent control (rule derived on 1000/2000)
FP = "https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config={}&split=train&offset={}&length={}"
WK = "https://datasets-server.huggingface.co/rows?dataset=wikimedia/wikipedia&config=20231101.{}&split=train&offset={}&length=100"


def get(u):
    for _ in range(2):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120))
            time.sleep(5)
            return d["rows"]
        except Exception as e:
            print("retry", repr(e)[:60], flush=True)
            time.sleep(30)
    return []


def judge(t, script):
    letters = [c for c in t[:50000] if c.isalpha()]
    if len(letters) < 200:
        return None
    own = sum(1 for c in letters if unicodedata.name(c, "").startswith(SC[script])) / len(letters)
    r = {"own": round(own, 3), "mismatch": own < 0.5}
    if script == "Arab":
        a = [c for c in t if arab(c)]
        n = max(1, len(a))
        w = t.split()
        rv, fw = sum(w.count(x) for x in REV), sum(w.count(x) for x in FWD)
        r.update(PF=sum(1 for c in a if ord(c) >= 0xFB50) / n > 0.05, REV=rv > fw and rv >= 5,
                 LEG3=sum(1 for c in a if 0x063B <= ord(c) <= 0x063F) / n > 0.005)
        r["corrupt"] = len(a) >= 200 and (r["PF"] or r["REV"] or r["LEG3"])
    elif script in BRAHMIC:
        wd, b = scan_text(t, script)
        r["invalid"] = round(b / max(1, wd), 4)
        r["corrupt"] = wd >= 50 and b / wd > 0.05
    else:
        r["corrupt"] = False
    r["bad"] = bool(r["mismatch"] or r["corrupt"])
    return r


def summarise(cfg, size, rows):
    script = cfg.split("_")[1]
    js = []
    for x in rows:
        if not x["row"].get("text"):
            continue
        j = judge(x["row"]["text"], script)
        if j:
            js.append({"row": x["row_idx"], "id": x["row"]["id"], "extractor": x["row"]["extractor"],
                       "lid": x["row"]["full_doc_lid"], "lid_score": x["row"]["full_doc_lid_score"],
                       "tokens": x["row"]["token_count"], **j})
    n, k = len(js), sum(j["bad"] for j in js)
    tt, tk = sum(j["tokens"] for j in js), sum(j["tokens"] for j in js if j["bad"])
    mt = statistics.mean([x["row"]["token_count"] for x in rows]) if rows else 0
    return {"docs": size, "fetched": len(rows), "n": n, "bad": k, "share": round(k / max(1, n), 3), "ci95": wilson(k, n),
            "mismatch": sum(j["mismatch"] for j in js), "corrupt": sum(bool(j["corrupt"]) for j in js),
            "token_share": round(tk / max(1, tt), 3), "mean_tokens": round(mt),
            "est_bad_tokens_B": round(size * mt * tk / max(1, tt) / 1e9, 3),
            "extractor": dict(collections.Counter(x["row"]["extractor"] for x in rows))}, js


def screen():
    cfgs = json.loads((Path(__file__).resolve().parent.parent / "results" / "nonlatin_configs.json").read_text())
    rnd = random.Random(3232)
    anp = sorted(rnd.sample(range(cfgs["anp_Deva"] - 20), 5))
    R, D = {}, {}
    for cfg, size in sorted(cfgs.items()):
        offs = anp if cfg == "anp_Deva" else [rnd.randrange(0, size - 20)]
        rows = [x for o in offs for x in get(FP.format(cfg, o, 20))]
        R[cfg], D[cfg] = summarise(cfg, size, rows)
        print(cfg, json.dumps(R[cfg]), flush=True)
    return {"results": R, "docs": D}


def retest():
    rnd = random.Random(3333)
    R, D, C = {}, {}, {}
    for cfg, size in RETEST.items():
        rows = [x for o in sorted(rnd.sample(range(size - 20), 5)) for x in get(FP.format(cfg, o, 20))]
        R[cfg], D[cfg] = summarise(cfg, size, rows)
        print(cfg, json.dumps(R[cfg]), flush=True)
    for lang, script, off in WIKI:
        js = [j for j in (judge(x["row"]["text"], script) for x in get(WK.format(lang, off))) if j]
        k = sum(j["bad"] for j in js)
        C[f"{lang}@{off}"] = {"n": len(js), "bad": k, "share": round(k / max(1, len(js)), 3), "ci95": wilson(k, len(js))}
        print("wiki", lang, off, json.dumps(C[f"{lang}@{off}"]), flush=True)
    return {"results": R, "controls": C, "docs": D}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "retest"
    out = screen() if mode == "screen" else retest()
    p = Path(__file__).resolve().parent.parent / "results" / f"exile_{mode}_results.json"
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
