import csv
import statistics


class Timeline:
    def __init__(self, segments):
        self._segments = segments  # list of (speaker_id, start, end)

    @classmethod
    def load(cls, basename):
        path = f"output/{basename}/timeline.csv"
        segments = []
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                segments.append((row["SPEAKER_ID"], float(row["start_time"]), float(row["end_time"])))
        return cls(segments)

    def net_duration(self):
        return sum(end - start for _, start, end in self._segments)

    def airtime(self, speaker):
        return sum(end - start for spk, start, end in self._segments if spk == speaker)

    def airtime_distribution(self):
        speakers = {spk for spk, _, _ in self._segments}
        total = self.net_duration()
        return {spk: self.airtime(spk) / total * 100 for spk in speakers}

    def segment_stats(self, speaker):
        lengths = [end - start for spk, start, end in self._segments if spk == speaker]
        if not lengths:
            return {"longest": 0.0, "shortest": 0.0, "mean": 0.0, "stddev": 0.0}
        return {
            "longest": max(lengths),
            "shortest": min(lengths),
            "mean": statistics.mean(lengths),
            "stddev": statistics.stdev(lengths) if len(lengths) > 1 else 0.0,
        }
