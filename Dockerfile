# ============================================================================
# Stage 1: builder — install python deps into /app/.venv using uv
# ============================================================================
ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:latest
FROM ${UV_IMAGE} AS uv-bin
FROM ${PYTHON_IMAGE} AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1

RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g; s|http://security.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
    && sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g; s|http://security.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-bin /uv /uvx /usr/local/bin/

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
# vista 代码运行时读 ".claude/skills/vista-factor-planning" / ".claude/skills/vista-python-factor"
# 这些文件从 vista 上游源码 (.codex/skills 和 .claude/skills 两份一致) 复制过来,随镜像交付。
COPY .claude/skills/ ./.claude/skills/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Image-slimming attempts (kept here as a "do not retry" note):
#   - Removing __pycache__/*.pyc saves ~150MB but *adds* ~1s to cold start
#     because CPython has to recompile every imported .py on first hit.
#     UV_COMPILE_BYTECODE=1 above intentionally pre-builds them.
#   - Removing in-package tests/docs/examples/benchmarks dirs only saves
#     ~8MB safely — most are real Python sub-packages (numpy.tests,
#     pandas.tests, botocore.docs is imported by boto3 to generate service
#     docstrings, numpy.testing / pandas.testing are public runtime APIs).
#     Deleting without an __init__.py guard breaks the runtime.
#   - `strip --strip-unneeded` on *.so / *.so.* breaks numpy's bundled
#     libscipy_openblas (ELF page-alignment errors on dlopen).
# Real cold-start wins live elsewhere: ACR image acceleration and FC
# provisioned concurrency for latency-sensitive functions.

# ============================================================================
# Stage 2: runtime — minimal image containing python + .venv
# ============================================================================
FROM ${PYTHON_IMAGE} AS runtime

RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g; s|http://security.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
    && sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g; s|http://security.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app /app

# Non-root runtime. Use a fixed UID/GID so FC log/file ownership is stable
# across deploys and readable by CI tooling that mounts the image.
RUN groupadd --system --gid 10001 vista \
    && useradd --system --uid 10001 --gid 10001 --home /home/vista --shell /usr/sbin/nologin vista \
    && mkdir -p /home/vista /tmp/vista-fc \
    && chown -R vista:vista /app /home/vista /tmp/vista-fc

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src:/app \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    LOG_FORMAT=json \
    FC_SERVER_PORT=9000 \
    HOME=/home/vista \
    VISTA_FC_TMP_ROOT=/tmp/vista-fc

USER vista:vista

EXPOSE 9000

# tini 负责信号；CMD 会被函数级 args 覆盖。
# 默认 args 只是占位；FC 必须在 customContainerConfig.args 里传 <module>:<func>。
ENTRYPOINT ["tini", "--", "python", "-m", "vista_fc.runtime.adapter"]
CMD ["handlers.factor_detect:handler"]
