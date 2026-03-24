import re
from dataclasses import dataclass, field
from typing import Optional

from .corrections import apply as apply_corrections
from .word import Word  # noqa: F401 — re-exported for callers that import Word from here


@dataclass
class Override:
    source: str
    text: str


def _collapse(text, language):
    if language == "ko":
        text = re.sub(r'([\uAC00-\uD7A3])\1{4,}', r'\1\1\1', text)
    return re.sub(r'[Mm]{3,}', 'Mmm', text)


def _is_filler(text, language):
    text = text.strip()
    if language == "ko":
        return bool(re.fullmatch(r'[\u3130-\u318F아어고으\s]+', text))
    return bool(re.fullmatch(r'[hH][aAeE]+([hH][aAeE]*)*[\s!.]*', text))


def clean(text, language):
    t = text.strip()
    if t == "[TIMEOUT]":
        return ""
    t = apply_corrections(t).strip()
    t = _collapse(t, language)
    if not t or _is_filler(t, language):
        return ""
    return t


@dataclass
class Segment:
    id: int
    start: float
    end: float
    raw_text: str
    language: str
    confidence: float = 0.0
    speaker_id: str = ""
    words: list = field(default_factory=list)
    override: Optional[Override] = None

    @classmethod
    def from_dict(cls, row, override=None):
        return cls(
            id=int(row['segment_id']),
            start=float(row['start_time']),
            end=float(row['end_time']),
            raw_text=row['text'],
            language=row['language'],
            confidence=float(row['confidence']),
            speaker_id=row['speaker_id'],
            override=override,
        )

    @property
    def cleaned_text(self):
        return clean(self.raw_text, self.language)

    @property
    def text(self):
        if self.override and self.override.source == self.cleaned_text:
            return self.override.text
        return self.cleaned_text

    def low_confidence(self):
        return self.confidence < -1.5
