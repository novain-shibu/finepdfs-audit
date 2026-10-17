"""Kaggle 2xT4 job (private): RolmOCR (reducto/RolmOCR, Apache-2.0) on invent7 FRESH2 Word PDFs. Pre-registered in
invent7/FINDINGS.md sec 19. transformers only (preinstalled), LM fp16 + vision fp32, card prompt, temperature 0.2,
max_new_tokens 6144, longest side 1288 px, batch 6, hard cap 45 min. Writes /kaggle/working/vlm_results.json after every
batch (a crash keeps earlier pages)."""
import glob, io, json, os, sys, time

T0 = time.time()
CAP = 45 * 60
OUT = "/kaggle/working/vlm_results.json"
PROMPT = "Return the plain text representation of this document as if you were reading it naturally.\n"
LANGS = "hi bn ta ml te kn gu pa or si".split()
LOG = []


def log(msg):
    line = f"[{time.time() - T0:7.1f}s] {msg}"
    print(line, flush=True)
    LOG.append(line)


def render(pdf, pno, longest=1288):
    import pymupdf
    from PIL import Image
    page = pymupdf.open(pdf)[pno]
    zoom = longest / max(page.rect.width, page.rect.height)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def jobs(pdfs):
    import pymupdf
    by = {}
    for p in pdfs:
        by.setdefault(os.path.basename(p).split("_")[1], []).append(p)
    order, k = [], 0
    while any(by.values()):  # round-robin over scripts
        for lang in LANGS:
            if by.get(lang):
                order.append(by[lang].pop(0))
    return [(p, i) for p in order for i in range(len(pymupdf.open(p)))]


def script_share(t):
    s = [c for c in t if not c.isspace()]
    return sum(0x0900 <= ord(c) < 0x0E00 for c in s) / max(1, len(s))


def main():
    res = {"log": LOG, "pages": {}, "sec": {}, "tokens": {}}
    os.system(f"{sys.executable} -m pip install -q pymupdf")
    import torch, transformers
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
    log(f"torch {torch.__version__} transformers {transformers.__version__} gpus {torch.cuda.device_count()} "
        f"{torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-'}")
    pdfs = sorted(glob.glob("/kaggle/input/**/fresh2_*.pdf", recursive=True))
    J = jobs(pdfs)
    log(f"{len(pdfs)} PDFs, {len(J)} pages")
    proc = AutoProcessor.from_pretrained("reducto/RolmOCR")
    proc.tokenizer.padding_side = "left"
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained("reducto/RolmOCR", torch_dtype=torch.float16,
                                                               device_map="auto", attn_implementation="sdpa")
    vis = getattr(model, "visual", None) or getattr(getattr(model, "model", None), "visual", None)
    vis.to(torch.float32)  # T4: no bf16; keep the vision tower in fp32 against fp16 overflow
    model.eval()
    log(f"model loaded; vision dtype {next(vis.parameters()).dtype}")

    def run(batch):
        imgs = [render(p, i) for p, i in batch]
        msgs = [[{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPT}]}] for _ in batch]
        texts = [proc.apply_chat_template(m, tokenize=False, add_generation_prompt=True) for m in msgs]
        inp = proc(text=texts, images=imgs, return_tensors="pt", padding=True).to(model.device)
        inp["pixel_values"] = inp["pixel_values"].to(torch.float32)
        t = time.time()
        with torch.no_grad():
            out = model.generate(**inp, max_new_tokens=6144, do_sample=True, temperature=0.2)
        gen = out[:, inp["input_ids"].shape[1]:]
        dec = proc.batch_decode(gen, skip_special_tokens=True)
        ntok = [int((g != proc.tokenizer.pad_token_id).sum()) for g in gen]
        return dec, ntok, time.time() - t

    torch.manual_seed(0)
    dec, ntok, sec = run(J[:1])  # preflight
    log(f"preflight 1 page: {sec:.1f}s {ntok[0]} tok, script share {script_share(dec[0]):.2f}, sample {dec[0][:120]!r}")
    if script_share(dec[0]) < 0.3:
        log("preflight output is not script text -> abort (fix locally, do not rerun blind)")
        json.dump(res, open(OUT, "w"), ensure_ascii=False); return
    key = lambda j: f"{os.path.basename(j[0])}|{j[1]}"
    res["pages"][key(J[0])], res["sec"][key(J[0])], res["tokens"][key(J[0])] = dec[0], sec, ntok[0]
    rest, B = J[1:], 6
    for s in range(0, len(rest), B):
        if time.time() - T0 > CAP - 120:
            log("time cap reached"); break
        batch = rest[s:s + B]
        try:
            dec, ntok, sec = run(batch)
        except Exception as e:  # one bad batch never stops the run
            log(f"batch {s} ERROR {e!r}"[:300]); torch.cuda.empty_cache(); continue
        for j, d, n in zip(batch, dec, ntok):
            res["pages"][key(j)], res["sec"][key(j)], res["tokens"][key(j)] = d, sec / len(batch), n
        log(f"batch {s // B}: {len(batch)} pages {sec:.0f}s max_tok {max(ntok)}")
        json.dump(res, open(OUT, "w"), ensure_ascii=False)
    log(f"done: {len(res['pages'])}/{len(J)} pages")
    json.dump(res, open(OUT, "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
