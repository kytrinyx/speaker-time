import unicodedata

# Pure phonetic fillers that carry no content when they appear alone.
# Deliberately conservative — "네" (yes), "맞아" (right), "좋아" (good) are excluded
# because they're meaningful as standalone responses.
BACKCHANNEL_TOKENS = {
    # Korean phonetic fillers
    "음", "어", "아", "응", "에", "으흠", "어허", "음음",
    # English phonetic fillers
    "uh", "um", "mm", "hmm", "mm-hmm", "mmm", "hm", "ah", "oh", "er", "huh", "mhm",
}


def _tokens(text):
    """Split text into lowercase words with leading/trailing punctuation stripped."""
    result = []
    for word in text.split():
        stripped = word.strip(
            "".join(c for c in word if unicodedata.category(c).startswith("P"))
        ).lower()
        if stripped:
            result.append(stripped)
    return result


def is_backchannel(cue):
    """Return True if the cue consists entirely of phonetic filler tokens."""
    tokens = _tokens(cue.text)
    return bool(tokens) and all(t in BACKCHANNEL_TOKENS for t in tokens)
