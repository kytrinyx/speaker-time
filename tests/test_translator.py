import json
import os
import pytest
from halfhalf.translator import Translator
from halfhalf.cue import Cue


def make_cue(text, start=0.0, end=1.0):
    return Cue(start, end, text)


@pytest.fixture
def cache_path(tmp_path):
    return str(tmp_path / "translations.json")


# --- lookup ---

def test_lookup_returns_cached_translation(cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)
    t._cache["ko-en"]["안녕하세요."] = "Hello."
    assert t.lookup("안녕하세요.", "ko", "en") == "Hello."


def test_lookup_returns_none_for_missing(cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)
    assert t.lookup("unknown", "ko", "en") is None


def test_lookup_returns_none_for_wrong_direction(cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)
    t._cache["ko-en"]["안녕."] = "Hello."
    assert t.lookup("안녕.", "en", "ko") is None


# --- cache loading ---

def test_loads_existing_cache(tmp_path):
    cache = {
        "ko-en": {"안녕하세요.": "Hello."},
        "en-ko": {"Hello.": "안녕하세요."},
    }
    cache_path = str(tmp_path / "translations.json")
    with open(cache_path, "w") as f:
        json.dump(cache, f)

    t = Translator(cohost="Jeep", cache_path=cache_path)
    assert t.lookup("안녕하세요.", "ko", "en") == "Hello."
    assert t.lookup("Hello.", "en", "ko") == "안녕하세요."


def test_starts_with_empty_cache_when_file_missing(cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)
    assert t._cache == {"ko-en": {}, "en-ko": {}}


# --- missing ---

def test_missing_returns_untranslated_texts(cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)
    t._cache["ko-en"]["안녕하세요."] = "Hello."

    cues = [make_cue("안녕하세요."), make_cue("감사합니다.")]
    result = t.missing(cues)
    assert result["ko-en"] == ["감사합니다."]


def test_missing_returns_empty_when_all_translated(cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)
    t._cache["ko-en"]["안녕하세요."] = "Hello."

    cues = [make_cue("안녕하세요.")]
    result = t.missing(cues)
    assert result["ko-en"] == []


def test_missing_only_considers_correct_language(cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)
    cues = [make_cue("Hello."), make_cue("안녕하세요.")]

    result = t.missing(cues)
    # "Hello." is en — appears in en-ko missing; "안녕하세요." is ko — appears in ko-en missing
    assert "Hello." in result["en-ko"]
    assert "안녕하세요." in result["ko-en"]
    assert "Hello." not in result["ko-en"]
    assert "안녕하세요." not in result["en-ko"]


# --- _translate_chunk parsing ---

def test_translate_chunk_parses_valid_json(tmp_path, cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)

    response = json.dumps([{"id": 1, "text": "Hello."}, {"id": 2, "text": "Thank you."}])
    log_path = str(tmp_path / "log.json")
    bad_path = str(tmp_path / "bad.json")

    t._call_replicate = lambda prompt: response
    result = t._translate_chunk(["안녕하세요.", "감사합니다."], "ko", "en", log_path, bad_path)
    assert result == ["Hello.", "Thank you."]


def test_translate_chunk_strips_markdown_fences(tmp_path, cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)

    inner = json.dumps([{"id": 1, "text": "Hello."}])
    response = f"```json\n{inner}\n```"
    log_path = str(tmp_path / "log.json")
    bad_path = str(tmp_path / "bad.json")

    t._call_replicate = lambda prompt: response
    result = t._translate_chunk(["안녕하세요."], "ko", "en", log_path, bad_path)
    assert result == ["Hello."]


def test_translate_chunk_raises_on_missing_ids(tmp_path, cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)

    # Returns only id 1 but we sent 2 items
    response = json.dumps([{"id": 1, "text": "Hello."}])
    log_path = str(tmp_path / "log.json")
    bad_path = str(tmp_path / "bad.json")

    t._call_replicate = lambda prompt: response
    with pytest.raises(ValueError):
        t._translate_chunk(["안녕하세요.", "감사합니다."], "ko", "en", log_path, bad_path)


def test_translate_chunk_raises_on_duplicate_ids(tmp_path, cache_path):
    t = Translator(cohost="Jeep", cache_path=cache_path)

    response = json.dumps([
        {"id": 1, "text": "Hello."},
        {"id": 1, "text": "Hi."},
    ])
    log_path = str(tmp_path / "log.json")
    bad_path = str(tmp_path / "bad.json")

    t._call_replicate = lambda prompt: response
    with pytest.raises(ValueError):
        t._translate_chunk(["안녕하세요."], "ko", "en", log_path, bad_path)
