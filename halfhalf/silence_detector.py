import csv
import os
import subprocess

from . import paths


def parse(output):
    """Parse ffmpeg silencedetect output into (start, end) tuples."""
    silences = []
    start = None
    for line in output.splitlines():
        if "silencedetect" not in line:
            continue
        if "silence_start" in line:
            start = float(line.split("silence_start:")[-1].strip())
        elif "silence_end" in line and start is not None:
            end = float(line.split("silence_end:")[-1].split("|")[0].strip())
            silences.append((start, end))
            start = None
    return silences


def detect(episode_id):
    """Run ffmpeg silencedetect on the episode audio and save results to CSV."""
    audio_path = paths.audio_file(episode_id)
    cmd = ["ffmpeg", "-i", audio_path, "-af", "silencedetect=noise=-30dB:d=0.1", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    silences = parse(result.stderr)
    _save(episode_id, silences)
    return silences


def _save(episode_id, silences):
    path = paths.silences_csv(episode_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["start_time", "end_time", "duration"])
        for start, end in silences:
            writer.writerow([start, end, round(end - start, 6)])
