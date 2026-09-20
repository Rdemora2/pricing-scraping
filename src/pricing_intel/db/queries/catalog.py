from __future__ import annotations

from uuid import UUID

from psycopg.rows import class_row

from pricing_intel.db import sql
from pricing_intel.db.pool import connection
from pricing_intel.domain.models import Product, Seller, Variant


async def get_or_create_seller(*, source_id: UUID, external_id: str, display_name: str) -> Seller:
    async with connection() as conn, conn.cursor(row_factory=class_row(Seller)) as cur:
        await cur.execute(
            sql.GET_OR_CREATE_SELLER,
            {
                "source_id": source_id,
                "external_id": external_id,
                "display_name": display_name,
            },
        )
        seller = await cur.fetchone()
        assert seller is not None
        return seller


async def find_variant_by_gtin(gtin: str) -> Variant | None:
    async with connection() as conn, conn.cursor(row_factory=class_row(Variant)) as cur:
        await cur.execute(sql.FIND_VARIANT_BY_GTIN, {"gtin": gtin})
        return await cur.fetchone()


async def find_variant_by_signature(signature: str) -> Variant | None:
    """Not yet product-scoped: increment 1 seeds a single canonical
    product, so a global signature lookup is unambiguous. Scoping by
    product would need a title/brand hint from the listing once more
    than one product is tracked (see docs/architecture.md)."""
    async with connection() as conn, conn.cursor(row_factory=class_row(Variant)) as cur:
        await cur.execute(sql.FIND_VARIANT_BY_SIGNATURE, {"signature": signature})
        return await cur.fetchone()


async def list_variants_for_product(product_id: UUID) -> list[Variant]:
    async with connection() as conn, conn.cursor(row_factory=class_row(Variant)) as cur:
        await cur.execute(sql.LIST_VARIANTS_FOR_PRODUCT, {"product_id": product_id})
        return await cur.fetchall()


async def get_variant(variant_id: UUID) -> Variant | None:
    async with connection() as conn, conn.cursor(row_factory=class_row(Variant)) as cur:
        await cur.execute(sql.GET_VARIANT, {"variant_id": variant_id})
        return await cur.fetchone()


async def get_product(product_id: UUID) -> Product | None:
    async with connection() as conn, conn.cursor(row_factory=class_row(Product)) as cur:
        await cur.execute(sql.GET_PRODUCT, {"product_id": product_id})
        return await cur.fetchone()
