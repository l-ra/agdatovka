FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AG_ENV=deploy \
    AG_AUTH_PROFILE=deploy

RUN groupadd --system --gid 10001 agdatovka \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin agdatovka
WORKDIR /app
COPY pyproject.toml README.md ./
COPY ag_datovka ./ag_datovka
COPY migrations ./migrations
RUN mkdir -p /app/data /app/objects && chown -R agdatovka:agdatovka /app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=2)"
CMD ["python", "-m", "ag_datovka.server", "--host", "0.0.0.0", "--port", "8080"]

