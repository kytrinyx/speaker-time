COHOSTS = {
    'jeep': 'Jeep',
    'katrina': 'Katrina',
    'ian': 'Ian',
    'sample': 'Jeep',
}


def cohost_for(episode_id):
    prefix = episode_id.split('-ep-')[0] if '-ep-' in episode_id else 'jeep'
    return COHOSTS.get(prefix, 'Jeep')


def translate_ko_en(cohost, n, payload):
    return (
        f"You are translating Korean subtitles to English for the Half & Half (하프앤하프) podcast. "
        f"The hosts are {cohost} and 정태웅 (also called 태웅쌤). "
        f"If a line consists entirely of phonetic back-channeling with no other content (e.g. '음', '네', '어'), return an empty string for that line. All other lines — including sentence fragments — must be translated. "
        f"Return a JSON array of objects with 'id' and 'text' fields. No explanation, no backticks.\n\n"
        f"Translate these {n} Korean subtitle lines to English. "
        f"CRITICAL: Do NOT merge or combine lines. Each input line maps to exactly one output object — even fragments, even one-word lines. "
        f"Return exactly {n} objects. If your count is less than {n}, you merged lines — fix it.\n\n"
        + payload
    )


def translate_en_ko(cohost, n, payload):
    return (
        f"You are translating English subtitles to Korean for the Half & Half (하프앤하프) podcast. "
        f"The hosts are {cohost} and 정태웅 (also called 태웅쌤). "
        f"If a line consists entirely of phonetic back-channeling with no other content (e.g. 'uh', 'um', 'hmm'), return an empty string for that line. All other lines — including sentence fragments — must be translated. "
        f"Return a JSON array of objects with 'id' and 'text' fields. No explanation, no backticks.\n\n"
        f"Translate these {n} English subtitle lines to Korean. "
        f"CRITICAL: Do NOT merge or combine lines. Each input line maps to exactly one output object — even fragments, even one-word lines. "
        f"Return exactly {n} objects. If your count is less than {n}, you merged lines — fix it.\n\n"
        + payload
    )
