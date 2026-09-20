"""Rule-based, revisable offer-to-variant matching.

Deliberately NOT a probabilistic/ML matcher: the brief requires that
uncertain correspondences be reviewable with a stated rationale rather
than presented as calibrated probabilities. ``confidence`` here is a
fixed value per rule, not a learned score.

The catalog itself (Product/Variant) is curated ahead of time (see
scripts/seed_catalog.py) — this module only decides which *existing*
variant a scraped listing corresponds to. An offer that matches nothing
is left unmatched rather than spawning a new canonical product from
unverified scraped text.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from pricing_intel.domain.enums import MatchMethod
from pricing_intel.domain.models import Variant
from pricing_intel.matching.signature import compute_signature


@dataclass(frozen=True, slots=True)
class MatchDecision:
    variant_id: UUID
    confidence: Decimal
    method: MatchMethod
    rationale: str


def decide_match(
    *,
    gtin: str | None,
    attributes: dict[str, str],
    variant_by_gtin: Variant | None,
    variant_by_signature: Variant | None,
) -> MatchDecision | None:
    """GTIN is authoritative when present; attribute signature is the
    fallback for listings that omit it (common for non-GTIN sources)."""
    if gtin:
        if variant_by_gtin is None:
            return None
        if variant_by_gtin.attributes_signature != compute_signature(attributes):
            return None
        return MatchDecision(
            variant_id=variant_by_gtin.id,
            confidence=Decimal("1.000"),
            method=MatchMethod.RULE_GTIN_EXACT,
            rationale=f"GTIN {gtin} matched the catalog exactly",
        )

    if variant_by_signature is not None:
        signature = compute_signature(attributes)
        return MatchDecision(
            variant_id=variant_by_signature.id,
            confidence=Decimal("0.900"),
            method=MatchMethod.RULE_ATTRIBUTES,
            rationale=f"Attribute signature '{signature}' matched the catalog",
        )

    return None
