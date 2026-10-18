"""Report section 8, control: is the damage in Word's export, or in the font or the extractor?
Same text and SAME font, two PDF producers: Word for Microsoft 365 (Save as PDF, word_var.ps1) and Microsoft Edge
(headless --print-to-pdf of an HTML page using that font). Both read back with the same PyMuPDF and pdfminer.
Letter-level recall, precision and F1 are the fair cross-producer metrics (word-level also penalises line breaks that split words).
Inputs: the section 3/8 test texts (Wikipedia, not redistributed) given as <lang>=<text file>=<Word PDF>.
Usage (Windows with Word + Edge):
  python word_vs_edge_test.py ml=fresh2_ml_a.txt=fresh2_ml_a.pdf hi=fresh2_hi_a.txt=fresh2_hi_a.pdf km=glob_km.txt=glob_km.pdf my=glob_my.txt=glob_my.pdf
"""
import collections, difflib, html, json, subprocess, sys, tempfile, time
from pathlib import Path
import pymupdf
from pdfminer.high_level import extract_text
from word_scripts_test import words, letters

FONT = {"ml": "Nirmala UI", "hi": "Nirmala UI", "km": "Leelawadee UI", "my": "Myanmar Text"}
EDGE = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if Path(p).exists())


def score(text, pdf):
    mu = "".join(p.get_text() for p in pymupdf.open(pdf)); pm = extract_text(str(pdf))
    g = collections.Counter(words(text))
    rec = lambda t: sum(min(k, collections.Counter(words(t))[w]) for w, k in g.items()) / max(1, sum(g.values()))
    a, b = letters(text), letters(mu)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = sum(x.size for x in sm.get_matching_blocks())
    r, pr = m / max(1, len(a)), m / max(1, len(b))  # letters kept (recall) / extracted letters that match (precision)
    return {"words_pymupdf": round(rec(mu), 4), "words_pdfminer": round(rec(pm), 4), "letters": round(r, 4),
            "letters_recall": round(r, 3), "letters_precision": round(pr, 3),
            "letters_f1": round(2 * r * pr / max(1e-9, r + pr), 3)}


def main(args):
    tmp = Path(tempfile.mkdtemp()); out = {}
    for a in args:
        lang, txt, wpdf = a.split("=")
        text = Path(txt).read_text(encoding="utf-8")
        page = tmp / f"{lang}.html"
        body = "".join(f"<p>{html.escape(p)}</p>" for p in text.split("\n") if p.strip())
        page.write_text(f"<!doctype html><meta charset='utf-8'><style>body{{font-family:'{FONT[lang]}';font-size:12pt;margin:2cm}}</style>{body}", encoding="utf-8")
        epdf = tmp / f"{lang}.pdf"
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={epdf}", page.as_uri()], check=False)
        time.sleep(3)
        out[lang] = {"font": FONT[lang], "word": score(text, wpdf), "edge": score(text, epdf)}
        print(lang, out[lang], flush=True)
    (Path(__file__).resolve().parent.parent / "results" / "word_vs_edge_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
