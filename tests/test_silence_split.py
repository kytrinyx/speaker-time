import pytest
from halfhalf.segment import Segment, Word
from halfhalf.silence_split import SilenceSplit


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


# --- No split cases ---

def test_no_silences_returns_single_cue():
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.0, 2.0),
    ])
    cues = SilenceSplit(silences=[]).split(s)
    assert len(cues) == 1


def test_silence_below_threshold_returns_single_cue():
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.3, 2.0),
    ])
    cues = SilenceSplit(silences=[(1.0, 1.3)], min_silence=0.4).split(s)
    assert len(cues) == 1


def test_no_words_returns_single_cue():
    s = Segment(id=1, start=0.0, end=2.0, raw_text="hello", language="en", words=[])
    cues = SilenceSplit(silences=[(0.5, 1.5)]).split(s)
    assert len(cues) == 1


# --- Split cases ---

def test_splits_on_silence():
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.8, 2.5),
    ])
    cues = SilenceSplit(silences=[(1.0, 1.8)], min_silence=0.4).split(s)
    assert len(cues) == 2


def test_split_point_is_two_thirds_of_silence():
    # silence 1.0 -> 1.9 (0.9s), split at 1.0 + 0.9 * 2/3 = 1.6
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.9, 2.5),
    ])
    cues = SilenceSplit(silences=[(1.0, 1.9)], min_silence=0.4).split(s)
    assert cues[0].end == pytest.approx(1.0 + 0.9 * 2 / 3)


def test_second_cue_starts_at_next_word():
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.9, 2.5),
    ])
    cues = SilenceSplit(silences=[(1.0, 1.9)], min_silence=0.4).split(s)
    assert cues[1].start == 1.9


def test_multiple_silences_produce_multiple_cues():
    s = seg("one two three", "en", [
        Word(" one", 0.0, 0.5),
        Word(" two", 1.5, 2.0),
        Word(" three", 3.5, 4.0),
    ])
    cues = SilenceSplit(silences=[(0.5, 1.5), (2.0, 3.5)], min_silence=0.4).split(s)
    assert len(cues) == 3


# --- Timestamps ---

def test_first_cue_starts_at_first_word():
    s = seg("hello there", "en", [
        Word(" hello", 5.0, 6.0),
        Word(" there", 7.0, 8.0),
    ])
    cues = SilenceSplit(silences=[(6.0, 7.0)], min_silence=0.4).split(s)
    assert cues[0].start == 5.0


def test_last_cue_ends_at_last_word():
    s = seg("hello there", "en", [
        Word(" hello", 5.0, 6.0),
        Word(" there", 7.0, 8.3),
    ])
    cues = SilenceSplit(silences=[(6.0, 7.0)], min_silence=0.4).split(s)
    assert cues[-1].end == 8.3
