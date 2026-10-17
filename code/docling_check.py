"""Re-extract the 24 originals with the CURRENT docling-parse and compare to FinePDFs' docling text and PyMuPDF.
Question: is the Docling-only scrambling (6/24 cases) still present in today's parser?"""
import json, sys
sys.path.insert(0, ".")
from validity import scan_text
from docling_parse.pdf_parser import DoclingPdfParser
from docling_core.types.doc.page import TextCellUnit

SCRIPT = {"hin": "Deva", "ben": "Beng", "tam": "Taml", "mal": "Mlym"}
rows = [json.loads(l) for l in open("originals.log", encoding="utf-8") if l.startswith("{")]
parser = DoclingPdfParser()
out = []
for r in rows:
    import re
    p = "originals/" + re.sub(r"[^A-Za-z0-9-]", "_", r["id"]).strip("_") + ".pdf"
    try:
        doc = parser.load(path_or_stream=p)
        parts = []
        for _, page in doc.iterate_pages():
            for cell in page.iterate_cells(unit_type=TextCellUnit.LINE):
                parts.append(cell.text)
        t = "\n".join(parts)
        w, b = scan_text(t, SCRIPT[r["cfg"][:3]])
        cur = b / w if w else None
    except Exception as e:
        cur = None; print("ERR", p, repr(e)[:120])
    rec = {"cfg": r["cfg"], "finepdfs": r["finepdfs_invalid"], "pymupdf": r["pymupdf_invalid"], "docling_now": cur,
           "producer": r["producer"][:30], "fonts": [f.split("+")[-1] for f in r["fonts"]][:6]}
    out.append(rec)
    flag = "DOCLING-ONLY" if r["finepdfs_invalid"] - r["pymupdf_invalid"] > 0.05 else ""
    print(f"{r['cfg'][:3]} finepdfs {r['finepdfs_invalid']:5.1%} pymupdf {r['pymupdf_invalid']:5.1%} docling-parse now {cur if cur is None else format(cur, '5.1%')}  {flag}")
json.dump(out, open("docling_check.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
