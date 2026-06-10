# ─── Stage 1: Builder ───────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


# ─── Stage 2: Runtime ───────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
    "-k", "uvicorn.workers.UvicornWorker", \
    "--workers", "4", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "120", \
    "--access-logfile", "-"]