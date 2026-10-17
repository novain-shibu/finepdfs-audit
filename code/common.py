"""Shared helpers for the audit/scoring scripts (same definitions as used in the original runs)."""
import re
import unicodedata

BLOCK = {"Taml": 0x0B80, "Mlym": 0x0D00, "Telu": 0x0C00, "Knda": 0x0C80, "Deva": 0x0900, "Beng": 0x0980}


def words(t):
    """Word split used for exact-word recall (NFC; splits on space, danda and common punctuation)."""
    return [w for w in re.split(r"[\s।॥.,;:!?()\[\]\"'“”‘’\-–—/]+", unicodedata.normalize("NFC", t)) if w]


def swords(t, base):
    """Script words (>= 2 chars) of one Unicode block, NFC, ZWNJ/ZWJ stripped (used by the two-reader check)."""
    t = unicodedata.normalize("NFC", t).replace("‌", "").replace("‍", "")
    return [w for w in re.findall(f"[\\u{base:04x}-\\u{base + 0x7F:04x}]+", t) if len(w) >= 2]
