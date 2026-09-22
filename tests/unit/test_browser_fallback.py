import socket
from dataclasses import dataclass

import pytest
from scrapy.http import Request, Response, TextResponse

from pricing_intel.collection import settings
from pricing_intel.collection.browser import (
    browser_request_meta,
    has_browser_fallback,
    install_browser_request_policy,
)
from pricing_intel.collection.items import ListingRejectedItem
from pricing_intel.collection.spiders.retail import (
    AmazonSpider,
    AmericanasSpider,
    CarrefourSpider,
    IPlaceSpider,
    KabumSpider,
)
from pricing_intel.domain.enums import RejectionStage


def _assert_blocked_without_browser(results: list, *, status: int) -> None:
    """A refused page escalates nothing and is recorded as an access loss.

    The invariant these tests protect is that a block never reaches the
    browser — not that the run forgets the block happened. The refusal is
    persisted so a source that starts answering 403 is visible as lost
    retailer depth rather than as an empty result.
    """
    assert not [item for item in results if isinstance(item, Request)]
    rejections = [item for item in results if isinstance(item, ListingRejectedItem)]
    assert len(rejections) == 1
    assert rejections[0]["stage"] == RejectionStage.ACCESS
    assert str(status) in rejections[0]["reason"]


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
    # No user_agent key: Playwright's own Chromium build must stay the single
    # source of truth for UA/Sec-CH-UA/navigator.userAgentData, or the three
    # disagree with each other — a stronger bot signal than any of them being
    # merely non-default.
    assert meta["playwright_context_kwargs"] == {
        "accept_downloads": False,
        "java_script_enabled": True,
        "locale": "pt-BR",
        "service_workers": "block",
        "timezone_id": "America/Sao_Paulo",
    }
    assert has_browser_fallback("amazon") is True
    assert has_browser_fallback("kabum") is True
    assert has_browser_fallback("iplace") is True
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


def _blocked_response(status: int, url: str) -> TextResponse:
    request = Request(url)
    return TextResponse(
        url=request.url,
        request=request,
        status=status,
        body=b"<html>access denied</html>",
        encoding="utf-8",
    )


@pytest.mark.parametrize("status", [401, 403, 429])
def test_amazon_blocked_product_page_does_not_escalate_to_browser(status: int) -> None:
    # Scrapy's HttpErrorMiddleware already keeps non-2xx responses away from
    # parse_product in production; this is the defense-in-depth check for if
    # that middleware were ever reconfigured (HTTPERROR_ALLOW_ALL and friends
    # — see test_settings_never_allow_error_responses_to_reach_spiders below).
    spider = _spider()
    response = _blocked_response(status, "https://www.amazon.com.br/example/dp/B0GQW2J4SK")

    _assert_blocked_without_browser(list(spider.parse_product(response)), status=status)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_carrefour_blocked_product_page_does_not_escalate_to_browser(status: int) -> None:
    spider = CarrefourSpider(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url="https://www.carrefour.com.br/",
        product_name="Apple iPhone 17",
        product_model="iphone_17",
        storages="256",
    )
    response = _blocked_response(status, "https://www.carrefour.com.br/produto/example")

    _assert_blocked_without_browser(list(spider.parse_product(response)), status=status)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_americanas_blocked_product_page_does_not_escalate_to_browser(status: int) -> None:
    spider = AmericanasSpider(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url="https://www.americanas.com.br/",
        product_name="Apple iPhone 17",
        product_model="iphone_17",
        storages="256",
    )
    response = _blocked_response(status, "https://www.americanas.com.br/produto/example/p")

    _assert_blocked_without_browser(list(spider.parse_product(response)), status=status)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_kabum_blocked_search_does_not_escalate_to_browser(status: int) -> None:
    spider = _kabum_spider()
    response = _blocked_response(
        status, "https://www.kabum.com.br/busca/apple-iphone-17-pro-max-512gb"
    )

    _assert_blocked_without_browser(
        list(spider.parse_search(response, storage_gb="512")), status=status
    )


def test_settings_never_allow_error_responses_to_reach_spiders() -> None:
    # The defense-in-depth checks above only hold in production because
    # Scrapy's HttpErrorMiddleware keeps non-2xx responses from ever reaching
    # a parse_*/parse_search callback. If either of these settings changed,
    # that guarantee would silently disappear.
    assert getattr(settings, "HTTPERROR_ALLOW_ALL", False) is False
    assert not getattr(settings, "HTTPERROR_ALLOWED_CODES", ())


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


def test_carrefour_never_requests_the_route_its_robots_txt_forbids() -> None:
    # Carrefour's robots.txt disallows /busca/. Product discovery moved to the
    # store's published sitemap, so no request may target the search route.
    spider = CarrefourSpider(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url="https://www.carrefour.com.br/",
        product_name="Apple iPhone 16",
        product_model="iphone_16",
        storages="128",
    )

    requests = list(spider.sitemap_requests())

    assert [request.url for request in requests] == ["https://www.carrefour.com.br/sitemap.xml"]
    assert not hasattr(spider, "parse_search")


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


def _iplace_spider(product_model: str = "iphone_17_pro") -> IPlaceSpider:
    spider = IPlaceSpider(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url="https://www.iplace.com.br/",
        product_name="Apple iPhone 17 Pro",
        product_model=product_model,
        storages="256",
    )
    spider.browser_resolver = _public_resolver
    return spider


def _iplace_response(status: int = 200, with_jsonld: bool = False) -> TextResponse:
    request = Request("https://www.iplace.com.br/apple-iphone-17-pro/100411PR")
    body = '<html><body><div id="root"></div></body></html>'
    if with_jsonld:
        # Trimmed to the fields the shared extractor reads; matches the shape
        # iPlace's rendered page embeds after client-side hydration.
        body = (
            '<script type="application/ld+json">'
            '{"@type":"Product","name":"Apple iPhone 17 Pro 256GB Azul-intenso",'
            '"sku":"100072467",'
            '"offers":[{"@type":"Offer","priceCurrency":"BRL","price":8829,'
            '"availability":"http://schema.org/InStock",'
            '"itemCondition":"http://schema.org/NewCondition"}]}'
            "</script>"
        )
    return TextResponse(
        url=request.url, request=request, status=status, body=body.encode(), encoding="utf-8"
    )


async def _first_start_request(spider: IPlaceSpider) -> Request:
    return await anext(request async for request in spider.start())


@pytest.mark.asyncio
async def test_iplace_resolves_a_verified_model_to_its_product_url() -> None:
    spider = _iplace_spider("iphone_17_pro_max")

    request = await _first_start_request(spider)

    assert request.url == "https://www.iplace.com.br/apple-iphone-17-pro-max/100544PR"
    assert request.callback == spider.parse_product


@pytest.mark.asyncio
async def test_iplace_rejects_a_model_with_no_verified_product_page() -> None:
    # iPlace is an Apple-only reseller (no Android) and, at the time this
    # mapping was verified, had no iphone_18_pro entry in productSitemap.xml
    # yet — both are reasons a model can be legitimately unmapped, not a bug.
    spider = _iplace_spider("galaxy_s26_ultra")

    with pytest.raises(ValueError, match="no verified product page"):
        await _first_start_request(spider)


def test_iplace_extraction_failure_escalates_to_browser() -> None:
    spider = _iplace_spider()

    fallback = list(spider.parse_product(_iplace_response(with_jsonld=False)))

    assert len(fallback) == 1
    assert fallback[0].meta["playwright"] is True
    assert fallback[0].callback == spider.parse_browser_product
    # Pin the restricted allowlist as a regression-detectable invariant: the
    # dozens of third-party trackers this page loads in a real browser must
    # stay unreachable from our fallback.
    assert fallback[0].meta["browser_allowed_hosts"] == ("www.iplace.com.br",)


def test_iplace_http_success_does_not_schedule_browser() -> None:
    spider = _iplace_spider()

    result = list(spider.parse_product(_iplace_response(with_jsonld=True)))

    assert len(result) == 1
    assert result[0]["extractor_name"] == "iplace_product_jsonld"
    assert result[0]["price_amount"] == 8829


@pytest.mark.parametrize("status", [401, 403, 429])
def test_iplace_blocked_status_does_not_escalate_to_browser(status: int) -> None:
    spider = _iplace_spider()

    _assert_blocked_without_browser(
        list(spider.parse_product(_iplace_response(status=status))), status=status
    )


def test_iplace_browser_evidence_is_explicit_in_extractor_name() -> None:
    spider = _iplace_spider()

    result = list(spider.parse_browser_product(_iplace_response(with_jsonld=True)))

    assert result[0]["extractor_name"] == "iplace_product_jsonld_browser_fallback"
