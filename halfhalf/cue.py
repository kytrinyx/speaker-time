from dataclasses import dataclass


@dataclass
class Cue:
    start: float
    end: float
    text: str

    @staticmethod
    def format_timestamp(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    @property
    def language(self):
        ascii_count = sum(1 for c in self.text if c.isascii() and c.isalpha())
        hangul_count = sum(1 for c in self.text if '\uAC00' <= c <= '\uD7A3' or '\u1100' <= c <= '\u11FF' or '\u3130' <= c <= '\u318F')
        return 'ko' if hangul_count >= ascii_count else 'en'

    def __str__(self):
        return f"{self.format_timestamp(self.start)} --> {self.format_timestamp(self.end)}\n{self.text}"
