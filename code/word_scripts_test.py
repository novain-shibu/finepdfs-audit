"""Report section 8: does Microsoft Word's 'Save as PDF' keep the text of each script readable?
For each script: Wikipedia text (wikimedia/wikipedia 20231101; offset 1000 x 3 rows, or 100 x 30 for bo/am/dv), saved as
PDF by Word (word_var.ps1, Windows only, default Windows font per script), read back with PyMuPDF and pdfminer.
Metrics: exact-word recall and letter / letter-3-gram recall vs the source. Texts and PDFs stay in a temp folder
(Wikipedia text is not redistributed). Usage (Windows with Word): python word_scripts_test.py"""
import collections, difflib, json, os, re, subprocess, tempfile, time, unicodedata, urllib.request
from pathlib import Path
import pymupdf
from pdfminer.high_level import extract_text
UA = {"User-Agent": "finepdfs-audit/1.4 (research; github.com/novain-shibu/finepdfs-audit)"}
FONTS = {"en": "Calibri", "ru": "Calibri", "he": "Segoe UI", "ka": "Segoe UI", "ar": "Arial", "fa": "Arial", "ur": "Arial",
         "km": "Leelawadee UI", "lo": "Leelawadee UI", "my": "Myanmar Text", "bo": "Microsoft Himalaya", "am": "Ebrima",
         "dv": "MV Boli", "jv": "Javanese Text"}
LONG = {"bo", "am", "dv"}
HERE = Path(__file__).resolve().parent


def doc_text(t):
    paras = [unicodedata.normalize("NFC", p.strip()) for p in t.split("\n") if len(p.strip()) > 60][:12]
    return "\n".join(paras)[:4000]


def words(t):
    return [w for w in re.split(r"[\s।॥.,;:!?()\[\]\"'“”‘’\-–—/،؛؟«»۔་།]+", unicodedata.normalize("NFC", t)) if w]


def letters(t):
    return [c for c in unicodedata.normalize("NFC", t) if not c.isspace() and unicodedata.category(c)[0] in "LM"]


def main():
    tmp = Path(tempfile.mkdtemp()); out = {}
    for lang, font in FONTS.items():
        off, n = (100, 30) if lang in LONG else (1000, 3)
        u = f"https://datasets-server.huggingface.co/rows?dataset=wikimedia/wikipedia&config=20231101.{lang}&split=train&offset={off}&length={n}"
        text = doc_text("\n".join(r["row"]["text"] for r in json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120))["rows"]))
        time.sleep(5)
        (HERE / f"_w_{lang}.txt").write_text(text, encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "word_var.ps1"),
                        "-in", f"_w_{lang}.txt", "-out", f"_w_{lang}.pdf", "-font", font], check=True)
        pdf = HERE / f"_w_{lang}.pdf"
        mu = "".join(p.get_text() for p in pymupdf.open(pdf)); pm = extract_text(str(pdf))
        g = collections.Counter(words(text))
        rec = lambda t: sum(min(k, collections.Counter(words(t))[w]) for w, k in g.items()) / max(1, sum(g.values()))
        a, b = letters(text), letters(mu)
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        g3 = collections.Counter("".join(a[i:i + 3]) for i in range(len(a) - 2)); m3 = collections.Counter("".join(b[i:i + 3]) for i in range(len(b) - 2))
        out[lang] = {"font": font, "words": sum(g.values()), "word_recall_pymupdf": round(rec(mu), 4), "word_recall_pdfminer": round(rec(pm), 4),
                     "letter_recall": round(sum(x.size for x in sm.get_matching_blocks()) / max(1, len(a)), 4),
                     "letter3_recall": round(sum(min(k, m3[x]) for x, k in g3.items()) / max(1, sum(g3.values())), 4)}
        for f in (HERE / f"_w_{lang}.txt", pdf):
            f.replace(tmp / f.name)
        print(lang, out[lang], flush=True)
    (HERE.parent / "results" / "word_scripts_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
