"""Kaggle CPU job (private): free OCR baseline (Tesseract, Apache-2.0) on invent7 FRESH2 Word PDFs, 10 scripts.
Installs from Ubuntu's official apt repository (fallback: Tesseract's official tessdata_fast models on GitHub).
Renders each page at 300 dpi with PyMuPDF, OCRs with `tesseract -l <lang>+eng --psm 3`, OMP_THREAD_LIMIT=1,
writes /kaggle/working/ocr_results.json incrementally. Time cap 40 min. Pre-registered in invent7/FINDINGS.md sec 18.
"""
import glob, json, os, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor

T0 = time.time()
CAP = 40 * 60
OUT = "/kaggle/working/ocr_results.json"
TESS = {"hi": "hin", "bn": "ben", "ta": "tam", "ml": "mal", "te": "tel", "kn": "kan", "gu": "guj", "pa": "pan",
        "or": "ori", "si": "sin"}
LOG = []


def log(msg):
    line = f"[{time.time() - T0:7.1f}s] {msg}"
    print(line, flush=True)
    LOG.append(line)


def sh(cmd, timeout=900):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-2000:]


def setup():
    pk = " ".join(f"tesseract-ocr-{t}" for t in TESS.values())
    code, out = sh(f"apt-get -qq update && DEBIAN_FRONTEND=noninteractive apt-get -qq install -y tesseract-ocr {pk}")
    log(f"apt rc={code} {out[-300:]}")
    code, out = sh("tesseract --version")
    log(f"tesseract: {out.splitlines()[0] if out else '?'}")
    code, langs = sh("tesseract --list-langs")
    missing = [t for t in list(TESS.values()) + ["eng"] if t not in langs.split()]
    if missing:
        tdir = "/kaggle/working/tessdata"
        os.makedirs(tdir, exist_ok=True)
        for t in list(TESS.values()) + ["eng"]:
            sh(f"curl -sL -o {tdir}/{t}.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/main/{t}.traineddata", 300)
        os.environ["TESSDATA_PREFIX"] = tdir
        code, langs = sh("tesseract --list-langs")
        log(f"fallback tessdata_fast for missing {missing}")
    log(f"langs: {sorted(langs.split()[4:])}")
    code, out = sh(f"{sys.executable} -m pip install -q pymupdf", 600)
    log(f"pip pymupdf rc={code}")
    return [t for t in TESS.values() if t not in langs.split()]


def ocr_page(args):
    pdf, pno, tl, workdir = args
    import pymupdf
    try:
        png = os.path.join(workdir, f"{os.path.basename(pdf)}_{pno}.png")
        pymupdf.open(pdf)[pno].get_pixmap(dpi=300).save(png)
        t = time.time()
        env = dict(os.environ, OMP_THREAD_LIMIT="1")
        r = subprocess.run(["tesseract", png, "stdout", "-l", f"{tl}+eng", "--psm", "3"],
                           capture_output=True, text=True, timeout=180, env=env)
        os.remove(png)
        return pno, r.stdout, time.time() - t, r.stderr[-200:] if r.returncode else ""
    except Exception as e:  # one bad page never stops the run
        return pno, "", 0.0, f"ERR {e!r}"[:300]


def main():
    results = {"log": LOG, "files": {}}
    missing = setup()
    if missing:
        log(f"models still missing: {missing}")
    import pymupdf
    pdfs = sorted(glob.glob("/kaggle/input/**/fresh2_*.pdf", recursive=True))
    log(f"{len(pdfs)} PDFs")
    workdir = "/kaggle/working/tmp"
    os.makedirs(workdir, exist_ok=True)
    jobs = []
    for pdf in pdfs:
        lang = os.path.basename(pdf).split("_")[1]
        if TESS[lang] in missing:
            continue
        jobs += [(pdf, i, TESS[lang], workdir) for i in range(len(pymupdf.open(pdf)))]
    if jobs:
        pno, txt, sec, err = ocr_page(jobs[0])
        log(f"preflight page: {sec:.1f}s, {len(txt)} chars, err={err!r}")
    ncpu = os.cpu_count() or 2
    pages = {}
    with ProcessPoolExecutor(max_workers=ncpu) as ex:
        futs = {ex.submit(ocr_page, j): j for j in jobs}
        for f, j in futs.items():
            left = CAP - (time.time() - T0)
            if left <= 0:
                log("time cap reached"); break
            try:
                pno, txt, sec, err = f.result(timeout=left)
            except Exception as e:
                pno, txt, sec, err = j[1], "", 0.0, f"ERR {e!r}"[:200]
            d = results["files"].setdefault(os.path.basename(j[0]), {"pages": {}, "page_sec": {}, "errors": []})
            d["pages"][pno] = txt; d["page_sec"][pno] = sec
            if err:
                d["errors"].append(err)
            json.dump(results, open(OUT, "w"), ensure_ascii=False, default=float)
    log(f"done: {len(results['files'])} files, workers={ncpu}")
    json.dump(results, open(OUT, "w"), ensure_ascii=False, default=float)


if __name__ == "__main__":
    main()
