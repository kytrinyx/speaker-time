import mecab_ko

from .cue import Cue
from .punctuation_split import normalize
from .segment import clean


TARGET_EC = {'고', '면', '자', '니까', '지만', '는데'}


def _find_split_word_indices(text):
    """Return list of space-word indices (0-based) after which to split.

    Walks the MeCab token stream tracking which space-separated word each
    morpheme belongs to. When a target EC morpheme is word-final, records
    a split after that word index.
    """
    raw_words = text.split()
    if len(raw_words) <= 1:
        return []

    word_spans = []
    search_from = 0
    for word in raw_words:
        idx = text.index(word, search_from)
        word_spans.append((idx, idx + len(word)))
        search_from = idx + len(word)

    tagger = mecab_ko.Tagger()
    splits = []
    char_pos = 0
    word_idx = 0

    node = tagger.parseToNode(text)
    while node:
        surface = node.surface
        if not surface:
            node = node.next
            continue

        while char_pos < len(text) and text[char_pos] in ' \t\n':
            char_pos += 1

        while word_idx < len(word_spans) and char_pos >= word_spans[word_idx][1]:
            word_idx += 1

        if word_idx >= len(word_spans):
            break

        tok_end = char_pos + len(surface)
        is_word_final = tok_end >= word_spans[word_idx][1]

        pos = node.feature.split(',')[0]
        if pos == 'EC' and surface in TARGET_EC and is_word_final:
            splits.append(word_idx)

        char_pos = tok_end
        node = node.next

    return splits


def _build_cues(segment, split_indices):
    """Build cues from a segment and a list of space-word split indices.

    Each index i in split_indices means: split after space-separated word i
    in segment.raw_text. Maps word boundaries to Whisper word timestamps via
    normalized text matching.
    """
    raw_words = segment.raw_text.split()
    boundaries = [0] + [i + 1 for i in split_indices] + [len(raw_words)]
    chunks = [" ".join(raw_words[s:e]) for s, e in zip(boundaries, boundaries[1:])]
    chunks = [c for c in chunks if c]
    if len(chunks) <= 1:
        return [Cue(segment.start, segment.end, segment.text)]

    full_norm = normalize("".join(w.text for w in segment.words))

    cues = []
    cursor = 0

    for chunk in chunks:
        chunk_norm = normalize(chunk)
        if not chunk_norm:
            continue

        pos = full_norm.find(chunk_norm, cursor)
        if pos == -1:
            pos = cursor
        end_pos = pos + len(chunk_norm)

        char_pos = 0
        chunk_words = []
        for w in segment.words:
            w_norm = normalize(w.text)
            w_start, w_end = char_pos, char_pos + len(w_norm)
            if w_end > pos and w_start < end_pos:
                chunk_words.append(w)
            char_pos = w_end

        if chunk_words:
            cleaned = clean(chunk, segment.language)
            if cleaned:
                cues.append(Cue(chunk_words[0].start, chunk_words[-1].end, cleaned))
        cursor = end_pos

    if not cues:
        return [Cue(segment.start, segment.end, segment.text)]
    return cues


class MecabSplit:
    """Split Korean segments at clause boundaries detected by MeCab.

    Runs MeCab on the full segment text and splits after words whose final
    morpheme is a target EC (연결어미): 고, 면, 자, 니까, 지만, 는데.

    English segments are returned as-is (single cue).
    """

    name = "mecab"

    def split(self, segment):
        if segment.language != 'ko':
            return [Cue(segment.start, segment.end, segment.text)]

        if not segment.words:
            return [Cue(segment.start, segment.end, segment.text)]

        split_indices = _find_split_word_indices(segment.raw_text)
        if not split_indices:
            return [Cue(segment.start, segment.end, segment.text)]

        return _build_cues(segment, split_indices)
