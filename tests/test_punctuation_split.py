import pytest
from halfhalf.segment import Segment, Word
from halfhalf.punctuation_split import PunctuationSplit


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


# --- No split cases ---

def test_no_punctuation_returns_single_cue():
    s = seg("안녕하세요", "ko", [
        Word(" 안녕하세요", 0.0, 1.0),
    ])
    cues = PunctuationSplit().split(s)
    assert len(cues) == 1


def test_trailing_punctuation_only_returns_single_cue():
    s = seg("안녕하세요.", "ko", [
        Word(" 안녕하세요.", 0.0, 1.0),
    ])
    cues = PunctuationSplit().split(s)
    assert len(cues) == 1


# --- Split cases ---

def test_splits_on_period():
    s = seg("안녕하세요. 반갑습니다.", "ko", [
        Word(" 안녕하세요.", 0.0, 1.0),
        Word(" 반갑습니다.", 1.1, 2.0),
    ])
    cues = PunctuationSplit().split(s)
    assert len(cues) == 2


def test_splits_on_question_mark():
    s = seg("잘 지내세요? 저는 잘 지냅니다.", "ko", [
        Word(" 잘", 0.0, 0.4),
        Word(" 지내세요?", 0.4, 1.0),
        Word(" 저는", 1.1, 1.5),
        Word(" 잘", 1.5, 1.8),
        Word(" 지냅니다.", 1.8, 2.5),
    ])
    cues = PunctuationSplit().split(s)
    assert len(cues) == 2


def test_splits_on_comma():
    s = seg("one small caveat, and I've said this", "en", [
        Word(" one", 0.0, 0.3),
        Word(" small", 0.3, 0.6),
        Word(" caveat,", 0.6, 1.0),
        Word(" and", 1.1, 1.3),
        Word(" I've", 1.3, 1.6),
        Word(" said", 1.6, 1.9),
        Word(" this", 1.9, 2.2),
    ])
    cues = PunctuationSplit().split(s)
    assert len(cues) == 2
    assert cues[0].text == "one small caveat,"
    assert cues[1].text == "and I've said this"


def test_splits_on_exclamation_mark():
    s = seg("잘했어요! 정말 대단해요.", "ko", [
        Word(" 잘했어요!", 0.0, 1.0),
        Word(" 정말", 1.1, 1.5),
        Word(" 대단해요.", 1.5, 2.5),
    ])
    cues = PunctuationSplit().split(s)
    assert len(cues) == 2



def test_three_sentences_split_into_three_cues():
    s = seg("안녕하세요. 잘 지내세요? 반갑습니다.", "ko", [
        Word(" 안녕하세요.", 0.0, 1.0),
        Word(" 잘", 1.1, 1.4),
        Word(" 지내세요?", 1.4, 2.0),
        Word(" 반갑습니다.", 2.1, 3.0),
    ])
    cues = PunctuationSplit().split(s)
    assert len(cues) == 3


def test_ellipsis_produces_single_split():
    s = seg("그런데... 잘 모르겠어요.", "ko", [
        Word(" 그런데...", 0.0, 1.0),
        Word(" 잘", 1.1, 1.4),
        Word(" 모르겠어요.", 1.4, 2.0),
    ])
    cues = PunctuationSplit().split(s)
    assert len(cues) == 2


# --- Timestamps ---

def test_cue_timestamps_come_from_words():
    s = seg("안녕하세요. 반갑습니다.", "ko", [
        Word(" 안녕하세요.", 1.5, 2.5),
        Word(" 반갑습니다.", 3.0, 4.2),
    ])
    cues = PunctuationSplit().split(s)
    assert cues[0].start == 1.5
    assert cues[0].end == 2.5
    assert cues[1].start == 3.0
    assert cues[1].end == 4.2
