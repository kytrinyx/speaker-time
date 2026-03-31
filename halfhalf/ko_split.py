from .mecab_split import _find_split_word_indices


class KoSplit:
    """Find split points in Korean fragments at clause and phrase boundaries via MeCab.

    standard — sentence-level boundaries (EC connective endings, EF sentence-final endings)
    weak     — phrase-level boundaries (particles, adnominal endings, conjunctions)

    Non-Korean fragments return empty lists.
    """

    name = "ko"

    def find_splits(self, fragment):
        """Return {'standard': [...], 'weak': [...]} of word indices where new chunks begin."""
        empty = {'standard': [], 'weak': []}
        if fragment.language != 'ko' or not fragment.words:
            return empty

        space_result = _find_split_word_indices(fragment.text)
        n = len(fragment.words)

        return {
            'standard': [s + 1 for s in space_result['standard'] if s + 1 < n],
            'weak': [s + 1 for s in space_result['weak'] if s + 1 < n],
        }
