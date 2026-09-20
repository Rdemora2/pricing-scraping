from datetime import UTC, datetime
from uuid import uuid4

from pricing_intel.domain.enums import Availability, Condition
from pricing_intel.domain.models import (
    PaymentTerms,
    ProductVariantOfferSnapshot,
    ShippingTerms,
    Variant,
)
from pricing_intel.pricing.intelligence import analyze_product


def variant(storage: int, color: str) -> Variant:
    return Variant(
        id=uuid4(),
        product_id=uuid4(),
        attributes={"storage_gb": str(storage), "color": color},
        attributes_signature=f"{storage}:{color}",
        gtin=None,
    )


def snapshot(
    canonical_variant: Variant,
    price: int,
    *,
    seller: str,
) -> ProductVariantOfferSnapshot:
    return ProductVariantOfferSnapshot(
        variant_id=canonical_variant.id,
        offer_id=uuid4(),
        source_name=seller,
        seller_name=seller,
        url=f"https://example.test/{uuid4()}",
        condition=Condition.NEW,
        availability=Availability.IN_STOCK,
        price_minor_units=price,
        currency="BRL",
        observed_at=datetime(2026, 9, 20, tzinfo=UTC),
        payment_terms=PaymentTerms(),
        shipping=ShippingTerms(known=False),
    )


def test_analyzes_storage_value_and_normalized_color_premium() -> None:
    product_id = uuid4()
    variants = [
        variant(256, "Preto"),
        variant(256, "Branco"),
        variant(512, "Preto"),
        variant(512, "Branco"),
        variant(1024, "Preto"),
        variant(1024, "Branco"),
    ]
    prices = [600_000, 620_000, 700_000, 740_000, 900_000, 980_000]
    snapshots = [
        snapshot(item, price, seller=f"Loja {index}")
        for index, (item, price) in enumerate(zip(variants, prices, strict=True), start=1)
    ]

    result = analyze_product(product_id, variants, snapshots)

    assert result.catalog_variant_count == 6
    assert result.observed_variant_count == 6
    assert result.coverage_pct == 100
    assert result.total_offer_count == 6
    assert result.retailer_count == 6
    assert result.sample_status == "strong"
    assert result.storages_gb == (256, 512, 1024)
    assert result.colors == ("Branco", "Preto")
    assert result.min_price_minor_units == 600_000
    assert result.max_price_minor_units == 980_000
    assert result.best_value_storage is not None
    assert result.best_value_storage.storage_gb == 1024
    assert result.cheapest_storage is not None
    assert result.cheapest_storage.storage_gb == 256
    assert result.most_expensive_storage is not None
    assert result.most_expensive_storage.storage_gb == 1024
    assert result.cheapest_color is not None
    assert result.cheapest_color.color == "Preto"
    assert result.cheapest_color.relative_price_delta_bps is not None
    assert result.cheapest_color.relative_price_delta_bps < 0
    assert result.most_expensive_color is not None
    assert result.most_expensive_color.color == "Branco"
    assert result.most_expensive_color.relative_price_delta_bps is not None
    assert result.most_expensive_color.relative_price_delta_bps > 0


def test_no_market_data_keeps_catalog_visible_without_inventing_insights() -> None:
    product_id = uuid4()
    variants = [variant(256, "Preto"), variant(512, "Preto")]

    result = analyze_product(product_id, variants, [])

    assert result.catalog_variant_count == 2
    assert result.observed_variant_count == 0
    assert result.coverage_pct == 0
    assert result.sample_status == "no_data"
    assert result.min_price_minor_units is None
    assert result.best_value_storage is None
    assert result.cheapest_color is None
    assert [item.observed_variant_count for item in result.storage_analysis] == [0, 0]


def test_single_storage_does_not_claim_best_value() -> None:
    product_id = uuid4()
    black = variant(256, "Preto")
    white = variant(256, "Branco")

    result = analyze_product(
        product_id,
        [black, white],
        [snapshot(black, 600_000, seller="Loja A"), snapshot(white, 620_000, seller="Loja B")],
    )

    assert result.best_value_storage is None
    assert result.cheapest_storage is not None
    assert result.cheapest_color is None


def test_ignores_variants_without_required_dimensions() -> None:
    incomplete = Variant(
        id=uuid4(),
        product_id=uuid4(),
        attributes={"storage_gb": "256"},
        attributes_signature="incomplete",
        gtin=None,
    )

    result = analyze_product(uuid4(), [incomplete], [])

    assert result.catalog_variant_count == 0
    assert result.storages_gb == ()
    assert result.colors == ()
