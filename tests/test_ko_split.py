from halfhalf.mimeograph import Fragment
from halfhalf.ko_split import KoSplit
from halfhalf.word import Word


def frag(*pairs):
    return Fragment([Word(text, start, end) for text, start, end in pairs])


ko = KoSplit()


def test_english_fragment_returns_empty():
    f = frag(("Hello", 0.0, 0.5), ("there.", 0.5, 1.0))
    assert ko.find_splits(f) == {'standard': [], 'weak': []}


def test_empty_words_returns_empty():
    assert ko.find_splits(Fragment([])) == {'standard': [], 'weak': []}


def test_ec_connective_returns_standard_index():
    # 공부하고 → EC ending; split after word 0, new chunk starts at word 1
    f = frag(("공부하고", 0.0, 0.8), ("싶어요.", 0.8, 1.5))
    assert ko.find_splits(f) == {'standard': [1], 'weak': []}


def test_ef_sentence_final_returns_standard_index():
    # 습니다 → EF ending
    f = frag(("돌아왔습니다", 0.0, 0.8), ("반갑습니다.", 0.8, 1.5))
    result = ko.find_splits(f)
    assert result['standard'] == [1]
    assert result['weak'] == []


def test_particle_euro_returns_weak_index():
    # 으로 → JKB direction particle; weak only
    f = frag(("한국어로", 0.0, 0.6), ("말해요.", 0.6, 1.2))
    result = ko.find_splits(f)
    assert result['weak'] == [1]
    assert result['standard'] == []


def test_multiple_ec_splits():
    f = frag(
        ("공부하고", 0.0, 0.5),
        ("쉬면", 0.5, 1.0),
        ("좋겠지만", 1.0, 1.5),
        ("모르겠어요.", 1.5, 2.0),
    )
    assert ko.find_splits(f) == {'standard': [1, 2, 3], 'weak': []}


def test_last_word_split_excluded():
    # Split index at last word would be out of bounds — should not appear
    f = frag(("공부하고", 0.0, 0.8), ("싶어요.", 0.8, 1.5))
    result = ko.find_splits(f)
    assert all(i < len(f.words) for i in result['standard'] + result['weak'])
