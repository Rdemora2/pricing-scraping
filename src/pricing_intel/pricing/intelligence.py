"""Explainable market intelligence across every canonical variant of a product.

The module deliberately derives insights from exact-variant comparisons first.
That prevents a cheap 256 GB offer from being compared directly with a 1 TB
offer when estimating a colour premium or a storage representative price.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise
from uuid import UUID

from pricing_intel.domain.models import ProductVariantOfferSnapshot, Variant
from pricing_intel.pricing.analysis import compare_variant, retailer_identity


@dataclass(frozen=True, slots=True)
class VariantIntelligence:
    variant_id: UUID
    storage_gb: int
    color: str
    min_price_minor_units: int | None
    median_price_minor_units: int | None
    max_price_minor_units: int | None
    offer_count: int
    retailer_count: int


@dataclass(frozen=True, slots=True)
class StorageIntelligence:
    storage_gb: int
    catalog_variant_count: int
    observed_variant_count: int
    min_price_minor_units: int | None
    representative_price_minor_units: int | None
    max_price_minor_units: int | None


@dataclass(frozen=True, slots=True)
class StorageStepIntelligence:
    from_storage_gb: int
    to_storage_gb: int
    added_storage_gb: int
    from_price_minor_units: int
    to_price_minor_units: int
    price_delta_minor_units: int
    price_delta_bps: int


@dataclass(frozen=True, slots=True)
class ColorIntelligence:
    color: str
    catalog_variant_count: int
    observed_variant_count: int
    comparable_storage_count: int
    min_price_minor_units: int | None
    representative_price_minor_units: int | None
    max_price_minor_units: int | None
    relative_price_delta_bps: int | None


@dataclass(frozen=True, slots=True)
class ProductIntelligence:
    product_id: UUID
    currency: str
    catalog_variant_count: int
    observed_variant_count: int
    coverage_pct: int
    total_offer_count: int
    retailer_count: int
    sample_status: str
    storages_gb: tuple[int, ...]
    colors: tuple[str, ...]
    min_price_minor_units: int | None
    max_price_minor_units: int | None
    cheapest_variant: VariantIntelligence | None
    most_expensive_variant: VariantIntelligence | None
    entry_storage_step: StorageStepIntelligence | None
    cheapest_storage: StorageIntelligence | None
    most_expensive_storage: StorageIntelligence | None
    cheapest_color: ColorIntelligence | None
    most_expensive_color: ColorIntelligence | None
    storage_steps: tuple[StorageStepIntelligence, ...]
    storage_analysis: tuple[StorageIntelligence, ...]
    color_analysis: tuple[ColorIntelligence, ...]
    variant_analysis: tuple[VariantIntelligence, ...]


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    value = (Decimal(ordered[middle - 1]) + Decimal(ordered[middle])) / 2
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _mean_rounded(values: list[int]) -> int:
    value = sum((Decimal(item) for item in values), start=Decimal(0)) / len(values)
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _storage(attributes: dict[str, str]) -> int | None:
    raw_value = attributes.get("storage_gb")
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        return None
    return value if value > 0 else None


def _color(attributes: dict[str, str]) -> str | None:
    value = attributes.get("color", "").strip()
    return value or None


def _sample_status(*, observed: int, catalog: int, retailer_count: int) -> str:
    if observed == 0:
        return "no_data"
    if observed < 2 or retailer_count < 3:
        return "limited"
    coverage = observed / catalog if catalog else 0
    if coverage < 0.75 or retailer_count < 6:
        return "developing"
    return "strong"


def analyze_product(
    product_id: UUID,
    variants: list[Variant],
    snapshots: list[ProductVariantOfferSnapshot],
    *,
    reference_currency: str = "BRL",
    observed_after: datetime | None = None,
) -> ProductIntelligence:
    """Build model-level insights from exact, comparable variant populations."""

    canonical: list[tuple[Variant, int, str]] = []
    for variant in variants:
        storage = _storage(variant.attributes)
        color = _color(variant.attributes)
        if storage is not None and color is not None:
            canonical.append((variant, storage, color))

    snapshots_by_variant: dict[UUID, list[ProductVariantOfferSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        snapshots_by_variant[snapshot.variant_id].append(snapshot)

    variant_analysis: list[VariantIntelligence] = []
    retailer_keys: set[str] = set()
    retailer_keys_by_storage: dict[int, set[str]] = defaultdict(set)
    for variant, storage, color in canonical:
        result = compare_variant(
            variant.id,
            list(snapshots_by_variant.get(variant.id, [])),
            reference_currency=reference_currency,
            observed_after=observed_after,
        )
        variant_analysis.append(
            VariantIntelligence(
                variant_id=variant.id,
                storage_gb=storage,
                color=color,
                min_price_minor_units=result.min_price_minor_units,
                median_price_minor_units=result.median_price_minor_units,
                max_price_minor_units=result.max_price_minor_units,
                offer_count=result.included_offer_count,
                retailer_count=result.retailer_count,
            )
        )
        variant_retailer_keys = {retailer_identity(item.seller_name) for item in result.included}
        retailer_keys.update(variant_retailer_keys)
        retailer_keys_by_storage[storage].update(variant_retailer_keys)

    observed = [point for point in variant_analysis if point.median_price_minor_units is not None]

    storage_catalog_counts: dict[int, int] = defaultdict(int)
    color_catalog_counts: dict[str, int] = defaultdict(int)
    for _, storage, color in canonical:
        storage_catalog_counts[storage] += 1
        color_catalog_counts[color] += 1

    observed_by_storage: dict[int, list[VariantIntelligence]] = defaultdict(list)
    observed_by_color: dict[str, list[VariantIntelligence]] = defaultdict(list)
    for point in observed:
        observed_by_storage[point.storage_gb].append(point)
        observed_by_color[point.color].append(point)

    storage_analysis: list[StorageIntelligence] = []
    for storage in sorted(storage_catalog_counts):
        points = observed_by_storage.get(storage, [])
        representative = (
            _median(
                [
                    point.median_price_minor_units
                    for point in points
                    if point.median_price_minor_units is not None
                ]
            )
            if points
            else None
        )
        storage_analysis.append(
            StorageIntelligence(
                storage_gb=storage,
                catalog_variant_count=storage_catalog_counts[storage],
                observed_variant_count=len(points),
                min_price_minor_units=(
                    min(
                        point.min_price_minor_units
                        for point in points
                        if point.min_price_minor_units is not None
                    )
                    if points
                    else None
                ),
                representative_price_minor_units=representative,
                max_price_minor_units=(
                    max(
                        point.max_price_minor_units
                        for point in points
                        if point.max_price_minor_units is not None
                    )
                    if points
                    else None
                ),
            )
        )

    storage_baselines = {
        storage: _median(
            [
                point.median_price_minor_units
                for point in points
                if point.median_price_minor_units is not None
            ]
        )
        for storage, points in observed_by_storage.items()
        if len(points) >= 2
    }
    color_deltas: dict[str, list[int]] = defaultdict(list)
    for point in observed:
        baseline = storage_baselines.get(point.storage_gb)
        if baseline is None:
            continue
        assert point.median_price_minor_units is not None
        delta = (
            (Decimal(point.median_price_minor_units) - Decimal(baseline))
            / Decimal(baseline)
            * Decimal(10_000)
        )
        color_deltas[point.color].append(int(delta.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))

    color_analysis: list[ColorIntelligence] = []
    for color in sorted(color_catalog_counts):
        points = observed_by_color.get(color, [])
        deltas = color_deltas.get(color, [])
        color_analysis.append(
            ColorIntelligence(
                color=color,
                catalog_variant_count=color_catalog_counts[color],
                observed_variant_count=len(points),
                comparable_storage_count=len(deltas),
                min_price_minor_units=(
                    min(
                        point.min_price_minor_units
                        for point in points
                        if point.min_price_minor_units is not None
                    )
                    if points
                    else None
                ),
                representative_price_minor_units=(
                    _median(
                        [
                            point.median_price_minor_units
                            for point in points
                            if point.median_price_minor_units is not None
                        ]
                    )
                    if points
                    else None
                ),
                max_price_minor_units=(
                    max(
                        point.max_price_minor_units
                        for point in points
                        if point.max_price_minor_units is not None
                    )
                    if points
                    else None
                ),
                relative_price_delta_bps=_mean_rounded(deltas) if deltas else None,
            )
        )

    priced_storages = [
        item for item in storage_analysis if item.representative_price_minor_units is not None
    ]
    indexed_colors = [item for item in color_analysis if item.comparable_storage_count >= 2]
    catalog_count = len(canonical)
    observed_count = len(observed)
    storage_steps: list[StorageStepIntelligence] = []
    for previous, current in pairwise(storage_analysis):
        step_retailers = retailer_keys_by_storage[previous.storage_gb].union(
            retailer_keys_by_storage[current.storage_gb]
        )
        if (
            previous.observed_variant_count < 2
            or current.observed_variant_count < 2
            or len(step_retailers) < 3
        ):
            continue
        if (
            previous.representative_price_minor_units is None
            or current.representative_price_minor_units is None
        ):
            continue
        price_delta = (
            current.representative_price_minor_units - previous.representative_price_minor_units
        )
        price_delta_bps = int(
            (
                Decimal(price_delta)
                / Decimal(previous.representative_price_minor_units)
                * Decimal(10_000)
            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        storage_steps.append(
            StorageStepIntelligence(
                from_storage_gb=previous.storage_gb,
                to_storage_gb=current.storage_gb,
                added_storage_gb=current.storage_gb - previous.storage_gb,
                from_price_minor_units=previous.representative_price_minor_units,
                to_price_minor_units=current.representative_price_minor_units,
                price_delta_minor_units=price_delta,
                price_delta_bps=price_delta_bps,
            )
        )

    return ProductIntelligence(
        product_id=product_id,
        currency=reference_currency,
        catalog_variant_count=catalog_count,
        observed_variant_count=observed_count,
        coverage_pct=(round(observed_count / catalog_count * 100) if catalog_count else 0),
        total_offer_count=sum(point.offer_count for point in observed),
        retailer_count=len(retailer_keys),
        sample_status=_sample_status(
            observed=observed_count, catalog=catalog_count, retailer_count=len(retailer_keys)
        ),
        storages_gb=tuple(sorted(storage_catalog_counts)),
        colors=tuple(sorted(color_catalog_counts)),
        min_price_minor_units=(
            min(
                point.min_price_minor_units
                for point in observed
                if point.min_price_minor_units is not None
            )
            if observed
            else None
        ),
        max_price_minor_units=(
            max(
                point.max_price_minor_units
                for point in observed
                if point.max_price_minor_units is not None
            )
            if observed
            else None
        ),
        cheapest_variant=(
            min(observed, key=lambda item: item.median_price_minor_units) if observed else None
        ),
        most_expensive_variant=(
            max(observed, key=lambda item: item.median_price_minor_units) if observed else None
        ),
        entry_storage_step=storage_steps[0] if storage_steps else None,
        cheapest_storage=(
            min(
                priced_storages,
                key=lambda item: (
                    item.representative_price_minor_units
                    if item.representative_price_minor_units is not None
                    else 2**63
                ),
            )
            if priced_storages
            else None
        ),
        most_expensive_storage=(
            max(priced_storages, key=lambda item: item.representative_price_minor_units or 0)
            if priced_storages
            else None
        ),
        cheapest_color=(
            min(indexed_colors, key=lambda item: item.relative_price_delta_bps or 0)
            if len(indexed_colors) >= 2
            else None
        ),
        most_expensive_color=(
            max(indexed_colors, key=lambda item: item.relative_price_delta_bps or 0)
            if len(indexed_colors) >= 2
            else None
        ),
        storage_steps=tuple(storage_steps),
        storage_analysis=tuple(storage_analysis),
        color_analysis=tuple(color_analysis),
        variant_analysis=tuple(variant_analysis),
    )
