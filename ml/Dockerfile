FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install Java for PySpark BEFORE Python dependencies to maximize cache efficiency
RUN apt-get update && apt-get install -y default-jre && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 2. Copy ONLY dependency files first
COPY pyproject.toml uv.lock ./

# 3. Use `uv sync` to create the virtual environment expected by `uv run`
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# 4. Copy your actual code AFTER dependencies are installed
COPY . .

# Keep container alive for dev and ML app
CMD ["sleep", "infinity"]