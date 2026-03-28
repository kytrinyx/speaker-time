import spacy

from .split_utils import normalize, derived_whisper_word_indices


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
      - cc whose head is a VERB, AUX, or NOUN (coordinating conjunction)
      - mark (subordinating conjunction)

    weak — finer-grained phrase boundaries (prefer to merge, used when fragments are long):
      - prep whose head is a VERB, AUX, NOUN, or ADJ
      - relcl, advcl, xcomp, ccomp, npadvmod
      - intj (discourse marker like "like") whose head is a VERB or AUX
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
        if token.dep_ == 'cc' and token.head.pos_ in ('VERB', 'AUX', 'NOUN'):
            standard_chars.append(token.idx)
        elif token.dep_ == 'mark':
            standard_chars.append(token.idx)
        elif token.dep_ == 'prep' and token.head.pos_ in ('VERB', 'AUX', 'NOUN', 'ADJ'):
            weak_chars.append(token.idx)
        elif token.dep_ in ('relcl', 'acl', 'advcl', 'xcomp', 'ccomp', 'npadvmod'):
            weak_chars.append(token.left_edge.idx)
        elif token.dep_ == 'intj' and token.head.pos_ in ('VERB', 'AUX'):
            weak_chars.append(token.idx)

    return {
        'standard': sorted(set(_chars_to_after_indices(standard_chars, word_spans))),
        'weak': sorted(set(_chars_to_after_indices(weak_chars, word_spans))),
    }



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
            'standard': sorted(set(derived_whisper_word_indices(space_result['standard'], segment.raw_text, segment.words))),
            'weak': sorted(set(derived_whisper_word_indices(space_result['weak'], segment.raw_text, segment.words))),
        }
