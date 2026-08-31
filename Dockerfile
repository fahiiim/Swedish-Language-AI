# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN python -m venv /opt/venv
COPY requirements.lock ./
RUN /opt/venv/bin/pip install --no-compile --requirement requirements.lock


FROM python:3.12-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579 AS runtime

ARG BUILD_VERSION=dev
ARG BUILD_REVISION=unknown

LABEL org.opencontainers.image.title="Swedish Citizenship Question API" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.revision="${BUILD_REVISION}"

ENV APP_ENV=production \
    DOCS_ENABLED=false \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app app ./app

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health', timeout=3)"]

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2 --proxy-headers --forwarded-allow-ips='*' --no-access-log"]
