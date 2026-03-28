import json
import os
import urllib.request

from .cue import Cue
from . import artifacts


class OllamaSplit:
    """Ask a local Ollama model where to split a word list by index, then slice directly."""

    name = "ollama"

    def __init__(self, model="exaone3.5:latest", cache_path=None):
        self.model = model
        self.name = f"ollama({model})"
        self.cache_path = cache_path
        self._cache = {}
        if cache_path and os.path.exists(cache_path):
            with open(cache_path) as f:
                self._cache = json.load(f)

    def _save_cache(self):
        if self.cache_path:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def find_splits(self, segment):
        """Return word indices into segment.words where new chunks begin."""
        if not segment.words:
            return []

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
                cleaned = artifacts.fixup(text, segment.language)
                if cleaned:
                    cues.append(Cue(chunk[0].start, chunk[-1].end, cleaned))

        return cues if cues else [Cue(segment.start, segment.end, segment.text)]
