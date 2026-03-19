# TODO

## Ollama not splitting long English cues

English cues over 80 chars trigger the Ollama sub-split, but Ollama sometimes returns the cue
unsplit (falling back to the original). Needs prompt tuning or a fallback strategy (e.g. word-count
split) so these cues don't silently pass through at full length.

## Filtering filler/non-verbal segments

Filter at the **cue level** in `create-vtt` (after splitting), not in `transcribe`, so raw data is preserved.

Rules per pattern:

- **Bracket markers** (`[laughter]`, `[noise]`, etc.) → drop the cue
- **Korean laughter consonants** (ㅋ-only, ㅎ-only strings) → drop
- **Korean laughter syllables** (하하하, 호호호, 헤헤헤, etc.) → drop
- **Korean filler vowels** (repeated 아 or 어):
  - Collapse repeated runs to a single instance
  - If the whole cue is just 아 or 어 after collapsing → drop
  - If mixed with real content → keep with collapsed form
- **Korean 음 alone** → keep
- **English laughter** (haha, hehe, hoho, etc.) → drop

## Workflow for identifying long cues and selectively fixing them

Starting point, see: bin/identify-long-cues, bin/split-cue

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
