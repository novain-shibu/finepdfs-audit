"""Fresh2 held-out texts (FINDINGS sec 17 amendment): wikimedia/wikipedia 20231101 offsets 1000/5000/17000, 5 rows, same
doc_text() as make_data.py, paced 5 s. Writes word_test/fresh2_<lang>_<a|b|c>.txt."""
from pathlib import Path
import make_data as M
for lang in M.LANGS:
    for tag, off in (("a", 1000), ("b", 5000), ("c", 17000)):
        Path(f"word_test/fresh2_{lang}_{tag}.txt").write_text(M.doc_text(M.rows(lang, off, 5)), encoding="utf-8")
    print(lang, "done", flush=True)
