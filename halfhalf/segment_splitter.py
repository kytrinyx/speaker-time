import os

from .cue import Cue
from .segment import Segment, clean
from .punctuation_split import PunctuationSplit
from .silence_split import SilenceSplit
from .mecab_split import MecabSplit
from .spacy_split import SpacySplit
from .merge import FragmentMerger, MAX_CHARS as MERGE_MAX_CHARS
from . import paths

MAX_CHARS = {"ko": 45, "default": 80}


class OllamaSplit:
    """Ask a local Ollama model where to split a word list by index, then slice directly."""

    name = "ollama"

    def __init__(self, model="exaone3.5:latest", cache_path=None):
        self.model = model
        self.name = f"ollama({model})"
        self.cache_path = cache_path
        self._cache = {}
        if cache_path and os.path.exists(cache_path):
            import json
            with open(cache_path) as f:
                self._cache = json.load(f)

    def _save_cache(self):
        if self.cache_path:
            import json
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def find_splits(self, segment):
        """Return word indices into segment.words where new chunks begin."""
        if not segment.words:
            return []

        import urllib.request, json

        source = segment.raw_text
        if source in self._cache:
            split_points = self._cache[source]
        else:
            numbered = "\n".join(f"{i}: {w.text.strip()}" for i, w in enumerate(segment.words))
            prompt = (
                "The following is a numbered list of words from a speech transcript.\n"
                "Return all natural clause and phrase boundaries as a comma-separated list "
                "of word indices where a new phrase begins. Include every possible boundary, "
                "not just major splits. Do not include 0. Do not explain.\n\n"
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
                return []

            self._cache[source] = split_points
            self._save_cache()

        n = len(segment.words)
        return [i for i in split_points if 0 < i < n]

    def split(self, segment):
        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        import urllib.request, json

        source = segment.raw_text
        if source in self._cache:
            split_points = self._cache[source]
        else:
            numbered = "\n".join(f"{i}: {w.text.strip()}" for i, w in enumerate(segment.words))
            prompt = (
                "The following is a numbered list of words from a speech transcript.\n"
                "Return all natural clause and phrase boundaries as a comma-separated list "
                "of word indices where a new phrase begins. Include every possible boundary, "
                "not just major splits. Do not include 0. Do not explain.\n\n"
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

            self._cache[source] = split_points
            self._save_cache()

        # Filter to valid indices and build slice boundaries
        n = len(segment.words)
        boundaries = [0] + [i for i in split_points if 0 < i < n] + [n]

        cues = []
        for start, end in zip(boundaries, boundaries[1:]):
            chunk = segment.words[start:end]
            if chunk:
                text = "".join(w.text for w in chunk).strip()
                cleaned = clean(text, segment.language)
                if cleaned:
                    cues.append(Cue(chunk[0].start, chunk[-1].end, cleaned))

        return cues if cues else [Cue(segment.start, segment.end, segment.text)]


def merge_short_cues(cues, threshold):
    """Merge adjacent cues if their combined length fits within the threshold."""
    if not cues:
        return cues
    result = [cues[0]]
    for cue in cues[1:]:
        prev = result[-1]
        merged_text = prev.text + " " + cue.text
        if len(merged_text) <= threshold:
            result[-1] = Cue(prev.start, cue.end, merged_text)
        else:
            result.append(cue)
    return result


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
        self._merge = FragmentMerger(max_chars_by_lang=self.max_chars_by_lang)
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

        cues = self._merge.merge(segment, all_splits, strong_splits, weak_splits, verbose=self.verbose and is_long)

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


class HybridSplit:
    """Punctuation split first; ollama sub-splits cues that are still too long; merge short fragments."""

    def __init__(self, max_chars_by_lang=None, model="exaone3.5:latest", cache_path=None, episode_id=None):
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else MAX_CHARS
        self._punct = PunctuationSplit()
        if cache_path is None and episode_id is not None:
            cache_path = paths.segment_breakpoints(episode_id)
        self._ollama = OllamaSplit(model=model, cache_path=cache_path)
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
                mini = Segment(
                    id=segment.id,
                    start=cue.start,
                    end=cue.end,
                    raw_text=cue.text,
                    language=segment.language,
                    words=cue_words,
                )
                sub_cues = self._ollama.split(mini)
                expanded.extend(merge_short_cues(sub_cues, threshold))
            else:
                expanded.append(cue)

        return expanded
