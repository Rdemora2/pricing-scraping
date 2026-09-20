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

import re
import unicodedata
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
    retailer_count: int
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


def _retailer_key(name: str) -> str:
    """Collapse known trading-name aliases without merging unrelated sellers."""
    folded = "".join(
        character
        for character in unicodedata.normalize("NFKD", name.casefold())
        if not unicodedata.combining(character)
    )
    normalized = re.sub(r"[^a-z0-9]+", " ", folded).strip()
    aliases = {
        "magazine luiza": "magalu",
        "magazineluiza": "magalu",
        "magalu": "magalu",
        "kabum": "kabum",
        "fast shop": "fast-shop",
        "fastshop": "fast-shop",
    }
    return aliases.get(normalized, normalized)


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
        elif snapshot.payment_terms.is_conditional:
            reason = "price depends on a commercial condition"
            if snapshot.payment_terms.condition_summary:
                reason += f": {snapshot.payment_terms.condition_summary}"
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
            retailer_count=0,
            min_price_minor_units=None,
            median_price_minor_units=None,
            max_price_minor_units=None,
            included=[],
            excluded=excluded,
            oldest_observation_at=None,
            newest_observation_at=None,
        )

    # One price per retailer prevents marketplace/aggregator duplicates from
    # biasing the distribution. Direct evidence wins over an aggregator copy;
    # within the same evidence tier the newest observation wins.
    deduplicated: dict[str, VariantOfferSnapshot] = {}
    for snapshot in sorted(
        included,
        key=lambda item: (
            item.source_name.startswith("Zoom —"),
            -item.observed_at.timestamp(),
            str(item.offer_id),
        ),
    ):
        seller_key = _retailer_key(snapshot.seller_name)
        if seller_key in deduplicated:
            excluded.append(
                ExcludedOffer(
                    offer_id=snapshot.offer_id,
                    source_name=snapshot.source_name,
                    seller_name=snapshot.seller_name,
                    reason="duplicate retailer observation; preferred evidence retained",
                )
            )
            continue
        deduplicated[seller_key] = snapshot

    included = list(deduplicated.values())
    prices = sorted(s.price_minor_units for s in included)
    observed_ats = [s.observed_at for s in included]

    return ComparisonResult(
        variant_id=variant_id,
        currency=reference_currency,
        included_offer_count=len(included),
        source_count=len({s.source_name for s in included}),
        retailer_count=len({_retailer_key(s.seller_name) for s in included}),
        min_price_minor_units=prices[0],
        median_price_minor_units=_median_minor_units(prices),
        max_price_minor_units=prices[-1],
        included=included,
        excluded=excluded,
        oldest_observation_at=min(observed_ats),
        newest_observation_at=max(observed_ats),
    )
