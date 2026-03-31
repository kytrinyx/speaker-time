import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime

from .prompts import translate_ko_en, translate_en_ko

REPLICATE_MODEL = "anthropic/claude-4.5-haiku"
REPLICATE_API_URL = f"https://api.replicate.com/v1/models/{REPLICATE_MODEL}/predictions"
CHUNK_SIZES = [100, 50, 25, 10, 1]

DIRECTIONS = [("ko", "en"), ("en", "ko")]


class Translator:
    """Translate cues in both directions (ko→en and en→ko), with a persistent cache.

    Cache is stored as:
      {
        "ko-en": { "<source text>": "<translation>", ... },
        "en-ko": { "<source text>": "<translation>", ... }
      }
    """

    def __init__(self, cohost, cache_path):
        self._cohost = cohost
        self._cache_path = cache_path
        self._cache = {"ko-en": {}, "en-ko": {}}
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                self._cache = json.load(f)

    def translate(self, cues):
        """Translate all cues for both directions, retrying with smaller chunks on failure.

        Returns a dict of still-missing texts per direction, e.g.:
          {"ko-en": ["text1", ...], "en-ko": []}
        """
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        logs_dir = os.path.join(os.path.dirname(self._cache_path), "..", "logs")
        still_missing = {}

        for source_lang, target_lang in DIRECTIONS:
            direction = f"{source_lang}-{target_lang}"
            direction_cache = self._cache.setdefault(direction, {})
            all_lines = [c.text for c in cues if c.language == source_lang]

            for chunk_size in CHUNK_SIZES:
                uncached = [line for line in all_lines if line not in direction_cache]
                if not uncached:
                    break

                label = "individual" if chunk_size == 1 else f"chunks of {chunk_size}"
                print(f"Translating {direction} ({label}): {len(uncached)} remaining")
                chunks = [uncached[i:i + chunk_size] for i in range(0, len(uncached), chunk_size)]

                for idx, chunk in enumerate(chunks):
                    log_path = os.path.join(logs_dir, f"translate-{direction}.{ts}.json")
                    bad_json_path = os.path.join(logs_dir, f"translate-{direction}.{chunk_size}.{idx + 1}.{ts}.bad.json")
                    try:
                        translated = self._translate_chunk(chunk, source_lang, target_lang, log_path, bad_json_path)
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"  Warning: chunk {idx + 1} failed ({e}), will retry")
                        continue
                    for source, result in zip(chunk, translated):
                        direction_cache[source] = result
                    self._save()

            missing = [line for line in all_lines if line not in direction_cache]
            if missing:
                print(f"  Warning: {len(missing)} {direction} translation(s) missing after all retries")
                for line in missing:
                    print(f"    - {line!r}")
            still_missing[direction] = missing

        return still_missing

    def missing(self, cues):
        """Return dict of untranslated texts per direction."""
        result = {}
        for source_lang, target_lang in DIRECTIONS:
            direction = f"{source_lang}-{target_lang}"
            cache = self._cache.get(direction, {})
            result[direction] = [c.text for c in cues if c.language == source_lang and c.text not in cache]
        return result

    def lookup(self, text, source_lang, target_lang):
        """Return the cached translation for a given text and direction, or None."""
        return self._cache.get(f"{source_lang}-{target_lang}", {}).get(text)

    def _save(self):
        os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
        with open(self._cache_path, "w") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def _translate_chunk(self, lines, source_lang, target_lang, log_path, bad_json_path):
        payload = [{"id": i + 1, "text": text} for i, text in enumerate(lines)]
        n = len(lines)
        payload_json = json.dumps(payload, ensure_ascii=False)

        if source_lang == "ko":
            prompt = translate_ko_en(self._cohost, n, payload_json)
        else:
            prompt = translate_en_ko(self._cohost, n, payload_json)

        text = self._call_replicate(prompt).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            from json_repair import repair_json
            result = repair_json(text, return_objects=True)
            if isinstance(result, list) and any(isinstance(el, list) for el in result):
                flat = []
                for el in result:
                    if isinstance(el, list):
                        flat.extend(el)
                    elif isinstance(el, dict):
                        flat.append(el)
                result = flat
            if not (isinstance(result, list) and all(isinstance(el, dict) for el in result)):
                os.makedirs(os.path.dirname(bad_json_path), exist_ok=True)
                with open(bad_json_path, "w") as f:
                    f.write(text)
                raise

        seen_ids = set()
        duplicate_ids = set()
        for item in result:
            if item["id"] in seen_ids:
                duplicate_ids.add(item["id"])
            seen_ids.add(item["id"])

        translated = {item["id"]: item["text"] for item in result if item["id"] not in duplicate_ids}
        expected_ids = set(range(1, n + 1))
        missing = sorted(expected_ids - set(translated.keys()))

        if duplicate_ids or missing:
            parts = []
            if duplicate_ids:
                parts.append(f"duplicate ids: {sorted(duplicate_ids)}")
            if missing:
                parts.append(f"missing ids: {missing}")
            parts.append(f"sent {n}, got {len(result)} back")
            log_entry = {"payload": payload, "response": result, "mismatch": "; ".join(parts)}
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w") as f:
                json.dump(log_entry, f, ensure_ascii=False, indent=2)
            raise ValueError(f"chunk mismatch (see {log_path})")

        return [translated[i + 1] for i in range(n)]

    def _call_replicate(self, prompt):
        api_key = os.environ.get("REPLICATE_API_TOKEN")
        if not api_key:
            raise RuntimeError("REPLICATE_API_TOKEN not set")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = json.dumps({"input": {"prompt": prompt, "max_tokens": 16384}}).encode("utf-8")
        req = urllib.request.Request(REPLICATE_API_URL, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        prediction_id = data["id"]
        poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"

        while True:
            req = urllib.request.Request(poll_url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            status = data["status"]
            if status == "succeeded":
                return "".join(data["output"])
            elif status == "failed":
                raise RuntimeError(f"Replicate prediction failed: {data.get('error')}")
            time.sleep(1)
