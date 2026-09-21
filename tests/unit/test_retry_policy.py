from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from scrapy import Request, Spider
from scrapy.http import Response

from pricing_intel.collection.retry_policy import (
    JITTER_SECONDS,
    MAX_DELAY_SECONDS,
    RetryAfterMiddleware,
    parse_retry_after,
)

_spider = Spider(name="test")


def test_parse_retry_after_reads_seconds() -> None:
    assert parse_retry_after("45") == 45.0


def test_parse_retry_after_reads_http_date() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert parse_retry_after("Thu, 01 Jan 2026 12:00:45 GMT", now=now) == 45.0


def test_parse_retry_after_clamps_a_past_date_to_zero() -> None:
    now = datetime(2026, 1, 1, 12, 0, 45, tzinfo=UTC)
    assert parse_retry_after("Thu, 01 Jan 2026 12:00:00 GMT", now=now) == 0.0


@pytest.mark.parametrize("value", ["", "   ", "not-a-date", "12:00"])
def test_parse_retry_after_rejects_unparseable_values(value: str) -> None:
    assert parse_retry_after(value) is None


def _response(status: int, headers: dict[str, str] | None = None) -> Response:
    request = Request("https://www.example.com.br/produto")
    return Response(url=request.url, request=request, status=status, headers=headers or {})


@pytest.mark.asyncio
async def test_process_request_waits_out_the_advertised_retry_after(monkeypatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr("pricing_intel.collection.retry_policy.asyncio.sleep", sleep)
    middleware = RetryAfterMiddleware()
    request = Request("https://www.example.com.br/produto")

    middleware.process_response(request, _response(429, {"Retry-After": "5"}), spider=_spider)
    await middleware.process_request(request, spider=_spider)

    sleep.assert_awaited_once()
    (waited,), _kwargs = sleep.call_args
    assert 5.0 <= waited <= 5.0 + JITTER_SECONDS


@pytest.mark.asyncio
async def test_process_request_caps_an_excessive_retry_after(monkeypatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr("pricing_intel.collection.retry_policy.asyncio.sleep", sleep)
    middleware = RetryAfterMiddleware()
    request = Request("https://www.example.com.br/produto")

    middleware.process_response(request, _response(429, {"Retry-After": "3600"}), spider=_spider)
    await middleware.process_request(request, spider=_spider)

    (waited,), _kwargs = sleep.call_args
    assert MAX_DELAY_SECONDS <= waited <= MAX_DELAY_SECONDS + JITTER_SECONDS


@pytest.mark.asyncio
async def test_process_request_does_not_wait_without_a_retry_after_header(monkeypatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr("pricing_intel.collection.retry_policy.asyncio.sleep", sleep)
    middleware = RetryAfterMiddleware()
    request = Request("https://www.example.com.br/produto")

    middleware.process_response(request, _response(429, {}), spider=_spider)
    await middleware.process_request(request, spider=_spider)

    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_request_ignores_retry_after_on_a_non_429_status(monkeypatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr("pricing_intel.collection.retry_policy.asyncio.sleep", sleep)
    middleware = RetryAfterMiddleware()
    request = Request("https://www.example.com.br/produto")

    # A 403 refusal must never gain a scheduled wait-and-retry from this
    # middleware — that would turn a hard access-control refusal into the
    # kind of automatic retry-around-blocking this project rejects elsewhere
    # (see test_browser_fallback.py::test_access_control_error_does_not_trigger_browser_fallback).
    middleware.process_response(request, _response(403, {"Retry-After": "5"}), spider=_spider)
    await middleware.process_request(request, spider=_spider)

    sleep.assert_not_awaited()


def test_process_response_returns_the_response_unchanged() -> None:
    middleware = RetryAfterMiddleware()
    request = Request("https://www.example.com.br/produto")
    response = _response(429, {"Retry-After": "5"})

    assert middleware.process_response(request, response, spider=_spider) is response
