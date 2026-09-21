"""Respect ``Retry-After`` on HTTP 429 instead of hammering a limited host.

Scrapy's stock ``RetryMiddleware`` requeues a 429 immediately; the only
pacing comes from AutoThrottle's latency estimate, which was never told the
server asked for a specific wait. This middleware reads the standard
``Retry-After`` response header (RFC 9110 §10.2.3 — seconds or an HTTP-date),
caps it to a sane ceiling, and defers the retried request's dispatch by that
long plus a small jitter.

It only annotates requests that ``RETRY_HTTP_CODES`` already covers and never
turns a non-retryable status (401, 403, a robots.txt refusal) into a retry —
that decision stays with ``RetryMiddleware`` and the spiders themselves.
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from scrapy import Request, Spider
from scrapy.http import Response

_META_KEY = "_retry_after_delay"
MAX_DELAY_SECONDS = 60.0
JITTER_SECONDS = 2.0


def parse_retry_after(value: str, *, now: datetime | None = None) -> float | None:
    """Return the seconds a ``Retry-After`` value asks the client to wait.

    Returns ``None`` when the value is empty or does not parse as either an
    integer second count or an RFC 5322/HTTP-date, per RFC 9110 §10.2.3.
    """
    value = value.strip()
    if not value:
        return None
    # delay-seconds is 1*DIGIT (RFC 9110 §10.2.3, ASCII 0-9 only). str.isdigit()
    # alone also accepts non-ASCII digits (e.g. superscripts) that float()
    # cannot parse, which would raise an uncaught ValueError below.
    if value.isascii() and value.isdigit():
        return float(value)
    try:
        target = parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    reference = now or datetime.now(UTC)
    return max((target - reference).total_seconds(), 0.0)


class RetryAfterMiddleware:
    """Downloader middleware: honor ``Retry-After`` before Scrapy retries a 429."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_response(self, request: Request, response: Response, spider: Spider) -> Response:
        if response.status == 429:
            header = response.headers.get("Retry-After")
            if header is not None:
                delay = parse_retry_after(header.decode("latin-1"))
                if delay is not None:
                    request.meta[_META_KEY] = min(delay, MAX_DELAY_SECONDS)
        return response

    async def process_request(self, request: Request, spider: Spider) -> None:
        delay = request.meta.pop(_META_KEY, None)
        if delay:
            await asyncio.sleep(delay + random.uniform(0, JITTER_SECONDS))
        return None
