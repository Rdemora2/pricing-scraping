"""Procrastinate tasks. Only one for increment 1: run a source's spider
and translate the outcome into the collection_run state machine
(pending -> running -> succeeded | failed | partial).
"""

from __future__ import annotations

from uuid import UUID

import structlog

from pricing_intel.collection.runner import run_spider
from pricing_intel.db.queries import catalog as catalog_q
from pricing_intel.db.queries import runs as runs_q
from pricing_intel.db.queries import sources as sources_q
from pricing_intel.domain.enums import RunStatus
from pricing_intel.jobs.app import app

logger = structlog.get_logger(__name__)


@app.task(queue="collection", retry=2)
async def run_collection(run_id: str, product_id: str | None = None) -> None:
    run_uuid = UUID(run_id)
    run = await runs_q.get_run(run_uuid)
    if run is None:
        logger.error("collection_run_not_found", run_id=run_id)
        return
    if run.status != RunStatus.PENDING:
        # Replaying a defer for a run already picked up (or finished) must
        # not re-execute it — reprocessing the same job must not duplicate
        # its effect.
        logger.warning("collection_run_already_started", run_id=run_id, status=run.status.value)
        return

    source = await sources_q.get_source(run.source_id)
    if source is None:
        await runs_q.finish_run(
            run_id=run_uuid,
            status=RunStatus.FAILED,
            stats={},
            failure_reason="source not found",
        )
        return

    product = await catalog_q.get_product(UUID(product_id)) if product_id else None
    variants = await catalog_q.list_variants_for_product(product.id) if product is not None else []
    product_model = next(
        (
            variant.attributes.get("model")
            for variant in variants
            if variant.attributes.get("model")
        ),
        None,
    )
    storages = sorted(
        {
            variant.attributes["storage_gb"]
            for variant in variants
            if variant.attributes.get("storage_gb")
        },
        key=int,
    )

    await runs_q.mark_running(run_uuid)
    log = logger.bind(run_id=run_id, source=source.name, spider=source.adapter_name)
    log.info("collection_run_started")

    result = await run_spider(
        spider_name=source.adapter_name,
        source_id=source.id,
        run_id=run_uuid,
        base_url=source.base_url,
        product_name=product.name if product else None,
        product_model=product_model,
        storages=storages,
    )
    stats = await runs_q.get_run_stats(run_uuid)

    if not result.succeeded:
        log.error(
            "collection_run_failed",
            exit_code=result.exit_code,
            stderr_tail=result.stderr[-2000:],
        )
        await runs_q.finish_run(
            run_id=run_uuid,
            status=RunStatus.FAILED,
            stats=stats,
            failure_reason=f"spider exited with code {result.exit_code}",
        )
        return

    if stats.get("offers_observed", 0) == 0:
        log.error("collection_run_empty")
        await runs_q.finish_run(
            run_id=run_uuid,
            status=RunStatus.FAILED,
            stats=stats,
            failure_reason="collector produced no observations",
        )
        return

    pending_left = await sources_q.count_pending_product_pages(source.id)
    status = RunStatus.PARTIAL if pending_left > 0 else RunStatus.SUCCEEDED
    log.info("collection_run_finished", status=status.value, pending_left=pending_left, **stats)
    await runs_q.finish_run(run_id=run_uuid, status=status, stats=stats)
