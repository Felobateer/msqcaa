# AGENTS.md — Instructions & System Architecture for AI Coding Agents

Welcome, Agent. You are operating in **MSQCAA** (Mass Spectrometry Quality Control AI Agent), an event-driven, production-grade MLOps and internal automation platform.

This document defines your entry points, development conventions, system boundaries, and verification commands. Follow these guidelines strictly.

---

## 1. Quick Start (`/init`)

To initialize your environment across services:

```bash
# 1. Start core backing services (Postgres, Kafka, Ollama, n8n)
docker compose up -d postgres_db kafka ollama n8n

# 2. Setup Python ML environment (Python 3.12 managed via uv)
cd ml
uv sync

# 3. Compile Rust Data Simulator
cd ../data_simulator
cargo build --release
