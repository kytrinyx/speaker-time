import csv
import statistics
from dataclasses import dataclass, field


@dataclass
class TimelineSegment:
    segment_id: int
    speaker_id: str
    start: float
    end: float
    audio_path: str
    duration: float = field(init=False)

    def __post_init__(self):
        self.duration = self.end - self.start


class Timeline:
    def __init__(self, segments):
        self._segments = segments  # list of TimelineSegment

    @classmethod
    def load(cls, episode_id):
        path = f"output/{episode_id}/timeline.csv"
        segments = []
        with open(path, newline="") as f:
            for idx, row in enumerate(csv.DictReader(f)):
                segment_id = idx + 1
                segments.append(TimelineSegment(
                    segment_id=segment_id,
                    speaker_id=row["SPEAKER_ID"],
                    start=float(row["start_time"]),
                    end=float(row["end_time"]),
                    audio_path=f"output/{episode_id}/audio/{segment_id:06d}.mp3",
                ))
        return cls(segments)

    def __iter__(self):
        return iter(self._segments)

    def net_duration(self):
        return sum(s.duration for s in self._segments)

    def airtime(self, speaker):
        return sum(s.duration for s in self._segments if s.speaker_id == speaker)

    def airtime_distribution(self):
        speakers = {s.speaker_id for s in self._segments}
        total = self.net_duration()
        return {spk: self.airtime(spk) / total * 100 for spk in speakers}

    def segment_stats(self, speaker):
        lengths = [s.duration for s in self._segments if s.speaker_id == speaker]
        if not lengths:
            return {"longest": 0.0, "mean": 0.0, "stddev": 0.0}
        return {
            "longest": max(lengths),
            "mean": statistics.mean(lengths),
            "median": statistics.median(lengths),
            "stddev": statistics.stdev(lengths) if len(lengths) > 1 else 0.0,
        }
