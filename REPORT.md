# FinePDFs: corrupted (text-layer path) and fabricated (rolmOCR path) text in complex-script configs, small-language configs filled with broken text, and why: unreadable government PDFs and Word's PDF export

**Full report, code and results:** https://github.com/novain-shibu/finepdfs-audit · permanent record: DOI [10.5281/zenodo.23432200](https://doi.org/10.5281/zenodo.23432200)

## TL;DR
1. **rolmOCR path: the stored text often does not say what the PDF says, in 7 scripts.** In random samples of rolmOCR-path documents, the stored text almost never matches what an independent OCR reads on the same PDF (docs below a threshold fixed before scoring, counting only pages that rendered properly): **Malayalam 18/18, Telugu 17/17, Kannada 17/17, Tamil 6/7, Sinhala 15/15, Odia 19/19, Punjabi 14/16**, vs **Hindi 0/16, Bengali 0/22, Marathi 0/18, Nepali 0/11, Gujarati 0/9 and Thai 3/17**. Khmer (8/9) and Burmese (8/8) point the same way on small samples. Hand-checked examples are fluent-looking script with a different meaning (e.g. a ministry social-security guide stored as text about "farmers in Kerala" and a "Motorist Office"). **Scale:** if the sampled rates hold, this is roughly **4.8 billion tokens** (95% CI 3.0-5.4 B) in about **170,000 documents** across the 7 configs, most of it Tamil (3.6 B).
2. **No existing signal flags it:** `ocr_quality_scores` is null for every row we fetched in the affected configs, language ID scores the fabricated documents at 0.99-1.00, and the text passes orthographic and vocabulary checks.
3. **Text-layer (docling) path, 16 complex scripts: 3-29% (most 9-21%) of words are orthographically impossible**, vs 0.00-0.55% in Wikipedia; roughly 300k documents with > 5% such words in the sampled configs. Mostly caused by the PDFs themselves (19 of 24 originals made with Microsoft Word).
4. **The text-layer damage is recoverable without OCR:** inverting OpenType shaping recovers 99.1% of words on held-out Word PDFs in 10 scripts (free Tesseract 86.2%; RolmOCR 61.2% on the documents it finished in our run).
5. **New in v1.2: the `glk_Arab` ("Gilaki") config is mostly broken Persian/Arabic PDF text.** In a fresh random sample, **80/95 docs (84%, 95% CI 76-90%; about 90% of the sampled tokens)** are Persian or Arabic PDFs whose text layer came out broken (presentation forms, reversed lines, legacy-font mojibake), labelled Gilaki by language ID; the same rules flag 0/104 real Gilaki and 0/40 Persian Wikipedia articles. If the rate holds, that is about 4.5 billion of the config's 4.98 billion tokens (section 5).
6. **New in v1.3: broken text of big languages is filed under small languages.** Across all 82 non-Latin configs with >= 1,000 docs, damaged or wrong-script text piles up in small-language configs while the big ones stay mostly clean. Confirmed on fresh samples: Southern Balochi `bcc_Arab` 99%, Kashmiri `kas_Arab` 94%, "Gilaki" `glk_Arab` 73% and Mesopotamian Arabic `acm_Arab` 69% are mostly Persian or standard Arabic with a broken text layer; Assamese 82%, Uyghur 67% and Punjabi 60% are the right language with a broken text layer. About 6.1 billion tokens are mislabelled if the sampled rates hold (section 6).
7. **New in v1.4: Indian government PDFs in regional languages mostly have no readable text.** Of 791 randomly sampled government (gov.in / nic.in) PDFs in nine Indian languages, **93.8% (95% CI 91.9-95.3%)** have no correct Unicode text: 73% are scans with no text (a screen reader can read them only after running OCR), 21% have a broken text layer (garbled when copied, searched or read aloud), only 6% are clean (checked on 29 originals: 27 agree). No improvement and likely worse over time: 91% in 2017-19 crawls, 97.5% in 2023-25 (crawl year approximates publication year; section 7).
8. **New in v1.4 (corrected in v1.5): a cause reaching beyond India, Microsoft Word's "Save as PDF".** Same text, same font: printed to PDF by Microsoft Edge, no letter is lost (a few vowel signs come out doubled; letter F1 97-99.5%); saved by Word for Microsoft 365, letters are lost and garbled (letter F1 34% Khmer, 85% Myanmar, 88% Malayalam, 90% Hindi), so most of the damage is in Word's export, not the font or the extraction tool. Word 365 also garbles Divehi and Lao, while Arabic, Hebrew, Thai, Amharic and Georgian survive. Word made 79% of the broken Indian-language originals, but also most of the clean ones, so that share shows how common Word is, not the cause (section 8).

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

## 5. New in v1.2: the `glk_Arab` ("Gilaki") config is mostly broken Persian/Arabic text
`glk_Arab` is one of the largest non-Latin configs: 4.98B tokens in 312,868 docs. Gilaki is a regional language of northern Iran with little written text, so that size is implausible. A first look at 20 rows showed Persian and Arabic PDFs whose text layer came out broken, labelled Gilaki (or Balochi) by language ID with low confidence.

**Test** (`code/gilaki_check.py`, pre-registered, datasets-server rows API, 5 s between calls). Rules per document, on Arabic-script characters only (documents with fewer than 200 are skipped); corrupted = any rule:
- PF: Arabic presentation forms (U+FB50-FDFF, U+FE70-FEFF) are more than 5% of the characters (shaped glyphs copied as text);
- REV: reversed function words (e.g. "رد", "زا", "هب", "تسا") outnumber the forward ones ("در", "از", "به", "است"), at least 5 hits (lines stored in visual order);
- LEG: legacy marks/letters (U+0655-065F, U+063B-063F) above 1% (legacy Iranian-font mojibake).
PASS if glk is >= 50% corrupted and both clean Wikipedia controls are <= 5%; KILL if any control exceeds 10%.

| run | glk_Arab corrupted (95% CI) | token share | Gilaki Wikipedia | Persian Wikipedia | verdict |
|---|---|---|---|---|---|
| v1 (seed 31) | 78/97 = 80% (71-87%) | 97% | 28/104 = 27% | 0/19 | **KILL**: rule LEG misfires on real Gilaki |
| v2 (fresh sample, seed 3131) | **80/95 = 84% (76-90%)** | **90%** | **0/104** | **0/40** | **PASS** |

v1 failed honestly: real Gilaki writes U+065A (ARABIC VOWEL SIGN SMALL V ABOVE, 1.1% of letters in Gilaki Wikipedia), which LEG counted as mojibake. v2 removes only that character, a change derived from the control alone, and was scored once on a fresh sample. In v2, rules fired PF 57, REV 13, LEG 13; 98 of 100 sampled docs are on the docling (text-layer) path; document-level language ID said glk_Arab 70, bcc_Arab 20, fas_Arab 8, with a median score of 0.44. For reference, real `fas_Arab` FinePDFs docs were 4/38 flagged (11%, CI 4-24%) in v1.

**What this means:** if the sampled rate holds, about 4.5B tokens labelled Gilaki are corrupted Persian/Arabic text. It is the same failure family as section 3 (a broken PDF text layer), in another script family, made worse because the corrupted text is then assigned to a rare language. Not claimed: what the remaining ~16% is (it may still be Persian rather than Gilaki), or the state of other low-resource Arabic-script configs (e.g. `bcc_Arab`), which were not sampled. Much of the damage looks reversible without OCR (not yet measured): Unicode NFKC normalisation maps presentation forms back to letters, and reversed lines can be detected and flipped; legacy-font mojibake needs per-font mapping tables.

## 6. New in v1.3: small-language configs collect broken text ("exile")
Section 5 showed one config (`glk_Arab`) that is mostly broken Persian. This section asks whether that is a pattern. Code: `code/exile_check.py`; results: `results/exile_screen_results.json`, `results/exile_retest_results.json` (document IDs, row offsets, flags and numbers only).

**Rules per document** (>= 200 letters). MISMATCH: fewer than 50% of the letters are in the config's own script. CORRUPT, Arabic script: presentation forms > 5%, or reversed lines (as in section 5), or legacy-font letters U+063B-063F > 0.5% (these occur 0 times in 2.1M characters of Wikipedia in Kashmiri, Uyghur, Gilaki, Persian, Arabic, Urdu, Sorani, Sindhi and Pashto); CORRUPT, Brahmic scripts: > 5% orthographically impossible words (section 2). BAD = mismatch or corrupt. This replaces section 5's LEG rule, which misfires on real Kashmiri (it writes U+0655/0656/0657/065B/065F; Kashmiri Wikipedia was flagged 49/49 under the old rule). The rules cannot see fabricated OCR text, which is fluent (section 1), so OCR-heavy configs are under-counted here.

**Screen** (pre-registered): 20 rows from each of the 82 non-Latin configs with >= 1,000 docs. Nine configs had BAD >= 50%; big configs were 0-15% (e.g. Persian 0/19, Arabic 3/20, Hindi 2/20, Bengali 2/19, Russian, Chinese and Greek 0/18-20).

**Fresh re-test** of the nine (pre-registered, 5 x 20 new rows each). CONFIRMED = BAD >= 50%, CI lower bound >= 30%, and clean Wikipedia controls for that script <= 5%.

| config | language label | docs | BAD (95% CI) | what it is (hand checks) | bad tokens if rate holds |
|---|---|---|---|---|---|
| `bcc_Arab` | Southern Balochi | 111,724 | **94/95 = 99% (94-100)** | Persian (e.g. Iranian university journals), broken text layer | ~1.6B |
| `kas_Arab` | Kashmiri | 21,699 | **94/100 = 94% (88-97)** | Persian legacy-font mojibake (Iranian university and medical PDFs) | ~0.6B |
| `glk_Arab` | Gilaki | 313,867 | **70/96 = 73% (63-81)** | Persian/Arabic, broken text layer (stricter rule than section 5's 84%) | ~3.9B |
| `acm_Arab` | Mesopotamian Arabic | 8,597 | **63/91 = 69% (59-78)** | standard Arabic (Jordan, Lebanon, Kuwait, Egypt), broken text layer | ~0.06B |
| `asm_Beng` | Assamese | 1,551 | **82/100 = 82% (73-88)** | Assamese, broken text layer | ~0.01B |
| `uig_Arab` | Uyghur | 2,889 | **66/98 = 67% (58-76)** | Uyghur, presentation forms copied as text | ~0.03B |
| `pan_Guru` | Punjabi | 14,727 | **57/95 = 60% (50-69)** | Punjabi, broken text layer or other script | ~0.25B |
| `anp_Deva` | Angika | 129,557 | 61/95 = 64% (54-73), *likely* | mostly not Devanagari: English with a zero-width joiner between words, tables, other languages | ~0.5B |
| `kas_Deva` | Kashmiri (Devanagari) | 4,309 | 43/86 = 50% (40-60), *likely* | mixed | ~0.01B |

Controls with the same rules: Wikipedia Uyghur 0/87, Arabic 0/97, Persian 0/100, Gilaki 0/96, Kashmiri 1/59 (independent articles; the rule was derived on others), Assamese 0/98, Punjabi 1/68; Hindi 2/33 (6%, above the 5% bar, so the two Devanagari configs are reported as likely, not confirmed).

**What this means.** In FinePDFs, text that the extractor damaged is often assigned by language ID to a small neighbouring language (median language-ID confidence 0.15-0.6 in the affected configs). The result is that the configs a builder would use for Balochi, Kashmiri, Gilaki or Mesopotamian Arabic are mostly broken Persian or Arabic: about 6.1 billion tokens in the four confirmed wrong-language configs if the sampled rates hold (about 6.6 billion with the two likely ones). The `glk_Arab` part overlaps section 5 (same config, stricter rule here); do not add the two. The general phenomenon, small-language subsets of web corpora that are mostly wrong-language or junk, was documented for older corpora by Kreutzer et al. (2022, "Quality at a Glance"); earlier related evidence: only about 40% of mC4's Marathi bucket was well-formed Marathi (Chung et al. 2023, UniMax); language-ID models confuse Balochi, Gilaki and Kashmiri with Persian (Ahmadi 2023, PALI); and a MITRE study found Word-made PDFs the worst source for Arabic and Persian text extraction (DTIC ADA546769). To our knowledge, this section is the first to show the effect in a 2025 PDF corpus, trace it to broken PDF text layers, and size it. A quick comparison points at PDF extraction as the cause: in Hugging Face's web corpus FineWeb-2, which uses the same config names, the same rules flag 0/19 `kas_Arab` docs (real Kashmiri) and 1/20 `glk_Arab` docs (20-row screen; `bcc_Arab` could not be fetched). Not claimed: anything about configs not re-tested; rolmOCR fabrication in these configs; exact token totals (estimates from mean tokens per sampled doc).

## 7. New in v1.4: Indian government regional-language PDFs - can a screen reader read them?
The text layer of a PDF is what screen readers (for blind and low-vision readers), search engines, translation tools and AI pipelines read. This section is a technical measurement of PDF text layers only; it makes no statement about any law, rule or guideline. Code: `code/gov_check.py`; results: `results/gov_results_run1_seed3535.json`, `results/gov_results_run2_seed3636.json`, `results/gov_verify_29_originals.json`.

**Method** (pre-registered). Random rows from ten Indian-language configs; keep documents whose URL host ends in `gov.in` or `nic.in`; drop truncated PDFs (FinePDFs sent those to OCR regardless). Classes: *OCR-routed* (FinePDFs judged the text layer unusable), *broken* (> 5% orthographically impossible words in the stored text), *usable*. **Verification**: 29 of the originals fetched from Common Crawl and read with PyMuPDF (the PDF's own text layer): OCR-routed -> 8/9 had no text at all (scanner output) and 1 broken; broken -> 9/10 broken, all made by Microsoft Word 2007-365; usable -> 9/10 usable. Agreement 27/29 = 93% (bar set beforehand: 80%). The downloaded PDFs were deleted after the check.

| | run 1 (seed 3535) | run 2, confirmation (seed 3636, fresh) |
|---|---|---|
| govt documents classified | 394 | 791 |
| scans / no usable text (OCR-routed) | 294 (75%) | 574 (73%) |
| broken text layer | 69 (18%) | 168 (21%) |
| usable | 31 (8%) | 49 (6%) |
| **no correct text layer (95% CI)** | **92.1% (89.0-94.4%)** | **93.8% (91.9-95.3%)** |

Run 2 per language: Hindi 99%, Marathi 99%, Tamil 100%, Malayalam 97.5%, Punjabi 96%, Gujarati 90%, Odia 88%, Telugu 88%, Kannada 87% (Bengali: almost no Indian government PDFs in the config). **Trend** (pre-registered, by Common Crawl snapshot year): 2017-19 91.4% (87.6-94.1%) -> 2023-25 97.5% (94.4-98.9%), confidence intervals (barely) not overlapping; the broken-Word share rose from 8% to 27-30%. Because crawl year only approximates publication year and Common Crawl's coverage changes over time, we read this as no improvement and likely worse. By host (n >= 15; counts in the results files): on 7 of the 9 such hosts, 98-100% of the PDFs had no correct text layer, on one 80%; one district site (report-generator output) was 17/17 clean, so clean output is possible.

**Scope.** These are government PDFs that Common Crawl captured and FinePDFs kept in its Indian-language configs (2013-2025), not a census of all government documents; crawl year approximates publication year. Prior work audited Indian government *websites* (Centre for Internet & Society 2012, 7,800 sites; WCAG 2.1 studies of ministry sites); we found no measurement of regional-language PDF text layers. The local checker `tools/indic_pdf_check.py` gives any office the same verdict (no text / broken / OK) for its own PDFs before publishing.

## 8. New in v1.4: Microsoft Word's "Save as PDF" and complex scripts
**At scale** (`results/word_rootcause_555.json`, `tools/indic_pdf_check.py` on the 555 broken originals of section 3): 477 have a broken text layer; Microsoft Word made 375 of them (79%, 95% CI 75-82%), across every version (2010: 103, 2016: 70, 2007: 64, 2013: 45, Microsoft 365: 49, 2019: 21); 308 of the 375 are tagged PDFs, i.e. made with accessibility structure switched on, and still unreadable. **Base rate (added in v1.5):** Word also made 16 of the 21 PDFs in the same set whose text layer was fine (76%), so the 79% shows how common Word is among these documents, not that Word caused the damage; in the government sample (section 7) the 9 verified broken PDFs were all Word-made versus 3 of 10 clean ones (small numbers). The causal evidence is the controlled tests below.

**Same text, same font, different producer (added in v1.5)** (`code/word_vs_edge_test.py`, `results/word_vs_edge_results.json`): the same source text in the same font, saved as PDF by Word for Microsoft 365 and printed to PDF by Microsoft Edge, read back with the same PyMuPDF:

| script (font) | Word 365: letters kept / letters right / F1 | Edge: letters kept / letters right / F1 |
|---|---|---|
| Malayalam (Nirmala UI) | 87.3% / 88.3% / 87.8% | 100.0% / 98.2% / 99.1% |
| Hindi (Nirmala UI) | 87.9% / 91.1% / 89.5% | 100.0% / 99.0% / 99.5% |
| Myanmar (Myanmar Text) | 87.4% / 83.4% / 85.4% | 100.0% / 94.5% / 97.2% |
| Khmer (Leelawadee UI) | 35.8% / 31.7% / 33.6% | 100.0% / 97.8% / 98.9% |

(letters kept = recall: share of the source's letters found in order; letters right = precision: share of extracted letters that match; corrected in v1.5.1, v1.5 reported recall only.) Edge loses no letter with the same font and the same extractor, but repeats some vowel signs (e.g. a doubled Malayalam aa-sign), which a screen reader would also read; Word loses and garbles far more. So most of the damage is in Word's export, not in the font or the extraction tool, and Edge's output is close to clean but not perfect. Word-level scores are lower for both producers (Edge: 48-96%) because of those doubled signs and because line breaks split words when text is read back, especially in scripts written without spaces; letter-level recall is therefore the fair measure, and word-level numbers for Khmer, Myanmar and Lao in the table below overstate the damage.

**Controlled test** (`code/word_scripts_test.py`, results `results/word_scripts_results.json`): Wikipedia text in 14 scripts saved as PDF by Word for Microsoft 365 with the default Windows font for each script, read back with PyMuPDF and pdfminer (pre-registered: a script is broken if both extractors recover < 90% of words; English and Russian controls must be >= 98%).

| script (font) | words recovered, PyMuPDF / pdfminer | letters recovered | verdict |
|---|---|---|---|
| English, Russian (Calibri) | 100% / 100% | 100% | control |
| Georgian (Segoe UI), Javanese, Amharic (Ebrima) | 99-100% | 100% | fine |
| Hebrew (Segoe UI) | 99.7% / 13.2% | 100% | fine (pdfminer's right-to-left handling) |
| Arabic, Persian, Urdu (Arial) | 91-93% / 4-8% | 97-99.7% | not broken by the rule |
| Tibetan (Microsoft Himalaya) | 87.3% / 87.3% | 95.3% | broken (mild) |
| Lao (Leelawadee UI) | 39.8% / 19.5% | 97.2% (85% of letter triples) | broken |
| Myanmar (Myanmar Text) | 6.9% / 6.9% | 87.4% (51% of letter triples) | broken |
| Divehi / Thaana (MV Boli) | 0.4% / 0.2% | 71.7% | broken |
| Khmer (Leelawadee UI) | 0.0% / 0.0% | 35.8% | broken |

With section 3's Word test (Devanagari, Bengali, Tamil, Malayalam, Telugu, Kannada, Gujarati, Gurmukhi, Odia and Sinhala: 7-65% of words recoverable), Word 365's PDF export garbles about 15 scripts whose languages have over a billion speakers (severely for Khmer and Divehi, moderately for Lao, mildly for Tibetan, by letter-level recall), while it handles Arabic, Hebrew, Thai, Amharic and Georgian. Another PDF producer (Typst) has been reported to export Khmer that extracts exactly, so the problem is fixable at the source. Prior art: many user reports (Adobe and Aspose forums: Khmer, Myanmar, Lao, Hindi), a 2020 PDF Association talk on complex scripts, and a MITRE study on Arabic/Persian PDFs (DTIC ADA546769); we found no systematic cross-script measurement of Word. Limits: one Word build, one font per script, Wikipedia text; some Word-made PDFs are clean (older Word versions and other fonts can behave differently); readers that use the PDF's text layer (screen readers, search, copy-paste) see the same text as the extractors.

## Suggestions
1. Don't route damaged Tamil/Malayalam/Telugu/Kannada text-layer docs to rolmOCR as is: that trades visible corruption for invisible fabrication.
2. Flag or drop rolmOCR-path docs in these configs whose text disagrees with an independent reader, or add a per-language OCR quality gate; at minimum, document the per-language risk in the card.
3. Use the orthographic-validity rate as a routing/quality feature on the text-layer path.
4. For Word-made PDFs, consider re-extraction by inverse shaping instead of OCR.
5. For Arabic-script PDFs, NFKC-normalise presentation forms and detect reversed lines before language ID; low-confidence language-ID results in rare-language configs deserve a check (`glk_Arab`: median 0.44).
6. Before release, check every config for script mismatch and broken text with the cheap per-document rules of section 6, and treat low language-ID confidence in small-language configs as a warning sign; the configs listed in section 6 can be re-assigned (most are Persian or Arabic) or dropped.
7. For Microsoft: write ActualText (or a correct ToUnicode mapping per glyph cluster) when exporting complex-script text from Word to PDF; until then, publishers of Indic, Sinhala, Khmer, Myanmar, Lao and Thaana PDFs should check that copied text matches the source (for Indian scripts: `tools/indic_pdf_check.py`).

I'm happy to run the two-reader check over full configs, or help test any fix.

## Limits
Hand checks: 11 documents in the first batch (7 South Indian, 4 controls) and 7 in the second (Punjabi, Sinhala, Odia confirmed; flagged Thai and Burmese pages were renderer failures, hence the rendering check; an unflagged Thai control was faithful; the Khmer PDF was unreadable), first read by the AI assistant on rendered page images, the two Malayalam examples then confirmed by the author; native-speaker checks of the other languages are welcome, and every example is linked above. Samples are clusters of consecutive rows. An earlier version of this report counted 7 docs whose pages had not rendered properly (Malayalam 20/20, Telugu 18/18, Kannada 18/18, Tamil 7/8); the counts above exclude them, which does not change any conclusion. Rule-based checks are a lower bound on damage. Section 5 rests on rules plus a reading by the AI assistant (the author does not read Persian); Persian-reader checks are welcome. Section 6 rests on 100-document samples per config and the same kind of reading; Arabic, Persian, Kashmiri, Uyghur and Assamese readers' checks are welcome.

AI assistance: analysis, code and this write-up were produced with an AI assistant (Claude); every number was re-derived from raw files.

Novain Shibu · georgeshibu380@gmail.com · [github.com/novain-shibu](https://github.com/novain-shibu) · [linkedin.com/in/novain-shibu](https://www.linkedin.com/in/novain-shibu)
