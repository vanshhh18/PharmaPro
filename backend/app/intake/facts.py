import re
from datetime import datetime



FACT_FIELDS = (
    "batch_id",
    "reported_result",
    "spec_limit",
    "event_date",
    "detection_context",
)

_MONTHS = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)

_BATCH_RE = re.compile(
    r"\bbatch(?:es|\s+no\.?|\s+number)?\s+([A-Za-z0-9][A-Za-z0-9._-]*)",
    re.IGNORECASE,
)

_RESULT_PATTERNS = (
    re.compile(r"\b(?:impurity|assay|content|result)s?\s*(?:value|result)?\s*of\s*([\d.]+)\s*%", re.IGNORECASE),
    re.compile(r"\b([\d.]+)\s*%\s*(?:against|versus|vs\.?|compared\s+to)", re.IGNORECASE),
    re.compile(r"\b(?:was|is)\s+([\d.]+)\s*%\s*[;,.)]", re.IGNORECASE),
)

_LIMIT_PATTERNS = (
    re.compile(r"\b(?:specification\s+|spec\s+)?limit\s*of\s*([\d.]+)\s*%", re.IGNORECASE),
    re.compile(r"\b(?:specification|spec)\s*(?:limit)?\s*[:=]\s*([\d.]+)\s*%", re.IGNORECASE),
    re.compile(r"\blimit\s*[:=]\s*([\d.]+)\s*%", re.IGNORECASE),
)

_DATE_PATTERNS = (
    re.compile(rf"\b(\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\s+\d{{4}})\b", re.IGNORECASE),
    re.compile(rf"\b((?:{_MONTHS})\s+\d{{1,2}},\s*\d{{4}})\b", re.IGNORECASE),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(rf"\b((?:{_MONTHS})\s+\d{{1,2}}\s*,?\s+\d{{4}})\b", re.IGNORECASE),
)

_DETECTION_RE = re.compile(
    r"\b(?:identified|detected|observed|discovered|flagged)\b", re.IGNORECASE
)
_MISSING_RE = re.compile(
    r"\b(?:does\s+not\s+include|not\s+included|not\s+documented|not\s+available|"
    r"missing|no\s+record|not\s+recorded|has\s+not\s+been\s+documented|"
    r"unknown|not\s+provided)\b",
    re.IGNORECASE,
)

_QUOTE_MAX = 320
_BORING_BATCH_VALUES = {"documented", "disposition", "record", "records", "number", "no"}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip() for part in parts if part.strip()]


def _find_sentences(regex: re.Pattern, text: str) -> list[str]:
    return [sentence for sentence in _sentences(text) if regex.search(sentence)]


def _quote_for(pattern: re.Pattern, text: str) -> str:
    for sentence in _sentences(text):
        if pattern.search(sentence):
            return sentence[:_QUOTE_MAX]
    return ""


def _distinct(patterns: tuple[re.Pattern, ...], text: str) -> list[tuple[str, str]]:
    """Return [(raw_match, quote)] preserving order, skipping duplicates."""
    found: list[tuple[str, str]] = []
    seen = set()
    for pattern in patterns:
        for match in pattern.finditer(text):
            (value,) = match.groups() if len(match.groups()) == 1 else (match.group(1),)
            key = value.lower().strip()
            if key in seen or not value:
                continue
            seen.add(key)
            found.append((value, _quote_for(pattern, text) or match.group(0)[:_QUOTE_MAX]))
    return found


def _parse_date(raw: str):
    raw = raw.replace(",", " ").replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(" ".join(raw.split()), fmt).date()
        except ValueError:
            continue
    return None


def extract_facts(text: str) -> dict:
    facts: list[dict] = []
    conflicts: list[dict] = []

    batches = [
        b for b in _distinct((_BATCH_RE,), text)
        if b[0].lower().strip("._-") not in _BORING_BATCH_VALUES
        and any(ch.isdigit() for ch in b[0])
    ]
    if batches:
        facts.append({"field": "batch_id", "value": batches[0][0], "quote": batches[0][1]})
        if len({b[0].lower() for b in batches}) > 1:
            conflicts.append({"field": "batch_id", "values": [b[0] for b in batches]})

    results = _distinct(_RESULT_PATTERNS, text)
    if results:
        facts.append({"field": "reported_result", "value": results[0][0] + "%", "quote": results[0][1]})
        if len({float(r[0]) for r in results}) > 1:
            conflicts.append({"field": "reported_result", "values": [r[0] + "%" for r in results]})

    limits = _distinct(_LIMIT_PATTERNS, text)
    if limits:
        facts.append({"field": "spec_limit", "value": limits[0][0] + "%", "quote": limits[0][1]})
        if len({float(l[0]) for l in limits}) > 1:
            conflicts.append({"field": "spec_limit", "values": [l[0] + "%" for l in limits]})

    dates = []
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            (raw,) = match.groups()
            if any(d[0].lower() == raw.lower() for d in dates):
                continue
            dates.append((raw, _quote_for(pattern, text)))
    if dates:
        facts.append({
            "field": "event_date",
            "value": dates[0][0],
            "quote": dates[0][1],
            "iso_date": (_parse_date(dates[0][0]).isoformat() if _parse_date(dates[0][0]) else None),
        })
        parsed = {_parse_date(d[0]) for d in dates}
        if len({p for p in parsed if p}) > 1:
            conflicts.append({"field": "event_date", "values": [d[0] for d in dates]})

    detection = _find_sentences(_DETECTION_RE, text)
    if detection:
        sentence = detection[0]
        facts.append({
            "field": "detection_context",
            "value": sentence[:_QUOTE_MAX],
            "quote": sentence[:_QUOTE_MAX],
        })

    missing = [field for field in FACT_FIELDS if not any(f["field"] == field for f in facts)]
    missing_statements = [s[:_QUOTE_MAX] for s in _find_sentences(_MISSING_RE, text)]

    return {
        "facts": facts,
        "missing": missing,
        "conflicts": conflicts,
        "missing_information_statements": missing_statements,
    }
