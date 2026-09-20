"""Seed the canonical catalog plus reviewed collection sources.

The external sources are explicit: their product URLs, robots policies and
structured-data adapters were reviewed for this increment. Broad search
results never become enabled sources through this script.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from psycopg.types.json import Jsonb

from pricing_intel.db.pool import close_pool, connection
from pricing_intel.matching.signature import compute_signature


@dataclass(frozen=True, slots=True)
class SeedVariant:
    attributes: dict[str, str]
    gtin: str | None = None


@dataclass(frozen=True, slots=True)
class SeedProduct:
    name: str
    brand: str
    category: str
    variants: tuple[SeedVariant, ...]


@dataclass(frozen=True, slots=True)
class SeedSource:
    name: str
    base_url: str
    kind: str
    adapter_name: str
    status: str = "candidate"


def _iphone_variant(storage: str, color: str, *, gtin: str | None = None) -> SeedVariant:
    return SeedVariant(
        attributes={
            "brand": "apple",
            "model": "iphone_17",
            "region": "br",
            "storage_gb": storage,
            "color": color,
        },
        gtin=gtin,
    )


def _device_variants(
    *, brand: str, model: str, storages: tuple[str, ...], colors: tuple[str, ...]
) -> tuple[SeedVariant, ...]:
    return tuple(
        SeedVariant(
            attributes={
                "brand": brand.lower(),
                "model": model,
                "region": "br",
                "storage_gb": storage,
                "color": color,
            }
        )
        for storage in storages
        for color in colors
    )


PRODUCTS = (
    SeedProduct(
        name="Apple iPhone 17",
        brand="Apple",
        category="smartphone",
        variants=tuple(
            _iphone_variant(
                storage,
                color,
                gtin="195950643428" if (storage, color) == ("256", "Preto") else None,
            )
            for storage in ("256", "512")
            for color in ("Preto", "Branco", "Azul-Névoa", "Lavanda", "Sálvia")
        ),
    ),
    SeedProduct(
        name="Apple iPhone 17 Pro",
        brand="Apple",
        category="smartphone",
        variants=_device_variants(
            brand="Apple",
            model="iphone_17_pro",
            storages=("256", "512", "1024"),
            colors=("Prateado", "Laranja-Cósmico", "Azul-Intenso"),
        ),
    ),
    SeedProduct(
        name="Apple iPhone 17 Pro Max",
        brand="Apple",
        category="smartphone",
        variants=_device_variants(
            brand="Apple",
            model="iphone_17_pro_max",
            storages=("256", "512", "1024", "2048"),
            colors=("Prateado", "Laranja-Cósmico", "Azul-Intenso"),
        ),
    ),
    SeedProduct(
        name="Samsung Galaxy S26",
        brand="Samsung",
        category="smartphone",
        variants=_device_variants(
            brand="Samsung",
            model="galaxy_s26",
            storages=("256", "512"),
            colors=("Violeta", "Azul", "Preto", "Branco", "Prata", "Dourado"),
        ),
    ),
    SeedProduct(
        name="Samsung Galaxy S26+",
        brand="Samsung",
        category="smartphone",
        variants=_device_variants(
            brand="Samsung",
            model="galaxy_s26_plus",
            storages=("256", "512"),
            colors=("Violeta", "Azul", "Preto", "Branco", "Prata", "Dourado"),
        ),
    ),
    SeedProduct(
        name="Samsung Galaxy S26 Ultra",
        brand="Samsung",
        category="smartphone",
        variants=_device_variants(
            brand="Samsung",
            model="galaxy_s26_ultra",
            storages=("256", "512", "1024"),
            colors=("Violeta", "Azul", "Preto", "Branco", "Prata", "Dourado"),
        ),
    ),
    SeedProduct(
        name="Nimbus Phone X",
        brand="Nimbus",
        category="smartphone",
        variants=(
            SeedVariant({"storage_gb": "128", "color": "Preto"}, "7891234500018"),
            SeedVariant({"storage_gb": "256", "color": "Preto"}, "7891234500025"),
            SeedVariant({"storage_gb": "128", "color": "Azul"}, "7891234500032"),
        ),
    ),
)

SOURCES = (
    SeedSource(
        name="iPlace",
        base_url="https://www.iplace.com.br/iphone-17-256gb-lavanda/100740PR",
        kind="real",
        adapter_name="iplace",
        # The reviewed product path currently returns HTTP 403 to the
        # declared collector user-agent. Keep the integration visible but do
        # not disguise the bot as a browser or retry around the restriction.
        status="candidate",
    ),
    SeedSource(
        name="Fast Shop",
        base_url=(
            "https://site.fastshop.com.br/iphone-17-apple--256gb--preto--tela-de-6-3---"
            "5g-e-camera-de-48mp-aemg6j4brapto_prd/p"
        ),
        kind="real",
        adapter_name="fast_shop",
        status="enabled",
    ),
    SeedSource(
        name="Fast Shop — Apple iPhone 17 Pro",
        base_url="https://site.fastshop.com.br/iphone-17-pro-256gb-azul-intenso-118300/p",
        kind="real",
        adapter_name="fast_shop",
        status="enabled",
    ),
    SeedSource(
        name="Fast Shop — Apple iPhone 17 Pro Max",
        base_url=(
            "https://site.fastshop.com.br/iphone-17-pro-max--256gb--azul-intenso--tela-de-6-9---"
            "5g-e-camera-de-48mp-aemfyp4beaazl_prd/p"
        ),
        kind="real",
        adapter_name="fast_shop",
        status="enabled",
    ),
    SeedSource(
        name="Samsung Shop — Galaxy S26",
        base_url="https://shop.samsung.com/br/galaxy-s26/p",
        kind="real",
        adapter_name="samsung_shop",
        status="enabled",
    ),
    SeedSource(
        name="Samsung Shop — Galaxy S26+",
        base_url="https://shop.samsung.com/br/galaxy-s26-plus/p",
        kind="real",
        adapter_name="samsung_shop",
        status="enabled",
    ),
    SeedSource(
        name="Samsung Shop — Galaxy S26 Ultra",
        base_url="https://shop.samsung.com/br/galaxy-s26-ultra/p",
        kind="real",
        adapter_name="samsung_shop",
        status="enabled",
    ),
    SeedSource(
        name="Zoom — Apple iPhone 17",
        base_url="https://www.zoom.com.br/celular/celular-apple-iphone-17-256gb",
        kind="real",
        adapter_name="zoom",
        status="enabled",
    ),
    SeedSource(
        name="Zoom — Apple iPhone 17 Pro",
        base_url="https://www.zoom.com.br/celular/celular-apple-iphone-17-pro-256gb",
        kind="real",
        adapter_name="zoom",
        status="enabled",
    ),
    SeedSource(
        name="Zoom — Apple iPhone 17 Pro Max",
        base_url="https://www.zoom.com.br/celular/celular-apple-iphone-17-pro-max-256gb",
        kind="real",
        adapter_name="zoom",
        status="enabled",
    ),
    SeedSource(
        name="Zoom — Samsung Galaxy S26",
        base_url="https://www.zoom.com.br/celular/celular-samsung-galaxy-s26-5g-256gb",
        kind="real",
        adapter_name="zoom",
        status="candidate",
    ),
    SeedSource(
        name="Zoom — Samsung Galaxy S26+",
        base_url="https://www.zoom.com.br/celular/celular-samsung-galaxy-s26-plus-5g-256gb",
        kind="real",
        adapter_name="zoom",
        status="candidate",
    ),
    SeedSource(
        name="Zoom — Samsung Galaxy S26 Ultra",
        base_url="https://www.zoom.com.br/celular/celular-samsung-galaxy-s26-ultra-5g-256gb",
        kind="real",
        adapter_name="zoom",
        status="enabled",
    ),
    SeedSource(
        name="2aFinder — Apple iPhone 17",
        base_url="https://2afinder.com/produto/iphone-iphone-17-2025-308835.md",
        kind="real",
        adapter_name="two_a_finder",
        status="enabled",
    ),
    SeedSource(
        name="2aFinder — Apple iPhone 17 Pro",
        base_url="https://2afinder.com/produto/iphone-iphone-17-pro-2025-308767.md",
        kind="real",
        adapter_name="two_a_finder",
        status="enabled",
    ),
    SeedSource(
        name="2aFinder — Apple iPhone 17 Pro Max",
        base_url="https://2afinder.com/produto/iphone-iphone-17-pro-max-2025.md",
        kind="real",
        adapter_name="two_a_finder",
        status="enabled",
    ),
    SeedSource(
        name="2aFinder — Samsung Galaxy S26",
        base_url="https://2afinder.com/produto/galaxy-s-galaxy-s26-2026-985394.md",
        kind="real",
        adapter_name="two_a_finder",
        status="enabled",
    ),
    SeedSource(
        name="2aFinder — Samsung Galaxy S26+",
        base_url="https://2afinder.com/produto/galaxy-s-galaxy-s26-2026-559881.md",
        kind="real",
        adapter_name="two_a_finder",
        status="enabled",
    ),
    SeedSource(
        name="2aFinder — Samsung Galaxy S26 Ultra",
        base_url="https://2afinder.com/produto/galaxy-s-galaxy-s26-ultra-2026-154055.md",
        kind="real",
        adapter_name="two_a_finder",
        status="enabled",
    ),
    SeedSource(
        name="Buscapé — Apple iPhone 17",
        base_url="https://www.buscape.com.br/celular/celular-apple-iphone-17-256gb",
        kind="real",
        adapter_name="buscape",
        status="enabled",
    ),
    SeedSource(
        name="Buscapé — Apple iPhone 17 Pro",
        base_url="https://www.buscape.com.br/celular/celular-apple-iphone-17-pro-256gb",
        kind="real",
        adapter_name="buscape",
        status="enabled",
    ),
    SeedSource(
        name="Buscapé — Apple iPhone 17 Pro Max",
        base_url="https://www.buscape.com.br/celular/celular-apple-iphone-17-pro-max-256gb",
        kind="real",
        adapter_name="buscape",
        status="enabled",
    ),
    SeedSource(
        name="Buscapé — Samsung Galaxy S26",
        base_url="https://www.buscape.com.br/celular/celular-samsung-galaxy-s26-5g-256gb",
        kind="real",
        adapter_name="buscape",
        status="enabled",
    ),
    SeedSource(
        name="Buscapé — Samsung Galaxy S26+",
        base_url=("https://www.buscape.com.br/celular/celular-samsung-galaxy-s26-plus-5g-256gb"),
        kind="real",
        adapter_name="buscape",
        status="enabled",
    ),
    SeedSource(
        name="Buscapé — Samsung Galaxy S26 Ultra",
        base_url=("https://www.buscape.com.br/celular/celular-samsung-galaxy-s26-ultra-5g-256gb"),
        kind="real",
        adapter_name="buscape",
        status="enabled",
    ),
    SeedSource(
        name="KaBuM! — Apple iPhone 17",
        base_url="https://www.kabum.com.br/produto/1016330/iphone-17-256gb-preto",
        kind="real",
        adapter_name="kabum",
        status="enabled",
    ),
    SeedSource(
        name="KaBuM! — Apple iPhone 17 Pro",
        base_url=(
            "https://www.kabum.com.br/produto/925346/iphone-17-pro-apple-256gb-camera-tripla-"
            "fusion-de-48mp-tela-6-3-super-retina-xdr-prateado"
        ),
        kind="real",
        adapter_name="kabum",
        status="enabled",
    ),
    SeedSource(
        name="KaBuM! — Apple iPhone 17 Pro Max",
        base_url=(
            "https://www.kabum.com.br/produto/925355/iphone-17-pro-max-apple-256gb-camera-"
            "tripla-fusion-de-48mp-tela-6-9-super-retina-xdr-prateado"
        ),
        kind="real",
        adapter_name="kabum",
        status="enabled",
    ),
    SeedSource(
        name="KaBuM! — Samsung Galaxy S26",
        base_url=(
            "https://www.kabum.com.br/produto/1007561/smartphone-samsung-galaxy-s26-256gb-"
            "12gb-ram-5g-inteligencia-artificial-camera-tripla-de-50mp-tela-de-6-3-branco-"
            "sm-s942bzwszto"
        ),
        kind="real",
        adapter_name="kabum",
        status="enabled",
    ),
    SeedSource(
        name="KaBuM! — Samsung Galaxy S26+",
        base_url=(
            "https://www.kabum.com.br/produto/1007582/smartphone-samsung-galaxy-s26-5g-"
            "256gb-12gb-ram-amoled-6-7-120hz-8k-preto-sm-s947bzkrzto"
        ),
        kind="real",
        adapter_name="kabum",
        status="enabled",
    ),
    SeedSource(
        name="KaBuM! — Samsung Galaxy S26 Ultra",
        base_url=(
            "https://www.kabum.com.br/produto/1048105/celular-samsung-galaxy-s26-ultra-de-"
            "256gb-12gb-ram-de-6-9-200-50-10-50mp-12mp-preto"
        ),
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
        name="Mercado Livre",
        base_url="https://www.mercadolivre.com.br/",
        kind="real",
        adapter_name="mercado_livre_api",
    ),
    SeedSource(
        name="Amazon Brasil",
        base_url="https://www.amazon.com.br/",
        kind="real",
        adapter_name="amazon_creators_api",
    ),
    SeedSource(
        name="Casas Bahia",
        base_url="https://www.casasbahia.com.br/",
        kind="real",
        adapter_name="pending_adapter",
    ),
    SeedSource(
        name="Ponto",
        base_url="https://www.pontofrio.com.br/",
        kind="real",
        adapter_name="pending_adapter",
    ),
    SeedSource(
        name="Magalu",
        base_url="https://www.magazineluiza.com.br/",
        kind="real",
        adapter_name="pending_adapter",
    ),
)


async def _seed_product(cur, product: SeedProduct) -> int:
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
