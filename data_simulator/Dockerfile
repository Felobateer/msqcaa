# ---------------------
#  Stage 1: Build stage
# ---------------------
FROM rust:slim-bookworm AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y \
    pkg-config libssl-dev cmake g++ \
    libcurl4-openssl-dev libsasl2-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY Cargo.toml Cargo.lock ./
COPY src ./src

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/usr/local/cargo/git \
    --mount=type=cache,target=/app/target \
    cargo build --release && \
    cp /app/target/release/data_simulator /app/data_simulator

# ---------------------
#  Stage 2: Runtime stage
# ---------------------
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libssl3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -u 10001 appuser
USER appuser

COPY --from=builder /app/data_simulator /app/data_simulator

CMD ["./data_simulator"]