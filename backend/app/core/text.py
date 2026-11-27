import re
import unicodedata

POLISH_TRANSLITERATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
    }
)
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9]+")
SLUG_FALLBACK = "item"


def slugify(value: str) -> str:
    transliterated = value.lower().translate(POLISH_TRANSLITERATION)
    ascii_only = (
        unicodedata.normalize("NFKD", transliterated).encode("ascii", "ignore").decode("ascii")
    )
    slug = NON_ALPHANUMERIC_PATTERN.sub("-", ascii_only).strip("-")
    return slug or SLUG_FALLBACK
