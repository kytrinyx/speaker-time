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

## Scripts

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

This counts existing `output/jeep*` directories to determine the episode number, downloads the audio as e.g. `jeep-ep-004.mp3`, and prints the filename:
```
jeep-ep-004.mp3
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

### Individual Pipeline Scripts

#### `diarize`
Performs speaker diarization and generates timeline CSV.

**Usage:**
```bash
./bin/diarize <audio_file>
```

#### `cut-audio`
Cuts audio into segments based on timeline CSV.

**Usage:**
```bash
./bin/cut-audio <audio_file>
```

#### `detect-language`
Generates language samples and detects speaker languages.

**Usage:**
```bash
./bin/detect-language <audio_file>
```

#### `transcribe`
Transcribes audio segments with language hints. Captures word-level timestamps alongside segment-level transcription.

**Usage:**
```bash
./bin/transcribe <audio_file>
```

**Output:**
- `transcription.csv` — one row per speaker segment with full text
- `words.csv` — one row per word with absolute timestamps and probability

#### `create-vtt`
Converts transcription CSV to WebVTT subtitle format. When `words.csv` is present, applies `HybridSplit` to produce shorter, more readable cues with accurate per-cue timestamps: first splits at sentence-ending punctuation, then uses a local Ollama model to sub-split any cue still over 80 characters.

**Usage:**
```bash
./bin/create-vtt <audiofile>
```

**Example:**
```bash
./bin/create-vtt sample.mp3
```

**Output:**
- Creates `output/sample/sample.vtt`
- One cue per sentence boundary (or per segment if `words.csv` is absent)

**Requires:** Ollama running locally (for sub-splitting long cues); uses `exaone3.5:latest` by default.

## Analysis Tools

### `compute-speaking-time`
Analyzes speaking time statistics from timeline CSV. Useful for understanding speaker distribution and segment counts.

**Usage:**
```bash
./bin/compute-speaking-time <audiofile>
```

**Example:**
```bash
./bin/compute-speaking-time sample.mp3
```

**Output:**
- Displays speaking time breakdown by speaker with percentages and segment counts

### `scan-long-segments`
Scans all `output/*/transcription.csv` files and reports segments exceeding per-language character thresholds (45 for Korean, 100 for English). Useful for identifying candidates that benefit most from cue splitting.

**Usage:**
```bash
./bin/scan-long-segments
```

**Output:**
- Writes `output/long-segments.csv` with all long segments
- Prints a summary to stdout with the top 10 longest per language

### `test-cue-splitting`
Development tool for testing the `HybridSplit` strategy against a fixture dataset (`output/test-cues/`). Runs `PunctuationSplit` over the fixture segments and prints resulting cues with timestamps.

**Usage:**
```bash
./bin/test-cue-splitting
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
A `sample.mp3` is included in the repo. Its source is https://youtu.be/0rlG4kVKZ3E.

Test your setup by running:
```bash
./bin/diarize sample.mp3
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
./bin/diarize interview.mp3
./bin/cut-audio interview.mp3
./bin/detect-language interview.mp3
./bin/transcribe interview.mp3
./bin/create-vtt interview.mp3

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
