from decimal import Decimal
from uuid import uuid4

from pricing_intel.domain.enums import MatchMethod
from pricing_intel.domain.models import Variant
from pricing_intel.matching.service import decide_match


def make_variant(*, gtin: str | None = "7891234500018") -> Variant:
    return Variant(
        id=uuid4(),
        product_id=uuid4(),
        attributes={"storage_gb": "128", "color": "Preto"},
        attributes_signature="color=preto|storage_gb=128",
        gtin=gtin,
    )


def test_gtin_match_is_authoritative() -> None:
    variant = make_variant()

    decision = decide_match(
        gtin=variant.gtin,
        attributes={"storage_gb": "128", "color": "Preto"},
        variant_by_gtin=variant,
        variant_by_signature=None,
    )

    assert decision is not None
    assert decision.variant_id == variant.id
    assert decision.confidence == Decimal("1.000")
    assert decision.method == MatchMethod.RULE_GTIN_EXACT


def test_unknown_gtin_does_not_fall_back_to_attributes() -> None:
    variant = make_variant(gtin=None)

    decision = decide_match(
        gtin="0000000000000",
        attributes=variant.attributes,
        variant_by_gtin=None,
        variant_by_signature=variant,
    )

    assert decision is None


def test_attributes_match_only_when_gtin_is_absent() -> None:
    variant = make_variant(gtin=None)

    decision = decide_match(
        gtin=None,
        attributes=variant.attributes,
        variant_by_gtin=None,
        variant_by_signature=variant,
    )

    assert decision is not None
    assert decision.variant_id == variant.id
    assert decision.confidence == Decimal("0.900")
    assert decision.method == MatchMethod.RULE_ATTRIBUTES


def test_no_supported_identifier_returns_no_match() -> None:
    assert (
        decide_match(
            gtin=None,
            attributes={},
            variant_by_gtin=None,
            variant_by_signature=None,
        )
        is None
    )
