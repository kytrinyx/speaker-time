import unicodedata

import mecab_ko

from .punctuation_split import normalize


TARGET_JKB_WEAK = {'으로', '로', '에'}
TARGET_JKB_COMITATIVE_WEAK = {'랑', '이랑'}
TARGET_JC_WEAK = {'이나', '나'}


def _find_split_word_indices(text):
    """Return {'standard': [...], 'weak': [...]} of space-word indices after which to split.

    standard — sentence boundaries:
      - EC connective endings (all)
      - EF sentence-final endings (all)

    weak — phrase boundaries:
      - JKB direction/means/locative particles 으로/로/에 at word boundary
      - JKB comitative particles 랑/이랑 (A and B)
      - ETM adnominal endings 는/은/을 (relative clause boundary)
      - JC conjunctive particles 이나/나 (A or B lists)
      - JX topic marker 는/은 following a JKB (에는, 에서는, 로는, etc.)
    """
    raw_words = text.split()
    if len(raw_words) <= 1:
        return {'standard': [], 'weak': []}

    word_spans = []
    search_from = 0
    for word in raw_words:
        idx = text.index(word, search_from)
        end = idx + len(word)
        stripped = end
        while stripped > idx and unicodedata.category(text[stripped - 1]).startswith('P'):
            stripped -= 1
        word_spans.append((idx, stripped if stripped > idx else end))
        search_from = end

    tagger = mecab_ko.Tagger()
    standard = []
    weak = []
    char_pos = 0
    word_idx = 0
    prev_pos = None

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

        is_last_word = word_idx == len(word_spans) - 1
        if is_word_final and not is_last_word:
            if pos == 'EC' or pos.endswith('+EC'):
                standard.append(word_idx)
            elif pos == 'EF' or pos.endswith('+EF'):
                standard.append(word_idx)
            elif pos == 'JKB' and surface in TARGET_JKB_WEAK:
                weak.append(word_idx)
            elif pos == 'JKB' and surface in TARGET_JKB_COMITATIVE_WEAK:
                weak.append(word_idx)
            elif pos == 'ETM' or pos.endswith('+ETM'):
                weak.append(word_idx)
            elif pos == 'JC' and surface in TARGET_JC_WEAK:
                weak.append(word_idx)
            elif pos == 'JX' and surface in ('는', '은') and prev_pos == 'JKB':
                weak.append(word_idx)

        prev_pos = pos
        char_pos = tok_end
        node = node.next

    return {'standard': standard, 'weak': weak}


def _space_to_whisper_indices(space_indices, raw_text, whisper_words):
    """Map space-word 'after' indices to Whisper word indices.

    Each space-word split index s means "split after space-word s", i.e. the
    next chunk starts at space-word s+1. This function finds the first Whisper
    word index that belongs to that next chunk via normalized text matching.
    """
    raw_words = raw_text.split()
    full_norm = normalize("".join(w.text for w in whisper_words))

    result = []
    search_start = 0
    for s in space_indices:
        if s + 1 >= len(raw_words):
            continue

        # Use two-word context to avoid false substring matches on short words
        # e.g. "and" alone matches inside "cando" (from "can"+"do"), but "doand" does not.
        # search_start advances monotonically so repeated identical contexts (e.g. "wantto"
        # appearing twice) map to distinct Whisper words instead of both hitting the first.
        context = normalize(raw_words[s] + raw_words[s + 1])
        offset = len(normalize(raw_words[s]))
        pos = full_norm.find(context, search_start)
        if pos == -1:
            pos = full_norm.find(normalize(raw_words[s + 1]), search_start)
            if pos == -1:
                continue
        else:
            pos += offset

        search_start = pos

        char_pos = 0
        for w_idx, w in enumerate(whisper_words):
            w_norm = normalize(w.text)
            if char_pos + len(w_norm) > pos:
                result.append(w_idx)
                break
            char_pos += len(w_norm)

    return result


class MecabSplit:
    """Find split points in Korean segments at clause and phrase boundaries via MeCab.

    standard — sentence-level boundaries:
      - EC connective endings (all)
      - EF sentence-final endings (all)

    weak — phrase-level boundaries:
      - JKB direction/means/locative particles 으로/로/에
      - JKB comitative particles 랑/이랑 (A and B)
      - ETM adnominal endings 는/은/을 (relative clause boundary)
      - JC conjunctive particles 이나/나 (A or B lists)
      - JX topic marker 는/은 following a JKB (에는, 에서는, etc.)

    English segments return empty lists.
    """

    name = "mecab"

    def find_splits(self, segment):
        """Return {'standard': [...], 'weak': [...]} of word indices where new chunks begin."""
        empty = {'standard': [], 'weak': []}
        if segment.language != 'ko':
            return empty

        if not segment.words:
            return empty

        space_result = _find_split_word_indices(segment.raw_text)
        if not space_result['standard'] and not space_result['weak']:
            return empty

        return {
            'standard': _space_to_whisper_indices(space_result['standard'], segment.raw_text, segment.words),
            'weak': _space_to_whisper_indices(space_result['weak'], segment.raw_text, segment.words),
        }
