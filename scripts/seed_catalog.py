"""Seed the canonical catalog plus reviewed collection sources.

Search-capable adapters are registered once at the retailer root and receive a
canonical product at collection time. Product URLs discovered inside the
retailer remain evidence, not long-lived collector configuration.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from psycopg.types.json import Jsonb

from pricing_intel.catalog import CATALOG_PRODUCTS, CatalogProduct
from pricing_intel.db.pool import close_pool, connection
from pricing_intel.matching.signature import compute_signature


@dataclass(frozen=True, slots=True)
class SeedSource:
    name: str
    base_url: str
    kind: str
    adapter_name: str
    status: str = "candidate"


PRODUCTS = CATALOG_PRODUCTS

SOURCES = (
    SeedSource(
        name="Amazon Brasil",
        base_url="https://www.amazon.com.br/",
        kind="real",
        adapter_name="amazon",
    ),
    SeedSource(
        name="Americanas",
        base_url="https://www.americanas.com.br/",
        kind="real",
        adapter_name="americanas",
        status="enabled",
    ),
    SeedSource(
        name="Carrefour",
        base_url="https://www.carrefour.com.br/",
        kind="real",
        adapter_name="carrefour",
        status="enabled",
    ),
    SeedSource(
        name="iPlace",
        base_url="https://www.iplace.com.br/",
        kind="real",
        adapter_name="iplace",
    ),
    SeedSource(
        name="Fast Shop",
        base_url="https://site.fastshop.com.br/",
        kind="real",
        adapter_name="fast_shop",
    ),
    SeedSource(
        name="Zoom",
        base_url="https://www.zoom.com.br/",
        kind="real",
        adapter_name="zoom",
        status="enabled",
    ),
    SeedSource(
        name="Buscapé",
        base_url="https://www.buscape.com.br/",
        kind="real",
        adapter_name="buscape",
        status="enabled",
    ),
    SeedSource(
        name="Samsung Shop",
        base_url="https://shop.samsung.com/br/",
        kind="real",
        adapter_name="samsung_shop",
        status="enabled",
    ),
    SeedSource(
        name="2aFinder",
        base_url="https://2afinder.com/",
        kind="real",
        adapter_name="two_a_finder",
    ),
    SeedSource(
        name="KaBuM!",
        base_url="https://www.kabum.com.br/",
        kind="real",
        adapter_name="kabum",
        status="enabled",
    ),
    SeedSource(
        name="Loja Aurora (lab)",
        base_url="http://lab-store-a:8000",
        kind="lab_simulated",
        adapter_name="lab_store_a",
        status="enabled",
    ),
    SeedSource(
        name="Mercado Boreal (lab)",
        base_url="http://lab-store-b:8000",
        kind="lab_simulated",
        adapter_name="lab_store_b",
        status="enabled",
    ),
    SeedSource(
        name="Apple Brasil",
        base_url="https://www.apple.com/br/iphone/",
        kind="real",
        adapter_name="catalog_reference",
    ),
    SeedSource(
        name="Samsung Brasil",
        base_url="https://www.samsung.com/br/smartphones/galaxy-s/",
        kind="real",
        adapter_name="catalog_reference",
    ),
    SeedSource(
        name="Motorola Brasil",
        base_url="https://www.motorola.com.br/premium-motorola",
        kind="real",
        adapter_name="catalog_reference",
    ),
    SeedSource(
        name="Mercado Livre",
        base_url="https://www.mercadolivre.com.br/",
        kind="real",
        adapter_name="mercado_livre_api",
    ),
    SeedSource(
        name="Casas Bahia",
        base_url="https://www.casasbahia.com.br/",
        kind="real",
        adapter_name="pending_adapter",
    ),
    SeedSource(
        name="Ponto",
        base_url="https://www.ponto.com.br/",
        kind="real",
        adapter_name="pending_adapter",
    ),
    SeedSource(
        name="Extra",
        base_url="https://www.extra.com.br/",
        kind="real",
        adapter_name="extra",
    ),
    SeedSource(
        name="Shopee Brasil",
        base_url="https://shopee.com.br/",
        kind="real",
        adapter_name="shopee",
    ),
    SeedSource(
        name="AliExpress Brasil",
        base_url="https://pt.aliexpress.com/",
        kind="real",
        adapter_name="aliexpress_br",
    ),
    SeedSource(
        name="Pichau",
        base_url="https://www.pichau.com.br/",
        kind="real",
        adapter_name="pichau",
    ),
    SeedSource(
        name="TerabyteShop",
        base_url="https://www.terabyteshop.com.br/",
        kind="real",
        adapter_name="terabyte",
    ),
    SeedSource(
        name="Xiaomi Brasil",
        base_url="https://www.mibrasil.com.br/",
        kind="real",
        adapter_name="catalog_reference",
    ),
    SeedSource(
        name="Realme Brasil",
        base_url="https://www.realme.com/br/",
        kind="real",
        adapter_name="catalog_reference",
    ),
    SeedSource(
        name="Claro Loja Online",
        base_url="https://loja.claro.com.br/",
        kind="real",
        adapter_name="conditional_price_candidate",
    ),
    SeedSource(
        name="Vivo Loja Online",
        base_url="https://loja.vivo.com.br/",
        kind="real",
        adapter_name="conditional_price_candidate",
    ),
    SeedSource(
        name="TIM Loja Online",
        base_url="https://loja.tim.com.br/",
        kind="real",
        adapter_name="conditional_price_candidate",
    ),
    SeedSource(
        name="JáCotei",
        base_url="https://www.jacotei.com.br/",
        kind="real",
        adapter_name="price_comparison_candidate",
    ),
    SeedSource(
        name="Bondfaro",
        base_url="https://www.bondfaro.com.br/",
        kind="real",
        adapter_name="bondfaro",
    ),
    SeedSource(
        name="Promobit",
        base_url="https://www.promobit.com.br/",
        kind="real",
        adapter_name="promotion_community_candidate",
    ),
    SeedSource(
        name="Pelando",
        base_url="https://www.pelando.com.br/",
        kind="real",
        adapter_name="promotion_community_candidate",
    ),
    SeedSource(
        name="Magalu",
        base_url="https://www.magazineluiza.com.br/",
        kind="real",
        adapter_name="magalu",
        # The root stays visible as a qualified candidate; access and seller
        # semantics must be revalidated before enabling its search adapter.
        status="candidate",
    ),
)


async def _seed_product(cur, product: CatalogProduct) -> int:
    await cur.execute("SELECT id FROM product WHERE name = %(name)s", {"name": product.name})
    row = await cur.fetchone()
    if row is None:
        await cur.execute(
            """
            INSERT INTO product (name, brand, category)
            VALUES (%(name)s, %(brand)s, %(category)s)
            RETURNING id
            """,
            {"name": product.name, "brand": product.brand, "category": product.category},
        )
        row = await cur.fetchone()
    assert row is not None
    product_id = row[0]

    for variant in product.variants:
        signature = compute_signature(variant.attributes)
        await cur.execute(
            """
            INSERT INTO variant (product_id, attributes, attributes_signature, gtin)
            VALUES (%(product_id)s, %(attributes)s, %(signature)s, %(gtin)s)
            ON CONFLICT (product_id, attributes_signature) DO UPDATE SET
                attributes = EXCLUDED.attributes,
                gtin = COALESCE(EXCLUDED.gtin, variant.gtin)
            """,
            {
                "product_id": product_id,
                "attributes": Jsonb(variant.attributes),
                "signature": signature,
                "gtin": variant.gtin,
            },
        )
    return len(product.variants)


async def seed() -> None:
    variant_count = 0
    async with connection() as conn, conn.cursor() as cur:
        for product in PRODUCTS:
            variant_count += await _seed_product(cur, product)

        # Source identities live at the retailer boundary. Retire legacy rows
        # that encoded one product page as one collector identity.
        for adapter_name, root_url in (
            ("amazon", "https://www.amazon.com.br/"),
            ("americanas", "https://www.americanas.com.br/"),
            ("carrefour", "https://www.carrefour.com.br/"),
            ("iplace", "https://www.iplace.com.br/"),
            ("fast_shop", "https://site.fastshop.com.br/"),
            ("zoom", "https://www.zoom.com.br/"),
            ("buscape", "https://www.buscape.com.br/"),
            ("samsung_shop", "https://shop.samsung.com/br/"),
            ("two_a_finder", "https://2afinder.com/"),
            ("kabum", "https://www.kabum.com.br/"),
            ("bondfaro", "https://www.bondfaro.com.br/"),
        ):
            await cur.execute(
                """
                UPDATE source
                SET status = 'disabled'
                WHERE adapter_name = %(adapter_name)s AND base_url <> %(root_url)s
                """,
                {"adapter_name": adapter_name, "root_url": root_url},
            )

        for source in SOURCES:
            # Source names are stable product/adapter identities. When a reviewed
            # canonical URL changes, retire the previous target instead of
            # leaving two enabled collectors after an idempotent reseed.
            await cur.execute(
                """
                UPDATE source
                SET status = 'disabled'
                WHERE name = %(name)s AND base_url <> %(base_url)s
                """,
                {"name": source.name, "base_url": source.base_url},
            )
            await cur.execute(
                """
                INSERT INTO source (name, base_url, kind, status, adapter_name)
                VALUES (%(name)s, %(base_url)s, %(kind)s, %(status)s, %(adapter_name)s)
                ON CONFLICT (base_url) DO UPDATE SET
                    name = EXCLUDED.name,
                    kind = EXCLUDED.kind,
                    status = EXCLUDED.status,
                    adapter_name = EXCLUDED.adapter_name
                """,
                {
                    "name": source.name,
                    "base_url": source.base_url,
                    "kind": source.kind,
                    "adapter_name": source.adapter_name,
                    "status": source.status,
                },
            )

    await close_pool()
    print(f"Seeded {len(PRODUCTS)} products, {variant_count} variants and {len(SOURCES)} sources.")


if __name__ == "__main__":
    asyncio.run(seed())
