"""API response contracts.

Separate from the internal domain/pricing dataclasses on purpose: the
wire format (money as a decimal string, not raw minor units) can stay
stable even if the internal representation changes.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from pricing_intel.domain.models import PaymentTerms, ShippingTerms
from pricing_intel.domain.money import Money
from pricing_intel.pricing.analysis import ComparisonResult


def _format_money(minor_units: int | None, currency: str) -> str | None:
    if minor_units is None:
        return None
    return str(Money(minor_units, currency).to_decimal())


class SourceResponse(BaseModel):
    id: UUID
    name: str
    base_url: str
    kind: str
    status: str


class RunResponse(BaseModel):
    id: UUID
    source_id: UUID
    trigger: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    stats: dict[str, int]
    failure_reason: str | None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    brand: str
    category: str


class VariantResponse(BaseModel):
    id: UUID
    product_id: UUID
    attributes: dict[str, str]
    gtin: str | None


class OfferSnapshotResponse(BaseModel):
    offer_id: UUID
    source_name: str
    seller_name: str
    url: str
    price: str
    currency: str
    condition: str
    availability: str
    observed_at: datetime
    payment_terms: PaymentTerms
    shipping: ShippingTerms


class ExcludedOfferResponse(BaseModel):
    offer_id: UUID
    source_name: str
    seller_name: str
    reason: str


class ComparisonResponse(BaseModel):
    variant_id: UUID
    currency: str
    has_comparable_data: bool
    included_offer_count: int
    source_count: int
    min_price: str | None
    median_price: str | None
    max_price: str | None
    offers: list[OfferSnapshotResponse]
    excluded: list[ExcludedOfferResponse]
    oldest_observation_at: datetime | None
    newest_observation_at: datetime | None
    generated_at: datetime

    @classmethod
    def from_result(cls, result: ComparisonResult, *, generated_at: datetime) -> ComparisonResponse:
        return cls(
            variant_id=result.variant_id,
            currency=result.currency,
            has_comparable_data=result.has_comparable_data,
            included_offer_count=result.included_offer_count,
            source_count=result.source_count,
            min_price=_format_money(result.min_price_minor_units, result.currency),
            median_price=_format_money(result.median_price_minor_units, result.currency),
            max_price=_format_money(result.max_price_minor_units, result.currency),
            offers=[
                OfferSnapshotResponse(
                    offer_id=snap.offer_id,
                    source_name=snap.source_name,
                    seller_name=snap.seller_name,
                    url=snap.url,
                    price=_format_money(snap.price_minor_units, snap.currency) or "0.00",
                    currency=snap.currency,
                    condition=snap.condition.value,
                    availability=snap.availability.value,
                    observed_at=snap.observed_at,
                    payment_terms=snap.payment_terms,
                    shipping=snap.shipping,
                )
                for snap in result.included
            ],
            excluded=[
                ExcludedOfferResponse(
                    offer_id=exc.offer_id,
                    source_name=exc.source_name,
                    seller_name=exc.seller_name,
                    reason=exc.reason,
                )
                for exc in result.excluded
            ],
            oldest_observation_at=result.oldest_observation_at,
            newest_observation_at=result.newest_observation_at,
            generated_at=generated_at,
        )
