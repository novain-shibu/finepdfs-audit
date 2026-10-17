# FinePDFs: complex-script text is often corrupted (text-layer path) or fabricated (rolmOCR path for Tamil, Malayalam, Telugu, Kannada)

Permanent record: DOI [10.5281/zenodo.23432200](https://doi.org/10.5281/zenodo.23432200) · code and results: https://github.com/novain-shibu/finepdfs-audit

## Summary
We measured the quality of FinePDFs text in 16 complex-script configs and traced the causes back to the original PDFs.
1. **Text-layer (Docling) path:** 3-29% (most 9-21%) of words are orthographically impossible (e.g. a vowel sign with no
   consonant before it), vs 0.00-0.55% in Wikipedia. Roughly 300k documents in the sampled configs have > 5% such words.
2. **Root cause:** in 18 of 24 original PDFs we fetched, the PDF's own text layer is broken; 19 of 24 were made with
   Microsoft Word. In a controlled test, Word for Microsoft 365 exporting Microsoft's own font (Nirmala UI) produced PDFs
   from which only 7-65% of words can be read back with a standard extractor.
3. **rolmOCR path (new, most serious):** for Tamil, Malayalam, Telugu and Kannada, most documents went through rolmOCR
   (74-84% of sampled docs). In random samples of those documents, the stored text almost never matches what an
   independent OCR reads on the same PDF (Malayalam 20/20, Telugu 18/18, Kannada 18/18, Tamil 7/8 docs below the
   pre-set threshold; Hindi 0/19 and Bengali 0/23). Hand-checked examples show fluent-looking script that does **not**
   say what the page says. The dataset card already warns that rolmOCR may hallucinate in low-resource languages; what we
   add is that in our samples of these four languages (together over 200 million speakers) it is the norm, not the
   exception (strongest evidence for Malayalam and Tamil), and that
   no signal in the dataset flags it: the `ocr_quality_scores` field is empty for every row we fetched in these configs,
   language ID scores the fabricated documents at 0.99-1.00, and the text passes orthographic and vocabulary checks.
   It matches a known model weakness: GlotOCR Bench (Kargaran et al., arXiv 2604.12978, April 2026) reports RolmOCR at
   0-3% Acc@5 on Tamil, Telugu, Kannada and Malayalam with the script itself correct.

## 1. Text-layer path: impossible words (random cluster sample, 3,149 docs, 16 configs)
Sample: per config 8 random offsets x 25 rows of `train` via the datasets-server rows API (seed 20261016).
Check (`validity.py`): in Brahmic scripts a dependent vowel sign or virama must follow a consonant (or nukta); anusvara,
visarga, candrabindu cannot start a word; for Thai/Khmer/Sinhala/Myanmar combining marks must follow a base. Hand check of
144 flagged words: 86.8% clear corruption, 0.7% legitimate words flagged. (One checker false positive found later: the
Bengali loanword spelling অ্যা is legitimate; it changes ben_Beng by about 0.3 points and asm_Beng by 0.) 95% CIs are
cluster bootstrap over the 8 offsets. Rates use docling documents with >= 20 words; the ">5%" column counts documents
with >= 50 words.

| config | docs | docling share | docling invalid % (95% CI) | docling docs >5% invalid | Wikipedia % |
|---|---|---|---|---|---|
| hin_Deva | 200 | 10% | 11.8% (7.5-13.1) | 15/18 | 0.03% |
| mar_Deva | 175 | 14% | 15.9% (7.3-24.7) | 16/23 | 0.15% |
| npi_Deva | 200 | 18% | 17.7% (12.2-23.7) | 29/36 | 0.07% |
| ben_Beng | 200 | 8% | 21.3% (15.9-28.4) | 10/16 | 0.55% |
| asm_Beng | 200 | 98% | 17.8% (14.0-22.6) | 145/189 | 0.03% |
| tam_Taml | 200 | 26% | 14.8% (7.6-18.1) | 32/50 | 0.01% |
| mal_Mlym | 200 | 25% | 8.2% (3.0-15.9) | 30/46 | 0.01% |
| tel_Telu | 200 | 16% | 13.2% (9.2-17.3) | 22/31 | 0.00% |
| kan_Knda | 200 | 22% | 10.7% (7.1-13.5) | 23/43 | 0.00% |
| guj_Gujr | 200 | 40% | 18.3% (13.8-20.3) | 71/78 | 0.03% |
| pan_Guru | 200 | 66% | 12.1% (9.0-15.0) | 84/127 | 0.03% |
| ory_Orya | 174 | 60% | 18.8% (14.2-22.7) | 79/102 | 0.00% |
| tha_Thai | 200 | 16% | 2.8% (1.8-5.0) | 6/24 | 0.00% |
| khm_Khmr | 200 | 46% | 13.1% (11.0-15.4) | 71/84 | 0.00% |
| sin_Sinh | 200 | 61% | 8.7% (6.6-11.0) | 64/114 | 0.00% |
| mya_Mymr | 200 | 44% | 28.7% (21.1-34.1) | 75/84 | 0.01% |

Estimated docs on the text-layer path with > 5% invalid words in these 16 configs: ~300k (point estimate; per-config CIs above).

## 2. Root cause: the PDFs, mostly Microsoft Word
- 24 original PDFs fetched from Common Crawl at FinePDFs' recorded offsets: in 18/24 the text layer itself is broken
  (PyMuPDF and pdfminer agree with FinePDFs' text within 5 points); 19/24 were produced by Microsoft Word. In the other 6,
  current docling-parse 7.22.3 extracts correctly (e.g. 24.7% -> 0.0% invalid), so re-extraction helps there.
- Controlled test (Word for Microsoft 365 build 16.0.20430, Save as PDF, Nirmala UI, Wikipedia text): words recoverable
  with PyMuPDF: Malayalam 7.1%, Odia 23.9%, Bengali 28.0%, Kannada 29.2%, Telugu 38.4%, Tamil 50.7%, Sinhala 51.0%,
  Gujarati 56.8%, Hindi 58.4%, Punjabi 65.3%. The PDFs are tagged but contain no ActualText, so the broken layer is the
  only text (search, copy-paste, screen readers, data pipelines).
- At scale: of 555 broken originals we fetched (all flagged docling docs of 13 configs in our sample), 329 embed font
  subsets that still carry the font's shaping tables, across 171 font builds (Vrinda 43 docs, Mangal 28+19, Arial Unicode
  MS 26, Nirmala UI 18, ...).

## 3. rolmOCR path: fabricated text in Tamil, Malayalam, Telugu, Kannada
Share of sampled docs on the rolmOCR path: tam 74%, mal 74%, tel 84%, kan 76% (hin 90%, ben 92%).
We fetched the originals of 150 random rolmOCR-path docs (6 configs x 25).

**Hand-checked examples** (stored text compared with the rendered page; labels written before any automatic score):

| doc | page actually says | FinePDFs text |
|---|---|---|
| mal_Mlym `<urn:uuid:04b30437-7e57-4603-870a-f2433993c43e>` | Ministry of Overseas Indian Affairs guide: "What is the Mahatma Gandhi Pravasi Suraksha Yojana? An integrated social security scheme of MOIA for emigrant workers in ECR countries..." | "What is 'the whole stage' (NPS) minute eligibility? ECR is a stage among the farmers of Kerala ... the whole stage motorist office (MOIA) ... the society's society's members" |
| mal_Mlym `<urn:uuid:083b4dda-f59e-4294-ba0b-dcfa4023decf>` | Kerala Govt Administrative Reforms circular (No. 7289, 22.02.2018) on putting office address, pincode, phone and email on official letters | "the rule of the stage - later violence becomes possible ... in crores, women farmers suddenly arose" |
| tel_Telu `<urn:uuid:60f21f81-0fa9-4d2f-8a06-cc46f5b94aed>` | Andhra Pradesh Rural Development circular on MGNREGS work for persons with disabilities | looping invented phrases ("reason long, lineage-adornment protected lineage-adornment ...") |
| kan_Knda `c3c44be4-4d79-402e-b562-4b10b9ec30ec` | Karnataka Janapada University, International Yoga Day, presided by Prof. C.T. Guruprasad | "University of Kannada speech", invented persons ("Dr. Shahrukh A. Samel") |
| kan_Knda `f87affe1-b476-41f3-9086-990fb744dc49` | Legion of Mary opening prayer ("In the name of the Father, and of the Son, and of the Holy Spirit. Amen ...") | "Kamu Kamu made music in the country made music made music ..." (loop) |
| tam_Taml `<urn:uuid:2667e232-fa6d-4ed8-9ffa-6cc8ce6cba82>` | Kanniyakumari district blindness-control society press note on cataract lens surgery | layout kept; "eye/cataract" replaced by "education", district name mangled |
| tam_Taml `<urn:uuid:40590782-bb3d-4ccd-ae66-79d282c70f6a>` | Tamil Nadu Backward Classes Welfare Dept scholarship application form | layout kept; key words replaced (e.g. "new" -> "New Year", "Backward Classes" -> non-word) |

Controls on the same path: hin `d6b08a5e-a791-4c7d-8fa5-cf442c78a756` and `<urn:uuid:1807029a-b950-48e3-b120-0140fa19b399>`
faithful (single-letter slips); ben `<urn:uuid:0eac4c2f-0765-4eed-9a37-172191550617>` and
`<urn:uuid:3337258e-7d36-4d7c-b6e4-6e663df5e14b>` mostly faithful (a few swapped words).

**Automatic check** (rule fixed before scoring, validated on the hand labels: 10/10 correct): agreement = share of the
stored words that free Tesseract 5.3.4 also reads on the same PDF (first 10 pages); < 0.25 = fabricated.

| config | docs below 0.25 (95% CI) | median agreement |
|---|---|---|
| mal_Mlym | 20/20 (84-100%) | 0.06 |
| tam_Taml | 7/8 (53-98%) | 0.20 |
| tel_Telu | 18/18 (82-100%) | 0.06 |
| kan_Knda | 18/18 (82-100%) | 0.10 |
| hin_Deva (control) | 0/19 (0-17%) | 0.86 |
| ben_Beng (control) | 0/23 (0-14%) | 0.78 |

Tesseract was chosen as the second reader because classic OCR engines garble rather than rewrite (see "Do VLMs Read or
Rewrite?", arXiv 2607.21617). Is Tesseract simply failing on these scans? For Malayalam and Tamil, Tesseract reads the scans about as well, relative to
clean pages, as it does for the Hindi/Bengali controls (share of its words found in a Wikipedia vocabulary, scans vs clean
pages: 0.88 and 0.85 vs 0.75 and 0.85 for the controls), so the low agreement points at the stored text. For Telugu and
Kannada, Tesseract itself is weaker on these scans (0.53 and 0.35), so their automatic rate is partly confounded; there
the evidence is the hand-checked examples plus GlotOCR Bench. The fabricated Malayalam text matches a Wikipedia
vocabulary as often as real Malayalam (0.42 vs 0.41), so vocabulary or orthography filters cannot catch it.
Alignment check: the NUMBERS in the stored text do match what Tesseract reads on the same pages (median agreement
0.90-1.00 for the four South Indian configs), so the comparison is on the right pages; the model copies digits and layout
correctly while the words around them disagree, consistent with GlotOCR Bench's finding that it cannot read these scripts.
Existing signals do not catch it: in every row we fetched for these configs (275 rows, 6 configs) `ocr_quality_scores` is
null, and `full_doc_lid_score` for the fabricated examples above is 0.99-1.00.

Our own run of RolmOCR (Kaggle 2xT4, fp16, model-card prompt) on synthetic Word PDFs with known text gave exact-word
recall Hindi 94.8%, Bengali 94.1%, Gujarati 53.2%, Tamil 40.4%, Telugu 17.8%, Kannada 8.8%, Malayalam 7.0% (one Malayalam
page repeated one word 78 times until the token limit). That setup differs from FinePDFs' (no bf16 on T4), so we rely on
the production text above, plus GlotOCR Bench, rather than on our run.

## 4. The text-layer damage is recoverable without OCR (for many Word-made PDFs)
The broken text layer still contains the exact glyph IDs. Searching for the Unicode text whose HarfBuzz shaping reproduces
those glyph IDs (and keeping a word only if re-shaping matches exactly) recovers the text:
- Held-out Word 365 PDFs, 10 scripts, 27 docs, 10,594 words: 99.1% exact words, vs free Tesseract 86.2% (non-italic;
  29.6% on Word's slanted italics) and PyMuPDF 22-77%. 14 ms/page on one laptop CPU core.
- Real broken FinePDFs originals, using only the font embedded in each PDF: 311 decoded; 81.4% of stretches verified by
  exact re-shaping; impossible-word rate 17.9% -> 1.8%. Pooling the partial cmaps of PDFs that share a font build
  is mixed in its current form: it helps some builds (Vrinda 67% -> 93%, Mangal 5.91 74% -> 83% verified) and hurts
  others (Mangal 6.9 91% -> 86%; Arial Unicode MS 80% -> 38%), because conflicting entries from other files remove
  correct ones.
- Limits: verified means renders identically (some spellings render identically and are flagged); no ground truth on real
  files; ~40% of broken originals do not embed shaping tables.
The recovery decoder is not part of this repository; a separate release is planned (available on request). It
builds on our earlier Malayalam-only prototype Unshape v0.1 (github.com/novain-shibu/unshape, DOI 10.5281/zenodo.23418945).

## Suggested fixes (low cost)
1. Do not route damaged Tamil/Malayalam/Telugu/Kannada text-layer documents to rolmOCR as is; per section 3 that trades
   visible corruption for invisible fabrication.
2. Flag or drop rolmOCR-path documents in these configs whose text disagrees with an independent reader (or add a
   per-language OCR quality gate); at minimum document the risk per language in the dataset card.
3. Add the orthographic-validity rate as a routing/quality feature for the text-layer path.
4. For Word-made PDFs, consider re-extraction by inverse shaping (section 4) instead of OCR.

## Limits
Hand check of section 3 = 11 documents (7 South Indian, 4 controls), done by the AI assistant reading the rendered page
images. The two Malayalam examples were then checked independently by the author: the author, who reads Malayalam,
compared both examples directly with the page images and found that the stored text does not match either page;
both were also checked with Google Lens (page) and Google Translate (FinePDFs text): page 1 = an MOIA
social-security scheme for overseas workers, stored text = "a platform for farmers in Kerala ... under the 'Motorist
Office'"; page 2 = a Kerala Government circular on the contents of official letters, stored text = "exploitation becomes
possible ... female farmers suddenly emerged". Native-speaker checks of the
other languages are welcome; document IDs are given so anyone can verify.
Sample = clusters of consecutive rows. Rule-based checks are a lower bound on damage.

AI assistance: analysis, code and this write-up were produced with an AI assistant (Claude); numbers were re-derived from
raw files, and the page-vs-text comparisons were done on rendered page images.

Novain Shibu
github.com/novain-shibu · linkedin.com/in/novain-shibu
