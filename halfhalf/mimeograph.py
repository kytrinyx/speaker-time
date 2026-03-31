import json
from dataclasses import dataclass

from . import language
from .word import Word

TERMINAL_PUNCTUATION = {".", "?", "!", "。", "？", "！"}
SILENCE_SPLIT_THRESHOLD = 0.4
SILENCE_STANDARD_THRESHOLD = 0.1


def _word_lang(text):
    """Return 'ko' or 'en' for text with alphabetic content, None otherwise."""
    ascii_count = sum(1 for c in text if c.isascii() and c.isalpha())
    hangul_count = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3' or '\u1100' <= c <= '\u11FF' or '\u3130' <= c <= '\u318F')
    if ascii_count == 0 and hangul_count == 0:
        return None
    return 'ko' if hangul_count >= ascii_count else 'en'


@dataclass
class Fragment:
    words: list

    @property
    def start(self):
        return self.words[0].start

    @property
    def end(self):
        return self.words[-1].end

    @property
    def text(self):
        return " ".join(w.text for w in self.words)

    @property
    def language(self):
        return language.of_text(self.text)

    @property
    def silence_splits(self):
        """Word indices where a gap >= 0.1s occurs (i means start new chunk at words[i])."""
        result = []
        for i in range(len(self.words) - 1):
            gap = self.words[i + 1].start - self.words[i].end
            if gap >= SILENCE_STANDARD_THRESHOLD:
                result.append(i + 1)
        return result


class Mimeograph:
    def __init__(self, words):
        self._words = words

    @classmethod
    def load(cls, path):
        with open(path) as f:
            data = json.load(f)
        words = [
            Word(w["text"], w["start"], w["end"])
            for w in data["words"]
            if w["type"] == "word"
        ]
        return cls(words)

    @property
    def fragments(self):
        result = []
        current = []
        for i, word in enumerate(self._words):
            current.append(word)
            has_terminal_punct = word.text.rstrip()[-1] in TERMINAL_PUNCTUATION
            next_word = self._words[i + 1] if i + 1 < len(self._words) else None
            has_silence = next_word is not None and (next_word.start - word.end) > SILENCE_SPLIT_THRESHOLD
            curr_lang = _word_lang(word.text)
            next_lang = _word_lang(next_word.text) if next_word is not None else None
            has_lang_switch = curr_lang is not None and next_lang is not None and curr_lang != next_lang
            if has_terminal_punct or has_silence or has_lang_switch:
                result.append(Fragment(current))
                current = []
        if current:
            result.append(Fragment(current))
        return result

    def __iter__(self):
        return iter(self._words)

    def __len__(self):
        return len(self._words)
