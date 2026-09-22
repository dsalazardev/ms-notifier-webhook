FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencias
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["sh", "-c", "python -c \"import sys, urllib.request, os; p=os.getenv('PORT', '8000'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/api/v1/health', timeout=3).status == 200 else 1)\""]

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]