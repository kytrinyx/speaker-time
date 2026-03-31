import glob
import json
import os
import subprocess

from . import paths
from .youtube_metadata import YoutubeMetadata


class Downloader:
    """Download a YouTube episode as MP3 and assign it an episode ID.

    Episode IDs are assigned sequentially per cohost prefix, e.g. jeep-ep-001.
    """

    def __init__(self, project_root=None, metadata_class=None):
        self._root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._metadata_class = metadata_class or YoutubeMetadata

    def download(self, url, cohost):
        """Download the audio for the given URL and return the episode_id."""
        episode_id = self._next_episode_id(cohost)

        output_dir = os.path.join(self._root, "output", episode_id)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(self._root, "audio"), exist_ok=True)

        mp3_path = os.path.join(self._root, "audio", f"{episode_id}.mp3")
        if os.path.exists(mp3_path):
            raise FileExistsError(f"{episode_id} already exists at audio/{episode_id}.mp3")

        self._save_metadata(url, episode_id)

        mp3_path = os.path.join(self._root, "audio", f"{episode_id}.mp3")
        subprocess.run(
            [
                "yt-dlp", "--extract-audio", "--audio-format=mp3", "--quiet",
                "-o", os.path.join(self._root, "audio", f"{episode_id}.%(ext)s"),
                url,
            ],
            check=True,
            capture_output=True,
        )
        print(f"Downloaded: {mp3_path}")

        return episode_id

    def _next_episode_id(self, cohost):
        pattern = os.path.join(self._root, "output", f"{cohost}*")
        number = len(glob.glob(pattern)) + 1
        return f"{cohost}-ep-{number:03d}"

    def _save_metadata(self, url, episode_id):
        meta = self._metadata_class(url)
        metadata = {}
        if meta.video_id:
            metadata["youtube_video_id"] = meta.video_id
        if meta.title:
            metadata["title"] = meta.title
        if metadata:
            with open(paths.metadata_json(episode_id), "w") as f:
                json.dump(metadata, f, indent=2)
