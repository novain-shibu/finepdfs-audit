"""Clean-text baselines (skeptic fix 2): >= 20k words per language from wikimedia/wikipedia (20231101 dumps, CC-BY-SA)
via the datasets-server rows API, random offsets, 4 s between calls. Stores counts + all flagged words for review."""
import json, random, sys, time, urllib.request
sys.path.insert(0, ".")
from validity import scan_text

LANGS = {"hi": "Deva", "mr": "Deva", "ne": "Deva", "bn": "Beng", "as": "Beng", "ta": "Taml", "ml": "Mlym", "te": "Telu",
         "kn": "Knda", "gu": "Gujr", "pa": "Guru", "or": "Orya", "th": "Thai", "km": "Khmr", "si": "Sinh", "my": "Mymr"}
UA = {"User-Agent": "invent7-validity-check/0.1 (research; github.com/novain-shibu)"}


def get(url):
    for _ in range(2):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120))
        except Exception as e:
            print("  retry", e, flush=True); time.sleep(30)
    return None


def main():
    rng = random.Random(7)
    out = {}
    for lang, script in LANGS.items():
        cfg = f"20231101.{lang}"
        size = get(f"https://datasets-server.huggingface.co/size?dataset=wikimedia/wikipedia&config={cfg}")
        time.sleep(4)
        n = (size or {}).get("size", {}).get("config", {}).get("num_rows", 1000)
        W = B = 0; bad = []
        for _ in range(6):
            if W >= 20000:
                break
            off = rng.randrange(0, max(1, n - 100))
            d = get(f"https://datasets-server.huggingface.co/rows?dataset=wikimedia/wikipedia&config={cfg}&split=train&offset={off}&length=100")
            time.sleep(4)
            for r in (d or {}).get("rows", []):
                w, b = scan_text(r["row"]["text"], script, bad); W += w; B += b
        out[lang] = {"script": script, "words": W, "invalid": B, "rate": B / W if W else None, "bad_words": bad[:200]}
        print(f"{lang} {script}: words {W} invalid {B} = {B / max(W, 1):.3%}", flush=True)
    json.dump(out, open("wiki_baseline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
