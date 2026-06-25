# stage 1: Install cargo-chef
FROM rust:slim-bookworm AS chef
USER root
RUN cargo install cargo-chef
WORKDIR /app

# stage 2: Analyze project and prepare a build recipe
FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

# stage 3: Build deps and app
FROM chef AS builder
COPY --from=planner /app/recipe.json recipe.json

# Install C/C++ build tools required by rdkafka
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libssl-dev \
    libcurl4-openssl-dev \
    libsasl2-dev

# Build ONLY the deps
RUN cargo chef cook --release --recipe-path recipe.json

# Copy source code and build
COPY . .
RUN cargo build --release

# stage 4: Run
FROM debian:bookworm-slim
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    libcurl4 \
    libsasl2-2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/data_simulator ./

CMD ["./data_simulator"]