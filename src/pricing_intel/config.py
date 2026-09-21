"""Runtime configuration loaded from environment variables.

Every setting has a local-friendly default so the service boots with
`docker compose up` and no manual `.env` authoring, per the project's
zero-cloud local requirement.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://pricing_intel:pricing_intel@localhost:5432/pricing_intel"
    environment: str = "local"
    log_level: str = "INFO"

    # Per-domain politeness limit applied both by Scrapy settings and by the
    # discovery scheduler; kept in one place so the two agree.
    collection_concurrency_per_domain: int = 2

    # How many complete collection runs to keep per (source, url). Every offer
    # extracted from a retained page remains linked to the same HTML evidence.
    evidence_retention_per_url: int = 5

    # Older observations remain in history but no longer influence the
    # current market comparison.
    comparison_max_age_hours: int = Field(default=72, ge=1, le=8760)

    # Optional. Broad web discovery stays disabled until the operator provides
    # a Brave Search API key; the key is only read server-side.
    brave_search_api_key: str | None = None
    discovery_max_results: int = 20
    discovery_query_variations: int = 3

    @property
    def sqlalchemy_database_url(self) -> str:
        """Alembic goes through SQLAlchemy; the app talks to psycopg directly."""
        return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
