from halfhalf.corrections import apply


def test_unaffected_text_passes_through():
    assert apply("안녕하세요") == "안녕하세요"


def test_corrects_podcast_name_korean():
    assert apply("아프의 나프의") == "하프앤하프"


def test_corrects_podcast_name_english():
    assert apply("Hathenah") == "Half and Half"


def test_corrects_host_name():
    assert apply("정태우") == "정태웅"


def test_corrects_jeep():
    assert apply("ZIF") == "Jeep"


def test_corrects_katrina():
    assert apply("카트린 나") == "카트리나"


def test_corrects_podcast_word():
    assert apply("파켓스") == "팟캐스트"


def test_longer_pattern_takes_precedence_over_shorter():
    # "하프 하프" is a substring of "하프앤하프앤하프앤하프" after partial replacement —
    # the longer pattern must be matched first.
    assert apply("하프앤하프앤하프앤하프") == "하프앤하프"
