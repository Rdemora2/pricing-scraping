"""Shared crawl/extraction flow for the simulated lab sources.

JSON-LD extraction is standards-based and source-agnostic, so it lives
once in collection/extraction.py. What legitimately differs per source
is markup (CSS selectors) and the entry URL — that is what a subclass
overrides, which is the actual shape of an "adapter per source".
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

import scrapy

from pricing_intel.collection.extraction import (
    ExtractionError,
    extract_listing,
    find_product_json_ld,
)
from pricing_intel.collection.items import DiscoveredPageItem, ListingItem
from pricing_intel.discovery.urls import canonicalize


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


class LabStoreSpider(scrapy.Spider):
    product_link_css: str
    next_page_css: str

    def __init__(self, source_id: str | None = None, run_id: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not source_id or not run_id:
            raise ValueError(f"{self.name} requires -a source_id=... -a run_id=...")
        self.source_id = source_id
        self.run_id = run_id

    def parse_category(self, response: scrapy.http.Response):
        yield DiscoveredPageItem(
            source_id=self.source_id,
            url=response.url,
            canonical_url=canonicalize(response.url),
            page_type="category",
        )

        for href in response.css(self.product_link_css).getall():
            product_url = urljoin(response.url, href)
            yield DiscoveredPageItem(
                source_id=self.source_id,
                url=product_url,
                canonical_url=canonicalize(product_url),
                page_type="product",
            )
            yield response.follow(product_url, callback=self.parse_product)

        next_href = response.css(self.next_page_css).get()
        if next_href:
            yield response.follow(next_href, callback=self.parse_category)

    def parse_product(self, response: scrapy.http.Response):
        try:
            product = find_product_json_ld(response.text)
            listing = extract_listing(product)
        except ExtractionError:
            self.logger.error("failed to extract a listing from %s", response.url)
            return

        yield ListingItem(
            source_id=self.source_id,
            run_id=self.run_id,
            url=response.url,
            canonical_url=canonicalize(response.url),
            http_status=response.status,
            raw_html=response.text,
            external_listing_id=response.url.rstrip("/").rsplit("/", 1)[-1],
            seller_external_id=_slugify(listing.seller_display_name),
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
