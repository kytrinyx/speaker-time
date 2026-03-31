import json
import os

from elevenlabs import ElevenLabs


BASE_KEYTERMS = [
    "Half & Half", "하프앤하프",
    "정태웅", "태웅쌤", "Taewoong Ssaem",
    "Jeep", "지프",
    "Katrina", "카트리나",
]


class Stenographer:
    """Transcribe episode audio using ElevenLabs Scribe v2."""

    def __init__(self, api_key=None):
        self._client = ElevenLabs(api_key=api_key or os.environ.get("ELEVENLABS_API_TOKEN"))

    def transcribe(self, audio_path, output_path):
        """Transcribe the audio file and save results to output_path.

        Skips transcription if output_path already exists.
        Returns the transcription data as a dict.
        """
        if os.path.exists(output_path):
            print(f"Transcription already exists: {output_path}")
            with open(output_path) as f:
                return json.load(f)

        print(f"Transcribing {audio_path}...")
        with open(audio_path, "rb") as f:
            result = self._client.speech_to_text.convert(
                file=f,
                model_id="scribe_v2",
                keyterms=BASE_KEYTERMS,
            )

        data = result.model_dump()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Transcription saved: {output_path}")
        return data
