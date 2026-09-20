"""add source candidates

Revision ID: 4b72cbb64fb0
Revises: 497bec61c6e8
"""

from collections.abc import Sequence

from alembic import op

revision: str = "4b72cbb64fb0"
down_revision: str | Sequence[str] | None = "497bec61c6e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE UNIQUE INDEX product_name_unique_ci ON product (lower(name))")
    op.execute(
        """
        CREATE TABLE source_candidate (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            url TEXT NOT NULL,
            canonical_url TEXT NOT NULL UNIQUE,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            snippet TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL,
            query TEXT NOT NULL,
            trust_tier TEXT NOT NULL CHECK (trust_tier IN ('trusted', 'known', 'unknown')),
            status TEXT NOT NULL DEFAULT 'candidate'
                CHECK (status IN ('candidate', 'reviewed', 'rejected')),
            discovered_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX source_candidate_discovered_idx ON source_candidate (discovered_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source_candidate")
    op.execute("DROP INDEX IF EXISTS product_name_unique_ci")
