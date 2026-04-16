"""Search-token normalization helpers."""

import re

from beartype import beartype

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
CAMEL_PATTERN = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")


@beartype
def tokenize_search_terms(text: str) -> tuple[str, ...]:
    """Tokenize text into lowercase search terms."""
    terms: list[str] = []
    for raw in TOKEN_PATTERN.findall(text):
        parts = CAMEL_PATTERN.findall(raw) or [raw]
        terms.extend(part.lower() for part in parts if part)
    return tuple(terms)
