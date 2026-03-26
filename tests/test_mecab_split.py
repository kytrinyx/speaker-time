import pytest
from halfhalf.segment import Segment, Word
from halfhalf.mecab_split import MecabSplit, _find_split_word_indices, _space_to_whisper_indices


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


# --- _find_split_word_indices ---

def test_splits_on_go():
    # 하고 → 하(VV) + 고(EC); split after word 0 (공부하고)
    assert 0 in _find_split_word_indices('공부하고 싶어요')['standard']

def test_splits_on_ef_seumnida():
    # 습니다 → EF sentence-final ending; split after word 0 (돌아왔습니다)
    assert 0 in _find_split_word_indices('돌아왔습니다 정태웅입니다')['standard']

def test_splits_on_ef_imnida():
    # 입니다 → VCP+EF; split after word 0 (정태웅입니다)
    assert 0 in _find_split_word_indices('정태웅입니다 반갑습니다')['standard']

def test_no_split_on_noun_ending_in_myeon():
    # 라면 is NNG (ramen), not EC — 면 never surfaces as a morpheme
    assert _find_split_word_indices('라면 먹을까요')['standard'] == []

def test_no_split_on_noun_ending_in_go():
    # 고등학교 is NNG — 고 is not an EC morpheme here
    # 다녀요 is EF but it's the last word, so no split recorded
    assert _find_split_word_indices('고등학교 다녀요')['standard'] == []

def test_splits_on_geonde():
    # 건데 → 것/NNB + 이/VCP + ᆫ데/EC (inflected compound NNB+VCP+EC); split after 건데 (index 6)
    assert 6 in _find_split_word_indices('네 그래서 이렇게 요즘 많이 느끼는 건데 사람들이 좀')['standard']

def test_splits_on_ef_with_trailing_punctuation():
    # 정태웅이었습니다. → EF before trailing SF; split should still fire
    assert 0 in _find_split_word_indices('정태웅이었습니다. 감사합니다.')['standard']

def test_no_split_single_word():
    result = _find_split_word_indices('공부하고')
    assert result == {'standard': [], 'weak': []}

def test_multiple_splits():
    # splits after 공부하고(0), 쉬면(1), 좋겠지만(2); 모르겠어요(3) is last word, skipped
    assert _find_split_word_indices('공부하고 쉬면 좋겠지만 모르겠어요')['standard'] == [0, 1, 2]

def test_weak_split_e():
    # 중에 → 중(NNB) + 에(JKB); weak split after word 0
    assert 0 in _find_split_word_indices('중에 하나가 있어요')['weak']

def test_weak_split_euro():
    # 으로 → JKB direction particle; weak split after word 0 (한국어로)
    assert 0 in _find_split_word_indices('한국어로 말해요')['weak']

def test_weak_split_euro_not_in_standard():
    assert 0 not in _find_split_word_indices('한국어로 말해요')['standard']

def test_weak_split_enun():
    # 주에는 → 주(NNG) + 에(JKB) + 는(JX); weak split after word 0
    assert 0 in _find_split_word_indices('주에는 공부해요')['weak']

def test_weak_split_enun_not_in_standard():
    assert 0 not in _find_split_word_indices('주에는 공부해요')['standard']

def test_plain_topic_marker_not_weak():
    # 사람은 → NNG + 은(JX) without preceding JKB — no weak split
    assert _find_split_word_indices('사람은 착해요')['weak'] == []

def test_weak_split_etm():
    # 없는 → 없(VA) + 는(ETM); weak split after word 0
    assert 0 in _find_split_word_indices('없는 정치적인 발언을 한다거나')['weak']

def test_weak_split_rang():
    # 때랑 → 때(NNG) + 랑(JKB comitative); weak split after word 0
    assert 0 in _find_split_word_indices('때랑 또 우리의 태도가 달라요')['weak']

def test_weak_split_ina():
    # 친구들이나 → 친구들(NNG) + 이나(JC); weak split after word 0
    assert 0 in _find_split_word_indices('친구들이나 가족들이랑 얘기해요')['weak']

def test_weak_split_ina_not_in_standard():
    assert 0 not in _find_split_word_indices('친구들이나 가족들이랑 얘기해요')['standard']

def test_weak_split_na():
    # 친구나 → 친구(NNG) + 나(JC); weak split after word 0
    assert 0 in _find_split_word_indices('친구나 가족이랑 얘기해요')['weak']


# --- MecabSplit.find_splits ---

def test_english_returns_empty():
    s = seg('Hello there', 'en', [
        Word('Hello', 0.0, 0.5),
        Word(' there', 0.5, 1.0),
    ])
    assert MecabSplit().find_splits(s) == {'standard': [], 'weak': []}

def test_no_words_returns_empty():
    s = Segment(id=1, start=0.0, end=1.0, raw_text='안녕하세요', language='ko', words=[])
    assert MecabSplit().find_splits(s) == {'standard': [], 'weak': []}

def test_korean_with_ec_returns_whisper_index():
    # split after 공부하고 (space-word 0) → new chunk starts at Whisper word 1
    s = seg('공부하고 싶어요', 'ko', [
        Word('공부하고', 0.0, 0.8),
        Word(' 싶어요', 0.8, 1.5),
    ])
    assert MecabSplit().find_splits(s) == {'standard': [1], 'weak': []}

def test_korean_with_ef_returns_whisper_index():
    # 습니다 EF; split after 돌아왔습니다 → new chunk starts at Whisper word 1
    s = seg('돌아왔습니다 반갑습니다', 'ko', [
        Word('돌아왔습니다', 0.0, 0.8),
        Word(' 반갑습니다', 0.8, 1.5),
    ])
    result = MecabSplit().find_splits(s)
    assert result['standard'] == [1]
    assert result['weak'] == []

def test_korean_with_euro_returns_weak():
    s = seg('한국어로 말해요', 'ko', [
        Word('한국어로', 0.0, 0.6),
        Word(' 말해요', 0.6, 1.2),
    ])
    result = MecabSplit().find_splits(s)
    assert result['weak'] == [1]
    assert result['standard'] == []

def test_korean_with_enun_returns_weak():
    s = seg('주에는 공부해요', 'ko', [
        Word('주에는', 0.0, 0.5),
        Word(' 공부해요', 0.5, 1.2),
    ])
    result = MecabSplit().find_splits(s)
    assert result['weak'] == [1]
    assert result['standard'] == []

def test_multiple_ec_splits():
    s = seg('공부하고 쉬면 좋겠지만 모르겠어요', 'ko', [
        Word('공부하고', 0.0, 0.5),
        Word(' 쉬면', 0.5, 1.0),
        Word(' 좋겠지만', 1.0, 1.5),
        Word(' 모르겠어요', 1.5, 2.0),
    ])
    assert MecabSplit().find_splits(s) == {'standard': [1, 2, 3], 'weak': []}

def test_space_to_whisper_second_occurrence():
    # "공부하고쉬고" appears twice in full_norm; splits at space-words 0 and 2 must map
    # to distinct Whisper words (1 and 3), not both to word 1 (the first match).
    whisper_words = [
        Word('공부하고', 0.0, 0.5),
        Word(' 쉬고', 0.5, 1.0),
        Word(' 공부하고', 1.0, 1.5),
        Word(' 쉬고', 1.5, 2.0),
        Word(' 됐어요', 2.0, 2.5),
    ]
    result = _space_to_whisper_indices([0, 2], '공부하고 쉬고 공부하고 쉬고 됐어요', whisper_words)
    assert result == [1, 3]

def test_repeated_ec_phrase_maps_all_splits():
    # Both occurrences of 공부하고 and 쉬고 (EC) must produce distinct Whisper indices.
    # Without search_start fix, the duplicate context "공부하고쉬고" collapses splits 2→1.
    s = seg('공부하고 쉬고 공부하고 쉬고 됐어요', 'ko', [
        Word('공부하고', 0.0, 0.5),
        Word(' 쉬고', 0.5, 1.0),
        Word(' 공부하고', 1.0, 1.5),
        Word(' 쉬고', 1.5, 2.0),
        Word(' 됐어요', 2.0, 2.5),
    ])
    assert MecabSplit().find_splits(s) == {'standard': [1, 2, 3, 4], 'weak': []}

def test_ec_not_falsely_matched_as_substring():
    # split after 했고 (space-word 1) → new chunk starts at second '다' (Whisper word 2)
    # '다' is short enough that full_norm.find('다') hits the first '다' (word 0) instead
    s = seg('다 했고 다 됐어요', 'ko', [
        Word('다', 0.0, 0.3),
        Word(' 했고', 0.3, 0.7),
        Word(' 다', 0.7, 1.0),
        Word(' 됐어요', 1.0, 1.5),
    ])
    assert MecabSplit().find_splits(s) == {'standard': [2], 'weak': []}
