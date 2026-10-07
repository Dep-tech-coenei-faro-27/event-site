FROM python:3.13-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

ARG UV_VERSION=0.12.23
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh \
    | env UV_UNMANAGED_INSTALL=/usr/local/bin sh

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/media \
    && chown -R app:app /app

USER app
WORKDIR /app

COPY --chown=app:app pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=app:app . .

RUN uv sync --frozen --no-dev \
    && sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh

# Atrás do túnel ou do proxy o IP do visitante vem em X-Forwarded-For. O contentor confia nas
# redes privadas do Docker; para mudar, defina FORWARDED_ALLOW_IPS no backend/.env.
ENV FORWARDED_ALLOW_IPS=172.16.0.0/12

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
