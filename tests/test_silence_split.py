from halfhalf.segment import Segment, Word
from halfhalf.silence_split import SilenceSplit


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


# --- No split cases ---

def test_no_silences_returns_empty():
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.0, 2.0),
    ])
    result = SilenceSplit(silences=[]).find_splits(s)
    assert result == {'mandatory': [], 'potential': []}


def test_silence_below_potential_threshold_returns_empty():
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.05, 2.0),
    ])
    result = SilenceSplit(silences=[(1.0, 1.05)]).find_splits(s)
    assert result == {'mandatory': [], 'potential': []}


def test_no_words_returns_empty():
    s = Segment(id=1, start=0.0, end=2.0, raw_text="hello", language="en", words=[])
    result = SilenceSplit(silences=[(0.5, 1.5)]).find_splits(s)
    assert result == {'mandatory': [], 'potential': []}


# --- Potential only (0.1s–0.4s) ---

def test_silence_above_potential_but_below_mandatory():
    # 0.3s silence: potential only
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.3, 2.0),
    ])
    result = SilenceSplit(silences=[(1.0, 1.3)]).find_splits(s)
    assert result == {'mandatory': [], 'potential': [1]}


# --- Mandatory (≥ 0.4s) ---

def test_silence_above_mandatory_threshold():
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.8, 2.5),
    ])
    result = SilenceSplit(silences=[(1.0, 1.8)]).find_splits(s)
    assert result == {'mandatory': [1], 'potential': [1]}


# --- Multiple silences ---

def test_multiple_silences_produce_multiple_indices():
    s = seg("one two three", "en", [
        Word(" one", 0.0, 0.5),
        Word(" two", 1.5, 2.0),
        Word(" three", 3.5, 4.0),
    ])
    result = SilenceSplit(silences=[(0.5, 1.5), (2.0, 3.5)]).find_splits(s)
    assert result == {'mandatory': [1, 2], 'potential': [1, 2]}


def test_mixed_mandatory_and_potential():
    # first gap 0.3s (potential only), second gap 0.8s (mandatory)
    s = seg("one two three", "en", [
        Word(" one", 0.0, 0.5),
        Word(" two", 0.8, 1.3),
        Word(" three", 2.1, 2.8),
    ])
    result = SilenceSplit(silences=[(0.5, 0.8), (1.3, 2.1)]).find_splits(s)
    assert result == {'mandatory': [2], 'potential': [1, 2]}


# --- Index values ---

def test_index_points_to_start_of_next_chunk():
    # split after words[0] → new chunk starts at words[1] → index 1
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.5, 2.5),
    ])
    result = SilenceSplit(silences=[(1.0, 1.5)]).find_splits(s)
    assert result['potential'] == [1]
