from pricing_intel.collection import settings
from pricing_intel.collection.spiders.retail import AmazonSpider


def test_http_profile_negotiates_html_in_portuguese_without_impersonation() -> None:
    assert settings.DEFAULT_REQUEST_HEADERS == {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
        "Cache-Control": "no-cache",
    }
    assert "bot" in settings.USER_AGENT
    assert "Mozilla" not in settings.USER_AGENT
    assert not any(
        name.casefold().startswith("sec-ch-ua") for name in settings.DEFAULT_REQUEST_HEADERS
    )


def test_amazon_inherits_the_governed_http_profile() -> None:
    assert "DEFAULT_REQUEST_HEADERS" not in AmazonSpider.custom_settings
