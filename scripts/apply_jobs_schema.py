"""Apply Procrastinate's schema once, keeping Docker bootstrap idempotent."""

from __future__ import annotations

import subprocess

import psycopg

from pricing_intel.config import get_settings


def main() -> None:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regtype('procrastinate_job_status')")
        row = cur.fetchone()
        assert row is not None
        schema_exists = row[0] is not None

    if schema_exists:
        print("Procrastinate schema already present; skipping bootstrap.")
        return

    subprocess.run(
        [
            "procrastinate",
            "-a",
            "pricing_intel.jobs.app.app",
            "schema",
            "--apply",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
