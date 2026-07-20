# syntax=docker/dockerfile:1

# --- Builder: resolve and install dependencies into a venv ---
FROM python:3.14-slim AS builder

# uv from the official distroless image (multi-arch)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

# --- Runtime: slim image with just the venv and app source ---
FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Non-root user; /app must be writable for NiceGUI's .nicegui storage dir
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /app/.venv /app/.venv
COPY . .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 5858

CMD ["python", "main.py"]
