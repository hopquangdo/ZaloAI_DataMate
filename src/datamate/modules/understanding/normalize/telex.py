"""Giải mã từ gõ Telex chưa được bộ gõ chuyển: "dduwowcj" → "được", "toongr" → "tổng".

Chỉ giải mã khi chắc: âm tiết tiếng Việt không bao giờ kết thúc bằng s/f/r/x/j, và chữ ghép
dd/aa/aw/ee/oo/ow/uw không có trong âm tiết không dấu bình thường. Kết quả phải là một âm tiết
tiếng Việt hợp lệ, không thì giữ nguyên từ gốc.
"""

from __future__ import annotations

import re
import unicodedata

_TONES = {"s": "́", "f": "̀", "r": "̉", "x": "̃", "j": "̣"}
_MODIFIERS = (
    ("dd", "đ"),
    ("uow", "ươ"),
    ("uwow", "ươ"),
    ("aa", "â"),
    ("aw", "ă"),
    ("ee", "ê"),
    ("oo", "ô"),
    ("ow", "ơ"),
    ("uw", "ư"),
)
_VOWELS = "aăâeêioôơuưy"
_MARKED = "ăâêôơư"
# phụ âm đầu, cụm nguyên âm, phụ âm cuối của một âm tiết tiếng Việt
_SYLLABLE = re.compile(
    r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdđghklmnpqrstvx])?"
    rf"([{_VOWELS}]{{1,3}})"
    r"(ch|ng|nh|[cmnpt])?$"
)


def _place_tone(word: str, tone: str) -> str:
    match = _SYLLABLE.match(word)
    if match is None:
        return word
    onset, vowels, final = match.group(1) or "", match.group(2), match.group(3) or ""
    if onset == "qu" or (onset == "gi" and vowels):
        pass  # "u" / "i" đã thuộc phụ âm đầu
    marked = [i for i, ch in enumerate(vowels) if ch in _MARKED]
    if marked:
        index = marked[-1]  # "ươ" → dấu trên "ơ"
    elif final or len(vowels) == 1:
        index = len(vowels) - 1
    elif vowels in ("oa", "oe", "uy"):
        index = 1
    else:
        index = 0
    toned = unicodedata.normalize("NFC", vowels[index] + _TONES[tone])
    return onset + vowels[:index] + toned + vowels[index + 1 :] + final


def decode_word(word: str) -> str:
    """Giải mã một từ Telex; trả lại nguyên từ nếu không chắc."""
    if not word.isascii() or not word.isalpha() or len(word) < 2 or len(word) > 9:
        return word
    lower = word.lower()
    tone = lower[-1] if lower[-1] in _TONES else None
    body = lower[:-1] if tone else lower
    decoded = body
    for pattern, replacement in _MODIFIERS:
        decoded = decoded.replace(pattern, replacement)
    if tone is None and decoded == body:
        return word  # không có dấu hiệu Telex nào
    # chỉ có chữ dấu ở cuối: dễ là từ ngoại / tên riêng ("Max", "box", "gas")
    short_foreign = len(word) < 3 or (len(word) == 3 and tone in ("s", "x"))
    if decoded == body and (word[0].isupper() or short_foreign):
        return word
    if not _SYLLABLE.match(decoded):
        return word
    result = _place_tone(decoded, tone) if tone else decoded
    return result.capitalize() if word[0].isupper() else result


def decode_telex(text: str) -> str:
    """Giải mã mọi từ Telex sót trong câu, giữ nguyên các từ khác."""
    return re.sub(r"[A-Za-z]+", lambda m: decode_word(m.group(0)), text)
