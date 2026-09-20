"""Runtime configuration loaded from environment variables.

Every setting has a local-friendly default so the service boots with
`docker compose up` and no manual `.env` authoring, per the project's
zero-cloud local requirement.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://pricing_intel:pricing_intel@localhost:5432/pricing_intel"
    environment: str = "local"
    log_level: str = "INFO"

    # Per-domain politeness limit applied both by Scrapy settings and by the
    # discovery scheduler; kept in one place so the two agree.
    collection_concurrency_per_domain: int = 2

    # How many evidence snapshots to keep per (source, url). Older rows are
    # pruned after each write so the evidence table does not grow unbounded
    # while still supporting reproducibility of recent runs.
    evidence_retention_per_url: int = 5

    @property
    def sqlalchemy_database_url(self) -> str:
        """Alembic goes through SQLAlchemy; the app talks to psycopg directly."""
        return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
