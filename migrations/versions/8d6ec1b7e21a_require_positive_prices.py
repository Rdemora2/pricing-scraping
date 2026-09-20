"""require strictly positive price observations

Revision ID: 8d6ec1b7e21a
Revises: 4b72cbb64fb0
"""

from collections.abc import Sequence

from alembic import op

revision: str = "8d6ec1b7e21a"
down_revision: str | Sequence[str] | None = "4b72cbb64fb0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE price_observation "
        "DROP CONSTRAINT price_observation_price_minor_units_check"
    )
    op.execute(
        "ALTER TABLE price_observation ADD CONSTRAINT price_observation_price_positive "
        "CHECK (price_minor_units > 0)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE price_observation DROP CONSTRAINT price_observation_price_positive"
    )
    op.execute(
        "ALTER TABLE price_observation ADD CONSTRAINT "
        "price_observation_price_minor_units_check CHECK (price_minor_units >= 0)"
    )
