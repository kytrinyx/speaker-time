from .cue import Cue
from .segment import clean


class SilenceSplit:
    """Split a segment at silence boundaries detected by ffmpeg.

    Silences are matched to inter-word gaps by overlap. Each qualifying silence
    ends the current cue at the 2/3 point of the silence window; the next cue
    starts at the following word's actual start time.
    """

    name = "silence"

    def __init__(self, silences, min_silence=0.4):
        self.silences = [(s, e) for s, e in silences if e - s >= min_silence]

    def split(self, segment):
        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        words = segment.words

        # For each consecutive word pair, find a silence that overlaps the gap.
        split_points = []  # (word_index i, split_time) — split after words[i]
        for i in range(len(words) - 1):
            gap_start = words[i].end
            gap_end = words[i + 1].start
            for s, e in self.silences:
                if s < gap_end and e > gap_start:
                    split_points.append((i, s + (e - s) * 2 / 3))
                    break

        if not split_points:
            return [Cue(segment.start, segment.end, segment.text)]

        boundaries = [0] + [i + 1 for i, _ in split_points] + [len(words)]
        end_times = [t for _, t in split_points] + [words[-1].end]

        cues = []
        for k, (start_idx, end_idx) in enumerate(zip(boundaries, boundaries[1:])):
            chunk = words[start_idx:end_idx]
            if chunk:
                text = "".join(w.text for w in chunk).strip()
                cleaned = clean(text, segment.language)
                if cleaned:
                    cues.append(Cue(chunk[0].start, end_times[k], cleaned))

        return cues if cues else [Cue(segment.start, segment.end, segment.text)]
