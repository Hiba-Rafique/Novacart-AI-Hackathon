# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN python -m pip install --no-cache-dir uv

COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api/src ./src
COPY policies ./policies
COPY apps/api/data ./data
RUN uv sync --frozen --no-dev
RUN .venv/bin/python -c "from pathlib import Path; from policyguard.ingest import validate_index; validate_index(Path('/app/policies'), Path('/app/data/index'))"

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DATA_DIR="/app/data" \
    INDEX_DIR="/app/data/index" \
    POLICIES_DIR="/app/policies" \
    APP_TIMEZONE="Asia/Karachi" \
    PORT=7860 \
    HOME=/home/user

RUN useradd --create-home --uid 1000 user
WORKDIR /app
COPY --from=builder --chown=user:user /app /app

USER user
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=4s --start-period=20s --retries=3 \
  CMD python -c 'import os, urllib.request; urllib.request.urlopen("http://127.0.0.1:" + os.environ.get("PORT", "7860") + "/healthz", timeout=3)' || exit 1

CMD ["sh", "-c", "exec uvicorn policyguard.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
