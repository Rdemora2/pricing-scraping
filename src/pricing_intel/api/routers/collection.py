from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from pricing_intel.api.schemas import RunResponse, SourceResponse
from pricing_intel.db.queries import runs as runs_q
from pricing_intel.db.queries import sources as sources_q
from pricing_intel.discovery.service import SourceNotEnabledError, trigger_collection
from pricing_intel.domain.models import CollectionRun

router = APIRouter(tags=["collection"])


def _is_allowed_local_origin(origin: str) -> bool:
    parsed = urlsplit(origin)
    return (
        parsed.scheme == "http"
        and parsed.hostname in {"localhost", "127.0.0.1"}
        and parsed.username is None
        and parsed.password is None
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
    )


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
async def list_sources(enabled_only: bool = True) -> list[SourceResponse]:
    sources = (
        await sources_q.list_enabled_sources() if enabled_only else await sources_q.list_sources()
    )
    return [
        SourceResponse(
            id=source.id,
            name=source.name,
            base_url=source.base_url,
            kind=source.kind.value,
            status=source.status.value,
            adapter_name=source.adapter_name,
        )
        for source in sources
    ]


@router.post("/sources/{source_id}/collect", response_model=RunResponse, status_code=202)
async def collect_source(source_id: UUID, request: Request) -> RunResponse:
    origin = request.headers.get("origin")
    if origin is not None and not _is_allowed_local_origin(origin):
        raise HTTPException(status_code=403, detail="origin not allowed")

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
