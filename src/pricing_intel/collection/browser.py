"""Governed Playwright acquisition for reviewed JavaScript-capable sources."""

from __future__ import annotations

import socket
from collections.abc import Collection
from urllib.parse import urlsplit

from scrapy.http import Request
from scrapy_playwright.page import PageMethod

from pricing_intel.collection.network_policy import Resolver, validate_outbound_url

BROWSER_FALLBACK_ADAPTERS = frozenset({"amazon", "americanas", "carrefour"})
_BLOCKED_RESOURCE_TYPES = frozenset({"font", "image", "media"})
DECLARED_USER_AGENT = "pricing-intel-lab-bot/0.1 (+local pricing intelligence portfolio project)"


def has_browser_fallback(adapter_name: str) -> bool:
    return adapter_name in BROWSER_FALLBACK_ADAPTERS


async def install_browser_request_policy(page, request: Request) -> None:
    """Restrict browser subrequests to the reviewed source hosts.

    Playwright traffic does not traverse Scrapy downloader middleware, so the
    browser needs its own fail-closed host boundary. Heavy visual resources are
    blocked because extraction only consumes the rendered DOM.
    """
    allowed_hosts = frozenset(request.meta.get("browser_allowed_hosts", ()))
    if not allowed_hosts:
        raise ValueError("browser request is missing its host allowlist")

    async def guard(route) -> None:
        browser_request = route.request
        parts = urlsplit(browser_request.url)
        if browser_request.resource_type in _BLOCKED_RESOURCE_TYPES:
            await route.abort()
        elif parts.scheme in {"about", "blob", "data"} or (
            parts.scheme == "https" and (parts.hostname or "").lower() in allowed_hosts
        ):
            await route.continue_()
        else:
            await route.abort()

    await page.route("**/*", guard)


def browser_request_meta(
    *,
    allowed_hosts: Collection[str],
    resolver: Resolver = socket.getaddrinfo,
) -> dict[str, object]:
    normalized_hosts = tuple(sorted({host.casefold().rstrip(".") for host in allowed_hosts}))
    if not normalized_hosts:
        raise ValueError("browser acquisition requires at least one allowed host")
    for host in normalized_hosts:
        validate_outbound_url(
            f"https://{host}/",
            allowed_hosts=normalized_hosts,
            resolver=resolver,
        )
    return {
        "playwright": True,
        "playwright_include_page": False,
        "playwright_page_init_callback": install_browser_request_policy,
        "playwright_page_goto_kwargs": {
            "wait_until": "domcontentloaded",
            "timeout": 15_000,
        },
        "playwright_page_methods": [PageMethod("wait_for_timeout", 750)],
        "playwright_context_kwargs": {
            "accept_downloads": False,
            "java_script_enabled": True,
            "locale": "pt-BR",
            "service_workers": "block",
            "timezone_id": "America/Sao_Paulo",
            "user_agent": DECLARED_USER_AGENT,
        },
        "browser_allowed_hosts": normalized_hosts,
    }
