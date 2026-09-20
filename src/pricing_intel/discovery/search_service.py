from __future__ import annotations

import asyncio
import ipaddress
import time
from urllib.parse import urlsplit

from pricing_intel.config import get_settings
from pricing_intel.db.queries import candidates as candidates_q
from pricing_intel.discovery.providers.brave import BraveSearchProvider
from pricing_intel.discovery.urls import canonicalize
from pricing_intel.domain.models import SourceCandidate


class DiscoveryNotConfiguredError(RuntimeError):
    pass


class DiscoveryRateLimitError(RuntimeError):
    pass


class SearchRateLimiter:
    def __init__(self, cooldown_seconds: float = 8.0):
        self._cooldown_seconds = cooldown_seconds
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now - self._last_request_at < self._cooldown_seconds:
                raise DiscoveryRateLimitError(
                    "aguarde alguns segundos antes de executar outra busca ampla"
                )
            self._last_request_at = now


_rate_limiter = SearchRateLimiter()


_TRUSTED_DOMAINS = {
    "apple.com",
    "amazon.com.br",
    "casasbahia.com.br",
    "fastshop.com.br",
    "iplace.com.br",
    "magazineluiza.com.br",
    "mercadolivre.com.br",
    "samsung.com",
}
_KNOWN_DOMAINS = {
    "americanas.com.br",
    "kabum.com.br",
    "pontofrio.com.br",
}


def _registered_domain(hostname: str) -> str:
    hostname = hostname.lower().rstrip(".")
    for domain in _TRUSTED_DOMAINS | _KNOWN_DOMAINS:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return domain
    return hostname


def trust_tier_for_domain(hostname: str) -> str:
    registered = _registered_domain(hostname)
    if registered in _TRUSTED_DOMAINS:
        return "trusted"
    if registered in _KNOWN_DOMAINS:
        return "known"
    return "unknown"


def safe_candidate_url(url: str) -> tuple[str, str] | None:
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        return None
    if parts.hostname.lower() == "localhost":
        return None
    try:
        if not ipaddress.ip_address(parts.hostname).is_global:
            return None
    except ValueError:
        pass
    canonical = canonicalize(url)
    return canonical, parts.hostname.lower().rstrip(".")


async def discover_candidates(query: str) -> list[SourceCandidate]:
    settings = get_settings()
    if not settings.brave_search_api_key:
        raise DiscoveryNotConfiguredError(
            "busca ampla indisponível: configure BRAVE_SEARCH_API_KEY no backend"
        )

    await _rate_limiter.acquire()
    await candidates_q.prune_candidates()

    provider = BraveSearchProvider(
        settings.brave_search_api_key,
        max_results=settings.discovery_max_results,
    )
    variations = [query, f"{query} preço Brasil", f"{query} comprar oferta Brasil"]
    variation_count = min(max(settings.discovery_query_variations, 1), len(variations))
    result_groups = await asyncio.gather(
        *(provider.search(item) for item in variations[:variation_count])
    )
    results = [result for group in result_groups for result in group]
    candidates: list[SourceCandidate] = []
    seen: set[str] = set()
    domain_counts: dict[str, int] = {}
    for result in results:
        safe_url = safe_candidate_url(result.url)
        if safe_url is None:
            continue
        canonical_url, domain = safe_url
        if canonical_url in seen or domain_counts.get(domain, 0) >= 3:
            continue
        seen.add(canonical_url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        candidate = await candidates_q.upsert_candidate(
            url=result.url,
            canonical_url=canonical_url,
            domain=domain,
            title=result.title,
            snippet=result.snippet,
            provider="brave_search",
            query="web discovery",
            trust_tier=trust_tier_for_domain(domain),
        )
        candidates.append(candidate)
    priority = {"trusted": 0, "known": 1, "unknown": 2}
    return sorted(candidates, key=lambda item: priority[item.trust_tier])


async def add_manual_candidate(*, url: str, title: str, snippet: str = "") -> SourceCandidate:
    safe_url = safe_candidate_url(url)
    if safe_url is None:
        raise ValueError("candidate URL must be a public HTTPS URL without credentials")
    canonical_url, domain = safe_url
    return await candidates_q.upsert_candidate(
        url=url,
        canonical_url=canonical_url,
        domain=domain,
        title=title,
        snippet=snippet,
        provider="manual",
        query="manual onboarding",
        trust_tier=trust_tier_for_domain(domain),
    )
