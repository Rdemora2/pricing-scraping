from __future__ import annotations

from uuid import UUID

from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from pricing_intel.db import sql
from pricing_intel.db.pool import connection
from pricing_intel.domain.enums import RunStatus, RunTrigger
from pricing_intel.domain.models import CollectionRun


async def create_run(
    *, source_id: UUID, trigger: RunTrigger, idempotency_key: str
) -> CollectionRun:
    """Idempotent: replaying the same idempotency_key returns the existing run."""
    async with connection() as conn, conn.cursor(row_factory=class_row(CollectionRun)) as cur:
        await cur.execute(
            sql.CREATE_RUN,
            {
                "source_id": source_id,
                "trigger": trigger.value,
                "idempotency_key": idempotency_key,
            },
        )
        run = await cur.fetchone()
        assert run is not None
        return run


async def get_run(run_id: UUID) -> CollectionRun | None:
    async with connection() as conn, conn.cursor(row_factory=class_row(CollectionRun)) as cur:
        await cur.execute(sql.GET_RUN, {"run_id": run_id})
        return await cur.fetchone()


async def mark_running(run_id: UUID) -> None:
    async with connection() as conn:
        await conn.execute(sql.MARK_RUN_RUNNING, {"run_id": run_id})


async def get_run_stats(run_id: UUID) -> dict[str, int]:
    async with connection() as conn, conn.cursor() as cur:
        await cur.execute(sql.COUNT_RUN_STATS, {"run_id": run_id})
        row = await cur.fetchone()
        assert row is not None
        observed, evidence, rejected_access, rejected_extraction, rejected_matching = row
        return {
            "offers_observed": observed,
            "evidence_recorded": evidence,
            # Collection loss, split by where it happened. Zero observations
            # with a high access count means the source blocked the run; a high
            # extraction count means the source changed shape; a high matching
            # count means the catalog does not describe what it is selling.
            "listings_rejected_access": rejected_access,
            "listings_rejected_extraction": rejected_extraction,
            "listings_rejected_matching": rejected_matching,
        }


async def finish_run(
    *,
    run_id: UUID,
    status: RunStatus,
    stats: dict[str, int],
    failure_reason: str | None = None,
) -> None:
    async with connection() as conn:
        await conn.execute(
            sql.FINISH_RUN,
            {
                "run_id": run_id,
                "status": status.value,
                "stats": Jsonb(stats),
                "failure_reason": failure_reason,
            },
        )
