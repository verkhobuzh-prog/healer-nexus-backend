"""
Shared slug generation with Ukrainian transliteration. Used by blog and taxonomy services.
"""
from __future__ import annotations

import re
import unicodedata

UA_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ye", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "yi", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "yu", "я": "ya",
    "А": "A", "Б": "B", "В": "V", "Г": "H", "Ґ": "G", "Д": "D", "Е": "E",
    "Є": "Ye", "Ж": "Zh", "З": "Z", "И": "Y", "І": "I", "Ї": "Yi", "Й": "Y",
    "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R",
    "С": "S", "Т": "T", "У": "U", "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch",
    "Ш": "Sh", "Щ": "Shch", "Ь": "", "Ю": "Yu", "Я": "Ya",
}


def generate_slug(title: str) -> str:
    """Slug from title with Ukrainian transliteration."""
    if not title or not title.strip():
        return "post"
    slug = title.strip()
    result = []
    for char in slug:
        if char in UA_TRANSLIT:
            result.append(UA_TRANSLIT[char])
        elif char.isalnum() or char in " -_":
            result.append(char)
        else:
            try:
                n = unicodedata.name(char)
                if "LATIN" in n or "DIGIT" in n:
                    result.append(char)
                else:
                    result.append("")
            except ValueError:
                result.append("")
    slug = "".join(result)
    slug = re.sub(r"[-\s]+", "-", slug).strip("-").lower()
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug or "post"
