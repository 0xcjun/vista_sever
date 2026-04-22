# syntax=docker/dockerfile:1.7

# ============================================================================
# Stage 1: builder — install python deps into /app/.venv using uv
# ============================================================================
FROM python:3.11-slim-bookworm AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy lock + manifest + README (hatchling reads README.md for wheel metadata)
COPY pyproject.toml uv.lock README.md ./

# Install deps only (no project) — secret-mount for private index token.
# Expected .env.build contents (loaded via `set -a . ... set +a`):
#   UV_INDEX_ZBCZSC_DEV_USERNAME=<user>
#   UV_INDEX_ZBCZSC_DEV_PASSWORD=<token>
RUN --mount=type=secret,id=uv_index,target=/run/secrets/uv_index \
    --mount=type=cache,target=/root/.cache/uv \
    if [ -f /run/secrets/uv_index ]; then \
      set -a && . /run/secrets/uv_index && set +a; \
    fi; \
    uv sync --frozen --no-dev --no-install-project

# Now copy actual source and install project
COPY src/ ./src/
COPY handlers/ ./handlers/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================================================
# Stage 2: runtime — minimal image containing python + .venv
# ============================================================================
FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src:/app \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    LOG_FORMAT=json \
    FC_SERVER_PORT=9000

EXPOSE 9000

# tini 负责信号；CMD 会被函数级 args 覆盖。
# 默认 args 只是占位；FC 必须在 customContainerConfig.args 里传 <module>:<func>。
ENTRYPOINT ["tini", "--", "python", "-m", "vista_fc.runtime.adapter"]
CMD ["handlers.factor_detect:handler"]
