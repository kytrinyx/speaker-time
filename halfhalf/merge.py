from .cue import Cue
from .segment import clean


MAX_CHARS = {"ko": 22, "en": 42, "default": 42}
READ_SPEEDS = {"ko": 8, "en": 17, "default": 17}


class FragmentMerger:
    """Merge fine-grained split-point chunks back into subtitle cues.

    Applies the Phase 4 rules from LONG_SEGMENTS.md:
    - Default to single-line cues
    - Pair adjacent chunks when one is too brief (< 0.6s) or too dense (> threshold chars/s)
    - Never pair across mandatory split points (major silences ≥ 0.4s)
    - Rebalance paired same-speaker cues at the best phrase boundary
    """

    name = "merge"

    def __init__(self, max_chars_by_lang=None, read_speeds_by_lang=None):
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else MAX_CHARS
        self.read_speeds_by_lang = read_speeds_by_lang if read_speeds_by_lang is not None else READ_SPEEDS

    def merge(self, segment, split_indices, strong_indices, weak_indices=None, verbose=False):
        """Merge fine-grained chunks into cues.

        segment: Segment with .words and .language
        split_indices: sorted list of all word indices where new chunks begin
        strong_indices: subset of split_indices; hard walls merge never crosses
        weak_indices: subset of split_indices; merger greedily collapses these first
        verbose: print pairing decisions to stdout
        Returns: List[Cue]
        """
        words = segment.words
        if not words:
            return [Cue(segment.start, segment.end, segment.text)]

        lang = segment.language
        char_limit = self.max_chars_by_lang.get(lang, self.max_chars_by_lang["default"])
        read_speed = self.read_speeds_by_lang.get(lang, self.read_speeds_by_lang["default"])
        strong_set = set(strong_indices)
        weak_set = set(weak_indices or [])

        boundaries = [0] + list(split_indices) + [len(words)]
        chunks = [words[boundaries[j]:boundaries[j + 1]] for j in range(len(boundaries) - 1)]

        # First pass: greedily merge across weak splits
        if weak_set:
            chunks, boundaries = self._merge_weak(chunks, boundaries, strong_set, weak_set, char_limit, lang, verbose)

        # Second pass: merge brief/dense fragments
        result = []
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            if not chunk:
                i += 1
                continue

            text = clean("".join(w.text for w in chunk).strip(), lang)
            duration = chunk[-1].end - chunk[0].start

            if i + 1 < len(chunks) and boundaries[i + 1] not in strong_set:
                next_chunk = chunks[i + 1]
                if next_chunk:
                    next_text = clean("".join(w.text for w in next_chunk).strip(), lang)
                    too_brief = duration < 0.6
                    too_dense = duration > 0 and len(text) / duration > read_speed
                    if too_brief or too_dense:
                        gap = next_chunk[0].start - chunk[-1].end
                        if len(next_text) <= char_limit and gap < 0.4:
                            reason = "too brief" if too_brief else f"too dense ({len(text)/duration:.1f} chars/s)"
                            if verbose:
                                print(f"    MERGE pair ({reason}): {text!r} + {next_text!r}")
                            result.append(self._make_paired_cue(chunk + next_chunk, lang))
                            i += 2
                            continue

            if text:
                if verbose:
                    print(f"    MERGE single: {text!r}")
                result.append(Cue(chunk[0].start, chunk[-1].end, text))
            i += 1

        return result if result else [Cue(segment.start, segment.end, segment.text)]

    def _merge_weak(self, chunks, boundaries, strong_set, weak_set, char_limit, lang, verbose):
        """First pass: greedily merge adjacent fragments separated by weak splits."""
        new_chunks = []
        new_boundaries = [0]

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
            new_boundaries.append(boundaries[i + 1])
            i += 1

        return new_chunks, new_boundaries

    def _make_paired_cue(self, words, lang):
        """Combine words into a two-line cue, rebalancing at the best phrase boundary."""
        split_idx = self._rebalance_point(words, lang)
        line1 = clean("".join(w.text for w in words[:split_idx]).strip(), lang)
        line2 = clean("".join(w.text for w in words[split_idx:]).strip(), lang)
        if line1 and line2:
            return Cue(words[0].start, words[-1].end, f"{line1}\n{line2}")
        text = clean("".join(w.text for w in words).strip(), lang)
        return Cue(words[0].start, words[-1].end, text)

    def _rebalance_point(self, words, lang):
        """Return the word index closest to the midpoint, using MeCab for Korean."""
        if lang == 'ko':
            idx = self._rebalance_korean(words)
            if idx is not None:
                return idx
        return self._rebalance_english(words)

    def _rebalance_english(self, words):
        """Split at the word boundary closest to the midpoint character count."""
        total = sum(len(w.text.strip()) for w in words)
        mid = total / 2
        cumulative = 0
        best_idx = len(words) // 2
        best_dist = float('inf')
        for i, w in enumerate(words[:-1]):
            cumulative += len(w.text.strip())
            dist = abs(cumulative - mid)
            if dist < best_dist:
                best_dist = dist
                best_idx = i + 1
        return best_idx

    def _rebalance_korean(self, words):
        """Split at the MeCab EC boundary closest to the midpoint word, or None if no EC found."""
        from .mecab_split import _find_split_word_indices, _space_to_whisper_indices
        combined = "".join(w.text for w in words)
        space_indices = _find_split_word_indices(combined)
        if not space_indices:
            return None
        whisper_indices = _space_to_whisper_indices(space_indices, combined, words)
        if not whisper_indices:
            return None
        mid = len(words) / 2
        return min(whisper_indices, key=lambda x: abs(x - mid))
