# TABLE WARS - Production Dockerfile
# Multi-stage build for optimized production image

FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Production stage
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 tablewars && \
    mkdir -p /app /app/logs /app/data && \
    chown -R tablewars:tablewars /app

WORKDIR /app

# Copy Python packages from builder
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copy application code
COPY --chown=tablewars:tablewars server/ ./server/

# Switch to non-root user
USER tablewars

# Expose port
EXPOSE 5001

# Health check — uses the DB-free /api/runtime/health (cheaper + truer
# liveness than /api/stats, which queries the database).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/api/runtime/health').read()" || exit 1

# Run with gunicorn for production.
# GeventWebSocketWorker provides WebSocket support for the legacy
# Socket.IO flows.
#
# --workers 1 is REQUIRED, not a default: the multi-game runtime keeps
# authoritative match state in process memory and runs the tick loop in
# this worker. Until per-match ownership claiming lands (see
# server/runtime/CONTEXT.md), additional workers would double-tick matches.
# Scale by running one container per venue (LOCATION_ID), not by adding
# workers. HTTP concurrency within a venue is handled by the gevent worker.
CMD ["gunicorn", \
     "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
     "--workers", "1", \
     "--bind", "0.0.0.0:5001", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--chdir", "server", \
     "app:app"]
