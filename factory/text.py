"""Tiny word matching helpers for English and Bangla text."""
import re
import unicodedata

_EN = re.compile(r"[a-z]+")
_BN = re.compile(r"[ঀ-৿]+")


def norm(text):
    return unicodedata.normalize("NFC", text.replace("‌", "").replace("‍", ""))


def en_words(text):
    return _EN.findall(text.lower())


def bn_words(text):
    return _BN.findall(norm(text))


def bn_list(s):
    return [norm(x) for x in s.split()]


def count(text, en_exact="", bn_exact="", bn_stems=""):
    """How many words of `text` match: English exact words, Bangla exact words or Bangla word stems."""
    en = set(en_exact.split())
    bx = set(bn_list(bn_exact))
    bs = bn_list(bn_stems)
    n = sum(1 for w in en_words(text) if w in en)
    for w in bn_words(text):
        if w in bx or any(w.startswith(s) for s in bs):
            n += 1
    return n


def has(text, spec):
    return count(text, *spec) > 0
