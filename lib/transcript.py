import csv
import os

FIELDNAMES = ['speaker_id', 'segment_id', 'start_time', 'end_time', 'text', 'language', 'confidence']


class Transcript:
    def __init__(self, path):
        self.path = path
        self._rows = {}  # {(segment_id, language): row}

    @classmethod
    def load(cls, path):
        t = cls(path)
        if not os.path.exists(path):
            return t
        with open(path, newline='') as f:
            for row in csv.DictReader(f):
                key = (int(row['segment_id']), row['language'])
                t._rows[key] = row
        return t

    def contains(self, segment_id, language):
        return (segment_id, language) in self._rows

    def needs_transcription(self, segment_id, language):
        row = self._rows.get((segment_id, language))
        if row is None:
            return True
        return float(row['confidence']) < -1.5

    def low_confidence(self, segment_id, language):
        return self.needs_transcription(segment_id, language)

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
            yield by_segment[segment_id]
