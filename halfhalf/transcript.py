import csv
import json
import os
import re

from .corrections import apply as apply_corrections


def _is_filler(text, lang):
    if lang == "ko":
        return bool(re.fullmatch(r'[\u3130-\u318F아어고으\s]+', text))
    return bool(re.fullmatch(r'[hH][aAeE]+([hH][aAeE]*)*[\s!.]*', text))


def _collapse_korean(text):
    return re.sub(r'([\uAC00-\uD7A3])\1{4,}', r'\1\1\1', text)

FIELDNAMES = ['speaker_id', 'segment_id', 'start_time', 'end_time', 'text', 'language', 'confidence']


class Transcript:
    def __init__(self, episode_id):
        self.episode_id = episode_id
        self.path = os.path.join("output", episode_id, "transcription.csv")
        self._corrections_path = os.path.join("output", episode_id, "intro_outro_corrections.json")
        self._rows = {}  # {(segment_id, language): row}
        self._intro_outro_corrections = {}  # {segment_id: corrected_text}

    @classmethod
    def load(cls, episode_id):
        t = cls(episode_id)
        if not os.path.exists(t.path):
            return t
        with open(t.path, newline='') as f:
            for row in csv.DictReader(f):
                key = (int(row['segment_id']), row['language'])
                t._rows[key] = row
        if os.path.exists(t._corrections_path):
            with open(t._corrections_path) as f:
                t._intro_outro_corrections = {int(k): v for k, v in json.load(f).items()}
        return t

    @property
    def corrections_path(self):
        return self._corrections_path

    def get(self, segment_id, language):
        return self._rows.get((segment_id, language))

    def contains(self, segment_id, language):
        return (segment_id, language) in self._rows

    def needs_transcription(self, segment_id, language):
        if self.contains(segment_id, language):
            return False
        for (sid, lang), row in self._rows.items():
            if sid == segment_id and not self.low_confidence(sid, lang):
                return False
        return True

    def low_confidence(self, segment_id, language):
        row = self._rows.get((segment_id, language))
        if row is None:
            return False
        return float(row['confidence']) < -1.5

    def upsert(self, row):
        key = (int(row['segment_id']), row['language'])
        self._rows[key] = row

    def save(self):
        rows = sorted(self._rows.values(), key=lambda r: (int(r['segment_id']), r['language']))
        with open(self.path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    def __iter__(self):
        by_segment = {}
        for (segment_id, _), row in self._rows.items():
            if segment_id not in by_segment or float(row['confidence']) > float(by_segment[segment_id]['confidence']):
                by_segment[segment_id] = row
        for segment_id in sorted(by_segment):
            row = dict(by_segment[segment_id])
            row['text'] = apply_corrections(row['text'])
            if segment_id in self._intro_outro_corrections:
                row['text'] = self._intro_outro_corrections[segment_id]
            lang = row.get('language', '')
            if lang == 'ko':
                row['text'] = _collapse_korean(row['text'])
            if _is_filler(row['text'].strip(), lang):
                continue
            yield row
