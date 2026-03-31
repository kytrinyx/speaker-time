import spacy
from halfhalf.mimeograph import Fragment
from halfhalf.en_split import EnSplit
from halfhalf.word import Word

_nlp = spacy.load("en_core_web_sm")


def frag(*pairs):
    return Fragment([Word(text, start, end) for text, start, end in pairs])


en = EnSplit()


def test_korean_fragment_returns_empty():
    f = frag(("안녕하세요", 0.0, 0.8), ("반갑습니다.", 0.8, 1.5))
    assert en.find_splits(f) == {'standard': [], 'weak': []}


def test_empty_words_returns_empty():
    assert en.find_splits(Fragment([])) == {'standard': [], 'weak': []}


def test_simple_sentence_returns_empty():
    f = frag(("I", 0.0, 0.2), ("like", 0.2, 0.5), ("coffee.", 0.5, 0.9))
    result = en.find_splits(f)
    assert result['standard'] == []


def test_cc_with_verb_head_returns_standard_index():
    # "and" is cc with verb head → standard split; new chunk starts at "and" (word 3)
    f = frag(
        ("I", 0.0, 0.2),
        ("went", 0.2, 0.5),
        ("home", 0.5, 0.8),
        ("and", 0.8, 1.0),
        ("I", 1.0, 1.1),
        ("made", 1.1, 1.4),
        ("dinner.", 1.4, 1.8),
    )
    result = en.find_splits(f)
    assert 3 in result['standard']


def test_mark_returns_standard_index():
    # "if" is mark → standard split; new chunk starts at "if" (word 3)
    f = frag(
        ("We", 0.0, 0.2),
        ("can", 0.2, 0.4),
        ("go", 0.4, 0.6),
        ("if", 0.6, 0.8),
        ("you", 0.8, 1.0),
        ("want.", 1.0, 1.3),
    )
    result = en.find_splits(f)
    assert 3 in result['standard']


def test_prep_with_verb_head_returns_weak():
    # "about" is prep with noun head → weak split
    f = frag(
        ("I", 0.0, 0.2),
        ("might", 0.2, 0.4),
        ("know", 0.4, 0.6),
        ("things", 0.6, 0.9),
        ("about", 0.9, 1.1),
        ("developers.", 1.1, 1.5),
    )
    result = en.find_splits(f)
    assert 4 in result['weak']


def test_last_word_split_excluded():
    f = frag(
        ("I", 0.0, 0.2),
        ("went", 0.2, 0.5),
        ("home", 0.5, 0.8),
        ("and", 0.8, 1.0),
        ("slept.", 1.0, 1.4),
    )
    result = en.find_splits(f)
    assert all(i < len(f.words) for i in result['standard'] + result['weak'])
