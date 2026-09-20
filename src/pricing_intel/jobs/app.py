"""Procrastinate wiring: a Postgres-backed job queue (SKIP LOCKED), no
Redis/RabbitMQ — the MVP's volume does not justify a second datastore.
"""

from __future__ import annotations

import procrastinate

from pricing_intel.config import get_settings

connector = procrastinate.PsycopgConnector(conninfo=get_settings().database_url)

app = procrastinate.App(connector=connector)

# Imported last and unused directly: importing the module registers its
# @app.task-decorated functions onto `app` above. Must stay after `app`
# is defined to avoid a circular import.
from pricing_intel.jobs import tasks  # noqa: E402,F401
