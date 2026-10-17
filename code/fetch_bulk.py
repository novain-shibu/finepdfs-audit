"""FINDINGS sec 23: fetch the ORIGINAL PDFs of every flagged doc in random_sample_v2 (13 configs the decoder covers).
1) metadata: re-read the same 25-row pages from the datasets-server rows API (3 s apart) to get Common Crawl file_path/offset;
2) PDFs: one byte-range request per doc to data.commoncrawl.org, 3 s apart, one retry on 503, stop after 3 consecutive
errors, hard stop at 450 MB. Local only (originals_bulk/), never redistributed. Resumable (skips files already present)."""
import json, re, sys, time, urllib.error, urllib.request
from pathlib import Path
sys.path.insert(0, ".")
from fetch_originals import warc_payload, UA

CFGS = "hin_Deva mar_Deva npi_Deva ben_Beng asm_Beng tam_Taml mal_Mlym tel_Telu kan_Knda guj_Gujr pan_Guru ory_Orya sin_Sinh".split()
OUT, META, CAP = Path("originals_bulk"), Path("originals_bulk_meta.json"), 450 * 2**20


def get(url):
    for _ in range(2):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120))
        except Exception as e:
            print("  retry", repr(e)[:120], flush=True); time.sleep(30)
    return None


def metadata():
    if META.exists():
        return json.loads(META.read_text(encoding="utf-8"))
    d = json.load(open("random_sample_v2.json", encoding="utf-8"))["docs"]
    meta = []
    for cfg in CFGS:
        want = {r["id"]: r for r in d[cfg] if r["extractor"] == "docling" and r["words"] >= 100 and r["invalid"] / r["words"] > 0.05}
        for off in sorted({r["offset"] for r in want.values()}):
            page = get(f"https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config={cfg}&split=train&offset={off}&length=25")
            time.sleep(3)
            for row in (page or {}).get("rows", []):
                r = row["row"]
                if r["id"] in want:
                    w = want[r["id"]]
                    meta.append({"cfg": cfg, "id": r["id"], "url": r.get("url"), "file_path": r.get("file_path"),
                                 "cc_offset": r.get("offset"), "words": w["words"], "invalid": w["invalid"]})
        print(cfg, "meta so far", len(meta), flush=True)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=0), encoding="utf-8")
    return meta


def main():
    meta = metadata()
    OUT.mkdir(exist_ok=True)
    used = sum(p.stat().st_size for p in OUT.glob("*.pdf"))
    errs = got = 0
    for i, m in enumerate(meta):
        p = OUT / (re.sub(r"[^A-Za-z0-9-]", "_", m["id"]).strip("_") + ".pdf")
        if p.exists() or m.get("skip"):
            continue
        if used > CAP:
            print("STOP: 450 MB cap reached", flush=True); break
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
            p.write_bytes(pdf); used += len(pdf); got += 1
        if i % 25 == 0:
            print(f"{i}/{len(meta)} got {got} used {used / 2**20:.0f} MB", flush=True)
    print(f"DONE got {got}, total {used / 2**20:.0f} MB in {OUT}", flush=True)


if __name__ == "__main__":
    main()
