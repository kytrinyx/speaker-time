from dataclasses import dataclass, field

from .cue import Cue
from .segment import clean


MAX_CHARS = {"ko": 30, "en": 50, "default": 50}

STRONG_MARKER = '\u23f9'    # ⏹
ORDINARY_MARKER = '\u25cb'  # ○
WEAK_MARKER = '\u2022'      # •

MARKER = {
    'strong': STRONG_MARKER,
    'ordinary': ORDINARY_MARKER,
    'weak': WEAK_MARKER,
}


def merge(segment, split_indices, strong_indices, weak_indices=None, verbose=False, max_chars_by_lang=None):
    return FragmentMerger(segment, split_indices, strong_indices, weak_indices, verbose, max_chars_by_lang).merge()


@dataclass
class MergedChunk:
    boundary: str          # 'first' | 'strong' | 'ordinary' | 'weak'
    parts: list            # list of (list[Word], str | None) — (words, boundary_type_after or None)
    start: float
    end: float


class FragmentMerger:
    """Merge fine-grained split-point chunks back into subtitle cues.

    Two passes:
    1. Greedily merge across weak split points if the combined text fits within
       the character limit.
    2. Emit each remaining chunk as a single cue.
    """

    def __init__(self, segment, split_indices, strong_indices, weak_indices=None, verbose=False, max_chars_by_lang=None):
        self.segment = segment
        self.split_indices = split_indices
        self.strong_indices = strong_indices
        self.weak_indices = weak_indices or []
        self.verbose = verbose
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else MAX_CHARS

    def _plan(self):
        """Return the merge plan as a list of MergedChunk."""
        seg = self.segment
        words = seg.words
        lang = seg.language
        char_limit = self.max_chars_by_lang.get(lang, self.max_chars_by_lang["default"])
        strong_set = set(self.strong_indices)
        weak_set = set(self.weak_indices)

        boundaries = [0] + list(self.split_indices) + [len(words)]
        n = len(boundaries) - 1

        i = 0
        chunks = []
        while i < n:
            chunk_start_i = i
            chunk_start_word = boundaries[i]
            chunk_end_word = boundaries[i + 1]
            parts = [(words[chunk_start_word:chunk_end_word], None)]

            while i + 1 < n:
                next_boundary = boundaries[i + 1]
                if next_boundary in strong_set or next_boundary not in weak_set:
                    break
                next_end_word = boundaries[i + 2]
                combined_text = clean("".join(w.text for w in words[chunk_start_word:next_end_word]).strip(), lang)
                if len(combined_text) <= char_limit:
                    parts[-1] = (parts[-1][0], 'weak')
                    parts.append((words[chunk_end_word:next_end_word], None))
                    chunk_end_word = next_end_word
                    i += 1
                else:
                    break

            if chunk_start_i == 0:
                btype = 'first'
            else:
                b = boundaries[chunk_start_i]
                if b in strong_set:
                    btype = 'strong'
                elif b in weak_set:
                    btype = 'weak'
                else:
                    btype = 'ordinary'

            all_chunk_words = [w for part_words, _ in parts for w in part_words]
            start_t = all_chunk_words[0].start if all_chunk_words else seg.start
            end_t = all_chunk_words[-1].end if all_chunk_words else seg.end

            chunks.append(MergedChunk(boundary=btype, parts=parts, start=start_t, end=end_t))
            i += 1

        # Second pass: merge across ordinary boundaries where combined text fits
        result = []
        for chunk in chunks:
            if chunk.boundary == 'ordinary' and result:
                prev = result[-1]
                all_words = [w for pw, _ in prev.parts for w in pw] + [w for pw, _ in chunk.parts for w in pw]
                combined_text = clean("".join(w.text for w in all_words).strip(), lang)
                if len(combined_text) <= char_limit:
                    new_parts = prev.parts[:-1] + [(prev.parts[-1][0], 'ordinary')] + chunk.parts
                    result[-1] = MergedChunk(
                        boundary=prev.boundary,
                        parts=new_parts,
                        start=prev.start,
                        end=chunk.end,
                    )
                    continue
            result.append(chunk)

        return result

    def __repr__(self):
        seg = self.segment
        lines = [f"Segment {seg.id} ({len(seg.text)} chars)", seg.text, ""]

        if not seg.words:
            for cue in self.merge():
                lines.append(f"- {cue.text}")
            return "\n".join(lines)

        for chunk in self._plan():
            pieces = []
            for part_words, boundary_after in chunk.parts:
                t = clean("".join(w.text for w in part_words).strip(), seg.language)
                if t:
                    pieces.append(t)
                    if boundary_after:
                        pieces.append(f' {MARKER[boundary_after]} ')
            text = "".join(pieces).strip()

            if not text:
                continue

            prefix = '<' if chunk.boundary == 'first' else MARKER[chunk.boundary]
            lines.append(f" {prefix} {text}")

        lines.append(" >")
        return "\n".join(lines)

    def merge(self):
        """Merge fine-grained chunks into cues. Returns: List[Cue]"""
        segment = self.segment
        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        lang = segment.language
        result = []
        for chunk in self._plan():
            all_words = [w for part_words, _ in chunk.parts for w in part_words]
            text = clean("".join(w.text for w in all_words).strip(), lang)
            if text:
                if self.verbose and len(chunk.parts) > 1:
                    part_texts = [clean("".join(w.text for w in pw).strip(), lang) for pw, _ in chunk.parts]
                    print(f"    WEAK MERGE: " + " + ".join(f"{t!r}" for t in part_texts if t))
                if self.verbose:
                    print(f"    CUE: {text!r}")
                result.append(Cue(chunk.start, chunk.end, text))

        return result if result else [Cue(segment.start, segment.end, segment.text)]
