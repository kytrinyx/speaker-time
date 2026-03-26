import pytest
from halfhalf.segment import Segment, Word
import halfhalf.fragment_merger as fragment_merger
from halfhalf.fragment_merger import FragmentMerger, STRONG_MARKER, ORDINARY_MARKER, WEAK_MARKER


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


def merge(segment, split_indices, strong_indices=None, weak_indices=None, max_chars_by_lang=None):
    return fragment_merger.merge(segment, split_indices, strong_indices or [], weak_indices or [], max_chars_by_lang=max_chars_by_lang)


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
    s = seg("안녕, 얘들아.", "ko", [
        Word("안녕,", 0.0, 0.3),
        Word(" 얘들아.", 0.35, 1.0),
    ])
    result = merge(s, [1], max_chars_by_lang={"ko": 5, "default": 50})
    assert len(result) == 2


# --- Timestamps ---

def test_cue_timestamps():
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
    s = seg("안녕, 얘들아.", "ko", [
        Word("안녕,", 0.0, 0.5),
        Word(" 얘들아.", 0.5, 1.0),
    ])
    result = merge(s, split_indices=[1], weak_indices=[1], max_chars_by_lang={"ko": 5, "default": 50})
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


# --- __repr__ ---

def test_repr_all_three_markers():
    # jeep-ep-040 segment 1143: has weak merges (•), ordinary boundaries (○), and a strong boundary (⏹)
    text = "Like people who provide a service or who make art, like how can you separate the artist from the art and do you?"
    words = [
        Word(' Like', 4053.183, 4053.403),
        Word(' people', 4053.403, 4054.043),
        Word(' who', 4054.043, 4054.383),
        Word(' provide', 4054.383, 4054.803),
        Word(' a', 4054.803, 4054.903),
        Word(' service', 4054.903, 4055.323),
        Word(' or', 4055.323, 4055.643),
        Word(' who', 4055.643, 4055.803),
        Word(' make', 4055.803, 4055.983),
        Word(' art,', 4055.983, 4056.363),
        Word(' like', 4056.943, 4057.123),
        Word(' how', 4057.123, 4057.523),
        Word(' can', 4057.523, 4057.943),
        Word(' you', 4057.943, 4058.163),
        Word(' separate', 4058.163, 4058.623),
        Word(' the', 4058.623, 4059.183),
        Word(' artist', 4059.183, 4059.403),
        Word(' from', 4059.403, 4059.683),
        Word(' the', 4059.683, 4059.803),
        Word(' art', 4059.803, 4060.043),
        Word(' and', 4060.043, 4060.343),
        Word(' do', 4060.343, 4060.643),
        Word(' you?', 4060.643, 4060.803),
    ]
    s = Segment(id=1143, start=4053.183, end=4060.803, raw_text=text, language='en', words=words)
    fm = FragmentMerger(s, split_indices=[2, 6, 10, 17, 20], strong_indices=[10], weak_indices=[2, 10, 17])
    assert repr(fm) == (
        f"Segment 1143 (112 chars)\n"
        f"{text}\n"
        f"\n"
        f" < Like people {WEAK_MARKER} who provide a service {ORDINARY_MARKER} or who make art,\n"
        f" {STRONG_MARKER} like how can you separate the artist {WEAK_MARKER} from the art\n"
        f" {ORDINARY_MARKER} and do you?\n"
        f" >"
    )


def test_merge_across_ordinary_boundary_absorbing_fragment_from_weak_boundary():
    # jeep-ep-040 segment 1120: weak merge at index 3 succeeds, but index 8 is blocked by char limit
    # so index 8 appears as a • boundary (unmerged weak) rather than being absorbed
    text = "There's this concept of everything as a remix where if you're making something..."
    words = [
        Word(" There's", 3961.418, 3961.758),
        Word(' this', 3961.758, 3961.858),
        Word(' concept', 3961.858, 3962.218),
        Word(' of', 3962.218, 3962.438),
        Word(' everything', 3962.438, 3962.778),
        Word(' as', 3962.778, 3963.078),
        Word(' a', 3963.078, 3963.158),
        Word(' remix', 3963.158, 3963.478),
        Word(' where', 3963.478, 3964.478),
        Word(' if', 3964.478, 3966.078),
        Word(" you're", 3966.078, 3966.298),
        Word(' making', 3966.298, 3966.598),
        Word(' something...', 3966.598, 3967.498),
    ]
    s = Segment(id=1120, start=3961.418, end=3967.498, raw_text=text, language='en', words=words)
    fm = FragmentMerger(s, split_indices=[3, 8, 9], strong_indices=[], weak_indices=[3, 8])
    assert repr(fm) == (
        f"Segment 1120 (81 chars)\n"
        f"{text}\n"
        f"\n"
        f" < There's this concept {WEAK_MARKER} of everything as a remix\n"
        f" {WEAK_MARKER} where {ORDINARY_MARKER} if you're making something...\n"
        f" >"
    )
