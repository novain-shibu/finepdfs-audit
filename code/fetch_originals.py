"""Fetch the ORIGINAL PDFs of flagged docling documents from Common Crawl (public archive, free; one byte-range request per
document, sequential, 3 s apart). Reads one gzip WARC member starting at FinePDFs' recorded offset and stops at its end.
PDFs are stored locally only (originals/, never redistributed). Then compares, per document:
  FinePDFs docling text  vs  pdfminer text  vs  PyMuPDF text  (same orthographic check)  -> PDF text layer or Docling at fault?
and lists the embedded fonts (which producers/fonts cause the corruption).
"""
import io, json, os, re, sys, time, urllib.error, urllib.request, zlib
from pathlib import Path
sys.path.insert(0, ".")
from validity import scan_text

PER_LANG, OUT = int(os.environ.get("PER_LANG", "6")), Path("originals")
UA = {"User-Agent": "invent7-validity-check/0.1 (research; github.com/novain-shibu)"}


def warc_payload(file_path, offset):
    req = urllib.request.Request("https://data.commoncrawl.org/" + file_path,
                                 headers={**UA, "Range": f"bytes={offset}-{offset + 60_000_000}"})
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    buf = io.BytesIO()
    with urllib.request.urlopen(req, timeout=120) as r:
        while not d.eof:
            chunk = r.read(65536)
            if not chunk:
                break
            buf.write(d.decompress(chunk))
    raw = buf.getvalue()
    # WARC headers \r\n\r\n HTTP headers \r\n\r\n body
    i = raw.find(b"\r\n\r\n"); j = raw.find(b"\r\n\r\n", i + 4)
    return raw[j + 4:] if raw[:4] == b"WARC" and j > 0 else b""


def main():
    OUT.mkdir(exist_ok=True)
    results = []
    for cfg, s in [("hin_Deva", "Deva"), ("ben_Beng", "Beng"), ("tam_Taml", "Taml"), ("mal_Mlym", "Mlym")]:
        rows = json.load(open(f"sample/{cfg}.json", encoding="utf-8"))
        fl = []
        for r in rows:
            if r["extractor"] != "docling" or r["is_truncated"]:
                continue
            w, b = scan_text(r["text"], s)
            if w >= 100 and b / w > 0.05:
                fl.append((r, w, b))
        for r, w, b in fl[:PER_LANG]:
            rec = {"cfg": cfg, "id": r["id"], "url": r["url"], "finepdfs_invalid": b / w}
            try:
                try:
                    pdf = warc_payload(r["file_path"], r["offset"])
                except urllib.error.HTTPError as e:
                    if e.code != 503:
                        raise
                    time.sleep(30)                      # Common Crawl busy: one polite retry, then give up
                    pdf = warc_payload(r["file_path"], r["offset"])
                time.sleep(5)
                if not pdf.startswith(b"%PDF"):
                    rec["error"] = "payload is not a PDF"; results.append(rec); continue
                p = OUT / (re.sub(r"[^A-Za-z0-9-]", "_", r["id"]).strip("_") + ".pdf")
                p.write_bytes(pdf)
                rec["bytes"] = len(pdf)
                import pymupdf
                from pdfminer.high_level import extract_text
                doc = pymupdf.open(p)
                t_mu = "".join(pg.get_text() for pg in doc)
                fonts = sorted({f[3] for pg in doc for f in pg.get_fonts(full=True)})
                rec["producer"] = (doc.metadata or {}).get("producer", "")
                rec["creator"] = (doc.metadata or {}).get("creator", "")
                rec["fonts"] = fonts[:12]
                try:
                    t_pm = extract_text(str(p))
                except Exception as e:
                    t_pm = ""
                for name, t in (("pymupdf", t_mu), ("pdfminer", t_pm)):
                    w2, b2 = scan_text(t, s)
                    rec[name + "_invalid"] = b2 / w2 if w2 else None
                    rec[name + "_words"] = w2
            except Exception as e:
                rec["error"] = repr(e)[:200]
            results.append(rec)
            print(json.dumps(rec, ensure_ascii=False), flush=True)
    json.dump(results, open("originals_check.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
