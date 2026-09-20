from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pricing_intel.domain.enums import Availability, Condition
from pricing_intel.domain.models import PaymentTerms, ShippingTerms, VariantOfferSnapshot
from pricing_intel.pricing.analysis import compare_variant


def snapshot(
    price: int,
    *,
    source: str = "Aurora",
    currency: str = "BRL",
    condition: Condition = Condition.NEW,
    availability: Availability = Availability.IN_STOCK,
    observed_at: datetime | None = None,
) -> VariantOfferSnapshot:
    return VariantOfferSnapshot(
        offer_id=uuid4(),
        source_name=source,
        seller_name=f"{source} seller",
        url=f"https://example.test/{uuid4()}",
        condition=condition,
        availability=availability,
        price_minor_units=price,
        currency=currency,
        observed_at=observed_at or datetime.now(UTC),
        payment_terms=PaymentTerms(),
        shipping=ShippingTerms(known=False),
    )


def test_comparison_reports_population_and_rounds_even_median() -> None:
    variant_id = uuid4()
    oldest = datetime(2026, 9, 19, tzinfo=UTC)
    newest = oldest + timedelta(hours=2)
    result = compare_variant(
        variant_id,
        [
            snapshot(349900, observed_at=oldest),
            snapshot(350000, source="Boreal", observed_at=newest),
        ],
    )

    assert result.included_offer_count == 2
    assert result.source_count == 2
    assert result.min_price_minor_units == 349900
    assert result.median_price_minor_units == 349950
    assert result.max_price_minor_units == 350000
    assert result.oldest_observation_at == oldest
    assert result.newest_observation_at == newest


def test_comparison_explains_each_exclusion() -> None:
    result = compare_variant(
        uuid4(),
        [
            snapshot(100, currency="USD"),
            snapshot(200, condition=Condition.USED),
            snapshot(300, availability=Availability.OUT_OF_STOCK),
        ],
    )

    assert result.has_comparable_data is False
    assert result.included_offer_count == 0
    assert [item.reason for item in result.excluded] == [
        "currency USD is not comparable to BRL",
        "condition is 'used', comparison baseline is 'new'",
        "availability is 'out_of_stock', not in_stock",
    ]


def test_empty_comparison_is_explicitly_insufficient() -> None:
    result = compare_variant(UUID(int=0), [])

    assert result.has_comparable_data is False
    assert result.median_price_minor_units is None
    assert result.oldest_observation_at is None
