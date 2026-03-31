from .cue import Cue
from .en_split import EnSplit
from .ko_split import KoSplit
from .llm_split import LLMSplit

MAX_CHARS = {"ko": 30, "en": 50, "default": 50}


class FragmentSplitter:
    """Split a Fragment into subtitle Cues.

    For fragments within the character limit, emits a single Cue.
    For longer fragments, collects split points from silence gaps and
    language-specific splitters (KoSplit / EnSplit), then merges the
    resulting chunks into cues via a two-pass greedy merge.

    Falls back to the injected fallback splitter (default: OllamaSplit)
    only when a sub-chunk still exceeds the character limit after all
    other strategies have been applied.
    """

    def __init__(self, fallback=None, cache_path=None, max_chars_by_lang=None):
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else MAX_CHARS
        self._ko = KoSplit()
        self._en = EnSplit()
        self._fallback = fallback if fallback is not None else LLMSplit(cache_path=cache_path)

    def split(self, fragment):
        """Return a list of Cues for the given Fragment."""
        if not fragment.words:
            return []

        char_limit = self.max_chars_by_lang.get(fragment.language, self.max_chars_by_lang["default"])

        if len(fragment.text) <= char_limit:
            return [Cue(fragment.start, fragment.end, fragment.text)]

        lang_result = self._ko.find_splits(fragment) if fragment.language == 'ko' else self._en.find_splits(fragment)

        ordinary = sorted(set(fragment.silence_splits + lang_result['standard']))
        weak = sorted(set(lang_result['weak']) - set(ordinary))
        all_splits = sorted(set(ordinary) | set(weak))

        if self._any_too_long(fragment, all_splits, char_limit):
            fallback_splits = self._fallback.find_splits(fragment)
            all_splits = sorted(set(all_splits) | set(fallback_splits))

        return self._merge(fragment, all_splits, set(ordinary), set(weak), char_limit)

    def _any_too_long(self, fragment, split_indices, char_limit):
        words = fragment.words
        boundaries = [0] + list(split_indices) + [len(words)]
        for start, end in zip(boundaries, boundaries[1:]):
            chunk = words[start:end]
            if chunk and len(" ".join(w.text for w in chunk)) > char_limit:
                return True
        return False

    def _merge(self, fragment, split_indices, ordinary_set, weak_set, char_limit):
        words = fragment.words
        boundaries = [0] + list(split_indices) + [len(words)]
        n = len(boundaries) - 1

        # Pass 1: greedily merge across pure-weak boundaries
        chunks = []
        i = 0
        while i < n:
            chunk_start = boundaries[i]
            chunk_end = boundaries[i + 1]

            while i + 1 < n:
                next_boundary = boundaries[i + 1]
                if next_boundary not in weak_set:
                    break
                next_end = boundaries[i + 2]
                combined = " ".join(w.text for w in words[chunk_start:next_end])
                if len(combined) <= char_limit:
                    chunk_end = next_end
                    i += 1
                else:
                    break

            btype = 'ordinary' if boundaries[i] in ordinary_set else 'first' if i == 0 else 'weak'
            chunks.append((chunk_start, chunk_end, btype))
            i += 1

        # Pass 2: merge across ordinary boundaries if combined text fits
        result = []
        for chunk_start, chunk_end, btype in chunks:
            if btype == 'ordinary' and result:
                prev_start, prev_end, prev_btype = result[-1]
                combined = " ".join(w.text for w in words[prev_start:chunk_end])
                if len(combined) <= char_limit:
                    result[-1] = (prev_start, chunk_end, prev_btype)
                    continue
            result.append((chunk_start, chunk_end, btype))

        cues = []
        for start, end, _ in result:
            chunk = words[start:end]
            if chunk:
                text = " ".join(w.text for w in chunk)
                if text:
                    cues.append(Cue(chunk[0].start, chunk[-1].end, text))

        return cues if cues else [Cue(fragment.start, fragment.end, fragment.text)]
