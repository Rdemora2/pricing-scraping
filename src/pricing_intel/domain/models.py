"""Read/write domain models.

These are boundary objects, not an ORM layer: the db/ package maps raw
rows to and from them by hand with explicit SQL (brief: "SQL explícito,
sem ORM mágico"). Validation here is what protects the rest of the
system from malformed scraped data.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pricing_intel.domain.enums import (
    Availability,
    Condition,
    DiscoveredPageStatus,
    EvidenceType,
    MatchMethod,
    PageType,
    PriceBasis,
    RunStatus,
    RunTrigger,
    SourceKind,
    SourceStatus,
)


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Source(_Model):
    id: UUID
    name: str
    base_url: str
    kind: SourceKind
    status: SourceStatus
    adapter_name: str
    created_at: datetime


class SourceCandidate(_Model):
    id: UUID
    url: str
    canonical_url: str
    domain: str
    title: str
    snippet: str
    provider: str
    query: str
    trust_tier: str
    status: str
    discovered_at: datetime


class DiscoveredPage(_Model):
    id: UUID
    source_id: UUID
    url: str
    canonical_url: str
    page_type: PageType
    status: DiscoveredPageStatus
    first_discovered_at: datetime
    last_seen_at: datetime


class CollectionRun(_Model):
    id: UUID
    source_id: UUID
    trigger: RunTrigger
    status: RunStatus
    idempotency_key: str
    started_at: datetime | None
    finished_at: datetime | None
    stats: dict[str, int]
    failure_reason: str | None
    created_at: datetime


class Evidence(_Model):
    id: UUID
    collection_run_id: UUID
    source_id: UUID
    offer_id: UUID | None
    evidence_type: EvidenceType
    url: str
    http_status: int | None
    extractor_name: str
    extractor_version: str
    content_hash: str
    raw_excerpt: str
    fetched_at: datetime


class Seller(_Model):
    id: UUID
    source_id: UUID
    external_id: str
    display_name: str


class Product(_Model):
    id: UUID
    name: str
    brand: str
    category: str
    created_at: datetime


class Variant(_Model):
    id: UUID
    product_id: UUID
    attributes: dict[str, str]
    attributes_signature: str
    gtin: str | None


class Offer(_Model):
    id: UUID
    source_id: UUID
    seller_id: UUID
    external_listing_id: str
    url: str
    raw_title: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_price_minor_units: int | None
    last_price_currency: str | None
    last_verified_at: datetime | None
    last_changed_at: datetime | None


class OfferMatch(_Model):
    id: UUID
    offer_id: UUID
    variant_id: UUID
    confidence: Decimal = Field(ge=0, le=1)
    method: MatchMethod
    rationale: str
    matched_at: datetime
    is_active: bool


class ShippingTerms(_Model):
    known: bool
    cost_minor_units: int | None = None
    cost_currency: str | None = None
    free_shipping_threshold_minor_units: int | None = None


class PaymentTerms(_Model):
    installment_count: int | None = None
    cash_discount_pct: Decimal | None = None
    coupon_code: str | None = None
    price_basis: PriceBasis = PriceBasis.ADVERTISED
    is_conditional: bool = False
    condition_summary: str | None = None


class VariantOfferSnapshot(_Model):
    """Latest known state of one offer matched to a variant.

    A read-model projection (source/seller names joined in), not a raw
    table row — this is what the pricing analysis layer filters and
    aggregates over.
    """

    offer_id: UUID
    source_name: str
    seller_name: str
    url: str
    condition: Condition
    availability: Availability
    price_minor_units: int
    currency: str
    observed_at: datetime
    payment_terms: PaymentTerms
    shipping: ShippingTerms


class PriceObservation(_Model):
    id: UUID
    offer_id: UUID
    collection_run_id: UUID
    observed_at: datetime
    price_minor_units: int
    currency: str
    availability: Availability
    condition: Condition
    payment_terms: PaymentTerms
    shipping: ShippingTerms
