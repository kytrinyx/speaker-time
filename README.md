# Speaker Diarization and Transcription Pipeline

A complete audio processing pipeline that performs speaker diarization, language detection, and transcription using pyannote.audio and OpenAI Whisper.

## Features

- **Youtube Download**: Downloads a given youtube video
- **Speaker Diarization**: Identifies different speakers and their speaking segments
- **Audio Segmentation**: Cuts original audio into individual speaker segments
- **Language Detection**: Automatically detects the language spoken by each speaker
- **Transcription**: Generates full transcripts with speaker attribution
- **VTT Subtitle Generation**: Creates WebVTT subtitle files from transcriptions
- **Translation**: Translates Korean subtitles to English and English subtitles to Korean

## Pipeline

### `process`
Main entry point. Downloads a YouTube video and runs the complete pipeline.

**Usage:**
```bash
./bin/process <url> <--cohost>
```

**Example:**
```bash
./bin/process https://www.youtube.com/watch?v=... --jeep
```

### `download`
Downloads a YouTube video as MP3 and determines the next episode filename based on existing output directories. Outputs the filename to stdout.

**Usage:**
```bash
./bin/download <url> <--cohost>
```

**Example:**
```bash
./bin/download https://www.youtube.com/watch?v=... --jeep
```

This counts existing `output/jeep*` directories to determine the episode number, downloads the audio as e.g. `audio/jeep-ep-004.mp3`, and prints the episode_id:
```
jeep-ep-004
```

**Output Structure:**
```
output/
└── jeep-ep-001/
    ├── data/
    │   ├── timeline.csv                  # Speaker timeline with timestamps
    │   ├── transcription.csv             # Complete transcription data
    │   ├── words.csv                     # Word-level timestamps from transcription
    │   ├── cue-overrides.json            # Cached Claude corrections for intro/outro
    │   ├── segment-breakpoints.json      # Cached Ollama LLM splitting results
    │   ├── split-segment-cues.json           # Cached cue splits (from split-segments)
    │   ├── translation.ko-en.cache.json  # Cached ko->en translation chunks
    │   └── translation.en-ko.cache.json  # Cached en->ko translation chunks
    ├── audio/                            # Individual audio segments
    │   ├── 000001.mp3
    │   ├── 000002.mp3
    │   └── ...
    ├── language_detection/               # Language detection samples and logs
    │   ├── SPEAKER_00.concatenated.mp3
    │   ├── SPEAKER_00.log.json
    │   ├── SPEAKER_01.concatenated.mp3
    │   └── SPEAKER_01.log.json
    ├── metadata.json                     # Video info, speaker stats, and language mapping
    └── subtitles/
        ├── jeep-ep-001.en-en.vtt         # English subtitles
        ├── jeep-ep-001.ko-ko.vtt         # Korean subtitles
        ├── jeep-ep-001.en-ko.vtt         # English subtitles translated to Korean
        └── jeep-ep-001.ko-en.vtt         # Korean subtitles translated to English
```

### `diarize`
Performs speaker diarization, generates timeline CSV, and adds per-speaker stats to `metadata.json`.

**Usage:**
```bash
./bin/diarize <episode_id>
```

### `cut-audio`
Cuts audio into segments based on timeline CSV.

**Usage:**
```bash
./bin/cut-audio <episode_id>
```

### `detect-language`
Generates language samples and detects speaker languages.

**Usage:**
```bash
./bin/detect-language <episode_id>
```

### `transcribe`
Transcribes audio segments with language hints. Captures word-level timestamps alongside segment-level transcription.

For bilingual content, code-switching causes Whisper to produce garbage or silent mistranslations when the audio language doesn't match the hint. After each transcription, if the confidence score is below -1.5 or is 0.0 (indicating a timeout or empty result), the segment is retranscribed with the opposite language hint. Both results are stored in `transcription.csv`; downstream steps use whichever has higher confidence.

An `initial_prompt` is passed to Whisper for each segment to improve transcription of proper nouns (host names, show name). Prompts are episode-specific and built from `halfhalf/prompts.py` based on the episode_id prefix.

**Usage:**
```bash
./bin/transcribe <episode_id>
```

**Output:**
- `transcription.csv` — one or two rows per speaker segment (one per language attempted), best confidence wins downstream
- `words.csv` — one row per word per language attempt, with absolute timestamps and probability

### `correct-intro-outro`
Uses Claude to detect and correct transcription errors in the intro and outro sequences of the episode. The intro (first few Korean segments) and outro (last segments in each language) tend to have fixed text that repeats across episodes, making them good candidates for LLM correction. Results are cached in `cue-overrides.json`; sequences whose text hasn't changed since the last run are skipped. Corrections are applied by downstream steps when loading the transcript.

**Usage:**
```bash
./bin/correct-intro-outro <episode_id>
```

**Output:**
- `data/cue-overrides.json` — cached corrections keyed by sequence ID

**Requires:** `ANTHROPIC_API_KEY` environment variable.

### `split-segments`
Applies `HybridSplit` to each transcription segment to produce shorter, more readable cues with accurate per-cue timestamps: first splits at sentence-ending punctuation, then uses a local Ollama model to sub-split any cue still over 80 characters. Results are cached in `split-segment-cues.json`; segments whose source text is unchanged since the last run are skipped.

**Usage:**
```bash
./bin/split-segments <episode_id>
```

**Output:**
- `data/split-segment-cues.json` — cached cue splits keyed by segment ID

**Requires:** Ollama running locally; uses `exaone3.5:latest` by default.

### `create-vtt`
Converts transcription CSV to WebVTT subtitle format. Skips segments that are empty, timed out, filler-only, or have low confidence (below -1.5 or 0.0). Reads pre-computed cue splits from `split-segment-cues.json` (produced by `split-segments`) when available; falls back to one cue per segment otherwise.

**Usage:**
```bash
./bin/create-vtt <episode_id>
```

**Example:**
```bash
./bin/create-vtt sample
```

**Output** (written to `subtitles/`):
- `{episode_id}.en-en.vtt` — English-only captions
- `{episode_id}.ko-ko.vtt` — Korean-only captions

### `translate-vtt`
Translates the Korean and English subtitle files using Claude Haiku via the Replicate API. Produces translated counterparts in `subtitles/`. Skips files that already exist.

**Usage:**
```bash
./bin/translate-vtt <episode_id>
```

**Output** (written to `subtitles/`):
- `{episode_id}.ko-en.vtt` — Korean captions translated to English
- `{episode_id}.en-ko.vtt` — English captions translated to Korean

**Requires:** `REPLICATE_API_TOKEN` environment variable.

## Tools

### `transcribe-segment`
Re-transcribes a single audio segment and patches both `transcription.csv` and `words.csv` in place. Useful when a segment has a bad transcription and you want to fix just that one without rerunning the full transcription step.

Skips the segment if existing confidence is already good (≥ -1.5 and non-zero). Otherwise transcribes with the speaker's assigned language hint; if the result is still low confidence, retranscribes with the opposite language. Both results are stored when the alt language is tried.

**Usage:**
```bash
./tools/transcribe-segment <episode_id> <segment_id>
```

**Example:**
```bash
./tools/transcribe-segment sample-ep-001 42
```

**Requires:** Whisper model (same as `transcribe`).

### `split-segment`
Re-runs the cue splitting logic for a single segment and patches `split-segment-cues.json` in place. Useful when `create-vtt` produces a long or poorly split cue and you want to fix just that one segment without rerunning the whole pipeline.

**Usage:**
```bash
./tools/split-segment <episode_id> <segment_id>            # update split-segment-cues.json
./tools/split-segment <episode_id> <segment_id> --dry-run  # print new cues to stdout only
```

**Example:**
```bash
./tools/split-segment sample-ep-001 42            # apply the split
./tools/split-segment sample-ep-001 42 --dry-run  # inspect proposed split
```

**Requires:** Ollama running locally (same as `split-segments`).

### `doctor`
Re-runs the post-transcription pipeline steps (`transcribe`, `correct-intro-outro`, `split-segments`, `create-vtt`, `translate-vtt`) for an episode. Useful after making manual corrections to transcription data.

**Usage:**
```bash
./tools/doctor <episode_id>
```

### `long-cues`
Prints all cues that exceed the per-language character threshold (80 for English, 45 for Korean). Useful for identifying segments that need manual re-splitting.

**Usage:**
```bash
./tools/long-cues <episode_id>
```

### `view-corrections`
Displays the pending LLM corrections for an episode's intro and outro sequences — showing both the raw transcribed text and the corrected version, with a diff of each change. Useful for reviewing what `correct-intro-outro` will apply before regenerating VTT files.

**Usage:**
```bash
./tools/view-corrections <episode_id>
```

### `index`
Prints a comma-separated list of all processed episodes and their Youtube IDs. Takes no arguments.

**Usage:**
```bash
./tools/index
```

## Testing

Tests live in `tests/`. Run a specific test file with:

```bash
python -m pytest tests/test_punctuation_split.py
```

## Scripts

Ad-hoc scripts go in the `./scripts/` in order to not pollute `./bin`.

## Dependencies

### System Dependencies
- **FFmpeg**: Required for audio processing and segmentation
- **Python 3.8+**: Compatible with pyannote and whisper

### Python Packages
- pyannote.audio
- openai-whisper
- ffmpeg-python

### Local Services
- **Ollama**: Required by `split-segments` for sub-splitting long cues. Install from [ollama.com](https://ollama.com) and pull the model: `ollama pull exaone3.5:latest`

## Setup Instructions

### 1. Install System Dependencies
Ensure FFmpeg is installed on your system:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### 2. Install Python Dependencies
```bash
pip install pyannote.audio openai-whisper ffmpeg-python
```

### 3. Hugging Face Setup

**Step 1: Accept Model Licenses**
You must accept the user conditions for the following models:
- Visit [hf.co/pyannote/speaker-diarization](https://huggingface.co/pyannote/speaker-diarization) and accept user conditions
- Visit [hf.co/pyannote/segmentation](https://huggingface.co/pyannote/segmentation) and accept user conditions

**Step 2: Create Access Token**
- Go to [hf.co/settings/tokens](https://huggingface.co/settings/tokens)
- Create a new **read-only** access token
- Copy the token for the next step

**Step 3: Set Environment Variable**
```bash
export HUGGINGFACE_SPEAKER_DIARIZATION=your_token_here
```

### 4. Verify Setup

Test your setup by running:
```bash
./bin/diarize sample
```

## File Formats

### Timeline CSV (`data/timeline.csv`)
```csv
SPEAKER_ID,start_time,end_time
SPEAKER_00,0.008488964346349746,0.534804753820034
SPEAKER_01,22.80984719864177,24.558573853989813
```

### Metadata JSON (`metadata.json`)
Initialized by `download` with `youtube_video_id` and `title`. Then written by `diarize` with per-speaker timeline stats (including `skip: true` for speakers with median segment duration below 0.5s), then enriched by `detect-language` with language and confidence. Speakers with `skip: true` are not processed by `detect-language` and have no language fields. `confidence` is 1.0 when detection confidence was ≥ 0.9, and 0.0 when it fell below that threshold (language will be `"?"`). The raw per-segment confidence values are preserved in `language_detection/*.log.json`.

```json
{
  "youtube_video_id": "0rlG4kVKZ3E",
  "title": "Half & Half Episode 1",
  "SPEAKER_00": {
    "airtime_seconds": 1403.616,
    "airtime_pct": 54.56,
    "segments": 463,
    "long_segments": 0,
    "longest": 22.9,
    "mean": 3.03,
    "median": 2.1,
    "stddev": 3.25,
    "skip": false,
    "language": "ko",
    "confidence": 1.0
  }
}
```
### Transcription CSV (`data/transcription.csv`)
Keyed by `(segment_id, language)`. A segment may have two rows when code-switching triggers an alt-language attempt. Downstream steps iterate via `Transcript.__iter__`, which yields the highest-confidence row per segment.

```csv
speaker_id,segment_id,start_time,end_time,text,language,confidence
SPEAKER_00,1,0.008488964346349746,0.534804753820034,,ko,0.0
SPEAKER_00,2,0.7555178268251275,2.1307300509337863,그쵸 근데,ko,-0.6298892157418388
SPEAKER_02,974,3301.2,3309.8,I'm raising a daughter. When I go home...,en,-0.8621
SPEAKER_02,974,3301.2,3309.8,따로 키우고 있어서 집에 가면...,ko,-0.3500
```

### Words CSV (`data/words.csv`)
Word-level timestamps with absolute times (offset to match the original audio, not the segment file). Keyed by `(segment_id, language)` — when both language attempts are stored for a segment, both sets of word rows appear. Downstream steps filter by the winning language.

```csv
segment_id,language,word_index,word,start_time,end_time,probability
2,ko,0, 그쵸,0.756,1.276,0.8263
2,ko,1, 근데,1.276,1.516,0.5683
```

Segments with timeouts or errors produce no rows in this file.

## Configuration

- **Segment Gap Threshold**: 3 seconds (segments within 3s are considered contiguous)
- **Transcription Timeout**: 30 seconds per audio segment
- **Whisper Model**: Uses "small" model for balance of speed and accuracy (actually, tell a lie; it's because my computer can't handle bigger ones)

## Example Usage

```bash
# Full pipeline: download + process
./bin/process https://www.youtube.com/watch?v=... --jeep

# Download only (outputs filename)
./bin/download https://www.youtube.com/watch?v=... --jeep

# Run individual steps on a local file
./bin/diarize interview
./bin/cut-audio interview
./bin/detect-language interview
./bin/transcribe interview
./bin/correct-intro-outro interview
./bin/split-segments interview
./bin/create-vtt interview
./bin/translate-vtt interview

```

## Notes

- Audio segments are zero-padded (000001.mp3, 000002.mp3, etc.)
- Language detection improves transcription accuracy for multilingual content
- Pipeline scripts handle re-runs by skipping completed steps: `diarize` skips if timeline.csv exists, `cut-audio` and `transcribe` resume where they left off
- Speaker diarization cannot guarantee same speaker id on multiple runs; if script crashes during diarization it will have to restart from scratch
- VTT files exclude empty segments, timeout markers, filler-only segments, and low-confidence segments (confidence below -1.5 or 0.0)
- `split-segments` produces multiple cues per segment (requires Ollama); `create-vtt` uses the cached splits when available, falling back to one cue per segment otherwise
