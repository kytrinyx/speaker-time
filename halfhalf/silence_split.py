class SilenceSplit:
    """Find split points at silence boundaries detected by ffmpeg.

    Silences are matched to inter-word gaps by overlap. Returns word indices
    where new chunks begin, split into mandatory (≥ 0.4s) and potential (≥ 0.1s).
    """

    name = "silence"

    def __init__(self, silences):
        self.silences = list(silences)

    def find_splits(self, segment):
        """Return {'mandatory': List[int], 'potential': List[int]} of word indices.

        Index i means "start a new chunk at segment.words[i]".
        mandatory — silences ≥ 0.4s (hard walls the merge phase never crosses)
        potential — silences ≥ 0.1s (includes mandatory; all are valid split candidates)
        """
        if not segment.words:
            return {'mandatory': [], 'potential': []}

        words = segment.words
        mandatory, potential = [], []

        for i in range(len(words) - 1):
            gap_start = words[i].end
            gap_end = words[i + 1].start
            for s, e in self.silences:
                if s < gap_end and e > gap_start:
                    dur = e - s
                    if dur >= 0.1:
                        potential.append(i + 1)
                        if dur >= 0.4:
                            mandatory.append(i + 1)
                    break

        return {'mandatory': mandatory, 'potential': potential}
