FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for better caching
COPY src/requirements.txt /tmp/requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN useradd -u 1000 -m appuser \
    && mkdir -p /app/audit \
    && chown -R appuser:appuser /app

# Install Python deps from wheels built in builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links /wheels -r /tmp/requirements.txt || true
COPY src/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY . /app

# Copy scripts
COPY scripts/entrypoint.sh /entrypoint.sh
COPY scripts/healthcheck.sh /healthcheck.sh
RUN chmod +x /entrypoint.sh /healthcheck.sh && chown appuser:appuser /entrypoint.sh /healthcheck.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD /healthcheck.sh || exit 1

ENTRYPOINT ["/entrypoint.sh"]
