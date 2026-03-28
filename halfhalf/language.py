def of_text(text):
    ascii_count = sum(1 for c in text if c.isascii() and c.isalpha())
    hangul_count = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3' or '\u1100' <= c <= '\u11FF' or '\u3130' <= c <= '\u318F')
    return 'ko' if hangul_count >= ascii_count else 'en'
