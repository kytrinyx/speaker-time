import re

from .corrections import apply as apply_corrections


def _collapse(text, language):
    if language == "ko":
        text = re.sub(r'([\uAC00-\uD7A3])\1{4,}', r'\1\1\1', text)
    return re.sub(r'[Mm]{3,}', 'Mmm', text)


def _is_filler(text, language):
    text = text.strip()
    if language == "ko":
        return bool(re.fullmatch(r'[\u3130-\u318F아어고으\s]+', text))
    return bool(re.fullmatch(r'[hH][aAeE]+([hH][aAeE]*)*[\s!.]*', text))


def fixup(text, language):
    t = text.strip()
    if t == "[TIMEOUT]":
        return ""
    t = apply_corrections(t).strip()
    t = _collapse(t, language)
    if not t or _is_filler(t, language):
        return ""
    return t
