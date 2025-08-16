# Speaker Diarization and Transcription Pipeline

A complete audio processing pipeline that performs speaker diarization, language detection, and transcription using pyannote.audio and OpenAI Whisper.

## Features

- **Speaker Diarization**: Identifies different speakers and their speaking segments
- **Overlap Resolution**: Handles overlapping speech by prioritizing the original speaker
- **Language Detection**: Automatically detects the language spoken by each speaker
- **Audio Segmentation**: Cuts original audio into individual speaker segments
- **Transcription**: Generates full transcripts with speaker attribution
- **VTT Subtitle Generation**: Creates WebVTT subtitle files from transcriptions

## Scripts

### `speaker-time`
Main processing script that handles the complete pipeline.

**Usage:**
```bash
./speaker-time <audio_file>
```

**Example:**
```bash
./speaker-time sample.mp3
```

**Output Structure:**
```
output/
└── sample/
    ├── sample_timeline.csv          # Speaker timeline with timestamps
    ├── audio/                       # Individual audio segments
    │   ├── 000001.mp3
    │   ├── 000002.mp3
    │   └── ...
    ├── language_detection/          # Language detection samples
    │   ├── SPEAKER_00_language_sample.mp3
    │   └── SPEAKER_01_language_sample.mp3
    ├── metadata.json               # Speaker language mapping
    └── transcription.csv           # Complete transcription data
```

### `create-vtt`
Converts transcription CSV to WebVTT subtitle format.

**Usage:**
```bash
./create-vtt <basename>
```

**Example:**
```bash
./create-vtt sample
```

**Output:**
- Creates `output/sample/sample.vtt` with properly formatted subtitles

## Dependencies

### System Dependencies
- **FFmpeg**: Required for audio processing and segmentation
- **Python 3.8+**: Compatible with pyannote and whisper

### Python Packages
- pyannote.audio
- openai-whisper
- ffmpeg-python

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
./speaker-time sample.mp3
```

## File Formats

### Timeline CSV (`*_timeline.csv`)
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

## Configuration

- **Minimum Speaker Duration**: 20 seconds (speakers with less total time are skipped)
- **Language Sample Duration**: 20-60 seconds per speaker
- **Segment Gap Threshold**: 3 seconds (segments within 3s are considered contiguous)
- **Transcription Timeout**: 30 seconds per audio segment
- **Whisper Model**: Uses "small" model for balance of speed and accuracy

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
# Process audio file
./speaker-time interview.mp3

# Generate subtitles
./create-vtt interview

# View results
ls output/interview/
# interview_timeline.csv  audio/  language_detection/  metadata.json  transcription.csv  interview.vtt
```

## Notes

- Empty segments and timeouts are handled gracefully
- Audio segments are zero-padded (000001.mp3, 000002.mp3, etc.)
- Language detection improves transcription accuracy for multilingual content
- VTT files exclude empty segments and timeout markers for clean subtitle output
