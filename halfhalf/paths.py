import os


def episode_dir(episode_id):
    return os.path.join("output", episode_id)


def data_dir(episode_id):
    return os.path.join("output", episode_id, "data")


def audio_file(episode_id):
    return os.path.join("audio", f"{episode_id}.mp3")


def timeline_csv(episode_id):
    return os.path.join("output", episode_id, "data", "timeline.csv")


def metadata_json(episode_id):
    return os.path.join("output", episode_id, "metadata.json")


def transcription_csv(episode_id):
    return os.path.join("output", episode_id, "data", "transcription.csv")


def words_csv(episode_id):
    return os.path.join("output", episode_id, "data", "words.csv")


def llm_corrections_cache(episode_id):
    return os.path.join("output", episode_id, "data", "llm_corrections_cache.json")


def split_segments_json(episode_id):
    return os.path.join("output", episode_id, "data", "split_segments.json")


def backups_dir(episode_id):
    return os.path.join("output", episode_id, "backups")


def audio_dir(episode_id):
    return os.path.join("output", episode_id, "audio")


def audio_segment(episode_id, segment_id):
    return os.path.join("output", episode_id, "audio", f"{segment_id:06d}.mp3")


def language_detection_dir(episode_id):
    return os.path.join("output", episode_id, "language_detection")


def subtitles_dir(episode_id):
    return os.path.join("output", episode_id, "subtitles")


def vtt_file(episode_id, source_lang, target_lang=None):
    if target_lang is None:
        target_lang = source_lang
    return os.path.join("output", episode_id, "subtitles", f"{episode_id}.{source_lang}-{target_lang}.vtt")


def ollama_cache(episode_id):
    return os.path.join("output", episode_id, "data", "ollama_cache.json")


def translation_cache(episode_id, source_lang, target_lang):
    return os.path.join("output", episode_id, f"translation.{source_lang}-{target_lang}.cache.json")
