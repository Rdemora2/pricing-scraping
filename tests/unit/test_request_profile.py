from pricing_intel.collection import settings
from pricing_intel.collection.browser import CHROME_MAJOR_VERSION
from pricing_intel.collection.spiders.retail import AmazonSpider


def test_http_profile_negotiates_html_in_portuguese_like_a_current_desktop_browser() -> None:
    assert {
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "Sec-CH-UA": (
            f'"Chromium";v="{CHROME_MAJOR_VERSION}", "Not_A Brand";v="24", '
            f'"Google Chrome";v="{CHROME_MAJOR_VERSION}"'
        ),
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    } == settings.DEFAULT_REQUEST_HEADERS
    assert "Mozilla" in settings.USER_AGENT
    assert f"Chrome/{CHROME_MAJOR_VERSION}." in settings.USER_AGENT
    # Client Hints must name the same Chrome version as the User-Agent string,
    # or the mismatch itself becomes a bot-detection signal.
    assert CHROME_MAJOR_VERSION in settings.DEFAULT_REQUEST_HEADERS["Sec-CH-UA"]


def test_amazon_inherits_the_governed_http_profile() -> None:
    assert "DEFAULT_REQUEST_HEADERS" not in AmazonSpider.custom_settings
    assert "COMPRESSION_ENABLED" not in AmazonSpider.custom_settings
