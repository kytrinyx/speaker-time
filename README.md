# Speaker Diarization and Transcription Pipeline

A complete audio processing pipeline that performs speaker diarization, language detection, and transcription using pyannote.audio and OpenAI Whisper.

## Features

- **Youtube Download**: Downloads a given youtube video
- **Speaker Diarization**: Identifies different speakers and their speaking segments
- **Overlap Resolution**: Handles overlapping speech by prioritizing the original speaker
- **Language Detection**: Automatically detects the language spoken by each speaker
- **Audio Segmentation**: Cuts original audio into individual speaker segments
- **Transcription**: Generates full transcripts with speaker attribution
- **VTT Subtitle Generation**: Creates WebVTT subtitle files from transcriptions

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

This counts existing `output/jeep*` directories to determine the episode number, downloads the audio as e.g. `audio/jeep-ep-004.mp3`, and prints the basename:
```
jeep-ep-004
```

**Output Structure:**
```
output/
└── sample/
    ├── timeline.csv                 # Speaker timeline with timestamps
    ├── audio/                       # Individual audio segments
    │   ├── 000001.mp3
    │   ├── 000002.mp3
    │   └── ...
    ├── language_detection/          # Language detection samples
    │   ├── SPEAKER_00_language_sample.mp3
    │   └── SPEAKER_01_language_sample.mp3
    ├── metadata.json               # Speaker language mapping
    ├── transcription.csv           # Complete transcription data
    ├── words.csv                   # Word-level timestamps from transcription
    └── sample.vtt                  # WebVTT subtitle file
```

### `diarize`
Performs speaker diarization and generates timeline CSV.

**Usage:**
```bash
./bin/diarize <basename>
```

### `cut-audio`
Cuts audio into segments based on timeline CSV.

**Usage:**
```bash
./bin/cut-audio <basename>
```

### `detect-language`
Generates language samples and detects speaker languages.

**Usage:**
```bash
./bin/detect-language <basename>
```

### `transcribe`
Transcribes audio segments with language hints. Captures word-level timestamps alongside segment-level transcription.

**Usage:**
```bash
./bin/transcribe <basename>
```

**Output:**
- `transcription.csv` — one row per speaker segment with full text
- `words.csv` — one row per word with absolute timestamps and probability

### `create-vtt`
Converts transcription CSV to WebVTT subtitle format. When `words.csv` is present, applies `HybridSplit` to produce shorter, more readable cues with accurate per-cue timestamps: first splits at sentence-ending punctuation, then uses a local Ollama model to sub-split any cue still over 80 characters.

**Usage:**
```bash
./bin/create-vtt <basename>
```

**Example:**
```bash
./bin/create-vtt sample
```

**Output:**
- Creates `output/sample/sample.vtt`
- One cue per sentence boundary (or per segment if `words.csv` is absent)

**Requires:** Ollama running locally (for sub-splitting long cues); uses `exaone3.5:latest` by default.


## Tools

### `transcribe-cue`
Re-transcribes a single audio segment and patches both `transcription.csv` and `words.csv` in place. Useful when a segment has a bad transcription and you want to fix just that one without rerunning the full transcription step.

**Usage:**
```bash
./tools/transcribe-cue <basename> <segment_id>
```

**Example:**
```bash
./tools/transcribe-cue sample-ep-001 42
```

**Requires:** Whisper model (same as `transcribe`).

### `split-cue`
Re-runs the cue splitting logic for a single segment and patches the VTT file in place. Useful when `create-vtt` produces a long or poorly split cue and you want to fix just that one segment without rerunning the whole pipeline.

**Usage:**
```bash
./tools/split-cue <basename> <segment_id>            # replace cues in the .vtt file
./tools/split-cue <basename> <segment_id> --dry-run  # print new cues to stdout only
```

**Example:**
```bash
./tools/split-cue sample-ep-001 42            # apply the split
./tools/split-cue sample-ep-001 42 --dry-run  # inspect proposed split
```

**Requires:** Ollama running locally (same as `create-vtt`).

### `detect-language-file`
Runs language detection on any audio file and prints the detected language and confidence score. Useful for checking individual language samples without running the full pipeline.

**Usage:**
```bash
./tools/detect-language-file <audio-file> [--debug]
```

**Example:**
```bash
./tools/detect-language-file output/jeep-ep-023/language_detection/SPEAKER_02_language_sample.mp3 --debug
```

**Output:**
- `language` and `confidence` for the detected language
- With `--debug`: per-chunk language and confidence, a warning if chunks disagree on language, and stddev of the winning language's confidence across chunks

## Scripts

### `compute-speaking-time`
Analyzes speaking time statistics from timeline CSV. Useful for understanding speaker distribution and segment counts.

**Usage:**
```bash
./scripts/compute-speaking-time <basename>
```

**Example:**
```bash
./scripts/compute-speaking-time sample
```

**Output:**
- Displays speaking time breakdown by speaker with percentages and segment counts

### `scan-long-segments`
Scans all `output/*/transcription.csv` files and reports segments exceeding per-language character thresholds (45 for Korean, 100 for English). Useful for identifying candidates that benefit most from cue splitting.

**Usage:**
```bash
./scripts/scan-long-segments
```

**Output:**
- Writes `output/long-segments.csv` with all long segments
- Prints a summary to stdout with the top 10 longest per language

### `identify-long-cues`
Scans a VTT file for cues that exceed per-language character limits (45 for Korean, 80 for English) and appends `transcribe-cue` and `split-cue` commands to `todo-list.txt` for each offending segment.

**Usage:**
```bash
./scripts/identify-long-cues <basename>
```

**Example:**
```bash
./scripts/identify-long-cues sample-ep-001
```

**Output:**
- Appends `./tools/transcribe-cue` and `./tools/split-cue` lines to `todo-list.txt`
- Prints a summary of violating cues and affected segments

### `find-foreign-chars`
Scans a `transcription.csv` for segments containing characters that are neither ASCII nor Korean, and appends `transcribe-cue` commands to `todo-list.txt` for each match. Useful for catching OCR-style errors or segments transcribed in the wrong language.

**Usage:**
```bash
./scripts/find-foreign-chars <basename>
```

**Example:**
```bash
./scripts/find-foreign-chars sample-ep-001
```

**Output:**
- Appends `./tools/transcribe-cue` lines to `todo-list.txt`
- Prints a count of affected segments

### `speaker-airtime`
Shows airtime for a single speaker within an episode. Useful for checking whether a suspect speaker is a real speaker or a diarization artifact.

**Usage:**
```bash
./scripts/speaker-airtime <episode> <speaker>
```

**Example:**
```bash
./scripts/speaker-airtime jeep-ep-012 SPEAKER_03
```

**Output:**
- Total airtime (HH:MM:SS.mmm), percentage of episode, and segment count

### `speaker-foreign-chars`
Shows transcription segments with foreign characters for a specific speaker. Prints to stdout rather than writing to `todo-list.txt` — useful for quick diagnostic checks.

**Usage:**
```bash
./scripts/speaker-foreign-chars <episode> <speaker>
```

**Example:**
```bash
./scripts/speaker-foreign-chars jeep-ep-023 SPEAKER_02
```

**Output:**
- Each garbled segment's `segment_id` and text, followed by a total count

### `run-todo`
Executes each command in a todo list file line by line. Pairs with `identify-long-cues` and `find-foreign-chars`, which populate the list, and `transcribe-cue`/`split-cue`, which do the actual repair work.

**Usage:**
```bash
./scripts/run-todo [todo-file]
```

Defaults to `todo-list.txt` if no file is specified.

**Example:**
```bash
./scripts/run-todo
./scripts/run-todo my-custom-list.txt
```

### `test-cue-splitting`
Development tool for testing the `HybridSplit` strategy against a fixture dataset (`output/test-cues/`). Runs `PunctuationSplit` over the fixture segments and prints resulting cues with timestamps.

**Usage:**
```bash
./scripts/test-cue-splitting
```

## Dependencies

### System Dependencies
- **FFmpeg**: Required for audio processing and segmentation
- **Python 3.8+**: Compatible with pyannote and whisper

### Python Packages
- pyannote.audio
- openai-whisper
- ffmpeg-python

### Local Services
- **Ollama**: Required by `create-vtt` for sub-splitting long cues. Install from [ollama.com](https://ollama.com) and pull the model: `ollama pull exaone3.5:latest`

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

### Timeline CSV (`timeline.csv`)
```csv
SPEAKER_ID,start_time,end_time
SPEAKER_00,0.008488964346349746,0.534804753820034
SPEAKER_01,22.80984719864177,24.558573853989813
```

### Metadata JSON (`metadata.json`)
```json
{
  "SPEAKER_00": {
    "language": "ko",
    "confidence": 0.975
  },
  "SPEAKER_01": {
    "language": "en",
    "confidence": 0.999
  }
}
```

### Transcription CSV (`transcription.csv`)
```csv
speaker_id,segment_id,start_time,end_time,text,language,confidence
SPEAKER_00,1,0.008488964346349746,0.534804753820034,,ko,0.0
SPEAKER_00,2,0.7555178268251275,2.1307300509337863,그쵸 근데,ko,-0.6298892157418388
```

### Words CSV (`words.csv`)
Word-level timestamps with absolute times (offset to match the original audio, not the segment file).

```csv
segment_id,word_index,word,start_time,end_time,probability
2,0, 그쵸,0.756,1.276,0.8263
2,1, 근데,1.276,1.516,0.5683
```

Segments with timeouts or errors produce no rows in this file.

## Configuration

- **Minimum Speaker Duration**: 20 seconds (speakers with less total time are skipped)
- **Language Sample Duration**: 20-60 seconds per speaker
- **Segment Gap Threshold**: 3 seconds (segments within 3s are considered contiguous)
- **Transcription Timeout**: 30 seconds per audio segment
- **Whisper Model**: Uses "small" model for balance of speed and accuracy (actually, tell a lie; it's because my computer can't handle bigger ones)

## Workflow

1. **Diarization**: Identifies speakers and their speaking times
2. **Overlap Resolution**: Assigns overlapping segments to original speakers
3. **Timeline Generation**: Creates CSV with precise timestamps
4. **Audio Cutting**: Splits original audio into numbered segments
5. **Language Detection**: Analyzes 20-60s samples to detect each speaker's language
6. **Transcription**: Transcribes each segment using language-specific hints
7. **VTT Generation**: Converts transcription to subtitle format

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
./bin/create-vtt interview

# View results
ls output/interview/
# timeline.csv  audio/  language_detection/  metadata.json  transcription.csv  words.csv  interview.vtt

```

## Notes

- Empty segments and timeouts are handled gracefully
- Audio segments are zero-padded (000001.mp3, 000002.mp3, etc.)
- Language detection improves transcription accuracy for multilingual content
- VTT files exclude empty segments and timeout markers for clean subtitle output
- `create-vtt` produces multiple cues per segment when `words.csv` is present; falls back to one cue per segment otherwise
- All pipeline scripts efficiently handle re-runs by skipping completed steps: `diarize` skips if timeline.csv exists, `cut-audio` and `transcribe` resume where they left off
- Speaker diarization cannot guarantee same speaker id on multiple runs; if script crashes during diarization it will have to restart from scratch
- Use individual scripts for debugging or partial processing of the pipeline
