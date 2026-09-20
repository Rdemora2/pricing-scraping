from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from pricing_intel.api.schemas import RunResponse, SourceResponse
from pricing_intel.db.queries import runs as runs_q
from pricing_intel.db.queries import sources as sources_q
from pricing_intel.discovery.service import SourceNotEnabledError, trigger_collection
from pricing_intel.domain.models import CollectionRun

router = APIRouter(tags=["collection"])


def _run_response(run: CollectionRun) -> RunResponse:
    return RunResponse(
        id=run.id,
        source_id=run.source_id,
        trigger=run.trigger.value,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        stats=run.stats,
        failure_reason=run.failure_reason,
    )


@router.get("/sources", response_model=list[SourceResponse])
async def list_sources() -> list[SourceResponse]:
    sources = await sources_q.list_enabled_sources()
    return [
        SourceResponse(
            id=source.id,
            name=source.name,
            base_url=source.base_url,
            kind=source.kind.value,
            status=source.status.value,
        )
        for source in sources
    ]


@router.post("/sources/{source_id}/collect", response_model=RunResponse, status_code=202)
async def collect_source(source_id: UUID) -> RunResponse:
    try:
        run = await trigger_collection(source_id)
    except SourceNotEnabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _run_response(run)


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: UUID) -> RunResponse:
    run = await runs_q.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _run_response(run)
