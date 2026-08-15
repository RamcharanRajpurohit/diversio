"""Short-lived in-memory storage for upload previews.

The app intentionally does not persist employee data. Pagination needs the
analysis result to survive the redirect from POST to GET, so this module keeps
results only in the current Python process and expires old entries.
"""

from dataclasses import dataclass
from secrets import token_urlsafe
from time import monotonic

from .core.models import AnalysisResult

MAX_ENTRIES = 8
TTL_SECONDS = 30 * 60


@dataclass(slots=True)
class CachedPreview:
    filename: str
    result: AnalysisResult
    created_at: float


_CACHE: dict[str, CachedPreview] = {}


def put(filename: str, result: AnalysisResult) -> str:
    prune()
    token = token_urlsafe(16)
    _CACHE[token] = CachedPreview(filename, result, monotonic())
    prune()
    return token


def get(token: str) -> CachedPreview | None:
    prune()
    return _CACHE.get(token)


def prune() -> None:
    now = monotonic()
    expired = [
        token
        for token, preview in _CACHE.items()
        if now - preview.created_at > TTL_SECONDS
    ]
    for token in expired:
        del _CACHE[token]

    while len(_CACHE) > MAX_ENTRIES:
        oldest = min(_CACHE, key=lambda token: _CACHE[token].created_at)
        del _CACHE[oldest]
