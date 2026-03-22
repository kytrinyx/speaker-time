import signal
import whisper
import torch


class Transcriber:
    def __init__(self, prompts):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.use_fp16 = device == "cuda"
        self.model = whisper.load_model("small", device=device)
        self.prompts = prompts

    def transcribe_segment(self, audio_file, segment_id, speaker_id, language, start_time, end_time):
        """Transcribe a segment, with alt-language fallback if low confidence.

        Returns (rows, words) where rows is a list of transcription row dicts
        and words is a list of word row dicts.

        Raises on unexpected errors — callers decide how to handle them.
        """
        primary_row, primary_words = self._transcribe_one(
            audio_file, segment_id, speaker_id, language, start_time, end_time
        )
        rows = [primary_row]
        words = list(primary_words)

        if float(primary_row['confidence']) < -1.5:
            alt_language = 'ko' if language == 'en' else 'en'
            print(f"  Low confidence ({float(primary_row['confidence']):.4f}), trying alt language ({alt_language})...")
            alt_row, alt_words = self._transcribe_one(
                audio_file, segment_id, speaker_id, alt_language, start_time, end_time
            )
            rows.append(alt_row)
            words += alt_words

        return rows, words

    def _transcribe_one(self, audio_file, segment_id, speaker_id, language, start_time, end_time):
        def timeout_handler(signum, frame):
            raise TimeoutError("Transcription timeout")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)

        try:
            result = self.model.transcribe(
                audio_file,
                language=language,
                fp16=self.use_fp16,
                word_timestamps=True,
                initial_prompt=self.prompts.get(language, ''),
            )
            signal.alarm(0)

            confidence = (
                float(result.get('segments', [{}])[0].get('avg_logprob', 0.0))
                if result.get('segments') else 0.0
            )
            row = {
                'speaker_id': speaker_id,
                'segment_id': segment_id,
                'start_time': start_time,
                'end_time': end_time,
                'text': result['text'].strip(),
                'language': language,
                'confidence': confidence,
            }

            offset = float(start_time)
            words = []
            word_index = 0
            for whisper_segment in result.get('segments', []):
                for word_info in whisper_segment.get('words', []):
                    words.append({
                        'segment_id': segment_id,
                        'word_index': word_index,
                        'word': word_info['word'],
                        'start_time': round(offset + word_info['start'], 3),
                        'end_time': round(offset + word_info['end'], 3),
                        'probability': round(word_info.get('probability', 0.0), 4),
                        'language': language,
                    })
                    word_index += 1

            print(f"  [{language}] {result['text'].strip()[:80]} (confidence: {confidence:.4f})")
            return row, words

        except TimeoutError:
            signal.alarm(0)
            print(f"  [{language}] Timeout (30s limit exceeded)")
            row = {
                'speaker_id': speaker_id,
                'segment_id': segment_id,
                'start_time': start_time,
                'end_time': end_time,
                'text': "[TIMEOUT]",
                'language': language,
                'confidence': 0.0,
            }
            return row, []
