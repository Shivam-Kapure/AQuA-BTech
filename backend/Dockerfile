FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --locked --no-dev

COPY app ./app
COPY .env.example ./.env.example

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
