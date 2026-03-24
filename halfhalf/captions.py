import json
import os

from .cue import Cue
from .transcript import Transcript


class Captions:
    def __init__(self, episode_id):
        self.episode_id = episode_id
        self._transcript = Transcript.load(episode_id)
        self._split_cache = {}
        split_path = os.path.join("output", episode_id, "split_segments.json")
        if os.path.exists(split_path):
            with open(split_path) as f:
                self._split_cache = json.load(f)

    @classmethod
    def load(cls, episode_id):
        return cls(episode_id)

    def __iter__(self):
        for row in self._transcript:
            text = row["text"].strip()
            lang = row.get("language", "")
            sid = int(row["segment_id"])
            if not text or text == "[TIMEOUT]" or self._transcript.low_confidence(sid, lang):
                continue
            cached = self._split_cache.get(str(sid))
            if cached:
                for c in cached["cues"]:
                    yield Cue(c["start"], c["end"], c["text"])
            else:
                yield Cue(float(row["start_time"]), float(row["end_time"]), text)
