import json
import os
import whisper


CONFIDENCE_THRESHOLD = 0.9


def detect_language(audio_file, model, debug=False):
    """Detect the language of an audio file using multi-chunk averaging.

    Splits the audio into 30-second chunks (Whisper's context window), runs
    language detection on each, and averages the probability distributions
    to avoid the bias of using only the first 30 seconds.

    Returns a dict: {"language": str, "confidence": float}
    """
    import statistics

    audio = whisper.load_audio(audio_file)
    chunk_size = whisper.audio.N_SAMPLES

    all_probs = []
    for i in range(0, len(audio), chunk_size):
        chunk = audio[i:i + chunk_size]
        if len(chunk) < chunk_size // 2:
            break
        chunk = whisper.pad_or_trim(chunk)
        mel = whisper.log_mel_spectrogram(chunk, n_mels=model.dims.n_mels).to(model.device)
        _, chunk_probs = model.detect_language(mel)
        all_probs.append(chunk_probs)

    avg_probs = {lang: sum(p[lang] for p in all_probs) / len(all_probs) for lang in all_probs[0]}
    detected_language = max(avg_probs, key=avg_probs.get)
    confidence = avg_probs[detected_language]

    if debug:
        chunk_winners = [max(p, key=p.get) for p in all_probs]
        chunk_confidences = [p[detected_language] for p in all_probs]
        unique_winners = set(chunk_winners)
        print(f"  chunks ({len(all_probs)}):")
        for idx, (winner, probs) in enumerate(zip(chunk_winners, all_probs)):
            print(f"    chunk {idx+1}: {winner} ({probs[winner]:.3f})")
        if len(unique_winners) > 1:
            print(f"  WARNING: chunks disagree on language: {', '.join(sorted(unique_winners))}")
        if len(chunk_confidences) > 1:
            stddev = statistics.stdev(chunk_confidences)
            print(f"  stddev of '{detected_language}' confidence across chunks: {stddev:.3f}")

    return {"language": detected_language, "confidence": float(confidence)}


def detect_file_language(audio_file, model):
    """Detect the language of an audio file using the first 30 seconds.

    Loads the audio, pads or trims to Whisper's 30-second context window,
    and runs language detection once. The caller is responsible for ensuring
    the audio file is short enough that using only the first 30 seconds is
    acceptable.

    Returns a dict: {"language": str, "confidence": float}
    """
    audio = whisper.load_audio(audio_file)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio, n_mels=model.dims.n_mels).to(model.device)
    _, probs = model.detect_language(mel)
    language = max(probs, key=probs.get)
    return {"language": language, "confidence": float(probs[language])}


def _append_log(path, entries):
    existing = []
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f)
    with open(path, "w") as f:
        json.dump(existing + entries, f, indent=2)


class SerialLanguageDetector:
    def __init__(self, segments):
        self._segments = sorted(segments, key=lambda s: s.duration, reverse=True)
        self.log = []

    def detect(self, model):
        for segment in self._segments[:5]:
            result = detect_file_language(segment.audio_path, model)
            self.log.append({"path": segment.audio_path, **result})
            if result["confidence"] >= self.CONFIDENCE_THRESHOLD:
                return result["language"]

    def write_log(self, path):
        _append_log(path, self.log)


class ConcatenatingLanguageDetector:
    TARGET_DURATION = 30.0

    def __init__(self, segments):
        self._segments = sorted(segments, key=lambda s: s.duration, reverse=True)
        self.log = []

    def detect(self, model, output_path):
        import ffmpeg

        selected = []
        total = 0.0
        for segment in self._segments:
            if total >= self.TARGET_DURATION:
                break
            selected.append(segment)
            total += segment.duration

        if not selected:
            return None

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if len(selected) == 1:
            import shutil
            shutil.copy(selected[0].audio_path, output_path)
        else:
            inputs = [ffmpeg.input(s.audio_path) for s in selected]
            joined = ffmpeg.concat(*inputs, v=0, a=1)
            ffmpeg.output(joined, output_path).run(overwrite_output=True, quiet=True)

        result = detect_file_language(output_path, model)
        self.log.append({"path": output_path, **result})

        if result["confidence"] >= self.CONFIDENCE_THRESHOLD:
            return result["language"]
        return None

    def write_log(self, path):
        _append_log(path, self.log)
