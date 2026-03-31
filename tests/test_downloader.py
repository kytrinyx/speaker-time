import json
import os
import pytest
from halfhalf.downloader import Downloader
from halfhalf.youtube_metadata import YoutubeMetadata


class StubMetadata:
    def __init__(self, url, video_id="test-id", title="Test Title"):
        self._video_id = video_id
        self._title = title

    @property
    def video_id(self):
        return self._video_id

    @property
    def title(self):
        return self._title


def stub_metadata_class(video_id="test-id", title="Test Title"):
    """Return a metadata class (not instance) that yields fixed values."""
    class _Stub(StubMetadata):
        def __init__(self, url):
            super().__init__(url, video_id=video_id, title=title)
    return _Stub


@pytest.fixture
def project_root(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "audio").mkdir()
    return str(tmp_path)


# --- YoutubeMetadata.video_id ---

def test_video_id_from_standard_url():
    assert YoutubeMetadata("https://www.youtube.com/watch?v=abc123").video_id == "abc123"


def test_video_id_from_short_url():
    assert YoutubeMetadata("https://youtu.be/xyz789").video_id == "xyz789"


def test_video_id_none_when_missing():
    assert YoutubeMetadata("https://www.youtube.com/watch").video_id is None


# --- _next_episode_id ---

def test_first_episode_is_001(project_root):
    d = Downloader(project_root=project_root)
    assert d._next_episode_id("jeep") == "jeep-ep-001"


def test_second_episode_increments(project_root):
    os.makedirs(os.path.join(project_root, "output", "jeep-ep-001"))
    d = Downloader(project_root=project_root)
    assert d._next_episode_id("jeep") == "jeep-ep-002"


def test_episode_numbering_is_per_cohost(project_root):
    os.makedirs(os.path.join(project_root, "output", "jeep-ep-001"))
    os.makedirs(os.path.join(project_root, "output", "jeep-ep-002"))
    d = Downloader(project_root=project_root)
    assert d._next_episode_id("katrina") == "katrina-ep-001"


def test_episode_number_is_zero_padded(project_root):
    for i in range(1, 10):
        os.makedirs(os.path.join(project_root, "output", f"jeep-ep-{i:03d}"))
    d = Downloader(project_root=project_root)
    assert d._next_episode_id("jeep") == "jeep-ep-010"


# --- _save_metadata ---

def test_save_metadata_writes_video_id_and_title(project_root, monkeypatch):
    monkeypatch.chdir(project_root)
    os.makedirs(os.path.join(project_root, "output", "jeep-ep-001"))
    d = Downloader(project_root=project_root, metadata_class=stub_metadata_class("abc123", "My Episode"))
    d._save_metadata("https://www.youtube.com/watch?v=abc123", "jeep-ep-001")

    from halfhalf import paths
    with open(paths.metadata_json("jeep-ep-001")) as f:
        data = json.load(f)
    assert data["youtube_video_id"] == "abc123"
    assert data["title"] == "My Episode"


def test_save_metadata_omits_missing_video_id(project_root, monkeypatch):
    monkeypatch.chdir(project_root)
    os.makedirs(os.path.join(project_root, "output", "jeep-ep-001"))
    d = Downloader(project_root=project_root, metadata_class=stub_metadata_class(video_id=None, title="My Episode"))
    d._save_metadata("https://www.youtube.com/watch", "jeep-ep-001")

    from halfhalf import paths
    with open(paths.metadata_json("jeep-ep-001")) as f:
        data = json.load(f)
    assert "youtube_video_id" not in data
    assert data["title"] == "My Episode"


# --- download: FileExistsError when mp3 already present ---

def test_download_raises_if_mp3_already_exists(project_root, monkeypatch):
    d = Downloader(project_root=project_root, metadata_class=stub_metadata_class())
    episode_id = d._next_episode_id("jeep")
    mp3 = os.path.join(project_root, "audio", f"{episode_id}.mp3")
    open(mp3, "w").close()

    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: None)

    with pytest.raises(FileExistsError):
        d.download("https://www.youtube.com/watch?v=abc", "jeep")
