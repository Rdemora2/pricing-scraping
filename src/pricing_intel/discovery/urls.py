"""URL canonicalization for discovery bookkeeping.

Goal is deduplication without collapsing variant-identifying links: we
drop known tracking noise (utm_*, session/click ids) and normalize
ordering/case, but any query parameter we do not recognize as noise is
kept — silently dropping an unfamiliar param could merge two distinct
product variants into one discovered_page row.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_NOISE_PARAM_PREFIXES = ("utm_",)
_NOISE_PARAMS = frozenset(
    {
        "gclid",
        "fbclid",
        "sessionid",
        "session_id",
        "click_id",
        "ref",
    }
)


def _is_noise(param_name: str) -> bool:
    lowered = param_name.lower()
    return lowered in _NOISE_PARAMS or lowered.startswith(_NOISE_PARAM_PREFIXES)


def canonicalize(url: str) -> str:
    parts = urlsplit(url)
    kept_params = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_noise(key)
    )
    path = parts.path.rstrip("/") or "/"
    netloc = parts.netloc.lower()
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(kept_params), ""))
