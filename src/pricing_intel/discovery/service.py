"""Orchestration entry point: turns "collect this source now" into a
CollectionRun row plus a deferred Procrastinate job.

Kept deliberately thin — discovery of product pages within a source
happens inside the spider crawl itself (see collection/spiders/base.py)
since separating it would mean fetching every category page twice.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from pricing_intel.db.queries import runs as runs_q
from pricing_intel.db.queries import sources as sources_q
from pricing_intel.domain.enums import RunStatus, RunTrigger
from pricing_intel.domain.models import CollectionRun, Source
from pricing_intel.jobs.tasks import run_collection


class SourceNotEnabledError(Exception):
    pass


def _manual_idempotency_key(source_id: UUID, *, now: datetime) -> str:
    """One manual trigger per source per minute collapses accidental
    double-clicks into the same run instead of queueing duplicates."""
    bucket = now.strftime("%Y%m%dT%H%M")
    return hashlib.sha256(f"{source_id}:{bucket}".encode()).hexdigest()


async def trigger_collection(source_id: UUID) -> CollectionRun:
    source = await sources_q.get_source(source_id)
    if source is None:
        raise ValueError(f"unknown source: {source_id}")
    if source.status.value != "enabled":
        raise SourceNotEnabledError(
            f"source '{source.name}' is not enabled (status={source.status.value})"
        )

    idempotency_key = _manual_idempotency_key(source_id, now=datetime.now(UTC))
    run = await runs_q.create_run(
        source_id=source_id, trigger=RunTrigger.MANUAL, idempotency_key=idempotency_key
    )
    if run.status == RunStatus.PENDING:
        await run_collection.defer_async(run_id=str(run.id))
    return run


async def trigger_all_enabled() -> list[CollectionRun]:
    sources: list[Source] = await sources_q.list_enabled_sources()
    return [await trigger_collection(source.id) for source in sources]
