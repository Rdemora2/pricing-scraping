"""add listing rejection quarantine

Revision ID: c3a71f5d8e04
Revises: 8d6ec1b7e21a
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c3a71f5d8e04"
down_revision: str | Sequence[str] | None = "8d6ec1b7e21a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE rejection_stage AS ENUM ('access', 'extraction', 'matching')")
    op.execute(
        """
        CREATE TABLE listing_rejection (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            collection_run_id UUID NOT NULL REFERENCES collection_run (id) ON DELETE CASCADE,
            source_id UUID NOT NULL REFERENCES source (id) ON DELETE CASCADE,
            stage rejection_stage NOT NULL,
            reason TEXT NOT NULL,
            url TEXT NOT NULL,
            raw_title TEXT NOT NULL DEFAULT '',
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX listing_rejection_run_idx ON listing_rejection (collection_run_id)")
    op.execute(
        "CREATE INDEX listing_rejection_source_stage_idx "
        "ON listing_rejection (source_id, stage, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS listing_rejection")
    op.execute("DROP TYPE IF EXISTS rejection_stage")
