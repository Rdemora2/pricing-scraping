from __future__ import annotations

from psycopg.rows import class_row

from pricing_intel.db.pool import connection
from pricing_intel.domain.models import SourceCandidate


async def upsert_candidate(
    *,
    url: str,
    canonical_url: str,
    domain: str,
    title: str,
    snippet: str,
    provider: str,
    query: str,
    trust_tier: str,
) -> SourceCandidate:
    async with connection() as conn, conn.cursor(row_factory=class_row(SourceCandidate)) as cur:
        await cur.execute(
            """
            INSERT INTO source_candidate
                (url, canonical_url, domain, title, snippet, provider, query, trust_tier)
            VALUES
                (%(url)s, %(canonical_url)s, %(domain)s, %(title)s, %(snippet)s,
                 %(provider)s, %(query)s, %(trust_tier)s)
            ON CONFLICT (canonical_url) DO UPDATE SET
                url = EXCLUDED.url,
                title = EXCLUDED.title,
                snippet = EXCLUDED.snippet,
                provider = EXCLUDED.provider,
                query = EXCLUDED.query,
                trust_tier = EXCLUDED.trust_tier,
                discovered_at = now()
            RETURNING id, url, canonical_url, domain, title, snippet, provider,
                      query, trust_tier, status, discovered_at
            """,
            {
                "url": url,
                "canonical_url": canonical_url,
                "domain": domain,
                "title": title,
                "snippet": snippet,
                "provider": provider,
                "query": query,
                "trust_tier": trust_tier,
            },
        )
        candidate = await cur.fetchone()
        assert candidate is not None
        return candidate


async def list_candidates(*, limit: int = 50) -> list[SourceCandidate]:
    async with connection() as conn, conn.cursor(row_factory=class_row(SourceCandidate)) as cur:
        await cur.execute(
            """
            SELECT id, url, canonical_url, domain, title, snippet, provider,
                   query, trust_tier, status, discovered_at
            FROM source_candidate
            ORDER BY
                CASE trust_tier WHEN 'trusted' THEN 0 WHEN 'known' THEN 1 ELSE 2 END,
                discovered_at DESC
            LIMIT %(limit)s
            """,
            {"limit": min(max(limit, 1), 100)},
        )
        return await cur.fetchall()


async def prune_candidates(*, retention_days: int = 30, max_rows: int = 1000) -> None:
    async with connection() as conn:
        await conn.execute(
            """
            DELETE FROM source_candidate
            WHERE status = 'candidate'
              AND (
                discovered_at < now() - make_interval(days => %(retention_days)s)
                OR id IN (
                    SELECT id FROM source_candidate
                    WHERE status = 'candidate'
                    ORDER BY discovered_at DESC
                    OFFSET %(max_rows)s
                )
              )
            """,
            {"retention_days": retention_days, "max_rows": max_rows},
        )
