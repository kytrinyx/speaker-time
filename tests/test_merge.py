from halfhalf.segment import Segment, Word
from halfhalf.merge import FragmentMerger


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


def merge(segment, split_indices, strong_indices=None, weak_indices=None, max_chars_by_lang=None):
    return FragmentMerger(max_chars_by_lang=max_chars_by_lang).merge(segment, split_indices, strong_indices or [], weak_indices or [])


# --- No splits ---

def test_no_words_returns_single_cue():
    s = Segment(id=1, start=0.0, end=1.0, raw_text="hello", language="en", words=[])
    result = merge(s, [])
    assert len(result) == 1


def test_no_split_indices_returns_single_cue():
    s = seg("hello there", "en", [
        Word(" hello", 0.0, 0.4),
        Word(" there", 0.4, 0.8),
    ])
    result = merge(s, [])
    assert len(result) == 1
    assert result[0].text == "hello there"


# --- Split indices ---

def test_two_chunks_returns_two_cues():
    s = seg("hello there how are you doing today friend", "en", [
        Word(" hello", 0.0, 1.0),
        Word(" there", 1.0, 2.0),
        Word(" how", 2.0, 3.0),
        Word(" are", 3.0, 4.0),
        Word(" you", 4.0, 5.0),
        Word(" doing", 5.0, 6.0),
        Word(" today", 6.0, 7.0),
        Word(" friend", 7.0, 8.0),
    ])
    result = merge(s, [4])
    assert len(result) == 2
    assert "\n" not in result[0].text
    assert "\n" not in result[1].text


def test_strong_boundary_produces_two_cues():
    s = seg("hello there how are you", "en", [
        Word(" hello", 0.0, 0.2),
        Word(" there", 0.2, 0.4),
        Word(" how", 0.4, 1.0),
        Word(" are", 1.0, 1.5),
        Word(" you", 1.5, 2.0),
    ])
    result = merge(s, split_indices=[2], strong_indices=[2])
    assert len(result) == 2


def test_next_chunk_exceeds_char_limit_produces_two_cues():
    long_next = "가나다라마바사아자차카타파하가나다라마바사아자"  # 23 chars > Korean limit of 22
    s = seg("안녕 " + long_next, "ko", [
        Word("안녕", 0.0, 0.3),
        Word(" " + long_next, 0.35, 1.5),
    ])
    result = merge(s, [1])
    assert len(result) == 2


# --- Timestamps ---

def test_single_cue_timestamps():
    s = seg("hello there", "en", [
        Word(" hello", 0.5, 1.5),
        Word(" there", 2.0, 3.0),
    ])
    result = merge(s, [])
    assert result[0].start == 0.5
    assert result[0].end == 3.0


# --- Weak boundary ---

def test_weak_boundary_merges_if_fits():
    # Fragments "hello there" + "my friend" fit within char limit → merged into one
    s = seg("hello there my friend", "en", [
        Word(" hello", 0.0, 0.5),
        Word(" there", 0.5, 1.0),
        Word(" my", 1.0, 1.5),
        Word(" friend", 1.5, 2.0),
    ])
    result = merge(s, split_indices=[2], weak_indices=[2])
    assert len(result) == 1
    assert "\n" not in result[0].text

def test_weak_boundary_not_merged_if_exceeds_char_limit():
    long = "가나다라마바사아자차카타파하가나다라마바사아자"  # 23 chars > Korean limit of 22
    s = seg("안녕 " + long, "ko", [
        Word("안녕", 0.0, 0.5),
        Word(" " + long, 0.5, 1.5),
    ])
    result = merge(s, split_indices=[1], weak_indices=[1], max_chars_by_lang={"ko": 22, "default": 50})
    assert len(result) == 2

def test_weak_boundary_not_merged_across_strong():
    # weak split coincides with strong split → strong wins, no merge
    s = seg("hello there my friend", "en", [
        Word(" hello", 0.0, 0.5),
        Word(" there", 0.5, 1.0),
        Word(" my", 1.0, 1.5),
        Word(" friend", 1.5, 2.0),
    ])
    result = merge(s, split_indices=[2], strong_indices=[2], weak_indices=[2])
    assert len(result) == 2
