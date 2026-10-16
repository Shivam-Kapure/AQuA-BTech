FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HOME=/app/.cache

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --locked --no-dev

COPY app ./app
COPY .env.example ./.env.example

# Hugging Face Spaces runs the container as uid 1000; it needs write access for
# the embedding model cache, Chroma data, and Playwright scripts/artifacts.
RUN mkdir -p .cache data playwright_scripts playwright_artifacts \
    && chown -R 1000:1000 /app
USER 1000

# 7860 is the Hugging Face Spaces default; set PORT to override (e.g. 8000 locally).
EXPOSE 7860
CMD ["sh", "-c", "/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
