"""Skeptic check for sec 26: is low agreement caused by Tesseract failing on South Indian scans?
For each scored doc: share of Tesseract's script words found in a held-out Wikipedia vocabulary (word_test/train_<lang>.txt)
vs the same share for FinePDFs' text. If Tesseract reads real words while agreeing little with FinePDFs, the low agreement
is FinePDFs' text, not Tesseract."""
import collections, json, re, statistics
from pathlib import Path
from common import swords, BLOCK
LANG = {"tam_Taml": "ta", "mal_Mlym": "ml", "tel_Telu": "te", "kan_Knda": "kn", "hin_Deva": "hi", "ben_Beng": "bn"}
meta = {m["id"]: m for m in json.loads(Path("ocrpath_meta.json").read_text(encoding="utf-8"))}
T = json.loads(Path("kaggle_out5/tess5.json").read_text(encoding="utf-8"))
rows = [r for r in json.loads(Path("score26_results.json").read_text()) if "agreement" in r]
for cfg, l in LANG.items():
    base = BLOCK[cfg.split("_")[1]]
    vocab = set(swords(Path(f"word_test/train_{l}.txt").read_text(encoding="utf-8"), base))
    t_in, f_in = [], []
    for r in rows:
        if r["cfg"] != cfg: continue
        tw = swords("\n".join(T[r["id"]]["pages"]), base); fw = swords(meta[r["id"]]["text"], base)
        t_in.append(sum(w in vocab for w in tw) / max(1, len(tw))); f_in.append(sum(w in vocab for w in fw) / max(1, len(fw)))
    print(f"{cfg}: docs {len(t_in)} | Tesseract words in Wikipedia vocab: median {statistics.median(t_in):.2f} | "
          f"FinePDFs words in vocab: median {statistics.median(f_in):.2f}")
