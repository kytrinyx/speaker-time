import json
import os
import time
import urllib.request

REPLICATE_MODEL = "anthropic/claude-4.5-haiku"
REPLICATE_API_URL = f"https://api.replicate.com/v1/models/{REPLICATE_MODEL}/predictions"


class LLMSplit:
    """Ask Claude Haiku (via Replicate) where to split a Fragment by word index.

    Uses fragment.text as the cache key. Only triggered when other splitters
    leave chunks that still exceed the character limit.
    """

    name = "llm"

    def __init__(self, cache_path=None):
        self.cache_path = cache_path
        self._cache = {}
        if cache_path and os.path.exists(cache_path):
            with open(cache_path) as f:
                self._cache = json.load(f)

    def find_splits(self, fragment):
        """Return word indices into fragment.words where new chunks begin."""
        if not fragment.words:
            return []

        source = fragment.text
        if source in self._cache:
            return [i for i in self._cache[source] if 0 < i < len(fragment.words)]

        numbered = "\n".join(f"{i}: {w.text.strip()}" for i, w in enumerate(fragment.words))
        prompt = (
            "The following is a numbered list of words from a speech transcript.\n"
            "Return all natural clause and phrase boundaries as a comma-separated list "
            "of word indices where a new phrase begins. Include every possible boundary, "
            "not just major splits. Do not include 0. Do not explain.\n\n"
            f"{numbered}"
        )

        raw = self._call_replicate(prompt)
        try:
            split_points = sorted(set(
                int(x.strip()) for x in raw.split(",")
                if x.strip().isdigit()
            ))
        except ValueError:
            return []

        self._cache[source] = split_points
        self._save_cache()

        n = len(fragment.words)
        return [i for i in split_points if 0 < i < n]

    def _call_replicate(self, prompt):
        api_key = os.environ.get("REPLICATE_API_TOKEN")
        if not api_key:
            raise RuntimeError("REPLICATE_API_TOKEN not set")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = json.dumps({"input": {"prompt": prompt, "max_tokens": 1024}}).encode()
        req = urllib.request.Request(REPLICATE_API_URL, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

        prediction_id = data["id"]
        poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"

        while True:
            req = urllib.request.Request(poll_url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
            if data["status"] == "succeeded":
                return "".join(data["output"]).strip()
            elif data["status"] == "failed":
                raise RuntimeError(f"Replicate prediction failed: {data.get('error')}")
            time.sleep(1)

    def _save_cache(self):
        if self.cache_path:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
