"""Synchronous data access for the Scrapy pipeline.

Scrapy's pipeline hooks are sync, and the spider process runs in its own
Twisted reactor isolated from the FastAPI/Procrastinate asyncio loop
(see collection/runner.py) — so this deliberately does NOT reuse the
async pool in db/pool.py. It shares the same SQL text from db/sql.py.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from pricing_intel.config import get_settings
from pricing_intel.db import sql
from pricing_intel.domain.enums import Availability, Condition, EvidenceType, MatchMethod
from pricing_intel.domain.models import (
    DiscoveredPage,
    Evidence,
    Offer,
    PaymentTerms,
    PriceObservation,
    Seller,
    ShippingTerms,
    Variant,
)


class SyncDb:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    @classmethod
    def connect(cls) -> SyncDb:
        return cls(psycopg.connect(get_settings().database_url))

    def close(self) -> None:
        self._conn.close()

    def upsert_discovered_page(
        self,
        *,
        source_id: UUID,
        url: str,
        canonical_url: str,
        page_type: str,
        status: str = "pending",
    ) -> DiscoveredPage:
        with self._conn.cursor(row_factory=class_row(DiscoveredPage)) as cur:
            cur.execute(
                sql.UPSERT_DISCOVERED_PAGE,
                {
                    "source_id": source_id,
                    "url": url,
                    "canonical_url": canonical_url,
                    "page_type": page_type,
                    "status": status,
                },
            )
            page = cur.fetchone()
        self._conn.commit()
        assert page is not None
        return page

    def mark_page_status(self, page_id: UUID, status: str) -> None:
        self._conn.execute(sql.MARK_PAGE_STATUS, {"page_id": page_id, "status": status})
        self._conn.commit()

    def get_or_create_seller(
        self, *, source_id: UUID, external_id: str, display_name: str
    ) -> Seller:
        with self._conn.cursor(row_factory=class_row(Seller)) as cur:
            cur.execute(
                sql.GET_OR_CREATE_SELLER,
                {
                    "source_id": source_id,
                    "external_id": external_id,
                    "display_name": display_name,
                },
            )
            seller = cur.fetchone()
        self._conn.commit()
        assert seller is not None
        return seller

    def find_variant_by_gtin(self, gtin: str) -> Variant | None:
        with self._conn.cursor(row_factory=class_row(Variant)) as cur:
            cur.execute(sql.FIND_VARIANT_BY_GTIN, {"gtin": gtin})
            return cur.fetchone()

    def find_variant_by_signature(self, signature: str) -> Variant | None:
        with self._conn.cursor(row_factory=class_row(Variant)) as cur:
            cur.execute(sql.FIND_VARIANT_BY_SIGNATURE, {"signature": signature})
            return cur.fetchone()

    def upsert_offer(
        self,
        *,
        source_id: UUID,
        seller_id: UUID,
        external_listing_id: str,
        url: str,
        raw_title: str,
    ) -> Offer:
        with self._conn.cursor(row_factory=class_row(Offer)) as cur:
            cur.execute(
                sql.UPSERT_OFFER,
                {
                    "source_id": source_id,
                    "seller_id": seller_id,
                    "external_listing_id": external_listing_id,
                    "url": url,
                    "raw_title": raw_title,
                },
            )
            offer = cur.fetchone()
        self._conn.commit()
        assert offer is not None
        return offer

    def set_offer_match(
        self,
        *,
        offer_id: UUID,
        variant_id: UUID,
        confidence: Decimal,
        method: MatchMethod,
        rationale: str,
    ) -> None:
        self._conn.execute(sql.DEACTIVATE_ACTIVE_MATCHES, {"offer_id": offer_id})
        self._conn.execute(
            sql.INSERT_OFFER_MATCH,
            {
                "offer_id": offer_id,
                "variant_id": variant_id,
                "confidence": confidence,
                "method": method.value,
                "rationale": rationale,
            },
        )
        self._conn.commit()

    def record_price_observation(
        self,
        *,
        offer_id: UUID,
        collection_run_id: UUID,
        observed_at: datetime,
        price_minor_units: int,
        currency: str,
        availability: Availability,
        condition: Condition,
        payment_terms: PaymentTerms,
        shipping: ShippingTerms,
    ) -> PriceObservation | None:
        with self._conn.cursor(row_factory=class_row(PriceObservation)) as cur:
            cur.execute(
                sql.INSERT_PRICE_OBSERVATION,
                {
                    "offer_id": offer_id,
                    "collection_run_id": collection_run_id,
                    "observed_at": observed_at,
                    "price_minor_units": price_minor_units,
                    "currency": currency,
                    "availability": availability.value,
                    "condition": condition.value,
                    "payment_terms": Jsonb(payment_terms.model_dump(mode="json")),
                    "shipping": Jsonb(shipping.model_dump(mode="json")),
                },
            )
            observation = cur.fetchone()
        if observation is not None:
            self._conn.execute(
                sql.UPDATE_OFFER_PRICE_SUMMARY,
                {
                    "offer_id": offer_id,
                    "observed_at": observed_at,
                    "price_minor_units": price_minor_units,
                    "currency": currency,
                },
            )
        self._conn.commit()
        return observation

    def record_evidence(
        self,
        *,
        collection_run_id: UUID,
        source_id: UUID,
        offer_id: UUID | None,
        evidence_type: EvidenceType,
        url: str,
        http_status: int | None,
        extractor_name: str,
        extractor_version: str,
        content_hash: str,
        raw_excerpt: str,
        fetched_at: datetime,
    ) -> Evidence:
        with self._conn.cursor(row_factory=class_row(Evidence)) as cur:
            cur.execute(
                sql.INSERT_EVIDENCE,
                {
                    "collection_run_id": collection_run_id,
                    "source_id": source_id,
                    "offer_id": offer_id,
                    "evidence_type": evidence_type.value,
                    "url": url,
                    "http_status": http_status,
                    "extractor_name": extractor_name,
                    "extractor_version": extractor_version,
                    "content_hash": content_hash,
                    "raw_excerpt": raw_excerpt,
                    "fetched_at": fetched_at,
                },
            )
            evidence = cur.fetchone()
            assert evidence is not None
        self._conn.execute(
            sql.PRUNE_EVIDENCE,
            {
                "source_id": source_id,
                "url": url,
                "keep": get_settings().evidence_retention_per_url,
            },
        )
        self._conn.commit()
        return evidence
