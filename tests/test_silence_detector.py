from halfhalf.silence_detector import parse


FFMPEG_OUTPUT = """
[silencedetect @ 0x7fb96dc04640] silence_start: 1.2185
[silencedetect @ 0x7fb96dc04640] silence_end: 1.993271 | silence_duration: 0.774771
[silencedetect @ 0x7fb96dc04640] silence_start: 3.654667
[silencedetect @ 0x7fb96dc04640] silence_end: 3.883062 | silence_duration: 0.228396
[silencedetect @ 0x7fb96dc04640] silence_start: 3.925896
[silencedetect @ 0x7fb96dc04640] silence_end: 4.028146 | silence_duration: 0.10225
[silencedetect @ 0x7fb96dc04640] silence_start: 5.335167
[silencedetect @ 0x7fb96dc04640] silence_end: 5.476625 | silence_duration: 0.141458
"""


def test_parse_returns_four_silences():
    result = parse(FFMPEG_OUTPUT)
    assert len(result) == 4


def test_parse_start_and_end_times():
    result = parse(FFMPEG_OUTPUT)
    assert result[0] == (1.2185, 1.993271)
    assert result[1] == (3.654667, 3.883062)
    assert result[2] == (3.925896, 4.028146)
    assert result[3] == (5.335167, 5.476625)


def test_parse_empty_output():
    assert parse("") == []


def test_parse_no_silence_lines():
    assert parse("ffmpeg version 6.0\nsome other output\n") == []
