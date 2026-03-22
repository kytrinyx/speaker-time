import csv
import os

FIELDNAMES = ['segment_id', 'language', 'word_index', 'word', 'start_time', 'end_time', 'probability']


class Words:
    def __init__(self, path):
        self.path = path
        self._rows = []

    @classmethod
    def load(cls, path):
        w = cls(path)
        if not os.path.exists(path):
            return w
        with open(path, newline='') as f:
            for row in csv.DictReader(f):
                row.setdefault('language', '')
                w._rows.append(row)
        return w

    def upsert_segment(self, segment_id, new_words, languages):
        self._rows = [
            row for row in self._rows
            if not (int(row['segment_id']) == segment_id and row.get('language') in languages)
        ]
        self._rows += new_words

    def save(self):
        rows = sorted(self._rows, key=lambda r: (int(r['segment_id']), r.get('language', ''), int(r['word_index'])))
        with open(self.path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
