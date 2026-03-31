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


def test_cc_with_noun_head_returns_standard_index():
    # "or" is cc with NOUN head → standard split; new chunk starts at "or" (word 2)
    f = frag(
        ("like", 0.0, 0.2), ("movies", 0.2, 0.5), ("or", 0.5, 0.7),
        ("TV", 0.7, 0.9), ("shows.", 0.9, 1.2),
    )
    result = en.find_splits(f)
    assert 2 in result['standard']


def test_cc_with_aux_head_returns_standard_index():
    # "and" is cc with AUX head (was) → standard split; new chunk starts at "and" (word 5)
    f = frag(
        ("it", 0.0, 0.1), ("was", 0.1, 0.3), ("a", 0.3, 0.4), ("complete", 0.4, 0.6),
        ("accident", 0.6, 0.9), ("and", 0.9, 1.1), ("it", 1.1, 1.2), ("was", 1.2, 1.4),
        ("not", 1.4, 1.6), ("their", 1.6, 1.8), ("fault.", 1.8, 2.1),
    )
    result = en.find_splits(f)
    assert 5 in result['standard']


def test_mark_because_returns_standard_index():
    # "because" is mark → standard split; new chunk starts at "because" (word 3)
    f = frag(
        ("I", 0.0, 0.1), ("stayed", 0.1, 0.4), ("home", 0.4, 0.6),
        ("because", 0.6, 0.9), ("it", 0.9, 1.0), ("was", 1.0, 1.2), ("raining.", 1.2, 1.6),
    )
    result = en.find_splits(f)
    assert 3 in result['standard']


def test_prep_with_adj_head_returns_weak():
    # "with" is prep with ADJ head (familiar) → weak split; new chunk starts at "with" (word 2)
    f = frag(
        ("more", 0.0, 0.2), ("familiar", 0.2, 0.5), ("with", 0.5, 0.7),
        ("the", 0.7, 0.8), ("people.", 0.8, 1.1),
    )
    result = en.find_splits(f)
    assert 2 in result['weak']


def test_intj_with_verb_head_returns_weak():
    # "like" is intj with VERB head (flip) → weak split; new chunk starts at "like" (word 3)
    f = frag(
        ("enjoy", 0.0, 0.3), ("it", 0.3, 0.5), ("anymore", 0.5, 0.8),
        ("like", 0.8, 1.0), ("I", 1.0, 1.1), ("will", 1.1, 1.3),
        ("just", 1.3, 1.5), ("flip", 1.5, 1.7), ("a", 1.7, 1.8), ("switch.", 1.8, 2.1),
    )
    result = en.find_splits(f)
    assert 3 in result['weak']


def test_acl_returns_weak():
    # "listening" is acl modifying "everybody" → weak split; new chunk starts at "listening" (word 2)
    f = frag(
        ("probably", 0.0, 0.3), ("everybody", 0.3, 0.6), ("listening", 0.6, 0.9),
        ("has", 0.9, 1.1), ("different", 1.1, 1.4), ("opinions.", 1.4, 1.8),
    )
    result = en.find_splits(f)
    assert 2 in result['weak']
