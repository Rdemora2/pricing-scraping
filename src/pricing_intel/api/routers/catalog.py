from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException

from pricing_intel.api.schemas import ComparisonResponse, ProductResponse, VariantResponse
from pricing_intel.db.queries import catalog as catalog_q
from pricing_intel.db.queries import offers as offers_q
from pricing_intel.pricing.analysis import compare_variant

router = APIRouter(tags=["catalog"])


@router.get("/products", response_model=list[ProductResponse])
async def list_products() -> list[ProductResponse]:
    products = await catalog_q.list_products()
    return [
        ProductResponse(id=p.id, name=p.name, brand=p.brand, category=p.category) for p in products
    ]


@router.get("/products/{product_id}/variants", response_model=list[VariantResponse])
async def list_variants(product_id: UUID) -> list[VariantResponse]:
    variants = await catalog_q.list_variants_for_product(product_id)
    return [
        VariantResponse(id=v.id, product_id=v.product_id, attributes=v.attributes, gtin=v.gtin)
        for v in variants
    ]


@router.get("/variants/{variant_id}/comparison", response_model=ComparisonResponse)
async def get_comparison(variant_id: UUID) -> ComparisonResponse:
    variant = await catalog_q.get_variant(variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="variant not found")
    snapshots = await offers_q.list_latest_snapshots_for_variant(variant_id)
    result = compare_variant(variant_id, snapshots)
    return ComparisonResponse.from_result(result, generated_at=datetime.now(UTC))
