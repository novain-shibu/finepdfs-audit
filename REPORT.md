# FinePDFs: corrupted (text-layer path) and fabricated (rolmOCR path) text in complex-script configs

**Full report, code and results:** https://github.com/novain-shibu/finepdfs-audit · permanent record: DOI [10.5281/zenodo.23432200](https://doi.org/10.5281/zenodo.23432200)

## TL;DR
1. **rolmOCR path: the stored text often does not say what the PDF says, in 7 scripts.** In random samples of rolmOCR-path documents, the stored text almost never matches what an independent OCR reads on the same PDF (docs below a threshold fixed before scoring, counting only pages that rendered properly): **Malayalam 18/18, Telugu 17/17, Kannada 17/17, Tamil 6/7, Sinhala 15/15, Odia 19/19, Punjabi 14/16**, vs **Hindi 0/16, Bengali 0/22, Marathi 0/18, Nepali 0/11, Gujarati 0/9 and Thai 3/17**. Khmer (8/9) and Burmese (8/8) point the same way on small samples. Hand-checked examples are fluent-looking script with a different meaning (e.g. a ministry social-security guide stored as text about "farmers in Kerala" and a "Motorist Office"). **Scale:** if the sampled rates hold, this is roughly **4.8 billion tokens** (95% CI 3.0-5.4 B) in about **170,000 documents** across the 7 configs, most of it Tamil (3.6 B).
2. **No existing signal flags it:** `ocr_quality_scores` is null for every row we fetched in the affected configs, language ID scores the fabricated documents at 0.99-1.00, and the text passes orthographic and vocabulary checks.
3. **Text-layer (docling) path, 16 complex scripts: 3-29% (most 9-21%) of words are orthographically impossible**, vs 0.00-0.55% in Wikipedia; roughly 300k documents with > 5% such words in the sampled configs. Mostly caused by the PDFs themselves (19 of 24 originals made with Microsoft Word).
4. **The text-layer damage is recoverable without OCR:** inverting OpenType shaping recovers 99.1% of words on held-out Word PDFs in 10 scripts (free Tesseract 86.2%; RolmOCR 61.2% on the documents it finished in our run).

The dataset card already warns that rolmOCR may hallucinate in low-resource languages. What this adds: in our samples of these seven languages (together well over 200 million speakers) it is the norm, not the exception, while scripts close to high-resource ones (Devanagari, Bengali, Gujarati, Thai) are largely fine; and nothing in the released data marks it. It matches a known model weakness: GlotOCR Bench (Kargaran et al., arXiv 2604.12978) reports RolmOCR at 0-3% Acc@5 on Tamil, Telugu, Kannada and Malayalam with the script itself correct.

## Verify it yourself in 2 minutes
Open the original PDF and the stored row side by side:

| config / id | original PDF (page) | stored row (datasets-server) | what the page says | what FinePDFs stores |
|---|---|---|---|---|
| mal_Mlym `<urn:uuid:04b30437-7e57-4603-870a-f2433993c43e>` | [mea.gov.in PDF](http://www.mea.gov.in/images/pdf/16-malayalam-faq-new.pdf) (p. 3) | [row 16528](https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config=mal_Mlym&split=train&offset=16528&length=1) | "What is the Mahatma Gandhi Pravasi Suraksha Yojana? An integrated social security scheme of the Ministry of Overseas Indian Affairs (MOIA) for emigrant workers in ECR countries..." | "What is 'the whole stage' (NPS) minute eligibility? ECR is a stage among the farmers of Kerala ... the whole stage motorist office (MOIA) ... the society's society's members" |
| mal_Mlym `<urn:uuid:083b4dda-f59e-4294-ba0b-dcfa4023decf>` | [irrigation.kerala.gov.in PDF](http://irrigation.kerala.gov.in/images/gos/71_2018_7289_2018.pdf) | [row 49747](https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config=mal_Mlym&split=train&offset=49747&length=1) | Kerala Govt Administrative Reforms circular No. 7289 (22.02.2018): official letters must carry office name, pin code, phone, officer and email | "the rule of the stage - later violence becomes possible ... in crores, women farmers suddenly arose" |
| tel_Telu `<urn:uuid:60f21f81-0fa9-4d2f-8a06-cc46f5b94aed>` | [rd.ap.gov.in PDF](http://rd.ap.gov.in/EGS/CIRNO_1688_EGS_PMD_APNA_07052011.pdf) | [row 26002](https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config=tel_Telu&split=train&offset=26002&length=1) | Andhra Pradesh Rural Development circular on MGNREGS work for persons with disabilities | looping invented phrases ("reason long, lineage-adornment protected lineage-adornment ...") |
| kan_Knda `c3c44be4-4d79-402e-b562-4b10b9ec30ec` | [janapadauniversity.ac.in PDF](https://www.janapadauniversity.ac.in/assets/upload/attachment/672260228_1338133319_KJVV_World%20Yoga%20Day%20(E)_2022.pdf) | [row 18679](https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config=kan_Knda&split=train&offset=18679&length=1) | Karnataka Janapada University, International Yoga Day, presided by Prof. C.T. Guruprasad | "University of Kannada speech", invented persons ("Dr. Shahrukh A. Samel") |
| kan_Knda `f87affe1-b476-41f3-9086-990fb744dc49` | [legionofmary.ie PDF](https://legionofmary.ie/images/uploads/files/Kannada.pdf) | [row 29274](https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config=kan_Knda&split=train&offset=29274&length=1) | Legion of Mary opening prayer ("In the name of the Father, and of the Son, and of the Holy Spirit. Amen ...") | "Kamu Kamu made music in the country made music made music ..." (loop) |
| tam_Taml `<urn:uuid:2667e232-fa6d-4ed8-9ffa-6cc8ce6cba82>` | [kanyakumari.nic.in PDF](http://www.kanyakumari.nic.in/pressrelease/664_22.09.2016.pdf) | [row 30347](https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config=tam_Taml&split=train&offset=30347&length=1) | district blindness-control society press note on cataract lens surgery | layout kept; "eye/cataract" replaced by "education", district name mangled |
| tam_Taml `<urn:uuid:40590782-bb3d-4ccd-ae66-79d282c70f6a>` | [americancollege.edu.in PDF](https://americancollege.edu.in/wp-content/uploads/2023/09/BC-FRESH-1-001.pdf) | [row 92471](https://datasets-server.huggingface.co/rows?dataset=HuggingFaceFW/finepdfs&config=tam_Taml&split=train&offset=92471&length=1) | Tamil Nadu Backward Classes Welfare Dept scholarship form | layout kept; key words replaced ("new" -> "New Year", "Backward Classes" -> non-word) |

(Quotes are English gists; the originals are in the linked files. If a web link is gone, the same PDF is in Common Crawl at the `file_path`/`offset` recorded in the row.) The two Malayalam examples were checked directly against the page images by the author, a Malayalam reader, and also with Google Lens (page) and Google Translate (stored text). Controls on the same path were faithful (hin `d6b08a5e-a791-4c7d-8fa5-cf442c78a756`, `<urn:uuid:1807029a-b950-48e3-b120-0140fa19b399>`) or mostly faithful with a few swapped words (ben `<urn:uuid:0eac4c2f-0765-4eed-9a37-172191550617>`, `<urn:uuid:3337258e-7d36-4d7c-b6e4-6e663df5e14b>`).

## 1. rolmOCR path: how the rate was measured
- 25 random rolmOCR-path docs per config were fetched from Common Crawl and read with free Tesseract 5.3.4 (first 10 pages), compared with the stored text of the same pages. Agreement = share of the stored script words that Tesseract also reads; < 0.25 = fabricated (for Thai, Khmer and Burmese, which do not separate words with spaces: character 3-gram agreement < 0.558, calibrated beforehand on the scored docs of the first 6 configs, 94% agreement with the word rule). Rules were fixed before scoring; the word rule sorted the hand-labelled documents (labels written before any score) 10/10 correctly.
- **Rendering check (applied to all configs):** some PDFs use non-embedded legacy fonts, so a renderer shows garbage and Tesseract reads garbage; the agreement is then meaningless (found by hand on Burmese and Thai pages whose stored text actually matched the topic). Only docs whose Tesseract output is mostly in the expected script are counted below; this removed 1-3 docs per config in the first six configs and 14 of ~23 in Khmer and Burmese.

| config | docs flagged (95% CI) |
|---|---|
| mal_Mlym | 18/18 (82-100%) |
| tel_Telu | 17/17 (82-100%) |
| kan_Knda | 17/17 (82-100%) |
| tam_Taml | 6/7 (49-97%) |
| sin_Sinh | 15/15 (80-100%) |
| ory_Orya | 19/19 (83-100%) |
| pan_Guru | 14/16 (64-97%) |
| khm_Khmr (small n) | 8/9 (56-98%) |
| mya_Mymr (small n) | 8/8 (68-100%) |
| tha_Thai | 3/17 (6-41%) |
| guj_Gujr | 0/9 (0-30%) |
| mar_Deva | 0/18 (0-18%) |
| npi_Deva | 0/11 (0-26%) |
| hin_Deva (control) | 0/16 (0-19%) |
| ben_Beng (control) | 0/22 (0-15%) |

Hand checks of a median flagged document in the second batch: Punjabi (a Gurmukhi children's Bible) stored as garbled text in Devanagari script; Sinhala (a 2013 Sri Lankan IT exam whose question 1 asks for 57 in binary) stored with an invented question about coaxial and fiber-optic cables; Odia ("Journalism and Mass Communication, JMC 02/01, Reporting") stored with the code kept and the words replaced.

- **Is Tesseract just failing?** Tesseract was chosen as the second reader because classic engines garble rather than rewrite ("Do VLMs Read or Rewrite?", arXiv 2607.21617). For Malayalam and Tamil (first batch) it reads these scans about as well, relative to clean pages, as it does for the Hindi/Bengali controls (share of its words found in a Wikipedia vocabulary, scans vs clean pages: 0.88 and 0.85 vs 0.75 and 0.85), so the low agreement points at the stored text. For Telugu and Kannada Tesseract itself is weaker on these scans (0.53 and 0.35), so their automatic rate is partly confounded; there the evidence is the hand-checked examples plus GlotOCR Bench.
- **Right pages?** The numbers in the stored text match what Tesseract reads on the same pages (median 0.90-1.00 for the four configs): the model copies digits and layout while the words around them are invented.
- **Why filters miss it:** the fabricated Malayalam text matches a Wikipedia vocabulary as often as real Malayalam (0.42 vs 0.41).
- Our own RolmOCR run (Kaggle 2xT4, fp16, model-card prompt) on synthetic Word PDFs with known text: exact-word recall Hindi 94.8%, Bengali 94.1%, Gujarati 53.2%, Tamil 40.4%, Telugu 17.8%, Kannada 8.8%, Malayalam 7.0% (one Malayalam page repeated one word 78 times until the token limit). That setup differs from yours (no bf16 on T4), so the conclusions rest on the production text above, not on this run.

## 2. Text-layer path: impossible words (random cluster sample, 3,149 docs, 16 configs)
8 random offsets x 25 rows per config (seed 20261016). Check: in Brahmic scripts a dependent vowel sign or virama must follow a consonant (or nukta), anusvara/visarga/candrabindu cannot start a word; for Thai/Khmer/Sinhala/Myanmar combining marks must follow a base. Hand check of 144 flagged words: 86.8% clear corruption, 0.7% legitimate words flagged (one later-found false positive, the Bengali loanword spelling অ্যা, changes ben_Beng by about 0.3 points). Docling docs with >= 20 words; ">5%" counts docs with >= 50 words; 95% CI = cluster bootstrap.

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

## 3. Root cause of the text-layer damage: the PDFs, mostly Microsoft Word
- 24 originals fetched at your recorded offsets: in 18/24 the PDF's own text layer is broken (PyMuPDF and pdfminer agree with the stored text within 5 points); 19/24 were made with Microsoft Word. In the other 6, current docling-parse 7.22.3 extracts correctly (e.g. 24.7% -> 0.0% invalid), so re-extraction helps there.
- Controlled test (Word for Microsoft 365 build 16.0.20430, Save as PDF, Nirmala UI, Wikipedia text): words recoverable with PyMuPDF: Malayalam 7.1%, Odia 23.9%, Bengali 28.0%, Kannada 29.2%, Telugu 38.4%, Tamil 50.7%, Sinhala 51.0%, Gujarati 56.8%, Hindi 58.4%, Punjabi 65.3%. The PDFs are tagged but contain no ActualText, so the broken layer is the only text.
- At scale: of 555 broken originals fetched (all flagged docling docs of 13 configs in our sample), 329 embed font subsets that still carry the font's shaping tables (171 font builds: Vrinda 43 docs, Mangal 28+19, Arial Unicode MS 26, Nirmala UI 18, ...).

## 4. Recoverable without OCR (for many Word-made PDFs)
The broken text layer still contains the exact glyph IDs; searching for the Unicode text whose HarfBuzz shaping reproduces them (keeping a word only if re-shaping matches exactly) recovers the text:
- Held-out Word 365 PDFs, 10 scripts, 27 docs, 10,594 words: **99.1% exact words** vs free Tesseract 86.2% (non-italic; 29.6% on Word's slanted italics) and PyMuPDF 22-77%; 14 ms/page on one laptop CPU core.
- The 7 documents RolmOCR finished in our run (2,688 words): RolmOCR 61.2%, Tesseract 91.2%, inverse shaping 99.3% (scoring that favours the OCR systems).
- Real broken FinePDFs originals, using only the font embedded in each PDF: 311 decoded; 81.4% of stretches verified by exact re-shaping; impossible-word rate 17.9% -> 1.8%. Limits: verified = renders identically; ~40% of broken originals do not embed shaping tables.
- The decoder is not in the repository yet (separate release planned); the exact versions behind these numbers are fingerprinted (SHA-256) in the repo. Happy to share it with the FinePDFs team (available on request: georgeshibu380@gmail.com or an issue on the repo).

## Suggestions
1. Don't route damaged Tamil/Malayalam/Telugu/Kannada text-layer docs to rolmOCR as is: that trades visible corruption for invisible fabrication.
2. Flag or drop rolmOCR-path docs in these configs whose text disagrees with an independent reader, or add a per-language OCR quality gate; at minimum, document the per-language risk in the card.
3. Use the orthographic-validity rate as a routing/quality feature on the text-layer path.
4. For Word-made PDFs, consider re-extraction by inverse shaping instead of OCR.

I'm happy to run the two-reader check over full configs, or help test any fix.

## Limits
Hand checks: 11 documents in the first batch (7 South Indian, 4 controls) and 7 in the second (Punjabi, Sinhala, Odia confirmed; flagged Thai and Burmese pages were renderer failures, hence the rendering check; an unflagged Thai control was faithful; the Khmer PDF was unreadable), first read by the AI assistant on rendered page images, the two Malayalam examples then confirmed by the author; native-speaker checks of the other languages are welcome, and every example is linked above. Samples are clusters of consecutive rows. An earlier version of this report counted 7 docs whose pages had not rendered properly (Malayalam 20/20, Telugu 18/18, Kannada 18/18, Tamil 7/8); the counts above exclude them, which does not change any conclusion. Rule-based checks are a lower bound on damage.

AI assistance: analysis, code and this write-up were produced with an AI assistant (Claude); every number was re-derived from raw files.

Novain Shibu · georgeshibu380@gmail.com · [github.com/novain-shibu](https://github.com/novain-shibu) · [linkedin.com/in/novain-shibu](https://www.linkedin.com/in/novain-shibu)
