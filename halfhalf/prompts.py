COHOSTS = {
    'jeep': 'Jeep',
    'katrina': 'Katrina',
    'ian': 'Ian',
    'sample': 'Jeep',
}


def cohost_for(episode_id):
    prefix = episode_id.split('-ep-')[0] if '-ep-' in episode_id else 'jeep'
    return COHOSTS.get(prefix, 'Jeep')


def build_prompts(episode_id):
    prefix = episode_id.split('-ep-')[0] if '-ep-' in episode_id else 'jeep'
    cohost = COHOSTS.get(prefix, 'Jeep')
    return {
        'en': f"This is Half & Half podcast with hosts {cohost} and 태웅쌤 (정태웅).",
        'ko': f"이것은 하프앤하프 팟캐스트입니다. 진행자는 {cohost}과 정태웅입니다.",
    }
