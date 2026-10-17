"""Analyse random_sample.json: per config, docling share, invalid-word rate on docling docs with a cluster bootstrap CI
(resampling the 8 random offsets), rolmOCR rate, Wikipedia baseline, and the FinePDFs-wide estimate of affected docs."""
import json, random, sys

CONFIG_ROWS = {"hin_Deva": 850570, "mar_Deva": 185544, "npi_Deva": 181691, "ben_Beng": 539857, "asm_Beng": 1551,
               "tam_Taml": 100576, "mal_Mlym": 54104, "tel_Telu": 31411, "kan_Knda": 35407, "guj_Gujr": 84057,
               "pan_Guru": 14727, "ory_Orya": 5745,
               "tha_Thai": 2516013, "khm_Khmr": 23142, "sin_Sinh": 20112, "mya_Mymr": 29171}
WIKI_OF = {"hin_Deva": "hi", "mar_Deva": "mr", "npi_Deva": "ne", "ben_Beng": "bn", "asm_Beng": "as", "tam_Taml": "ta",
           "mal_Mlym": "ml", "tel_Telu": "te", "kan_Knda": "kn", "guj_Gujr": "gu", "pan_Guru": "pa", "ory_Orya": "or",
           "tha_Thai": "th", "khm_Khmr": "km", "sin_Sinh": "si", "mya_Mymr": "my"}


def rate(docs):
    W = sum(d["words"] for d in docs); B = sum(d["invalid"] for d in docs)
    return B / W if W else float("nan")


def main(path="random_sample.json"):
    S = json.load(open(path, encoding="utf-8"))
    rng = random.Random(1)
    tot_docs = tot_bad = 0
    rows = []
    print(f"{'config':9s} {'docs':>4s} {'docling%':>8s} {'docling invalid':>16s} {'95% CI':>15s} {'bad docs':>9s} {'OCR invalid':>11s} {'wiki':>6s}")
    for cfg, docs in S["docs"].items():
        dl = [d for d in docs if d["extractor"] == "docling" and d["words"] >= 20]
        oc = [d for d in docs if d["extractor"] != "docling" and d["words"] >= 20]
        clusters = {}
        for d in dl:
            clusters.setdefault(d["offset"], []).append(d)
        keys = list(clusters)
        boots = []
        for _ in range(2000):
            pick = [d for k in (rng.choice(keys) for _ in keys) for d in clusters[k]] if keys else []
            if pick:
                boots.append(rate(pick))
        boots.sort()
        ci = (boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots)) - 1]) if boots else (float("nan"),) * 2
        bad = [d for d in dl if d["words"] >= 50 and d["invalid"] / d["words"] > 0.05]
        n50 = sum(d["words"] >= 50 for d in dl)
        w = S["wiki"].get(WIKI_OF[cfg], {})
        wr = w["invalid"] / w["words"] if w.get("words") else float("nan")
        share_bad = len(bad) / len(docs) if docs else 0
        tot_docs += CONFIG_ROWS[cfg]; tot_bad += share_bad * CONFIG_ROWS[cfg]
        rows.append(dict(config=cfg, docs=len(docs), docling_share=len(dl) / max(1, len(docs)), docling_invalid=rate(dl),
                         ci=ci, bad_docs=len(bad), docs50=n50, ocr_invalid=rate(oc), wiki_invalid=wr, est_bad_docs=share_bad * CONFIG_ROWS[cfg]))
        print(f"{cfg:9s} {len(docs):4d} {len(dl) / max(1, len(docs)):8.0%} {rate(dl):16.2%} {ci[0]:7.1%}-{ci[1]:6.1%} {len(bad):4d}/{n50:<4d} {rate(oc):11.2%} {wr:6.2%}")
    print(f"\nEstimated FinePDFs docs (train split, sampled configs) on the docling path with >5% invalid words: "
          f"{tot_bad:,.0f} of {tot_docs:,} ({tot_bad / tot_docs:.1%})")
    json.dump(rows, open("random_summary.json", "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
