import os
import shutil

from .cue import Cue
from . import paths


class SubtitlesGenerator:
    """Generate source and translated VTT subtitle files from a list of Cues.

    Produces four files per episode:
      <episode>.ko.vtt       — Korean cues (source)
      <episode>.en.vtt       — English cues (source)
      <episode>.ko-en.vtt    — Korean cues translated to English
      <episode>.en-ko.vtt    — English cues translated to Korean
    """

    def __init__(self, episode_id, cues, translator, subtitles_dir=None):
        self._episode_id = episode_id
        self._cues = cues
        self._translator = translator
        self._subtitles_dir = subtitles_dir or os.environ.get(
            "HALF_AND_HALF_SUBTITLES_DIR", os.path.expanduser("~/Desktop/")
        )

    def generate(self):
        """Write all VTT files and copy them to the subtitles directory."""
        subtitles_dir = paths.subtitles_dir(self._episode_id)
        os.makedirs(subtitles_dir, exist_ok=True)

        files = []

        for lang in ("ko", "en"):
            cues = [c for c in self._cues if c.language == lang]
            path, count = self._write_source_vtt(cues, lang)
            files.append((path, count))

        for source_lang, target_lang in (("ko", "en"), ("en", "ko")):
            cues = [c for c in self._cues if c.language == source_lang]
            path, count = self._write_translated_vtt(cues, source_lang, target_lang)
            files.append((path, count))

        for path, count in files:
            print(f"  - {os.path.basename(path)} ({count} cues)")
            shutil.copy(path, self._subtitles_dir)

        print(f"\n  Written to:\n  {subtitles_dir}/")
        print(f"\n  Copied to:\n  {self._subtitles_dir}")

    def _write_source_vtt(self, cues, lang):
        path = paths.vtt_file(self._episode_id, lang)
        with open(path, "w") as f:
            f.write("WEBVTT\n\n")
            for cue in cues:
                f.write(f"{cue}\n\n")
        return path, len(cues)

    def _write_translated_vtt(self, cues, source_lang, target_lang):
        path = paths.vtt_file(self._episode_id, source_lang, target_lang)
        written = 0
        with open(path, "w") as f:
            f.write("WEBVTT\n\n")
            for cue in cues:
                text = self._translator.lookup(cue.text, source_lang, target_lang)
                if not text or not text.strip():
                    continue
                f.write(f"{Cue.format_timestamp(cue.start)} --> {Cue.format_timestamp(cue.end)}\n")
                f.write(f"{text}\n\n")
                written += 1
        return path, written
