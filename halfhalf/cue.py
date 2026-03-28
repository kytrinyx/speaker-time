from dataclasses import dataclass

from . import language


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
        return language.of_text(self.text)

    def __str__(self):
        return f"{self.format_timestamp(self.start)} --> {self.format_timestamp(self.end)}\n{self.text}"
