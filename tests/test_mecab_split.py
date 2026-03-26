import pytest
from halfhalf.segment import Segment, Word
from halfhalf.mecab_split import MecabSplit, _find_split_word_indices, _build_cues


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


# --- _build_cues ---

def test_single_split_index_produces_two_cues():
    s = seg('오늘은 공부하고 내일은 쉬어요', 'ko', [
        Word('오늘은', 0.0, 0.5),
        Word(' 공부하고', 0.5, 1.0),
        Word(' 내일은', 1.0, 1.5),
        Word(' 쉬어요', 1.5, 2.0),
    ])
    cues = _build_cues(s, [1])
    assert len(cues) == 2
    assert cues[0].text == '오늘은 공부하고'
    assert cues[1].text == '내일은 쉬어요'

def test_timestamps_come_from_whisper_words():
    s = seg('가고 싶어요', 'ko', [
        Word('가고', 1.0, 1.5),
        Word(' 싶어요', 2.0, 3.0),
    ])
    cues = _build_cues(s, [0])
    assert cues[0].start == 1.0
    assert cues[0].end == 1.5
    assert cues[1].start == 2.0
    assert cues[1].end == 3.0

def test_empty_split_indices_returns_single_cue():
    s = seg('안녕하세요', 'ko', [Word('안녕하세요', 0.0, 1.0)])
    cues = _build_cues(s, [])
    assert len(cues) == 1

def test_multiple_split_indices():
    s = seg('하나 둘 셋 넷', 'ko', [
        Word('하나', 0.0, 0.5),
        Word(' 둘', 0.5, 1.0),
        Word(' 셋', 1.0, 1.5),
        Word(' 넷', 1.5, 2.0),
    ])
    cues = _build_cues(s, [0, 2])
    assert len(cues) == 3
    assert cues[0].text == '하나'
    assert cues[1].text == '둘 셋'
    assert cues[2].text == '넷'


# --- MecabSplit.split (integration) ---

def test_english_returns_single_cue():
    s = seg('Hello there', 'en', [
        Word('Hello', 0.0, 0.5),
        Word(' there', 0.5, 1.0),
    ])
    cues = MecabSplit().split(s)
    assert len(cues) == 1

def test_no_words_returns_single_cue():
    s = Segment(id=1, start=0.0, end=1.0, raw_text='안녕하세요', language='ko', words=[])
    cues = MecabSplit().split(s)
    assert len(cues) == 1

def test_korean_with_ec_splits():
    s = seg('공부하고 싶어요', 'ko', [
        Word('공부하고', 0.0, 0.8),
        Word(' 싶어요', 0.8, 1.5),
    ])
    cues = MecabSplit().split(s)
    assert len(cues) == 2

def test_korean_without_ec_stays_whole():
    s = seg('안녕하세요 반갑습니다', 'ko', [
        Word('안녕하세요', 0.0, 0.8),
        Word(' 반갑습니다', 0.8, 1.5),
    ])
    cues = MecabSplit().split(s)
    assert len(cues) == 1
