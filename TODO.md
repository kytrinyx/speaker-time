# TODO

## Filtering filler/non-verbal segments

Should we filter out filler/non-verbal segments from transcripts entirely?
- Korean laughter: repeated ㅋ characters (ㅋㅋㅋㅋ...)
- Korean filler: repeated 아 characters (아아아아...) and similar
- English laughter: "haha", "hehe", repeated laughter tokens, "[laughter]" markers, etc.
- These add noise to subtitles without meaningful content
- Where to filter: in `transcribe` (skip writing the row) or `create-vtt` (skip rendering)?

## Start Ollama

Let `./process` start the Ollama instance if it's not running.

## `doctor` script

A diagnostic/repair script that scans episode output for known transcription problems and optionally
fixes them.

Problem types to detect (and potentially fix):
- **Garbled text** — segments with low confidence scores or malformed characters
- **Nonsense transcription** — repeated syllables, filler loops (ㅋㅋㅋ, hahaha), or incoherent
output that slipped through
- **Timeouts** — segments marked `[TIMEOUT]` that could be retried

Could run in two modes: `--check` (report only) and `--fix` (selectively re-process flagged
segments).
