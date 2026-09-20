"""Item pipeline: validates and persists what the spiders scrape.

One pipeline handles both item types on purpose — discovery bookkeeping
and listing extraction share the same Postgres connection and the same
collection run, and splitting them into separate pipeline classes would
only add indirection without decoupling anything real.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from itemadapter import ItemAdapter

from pricing_intel.collection.db import SyncDb
from pricing_intel.collection.items import DiscoveredPageItem, ListingItem
from pricing_intel.domain.enums import DiscoveredPageStatus, EvidenceType
from pricing_intel.domain.money import Money
from pricing_intel.matching.service import decide_match
from pricing_intel.matching.signature import compute_signature

EXTRACTOR_NAME = "jsonld_schema_org_product"
EXTRACTOR_VERSION = "1.0.0"


class PostgresPipeline:
    def open_spider(self, spider):
        self.db = SyncDb.connect()

    def close_spider(self, spider):
        self.db.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if isinstance(item, DiscoveredPageItem):
            self._handle_discovered_page(adapter)
        elif isinstance(item, ListingItem):
            self._handle_listing(adapter, spider)
        return item

    def _handle_discovered_page(self, adapter: ItemAdapter) -> None:
        self.db.upsert_discovered_page(
            source_id=adapter["source_id"],
            url=adapter["url"],
            canonical_url=adapter["canonical_url"],
            page_type=adapter["page_type"],
        )

    def _handle_listing(self, adapter: ItemAdapter, spider) -> None:
        source_id = adapter["source_id"]
        run_id = adapter["run_id"]
        url = adapter["url"]
        raw_html: str = adapter["raw_html"]
        content_hash = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)

        seller = self.db.get_or_create_seller(
            source_id=source_id,
            external_id=adapter["seller_external_id"],
            display_name=adapter["seller_display_name"],
        )
        offer = self.db.upsert_offer(
            source_id=source_id,
            seller_id=seller.id,
            external_listing_id=adapter["external_listing_id"],
            url=url,
            raw_title=adapter["raw_title"],
        )

        self._match_offer(adapter, offer_id=offer.id, spider=spider, url=url)

        money = Money.from_decimal(adapter["price_amount"], adapter["currency"])
        self.db.record_price_observation(
            offer_id=offer.id,
            collection_run_id=run_id,
            observed_at=now,
            price_minor_units=money.minor_units,
            currency=money.currency,
            availability=adapter["availability"],
            condition=adapter["condition"],
            payment_terms=adapter["payment_terms"],
            shipping=adapter["shipping"],
        )

        self.db.record_evidence(
            collection_run_id=run_id,
            source_id=source_id,
            offer_id=offer.id,
            evidence_type=EvidenceType.LISTING_PAGE,
            url=url,
            http_status=adapter.get("http_status"),
            extractor_name=EXTRACTOR_NAME,
            extractor_version=EXTRACTOR_VERSION,
            content_hash=content_hash,
            raw_excerpt=raw_html[:5000],
            fetched_at=now,
        )

        page = self.db.upsert_discovered_page(
            source_id=source_id,
            url=url,
            canonical_url=adapter["canonical_url"],
            page_type="product",
        )
        self.db.mark_page_status(page.id, DiscoveredPageStatus.COLLECTED.value)

    def _match_offer(self, adapter: ItemAdapter, *, offer_id, spider, url: str) -> None:
        gtin = adapter.get("gtin")
        attributes = adapter["attributes"]
        signature = compute_signature(attributes)
        decision = decide_match(
            gtin=gtin,
            attributes=attributes,
            variant_by_gtin=self.db.find_variant_by_gtin(gtin) if gtin else None,
            variant_by_signature=self.db.find_variant_by_signature(signature),
        )
        if decision is None:
            spider.logger.warning("offer %s at %s did not match any known variant", offer_id, url)
            return
        self.db.set_offer_match(
            offer_id=offer_id,
            variant_id=decision.variant_id,
            confidence=decision.confidence,
            method=decision.method,
            rationale=decision.rationale,
        )
