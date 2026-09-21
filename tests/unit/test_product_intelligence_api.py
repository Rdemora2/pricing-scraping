from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from pricing_intel.api.routers import catalog
from pricing_intel.domain.enums import Availability, Condition
from pricing_intel.domain.models import (
    PaymentTerms,
    Product,
    ProductVariantOfferSnapshot,
    ShippingTerms,
    Variant,
)


async def test_product_intelligence_endpoint_returns_explainable_contract(monkeypatch) -> None:
    product = Product(
        id=uuid4(),
        name="Apple iPhone 17 Pro",
        brand="Apple",
        category="smartphone",
        created_at=datetime(2026, 9, 20, tzinfo=UTC),
    )
    variants = [
        Variant(
            id=uuid4(),
            product_id=product.id,
            attributes={"storage_gb": storage, "color": color},
            attributes_signature=f"{storage}:{color}",
            gtin=None,
        )
        for storage, color in (
            ("256", "Prateado"),
            ("256", "Preto"),
            ("512", "Prateado"),
            ("512", "Preto"),
        )
    ]
    snapshots = [
        ProductVariantOfferSnapshot(
            variant_id=item.id,
            offer_id=uuid4(),
            source_name=f"Fonte {index}",
            seller_name=f"Loja {index}",
            url=f"https://example.test/{index}",
            condition=Condition.NEW,
            availability=Availability.IN_STOCK,
            price_minor_units=price,
            currency="BRL",
            observed_at=datetime.now(UTC),
            payment_terms=PaymentTerms(),
            shipping=ShippingTerms(known=False),
        )
        for index, (item, price) in enumerate(
            zip(variants, (700_000, 720_000, 850_000, 880_000), strict=True), start=1
        )
    ]

    async def get_product(_product_id):
        return product

    async def list_variants(_product_id):
        return variants

    async def list_snapshots(_product_id):
        return snapshots

    monkeypatch.setattr(catalog.catalog_q, "get_product", get_product)
    monkeypatch.setattr(catalog.catalog_q, "list_variants_for_product", list_variants)
    monkeypatch.setattr(catalog.offers_q, "list_latest_snapshots_for_product", list_snapshots)

    response = await catalog.get_product_intelligence(product.id)

    assert response.product_id == product.id
    assert response.storages_gb == [256, 512]
    assert response.colors == ["Prateado", "Preto"]
    assert [item.offer_count for item in response.variant_analysis] == [1, 1, 1, 1]
    assert response.min_price == "7000.00"
    assert response.freshness_window_hours == 72
    assert response.entry_storage_step is not None
    assert response.entry_storage_step.from_storage_gb == 256
    assert response.entry_storage_step.to_storage_gb == 512
    assert response.entry_storage_step.price_delta == "1550.00"
    assert response.entry_storage_step.price_delta_pct == "21.83"
    assert len(response.storage_steps) == 1
    assert response.methodology[-1] == (
        "Saltos de capacidade exigem duas cores por capacidade e três varejistas entre as duas capacidades."
    )


async def test_product_intelligence_endpoint_rejects_unknown_product(monkeypatch) -> None:
    async def get_product(_product_id):
        return None

    monkeypatch.setattr(catalog.catalog_q, "get_product", get_product)

    with pytest.raises(HTTPException) as exc_info:
        await catalog.get_product_intelligence(uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "product not found"
