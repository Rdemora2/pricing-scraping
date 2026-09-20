from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from pricing_intel.db import sql
from pricing_intel.db.pool import connection
from pricing_intel.domain.enums import Availability, Condition, MatchMethod
from pricing_intel.domain.models import (
    Offer,
    OfferMatch,
    PaymentTerms,
    PriceObservation,
    ShippingTerms,
    VariantOfferSnapshot,
)


async def upsert_offer(
    *,
    source_id: UUID,
    seller_id: UUID,
    external_listing_id: str,
    url: str,
    raw_title: str,
) -> Offer:
    async with connection() as conn, conn.cursor(row_factory=class_row(Offer)) as cur:
        await cur.execute(
            sql.UPSERT_OFFER,
            {
                "source_id": source_id,
                "seller_id": seller_id,
                "external_listing_id": external_listing_id,
                "url": url,
                "raw_title": raw_title,
            },
        )
        offer = await cur.fetchone()
        assert offer is not None
        return offer


async def get_offer(offer_id: UUID) -> Offer | None:
    async with connection() as conn, conn.cursor(row_factory=class_row(Offer)) as cur:
        await cur.execute(sql.GET_OFFER, {"offer_id": offer_id})
        return await cur.fetchone()


async def record_price_observation(
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
    """Returns None when this (offer, run) pair was already recorded —
    replaying a run must not duplicate its effect."""
    async with connection() as conn:
        async with conn.cursor(row_factory=class_row(PriceObservation)) as cur:
            await cur.execute(
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
            observation = await cur.fetchone()
        if observation is not None:
            await conn.execute(
                sql.UPDATE_OFFER_PRICE_SUMMARY,
                {
                    "offer_id": offer_id,
                    "observed_at": observed_at,
                    "price_minor_units": price_minor_units,
                    "currency": currency,
                },
            )
        return observation


async def set_offer_match(
    *,
    offer_id: UUID,
    variant_id: UUID,
    confidence: Decimal,
    method: MatchMethod,
    rationale: str,
) -> OfferMatch:
    """Supersedes any active match for this offer (kept, not deleted, for audit)."""
    async with connection() as conn:
        await conn.execute(sql.DEACTIVATE_ACTIVE_MATCHES, {"offer_id": offer_id})
        async with conn.cursor(row_factory=class_row(OfferMatch)) as cur:
            await cur.execute(
                sql.INSERT_OFFER_MATCH,
                {
                    "offer_id": offer_id,
                    "variant_id": variant_id,
                    "confidence": confidence,
                    "method": method.value,
                    "rationale": rationale,
                },
            )
            match = await cur.fetchone()
            assert match is not None
            return match


async def get_active_match(offer_id: UUID) -> OfferMatch | None:
    async with connection() as conn, conn.cursor(row_factory=class_row(OfferMatch)) as cur:
        await cur.execute(sql.GET_ACTIVE_MATCH, {"offer_id": offer_id})
        return await cur.fetchone()


async def list_latest_snapshots_for_variant(variant_id: UUID) -> list[VariantOfferSnapshot]:
    async with (
        connection() as conn,
        conn.cursor(row_factory=class_row(VariantOfferSnapshot)) as cur,
    ):
        await cur.execute(sql.LATEST_OBSERVATION_SNAPSHOTS_FOR_VARIANT, {"variant_id": variant_id})
        return await cur.fetchall()


async def count_sources_for_variant(variant_id: UUID) -> int:
    async with connection() as conn, conn.cursor() as cur:
        await cur.execute(sql.COUNT_SOURCES_FOR_VARIANT, {"variant_id": variant_id})
        row = await cur.fetchone()
        assert row is not None
        return row[0]
