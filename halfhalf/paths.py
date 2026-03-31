import os


def audio_file(episode_id):
    return os.path.join("audio", f"{episode_id}.mp3")


def metadata_json(episode_id):
    return os.path.join("output", episode_id, "metadata.json")


def subtitles_dir(episode_id):
    return os.path.join("output", episode_id, "subtitles")


def vtt_file(episode_id, source_lang, target_lang=None):
    if target_lang is None:
        target_lang = source_lang
    return os.path.join("output", episode_id, "subtitles", f"{episode_id}.{source_lang}-{target_lang}.vtt")


def llm_splits_json(episode_id):
    return os.path.join("output", episode_id, "data", "llm-splits.json")


def translations_json(episode_id):
    return os.path.join("output", episode_id, "data", "translations.json")


def transcription_json(episode_id):
    return os.path.join("output", episode_id, "data", "transcription.json")
