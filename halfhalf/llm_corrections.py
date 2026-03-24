import json

INTRO_KO_LINES = 5
OUTRO_LINES = 15
OUTRO_KO_LINES = 5
OUTRO_EN_LINES = 5
CLAUDE_MODEL = "claude-haiku-4-5-20251001"


def get_intro_rows(segments):
    rows = []
    for seg in segments:
        if seg.derived_language == "en":
            break
        rows.append(seg)
        if len(rows) >= INTRO_KO_LINES:
            break
    return rows


def get_outro_rows(segments, language):
    tail = segments[-OUTRO_LINES:]
    rows = [s for s in tail if s.derived_language == language]
    n = OUTRO_KO_LINES if language == "ko" else OUTRO_EN_LINES
    return rows[-n:]


def claude_correct(rows, cohost, client):
    payload = [{"segment_id": seg.id, "language": seg.language, "text": seg.text} for seg in rows]
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=(
            f"You are correcting Whisper speech-to-text transcription errors in a podcast called 하프앤하프 (Half and Half). "
            f"The Korean host is 정태웅. The English-speaking host is {cohost}. "
            f"CRITICAL: Fix ONLY clear mis-transcriptions of the podcast name (하프앤하프 / Half and Half) and host names (정태웅, 지프/Jeep, 카트리나/Katrina). "
            f"Do NOT change anything else — not spelling, grammar, punctuation, word choice, or any content outside of these specific names. "
            f"Only correct the podcast name itself (하프앤하프 or Half and Half) when it is clearly mis-transcribed. Do NOT correct surrounding chit-chat or descriptive phrases around the name, even if they seem like transcription errors. "
            f"Only correct the podcast name when it clearly refers to 하프앤하프 itself — do not change references to other podcasts or shows. "
            f"In Korean segments, do not change between Korean transliterations and English spellings of host names (e.g. 카트리나/Katrina, 지프/Jeep are equivalent). "
            f"Each segment includes a language field: use 하프앤하프 for mis-transcriptions in Korean segments and Half and Half for mis-transcriptions in English segments. "
            f"Names and phrases may be split across adjacent segments due to diarization artifacts — "
            f"use surrounding context to recognize and correct partial fragments. "
            f"If a segment's entire content was a fragment that has been absorbed into the correction of an adjacent segment, set that segment's text to an empty string. "
            f"Return a flat JSON object where each key is a segment_id and each value is the corrected text, e.g. {{\"4\": \"corrected text\", \"9\": \"other text\"}}. No explanation, no wrapping keys, no backticks."
        ),
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def correct(sequence, cohost, client):
    cache_key = sequence.text()
    originals = {seg.id: seg.text for seg in sequence.segments}
    result = claude_correct(sequence.segments, cohost, client)
    corrections = {}
    for seg_id_str, corrected in result.items():
        seg_id = int(seg_id_str)
        source = originals.get(seg_id, "")
        if corrected != source:
            corrections[str(seg_id)] = {"source": source, "text": corrected}
    return {"cache_key": cache_key, "corrections": corrections}


