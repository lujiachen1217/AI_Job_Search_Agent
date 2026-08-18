"""Centralized allowlist-based location policy for all job sources."""

import re

from src.config import (
    ALLOWED_LOCATION_KEYWORDS,
    US_STATE_ABBREVIATIONS,
    US_STATE_NAMES,
)


_ALLOWED_KEYWORD_PATTERN = re.compile(
    r"(?<!\w)(?:"
    + "|".join(
        re.escape(keyword) for keyword in sorted(
            ALLOWED_LOCATION_KEYWORDS, key=len, reverse=True
        )
    )
    + r")(?!\w)",
    re.IGNORECASE,
)
_US_STATE_NAME_PATTERN = re.compile(
    r"(?<!\w)(?:"
    + "|".join(
        re.escape(state) for state in sorted(
            US_STATE_NAMES, key=len, reverse=True
        )
    )
    + r")(?!\w)",
    re.IGNORECASE,
)
_US_STATE_ABBREVIATION_PATTERN = re.compile(
    r"(?:^|[,;/(-]\s*)(?:"
    + "|".join(US_STATE_ABBREVIATIONS)
    + r")(?=$|[,;/)-])",
    re.IGNORECASE,
)
_US_COUNTRY_CODE_PATTERN = re.compile(
    r"(?:^|[,\s(/|-])(?:US|U\.S\.|USA|U\.S\.A\.)(?:$|[,\s)/|-])",
    re.IGNORECASE,
)
_HONG_KONG_CODE_PATTERN = re.compile(
    r"(?:^|[,\s(/|-])HK(?:$|[,\s)/|-])",
    re.IGNORECASE,
)
_GENERIC_REMOTE_PATTERN = re.compile(
    r"^remote(?:\s*[-,/|]?\s*(?:hybrid|flexible|anywhere))?$",
    re.IGNORECASE,
)


def is_allowed_location(location: str) -> bool:
    """Return whether a location clearly belongs to an allowed region."""
    normalized = re.sub(r"\s+", " ", location or "").strip()
    if not normalized:
        return False

    if _GENERIC_REMOTE_PATTERN.fullmatch(normalized):
        return True

    return any(
        pattern.search(normalized)
        for pattern in (
            _ALLOWED_KEYWORD_PATTERN,
            _US_STATE_NAME_PATTERN,
            _US_STATE_ABBREVIATION_PATTERN,
            _US_COUNTRY_CODE_PATTERN,
            _HONG_KONG_CODE_PATTERN,
        )
    )


def is_excluded_location(location: str) -> bool:
    """Return whether a location falls outside the centralized allowlist."""
    return not is_allowed_location(location)
