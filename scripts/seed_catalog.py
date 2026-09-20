"""Seeds the canonical product/variant catalog and the two lab sources.

Idempotent (safe to run again). The lab sources are inserted directly
as 'enabled' because they are ours, already reviewed by construction —
a real, externally-discovered source must start as 'candidate' and be
flipped to 'enabled' by an explicit, reviewed decision (see
docs/architecture.md), which this script deliberately does not
automate for anything but the lab.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from psycopg.types.json import Jsonb

from pricing_intel.db.pool import close_pool, connection
from pricing_intel.matching.signature import compute_signature

PRODUCT = {"name": "Nimbus Phone X", "brand": "Nimbus", "category": "smartphone"}


@dataclass(frozen=True, slots=True)
class SeedVariant:
    attributes: dict[str, str]
    gtin: str


@dataclass(frozen=True, slots=True)
class SeedSource:
    name: str
    base_url: str
    kind: str
    adapter_name: str


VARIANTS = [
    SeedVariant(attributes={"storage_gb": "128", "color": "Preto"}, gtin="7891234500018"),
    SeedVariant(attributes={"storage_gb": "256", "color": "Preto"}, gtin="7891234500025"),
    SeedVariant(attributes={"storage_gb": "128", "color": "Azul"}, gtin="7891234500032"),
]

SOURCES = [
    SeedSource(
        name="Loja Aurora (lab)",
        base_url="http://lab-store-a:8000",
        kind="lab_simulated",
        adapter_name="lab_store_a",
    ),
    SeedSource(
        name="Mercado Boreal (lab)",
        base_url="http://lab-store-b:8000",
        kind="lab_simulated",
        adapter_name="lab_store_b",
    ),
]


async def seed() -> None:
    async with connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO product (name, brand, category)
            VALUES (%(name)s, %(brand)s, %(category)s)
            ON CONFLICT DO NOTHING
            """,
            PRODUCT,
        )
        await cur.execute("SELECT id FROM product WHERE name = %(name)s", {"name": PRODUCT["name"]})
        row = await cur.fetchone()
        assert row is not None
        product_id = row[0]

        for variant in VARIANTS:
            signature = compute_signature(variant.attributes)
            await cur.execute(
                """
                INSERT INTO variant (product_id, attributes, attributes_signature, gtin)
                VALUES (%(product_id)s, %(attributes)s, %(signature)s, %(gtin)s)
                ON CONFLICT (product_id, attributes_signature) DO NOTHING
                """,
                {
                    "product_id": product_id,
                    "attributes": Jsonb(variant.attributes),
                    "signature": signature,
                    "gtin": variant.gtin,
                },
            )

        for source in SOURCES:
            await cur.execute(
                """
                INSERT INTO source (name, base_url, kind, status, adapter_name)
                VALUES (%(name)s, %(base_url)s, %(kind)s, 'enabled', %(adapter_name)s)
                ON CONFLICT (base_url) DO UPDATE SET status = 'enabled'
                """,
                {
                    "name": source.name,
                    "base_url": source.base_url,
                    "kind": source.kind,
                    "adapter_name": source.adapter_name,
                },
            )

    await close_pool()
    print(f"Seeded product {product_id} with {len(VARIANTS)} variants and {len(SOURCES)} sources.")


if __name__ == "__main__":
    asyncio.run(seed())
