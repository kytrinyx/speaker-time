from .spacy_split import _find_split_space_indices


class EnSplit:
    """Find split points in English fragments at clause and phrase boundaries via spaCy.

    standard — strong clause boundaries (coordinating conjunctions, subordinating conjunctions)
    weak     — finer-grained phrase boundaries (prep, relcl, advcl, xcomp, ccomp, intj)

    Non-English fragments return empty lists.
    """

    name = "en"

    def __init__(self):
        self._nlp = None

    def _get_nlp(self):
        if self._nlp is None:
            import spacy
            self._nlp = spacy.load("en_core_web_sm")
        return self._nlp

    def find_splits(self, fragment):
        """Return {'standard': [...], 'weak': [...]} of word indices where new chunks begin."""
        empty = {'standard': [], 'weak': []}
        if fragment.language != 'en' or not fragment.words:
            return empty

        space_result = _find_split_space_indices(fragment.text, self._get_nlp())
        n = len(fragment.words)

        return {
            'standard': sorted(set(s + 1 for s in space_result['standard'] if s + 1 < n)),
            'weak': sorted(set(s + 1 for s in space_result['weak'] if s + 1 < n)),
        }
