# syntax=docker/dockerfile:1.7

# ---------- Stage 1: build the virtualenv with uv ----------
FROM python:3.11-slim-bookworm AS builder

# Pull a pinned uv binary; pin the version for reproducible builds.
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first so the layer is cached when only source changes.
COPY pyproject.toml uv.lock ./

# Build a self-contained venv at /app/.venv with locked dependencies.
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
RUN uv sync --frozen --no-dev --no-install-project


# ---------- Stage 2: runtime ----------
FROM python:3.11-slim-bookworm AS runtime

# Reuse the venv built above.
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NEXTBOT_DATA_DIR=/app/data

# Install Chromium plus its system libraries via Playwright.
# `--with-deps` invokes apt-get under the hood; clean lists afterwards.
RUN /app/.venv/bin/playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Project source last so iterative code changes only invalidate this layer.
COPY . .

# Persist .env / app.db / .webui_auth.json across container restarts.
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 18081

CMD ["python", "bot.py"]
