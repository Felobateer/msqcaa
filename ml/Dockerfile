FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 1. Copy ONLY dependency files first
COPY pyproject.toml uv.lock* ./

# 2. Mount a persistent cache folder for uv to reuse downloaded packages
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r pyproject.toml

# 3. Copy your actual code AFTER dependencies are installed
COPY . .

# Since you removed Jupyter, run your main script (or keep it alive for dev)
CMD ["sleep", "infinity"]