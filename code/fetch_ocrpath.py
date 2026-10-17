"""FINDINGS sec 25: fetch rolmOCR-path FinePDFs docs (text + original PDF) for the hallucination audit.
25 docs (>= 100 words) per config, spread over random_sample_v2 clusters (seed 0). Rows API 3 s apart; Common Crawl 3 s
apart, one retry on 503, stop after 3 consecutive errors; stop if originals_bulk + ocrpath_pdfs exceeds 480 MB.
Local only, never redistributed."""
import json, random, re, sys, time, urllib.error
from pathlib import Path
sys.path.insert(0, ".")
from fetch_originals import warc_payload
from fetch_bulk import get

CFGS = ["tam_Taml", "mal_Mlym", "tel_Telu", "kan_Knda", "hin_Deva", "ben_Beng"]
OUT, META, CAP = Path("ocrpath_pdfs"), Path("ocrpath_meta.json"), 480 * 2**20


def used():
    return sum(p.stat().st_size for d in ("originals_bulk", "ocrpath_pdfs") for p in Path(d).glob("*.pdf"))


def main():
    rnd = random.Random(0)
    d = json.load(open("random_sample_v2.json", encoding="utf-8"))["docs"]
    if META.exists():
        meta = json.loads(META.read_text(encoding="utf-8"))
    else:
        meta = []
        for cfg in CFGS:
            pool = [r for r in d[cfg] if r["extractor"] != "docling" and r["words"] >= 100]
            pick = {r["id"]: r for r in rnd.sample(pool, min(25, len(pool)))}
            for off in sorted({r["offset"] for r in pick.values()}):
                page = get(f"https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config={cfg}&split=train&offset={off}&length=25")
                time.sleep(3)
                for row in (page or {}).get("rows", []):
                    r = row["row"]
                    if r["id"] in pick:
                        meta.append({"cfg": cfg, "id": r["id"], "extractor": r.get("extractor"), "file_path": r.get("file_path"),
                                     "cc_offset": r.get("offset"), "text": r["text"]})
            print(cfg, "meta", len(meta), flush=True)
        META.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    errs = got = 0
    for i, m in enumerate(meta):
        p = OUT / (re.sub(r"[^A-Za-z0-9-]", "_", m["id"]).strip("_") + ".pdf")
        if p.exists():
            continue
        if used() > CAP:
            print("STOP: storage cap", flush=True); break
        try:
            try:
                pdf = warc_payload(m["file_path"], m["cc_offset"])
            except urllib.error.HTTPError as e:
                if e.code != 503:
                    raise
                time.sleep(30); pdf = warc_payload(m["file_path"], m["cc_offset"])
            errs = 0
        except Exception as e:
            errs += 1; print(i, "ERROR", repr(e)[:120], flush=True); time.sleep(3)
            if errs >= 3:
                print("STOP: 3 consecutive errors", flush=True); break
            continue
        time.sleep(3)
        if pdf.startswith(b"%PDF"):
            p.write_bytes(pdf); got += 1
        if i % 25 == 0:
            print(f"{i}/{len(meta)} got {got} total storage {used() / 2**20:.0f} MB", flush=True)
    print(f"DONE got {got}, total storage {used() / 2**20:.0f} MB", flush=True)


if __name__ == "__main__":
    main()
