from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from pricing_intel.api.routers.collection import _is_allowed_local_origin
from pricing_intel.api.schemas import (
    DiscoverySearchRequest,
    ManualCandidateRequest,
    SourceCandidateResponse,
)
from pricing_intel.db.queries import candidates as candidates_q
from pricing_intel.discovery.providers.brave import SearchProviderError
from pricing_intel.discovery.search_service import (
    DiscoveryNotConfiguredError,
    DiscoveryRateLimitError,
    add_manual_candidate,
    discover_candidates,
)
from pricing_intel.domain.models import SourceCandidate

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _response(candidate: SourceCandidate) -> SourceCandidateResponse:
    return SourceCandidateResponse(
        id=candidate.id,
        url=candidate.url,
        domain=candidate.domain,
        title=candidate.title,
        snippet=candidate.snippet,
        provider=candidate.provider,
        query=candidate.query,
        trust_tier=candidate.trust_tier,
        status=candidate.status,
        discovered_at=candidate.discovered_at,
    )


@router.get("/candidates", response_model=list[SourceCandidateResponse])
async def list_candidates() -> list[SourceCandidateResponse]:
    return [_response(item) for item in await candidates_q.list_candidates()]


@router.post("/candidates", response_model=SourceCandidateResponse, status_code=201)
async def create_candidate(
    payload: ManualCandidateRequest, request: Request
) -> SourceCandidateResponse:
    origin = request.headers.get("origin")
    if origin is not None and not _is_allowed_local_origin(origin):
        raise HTTPException(status_code=403, detail="origin not allowed")
    try:
        candidate = await add_manual_candidate(
            url=payload.url.strip(),
            title=payload.title.strip(),
            snippet=payload.snippet.strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _response(candidate)


@router.post("/search", response_model=list[SourceCandidateResponse])
async def search(
    payload: DiscoverySearchRequest, request: Request
) -> list[SourceCandidateResponse]:
    origin = request.headers.get("origin")
    if origin is not None and not _is_allowed_local_origin(origin):
        raise HTTPException(status_code=403, detail="origin not allowed")
    try:
        candidates = await discover_candidates(payload.query.strip())
    except DiscoveryNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DiscoveryRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except SearchProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [_response(item) for item in candidates]
