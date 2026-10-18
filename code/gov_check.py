"""Report section 7: Indian government (gov.in / nic.in) PDFs in FinePDFs' Indian-language configs - usable text or not?
Classes per govt doc (truncated PDFs dropped): ocr_routed (FinePDFs judged no usable text layer), broken (> 5% impossible
spellings in the stored text), usable. Paced 5 s; saves document IDs, URLs, offsets and classes only (no text).
Usage: python gov_check.py 3535 8    (run 1)   |   python gov_check.py 3636 16    (run 2, the confirmation sample)"""
import json, random, sys, time, urllib.request, urllib.parse, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from validity import scan_text
from gilaki_check import wilson
UA = {"User-Agent": "finepdfs-audit/1.3 (github.com/novain-shibu)"}
CFG = {"hin_Deva": 850570, "mar_Deva": 185544, "ben_Beng": 539857, "guj_Gujr": 84057, "pan_Guru": 14727,
       "ory_Orya": 5745, "tam_Taml": 100576, "tel_Telu": 31411, "kan_Knda": 35407, "mal_Mlym": 54104}
U = "https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config={}&split=train&offset={}&length=20"
def get(cfg, off):
    for _ in range(2):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(U.format(cfg, off), headers=UA), timeout=120)); time.sleep(5)
            return d["rows"]
        except Exception as e:
            print("retry", repr(e)[:60], flush=True); time.sleep(30)
    return []
def gov(url):
    h = (urllib.parse.urlparse(url).hostname or "").lower()
    return h.endswith("gov.in") or h.endswith("nic.in")
rnd = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 3535); R = {}; D = []; tot = collections.Counter()
for cfg, size in CFG.items():
    script = cfg.split("_")[1]; c = collections.Counter()
    for off in sorted(rnd.sample(range(size - 20), int(sys.argv[2]) if len(sys.argv) > 2 else 8)):
        for r in get(cfg, off):
            x = r["row"]; c["rows"] += 1
            if not gov(x.get("url") or ""):
                continue
            c["gov"] += 1
            if x.get("is_truncated"):
                c["truncated"] += 1; continue
            if x["extractor"] == "rolmOCR":
                cls = "ocr_routed"
            else:
                w, b = scan_text(x.get("text") or "", script)
                if w < 50:
                    c["too_short"] += 1; continue
                cls = "broken" if b / w > 0.05 else "usable"
            c[cls] += 1
            D.append({"cfg": cfg, "row": r["row_idx"], "id": x["id"], "url": x["url"], "file_path": x.get("file_path"),
                      "offset": x.get("offset"), "class": cls})
    n = c["ocr_routed"] + c["broken"] + c["usable"]; k = c["ocr_routed"] + c["broken"]
    R[cfg] = dict(c) | {"n": n, "inaccessible": k, "share": round(k / max(1, n), 3), "ci95": wilson(k, n)}
    tot.update({kk: v for kk, v in c.items()})
    print(cfg, json.dumps(R[cfg]), flush=True)
n = tot["ocr_routed"] + tot["broken"] + tot["usable"]; k = tot["ocr_routed"] + tot["broken"]
R["ALL"] = dict(tot) | {"n": n, "inaccessible": k, "share": round(k / max(1, n), 3), "ci95": wilson(k, n)}
print("ALL", json.dumps(R["ALL"]), flush=True)
json.dump({"results": R, "docs": D}, open(str(__import__("pathlib").Path(__file__).resolve().parent.parent / "results" / "gov_results.json"), "w", encoding="utf-8"), indent=1)
