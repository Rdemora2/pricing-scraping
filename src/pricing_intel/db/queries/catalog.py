from __future__ import annotations

from uuid import UUID

from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from pricing_intel.db import sql
from pricing_intel.db.pool import connection
from pricing_intel.domain.models import Product, Seller, Variant
from pricing_intel.matching.signature import compute_signature


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
    """Resolve a full canonical signature.

    Production adapters include brand, model, region, storage and color,
    preventing the cross-product ambiguity of a storage/color-only signature.
    Legacy laboratory variants intentionally remain isolated by their simpler
    signatures.
    """
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


async def list_products() -> list[Product]:
    async with connection() as conn, conn.cursor(row_factory=class_row(Product)) as cur:
        await cur.execute(sql.LIST_PRODUCTS)
        return await cur.fetchall()


async def get_product(product_id: UUID) -> Product | None:
    async with connection() as conn, conn.cursor(row_factory=class_row(Product)) as cur:
        await cur.execute(sql.GET_PRODUCT, {"product_id": product_id})
        return await cur.fetchone()


async def create_product_with_variants(
    *,
    name: str,
    brand: str,
    category: str,
    variants: list[tuple[dict[str, str], str | None]],
) -> tuple[Product, list[Variant]]:
    async with connection() as conn:
        async with conn.cursor(row_factory=class_row(Product)) as cur:
            await cur.execute(
                """
                INSERT INTO product (name, brand, category)
                VALUES (%(name)s, %(brand)s, %(category)s)
                ON CONFLICT (lower(name)) DO NOTHING
                RETURNING id, name, brand, category, created_at
                """,
                {"name": name, "brand": brand, "category": category},
            )
            product = await cur.fetchone()
        if product is None:
            raise ValueError(f"product already exists: {name}")

        created_variants: list[Variant] = []
        for attributes, gtin in variants:
            async with conn.cursor(row_factory=class_row(Variant)) as cur:
                await cur.execute(
                    """
                    INSERT INTO variant (product_id, attributes, attributes_signature, gtin)
                    VALUES (%(product_id)s, %(attributes)s, %(signature)s, %(gtin)s)
                    RETURNING id, product_id, attributes, attributes_signature, gtin
                    """,
                    {
                        "product_id": product.id,
                        "attributes": Jsonb(attributes),
                        "signature": compute_signature(attributes),
                        "gtin": gtin,
                    },
                )
                variant = await cur.fetchone()
                assert variant is not None
                created_variants.append(variant)
        return product, created_variants
