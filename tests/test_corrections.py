from halfhalf.corrections import substitute


def test_unaffected_text_passes_through():
    assert substitute("안녕하세요") == "안녕하세요"


def test_corrects_podcast_name_korean():
    assert substitute("아프의 나프의") == "하프앤하프"


def test_corrects_podcast_name_english():
    assert substitute("Hathenah") == "Half and Half"


def test_corrects_host_name():
    assert substitute("정태우") == "정태웅"


def test_corrects_jeep():
    assert substitute("ZIF") == "Jeep"


def test_corrects_katrina():
    assert substitute("카트린 나") == "카트리나"


def test_corrects_podcast_word():
    assert substitute("파켓스") == "팟캐스트"


def test_longer_pattern_takes_precedence_over_shorter():
    # "하프 하프" is a substring of "하프앤하프앤하프앤하프" after partial replacement —
    # the longer pattern must be matched first.
    assert substitute("하프앤하프앤하프앤하프") == "하프앤하프"
