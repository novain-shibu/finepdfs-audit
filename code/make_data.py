"""Provenance (skeptic2 fix 5): regenerate every text file used by the Word tests from wikimedia/wikipedia (20231101, CC-BY-SA)
via the datasets-server rows API, paced 5 s.  train_<lang>.txt = offset 3000, 60 rows (syllable inventory only);
gt_<lang>.txt = offset 500, 5 rows (bench test); fresh_<lang>_<a|b|c>.txt = offsets 8000/12000/16000, 5 rows (fresh test).
Paragraphs > 60 chars, NFC, first 12 paragraphs, cut at 4000 chars (gt/fresh)."""
import json, sys, time, unicodedata, urllib.request
from pathlib import Path
UA = {"User-Agent": "invent7-validity-check/0.1 (research; github.com/novain-shibu)"}
LANGS = ["hi", "bn", "ta", "ml", "te", "kn", "gu", "pa", "or", "si"]


def rows(lang, off, n):
    url = f"https://datasets-server.huggingface.co/rows?dataset=wikimedia/wikipedia&config=20231101.{lang}&split=train&offset={off}&length={n}"
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120))
    time.sleep(5)
    return "\n".join(r["row"]["text"] for r in d["rows"])


def doc_text(t):
    paras = [unicodedata.normalize("NFC", p.strip()) for p in t.split("\n") if len(p.strip()) > 60][:12]
    return "\n".join(paras)[:4000]


def main(which):
    out = Path("word_test")
    for lang in LANGS:
        if which in ("all", "train"):
            (out / f"train_{lang}.txt").write_text(unicodedata.normalize("NFC", rows(lang, 3000, 60)), encoding="utf-8")
        if which in ("all", "gt"):
            (out / f"gt_{lang}.txt").write_text(doc_text(rows(lang, 500, 5)), encoding="utf-8")
        if which in ("all", "fresh"):
            for tag, off in (("a", 8000), ("b", 12000), ("c", 16000)):
                (out / f"fresh_{lang}_{tag}.txt").write_text(doc_text(rows(lang, off, 5)), encoding="utf-8")
        print(lang, "done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fresh")
