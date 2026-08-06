# Half & Half / 하프앤하프

Subtitle generation pipeline for a bilingual Korean/English podcast.

## Overview

The pipeline downloads a YouTube episode, transcribes it with ElevenLabs Scribe, splits the transcript into subtitle cues using an LLM, translates each cue, and writes four VTT files.

## Setup

**Prerequisites (brew):**

```
brew install yt-dlp mecab-ko
```

**Python dependencies:**

```
uv sync
```

This installs all Python dependencies (including the spacy model) into a local `.venv` using Python 3.13.

**API keys:**

Copy `.env.example` to `.env` and fill in your keys:

```
cp .env.example .env
```

You'll need a [Replicate](https://replicate.com) API token (`REPLICATE_API_TOKEN`) and an [ElevenLabs](https://elevenlabs.io) API token (`ELEVENLABS_API_TOKEN`).

**Run commands:**

Either activate the venv first:

```
source .venv/bin/activate
```

Or prefix commands with `uv run`:

```
uv run bin/transcribe --url=<youtube-url> --cohost=<name>
```

## Usage

**New episode** (download + process):

```
bin/transcribe --url=<youtube-url> --cohost=<name>
```

**Resume existing episode** (skip download):

```
bin/transcribe --episode=<episode_id>
```

**Retry failed translations** (without re-transcribing or re-splitting):

```
bin/retranslate <episode_id>
```

## Pipeline Steps

1. **Download** — fetches audio from YouTube and saves it to `audio/<episode_id>.mp3`
2. **Transcribe** — sends audio to ElevenLabs Scribe v2, saves word-level JSON to `output/<episode_id>/data/transcription.json`
3. **Split into cues** — groups words into fragments, then uses an LLM to split fragments into subtitle cues; results cached in `output/<episode_id>/data/llm-splits.json`; backchannels filtered out
4. **Translate** — translates each cue in both directions (ko→en, en→ko); results cached in `output/<episode_id>/data/translations.json`
5. **Generate subtitles** — writes four VTT files to `output/<episode_id>/subtitles/` and copies them to `~/Desktop/` (or `$HALF_AND_HALF_SUBTITLES_DIR`)

## Output Files

| File | Contents |
|------|----------|
| `<episode>.ko.vtt` | Korean cues (source) |
| `<episode>.en.vtt` | English cues (source) |
| `<episode>.ko-en.vtt` | Korean cues translated to English |
| `<episode>.en-ko.vtt` | English cues translated to Korean |

## Hosts

- 정태웅 (태웅쌤) is always the Korean-language co-host
- English co-host varies by episode prefix: `jeep-*` → Jeep, `katrina-*` → Katrina, `ian-*` → Ian
- Host mapping is configured in `halfhalf/prompts.py`
