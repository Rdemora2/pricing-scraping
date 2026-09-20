"""API response contracts.

Separate from the internal domain/pricing dataclasses on purpose: the
wire format (money as a decimal string, not raw minor units) can stay
stable even if the internal representation changes.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from pricing_intel.domain.models import PaymentTerms, ShippingTerms
from pricing_intel.domain.money import Money
from pricing_intel.pricing.analysis import ComparisonResult
from pricing_intel.pricing.intelligence import (
    ColorIntelligence,
    ProductIntelligence,
    StorageIntelligence,
    VariantIntelligence,
)


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
    adapter_name: str


class DiscoverySearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=160)

    @field_validator("query")
    @classmethod
    def query_must_have_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("query must contain at least three non-space characters")
        return value


class SourceCandidateResponse(BaseModel):
    id: UUID
    url: str
    domain: str
    title: str
    snippet: str
    provider: str
    query: str
    trust_tier: str
    status: str
    discovered_at: datetime


class ManualCandidateRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    title: str = Field(min_length=2, max_length=300)
    snippet: str = Field(default="", max_length=1000)


class VariantCreateRequest(BaseModel):
    attributes: dict[str, str]
    gtin: str | None = Field(default=None, min_length=8, max_length=14)

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, str]) -> dict[str, str]:
        if not 1 <= len(value) <= 12:
            raise ValueError("a variant must have between 1 and 12 attributes")
        normalized = {key.strip(): item.strip() for key, item in value.items()}
        if any(
            not key or not item or len(key) > 50 or len(item) > 100
            for key, item in normalized.items()
        ):
            raise ValueError("variant attributes must be non-empty and bounded")
        return normalized


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    brand: str = Field(min_length=1, max_length=100)
    category: str = Field(default="smartphone", min_length=2, max_length=100)
    variants: list[VariantCreateRequest] = Field(min_length=1, max_length=100)


class ProductDetailResponse(BaseModel):
    product: ProductResponse
    variants: list[VariantResponse]


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
    retailer_count: int
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
            retailer_count=result.retailer_count,
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


class VariantIntelligenceResponse(BaseModel):
    variant_id: UUID
    storage_gb: int
    color: str
    min_price: str
    median_price: str
    max_price: str
    offer_count: int
    retailer_count: int

    @classmethod
    def from_result(
        cls, result: VariantIntelligence, *, currency: str
    ) -> VariantIntelligenceResponse:
        return cls(
            variant_id=result.variant_id,
            storage_gb=result.storage_gb,
            color=result.color,
            min_price=_format_money(result.min_price_minor_units, currency) or "0.00",
            median_price=_format_money(result.median_price_minor_units, currency) or "0.00",
            max_price=_format_money(result.max_price_minor_units, currency) or "0.00",
            offer_count=result.offer_count,
            retailer_count=result.retailer_count,
        )


class StorageIntelligenceResponse(BaseModel):
    storage_gb: int
    catalog_variant_count: int
    observed_variant_count: int
    min_price: str | None
    representative_price: str | None
    max_price: str | None
    price_per_gb: str | None

    @classmethod
    def from_result(
        cls, result: StorageIntelligence, *, currency: str
    ) -> StorageIntelligenceResponse:
        return cls(
            storage_gb=result.storage_gb,
            catalog_variant_count=result.catalog_variant_count,
            observed_variant_count=result.observed_variant_count,
            min_price=_format_money(result.min_price_minor_units, currency),
            representative_price=_format_money(result.representative_price_minor_units, currency),
            max_price=_format_money(result.max_price_minor_units, currency),
            price_per_gb=_format_money(result.price_per_gb_minor_units, currency),
        )


class ColorIntelligenceResponse(BaseModel):
    color: str
    catalog_variant_count: int
    observed_variant_count: int
    comparable_storage_count: int
    min_price: str | None
    representative_price: str | None
    max_price: str | None
    relative_price_delta_pct: str | None

    @classmethod
    def from_result(cls, result: ColorIntelligence, *, currency: str) -> ColorIntelligenceResponse:
        delta = (
            str((Decimal(result.relative_price_delta_bps) / Decimal(100)).quantize(Decimal("0.01")))
            if result.relative_price_delta_bps is not None
            else None
        )
        return cls(
            color=result.color,
            catalog_variant_count=result.catalog_variant_count,
            observed_variant_count=result.observed_variant_count,
            comparable_storage_count=result.comparable_storage_count,
            min_price=_format_money(result.min_price_minor_units, currency),
            representative_price=_format_money(result.representative_price_minor_units, currency),
            max_price=_format_money(result.max_price_minor_units, currency),
            relative_price_delta_pct=delta,
        )


class ProductIntelligenceResponse(BaseModel):
    product_id: UUID
    currency: str
    catalog_variant_count: int
    observed_variant_count: int
    coverage_pct: int
    total_offer_count: int
    retailer_count: int
    sample_status: str
    storages_gb: list[int]
    colors: list[str]
    min_price: str | None
    max_price: str | None
    cheapest_variant: VariantIntelligenceResponse | None
    most_expensive_variant: VariantIntelligenceResponse | None
    best_value_storage: StorageIntelligenceResponse | None
    cheapest_storage: StorageIntelligenceResponse | None
    most_expensive_storage: StorageIntelligenceResponse | None
    cheapest_color: ColorIntelligenceResponse | None
    most_expensive_color: ColorIntelligenceResponse | None
    storage_analysis: list[StorageIntelligenceResponse]
    color_analysis: list[ColorIntelligenceResponse]
    methodology: list[str]
    generated_at: datetime

    @classmethod
    def from_result(
        cls, result: ProductIntelligence, *, generated_at: datetime
    ) -> ProductIntelligenceResponse:
        currency = result.currency

        def variant(item: VariantIntelligence | None) -> VariantIntelligenceResponse | None:
            return (
                VariantIntelligenceResponse.from_result(item, currency=currency) if item else None
            )

        def storage(item: StorageIntelligence | None) -> StorageIntelligenceResponse | None:
            return (
                StorageIntelligenceResponse.from_result(item, currency=currency) if item else None
            )

        def color(item: ColorIntelligence | None) -> ColorIntelligenceResponse | None:
            return ColorIntelligenceResponse.from_result(item, currency=currency) if item else None

        return cls(
            product_id=result.product_id,
            currency=currency,
            catalog_variant_count=result.catalog_variant_count,
            observed_variant_count=result.observed_variant_count,
            coverage_pct=result.coverage_pct,
            total_offer_count=result.total_offer_count,
            retailer_count=result.retailer_count,
            sample_status=result.sample_status,
            storages_gb=list(result.storages_gb),
            colors=list(result.colors),
            min_price=_format_money(result.min_price_minor_units, currency),
            max_price=_format_money(result.max_price_minor_units, currency),
            cheapest_variant=variant(result.cheapest_variant),
            most_expensive_variant=variant(result.most_expensive_variant),
            best_value_storage=storage(result.best_value_storage),
            cheapest_storage=storage(result.cheapest_storage),
            most_expensive_storage=storage(result.most_expensive_storage),
            cheapest_color=color(result.cheapest_color),
            most_expensive_color=color(result.most_expensive_color),
            storage_analysis=[
                StorageIntelligenceResponse.from_result(item, currency=currency)
                for item in result.storage_analysis
            ],
            color_analysis=[
                ColorIntelligenceResponse.from_result(item, currency=currency)
                for item in result.color_analysis
            ],
            methodology=[
                "Cada variante compara somente ofertas novas, disponíveis e na mesma moeda.",
                "O preço representativo é a mediana das variantes observadas em cada grupo.",
                "O índice de cor mede o desvio contra a mediana das cores da mesma capacidade.",
                "Melhor custo-benefício exige duas cores por capacidade, duas capacidades e três varejistas.",
            ],
            generated_at=generated_at,
        )
