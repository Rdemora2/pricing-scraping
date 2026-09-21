from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from psycopg.errors import UniqueViolation

from pricing_intel.api.routers.collection import _is_allowed_local_origin
from pricing_intel.api.schemas import (
    ComparisonResponse,
    ProductCreateRequest,
    ProductDetailResponse,
    ProductIntelligenceResponse,
    ProductResponse,
    VariantResponse,
)
from pricing_intel.config import get_settings
from pricing_intel.db.queries import catalog as catalog_q
from pricing_intel.db.queries import offers as offers_q
from pricing_intel.pricing.analysis import compare_variant
from pricing_intel.pricing.intelligence import analyze_product

router = APIRouter(tags=["catalog"])


def _product_response(product) -> ProductResponse:
    return ProductResponse(
        id=product.id, name=product.name, brand=product.brand, category=product.category
    )


def _variant_response(variant) -> VariantResponse:
    return VariantResponse(
        id=variant.id,
        product_id=variant.product_id,
        attributes=variant.attributes,
        gtin=variant.gtin,
    )


@router.get("/products", response_model=list[ProductResponse])
async def list_products() -> list[ProductResponse]:
    products = await catalog_q.list_products()
    return [_product_response(product) for product in products]


@router.post("/products", response_model=ProductDetailResponse, status_code=201)
async def create_product(payload: ProductCreateRequest, request: Request) -> ProductDetailResponse:
    origin = request.headers.get("origin")
    if origin is not None and not _is_allowed_local_origin(origin):
        raise HTTPException(status_code=403, detail="origin not allowed")
    signatures = {
        tuple(sorted((key.lower(), value.lower()) for key, value in variant.attributes.items()))
        for variant in payload.variants
    }
    if len(signatures) != len(payload.variants):
        raise HTTPException(status_code=422, detail="duplicate variant attributes")
    try:
        product, variants = await catalog_q.create_product_with_variants(
            name=payload.name.strip(),
            brand=payload.brand.strip(),
            category=payload.category.strip(),
            variants=[(variant.attributes, variant.gtin) for variant in payload.variants],
        )
    except (UniqueViolation, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail="a product with this name or a variant with this GTIN already exists",
        ) from exc
    return ProductDetailResponse(
        product=_product_response(product),
        variants=[_variant_response(variant) for variant in variants],
    )


@router.get("/products/{product_id}/variants", response_model=list[VariantResponse])
async def list_variants(product_id: UUID) -> list[VariantResponse]:
    variants = await catalog_q.list_variants_for_product(product_id)
    return [_variant_response(variant) for variant in variants]


@router.get("/products/{product_id}/intelligence", response_model=ProductIntelligenceResponse)
async def get_product_intelligence(product_id: UUID) -> ProductIntelligenceResponse:
    product = await catalog_q.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    variants = await catalog_q.list_variants_for_product(product_id)
    snapshots = await offers_q.list_latest_snapshots_for_product(product_id)
    generated_at = datetime.now(UTC)
    freshness_hours = get_settings().comparison_max_age_hours
    result = analyze_product(
        product_id,
        variants,
        snapshots,
        observed_after=generated_at - timedelta(hours=freshness_hours),
    )
    return ProductIntelligenceResponse.from_result(
        result,
        generated_at=generated_at,
        freshness_window_hours=freshness_hours,
    )


@router.get("/variants/{variant_id}/comparison", response_model=ComparisonResponse)
async def get_comparison(variant_id: UUID) -> ComparisonResponse:
    variant = await catalog_q.get_variant(variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="variant not found")
    snapshots = await offers_q.list_latest_snapshots_for_variant(variant_id)
    generated_at = datetime.now(UTC)
    freshness_hours = get_settings().comparison_max_age_hours
    result = compare_variant(
        variant_id,
        snapshots,
        observed_after=generated_at - timedelta(hours=freshness_hours),
    )
    return ComparisonResponse.from_result(
        result,
        generated_at=generated_at,
        freshness_window_hours=freshness_hours,
    )
