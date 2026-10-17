"""FINDINGS sec 28: pick up to 25 random rolmOCR-path docs per census config (seed 0) and fetch their stored text, Common
Crawl location and token_count via the rows API (3 s apart). Also keeps extractor + token_count of every row on the
fetched pages (for the token-share scale estimate). Writes census_meta.json. No PDFs are downloaded here."""
import json, random, time, urllib.request
from pathlib import Path

UA = {"User-Agent": "invent7-validity-check/0.1 (research; github.com/novain-shibu)"}
CFGS = ["guj_Gujr", "ory_Orya", "pan_Guru", "sin_Sinh", "mar_Deva", "npi_Deva", "tha_Thai", "khm_Khmr", "mya_Mymr"]
NOSPACE = {"tha_Thai", "khm_Khmr", "mya_Mymr"}


def get(url):
    for _ in range(2):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120))
        except Exception as e:
            print("  retry", repr(e)[:100], flush=True); time.sleep(30)
    return None


def main():
    rnd = random.Random(0)
    d = json.load(open("random_sample_v2.json", encoding="utf-8"))["docs"]
    out = {"docs": [], "pages": {}}
    for cfg in CFGS:
        minw = 20 if cfg in NOSPACE else 100
        pool = [r for r in d[cfg] if r["extractor"] != "docling" and r["words"] >= minw]
        pick = {r["id"] for r in rnd.sample(pool, min(25, len(pool)))}
        offs = sorted({r["offset"] for r in d[cfg] if r["id"] in pick})
        allrows = []
        for off in offs:
            page = get(f"https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config={cfg}&split=train&offset={off}&length=25")
            time.sleep(3)
            for x in (page or {}).get("rows", []):
                r = x["row"]
                allrows.append({"extractor": r["extractor"], "tokens": r["token_count"]})
                if r["id"] in pick:
                    out["docs"].append({"cfg": cfg, "id": r["id"], "file_path": r["file_path"], "cc_offset": r["offset"],
                                        "tokens": r["token_count"], "text": r["text"]})
        out["pages"][cfg] = allrows
        print(cfg, "pool", len(pool), "picked", len(pick), "pages", len(offs), "rows", len(allrows), flush=True)
    Path("census_meta.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("docs", len(out["docs"]))


if __name__ == "__main__":
    main()
