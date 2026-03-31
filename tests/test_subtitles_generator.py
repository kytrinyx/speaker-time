import os
import pytest
from halfhalf.subtitles_generator import SubtitlesGenerator
from halfhalf.cue import Cue


class StubTranslator:
    def __init__(self, translations=None):
        self._translations = translations or {}

    def lookup(self, text, source_lang, target_lang):
        return self._translations.get((text, source_lang, target_lang))


def make_cue(text, start=0.0, end=1.0):
    return Cue(start, end, text)


@pytest.fixture
def episode_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return "test-ep-001"


def generator(episode_id, cues, translator, tmp_path):
    return SubtitlesGenerator(episode_id, cues, translator, subtitles_dir=str(tmp_path / "dest"))


# --- source VTT files ---

def test_writes_korean_source_vtt(episode_id, tmp_path):
    cues = [make_cue("안녕하세요.", 0.0, 1.5)]
    gen = generator(episode_id, cues, StubTranslator(), tmp_path)
    gen.generate()

    vtt = tmp_path / "output" / episode_id / "subtitles" / f"{episode_id}.ko-ko.vtt"
    content = vtt.read_text()
    assert content.startswith("WEBVTT\n")
    assert "안녕하세요." in content


def test_writes_english_source_vtt(episode_id, tmp_path):
    cues = [make_cue("Hello there.", 0.0, 1.5)]
    gen = generator(episode_id, cues, StubTranslator(), tmp_path)
    gen.generate()

    vtt = tmp_path / "output" / episode_id / "subtitles" / f"{episode_id}.en-en.vtt"
    content = vtt.read_text()
    assert content.startswith("WEBVTT\n")
    assert "Hello there." in content


def test_source_vtt_contains_timestamp(episode_id, tmp_path):
    cues = [make_cue("Hello.", 61.0, 62.5)]
    gen = generator(episode_id, cues, StubTranslator(), tmp_path)
    gen.generate()

    vtt = tmp_path / "output" / episode_id / "subtitles" / f"{episode_id}.en-en.vtt"
    content = vtt.read_text()
    assert "00:01:01.000 --> 00:01:02.500" in content


# --- translated VTT files ---

def test_writes_translated_vtt_when_translation_available(episode_id, tmp_path):
    cues = [make_cue("안녕하세요.", 0.0, 1.5)]
    translator = StubTranslator({("안녕하세요.", "ko", "en"): "Hello."})
    gen = generator(episode_id, cues, translator, tmp_path)
    gen.generate()

    vtt = tmp_path / "output" / episode_id / "subtitles" / f"{episode_id}.ko-en.vtt"
    content = vtt.read_text()
    assert "Hello." in content


def test_translated_vtt_skips_missing_translation(episode_id, tmp_path):
    cues = [
        make_cue("안녕하세요.", 0.0, 1.5),
        make_cue("감사합니다.", 2.0, 3.0),
    ]
    translator = StubTranslator({("안녕하세요.", "ko", "en"): "Hello."})
    gen = generator(episode_id, cues, translator, tmp_path)
    gen.generate()

    vtt = tmp_path / "output" / episode_id / "subtitles" / f"{episode_id}.ko-en.vtt"
    content = vtt.read_text()
    assert "Hello." in content
    assert "감사합니다." not in content


def test_translated_vtt_skips_empty_translation(episode_id, tmp_path):
    cues = [make_cue("음.", 0.0, 0.5)]
    translator = StubTranslator({("음.", "ko", "en"): ""})
    gen = generator(episode_id, cues, translator, tmp_path)
    gen.generate()

    vtt = tmp_path / "output" / episode_id / "subtitles" / f"{episode_id}.ko-en.vtt"
    content = vtt.read_text()
    # Only the header — no cues written
    assert content.strip() == "WEBVTT"


def test_translated_vtt_skips_whitespace_only_translation(episode_id, tmp_path):
    cues = [make_cue("음.", 0.0, 0.5)]
    translator = StubTranslator({("음.", "ko", "en"): "   "})
    gen = generator(episode_id, cues, translator, tmp_path)
    gen.generate()

    vtt = tmp_path / "output" / episode_id / "subtitles" / f"{episode_id}.ko-en.vtt"
    content = vtt.read_text()
    assert content.strip() == "WEBVTT"


# --- cues routed to correct file ---

def test_korean_cues_excluded_from_english_vtt(episode_id, tmp_path):
    cues = [make_cue("안녕하세요.", 0.0, 1.0), make_cue("Hello.", 1.5, 2.0)]
    gen = generator(episode_id, cues, StubTranslator(), tmp_path)
    gen.generate()

    vtt = tmp_path / "output" / episode_id / "subtitles" / f"{episode_id}.en-en.vtt"
    content = vtt.read_text()
    assert "안녕하세요." not in content
    assert "Hello." in content


def test_copies_files_to_destination(episode_id, tmp_path):
    cues = [make_cue("Hello.", 0.0, 1.0)]
    dest = tmp_path / "dest"
    dest.mkdir()
    gen = SubtitlesGenerator(episode_id, cues, StubTranslator(), subtitles_dir=str(dest))
    gen.generate()

    copied = list(dest.iterdir())
    assert len(copied) == 4
