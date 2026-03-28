import unicodedata


def normalize(s):
    s = unicodedata.normalize("NFC", s)
    return ''.join(c for c in s if not unicodedata.category(c).startswith('P') and not c.isspace()).lower()


def derived_whisper_word_indices(space_indices, raw_text, whisper_words):
    """Map space-word 'after' indices to Whisper word indices.

    Each space-word split index s means "split after space-word s", i.e. the
    next chunk starts at space-word s+1. This function finds the first Whisper
    word index that belongs to that next chunk via normalized text matching.
    """
    raw_words = raw_text.split()
    full_norm = normalize("".join(w.text for w in whisper_words))

    result = []
    search_start = 0
    for s in space_indices:
        if s + 1 >= len(raw_words):
            continue

        # Use two-word context to avoid false substring matches on short words
        # e.g. "and" alone matches inside "cando" (from "can"+"do"), but "doand" does not.
        # search_start advances monotonically so repeated identical contexts (e.g. "wantto"
        # appearing twice) map to distinct Whisper words instead of both hitting the first.
        context = normalize(raw_words[s] + raw_words[s + 1])
        offset = len(normalize(raw_words[s]))
        pos = full_norm.find(context, search_start)
        if pos == -1:
            pos = full_norm.find(normalize(raw_words[s + 1]), search_start)
            if pos == -1:
                continue
        else:
            pos += offset

        search_start = pos

        char_pos = 0
        for w_idx, w in enumerate(whisper_words):
            w_norm = normalize(w.text)
            if char_pos + len(w_norm) > pos:
                result.append(w_idx)
                break
            char_pos += len(w_norm)

    return result
