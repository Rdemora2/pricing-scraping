import socket
from dataclasses import dataclass

import pytest
from scrapy.http import Request, Response, TextResponse

from pricing_intel.collection.browser import (
    browser_request_meta,
    has_browser_fallback,
    install_browser_request_policy,
)
from pricing_intel.collection.spiders.retail import AmazonSpider, AmericanasSpider, KabumSpider


@dataclass
class _BrowserRequest:
    url: str
    resource_type: str = "document"


class _Route:
    def __init__(self, url: str, resource_type: str = "document") -> None:
        self.request = _BrowserRequest(url, resource_type)
        self.action: str | None = None

    async def abort(self) -> None:
        self.action = "abort"

    async def continue_(self) -> None:
        self.action = "continue"


class _Page:
    handler = None

    async def route(self, _pattern: str, handler) -> None:
        self.handler = handler


def _public_resolver(host: str, port: int, *_args, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _spider() -> AmazonSpider:
    spider = AmazonSpider(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url="https://www.amazon.com.br/",
        product_name="Apple iPhone 17",
        product_model="iphone_17",
        storages="256",
    )
    spider.browser_resolver = _public_resolver
    return spider


def _response(body: str) -> TextResponse:
    request = Request("https://www.amazon.com.br/example/dp/B0GQW2J4SK")
    return TextResponse(url=request.url, request=request, body=body.encode(), encoding="utf-8")


def _kabum_spider() -> KabumSpider:
    spider = KabumSpider(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url="https://www.kabum.com.br/",
        product_name="Apple iPhone 17 Pro Max",
        product_model="iphone_17_pro_max",
        storages="512",
    )
    spider.browser_resolver = _public_resolver
    return spider


def _amazon_page() -> str:
    return """
        <h1><span id="productTitle">Apple iPhone 17 de 256 GB — Preto</span></h1>
        <div id="corePrice_feature_div"><span class="a-offscreen">R$ 5.698,99</span></div>
        <div id="availability"><span>Em estoque</span></div>
        <div offer-display-feature-name="desktop-merchant-info">
          <span class="offer-display-feature-text-message">Amazon.com.br</span>
          <span class="offer-display-feature-text-message">Amazon.com.br</span>
        </div>
    """


def test_browser_metadata_is_explicit_and_bounded() -> None:
    meta = browser_request_meta(
        allowed_hosts=("www.amazon.com.br",),
        resolver=_public_resolver,
    )

    assert meta["playwright"] is True
    assert meta["playwright_include_page"] is False
    assert meta["browser_allowed_hosts"] == ("www.amazon.com.br",)
    assert meta["playwright_context_kwargs"] == {
        "accept_downloads": False,
        "java_script_enabled": True,
        "locale": "pt-BR",
        "service_workers": "block",
        "timezone_id": "America/Sao_Paulo",
        "user_agent": "pricing-intel-lab-bot/0.1 (+local pricing intelligence portfolio project)",
    }
    assert has_browser_fallback("amazon") is True
    assert has_browser_fallback("kabum") is True
    assert has_browser_fallback("fast_shop") is False


@pytest.mark.asyncio
async def test_browser_policy_allows_reviewed_host_and_blocks_other_networks() -> None:
    page = _Page()
    request = Request(
        "https://www.amazon.com.br/item",
        meta={"browser_allowed_hosts": ("www.amazon.com.br",)},
    )
    await install_browser_request_policy(page, request)
    assert page.handler is not None

    allowed = _Route("https://www.amazon.com.br/script.js", "script")
    external = _Route("https://tracker.example/collect", "xhr")
    image = _Route("https://www.amazon.com.br/image.jpg", "image")
    await page.handler(allowed)
    await page.handler(external)
    await page.handler(image)

    assert allowed.action == "continue"
    assert external.action == "abort"
    assert image.action == "abort"


def test_amazon_uses_browser_only_after_http_extraction_failure() -> None:
    spider = _spider()

    fallback = list(spider.parse_product(_response("<html>missing product data</html>")))

    assert len(fallback) == 1
    assert fallback[0].meta["playwright"] is True
    assert fallback[0].dont_filter is True
    assert fallback[0].callback == spider.parse_browser_product


def test_amazon_uses_browser_after_non_text_http_response() -> None:
    spider = _spider()
    request = Request("https://www.amazon.com.br/example/dp/B0GQW2J4SK")
    response = Response(url=request.url, request=request, body=b"opaque")

    fallback = list(spider.parse_product(response))

    assert len(fallback) == 1
    assert fallback[0].meta["playwright"] is True


@pytest.mark.asyncio
async def test_access_control_error_does_not_trigger_browser_fallback() -> None:
    spider = _spider()

    requests = [request async for request in spider.start()]

    assert requests[0].errback is None


def test_amazon_http_success_does_not_schedule_browser() -> None:
    spider = _spider()

    result = list(spider.parse_product(_response(_amazon_page())))

    assert len(result) == 1
    assert result[0]["extractor_name"] == "amazon_visible_buy_box"
    assert result[0]["seller_display_name"] == "Amazon.com.br"


def test_browser_evidence_is_explicit_in_extractor_name() -> None:
    spider = _spider()

    result = list(spider.parse_browser_product(_response(_amazon_page())))

    assert result[0]["extractor_name"] == "amazon_visible_buy_box_browser_fallback"


def test_kabum_search_uses_browser_only_when_http_has_no_product_links() -> None:
    spider = _kabum_spider()
    request = Request("https://www.kabum.com.br/busca/apple-iphone-17-pro-max-512gb")
    response = TextResponse(
        url=request.url, request=request, body=b"<main></main>", encoding="utf-8"
    )

    fallback = list(spider.parse_search(response, storage_gb="512"))

    assert len(fallback) == 1
    assert fallback[0].meta["playwright"] is True
    assert fallback[0].callback == spider.parse_search


def test_kabum_rendered_search_follows_only_the_exact_product() -> None:
    spider = _kabum_spider()
    request = Request(
        "https://www.kabum.com.br/busca/apple-iphone-17-pro-max-512gb",
        meta={"playwright": True},
    )
    body = b"""
      <a href="/produto/123/iphone-17-pro-max-512gb-preto">Apple iPhone 17 Pro Max 512GB</a>
      <a href="/produto/124/iphone-17-pro-512gb-preto">Apple iPhone 17 Pro 512GB</a>
    """
    response = TextResponse(url=request.url, request=request, body=body, encoding="utf-8")

    product_requests = list(spider.parse_search(response, storage_gb="512"))

    assert [item.url for item in product_requests] == [
        "https://www.kabum.com.br/produto/123/iphone-17-pro-max-512gb-preto"
    ]
    assert all(not item.meta.get("playwright") for item in product_requests)


@pytest.mark.parametrize(
    ("spider_class", "search_url", "wait_selector"),
    [
        (AmazonSpider, "https://www.amazon.com.br/s?k=iphone", "a[href*='/dp/']"),
        (
            AmericanasSpider,
            "https://www.americanas.com.br/s?q=iphone",
            "a[href$='/p'], a[href*='/p?']",
        ),
    ],
)
def test_js_catalog_search_has_one_bounded_browser_fallback(
    spider_class, search_url: str, wait_selector: str
) -> None:
    spider = spider_class(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url=search_url.split("/s?", 1)[0] + "/",
        product_name="Apple iPhone 17 Pro Max",
        product_model="iphone_17_pro_max",
        storages="512",
    )
    spider.browser_resolver = _public_resolver
    request = Request(search_url)
    response = TextResponse(
        url=request.url, request=request, body=b"<main></main>", encoding="utf-8"
    )

    fallback = list(spider.parse_search(response, storage_gb="512"))

    assert len(fallback) == 1
    assert fallback[0].meta["playwright"] is True
    assert fallback[0].callback == spider.parse_search
    page_method = fallback[0].meta["playwright_page_methods"][0]
    assert page_method.method == "wait_for_selector"
    assert page_method.args == (wait_selector,)


def test_rendered_amazon_search_follows_exact_model_and_capacity() -> None:
    spider = AmazonSpider(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url="https://www.amazon.com.br/",
        product_name="Apple iPhone 17 Pro Max",
        product_model="iphone_17_pro_max",
        storages="512",
    )
    request = Request(
        "https://www.amazon.com.br/s?k=iphone",
        meta={"playwright": True},
    )
    body = b"""
      <a href="/Apple-iPhone-Pro-Max-512/dp/B0FQH3X8R8">Apple iPhone 17 Pro Max 512GB</a>
      <a href="/Apple-iPhone-Pro-512/dp/B0FQH3X8R9">Apple iPhone 17 Pro 512GB</a>
    """
    response = TextResponse(url=request.url, request=request, body=body, encoding="utf-8")

    product_requests = list(spider.parse_search(response, storage_gb="512"))

    assert [item.url for item in product_requests] == [
        "https://www.amazon.com.br/Apple-iPhone-Pro-Max-512/dp/B0FQH3X8R8"
    ]
