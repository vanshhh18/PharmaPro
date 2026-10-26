import re
import unicodedata

from ..config import settings


class IntakeError(ValueError):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


# Remove characters that carry no meaning in a quality report and could be
# used to hide content or confuse parsing. Keep letters, digits, whitespace,
# and common punctuation/symbols seen in reports.
_ALLOWED_PREFIXES = ("L", "N", "Z", "P", "S")


def normalize_text(raw: str) -> str:
    """Normalize untrusted report text. Raises IntakeError when unusable."""
    if raw is None:
        raise IntakeError("No report text was supplied")

    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", "")

    cleaned_chars = []
    for char in text:
        category = unicodedata.category(char)
        if char in "\n\t ":
            cleaned_chars.append(char)
        elif category.startswith(_ALLOWED_PREFIXES):
            cleaned_chars.append(char)
        # anything else (control chars Cf/Cc/Others) is dropped

    text = "".join(cleaned_chars)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if not text or not any(ch.isalnum() for ch in text):
        raise IntakeError("Report text is empty or contains no readable content")

    if len(text) > settings.max_report_chars:
        raise IntakeError(
            f"Report text exceeds the {settings.max_report_chars} character limit",
            status_code=413,
        )
    return text
