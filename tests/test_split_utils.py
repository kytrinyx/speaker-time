from halfhalf.word import Word
from halfhalf.split_utils import derived_whisper_word_indices


def test_repeated_context_korean():
    # "공부하고쉬고" appears twice in full_norm; splits at space-words 0 and 2 must map
    # to distinct Whisper words (1 and 3), not both to word 1 (the first match).
    whisper_words = [
        Word('공부하고', 0.0, 0.5),
        Word(' 쉬고', 0.5, 1.0),
        Word(' 공부하고', 1.0, 1.5),
        Word(' 쉬고', 1.5, 2.0),
        Word(' 됐어요', 2.0, 2.5),
    ]
    result = derived_whisper_word_indices([0, 2], '공부하고 쉬고 공부하고 쉬고 됐어요', whisper_words)
    assert result == [1, 3]


def test_repeated_context_english():
    # "ranand" appears twice in full_norm; splits at space-words 1 and 4 must map
    # to distinct Whisper words (2 and 5), not both to word 2 (the first match).
    whisper_words = [
        Word('she', 0.0, 0.2),
        Word(' ran', 0.2, 0.5),
        Word(' and', 0.5, 0.7),
        Word(' she', 0.7, 0.9),
        Word(' ran', 0.9, 1.2),
        Word(' and', 1.2, 1.4),
        Word(' she', 1.4, 1.6),
        Word(' stopped', 1.6, 2.0),
    ]
    result = derived_whisper_word_indices([1, 4], 'she ran and she ran and she stopped', whisper_words)
    assert result == [2, 5]
