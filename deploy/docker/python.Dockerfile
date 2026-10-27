FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY apps ./apps
COPY packages ./packages
COPY services ./services

RUN uv sync --frozen --all-packages --no-dev

EXPOSE 8000
