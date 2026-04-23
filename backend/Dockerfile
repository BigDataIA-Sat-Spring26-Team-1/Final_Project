# syntax=docker/dockerfile:1.7
# ------------------------------------------------------------------------------
# CurateAI Backend — Cloud Run production image
#
# Design goals:
#   1. Small runtime footprint via a two-stage build (builder compiles the venv,
#      runtime ships only the interpreter + resolved site-packages).
#   2. Deterministic installs — `uv sync --frozen` pins everything to uv.lock so
#      an image built today will build byte-identical a month from now.
#   3. Cloud Run contract compliance — respect the injected $PORT (defaults to
#      8080) and run as a non-root user so gVisor's sandbox stays happy.
#   4. Signals pass through cleanly — CMD uses `exec` so uvicorn becomes PID 1
#      and actually receives SIGTERM when Cloud Run drains the instance.
# ------------------------------------------------------------------------------

# ---------- Stage 1: builder ----------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# Minimal build toolchain — only needed if any wheel has to compile from sdist.
# Most of our deps ship manylinux wheels, but trafilatura/lxml occasionally
# falls back to source on niche arches, so we keep this cheap safety net.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# uv is fetched by copying it straight out of the official distroless image —
# avoids a `pip install uv` round-trip and keeps the layer deterministic.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only the dep manifests first so the resolve layer caches across code edits.
COPY pyproject.toml uv.lock ./

# Create the venv with prod-only deps. `--frozen` refuses to touch the lockfile;
# if pyproject.toml drifts from uv.lock the build fails loudly rather than
# silently shipping unpinned versions.
RUN uv sync --frozen --no-dev --no-install-project

# Now layer in the application itself. Kept separate so iterating on app code
# doesn't invalidate the (expensive) dependency layer above.
COPY app/ ./app/
RUN uv sync --frozen --no-dev


# ---------- Stage 2: runtime ---------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Cloud Run injects PORT; 8080 is only a local-dev / docker-compose default.
    PORT=8080

# libgomp1: runtime dep of scikit-learn's OpenMP kernels.
# curl:     used by the HEALTHCHECK directive below; ~1 MB, worth it.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 app \
    && useradd  --system --uid 1001 --gid app --home /app --shell /usr/sbin/nologin app

WORKDIR /app

# Copy the resolved venv + app from the builder. Ownership flip happens in the
# single COPY so we don't need a follow-up `chown -R` layer.
COPY --from=builder --chown=app:app /app /app

USER app

EXPOSE 8080

# Local-only convenience — Cloud Run ignores HEALTHCHECK and runs its own
# startup/liveness probes. Still useful under docker-compose.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail --silent "http://127.0.0.1:${PORT}/livez" || exit 1

# `exec` + shell form so $PORT expands AND uvicorn owns PID 1 for clean SIGTERM.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'
