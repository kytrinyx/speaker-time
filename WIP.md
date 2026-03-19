# Work in Progress

## Subtitle Line Length Problem

### Problem
`create-vtt` generates one VTT cue per speaker segment. Segments can be long, resulting in too many words on screen at once.

English example:
> Thank you. And actually, I really wanted to do this even though I feel awkward right now. Yeah. Because I wanted to kind of... Like, how do we say... Testify? Testify? Like, show... Like, show how we do when we switch.

Korean example:
> 아니면 또 다른 한국인 구독자분들이 지워주실 수도 있으니까 나이스 댓글 남겨주시면 되겠습니다 그러면 이번 에피소드는 너무 늦어지기 전에 이 점에서 마무리할까요?

### What We Have
`transcribe` now captures word-level timestamps in `words.csv`:
```
segment_id,word_index,word,start_time,end_time,probability
```
This gives us the timing data needed to split cues mid-segment. `create-vtt` doesn't use this file yet.

### Options Considered

**1. Punctuation-based splitting**
Split at sentence/clause boundaries (`.`, `?`, `!`, `,`). Use word timestamps to set the cue start/end times around each chunk.
- Works well for English (conversational content has frequent punctuation)
- Less reliable for Korean (natural clause breaks often lack punctuation)

**2. Word/character count ceiling**
Split when a running count exceeds a threshold (e.g. ~7 words or ~42 characters).
- Language-agnostic
- Ignores natural phrasing — may split mid-thought

**3. Gap-based splitting**
Split at silences between words.
- Respects natural pauses
- Gaps vary a lot; could produce odd groupings

**4. Hybrid: punctuation-preferred with count ceiling**
Split at punctuation when available, force-split when count exceeds threshold.
- Handles both English and Korean with one code path
- Most promising approach so far

### Korean Note
Korean has clear grammatical markers for natural clause boundaries, but these don't always correspond to punctuation in the transcription. Word-level timestamps for Korean from Whisper may also be chunkier (grouping syllable-blocks rather than individual words).

### Open Questions
- What does `words.csv` actually look like for Korean segments? (Need to run transcription on queued episodes to find out — haven't done a full run with word-level capture yet.)
- What's the right word/character count threshold?
- How to handle segments with no `words.csv` rows (timeouts/errors) — fall back to current behavior (one cue for the full segment text)?

### Status
Discussed options. Waiting on real `words.csv` data from a full transcription run before finalizing approach.
