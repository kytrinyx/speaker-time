import spacy

from .punctuation_split import normalize


def _find_split_space_indices(text, nlp):
    """Return list of space-word 'after' indices at which to split.

    A result value of s means: split after space-word s (new chunk starts at s+1).

    Splits before the first token of:
    - cc whose head is a VERB — coordinating conjunction joining clauses
    - mark — subordinating conjunction
    - prep whose head is a VERB or AUX — prepositional phrase modifying a verb
    - relcl — relative clause
    - advcl — adverbial clause modifier
    - xcomp — open clausal complement
    - ccomp — clausal complement
    - npadvmod — noun phrase adverbial modifier
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

    doc = nlp(text)
    split_char_positions = []

    for token in doc:
        if token.dep_ == 'cc' and token.head.pos_ == 'VERB':
            split_char_positions.append(token.idx)
        elif token.dep_ == 'mark':
            split_char_positions.append(token.idx)
        elif token.dep_ == 'prep' and token.head.pos_ in ('VERB', 'AUX'):
            split_char_positions.append(token.idx)
        elif token.dep_ in ('relcl', 'advcl', 'xcomp', 'ccomp', 'npadvmod'):
            split_char_positions.append(token.left_edge.idx)

    after_indices = []
    for char_pos in split_char_positions:
        w_idx = None
        for i, (start, end) in enumerate(word_spans):
            if start <= char_pos < end:
                w_idx = i
                break
        if w_idx is not None and w_idx > 0:
            after_indices.append(w_idx - 1)

    return sorted(set(after_indices))


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
        """Return word indices into segment.words where new chunks begin."""
        if segment.language != 'en':
            return []

        if not segment.words:
            return []

        space_indices = _find_split_space_indices(segment.raw_text, self._get_nlp())
        if not space_indices:
            return []

        return sorted(set(_space_to_whisper_indices(space_indices, segment.raw_text, segment.words)))
