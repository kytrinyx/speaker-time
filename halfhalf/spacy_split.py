import spacy

from .punctuation_split import normalize


def _chars_to_after_indices(char_positions, word_spans):
    """Map char positions to space-word 'after' indices (split before char_pos)."""
    after_indices = []
    for char_pos in char_positions:
        for i, (start, end) in enumerate(word_spans):
            if start <= char_pos < end:
                if i > 0:
                    after_indices.append(i - 1)
                break
    return after_indices


def _find_split_space_indices(text, nlp):
    """Return {'standard': [...], 'weak': [...]} of space-word 'after' indices.

    A result value of s means: split after space-word s (new chunk starts at s+1).

    standard — strong clause boundaries:
      - cc whose head is a VERB (coordinating conjunction joining clauses)
      - mark (subordinating conjunction)

    weak — finer-grained phrase boundaries (prefer to merge, used when fragments are long):
      - prep whose head is a VERB or AUX
      - relcl, advcl, xcomp, ccomp, npadvmod
    """
    raw_words = text.split()
    if len(raw_words) <= 1:
        return {'standard': [], 'weak': []}

    word_spans = []
    search_from = 0
    for word in raw_words:
        idx = text.index(word, search_from)
        word_spans.append((idx, idx + len(word)))
        search_from = idx + len(word)

    doc = nlp(text)
    standard_chars = []
    weak_chars = []

    for token in doc:
        if token.dep_ == 'cc' and token.head.pos_ == 'VERB':
            standard_chars.append(token.idx)
        elif token.dep_ == 'mark':
            standard_chars.append(token.idx)
        elif token.dep_ == 'prep' and token.head.pos_ in ('VERB', 'AUX'):
            weak_chars.append(token.idx)
        elif token.dep_ in ('relcl', 'advcl', 'xcomp', 'ccomp', 'npadvmod'):
            weak_chars.append(token.left_edge.idx)

    return {
        'standard': sorted(set(_chars_to_after_indices(standard_chars, word_spans))),
        'weak': sorted(set(_chars_to_after_indices(weak_chars, word_spans))),
    }


def _space_to_whisper_indices(space_indices, raw_text, whisper_words):
    """Map space-word 'after' indices to Whisper word indices.

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
        # e.g. "and" alone matches inside "cando" (from "can"+"do"), but "doand" does not
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


class SpacySplit:
    """Find split points in English segments at clause boundaries via spaCy.

    Splits before coordinating conjunctions (cc) whose head is a verb,
    and before subordinating conjunctions (mark).

    Korean segments return an empty list.
    """

    name = "spacy"

    def __init__(self):
        self._nlp = None

    def _get_nlp(self):
        if self._nlp is None:
            self._nlp = spacy.load("en_core_web_sm")
        return self._nlp

    def find_splits(self, segment):
        """Return {'strong': [], 'standard': [...], 'weak': [...]} of word indices.

        Index i means "start a new chunk at segment.words[i]".
        standard — strong clause boundaries (cc+VERB, mark)
        weak     — finer-grained phrase boundaries (prep, relcl, advcl, xcomp, ccomp, npadvmod)
        """
        empty = {'strong': [], 'standard': [], 'weak': []}
        if segment.language != 'en':
            return empty

        if not segment.words:
            return empty

        space_result = _find_split_space_indices(segment.raw_text, self._get_nlp())

        return {
            'strong': [],
            'standard': sorted(set(_space_to_whisper_indices(space_result['standard'], segment.raw_text, segment.words))),
            'weak': sorted(set(_space_to_whisper_indices(space_result['weak'], segment.raw_text, segment.words))),
        }
