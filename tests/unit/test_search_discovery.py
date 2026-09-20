import pytest

from pricing_intel.discovery.search_service import (
    DiscoveryRateLimitError,
    SearchRateLimiter,
    safe_candidate_url,
    trust_tier_for_domain,
)


def test_discovery_prioritizes_reviewed_commerce_domains() -> None:
    assert trust_tier_for_domain("www.apple.com") == "trusted"
    assert trust_tier_for_domain("site.fastshop.com.br") == "trusted"
    assert trust_tier_for_domain("m.magazineluiza.com.br") == "trusted"
    assert trust_tier_for_domain("shop.samsung.com") == "trusted"


def test_discovery_marks_unlisted_domains_for_review() -> None:
    assert trust_tier_for_domain("oferta.example") == "unknown"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/item",
        "https://localhost/item",
        "https://127.0.0.1/item",
        "https://10.0.0.1/item",
        "https://user:password@example.com/item",
    ],
)
def test_discovery_rejects_unsafe_candidate_urls(url: str) -> None:
    assert safe_candidate_url(url) is None


def test_discovery_accepts_and_canonicalizes_public_https_url() -> None:
    assert safe_candidate_url("https://www.apple.com/br/iphone/?utm_source=test") == (
        "https://www.apple.com/br/iphone",
        "www.apple.com",
    )


async def test_discovery_rate_limiter_rejects_immediate_second_request() -> None:
    limiter = SearchRateLimiter(cooldown_seconds=60)

    await limiter.acquire()

    with pytest.raises(DiscoveryRateLimitError):
        await limiter.acquire()
