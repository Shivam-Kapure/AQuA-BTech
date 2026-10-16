FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --locked --no-dev

COPY app ./app
COPY .env.example ./.env.example

# Run as a non-root user (uid 1000) with a writable home for the embedding model
# cache, Chroma data, and Playwright scripts/artifacts.
ENV HOME=/app
RUN mkdir -p .cache data playwright_scripts playwright_artifacts \
    && chown -R 1000:1000 /app
USER 1000
# Download the ONNX embedding model at build time so instances don't fetch it on every cold start.
RUN /app/.venv/bin/python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as E; E()(['warm-up'])"

# Listens on $PORT (Cloud Run sets 8080; 7860 when unset; 8000 via docker-compose).
EXPOSE 7860
CMD ["sh", "-c", "/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
