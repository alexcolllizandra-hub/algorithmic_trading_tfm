# Quantitative API image. Build context is the REPOSITORY ROOT so the existing
# perp_lab package is installed as the single quantitative core (no logic is
# duplicated). Runs as a non-root user with a container health check.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1) Dependency + package layer (cached until sources change).
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra api

# 2) Small config + manifest inputs the API needs (no large data baked in;
#    parquet is provided at runtime via a read-only volume).
COPY configs ./configs
COPY data/manifests ./data/manifests

# Non-root runtime user. The API is strictly read-only, so the user only needs
# read/execute on the (root-owned, world-readable) venv and inputs; avoid a
# recursive chown of the ~1GB venv which would create a huge, slow-to-export
# duplicate layer.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"

CMD ["uvicorn", "perp_lab.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
