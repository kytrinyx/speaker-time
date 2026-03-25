import os
import re
import unicodedata
from dataclasses import dataclass

from .cue import Cue
from .segment import Segment, clean
from . import paths

MAX_CHARS = {"ko": 45, "default": 80}


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

    def __init__(self, max_chars_by_lang=None):
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else MAX_CHARS

    def split(self, segment):
        threshold = self.max_chars_by_lang.get(segment.language, self.max_chars_by_lang["default"])
        if len(segment.raw_text) <= threshold:
            return [Cue(segment.start, segment.end, segment.text)]

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
        return merge_short_cues(cues, threshold)


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


class HybridSplit:
    """Punctuation split first; ollama sub-splits cues that are still too long; merge short fragments."""

    def __init__(self, max_chars_by_lang=None, model="exaone3.5:latest", cache_path=None, episode_id=None):
        self.max_chars_by_lang = max_chars_by_lang if max_chars_by_lang is not None else MAX_CHARS
        self._punct = PunctuationSplit(max_chars_by_lang=self.max_chars_by_lang)
        if cache_path is None and episode_id is not None:
            cache_path = paths.ollama_cache(episode_id)
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
