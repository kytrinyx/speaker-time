import re
import unicodedata

from .cue import Cue
from .segment import clean


def normalize(s):
    s = unicodedata.normalize("NFC", s)
    return ''.join(c for c in s if not unicodedata.category(c).startswith('P') and not c.isspace()).lower()


def split_text_at_punctuation(text):
    """Split text at sentence boundaries - punctuation followed by whitespace or end of string."""
    parts = re.split(r'(?<=[.?!])(?=\s|$)', text.strip())
    return [p.strip() for p in parts if p.strip()]


class PunctuationSplit:
    """Split at sentence-ending punctuation (. ? !), using segment.raw_text as the authoritative boundary source."""

    name = "punctuation"

    def split(self, segment):
        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        chunks = split_text_at_punctuation(segment.raw_text)
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
                cleaned = clean(chunk, segment.language)
                if cleaned:
                    cues.append(Cue(chunk_words[0].start, chunk_words[-1].end, cleaned))
            cursor = end_pos

        if not cues:
            return [Cue(segment.start, segment.end, segment.text)]
        return cues
