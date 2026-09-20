"""Descriptive, explainable price comparison for one canonical variant.

Deliberately does NOT compute demand, elasticity, or a "recommended
price" — brief section 7 rules that out for this increment. Every
number here answers "what did we actually observe, and from how much
of it" rather than predicting anything.

Comparability filters (currency, condition, availability) are applied
here, in testable Python, rather than folded into the SQL query, so the
exclusion rules can be unit-tested against fixtures without a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from pricing_intel.domain.enums import Availability, Condition
from pricing_intel.domain.models import VariantOfferSnapshot


@dataclass(frozen=True, slots=True)
class ExcludedOffer:
    offer_id: UUID
    source_name: str
    seller_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    variant_id: UUID
    currency: str
    included_offer_count: int
    source_count: int
    min_price_minor_units: int | None
    median_price_minor_units: int | None
    max_price_minor_units: int | None
    included: list[VariantOfferSnapshot]
    excluded: list[ExcludedOffer]
    oldest_observation_at: datetime | None
    newest_observation_at: datetime | None

    @property
    def has_comparable_data(self) -> bool:
        return self.included_offer_count > 0


def _median_minor_units(sorted_prices: list[int]) -> int:
    count = len(sorted_prices)
    middle = count // 2
    if count % 2 == 1:
        return sorted_prices[middle]
    average = (Decimal(sorted_prices[middle - 1]) + Decimal(sorted_prices[middle])) / 2
    return int(average.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compare_variant(
    variant_id: UUID,
    snapshots: list[VariantOfferSnapshot],
    *,
    reference_currency: str = "BRL",
) -> ComparisonResult:
    included: list[VariantOfferSnapshot] = []
    excluded: list[ExcludedOffer] = []

    for snapshot in snapshots:
        if snapshot.currency != reference_currency:
            reason = f"currency {snapshot.currency} is not comparable to {reference_currency}"
        elif snapshot.condition != Condition.NEW:
            reason = f"condition is '{snapshot.condition.value}', comparison baseline is 'new'"
        elif snapshot.availability != Availability.IN_STOCK:
            reason = f"availability is '{snapshot.availability.value}', not in_stock"
        else:
            included.append(snapshot)
            continue
        excluded.append(
            ExcludedOffer(
                offer_id=snapshot.offer_id,
                source_name=snapshot.source_name,
                seller_name=snapshot.seller_name,
                reason=reason,
            )
        )

    if not included:
        return ComparisonResult(
            variant_id=variant_id,
            currency=reference_currency,
            included_offer_count=0,
            source_count=0,
            min_price_minor_units=None,
            median_price_minor_units=None,
            max_price_minor_units=None,
            included=[],
            excluded=excluded,
            oldest_observation_at=None,
            newest_observation_at=None,
        )

    prices = sorted(s.price_minor_units for s in included)
    observed_ats = [s.observed_at for s in included]

    return ComparisonResult(
        variant_id=variant_id,
        currency=reference_currency,
        included_offer_count=len(included),
        source_count=len({s.source_name for s in included}),
        min_price_minor_units=prices[0],
        median_price_minor_units=_median_minor_units(prices),
        max_price_minor_units=prices[-1],
        included=included,
        excluded=excluded,
        oldest_observation_at=min(observed_ats),
        newest_observation_at=max(observed_ats),
    )
