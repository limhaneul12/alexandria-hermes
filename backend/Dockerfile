FROM python:3.13-slim AS runtime

WORKDIR /app

# Install uv without pip
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock* ./
COPY alembic.ini ./alembic.ini
COPY app ./app
COPY migrations ./migrations

RUN uv sync --locked

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
