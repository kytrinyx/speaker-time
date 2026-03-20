import whisper


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
