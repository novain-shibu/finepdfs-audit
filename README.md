# FinePDFs audit: corrupted and fabricated complex-script text

An audit of the complex-script configs of [HuggingFaceFW/finepdfs](https://huggingface.co/datasets/HuggingFaceFW/finepdfs).
Full report: **[REPORT.md](REPORT.md)**.

## Findings in short
1. **Text-layer (Docling) path:** 3-29% (most 9-21%) of words are orthographically impossible in 16 complex-script
   configs, vs 0.00-0.55% in Wikipedia; roughly 300k documents with > 5% such words in the sampled configs.
2. **Root cause:** mostly the PDFs themselves; in 18 of 24 originals the text layer itself is broken, 19 of 24 were made
   with Microsoft Word, and Word for
   Microsoft 365 with its own font (Nirmala UI) exports PDFs from which only 7-65% of words can be read back.
3. **rolmOCR path:** for Tamil, Malayalam, Telugu and Kannada the stored text of random documents almost never matches an
   independent OCR of the same PDF (Malayalam 20/20, Telugu 18/18, Kannada 18/18, Tamil 7/8 below a pre-set threshold;
   Hindi 0/19, Bengali 0/23). Hand-checked examples are fluent-looking but say something other than what the page says.
   Consistent with GlotOCR Bench (arXiv 2604.12978).
4. **Recovery without OCR:** inverting OpenType shaping recovers 99.1% of words on held-out Word PDFs in 10 scripts
   (free Tesseract: 86.2%).

## What is in this repository
- `REPORT.md` - the report (numbers, method, limits).
- `code/` - every script used: sampling and orthographic check (`validity.py`, `random_sample.py`, `analyze_random.py`),
  original-PDF fetch (`fetch_originals.py`, `fetch_bulk.py`, `fetch_ocrpath.py`), the two-reader fabrication check
  (`score26.py`, `skeptic26.py`, `anchors26.py`, `kaggle/tesseract_finepdfs_ocrpath.py`), test-data generation
  (`make_data.py`, `fresh2_data.py`, `word_var.ps1`), OCR baselines (`kaggle/`) and scorers; shared helpers in
  `common.py`. Research code: paths assume the original working layout.
- The recovery decoder (section 4 of the report) is NOT included; a separate release is planned (available on request).
  It builds on the earlier Malayalam-only prototype [Unshape v0.1](https://github.com/novain-shibu/unshape).
- `results/` - raw result files (document IDs and numbers only), hand labels written before automatic scores
  (`labels26.json`), and the SHA-256 of each frozen decoder version.

## What is NOT in this repository (on purpose)
No PDFs, page images, fonts, Wikipedia text or FinePDFs document text are redistributed. Every result names FinePDFs
document IDs, so anyone can fetch the same originals from Common Crawl (FinePDFs records the WARC path and offset) and
the stored text from the dataset itself.

## Data sources and licences
FinePDFs (ODC-By 1.0); original PDFs via Common Crawl (Common Crawl terms of use); Wikipedia text (CC BY-SA 4.0) used
only locally to generate test PDFs; Windows system fonts used locally only. Code: Apache-2.0 (`LICENSE`). Report text and
result files: CC BY 4.0.

## AI assistance
Analysis, code and write-up were produced with an AI assistant (Claude); numbers were re-derived from raw files.

## Citation
See `CITATION.cff`. Author: Novain Shibu - github.com/novain-shibu - linkedin.com/in/novain-shibu
