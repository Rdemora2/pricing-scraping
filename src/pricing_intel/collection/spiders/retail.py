"""Reviewed, single-page retailer adapters.

These spiders consume public Product JSON-LD with conservative limits.  They
do not log in, solve challenges or retry around access controls.
"""

from __future__ import annotations

from urllib.parse import urljoin

import scrapy

from pricing_intel.collection.extraction import ExtractionError
from pricing_intel.collection.items import ListingItem
from pricing_intel.collection.network_policy import validate_reference_url
from pricing_intel.collection.real_sources import (
    BuscapeOfferParser,
    RetailListing,
    TwoAFinderMarkdownParser,
    extract_fast_shop_listing,
    extract_iplace_listings,
    extract_kabum_listing,
    extract_samsung_shop_listings,
    extract_zoom_listings,
)
from pricing_intel.discovery.urls import canonicalize


class _RetailSpider(scrapy.Spider):
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 2}  # noqa: RUF012 - Scrapy class contract
    allowed_domains: tuple[str, ...] = ()
    extractor_name: str
    extractor_version = "1.0.0"

    def __init__(
        self,
        source_id: str | None = None,
        run_id: str | None = None,
        base_url: str | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if not source_id or not run_id or not base_url:
            raise ValueError(f"{self.name} requires source_id, run_id and base_url")
        self.source_id = source_id
        self.run_id = run_id
        self.base_url = base_url

    async def start(self):
        yield scrapy.Request(self.base_url, callback=self.parse_product)

    def parse_product(self, response: scrapy.http.Response):
        raise NotImplementedError

    def listing_item(self, response: scrapy.http.Response, listing: RetailListing) -> ListingItem:
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
            extractor_name=self.extractor_name,
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
    name = "iplace"
    allowed_domains = ("www.iplace.com.br",)
    extractor_name = "iplace_product_jsonld"

    def parse_product(self, response: scrapy.http.Response):
        try:
            listings = extract_iplace_listings(response.text, response.url)
        except ExtractionError as exc:
            self.logger.error("iPlace extraction failed: %s", exc)
            return
        for listing in listings:
            yield self.listing_item(response, listing)


class FastShopSpider(_RetailSpider):
    name = "fast_shop"
    allowed_domains = ("site.fastshop.com.br",)
    extractor_name = "fast_shop_product_jsonld"

    def parse_product(self, response: scrapy.http.Response):
        try:
            listing = extract_fast_shop_listing(response.text, response.url)
        except ExtractionError as exc:
            self.logger.error("Fast Shop extraction failed: %s", exc)
            return
        yield self.listing_item(response, listing)


class KabumSpider(_RetailSpider):
    name = "kabum"
    allowed_domains = ("www.kabum.com.br",)
    extractor_name = "kabum_product_jsonld"

    def parse_product(self, response: scrapy.http.Response):
        try:
            listing = extract_kabum_listing(response.text, response.url)
        except ExtractionError as exc:
            self.logger.error("KaBuM! extraction failed: %s", exc)
            return
        yield self.listing_item(response, listing)


class SamsungShopSpider(_RetailSpider):
    name = "samsung_shop"
    allowed_domains = ("shop.samsung.com",)
    extractor_name = "samsung_shop_product_group_jsonld"

    def parse_product(self, response: scrapy.http.Response):
        try:
            listings = extract_samsung_shop_listings(response.text, response.url)
        except ExtractionError as exc:
            self.logger.error("Samsung Shop extraction failed: %s", exc)
            return
        for listing in listings:
            yield self.listing_item(response, listing)


class ZoomSpider(_RetailSpider):
    name = "zoom"
    allowed_domains = ("www.zoom.com.br",)
    extractor_name = "zoom_aggregate_offer_jsonld"

    def parse_product(self, response: scrapy.http.Response):
        try:
            listings = extract_zoom_listings(response.text, response.url)
        except ExtractionError as exc:
            self.logger.error("Zoom extraction failed: %s", exc)
            return
        for listing in listings:
            yield self.listing_item(response, listing)


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
            return
        for listing in listings:
            yield self.listing_item(response, listing)


class BuscapeSpider(_RetailSpider):
    name = "buscape"
    # Product page + public offer document, plus one robots.txt fetch per host.
    custom_settings = {"CLOSESPIDER_PAGECOUNT": 5}  # noqa: RUF012 - Scrapy contract
    allowed_domains = ("www.buscape.com.br", "api-v1.zoom.com.br")
    extractor_name = "buscape_public_product_offers"
    extractor_version = "1.0.0"
    parser = BuscapeOfferParser()

    def parse_product(self, response: scrapy.http.Response):
        try:
            product_id = self.parser.product_id(response.text)
        except ExtractionError as exc:
            self.logger.error("Buscapé product id extraction failed: %s", exc)
            return
        api_url = (
            f"https://api-v1.zoom.com.br/sale-condition/v1/product/{product_id}"
            "?order=DEFAULT&page=1&pageSize=20&resolution=LARGE&affiliateId=1&brand=buscape"
        )
        yield scrapy.Request(
            api_url,
            callback=self.parse_offers,
            cb_kwargs={"evidence_url": response.url},
        )

    def parse_offers(self, response: scrapy.http.Response, *, evidence_url: str):
        try:
            listings = self.parser.parse(response.text, evidence_url)
        except ExtractionError as exc:
            self.logger.error("Buscapé offer extraction failed: %s", exc)
            return
        for listing in listings:
            yield self.listing_item(response, listing)
