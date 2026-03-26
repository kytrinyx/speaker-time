from .cue import Cue
from .segment import clean


MAX_CHARS = {"ko": 30, "en": 50, "default": 50}


class FragmentMerger:
    """Merge fine-grained split-point chunks back into subtitle cues.

    Two passes:
    1. Greedily merge across weak split points if the combined text fits within
       the character limit.
    2. Emit each remaining chunk as a single cue.
    """

    name = "merge"

    def __init__(self, max_chars_by_lang=None):
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else MAX_CHARS

    def merge(self, segment, split_indices, strong_indices, weak_indices=None, verbose=False):
        """Merge fine-grained chunks into cues.

        segment: Segment with .words and .language
        split_indices: sorted list of all word indices where new chunks begin
        strong_indices: subset of split_indices; hard walls merge never crosses
        weak_indices: subset of split_indices; merger greedily collapses these first
        verbose: print merge decisions to stdout
        Returns: List[Cue]
        """
        words = segment.words
        if not words:
            return [Cue(segment.start, segment.end, segment.text)]

        lang = segment.language
        char_limit = self.max_chars_by_lang.get(lang, self.max_chars_by_lang["default"])
        strong_set = set(strong_indices)
        weak_set = set(weak_indices or [])

        boundaries = [0] + list(split_indices) + [len(words)]
        chunks = [words[boundaries[j]:boundaries[j + 1]] for j in range(len(boundaries) - 1)]

        # First pass: greedily merge across weak splits
        if weak_set:
            chunks = self._merge_weak(chunks, boundaries, strong_set, weak_set, char_limit, lang, verbose)

        # Second pass: emit each chunk as a single cue
        result = []
        for chunk in chunks:
            if not chunk:
                continue
            text = clean("".join(w.text for w in chunk).strip(), lang)
            if text:
                if verbose:
                    print(f"    CUE: {text!r}")
                result.append(Cue(chunk[0].start, chunk[-1].end, text))

        return result if result else [Cue(segment.start, segment.end, segment.text)]

    def _merge_weak(self, chunks, boundaries, strong_set, weak_set, char_limit, lang, verbose):
        """First pass: greedily merge adjacent fragments separated by weak splits."""
        new_chunks = []

        i = 0
        while i < len(chunks):
            chunk = chunks[i]

            while (i + 1 < len(chunks) and
                   boundaries[i + 1] in weak_set and
                   boundaries[i + 1] not in strong_set):
                next_chunk = chunks[i + 1]
                combined = chunk + next_chunk
                combined_text = clean("".join(w.text for w in combined).strip(), lang)
                if len(combined_text) <= char_limit:
                    if verbose and chunk and next_chunk:
                        t1 = clean("".join(w.text for w in chunk).strip(), lang)
                        t2 = clean("".join(w.text for w in next_chunk).strip(), lang)
                        print(f"    WEAK MERGE: {t1!r} + {t2!r}")
                    chunk = combined
                    i += 1
                else:
                    break

            new_chunks.append(chunk)
            i += 1

        return new_chunks
