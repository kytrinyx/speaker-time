import json
import os

from .cue import Cue
from .transcript import Transcript
from . import paths


class Captions:
    def __init__(self, episode_id):
        self.episode_id = episode_id
        self._transcript = Transcript.load(episode_id)
        self._split_cache = {}
        split_path = paths.split_segment_cues(episode_id)
        if os.path.exists(split_path):
            with open(split_path) as f:
                self._split_cache = json.load(f)

    @classmethod
    def load(cls, episode_id):
        return cls(episode_id)

    def __iter__(self):
        for seg in self._transcript:
            text = seg.text
            if seg.low_confidence():
                continue
            cached = self._split_cache.get(str(seg.id))
            if cached:
                for c in cached["cues"]:
                    yield Cue(c["start"], c["end"], c["text"])
            else:
                yield Cue(seg.start, seg.end, text)
