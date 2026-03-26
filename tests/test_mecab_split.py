import pytest
from halfhalf.segment import Segment, Word
from halfhalf.mecab_split import MecabSplit, _find_split_word_indices


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


# --- _find_split_word_indices ---

def test_splits_on_go():
    # 하고 → 하(VV) + 고(EC); split after word 0 (공부하고)
    assert 0 in _find_split_word_indices('공부하고 싶어요')

def test_splits_on_myeon():
    # 하면 → 하(VV) + 면(EC)
    assert 0 in _find_split_word_indices('하면 좋겠어요')

def test_splits_on_jiman():
    # 좋겠지만 → ... + 지만(EC)
    assert 0 in _find_split_word_indices('좋겠지만 모르겠어요')

def test_splits_on_nikka():
    assert 0 in _find_split_word_indices('바쁘니까 나중에 해요')

def test_splits_on_neunde():
    assert 0 in _find_split_word_indices('맛있는데 살이 쪄요')

def test_no_split_on_plain_noun():
    assert _find_split_word_indices('안녕하세요 반갑습니다') == []

def test_no_split_on_noun_ending_in_myeon():
    # 라면 is NNG (ramen), not EC — 면 never surfaces as a morpheme
    assert _find_split_word_indices('라면 먹을까요') == []

def test_no_split_on_noun_ending_in_go():
    # 고등학교 is NNG — 고 is not an EC morpheme here
    assert _find_split_word_indices('고등학교 다녀요') == []

def test_no_split_single_word():
    assert _find_split_word_indices('공부하고') == []

def test_multiple_splits():
    # splits after 공부하고(0), 쉬면(1), 좋겠지만(2)
    assert _find_split_word_indices('공부하고 쉬면 좋겠지만 모르겠어요') == [0, 1, 2]


# --- MecabSplit.find_splits ---

def test_english_returns_empty():
    s = seg('Hello there', 'en', [
        Word('Hello', 0.0, 0.5),
        Word(' there', 0.5, 1.0),
    ])
    assert MecabSplit().find_splits(s) == []

def test_no_words_returns_empty():
    s = Segment(id=1, start=0.0, end=1.0, raw_text='안녕하세요', language='ko', words=[])
    assert MecabSplit().find_splits(s) == []

def test_korean_without_ec_returns_empty():
    s = seg('안녕하세요 반갑습니다', 'ko', [
        Word('안녕하세요', 0.0, 0.8),
        Word(' 반갑습니다', 0.8, 1.5),
    ])
    assert MecabSplit().find_splits(s) == []

def test_korean_with_ec_returns_whisper_index():
    # split after 공부하고 (space-word 0) → new chunk starts at Whisper word 1
    s = seg('공부하고 싶어요', 'ko', [
        Word('공부하고', 0.0, 0.8),
        Word(' 싶어요', 0.8, 1.5),
    ])
    assert MecabSplit().find_splits(s) == [1]

def test_multiple_ec_splits():
    s = seg('공부하고 쉬면 좋겠지만 모르겠어요', 'ko', [
        Word('공부하고', 0.0, 0.5),
        Word(' 쉬면', 0.5, 1.0),
        Word(' 좋겠지만', 1.0, 1.5),
        Word(' 모르겠어요', 1.5, 2.0),
    ])
    assert MecabSplit().find_splits(s) == [1, 2, 3]

def test_ec_not_falsely_matched_as_substring():
    # split after 했고 (space-word 1) → new chunk starts at second '다' (Whisper word 2)
    # '다' is short enough that full_norm.find('다') hits the first '다' (word 0) instead
    s = seg('다 했고 다 됐어요', 'ko', [
        Word('다', 0.0, 0.3),
        Word(' 했고', 0.3, 0.7),
        Word(' 다', 0.7, 1.0),
        Word(' 됐어요', 1.0, 1.5),
    ])
    assert MecabSplit().find_splits(s) == [2]
