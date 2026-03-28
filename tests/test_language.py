from halfhalf.language import of_text


def test_english_text():
    assert of_text("hello world") == 'en'


def test_korean_text():
    assert of_text("안녕하세요") == 'ko'


def test_mixed_hangul_dominant():
    assert of_text("안녕하세요 hi") == 'ko'


def test_mixed_ascii_dominant():
    assert of_text("hello 안 world") == 'en'


def test_equal_counts_returns_korean():
    assert of_text("hi 안녕") == 'ko'
