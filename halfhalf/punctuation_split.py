import re

from .cue import Cue
from . import artifacts
from .split_utils import normalize


def split_text_at_punctuation(text):
    """Split text at punctuation followed by whitespace or end of string."""
    parts = re.split(r'(?<=[.?!,])(?=\s|$)', text.strip())
    return [p.strip() for p in parts if p.strip()]


class PunctuationSplit:
    """Split at sentence-ending punctuation (. ? !), using segment.raw_text as the authoritative boundary source."""

    name = "punctuation"

    def find_splits(self, segment):
        """Return word indices into segment.words where new chunks begin."""
        if not segment.words:
            return []

        chunks = split_text_at_punctuation(segment.raw_text)
        if len(chunks) <= 1:
            return []

        full_norm = normalize("".join(w.text for w in segment.words))
        splits = []
        cursor = 0
        first_chunk = True

        for chunk in chunks:
            chunk_norm = normalize(chunk)
            if not chunk_norm:
                continue

            pos = full_norm.find(chunk_norm, cursor)
            if pos == -1:
                pos = cursor
            end_pos = pos + len(chunk_norm)

            if not first_chunk:
                char_pos = 0
                for w_idx, w in enumerate(segment.words):
                    w_norm = normalize(w.text)
                    if char_pos + len(w_norm) > pos:
                        splits.append(w_idx)
                        break
                    char_pos += len(w_norm)

            first_chunk = False
            cursor = end_pos

        return splits

    def split(self, segment):
        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        indices = self.find_splits(segment)
        if not indices:
            return [Cue(segment.start, segment.end, segment.text)]

        boundaries = [0] + indices + [len(segment.words)]
        cues = []
        for start, end in zip(boundaries, boundaries[1:]):
            chunk = segment.words[start:end]
            if chunk:
                text = "".join(w.text for w in chunk).strip()
                cleaned = artifacts.fixup(text, segment.language)
                if cleaned:
                    cues.append(Cue(chunk[0].start, chunk[-1].end, cleaned))

        return cues if cues else [Cue(segment.start, segment.end, segment.text)]
