# syntax=docker/dockerfile:1
# Multi-stage production Dockerfile for Boards backend
# Supports both API server and worker modes via CMD override

# Build stage - install dependencies and build the package
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /build

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (production only, no dev dependencies)
# Using --frozen to ensure reproducible builds
# Install with all generator and storage extras for out-of-box functionality
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --extra all

# Copy source code and build artifacts
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY README.md ./
COPY MANIFEST.in ./

# Install the package itself in the virtual environment
# Include all generator and storage extras for complete functionality
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra all

# Runtime stage - minimal production image
FROM python:3.12-slim AS runtime

# Install runtime dependencies (required for some Python packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r boards --gid=1000 && \
    useradd -r -g boards --uid=1000 --home-dir=/app --shell=/bin/bash boards

# Set working directory
WORKDIR /app

# Copy Python packages from builder's virtual environment
# Exclude unnecessary files to reduce image size
COPY --from=builder /build/.venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Remove unnecessary files to reduce image size
RUN find /usr/local/lib/python3.12/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.12/site-packages -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.12/site-packages -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.12/site-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Copy console scripts (boards-server, boards-worker, etc.)
# We selectively copy scripts to avoid overwriting the system Python binary
COPY --from=builder /build/.venv/bin/boards-* /usr/local/bin/
COPY --from=builder /build/.venv/bin/uvicorn /usr/local/bin/
COPY --from=builder /build/.venv/bin/dramatiq* /usr/local/bin/
COPY --from=builder /build/.venv/bin/alembic /usr/local/bin/

# Fix shebangs in copied scripts to point to system Python
RUN find /usr/local/bin -type f -executable -exec sed -i '1s|^#!/build/.venv/bin/python.*|#!/usr/local/bin/python3|' {} + 2>/dev/null || true

# Copy application code and migrations
COPY --from=builder --chown=boards:boards /build/src ./src
COPY --from=builder --chown=boards:boards /build/alembic ./alembic
COPY --from=builder --chown=boards:boards /build/alembic.ini ./

# Set Python path to include src directory
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER boards

# Expose API port (default 8800)
EXPOSE 8800

# Health check for API server
# Note: This will fail for worker-only containers, but that's acceptable
# as health checks can be disabled via docker-compose or runtime config
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8800/health || exit 1

# Default command: API server
# Override this command to run as worker:
#   docker run ... boards-backend dramatiq-gevent boards.workers.actors:broker --processes 1 --threads 50
CMD ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
