import pytest
import spacy

from halfhalf.segment import Segment
from halfhalf.word import Word
from halfhalf.spacy_split import SpacySplit, _find_split_space_indices

_nlp = spacy.load("en_core_web_sm")


def seg(text, language, words):
    start = words[0].start if words else 0.0
    end = words[-1].end if words else 1.0
    return Segment(id=1, start=start, end=end, raw_text=text, language=language, words=words)


# --- _find_split_space_indices ---

def test_splits_on_cc_with_verb_head():
    # "and" is cc with head=went (VERB) → split after space-word 2 ("home")
    result = _find_split_space_indices("I went home and I made dinner", _nlp)
    assert 2 in result

def test_splits_on_but():
    result = _find_split_space_indices("She likes apples but hates oranges", _nlp)
    assert 2 in result

def test_splits_on_mark_if():
    # "if" is mark → split after space-word 2 ("go")
    result = _find_split_space_indices("We can go if you want", _nlp)
    assert 2 in result

def test_splits_on_mark_because():
    result = _find_split_space_indices("I stayed home because it was raining", _nlp)
    assert any(i > 0 for i in result)

def test_no_split_single_word():
    assert _find_split_space_indices("Hello", _nlp) == []

def test_no_split_simple_sentence():
    assert _find_split_space_indices("I like coffee", _nlp) == []

def test_no_split_cc_with_noun_head():
    # "and" joins nouns, not verbs
    assert _find_split_space_indices("cats and dogs", _nlp) == []


# --- SpacySplit.find_splits ---

def test_korean_returns_empty():
    s = seg("안녕하세요 반갑습니다", "ko", [
        Word("안녕하세요", 0.0, 0.8),
        Word(" 반갑습니다", 0.8, 1.5),
    ])
    assert SpacySplit().find_splits(s) == []

def test_no_words_returns_empty():
    s = Segment(id=1, start=0.0, end=1.0, raw_text="Hello there", language="en", words=[])
    assert SpacySplit().find_splits(s) == []

def test_english_without_clause_boundary_returns_empty():
    s = seg("I like coffee", "en", [
        Word("I", 0.0, 0.3),
        Word(" like", 0.3, 0.6),
        Word(" coffee", 0.6, 1.0),
    ])
    assert SpacySplit().find_splits(s) == []

def test_english_with_cc_returns_whisper_index():
    # Split before "and" → new chunk starts at Whisper word 3
    s = seg("I went home and I made dinner", "en", [
        Word("I", 0.0, 0.2),
        Word(" went", 0.2, 0.5),
        Word(" home", 0.5, 0.8),
        Word(" and", 0.8, 1.0),
        Word(" I", 1.0, 1.1),
        Word(" made", 1.1, 1.4),
        Word(" dinner", 1.4, 1.8),
    ])
    assert SpacySplit().find_splits(s) == [3]

def test_english_with_mark_returns_whisper_index():
    # Split before "if" → new chunk starts at Whisper word 3
    s = seg("We can go if you want", "en", [
        Word("We", 0.0, 0.2),
        Word(" can", 0.2, 0.4),
        Word(" go", 0.4, 0.6),
        Word(" if", 0.6, 0.8),
        Word(" you", 0.8, 1.0),
        Word(" want", 1.0, 1.3),
    ])
    assert SpacySplit().find_splits(s) == [3]

def test_cc_not_falsely_matched_as_substring():
    # "and" appears inside "cando" (can+do) in the normalized whisper stream —
    # must map to the actual standalone "and" word (index 8), not word index 1 ("can").
    # ccomp also fires on the "what..." clauses, giving additional splits at word 3.
    s = seg("they can do what they want to do and I'll do what I want to do.", "en", [
        Word(" they", 0.0, 0.2),
        Word(" can", 0.2, 0.4),
        Word(" do", 0.4, 0.6),
        Word(" what", 0.6, 0.8),
        Word(" they", 0.8, 1.0),
        Word(" want", 1.0, 1.2),
        Word(" to", 1.2, 1.4),
        Word(" do", 1.4, 1.6),
        Word(" and", 1.6, 1.8),
        Word(" I'll", 1.8, 2.0),
        Word(" do", 2.0, 2.2),
        Word(" what", 2.2, 2.4),
        Word(" I", 2.4, 2.6),
        Word(" want", 2.6, 2.8),
        Word(" to", 2.8, 3.0),
        Word(" do", 3.0, 3.2),
        Word(".", 3.2, 3.4),
    ])
    result = SpacySplit().find_splits(s)
    assert 8 in result       # cc split before "and" — the key regression check
    assert result == sorted(set(result))  # no duplicates
