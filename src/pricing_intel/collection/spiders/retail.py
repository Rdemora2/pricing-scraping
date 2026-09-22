"""Reviewed, single-page retailer adapters.

These spiders consume public Product JSON-LD with conservative limits.  They
do not log in, solve challenges or retry around access controls.
"""

from __future__ import annotations

import gzip
import re
import socket
from urllib.parse import quote, quote_plus, urljoin, urlsplit

import scrapy
from scrapy_playwright.page import PageMethod

from pricing_intel.collection.browser import browser_request_meta
from pricing_intel.collection.extraction import ExtractionError
from pricing_intel.collection.items import ListingItem, ListingRejectedItem
from pricing_intel.collection.network_policy import Resolver, validate_reference_url
from pricing_intel.collection.real_sources import (
    BUSCAPE_MAX_OFFER_PAGES,
    BUSCAPE_OFFER_PAGE_SIZE,
    SITEMAP_MAX_DOCUMENTS,
    BuscapeOfferParser,
    RetailListing,
    SkipLog,
    TwoAFinderMarkdownParser,
    extract_amazon_listing,
    extract_americanas_listing,
    extract_carrefour_listing,
    extract_fast_shop_listing,
    extract_iplace_listings,
    extract_kabum_listing,
    extract_product_search_urls,
    extract_samsung_shop_listings,
    extract_sitemap_locations,
    extract_zoom_listings,
    is_sitemap_index,
    select_sitemap_product_urls,
)
from pricing_intel.discovery.urls import canonicalize
from pricing_intel.domain.enums import RejectionStage


class _RetailSpider(scrapy.Spider):
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 2}  # noqa: RUF012 - Scrapy class contract
    allowed_domains: tuple[str, ...] = ()
    extractor_name: str
    extractor_version = "1.0.0"
    browser_fallback_enabled = False
    browser_allowed_domains: tuple[str, ...] = ()
    # Sitemap-driven discovery, for retailers whose robots.txt forbids the
    # search route while leaving product pages public.
    sitemap_paths: tuple[str, ...] = ()
    sitemap_index_markers: tuple[str, ...] = ()
    sitemap_product_markers: tuple[str, ...] = ("/produto/",)

    def __init__(
        self,
        source_id: str | None = None,
        run_id: str | None = None,
        base_url: str | None = None,
        product_name: str | None = None,
        product_model: str | None = None,
        storages: str | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if not source_id or not run_id or not base_url:
            raise ValueError(f"{self.name} requires source_id, run_id and base_url")
        self.source_id = source_id
        self.run_id = run_id
        self.base_url = base_url
        self.product_name = product_name
        self.product_model = product_model
        self.storages = tuple(item for item in (storages or "").split(",") if item)
        self.browser_resolver: Resolver = socket.getaddrinfo
        self._sitemap_seen: set[str] = set()

    async def start(self):
        yield scrapy.Request(self.base_url, callback=self.parse_product)

    def catalog_search_requests(self, callback):
        if not self.product_name or not self.product_model or not self.storages:
            raise ValueError(f"{self.name} requires a canonical product search context")
        for storage in self.storages:
            capacity = f"{int(storage) // 1024}TB" if int(storage) >= 1024 else f"{storage}GB"
            yield scrapy.Request(
                self.catalog_search_url(capacity),
                callback=callback,
                cb_kwargs={"storage_gb": storage},
            )

    def catalog_search_url(self, capacity: str) -> str:
        query = quote(f"{self.product_name} {capacity}".replace(" ", "+"), safe="")
        return urljoin(self.base_url, f"busca/{query}")

    def product_requests_from_search(
        self,
        response: scrapy.http.Response,
        *,
        storage_gb: str,
        product_path_markers: tuple[str, ...] = ("/celular/",),
    ):
        if any(marker in urlsplit(response.url).path for marker in product_path_markers):
            yield scrapy.Request(response.url, callback=self.parse_product, dont_filter=True)
            return
        urls = extract_product_search_urls(
            response.text,
            response.url,
            product_name=self.product_name or "",
            product_model=self.product_model or "",
            storage_gb=storage_gb,
            product_path_markers=product_path_markers,
        )
        for url in urls:
            validate_reference_url(url, allowed_hosts=self.allowed_domains)
            yield scrapy.Request(url, callback=self.parse_product)

    def browser_fallback_request(self, url: str) -> scrapy.Request:
        if not self.browser_fallback_enabled:
            raise RuntimeError(f"{self.name} does not support browser fallback")
        allowed_hosts = self.browser_allowed_domains or self.allowed_domains
        return scrapy.Request(
            url,
            callback=self.parse_browser_product,
            dont_filter=True,
            meta=browser_request_meta(
                allowed_hosts=allowed_hosts,
                resolver=self.browser_resolver,
            ),
        )

    def browser_search_request(
        self,
        response: scrapy.http.Response,
        *,
        callback,
        storage_gb: str,
        wait_selector: str,
    ) -> scrapy.Request:
        """Render one search page once when its HTTP body has no product links."""
        if not self.browser_fallback_enabled:
            raise RuntimeError(f"{self.name} does not support browser fallback")
        allowed_hosts = self.browser_allowed_domains or self.allowed_domains
        meta = browser_request_meta(
            allowed_hosts=allowed_hosts,
            resolver=self.browser_resolver,
        )
        meta["playwright_page_methods"] = [
            PageMethod("wait_for_selector", wait_selector, timeout=10_000)
        ]
        return scrapy.Request(
            response.url,
            callback=callback,
            cb_kwargs={"storage_gb": storage_gb},
            dont_filter=True,
            meta=meta,
        )

    def sitemap_requests(self):
        if not self.sitemap_paths:
            raise ValueError(f"{self.name} has no sitemap configured")
        if not self.product_name or not self.product_model or not self.storages:
            raise ValueError(f"{self.name} requires a canonical product search context")
        for path in self.sitemap_paths:
            url = urljoin(self.base_url, path)
            validate_reference_url(url, allowed_hosts=self.allowed_domains)
            yield scrapy.Request(url, callback=self.parse_sitemap, cb_kwargs={"depth": 0})

    @staticmethod
    def sitemap_document(response: scrapy.http.Response) -> str:
        """Read a sitemap body, transparently decompressing a ``.xml.gz`` one.

        Content-Encoding is already handled upstream; this covers the separate
        case of a sitemap that is itself a gzip file.
        """
        body = response.body
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        return body.decode("utf-8", errors="replace")

    def parse_sitemap(self, response: scrapy.http.Response, *, depth: int):
        if response.status != 200:
            yield self.refused_response(response, what=f"{self.name} sitemap")
            return
        try:
            document = self.sitemap_document(response)
        except (OSError, EOFError) as exc:
            self.logger.error("%s sitemap is not readable: %s", self.name, exc)
            yield self.rejection_item(url=response.url, reason=f"unreadable sitemap: {exc}")
            return

        host = self.allowed_domains[0]
        if is_sitemap_index(document):
            # One level of indirection only. A sitemap index pointing at
            # another index is not a shape this adapter follows blindly.
            if depth >= 1:
                self.logger.error("%s sitemap index nests deeper than expected", self.name)
                return
            yield from self._sitemap_index_requests(document, host=host, depth=depth)
            return

        for storage in self.storages:
            for url in select_sitemap_product_urls(
                document,
                product_name=self.product_name or "",
                product_model=self.product_model or "",
                storage_gb=storage,
                allowed_host=host,
                product_path_markers=self.sitemap_product_markers,
            ):
                if url in self._sitemap_seen:
                    continue
                self._sitemap_seen.add(url)
                validate_reference_url(url, allowed_hosts=self.allowed_domains)
                yield scrapy.Request(url, callback=self.parse_product)

    def _sitemap_index_requests(self, document: str, *, host: str, depth: int):
        followed = 0
        for location in extract_sitemap_locations(document, allowed_host=host):
            if self.sitemap_index_markers and not any(
                marker in location.casefold() for marker in self.sitemap_index_markers
            ):
                continue
            validate_reference_url(location, allowed_hosts=self.allowed_domains)
            yield scrapy.Request(
                location, callback=self.parse_sitemap, cb_kwargs={"depth": depth + 1}
            )
            followed += 1
            if followed >= SITEMAP_MAX_DOCUMENTS:
                return

    def rejection_item(
        self,
        *,
        url: str,
        reason: str,
        stage: RejectionStage = RejectionStage.EXTRACTION,
        raw_title: str = "",
        attributes: dict[str, str] | None = None,
    ) -> ListingRejectedItem:
        """Record something this run saw and did not turn into an offer.

        Every one of these is a retailer that will not reach a comparison.
        Persisting them separates "the source has nothing" from "we dropped
        it", which a log line inside a subprocess cannot answer.
        """
        return ListingRejectedItem(
            source_id=self.source_id,
            run_id=self.run_id,
            stage=stage,
            reason=reason,
            url=url,
            raw_title=raw_title,
            attributes=attributes or {},
        )

    def refused_response(self, response: scrapy.http.Response, *, what: str) -> ListingRejectedItem:
        self.logger.error("%s refused with HTTP %s", what, response.status)
        return self.rejection_item(
            url=response.url,
            reason=f"{what} refused with HTTP {response.status}",
            stage=RejectionStage.ACCESS,
        )

    def skipped_items(self, skips: SkipLog, *, url: str):
        """Turn per-entry extractor skips into persisted rejections."""
        for entry in skips.entries:
            yield self.rejection_item(url=url, reason=entry.reason, raw_title=entry.raw_title)

    def parse_product(self, response: scrapy.http.Response):
        raise NotImplementedError

    def parse_browser_product(self, response: scrapy.http.Response):
        raise NotImplementedError

    @staticmethod
    def response_text(response: scrapy.http.Response) -> str:
        try:
            return response.text
        except AttributeError as exc:
            raise ExtractionError("response body is not classified as text") from exc

    def listing_item(
        self,
        response: scrapy.http.Response,
        listing: RetailListing,
        *,
        browser_fallback: bool = False,
    ) -> ListingItem:
        url = urljoin(response.url, listing.url)
        validate_reference_url(url, allowed_hosts=self.allowed_domains)
        return ListingItem(
            source_id=self.source_id,
            run_id=self.run_id,
            url=url,
            canonical_url=canonicalize(url),
            # Keep the commercial reference separate from the exact document
            # whose body and hash are persisted as extraction evidence.
            evidence_url=response.url,
            evidence_canonical_url=canonicalize(response.url),
            http_status=response.status,
            raw_html=response.text,
            extractor_name=(
                f"{self.extractor_name}_browser_fallback"
                if browser_fallback
                else self.extractor_name
            ),
            extractor_version=self.extractor_version,
            external_listing_id=listing.external_listing_id,
            seller_external_id=listing.seller_external_id,
            seller_display_name=listing.seller_display_name,
            raw_title=listing.raw_title,
            gtin=listing.gtin,
            attributes=listing.attributes,
            price_amount=listing.price_amount,
            currency=listing.currency,
            availability=listing.availability,
            condition=listing.condition,
            payment_terms=listing.payment_terms,
            shipping=listing.shipping,
        )


class IPlaceSpider(_RetailSpider):
    """Apple-only reseller. iPlace does not carry Android devices.

    ``/searchresults/`` is disallowed by iPlace's robots.txt, so product
    pages are resolved from a slug verified against the site's own
    ``productSitemap.xml`` rather than searched. Only canonical models
    confirmed present in that sitemap are listed; an unlisted model raises
    instead of guessing a slug, mirroring ``SamsungShopSpider``.
    """

    name = "iplace"
    allowed_domains = ("www.iplace.com.br",)
    extractor_name = "iplace_product_jsonld"
    browser_fallback_enabled = True
    browser_allowed_domains = ("www.iplace.com.br",)
    # Every product page needs client-side rendering for both the visible
    # buy box and its Product JSON-LD, so this is the everyday path here,
    # not a rare fallback. It is still gated the same way as elsewhere: the
    # HTTP request must already have been allowed (2xx) with evidence found
    # insufficient before a browser request is issued.
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 4}  # noqa: RUF012 - Scrapy class contract

    _PRODUCT_SLUGS = {  # noqa: RUF012 - Scrapy class contract
        "iphone_16_plus": "apple-iphone-16-plus/100028PR",
        "iphone_16_pro": "apple-iphone-16-pro/100029PR",
        "iphone_16_pro_max": "apple-iphone-16-pro-max/100030PR",
        "iphone_17_pro": "apple-iphone-17-pro/100411PR",
        "iphone_17_pro_max": "apple-iphone-17-pro-max/100544PR",
        "iphone_air": "apple-iphone-air/100408PR",
    }

    async def start(self):
        if not self.product_model:
            raise ValueError(f"{self.name} requires a canonical product model")
        slug = self._PRODUCT_SLUGS.get(self.product_model)
        if slug is None:
            raise ValueError(
                f"{self.name} has no verified product page for model "
                f"{self.product_model!r}; add it to _PRODUCT_SLUGS only after "
                "confirming the slug in productSitemap.xml"
            )
        yield scrapy.Request(urljoin(self.base_url, slug), callback=self.parse_product)

    def parse_product(self, response: scrapy.http.Response):
        if response.status != 200:
            yield self.refused_response(response, what="iPlace product page")
            return
        skips = SkipLog()
        try:
            listings = extract_iplace_listings(
                self.response_text(response), response.url, skips=skips
            )
        except ExtractionError as exc:
            self.logger.warning("iPlace HTTP extraction failed; trying browser: %s", exc)
            yield self.browser_fallback_request(response.url)
            return
        for listing in listings:
            yield self.listing_item(response, listing)
        yield from self.skipped_items(skips, url=response.url)

    def parse_browser_product(self, response: scrapy.http.Response):
        if response.status != 200:
            yield self.refused_response(response, what="iPlace browser fallback")
            return
        skips = SkipLog()
        try:
            listings = extract_iplace_listings(
                self.response_text(response), response.url, skips=skips
            )
        except ExtractionError as exc:
            self.logger.error("iPlace browser fallback failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        for listing in listings:
            yield self.listing_item(response, listing, browser_fallback=True)
        yield from self.skipped_items(skips, url=response.url)


class AmazonSpider(_RetailSpider):
    name = "amazon"
    allowed_domains = ("www.amazon.com.br",)
    extractor_name = "amazon_visible_buy_box"
    browser_fallback_enabled = True
    browser_allowed_domains = (
        "www.amazon.com.br",
        "m.media-amazon.com",
        "images-na.ssl-images-amazon.com",
    )
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 40}  # noqa: RUF012 - Scrapy class contract

    def catalog_search_url(self, capacity: str) -> str:
        return urljoin(self.base_url, f"s?k={quote_plus(f'{self.product_name} {capacity}')}")

    async def start(self):
        for request in self.catalog_search_requests(self.parse_search):
            yield request

    def parse_search(self, response: scrapy.http.Response, *, storage_gb: str):
        if response.status != 200:
            yield self.refused_response(response, what="Amazon search")
            return
        try:
            self.response_text(response)
        except ExtractionError as exc:
            self.logger.error("Amazon search is not a readable HTML response: %s", exc)
            return
        requests = list(
            self.product_requests_from_search(
                response,
                storage_gb=storage_gb,
                product_path_markers=("/dp/",),
            )
        )
        if requests:
            yield from requests
        elif response.meta.get("playwright"):
            self.logger.error("Amazon rendered search returned no canonical products")
            yield self.rejection_item(
                url=response.url,
                reason="rendered search page exposed no canonical product link",
            )
        else:
            yield self.browser_search_request(
                response,
                callback=self.parse_search,
                storage_gb=storage_gb,
                wait_selector="a[href*='/dp/']",
            )

    def parse_product(self, response: scrapy.http.Response):
        if response.status != 200:
            yield self.refused_response(response, what="Amazon product page")
            return
        try:
            listing = extract_amazon_listing(self.response_text(response), response.url)
        except ExtractionError as exc:
            self.logger.warning("Amazon HTTP extraction failed; trying browser: %s", exc)
            yield self.browser_fallback_request(response.url)
            return
        yield self.listing_item(response, listing)

    def parse_browser_product(self, response: scrapy.http.Response):
        try:
            listing = extract_amazon_listing(self.response_text(response), response.url)
        except ExtractionError as exc:
            self.logger.error("Amazon browser fallback failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        yield self.listing_item(response, listing, browser_fallback=True)


class CarrefourSpider(_RetailSpider):
    name = "carrefour"
    allowed_domains = ("www.carrefour.com.br",)
    extractor_name = "carrefour_product_pix"
    browser_fallback_enabled = True
    browser_allowed_domains = ("www.carrefour.com.br", "carrefourbr.vtexassets.com")
    # One sitemap index, up to SITEMAP_MAX_DOCUMENTS product sitemaps, and up
    # to MAX_SEARCH_RESULTS_PER_CAPACITY product pages for each of four
    # capacities, plus browser fallbacks and robots.txt.
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 72}  # noqa: RUF012
    # Carrefour's robots.txt forbids /busca/, the route the device-driven
    # collector used, while leaving product pages public. Product URLs are
    # therefore resolved from the store's own published sitemap — the same
    # shape iPlace uses (INC-12), and a route the retailer publishes for
    # crawlers rather than one it declines to serve them.
    sitemap_paths = ("sitemap.xml",)
    sitemap_index_markers = ("product", "produto")
    # The same product path marker the search route already validated.
    sitemap_product_markers = ("/produto/",)

    async def start(self):
        for request in self.sitemap_requests():
            yield request

    def parse_product(self, response: scrapy.http.Response):
        if response.status != 200:
            yield self.refused_response(response, what="Carrefour product page")
            return
        try:
            listing = extract_carrefour_listing(self.response_text(response), response.url)
        except ExtractionError as exc:
            self.logger.warning("Carrefour HTTP extraction failed; trying browser: %s", exc)
            yield self.browser_fallback_request(response.url)
            return
        yield self.listing_item(response, listing)

    def parse_browser_product(self, response: scrapy.http.Response):
        try:
            listing = extract_carrefour_listing(self.response_text(response), response.url)
        except ExtractionError as exc:
            self.logger.error("Carrefour browser fallback failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        yield self.listing_item(response, listing, browser_fallback=True)


class AmericanasSpider(_RetailSpider):
    name = "americanas"
    allowed_domains = ("www.americanas.com.br",)
    extractor_name = "americanas_product_jsonld"
    browser_fallback_enabled = True
    browser_allowed_domains = ("www.americanas.com.br", "americanas.vtexassets.com")
    # Up to 4 storage searches (+ up to 4 rendered-search fallbacks) plus up
    # to MAX_SEARCH_RESULTS_PER_CAPACITY product pages per capacity.
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 56}  # noqa: RUF012

    def catalog_search_url(self, capacity: str) -> str:
        return urljoin(self.base_url, f"s?q={quote_plus(f'{self.product_name} {capacity}')}")

    async def start(self):
        for request in self.catalog_search_requests(self.parse_search):
            yield request

    def parse_search(self, response: scrapy.http.Response, *, storage_gb: str):
        if response.status != 200:
            yield self.refused_response(response, what="Americanas search")
            return
        try:
            self.response_text(response)
        except ExtractionError as exc:
            self.logger.error("Americanas search is not a readable HTML response: %s", exc)
            return
        requests = list(
            self.product_requests_from_search(
                response,
                storage_gb=storage_gb,
                product_path_markers=("/p",),
            )
        )
        if requests:
            yield from requests
        elif response.meta.get("playwright"):
            self.logger.error("Americanas rendered search returned no canonical products")
            yield self.rejection_item(
                url=response.url,
                reason="rendered search page exposed no canonical product link",
            )
        else:
            yield self.browser_search_request(
                response,
                callback=self.parse_search,
                storage_gb=storage_gb,
                wait_selector="a[href$='/p'], a[href*='/p?']",
            )

    def parse_product(self, response: scrapy.http.Response):
        if response.status != 200:
            yield self.refused_response(response, what="Americanas product page")
            return
        try:
            listing = extract_americanas_listing(self.response_text(response), response.url)
        except ExtractionError as exc:
            self.logger.warning("Americanas HTTP extraction failed; trying browser: %s", exc)
            yield self.browser_fallback_request(response.url)
            return
        yield self.listing_item(response, listing)

    def parse_browser_product(self, response: scrapy.http.Response):
        try:
            listing = extract_americanas_listing(self.response_text(response), response.url)
        except ExtractionError as exc:
            self.logger.error("Americanas browser fallback failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        yield self.listing_item(response, listing, browser_fallback=True)


class FastShopSpider(_RetailSpider):
    name = "fast_shop"
    allowed_domains = ("site.fastshop.com.br",)
    extractor_name = "fast_shop_product_jsonld"

    def parse_product(self, response: scrapy.http.Response):
        try:
            listing = extract_fast_shop_listing(response.text, response.url)
        except ExtractionError as exc:
            self.logger.error("Fast Shop extraction failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        yield self.listing_item(response, listing)


class KabumSpider(_RetailSpider):
    name = "kabum"
    allowed_domains = ("www.kabum.com.br",)
    extractor_name = "kabum_product_jsonld"
    # Four HTTP searches, up to four JS fallbacks and up to
    # MAX_SEARCH_RESULTS_PER_CAPACITY product pages per capacity.
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 48}  # noqa: RUF012
    browser_fallback_enabled = True
    browser_allowed_domains = ("www.kabum.com.br",)

    def catalog_search_url(self, capacity: str) -> str:
        query = re.sub(
            r"[^a-z0-9]+",
            "-",
            f"{self.product_name} {capacity}".casefold(),
        ).strip("-")
        return urljoin(self.base_url, f"busca/{query}")

    async def start(self):
        for request in self.catalog_search_requests(self.parse_search):
            yield request

    def parse_search(self, response: scrapy.http.Response, *, storage_gb: str):
        if response.status != 200:
            yield self.refused_response(response, what="KaBuM! search")
            return
        requests = list(
            self.product_requests_from_search(
                response,
                storage_gb=storage_gb,
                product_path_markers=("/produto/",),
            )
        )
        if requests:
            yield from requests
            return
        if response.meta.get("playwright"):
            self.logger.error("KaBuM! rendered search returned no canonical products")
            yield self.rejection_item(
                url=response.url,
                reason="rendered search page exposed no canonical product link",
            )
            return
        meta = browser_request_meta(
            allowed_hosts=self.browser_allowed_domains,
            resolver=self.browser_resolver,
        )
        meta["playwright_page_methods"] = [
            PageMethod("wait_for_selector", "a[href*='/produto/']", timeout=10_000)
        ]
        yield scrapy.Request(
            response.url,
            callback=self.parse_search,
            cb_kwargs={"storage_gb": storage_gb},
            dont_filter=True,
            meta=meta,
        )

    def parse_product(self, response: scrapy.http.Response):
        try:
            listing = extract_kabum_listing(response.text, response.url)
        except ExtractionError as exc:
            self.logger.error("KaBuM! extraction failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        yield self.listing_item(response, listing)


class SamsungShopSpider(_RetailSpider):
    name = "samsung_shop"
    allowed_domains = ("shop.samsung.com",)
    extractor_name = "samsung_shop_product_group_jsonld"
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 3}  # noqa: RUF012

    async def start(self):
        if not self.product_name or not self.product_model:
            raise ValueError(f"{self.name} requires a canonical product search context")
        if not self.product_model.startswith("galaxy_"):
            raise ValueError(f"{self.name} only resolves canonical Galaxy models")
        slug = self.product_model.replace("_plus", "-plus").replace("_", "-")
        yield scrapy.Request(
            urljoin(self.base_url, f"{slug}/p"),
            callback=self.parse_product,
        )

    def parse_product(self, response: scrapy.http.Response):
        skips = SkipLog()
        try:
            listings = extract_samsung_shop_listings(response.text, response.url, skips=skips)
        except ExtractionError as exc:
            self.logger.error("Samsung Shop extraction failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        for listing in listings:
            yield self.listing_item(response, listing)
        yield from self.skipped_items(skips, url=response.url)


class ZoomSpider(_RetailSpider):
    name = "zoom"
    allowed_domains = ("www.zoom.com.br",)
    extractor_name = "zoom_aggregate_offer_jsonld"
    # Four searches plus up to MAX_SEARCH_RESULTS_PER_CAPACITY product pages
    # (one per matched color) for each capacity.
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 40}  # noqa: RUF012

    async def start(self):
        for request in self.catalog_search_requests(self.parse_search):
            yield request

    def parse_search(self, response: scrapy.http.Response, *, storage_gb: str):
        yield from self.product_requests_from_search(response, storage_gb=storage_gb)

    def parse_product(self, response: scrapy.http.Response):
        skips = SkipLog()
        try:
            listings = extract_zoom_listings(response.text, response.url, skips=skips)
        except ExtractionError as exc:
            self.logger.error("Zoom extraction failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        for listing in listings:
            yield self.listing_item(response, listing)
        yield from self.skipped_items(skips, url=response.url)


class BondfaroSpider(_RetailSpider):
    name = "bondfaro"
    allowed_domains = ("www.bondfaro.com.br",)
    extractor_name = "bondfaro_aggregate_offer_jsonld"
    # Four searches plus up to MAX_SEARCH_RESULTS_PER_CAPACITY product pages
    # (one per matched color) for each capacity.
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 40}  # noqa: RUF012

    def catalog_search_url(self, capacity: str) -> str:
        query = quote_plus(f"{self.product_name} {capacity}")
        return urljoin(self.base_url, f"busca/{query}")

    async def start(self):
        for request in self.catalog_search_requests(self.parse_search):
            yield request

    def parse_search(self, response: scrapy.http.Response, *, storage_gb: str):
        yield from self.product_requests_from_search(response, storage_gb=storage_gb)

    def parse_product(self, response: scrapy.http.Response):
        skips = SkipLog()
        try:
            listings = extract_zoom_listings(response.text, response.url, skips=skips)
        except ExtractionError as exc:
            self.logger.error("Bondfaro extraction failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        for listing in listings:
            yield self.listing_item(response, listing)
        yield from self.skipped_items(skips, url=response.url)


class TwoAFinderSpider(_RetailSpider):
    name = "two_a_finder"
    allowed_domains = ("2afinder.com",)
    extractor_name = "two_a_finder_markdown_table"
    extractor_version = "1.0.0"
    parser = TwoAFinderMarkdownParser()

    def parse_product(self, response: scrapy.http.Response):
        try:
            listings = self.parser.parse(response.text, response.url)
        except ExtractionError as exc:
            self.logger.error("2aFinder extraction failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        for listing in listings:
            yield self.listing_item(response, listing)


class BuscapeSpider(_RetailSpider):
    name = "buscape"
    # Four searches, up to MAX_SEARCH_RESULTS_PER_CAPACITY product pages per
    # capacity (one per matched color), up to BUSCAPE_MAX_OFFER_PAGES offer
    # documents per product page, plus one robots.txt fetch per host:
    # 4 + 4*8 + 32*3 + 2 = 134. The headroom absorbs redirects.
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 160}  # noqa: RUF012 - Scrapy contract
    allowed_domains = ("www.buscape.com.br", "api-v1.zoom.com.br")
    extractor_name = "buscape_public_product_offers"
    extractor_version = "1.1.0"
    parser = BuscapeOfferParser()

    async def start(self):
        for request in self.catalog_search_requests(self.parse_search):
            yield request

    def parse_search(self, response: scrapy.http.Response, *, storage_gb: str):
        yield from self.product_requests_from_search(response, storage_gb=storage_gb)

    def offer_page_request(
        self, product_id: str, *, page: int, evidence_url: str
    ) -> scrapy.Request:
        api_url = (
            f"https://api-v1.zoom.com.br/sale-condition/v1/product/{product_id}"
            f"?order=DEFAULT&page={page}&pageSize={BUSCAPE_OFFER_PAGE_SIZE}"
            "&resolution=LARGE&affiliateId=1&brand=buscape"
        )
        return scrapy.Request(
            api_url,
            callback=self.parse_offers,
            cb_kwargs={
                "evidence_url": evidence_url,
                "product_id": product_id,
                "page": page,
            },
        )

    def parse_product(self, response: scrapy.http.Response):
        try:
            product_id = self.parser.product_id(response.text)
        except ExtractionError as exc:
            self.logger.error("Buscapé product id extraction failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        yield self.offer_page_request(product_id, page=1, evidence_url=response.url)

    def parse_offers(
        self,
        response: scrapy.http.Response,
        *,
        evidence_url: str,
        product_id: str | None = None,
        page: int = 1,
    ):
        """Emit one page of retailer offers and follow the next one when full.

        Only a full page can hide further retailers behind it, so a short page
        ends pagination. The ceiling stays a hard stop regardless.
        """
        skips = SkipLog()
        try:
            offer_page = self.parser.parse_page(response.text, evidence_url, skips=skips)
        except ExtractionError as exc:
            self.logger.error("Buscapé offer extraction failed: %s", exc)
            yield self.rejection_item(url=response.url, reason=str(exc))
            return
        if not offer_page.listings and page == 1:
            self.logger.error("Buscapé offer document has no canonical offers")
        for listing in offer_page.listings:
            yield self.listing_item(response, listing)
        yield from self.skipped_items(skips, url=evidence_url)
        if product_id and offer_page.is_full and page < BUSCAPE_MAX_OFFER_PAGES:
            yield self.offer_page_request(product_id, page=page + 1, evidence_url=evidence_url)
