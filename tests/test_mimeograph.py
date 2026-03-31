from halfhalf.mimeograph import Fragment, Mimeograph
from halfhalf.word import Word


def make_words(*pairs):
    """Build a word list from (text, start, end) tuples."""
    return [Word(text, start, end) for text, start, end in pairs]


def test_fragments_splits_on_period():
    m = Mimeograph(make_words(
        ("Thank", 0.0, 0.3),
        ("you.", 0.4, 0.7),
        ("Bye.", 0.8, 1.0),
    ))
    fragments = m.fragments
    assert len(fragments) == 2
    assert fragments[0].text == "Thank you."
    assert fragments[1].text == "Bye."


def test_fragments_splits_on_question_mark():
    m = Mimeograph(make_words(
        ("Really?", 0.0, 0.5),
        ("Yes.", 0.6, 0.9),
    ))
    fragments = m.fragments
    assert len(fragments) == 2
    assert fragments[0].text == "Really?"


def test_fragments_splits_on_exclamation():
    m = Mimeograph(make_words(
        ("화이팅!", 0.0, 0.5),
        ("Good.", 0.6, 0.9),
    ))
    assert len(m.fragments) == 2


def test_fragments_trailing_words_without_punctuation():
    m = Mimeograph(make_words(
        ("Hello.", 0.0, 0.4),
        ("Yeah", 0.5, 0.7),
        ("...", 0.8, 1.0),
    ))
    fragments = m.fragments
    assert len(fragments) == 2
    assert fragments[1].text == "Yeah ..."


def test_fragment_start_and_end():
    m = Mimeograph(make_words(
        ("Hello", 1.0, 1.4),
        ("there.", 1.5, 2.0),
    ))
    f = m.fragments[0]
    assert f.start == 1.0
    assert f.end == 2.0


def test_fragment_language_english():
    m = Mimeograph(make_words(
        ("Good", 0.0, 0.3),
        ("job.", 0.4, 0.6),
    ))
    assert m.fragments[0].language == "en"


def test_fragment_language_korean():
    m = Mimeograph(make_words(
        ("감사합니다.", 0.0, 0.8),
    ))
    assert m.fragments[0].language == "ko"


def test_fragments_splits_on_significant_silence():
    m = Mimeograph(make_words(
        ("Well", 0.0, 0.3),
        ("yeah", 0.75, 1.0),  # 0.45s gap — split
        ("okay", 1.1, 1.4),
    ))
    assert len(m.fragments) == 2
    assert m.fragments[0].text == "Well"
    assert m.fragments[1].text == "yeah okay"


def test_fragments_no_split_on_small_silence():
    m = Mimeograph(make_words(
        ("Well", 0.0, 0.3),
        ("yeah", 0.65, 1.0),  # 0.35s gap — no split
        ("okay", 1.1, 1.4),
    ))
    assert len(m.fragments) == 1


def test_silence_splits_returns_indices_for_gaps_over_threshold():
    words = make_words(
        ("Well", 0.0, 0.3),
        ("yeah", 0.45, 0.8),  # 0.15s gap — standard
        ("okay", 0.92, 1.2),  # 0.12s gap — standard, included
        ("right", 1.25, 1.5), # 0.05s gap — below threshold, excluded
    )
    f = Fragment(words)
    assert f.silence_splits == [1, 2]


def test_silence_splits_empty_when_no_gaps():
    words = make_words(
        ("Hello", 0.0, 0.4),
        ("there", 0.4, 0.8),
        ("world", 0.8, 1.2),
    )
    assert Fragment(words).silence_splits == []


def test_silence_splits_single_word():
    assert Fragment(make_words(("Hello.", 0.0, 0.5))).silence_splits == []


def test_fragments_split_on_language_switch():
    m = Mimeograph(make_words(
        ("네", 0.0, 0.2),
        ("um,", 0.25, 0.5),
        ("that", 0.5, 0.7),
        ("I", 0.7, 0.9),
    ))
    fragments = m.fragments
    assert len(fragments) == 2
    assert fragments[0].text == "네"
    assert fragments[1].text == "um, that I"


def test_fragments_no_split_on_punctuation_between_same_language():
    m = Mimeograph(make_words(
        ("좋아요,", 0.0, 0.4),
        ("그리고", 0.45, 0.8),
    ))
    assert len(m.fragments) == 1


def test_fragments_no_split_on_number_between_language_switch():
    m = Mimeograph(make_words(
        ("네,", 0.0, 0.2),
        ("3", 0.25, 0.35),
        ("months", 0.4, 0.7),
    ))
    # "3" has no alphabetic content — no lang switch triggered on either side
    assert len(m.fragments) == 1
    assert m.fragments[0].text == "네, 3 months"


def test_fragments_split_on_silence_and_punctuation():
    m = Mimeograph(make_words(
        ("Nice.", 0.0, 0.3),
        ("Well", 0.8, 1.1),   # 0.5s gap after punctuation — already split by punctuation
        ("yeah", 1.6, 1.9),   # 0.5s gap — split
        ("okay", 2.0, 2.3),
    ))
    assert len(m.fragments) == 3
