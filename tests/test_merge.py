from halfhalf.segment import Segment, Word
from halfhalf.merge import FragmentMerger


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


def merge(segment, split_indices, strong_indices=None, weak_indices=None):
    return FragmentMerger().merge(segment, split_indices, strong_indices or [], weak_indices or [])


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


# --- Two chunks, no trigger ---

def test_two_chunks_no_trigger_returns_two_cues():
    # Each chunk is long enough and slow enough to not trigger pairing
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
    # Split after word 3; each chunk is 4s duration, 4 words — not brief or dense
    result = merge(s, [4])
    assert len(result) == 2
    assert "\n" not in result[0].text
    assert "\n" not in result[1].text


# --- Too brief trigger ---

def test_brief_chunk_pairs_with_next():
    # First chunk: 0.4s duration — too brief (< 0.6s)
    s = seg("hi there how are you", "en", [
        Word(" hi", 0.0, 0.2),
        Word(" there", 0.2, 0.4),
        Word(" how", 0.4, 1.0),
        Word(" are", 1.0, 1.5),
        Word(" you", 1.5, 2.0),
    ])
    result = merge(s, [2])
    assert len(result) == 1
    assert "\n" in result[0].text
    assert result[0].start == 0.0
    assert result[0].end == 2.0


def test_brief_chunk_not_paired_when_gap_too_large():
    # 0.4s gap between chunks → guard fails
    s = seg("hi there", "en", [
        Word(" hi", 0.0, 0.2),
        Word(" there", 1.0, 1.5),
    ])
    result = merge(s, [1])
    assert len(result) == 2


def test_brief_chunk_not_paired_when_next_exceeds_char_limit():
    # Next chunk text exceeds Korean char limit (22)
    long_next = "가나다라마바사아자차카타파하가나다라마바사아자"  # 23 chars
    s = seg("안녕 " + long_next, "ko", [
        Word("안녕", 0.0, 0.3),
        Word(" " + long_next, 0.35, 1.5),
    ])
    result = merge(s, [1])
    assert len(result) == 2


# --- Too dense trigger ---

def test_dense_chunk_pairs_with_next():
    # English read speed threshold: 17 chars/s
    # Chunk: "Hello world" (11 chars) over 0.5s = 22 chars/s → too dense
    s = seg("Hello world how are you doing today", "en", [
        Word(" Hello", 0.0, 0.25),
        Word(" world", 0.25, 0.5),
        Word(" how", 0.5, 1.0),
        Word(" are", 1.0, 1.5),
        Word(" you", 1.5, 2.0),
        Word(" doing", 2.0, 2.5),
        Word(" today", 2.5, 3.0),
    ])
    result = merge(s, [2])
    assert len(result) == 1
    assert "\n" in result[0].text


# --- Mandatory boundary ---

def test_mandatory_boundary_prevents_pairing():
    # First chunk too brief, but boundary is mandatory
    s = seg("hello there how are you", "en", [
        Word(" hello", 0.0, 0.2),
        Word(" there", 0.2, 0.4),
        Word(" how", 0.4, 1.0),
        Word(" are", 1.0, 1.5),
        Word(" you", 1.5, 2.0),
    ])
    result = merge(s, split_indices=[2], strong_indices=[2])
    assert len(result) == 2


# --- Three chunks ---

def test_three_chunks_first_brief_mandatory_after_second():
    # Chunks: [0,1] [2,3] [4]
    # Boundary 2 is NOT mandatory, boundary 4 IS mandatory
    # Chunk 0-1: 0.4s duration → too brief → pairs with chunk 2-3
    # Chunk 4: mandatory wall before it → stays separate
    s = seg("hi there how are you", "en", [
        Word(" hi", 0.0, 0.2),
        Word(" there", 0.2, 0.4),
        Word(" how", 0.4, 1.0),
        Word(" are", 1.0, 1.5),
        Word(" you", 1.5, 2.0),
    ])
    result = merge(s, split_indices=[2, 4], strong_indices=[4])
    assert len(result) == 2
    assert "\n" in result[0].text   # paired
    assert "\n" not in result[1].text  # single


# --- Timestamps ---

def test_paired_cue_spans_both_chunks():
    s = seg("hi there", "en", [
        Word(" hi", 1.0, 1.3),
        Word(" there", 1.35, 2.0),
    ])
    result = merge(s, [1])
    assert result[0].start == 1.0
    assert result[0].end == 2.0


def test_single_cue_timestamps():
    s = seg("hello there", "en", [
        Word(" hello", 0.5, 1.5),
        Word(" there", 2.0, 3.0),
    ])
    result = merge(s, [])
    assert result[0].start == 0.5
    assert result[0].end == 3.0


# --- Rebalancing ---

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
    result = merge(s, split_indices=[1], weak_indices=[1])
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


# --- Rebalancing ---

def test_english_rebalance_splits_near_midpoint():
    # "hello there" (5+5=10 chars) paired with "how are" (3+3=6 chars)
    # Combined 16 chars, midpoint 8, best split after "hello there" (10) vs after "hello"(5)
    # After "hello": dist=3, after "hello there": dist=2 → split after "hello there"
    # So line1="hello there", line2="how are"
    s = seg("hello there how are", "en", [
        Word(" hello", 0.0, 0.2),
        Word(" there", 0.2, 0.4),
        Word(" how", 0.4, 1.0),
        Word(" are", 1.0, 1.5),
    ])
    result = merge(s, [2])
    assert len(result) == 1
    lines = result[0].text.split("\n")
    assert len(lines) == 2
