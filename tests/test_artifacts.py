from halfhalf.artifacts import fixup


def test_normal_text_passes_through():
    assert fixup("Hello world", "en") == "Hello world"


def test_strips_leading_and_trailing_whitespace():
    assert fixup("  hello  ", "en") == "hello"


def test_timeout_returns_empty():
    assert fixup("[TIMEOUT]", "en") == ""
    assert fixup("[TIMEOUT]", "ko") == ""


def test_empty_string_returns_empty():
    assert fixup("", "en") == ""


def test_applies_corrections():
    assert fixup("아프의 나프의", "ko") == "하프앤하프"


def test_collapses_repeated_korean_characters():
    assert fixup("가가가가가", "ko") == "가가가"


def test_does_not_collapse_korean_below_threshold():
    assert fixup("가가가가", "ko") == "가가가가"


def test_collapses_mmm():
    assert fixup("Mmmmmm", "en") == "Mmm"


def test_english_filler_returns_empty():
    assert fixup("hahaha", "en") == ""


def test_korean_filler_returns_empty():
    assert fixup("으", "ko") == ""


def test_non_filler_korean_passes_through():
    assert fixup("안녕하세요", "ko") == "안녕하세요"
