from halfhalf.backchannel import is_backchannel
from halfhalf.cue import Cue


def cue(text):
    return Cue(0.0, 1.0, text)


# --- should filter ---

def test_filters_korean_filler_um():
    assert is_backchannel(cue("음."))

def test_filters_korean_filler_eo():
    assert is_backchannel(cue("어."))

def test_filters_english_um():
    assert is_backchannel(cue("Um."))

def test_filters_english_uh():
    assert is_backchannel(cue("uh..."))

def test_filters_mm_hmm():
    assert is_backchannel(cue("mm-hmm."))

def test_filters_multiple_fillers():
    assert is_backchannel(cue("음, 어."))

def test_filters_mixed_language_fillers():
    assert is_backchannel(cue("음. um."))


# --- should not filter ---

def test_keeps_yes_english():
    assert not is_backchannel(cue("Yes."))

def test_keeps_right():
    assert not is_backchannel(cue("Right."))

def test_keeps_bye():
    assert not is_backchannel(cue("Bye-bye."))

def test_keeps_korean_yes():
    assert not is_backchannel(cue("네."))

def test_keeps_substantive_with_filler():
    assert not is_backchannel(cue("음, 그렇구나."))

def test_keeps_substantive_with_filler_english():
    assert not is_backchannel(cue("Um, I see."))

def test_keeps_empty_text():
    assert not is_backchannel(cue(""))
