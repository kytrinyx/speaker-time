from halfhalf.fragment_splitter import FragmentSplitter, MAX_CHARS
from halfhalf.mimeograph import Fragment
from halfhalf.word import Word


def frag(*pairs):
    return Fragment([Word(text, start, end) for text, start, end in pairs])


class StubFallback:
    def __init__(self, indices=None):
        self.called = False
        self._indices = indices or []

    def find_splits(self, fragment):
        self.called = True
        return self._indices


def splitter(fallback=None, max_chars=None):
    return FragmentSplitter(
        fallback=fallback or StubFallback(),
        max_chars_by_lang=max_chars or MAX_CHARS,
    )


# --- basic cases ---

def test_empty_fragment_returns_no_cues():
    assert splitter().split(Fragment([])) == []


def test_short_fragment_returns_single_cue():
    f = frag(("Hello.", 0.0, 0.5))
    cues = splitter().split(f)
    assert len(cues) == 1
    assert cues[0].text == "Hello."
    assert cues[0].start == 0.0
    assert cues[0].end == 0.5


def test_short_fragment_does_not_call_fallback():
    stub = StubFallback()
    f = frag(("Hello.", 0.0, 0.5))
    splitter(fallback=stub).split(f)
    assert not stub.called


# --- splitting ---

def test_long_english_fragment_splits_on_cc():
    # "and" triggers EnSplit standard split; both halves fit within limit
    f = frag(
        ("I", 0.0, 0.2), ("went", 0.2, 0.5), ("home", 0.5, 0.8),
        ("and", 0.8, 1.0), ("I", 1.0, 1.1), ("made", 1.1, 1.4), ("dinner.", 1.4, 1.8),
    )
    cues = splitter(max_chars={"en": 20, "ko": 30, "default": 20}).split(f)
    assert len(cues) == 2
    assert cues[0].text == "I went home"
    assert cues[1].text == "and I made dinner."


def test_long_korean_fragment_splits_on_ec():
    f = frag(
        ("공부하고", 0.0, 0.5),
        ("싶어요.", 0.5, 1.0),
    )
    cues = splitter(max_chars={"ko": 5, "en": 50, "default": 50}).split(f)
    assert len(cues) == 2
    assert cues[0].text == "공부하고"
    assert cues[1].text == "싶어요."


# --- fallback ---

def test_fallback_called_when_chunks_still_too_long():
    stub = StubFallback(indices=[2])
    # Tiny char limit so everything is too long; no linguistic splits available
    f = frag(
        ("Well", 0.0, 0.3),
        ("yeah", 0.35, 0.7),
        ("okay", 0.75, 1.0),
        ("right.", 1.0, 1.3),
    )
    splitter(fallback=stub, max_chars={"en": 1, "ko": 1, "default": 1}).split(f)
    assert stub.called


def test_fallback_not_called_when_splits_sufficient():
    stub = StubFallback()
    f = frag(
        ("I", 0.0, 0.2), ("went", 0.2, 0.5), ("home", 0.5, 0.8),
        ("and", 0.8, 1.0), ("I", 1.0, 1.1), ("made", 1.1, 1.4), ("dinner.", 1.4, 1.8),
    )
    splitter(fallback=stub, max_chars={"en": 20, "ko": 30, "default": 20}).split(f)
    assert not stub.called


# --- cue timing ---

def test_cue_start_and_end_match_words():
    f = frag(
        ("I", 1.0, 1.2), ("went", 1.2, 1.5), ("home", 1.5, 1.8),
        ("and", 1.8, 2.0), ("slept.", 2.0, 2.4),
    )
    cues = splitter(max_chars={"en": 15, "ko": 30, "default": 15}).split(f)
    assert cues[0].start == 1.0
    assert cues[0].end == 1.8
    assert cues[1].start == 1.8
    assert cues[1].end == 2.4


# --- silence splits used as ordinary ---

def test_silence_gap_used_as_split_point():
    # Gap of 0.5s between "home" and "and" → silence split at index 3
    # With tiny char limit, silence split should be used
    f = frag(
        ("I", 0.0, 0.2), ("went", 0.2, 0.5), ("home", 0.5, 0.8),
        ("and", 1.3, 1.5), ("slept.", 1.5, 1.9),  # 0.5s gap
    )
    cues = splitter(max_chars={"en": 15, "ko": 30, "default": 15}).split(f)
    texts = [c.text for c in cues]
    assert "I went home" in texts
    assert "and slept." in texts
