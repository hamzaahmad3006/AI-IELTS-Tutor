# syntax=docker/dockerfile:1

# ---- base ----
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# ---- dependencies ----
FROM base AS deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- runtime ----
FROM base AS runtime
# Non-root user; /app owned by it so the app can write a SQLite file in dev.
RUN adduser --disabled-password --gecos "" appuser
COPY --from=deps /usr/local /usr/local
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
