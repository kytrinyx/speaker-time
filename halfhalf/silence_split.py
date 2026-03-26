class SilenceSplit:
    """Find split points at silence boundaries detected by ffmpeg.

    Silences are matched to inter-word gaps by overlap. Returns word indices
    where new chunks begin, split into strong (≥ 0.4s) and standard (≥ 0.1s).
    """

    name = "silence"

    def __init__(self, silences):
        self.silences = list(silences)

    def find_splits(self, segment):
        """Return {'strong': List[int], 'standard': List[int]} of word indices.

        Index i means "start a new chunk at segment.words[i]".
        strong   — silences ≥ 0.4s (hard walls the merge phase never crosses)
        standard — silences ≥ 0.1s (includes strong; all are valid split candidates)
        """
        if not segment.words:
            return {'strong': [], 'standard': []}

        words = segment.words
        strong, standard = [], []

        for i in range(len(words) - 1):
            gap_start = words[i].end
            gap_end = words[i + 1].start
            for s, e in self.silences:
                if s < gap_end and e > gap_start:
                    dur = e - s
                    if dur >= 0.1:
                        standard.append(i + 1)
                        if dur >= 0.4:
                            strong.append(i + 1)
                    break

        return {'strong': strong, 'standard': standard}
