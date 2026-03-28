from .cue import Cue
from .segment import clean
from .punctuation_split import PunctuationSplit
from .silence_split import SilenceSplit
from .mecab_split import MecabSplit
from .spacy_split import SpacySplit
from .ollama_split import OllamaSplit
from . import fragment_merger
from .fragment_merger import MAX_CHARS as MERGE_MAX_CHARS
from . import paths

class SegmentSplitter:
    """Orchestrate all splitters and merge into subtitle cues.

    Phase 3+4 from LONG_SEGMENTS.md:
    1. Collect split points from PunctuationSplit, SilenceSplit, and MecabSplit
    2. Fall back to OllamaSplit if any fragment still exceeds the character limit
    3. Merge fine-grained chunks into cues via FragmentMerger
    """

    name = "segment_splitter"

    def __init__(self, silences, model="exaone3.5:latest", cache_path=None, episode_id=None, max_chars_by_lang=None, verbose=False):
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else MERGE_MAX_CHARS
        self.verbose = verbose
        self._punct = PunctuationSplit()
        self._silence = SilenceSplit(silences)
        self._mecab = MecabSplit()
        self._spacy = SpacySplit()
        if cache_path is None and episode_id is not None:
            cache_path = paths.segment_breakpoints(episode_id)
        self._ollama = OllamaSplit(model=model, cache_path=cache_path)

    def split(self, segment):
        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        char_limit = self.max_chars_by_lang.get(segment.language, self.max_chars_by_lang["default"])
        is_long = len(segment.text) > char_limit

        if self.verbose and is_long:
            print(f"\n=== Segment {segment.id} [{segment.start:.2f}s-{segment.end:.2f}s] lang={segment.language} ({len(segment.text)} chars) ===")
            print(f"  {segment.text!r}")

        punct_splits = self._punct.find_splits(segment)
        silence_result = self._silence.find_splits(segment)
        strong_splits = silence_result['strong']
        silence_standard = silence_result['standard']
        mecab_result = self._mecab.find_splits(segment)
        mecab_standard = mecab_result['standard']
        mecab_weak = mecab_result['weak']
        spacy_result = self._spacy.find_splits(segment)
        spacy_standard = spacy_result['standard']
        weak_splits = sorted(set(spacy_result['weak'] + mecab_weak))

        if self.verbose and is_long:
            print(f"  PUNCT:    {punct_splits} → {self._fragments(segment, punct_splits)}")
            print(f"  SILENCE:  strong={strong_splits} standard={silence_standard}")
            print(f"  MECAB:    standard={mecab_standard} weak={mecab_weak}")
            print(f"  SPACY:    standard={spacy_standard} weak={spacy_result['weak']}")

        all_splits = sorted(set(punct_splits + silence_standard + mecab_standard + spacy_standard + weak_splits))

        if self.verbose and is_long:
            print(f"  COMBINED: {all_splits} → {self._fragments(segment, all_splits)}")

        if self._any_fragment_too_long(segment, all_splits, char_limit):
            ollama_splits = self._ollama.find_splits(segment)
            if self.verbose and is_long:
                added = sorted(set(ollama_splits) - set(all_splits))
                print(f"  OLLAMA:   triggered → added {added}")
            all_splits = sorted(set(all_splits + ollama_splits))
        elif self.verbose and is_long:
            print(f"  OLLAMA:   not needed")

        cues = fragment_merger.merge(segment, all_splits, strong_splits, weak_splits, verbose=self.verbose and is_long, max_chars_by_lang=self.max_chars_by_lang)

        if self.verbose and is_long:
            print(f"  FINAL ({len(cues)} cues):")
            for c in cues:
                print(f"    [{c.start:.2f}-{c.end:.2f}] {c.text!r}")

        return cues

    def _fragments(self, segment, split_indices):
        words = segment.words
        boundaries = [0] + list(split_indices) + [len(words)]
        result = []
        for start, end in zip(boundaries, boundaries[1:]):
            chunk = words[start:end]
            if chunk:
                result.append(clean("".join(w.text for w in chunk).strip(), segment.language))
        return result

    def _any_fragment_too_long(self, segment, split_indices, char_limit):
        words = segment.words
        boundaries = [0] + list(split_indices) + [len(words)]
        for start, end in zip(boundaries, boundaries[1:]):
            chunk = words[start:end]
            if chunk and len(clean("".join(w.text for w in chunk).strip(), segment.language)) > char_limit:
                return True
        return False


