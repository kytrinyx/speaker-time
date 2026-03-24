import re
import unicodedata
from dataclasses import dataclass, field

from .cue import Cue


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class TranscriptionSegment:
    id: int
    start: float
    end: float
    text: str
    language: str
    words: list = field(default_factory=list)

    def is_filler(self):
        if self.language == "ko":
            return bool(re.fullmatch(r'[ㅋㅎ아어고으\s]+', self.text))
        return bool(re.fullmatch(r'[hH][aAeE]+([hH][aAeE]*)*[\s!.]*', self.text))


def normalize(s):
    s = unicodedata.normalize("NFC", s)
    return ''.join(c for c in s if not unicodedata.category(c).startswith('P') and not c.isspace()).lower()


def split_text_at_punctuation(text):
    """Split text at sentence boundaries (.?!), treating ... as a single unit."""
    chunks = re.findall(r'[^.?!]+(?:[.?!]+|$)', text.strip())
    return [c.strip() for c in chunks if c.strip()]


def words_to_cue(words, fallback_start, fallback_end):
    text = "".join(w.text for w in words).strip()
    start = words[0].start if words else fallback_start
    end = words[-1].end if words else fallback_end
    return Cue(start, end, text)


class PunctuationSplit:
    """Split at sentence-ending punctuation (. ? !), using segment.text as the authoritative boundary source."""

    name = "punctuation"

    def split(self, segment):
        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        chunks = split_text_at_punctuation(segment.text)
        if len(chunks) <= 1:
            return [Cue(segment.start, segment.end, segment.text)]

        # Build normalized concatenation of all word tokens for cursor alignment
        full_norm = normalize("".join(w.text for w in segment.words))

        cues = []
        cursor = 0  # position in full_norm

        for chunk in chunks:
            chunk_norm = normalize(chunk)
            if not chunk_norm:
                continue

            pos = full_norm.find(chunk_norm, cursor)
            if pos == -1:
                pos = cursor  # fallback: use current position
            end_pos = pos + len(chunk_norm)

            # Collect words whose normalized span overlaps [pos, end_pos)
            char_pos = 0
            chunk_words = []
            for w in segment.words:
                w_norm = normalize(w.text)
                w_start, w_end = char_pos, char_pos + len(w_norm)
                if w_end > pos and w_start < end_pos:
                    chunk_words.append(w)
                char_pos = w_end

            if chunk_words:
                cues.append(words_to_cue(chunk_words, segment.start, segment.end))
            cursor = end_pos

        return cues if cues else [Cue(segment.start, segment.end, segment.text)]


class OllamaSplit:
    """Ask a local Ollama model where to split a word list by index, then slice directly."""

    name = "ollama"

    def __init__(self, model="exaone3.5:latest"):
        self.model = model
        self.name = f"ollama({model})"

    def split(self, segment):
        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        import urllib.request, json

        numbered = "\n".join(f"{i}: {w.text.strip()}" for i, w in enumerate(segment.words))
        prompt = (
            "The following is a numbered list of words from a speech transcript.\n"
            "Return only the indices where a new clause should begin (i.e. split points), "
            "as a comma-separated list of integers. Do not include 0. Do not explain.\n\n"
            f"{numbered}"
        )

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())

        raw = result["response"].strip()
        try:
            split_points = sorted(set(
                int(x.strip()) for x in raw.split(",")
                if x.strip().isdigit()
            ))
        except ValueError:
            return [Cue(segment.start, segment.end, segment.text)]

        # Filter to valid indices and build slice boundaries
        n = len(segment.words)
        boundaries = [0] + [i for i in split_points if 0 < i < n] + [n]

        cues = []
        for start, end in zip(boundaries, boundaries[1:]):
            chunk = segment.words[start:end]
            if chunk:
                cues.append(words_to_cue(chunk, segment.start, segment.end))

        return cues if cues else [Cue(segment.start, segment.end, segment.text)]


class HybridSplit:
    """Punctuation split first; ollama sub-splits cues that are still too long; merge short fragments."""

    def __init__(self, max_chars_by_lang=None, min_chars=20, model="exaone3.5:latest"):
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else {"ko": 45, "default": 80}
        self.min_chars = min_chars
        self._punct = PunctuationSplit()
        self._ollama = OllamaSplit(model=model)
        parts = ", ".join(f"{k}={v}" for k, v in self.max_chars_by_lang.items())
        self.name = f"hybrid({parts})"

    def split(self, segment):
        cues = self._punct.split(segment)

        # Sub-split any cue that's still over the threshold
        expanded = []
        for cue in cues:
            threshold = self.max_chars_by_lang.get(segment.language, self.max_chars_by_lang["default"])
            if len(cue.text) > threshold:
                cue_words = [w for w in segment.words
                             if w.end > cue.start and w.start < cue.end]
                mini = TranscriptionSegment(segment.id, cue.start, cue.end, cue.text,
                               segment.language, cue_words)
                sub_cues = self._ollama.split(mini)
                expanded.extend(self._merge_short(sub_cues))
            else:
                expanded.append(cue)

        return expanded

    def _merge_short(self, cues):
        if not cues:
            return cues
        result = [cues[0]]
        for cue in cues[1:]:
            prev = result[-1]
            if len(prev.text) < self.min_chars:
                result[-1] = Cue(prev.start, cue.end, prev.text + " " + cue.text)
            else:
                result.append(cue)
        # merge trailing short cue back into predecessor
        if len(result) > 1 and len(result[-1].text) < self.min_chars:
            last = result.pop()
            result[-1] = Cue(result[-1].start, last.end, result[-1].text + " " + last.text)
        return result
