# Known mis-transcriptions of host names and podcast name.
# Ordered: longer/more-specific patterns must come before shorter ones
# to avoid partial-match interference.

CORRECTIONS = [
    # Podcast name variants (하프앤하프)
    ("커플 너프", "하프앤하프"),
    ("하프이나 하프", "하프앤하프"),
    ("하프엔 하프", "하프앤하프"),
    ("하프인 하프", "하프앤하프"),
    ("하프에 하프", "하프앤하프"),
    ("하프리나프", "하프앤하프"),
    ("하프히너프", "하프앤하프"),
    ("하프에다프", "하프앤하프"),
    ("하프앤어프", "하프앤하프"),
    ("하프앤나프", "하프앤하프"),
    ("하프앤 하프", "하프앤하프"),
    ("하프엔하프", "하프앤하프"),
    ("하프 하프", "하프앤하프"),
    ("하프하프", "하프앤하프"),
    ("하프&하프", "하프앤하프"),

    # Host name variants (정태웅)
    ("정태홍", "정태웅"),
    ("정태용", "정태웅"),
    ("정태옥", "정태웅"),
    ("종태영", "정태웅"),

    # Jeep co-host name variants
    ("ZIF", "Jeep"),

    # 팟캐스트 variants
    ("파키스트", "팟캐스트"),
    ("파케스트", "팟캐스트"),
    ("팟키스트", "팟캐스트"),
    ("팟케스트", "팟캐스트"),
    ("팟기스트", "팟캐스트"),
    ("파티스트", "팟캐스트"),
]


def apply(text):
    for bad, good in CORRECTIONS:
        text = text.replace(bad, good)
    return text
