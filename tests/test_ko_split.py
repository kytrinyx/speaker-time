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


def test_no_split_on_noun_ending_in_myeon():
    # 라면 is NNG (ramen), not EC — should not split
    f = frag(("라면", 0.0, 0.5), ("먹을까요.", 0.5, 1.2))
    assert ko.find_splits(f) == {'standard': [], 'weak': []}


def test_no_split_on_noun_ending_in_go():
    # 고등학교 is NNG — 고 is not an EC morpheme here
    f = frag(("고등학교", 0.0, 0.5), ("다녀요.", 0.5, 1.0))
    assert ko.find_splits(f) == {'standard': [], 'weak': []}


def test_ef_compound_imnida():
    # 정태웅입니다 → VCP+EF compound; triggers endswith('+EF') branch
    f = frag(("정태웅입니다", 0.0, 0.8), ("반갑습니다.", 0.8, 1.5))
    result = ko.find_splits(f)
    assert result['standard'] == [1]


def test_ec_compound_geonde():
    # 건데 → NNB+VCP+EC compound; triggers endswith('+EC') branch
    f = frag(("느끼는", 0.0, 0.4), ("건데", 0.4, 0.7), ("사람들이", 0.7, 1.1), ("좀.", 1.1, 1.4))
    result = ko.find_splits(f)
    assert 2 in result['standard']


def test_ef_with_trailing_punctuation():
    # EF ending before trailing '.'; split should still fire
    f = frag(("정태웅이었습니다.", 0.0, 0.8), ("감사합니다.", 0.8, 1.5))
    result = ko.find_splits(f)
    assert 1 in result['standard']


def test_weak_jkb_e():
    # 중에 → NNB + 에(JKB locative); weak split only
    f = frag(("중에", 0.0, 0.4), ("하나가", 0.4, 0.8), ("있어요.", 0.8, 1.3))
    result = ko.find_splits(f)
    assert 1 in result['weak']
    assert 1 not in result['standard']


def test_weak_jx_following_jkb():
    # 주에는 → 주(NNG) + 에(JKB) + 는(JX); weak split only
    f = frag(("주에는", 0.0, 0.5), ("공부해요.", 0.5, 1.2))
    result = ko.find_splits(f)
    assert 1 in result['weak']
    assert 1 not in result['standard']


def test_plain_topic_marker_not_weak():
    # 사람은 → NNG + 은(JX) without preceding JKB — no weak split
    f = frag(("사람은", 0.0, 0.5), ("착해요.", 0.5, 1.0))
    assert ko.find_splits(f) == {'standard': [], 'weak': []}


def test_weak_etm():
    # 없는 → VA + 는(ETM adnominal); weak split
    f = frag(("없는", 0.0, 0.4), ("발언을", 0.4, 0.8), ("한다거나.", 0.8, 1.3))
    result = ko.find_splits(f)
    assert 1 in result['weak']


def test_weak_jkb_comitative_rang():
    # 때랑 → NNG + 랑(JKB comitative); weak split
    f = frag(("때랑", 0.0, 0.4), ("또", 0.4, 0.6), ("우리의", 0.6, 0.9), ("태도가", 0.9, 1.2), ("달라요.", 1.2, 1.5))
    result = ko.find_splits(f)
    assert 1 in result['weak']


def test_weak_jc_ina():
    # 친구들이나 → NNG + 이나(JC conjunctive); weak split only
    f = frag(("친구들이나", 0.0, 0.5), ("가족들이랑", 0.5, 1.0), ("얘기해요.", 1.0, 1.5))
    result = ko.find_splits(f)
    assert 1 in result['weak']
    assert 1 not in result['standard']


def test_weak_jc_na():
    # 친구나 → NNG + 나(JC conjunctive); weak split
    f = frag(("친구나", 0.0, 0.4), ("가족이랑", 0.4, 0.8), ("얘기해요.", 0.8, 1.3))
    result = ko.find_splits(f)
    assert 1 in result['weak']
