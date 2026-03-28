from dataclasses import dataclass, field
from typing import Optional

from . import artifacts
from . import language
from .corrections import SegmentOverride
from .word import Word  # noqa: F401 — re-exported for callers that import Word from here


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
    override: Optional[SegmentOverride] = None
    text: str = field(init=False)

    def __post_init__(self):
        if self.override and self.override.source == self.cleaned_text:
            self.text = self.override.text
        else:
            self.text = self.cleaned_text

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
        return artifacts.fixup(self.raw_text, self.language)

    @property
    def derived_language(self):
        return language.of_text(self.text)

    def low_confidence(self):
        return self.confidence < -1.5
