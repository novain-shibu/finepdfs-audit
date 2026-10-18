"""indic_pdf_check: can a screen reader (or search, or an AI) read this Indian-language PDF?

Reads the PDF's own text layer (what assistive technology and text extractors see) and reports, per PDF:
  NO_TEXT  - fewer than 50 words in an Indian script: a scan/image or text without Unicode (needs OCR + tagging)
  BROKEN   - more than 5% of words are impossible spellings (typical of Microsoft Word's PDF export of Indic text)
  OK       - text layer looks readable
plus the dominant script, word count, broken-word share, producer/creator and whether the PDF is tagged.
Usage: python indic_pdf_check.py file1.pdf [file2.pdf ...] [--json]
Local only; reads files, changes nothing. Needs: pymupdf. Uses validity.py (finepdfs-audit) for the spelling rules.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import pymupdf
from validity import scan_text, BASE

SCRIPTS = [s for s in BASE]  # Deva Beng Guru Gujr Orya Taml Telu Knda Mlym (+ others validity.py knows)


def check(path):
    doc = pymupdf.open(path)
    text = "".join(page.get_text() for page in doc)
    best = max(((s,) + scan_text(text, s) for s in SCRIPTS), key=lambda t: t[1])
    script, words, bad = best
    share = bad / words if words else 0.0
    verdict = "NO_TEXT" if words < 50 else ("BROKEN" if share > 0.05 else "OK")
    md = doc.metadata or {}
    return {"file": Path(path).name, "verdict": verdict, "script": script if words else None, "words": words,
            "broken_share": round(share, 4), "pages": len(doc), "tagged": bool(doc.pdf_catalog() and
            "StructTreeRoot" in doc.xref_object(doc.pdf_catalog())), "producer": md.get("producer", ""),
            "creator": md.get("creator", "")}


def main(argv):
    as_json = "--json" in argv
    files = [a for a in argv if a != "--json"]
    rows = []
    for f in files:
        try:
            rows.append(check(f))
        except Exception as e:
            rows.append({"file": Path(f).name, "verdict": "ERROR", "error": repr(e)[:100]})
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for r in rows:
            if r["verdict"] == "ERROR":
                print(f"{r['file']}: ERROR {r['error']}"); continue
            print(f"{r['file']}: {r['verdict']:7s} script={r['script']} words={r['words']} broken={r['broken_share']:.1%} "
                  f"tagged={r['tagged']} creator={r['creator'][:30]!r}")
        from collections import Counter
        c = Counter(r["verdict"] for r in rows)
        print(f"-- {len(rows)} PDFs: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))


if __name__ == "__main__":
    main(sys.argv[1:])
