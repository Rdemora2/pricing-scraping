from __future__ import annotations

from uuid import UUID

from psycopg.rows import class_row

from pricing_intel.db import sql
from pricing_intel.db.pool import connection
from pricing_intel.domain.enums import PageType
from pricing_intel.domain.models import DiscoveredPage, Source


async def list_enabled_sources() -> list[Source]:
    async with connection() as conn, conn.cursor(row_factory=class_row(Source)) as cur:
        await cur.execute(sql.LIST_ENABLED_SOURCES)
        return await cur.fetchall()


async def get_source(source_id: UUID) -> Source | None:
    async with connection() as conn, conn.cursor(row_factory=class_row(Source)) as cur:
        await cur.execute(sql.GET_SOURCE_BY_ID, {"source_id": source_id})
        return await cur.fetchone()


async def upsert_discovered_page(
    *, source_id: UUID, url: str, canonical_url: str, page_type: PageType
) -> DiscoveredPage:
    async with connection() as conn, conn.cursor(row_factory=class_row(DiscoveredPage)) as cur:
        await cur.execute(
            sql.UPSERT_DISCOVERED_PAGE,
            {
                "source_id": source_id,
                "url": url,
                "canonical_url": canonical_url,
                "page_type": page_type.value,
            },
        )
        page = await cur.fetchone()
        assert page is not None
        return page


async def list_pending_product_pages(source_id: UUID) -> list[DiscoveredPage]:
    async with connection() as conn, conn.cursor(row_factory=class_row(DiscoveredPage)) as cur:
        await cur.execute(sql.LIST_PENDING_PAGES, {"source_id": source_id})
        return await cur.fetchall()


async def mark_page_status(page_id: UUID, status: str) -> None:
    async with connection() as conn:
        await conn.execute(sql.MARK_PAGE_STATUS, {"page_id": page_id, "status": status})


async def count_pending_product_pages(source_id: UUID) -> int:
    async with connection() as conn, conn.cursor() as cur:
        await cur.execute(sql.COUNT_PENDING_PRODUCT_PAGES, {"source_id": source_id})
        row = await cur.fetchone()
        assert row is not None
        return row[0]
