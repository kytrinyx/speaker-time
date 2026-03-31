import subprocess
from urllib.parse import urlparse, parse_qs


class YoutubeMetadata:
    def __init__(self, url):
        self._url = url

    @property
    def video_id(self):
        parsed = urlparse(self._url)
        if parsed.hostname in ("youtu.be",):
            return parsed.path.lstrip("/")
        return parse_qs(parsed.query).get("v", [None])[0]

    @property
    def title(self):
        result = subprocess.run(
            ["yt-dlp", "--print", "title", "--quiet", self._url],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
