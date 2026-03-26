import mecab_ko

from .punctuation_split import normalize


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


def _space_to_whisper_indices(space_indices, raw_text, whisper_words):
    """Map space-word split indices to Whisper word indices.

    Each space-word split index s means "split after space-word s", i.e. the
    next chunk starts at space-word s+1. This function finds the first Whisper
    word index that belongs to that next chunk via normalized text matching.
    """
    raw_words = raw_text.split()
    full_norm = normalize("".join(w.text for w in whisper_words))

    result = []
    for s in space_indices:
        if s + 1 >= len(raw_words):
            continue

        # Use two-word context to avoid false substring matches on short words
        context = normalize(raw_words[s] + raw_words[s + 1])
        offset = len(normalize(raw_words[s]))
        pos = full_norm.find(context)
        if pos == -1:
            pos = full_norm.find(normalize(raw_words[s + 1]))
            if pos == -1:
                continue
        else:
            pos += offset

        char_pos = 0
        for w_idx, w in enumerate(whisper_words):
            w_norm = normalize(w.text)
            if char_pos + len(w_norm) > pos:
                result.append(w_idx)
                break
            char_pos += len(w_norm)

    return result


class MecabSplit:
    """Find split points in Korean segments at clause boundaries detected by MeCab.

    Runs MeCab on the full segment text and splits after words whose final
    morpheme is a target EC (연결어미): 고, 면, 자, 니까, 지만, 는데.

    English segments return an empty list.
    """

    name = "mecab"

    def find_splits(self, segment):
        """Return word indices into segment.words where new chunks begin."""
        if segment.language != 'ko':
            return []

        if not segment.words:
            return []

        space_indices = _find_split_word_indices(segment.raw_text)
        if not space_indices:
            return []

        return _space_to_whisper_indices(space_indices, segment.raw_text, segment.words)
