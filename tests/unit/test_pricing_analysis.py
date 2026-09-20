from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pricing_intel.domain.enums import Availability, Condition
from pricing_intel.domain.models import PaymentTerms, ShippingTerms, VariantOfferSnapshot
from pricing_intel.pricing.analysis import compare_variant


def snapshot(
    price: int,
    *,
    source: str = "Aurora",
    seller: str | None = None,
    currency: str = "BRL",
    condition: Condition = Condition.NEW,
    availability: Availability = Availability.IN_STOCK,
    observed_at: datetime | None = None,
    payment_terms: PaymentTerms | None = None,
) -> VariantOfferSnapshot:
    return VariantOfferSnapshot(
        offer_id=uuid4(),
        source_name=source,
        seller_name=seller or f"{source} seller",
        url=f"https://example.test/{uuid4()}",
        condition=condition,
        availability=availability,
        price_minor_units=price,
        currency=currency,
        observed_at=observed_at or datetime.now(UTC),
        payment_terms=payment_terms or PaymentTerms(),
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
    assert result.retailer_count == 2
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


def test_conditional_price_is_not_mixed_into_market_baseline() -> None:
    result = compare_variant(
        uuid4(),
        [
            snapshot(
                499900,
                payment_terms=PaymentTerms(
                    is_conditional=True,
                    condition_summary="exclusivo para pagamento com cartão da loja",
                ),
            )
        ],
    )

    assert result.has_comparable_data is False
    assert result.excluded[0].reason == (
        "price depends on a commercial condition: exclusivo para pagamento com cartão da loja"
    )


def test_comparison_deduplicates_retailer_and_prefers_direct_evidence() -> None:
    result = compare_variant(
        uuid4(),
        [
            snapshot(500000, source="Zoom — iPhone 17", seller="Fast Shop"),
            snapshot(490000, source="Fast Shop", seller="Fast Shop"),
            snapshot(510000, source="Zoom — iPhone 17", seller="Amazon"),
        ],
    )

    assert result.included_offer_count == 2
    assert result.retailer_count == 2
    assert result.source_count == 2
    assert {item.price_minor_units for item in result.included} == {490000, 510000}
    assert result.excluded[0].reason == (
        "duplicate retailer observation; preferred evidence retained"
    )


def test_comparison_collapses_known_retailer_trading_name_aliases() -> None:
    result = compare_variant(
        uuid4(),
        [
            snapshot(500000, source="Zoom — iPhone 17", seller="Magazine Luiza"),
            snapshot(490000, source="KaBuM! marketplace", seller="Magalu"),
        ],
    )

    assert result.included_offer_count == 1
    assert result.retailer_count == 1
    assert result.included[0].seller_name == "Magalu"
