from __future__ import annotations

from datetime import datetime
from uuid import UUID

from psycopg.rows import class_row

from pricing_intel.config import get_settings
from pricing_intel.db import sql
from pricing_intel.db.pool import connection
from pricing_intel.domain.enums import EvidenceType
from pricing_intel.domain.models import Evidence


async def record_evidence(
    *,
    collection_run_id: UUID,
    source_id: UUID,
    offer_id: UUID | None,
    evidence_type: EvidenceType,
    url: str,
    http_status: int | None,
    extractor_name: str,
    extractor_version: str,
    content_hash: str,
    raw_excerpt: str,
    fetched_at: datetime,
) -> Evidence:
    """Inserts one evidence row and prunes older rows for the same URL
    beyond the configured retention count, in the same transaction."""
    async with connection() as conn:
        async with conn.cursor(row_factory=class_row(Evidence)) as cur:
            await cur.execute(
                sql.INSERT_EVIDENCE,
                {
                    "collection_run_id": collection_run_id,
                    "source_id": source_id,
                    "offer_id": offer_id,
                    "evidence_type": evidence_type.value,
                    "url": url,
                    "http_status": http_status,
                    "extractor_name": extractor_name,
                    "extractor_version": extractor_version,
                    "content_hash": content_hash,
                    "raw_excerpt": raw_excerpt,
                    "fetched_at": fetched_at,
                },
            )
            evidence = await cur.fetchone()
            assert evidence is not None
        await conn.execute(
            sql.PRUNE_EVIDENCE,
            {
                "source_id": source_id,
                "url": url,
                "keep": get_settings().evidence_retention_per_url,
            },
        )
        return evidence
