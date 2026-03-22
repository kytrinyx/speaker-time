import json

INTRO_KO_LINES = 5
OUTRO_LINES = 15
CLAUDE_MODEL = "claude-haiku-4-5-20251001"


def get_intro_rows(segments):
    rows = []
    for row in segments:
        if row["language"] == "en":
            break
        rows.append(row)
        if len(rows) >= INTRO_KO_LINES:
            break
    return rows


def get_outro_rows(segments):
    return segments[-OUTRO_LINES:]


def claude_correct(rows, cohost, client):
    payload = [{"segment_id": int(r["segment_id"]), "language": r["language"], "text": r["text"].strip()} for r in rows]
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=(
            f"You are correcting Whisper speech-to-text transcription errors in a podcast called "
            f"하프앤하프 (Half and Half). The Korean host is 정태웅. The other host is {cohost}. "
            f"Fix ONLY mis-transcriptions of the podcast name and host names (정태웅, {cohost}). "
            f"Each segment includes a language field: use 하프앤하프 in Korean segments and Half and Half in English segments. "
            f"Do not change anything else — not spelling, grammar, content, or anything outside of these specific names. "
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


def generate_corrections(basename, cohost, client):
    from .transcript import Transcript
    transcript = Transcript.load(basename)
    segments = [row for row in transcript if row["text"].strip()]

    corrections = {}
    for rows in [get_intro_rows(segments), get_outro_rows(segments)]:
        if not rows:
            continue
        originals = {int(r["segment_id"]): r["text"].strip() for r in rows}
        result = claude_correct(rows, cohost, client)
        for seg_id, corrected in result.items():
            if corrected != originals.get(int(seg_id)):
                corrections[int(seg_id)] = corrected

    return transcript.corrections_path, corrections
