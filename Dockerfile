FROM python:3.14-slim AS dependencies

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.12.11

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM dependencies AS builder

COPY alembic.ini scrapy.cfg ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY src ./src
COPY lab ./lab

RUN uv sync --frozen --no-dev

FROM python:3.14-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder --chown=app:app /app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "pricing_intel.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM dependencies AS browser-base

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONDONTWRITEBYTECODE=1

RUN .venv/bin/playwright install --with-deps --only-shell chromium \
    && chmod -R a+rX /ms-playwright

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

FROM browser-base AS browser-runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

USER app

CMD ["procrastinate", "-a", "pricing_intel.jobs.app.app", "worker", "--queues", "collection", "--concurrency", "1"]
